# Enriched procedure body candidate

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
            "time-series metadata"
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
            {"title": "USGS NWIS Help", "href": USGS_NWIS_HELP, "rel": "related"}
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": "U.S. Geological Survey",
                "website": USGS_WATER_HOME
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python"
            }
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
            )
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
            )
        },
        "validTime": [VALID_TIME_START, ".."]
    }
}
