#!/usr/bin/env python3
"""
bootstrap_met_office_datahub.py -- Register curated Met Office Weather DataHub
Land Observations resources on the OS4CSAPI server.
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config, _auth_header,
    api_put, find_by_uid, ensure_procedure, ensure_system, ensure_datastream, ensure_deployment,
    clean_resource, add_bootstrap_args, print_summary,
)


VALID_TIME_START = "2026-01-01T00:00:00Z"

PROC_UID = "urn:os4csapi:procedure:met-office-datahub-land-observations:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:met-office-datahub-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:met-office-datahub-land-observations:v1"

MET_OFFICE_HOME = "https://datahub.metoffice.gov.uk/"
MET_OFFICE_DOCS = "https://datahub.metoffice.gov.uk/docs"
MET_OFFICE_GLOSSARY = "https://datahub.metoffice.gov.uk/docs/glossary?models=mo-land-observations"
LAND_OBS_OVERVIEW = "https://datahub.metoffice.gov.uk/docs/g/category/observations/overview"
LAND_OBS_API_DOCS = "https://datahub.metoffice.gov.uk/docs/g/category/observations/type/land-observations/api-documentation"
LAND_OBS_PRICING = "https://datahub.metoffice.gov.uk/pricing/observations"
LAND_OBS_API_CONTEXT = "/observation-land/1"
LAND_OBS_BASE_URL = "https://data.hub.api.metoffice.gov.uk/observation-land/1"


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_stations() -> list[dict]:
    return _load_config()["stations"]


def _load_parameters() -> list[dict]:
    return _load_config()["parameters"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:met-office-datahub-land-observations:{_uid_token(station_id)}:v1"


def _deploy_uid(station_id: str) -> str:
    return f"urn:os4csapi:deployment:met-office-datahub-land-observations-{_uid_token(station_id)}:v1"


def _datastream_uid(station: dict, parameter: dict) -> str:
    return (
        "urn:os4csapi:datastream:met-office-datahub-land-observations:"
        f"{_uid_token(station['id'])}:{parameter['outputName']}:v1"
    )


def _nearest_url(station: dict) -> str:
    return f"{LAND_OBS_BASE_URL}/nearest?latitude={station['lat']}&longitude={station['lon']}"


def _observation_url(station: dict) -> str:
    geohash = station.get("geohash") or "{resolved-geohash}"
    return f"{LAND_OBS_BASE_URL}/{quote(str(geohash), safe='')}"


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "Met Office DataHub Land Observations v1",
        "description": (
            "Publishes a curated set of Met Office Weather DataHub Land Observations "
            "for selected UK weather locations."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "Met Office DataHub Land Observations v1",
    "description": (
        "Fetches recent hourly observations from the Met Office Weather DataHub "
        "Land Observations API. The initial curated set uses the documented nearest "
        "location/geohash flow and publishes selected station weather parameters."
    ),
    "keywords": [
        "Met Office",
        "Weather DataHub",
        "Land Observations",
        "weather",
        "meteorology",
        "WMO",
        "hourly observations",
    ],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Weather DataHub", "link": {"href": MET_OFFICE_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Weather DataHub Docs", "link": {"href": MET_OFFICE_DOCS, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Land Observations Overview", "link": {"href": LAND_OBS_OVERVIEW, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Land Observations API Documentation", "link": {"href": LAND_OBS_API_DOCS, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Land Observations Glossary", "link": {"href": MET_OFFICE_GLOSSARY, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Land Observations Pricing", "link": {"href": LAND_OBS_PRICING, "type": "text/html"}},
    ],
    "contacts": [
        {
            "role": "operator",
            "organisationName": "Met Office",
            "contactInfo": {"onlineResource": {"linkage": "https://www.metoffice.gov.uk/"}},
        },
        {
            "role": "publisher",
            "organisationName": "OS4CSAPI",
            "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}},
        },
    ],
}


def _system_stub(station: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _system_uid(station["id"]),
            "featureType": "sosa:Sensor",
            "name": f"Met Office Land Observations {station['name']}",
            "description": station["description"],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    geohash = station.get("geohash") or "Resolved from nearest endpoint at runtime"
    docs = [
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Met Office Land Observations API Documentation",
            "link": {"href": LAND_OBS_API_DOCS, "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Nearest location query",
            "description": "Documented lookup used to resolve the nearest Met Office Land Observations location/geohash.",
            "link": {"href": _nearest_url(station), "type": "application/json"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Observation location query",
            "description": "Observation query for the resolved geohash. Placeholder remains until geohash is resolved.",
            "link": {"href": _observation_url(station), "type": "application/json"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Land Observations Glossary",
            "link": {"href": MET_OFFICE_GLOSSARY, "type": "text/html"},
        },
    ]

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station["id"]),
        "uniqueId": _system_uid(station["id"]),
        "definition": "sosa:System",
        "label": f"Met Office Land Observations {station['name']}",
        "description": (
            f"Curated Met Office Weather DataHub Land Observations location for {station['name']}. "
            "The publisher resolves the nearest Met Office observation location/geohash and publishes selected hourly weather parameters."
        ),
        "keywords": ["Met Office", "Weather DataHub", "Land Observations", "weather", station["id"], station["name"]],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": station["name"]},
            {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "Curated Location ID", "value": station["id"]},
            {"definition": "http://sensorml.com/ont/swe/property/Identifier", "label": "Met Office Geohash", "value": geohash},
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(station["id"])},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "Met Office Land Observations weather station"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Weather observation monitoring and situational awareness"},
        ],
        "contacts": [
            {"role": "operator", "organisationName": "Met Office", "contactInfo": {"onlineResource": {"linkage": "https://www.metoffice.gov.uk/"}}},
        ],
        "documents": docs,
        "characteristics": [{"label": "Location Properties", "characteristics": [
            {"type": "Text", "name": "curated_location_id", "label": "Curated Location ID", "value": station["id"]},
            {"type": "Text", "name": "met_office_api_context", "label": "Met Office API Context", "value": LAND_OBS_API_CONTEXT},
            {"type": "Text", "name": "geohash", "label": "Resolved Geohash", "value": geohash},
            {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": station.get("selectionReason", "Curated demo location")},
            {"type": "Text", "name": "free_plan_limit", "label": "Free Plan Limit", "value": "360 calls per day"},
        ]}],
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _go_compatible_system_sml(sml: dict, base_url: str) -> dict:
    if "csapi-go" not in base_url:
        return sml
    compat = dict(sml)
    compat.pop("characteristics", None)
    return compat


def _datastream_schema(station: dict, parameter: dict) -> dict:
    result_field = parameter["resultField"]
    return {
        "uid": _datastream_uid(station, parameter),
        "outputName": parameter["outputName"],
        "name": parameter["label"],
        "description": (
            f"{parameter['label']} from the Met Office Weather DataHub Land Observations API "
            f"for the curated {station['name']} location."
        ),
        "documentation": [
            {"title": "Land Observations API Documentation", "href": LAND_OBS_API_DOCS, "rel": "documentation"},
            {"title": "Land Observations Glossary", "href": MET_OFFICE_GLOSSARY, "rel": "describedby"},
            {"title": "Nearest Location Query", "href": _nearest_url(station), "rel": "service"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": f"Met Office {parameter['label']} Observation",
                "description": "Met Office Land Observations reading with source metadata.",
                "fields": [
                    {"type": "Text", "name": "locationId", "label": "Curated Location ID", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "geohash", "label": "Met Office Geohash", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "parameter", "label": "Parameter", "definition": "http://sensorml.com/ont/swe/property/ObservableProperty"},
                    {"type": "Quantity", "name": result_field, "label": parameter["label"], "definition": "http://sensorml.com/ont/swe/property/Value", "uom": {"code": parameter.get("uom", parameter["unit"])}},
                    {"type": "Text", "name": "unit", "label": "Unit", "definition": "http://sensorml.com/ont/swe/property/Unit"},
                    {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-2.5, 54.5]},
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "Met Office DataHub Demo",
            "description": "Top-level grouping for curated Met Office Weather DataHub publisher resources.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-2.5, 54.5]},
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "Met Office Land Observations Locations",
            "description": "Grouping deployment for curated Met Office Land Observations weather locations.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _deploy_uid(station["id"]),
            "featureType": "sosa:Deployment",
            "name": f"Met Office {station['name']}",
            "description": f"Deployment node linking curated Met Office Land Observations location {station['name']} to its CSAPI weather system.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": f"{base_url.rstrip('/')}/systems/{system_server_id}",
                "uid": _system_uid(station["id"]),
                "title": f"Met Office Land Observations {station['name']}",
            },
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool = False, stats: dict):
    stations = _load_stations()
    for station in stations:
        clean_resource(base_url, auth, "deployments", _deploy_uid(station["id"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for station in stations:
        clean_resource(base_url, auth, "systems", _system_uid(station["id"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _ensure_system_resilient(base_url: str, auth: str, station: dict,
                             *, dry_run: bool, stats: dict, force_sml: bool) -> str | None:
    uid = _system_uid(station["id"])
    try:
        return ensure_system(
            base_url, auth, uid, _system_stub(station),
            _go_compatible_system_sml(_system_sml(station), base_url),
            dry_run=dry_run, stats=stats, force_sml=force_sml,
        )
    except RuntimeError as exc:
        if "HTTP 500 POST" not in str(exc) or "/systems" not in str(exc):
            raise
        recovered = find_by_uid(base_url, auth, "systems", uid, no_cache=True)
        if not recovered:
            raise
        print(f"  [WARN] Server returned HTTP 500 after creating system {uid}; recovered id={recovered}")
        if not dry_run:
            try:
                api_put(base_url, f"systems/{recovered}",
                        _go_compatible_system_sml(_system_sml(station), base_url),
                        auth, content_type="application/sml+json")
                print(f"  [SML] PUT SensorML for recovered system {uid} (id={recovered})")
            except Exception as sml_exc:
                print(f"  [WARN] SML PUT skipped for recovered system {uid} (id={recovered}): {sml_exc}")
        if stats:
            stats.setdefault("recovered", 0)
            stats["recovered"] += 1
        return recovered


def bootstrap(*, clean: bool = False, clean_only: bool = False,
              dry_run: bool = False, force_sml: bool = False):
    server_config = get_config()
    base_url = server_config["base_url"]
    auth = _auth_header(server_config["user"], server_config["password"])
    stations = _load_stations()
    parameters = _load_parameters()
    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  Met Office DataHub Land Observations -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)}")
    print(f"  Parameters:{len(parameters)}")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}")
    print()

    if clean or clean_only:
        print("  -- Cleaning existing resources --")
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    print("  -- Procedure --")
    ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_STUB, PROCEDURE_SML,
                     dry_run=dry_run, stats=stats, force_sml=force_sml)

    print("  -- Systems + Datastreams --")
    system_ids: dict[str, str] = {}
    for station in stations:
        sys_id = _ensure_system_resilient(
            base_url, auth, station, dry_run=dry_run, stats=stats, force_sml=force_sml)
        if sys_id:
            system_ids[station["id"]] = sys_id
        for parameter in parameters:
            if dry_run and not sys_id:
                print(f"  [DRY] Would create datastream '{parameter['outputName']}' on system {station['id']}")
                continue
            ensure_datastream(base_url, auth, sys_id or "pending", parameter["outputName"],
                              _datastream_schema(station, parameter),
                              dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id, dry_run=dry_run, stats=stats)
    for station in stations:
        sys_id = system_ids.get(station["id"]) or "pending"
        ensure_deployment(base_url, auth, _deploy_uid(station["id"]),
                          _deploy_station(station, sys_id, base_url),
                          parent_id=group_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap Met Office DataHub Land Observations resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only,
              dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()