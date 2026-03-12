"""
Datastream schema candidates for publishers/usgs_eq/bootstrap_usgs_eq.py
"""

ENRICHED_DATASTREAM_DOCUMENTATION = [
    {"title": "GeoJSON Summary Feed", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
    {"title": "GeoJSON Detail Feed", "href": USGS_EQ_DETAIL_DOC, "rel": "documentation"},
    {"title": "Feed Lifecycle Policy", "href": USGS_EQ_LIFECYCLE, "rel": "policy"},
    {"title": "Event Terms", "href": USGS_EQ_EVENT_TERMS, "rel": "describedby"},
    {"title": "FDSN Event API", "href": USGS_EQ_FDSN_EVENT_API, "rel": "service"},
]

ENRICHED_DATASTREAM_CHARACTERISTICS = [
    {"label": "Observation Model", "value": "One observation per earthquake event"},
    {"label": "Default Runtime Surface", "value": "GeoJSON summary feed"},
    {"label": "Selective Enrichment Surface", "value": "GeoJSON detail feed and FDSN query.geojson"},
    {"label": "Coverage", "value": "Global"},
    {"label": "Dedupe", "value": "Use (eventId, updatedTime) to skip unchanged events and republish revisions"},
    {"label": "Omitted But Available Summary Fields", "value": "url, sig, alert, tsunami, net, types, nst, dmin, rms, gap"},
]

CURRENT_SAFE_RESULT_FIELDS = [
    "eventId",
    "magnitude",
    "magType",
    "place",
    "eventTime",
    "updatedTime",
    "latitude",
    "longitude",
    "depth_km",
    "status",
    "eventType",
    "title",
    "detailUrl",
]

OPTIONAL_EXTENDED_RESULT_FIELDS = [
    "eventPageUrl",
    "significance",
    "alertLevel",
    "tsunami",
    "network",
    "numStations",
    "minimumDistance",
    "rms",
    "gap",
]
