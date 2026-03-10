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
