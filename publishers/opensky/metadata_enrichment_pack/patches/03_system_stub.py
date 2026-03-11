# Replacement `_system_stub(config)`

def _system_stub(config: dict) -> dict:
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
            "uid": SYSTEM_UID,
            "featureType": "sosa:Sensor",
            "name": "OpenSky ADS-B Feed - Southern Arizona",
            "description": (
                "Feed-adapter system for OpenSky aircraft surveillance over southern Arizona. "
                "The system represents the configured OpenSky query window rather than any single "
                "physical sensor. It polls the OpenSky REST API, receives many aircraft state vectors "
                "per cycle, and republishes each aircraft state as a CSAPI observation."
            ),
            "typeOf@link": {"href": "pending", "title": "OpenSky ADS-B Decoder v1"},
            "keywords": [
                "OpenSky",
                "ADS-B",
                "airspace tracking",
                "feed adapter",
                "southern Arizona",
            ],
            "links": [
                {"rel": "about", "title": "OpenSky Network", "href": OPENSKY_HOME},
                {"rel": "documentation", "title": "REST API Docs", "href": OPENSKY_API_DOC},
                {"rel": "describedby", "title": "State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC},
                {"rel": "about", "title": "About OpenSky", "href": OPENSKY_ABOUT},
            ],
            "authProfile": {
                "mode": config.get("auth", {}).get("mode", "anonymous"),
                "tokenEndpoint": config.get("auth", {}).get("oauth2_token_url", OPENSKY_AUTH_TOKEN_URL),
                "note": config.get("auth", {}).get("note", ""),
            },
            "coverageProfile": {
                "label": config.get("description", "OpenSky configured coverage window"),
                "bbox": _bbox_label(config),
                "area_sq_deg": bbox.get("area_sq_deg", 0),
                "cadence_seconds": config.get("cadence_seconds", 300),
                "credit_budget_note": _daily_budget_note(config),
            },
            "image": {
                "href": "./metadata_enrichment_pack/assets/opensky_feed_adapter_generic.svg",
                "title": "Representative OpenSky feed-adapter coverage graphic",
            },
            "validTime": [VALID_TIME_START, ".."],
        },
    }
