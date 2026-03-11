#!/usr/bin/env python3
"""
bootstrap_usgs_water.py — Register USGS water monitoring resources on the OS4CSAPI server.

Creates per-station CSAPI resources:
  Procedure:
    1. urn:os4csapi:procedure:usgs-water-observation:v1

  Systems (one per station):
    N. urn:os4csapi:system:usgs-water:{nwisId}:v1

  Datastreams (two per station):
    N. "Discharge"   (00060)  under each station system
    N. "Gage Height" (00065)  under each station system

  Deployment tree:
    urn:os4csapi:deployment:usgs-water-demo:v1
    └─ urn:os4csapi:deployment:usgs-water-stations:v1
       ├─ urn:os4csapi:deployment:usgs-water-{nwisId}:v1  (platform@link → system)
       ...

Station list is read from stations.json (same directory).

Usage:
    python -m publishers.usgs_water.bootstrap_usgs_water              # create (skip if exists)
    python -m publishers.usgs_water.bootstrap_usgs_water --clean      # delete + recreate
    python -m publishers.usgs_water.bootstrap_usgs_water --clean-only # delete only
    python -m publishers.usgs_water.bootstrap_usgs_water --dry-run    # print what would happen

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

PROC_UID = "urn:os4csapi:procedure:usgs-water-observation:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:usgs-water-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:usgs-water-stations:v1"

# Output names — one datastream per parameter
DS_DISCHARGE_OUTPUT = "usgsDischarge"
DS_GAGE_HEIGHT_OUTPUT = "usgsGageHeight"

# USGS references
USGS_OGC_API = "https://api.waterdata.usgs.gov/ogcapi/v0/"
USGS_LEGACY_API = "https://waterservices.usgs.gov/nwis/iv/"
USGS_WATER_HOME = "https://waterdata.usgs.gov/"
USGS_API_DOCS = "https://api.waterdata.usgs.gov/ogcapi/v0/openapi?f=html"
USGS_NWIS_HELP = "https://help.waterdata.usgs.gov/faq/automated-retrievals"


def _load_stations() -> list[dict]:
    """Load station list from stations.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["stations"]


def _system_uid(nwis_id: str) -> str:
    return f"urn:os4csapi:system:usgs-water:{nwis_id}:v1"


def _deploy_uid(nwis_id: str) -> str:
    return f"urn:os4csapi:deployment:usgs-water-{nwis_id}:v1"


def _monitoring_location_url(nwis_id: str) -> str:
    return f"{USGS_OGC_API}collections/monitoring-locations/items/USGS-{nwis_id}"


def _continuous_url(nwis_id: str) -> str:
    return f"{USGS_OGC_API}collections/continuous/items?monitoring_location_id=USGS-{nwis_id}&limit=10"


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "USGS Water Observation v1",
        "description": (
            "Publishes real-time USGS water monitoring observations derived from the USGS Water "
            "Data OGC API (api.waterdata.usgs.gov). Continuous instantaneous values for discharge "
            "(streamflow) and gage height are normalized and published as flat JSON result objects. "
            "Upstream data originates from the USGS National Water Information System (NWIS) with "
            "reporting intervals typically at 15 minutes."
        ),
        "keywords": [
            "USGS",
            "water",
            "hydrology",
            "streamflow",
            "discharge",
            "gage height",
            "NWIS",
            "monitoring",
            "OGC API",
        ],
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
            {"title": "USGS Water Data API Docs", "href": USGS_API_DOCS, "rel": "describedby"},
            {"title": "USGS Water Data Home", "href": USGS_WATER_HOME, "rel": "about"},
            {"title": "USGS NWIS Help", "href": USGS_NWIS_HELP, "rel": "related"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": "U.S. Geological Survey",
                "website": USGS_WATER_HOME,
            },
        ],
        "lineage": {
            "source": "U.S. Geological Survey / Water Resources",
            "upstream": (
                "Continuous instantaneous values from USGS Water Data OGC API. "
                "Source data is collected by automated data-collection equipment at "
                "USGS monitoring stations and transmitted via satellite or phone."
            ),
            "normalization": (
                "Publisher fetches GeoJSON features from the continuous collection, "
                "extracts value/unit/time/qualifier, and publishes normalized observation records."
            ),
        },
        "usageConstraints": {
            "apiKeyNote": (
                "USGS API key is recommended for higher rate limits. "
                "Register at https://api.usgs.gov."
            ),
            "disclaimer": (
                "Provisional data subject to revision. Data are released on the condition "
                "that neither the USGS nor the United States Government may be held liable "
                "for any damages resulting from authorized or unauthorized use."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _system_stub(station: dict, proc_id: str) -> dict:
    """GeoJSON Feature stub for a USGS water monitoring station system."""
    nwis_id = station["nwisId"]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _system_uid(nwis_id),
            "featureType": "sosa:Sensor",
            "name": f"USGS {nwis_id} — {station['name']}",
            "description": (
                f"USGS water monitoring station {nwis_id} ({station['fullName']}). "
                f"{station['stateAbbr']}, {station.get('county', '')}. "
                f"Lat {station['lat']}, Lon {station['lon']}."
            ),
            "typeOf@link": {"href": proc_id, "title": "USGS Water Observation v1"},
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    """SensorML body for rich system metadata."""
    nwis_id = station["nwisId"]
    drainage = station.get("drainageArea_sqmi")
    drainage_text = f"{drainage} sq mi" if drainage else "Not available"

    characteristics_fields = [
        {"type": "Text", "name": "reporting_cadence",
         "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
         "label": "Reporting Cadence",
         "value": "Instantaneous values at 15-minute intervals (typical)"},
        {"type": "Text", "name": "timezone",
         "definition": "http://sensorml.com/ont/swe/property/TimeZone",
         "label": "Station Timezone",
         "value": station.get("tz", "UTC")},
        {"type": "Text", "name": "drainage_area",
         "definition": "http://sensorml.com/ont/swe/property/DrainageArea",
         "label": "Drainage Area",
         "value": drainage_text},
        {"type": "Text", "name": "huc",
         "definition": "http://sensorml.com/ont/swe/property/HydrologicUnitCode",
         "label": "Hydrologic Unit Code",
         "value": station.get("huc", "")},
    ]

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(nwis_id),
        "uniqueId": _system_uid(nwis_id),
        "definition": "sosa:System",
        "label": f"USGS {nwis_id} \u2014 {station['name']}",
        "description": (
            f"USGS water monitoring station at {station['name']} (NWIS ID {nwis_id}). "
            f"Located in {station.get('county', '')}, {station['state']}. "
            f"Drainage area: {drainage_text}. "
            "Continuous instantaneous values for discharge and gage height."
        ),
        "keywords": [
            "USGS", "NWIS", "water", "hydrology", "streamflow",
            "monitoring station", nwis_id, station["stateAbbr"],
        ],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName",
             "label": "Short Name", "value": f"USGS {nwis_id}"},
            {"definition": "http://sensorml.com/ont/swe/property/LongName",
             "label": "Long Name", "value": station["fullName"]},
            {"definition": "http://sensorml.com/ont/swe/property/ModelNumber",
             "label": "NWIS Site Number", "value": nwis_id},
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID",
             "label": "OS4CSAPI UID", "value": _system_uid(nwis_id)},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType",
             "label": "Site Type", "value": station.get("siteType", "Stream")},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
             "label": "Network", "value": "USGS National Water Information System (NWIS)"},
            {"definition": "http://sensorml.com/ont/swe/property/SystemRole",
             "label": "Operator", "value": "U.S. Geological Survey"},
        ],
        "contacts": [
            {
                "role": "http://sensorml.com/ont/swe/property/Operator",
                "organisationName": "U.S. Geological Survey",
                "contactInfo": {
                    "website": USGS_WATER_HOME,
                },
            },
        ],
        "documents": [
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Monitoring Location",
                "description": f"USGS OGC API monitoring location resource for site {nwis_id}.",
                "link": {"href": _monitoring_location_url(nwis_id), "type": "application/geo+json"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Continuous Data",
                "description": f"Continuous instantaneous values for site {nwis_id}.",
                "link": {"href": _continuous_url(nwis_id), "type": "application/geo+json"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "USGS Water Data OGC API",
                "description": "USGS Water Data OGC API documentation.",
                "link": {"href": USGS_API_DOCS, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "USGS Water Data Home",
                "description": "USGS National Water Dashboard.",
                "link": {"href": USGS_WATER_HOME, "type": "text/html"},
            },
        ],
        "characteristics": [
            {
                "label": "Station Properties",
                "characteristics": characteristics_fields,
            },
        ],
        "capabilities": [
            {
                "definition": "http://www.w3.org/ns/ssn/systems/SystemCapability",
                "label": "Publisher Capabilities",
                "capabilities": [
                    {"type": "Quantity", "name": "update_interval",
                     "definition": "http://qudt.org/vocab/quantitykind/Period",
                     "label": "Publish Interval", "uom": {"code": "s"}, "value": 900.0},
                    {"type": "Text", "name": "data_source",
                     "definition": "http://sensorml.com/ont/swe/property/DataSource",
                     "label": "Data Source", "value": "USGS Water Data OGC API — continuous collection"},
                ],
            },
        ],
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _discharge_datastream_schema() -> dict:
    """SWE DataRecord schema for the discharge (streamflow) datastream."""
    return {
        "outputName": DS_DISCHARGE_OUTPUT,
        "name": "Discharge",
        "description": (
            "Instantaneous discharge (streamflow) from a USGS monitoring station. "
            "Source: USGS Water Data OGC API continuous collection, parameter code 00060."
        ),
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "USGS Discharge Observation",
                "description": "Instantaneous discharge (streamflow) value",
                "fields": [
                    {"type": "Time",     "name": "timestamp",       "label": "Observation Time",
                     "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime",
                     "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "stationId",      "label": "NWIS Site ID",
                     "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Quantity", "name": "discharge_cfs",   "label": "Discharge",
                     "definition": "http://www.opengis.net/def/property/OGC/0/Discharge",
                     "uom": {"code": "ft3/s"}},
                    {"type": "Text",     "name": "qualifier",      "label": "Data Qualifier",
                     "definition": "http://sensorml.com/ont/swe/property/QualityFlag"},
                    {"type": "Text",     "name": "approvalStatus", "label": "Approval Status",
                     "definition": "http://sensorml.com/ont/swe/property/ApprovalStatus"},
                ],
            },
        },
    }


def _gage_height_datastream_schema() -> dict:
    """SWE DataRecord schema for the gage height (water level) datastream."""
    return {
        "outputName": DS_GAGE_HEIGHT_OUTPUT,
        "name": "Gage Height",
        "description": (
            "Instantaneous gage height (water surface elevation above datum) from a USGS "
            "monitoring station. Source: USGS Water Data OGC API continuous collection, "
            "parameter code 00065."
        ),
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "USGS Gage Height Observation",
                "description": "Instantaneous gage height (water level) value",
                "fields": [
                    {"type": "Time",     "name": "timestamp",       "label": "Observation Time",
                     "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime",
                     "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "stationId",      "label": "NWIS Site ID",
                     "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Quantity", "name": "gage_height_ft",  "label": "Gage Height",
                     "definition": "http://www.opengis.net/def/property/OGC/0/GageHeight",
                     "uom": {"code": "ft"}},
                    {"type": "Text",     "name": "qualifier",      "label": "Data Qualifier",
                     "definition": "http://sensorml.com/ont/swe/property/QualityFlag"},
                    {"type": "Text",     "name": "approvalStatus", "label": "Approval Status",
                     "definition": "http://sensorml.com/ont/swe/property/ApprovalStatus"},
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
            "name": "USGS Water Monitoring Demo",
            "description": (
                "Demonstration deployment for USGS water monitoring stations publishing "
                "discharge and gage height observations via the USGS Water Data OGC API into CSAPI."
            ),
            "documentation": [
                {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
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
            "name": "USGS Water Monitoring Stations",
            "description": (
                "USGS water monitoring stations across 8 US states selected for the "
                "OS4CSAPI demonstration. Each station has discharge and gage height datastreams."
            ),
            "documentation": [
                {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str) -> dict:
    nwis_id = station["nwisId"]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _deploy_uid(nwis_id),
            "featureType": "sosa:Deployment",
            "name": f"USGS {nwis_id} Station Feed",
            "description": (
                f"CSAPI deployment node for USGS station {nwis_id} ({station['name']}) "
                "with discharge and gage height datastreams."
            ),
            "externalLinks": [
                {"href": _monitoring_location_url(nwis_id),
                 "title": "USGS Monitoring Location", "rel": "canonical"},
                {"href": _continuous_url(nwis_id),
                 "title": "Continuous Data", "rel": "latest-version"},
            ],
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(nwis_id),
                "title": f"USGS {nwis_id}",
            },
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url: str, auth: str, stations: list[dict],
              *, dry_run: bool = False, stats: dict):
    """Delete all USGS water resources (reverse order)."""
    # Deployments (leaf → root)
    for st in reversed(stations):
        clean_resource(base_url, auth, "deployments", _deploy_uid(st["nwisId"]),
                       dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID,
                   dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID,
                   dry_run=dry_run, stats=stats)

    # Systems (datastreams cascade-deleted by server)
    for st in reversed(stations):
        clean_resource(base_url, auth, "systems", _system_uid(st["nwisId"]),
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
    print("  USGS Water Monitoring — Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)} ({', '.join(s['nwisId'] for s in stations)})")
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
    proc_id = ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_BODY,
                               dry_run=dry_run, stats=stats)

    # ── Systems + Datastreams ─────────────────────────────────────────
    print("  ── Systems + Datastreams ──")
    system_ids: dict[str, str] = {}   # nwisId → server ID

    for st in stations:
        nwis_id = st["nwisId"]
        uid = _system_uid(nwis_id)

        stub = _system_stub(st, proc_id or "pending")
        sml = _system_sml(st)

        sys_id = ensure_system(base_url, auth, uid, stub, sml,
                               dry_run=dry_run, stats=stats,
                               force_sml=force_sml)
        system_ids[nwis_id] = sys_id

        if sys_id or dry_run:
            # Create discharge datastream
            if "00060" in st.get("parameterCodes", []):
                ensure_datastream(base_url, auth, sys_id or "pending",
                                  DS_DISCHARGE_OUTPUT,
                                  _discharge_datastream_schema(),
                                  dry_run=dry_run, stats=stats)

            # Create gage height datastream
            if "00065" in st.get("parameterCodes", []):
                ensure_datastream(base_url, auth, sys_id or "pending",
                                  DS_GAGE_HEIGHT_OUTPUT,
                                  _gage_height_datastream_schema(),
                                  dry_run=dry_run, stats=stats)

    # ── Deployment tree ───────────────────────────────────────────────
    print("  ── Deployments ──")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id,
                                 dry_run=dry_run, stats=stats)

    for st in stations:
        nwis_id = st["nwisId"]
        sys_id = system_ids.get(nwis_id)
        if sys_id or dry_run:
            ensure_deployment(base_url, auth, _deploy_uid(nwis_id),
                              _deploy_station(st, sys_id or "pending"),
                              parent_id=group_id,
                              dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap USGS water monitoring resources on the CSAPI server.")
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
