# OpenSky metadata enrichment candidate snippets
#
# This file is a convenience review bundle that mirrors the content of the
# numbered patch files in this directory. For an apply order, see:
#   ../notes/APPLY_ORDER.md

OPENSKY_STATE_VECTORS_DOC = "https://openskynetwork.github.io/opensky-api/index.html#state-vectors"
OPENSKY_AUTH_TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"

def _bbox_label(config: dict) -> str:
    bbox = config["bounding_box"]
    return (
        f"lat {bbox['lamin']}-{bbox['lamax']}, "
        f"lon {bbox['lomin']}-{bbox['lomax']}"
    )

def _daily_budget_note(config: dict) -> str:
    bbox = config["bounding_box"]
    cadence = int(config.get("cadence_seconds", 300))
    req_per_day = int(86400 / cadence) if cadence > 0 else 0
    credit_cost = bbox.get("credit_cost_per_request", 1)
    total = req_per_day * credit_cost
    return (
        f"{req_per_day} requests/day at {credit_cost} credit(s)/request "
        f"for an estimated {total} credits/day."
    )

def _position_source_summary() -> str:
    return "ADS-B, ASTERIX, MLAT, FLARM"


PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "OpenSky ADS-B Decoder v1",
        "description": (
            "Publishes aircraft state vectors from the OpenSky Network REST API using a "
            "configured geographic bounding box. Each upstream state vector becomes one "
            "CSAPI observation for one aircraft at one observation timestamp. The current "
            "publisher polls the REST API at a configured cadence, normalizes the array-based "
            "OpenSky payload into named fields, and skips repeated aircraft records whose "
            "observation timestamps have not changed."
        ),
        "documentation": [
            {"title": "OpenSky Network", "href": OPENSKY_HOME, "rel": "about"},
            {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
            {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
            {"title": "About OpenSky", "href": OPENSKY_ABOUT, "rel": "about"},
        ],
        "lineage": {
            "source": OPENSKY_CONTACT_ORG,
            "upstream": "OpenSky REST API /states/all endpoint filtered to the southern Arizona demo window",
            "normalization": (
                "Publisher fetches array-based state vectors, expands each array into named "
                "observation result fields, maps integer position-source codes to readable labels, "
                "and emits one observation per aircraft state snapshot."
            ),
        },
        "usageConstraints": {
            "authModeNote": "Current demo configuration uses anonymous access. OAuth2-supported access is available for higher credit budgets.",
            "rateLimitNote": "At the current demo cadence (300s) and current 12 sq deg window, the feed consumes about 288 credits/day.",
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}


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
                "physical sensor."
            ),
            "typeOf@link": {"href": "pending", "title": "OpenSky ADS-B Decoder v1"},
            "links": [
                {"rel": "about", "title": "OpenSky Network", "href": OPENSKY_HOME},
                {"rel": "documentation", "title": "REST API Docs", "href": OPENSKY_API_DOC},
                {"rel": "describedby", "title": "State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC},
            ],
            "authProfile": {
                "mode": config.get("auth", {}).get("mode", "anonymous"),
                "tokenEndpoint": config.get("auth", {}).get("oauth2_token_url", OPENSKY_AUTH_TOKEN_URL),
            },
            "coverageProfile": {
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


def _system_sml(config: dict) -> dict:
    bbox = config["bounding_box"]
    center_lon = (bbox["lomin"] + bbox["lomax"]) / 2
    center_lat = (bbox["lamin"] + bbox["lamax"]) / 2
    auth_cfg = config.get("auth", {})

    return {
        "type": "PhysicalSystem",
        "id": SYSTEM_UID,
        "uniqueId": SYSTEM_UID,
        "definition": "sosa:System",
        "label": "OpenSky ADS-B Feed - Southern Arizona",
        "keywords": [
            "ADS-B",
            "OpenSky",
            "aircraft",
            "tracking",
            "southern Arizona",
            "feed adapter",
            auth_cfg.get("mode", "anonymous"),
        ],
        "documents": [
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "OpenSky Network",
                "description": "Primary landing page for the OpenSky Network.",
                "link": {"href": OPENSKY_HOME, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "OpenSky REST API",
                "description": "REST API reference for states, flights, and tracks.",
                "link": {"href": OPENSKY_API_DOC, "type": "text/html"},
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "OpenSky State Vector Fields",
                "description": "Field-level reference for the state vector payload normalized by the publisher.",
                "link": {"href": OPENSKY_STATE_VECTORS_DOC, "type": "text/html"},
            },
        ],
        "characteristics": [
            {
                "name": "coverage_profile",
                "type": "DataRecord",
                "label": "Coverage Profile",
                "fields": [
                    {"type": "Text", "name": "bounding_box", "label": "Bounding Box", "value": _bbox_label(config)},
                    {"type": "Count", "name": "area_sq_deg", "label": "Area (sq deg)", "value": bbox.get("area_sq_deg", 0)},
                ],
            },
            {
                "name": "access_profile",
                "type": "DataRecord",
                "label": "Access Profile",
                "fields": [
                    {"type": "Text", "name": "auth_mode", "label": "Auth Mode", "value": auth_cfg.get("mode", "anonymous")},
                    {"type": "Text", "name": "daily_budget_note", "label": "Daily Budget Note", "value": _daily_budget_note(config)},
                ],
            },
            {
                "name": "position_source_vocabulary",
                "type": "DataRecord",
                "label": "Position Source Vocabulary",
                "fields": [
                    {"type": "Text", "name": "source_0", "label": "Source 0", "value": "ADS-B"},
                    {"type": "Text", "name": "source_1", "label": "Source 1", "value": "ASTERIX"},
                    {"type": "Text", "name": "source_2", "label": "Source 2", "value": "MLAT"},
                    {"type": "Text", "name": "source_3", "label": "Source 3", "value": "FLARM"},
                ],
            },
        ],
        "capabilities": [
            {
                "name": "publisher_capabilities",
                "type": "DataRecord",
                "label": "Publisher Capabilities",
                "capabilities": [
                    {"type": "Text", "name": "observation_model", "label": "Observation Model", "value": "One aircraft state vector per CSAPI observation"},
                    {"type": "Text", "name": "deduplication_rule", "label": "Deduplication Rule", "value": "Repeated aircraft reports with unchanged timestamps are skipped"},
                    {"type": "Text", "name": "position_sources", "label": "Position Sources", "value": _position_source_summary()},
                ],
            },
        ],
        "position": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


DATASTREAM_METADATA = {
    "description": (
        "Normalized OpenSky aircraft state vectors. Each observation represents one aircraft "
        "inside the configured bounding box at one upstream observation timestamp."
    ),
    "documentation": [
        {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
        {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
    ],
    "characteristics": [
        {"label": "Observation Model", "value": "One observation per aircraft per cycle"},
        {"label": "Coverage Filter", "value": "Bounding-box filter applied at the source API"},
        {"label": "Null Handling", "value": "Nullable numeric values are normalized to JSON-safe `NaN` strings by the current publisher"},
        {"label": "Position Source Vocabulary", "value": _position_source_summary()},
    ],
}


DEPLOYMENT_METADATA_NOTES = {
    "root_description": (
        "Top-level CSAPI deployment grouping for feed-adapter aircraft tracking resources "
        "published by OSHConnect-Python."
    ),
    "feed_description_template": (
        "Configured OpenSky feed-adapter deployment for {_bbox_label(config)} at "
        "{config.get('cadence_seconds', 300)}s cadence."
    ),
}
