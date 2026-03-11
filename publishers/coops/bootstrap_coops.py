#!/usr/bin/env python3
"""
bootstrap_coops.py — Register NOAA CO-OPS tides & currents resources on the OS4CSAPI server.

Creates per-station CSAPI resources:
  Procedure:
    1. urn:os4csapi:procedure:coops-water-level:v1

  Systems (one per station):
    N. urn:os4csapi:system:coops:{stationId}:v1

  Datastreams (one per station):
    N. "Coastal Observation"  under each station system

  Deployment tree:
    urn:os4csapi:deployment:coops-coastal-demo:v1
    └─ urn:os4csapi:deployment:coops-stations:v1
       ├─ urn:os4csapi:deployment:coops-{stationId}:v1  (platform@link → system)
       ...

Station list is read from stations.json (same directory).

Usage:
    python -m publishers.coops.bootstrap_coops              # create (skip if exists)
    python -m publishers.coops.bootstrap_coops --clean      # delete + recreate
    python -m publishers.coops.bootstrap_coops --clean-only # delete only
    python -m publishers.coops.bootstrap_coops --dry-run    # print what would happen
    python -m publishers.coops.bootstrap_coops --force-sml  # re-PUT SensorML on existing

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

PROC_UID = "urn:os4csapi:procedure:coops-water-level:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:coops-coastal-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:coops-stations:v1"

DS_OUTPUT_NAME = "coopsCoastalObs"

# ── CO-OPS Official URLs ─────────────────────────────────────────────────
COOPS_HOME = "https://tidesandcurrents.noaa.gov/"
COOPS_API_DOC = "https://api.tidesandcurrents.noaa.gov/api/prod/"
COOPS_STATION_BASE = "https://tidesandcurrents.noaa.gov/stationhome.html?id="
COOPS_WATER_LEVELS_BASE = "https://tidesandcurrents.noaa.gov/waterlevels.html?id="
COOPS_MET_BASE = "https://tidesandcurrents.noaa.gov/met.html?id="
COOPS_PREDICTIONS_BASE = "https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id="
COOPS_DATUMS_BASE = "https://tidesandcurrents.noaa.gov/datums.html?id="
COOPS_INVENTORY_BASE = "https://tidesandcurrents.noaa.gov/inventory.html?id="
COOPS_MEASUREMENT_SPECS = "https://tidesandcurrents.noaa.gov/measure.html"
COOPS_GLOSSARY = "https://tidesandcurrents.noaa.gov/glossary.html"

COOPS_CONTACT_EMAIL = "co-ops.userservices@noaa.gov"
COOPS_CONTACT_ORG = "Center for Operational Oceanographic Products and Services"
COOPS_CONTACT_ADDRESS = "1305 East-West Highway, Silver Spring, MD 20910"


def _station_page_url(station_id: str) -> str:
    return f"{COOPS_STATION_BASE}{station_id}"


def _station_water_level_url(station_id: str) -> str:
    return f"{COOPS_WATER_LEVELS_BASE}{station_id}"


def _station_met_url(station_id: str) -> str:
    return f"{COOPS_MET_BASE}{station_id}"


def _station_predictions_url(station_id: str) -> str:
    return f"{COOPS_PREDICTIONS_BASE}{station_id}"


def _station_datums_url(station_id: str) -> str:
    return f"{COOPS_DATUMS_BASE}{station_id}"


def _station_inventory_url(station_id: str) -> str:
    return f"{COOPS_INVENTORY_BASE}{station_id}"


def _load_stations() -> list[dict]:
    """Load station list from stations.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["coops_stations"]


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:coops:{station_id}:v1"


def _deploy_uid(station_id: str) -> str:
    return f"urn:os4csapi:deployment:coops-{station_id}:v1"


# ═══════════════════════════════════════════════════════════════════════════
#  Resource definitions
# ═══════════════════════════════════════════════════════════════════════════

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "CO-OPS Coastal Observation v1",
        "description": (
            "Publishes real-time water level observations, tide predictions, and coastal "
            "meteorological data from NOAA's Center for Operational Oceanographic Products "
            "and Services (CO-OPS). Data is sourced from the CO-OPS Data API, normalized "
            "into a flat JSON result object, and published to CSAPI. Water levels are "
            "6-minute verified observations referenced to the MLLW datum in metric units."
        ),
        "keywords": [
            "NOAA", "CO-OPS", "tides", "water level", "coastal",
            "tide gauge", "predictions", "MLLW", "sea level",
        ],
        "documentation": [
            {"title": "CO-OPS Home", "href": COOPS_HOME, "rel": "about"},
            {"title": "CO-OPS Data API", "href": COOPS_API_DOC, "rel": "documentation"},
            {"title": "Measurement Specifications", "href": COOPS_MEASUREMENT_SPECS, "rel": "describedby"},
            {"title": "CO-OPS Glossary", "href": COOPS_GLOSSARY, "rel": "glossary"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": COOPS_CONTACT_ORG,
                "website": COOPS_HOME,
                "email": COOPS_CONTACT_EMAIL,
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python",
            },
        ],
        "lineage": {
            "source": "NOAA / Center for Operational Oceanographic Products and Services",
            "upstream": f"CO-OPS Data API at {COOPS_API_DOC}",
            "normalization": (
                "Publisher fetches water level, predictions, and available met products "
                "from the CO-OPS JSON API and emits a flat JSON result with metric units."
            ),
        },
        "usageConstraints": {
            "sourceProtocol": "HTTPS",
            "sourceFormat": "JSON via CO-OPS Data API (datagetter)",
            "rateLimitNote": "No explicit rate limit documented; publisher uses 6-minute cadence matching data refresh.",
            "qualityControlNote": (
                "Water levels undergo real-time quality control. Preliminary data is available "
                "within minutes; verified data typically available after 1-2 months."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _system_stub(station: dict, proc_id: str) -> dict:
    """GeoJSON Feature stub for a CO-OPS station system."""
    station_id = station["id"]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _system_uid(station_id),
            "featureType": "sosa:Sensor",
            "name": f"CO-OPS {station_id} — {station['name']}",
            "description": (
                f"NOAA CO-OPS tide station {station_id} at {station['name']}. "
                f"Established {station.get('established', 'unknown')}. "
                f"Mean tidal range: {station.get('mean_range_ft', '?')} ft."
            ),
            "typeOf@link": {"href": proc_id, "title": "CO-OPS Coastal Observation v1"},
            "links": [
                {"rel": "about", "title": "Station Home", "href": _station_page_url(station_id)},
                {"rel": "alternate", "title": "Water Levels", "href": _station_water_level_url(station_id)},
                {"rel": "alternate", "title": "Tide Predictions", "href": _station_predictions_url(station_id)},
                {"rel": "alternate", "title": "Met Observations", "href": _station_met_url(station_id)},
            ],
            "validTime": [VALID_TIME_START, ".."],
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
    station_id = station["id"]
    sensors = station.get("sensors", [])

    # ── Build inner SWE characteristic items ──────────────────────────
    char_items: list[dict] = [
        {"type": "Text", "name": "operator",
         "definition": "http://sensorml.com/ont/swe/property/Operator",
         "label": "Operator", "value": COOPS_CONTACT_ORG},
        {"type": "Text", "name": "station_type",
         "definition": "http://sensorml.com/ont/swe/property/SensorType",
         "label": "Station Type", "value": "Coastal tide gauge / water level station"},
    ]
    if "established" in station:
        char_items.append(
            {"type": "Text", "name": "established",
             "definition": "http://purl.org/dc/terms/created",
             "label": "Date Established", "value": station["established"]})
    if "mean_range_ft" in station:
        char_items.append(
            {"type": "Quantity", "name": "mean_tidal_range",
             "definition": "http://qudt.org/vocab/quantitykind/Height",
             "label": "Mean Tidal Range", "uom": {"code": "[ft_i]"}, "value": station["mean_range_ft"]})
    if "diurnal_range_ft" in station:
        char_items.append(
            {"type": "Quantity", "name": "diurnal_tidal_range",
             "definition": "http://qudt.org/vocab/quantitykind/Height",
             "label": "Diurnal Tidal Range", "uom": {"code": "[ft_i]"}, "value": station["diurnal_range_ft"]})
    if "met_elevation_ft" in station:
        char_items.append(
            {"type": "Quantity", "name": "met_site_elevation",
             "definition": "http://sensorml.com/ont/swe/property/Elevation",
             "label": "Met Site Elevation (above MSL)", "uom": {"code": "[ft_i]"}, "value": station["met_elevation_ft"]})

    # ── Build documents list ──────────────────────────────────────────
    docs: list[dict] = [
        {
            "role": "http://dbpedia.org/resource/Photograph",
            "name": "Station Hardware Photo",
            "description": f"CO-OPS photograph of the tide station installation at {station['name']}.",
            "link": {
                "href": station.get(
                    "station_photo",
                    f"https://cdn.tidesandcurrents.noaa.gov/assets/stationphotos/{station_id}A.jpg",
                ),
                "type": "image/jpeg",
            },
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Station Home Page",
            "description": f"CO-OPS station home page for {station_id}.",
            "link": {"href": _station_page_url(station_id), "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Water Levels",
            "description": f"Observed and predicted water levels for {station_id}.",
            "link": {"href": _station_water_level_url(station_id), "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Tide Predictions",
            "description": f"NOAA tide predictions for {station_id}.",
            "link": {"href": _station_predictions_url(station_id), "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Datums",
            "description": f"Tidal datum information for {station_id}.",
            "link": {"href": _station_datums_url(station_id), "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Meteorological Observations",
            "description": f"CO-OPS meteorological observations for {station_id}.",
            "link": {"href": _station_met_url(station_id), "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Data Inventory",
            "description": f"CO-OPS data inventory for {station_id}.",
            "link": {"href": _station_inventory_url(station_id), "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Measurement Specifications",
            "description": "CO-OPS sensor measurement specifications and accuracy standards.",
            "link": {"href": COOPS_MEASUREMENT_SPECS, "type": "text/html"},
        },
    ]

    # ── Build sensor description from available sensors ───────────────
    sensor_labels = {
        "water_level": "Water Level (microwave & backup gauges)",
        "air_temperature": "Air Temperature",
        "water_temperature": "Water Temperature",
        "wind": "Wind Speed / Direction / Gust",
        "air_pressure": "Barometric Pressure",
    }
    sensor_desc = "; ".join(sensor_labels.get(s, s) for s in sensors) if sensors else "Water Level"

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station_id),
        "uniqueId": _system_uid(station_id),
        "definition": "sosa:System",
        "label": f"CO-OPS {station_id} — {station['name']}",
        "description": (
            f"Coastal tide and water level station at {station['name']} ({station_id}) operated by "
            f"NOAA CO-OPS. Established {station.get('established', 'unknown')}. "
            f"Sensors: {sensor_desc}."
        ),
        "keywords": [
            "NOAA", "CO-OPS", "tide", "water level", "coastal",
            "tide gauge", station_id, station["name"],
        ],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName",
             "label": "Short Name", "value": f"CO-OPS {station_id}"},
            {"definition": "http://sensorml.com/ont/swe/property/LongName",
             "label": "Long Name", "value": f"NOAA CO-OPS Station {station_id} — {station['name']}"},
            {"definition": "http://sensorml.com/ont/swe/property/StationID",
             "label": "Station ID", "value": station_id},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType",
             "label": "Sensor Type", "value": "Coastal tide gauge / water level station"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
             "label": "Intended Application", "value": "Coastal water level monitoring; navigation safety; coastal hazard warning"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organisationName": COOPS_CONTACT_ORG,
                "contactInfo": {
                    "address": {
                        "deliveryPoint": COOPS_CONTACT_ADDRESS,
                        "electronicMailAddress": COOPS_CONTACT_EMAIL,
                    },
                    "onlineResource": {"linkage": COOPS_HOME},
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
        "characteristics": [
            {
                "name": "station_characteristics",
                "type": "DataRecord",
                "label": "Station Characteristics",
                "fields": char_items,
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
                     "label": "Publish Interval", "uom": {"code": "s"}, "value": 360.0},
                    {"type": "Text", "name": "data_source",
                     "definition": "http://sensorml.com/ont/swe/property/DataSource",
                     "label": "Data Source", "value": "CO-OPS Data API (datagetter)"},
                ],
            },
        ],
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _datastream_schema() -> dict:
    """SWE DataRecord schema for coastal observation datastream.

    CO-OPS fields (metric units via API request):
      water_level_m  - Observed water level above MLLW (m)
      prediction_m   - Predicted water level above MLLW (m)
      sigma_m        - Standard deviation of water level (m)
      air_temp_c     - Air temperature (°C)
      water_temp_c   - Water temperature (°C)
      wind_speed_ms  - Wind speed (m/s)
      wind_dir_deg   - Wind direction from (°T)
      wind_gust_ms   - Wind gust (m/s)
      pressure_hpa   - Barometric pressure (hPa / mb)
    """
    return {
        "outputName": DS_OUTPUT_NAME,
        "name": "Coastal Observation",
        "description": (
            "Combined water level, tide prediction, and coastal meteorological observation "
            "from a NOAA CO-OPS station. Water levels are 6-minute observations referenced "
            "to MLLW datum in metric units. Meteorological fields may be NaN if the station "
            "does not have the corresponding sensor."
        ),
        "documentation": [
            {"title": "CO-OPS Data API", "href": COOPS_API_DOC, "rel": "documentation"},
            {"title": "Measurement Specifications", "href": COOPS_MEASUREMENT_SPECS, "rel": "describedby"},
            {"title": "CO-OPS Glossary", "href": COOPS_GLOSSARY, "rel": "glossary"},
        ],
        "characteristics": [
            {"label": "Source Format", "value": "JSON via CO-OPS Data API (datagetter)"},
            {"label": "Nominal Availability", "value": "6-minute water levels; met data refreshed 6-minute"},
            {"label": "Quality Control", "value": "Real-time QC applied; verified data available after 1-2 months"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "CO-OPS Coastal Observation",
                "description": "Water level, tide prediction, and coastal meteorological data",
                "fields": [
                    {"type": "Time",     "name": "timestamp",        "label": "Observation Time",     "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "stationId",       "label": "Station ID",           "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Quantity", "name": "lat_deg",          "label": "Latitude",             "definition": "http://sensorml.com/ont/swe/property/GeodeticLatitude",    "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "lon_deg",          "label": "Longitude",            "definition": "http://sensorml.com/ont/swe/property/GeodeticLongitude",   "uom": {"code": "deg"}},
                    {"type": "Quantity", "name": "water_level_m",    "label": "Water Level (MLLW)",   "definition": "http://mmisw.org/ont/cf/parameter/sea_surface_height_above_reference_datum", "uom": {"code": "m"}},
                    {"type": "Quantity", "name": "prediction_m",     "label": "Tide Prediction (MLLW)", "definition": "http://mmisw.org/ont/cf/parameter/sea_surface_height_above_reference_datum", "uom": {"code": "m"}, "optional": True},
                    {"type": "Quantity", "name": "sigma_m",          "label": "Std Deviation",        "definition": "http://www.opengis.net/def/property/OGC/0/Uncertainty",    "uom": {"code": "m"},   "optional": True},
                    {"type": "Quantity", "name": "air_temp_c",       "label": "Air Temperature",      "definition": "http://sensorml.com/ont/swe/property/AirTemperature",      "uom": {"code": "Cel"}, "optional": True},
                    {"type": "Quantity", "name": "water_temp_c",     "label": "Water Temperature",    "definition": "http://sensorml.com/ont/swe/property/WaterTemperature",    "uom": {"code": "Cel"}, "optional": True},
                    {"type": "Quantity", "name": "wind_speed_ms",    "label": "Wind Speed",           "definition": "http://sensorml.com/ont/swe/property/WindSpeed",           "uom": {"code": "m/s"}, "optional": True},
                    {"type": "Quantity", "name": "wind_direction_deg", "label": "Wind Direction",     "definition": "http://sensorml.com/ont/swe/property/WindDirection",       "uom": {"code": "deg"}, "optional": True},
                    {"type": "Quantity", "name": "wind_gust_ms",     "label": "Wind Gust",            "definition": "http://sensorml.com/ont/swe/property/WindGust",            "uom": {"code": "m/s"}, "optional": True},
                    {"type": "Quantity", "name": "pressure_hpa",     "label": "Barometric Pressure",  "definition": "http://sensorml.com/ont/swe/property/AtmosphericPressure", "uom": {"code": "hPa"}, "optional": True},
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
            "name": "CO-OPS Coastal Demo Deployment",
            "description": (
                "Top-level CSAPI deployment grouping for NOAA CO-OPS coastal tide stations "
                "published by OSHConnect-Python. This grouping represents the demo / integration "
                "scope, not a single physical field deployment."
            ),
            "documentation": [
                {"title": "CO-OPS Home", "href": COOPS_HOME, "rel": "about"},
            ],
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
            "name": "CO-OPS Tide Stations",
            "description": (
                "Grouping deployment for curated CO-OPS coastal stations. Each child deployment "
                "links a station/system resource to the demo deployment tree."
            ),
            "documentation": [
                {"title": "CO-OPS Home", "href": COOPS_HOME, "rel": "about"},
                {"title": "CO-OPS Data API", "href": COOPS_API_DOC, "rel": "documentation"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str) -> dict:
    station_id = station["id"]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _deploy_uid(station_id),
            "featureType": "sosa:Deployment",
            "name": f"Tide Station {station_id} Feed",
            "description": f"CO-OPS tide station {station_id} ({station['name']}) observation feed.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(station_id),
                "title": f"CO-OPS {station_id}",
            },
            "links": [
                {"rel": "about", "title": "Station Home", "href": _station_page_url(station_id)},
                {"rel": "alternate", "title": "Water Levels", "href": _station_water_level_url(station_id)},
                {"rel": "alternate", "title": "Met Observations", "href": _station_met_url(station_id)},
            ],
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Bootstrap logic
# ═══════════════════════════════════════════════════════════════════════════

def clean_all(base_url: str, auth: str, stations: list[dict],
              *, dry_run: bool = False, stats: dict):
    """Delete all CO-OPS resources (reverse order)."""
    # Deployments (leaf → root)
    for st in reversed(stations):
        clean_resource(base_url, auth, "deployments", _deploy_uid(st["id"]),
                       dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID,
                   dry_run=dry_run, stats=stats)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID,
                   dry_run=dry_run, stats=stats)

    # Systems (datastreams deleted automatically via cascade)
    for st in reversed(stations):
        clean_resource(base_url, auth, "systems", _system_uid(st["id"]),
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
    print("  CO-OPS Coastal Observation — Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)} ({', '.join(s['id'] for s in stations)})")
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
    system_ids: dict[str, str] = {}

    for st in stations:
        uid = _system_uid(st["id"])

        stub = _system_stub(st, proc_id or "pending")
        sml = _system_sml(st)

        sys_id = ensure_system(base_url, auth, uid, stub, sml,
                               dry_run=dry_run, stats=stats,
                               force_sml=force_sml)
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
        description="Bootstrap CO-OPS coastal observation resources on the CSAPI server.")
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
