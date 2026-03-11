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

# ── Contact ──────────────────────────────────────────────────────────────
OPENSKY_CONTACT_ORG = "The OpenSky Network Association"
OPENSKY_CONTACT_URL = "https://opensky-network.org/"


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
            "Publishes real-time ADS-B aircraft state vectors from the OpenSky Network "
            "REST API. Data includes position, altitude, velocity, heading, vertical rate, "
            "transponder code, and on-ground status for all aircraft visible in a configured "
            "bounding box. Each observation represents one aircraft at one moment in time."
        ),
        "keywords": [
            "ADS-B", "aircraft", "tracking", "OpenSky", "transponder",
            "aviation", "airspace", "surveillance", "state vector",
        ],
        "documentation": [
            {"title": "OpenSky Network", "href": OPENSKY_HOME, "rel": "about"},
            {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
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
            "upstream": f"OpenSky Network REST API at {OPENSKY_API_DOC}",
            "normalization": (
                "Publisher fetches ADS-B state vectors from the OpenSky Network /states/all "
                "endpoint with a geographic bounding box filter. Each state vector array is "
                "unpacked into a flat JSON observation with named fields."
            ),
        },
        "usageConstraints": {
            "sourceProtocol": "HTTPS",
            "sourceFormat": "JSON array of state vector arrays",
            "rateLimitNote": (
                "Anonymous: 400 API credits/day, 10s time resolution. "
                "Authenticated (OAuth2): 4000 credits/day, 5s resolution."
            ),
            "qualityControlNote": (
                "State vectors are derived from ADS-B, MLAT, and FLARM inputs. "
                "Position source is indicated per vector. Coverage depends on receiver "
                "density in the target area."
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
            "name": "OpenSky ADS-B Feed — Southern Arizona",
            "description": (
                f"Feed adapter system that publishes ADS-B aircraft state vectors from the "
                f"OpenSky Network for a bounding box over southern Arizona "
                f"(lat {bbox['lamin']}–{bbox['lamax']}, lon {bbox['lomin']}–{bbox['lomax']}). "
                f"Each observation is one aircraft's state at one moment; the datastream "
                f"contains a continuous flow of multi-aircraft state vectors."
            ),
            "typeOf@link": {"href": "pending", "title": "OpenSky ADS-B Decoder v1"},
            "links": [
                {"rel": "about", "title": "OpenSky Network", "href": OPENSKY_HOME},
                {"rel": "documentation", "title": "REST API Docs", "href": OPENSKY_API_DOC},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(config: dict) -> dict:
    """SensorML body for the OpenSky feed adapter system."""
    bbox = config["bounding_box"]
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2

    return {
        "type": "PhysicalSystem",
        "id": SYSTEM_UID,
        "uniqueId": SYSTEM_UID,
        "definition": "sosa:System",
        "label": "OpenSky ADS-B Feed — Southern Arizona",
        "description": (
            "Feed adapter that publishes aircraft ADS-B state vectors from the OpenSky "
            "Network. Covers southern Arizona airspace — Tucson, Phoenix, and Fort Huachuca. "
            "This is a virtual system (Pattern C: feed adapter) — it does not represent a "
            "single physical sensor but aggregates data from the crowd-sourced OpenSky "
            "receiver network."
        ),
        "keywords": [
            "ADS-B", "OpenSky", "aircraft", "tracking", "airspace",
            "Arizona", "feed adapter", "surveillance",
        ],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName",
             "label": "Short Name", "value": "OpenSky AZ Feed"},
            {"definition": "http://sensorml.com/ont/swe/property/LongName",
             "label": "Long Name", "value": "OpenSky Network ADS-B Feed — Southern Arizona Airspace"},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType",
             "label": "Sensor Type", "value": "ADS-B Feed Adapter (crowd-sourced receiver network)"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
             "label": "Intended Application", "value": "Airspace surveillance; aircraft tracking; situational awareness"},
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
                "description": "The OpenSky Network — a community-based ADS-B receiver network.",
                "link": {"href": OPENSKY_HOME, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "REST API Documentation",
                "description": "OpenSky Network REST API reference for state vectors, flights, and tracks.",
                "link": {"href": OPENSKY_API_DOC, "type": "text/html"},
            },
        ],
        "characteristics": [
            {
                "name": "feed_characteristics",
                "type": "DataRecord",
                "label": "Feed Characteristics",
                "fields": [
                    {"type": "Text", "name": "data_source",
                     "definition": "http://sensorml.com/ont/swe/property/DataSource",
                     "label": "Data Source", "value": "OpenSky Network (crowd-sourced ADS-B)"},
                    {"type": "Text", "name": "coverage_area",
                     "definition": "http://sensorml.com/ont/swe/property/SensorType",
                     "label": "Coverage Area",
                     "value": f"Southern Arizona: lat {bbox['lamin']}-{bbox['lamax']}, lon {bbox['lomin']}-{bbox['lomax']}"},
                ],
            },
        ],
        "capabilities": [
            {
                "name": "publisher_capabilities",
                "type": "DataRecord",
                "label": "Publisher Capabilities",
                "capabilities": [
                    {"type": "Quantity", "name": "update_interval",
                     "definition": "http://qudt.org/vocab/quantitykind/Period",
                     "label": "Publish Interval", "uom": {"code": "s"},
                     "value": config.get("cadence_seconds", 300)},
                    {"type": "Text", "name": "data_source",
                     "definition": "http://sensorml.com/ont/swe/property/DataSource",
                     "label": "Data Source", "value": "OpenSky Network REST API"},
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
        "name": "Aircraft State Vectors",
        "description": (
            "ADS-B state vectors from the OpenSky Network. Each observation represents "
            "one aircraft at one moment in time, with position, altitude, velocity, heading, "
            "and transponder information. Multiple aircraft observations are published per cycle."
        ),
        "documentation": [
            {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
            {"title": "State Vector Fields", "href": "https://openskynetwork.github.io/opensky-api/index.html#state-vectors", "rel": "describedby"},
        ],
        "characteristics": [
            {"label": "Source Format", "value": "JSON array of state vector arrays via OpenSky REST API"},
            {"label": "Nominal Availability", "value": "Continuous; 10s resolution (anonymous)"},
            {"label": "Quality Control", "value": "ADS-B integrity checks by OpenSky; MLAT positions less precise"},
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
                "Top-level CSAPI deployment grouping for aircraft tracking feeds "
                "published by OSHConnect-Python. Currently includes the OpenSky Network "
                "ADS-B feed for southern Arizona airspace."
            ),
            "documentation": [
                {"title": "OpenSky Network", "href": OPENSKY_HOME, "rel": "about"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_feed(config: dict, system_server_id: str) -> dict:
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
            "uid": DEPLOY_FEED_UID,
            "featureType": "sosa:Deployment",
            "name": "OpenSky ADS-B Feed",
            "description": (
                f"OpenSky Network ADS-B feed adapter for southern Arizona airspace "
                f"(lat {bbox['lamin']}–{bbox['lamax']}, lon {bbox['lomin']}–{bbox['lomax']}). "
                f"Publishes aircraft state vectors at {config.get('cadence_seconds', 300)}s cadence."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": SYSTEM_UID,
                "title": "OpenSky ADS-B Feed — Southern Arizona",
            },
            "links": [
                {"rel": "about", "title": "OpenSky Network", "href": OPENSKY_HOME},
                {"rel": "documentation", "title": "REST API", "href": OPENSKY_API_DOC},
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
                   dry_run=dry_run, stats=stats)
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
                      _deploy_feed(config, sys_id or "pending"),
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
