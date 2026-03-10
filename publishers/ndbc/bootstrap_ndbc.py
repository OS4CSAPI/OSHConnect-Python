#!/usr/bin/env python3
"""
bootstrap_ndbc.py — Register NOAA NDBC buoy observation resources on the OS4CSAPI server.

Creates per-buoy CSAPI resources:
  Procedure:
    1. urn:os4csapi:procedure:ndbc-buoy-observation:v1

  Systems (one per buoy):
    N. urn:os4csapi:system:ndbc:{stationId}:v1

  Datastreams (one per buoy):
    N. "Buoy Observation"  under each station system

  Deployment tree:
    urn:os4csapi:deployment:ndbc-buoy-demo:v1
    └─ urn:os4csapi:deployment:ndbc-buoys:v1
       ├─ urn:os4csapi:deployment:ndbc-{stationId}:v1  (platform@link → system)
       ...

Station list is read from stations.json (same directory).

Usage:
    python -m publishers.ndbc.bootstrap_ndbc              # create (skip if exists)
    python -m publishers.ndbc.bootstrap_ndbc --clean      # delete + recreate
    python -m publishers.ndbc.bootstrap_ndbc --clean-only # delete only
    python -m publishers.ndbc.bootstrap_ndbc --dry-run    # print what would happen

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

PROC_UID = "urn:os4csapi:procedure:ndbc-buoy-observation:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:ndbc-buoy-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:ndbc-buoys:v1"

DS_OUTPUT_NAME = "ndbcBuoyObs"


def _load_stations() -> list[dict]:
    """Load buoy list from stations.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["ndbc_buoys"]


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:ndbc:{station_id}:v1"


def _deploy_uid(station_id: str) -> str:
    return f"urn:os4csapi:deployment:ndbc-{station_id}:v1"


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "NDBC Buoy Observation v1",
        "description": (
            "Ingests real-time marine meteorological observations from NOAA's "
            "National Data Buoy Center (NDBC). Fetches the latest observation per buoy "
            "from realtime2 text feeds, parses fixed-width fields, and publishes as a "
            "flat JSON result object. Source: NOAA / NDBC. "
            "Update cadence: ~10 min (buoy-dependent, publisher polls hourly)."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _system_stub(station: dict, proc_id: str) -> dict:
    """GeoJSON Feature stub for a NDBC buoy system."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _system_uid(station["id"]),
            "featureType": "sosa:Sensor",
            "name": f"NDBC {station['id']} — {station['name']}",
            "description": (
                f"NOAA NDBC buoy station {station['id']} "
                f"at {station['name']}. Lat {station['lat']}, Lon {station['lon']}, "
                f"Water depth {station.get('water_depth_m', '?')}m."
            ),
            "typeOf@link": {"href": proc_id, "title": "NDBC Buoy Observation v1"},
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    """SensorML body for rich system metadata."""
    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station["id"]),
        "uniqueId": _system_uid(station["id"]),
        "label": f"NDBC {station['id']} — {station['name']}",
        "description": (
            f"NOAA National Data Buoy Center station {station['id']} at "
            f"{station['name']}. Reports wind speed/direction/gust, wave height/"
            f"period/direction, air temperature, water temperature, barometric "
            f"pressure, dewpoint, and visibility."
        ),
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _datastream_schema() -> dict:
    """SWE DataRecord schema for buoy observation datastream.

    NDBC fields (SI units, already in source data):
      WDIR  - Wind direction (degT)
      WSPD  - Wind speed (m/s)
      GST   - Wind gust (m/s)
      WVHT  - Significant wave height (m)
      DPD   - Dominant wave period (s)
      APD   - Average wave period (s)
      MWD   - Mean wave direction (degT)
      PRES  - Sea level pressure (hPa)
      ATMP  - Air temperature (degC)
      WTMP  - Water temperature (degC)
      DEWP  - Dewpoint temperature (degC)
      VIS   - Station visibility (nmi)
      PTDY  - Pressure tendency (hPa)
      TIDE  - Water level (ft)
    """
    return {
        "outputName": DS_OUTPUT_NAME,
        "name": "Buoy Observation",
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "NDBC Buoy Observation",
                "description": "NDBC marine buoy observation (wind, waves, temperature, pressure)",
                "fields": [
                    {"type": "Time",     "name": "timestamp",              "label": "Observation Time",         "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "stationId",             "label": "Station ID",               "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Quantity", "name": "lat_deg",               "label": "Latitude",                 "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude",  "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "lon_deg",               "label": "Longitude",                "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude", "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "wind_direction_deg",    "label": "Wind Direction",           "definition": "http://sensorml.com/ont/swe/property/WindDirection",     "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "wind_speed_ms",         "label": "Wind Speed",               "definition": "http://sensorml.com/ont/swe/property/WindSpeed",         "uom": {"code": "m/s"}},
                    {"type": "Quantity", "name": "wind_gust_ms",          "label": "Wind Gust",                "definition": "http://sensorml.com/ont/swe/property/WindGust",          "uom": {"code": "m/s"}, "optional": True},
                    {"type": "Quantity", "name": "wave_height_m",         "label": "Significant Wave Height",  "definition": "http://sensorml.com/ont/swe/property/WaveHeight",        "uom": {"code": "m"},   "optional": True},
                    {"type": "Quantity", "name": "dominant_wave_period_s", "label": "Dominant Wave Period",    "definition": "http://sensorml.com/ont/swe/property/WavePeriod",        "uom": {"code": "s"},   "optional": True},
                    {"type": "Quantity", "name": "avg_wave_period_s",     "label": "Average Wave Period",      "definition": "http://sensorml.com/ont/swe/property/WavePeriod",        "uom": {"code": "s"},   "optional": True},
                    {"type": "Quantity", "name": "mean_wave_direction_deg", "label": "Mean Wave Direction",    "definition": "http://sensorml.com/ont/swe/property/WaveDirection",     "uom": {"code": "deg"}, "optional": True},
                    {"type": "Quantity", "name": "pressure_hpa",          "label": "Sea Level Pressure",       "definition": "http://sensorml.com/ont/swe/property/AtmosphericPressure", "uom": {"code": "hPa"}},
                    {"type": "Quantity", "name": "air_temp_c",            "label": "Air Temperature",          "definition": "http://sensorml.com/ont/swe/property/AirTemperature",    "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "water_temp_c",          "label": "Water Temperature",        "definition": "http://sensorml.com/ont/swe/property/WaterTemperature",  "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "dewpoint_c",            "label": "Dewpoint",                 "definition": "http://sensorml.com/ont/swe/property/DewPoint",          "uom": {"code": "Cel"}, "optional": True},
                    {"type": "Quantity", "name": "visibility_nmi",        "label": "Visibility",               "definition": "http://sensorml.com/ont/swe/property/Visibility",        "uom": {"code": "[nmi_i]"}, "optional": True},
                    {"type": "Quantity", "name": "pressure_tendency_hpa", "label": "Pressure Tendency",        "definition": "http://sensorml.com/ont/swe/property/PressureTendency",  "uom": {"code": "hPa"}, "optional": True},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-90.0, 30.0],
        },
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "NDBC Buoy Demo",
            "description": "Demonstration deployment: NOAA NDBC marine buoy observations across US coastal waters.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-90.0, 30.0],
        },
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "NDBC Buoy Stations",
            "description": "NOAA National Data Buoy Center marine observation buoys along US coastlines.",
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
            "name": f"Buoy {station['id']} Feed",
            "description": f"NDBC buoy {station['id']} ({station['name']}) observation feed.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(station["id"]),
                "title": f"NDBC {station['id']}",
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url: str, auth: str, stations: list[dict],
              *, dry_run: bool = False, stats: dict):
    """Delete all NDBC resources (reverse order)."""
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
    print("  NDBC Buoy Observation — Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Buoys:     {len(stations)} ({', '.join(s['id'] for s in stations)})")
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
        description="Bootstrap NDBC buoy observation resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()

    bootstrap(
        clean=args.clean,
        clean_only=args.clean_only,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
