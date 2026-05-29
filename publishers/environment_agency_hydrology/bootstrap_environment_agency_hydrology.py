#!/usr/bin/env python3
"""
bootstrap_environment_agency_hydrology.py -- Register Environment Agency
Hydrology resources on the OS4CSAPI server.

Creates curated station-centric CSAPI resources:
  Procedure:
    urn:os4csapi:procedure:environment-agency-hydrology:v1

  Systems:
    urn:os4csapi:system:environment-agency-hydrology:{stationNotation}:v1

  Datastreams:
    one datastream per selected Environment Agency measure under each station

Station and measure selection is read from stations.json in this directory.
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

PROC_UID = "urn:os4csapi:procedure:environment-agency-hydrology:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:environment-agency-hydrology-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:environment-agency-hydrology-stations:v1"

EA_HYDROLOGY_HOME = "https://environment.data.gov.uk/hydrology/"
EA_API_REFERENCE = "https://environment.data.gov.uk/hydrology/doc/reference"
EA_DATASET = (
    "https://www.data.gov.uk/dataset/98a4d46e-23e7-4430-883c-9e5f14645e8f/"
    "hydrological-open-data"
)
EA_STATIONS = "https://environment.data.gov.uk/hydrology/id/stations.json"
EA_MEASURES = "https://environment.data.gov.uk/hydrology/id/measures.json"
EA_READINGS = "https://environment.data.gov.uk/hydrology/data/readings.json"
OGL3 = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
EA_GAUGE_PHOTO = (
    "https://upload.wikimedia.org/wikipedia/commons/f/f0/"
    "Environment_Agency_Morton_River_Gauge_Station_-_geograph.org.uk_-_283345.jpg"
)
EA_GAUGE_PHOTO_PAGE = (
    "https://commons.wikimedia.org/wiki/"
    "File:Environment_Agency_Morton_River_Gauge_Station_-_geograph.org.uk_-_283345.jpg"
)
CC_BY_SA_20 = "https://creativecommons.org/licenses/by-sa/2.0/"
PUBLISH_INTERVAL_SECONDS = 900


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as f:
        return json.load(f)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-")


def _system_uid(station_notation: str) -> str:
    return f"urn:os4csapi:system:environment-agency-hydrology:{_uid_token(station_notation)}:v1"


def _legacy_system_uid(station_notation: str) -> str:
    return f"urn:os4csapi:system:environment-agency-hydrology:{station_notation}:v1"


def _deploy_uid(station_notation: str) -> str:
    return f"urn:os4csapi:deployment:environment-agency-hydrology-{_uid_token(station_notation)}:v1"


def _legacy_deploy_uid(station_notation: str) -> str:
    return f"urn:os4csapi:deployment:environment-agency-hydrology-{station_notation}:v1"


def _datastream_uid(station: dict, measure: dict) -> str:
    return (
        "urn:os4csapi:datastream:environment-agency-hydrology:"
        f"{_uid_token(station['stationNotation'])}:{measure['outputName']}:v1"
    )


def _latest_reading_url(measure: dict) -> str:
    encoded_measure = quote(measure["measureUri"], safe="")
    return f"{EA_READINGS}?measure={encoded_measure}&latest=true&_limit=1"


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "Environment Agency Hydrology Observation v1",
        "description": (
            "Publishes a curated set of live and recent Environment Agency "
            "Hydrology readings for river level, river flow, rainfall, and "
            "groundwater level."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "Environment Agency Hydrology Observation v1",
    "description": (
        "Fetches selected latest readings from the Environment Agency Hydrology "
        "API and publishes one CSAPI observation per selected station measure. "
        "The initial curated set covers river level, river flow, rainfall, and "
        "groundwater level while preserving Environment Agency measure identity, "
        "quality fields, units, and source URLs."
    ),
    "keywords": [
        "Environment Agency",
        "hydrology",
        "river level",
        "river flow",
        "rainfall",
        "groundwater",
        "open data",
        "OGL",
    ],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Hydrology Data Explorer", "link": {"href": EA_HYDROLOGY_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Hydrology API Reference", "link": {"href": EA_API_REFERENCE, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Hydrological Open Data Dataset", "link": {"href": EA_DATASET, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Open Government Licence v3.0", "link": {"href": OGL3, "type": "text/html"}},
    ],
    "contacts": [
        {
            "role": "operator",
            "organisationName": "Environment Agency",
            "contactInfo": {"onlineResource": {"linkage": "https://environment.data.gov.uk/"}},
        },
        {
            "role": "publisher",
            "organisationName": "OS4CSAPI",
            "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}},
        },
    ],
}


def _system_stub(station: dict) -> dict:
    notation = station["stationNotation"]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _system_uid(notation),
            "featureType": "sosa:Sensor",
            "name": f"EA Hydrology {station['name']}",
            "description": (
                f"Curated Environment Agency hydrology station {station['name']} "
                f"({notation}) with selected live/recent measure datastreams."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    notation = station["stationNotation"]
    measure_labels = ", ".join(m["label"] for m in station.get("measures", []))
    docs = [
        {
            "role": "http://dbpedia.org/resource/Photograph",
            "name": "Representative Hydrometric Gauge Photo",
            "description": (
                "Representative photograph of an Environment Agency river gauge station. "
                "Used as a visual proxy for curated Environment Agency hydrology stations; "
                "not a station-specific photograph. Photo: Brian Green / Geograph, CC BY-SA 2.0."
            ),
            "link": {"href": EA_GAUGE_PHOTO, "type": "image/jpeg"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Environment Agency Station Resource",
            "description": f"Linked-data station resource for {station['name']}.",
            "link": {"href": station["stationUrl"], "type": "application/json"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Hydrology API Reference",
            "link": {"href": EA_API_REFERENCE, "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Representative Gauge Photo Source",
            "description": "Wikimedia Commons source page for the representative gauge photo.",
            "link": {"href": EA_GAUGE_PHOTO_PAGE, "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Representative Gauge Photo License",
            "description": "Creative Commons Attribution-ShareAlike 2.0 license for the representative gauge photo.",
            "link": {"href": CC_BY_SA_20, "type": "text/html"},
        },
    ]
    for measure in station.get("measures", []):
        docs.append({
            "role": "http://dbpedia.org/resource/Web_page",
            "name": measure["label"],
            "description": "Latest-reading query for this curated Environment Agency measure.",
            "link": {"href": _latest_reading_url(measure), "type": "application/json"},
        })

    characteristics = [
        {"type": "Text", "name": "station_notation", "label": "Station Notation", "value": notation},
        {"type": "Text", "name": "river_name", "label": "River Name", "value": station.get("riverName") or "Not available"},
        {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": station.get("selectionReason", "Curated demo station")},
        {"type": "Text", "name": "curated_measures", "label": "Curated Measures", "value": measure_labels},
        {"type": "Text", "name": "license", "label": "License", "value": "Open Government Licence v3.0"},
    ]

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(notation),
        "uniqueId": _system_uid(notation),
        "definition": "sosa:System",
        "label": f"EA Hydrology {station['name']}",
        "description": (
            f"Environment Agency hydrology station {station['name']} ({notation}). "
            "This CSAPI system represents one curated station from the Hydrology "
            "Open Data API and exposes selected measure datastreams."
        ),
        "keywords": ["Environment Agency", "hydrology", "water", station["name"], notation],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"EA {station['name']}"},
            {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "Station Notation", "value": notation},
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(notation)},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "Environment Agency hydrology monitoring station"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Hydrology monitoring and environmental situational awareness"},
        ],
        "contacts": [
            {"role": "operator", "organisationName": "Environment Agency", "contactInfo": {"onlineResource": {"linkage": "https://environment.data.gov.uk/"}}},
        ],
        "documents": docs,
        "characteristics": [{"label": "Station Properties", "characteristics": characteristics}],
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
                    "name": "source_query_mode",
                    "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
                    "label": "Source Query Mode",
                    "value": "Latest Environment Agency Hydrology readings polled with latest=true",
                },
            ],
        }],
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


def _datastream_schema(station: dict, measure: dict) -> dict:
    result_field = measure.get("resultField", "value")
    return {
        "uid": _datastream_uid(station, measure),
        "outputName": measure["outputName"],
        "name": measure["parameterName"],
        "description": (
            f"{measure['label']}. Values are fetched from the Environment Agency "
            "Hydrology API using latest=true and published as one CSAPI observation "
            "per selected measure."
        ),
        "documentation": [
            {"title": "Latest Reading", "href": _latest_reading_url(measure), "rel": "service"},
            {"title": "Measure Resource", "href": measure["measureUri"], "rel": "describedby"},
            {"title": "Hydrology API Reference", "href": EA_API_REFERENCE, "rel": "documentation"},
            {"title": "Open Government Licence v3.0", "href": OGL3, "rel": "license"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": f"Environment Agency {measure['parameterName']} Reading",
                "description": "Latest Environment Agency Hydrology reading with source quality metadata.",
                "fields": [
                    {"type": "Time", "name": "timestamp", "label": "Observation Time", "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text", "name": "stationId", "label": "Station Notation", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "measureId", "label": "Measure Notation", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "parameter", "label": "Parameter", "definition": "http://sensorml.com/ont/swe/property/ObservableProperty"},
                    {"type": "Quantity", "name": result_field, "label": measure["parameterName"], "definition": "http://sensorml.com/ont/swe/property/Value", "uom": {"code": measure.get("uom", measure["unit"])}},
                    {"type": "Text", "name": "unit", "label": "Unit", "definition": "http://sensorml.com/ont/swe/property/Unit"},
                    {"type": "Text", "name": "valueType", "label": "Value Type", "definition": "http://sensorml.com/ont/swe/property/Statistic"},
                    {"type": "Text", "name": "quality", "label": "Quality", "definition": "http://sensorml.com/ont/swe/property/QualityFlag"},
                    {"type": "Text", "name": "completeness", "label": "Completeness", "definition": "http://sensorml.com/ont/swe/property/Status"},
                    {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-2.5, 52.5]},
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "Environment Agency Hydrology Demo",
            "description": (
                "Top-level grouping for curated Environment Agency hydrology monitoring station "
                "resources covering river level, river flow, rainfall, and groundwater sensors."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-2.5, 52.5]},
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "Environment Agency Hydrology Stations",
            "description": (
                "Grouping deployment for curated Environment Agency hydrology monitoring stations "
                "and their river, rainfall, and groundwater sensor datastreams."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    notation = station["stationNotation"]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _deploy_uid(notation),
            "featureType": "sosa:Deployment",
            "name": f"EA Hydrology {station['name']}",
            "description": (
                f"Deployment node linking Environment Agency hydrology monitoring station "
                f"{station['name']} to its CSAPI water sensor system."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": f"{base_url.rstrip('/')}/systems/{system_server_id}",
                "uid": _system_uid(notation),
                "title": f"EA Hydrology {station['name']}",
            },
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool = False, stats: dict):
    stations = _load_stations()
    for station in stations:
        clean_resource(base_url, auth, "deployments", _deploy_uid(station["stationNotation"]), dry_run=dry_run, stats=stats, cascade=True)
        if _uid_token(station["stationNotation"]) != station["stationNotation"]:
            clean_resource(base_url, auth, "deployments", _legacy_deploy_uid(station["stationNotation"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for station in stations:
        clean_resource(base_url, auth, "systems", _system_uid(station["stationNotation"]), dry_run=dry_run, stats=stats, cascade=True)
        if _uid_token(station["stationNotation"]) != station["stationNotation"]:
            clean_resource(base_url, auth, "systems", _legacy_system_uid(station["stationNotation"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _cleanup_legacy_uid(base_url: str, auth: str, station: dict, *, dry_run: bool, stats: dict):
    notation = station["stationNotation"]
    if _uid_token(notation) == notation:
        return
    clean_resource(base_url, auth, "deployments", _legacy_deploy_uid(notation),
                   dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "systems", _legacy_system_uid(notation),
                   dry_run=dry_run, stats=stats, cascade=True)


def _ensure_system_resilient(base_url: str, auth: str, station: dict,
                             *, dry_run: bool, stats: dict, force_sml: bool) -> str | None:
    uid = _system_uid(station["stationNotation"])
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
    print("  Environment Agency Hydrology -- Bootstrap")
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
        notation = station["stationNotation"]
        _cleanup_legacy_uid(base_url, auth, station, dry_run=dry_run, stats=stats)
        sys_id = _ensure_system_resilient(
            base_url, auth, station, dry_run=dry_run, stats=stats, force_sml=force_sml)
        if sys_id:
            system_ids[notation] = sys_id
        for measure in station.get("measures", []):
            if dry_run and not sys_id:
                print(f"  [DRY] Would create datastream '{measure['outputName']}' on system {notation}")
                continue
            ensure_datastream(base_url, auth, sys_id or "pending", measure["outputName"],
                              _datastream_schema(station, measure),
                              dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id, dry_run=dry_run, stats=stats)
    for station in stations:
        notation = station["stationNotation"]
        sys_id = system_ids.get(notation) or "pending"
        ensure_deployment(base_url, auth, _deploy_uid(notation),
                          _deploy_station(station, sys_id, base_url),
                          parent_id=group_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap Environment Agency Hydrology resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only,
              dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
