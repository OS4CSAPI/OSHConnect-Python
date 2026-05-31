#!/usr/bin/env python3
"""
bootstrap_opensky.py — Register OpenSky Network ADS-B tracking resources on the OS4CSAPI server.

Creates a single-system "feed adapter" (Pattern C):
  Procedure:
    1. urn:os4csapi:procedure:opensky-adsb-decoder:v1

  System (one feed adapter):
    1. urn:os4csapi:system:opensky-feed:v1

  Datastream (one under the feed system):
    1. "Aircraft State Vectors"  (outputName: adsbState)

  Deployment tree:
    urn:os4csapi:deployment:airspace-tracking-demo:v1
    └─ urn:os4csapi:deployment:opensky-feed:v1  (platform@link → system)

This is Pattern C from the Publishers Plan: a single "feed adapter" system that
publishes state vectors for all aircraft visible in the configured bounding box.
Each observation contains one aircraft's state at one point in time.

Configuration is read from config.json (same directory).

Usage:
    python -m publishers.opensky.bootstrap_opensky              # create (skip if exists)
    python -m publishers.opensky.bootstrap_opensky --clean      # delete + recreate
    python -m publishers.opensky.bootstrap_opensky --clean-only # delete only
    python -m publishers.opensky.bootstrap_opensky --dry-run    # print what would happen
    python -m publishers.opensky.bootstrap_opensky --force-sml  # re-PUT SensorML on existing

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
    ensure_procedure, ensure_system, ensure_datastream, ensure_deployment,
    clean_resource, add_bootstrap_args, print_summary,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════

VALID_TIME_START = "2026-01-01T00:00:00Z"

PROC_UID = "urn:os4csapi:procedure:opensky-adsb-decoder:v1"
SYSTEM_UID = "urn:os4csapi:system:opensky-feed:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:airspace-tracking-demo:v1"
DEPLOY_FEED_UID = "urn:os4csapi:deployment:opensky-feed:v1"

DS_OUTPUT_NAME = "adsbState"

# ── OpenSky Network Official URLs ────────────────────────────────────────
OPENSKY_HOME = "https://opensky-network.org/"
OPENSKY_API_DOC = "https://openskynetwork.github.io/opensky-api/rest.html"
OPENSKY_ABOUT = "https://opensky-network.org/about/about-us"
OPENSKY_STATE_VECTORS_DOC = "https://openskynetwork.github.io/opensky-api/index.html#state-vectors"
OPENSKY_AUTH_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
OPENSKY_ADSB_ANTENNA_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/6/68/Homemade_1090_MHz_ADS-B_dipole_antenna.jpg"
OPENSKY_ADSB_ANTENNA_SOURCE = "https://commons.wikimedia.org/wiki/File:Homemade_1090_MHz_ADS-B_dipole_antenna.jpg"
OPENSKY_ADSB_ANTENNA_LICENSE = "https://creativecommons.org/licenses/by-sa/3.0/"

# ── Contact ──────────────────────────────────────────────────────────────
OPENSKY_CONTACT_ORG = "The OpenSky Network Association"
OPENSKY_CONTACT_URL = "https://opensky-network.org/"


# ── Enrichment helpers (from metadata_enrichment_pack) ───────────────────

def _bbox_label(config: dict) -> str:
    bbox = config["bounding_box"]
    return (
        f"lat {bbox['lamin']}-{bbox['lamax']}, "
        f"lon {bbox['lomin']}-{bbox['lomax']}"
    )

def _daily_budget_note(config: dict) -> str:
    bbox = config["bounding_box"]
    cadence = int(config.get("cadence_seconds", 300))
    req_per_day = int(86400 / cadence) if cadence > 0 else 0
    credit_cost = bbox.get("credit_cost_per_request", 1)
    total = req_per_day * credit_cost
    return (
        f"{req_per_day} requests/day at {credit_cost} credit(s)/request "
        f"for an estimated {total} credits/day."
    )

def _position_source_summary() -> str:
    return "ADS-B, ASTERIX, MLAT, FLARM"


def _load_config() -> dict:
    """Load config from config.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "config.json")) as f:
        return json.load(f)["opensky"]


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "OpenSky ADS-B Decoder v1",
        "description": (
            "Publishes aircraft state vectors from the OpenSky Network REST API using a "
            "configured geographic bounding box. Each upstream state vector becomes one "
            "CSAPI observation for one aircraft at one observation timestamp. The current "
            "publisher polls the REST API at a configured cadence, normalizes the array-based "
            "OpenSky payload into named fields, and skips repeated aircraft records whose "
            "observation timestamps have not changed."
        ),
        "keywords": [
            "ADS-B",
            "aircraft",
            "tracking",
            "OpenSky",
            "transponder",
            "airspace",
            "state vector",
            "feed adapter",
            "Pattern C",
            "southern Arizona",
        ],
        "documentation": [
            {"title": "OpenSky Network", "href": OPENSKY_HOME, "rel": "about"},
            {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
            {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
            {"title": "About OpenSky", "href": OPENSKY_ABOUT, "rel": "about"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": OPENSKY_CONTACT_ORG,
                "website": OPENSKY_CONTACT_URL,
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python",
            },
        ],
        "lineage": {
            "source": OPENSKY_CONTACT_ORG,
            "upstream": "OpenSky REST API /states/all endpoint filtered to the southern Arizona demo window",
            "normalization": (
                "Publisher fetches array-based state vectors, expands each array into named "
                "observation result fields, maps integer position-source codes to readable labels, "
                "and emits one observation per aircraft state snapshot."
            ),
        },
        "usageConstraints": {
            "sourceProtocol": "HTTPS",
            "sourceFormat": "JSON object with top-level `time` and `states[][]` array payload",
            "authModeNote": "Current demo configuration uses anonymous access. OAuth2-supported access is available for higher credit budgets.",
            "rateLimitNote": "At the current demo cadence (300s) and current 12 sq deg window, the feed consumes about 288 credits/day.",
            "coverageNote": "Current demo window is southern Arizona: lat 31.0-34.0, lon -113.0--109.0 (12 sq deg).",
            "qualityControlNote": (
                "Position source varies by aircraft record and may reflect ADS-B, ASTERIX, MLAT, "
                "or FLARM provenance."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _system_stub(config: dict) -> dict:
    """GeoJSON Feature stub for the OpenSky feed adapter system."""
    bbox = config["bounding_box"]
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
        },
        "properties": {
            "uid": SYSTEM_UID,
            "featureType": "sosa:Sensor",
            "name": "OpenSky ADS-B Feed - Southern Arizona",
            "description": (
                "Feed-adapter system for OpenSky aircraft surveillance over southern Arizona. "
                "The system represents the configured OpenSky query window rather than any single "
                "physical sensor. It polls the OpenSky REST API, receives many aircraft state vectors "
                "per cycle, and republishes each aircraft state as a CSAPI observation."
            ),
            "typeOf@link": {"href": "pending", "title": "OpenSky ADS-B Decoder v1"},
            "keywords": [
                "OpenSky",
                "ADS-B",
                "airspace tracking",
                "feed adapter",
                "southern Arizona",
            ],
            "links": [
                {"rel": "about", "title": "OpenSky Network", "href": OPENSKY_HOME},
                {"rel": "documentation", "title": "REST API Docs", "href": OPENSKY_API_DOC},
                {"rel": "describedby", "title": "State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC},
                {"rel": "about", "title": "About OpenSky", "href": OPENSKY_ABOUT},
            ],
            "authProfile": {
                "mode": config.get("auth", {}).get("mode", "anonymous"),
                "tokenEndpoint": config.get("auth", {}).get("oauth2_token_url", OPENSKY_AUTH_TOKEN_URL),
                "note": config.get("auth", {}).get("note", ""),
            },
            "coverageProfile": {
                "label": config.get("description", "OpenSky configured coverage window"),
                "bbox": _bbox_label(config),
                "area_sq_deg": bbox.get("area_sq_deg", 0),
                "cadence_seconds": config.get("cadence_seconds", 300),
                "credit_budget_note": _daily_budget_note(config),
            },
            "image": {
                "href": OPENSKY_ADSB_ANTENNA_IMAGE,
                "title": "Representative 1090 MHz ADS-B antenna photograph",
            },
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(config: dict) -> dict:
    """SensorML body for the OpenSky feed adapter system."""
    bbox = config["bounding_box"]
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2
    auth_cfg = config.get("auth", {})

    return {
        "type": "PhysicalSystem",
        "id": SYSTEM_UID,
        "uniqueId": SYSTEM_UID,
        "definition": "sosa:System",
        "label": "OpenSky ADS-B Feed - Southern Arizona",
        "description": (
            "Feed-adapter system representing OpenSky aircraft tracking over southern Arizona. "
            "This system is not a single aircraft sensor. It is a configured API-backed collection "
            "point for many aircraft state vectors retrieved from the OpenSky Network and republished "
            "as individual CSAPI observations."
        ),
        "keywords": [
            "ADS-B",
            "OpenSky",
            "aircraft",
            "tracking",
            "airspace",
            "southern Arizona",
            "feed adapter",
            "state vector",
            auth_cfg.get("mode", "anonymous"),
        ],
        "identifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "Short Name",
                "value": "OpenSky AZ Feed",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/LongName",
                "label": "Long Name",
                "value": "OpenSky Network ADS-B Feed - Southern Arizona Airspace",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/UniqueID",
                "label": "OS4CSAPI UID",
                "value": SYSTEM_UID,
            },
        ],
        "classifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/SensorType",
                "label": "System Type",
                "value": "ADS-B feed adapter (crowd-sourced receiver network)",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
                "label": "Intended Application",
                "value": "Airspace surveillance; aircraft tracking; situational awareness",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/SystemRole",
                "label": "Bootstrap Pattern",
                "value": "Pattern C feed adapter",
            },
        ],
        "contacts": [
            {
                "role": "operator",
                "organisationName": OPENSKY_CONTACT_ORG,
                "contactInfo": {
                    "onlineResource": {"linkage": OPENSKY_HOME},
                },
            },
            {
                "role": "publisher",
                "organisationName": "OS4CSAPI",
                "contactInfo": {
                    "onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"},
                },
            },
        ],
        "documents": [
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "OpenSky Network",
                "description": "Primary landing page for the OpenSky Network.",
                "link": {"href": OPENSKY_HOME, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "OpenSky REST API",
                "description": "REST API reference for states, flights, and tracks.",
                "link": {"href": OPENSKY_API_DOC, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "OpenSky State Vector Fields",
                "description": "Field-level reference for the state vector payload normalized by the publisher.",
                "link": {"href": OPENSKY_STATE_VECTORS_DOC, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "About OpenSky",
                "description": "Operator/about page for the OpenSky Network Association.",
                "link": {"href": OPENSKY_ABOUT, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Photograph",
                "name": "Representative 1090 MHz ADS-B Antenna Photograph",
                "description": (
                    "Photograph of real 1090 MHz ADS-B antenna hardware used as the representative "
                    "source image for the OpenSky ADS-B feed adapter. The OpenSky resource is a "
                    "crowd-sourced receiver-network feed rather than a single station. "
                    "Photo: Happy-marmotte, CC BY-SA 3.0, via Wikimedia Commons."
                ),
                "link": {"href": OPENSKY_ADSB_ANTENNA_IMAGE, "type": "image/jpeg"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Representative ADS-B Antenna Photo Source",
                "description": "Wikimedia Commons source page for the ADS-B antenna photograph.",
                "link": {"href": OPENSKY_ADSB_ANTENNA_SOURCE, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Representative ADS-B Antenna Photo License",
                "description": "Creative Commons Attribution-ShareAlike 3.0 license for the ADS-B antenna photograph.",
                "link": {"href": OPENSKY_ADSB_ANTENNA_LICENSE, "type": "text/html"},
            },
        ],
        "characteristics": [
            {
                "name": "coverage_profile",
                "type": "DataRecord",
                "label": "Coverage Profile",
                "fields": [
                    {"type": "Text", "name": "coverage_label", "label": "Coverage Label", "value": config.get("description", "Configured OpenSky coverage window")},
                    {"type": "Text", "name": "bounding_box", "label": "Bounding Box", "value": _bbox_label(config)},
                    {"type": "Count", "name": "area_sq_deg", "label": "Area (sq deg)", "value": bbox.get("area_sq_deg", 0)},
                ],
            },
            {
                "name": "access_profile",
                "type": "DataRecord",
                "label": "Access Profile",
                "fields": [
                    {"type": "Text", "name": "auth_mode", "label": "Auth Mode", "value": auth_cfg.get("mode", "anonymous")},
                    {"type": "Quantity", "name": "publish_interval", "label": "Publish Interval", "uom": {"code": "s"}, "value": config.get("cadence_seconds", 300)},
                    {"type": "Count", "name": "credit_cost_per_request", "label": "Credit Cost Per Request", "value": bbox.get("credit_cost_per_request", 1)},
                    {"type": "Text", "name": "daily_budget_note", "label": "Daily Budget Note", "value": _daily_budget_note(config)},
                ],
            },
            {
                "name": "position_source_vocabulary",
                "type": "DataRecord",
                "label": "Position Source Vocabulary",
                "fields": [
                    {"type": "Text", "name": "source_0", "label": "Source 0", "value": "ADS-B"},
                    {"type": "Text", "name": "source_1", "label": "Source 1", "value": "ASTERIX"},
                    {"type": "Text", "name": "source_2", "label": "Source 2", "value": "MLAT"},
                    {"type": "Text", "name": "source_3", "label": "Source 3", "value": "FLARM"},
                ],
            },
        ],
        "capabilities": [
            {
                "name": "publisher_capabilities",
                "type": "DataRecord",
                "label": "Publisher Capabilities",
                "capabilities": [
                    {
                        "type": "Quantity",
                        "name": "update_interval",
                        "definition": "http://qudt.org/vocab/quantitykind/Period",
                        "label": "Publish Interval",
                        "uom": {"code": "s"},
                        "value": config.get("cadence_seconds", 300),
                    },
                    {
                        "type": "Text",
                        "name": "observation_model",
                        "label": "Observation Model",
                        "value": "One aircraft state vector per CSAPI observation",
                    },
                    {
                        "type": "Text",
                        "name": "deduplication_rule",
                        "label": "Deduplication Rule",
                        "value": "Repeated aircraft reports with unchanged timestamps are skipped",
                    },
                    {
                        "type": "Text",
                        "name": "position_sources",
                        "label": "Position Sources",
                        "value": _position_source_summary(),
                    },
                ],
            },
        ],
        "position": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _datastream_schema() -> dict:
    """SWE DataRecord schema for ADS-B state vector datastream."""
    return {
        "outputName": DS_OUTPUT_NAME,
        "uid": "urn:os4csapi:datastream:opensky-feed:adsbState:v1",
        "name": "Aircraft State Vectors",
        "description": (
            "Normalized OpenSky aircraft state vectors. Each observation represents one aircraft "
            "inside the configured bounding box at one upstream observation timestamp. The publisher "
            "polls the OpenSky REST API, expands the array-based payload into named fields, and posts "
            "one CSAPI observation per aircraft record."
        ),
        "documentation": [
            {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
            {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
            {"title": "About OpenSky", "href": OPENSKY_ABOUT, "rel": "about"},
        ],
        "characteristics": [
            {"label": "Observation Model", "value": "One observation per aircraft per cycle"},
            {"label": "Coverage Filter", "value": "Bounding-box filter applied at the source API"},
            {"label": "Null Handling", "value": "Nullable numeric values are normalized to JSON-safe NaN strings by the current publisher"},
            {"label": "Position Source Vocabulary", "value": _position_source_summary()},
            {"label": "Deduplication", "value": "Repeated aircraft states with unchanged timestamps are skipped"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "Aircraft State Vector",
                "description": "Single aircraft ADS-B state vector from OpenSky Network",
                "fields": [
                    {"type": "Time",     "name": "timestamp",        "label": "Position Time",        "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "icao24",           "label": "ICAO 24-bit Address",  "definition": "http://sensorml.com/ont/swe/property/TransponderID"},
                    {"type": "Text",     "name": "callsign",         "label": "Callsign",             "definition": "http://sensorml.com/ont/swe/property/Callsign"},
                    {"type": "Text",     "name": "origin_country",   "label": "Origin Country",       "definition": "http://sensorml.com/ont/swe/property/Country"},
                    {"type": "Quantity", "name": "lat_deg",          "label": "Latitude",             "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude",    "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "lon_deg",          "label": "Longitude",            "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude",   "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "baro_altitude_m",  "label": "Barometric Altitude",  "definition": "http://sensorml.com/ont/swe/property/BarometricAltitude",  "uom": {"code": "m"}},
                    {"type": "Quantity", "name": "geo_altitude_m",   "label": "Geometric Altitude",   "definition": "http://sensorml.com/ont/swe/property/GeometricAltitude",   "uom": {"code": "m"}},
                    {"type": "Quantity", "name": "velocity_ms",      "label": "Ground Speed",         "definition": "http://sensorml.com/ont/swe/property/GroundSpeed",         "uom": {"code": "m/s"}},
                    {"type": "Quantity", "name": "true_track_deg",   "label": "True Track",           "definition": "http://sensorml.com/ont/swe/property/TrueTrack",           "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "vertical_rate_ms", "label": "Vertical Rate",        "definition": "http://sensorml.com/ont/swe/property/VerticalRate",        "uom": {"code": "m/s"}},
                    {"type": "Text",     "name": "on_ground",        "label": "On Ground",            "definition": "http://sensorml.com/ont/swe/property/OnGroundStatus"},
                    {"type": "Text",     "name": "squawk",           "label": "Squawk Code",          "definition": "http://sensorml.com/ont/swe/property/TransponderCode"},
                    {"type": "Text",     "name": "position_source",  "label": "Position Source",      "definition": "http://sensorml.com/ont/swe/property/PositionSource"},
                ],
            },
        },
    }


def _deploy_root(config: dict) -> dict:
    bbox = config["bounding_box"]
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
        },
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "Airspace Tracking Demo Deployment",
            "description": (
                "Top-level CSAPI deployment grouping for feed-adapter aircraft tracking resources "
                "published by OSHConnect-Python. This is a conceptual deployment group for the demo "
                "story, not a single physical field installation."
            ),
            "documentation": [
                {"title": "OpenSky Network", "href": OPENSKY_HOME, "rel": "about"},
                {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
                {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_feed(config: dict, system_server_id: str, base_url: str) -> dict:
    bbox = config["bounding_box"]
    system_href = f"{base_url.rstrip('/')}/systems/{system_server_id}"
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
        },
        "properties": {
            "uid": DEPLOY_FEED_UID,
            "featureType": "sosa:Deployment",
            "name": "OpenSky ADS-B Feed",
            "description": (
                f"Configured OpenSky feed-adapter deployment for {_bbox_label(config)}. "
                f"Publishes one observation per aircraft state at {config.get('cadence_seconds', 300)}s cadence. "
                f"Current auth mode: {config.get('auth', {}).get('mode', 'anonymous')}."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_href,
                "uid": SYSTEM_UID,
                "title": "OpenSky ADS-B Feed - Southern Arizona",
            },
            "links": [
                {"rel": "about", "title": "OpenSky Network", "href": OPENSKY_HOME},
                {"rel": "documentation", "title": "REST API", "href": OPENSKY_API_DOC},
                {"rel": "describedby", "title": "State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC},
            ],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url, auth, *, dry_run=False, stats):
    """Delete all OpenSky resources (reverse order)."""
    clean_resource(base_url, auth, "deployments", DEPLOY_FEED_UID,
                   dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID,
                   dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "systems", SYSTEM_UID,
                   dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID,
                   dry_run=dry_run, stats=stats)


def bootstrap(*, clean=False, clean_only=False, dry_run=False, force_sml=False):
    """Main bootstrap entry point."""
    server_config = get_config()
    base_url = server_config["base_url"]
    auth = _auth_header(server_config["user"], server_config["password"])
    config = _load_config()

    bbox = config["bounding_box"]
    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  OpenSky Network ADS-B Feed — Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Bbox:      lat {bbox['lamin']}–{bbox['lamax']}, lon {bbox['lomin']}–{bbox['lomax']}")
    print(f"  Pattern:   C (feed adapter: single system, single datastream)")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}")
    print()

    if clean or clean_only:
        print("  ── Cleaning existing resources ──")
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    print("  ── Procedure ──")
    proc_id = ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_BODY,
                               dry_run=dry_run, stats=stats)

    print("  ── System + Datastream ──")
    stub = _system_stub(config)
    # Link typeOf to the actual procedure ID
    stub["properties"]["typeOf@link"]["href"] = proc_id or "pending"
    sml = _system_sml(config)

    sys_id = ensure_system(base_url, auth, SYSTEM_UID, stub, sml,
                           dry_run=dry_run, stats=stats, force_sml=force_sml)

    if sys_id or dry_run:
        ensure_datastream(base_url, auth, sys_id or "pending", DS_OUTPUT_NAME,
                          _datastream_schema(), dry_run=dry_run, stats=stats)

    print("  ── Deployments ──")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(config),
                                dry_run=dry_run, stats=stats)
    ensure_deployment(base_url, auth, DEPLOY_FEED_UID,
                      _deploy_feed(config, sys_id or "pending", base_url),
                      parent_id=root_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap OpenSky Network ADS-B resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only,
              dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
