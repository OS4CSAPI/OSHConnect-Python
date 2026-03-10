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
BUOYCAM_PROC_UID = "urn:os4csapi:procedure:ndbc:buoycam-imagery:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:ndbc-buoy-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:ndbc-buoys:v1"

DS_OUTPUT_NAME = "ndbcBuoyObs"
BUOYCAM_DS_OUTPUT_NAME = "ndbcBuoyCamImage"

# BuoyCAM-specific URLs
NDBC_BUOYCAM_HOME = "https://www.ndbc.noaa.gov/buoycams.shtml"
NDBC_BUOYCAM_STATUS = "https://www.ndbc.noaa.gov/buoycam_status.php"
BUOYCAM_CACHE_BASE = "https://os4csapi-osh.duckdns.org/buoycam"

# ── NDBC Official URLs ────────────────────────────────────────────────────
NDBC_HOME = "https://www.ndbc.noaa.gov/"
NDBC_WEB_DATA_GUIDE = "https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf"
NDBC_RT_DATA_DOC = "https://www.ndbc.noaa.gov/faq/rt_data_access.shtml"
NDBC_MEAS_DESC = "https://www.ndbc.noaa.gov/faq/measdes.shtml"
NDBC_STATUS_REPORT = "https://www.ndbc.noaa.gov/wstat.shtml"
NDBC_STATION_PAGE_BASE = "https://www.ndbc.noaa.gov/station_page.php?station="
NDBC_STATION_REALTIME_BASE = "https://www.ndbc.noaa.gov/station_realtime.php?station="
NDBC_STATION_HISTORY_BASE = "https://www.ndbc.noaa.gov/station_history.php?station="
NDBC_REALTIME_TEXT_BASE = "https://www.ndbc.noaa.gov/data/realtime2"
NDBC_BUOYCAM_FAQ = "https://www.ndbc.noaa.gov/faq/buoycamlinks.shtml"
NDBC_BUOYCAM_BASE = "https://www.ndbc.noaa.gov/buoycam.php?station="
NDBC_NETCDF = "https://dods.ndbc.noaa.gov/"

NDBC_CONTACT_EMAIL = "webmaster.ndbc@noaa.gov"
NDBC_CONTACT_ORG = "National Data Buoy Center"
NDBC_CONTACT_ADDRESS = "Building 3205, Stennis Space Center, MS 39529"


def _station_page_url(station_id: str) -> str:
    return f"{NDBC_STATION_PAGE_BASE}{station_id}"


def _station_realtime_url(station_id: str) -> str:
    return f"{NDBC_STATION_REALTIME_BASE}{station_id}"


def _station_history_url(station_id: str) -> str:
    return f"{NDBC_STATION_HISTORY_BASE}{station_id}"


def _station_realtime_text_url(station_id: str) -> str:
    return f"{NDBC_REALTIME_TEXT_BASE}/{station_id}.txt"


def _station_buoycam_url(station_id: str) -> str:
    return f"{NDBC_BUOYCAM_BASE}{station_id}"


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
            "Publishes real-time marine meteorological and oceanographic observations from NOAA's "
            "National Data Buoy Center (NDBC). Observations are sourced from NDBC realtime flat files, "
            "normalized into a flat JSON result object, and published to CSAPI. Realtime files generally "
            "represent the last 45 days of data that have undergone automated quality checks; most stations "
            "report hourly and much of the data is typically available by about 25 minutes after the hour."
        ),
        "keywords": [
            "NOAA", "NDBC", "buoy", "marine weather", "waves",
            "oceanographic", "realtime2", "surface observations",
        ],
        "documentation": [
            {"title": "NDBC Home", "href": NDBC_HOME, "rel": "about"},
            {"title": "NDBC Web Data Guide", "href": NDBC_WEB_DATA_GUIDE, "rel": "documentation"},
            {"title": "NDBC Realtime Data Retrieval FAQ", "href": NDBC_RT_DATA_DOC, "rel": "documentation"},
            {"title": "NDBC Measurement Descriptions and Units", "href": NDBC_MEAS_DESC, "rel": "describedby"},
            {"title": "NDBC Station Status Report", "href": NDBC_STATUS_REPORT, "rel": "status"},
            {"title": "NDBC BuoyCAM FAQ", "href": NDBC_BUOYCAM_FAQ, "rel": "related"},
            {"title": "NDBC NetCDF / THREDDS Access", "href": NDBC_NETCDF, "rel": "alternate"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": NDBC_CONTACT_ORG,
                "website": NDBC_HOME,
                "email": NDBC_CONTACT_EMAIL,
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python",
            },
        ],
        "lineage": {
            "source": "NOAA / National Data Buoy Center",
            "upstream": f"Realtime flat files from {NDBC_REALTIME_TEXT_BASE}",
            "normalization": (
                "Publisher parses NDBC realtime fields and emits a flat JSON result with marine "
                "weather and wave values using source units documented by NDBC."
            ),
        },
        "usageConstraints": {
            "sourceProtocol": "HTTPS",
            "sourceFormat": "Whitespace-delimited realtime flat files",
            "rateLimitNote": "NDBC asks users to limit retrievals to a minimal level.",
            "qualityControlNote": (
                "Realtime files generally contain the last 45 days of data that have undergone "
                "automated quality checks; historical files reflect additional post-processing."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _system_stub(station: dict, proc_id: str) -> dict:
    """GeoJSON Feature stub for a NDBC buoy system."""
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
            "name": f"NDBC {station_id} — {station['name']}",
            "description": (
                f"NOAA NDBC buoy station {station_id} at {station['name']}. "
                f"Platform type: {station.get('platform_type', 'buoy/platform unknown')}. "
                f"Water depth: {station.get('water_depth_m', '?')} m."
            ),
            "typeOf@link": {"href": proc_id, "title": "NDBC Buoy Observation v1"},
            "links": [
                {"rel": "about", "title": "NDBC Station Page", "href": _station_page_url(station_id)},
                {"rel": "alternate", "title": "Realtime Station Page", "href": _station_realtime_url(station_id)},
                {"rel": "alternate", "title": "Historical Station Page", "href": _station_history_url(station_id)},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    """SensorML body for rich system metadata."""
    station_id = station["id"]
    owner = station.get("owner", "National Data Buoy Center")
    platform_type = station.get("platform_type", "Buoy / marine observing platform")
    payload_type = station.get("payload_type", "Unknown")

    characteristics = [
        {"label": "Owner / Maintainer", "value": owner},
        {"label": "Platform Type", "value": platform_type},
        {"label": "Payload Type", "value": payload_type},
    ]
    if "site_elevation_m" in station:
        characteristics.append({"label": "Site Elevation (m)", "value": station["site_elevation_m"]})
    if "air_temp_height_m" in station:
        characteristics.append({"label": "Air Temp Height (m)", "value": station["air_temp_height_m"]})
    if "anemometer_height_m" in station:
        characteristics.append({"label": "Anemometer Height (m)", "value": station["anemometer_height_m"]})
    if "barometer_height_m" in station:
        characteristics.append({"label": "Barometer Height (m)", "value": station["barometer_height_m"]})
    if "sea_temp_depth_m" in station:
        characteristics.append({"label": "Sea Temp Depth (m)", "value": station["sea_temp_depth_m"]})
    if "water_depth_m" in station:
        characteristics.append({"label": "Water Depth (m)", "value": station["water_depth_m"]})
    if "watch_circle_radius_yd" in station:
        characteristics.append({"label": "Watch Circle Radius (yd)", "value": station["watch_circle_radius_yd"]})
    if station.get("has_buoycam"):
        characteristics.append({"label": "BuoyCAM", "value": _station_buoycam_url(station_id)})

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station_id),
        "uniqueId": _system_uid(station_id),
        "label": f"NDBC {station_id} — {station['name']}",
        "description": (
            f"Marine observing platform at {station['name']} ({station_id}) operated by NOAA's "
            f"National Data Buoy Center. This resource represents the station as exposed through "
            f"NDBC realtime and station web resources."
        ),
        "identifiers": [
            {"label": "OS4CSAPI UID", "value": _system_uid(station_id)},
            {"label": "NDBC Station Identifier", "value": station_id},
        ],
        "classifiers": [
            {"label": "System Type", "value": platform_type},
            {"label": "Operator", "value": owner},
            {"label": "Program", "value": "NOAA National Data Buoy Center"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": owner,
                "website": NDBC_HOME,
                "email": NDBC_CONTACT_EMAIL,
            },
        ],
        "documentation": [
            {"name": "NDBC Station Page", "url": _station_page_url(station_id)},
            {"name": "Realtime Station Page", "url": _station_realtime_url(station_id)},
            {"name": "Historical Station Page", "url": _station_history_url(station_id)},
            {"name": "Realtime Flat File", "url": _station_realtime_text_url(station_id)},
            {"name": "Measurement Descriptions and Units", "url": NDBC_MEAS_DESC},
            {"name": "Realtime Data Retrieval FAQ", "url": NDBC_RT_DATA_DOC},
            {"name": "Station Status Report", "url": NDBC_STATUS_REPORT},
            {"name": "BuoyCAM FAQ", "url": NDBC_BUOYCAM_FAQ},
        ],
        "characteristics": characteristics,
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
        "description": (
            "Latest NDBC buoy observation for a station. Source values originate from NDBC realtime "
            "flat files and are normalized by the publisher into a flat JSON result object for CSAPI."
        ),
        "documentation": [
            {"title": "NDBC Web Data Guide", "href": NDBC_WEB_DATA_GUIDE, "rel": "documentation"},
            {"title": "NDBC Realtime Data Retrieval FAQ", "href": NDBC_RT_DATA_DOC, "rel": "documentation"},
            {"title": "NDBC Measurement Descriptions and Units", "href": NDBC_MEAS_DESC, "rel": "describedby"},
        ],
        "characteristics": [
            {"label": "Source Format", "value": "NDBC realtime2 flat file"},
            {"label": "Nominal Availability", "value": "Most stations hourly; much data typically available by ~25 minutes after the hour"},
            {"label": "Quality Control", "value": "Realtime files reflect automated QC; historical data reflect additional post-processing"},
        ],
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


# ═══════════════════════════════════════════════════════════════════════════
#  BuoyCAM resource definitions
# ═══════════════════════════════════════════════════════════════════════════

BUOYCAM_PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": BUOYCAM_PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "NDBC BuoyCAM Imagery v1",
        "description": (
            "Publishes cached BuoyCAM imagery from NOAA NDBC buoy-mounted cameras. "
            "The publisher periodically polls each station's latest-image endpoint, "
            "fetches the JPEG when a new image is detected (via SHA-256 hash comparison), "
            "caches the image to an immutable URL, and publishes an observation record "
            "referencing that cached URL. BuoyCAMs are daylight-only; image frequency varies "
            "but status updates typically occur every 30-60 minutes during daylight hours."
        ),
        "keywords": [
            "NOAA", "NDBC", "buoy", "BuoyCAM", "camera", "imagery",
            "marine", "ocean", "visual", "JPEG",
        ],
        "documentation": [
            {"title": "NDBC BuoyCAM Overview", "href": NDBC_BUOYCAM_HOME, "rel": "about"},
            {"title": "NDBC BuoyCAM FAQ / Latest Image Links", "href": NDBC_BUOYCAM_FAQ, "rel": "documentation"},
            {"title": "NDBC BuoyCAM Status Page", "href": NDBC_BUOYCAM_STATUS, "rel": "status"},
            {"title": "NDBC Station Page Pattern", "href": NDBC_STATION_PAGE_BASE, "rel": "describedby"},
            {"title": "NDBC Home", "href": NDBC_HOME, "rel": "about"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": NDBC_CONTACT_ORG,
                "website": NDBC_HOME,
                "email": NDBC_CONTACT_EMAIL,
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python",
            },
        ],
        "lineage": {
            "source": "NOAA / National Data Buoy Center — BuoyCAM program",
            "upstream": "Latest-image JPEG endpoint per station via NDBC BuoyCAM",
            "normalization": (
                "Publisher fetches latest JPEG, computes SHA-256 hash for deduplication, "
                "caches the image to an immutable URL on the OS4CSAPI static host, and "
                "publishes a JSON observation record referencing the cached image URL."
            ),
        },
        "usageConstraints": {
            "sourceProtocol": "HTTPS",
            "sourceFormat": "image/jpeg",
            "rateLimitNote": "Publisher polls at 15-minute intervals to align with NDBC refresh cadence.",
            "qualityControlNote": (
                "BuoyCAMs are daylight-only. Images may be stale at night or during outages. "
                "The publisher only publishes when a genuinely new image is detected."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _buoycam_datastream_schema() -> dict:
    """SWE DataRecord schema for BuoyCAM image-reference datastream."""
    return {
        "outputName": BUOYCAM_DS_OUTPUT_NAME,
        "name": "BuoyCAM Image",
        "description": (
            "Each observation represents one fetched BuoyCAM image frame. The result is a "
            "JSON record containing the immutable cached image URL, hash, size, and camera "
            "status — not raw binary image data. Images are cached to an immutable URL so "
            "historical observations remain visually stable."
        ),
        "documentation": [
            {"title": "NDBC BuoyCAM Overview", "href": NDBC_BUOYCAM_HOME, "rel": "about"},
            {"title": "NDBC BuoyCAM FAQ", "href": NDBC_BUOYCAM_FAQ, "rel": "documentation"},
            {"title": "NDBC BuoyCAM Status", "href": NDBC_BUOYCAM_STATUS, "rel": "status"},
        ],
        "characteristics": [
            {"label": "Source Format", "value": "image/jpeg from NDBC BuoyCAM latest-image endpoint"},
            {"label": "Storage Mode", "value": "cached-immutable (publisher caches each image to a unique URL)"},
            {"label": "Nominal Refresh", "value": "Every 30-60 minutes during daylight; publisher polls every 15 minutes"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "BuoyCAM Image Reference",
                "description": "Cached BuoyCAM image metadata and immutable URL",
                "fields": [
                    {"type": "Time",     "name": "timestamp",        "label": "Fetch Time",            "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text",     "name": "stationId",       "label": "Station ID",            "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text",     "name": "imageUrl",        "label": "Cached Image URL",      "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"},
                    {"type": "Text",     "name": "mediaType",       "label": "Media Type",            "definition": "http://purl.org/dc/elements/1.1/format"},
                    {"type": "Text",     "name": "cameraStatus",    "label": "Camera Status",         "definition": "http://sensorml.com/ont/swe/property/SystemStatus"},
                    {"type": "Text",     "name": "sha256",          "label": "Image SHA-256",         "definition": "http://www.opengis.net/def/property/OGC/0/Checksum"},
                    {"type": "Quantity", "name": "contentLength",   "label": "Image Size (bytes)",    "definition": "http://purl.org/dc/terms/extent",  "uom": {"code": "By"}},
                    {"type": "Text",     "name": "latestImageUrl",  "label": "NDBC Latest Image URL", "definition": "http://www.opengis.net/def/property/OGC/0/SourceURL"},
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
            "name": "NDBC Buoy Demo Deployment",
            "description": (
                "Top-level CSAPI deployment grouping for NOAA NDBC buoy stations published by "
                "OSHConnect-Python. This grouping represents the demo / integration scope, not a "
                "single physical field deployment."
            ),
            "documentation": [
                {"title": "NDBC Home", "href": NDBC_HOME, "rel": "about"},
                {"title": "NDBC Station Status Report", "href": NDBC_STATUS_REPORT, "rel": "status"},
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
            "name": "NDBC Buoy Stations",
            "description": (
                "Grouping deployment for curated NDBC buoy stations. Each child deployment links a "
                "station platform/system resource to the demo deployment tree."
            ),
            "documentation": [
                {"title": "NDBC Home", "href": NDBC_HOME, "rel": "about"},
                {"title": "NDBC Web Data Guide", "href": NDBC_WEB_DATA_GUIDE, "rel": "documentation"},
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
            "name": f"Buoy {station_id} Feed",
            "description": f"NDBC buoy {station_id} ({station['name']}) observation feed.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(station_id),
                "title": f"NDBC {station_id}",
            },
            "links": [
                {"rel": "about", "title": "NDBC Station Page", "href": _station_page_url(station_id)},
                {"rel": "alternate", "title": "Realtime Station Page", "href": _station_realtime_url(station_id)},
                {"rel": "alternate", "title": "Historical Station Page", "href": _station_history_url(station_id)},
            ],
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

    # Systems (datastreams deleted automatically via cascade)
    for st in reversed(stations):
        clean_resource(base_url, auth, "systems", _system_uid(st["id"]),
                       dry_run=dry_run, stats=stats, cascade=True)

    # Procedures
    clean_resource(base_url, auth, "procedures", BUOYCAM_PROC_UID,
                   dry_run=dry_run, stats=stats)
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

    # ── Procedures ────────────────────────────────────────────────────
    print("  ── Procedures ──")
    proc_id = ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_BODY,
                               dry_run=dry_run, stats=stats)
    buoycam_proc_id = ensure_procedure(base_url, auth, BUOYCAM_PROC_UID,
                                       BUOYCAM_PROCEDURE_BODY,
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

            # BuoyCAM datastream (only for camera-equipped stations)
            if st.get("has_buoycam"):
                ensure_datastream(base_url, auth, sys_id or "pending",
                                  BUOYCAM_DS_OUTPUT_NAME,
                                  _buoycam_datastream_schema(),
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
