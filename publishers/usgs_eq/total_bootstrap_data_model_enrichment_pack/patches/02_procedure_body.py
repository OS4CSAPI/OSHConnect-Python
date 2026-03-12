"""
Procedure metadata candidates for publishers/usgs_eq/bootstrap_usgs_eq.py
"""

ENRICHED_PROCEDURE_DOCUMENTATION = [
    {"title": "USGS Earthquake Hazards Program", "href": USGS_EQ_HOME, "rel": "about"},
    {"title": "GeoJSON Summary Feed", "href": USGS_EQ_FEED_DOC, "rel": "documentation"},
    {"title": "GeoJSON Detail Feed", "href": USGS_EQ_DETAIL_DOC, "rel": "documentation"},
    {"title": "Feed Lifecycle Policy", "href": USGS_EQ_LIFECYCLE, "rel": "policy"},
    {"title": "ComCat Documentation", "href": USGS_EQ_GLOSSARY, "rel": "describedby"},
    {"title": "Event Terms", "href": USGS_EQ_EVENT_TERMS, "rel": "describedby"},
    {"title": "FDSN Event API", "href": USGS_EQ_FDSN_EVENT_API, "rel": "service"},
]

ENRICHED_PROCEDURE_DESCRIPTION = (
    "Procedure describing how the OSHConnect-Python USGS earthquake publisher "
    "polls an official USGS GeoJSON summary feed, normalizes each feature into "
    "one CSAPI observation, and exposes a per-event detail link for richer "
    "drill-down. The baseline runtime uses the summary feed only; detail-feed "
    "and FDSN resources are documented as selective enrichment companions."
)

ENRICHED_PROCEDURE_CHARACTERISTICS = [
    {"label": "Observation Pattern", "value": "Pattern C feed adapter"},
    {"label": "Default Feed Variant", "value": "all_day"},
    {"label": "Variant Strategy", "value": "Feed variant is configurable and should be treated as runtime policy, not a different data model"},
    {"label": "Detail Enrichment Policy", "value": "Optional and selective; not required for every polling cycle"},
]
