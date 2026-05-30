#!/usr/bin/env python3
"""Bootstrap curated Finnish Digitraffic road-weather CSAPI resources."""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config, _auth_header, api_put, find_by_uid,
    ensure_procedure, ensure_system, ensure_datastream, ensure_deployment,
    clean_resource, add_bootstrap_args, print_summary,
)


VALID_TIME_START = "2026-01-01T00:00:00Z"
PUBLISH_INTERVAL_SECONDS = 300

PROC_UID = "urn:os4csapi:procedure:digitraffic-road-weather:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:digitraffic-road-weather-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:digitraffic-road-weather-stations:v1"

DIGITRAFFIC_HOME = "https://www.digitraffic.fi/en/road-traffic/"
DIGITRAFFIC_LICENSE = "https://www.digitraffic.fi/en/terms-of-use/"
DIGITRAFFIC_STATIONS = "https://tie.digitraffic.fi/api/weather/v1/stations"
DIGITRAFFIC_LATEST = "https://tie.digitraffic.fi/api/weather/v1/stations/data"
DIGITRAFFIC_ROAD_WEATHER_STATION_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/9/94/Traffic_weather_station_general_view.jpg"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as file:
        return json.load(file)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:digitraffic-road-weather:{_uid_token(station_id)}:v1"


def _deploy_uid(station_id: str) -> str:
    return f"urn:os4csapi:deployment:digitraffic-road-weather-{_uid_token(station_id)}:v1"


def _datastream_uid(station: dict) -> str:
    return f"urn:os4csapi:datastream:digitraffic-road-weather:{_uid_token(station['stationId'])}:roadWeatherObs:v1"


def _station_data_url(station_id: str) -> str:
    return f"https://tie.digitraffic.fi/api/weather/v1/stations/{station_id}/data"


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "Digitraffic Road Weather Observation v1",
        "description": "Publishes curated Finnish road-weather station readings from Fintraffic Digitraffic.",
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "Digitraffic Road Weather Observation v1",
    "description": (
        "Fetches current road-weather readings from Fintraffic Digitraffic road weather "
        "station APIs and publishes one CSAPI observation per curated Finnish station. "
        "The observation result preserves source station ID, sensor IDs, names, units, "
        "measured times, and source URLs."
    ),
    "keywords": ["Fintraffic", "Digitraffic", "Finland", "road weather", "weather station", "open data"],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Road Traffic", "link": {"href": DIGITRAFFIC_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Road Weather Stations", "link": {"href": DIGITRAFFIC_STATIONS, "type": "application/json"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Terms of Use", "link": {"href": DIGITRAFFIC_LICENSE, "type": "text/html"}},
    ],
    "contacts": [
        {"role": "operator", "organisationName": "Fintraffic / Digitraffic", "contactInfo": {"onlineResource": {"linkage": DIGITRAFFIC_HOME}}},
        {"role": "publisher", "organisationName": "OS4CSAPI", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}}},
    ],
}


def _system_stub(station: dict) -> dict:
    station_id = station["stationId"]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _system_uid(station_id),
            "featureType": "sosa:Sensor",
            "name": f"Digitraffic Road Weather {station['name']}",
            "description": f"Curated Finnish road-weather station {station['sourceName']} ({station_id}).",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    station_id = station["stationId"]
    characteristics = [
        {"type": "Text", "name": "station_id", "label": "Digitraffic Station ID", "value": station_id},
        {"type": "Text", "name": "source_name", "label": "Source Station Name", "value": station["sourceName"]},
        {"type": "Text", "name": "route", "label": "Route", "value": station.get("route", "")},
        {"type": "Text", "name": "region", "label": "Region", "value": station.get("region", "")},
        {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": station.get("selectionReason", "Curated Finland road-weather demo station")},
        {"type": "Text", "name": "license", "label": "License", "value": "Digitraffic terms of use; attribution required"},
    ]
    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station_id),
        "uniqueId": _system_uid(station_id),
        "definition": "sosa:System",
        "label": f"Digitraffic Road Weather {station['name']}",
        "description": (
            f"Finnish road-weather station {station['sourceName']} ({station_id}) from "
            "Fintraffic Digitraffic. The station publishes current road and weather sensor values."
        ),
        "keywords": ["Fintraffic", "Digitraffic", "Finland", "road weather", station["name"], station_id],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"FIN Road Wx {station['name']}"},
            {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "Digitraffic Station ID", "value": station_id},
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(station_id)},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "Fintraffic Digitraffic road weather station"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Road weather monitoring and transport situational awareness"},
        ],
        "contacts": [{"role": "operator", "organisationName": "Fintraffic / Digitraffic", "contactInfo": {"onlineResource": {"linkage": DIGITRAFFIC_HOME}}}],
        "documents": [
            {"role": "http://dbpedia.org/resource/Photograph", "name": "Actual traffic weather station hardware", "description": "Photograph of real road-weather station sensor hardware used as the representative hardware image for Digitraffic road-weather station cards. Source: Wikimedia Commons.", "link": {"href": DIGITRAFFIC_ROAD_WEATHER_STATION_IMAGE, "type": "image/jpeg"}},
            {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Road Weather Station Data", "link": {"href": _station_data_url(station_id), "type": "application/json"}},
            {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Terms of Use", "link": {"href": DIGITRAFFIC_LICENSE, "type": "text/html"}},
        ],
        "characteristics": [{"label": "Station Properties", "characteristics": characteristics}],
        "capabilities": [{
            "definition": "http://www.w3.org/ns/ssn/systems/SystemCapability",
            "label": "Publisher Capabilities",
            "capabilities": [
                {"type": "Quantity", "name": "publish_interval", "definition": "http://qudt.org/vocab/quantitykind/Period", "label": "Publish Interval", "uom": {"code": "s"}, "value": PUBLISH_INTERVAL_SECONDS},
                {"type": "Text", "name": "source_query_mode", "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency", "label": "Source Query Mode", "value": "Latest Fintraffic Digitraffic road-weather readings polled from station-specific JSON endpoints"},
            ],
        }],
        "position": {"type": "Point", "coordinates": [station["lon"], station["lat"]], "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326"},
    }


def _datastream_schema(station: dict) -> dict:
    return {
        "uid": _datastream_uid(station),
        "outputName": "roadWeatherObs",
        "name": "Digitraffic Road Weather Observation",
        "description": "Latest Fintraffic Digitraffic road-weather sensor values for one curated Finnish station.",
        "documentation": [
            {"title": "Station Latest Data", "href": _station_data_url(station["stationId"]), "rel": "service"},
            {"title": "Digitraffic Road Weather Stations", "href": DIGITRAFFIC_STATIONS, "rel": "describedby"},
            {"title": "Digitraffic Terms of Use", "href": DIGITRAFFIC_LICENSE, "rel": "license"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "Digitraffic Road Weather Reading",
                "fields": [
                    {"type": "Time", "name": "timestamp", "label": "Observation Time", "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text", "name": "stationId", "label": "Digitraffic Station ID", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "stationName", "label": "Station Name", "definition": "http://sensorml.com/ont/swe/property/Name"},
                    {"type": "Quantity", "name": "airTemperature_c", "label": "Air Temperature", "definition": "http://sensorml.com/ont/swe/property/AirTemperature", "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "roadSurfaceTemperature_c", "label": "Road Surface Temperature", "definition": "http://sensorml.com/ont/swe/property/Temperature", "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "windSpeed_ms", "label": "Wind Speed", "definition": "http://sensorml.com/ont/swe/property/WindSpeed", "uom": {"code": "m/s"}},
                    {"type": "Quantity", "name": "windDirection_deg", "label": "Wind Direction", "definition": "http://sensorml.com/ont/swe/property/WindDirection", "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "precipitation", "label": "Precipitation", "definition": "http://sensorml.com/ont/swe/property/Precipitation"},
                    {"type": "Text", "name": "roadConditionCode", "label": "Road Condition Code", "definition": "http://sensorml.com/ont/swe/property/Status"},
                    {"type": "Text", "name": "warningCode", "label": "Warning Code", "definition": "http://sensorml.com/ont/swe/property/Warning"},
                    {"type": "Text", "name": "sensorValuesJson", "label": "All Source Sensor Values JSON", "definition": "http://sensorml.com/ont/swe/property/RawData"},
                    {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [25.0, 63.5]}, "properties": {"uid": DEPLOY_ROOT_UID, "featureType": "sosa:Deployment", "name": "Digitraffic Road Weather Demo", "description": "Top-level grouping for curated Finnish road-weather station resources.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_group() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [25.0, 63.5]}, "properties": {"uid": DEPLOY_GROUP_UID, "featureType": "sosa:Deployment", "name": "Digitraffic Road Weather Stations", "description": "Grouping deployment for curated Fintraffic Digitraffic road-weather stations.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _deploy_uid(station["stationId"]),
            "featureType": "sosa:Deployment",
            "name": f"Digitraffic Road Weather {station['name']}",
            "description": f"Deployment linking Finnish road-weather station {station['sourceName']} to its CSAPI system.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {"href": f"{base_url.rstrip('/')}/systems/{system_server_id}", "uid": _system_uid(station["stationId"]), "title": f"Digitraffic Road Weather {station['name']}"},
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool, stats: dict):
    stations = _load_stations()
    for station in stations:
        clean_resource(base_url, auth, "deployments", _deploy_uid(station["stationId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for station in stations:
        clean_resource(base_url, auth, "systems", _system_uid(station["stationId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _ensure_system_resilient(base_url: str, auth: str, station: dict, *, dry_run: bool, stats: dict, force_sml: bool) -> str | None:
    uid = _system_uid(station["stationId"])
    try:
        return ensure_system(base_url, auth, uid, _system_stub(station), _system_sml(station), dry_run=dry_run, stats=stats, force_sml=force_sml)
    except RuntimeError as exc:
        if "HTTP 500 POST" not in str(exc) or "/systems" not in str(exc):
            raise
        recovered = find_by_uid(base_url, auth, "systems", uid, no_cache=True)
        if not recovered:
            raise
        print(f"  [WARN] Server returned HTTP 500 after creating system {uid}; recovered id={recovered}")
        if not dry_run:
            try:
                api_put(base_url, f"systems/{recovered}", _system_sml(station), auth, content_type="application/sml+json")
                print(f"  [SML] PUT SensorML for recovered system {uid} (id={recovered})")
            except Exception as sml_exc:
                print(f"  [WARN] SML PUT skipped for recovered system {uid} (id={recovered}): {sml_exc}")
        stats.setdefault("recovered", 0)
        stats["recovered"] += 1
        return recovered


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False, force_sml: bool = False):
    config = get_config()
    base_url = config["base_url"]
    auth = _auth_header(config["user"], config["password"])
    stations = _load_stations()
    stats: dict[str, int] = {}

    print("\n" + "=" * 70)
    print("  Digitraffic Road Weather -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)}")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}\n")

    if clean or clean_only:
        print("  -- Cleaning existing resources --")
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    print("  -- Procedure --")
    ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_STUB, PROCEDURE_SML, dry_run=dry_run, stats=stats, force_sml=force_sml)

    print("  -- Systems + Datastreams --")
    system_ids: dict[str, str] = {}
    for station in stations:
        sys_id = _ensure_system_resilient(base_url, auth, station, dry_run=dry_run, stats=stats, force_sml=force_sml)
        if sys_id:
            system_ids[station["stationId"]] = sys_id
        ensure_datastream(base_url, auth, sys_id or "pending", "roadWeatherObs", _datastream_schema(station), dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(), dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(), parent_id=root_id, dry_run=dry_run, stats=stats)
    for station in stations:
        ensure_deployment(base_url, auth, _deploy_uid(station["stationId"]), _deploy_station(station, system_ids.get(station["stationId"], "pending"), base_url), parent_id=group_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Digitraffic Road Weather resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only, dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()