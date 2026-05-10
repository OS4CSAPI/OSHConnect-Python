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

# ── Enrichment Pack URLs (2026-03-12) ────────────────────────────────────
USGS_EQ_DETAIL_DOC = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson_detail.php"
USGS_EQ_LIFECYCLE = "https://earthquake.usgs.gov/earthquakes/feed/policy.php"
USGS_EQ_EVENT_TERMS = "https://earthquake.usgs.gov/data/comcat/data-eventterms.php"
USGS_EQ_FDSN_EVENT_API = "https://earthquake.usgs.gov/fdsnws/event/1/"

USGS_EQ_FEED_VARIANTS = {
    "all_hour": "All earthquakes, past hour",
    "all_day": "All earthquakes, past day",
    "all_week": "All earthquakes, past week",
    "all_month": "All earthquakes, past month",
    "significant_hour": "Significant earthquakes, past hour",
    "significant_day": "Significant earthquakes, past day",
    "significant_week": "Significant earthquakes, past week",
    "significant_month": "Significant earthquakes, past month",
    "1.0_hour": "Magnitude 1.0+, past hour",
    "2.5_day": "Magnitude 2.5+, past day",
    "4.5_week": "Magnitude 4.5+, past week",
}


def _summary_feed_url(variant: str) -> str:
    return f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{variant}.geojson"


def _detail_url(event_id: str) -> str:
    return f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/{event_id}.geojson"


def _fdsn_query_url(event_id: str) -> str:
    return f"https://earthquake.usgs.gov/fdsnws/event/1/query.geojson?format=geojson&eventid={event_id}"

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
            "Procedure describing how the OSHConnect-Python USGS earthquake publisher "
            "polls an official USGS GeoJSON summary feed, normalizes each feature into "
            "one CSAPI observation, and exposes a per-event detail link for richer "
            "drill-down. The baseline runtime uses the summary feed only; detail-feed "
            "and FDSN resources are documented as selective enrichment companions."
        ),
        "documentation": [
            {"title": "USGS Earthquake Hazards Program", "href": USGS_EQ_HOME, "rel": "about"},
            {"title": "GeoJSON Summary Feed", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
            {"title": "GeoJSON Detail Feed", "href": USGS_EQ_DETAIL_DOC, "rel": "documentation"},
            {"title": "Feed Lifecycle Policy", "href": USGS_EQ_LIFECYCLE, "rel": "policy"},
            {"title": "ComCat Documentation", "href": USGS_EQ_GLOSSARY, "rel": "describedby"},
            {"title": "Event Terms", "href": USGS_EQ_EVENT_TERMS, "rel": "describedby"},
            {"title": "FDSN Event API", "href": USGS_EQ_FDSN_EVENT_API, "rel": "service"},
        ],
        "characteristics": [
            {"label": "Observation Pattern", "value": "Pattern C feed adapter"},
            {"label": "Default Feed Variant", "value": "all_day"},
            {"label": "Variant Strategy", "value": "Feed variant is configurable and should be treated as runtime policy, not a different data model"},
            {"label": "Detail Enrichment Policy", "value": "Optional and selective; not required for every polling cycle"},
        ],
    },
}


def _system_stub(config: dict) -> dict:
    """GeoJSON system stub for the initial POST."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-105.2214, 39.7392],  # USGS NEIC, Golden, Colorado
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
            {"name": "USGS Earthquake Hazards Program", "description": "Program home", "link": {"href": USGS_EQ_HOME}},
            {"name": "GeoJSON Summary Feed Documentation", "description": "Summary feed format and variant documentation", "link": {"href": USGS_EQ_FEED_DOC}},
            {"name": "GeoJSON Detail Feed Documentation", "description": "Detail feed structure and product documentation", "link": {"href": USGS_EQ_DETAIL_DOC}},
            {"name": "Feed Lifecycle Policy", "description": "Production feed availability and deprecation policy", "link": {"href": USGS_EQ_LIFECYCLE}},
            {"name": "ComCat Documentation", "description": "Catalog and product documentation", "link": {"href": USGS_EQ_GLOSSARY}},
            {"name": "Event Terms", "description": "Official field semantics", "link": {"href": USGS_EQ_EVENT_TERMS}},
            {"name": "FDSN Event API", "description": "Official query interface for targeted retrieval and future backfill", "link": {"href": USGS_EQ_FDSN_EVENT_API}},
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
            {
                "name": "feed_surface",
                "type": "DataRecord",
                "label": "Feed Surface",
                "fields": [
                    {"type": "Text", "name": "runtime_surface", "label": "Runtime Surface", "value": "GeoJSON summary feed"},
                    {"type": "Text", "name": "companion_surface", "label": "Companion Surface", "value": "GeoJSON detail feed and FDSN query.geojson"},
                    {"type": "Text", "name": "modeling_note", "label": "Modeling Note", "value": "The system is a global feed adapter and not a physical seismic station"},
                ],
            },
            {
                "name": "feed_lifecycle",
                "type": "DataRecord",
                "label": "Feed Lifecycle",
                "fields": [
                    {"type": "Text", "name": "production_availability", "label": "Production Availability", "value": "Official policy states production feeds remain available for at least six months in production or deprecated form"},
                    {"type": "Text", "name": "deprecation_notice", "label": "Deprecation Notice", "value": "Official policy states at least 30 days notice before deprecation and removal"},
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
                    {
                        "type": "Text",
                        "name": "enrichment_policy",
                        "label": "Enrichment Policy",
                        "value": "Summary feed by default, detail and FDSN only when stronger per-event context is needed",
                    },
                ],
            },
        ],
        "position": {
            "type": "Point",
            "coordinates": [-105.2214, 39.7392],  # USGS NEIC, Golden, Colorado
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _datastream_schema() -> dict:
    """SWE DataRecord schema for earthquake event datastream."""
    return {
        "uid": "urn:os4csapi:datastream:usgs-eq-feed:earthquakeEvent:v1",
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
            {"title": "GeoJSON Summary Feed", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
            {"title": "GeoJSON Detail Feed", "href": USGS_EQ_DETAIL_DOC, "rel": "documentation"},
            {"title": "Feed Lifecycle Policy", "href": USGS_EQ_LIFECYCLE, "rel": "policy"},
            {"title": "Event Terms", "href": USGS_EQ_EVENT_TERMS, "rel": "describedby"},
            {"title": "FDSN Event API", "href": USGS_EQ_FDSN_EVENT_API, "rel": "service"},
        ],
        "characteristics": [
            {"label": "Observation Model", "value": "One observation per earthquake event"},
            {"label": "Default Runtime Surface", "value": "GeoJSON summary feed"},
            {"label": "Selective Enrichment Surface", "value": "GeoJSON detail feed and FDSN query.geojson"},
            {"label": "Coverage", "value": "Global"},
            {"label": "Dedupe", "value": "Use (eventId, updatedTime) to skip unchanged events and republish revisions"},
            {"label": "Omitted But Available Summary Fields", "value": "url, sig, alert, tsunami, net, types, nst, dmin, rms, gap"},
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
            "coordinates": [-105.2214, 39.7392],  # USGS NEIC, Golden, Colorado
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
                {"title": "GeoJSON Summary Feed Docs", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
                {"title": "GeoJSON Detail Feed Docs", "href": USGS_EQ_DETAIL_DOC, "rel": "documentation"},
                {"title": "Feed Lifecycle Policy", "href": USGS_EQ_LIFECYCLE, "rel": "policy"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_feed(system_server_id: str, base_url: str) -> dict:
    """Feed-level deployment node linked to the earthquake feed system."""
    system_href = f"{base_url.rstrip('/')}/systems/{system_server_id}"
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-105.2214, 39.7392],  # USGS NEIC, Golden, Colorado
        },
        "properties": {
            "uid": DEPLOY_FEED_UID,
            "featureType": "sosa:Deployment",
            "name": "USGS Earthquake Feed",
            "description": (
                "Configured USGS earthquake feed-adapter deployment. Polls one official "
                "USGS GeoJSON summary feed variant on a fixed cadence and publishes one "
                "observation per earthquake event. The deployment documents the detail "
                "feed and FDSN event service as optional enrichment companions rather than "
                "baseline polling dependencies."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_href,
                "uid": SYSTEM_UID,
                "title": "USGS Earthquake Feed",
            },
            "links": [
                {"rel": "documentation", "title": "GeoJSON Summary Feed Docs", "href": USGS_EQ_FEED_DOC},
                {"rel": "documentation", "title": "GeoJSON Detail Feed Docs", "href": USGS_EQ_DETAIL_DOC},
                {"rel": "describedby", "title": "Event Terms", "href": USGS_EQ_EVENT_TERMS},
                {"rel": "service", "title": "FDSN Event API", "href": USGS_EQ_FDSN_EVENT_API},
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
                      _deploy_feed(sys_id or "pending", base_url),
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
