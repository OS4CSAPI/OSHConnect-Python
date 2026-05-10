#!/usr/bin/env python3
"""
bootstrap_usgs_nims.py -- Register USGS NIMS imagery resources on the OS4CSAPI server.

Adds imagery datastreams to the existing USGS water monitoring station systems
(Pattern A — companion datastream on same station system) and creates a NIMS-specific
deployment tree.

Creates:
  Procedure:
    1. urn:os4csapi:procedure:usgs-nims-imagery:v1

  Datastreams (one per camera, on existing water station systems):
    N. "NIMS Station Image" (outputName: usgsNimsImage) under each station system

  Deployment tree:
    urn:os4csapi:deployment:usgs-nims-demo:v1
    └── urn:os4csapi:deployment:usgs-nims-cameras:v1
        └── urn:os4csapi:deployment:usgs-nims-{nwisId}:v1  (platform@link → existing system)
        ...

Camera list is read from cameras.json (same directory).
Systems must already exist from bootstrap_usgs_water.py.

Usage:
    python -m publishers.usgs_nims.bootstrap_usgs_nims              # create (skip if exists)
    python -m publishers.usgs_nims.bootstrap_usgs_nims --clean      # delete + recreate
    python -m publishers.usgs_nims.bootstrap_usgs_nims --clean-only # delete only
    python -m publishers.usgs_nims.bootstrap_usgs_nims --dry-run    # print what would happen

Requires: Python 3.10+, no external dependencies.
"""

import argparse
import json
import os
import sys

# Add parent dir to path for shared helpers
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config, _auth_header,
    ensure_procedure, ensure_datastream, ensure_deployment,
    find_by_uid, clean_resource, add_bootstrap_args, print_summary,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════

VALID_TIME_START = "2026-01-01T00:00:00Z"

PROC_UID = "urn:os4csapi:procedure:usgs-nims-imagery:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:usgs-nims-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:usgs-nims-cameras:v1"

DS_OUTPUT_NAME = "usgsNimsImage"

# NIMS references
NIMS_API_BASE = "https://api.waterdata.usgs.gov/nims/v0/"
NIMS_S3_BASE = "https://usgs-nims-images.s3.amazonaws.com"
USGS_API_REGISTRATION = "https://api.usgs.gov/"
USGS_WATER_HOME = "https://waterdata.usgs.gov/"
USGS_OGC_API = "https://api.waterdata.usgs.gov/ogcapi/v0/"
USGS_NIMS_CAMERAS = "https://api.waterdata.usgs.gov/nims/v0/cameras"
USGS_NIMS_LIST_FILES = "https://api.waterdata.usgs.gov/nims/v0/listFiles"
USGS_NIMS_DOCS = "https://api.waterdata.usgs.gov/nims/v0/docs"
USGS_NIMS_SITE_DISCOVERY = "https://api.waterdata.usgs.gov/nims/v0/cameras?siteId="
USGS_NIMS_RAWITEM_NOTE = "https://api.waterdata.usgs.gov/nims/v0/listFiles"


def _load_cameras() -> list[dict]:
    """Load camera list from cameras.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "cameras.json")) as f:
        return json.load(f)["cameras"]


def _system_uid(nwis_id: str) -> str:
    """UID for the existing USGS water station system (shared with usgs_water)."""
    return f"urn:os4csapi:system:usgs-water:{nwis_id}:v1"


def _deploy_uid(nwis_id: str) -> str:
    return f"urn:os4csapi:deployment:usgs-nims-{nwis_id}:v1"


def _camera_page_url(cam_id: str) -> str:
    return f"{NIMS_API_BASE}cameras?camId={cam_id}"


def _list_files_url(cam_id: str, limit: int = 5) -> str:
    return f"{NIMS_API_BASE}listFiles?camId={cam_id}&limit={limit}&recent=true"


def _timelapse_url(cam: dict) -> str:
    tl_dir = cam.get("tlDir", "")
    cam_id = cam["camId"]
    return f"{tl_dir}{cam_id}_720.mp4"


def _site_cameras_url(nwis_id: str) -> str:
    return f"{NIMS_API_BASE}cameras?siteId={nwis_id}"


def _list_files_rawitem_url(cam_id: str, limit: int = 5) -> str:
    return f"{NIMS_API_BASE}listFiles?camId={cam_id}&limit={limit}&recent=true&rawItem=true"


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "USGS NIMS Station Imagery v1",
        "description": (
            "Publishes image-reference observations from the USGS National Imagery Management "
            "System (NIMS). The current publisher model reuses existing USGS water monitoring "
            "station systems and attaches one selected imagery datastream per curated camera as "
            "a Pattern A companion datastream. Runtime polls NIMS listFiles, derives image time, "
            "constructs stable S3-hosted URLs for multiple image resolutions, and publishes URLs "
            "and metadata instead of binary image payloads."
        ),
        "keywords": [
            "USGS",
            "NIMS",
            "station imagery",
            "camera discovery",
            "listFiles",
            "image reference",
            "timelapse",
            "shared system",
            "Pattern A",
        ],
        "documentation": [
            {"title": "NIMS v0 Camera Discovery", "href": USGS_NIMS_CAMERAS, "rel": "documentation"},
            {"title": "NIMS v0 Image Listing", "href": USGS_NIMS_LIST_FILES, "rel": "documentation"},
            {"title": "NIMS v0 Swagger Docs", "href": USGS_NIMS_DOCS, "rel": "describedby"},
            {"title": "NIMS Image Bucket (S3)", "href": NIMS_S3_BASE, "rel": "alternate"},
            {"title": "USGS API Registration", "href": USGS_API_REGISTRATION, "rel": "related"},
            {"title": "USGS Water Data Home", "href": USGS_WATER_HOME, "rel": "about"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": "U.S. Geological Survey",
                "website": USGS_WATER_HOME,
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python",
            },
        ],
        "lineage": {
            "source": "U.S. Geological Survey / National Imagery Management System (NIMS)",
            "upstream": (
                "Camera identity and directory metadata come from NIMS cameras responses. "
                "Newest image filenames come from listFiles. Resolution-specific URLs are "
                "constructed from the returned directory paths and filenames."
            ),
            "normalization": (
                "The current runtime uses listFiles string-array mode, parses image time from the "
                "filename pattern, and publishes imageUrl, thumbUrl, smallUrl, filename, mediaType, "
                "and optional timeLapseUrl in the observation result body."
            ),
        },
        "usageConstraints": {
            "apiKeyNote": (
                "A USGS API key is recommended for higher request ceilings. Register at "
                "https://api.usgs.gov."
            ),
            "nimsVersionNote": (
                "NIMS v0 is the active verified endpoint as of 2026-03-11. The package keeps v0 URLs "
                "and does not assume a v1 migration path is live yet."
            ),
            "sharedSystemNote": (
                "This publisher uses Pattern A and reuses existing USGS water station systems. "
                "It does not create NIMS-specific systems."
            ),
            "selectionNote": (
                "The current curated model selects one camera per station system even though some "
                "NIMS sites now expose multiple live cameras."
            ),
            "rawItemNote": (
                "NIMS listFiles also supports rawItem=true responses with timestamp and file-size "
                "fields. The current runtime does not yet use that richer mode."
            ),
            "imageryNote": (
                "NIMS cameras may be daylight-only or 24x7. Refresh intervals vary by camera. "
                "Images may be stale during darkness, outages, or reduced capture windows."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _imagery_datastream_schema(cam: dict) -> dict:
    """SWE DataRecord schema for the NIMS imagery datastream."""
    cam_id = cam["camId"]
    nwis_id = cam["nwisId"]
    station_name = cam.get("stationName", cam.get("camName", nwis_id))
    ingest_period = cam.get("ingestPeriod", "unknown")
    ingest_interval = cam.get("ingestIntervalMin", "unknown")
    timelapse_enabled = cam.get("TL_enabled", False)

    return {
        "uid": f"urn:os4csapi:datastream:usgs-nims:{cam_id}:usgsNimsImage:v1",
        "outputName": DS_OUTPUT_NAME,
        "name": "NIMS Station Image",
        "description": (
            f"Image-reference observations from selected USGS NIMS camera {cam_id} at gaging "
            f"station {nwis_id} ({station_name}). This datastream is a Pattern A companion "
            f"datastream on the shared USGS water station system. Current camera capture mode is "
            f"{ingest_period} with an approximate {ingest_interval}-minute interval. "
            f"Timelapse enabled: {str(timelapse_enabled).lower()}."
        ),
        "documentation": [
            {"title": "NIMS Camera Discovery", "href": _camera_page_url(cam_id), "rel": "documentation"},
            {"title": "NIMS Site Discovery", "href": _site_cameras_url(nwis_id), "rel": "documentation"},
            {"title": "NIMS Image Listing", "href": _list_files_url(cam_id, 5), "rel": "documentation"},
            {"title": "NIMS Raw Item Listing", "href": _list_files_rawitem_url(cam_id, 5), "rel": "documentation"},
            {"title": "NIMS S3 Bucket", "href": NIMS_S3_BASE, "rel": "alternate"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "NIMS Image Reference",
                "description": (
                    "USGS NIMS image-reference metadata and resolution-specific URLs. "
                    "The time field named timestamp is populated from phenomenonTime and "
                    "must not be included inside the result body."
                ),
                "fields": [
                    {
                        "type": "Time",
                        "name": "timestamp",
                        "label": "Image Time",
                        "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime",
                        "referenceTime": "1970-01-01T00:00:00Z",
                        "uom": {"code": "s"},
                    },
                    {
                        "type": "Text",
                        "name": "stationId",
                        "label": "NWIS Site ID",
                        "definition": "http://sensorml.com/ont/swe/property/StationID",
                    },
                    {
                        "type": "Text",
                        "name": "camId",
                        "label": "Camera ID",
                        "definition": "http://sensorml.com/ont/swe/property/SensorID",
                    },
                    {
                        "type": "Text",
                        "name": "imageUrl",
                        "label": "Full-Size Image URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL",
                    },
                    {
                        "type": "Text",
                        "name": "thumbUrl",
                        "label": "Thumbnail Image URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL",
                    },
                    {
                        "type": "Text",
                        "name": "smallUrl",
                        "label": "720px Image URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL",
                    },
                    {
                        "type": "Text",
                        "name": "mediaType",
                        "label": "Media Type",
                        "definition": "http://purl.org/dc/elements/1.1/format",
                    },
                    {
                        "type": "Text",
                        "name": "filename",
                        "label": "Image Filename",
                        "definition": "http://purl.org/dc/elements/1.1/identifier",
                    },
                    {
                        "type": "Text",
                        "name": "timeLapseUrl",
                        "label": "Timelapse Video URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/VideoURL",
                        "optional": True,
                    },
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-100.0, 39.0],
        },
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "USGS NIMS Imagery Demo",
            "description": (
                "Top-level CSAPI deployment grouping for USGS NIMS gaging-station imagery "
                "published by OSHConnect-Python. Imagery datastreams are companion datastreams "
                "attached to existing USGS water monitoring station systems under the Pattern A model."
            ),
            "documentation": [
                {"title": "NIMS Camera Discovery", "href": USGS_NIMS_CAMERAS, "rel": "documentation"},
                {"title": "NIMS Swagger Docs", "href": USGS_NIMS_DOCS, "rel": "describedby"},
                {"title": "NIMS S3 Image Bucket", "href": NIMS_S3_BASE, "rel": "alternate"},
                {"title": "USGS Water Data Home", "href": USGS_WATER_HOME, "rel": "about"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-100.0, 39.0],
        },
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "USGS NIMS Camera Stations",
            "description": (
                "Grouping deployment for the curated set of USGS NIMS camera-equipped gaging "
                "stations. Each child deployment represents one selected camera linked to one "
                "existing USGS water station system."
            ),
            "documentation": [
                {"title": "NIMS Camera Discovery", "href": USGS_NIMS_CAMERAS, "rel": "documentation"},
                {"title": "USGS Water OGC API", "href": USGS_OGC_API, "rel": "related"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_camera(cam: dict, system_server_id: str, base_url: str) -> dict:
    nwis_id = cam["nwisId"]
    cam_id = cam["camId"]
    station_name = cam.get("stationName", cam.get("camName", nwis_id))
    system_href = f"{base_url.rstrip('/')}/systems/{system_server_id}"
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [cam["lon"], cam["lat"]],
        },
        "properties": {
            "uid": _deploy_uid(nwis_id),
            "featureType": "sosa:Deployment",
            "name": f"NIMS Camera {nwis_id}",
            "description": (
                f"CSAPI deployment node for selected NIMS camera {cam_id} at USGS gaging station "
                f"{nwis_id} ({station_name}). This deployment links imagery observations to the "
                "existing shared USGS water station system rather than creating a separate camera system."
            ),
            "externalLinks": [
                {"href": _camera_page_url(cam_id), "title": "NIMS Camera Discovery", "rel": "canonical"},
                {"href": _site_cameras_url(nwis_id), "title": "NIMS Site Discovery", "rel": "related"},
                {"href": _list_files_url(cam_id, 10), "title": "NIMS Recent Images", "rel": "latest-version"},
                {"href": _list_files_rawitem_url(cam_id, 10), "title": "NIMS Recent Images (rawItem)", "rel": "related"},
                {"href": _timelapse_url(cam), "title": "NIMS Timelapse Video", "rel": "alternate"},
            ],
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_href,
                "uid": _system_uid(nwis_id),
                "title": f"USGS {nwis_id}",
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url: str, auth: str, cameras: list[dict],
              *, dry_run: bool = False, stats: dict):
    """Delete all NIMS imagery resources (reverse order).

    NOTE: Does NOT delete the shared water station systems — those belong
    to the water bootstrap. Only deletes NIMS-specific resources:
    deployments and the NIMS procedure. Datastreams on shared systems
    are removed individually.
    """
    # Deployments (leaf → root)
    for cam in reversed(cameras):
        clean_resource(base_url, auth, "deployments", _deploy_uid(cam["nwisId"]),
                       dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID,
                   dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID,
                   dry_run=dry_run, stats=stats)

    # Datastreams on existing systems (find + delete individually)
    for cam in cameras:
        sys_id = find_by_uid(base_url, auth, "systems", _system_uid(cam["nwisId"]))
        if not sys_id:
            continue
        from publishers.bootstrap_helpers import find_datastream, api_delete
        ds = find_datastream(base_url, auth, sys_id, DS_OUTPUT_NAME)
        if ds and ds.get("id"):
            ds_id = ds["id"]
            if dry_run:
                print(f"  [DRY] Would delete datastream {DS_OUTPUT_NAME} (id={ds_id}) "
                      f"on system {cam['nwisId']}")
            else:
                print(f"  DELETE datastream {DS_OUTPUT_NAME} (id={ds_id}) on system {cam['nwisId']}")
                api_delete(base_url, f"datastreams/{ds_id}", auth)
                if stats is not None:
                    stats.setdefault("deleted", 0)
                    stats["deleted"] += 1

    # Procedure
    clean_resource(base_url, auth, "procedures", PROC_UID,
                   dry_run=dry_run, stats=stats)


def bootstrap(*, clean: bool = False, clean_only: bool = False,
              dry_run: bool = False):
    """Main bootstrap entry point."""
    config = get_config()
    base_url = config["base_url"]
    auth = _auth_header(config["user"], config["password"])
    cameras = _load_cameras()

    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  USGS NIMS Imagery -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Cameras:   {len(cameras)} ({', '.join(c['nwisId'] for c in cameras)})")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}")
    print(f"  Pattern:   A (companion datastream on existing water station systems)")
    print()

    # -- Clean --
    if clean or clean_only:
        print("  -- Cleaning NIMS-specific resources --")
        clean_all(base_url, auth, cameras, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    # -- Procedure --
    print("  -- Procedures --")
    proc_id = ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_BODY,
                               dry_run=dry_run, stats=stats)

    # -- Datastreams on existing systems --
    print("  -- Imagery Datastreams (on existing water station systems) --")
    system_ids: dict[str, str] = {}  # nwisId → server ID

    for cam in cameras:
        nwis_id = cam["nwisId"]
        sys_uid = _system_uid(nwis_id)

        # Find existing system from water bootstrap
        sys_id = find_by_uid(base_url, auth, "systems", sys_uid)
        if not sys_id:
            print(f"  [WARN] System {sys_uid} not found — run bootstrap_usgs_water.py first")
            continue

        system_ids[nwis_id] = sys_id

        # Create imagery datastream on existing system
        ensure_datastream(base_url, auth, sys_id, DS_OUTPUT_NAME,
                          _imagery_datastream_schema(cam),
                          dry_run=dry_run, stats=stats)

    # -- Deployment tree --
    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id,
                                 dry_run=dry_run, stats=stats)

    for cam in cameras:
        nwis_id = cam["nwisId"]
        sys_id = system_ids.get(nwis_id)
        if sys_id or dry_run:
            ensure_deployment(base_url, auth, _deploy_uid(nwis_id),
                              _deploy_camera(cam, sys_id or "pending", base_url),
                              parent_id=group_id,
                              dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap USGS NIMS imagery resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()

    bootstrap(
        clean=args.clean,
        clean_only=args.clean_only,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
