#!/usr/bin/env python3
"""
bootstrap_met_office_global_spot.py -- Register curated Met Office Weather
DataHub Global Spot forecast resources on the OS4CSAPI server.
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config, _auth_header,
    api_put, find_by_uid, ensure_procedure, ensure_system, ensure_datastream, ensure_deployment,
    clean_resource, add_bootstrap_args, print_summary,
)


VALID_TIME_START = "2026-01-01T00:00:00Z"

PROC_UID = "urn:os4csapi:procedure:met-office-datahub-global-spot-hourly:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:met-office-datahub-global-spot-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:met-office-datahub-global-spot-hourly:v1"

MET_OFFICE_HOME = "https://datahub.metoffice.gov.uk/"
MET_OFFICE_DOCS = "https://datahub.metoffice.gov.uk/docs"
MET_OFFICE_GLOSSARY = "https://datahub.metoffice.gov.uk/docs/glossary"
SITE_SPECIFIC_OVERVIEW = "https://datahub.metoffice.gov.uk/docs/g/category/site-specific/overview"
SITE_SPECIFIC_PRICING = "https://datahub.metoffice.gov.uk/pricing/site-specific"
GLOBAL_SPOT_API_CONTEXT = "/sitespecific/v0"
GLOBAL_SPOT_BASE_URL = "https://data.hub.api.metoffice.gov.uk/sitespecific/v0"
GLOBAL_SPOT_DEFAULT_HOURLY_PATH = "/point/hourly"
PUBLISH_INTERVAL_SECONDS = 3600
GLOBAL_SPOT_THUMBNAIL_DATA_URI = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 320 200'%3E"
    "%3Crect width='320' height='200' fill='%23082f49'/%3E"
    "%3Cpath d='M0 138 C44 112 82 160 128 132 S210 92 320 126 L320 200 L0 200 Z' fill='%230f766e'/%3E"
    "%3Cpath d='M0 158 C58 128 104 178 166 144 S258 118 320 146' fill='none' stroke='%235eead4' stroke-width='3' opacity='.75'/%3E"
    "%3Ccircle cx='238' cy='58' r='26' fill='%23fef3c7'/%3E"
    "%3Cpath d='M70 66 h86 a26 26 0 0 0 -44 -18 a35 35 0 0 0 -66 11 a22 22 0 0 0 24 7z' fill='%23e0f2fe'/%3E"
    "%3Cpath d='M68 96 h178' stroke='%2393c5fd' stroke-width='4' stroke-linecap='round' stroke-dasharray='12 9'/%3E"
    "%3Ctext x='160' y='178' text-anchor='middle' font-family='Arial,sans-serif' font-size='19' font-weight='700' fill='%23f8fafc'%3EGlobal Spot Forecast%3C/text%3E"
    "%3C/svg%3E"
)


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "forecast_points.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_locations() -> list[dict]:
    return _load_config()["locations"]


def _load_parameters() -> list[dict]:
    return _load_config()["parameters"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _system_uid(location_id: str) -> str:
    return f"urn:os4csapi:system:met-office-datahub-global-spot:{_uid_token(location_id)}:v1"


def _deploy_uid(location_id: str) -> str:
    return f"urn:os4csapi:deployment:met-office-datahub-global-spot-{_uid_token(location_id)}:v1"


def _datastream_uid(location: dict, parameter: dict) -> str:
    return (
        "urn:os4csapi:datastream:met-office-datahub-global-spot:"
        f"{_uid_token(location['id'])}:{parameter['outputName']}:v1"
    )


def _forecast_url(location: dict) -> str:
    query = urlencode({"latitude": f"{location['lat']:.4f}", "longitude": f"{location['lon']:.4f}"})
    return f"{GLOBAL_SPOT_BASE_URL}{GLOBAL_SPOT_DEFAULT_HOURLY_PATH}?{query}"


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:Procedure",
        "name": "Met Office DataHub Global Spot Hourly Forecast v1",
        "description": (
            "Publishes deterministic hourly point forecasts from the Met Office "
            "Weather DataHub Global Spot / Site-Specific Forecast API for selected UK locations."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ForecastingProcedure",
    "label": "Met Office DataHub Global Spot Hourly Forecast v1",
    "description": (
        "Fetches deterministic hourly site-specific forecasts from the Met Office "
        "Weather DataHub Global Spot API. Published CSAPI observations represent "
        "forecast values with explicit issue time, valid time, lead time, location, "
        "parameter, unit, and source metadata. These resources are virtual forecast "
        "points, not physical deployed sensors."
    ),
    "keywords": [
        "Met Office",
        "Weather DataHub",
        "Global Spot",
        "Site-Specific Forecast",
        "forecast",
        "weather",
        "deterministic",
        "hourly",
    ],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Weather DataHub", "link": {"href": MET_OFFICE_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Weather DataHub Docs", "link": {"href": MET_OFFICE_DOCS, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Site-Specific Forecast Overview", "link": {"href": SITE_SPECIFIC_OVERVIEW, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Site-Specific Pricing", "link": {"href": SITE_SPECIFIC_PRICING, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Weather DataHub Glossary", "link": {"href": MET_OFFICE_GLOSSARY, "type": "text/html"}},
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


def _system_stub(location: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [location["lon"], location["lat"]]},
        "properties": {
            "uid": _system_uid(location["id"]),
            "featureType": "sosa:System",
            "name": f"Met Office Global Spot Forecast {location['name']}",
            "description": location["description"],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(location: dict) -> dict:
    return {
        "type": "PhysicalSystem",
        "id": _system_uid(location["id"]),
        "uniqueId": _system_uid(location["id"]),
        "definition": "sosa:System",
        "label": f"Met Office Global Spot Forecast {location['name']}",
        "description": (
            f"Curated virtual Met Office Global Spot forecast point for {location['name']}. "
            "This system represents a configured forecast location, not a physical sensor. "
            "The publisher retrieves deterministic hourly forecasts and publishes each valid-time value explicitly as forecast data."
        ),
        "keywords": ["Met Office", "Weather DataHub", "Global Spot", "Site-Specific Forecast", "forecast", location["id"], location["name"]],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": location["name"]},
            {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "Curated Forecast Point ID", "value": location["id"]},
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(location["id"])},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SystemType", "label": "Source Type", "value": "Met Office Global Spot virtual forecast point"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Weather forecast situational awareness"},
            {"definition": "http://sensorml.com/ont/swe/property/Status", "label": "Observation Semantics", "value": "Forecast, not observed telemetry"},
        ],
        "contacts": [
            {"role": "operator", "organisationName": "Met Office", "contactInfo": {"onlineResource": {"linkage": "https://www.metoffice.gov.uk/"}}},
        ],
        "documents": [
            {"role": "http://dbpedia.org/resource/Web_page", "name": "Site-Specific Forecast Overview", "link": {"href": SITE_SPECIFIC_OVERVIEW, "type": "text/html"}},
            {"role": "http://dbpedia.org/resource/Web_page", "name": "Forecast point query", "description": "Configured hourly Global Spot forecast query for this point. The exact endpoint path may be overridden at runtime.", "link": {"href": _forecast_url(location), "type": "application/json"}},
            {"role": "http://dbpedia.org/resource/Web_page", "name": "Weather DataHub Glossary", "link": {"href": MET_OFFICE_GLOSSARY, "type": "text/html"}},
            {
                "role": "http://dbpedia.org/resource/Photograph",
                "name": "Representative Global Spot Forecast Thumbnail",
                "description": (
                    "Original OS4CSAPI SVG thumbnail for a Met Office Global Spot virtual forecast point. "
                    "This represents forecast data, not a physical deployed sensor."
                ),
                "link": {"href": GLOBAL_SPOT_THUMBNAIL_DATA_URI, "type": "image/svg+xml"},
            },
        ],
        "characteristics": [{"label": "Forecast Point Properties", "characteristics": [
            {"type": "Text", "name": "curated_location_id", "label": "Curated Forecast Point ID", "value": location["id"]},
            {"type": "Text", "name": "met_office_api_context", "label": "Met Office API Context", "value": GLOBAL_SPOT_API_CONTEXT},
            {"type": "Text", "name": "forecast_semantics", "label": "Forecast Semantics", "value": "Deterministic hourly forecast values; not observed station readings"},
            {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": location.get("selectionReason", "Curated demo forecast point")},
            {"type": "Text", "name": "free_plan_limit", "label": "Free Plan Limit", "value": "360 calls per day"},
        ]}],
        "capabilities": [{
            "definition": "http://www.w3.org/ns/ssn/systems/SystemCapability",
            "label": "Publisher Capabilities",
            "capabilities": [
                {
                    "type": "Quantity",
                    "name": "publish_interval",
                    "definition": "http://qudt.org/vocab/quantitykind/Period",
                    "label": "Publish Interval",
                    "uom": {"code": "s"},
                    "value": PUBLISH_INTERVAL_SECONDS,
                },
                {
                    "type": "Text",
                    "name": "source_forecast_cadence",
                    "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
                    "label": "Source Forecast Cadence",
                    "value": "Hourly deterministic forecasts from Met Office Global Spot",
                },
            ],
        }],
        "position": {
            "type": "Point",
            "coordinates": [location["lon"], location["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _go_compatible_system_sml(sml: dict, base_url: str) -> dict:
    if "csapi-go" not in base_url:
        return sml
    compat = dict(sml)
    compat.pop("characteristics", None)
    return compat


def _datastream_schema(location: dict, parameter: dict) -> dict:
    result_field = parameter["resultField"]
    return {
        "uid": _datastream_uid(location, parameter),
        "outputName": parameter["outputName"],
        "name": parameter["label"],
        "description": (
            f"{parameter['label']} from the Met Office Weather DataHub Global Spot hourly forecast "
            f"for the curated {location['name']} forecast point. Values are forecasts, not observations."
        ),
        "documentation": [
            {"title": "Site-Specific Forecast Overview", "href": SITE_SPECIFIC_OVERVIEW, "rel": "documentation"},
            {"title": "Forecast Point Query", "href": _forecast_url(location), "rel": "service"},
            {"title": "Weather DataHub Glossary", "href": MET_OFFICE_GLOSSARY, "rel": "describedby"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": f"Met Office {parameter['label']}",
                "description": "Met Office Global Spot hourly forecast value with source metadata.",
                "fields": [
                    {"type": "Text", "name": "locationId", "label": "Curated Forecast Point ID", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "forecastType", "label": "Forecast Type", "definition": "http://sensorml.com/ont/swe/property/ObservationType"},
                    {"type": "Text", "name": "issuedTime", "label": "Forecast Issued Time", "definition": "http://sensorml.com/ont/swe/property/ReferenceTime"},
                    {"type": "Text", "name": "validTime", "label": "Forecast Valid Time", "definition": "http://sensorml.com/ont/swe/property/PhenomenonTime"},
                    {"type": "Quantity", "name": "leadTimeHours", "label": "Forecast Lead Time", "definition": "http://sensorml.com/ont/swe/property/TimeOffset", "uom": {"code": "h"}},
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
            "name": "Met Office Global Spot Forecast Demo",
            "description": "Top-level grouping for curated Met Office Weather DataHub Global Spot forecast resources.",
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
            "name": "Met Office Global Spot Hourly Forecast Points",
            "description": "Grouping deployment for curated Met Office Global Spot hourly forecast points.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_location(location: dict, system_server_id: str, base_url: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [location["lon"], location["lat"]]},
        "properties": {
            "uid": _deploy_uid(location["id"]),
            "featureType": "sosa:Deployment",
            "name": f"Met Office Global Spot {location['name']}",
            "description": f"Deployment node linking curated Met Office Global Spot forecast point {location['name']} to its CSAPI forecast system.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": f"{base_url.rstrip('/')}/systems/{system_server_id}",
                "uid": _system_uid(location["id"]),
                "title": f"Met Office Global Spot Forecast {location['name']}",
            },
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool = False, stats: dict):
    locations = _load_locations()
    for location in locations:
        clean_resource(base_url, auth, "deployments", _deploy_uid(location["id"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for location in locations:
        clean_resource(base_url, auth, "systems", _system_uid(location["id"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _ensure_system_resilient(base_url: str, auth: str, location: dict,
                             *, dry_run: bool, stats: dict, force_sml: bool) -> str | None:
    uid = _system_uid(location["id"])
    try:
        return ensure_system(
            base_url, auth, uid, _system_stub(location),
            _go_compatible_system_sml(_system_sml(location), base_url),
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
                        _go_compatible_system_sml(_system_sml(location), base_url),
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
    locations = _load_locations()
    parameters = _load_parameters()
    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  Met Office DataHub Global Spot Hourly Forecast -- Bootstrap")
    print("=" * 70)
    print(f"  Server:     {base_url}")
    print(f"  Locations:  {len(locations)}")
    print(f"  Parameters: {len(parameters)}")
    print(f"  Clean:      {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}")
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
    for location in locations:
        sys_id = _ensure_system_resilient(
            base_url, auth, location, dry_run=dry_run, stats=stats, force_sml=force_sml)
        if sys_id:
            system_ids[location["id"]] = sys_id
        for parameter in parameters:
            if dry_run and not sys_id:
                print(f"  [DRY] Would create datastream '{parameter['outputName']}' on system {location['id']}")
                continue
            ensure_datastream(base_url, auth, sys_id or "pending", parameter["outputName"],
                              _datastream_schema(location, parameter),
                              dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id, dry_run=dry_run, stats=stats)
    for location in locations:
        sys_id = system_ids.get(location["id"]) or "pending"
        ensure_deployment(base_url, auth, _deploy_uid(location["id"]),
                          _deploy_location(location, sys_id, base_url),
                          parent_id=group_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap Met Office DataHub Global Spot hourly forecast resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only,
              dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
