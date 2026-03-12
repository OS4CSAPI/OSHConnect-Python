"""
System metadata candidates for publishers/usgs_eq/bootstrap_usgs_eq.py
"""

ENRICHED_SYSTEM_DOCUMENTS = [
    {"name": "USGS Earthquake Hazards Program", "description": "Program home", "link": {"href": USGS_EQ_HOME}},
    {"name": "GeoJSON Summary Feed Documentation", "description": "Summary feed format and variant documentation", "link": {"href": USGS_EQ_FEED_DOC}},
    {"name": "GeoJSON Detail Feed Documentation", "description": "Detail feed structure and product documentation", "link": {"href": USGS_EQ_DETAIL_DOC}},
    {"name": "Feed Lifecycle Policy", "description": "Production feed availability and deprecation policy", "link": {"href": USGS_EQ_LIFECYCLE}},
    {"name": "ComCat Documentation", "description": "Catalog and product documentation", "link": {"href": USGS_EQ_GLOSSARY}},
    {"name": "Event Terms", "description": "Official field semantics", "link": {"href": USGS_EQ_EVENT_TERMS}},
    {"name": "FDSN Event API", "description": "Official query interface for targeted retrieval and future backfill", "link": {"href": USGS_EQ_FDSN_EVENT_API}},
]

ENRICHED_SYSTEM_CHARACTERISTICS = [
    {
        "name": "feed_surface",
        "type": "DataRecord",
        "label": "Feed Surface",
        "fields": [
            {"type": "Text", "name": "runtime_surface", "label": "Runtime Surface", "value": "GeoJSON summary feed"},
            {"type": "Text", "name": "companion_surface", "label": "Companion Surface", "value": "GeoJSON detail feed and FDSN query.geojson"},
            {"type": "Text", "name": "modeling_note", "label": "Modeling Note", "value": "The system is a global feed adapter and not a physical seismic station"},
        ],
    },
    {
        "name": "feed_lifecycle",
        "type": "DataRecord",
        "label": "Feed Lifecycle",
        "fields": [
            {"type": "Text", "name": "production_availability", "label": "Production Availability", "value": "Official policy states production feeds remain available for at least six months in production or deprecated form"},
            {"type": "Text", "name": "deprecation_notice", "label": "Deprecation Notice", "value": "Official policy states at least 30 days notice before deprecation and removal"},
        ],
    },
]

OPTIONAL_SYSTEM_CAPABILITIES = [
    {
        "type": "Text",
        "name": "enrichment_policy",
        "label": "Enrichment Policy",
        "value": "Summary feed by default, detail and FDSN only when stronger per-event context is needed",
    },
]
