#!/usr/bin/env python3
"""Bootstrap curated Finnish SYKE hydrology CSAPI resources."""

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
PROC_UID = "urn:os4csapi:procedure:syke-hydrology:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:syke-hydrology-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:syke-hydrology-stations:v1"
PUBLISH_INTERVAL_SECONDS = 900

SYKE_ODATA_BASE = "https://rajapinnat.ymparisto.fi/api/Hydrologiarajapinta/1.0/odata"
SYKE_OPEN_DATA = "https://www.syke.fi/fi-FI/Avoin_tieto"
VESI_PORTAL = "https://www.vesi.fi/"
SYKE_HOME = "https://www.syke.fi/"
REPRESENTATIVE_GAUGE_PHOTO = "https://upload.wikimedia.org/wikipedia/commons/1/12/Crews_Lake_Water_Level_Gauge.jpg"
REPRESENTATIVE_GAUGE_PHOTO_PAGE = "https://commons.wikimedia.org/wiki/File:Crews_Lake_Water_Level_Gauge.jpg"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as file:
        return json.load(file)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-")


def _system_uid(station_notation: str) -> str:
    return f"urn:os4csapi:system:syke-hydrology:{_uid_token(station_notation)}:v1"


def _deploy_uid(station_notation: str) -> str:
    return f"urn:os4csapi:deployment:syke-hydrology-{_uid_token(station_notation)}:v1"


def _datastream_uid(station: dict, measure: dict) -> str:
    return f"urn:os4csapi:datastream:syke-hydrology:{_uid_token(station['stationNotation'])}:{measure['outputName']}:v1"


def _latest_reading_url(measure: dict) -> str:
    params = {
        "$filter": f"Paikka_Id eq {int(measure['placeId'])}",
        "$orderby": "Aika desc",
        "$top": 1,
    }
    return f"{SYKE_ODATA_BASE}/{measure['entity']}?{urlencode(params)}"


def _procedure_stub() -> dict:
    return {"type": "Feature", "geometry": None, "properties": {"uid": PROC_UID, "featureType": "sosa:ObservingProcedure", "name": "SYKE Hydrology Observation v1", "description": "Publishes curated Finnish water level and discharge readings from the public SYKE Hydrologiarajapinta OData API.", "validTime": [VALID_TIME_START, ".."]}}


def _procedure_sml() -> dict:
    return {"type": "SimpleProcess", "id": PROC_UID, "uniqueId": PROC_UID, "definition": "sosa:ObservingProcedure", "label": "SYKE Hydrology Observation v1", "description": "Fetches selected latest water-level and discharge readings from the Finnish Environment Institute (SYKE) Hydrologiarajapinta OData API and publishes one CSAPI observation per selected station measure.", "keywords": ["SYKE", "vesi.fi", "Finland", "hydrology", "water level", "discharge", "OData", "open data"], "documents": [{"role": "http://dbpedia.org/resource/Web_page", "name": "SYKE Open Data", "link": {"href": SYKE_OPEN_DATA, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "vesi.fi", "link": {"href": VESI_PORTAL, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "SYKE Hydrologiarajapinta OData", "link": {"href": SYKE_ODATA_BASE, "type": "application/json"}}], "contacts": [{"role": "operator", "organisationName": "Finnish Environment Institute (SYKE)", "contactInfo": {"onlineResource": {"linkage": SYKE_HOME}}}, {"role": "publisher", "organisationName": "OS4CSAPI", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}}}]}


def _system_stub(station: dict) -> dict:
    notation = station["stationNotation"]
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]}, "properties": {"uid": _system_uid(notation), "featureType": "sosa:Sensor", "name": f"SYKE Hydrology {station['name']}", "description": f"Curated Finnish SYKE hydrology station {station['name']} ({notation}) with selected water-level/discharge datastreams.", "validTime": [VALID_TIME_START, ".."]}}


def _system_sml(station: dict) -> dict:
    notation = station["stationNotation"]
    measure_labels = ", ".join(measure["label"] for measure in station.get("measures", []))
    docs = [{"role": "http://dbpedia.org/resource/Photograph", "name": "Representative Water-Level Gauge Photo", "description": "Real water-level staff gauge photograph used as representative sensor imagery for SYKE hydrology stations; not station-specific imagery.", "link": {"href": REPRESENTATIVE_GAUGE_PHOTO, "type": "image/jpeg"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Representative Gauge Photo Source", "link": {"href": REPRESENTATIVE_GAUGE_PHOTO_PAGE, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "SYKE Hydrologiarajapinta OData", "link": {"href": SYKE_ODATA_BASE, "type": "application/json"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "vesi.fi", "link": {"href": VESI_PORTAL, "type": "text/html"}}]
    for measure in station.get("measures", []):
        docs.append({"role": "http://dbpedia.org/resource/Web_page", "name": measure["label"], "description": "Latest-reading query for this curated SYKE measure.", "link": {"href": _latest_reading_url(measure), "type": "application/json"}})
    characteristics = [{"type": "Text", "name": "station_notation", "label": "Station Notation", "value": notation}, {"type": "Text", "name": "municipality", "label": "Municipality", "value": station.get("municipality", "")}, {"type": "Text", "name": "basin", "label": "Main Basin", "value": station.get("basin", "")}, {"type": "Text", "name": "sub_basin", "label": "Sub-Basin", "value": station.get("subBasin", "")}, {"type": "Text", "name": "lake", "label": "Lake", "value": station.get("lake", "")}, {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": station.get("selectionReason", "Curated Finnish demo station")}, {"type": "Text", "name": "curated_measures", "label": "Curated Measures", "value": measure_labels}]
    return {"type": "PhysicalSystem", "id": _system_uid(notation), "uniqueId": _system_uid(notation), "definition": "sosa:System", "label": f"SYKE Hydrology {station['name']}", "description": f"Finnish SYKE hydrology station {station['name']} ({notation}) in {station.get('municipality', 'Finland')}. This CSAPI system exposes selected water-level and discharge readings from the public Hydrologiarajapinta OData API.", "keywords": ["SYKE", "vesi.fi", "Finland", "hydrology", "water", station["name"], notation], "identifiers": [{"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"SYKE {station['name']}"}, {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "Station Notation", "value": notation}, {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(notation)}], "classifiers": [{"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "SYKE hydrology monitoring station"}, {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Finnish hydrology monitoring and environmental situational awareness"}], "contacts": [{"role": "operator", "organisationName": "Finnish Environment Institute (SYKE)", "contactInfo": {"onlineResource": {"linkage": SYKE_HOME}}}], "documents": docs, "characteristics": [{"label": "Station Properties", "characteristics": characteristics}], "capabilities": [{"label": "Publisher Capabilities", "capabilities": [{"type": "Quantity", "name": "publish_interval", "label": "Publish Interval", "uom": {"code": "s"}, "value": PUBLISH_INTERVAL_SECONDS}, {"type": "Text", "name": "source_query_mode", "label": "Source Query Mode", "value": "Latest SYKE OData readings polled with Paikka_Id filter and Aika desc ordering"}]}], "position": {"type": "Point", "coordinates": [station["lon"], station["lat"]], "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326"}}


def _go_compatible_system_sml(sml: dict, base_url: str) -> dict:
    if "csapi-go" not in base_url:
        return sml
    compatible = dict(sml)
    compatible.pop("characteristics", None)
    return compatible


def _datastream_schema(station: dict, measure: dict) -> dict:
    result_field = measure.get("resultField", "value")
    return {"uid": _datastream_uid(station, measure), "outputName": measure["outputName"], "name": measure["parameterName"], "description": f"{measure['label']}. Values are fetched from the SYKE Hydrologiarajapinta OData API and published as one CSAPI observation per selected station measure.", "documentation": [{"title": "Latest Reading", "href": _latest_reading_url(measure), "rel": "service"}, {"title": "SYKE Hydrologiarajapinta OData", "href": SYKE_ODATA_BASE, "rel": "documentation"}, {"title": "vesi.fi", "href": VESI_PORTAL, "rel": "about"}], "schema": {"obsFormat": "application/om+json", "resultSchema": {"type": "DataRecord", "label": f"SYKE {measure['parameterName']} Reading", "description": "Latest SYKE hydrology reading with source flag and raw query URL.", "fields": [{"type": "Time", "name": "timestamp", "label": "Observation Time", "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}}, {"type": "Text", "name": "stationId", "label": "Station Notation", "definition": "http://sensorml.com/ont/swe/property/StationID"}, {"type": "Text", "name": "placeId", "label": "SYKE Paikka ID", "definition": "http://sensorml.com/ont/swe/property/Identifier"}, {"type": "Text", "name": "parameter", "label": "Parameter", "definition": "http://sensorml.com/ont/swe/property/ObservableProperty"}, {"type": "Quantity", "name": result_field, "label": measure["parameterName"], "definition": "http://sensorml.com/ont/swe/property/Value", "uom": {"code": measure["unit"]}}, {"type": "Text", "name": "unit", "label": "Unit", "definition": "http://sensorml.com/ont/swe/property/Unit"}, {"type": "Text", "name": "flagId", "label": "SYKE Flag ID", "definition": "http://sensorml.com/ont/swe/property/QualityFlag"}, {"type": "Quantity", "name": "minimumValue", "label": "Minimum Value", "definition": "http://sensorml.com/ont/swe/property/Minimum", "uom": {"code": measure["unit"]}}, {"type": "Quantity", "name": "maximumValue", "label": "Maximum Value", "definition": "http://sensorml.com/ont/swe/property/Maximum", "uom": {"code": measure["unit"]}}, {"type": "Text", "name": "remark", "label": "Remark", "definition": "http://sensorml.com/ont/swe/property/Comment"}, {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"}]}}}


def _deploy_root() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [26.0, 63.0]}, "properties": {"uid": DEPLOY_ROOT_UID, "featureType": "sosa:Deployment", "name": "SYKE Hydrology Demo", "description": "Top-level grouping for curated Finnish SYKE hydrology monitoring station resources.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_group() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [26.0, 63.0]}, "properties": {"uid": DEPLOY_GROUP_UID, "featureType": "sosa:Deployment", "name": "SYKE Hydrology Stations", "description": "Grouping deployment for curated Finnish SYKE water-level and discharge stations.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    notation = station["stationNotation"]
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]}, "properties": {"uid": _deploy_uid(notation), "featureType": "sosa:Deployment", "name": f"SYKE Hydrology {station['name']}", "description": f"Deployment node linking Finnish SYKE hydrology station {station['name']} to its CSAPI system.", "validTime": [VALID_TIME_START, ".."], "platform@link": {"href": f"{base_url.rstrip('/')}/systems/{system_server_id}", "uid": _system_uid(notation), "title": f"SYKE Hydrology {station['name']}"}}}


def clean_all(base_url: str, auth: str, *, dry_run: bool = False, stats: dict):
    stations = _load_stations()
    for station in stations:
        clean_resource(base_url, auth, "deployments", _deploy_uid(station["stationNotation"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for station in stations:
        clean_resource(base_url, auth, "systems", _system_uid(station["stationNotation"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _ensure_system_resilient(base_url: str, auth: str, station: dict, *, dry_run: bool, stats: dict, force_sml: bool) -> str | None:
    uid = _system_uid(station["stationNotation"])
    try:
        return ensure_system(base_url, auth, uid, _system_stub(station), _go_compatible_system_sml(_system_sml(station), base_url), dry_run=dry_run, stats=stats, force_sml=force_sml)
    except RuntimeError as exc:
        if "HTTP 500 POST" not in str(exc) or "/systems" not in str(exc):
            raise
        recovered = find_by_uid(base_url, auth, "systems", uid, no_cache=True)
        if not recovered:
            raise
        print(f"  [WARN] Server returned HTTP 500 after creating system {uid}; recovered id={recovered}")
        if not dry_run:
            try:
                api_put(base_url, f"systems/{recovered}", _go_compatible_system_sml(_system_sml(station), base_url), auth, content_type="application/sml+json")
                print(f"  [SML] PUT SensorML for recovered system {uid} (id={recovered})")
            except Exception as sml_exc:
                print(f"  [WARN] SML PUT skipped for recovered system {uid} (id={recovered}): {sml_exc}")
        if stats:
            stats.setdefault("recovered", 0)
            stats["recovered"] += 1
        return recovered


def _print_dry_run_plan(stations: list[dict]):
    print("  -- Procedure --")
    print(f"  [DRY] Would create/update procedure: {PROC_UID}")
    print("  -- Systems + Datastreams --")
    for station in stations:
        print(f"  [DRY] Would create/update system: {_system_uid(station['stationNotation'])}")
        for measure in station.get("measures", []):
            print(f"  [DRY] Would create datastream '{measure['outputName']}' for Paikka_Id {measure['placeId']}")
    print("  -- Deployments --")
    print(f"  [DRY] Would create deployment: {DEPLOY_ROOT_UID}")
    print(f"  [DRY] Would create deployment: {DEPLOY_GROUP_UID}")
    for station in stations:
        print(f"  [DRY] Would create deployment: {_deploy_uid(station['stationNotation'])}")


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False, force_sml: bool = False):
    server_config = get_config()
    base_url = server_config["base_url"]
    auth = _auth_header(server_config["user"], server_config["password"])
    stations = _load_stations()
    stats: dict[str, int] = {}
    print("\n" + "=" * 70)
    print("  SYKE Hydrology -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)}")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}\n")
    if dry_run and not clean and not clean_only:
        _print_dry_run_plan(stations)
        print_summary(stats, dry_run)
        return
    if clean or clean_only:
        print("  -- Cleaning existing resources --")
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return
    print("  -- Procedure --")
    ensure_procedure(base_url, auth, PROC_UID, _procedure_stub(), _procedure_sml(), dry_run=dry_run, stats=stats, force_sml=force_sml)
    print("  -- Systems + Datastreams --")
    system_ids: dict[str, str] = {}
    for station in stations:
        notation = station["stationNotation"]
        sys_id = _ensure_system_resilient(base_url, auth, station, dry_run=dry_run, stats=stats, force_sml=force_sml)
        if sys_id:
            system_ids[notation] = sys_id
        for measure in station.get("measures", []):
            ensure_datastream(base_url, auth, sys_id or "pending", measure["outputName"], _datastream_schema(station, measure), dry_run=dry_run, stats=stats)
    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(), dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(), parent_id=root_id, dry_run=dry_run, stats=stats)
    for station in stations:
        notation = station["stationNotation"]
        ensure_deployment(base_url, auth, _deploy_uid(notation), _deploy_station(station, system_ids.get(notation) or "pending", base_url), parent_id=group_id, dry_run=dry_run, stats=stats)
    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap SYKE hydrology CSAPI resources")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only, dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
