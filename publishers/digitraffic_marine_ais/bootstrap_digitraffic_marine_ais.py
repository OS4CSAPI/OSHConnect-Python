#!/usr/bin/env python3
"""Bootstrap Finnish Digitraffic Marine AIS CSAPI resources."""

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
PROC_UID = "urn:os4csapi:procedure:digitraffic-marine-ais:v1"
SYSTEM_UID = "urn:os4csapi:system:digitraffic-marine-ais-feed:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:digitraffic-marine-ais-demo:v1"
LEGACY_DEPLOY_FEED_UID = "urn:os4csapi:deployment:digitraffic-marine-ais-feed:v1"
DS_OUTPUT_NAME = "digitrafficMarineAisPosition"

DIGITRAFFIC_MARINE_HOME = "https://www.digitraffic.fi/en/marine-traffic/"
DIGITRAFFIC_MARINE_SWAGGER = "https://meri.digitraffic.fi/swagger/"
DIGITRAFFIC_MARINE_AIS_LOCATIONS = "https://meri.digitraffic.fi/api/ais/v1/locations"
DIGITRAFFIC_MARINE_AIS_VESSELS = "https://meri.digitraffic.fi/api/ais/v1/vessels"
DIGITRAFFIC_TERMS = "https://www.digitraffic.fi/en/terms-of-use/"
AIS_ANTENNA_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/5/51/Compact_AIS_antenna.jpg"


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "config.json"), encoding="utf-8") as file:
        return json.load(file)["digitraffic_marine_ais"]


def _bbox_center(config: dict) -> tuple[float, float]:
    bbox = config["bounding_box"]
    return ((bbox["lomin"] + bbox["lomax"]) / 2, (bbox["lamin"] + bbox["lamax"]) / 2)


def _bbox_label(config: dict) -> str:
    bbox = config["bounding_box"]
    return f"lat {bbox['lamin']}-{bbox['lamax']}, lon {bbox['lomin']}-{bbox['lomax']}"


def _procedure_stub() -> dict:
    return {"type": "Feature", "geometry": None, "properties": {"uid": PROC_UID, "featureType": "sosa:ObservingProcedure", "name": "Digitraffic Marine AIS Decoder v1", "description": "Publishes vessel position observations from Fintraffic Digitraffic Marine AIS latest-location data.", "validTime": [VALID_TIME_START, ".."]}}


def _procedure_sml() -> dict:
    return {"type": "SimpleProcess", "id": PROC_UID, "uniqueId": PROC_UID, "definition": "sosa:ObservingProcedure", "label": "Digitraffic Marine AIS Decoder v1", "description": "Fetches the Fintraffic Digitraffic Marine AIS latest vessel-location feed, filters it to the configured Gulf of Finland demo window, enriches records with vessel metadata when available, and publishes one CSAPI observation per vessel state.", "keywords": ["Fintraffic", "Digitraffic", "Finland", "marine", "AIS", "vessel", "tracking", "Gulf of Finland"], "documents": [{"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Marine Traffic", "link": {"href": DIGITRAFFIC_MARINE_HOME, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Marine Swagger", "link": {"href": DIGITRAFFIC_MARINE_SWAGGER, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "AIS Locations Endpoint", "link": {"href": DIGITRAFFIC_MARINE_AIS_LOCATIONS, "type": "application/json"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Terms of Use", "link": {"href": DIGITRAFFIC_TERMS, "type": "text/html"}}], "contacts": [{"role": "operator", "organisationName": "Fintraffic / Digitraffic", "contactInfo": {"onlineResource": {"linkage": DIGITRAFFIC_MARINE_HOME}}}, {"role": "publisher", "organisationName": "OS4CSAPI", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}}}]}


def _system_stub(config: dict) -> dict:
    lon, lat = _bbox_center(config)
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"uid": SYSTEM_UID, "featureType": "sosa:Sensor", "name": "Digitraffic Marine AIS Feed - Gulf of Finland", "description": f"Feed-adapter system for Digitraffic Marine AIS vessel observations in the configured demo window ({_bbox_label(config)}).", "validTime": [VALID_TIME_START, ".."]}}


def _system_sml(config: dict) -> dict:
    lon, lat = _bbox_center(config)
    return {"type": "PhysicalSystem", "id": SYSTEM_UID, "uniqueId": SYSTEM_UID, "definition": "sosa:System", "label": "Digitraffic Marine AIS Feed - Gulf of Finland", "description": f"Feed-adapter system representing a bounded Digitraffic Marine AIS query window over the Gulf of Finland ({_bbox_label(config)}). The system is not a single physical sensor; it republishes live AIS vessel states from Fintraffic's public marine traffic infrastructure.", "keywords": ["Fintraffic", "Digitraffic", "Finland", "marine", "AIS", "vessels", "Gulf of Finland", "feed adapter"], "identifiers": [{"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": SYSTEM_UID}], "classifiers": [{"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "Digitraffic Marine AIS feed adapter"}, {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Maritime traffic situational awareness"}], "contacts": [{"role": "operator", "organisationName": "Fintraffic / Digitraffic", "contactInfo": {"onlineResource": {"linkage": DIGITRAFFIC_MARINE_HOME}}}], "documents": [{"role": "http://dbpedia.org/resource/Photograph", "name": "Actual AIS antenna hardware", "description": "Photograph of real compact AIS antenna hardware used as the representative sensor image for the AIS feed adapter. Source: Wikimedia Commons.", "link": {"href": AIS_ANTENNA_IMAGE, "type": "image/jpeg"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Marine Traffic", "link": {"href": DIGITRAFFIC_MARINE_HOME, "type": "text/html"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "AIS Locations Endpoint", "link": {"href": DIGITRAFFIC_MARINE_AIS_LOCATIONS, "type": "application/json"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "AIS Vessels Endpoint", "link": {"href": DIGITRAFFIC_MARINE_AIS_VESSELS, "type": "application/json"}}, {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Terms of Use", "link": {"href": DIGITRAFFIC_TERMS, "type": "text/html"}}], "characteristics": [{"label": "Feed Configuration", "characteristics": [{"type": "Text", "name": "coverage_bbox", "label": "Coverage BBox", "value": _bbox_label(config)}, {"type": "Quantity", "name": "max_vessels_per_cycle", "label": "Max Vessels Per Cycle", "uom": {"code": "1"}, "value": config.get("max_vessels_per_cycle", 60)}, {"type": "Text", "name": "license", "label": "License", "value": "Digitraffic terms of use and attribution"}]}], "capabilities": [{"definition": "http://www.w3.org/ns/ssn/systems/SystemCapability", "label": "Publisher Capabilities", "capabilities": [{"type": "Quantity", "name": "publish_interval", "definition": "http://qudt.org/vocab/quantitykind/Period", "label": "Publish Interval", "uom": {"code": "s"}, "value": config.get("cadence_seconds", 300)}]}], "position": {"type": "Point", "coordinates": [lon, lat], "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326"}}


def _datastream_schema() -> dict:
    fields = [
        {"type": "Text", "name": "mmsi", "label": "MMSI", "definition": "http://sensorml.com/ont/swe/property/MMSI"},
        {"type": "Text", "name": "vesselName", "label": "Vessel Name", "definition": "http://sensorml.com/ont/swe/property/Name"},
        {"type": "Text", "name": "callSign", "label": "Call Sign", "definition": "http://sensorml.com/ont/swe/property/CallSign"},
        {"type": "Text", "name": "imo", "label": "IMO Number", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
        {"type": "Quantity", "name": "lat_deg", "label": "Latitude", "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude", "uom": {"code": "deg"}},
        {"type": "Quantity", "name": "lon_deg", "label": "Longitude", "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude", "uom": {"code": "deg"}},
        {"type": "Quantity", "name": "sog_kts", "label": "Speed Over Ground", "definition": "http://sensorml.com/ont/swe/property/SpeedOverGround", "uom": {"code": "[kn_i]"}},
        {"type": "Quantity", "name": "cog_deg", "label": "Course Over Ground", "definition": "http://sensorml.com/ont/swe/property/CourseOverGround", "uom": {"code": "deg"}},
        {"type": "Quantity", "name": "heading_deg", "label": "Heading", "definition": "http://sensorml.com/ont/swe/property/Heading", "uom": {"code": "deg"}},
        {"type": "Text", "name": "navStatus", "label": "Navigation Status", "definition": "http://sensorml.com/ont/swe/property/Status"},
        {"type": "Text", "name": "shipType", "label": "Ship Type", "definition": "http://sensorml.com/ont/swe/property/Type"},
        {"type": "Text", "name": "destination", "label": "Destination", "definition": "http://sensorml.com/ont/swe/property/Destination"},
        {"type": "Text", "name": "sourceDataUpdatedTime", "label": "Source Data Updated Time", "definition": "http://sensorml.com/ont/swe/property/UpdateTime"},
        {"type": "Text", "name": "sourcePayloadJson", "label": "Source Payload JSON", "definition": "http://sensorml.com/ont/swe/property/RawData"},
    ]
    return {"uid": "urn:os4csapi:datastream:digitraffic-marine-ais:positions:v1", "outputName": DS_OUTPUT_NAME, "name": "Digitraffic Marine AIS Vessel Positions", "description": "Live AIS vessel position observations from Fintraffic Digitraffic Marine, filtered to the configured Gulf of Finland demo window.", "schema": {"obsFormat": "application/om+json", "resultSchema": {"type": "DataRecord", "label": "Digitraffic Marine AIS Vessel Position", "fields": fields}}}


def _deploy_root(config: dict) -> dict:
    lon, lat = _bbox_center(config)
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"uid": DEPLOY_ROOT_UID, "featureType": "sosa:Deployment", "name": "Digitraffic Marine AIS Demo", "description": "Top-level grouping for the Finnish Digitraffic Marine AIS feed-adapter demo.", "validTime": [VALID_TIME_START, ".."]}}


def clean_all(base_url: str, auth: str, *, dry_run: bool, stats: dict):
    clean_resource(base_url, auth, "deployments", LEGACY_DEPLOY_FEED_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "systems", SYSTEM_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False, force_sml: bool = False):
    config = _load_config(); server = get_config(); base_url = server["base_url"]; auth = _auth_header(server["user"], server["password"]); stats: dict[str, int] = {}
    print("\n" + "=" * 70); print("  Digitraffic Marine AIS -- Bootstrap"); print("=" * 70); print(f"  Server:    {base_url}"); print(f"  BBox:      {_bbox_label(config)}"); print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}\n")
    if clean or clean_only:
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run); return
    print("  -- Procedure --"); ensure_procedure(base_url, auth, PROC_UID, _procedure_stub(), _procedure_sml(), dry_run=dry_run, stats=stats, force_sml=force_sml)
    print("  -- System + Datastream --"); system_id = ensure_system(base_url, auth, SYSTEM_UID, _system_stub(config), _system_sml(config), dry_run=dry_run, stats=stats, force_sml=force_sml)
    if system_id:
        ensure_datastream(base_url, auth, system_id, DS_OUTPUT_NAME, _datastream_schema(), dry_run=dry_run, stats=stats)
    print("  -- Deployments --"); clean_resource(base_url, auth, "deployments", LEGACY_DEPLOY_FEED_UID, dry_run=dry_run, stats=stats, cascade=False); ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(config), dry_run=dry_run, stats=stats)
    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Digitraffic Marine AIS CSAPI resources")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only, dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()