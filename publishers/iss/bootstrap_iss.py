#!/usr/bin/env python3
"""
bootstrap_iss.py — Register ISS tracking resources on the server.

Creates CSAPI resources:
  Procedures:
    1. urn:os4csapi:procedure:sgp4-propagation:v1
    2. urn:os4csapi:procedure:orbit-track-generation:v1

  Systems:
    1. urn:os4csapi:system:iss-position-publisher:v1
    2. urn:os4csapi:system:iss-orbittrack-publisher:v1

  Datastreams:
    1. "issPosition" under position system
    2. "issOrbitTrack" under orbit-track system

  Deployment tree:
    urn:os4csapi:deployment:orbital-tracking-demo:v1
    └─ urn:os4csapi:deployment:leo-objects:v1
       └─ urn:os4csapi:deployment:iss-tracking-role:v1
          ├─ urn:os4csapi:deployment:iss-position-feed:v1
          └─ urn:os4csapi:deployment:iss-orbit-track-feed:v1

Usage:
    python -m publishers.iss.bootstrap_iss              # create (skip if exists)
    python -m publishers.iss.bootstrap_iss --dry-run    # print what would happen

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

PROC_SGP4_UID = "urn:os4csapi:procedure:sgp4-propagation:v1"
PROC_ORBIT_UID = "urn:os4csapi:procedure:orbit-track-generation:v1"

SYS_POS_UID = "urn:os4csapi:system:iss-position-publisher:v1"
SYS_TRACK_UID = "urn:os4csapi:system:iss-orbittrack-publisher:v1"

DS_POS_OUTPUT = "issPosition"
DS_TRACK_OUTPUT = "issOrbitTrack"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:orbital-tracking-demo:v1"


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions — Procedures
# ═══════════════════════════════════════════════════════════════════════════

def _procedure_sgp4() -> dict:
    return {
        "type": "Feature",
        "geometry": None,
        "properties": {
            "uid": PROC_SGP4_UID,
            "featureType": "sosa:ObservingProcedure",
            "name": "SGP4 Propagation v1",
            "description": (
                "Derives ISS geodetic position (WGS-84) from NORAD orbital elements "
                "using the Simplified General Perturbations Model 4 (SGP4). "
                "Input: OMM/TLE element set + target UTC epoch. "
                "Output: lat_deg, lon_deg, alt_km, velocity_km_s."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _procedure_orbit() -> dict:
    return {
        "type": "Feature",
        "geometry": None,
        "properties": {
            "uid": PROC_ORBIT_UID,
            "featureType": "sosa:ObservingProcedure",
            "name": "Orbit Track Generation v1",
            "description": (
                "Generates a predicted ground-track product for one full orbital period "
                "(~100 minutes) by propagating SGP4 positions at 60-second intervals."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions — Systems
# ═══════════════════════════════════════════════════════════════════════════

def _system_position() -> dict:
    return {
        "type": "Feature",
        "geometry": None,
        "properties": {
            "uid": SYS_POS_UID,
            "featureType": "sosa:Sensor",
            "name": "ISS Position Publisher",
            "description": (
                "Virtual sensor that computes the International Space Station's "
                "geodetic position using SGP4 propagation from NORAD TLE data."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "procedure@link": {
                "href": PROC_SGP4_UID,
                "title": "SGP4 Propagation v1",
                "type": "application/sml+json",
            },
        },
    }


def _system_orbit_track() -> dict:
    return {
        "type": "Feature",
        "geometry": None,
        "properties": {
            "uid": SYS_TRACK_UID,
            "featureType": "sosa:Sensor",
            "name": "ISS Orbit Track Publisher",
            "description": (
                "Virtual sensor that generates predicted ISS ground-track products "
                "by propagating SGP4 positions at 60-second intervals."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "procedure@link": {
                "href": PROC_ORBIT_UID,
                "title": "Orbit Track Generation v1",
                "type": "application/sml+json",
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions — Datastreams
# ═══════════════════════════════════════════════════════════════════════════

def _datastream_position() -> dict:
    return {
        "uid": "urn:os4csapi:datastream:iss:issPosition:v1",
        "name": "ISS Position (SGP4)",
        "outputName": DS_POS_OUTPUT,
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "ISS Geodetic Position Fix",
                "description": "Real-time ISS position derived from SGP4 propagation of NORAD TLE elements.",
                "fields": [
                    {"type": "Time", "name": "timestamp",
                     "definition": "http://sensorml.com/ont/swe/property/SamplingTime",
                     "label": "Sampling Time",
                     "referenceTime": "1970-01-01T00:00:00Z",
                     "uom": {"code": "s"}},
                    {"type": "Quantity", "name": "lat_deg",
                     "definition": "http://qudt.org/vocab/quantitykind/Latitude",
                     "label": "Latitude", "description": "Geodetic latitude (WGS-84)",
                     "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "lon_deg",
                     "definition": "http://qudt.org/vocab/quantitykind/Longitude",
                     "label": "Longitude", "description": "Geodetic longitude (WGS-84)",
                     "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "alt_km",
                     "definition": "http://qudt.org/vocab/quantitykind/Height",
                     "label": "Altitude", "description": "Altitude above WGS-84 ellipsoid",
                     "uom": {"code": "km"}},
                    {"type": "Quantity", "name": "velocity_km_s",
                     "definition": "http://qudt.org/vocab/quantitykind/Speed",
                     "label": "Orbital Velocity", "description": "ECI velocity magnitude",
                     "uom": {"code": "km/s"}},
                    {"type": "Count", "name": "noradId",
                     "definition": "http://sensorml.com/ont/swe/property/Identifier",
                     "label": "NORAD Catalog Number"},
                    {"type": "Text", "name": "assetName",
                     "definition": "http://sensorml.com/ont/swe/property/ShortName",
                     "label": "Asset Name"},
                    {"type": "Text", "name": "sourceEpoch",
                     "definition": "http://sensorml.com/ont/swe/property/ReferenceTime",
                     "label": "TLE Epoch",
                     "description": "ISO 8601 epoch of the source TLE element set"},
                    {"type": "Quantity", "name": "sourceAgeSec",
                     "definition": "http://qudt.org/vocab/quantitykind/Period",
                     "label": "TLE Age",
                     "description": "Seconds since TLE epoch",
                     "uom": {"code": "s"}},
                    {"type": "Quantity", "name": "posErrorM",
                     "definition": "http://qudt.org/vocab/quantitykind/Length",
                     "label": "Estimated Position Error",
                     "description": "Rough SGP4 position error estimate based on TLE age",
                     "uom": {"code": "m"}},
                    {"type": "Text", "name": "method",
                     "definition": "http://sensorml.com/ont/swe/property/AlgorithmType",
                     "label": "Propagation Method"},
                ],
            },
        },
    }


def _datastream_orbit_track() -> dict:
    return {
        "uid": "urn:os4csapi:datastream:iss:issOrbitTrack:v1",
        "name": "ISS Orbit Ground Track",
        "outputName": DS_TRACK_OUTPUT,
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "ISS Predicted Orbit Ground Track",
                "description": "Predicted ground track for one full orbital period (~100 min) computed via SGP4.",
                "fields": [
                    {"type": "Time", "name": "computedAt",
                     "definition": "http://sensorml.com/ont/swe/property/SamplingTime",
                     "label": "Computation Time",
                     "referenceTime": "1970-01-01T00:00:00Z",
                     "uom": {"code": "s"}},
                    {"type": "Count", "name": "noradId",
                     "definition": "http://sensorml.com/ont/swe/property/Identifier",
                     "label": "NORAD Catalog Number"},
                    {"type": "Text", "name": "assetName",
                     "definition": "http://sensorml.com/ont/swe/property/ShortName",
                     "label": "Asset Name"},
                    {"type": "Quantity", "name": "durationMin",
                     "definition": "http://qudt.org/vocab/quantitykind/Period",
                     "label": "Track Duration",
                     "uom": {"code": "min"}},
                    {"type": "Count", "name": "numPoints",
                     "definition": "http://sensorml.com/ont/swe/property/NumberOfElements",
                     "label": "Number of Track Points"},
                    {"type": "Text", "name": "method",
                     "definition": "http://sensorml.com/ont/swe/property/AlgorithmType",
                     "label": "Propagation Method"},
                    {"type": "Text", "name": "trackPointsJson",
                     "definition": "http://sensorml.com/ont/swe/property/DataPayload",
                     "label": "Track Points (JSON)",
                     "description": (
                         "JSON-encoded array of {timestamp, lat_deg, lon_deg, alt_km} objects "
                         "representing the predicted ground track."
                     )},
                ],
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions — Deployment tree
# ═══════════════════════════════════════════════════════════════════════════

def _deployment_tree() -> dict:
    return {
        "type": "Feature",
        "geometry": None,
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "Orbital Tracking Demo",
            "description": "Top-level deployment context for orbital object tracking demonstrations.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Bootstrap ISS resources on CSAPI server")
    add_bootstrap_args(parser)
    args = parser.parse_args()

    config = get_config()
    base_url = config["base_url"]
    auth = _auth_header(config["user"], config["password"])
    dry_run = args.dry_run
    stats = {"created": 0, "skipped": 0, "deleted": 0, "errors": 0}

    print(f"\n{'='*60}")
    print(f"  ISS Tracking Bootstrap")
    print(f"  Server: {base_url}")
    print(f"  Mode:   {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    # ── Clean if requested ────────────────────────────────────────────
    if getattr(args, "clean", False) or getattr(args, "clean_only", False):
        print("── Cleaning existing resources ──")
        clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, stats=stats)
        clean_resource(base_url, auth, "systems", SYS_POS_UID, stats=stats)
        clean_resource(base_url, auth, "systems", SYS_TRACK_UID, stats=stats)
        clean_resource(base_url, auth, "procedures", PROC_SGP4_UID, stats=stats)
        clean_resource(base_url, auth, "procedures", PROC_ORBIT_UID, stats=stats)
        if getattr(args, "clean_only", False):
            print_summary(stats)
            return

    # ── Procedures ────────────────────────────────────────────────────
    print("── Procedures ──")
    ensure_procedure(base_url, auth, PROC_SGP4_UID, _procedure_sgp4(),
                     dry_run=dry_run, stats=stats)
    ensure_procedure(base_url, auth, PROC_ORBIT_UID, _procedure_orbit(),
                     dry_run=dry_run, stats=stats)

    # ── Systems ───────────────────────────────────────────────────────
    print("\n── Systems ──")
    pos_sys_id = ensure_system(base_url, auth, SYS_POS_UID, _system_position(),
                               dry_run=dry_run, stats=stats)
    track_sys_id = ensure_system(base_url, auth, SYS_TRACK_UID, _system_orbit_track(),
                                  dry_run=dry_run, stats=stats)

    # ── Datastreams ───────────────────────────────────────────────────
    print("\n── Datastreams ──")
    if pos_sys_id:
        ensure_datastream(base_url, auth, pos_sys_id, DS_POS_OUTPUT,
                          _datastream_position(), dry_run=dry_run, stats=stats)
    if track_sys_id:
        ensure_datastream(base_url, auth, track_sys_id, DS_TRACK_OUTPUT,
                          _datastream_orbit_track(), dry_run=dry_run, stats=stats)

    # ── Deployment ────────────────────────────────────────────────────
    print("\n── Deployment ──")
    ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deployment_tree(),
                      dry_run=dry_run, stats=stats)

    # ── Summary ───────────────────────────────────────────────────────
    print_summary(stats)


if __name__ == "__main__":
    main()
