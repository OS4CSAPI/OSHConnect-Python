#!/usr/bin/env python3
"""Bootstrap Storebaelt webcam CSAPI resources."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config,
    _auth_header,
    ensure_procedure,
    ensure_system,
    ensure_datastream,
    ensure_deployment,
    clean_resource,
    add_bootstrap_args,
    print_summary,
)


VALID_TIME_START = "2026-01-01T00:00:00Z"
PUBLISH_INTERVAL_SECONDS = 300

PROC_UID = "urn:os4csapi:procedure:storebaelt-webcam-poster:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:storebaelt-webcams-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:storebaelt-webcams:v1"
DS_OUTPUT_NAME = "storebaeltWebcamImage"

STOREBAELT_HOME = "https://storebaelt.dk/"
STOREBAELT_WEBCAMS_PAGE = "https://storebaelt.dk/trafik-vejr/webcams/"
STOREBAELT_OPERATOR = "A/S Storebaelt"


def _load_cameras() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "cameras.json"), encoding="utf-8") as file:
        return json.load(file)["cameras"]


def _system_uid(camera: dict | str) -> str:
    camera_id = camera if isinstance(camera, str) else camera["id"]
    return f"urn:os4csapi:system:storebaelt-webcam:{camera_id}:v1"


def _deploy_uid(camera: dict) -> str:
    return f"urn:os4csapi:deployment:storebaelt-webcam-{camera['id']}:v1"


def _datastream_uid(camera: dict) -> str:
    return f"urn:os4csapi:datastream:storebaelt-webcam:{camera['id']}:storebaeltWebcamImage:v1"


def _camera_geometry(camera: dict) -> dict:
    return {"type": "Point", "coordinates": [camera["lon"], camera["lat"]]}


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "Storebaelt Webcam Poster Image Publisher v1",
        "description": "Publishes image-reference observations from the public Storebaelt traffic/weather webcam poster images.",
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "Storebaelt Webcam Poster Image Publisher v1",
    "description": (
        "Polls the public Storebaelt webcam poster JPEG endpoints exposed by the embedded "
        "Mediathand player pages and publishes image-reference observations. The live video "
        "player URLs and public Storebaelt webcam page are retained as provenance."
    ),
    "keywords": ["Storebaelt", "Denmark", "traffic", "weather", "webcam", "image reference"],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Storebaelt", "link": {"href": STOREBAELT_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Storebaelt Webcams", "link": {"href": STOREBAELT_WEBCAMS_PAGE, "type": "text/html"}},
    ],
    "contacts": [
        {"role": "operator", "organisationName": STOREBAELT_OPERATOR, "contactInfo": {"onlineResource": {"linkage": STOREBAELT_HOME}}},
        {"role": "publisher", "organisationName": "OS4CSAPI", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}}},
    ],
}


def _system_stub(camera: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": _camera_geometry(camera),
        "properties": {
            "uid": _system_uid(camera),
            "featureType": "sml:PhysicalSystem",
            "name": camera["title"],
            "description": f"Storebaelt public traffic/weather webcam at {camera['locationName']}.",
            "typeOf@link": {"href": "pending", "uid": PROC_UID, "title": "Storebaelt Webcam Poster Image Publisher v1"},
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(camera: dict) -> dict:
    return {
        "type": "PhysicalSystem",
        "id": _system_uid(camera),
        "uniqueId": _system_uid(camera),
        "definition": "sosa:System",
        "name": camera["title"],
        "label": camera["title"],
        "description": (
            f"Public Storebaelt traffic/weather webcam for {camera['locationName']}. "
            "The publisher emits references to the current poster JPEG and preserves the "
            "embedded player URL for live-video context."
        ),
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(camera)},
            {"definition": "http://sensorml.com/ont/swe/property/ProcedureID", "label": "Procedure UID", "value": PROC_UID},
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": camera["id"]},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "System Type", "value": "Traffic/weather webcam"},
            {"definition": "http://sensorml.com/ont/swe/property/DataSource", "label": "Data Source", "value": "Storebaelt webcams"},
            {"definition": "http://sensorml.com/ont/swe/property/Coverage", "label": "Coverage", "value": "Great Belt, Denmark"},
        ],
        "contacts": [
            {"role": "operator", "organisationName": STOREBAELT_OPERATOR, "contactInfo": {"onlineResource": {"linkage": STOREBAELT_HOME}}},
            {"role": "publisher", "organisationName": "OS4CSAPI Project", "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI"}}},
        ],
        "documents": [
            {"role": "http://dbpedia.org/resource/Web_page", "name": "Storebaelt Webcams", "link": {"href": camera["pageUrl"], "type": "text/html"}},
            {"role": "http://dbpedia.org/resource/Web_page", "name": "Embedded Webcam Player", "link": {"href": camera["playerUrl"], "type": "text/html"}},
            {"role": "http://dbpedia.org/resource/Photograph", "name": "Latest Webcam Poster", "link": {"href": camera["posterUrl"], "type": "image/jpeg"}},
        ],
        "characteristics": [
            {
                "name": "camera_source",
                "type": "DataRecord",
                "label": "Camera Source",
                "fields": [
                    {"name": "cameraId", "type": "Text", "label": "Camera ID", "value": camera["id"]},
                    {"name": "siteTitle", "type": "Text", "label": "Site Title", "value": camera["siteTitle"]},
                    {"name": "posterUrl", "type": "Text", "label": "Poster URL", "value": camera["posterUrl"]},
                    {"name": "playerUrl", "type": "Text", "label": "Player URL", "value": camera["playerUrl"]},
                    {"name": "publishIntervalSeconds", "type": "Count", "label": "Default Publish Interval", "value": PUBLISH_INTERVAL_SECONDS},
                ],
            }
        ],
    }


def _datastream_schema(camera: dict) -> dict:
    return {
        "uid": _datastream_uid(camera),
        "outputName": DS_OUTPUT_NAME,
        "name": "Storebaelt Webcam Image Reference",
        "description": f"Image-reference observations for {camera['title']}.",
        "documentation": [
            {"title": "Storebaelt Webcams", "href": camera["pageUrl"], "rel": "about"},
            {"title": "Embedded Player", "href": camera["playerUrl"], "rel": "service"},
            {"title": "Latest Poster JPEG", "href": camera["posterUrl"], "rel": "preview"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "Storebaelt Webcam Image Reference",
                "fields": [
                    {"type": "Text", "name": "cameraId", "label": "Camera ID", "definition": "http://sensorml.com/ont/swe/property/SensorID"},
                    {"type": "Text", "name": "cameraTitle", "label": "Camera Title", "definition": "http://purl.org/dc/elements/1.1/title"},
                    {"type": "Text", "name": "locationName", "label": "Location Name", "definition": "http://purl.org/dc/terms/spatial"},
                    {"type": "Text", "name": "imageUrl", "label": "Image URL", "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text", "name": "latestImageUrl", "label": "Latest Image URL", "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text", "name": "posterUrl", "label": "Poster Image URL", "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text", "name": "thumbUrl", "label": "Thumbnail URL", "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text", "name": "playerUrl", "label": "Player URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                    {"type": "Text", "name": "pageUrl", "label": "Source Page URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                    {"type": "Text", "name": "mediaType", "label": "Media Type", "definition": "http://purl.org/dc/elements/1.1/format"},
                    {"type": "Text", "name": "sourceType", "label": "Source Type", "definition": "http://sensorml.com/ont/swe/property/ProcessingType"},
                    {"type": "Boolean", "name": "live", "label": "Live Source", "definition": "http://sensorml.com/ont/swe/property/Status"},
                    {"type": "Count", "name": "httpStatus", "label": "HTTP Status", "definition": "http://sensorml.com/ont/swe/property/StatusCode"},
                    {"type": "Text", "name": "etag", "label": "HTTP ETag", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "lastModified", "label": "HTTP Last-Modified", "definition": "http://sensorml.com/ont/swe/property/Timestamp"},
                    {"type": "Text", "name": "sourceLastModifiedTime", "label": "Parsed Source Last-Modified Time", "definition": "http://sensorml.com/ont/swe/property/Timestamp"},
                    {"type": "Text", "name": "contentLength", "label": "Content Length", "definition": "http://sensorml.com/ont/swe/property/Size"},
                    {"type": "Text", "name": "imageSha256", "label": "Image SHA-256", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
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
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [11.0, 55.33]},
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "Storebaelt Webcams Demo",
            "description": "Top-level grouping for Storebaelt webcam image-reference resources.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [11.0, 55.33]},
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "Storebaelt Webcams",
            "description": "Grouping deployment for public Storebaelt traffic/weather webcams.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_camera(camera: dict, system_server_id: str, base_url: str) -> dict:
    return {
        "type": "Feature",
        "geometry": _camera_geometry(camera),
        "properties": {
            "uid": _deploy_uid(camera),
            "featureType": "sosa:Deployment",
            "name": camera["title"],
            "description": f"Storebaelt webcam deployment for {camera['locationName']}.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": f"{base_url.rstrip('/')}/systems/{system_server_id}",
                "uid": _system_uid(camera),
                "title": camera["title"],
            },
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool, stats: dict):
    for camera in _load_cameras():
        clean_resource(base_url, auth, "deployments", _deploy_uid(camera), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for camera in _load_cameras():
        clean_resource(base_url, auth, "systems", _system_uid(camera), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False, force_sml: bool = False):
    config = get_config()
    base_url = config["base_url"]
    auth = _auth_header(config["user"], config["password"])
    cameras = _load_cameras()
    stats: dict[str, int] = {}

    print("\n" + "=" * 70)
    print("  Storebaelt Webcams -- Bootstrap")
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

    print("  -- Systems and Datastreams --")
    system_ids: dict[str, str] = {}
    for camera in cameras:
        sys_id = ensure_system(base_url, auth, _system_uid(camera), _system_stub(camera), _system_sml(camera), dry_run=dry_run, stats=stats, force_sml=force_sml)
        system_ids[camera["id"]] = sys_id or "pending"
        ensure_datastream(base_url, auth, sys_id or "pending", DS_OUTPUT_NAME, _datastream_schema(camera), dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(), dry_run=dry_run, stats=stats, force_sml=force_sml)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(), parent_id=root_id, dry_run=dry_run, stats=stats, force_sml=force_sml)
    for camera in cameras:
        sys_id = system_ids.get(camera["id"])
        if not sys_id and not dry_run:
            continue
        ensure_deployment(base_url, auth, _deploy_uid(camera), _deploy_camera(camera, sys_id or "pending", base_url), parent_id=group_id, dry_run=dry_run, stats=stats, force_sml=force_sml)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Storebaelt Webcams resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only, dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
