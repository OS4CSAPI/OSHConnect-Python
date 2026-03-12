#!/usr/bin/env python3
"""
bootstrap_usgs_eq.py — Register USGS Earthquake Feed resources on the OS4CSAPI server.

Creates a single-system "feed adapter" (Pattern C):
  Procedure:
    1. urn:os4csapi:procedure:usgs-eq-feed-normalizer:v1

  System (one feed adapter):
    1. urn:os4csapi:system:usgs-eq-feed:v1

  Datastream (one under the feed system):
    1. "Earthquake Events"  (outputName: earthquakeEvent)

  Deployment tree:
    urn:os4csapi:deployment:seismic-monitoring-demo:v1
    └─ urn:os4csapi:deployment:usgs-eq-feed:v1  (platform@link → system)

This is Pattern C from the Publishers Plan: a single "feed adapter" system that
publishes each earthquake event from the USGS GeoJSON feed as an individual
observation. Deduplication is by (event ID, updated timestamp).

Configuration is read from config.json (same directory).

Usage:
    python -m publishers.usgs_eq.bootstrap_usgs_eq              # create (skip if exists)
    python -m publishers.usgs_eq.bootstrap_usgs_eq --clean      # delete + recreate
    python -m publishers.usgs_eq.bootstrap_usgs_eq --clean-only # delete only
    python -m publishers.usgs_eq.bootstrap_usgs_eq --dry-run    # print what would happen
    python -m publishers.usgs_eq.bootstrap_usgs_eq --force-sml  # re-PUT SensorML on existing

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

PROC_UID = "urn:os4csapi:procedure:usgs-eq-feed-normalizer:v1"
SYSTEM_UID = "urn:os4csapi:system:usgs-eq-feed:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:seismic-monitoring-demo:v1"
DEPLOY_FEED_UID = "urn:os4csapi:deployment:usgs-eq-feed:v1"

DS_OUTPUT_NAME = "earthquakeEvent"

# ── USGS Earthquake Official URLs ────────────────────────────────────────
USGS_EQ_HOME = "https://earthquake.usgs.gov/"
USGS_EQ_FEED_DOC = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php"
USGS_EQ_ABOUT = "https://earthquake.usgs.gov/aboutus/"
USGS_EQ_GLOSSARY = "https://earthquake.usgs.gov/data/comcat/index.php"
USGS_EQ_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

# ── Contact ──────────────────────────────────────────────────────────────
USGS_CONTACT_ORG = "U.S. Geological Survey (USGS)"
USGS_CONTACT_URL = "https://www.usgs.gov/"


def _load_config() -> dict:
    """Load config from config.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "config.json")) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════
#  Resource body builders
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY = {
    "type": "Feature",
    "properties": {
        "uid": PROC_UID,
        "featureType": "sml:SimpleProcess",
        "name": "USGS Earthquake Feed Normalizer",
        "description": (
            "Procedure describing how the OSHConnect-Python USGS Earthquake publisher "
            "normalizes GeoJSON earthquake events from the USGS Earthquake Hazards Program "
            "into individual CSAPI observations. The publisher polls the USGS GeoJSON summary "
            "feed, extracts each earthquake feature, and publishes a normalized observation "
            "with event metadata (magnitude, location, depth, status) to a single CSAPI "
            "datastream. Deduplication uses (event ID, updated timestamp) tuples."
        ),
        "documentation": [
            {"title": "USGS Earthquake Hazards Program", "href": USGS_EQ_HOME, "rel": "about"},
            {"title": "GeoJSON Summary Feed", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
            {"title": "ComCat Data Glossary", "href": USGS_EQ_GLOSSARY, "rel": "describedby"},
        ],
    },
}


def _system_stub(config: dict) -> dict:
    """GeoJSON system stub for the initial POST."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [0.0, 0.0],  # Global coverage — center of world
        },
        "properties": {
            "uid": SYSTEM_UID,
            "featureType": "sml:PhysicalSystem",
            "name": "USGS Earthquake Feed",
            "description": (
                "Feed-adapter system that ingests real-time earthquake events from the "
                "USGS Earthquake Hazards Program GeoJSON summary feed and publishes them as "
                "individual CSAPI observations. Global coverage — each observation carries "
                "its own geographic coordinates. Polls the all_day feed every 60 seconds."
            ),
            "typeOf@link": {
                "href": "pending",
                "uid": PROC_UID,
                "title": "USGS Earthquake Feed Normalizer",
            },
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(config: dict) -> dict:
    """Rich SensorML body for PUT after system creation."""
    return {
        "type": "SimpleProcess",
        "id": SYSTEM_UID,
        "uniqueId": SYSTEM_UID,
        "name": "USGS Earthquake Feed",
        "label": "USGS Earthquake Feed",
        "description": (
            "Feed-adapter system consuming real-time earthquake events from the USGS "
            "Earthquake Hazards Program. Publishes each earthquake as an individual CSAPI "
            "observation with magnitude, location, depth, and event metadata. "
            "Deduplication is by (event ID, updated timestamp) tuple — unchanged events are "
            "skipped, revised events are re-published."
        ),
        "identifiers": [
            {"label": "System UID", "value": SYSTEM_UID},
            {"label": "Procedure UID", "value": PROC_UID},
            {"label": "Short Name", "value": "USGS-EQ-Feed"},
            {"label": "Publisher", "value": "OSHConnect-Python"},
        ],
        "classifiers": [
            {"label": "Intended Application", "value": "Seismic Event Monitoring"},
            {"label": "Sensor Type", "value": "Feed Adapter (not a physical sensor)"},
            {"label": "Data Source", "value": "USGS Earthquake Hazards Program"},
            {"label": "Observation Pattern", "value": "Pattern C: one event per observation"},
            {"label": "Coverage", "value": "Global"},
        ],
        "contacts": [
            {
                "role": "http://sensorml.com/ont/swe/property/Operator",
                "organisationName": USGS_CONTACT_ORG,
                "links": [
                    {"href": USGS_CONTACT_URL, "title": "USGS"},
                ],
            },
            {
                "role": "http://sensorml.com/ont/swe/property/Author",
                "organisationName": "OS4CSAPI Project",
                "links": [
                    {"href": "https://github.com/OS4CSAPI", "title": "OS4CSAPI GitHub"},
                ],
            },
        ],
        "documents": [
            {"name": "USGS Earthquake Hazards Program", "description": "Data source homepage", "link": {"href": USGS_EQ_HOME}},
            {"name": "GeoJSON Summary Feed Documentation", "description": "Feed format and variant documentation", "link": {"href": USGS_EQ_FEED_DOC}},
            {"name": "ComCat Data Glossary", "description": "Parameter definitions and data catalog", "link": {"href": USGS_EQ_GLOSSARY}},
            {"name": "USGS About", "description": "About the U.S. Geological Survey", "link": {"href": USGS_EQ_ABOUT}},
        ],
        "characteristics": [
            {
                "name": "feed_configuration",
                "type": "DataRecord",
                "label": "Feed Configuration",
                "fields": [
                    {"type": "Text", "name": "feed_url", "label": "Feed URL", "value": config.get("feedUrl", USGS_EQ_FEED_URL)},
                    {"type": "Text", "name": "feed_variant", "label": "Feed Variant", "value": config.get("feedVariant", "all_day")},
                    {"type": "Quantity", "name": "polling_interval", "label": "Polling Interval", "uom": {"code": "s"}, "value": config.get("pollingIntervalSeconds", 60)},
                    {"type": "Text", "name": "coverage", "label": "Geographic Coverage", "value": "Global (all earthquakes worldwide)"},
                ],
            },
            {
                "name": "deduplication_config",
                "type": "DataRecord",
                "label": "Deduplication Configuration",
                "fields": [
                    {"type": "Text", "name": "primary_key", "label": "Primary Key", "value": "feature.id (USGS event ID)"},
                    {"type": "Text", "name": "update_field", "label": "Update Field", "value": "feature.properties.updated (epoch ms)"},
                    {"type": "Text", "name": "strategy", "label": "Strategy", "value": "Skip if (id, updated) already published; re-publish on revision"},
                ],
            },
            {
                "name": "magnitude_scale_vocabulary",
                "type": "DataRecord",
                "label": "Magnitude Scale Vocabulary",
                "fields": [
                    {"type": "Text", "name": "ml", "label": "ml", "value": "Local (Richter) magnitude"},
                    {"type": "Text", "name": "mb", "label": "mb", "value": "Body-wave magnitude"},
                    {"type": "Text", "name": "ms", "label": "ms", "value": "Surface-wave magnitude"},
                    {"type": "Text", "name": "mw", "label": "mw", "value": "Moment magnitude"},
                    {"type": "Text", "name": "mww", "label": "mww", "value": "W-phase moment magnitude"},
                    {"type": "Text", "name": "md", "label": "md", "value": "Duration magnitude"},
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
                        "label": "Polling Interval",
                        "uom": {"code": "s"},
                        "value": config.get("pollingIntervalSeconds", 60),
                    },
                    {
                        "type": "Text",
                        "name": "observation_model",
                        "label": "Observation Model",
                        "value": "One earthquake event per CSAPI observation",
                    },
                    {
                        "type": "Text",
                        "name": "deduplication_rule",
                        "label": "Deduplication Rule",
                        "value": "Events with unchanged (id, updated) tuples are skipped; revised events are re-published",
                    },
                    {
                        "type": "Text",
                        "name": "event_types",
                        "label": "Event Types",
                        "value": "earthquake, quarry blast, explosion, ice quake, other",
                    },
                ],
            },
        ],
        "position": {
            "type": "Point",
            "coordinates": [0.0, 0.0],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _datastream_schema() -> dict:
    """SWE DataRecord schema for earthquake event datastream."""
    return {
        "outputName": DS_OUTPUT_NAME,
        "name": "Earthquake Events",
        "description": (
            "Normalized earthquake events from the USGS GeoJSON summary feed. Each "
            "observation represents one seismic event with magnitude, geographic location, "
            "depth, and status metadata. The publisher polls the USGS all_day feed, "
            "deduplicates by (event ID, updated timestamp), and posts one CSAPI observation "
            "per new or revised earthquake."
        ),
        "documentation": [
            {"title": "USGS Earthquake Hazards Program", "href": USGS_EQ_HOME, "rel": "about"},
            {"title": "GeoJSON Summary Feed", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
            {"title": "ComCat Data Glossary", "href": USGS_EQ_GLOSSARY, "rel": "describedby"},
        ],
        "characteristics": [
            {"label": "Observation Model", "value": "One observation per earthquake event"},
            {"label": "Coverage", "value": "Global — all earthquakes worldwide"},
            {"label": "Feed Variant", "value": "all_day (200-400 events per fetch, ~300 KB)"},
            {"label": "Deduplication", "value": "Skip unchanged (id, updated) tuples; re-publish revised events"},
            {"label": "Magnitude Types", "value": "ml, mb, ms, mw, mww, md (reported by magType field)"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "Earthquake Event",
                "description": "Single earthquake event from USGS GeoJSON feed",
                "fields": [
                    {"type": "Text",     "name": "eventId",      "label": "Event ID",         "definition": "http://sensorml.com/ont/swe/property/EventID"},
                    {"type": "Quantity", "name": "magnitude",    "label": "Magnitude",        "definition": "http://qudt.org/vocab/quantitykind/RichterMagnitude", "uom": {"code": "1"}},
                    {"type": "Text",     "name": "magType",      "label": "Magnitude Type",   "definition": "http://sensorml.com/ont/swe/property/MagnitudeType"},
                    {"type": "Text",     "name": "place",        "label": "Place Description", "definition": "http://sensorml.com/ont/swe/property/LocationDescription"},
                    {"type": "Time",     "name": "eventTime",    "label": "Event Time",       "definition": "http://sensorml.com/ont/swe/property/EventTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "ms"}},
                    {"type": "Time",     "name": "updatedTime",  "label": "Updated Time",     "definition": "http://sensorml.com/ont/swe/property/UpdateTime",       "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "ms"}},
                    {"type": "Quantity", "name": "latitude",     "label": "Latitude",         "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude",  "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "longitude",    "label": "Longitude",        "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude", "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "depth_km",     "label": "Depth",            "definition": "http://qudt.org/vocab/quantitykind/Depth",               "uom": {"code": "km"}},
                    {"type": "Text",     "name": "status",       "label": "Review Status",    "definition": "http://sensorml.com/ont/swe/property/QualityStatus"},
                    {"type": "Text",     "name": "eventType",    "label": "Event Type",       "definition": "http://sensorml.com/ont/swe/property/EventType"},
                    {"type": "Text",     "name": "title",        "label": "Title",            "definition": "http://sensorml.com/ont/swe/property/EventTitle"},
                    {"type": "Text",     "name": "detailUrl",    "label": "Detail URL",       "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    """Top-level deployment group for seismic monitoring."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [0.0, 0.0],  # Global coverage
        },
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "Seismic Monitoring Demo Deployment",
            "description": (
                "Top-level CSAPI deployment grouping for the USGS earthquake feed-adapter "
                "publisher. This is a conceptual deployment group for the demo story — "
                "earthquake events are global and not tied to a single physical installation."
            ),
            "documentation": [
                {"title": "USGS Earthquake Hazards Program", "href": USGS_EQ_HOME, "rel": "about"},
                {"title": "GeoJSON Summary Feed", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_feed(system_server_id: str) -> dict:
    """Feed-level deployment node linked to the earthquake feed system."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [0.0, 0.0],  # Global coverage
        },
        "properties": {
            "uid": DEPLOY_FEED_UID,
            "featureType": "sosa:Deployment",
            "name": "USGS Earthquake Feed",
            "description": (
                "Configured USGS earthquake feed-adapter deployment. Polls the all_day "
                "GeoJSON feed every 60 seconds, publishing one observation per earthquake "
                "event. Global coverage — 200-400 events per feed cycle."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": SYSTEM_UID,
                "title": "USGS Earthquake Feed",
            },
            "links": [
                {"rel": "about", "title": "USGS Earthquake Hazards Program", "href": USGS_EQ_HOME},
                {"rel": "documentation", "title": "GeoJSON Feed Docs", "href": USGS_EQ_FEED_DOC},
                {"rel": "describedby", "title": "ComCat Glossary", "href": USGS_EQ_GLOSSARY},
            ],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url, auth, *, dry_run=False, stats):
    """Delete all USGS Earthquake resources (reverse order)."""
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

    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  USGS Earthquake Feed — Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Feed URL:  {config.get('feedUrl', USGS_EQ_FEED_URL)}")
    print(f"  Variant:   {config.get('feedVariant', 'all_day')}")
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
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    ensure_deployment(base_url, auth, DEPLOY_FEED_UID,
                      _deploy_feed(sys_id or "pending"),
                      parent_id=root_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap USGS Earthquake Feed resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only,
              dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
