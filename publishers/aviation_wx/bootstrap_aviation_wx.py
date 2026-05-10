#!/usr/bin/env python3
"""
bootstrap_aviation_wx.py — Register AviationWeather.gov METAR resources on the OS4CSAPI server.

Creates per-station CSAPI resources:
  Procedure:
    1. urn:os4csapi:procedure:metar-decoder:v1

  Systems (one per station):
    N. urn:os4csapi:system:awx:{icaoId}:v1

  Datastreams (one per station):
    N. "METAR Observation"  under each station system

  Deployment tree:
    urn:os4csapi:deployment:awx-metar-demo:v1
    └─ urn:os4csapi:deployment:awx-stations:v1
       ├─ urn:os4csapi:deployment:awx-{icaoId}:v1  (platform@link → system)
       ...

Station list is read from stations.json (same directory).

Usage:
    python -m publishers.aviation_wx.bootstrap_aviation_wx              # create (skip if exists)
    python -m publishers.aviation_wx.bootstrap_aviation_wx --clean      # delete + recreate
    python -m publishers.aviation_wx.bootstrap_aviation_wx --clean-only # delete only
    python -m publishers.aviation_wx.bootstrap_aviation_wx --dry-run    # print what would happen
    python -m publishers.aviation_wx.bootstrap_aviation_wx --force-sml  # re-PUT SensorML on existing

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

PROC_UID = "urn:os4csapi:procedure:metar-decoder:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:awx-metar-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:awx-stations:v1"

DS_OUTPUT_NAME = "metarObs"

# ── AviationWeather.gov Official URLs ────────────────────────────────────
AWX_HOME = "https://aviationweather.gov/"
AWX_API_DOC = "https://aviationweather.gov/data/api/"
AWX_METAR_BASE = "https://aviationweather.gov/metar/data?ids="

# ── FAA contact ──────────────────────────────────────────────────────────
FAA_CONTACT_ORG = "FAA / Aviation Weather Center (AWC)"
FAA_CONTACT_EMAIL = "awc.operations@noaa.gov"
FAA_CONTACT_ADDRESS = "7220 NW 101st Terrace, Kansas City, MO 64153"


def _station_page_url(icao_id: str) -> str:
    return f"{AWX_METAR_BASE}{icao_id}"


def _station_api_url(icao_id: str) -> str:
    return f"https://aviationweather.gov/api/data/metar?ids={icao_id}&format=json"


def _load_stations() -> list[dict]:
    """Load station list from stations.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["aviation_wx_stations"]


def _system_uid(icao_id: str) -> str:
    return f"urn:os4csapi:system:awx:{icao_id.lower()}:v1"


def _deploy_uid(icao_id: str) -> str:
    return f"urn:os4csapi:deployment:awx-{icao_id.lower()}:v1"


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions
#
#  Strict-parsing servers (csapi-go-v2 and later) reject any field in
#  GeoJSON `properties` outside the closed set
#  {featureType, uid, name, description, validTime, platform@link}.
#  All SensorML metadata (keywords, identifiers, classifiers, contacts,
#  documents, characteristics, capabilities, lineage, usageConstraints,
#  typeOf, ...) lives in a SEPARATE `application/sml+json` body that is
#  PUT against /systems/{id} or /procedures/{id} after creation.
#  See: docs/research/Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md §9.
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "featureType": "sosa:ObservingProcedure",
        "uid": PROC_UID,
        "name": "METAR Decoder v1",
        "description": (
            "Publishes real-time METAR observations from the AviationWeather.gov REST API. "
            "Data includes temperature, dew point, wind speed/direction, visibility, "
            "barometric pressure, cloud layers, flight category, and the raw METAR string. "
            "Observations are decoded from standard METAR format and published to CSAPI."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "METAR Decoder v1",
    "description": (
        "Publishes real-time METAR observations from the AviationWeather.gov REST API. "
        "Data includes temperature, dew point, wind speed/direction, visibility, "
        "barometric pressure, cloud layers, flight category, and the raw METAR string. "
        "Observations are decoded from standard METAR format and published to CSAPI."
    ),
    "keywords": [
        "METAR", "aviation", "weather", "AviationWeather.gov", "FAA", "AWC",
        "ASOS", "surface observation", "flight category",
    ],
    # NOTE: csapi-go-v2 ProcedureSensorMLFeature struct still has the
    # `documentation` typo (the c2ab201 fix landed only on
    # SystemSensorMLFeature). Until that lands, procedure SML PUT requires
    # the typo'd field name. /systems uses `documents` (correct).
    "documentation": [
        {"role": "http://dbpedia.org/resource/Web_page",
         "name": "AviationWeather.gov",
         "link": {"href": AWX_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page",
         "name": "AviationWeather Data API",
         "link": {"href": AWX_API_DOC, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page",
         "name": "METAR Format Guide",
         "link": {"href": "https://www.weather.gov/media/wrh/mesowest/metar_decode_key.pdf",
                  "type": "application/pdf"}},
    ],
    "contacts": [
        {
            "role": "operator",
            "organisationName": FAA_CONTACT_ORG,
            "contactInfo": {
                "address": {
                    "deliveryPoint": FAA_CONTACT_ADDRESS,
                    "electronicMailAddress": FAA_CONTACT_EMAIL,
                },
                "onlineResource": {"linkage": AWX_HOME},
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
}


def _system_stub(station: dict, proc_id: str) -> dict:
    """GeoJSON Feature stub for an aviation weather station system.

    Properties closed to {featureType, uid, name, description} per OGC 23-001
    strict parsing. typeOf, validTime, and links live in the companion SML body
    (see ``_system_sml``).
    """
    icao_id = station["icao_id"]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "featureType": "sosa:Sensor",
            "uid": _system_uid(icao_id),
            "name": f"AWX {icao_id} — {station['name']}",
            "description": (
                f"AviationWeather.gov METAR station {icao_id} at {station['name']}, "
                f"{station['city']}, {station['state']}. "
                f"Station type: {station.get('station_type', 'ASOS')}. "
                f"Field elevation: {station.get('elev_m', '?')} m MSL."
            ),
        },
    }


def _system_sml(station: dict) -> dict:
    """SensorML body for rich system metadata.

    Field shapes follow the SensorML JSON encoding expected by OSH SensorHub:
      - contacts use ``organisationName`` (British spelling) and nested ``contactInfo``
      - documents use ``"documents"`` key with ``link: {href, type}``
      - characteristics are grouped SWE DataComponent trees
      - identifiers / classifiers carry ``definition`` URIs
    """
    icao_id = station["icao_id"]

    # ── Build inner SWE characteristic items ──────────────────────────
    char_items: list[dict] = [
        {"type": "Text", "name": "operator",
         "definition": "http://sensorml.com/ont/swe/property/Operator",
         "label": "Operator", "value": FAA_CONTACT_ORG},
        {"type": "Text", "name": "station_type",
         "definition": "http://sensorml.com/ont/swe/property/SensorType",
         "label": "Station Type", "value": station.get("station_type", "ASOS")},
        {"type": "Text", "name": "faa_id",
         "definition": "http://sensorml.com/ont/swe/property/StationID",
         "label": "FAA Identifier", "value": station.get("faa_id", icao_id[1:])},
    ]
    if "elev_m" in station:
        char_items.append(
            {"type": "Quantity", "name": "field_elevation",
             "definition": "http://sensorml.com/ont/swe/property/Elevation",
             "label": "Field Elevation (MSL)", "uom": {"code": "m"}, "value": station["elev_m"]})

    # ── Build documents list ──────────────────────────────────────────
    docs: list[dict] = [
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "METAR Data Page",
            "description": f"AviationWeather.gov METAR data page for {icao_id}.",
            "link": {"href": _station_page_url(icao_id), "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "API Endpoint",
            "description": f"AviationWeather.gov JSON API endpoint for {icao_id}.",
            "link": {"href": _station_api_url(icao_id), "type": "application/json"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "METAR Decode Key",
            "description": "NWS guide to decoding standard METAR observations.",
            "link": {"href": "https://www.weather.gov/media/wrh/mesowest/metar_decode_key.pdf", "type": "application/pdf"},
        },
    ]
    if "airport_diagram" in station:
        docs.append({
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Airport Diagram",
            "description": f"FAA airport diagram for {station.get('faa_id', icao_id)}.",
            "link": {"href": station["airport_diagram"], "type": "application/pdf"},
        })

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(icao_id),
        "uniqueId": _system_uid(icao_id),
        "definition": "sosa:System",
        "label": f"AWX {icao_id} — {station['name']}",
        "description": (
            f"Automated Surface Observing System (ASOS) at {station['name']} ({icao_id}), "
            f"{station['city']}, {station['state']}. Field elevation: {station.get('elev_m', '?')} m MSL. "
            f"Provides hourly METAR and SPECI (special) weather observations."
        ),
        "keywords": [
            "METAR", "ASOS", "aviation", "weather", icao_id,
            station["name"], station.get("faa_id", ""),
        ],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName",
             "label": "Short Name", "value": f"AWX {icao_id}"},
            {"definition": "http://sensorml.com/ont/swe/property/LongName",
             "label": "Long Name", "value": f"AviationWeather {icao_id} — {station['name']}"},
            {"definition": "http://sensorml.com/ont/swe/property/StationID",
             "label": "ICAO Identifier", "value": icao_id},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType",
             "label": "Sensor Type", "value": "Automated Surface Observing System (ASOS)"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
             "label": "Intended Application", "value": "Aviation weather; surface observation; flight planning"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organisationName": FAA_CONTACT_ORG,
                "contactInfo": {
                    "address": {
                        "deliveryPoint": FAA_CONTACT_ADDRESS,
                        "electronicMailAddress": FAA_CONTACT_EMAIL,
                    },
                    "onlineResource": {"linkage": AWX_HOME},
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
        "documents": docs,
        # NOTE: characteristics/capabilities are part of OGC SensorML JSON encoding
        # but the strict csapi-go-v2 server does not accept them on the
        # SystemSensorMLFeature struct (see empirical probe 2026-05-09).
        # Field-elevation, station_type, operator, and update_interval information
        # is preserved in identifiers/classifiers/position above. char_items
        # (operator, station_type, faa_id, field_elevation) are intentionally not
        # serialised here; restore once upstream adds these fields back.
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _datastream_schema(icao_id: str = "") -> dict:
    """SWE DataRecord schema for METAR observation datastream.

    AviationWeather METAR fields:
      temp_c          - Temperature (°C)
      dewp_c          - Dew point (°C)
      wind_dir_deg    - Wind direction (°T, 0 = variable)
      wind_speed_kt   - Wind speed (knots)
      visibility_sm   - Visibility (statute miles)
      altimeter_inhg  - Altimeter setting (inHg)
      slp_hpa         - Sea-level pressure (hPa)
      flight_category - VFR/MVFR/IFR/LIFR
      cloud_cover     - Dominant sky cover (CLR/FEW/SCT/BKN/OVC)
      cloud_base_ft   - Lowest cloud base (feet AGL)
      raw_metar       - Raw METAR text
    """
    # NOTE: Strict csapi-go-v2 rejects 'documentation', 'characteristics', and
    # SWE Time field 'referenceTime'. Keeping body to fields the server accepts.
    return {
        "outputName": DS_OUTPUT_NAME,
        "name": "METAR Observation",
        "description": (
            "Decoded METAR aviation weather observation from an AviationWeather.gov station. "
            "Includes temperature, dew point, wind, visibility, altimeter setting, cloud layers, "
            "flight category, and the raw METAR string. Some fields may be NaN if not reported."
        ),
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "METAR Observation",
                "description": "Decoded METAR aviation weather observation",
                "fields": [
                    {"type": "Time",     "name": "timestamp",        "label": "Observation Time",     "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "stationId",        "label": "ICAO Station ID",      "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Quantity", "name": "lat_deg",          "label": "Latitude",             "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude",    "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "lon_deg",          "label": "Longitude",            "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude",   "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "temp_c",           "label": "Temperature",          "definition": "http://sensorml.com/ont/swe/property/AirTemperature",      "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "dewp_c",           "label": "Dew Point",            "definition": "http://mmisw.org/ont/cf/parameter/dew_point_temperature",  "uom": {"code": "Cel"}},
                    {"type": "Quantity", "name": "wind_dir_deg",     "label": "Wind Direction",       "definition": "http://sensorml.com/ont/swe/property/WindDirection",       "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "wind_speed_kt",    "label": "Wind Speed",           "definition": "http://sensorml.com/ont/swe/property/WindSpeed",           "uom": {"code": "[kn_i]"}},
                    {"type": "Quantity", "name": "visibility_sm",    "label": "Visibility",           "definition": "http://sensorml.com/ont/swe/property/Visibility",          "uom": {"code": "[mi_i]"}},
                    {"type": "Quantity", "name": "altimeter_inhg",   "label": "Altimeter Setting",    "definition": "http://sensorml.com/ont/swe/property/AtmosphericPressure", "uom": {"code": "[in_i'Hg]"}},
                    {"type": "Quantity", "name": "slp_hpa",          "label": "Sea-Level Pressure",   "definition": "http://sensorml.com/ont/swe/property/AtmosphericPressure", "uom": {"code": "hPa"}, "optional": True},
                    {"type": "Text",     "name": "flight_category",  "label": "Flight Category",      "definition": "http://codes.wmo.int/bufr4/codeflag/0-20-003"},
                    {"type": "Text",     "name": "cloud_cover",      "label": "Sky Cover",            "definition": "http://codes.wmo.int/bufr4/codeflag/0-20-010"},
                    {"type": "Quantity", "name": "cloud_base_ft",    "label": "Cloud Base (AGL)",     "definition": "http://mmisw.org/ont/cf/parameter/cloud_base_altitude",    "uom": {"code": "[ft_i]"}, "optional": True},
                    {"type": "Text",     "name": "rawMessage",       "label": "Raw METAR",            "definition": "http://codes.wmo.int/306/4678"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-111.5, 33.0],
        },
        "properties": {
            "featureType": "sosa:Deployment",
            "uid": DEPLOY_ROOT_UID,
            "name": "AviationWeather METAR Demo Deployment",
            "description": (
                "Top-level CSAPI deployment grouping for AviationWeather.gov METAR stations "
                "published by OSHConnect-Python. This grouping represents the demo / integration "
                "scope, not a single physical field deployment."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-111.5, 33.0],
        },
        "properties": {
            "featureType": "sosa:Deployment",
            "uid": DEPLOY_GROUP_UID,
            "name": "AviationWeather METAR Stations",
            "description": (
                "Grouping deployment for curated AviationWeather.gov METAR stations. Each child "
                "deployment links a station/system resource to the demo deployment tree."
            ),
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    icao_id = station["icao_id"]
    system_href = f"{base_url.rstrip('/')}/systems/{system_server_id}"
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "featureType": "sosa:Deployment",
            "uid": _deploy_uid(icao_id),
            "name": f"METAR {icao_id} Feed",
            "description": f"AviationWeather METAR station {icao_id} ({station['name']}) observation feed.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_href,
                "uid": _system_uid(icao_id),
                "title": f"AWX {icao_id}",
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url: str, auth: str, stations: list[dict],
              *, dry_run: bool = False, stats: dict):
    """Delete all AviationWeather resources (reverse order)."""
    # Deployments (leaf → root)
    for st in reversed(stations):
        clean_resource(base_url, auth, "deployments", _deploy_uid(st["icao_id"]),
                       dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID,
                   dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID,
                   dry_run=dry_run, stats=stats, cascade=True)

    # Systems (datastreams deleted automatically via cascade)
    for st in reversed(stations):
        clean_resource(base_url, auth, "systems", _system_uid(st["icao_id"]),
                       dry_run=dry_run, stats=stats, cascade=True)

    # Procedure
    clean_resource(base_url, auth, "procedures", PROC_UID,
                   dry_run=dry_run, stats=stats)


def bootstrap(*, clean: bool = False, clean_only: bool = False,
              dry_run: bool = False, force_sml: bool = False):
    """Main bootstrap entry point."""
    config = get_config()
    base_url = config["base_url"]
    auth = _auth_header(config["user"], config["password"])
    stations = _load_stations()

    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  AviationWeather METAR Observation — Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)} ({', '.join(s['icao_id'] for s in stations)})")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}")
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
    proc_id = ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_BODY_STUB,
                               sml_body=PROCEDURE_SML,
                               dry_run=dry_run, stats=stats,
                               force_sml=force_sml)

    # ── Systems + Datastreams ─────────────────────────────────────────
    print("  ── Systems + Datastreams ──")
    system_ids: dict[str, str] = {}

    for st in stations:
        uid = _system_uid(st["icao_id"])

        stub = _system_stub(st, proc_id or "pending")
        sml = _system_sml(st)

        sys_id = ensure_system(base_url, auth, uid, stub, sml,
                               dry_run=dry_run, stats=stats,
                               force_sml=force_sml)
        system_ids[st["icao_id"]] = sys_id

        if sys_id or dry_run:
            ensure_datastream(base_url, auth, sys_id or "pending", DS_OUTPUT_NAME,
                              _datastream_schema(st["icao_id"]),
                              dry_run=dry_run, stats=stats)

    # ── Deployment tree ───────────────────────────────────────────────
    print("  ── Deployments ──")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id,
                                 dry_run=dry_run, stats=stats)

    for st in stations:
        sys_id = system_ids.get(st["icao_id"])
        if sys_id or dry_run:
            ensure_deployment(base_url, auth, _deploy_uid(st["icao_id"]),
                              _deploy_station(st, sys_id or "pending", base_url),
                              parent_id=group_id,
                              dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap AviationWeather METAR resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()

    bootstrap(
        clean=args.clean,
        clean_only=args.clean_only,
        dry_run=args.dry_run,
        force_sml=args.force_sml,
    )


if __name__ == "__main__":
    main()
