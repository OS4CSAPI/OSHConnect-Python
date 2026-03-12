"""
Additional constants and helper URLs for publishers/usgs_eq/bootstrap_usgs_eq.py
"""

USGS_EQ_DETAIL_DOC = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson_detail.php"
USGS_EQ_LIFECYCLE = "https://earthquake.usgs.gov/earthquakes/feed/policy.php"
USGS_EQ_EVENT_TERMS = "https://earthquake.usgs.gov/data/comcat/data-eventterms.php"
USGS_EQ_FDSN_EVENT_API = "https://earthquake.usgs.gov/fdsnws/event/1/"

USGS_EQ_FEED_VARIANTS = {
    "all_hour": "All earthquakes, past hour",
    "all_day": "All earthquakes, past day",
    "all_week": "All earthquakes, past week",
    "all_month": "All earthquakes, past month",
    "significant_hour": "Significant earthquakes, past hour",
    "significant_day": "Significant earthquakes, past day",
    "significant_week": "Significant earthquakes, past week",
    "significant_month": "Significant earthquakes, past month",
    "1.0_hour": "Magnitude 1.0+, past hour",
    "2.5_day": "Magnitude 2.5+, past day",
    "4.5_week": "Magnitude 4.5+, past week",
}


def _summary_feed_url(variant: str) -> str:
    return f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{variant}.geojson"


def _detail_url(event_id: str) -> str:
    return f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/{event_id}.geojson"


def _fdsn_query_url(event_id: str) -> str:
    return f"https://earthquake.usgs.gov/fdsnws/event/1/query.geojson?format=geojson&eventid={event_id}"
