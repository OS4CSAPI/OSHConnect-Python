"""
Deployment metadata candidates for publishers/usgs_eq/bootstrap_usgs_eq.py
"""

ENRICHED_ROOT_DEPLOYMENT_NOTES = [
    {"rel": "about", "title": "USGS Earthquake Hazards Program", "href": USGS_EQ_HOME},
    {"rel": "documentation", "title": "GeoJSON Summary Feed Docs", "href": USGS_EQ_FEED_DOC},
    {"rel": "documentation", "title": "GeoJSON Detail Feed Docs", "href": USGS_EQ_DETAIL_DOC},
    {"rel": "policy", "title": "Feed Lifecycle Policy", "href": USGS_EQ_LIFECYCLE},
]

ENRICHED_FEED_DEPLOYMENT_NOTES = [
    {"rel": "documentation", "title": "GeoJSON Summary Feed Docs", "href": USGS_EQ_FEED_DOC},
    {"rel": "documentation", "title": "GeoJSON Detail Feed Docs", "href": USGS_EQ_DETAIL_DOC},
    {"rel": "describedby", "title": "Event Terms", "href": USGS_EQ_EVENT_TERMS},
    {"rel": "service", "title": "FDSN Event API", "href": USGS_EQ_FDSN_EVENT_API},
]

ENRICHED_FEED_DEPLOYMENT_DESCRIPTION = (
    "Configured USGS earthquake feed-adapter deployment. Polls one official "
    "USGS GeoJSON summary feed variant on a fixed cadence and publishes one "
    "observation per earthquake event. The deployment documents the detail "
    "feed and FDSN event service as optional enrichment companions rather than "
    "baseline polling dependencies."
)
