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
