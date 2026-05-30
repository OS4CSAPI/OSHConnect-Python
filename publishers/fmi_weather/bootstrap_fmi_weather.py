#!/usr/bin/env python3
"""Bootstrap curated Finnish FMI weather CSAPI resources."""

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
PUBLISH_INTERVAL_SECONDS = 600
PROC_UID = "urn:os4csapi:procedure:fmi-weather:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:fmi-weather-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:fmi-weather-stations:v1"
DS_OUTPUT_NAME = "fmiWeatherObs"
FMI_HOME = "https://en.ilmatieteenlaitos.fi/open-data"
FMI_WFS = "https://opendata.fmi.fi/wfs"
FMI_WEATHER_STATION_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/2/21/S%C3%A4%C3%A4asema_Kylm%C3%A4pihlaja.jpg"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as file:
        return json.load(file)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:fmi-weather:{_uid_token(station_id)}:v1"


def _deploy_uid(station_id: str) -> str:
    return f"urn:os4csapi:deployment:fmi-weather-{_uid_token(station_id)}:v1"


def _datastream_uid(station: dict) -> str:
    return f"urn:os4csapi:datastream:fmi-weather:{_uid_token(station['stationId'])}:{DS_OUTPUT_NAME}:v1"


def _image_docs(station: dict) -> list[dict]:
    return [{"role": "http://dbpedia.org/resource/Photograph", "name": "Actual Finnish weather station instrumentation", "description": f"Photograph of real Finnish weather-station instrumentation used as the representative sensor image for FMI weather station {station['name']}. Source: Wikimedia Commons.", "link": {"href": FMI_WEATHER_STATION_IMAGE, "type": "image/jpeg"}}]


PROCEDURE_STUB = {"type": "Feature", "geometry": None, "properties": {"uid": PROC_UID, "featureType": "sosa:ObservingProcedure", "name": "FMI Weather Observation v1", "description": "Publishes curated Finnish Meteorological Institute weather observations from FMI Open Data WFS.", "validTime": [VALID_TIME_START, ".."]}}
PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "FMI Weather Observation v1",
    "description": "Fetches recent FMI Open Data simple weather observations and publishes one combined observation per curated Finnish station.",
    "keywords": ["FMI", "Finnish Meteorological Institute", "Finland", "weather", "open data", "WFS"],
    "documents": [{"role": "http://dbpedia.org/resource/Web_page", "name": "FMI Open Data", "link": {"href": FMI_HOME, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "FMI WFS", "link": {"href": FMI_WFS, "type": "text/xml"}}],
    "contacts": [{"role": "operator", "organisationName": "Finnish Meteorological Institute", "contactInfo": {"onlineResource": {"linkage": FMI_HOME}}}, {"role": "publisher", "organisationName": "OS4CSAPI", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}}}],
}


def _system_stub(station: dict) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]}, "properties": {"uid": _system_uid(station["stationId"]), "featureType": "sosa:Sensor", "name": f"FMI Weather {station['name']}", "description": f"Curated FMI weather observation location for {station['name']}.", "validTime": [VALID_TIME_START, ".."]}}


def _system_sml(station: dict) -> dict:
    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station["stationId"]),
        "uniqueId": _system_uid(station["stationId"]),
        "definition": "sosa:System",
        "label": f"FMI Weather {station['name']}",
        "description": f"Finnish Meteorological Institute Open Data weather observation location for {station['name']} ({station.get('region', 'Finland')}).",
        "keywords": ["FMI", "Finland", "weather", station["name"], station["stationId"]],
        "identifiers": [{"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"FMI Wx {station['name']}"}, {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "Curated Station ID", "value": station["stationId"]}, {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(station["stationId"])}],
        "classifiers": [{"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "FMI weather observation station"}, {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Weather monitoring and environmental situational awareness"}],
        "contacts": [{"role": "operator", "organisationName": "Finnish Meteorological Institute", "contactInfo": {"onlineResource": {"linkage": FMI_HOME}}}],
        "documents": _image_docs(station) + [{"role": "http://dbpedia.org/resource/Web_page", "name": "FMI Open Data", "link": {"href": FMI_HOME, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "FMI WFS", "link": {"href": FMI_WFS, "type": "text/xml"}}],
        "characteristics": [{"label": "Station Properties", "characteristics": [{"type": "Text", "name": "place", "label": "FMI Place Query", "value": station.get("place", station["name"])}, {"type": "Text", "name": "region", "label": "Region", "value": station.get("region", "")}, {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": station.get("selectionReason", "Curated FMI weather station")}, {"type": "Text", "name": "license", "label": "License", "value": "FMI Open Data terms and attribution"}]}],
        "capabilities": [{"definition": "http://www.w3.org/ns/ssn/systems/SystemCapability", "label": "Publisher Capabilities", "capabilities": [{"type": "Quantity", "name": "publish_interval", "definition": "http://qudt.org/vocab/quantitykind/Period", "label": "Publish Interval", "uom": {"code": "s"}, "value": PUBLISH_INTERVAL_SECONDS}]}],
        "position": {"type": "Point", "coordinates": [station["lon"], station["lat"]], "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326"},
    }


def _datastream_schema(station: dict) -> dict:
    return {"uid": _datastream_uid(station), "outputName": DS_OUTPUT_NAME, "name": "FMI Weather Observation", "description": "Recent FMI Open Data weather parameters for one curated Finnish station.", "documentation": [{"title": "FMI Open Data", "href": FMI_HOME, "rel": "describedby"}], "schema": {"obsFormat": "application/om+json", "resultSchema": {"type": "DataRecord", "label": "FMI Weather Reading", "fields": [{"type": "Text", "name": "stationId", "label": "Station ID", "definition": "http://sensorml.com/ont/swe/property/StationID"}, {"type": "Text", "name": "stationName", "label": "Station Name", "definition": "http://sensorml.com/ont/swe/property/Name"}, {"type": "Quantity", "name": "airTemperature_c", "label": "Air Temperature", "definition": "http://sensorml.com/ont/swe/property/AirTemperature", "uom": {"code": "Cel"}}, {"type": "Quantity", "name": "relativeHumidity_pct", "label": "Relative Humidity", "definition": "http://sensorml.com/ont/swe/property/RelativeHumidity", "uom": {"code": "%"}}, {"type": "Quantity", "name": "windSpeed_ms", "label": "Wind Speed", "definition": "http://sensorml.com/ont/swe/property/WindSpeed", "uom": {"code": "m/s"}}, {"type": "Quantity", "name": "windGust_ms", "label": "Wind Gust", "definition": "http://sensorml.com/ont/swe/property/WindSpeed", "uom": {"code": "m/s"}}, {"type": "Quantity", "name": "windDirection_deg", "label": "Wind Direction", "definition": "http://sensorml.com/ont/swe/property/WindDirection", "uom": {"code": "deg"}}, {"type": "Quantity", "name": "precipitation1h_mm", "label": "Precipitation 1h", "definition": "http://sensorml.com/ont/swe/property/Precipitation", "uom": {"code": "mm"}}, {"type": "Quantity", "name": "pressureSeaLevel_hpa", "label": "Sea-Level Pressure", "definition": "http://sensorml.com/ont/swe/property/Pressure", "uom": {"code": "hPa"}}, {"type": "Text", "name": "sourceParametersJson", "label": "Source Parameters JSON", "definition": "http://sensorml.com/ont/swe/property/RawData"}, {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"}]}}}


def _deploy_root() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [25.0, 63.5]}, "properties": {"uid": DEPLOY_ROOT_UID, "featureType": "sosa:Deployment", "name": "FMI Weather Demo", "description": "Top-level grouping for curated FMI weather resources.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_group() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [25.0, 63.5]}, "properties": {"uid": DEPLOY_GROUP_UID, "featureType": "sosa:Deployment", "name": "FMI Weather Stations", "description": "Grouping deployment for curated FMI weather stations.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]}, "properties": {"uid": _deploy_uid(station["stationId"]), "featureType": "sosa:Deployment", "name": f"FMI Weather {station['name']}", "description": f"Deployment linking FMI weather location {station['name']} to its CSAPI system.", "validTime": [VALID_TIME_START, ".."], "platform@link": {"href": f"{base_url.rstrip('/')}/systems/{system_server_id}", "uid": _system_uid(station["stationId"]), "title": f"FMI Weather {station['name']}"}}}


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
            except Exception as sml_exc:
                print(f"  [WARN] SML PUT skipped for recovered system {uid}: {sml_exc}")
        stats["recovered"] = stats.get("recovered", 0) + 1
        return recovered


def clean_all(base_url: str, auth: str, *, dry_run: bool, stats: dict):
    for station in _load_stations():
        clean_resource(base_url, auth, "deployments", _deploy_uid(station["stationId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for station in _load_stations():
        clean_resource(base_url, auth, "systems", _system_uid(station["stationId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False, force_sml: bool = False):
    config = get_config(); base_url = config["base_url"]; auth = _auth_header(config["user"], config["password"]); stations = _load_stations(); stats: dict[str, int] = {}
    print("\n" + "=" * 70); print("  FMI Weather -- Bootstrap"); print("=" * 70); print(f"  Server:    {base_url}"); print(f"  Stations:  {len(stations)}"); print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}\n")
    if clean or clean_only:
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run); return
    print("  -- Procedure --"); ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_STUB, PROCEDURE_SML, dry_run=dry_run, stats=stats, force_sml=force_sml)
    print("  -- Systems and Datastreams --"); system_ids = {}
    for station in stations:
        sys_id = _ensure_system_resilient(base_url, auth, station, dry_run=dry_run, stats=stats, force_sml=force_sml); system_ids[station["stationId"]] = sys_id or "pending"; ensure_datastream(base_url, auth, sys_id or "pending", DS_OUTPUT_NAME, _datastream_schema(station), dry_run=dry_run, stats=stats)
    print("  -- Deployments --"); root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(), dry_run=dry_run, stats=stats); group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(), parent_id=root_id, dry_run=dry_run, stats=stats)
    for station in stations:
        ensure_deployment(base_url, auth, _deploy_uid(station["stationId"]), _deploy_station(station, system_ids.get(station["stationId"], "pending"), base_url), parent_id=group_id, dry_run=dry_run, stats=stats)
    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap FMI weather resources on the CSAPI server."); add_bootstrap_args(parser); args = parser.parse_args(); bootstrap(clean=args.clean, clean_only=args.clean_only, dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()