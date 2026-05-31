#!/usr/bin/env python3
"""Bootstrap Finnish Digitraffic Rail live-train CSAPI resources."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config, _auth_header,
    ensure_procedure, ensure_system, ensure_datastream, ensure_deployment,
    clean_resource, add_bootstrap_args, print_summary,
)


VALID_TIME_START = "2026-01-01T00:00:00Z"
PROC_UID = "urn:os4csapi:procedure:digitraffic-rail-trains:v1"
SYSTEM_UID = "urn:os4csapi:system:digitraffic-rail-trains-feed:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:digitraffic-rail-trains-demo:v1"
DEPLOY_FEED_UID = "urn:os4csapi:deployment:digitraffic-rail-trains-feed:v1"
DS_OUTPUT_NAME = "digitrafficRailTrainPosition"

DIGITRAFFIC_RAIL_HOME = "https://www.digitraffic.fi/en/railway-traffic/"
DIGITRAFFIC_RAIL_SWAGGER = "https://rata.digitraffic.fi/swagger/"
DIGITRAFFIC_RAIL_LOCATIONS = "https://rata.digitraffic.fi/api/v1/train-locations/latest/"
DIGITRAFFIC_RAIL_LIVE_TRAINS = "https://rata.digitraffic.fi/api/v1/live-trains"
DIGITRAFFIC_TERMS = "https://www.digitraffic.fi/en/terms-of-use/"
RAIL_REPRESENTATIVE_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/2/2d/Sm5_01_Helsinki_railway_station.jpg"


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "config.json"), encoding="utf-8") as file:
        return json.load(file)["digitraffic_rail_trains"]


def _bbox_center(config: dict) -> tuple[float, float]:
    bbox = config["bounding_box"]
    return ((bbox["lomin"] + bbox["lomax"]) / 2, (bbox["lamin"] + bbox["lamax"]) / 2)


def _bbox_label(config: dict) -> str:
    bbox = config["bounding_box"]
    return f"lat {bbox['lamin']}-{bbox['lamax']}, lon {bbox['lomin']}-{bbox['lomax']}"


def _procedure_stub() -> dict:
    return {"type": "Feature", "geometry": None, "properties": {"uid": PROC_UID, "featureType": "sosa:ObservingProcedure", "name": "Digitraffic Rail Live Train Decoder v1", "description": "Publishes Finnish live train position observations from Fintraffic Digitraffic Rail latest-location data.", "validTime": [VALID_TIME_START, ".."]}}


def _procedure_sml() -> dict:
    return {"type": "SimpleProcess", "id": PROC_UID, "uniqueId": PROC_UID, "definition": "sosa:ObservingProcedure", "label": "Digitraffic Rail Live Train Decoder v1", "description": "Fetches Fintraffic Digitraffic Rail latest train locations, optionally enriches them with live-train metadata, filters to the configured Finland demo window, and publishes one CSAPI observation per current train position.", "keywords": ["Fintraffic", "Digitraffic", "Finland", "rail", "train", "live train", "tracking"], "documents": [{"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Railway Traffic", "link": {"href": DIGITRAFFIC_RAIL_HOME, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Rail Swagger", "link": {"href": DIGITRAFFIC_RAIL_SWAGGER, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Latest Train Locations Endpoint", "link": {"href": DIGITRAFFIC_RAIL_LOCATIONS, "type": "application/json"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Terms of Use", "link": {"href": DIGITRAFFIC_TERMS, "type": "text/html"}}], "contacts": [{"role": "operator", "organisationName": "Fintraffic / Digitraffic", "contactInfo": {"onlineResource": {"linkage": DIGITRAFFIC_RAIL_HOME}}}, {"role": "publisher", "organisationName": "OS4CSAPI", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}}}]}


def _system_stub(config: dict) -> dict:
    lon, lat = _bbox_center(config)
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"uid": SYSTEM_UID, "featureType": "sosa:Sensor", "name": "Digitraffic Rail Live Trains Feed - Finland", "description": f"Feed-adapter system for Digitraffic Rail live train observations in the configured Finland demo window ({_bbox_label(config)}).", "validTime": [VALID_TIME_START, ".."]}}


def _system_sml(config: dict) -> dict:
    return {"type": "PhysicalSystem", "id": SYSTEM_UID, "uniqueId": SYSTEM_UID, "definition": "sosa:System", "label": "Digitraffic Rail Live Trains Feed - Finland", "description": f"Feed-adapter system representing a bounded Digitraffic Rail query window over Finland ({_bbox_label(config)}). The system republishes current train locations from Fintraffic's public railway traffic infrastructure.", "keywords": ["Fintraffic", "Digitraffic", "Finland", "rail", "train", "live trains", "feed adapter"], "identifiers": [{"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": SYSTEM_UID}], "classifiers": [{"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "Digitraffic Rail live train feed adapter"}, {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Rail traffic situational awareness"}], "contacts": [{"role": "operator", "organisationName": "Fintraffic / Digitraffic", "contactInfo": {"onlineResource": {"linkage": DIGITRAFFIC_RAIL_HOME}}}], "documents": [{"role": "http://dbpedia.org/resource/Photograph", "name": "Finnish passenger train at Helsinki railway station", "description": "Photograph of real Finnish rail rolling stock used as representative imagery for the Digitraffic Rail feed adapter. Source: Wikimedia Commons.", "link": {"href": RAIL_REPRESENTATIVE_IMAGE, "type": "image/jpeg"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Railway Traffic", "link": {"href": DIGITRAFFIC_RAIL_HOME, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Latest Train Locations Endpoint", "link": {"href": DIGITRAFFIC_RAIL_LOCATIONS, "type": "application/json"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Live Trains Endpoint", "link": {"href": DIGITRAFFIC_RAIL_LIVE_TRAINS, "type": "application/json"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Terms of Use", "link": {"href": DIGITRAFFIC_TERMS, "type": "text/html"}}], "capabilities": [{"label": "Publish Interval", "value": f"{config.get('cadence_seconds', 300)} s"}]}


def _datastream_schema() -> dict:
    fields = [
        {"type": "Text", "name": "trainNumber", "label": "Train Number", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
        {"type": "Text", "name": "departureDate", "label": "Departure Date", "definition": "http://sensorml.com/ont/swe/property/Date"},
        {"type": "Quantity", "name": "lat_deg", "label": "Latitude", "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude", "uom": {"code": "deg"}},
        {"type": "Quantity", "name": "lon_deg", "label": "Longitude", "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude", "uom": {"code": "deg"}},
        {"type": "Quantity", "name": "speed_kmh", "label": "Speed", "definition": "http://sensorml.com/ont/swe/property/Speed", "uom": {"code": "km/h"}},
        {"type": "Quantity", "name": "accuracy_m", "label": "Location Accuracy", "definition": "http://sensorml.com/ont/swe/property/Accuracy", "uom": {"code": "m"}},
        {"type": "Text", "name": "sourceTimestamp", "label": "Source Timestamp", "definition": "http://sensorml.com/ont/swe/property/UpdateTime"},
        {"type": "Text", "name": "trainType", "label": "Train Type", "definition": "http://sensorml.com/ont/swe/property/Type"},
        {"type": "Text", "name": "trainCategory", "label": "Train Category", "definition": "http://sensorml.com/ont/swe/property/Category"},
        {"type": "Text", "name": "commuterLineId", "label": "Commuter Line ID", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
        {"type": "Text", "name": "operatorShortCode", "label": "Operator", "definition": "http://sensorml.com/ont/swe/property/Operator"},
        {"type": "Text", "name": "sourcePayloadJson", "label": "Source Payload JSON", "definition": "http://sensorml.com/ont/swe/property/RawData"},
    ]
    return {"uid": "urn:os4csapi:datastream:digitraffic-rail-trains:positions:v1", "outputName": DS_OUTPUT_NAME, "name": "Digitraffic Rail Live Train Positions", "description": "Live Finnish train position observations from Fintraffic Digitraffic Rail latest train locations.", "schema": {"obsFormat": "application/om+json", "resultSchema": {"type": "DataRecord", "label": "Digitraffic Rail Live Train Position", "fields": fields}}}


def _deploy_root(config: dict) -> dict:
    lon, lat = _bbox_center(config)
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"uid": DEPLOY_ROOT_UID, "featureType": "sosa:Deployment", "name": "Digitraffic Rail Live Trains Demo", "description": "Top-level grouping for the Finnish Digitraffic Rail live-train feed-adapter demo.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_feed(config: dict, system_server_id: str, base_url: str) -> dict:
    lon, lat = _bbox_center(config)
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"uid": DEPLOY_FEED_UID, "featureType": "sosa:Deployment", "name": "Digitraffic Rail Live Trains Feed", "description": f"Deployment linking the Digitraffic Rail live-train feed adapter to the configured Finland query window ({_bbox_label(config)}).", "validTime": [VALID_TIME_START, ".."], "platform@link": {"href": f"{base_url.rstrip('/')}/systems/{system_server_id}", "uid": SYSTEM_UID, "title": "Digitraffic Rail Live Trains Feed - Finland"}}}


def clean_all(base_url: str, auth: str, *, dry_run: bool, stats: dict):
    clean_resource(base_url, auth, "deployments", DEPLOY_FEED_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "systems", SYSTEM_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _print_dry_run_plan(config: dict):
    print("  -- Procedure --")
    print(f"  [DRY] Would create/update procedure: {PROC_UID}")
    print("  -- System + Datastream --")
    print(f"  [DRY] Would create/update system: {SYSTEM_UID}")
    print(f"  [DRY] Would create datastream '{DS_OUTPUT_NAME}' on system {SYSTEM_UID}")
    print("  -- Deployments --")
    print(f"  [DRY] Would create deployment: {DEPLOY_ROOT_UID}")
    print(f"  [DRY] Would create deployment: {DEPLOY_FEED_UID}")
    print(f"  [DRY] Source endpoint: {config.get('locations_endpoint', DIGITRAFFIC_RAIL_LOCATIONS)}")


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False, force_sml: bool = False):
    config = _load_config(); server = get_config(); base_url = server["base_url"]; auth = _auth_header(server["user"], server["password"]); stats: dict[str, int] = {}
    print("\n" + "=" * 70); print("  Digitraffic Rail Live Trains -- Bootstrap"); print("=" * 70); print(f"  Server:    {base_url}"); print(f"  BBox:      {_bbox_label(config)}"); print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}\n")
    if dry_run and not clean and not clean_only:
        _print_dry_run_plan(config)
        print_summary(stats, dry_run)
        return
    if clean or clean_only:
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run); return
    print("  -- Procedure --"); ensure_procedure(base_url, auth, PROC_UID, _procedure_stub(), _procedure_sml(), dry_run=dry_run, stats=stats, force_sml=force_sml)
    print("  -- System + Datastream --"); system_id = ensure_system(base_url, auth, SYSTEM_UID, _system_stub(config), _system_sml(config), dry_run=dry_run, stats=stats, force_sml=force_sml)
    if system_id:
        ensure_datastream(base_url, auth, system_id, DS_OUTPUT_NAME, _datastream_schema(), dry_run=dry_run, stats=stats)
    print("  -- Deployments --"); ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(config), dry_run=dry_run, stats=stats)
    if system_id:
        ensure_deployment(base_url, auth, DEPLOY_FEED_UID, _deploy_feed(config, system_id, base_url), dry_run=dry_run, stats=stats)
    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Digitraffic Rail live-train CSAPI resources")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only, dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
