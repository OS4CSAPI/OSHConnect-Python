#!/usr/bin/env python3
"""Bootstrap curated Finnish Digitraffic weather camera CSAPI resources."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config, _auth_header,
    ensure_procedure, ensure_datastream, ensure_deployment,
    find_by_uid, clean_resource, add_bootstrap_args, print_summary,
)


VALID_TIME_START = "2026-01-01T00:00:00Z"
PUBLISH_INTERVAL_SECONDS = 300

PROC_UID = "urn:os4csapi:procedure:digitraffic-weathercam:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:digitraffic-weathercam-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:digitraffic-weathercam-presets:v1"
DS_OUTPUT_NAME = "digitrafficWeatherCamImage"

DIGITRAFFIC_HOME = "https://www.digitraffic.fi/en/road-traffic/"
DIGITRAFFIC_LICENSE = "https://www.digitraffic.fi/en/terms-of-service/"
DIGITRAFFIC_WEATHERCAM_STATIONS = "https://tie.digitraffic.fi/api/weathercam/v1/stations"
DIGITRAFFIC_WEATHERCAM_IMAGE_BASE = "https://weathercam.digitraffic.fi"


def _load_cameras() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "cameras.json"), encoding="utf-8") as file:
        return json.load(file)["cameras"]


def _system_uid(road_weather_station_id: str) -> str:
    return f"urn:os4csapi:system:digitraffic-road-weather:{road_weather_station_id}:v1"


def _deploy_uid(camera: dict) -> str:
    return f"urn:os4csapi:deployment:digitraffic-weathercam-{camera['presetId']}:v1"


def _datastream_uid(camera: dict) -> str:
    return f"urn:os4csapi:datastream:digitraffic-weathercam:{camera['presetId']}:digitrafficWeatherCamImage:v1"


def _station_data_url(camera_station_id: str) -> str:
    return f"https://tie.digitraffic.fi/api/weathercam/v1/stations/{camera_station_id}/data"


def _image_url(preset_id: str) -> str:
    return f"{DIGITRAFFIC_WEATHERCAM_IMAGE_BASE}/{preset_id}.jpg"


def _thumb_url(preset_id: str) -> str:
    return f"{_image_url(preset_id)}?thumbnail=true"


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "Digitraffic Weather Camera Image v1",
        "description": "Publishes image-reference observations from curated Fintraffic Digitraffic road-weather camera presets.",
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "Digitraffic Weather Camera Image v1",
    "description": (
        "Polls selected Fintraffic Digitraffic road-weather camera preset metadata, "
        "derives direct JPEG and thumbnail URLs, and publishes image-reference observations "
        "on the companion Digitraffic road-weather station systems."
    ),
    "keywords": ["Fintraffic", "Digitraffic", "Finland", "road weather", "weather camera", "image reference"],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Road Traffic", "link": {"href": DIGITRAFFIC_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Weather Cameras", "link": {"href": DIGITRAFFIC_WEATHERCAM_STATIONS, "type": "application/json"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Digitraffic Terms of Use", "link": {"href": DIGITRAFFIC_LICENSE, "type": "text/html"}},
    ],
    "contacts": [
        {"role": "operator", "organisationName": "Fintraffic / Digitraffic", "contactInfo": {"onlineResource": {"linkage": DIGITRAFFIC_HOME}}},
        {"role": "publisher", "organisationName": "OS4CSAPI", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}}},
    ],
}


def _datastream_schema(camera: dict) -> dict:
    preset_id = camera["presetId"]
    return {
        "uid": _datastream_uid(camera),
        "outputName": DS_OUTPUT_NAME,
        "name": "Digitraffic Weather Camera Image",
        "description": (
            f"Image-reference observations for Digitraffic camera preset {preset_id} "
            f"at {camera['cameraStationName']}, attached to road-weather station "
            f"{camera['roadWeatherStationId']} ({camera['roadWeatherStationName']})."
        ),
        "documentation": [
            {"title": "Weathercam Station Latest Data", "href": _station_data_url(camera["cameraStationId"]), "rel": "service"},
            {"title": "Latest JPEG", "href": _image_url(preset_id), "rel": "alternate"},
            {"title": "Latest Thumbnail", "href": _thumb_url(preset_id), "rel": "preview"},
            {"title": "Digitraffic Terms of Use", "href": DIGITRAFFIC_LICENSE, "rel": "license"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "Digitraffic Weather Camera Image Reference",
                "fields": [
                    {"type": "Text", "name": "stationId", "label": "Road Weather Station ID", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "camId", "label": "Weather Camera Preset ID", "definition": "http://sensorml.com/ont/swe/property/SensorID"},
                    {"type": "Text", "name": "cameraStationId", "label": "Camera Station ID", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "cameraStationName", "label": "Camera Station Name", "definition": "http://purl.org/dc/elements/1.1/title"},
                    {"type": "Text", "name": "imageUrl", "label": "Full-Size Image URL", "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text", "name": "thumbUrl", "label": "Thumbnail Image URL", "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text", "name": "latestImageUrl", "label": "Latest Image URL", "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text", "name": "mediaType", "label": "Media Type", "definition": "http://purl.org/dc/elements/1.1/format"},
                    {"type": "Text", "name": "sourceType", "label": "Source Type", "definition": "http://sensorml.com/ont/swe/property/ProcessingType"},
                    {"type": "Boolean", "name": "live", "label": "Live Source", "definition": "http://sensorml.com/ont/swe/property/Status"},
                    {"type": "Count", "name": "httpStatus", "label": "HTTP Status", "definition": "http://sensorml.com/ont/swe/property/StatusCode"},
                    {"type": "Text", "name": "etag", "label": "HTTP ETag", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "lastModified", "label": "HTTP Last-Modified", "definition": "http://sensorml.com/ont/swe/property/Timestamp"},
                    {"type": "Text", "name": "sourceLastModifiedTime", "label": "Parsed Source Last-Modified Time", "definition": "http://sensorml.com/ont/swe/property/Timestamp"},
                    {"type": "Text", "name": "contentLength", "label": "Content Length", "definition": "http://sensorml.com/ont/swe/property/Size"},
                    {"type": "Text", "name": "imageToken", "label": "Image Change Token", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Boolean", "name": "imageChanged", "label": "Image Changed", "definition": "http://sensorml.com/ont/swe/property/Status"},
                    {"type": "Text", "name": "firstSeenTime", "label": "Current Image First Seen Time", "definition": "http://sensorml.com/ont/swe/property/Timestamp"},
                    {"type": "Text", "name": "lastSeenTime", "label": "Source Last Checked Time", "definition": "http://sensorml.com/ont/swe/property/Timestamp"},
                    {"type": "Text", "name": "lastChangedTime", "label": "Image Last Changed Time", "definition": "http://sensorml.com/ont/swe/property/Timestamp"},
                    {"type": "Count", "name": "unchangedPollCount", "label": "Unchanged Poll Count", "definition": "http://sensorml.com/ont/swe/property/Count"},
                    {"type": "Text", "name": "stalenessStatus", "label": "Staleness Status", "definition": "http://sensorml.com/ont/swe/property/Status"},
                    {"type": "Count", "name": "sourceAgeSeconds", "label": "Seconds Since Image Changed", "definition": "http://sensorml.com/ont/swe/property/ElapsedTime"},
                    {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [25.0, 63.5]}, "properties": {"uid": DEPLOY_ROOT_UID, "featureType": "sosa:Deployment", "name": "Digitraffic Weather Camera Demo", "description": "Top-level grouping for curated Finnish road-weather camera image-reference resources.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_group() -> dict:
    return {"type": "Feature", "geometry": {"type": "Point", "coordinates": [25.0, 63.5]}, "properties": {"uid": DEPLOY_GROUP_UID, "featureType": "sosa:Deployment", "name": "Digitraffic Weather Camera Presets", "description": "Grouping deployment for curated Fintraffic Digitraffic weather camera presets.", "validTime": [VALID_TIME_START, ".."]}}


def _deploy_camera(camera: dict, system_server_id: str, base_url: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [camera["lon"], camera["lat"]]},
        "properties": {
            "uid": _deploy_uid(camera),
            "featureType": "sosa:Deployment",
            "name": f"Digitraffic Weather Camera {camera['cameraStationName']} {camera['presetId']}",
            "description": (
                f"Weather camera preset {camera['presetId']} attached to Finnish road-weather "
                f"station {camera['roadWeatherStationId']} ({camera['roadWeatherStationName']})."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {"href": f"{base_url.rstrip('/')}/systems/{system_server_id}", "uid": _system_uid(camera["roadWeatherStationId"]), "title": f"Digitraffic Road Weather {camera['roadWeatherStationName']}"},
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool, stats: dict):
    for camera in _load_cameras():
        clean_resource(base_url, auth, "deployments", _deploy_uid(camera), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False, force_sml: bool = False):
    config = get_config()
    base_url = config["base_url"]
    auth = _auth_header(config["user"], config["password"])
    cameras = _load_cameras()
    stats: dict[str, int] = {}

    print("\n" + "=" * 70)
    print("  Digitraffic Weathercam -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Cameras:   {len(cameras)}")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}\n")

    if clean or clean_only:
        print("  -- Cleaning existing resources --")
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    print("  -- Procedure --")
    ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_STUB, PROCEDURE_SML, dry_run=dry_run, stats=stats, force_sml=force_sml)

    print("  -- Companion Datastreams --")
    system_ids: dict[str, str] = {}
    for camera in cameras:
        station_id = camera["roadWeatherStationId"]
        sys_id = find_by_uid(base_url, auth, "systems", _system_uid(station_id), no_cache=True)
        if not sys_id and not dry_run:
            print(f"  [WARN] Missing road-weather system for station {station_id}; skipping camera {camera['presetId']}")
            continue
        system_ids[station_id] = sys_id or "pending"
        ensure_datastream(base_url, auth, sys_id or "pending", DS_OUTPUT_NAME, _datastream_schema(camera), dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(), dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(), parent_id=root_id, dry_run=dry_run, stats=stats)
    for camera in cameras:
        station_id = camera["roadWeatherStationId"]
        sys_id = system_ids.get(station_id)
        if not sys_id and not dry_run:
            continue
        ensure_deployment(base_url, auth, _deploy_uid(camera), _deploy_camera(camera, sys_id or "pending", base_url), parent_id=group_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Digitraffic Weathercam resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only, dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()