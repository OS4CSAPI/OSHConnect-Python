# Drop-in constants and helper URL builders for `bootstrap_ndbc.py`

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


# Replacement `PROCEDURE_BODY`

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
            "NOAA",
            "NDBC",
            "buoy",
            "marine weather",
            "waves",
            "oceanographic",
            "realtime2",
            "surface observations",
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
            "upstream": "Realtime flat files from https://www.ndbc.noaa.gov/data/realtime2",
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


# Replacement `_system_stub(station, proc_id)`

def _system_stub(station: dict, proc_id: str) -> dict:
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


# Replacement `_system_sml(station)`

def _system_sml(station: dict) -> dict:
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
            }
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


# Metadata additions for `_datastream_schema()`

# Add / merge the following fields at the top level of the datastream body:
{
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
        ...
    }
}

# Optional improvement:
# Add a final optional text field in the result schema for source provenance, e.g.
{"type": "Text", "name": "source_url", "label": "Source URL", "optional": True}


# Suggested deployment metadata enrichments

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

# For each per-station deployment, add station-specific links:
"links": [
    {"rel": "about", "title": "NDBC Station Page", "href": _station_page_url(station_id)},
    {"rel": "alternate", "title": "Realtime Station Page", "href": _station_realtime_url(station_id)},
    {"rel": "alternate", "title": "Historical Station Page", "href": _station_history_url(station_id)},
]
