#!/usr/bin/env python3
"""
bootstrap_usgs_water.py -- Register USGS water monitoring resources on the OS4CSAPI server.

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
    +-- urn:os4csapi:deployment:usgs-water-stations:v1
       +-- urn:os4csapi:deployment:usgs-water-{nwisId}:v1  (platform@link -> system)
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


# ======================================================================
#  Configuration
# ======================================================================

VALID_TIME_START = "2026-01-01T00:00:00Z"

PROC_UID = "urn:os4csapi:procedure:usgs-water-observation:v1"

DEPLOY_ROOT_UID = "urn:os4csapi:deployment:usgs-water-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:usgs-water-stations:v1"

# Output names -- one datastream per parameter
DS_DISCHARGE_OUTPUT = "usgsDischarge"
DS_GAGE_HEIGHT_OUTPUT = "usgsGageHeight"

# USGS references
USGS_OGC_API = "https://api.waterdata.usgs.gov/ogcapi/v0/"
USGS_LEGACY_API = "https://waterservices.usgs.gov/nwis/iv/"
USGS_WATER_HOME = "https://waterdata.usgs.gov/"
USGS_API_DOCS = "https://api.waterdata.usgs.gov/ogcapi/v0/openapi?f=html"
USGS_NWIS_HELP = "https://help.waterdata.usgs.gov/faq/automated-retrievals"

# Enrichment: additional official references
USGS_COLLECTIONS_HTML = "https://api.waterdata.usgs.gov/ogcapi/v0/collections?f=html"
USGS_OGC_DOCS = "https://api.waterdata.usgs.gov/docs/ogcapi/"
USGS_LATEST_CONTINUOUS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous"
USGS_TIME_SERIES_METADATA = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/time-series-metadata"
USGS_COMBINED_METADATA = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/combined-metadata"
USGS_PARAMETER_CODES = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/parameter-codes"
USGS_STATISTIC_CODES = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/statistic-codes"
USGS_API_REGISTRATION = "https://api.usgs.gov/"

# Series semantics
STATISTIC_INSTANTANEOUS = "00011"
STATISTIC_INSTANTANEOUS_NAME = "Instantaneous"


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


def _latest_continuous_url(nwis_id: str, parameter_code: str) -> str:
    return (
        f"{USGS_LATEST_CONTINUOUS}/items"
        f"?monitoring_location_id=USGS-{nwis_id}"
        f"&parameter_code={parameter_code}"
        f"&limit=5"
    )


def _time_series_metadata_url(nwis_id: str, parameter_code: str) -> str:
    return (
        f"{USGS_TIME_SERIES_METADATA}/items"
        f"?monitoring_location_id=USGS-{nwis_id}"
        f"&parameter_code={parameter_code}"
        f"&limit=10"
    )


def _combined_metadata_url(nwis_id: str, parameter_code: str) -> str:
    return (
        f"{USGS_COMBINED_METADATA}/items"
        f"?monitoring_location_id=USGS-{nwis_id}"
        f"&parameter_code={parameter_code}"
        f"&limit=10"
    )


# ======================================================================
#  Resource definitions
# ======================================================================

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "USGS Water Observation v1",
        "description": (
            "Publishes curated real-time USGS water monitoring observations from the USGS Water "
            "Data OGC API. The current station set uses one system per monitoring location and two "
            "datastreams per station: discharge (00060) and gage height (00065). Runtime fetches "
            "instantaneous values, normalizes them into flat JSON result objects, and publishes one "
            "observation per station and parameter per cycle."
        ),
        "keywords": [
            "USGS",
            "NWIS",
            "water",
            "hydrology",
            "streamflow",
            "gage height",
            "monitoring location",
            "OGC API",
            "instantaneous values",
            "time-series metadata",
        ],
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
            {"title": "USGS Water Data Collections", "href": USGS_COLLECTIONS_HTML, "rel": "describedby"},
            {"title": "USGS Water Data OpenAPI", "href": USGS_API_DOCS, "rel": "describedby"},
            {"title": "USGS OGC API Long-Form Docs", "href": USGS_OGC_DOCS, "rel": "documentation"},
            {"title": "Latest Continuous Collection", "href": USGS_LATEST_CONTINUOUS, "rel": "collection"},
            {"title": "Time Series Metadata Collection", "href": USGS_TIME_SERIES_METADATA, "rel": "collection"},
            {"title": "Combined Metadata Collection", "href": USGS_COMBINED_METADATA, "rel": "collection"},
            {"title": "USGS Water Data Home", "href": USGS_WATER_HOME, "rel": "about"},
            {"title": "USGS NWIS Help", "href": USGS_NWIS_HELP, "rel": "related"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": "U.S. Geological Survey",
                "website": USGS_WATER_HOME,
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python",
            },
        ],
        "lineage": {
            "source": "U.S. Geological Survey / Water Data OGC API",
            "upstream": (
                "Monitoring-location metadata comes from the monitoring-locations collection. "
                "Observation values come from the USGS continuous or latest-continuous collections. "
                "Series semantics are interpreted with reference to the time-series-metadata and "
                "combined-metadata collections."
            ),
            "normalization": (
                "Publisher maps USGS properties.time to phenomenonTime, publishes the value into "
                "the parameter-specific result field, and carries qualifier and approval status "
                "into the CSAPI observation result body."
            ),
        },
        "usageConstraints": {
            "apiKeyNote": (
                "A USGS API key is recommended for higher request ceilings. Register at "
                "https://api.usgs.gov."
            ),
            "seriesSemanticsNote": (
                "This publisher's datastreams represent statistic_id 00011 instantaneous values. "
                "Time-series-metadata can also expose daily series for the same parameter code, "
                "so parameter_code alone should not be treated as a unique series identifier."
            ),
            "runtimeNote": (
                "The current runtime fetches the newest values from the continuous collection. "
                "The live latest-continuous collection is a recommended follow-on upgrade for "
                "latest-only polling."
            ),
            "disclaimer": (
                "USGS water data may be provisional and subject to revision. Data are released on "
                "the condition that neither the USGS nor the United States Government may be held "
                "liable for damages resulting from authorized or unauthorized use."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


def _system_stub(station: dict, proc_id: str) -> dict:
    """GeoJSON Feature stub for a USGS water monitoring station system."""
    nwis_id = station["nwisId"]
    site_type = station.get("siteType", station.get("siteTypeCode", "Stream"))

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _system_uid(nwis_id),
            "featureType": "sosa:Sensor",
            "name": f"USGS {nwis_id} - {station['name']}",
            "description": (
                f"USGS monitoring location {nwis_id} ({station['fullName']}) in "
                f"{station.get('county', '')}, {station['state']}. This system represents the "
                "curated station-level water observing resource published by OSHConnect-Python, "
                "with discharge and gage-height datastreams derived from the USGS Water Data OGC API."
            ),
            "typeOf@link": {"href": proc_id, "title": "USGS Water Observation v1"},
            "keywords": [
                "USGS",
                "NWIS",
                "water monitoring",
                "hydrology",
                site_type,
                nwis_id,
                station["stateAbbr"],
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    """SensorML body for rich system metadata."""
    nwis_id = station["nwisId"]
    drainage = station.get("drainageArea_sqmi")
    drainage_text = f"{drainage} sq mi" if drainage is not None else "Not available"
    altitude = station.get("altitude_ft")
    altitude_text = f"{altitude} ft" if altitude is not None else "Not available"

    characteristics_fields = [
        {
            "type": "Text",
            "name": "reporting_cadence",
            "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
            "label": "Reporting Cadence",
            "value": "Instantaneous values at approximately 15-minute intervals",
        },
        {
            "type": "Text",
            "name": "timezone",
            "definition": "http://sensorml.com/ont/swe/property/TimeZone",
            "label": "Station Timezone",
            "value": station.get("tz", "UTC"),
        },
        {
            "type": "Text",
            "name": "uses_daylight_savings",
            "definition": "http://sensorml.com/ont/swe/property/TimeZone",
            "label": "Uses Daylight Savings",
            "value": station.get("usesDaylightSavings", "Unknown"),
        },
        {
            "type": "Text",
            "name": "drainage_area",
            "definition": "http://sensorml.com/ont/swe/property/DrainageArea",
            "label": "Drainage Area",
            "value": drainage_text,
        },
        {
            "type": "Text",
            "name": "hydrologic_unit_code",
            "definition": "http://sensorml.com/ont/swe/property/HydrologicUnitCode",
            "label": "Hydrologic Unit Code",
            "value": station.get("huc", ""),
        },
        {
            "type": "Text",
            "name": "site_type",
            "definition": "http://sensorml.com/ont/swe/property/SensorType",
            "label": "Site Type",
            "value": station.get("siteType", station.get("siteTypeCode", "Unknown")),
        },
        {
            "type": "Text",
            "name": "altitude",
            "definition": "http://sensorml.com/ont/swe/property/Elevation",
            "label": "Station Altitude",
            "value": altitude_text,
        },
        {
            "type": "Text",
            "name": "vertical_datum",
            "definition": "http://sensorml.com/ont/swe/property/VerticalDatum",
            "label": "Vertical Datum",
            "value": station.get("verticalDatum", "Not available"),
        },
        {
            "type": "Text",
            "name": "horizontal_accuracy",
            "definition": "http://sensorml.com/ont/swe/property/PositionalAccuracy",
            "label": "Horizontal Accuracy",
            "value": station.get("horizontalAccuracyNote", "Not available"),
        },
        {
            "type": "Text",
            "name": "coordinate_method",
            "definition": "http://sensorml.com/ont/swe/property/Method",
            "label": "Coordinate Method",
            "value": station.get("horizontalMethodName", "Not available"),
        },
    ]

    if station.get("camId"):
        characteristics_fields.append({
            "type": "Text",
            "name": "nims_camera_id",
            "definition": "http://sensorml.com/ont/swe/property/AssociatedFacility",
            "label": "Associated NIMS Camera",
            "value": station["camId"],
        })

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(nwis_id),
        "uniqueId": _system_uid(nwis_id),
        "definition": "sosa:System",
        "label": f"USGS {nwis_id} - {station['name']}",
        "description": (
            f"USGS water monitoring station at {station['name']} (NWIS ID {nwis_id}). "
            f"Located in {station.get('county', '')}, {station['state']}. "
            "This CSAPI system represents the curated monitoring-location resource published by "
            "OSHConnect-Python. It exposes discharge and gage-height datastreams anchored to the "
            "USGS Water Data OGC API instantaneous series semantics."
        ),
        "keywords": [
            "USGS",
            "NWIS",
            "water",
            "hydrology",
            "streamflow",
            "gage height",
            "monitoring location",
            nwis_id,
            station["stateAbbr"],
        ],
        "identifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "Short Name",
                "value": f"USGS {nwis_id}",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/LongName",
                "label": "Long Name",
                "value": station["fullName"],
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/ModelNumber",
                "label": "NWIS Site Number",
                "value": nwis_id,
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "Agency Code",
                "value": station.get("agencyCode", "USGS"),
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "District Code",
                "value": station.get("districtCode", ""),
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/UniqueID",
                "label": "OS4CSAPI UID",
                "value": _system_uid(nwis_id),
            },
        ],
        "classifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/SensorType",
                "label": "Site Type",
                "value": station.get("siteType", station.get("siteTypeCode", "Unknown")),
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
                "label": "Network",
                "value": "USGS National Water Information System (NWIS)",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/SystemRole",
                "label": "Operator",
                "value": station.get("agencyName", "U.S. Geological Survey"),
            },
        ],
        "contacts": [
            {
                "role": "http://sensorml.com/ont/swe/property/Operator",
                "organisationName": station.get("agencyName", "U.S. Geological Survey"),
                "contactInfo": {
                    "website": USGS_WATER_HOME,
                },
            },
        ],
        "documents": [
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Monitoring Location",
                "description": f"USGS monitoring-location resource for site {nwis_id}.",
                "link": {
                    "href": station.get("monitoringLocationUrl", _monitoring_location_url(nwis_id)),
                    "type": "application/geo+json",
                },
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Latest Continuous - Discharge",
                "description": f"Latest discharge values for site {nwis_id}.",
                "link": {
                    "href": station.get("latestContinuous00060Url", _latest_continuous_url(nwis_id, "00060")),
                    "type": "application/geo+json",
                },
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Latest Continuous - Gage Height",
                "description": f"Latest gage-height values for site {nwis_id}.",
                "link": {
                    "href": station.get("latestContinuous00065Url", _latest_continuous_url(nwis_id, "00065")),
                    "type": "application/geo+json",
                },
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Time Series Metadata - Discharge",
                "description": f"Time-series metadata for discharge at site {nwis_id}.",
                "link": {
                    "href": station.get("timeSeries00060Url", _time_series_metadata_url(nwis_id, "00060")),
                    "type": "application/geo+json",
                },
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Time Series Metadata - Gage Height",
                "description": f"Time-series metadata for gage height at site {nwis_id}.",
                "link": {
                    "href": station.get("timeSeries00065Url", _time_series_metadata_url(nwis_id, "00065")),
                    "type": "application/geo+json",
                },
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "USGS Water Data OGC API",
                "description": "Official USGS Water Data OGC API documentation.",
                "link": {"href": USGS_API_DOCS, "type": "text/html"},
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
                "label": "Published Datastreams",
                "capabilities": [
                    {
                        "type": "Text",
                        "name": "supported_parameter_codes",
                        "definition": "http://sensorml.com/ont/swe/property/DataSource",
                        "label": "Supported Parameter Codes",
                        "value": ",".join(station.get("parameterCodes", [])),
                    },
                    {
                        "type": "Text",
                        "name": "statistic_series",
                        "definition": "http://sensorml.com/ont/swe/property/DataSource",
                        "label": "Published Statistic",
                        "value": f"{STATISTIC_INSTANTANEOUS} ({STATISTIC_INSTANTANEOUS_NAME})",
                    },
                    {
                        "type": "Text",
                        "name": "source_collections",
                        "definition": "http://sensorml.com/ont/swe/property/DataSource",
                        "label": "Primary Source Collections",
                        "value": "monitoring-locations, latest-continuous or continuous, time-series-metadata",
                    },
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
            "Instantaneous discharge (streamflow) observations for the station-specific "
            "USGS NWIS instantaneous series. This datastream represents parameter code "
            "00060 with statistic_id 00011. Qualifier and approval status are passed "
            "through from the upstream USGS Water Data API response."
        ),
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
            {"title": "Latest Continuous Collection", "href": USGS_LATEST_CONTINUOUS, "rel": "collection"},
            {"title": "Time Series Metadata Collection", "href": USGS_TIME_SERIES_METADATA, "rel": "collection"},
            {"title": "Statistic Code 00011", "href": f"{USGS_STATISTIC_CODES}/items/00011?f=json", "rel": "describedby"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "USGS Discharge Observation",
                "description": (
                    "Instantaneous discharge value with station identifier, qualifier, and approval status. "
                    "The time field named timestamp is populated from phenomenonTime and must not be included "
                    "inside the result body."
                ),
                "fields": [
                    {
                        "type": "Time",
                        "name": "timestamp",
                        "label": "Observation Time",
                        "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime",
                        "referenceTime": "1970-01-01T00:00:00Z",
                        "uom": {"code": "s"},
                    },
                    {
                        "type": "Text",
                        "name": "stationId",
                        "label": "NWIS Site ID",
                        "definition": "http://sensorml.com/ont/swe/property/StationID",
                    },
                    {
                        "type": "Quantity",
                        "name": "discharge_cfs",
                        "label": "Discharge",
                        "definition": "http://www.opengis.net/def/property/OGC/0/Discharge",
                        "uom": {"code": "ft3/s"},
                    },
                    {
                        "type": "Text",
                        "name": "qualifier",
                        "label": "Data Qualifier",
                        "definition": "http://sensorml.com/ont/swe/property/QualityFlag",
                    },
                    {
                        "type": "Text",
                        "name": "approvalStatus",
                        "label": "Approval Status",
                        "definition": "http://sensorml.com/ont/swe/property/ApprovalStatus",
                    },
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
            "Instantaneous gage-height observations for the station-specific USGS NWIS "
            "instantaneous series. This datastream represents parameter code 00065 with "
            "statistic_id 00011. Qualifier and approval status are passed through from the "
            "upstream USGS Water Data API response."
        ),
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
            {"title": "Latest Continuous Collection", "href": USGS_LATEST_CONTINUOUS, "rel": "collection"},
            {"title": "Time Series Metadata Collection", "href": USGS_TIME_SERIES_METADATA, "rel": "collection"},
            {"title": "Statistic Code 00011", "href": f"{USGS_STATISTIC_CODES}/items/00011?f=json", "rel": "describedby"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "USGS Gage Height Observation",
                "description": (
                    "Instantaneous gage-height value with station identifier, qualifier, and approval status. "
                    "The time field named timestamp is populated from phenomenonTime and must not be included "
                    "inside the result body."
                ),
                "fields": [
                    {
                        "type": "Time",
                        "name": "timestamp",
                        "label": "Observation Time",
                        "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime",
                        "referenceTime": "1970-01-01T00:00:00Z",
                        "uom": {"code": "s"},
                    },
                    {
                        "type": "Text",
                        "name": "stationId",
                        "label": "NWIS Site ID",
                        "definition": "http://sensorml.com/ont/swe/property/StationID",
                    },
                    {
                        "type": "Quantity",
                        "name": "gage_height_ft",
                        "label": "Gage Height",
                        "definition": "http://www.opengis.net/def/property/OGC/0/GageHeight",
                        "uom": {"code": "ft"},
                    },
                    {
                        "type": "Text",
                        "name": "qualifier",
                        "label": "Data Qualifier",
                        "definition": "http://sensorml.com/ont/swe/property/QualityFlag",
                    },
                    {
                        "type": "Text",
                        "name": "approvalStatus",
                        "label": "Approval Status",
                        "definition": "http://sensorml.com/ont/swe/property/ApprovalStatus",
                    },
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
                "Top-level CSAPI deployment grouping for curated USGS water monitoring resources "
                "published by OSHConnect-Python. This grouping covers station-centric systems and "
                "their discharge and gage-height datastreams sourced from the USGS Water Data OGC API."
            ),
            "documentation": [
                {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
                {"title": "USGS Collections", "href": USGS_COLLECTIONS_HTML, "rel": "describedby"},
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
                "Grouping deployment for the curated multi-state USGS monitoring-location set used "
                "by the OS4CSAPI demonstration. Each child deployment pairs one curated USGS station "
                "with one CSAPI system and two datastreams."
            ),
            "documentation": [
                {"title": "Monitoring Locations Collection", "href": f"{USGS_OGC_API}collections/monitoring-locations", "rel": "collection"},
                {"title": "Time Series Metadata Collection", "href": USGS_TIME_SERIES_METADATA, "rel": "collection"},
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
                f"CSAPI deployment node for USGS monitoring location {nwis_id} ({station['name']}). "
                "This node anchors the station system and its discharge and gage-height datastreams "
                "to the curated USGS Water Data OGC API publisher model."
            ),
            "externalLinks": [
                {
                    "href": station.get("monitoringLocationUrl", _monitoring_location_url(nwis_id)),
                    "title": "USGS Monitoring Location",
                    "rel": "canonical",
                },
                {
                    "href": station.get("latestContinuous00060Url", _latest_continuous_url(nwis_id, "00060")),
                    "title": "Latest Continuous - Discharge",
                    "rel": "latest-version",
                },
                {
                    "href": station.get("latestContinuous00065Url", _latest_continuous_url(nwis_id, "00065")),
                    "title": "Latest Continuous - Gage Height",
                    "rel": "latest-version",
                },
            ],
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(nwis_id),
                "title": f"USGS {nwis_id}",
            },
        },
    }


# ======================================================================
#  Bootstrap logic
# ======================================================================

def clean_all(base_url: str, auth: str, stations: list[dict],
              *, dry_run: bool = False, stats: dict):
    """Delete all USGS water resources (reverse order)."""
    # Deployments (leaf -> root)
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
    print("  USGS Water Monitoring -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)} ({', '.join(s['nwisId'] for s in stations)})")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}")
    print()

    # -- Clean --
    if clean or clean_only:
        print("  -- Cleaning existing resources --")
        clean_all(base_url, auth, stations, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    # -- Procedure --
    print("  -- Procedures --")
    proc_id = ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_BODY,
                               dry_run=dry_run, stats=stats)

    # -- Systems + Datastreams --
    print("  -- Systems + Datastreams --")
    system_ids: dict[str, str] = {}   # nwisId -> server ID

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

    # -- Deployment tree --
    print("  -- Deployments --")
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


# ======================================================================
#  CLI
# ======================================================================

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
