#!/usr/bin/env python3
"""
bootstrap_nws.py — Register NWS weather observation resources on the OS4CSAPI server.

Creates per-station CSAPI resources:
  Procedure:
    1. urn:os4csapi:procedure:nws-surface-observation:v1

  Systems (one per station):
    N. urn:os4csapi:system:nws:{stationId}

  Datastreams (one per station):
    N. "Surface Observation"  under each station system

  Deployment tree:
    urn:os4csapi:deployment:nws-weather-demo:v1
    └─ urn:os4csapi:deployment:nws-az-stations:v1
       ├─ urn:os4csapi:deployment:nws-{stationId}:v1  (platform@link → system)
       ...

Station list is read from stations.json (same directory).

Usage:
    python -m publishers.nws.bootstrap_nws              # create (skip if exists)
    python -m publishers.nws.bootstrap_nws --clean      # delete + recreate
    python -m publishers.nws.bootstrap_nws --clean-only # delete only
    python -m publishers.nws.bootstrap_nws --dry-run    # print what would happen

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

PROC_UID = "urn:os4csapi:procedure:nws-surface-observation:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:nws-weather-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:nws-az-stations:v1"

DS_OUTPUT_NAME = "nwsSurfaceObs"


def _load_stations() -> list[dict]:
    """Load station list from stations.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["nws_stations"]


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:nws:{station_id.lower()}:v1"


def _deploy_uid(station_id: str) -> str:
    return f"urn:os4csapi:deployment:nws-{station_id.lower()}:v1"


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "NWS Surface Observation v1",
        "description": (
            "Ingests real-time surface weather observations from the US National Weather Service "
            "(api.weather.gov). Fetches the latest observation per station, normalises units "
            "to SI (degC, Pa, km/h, m), and publishes as a flat JSON result object. "
            "Source: NOAA / NWS. Update cadence: ~1 hour (station-dependent)."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _system_stub(station: dict, proc_id: str) -> dict:
    """GeoJSON Feature stub for a NWS station system."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"], station.get("elev_m", 0)],
        },
        "properties": {
            "uid": _system_uid(station["id"]),
            "featureType": "sosa:Sensor",
            "name": f"NWS {station['id']} — {station['name']}",
            "description": (
                f"NWS ASOS/AWOS surface observation station {station['id']} "
                f"at {station['name']}. Lat {station['lat']}, Lon {station['lon']}, "
                f"Elev {station.get('elev_m', '?')}m."
            ),
            "typeOf@link": {"href": proc_id, "title": "NWS Surface Observation v1"},
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    """SensorML body for rich system metadata."""
    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station["id"]),
        "uniqueId": _system_uid(station["id"]),
        "label": f"NWS {station['id']} — {station['name']}",
        "description": (
            f"Automated Surface Observing System (ASOS/AWOS) at {station['name']} "
            f"({station['id']}). Reports temperature, dewpoint, wind, pressure, "
            f"visibility, humidity, cloud layers, and present weather conditions."
        ),
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"], station.get("elev_m", 0)],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4979",
        },
    }


def _datastream_schema() -> dict:
    """SWE DataRecord schema for surface observation datastream.

    Format must match CSAPI POST systems/{id}/datastreams spec:
      { name, outputName, schema: { obsFormat, resultSchema: { ... } } }
    """
    return {
        "outputName": DS_OUTPUT_NAME,
        "name": "Surface Observation",
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "NWS Surface Observation",
                "description": "NWS surface weather observation (temperature, wind, pressure, visibility, humidity)",
                "fields": [
                    {"type": "Time",     "name": "timestamp",              "label": "Observation Time",         "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "stationId",             "label": "Station ID",               "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text",     "name": "stationName",           "label": "Station Name",             "definition": "http://sensorml.com/ont/swe/property/StationName"},
                    {"type": "Quantity", "name": "lat_deg",               "label": "Latitude",                 "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude",  "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "lon_deg",               "label": "Longitude",                "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude", "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "elev_m",                "label": "Station Elevation",        "definition": "http://sensorml.com/ont/swe/property/Elevation",         "uom": {"code": "m"}},
                    {"type": "Quantity", "name": "temperature_c",         "label": "Temperature",              "definition": "http://sensorml.com/ont/swe/property/AirTemperature",    "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "dewpoint_c",            "label": "Dewpoint",                 "definition": "http://sensorml.com/ont/swe/property/DewPoint",          "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "humidity_pct",          "label": "Relative Humidity",        "definition": "http://sensorml.com/ont/swe/property/HumidityValue",     "uom": {"code": "%"}},
                    {"type": "Quantity", "name": "wind_speed_kmh",        "label": "Wind Speed",               "definition": "http://sensorml.com/ont/swe/property/WindSpeed",         "uom": {"code": "km/h"}},
                    {"type": "Quantity", "name": "wind_direction_deg",    "label": "Wind Direction",           "definition": "http://sensorml.com/ont/swe/property/WindDirection",     "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "wind_gust_kmh",         "label": "Wind Gust",                "definition": "http://sensorml.com/ont/swe/property/WindGust",          "uom": {"code": "km/h"}, "optional": True},
                    {"type": "Quantity", "name": "barometric_pressure_pa", "label": "Barometric Pressure",    "definition": "http://sensorml.com/ont/swe/property/AtmosphericPressure", "uom": {"code": "Pa"}},
                    {"type": "Quantity", "name": "visibility_m",          "label": "Visibility",               "definition": "http://sensorml.com/ont/swe/property/Visibility",        "uom": {"code": "m"}},
                    {"type": "Text",     "name": "textDescription",       "label": "Conditions",               "definition": "http://sensorml.com/ont/swe/property/WeatherCondition"},
                    {"type": "Text",     "name": "rawMessage",            "label": "Raw METAR",                "definition": "http://sensorml.com/ont/swe/property/RawObservation"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-111.0, 32.5],
        },
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "NWS Weather Demo",
            "description": "Demonstration deployment: NWS surface weather observations for southern Arizona.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-111.0, 32.5],
        },
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "AZ Weather Stations",
            "description": "NWS ASOS/AWOS stations in the southern Arizona region.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _deploy_uid(station["id"]),
            "featureType": "sosa:Deployment",
            "name": f"{station['id']} Station Feed",
            "description": f"NWS station {station['id']} observation feed.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(station["id"]),
                "title": f"NWS {station['id']}",
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url: str, auth: str, stations: list[dict],
              *, dry_run: bool = False, stats: dict):
    """Delete all NWS resources (reverse order)."""
    # Deployments (leaf → root)
    for st in reversed(stations):
        clean_resource(base_url, auth, "deployments", _deploy_uid(st["id"]),
                       dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID,
                   dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID,
                   dry_run=dry_run, stats=stats)

    # Systems (datastreams deleted automatically by server)
    for st in reversed(stations):
        clean_resource(base_url, auth, "systems", _system_uid(st["id"]),
                       dry_run=dry_run, stats=stats)

    # Procedure
    clean_resource(base_url, auth, "procedures", PROC_UID,
                   dry_run=dry_run, stats=stats)


def bootstrap(*, clean: bool = False, clean_only: bool = False, dry_run: bool = False):
    """Main bootstrap entry point."""
    config = get_config()
    base_url = config["base_url"]
    auth = _auth_header(config["user"], config["password"])
    stations = _load_stations()

    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  NWS Weather Observation — Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)} ({', '.join(s['id'] for s in stations)})")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}")
    print()

    # ── Clean ─────────────────────────────────────────────────────────
    if clean or clean_only:
        print("  ── Cleaning existing resources ──")
        clean_all(base_url, auth, stations, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    # ── Procedure ─────────────────────────────────────────────────────
    print("  ── Procedures ──")
    proc_id = ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_BODY,
                               dry_run=dry_run, stats=stats)

    # ── Systems + Datastreams ─────────────────────────────────────────
    print("  ── Systems + Datastreams ──")
    system_ids: dict[str, str] = {}   # stationId → server ID

    for st in stations:
        uid = _system_uid(st["id"])

        # Build stub body — need procedure server ID for typeOf link
        stub = _system_stub(st, proc_id or "pending")
        sml = _system_sml(st)

        sys_id = ensure_system(base_url, auth, uid, stub, sml,
                               dry_run=dry_run, stats=stats)
        system_ids[st["id"]] = sys_id

        if sys_id or dry_run:
            ensure_datastream(base_url, auth, sys_id or "pending", DS_OUTPUT_NAME,
                              _datastream_schema(),
                              dry_run=dry_run, stats=stats)

    # ── Deployment tree ───────────────────────────────────────────────
    print("  ── Deployments ──")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id,
                                 dry_run=dry_run, stats=stats)

    for st in stations:
        sys_id = system_ids.get(st["id"])
        if sys_id or dry_run:
            ensure_deployment(base_url, auth, _deploy_uid(st["id"]),
                              _deploy_station(st, sys_id or "pending"),
                              parent_id=group_id,
                              dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap NWS weather observation resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()

    bootstrap(
        clean=args.clean,
        clean_only=args.clean_only,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
