# Metadata additions for `_datastream_schema()`

{
    "outputName": DS_OUTPUT_NAME,
    "name": "Aircraft State Vectors",
    "description": (
        "Normalized OpenSky aircraft state vectors. Each observation represents one aircraft "
        "inside the configured bounding box at one upstream observation timestamp. The publisher "
        "polls the OpenSky REST API, expands the array-based payload into named fields, and posts "
        "one CSAPI observation per aircraft record."
    ),
    "documentation": [
        {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
        {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
        {"title": "About OpenSky", "href": OPENSKY_ABOUT, "rel": "about"},
    ],
    "characteristics": [
        {"label": "Observation Model", "value": "One observation per aircraft per cycle"},
        {"label": "Coverage Filter", "value": "Bounding-box filter applied at the source API"},
        {"label": "Null Handling", "value": "Nullable numeric values are normalized to JSON-safe `NaN` strings by the current publisher"},
        {"label": "Position Source Vocabulary", "value": _position_source_summary()},
        {"label": "Deduplication", "value": "Repeated aircraft states with unchanged timestamps are skipped"},
    ],
    "schema": {
        "obsFormat": "application/om+json",
        "...": "Keep the existing resultSchema field list unchanged unless you also update the runtime publisher."
    }
}
