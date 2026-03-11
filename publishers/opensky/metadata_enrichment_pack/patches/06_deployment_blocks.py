# Suggested deployment metadata enrichments

def _deploy_root(config: dict) -> dict:
    bbox = config["bounding_box"]
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
        },
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "Airspace Tracking Demo Deployment",
            "description": (
                "Top-level CSAPI deployment grouping for feed-adapter aircraft tracking resources "
                "published by OSHConnect-Python. This is a conceptual deployment group for the demo "
                "story, not a single physical field installation."
            ),
            "documentation": [
                {"title": "OpenSky Network", "href": OPENSKY_HOME, "rel": "about"},
                {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
                {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_feed(config: dict, system_server_id: str) -> dict:
    bbox = config["bounding_box"]
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
        },
        "properties": {
            "uid": DEPLOY_FEED_UID,
            "featureType": "sosa:Deployment",
            "name": "OpenSky ADS-B Feed",
            "description": (
                f"Configured OpenSky feed-adapter deployment for {_bbox_label(config)}. "
                f"Publishes one observation per aircraft state at {config.get('cadence_seconds', 300)}s cadence. "
                f"Current auth mode: {config.get('auth', {}).get('mode', 'anonymous')}."
            ),
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": SYSTEM_UID,
                "title": "OpenSky ADS-B Feed - Southern Arizona",
            },
            "links": [
                {"rel": "about", "title": "OpenSky Network", "href": OPENSKY_HOME},
                {"rel": "documentation", "title": "REST API", "href": OPENSKY_API_DOC},
                {"rel": "describedby", "title": "State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC},
            ],
        },
    }
