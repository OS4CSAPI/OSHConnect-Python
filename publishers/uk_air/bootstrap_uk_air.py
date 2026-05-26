#!/usr/bin/env python3
"""
bootstrap_uk_air.py -- Register curated UK-AIR air pollution resources on the
OS4CSAPI server.

Creates station-centric CSAPI resources:
  Procedure:
    urn:os4csapi:procedure:uk-air:v1

  Systems:
    urn:os4csapi:system:uk-air:{siteId}:v1

  Datastreams:
    one datastream per selected UK-AIR pollutant timeseries under each site

Station and timeseries selection is read from stations.json in this directory.
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

PROC_UID = "urn:os4csapi:procedure:uk-air:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:uk-air-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:uk-air-stations:v1"

UK_AIR_HOME = "https://uk-air.defra.gov.uk/data/about_sos"
UK_AIR_API_DOCS = "https://uk-air.defra.gov.uk/data/sos/static/doc/api-doc/"
UK_AIR_API = "https://uk-air.defra.gov.uk/sos-ukair/api/v1"
UK_AIR_SOS_CAPABILITIES = "https://uk-air.defra.gov.uk/data/sos/service?service=SOS&request=GetCapabilities"
OGL3 = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as f:
        return json.load(f)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-")


def _system_uid(site_id: str) -> str:
    return f"urn:os4csapi:system:uk-air:{_uid_token(site_id)}:v1"


def _deploy_uid(site_id: str) -> str:
    return f"urn:os4csapi:deployment:uk-air-{_uid_token(site_id)}:v1"


def _datastream_uid(station: dict, series: dict) -> str:
    return f"urn:os4csapi:datastream:uk-air:{_uid_token(station['siteId'])}:{series['outputName']}:v1"


def _timeseries_url(series: dict) -> str:
    return f"{UK_AIR_API}/timeseries/{quote(str(series['timeseriesId']), safe='')}"


def _latest_data_url(series: dict) -> str:
    return f"{_timeseries_url(series)}/getData?timespan=PT72H/now"


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "UK-AIR Air Pollution Observation v1",
        "description": (
            "Publishes a curated set of recent Defra UK-AIR air pollution "
            "readings for nitrogen dioxide, ozone, PM10, and PM2.5."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "UK-AIR Air Pollution Observation v1",
    "description": (
        "Fetches selected recent readings from Defra UK-AIR's SOS / 52 North "
        "Timeseries REST API and publishes one CSAPI observation per selected "
        "pollutant timeseries. The initial curated set covers NO2, O3, PM10, "
        "and PM2.5 while preserving source timeseries identity, pollutant URIs, "
        "units, and source URLs."
    ),
    "keywords": [
        "UK-AIR",
        "Defra",
        "air quality",
        "air pollution",
        "nitrogen dioxide",
        "ozone",
        "PM10",
        "PM2.5",
        "SOS",
        "OGL",
    ],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "UK-AIR SOS Overview", "link": {"href": UK_AIR_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "UK-AIR REST API Docs", "link": {"href": UK_AIR_API_DOCS, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "UK-AIR SOS GetCapabilities", "link": {"href": UK_AIR_SOS_CAPABILITIES, "type": "text/xml"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Open Government Licence v3.0", "link": {"href": OGL3, "type": "text/html"}},
    ],
    "contacts": [
        {
            "role": "operator",
            "organisationName": "Defra UK-AIR",
            "contactInfo": {"onlineResource": {"linkage": "https://uk-air.defra.gov.uk/"}},
        },
        {
            "role": "publisher",
            "organisationName": "OS4CSAPI",
            "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}},
        },
    ],
}


def _system_stub(station: dict) -> dict:
    site_id = station["siteId"]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _system_uid(site_id),
            "featureType": "sosa:Sensor",
            "name": f"UK-AIR {station['name']}",
            "description": (
                f"Curated UK-AIR air quality monitoring site {station['name']} "
                "with selected live/recent pollutant datastreams."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    site_id = station["siteId"]
    pollutant_labels = ", ".join(s["pollutantCode"] for s in station.get("timeseries", []))
    docs = [
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "UK-AIR Representative Timeseries",
            "description": f"Primary UK-AIR REST timeseries metadata endpoint for {station['name']}.",
            "link": {"href": station["stationUrl"], "type": "application/json"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "UK-AIR REST API Docs",
            "link": {"href": UK_AIR_API_DOCS, "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Open Government Licence v3.0",
            "link": {"href": OGL3, "type": "text/html"},
        },
    ]
    for series in station.get("timeseries", []):
        docs.append({
            "role": "http://dbpedia.org/resource/Web_page",
            "name": series["label"],
            "description": "Recent data query for this curated UK-AIR pollutant timeseries.",
            "link": {"href": _latest_data_url(series), "type": "application/json"},
        })

    characteristics = [
        {"type": "Text", "name": "site_id", "label": "Curated Site ID", "value": site_id},
        {"type": "Text", "name": "site_type", "label": "Site Type", "value": station.get("siteType") or "Not available"},
        {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": station.get("selectionReason", "Curated demo station")},
        {"type": "Text", "name": "curated_pollutants", "label": "Curated Pollutants", "value": pollutant_labels},
        {"type": "Text", "name": "license", "label": "License", "value": "Open Government Licence v3.0"},
    ]

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(site_id),
        "uniqueId": _system_uid(site_id),
        "definition": "sosa:System",
        "label": f"UK-AIR {station['name']}",
        "description": (
            f"Defra UK-AIR air pollution monitoring site {station['name']}. "
            "This CSAPI system represents one curated site from the UK-AIR SOS / "
            "52 North Timeseries API and exposes selected pollutant datastreams."
        ),
        "keywords": ["UK-AIR", "Defra", "air quality", "air pollution", "monitoring station", station["name"], site_id],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"UK-AIR {station['name']}"},
            {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "Curated Site ID", "value": site_id},
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(site_id)},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "UK-AIR air quality monitoring station"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Air quality monitoring and environmental situational awareness"},
        ],
        "contacts": [
            {"role": "operator", "organisationName": "Defra UK-AIR", "contactInfo": {"onlineResource": {"linkage": "https://uk-air.defra.gov.uk/"}}},
        ],
        "documents": docs,
        "characteristics": [{"label": "Station Properties", "characteristics": characteristics}],
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


def _datastream_schema(station: dict, series: dict) -> dict:
    result_field = series.get("resultField", "value")
    return {
        "uid": _datastream_uid(station, series),
        "outputName": series["outputName"],
        "name": series["pollutantName"],
        "description": (
            f"{series['label']}. Values are fetched from the UK-AIR SOS / 52 North "
            "Timeseries REST API and published as one CSAPI observation per selected pollutant stream."
        ),
        "documentation": [
            {"title": "Recent Data", "href": _latest_data_url(series), "rel": "service"},
            {"title": "Timeseries Metadata", "href": _timeseries_url(series), "rel": "describedby"},
            {"title": "UK-AIR REST API Docs", "href": UK_AIR_API_DOCS, "rel": "documentation"},
            {"title": "Open Government Licence v3.0", "href": OGL3, "rel": "license"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": f"UK-AIR {series['pollutantCode']} Reading",
                "description": "Latest UK-AIR pollutant concentration reading with source identity metadata.",
                "fields": [
                    {"type": "Time", "name": "timestamp", "label": "Observation Time", "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text", "name": "stationId", "label": "Curated Site ID", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "sourceStationId", "label": "UK-AIR Station ID", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "timeseriesId", "label": "UK-AIR Timeseries ID", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "pollutant", "label": "Pollutant", "definition": "http://sensorml.com/ont/swe/property/ObservableProperty"},
                    {"type": "Text", "name": "pollutantUri", "label": "Pollutant URI", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                    {"type": "Quantity", "name": result_field, "label": series["pollutantName"], "definition": "http://sensorml.com/ont/swe/property/Value", "uom": {"code": series.get("uom", series["displayUnit"])}},
                    {"type": "Text", "name": "unit", "label": "Unit", "definition": "http://sensorml.com/ont/swe/property/Unit"},
                    {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-1.5, 53.0]},
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "UK-AIR Air Quality Demo",
            "description": "Top-level grouping for curated UK-AIR air quality monitoring station resources.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-1.5, 53.0]},
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "UK-AIR Monitoring Stations",
            "description": "Grouping deployment for curated UK-AIR air quality monitoring stations and pollutant datastreams.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    site_id = station["siteId"]
    pollutants = ", ".join(s["pollutantCode"] for s in station.get("timeseries", []))
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _deploy_uid(site_id),
            "featureType": "sosa:Deployment",
            "name": f"UK-AIR {station['name']}",
            "description": (
                f"Deployment node linking UK-AIR air quality monitoring station {station['name']} "
                f"to its CSAPI environmental sensor system for {pollutants}."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": f"{base_url.rstrip('/')}/systems/{system_server_id}",
                "uid": _system_uid(site_id),
                "title": f"UK-AIR {station['name']}",
            },
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool = False, stats: dict):
    stations = _load_stations()
    for station in stations:
        clean_resource(base_url, auth, "deployments", _deploy_uid(station["siteId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for station in stations:
        clean_resource(base_url, auth, "systems", _system_uid(station["siteId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _ensure_system_resilient(base_url: str, auth: str, station: dict,
                             *, dry_run: bool, stats: dict, force_sml: bool) -> str | None:
    uid = _system_uid(station["siteId"])
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
    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  UK-AIR -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)}")
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
        site_id = station["siteId"]
        sys_id = _ensure_system_resilient(
            base_url, auth, station, dry_run=dry_run, stats=stats, force_sml=force_sml)
        if sys_id:
            system_ids[site_id] = sys_id
        for series in station.get("timeseries", []):
            if dry_run and not sys_id:
                print(f"  [DRY] Would create datastream '{series['outputName']}' on system {site_id}")
                continue
            ensure_datastream(base_url, auth, sys_id or "pending", series["outputName"],
                              _datastream_schema(station, series),
                              dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id, dry_run=dry_run, stats=stats)
    for station in stations:
        site_id = station["siteId"]
        sys_id = system_ids.get(site_id) or "pending"
        ensure_deployment(base_url, auth, _deploy_uid(site_id),
                          _deploy_station(station, sys_id, base_url),
                          parent_id=group_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap UK-AIR resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only,
              dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
