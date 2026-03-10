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
