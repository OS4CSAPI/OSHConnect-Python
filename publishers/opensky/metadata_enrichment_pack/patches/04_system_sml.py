# Replacement `_system_sml(config)`

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
        "description": (
            "Feed-adapter system representing OpenSky aircraft tracking over southern Arizona. "
            "This system is not a single aircraft sensor. It is a configured API-backed collection "
            "point for many aircraft state vectors retrieved from the OpenSky Network and republished "
            "as individual CSAPI observations."
        ),
        "keywords": [
            "ADS-B",
            "OpenSky",
            "aircraft",
            "tracking",
            "airspace",
            "southern Arizona",
            "feed adapter",
            "state vector",
            auth_cfg.get("mode", "anonymous"),
        ],
        "identifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "Short Name",
                "value": "OpenSky AZ Feed",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/LongName",
                "label": "Long Name",
                "value": "OpenSky Network ADS-B Feed - Southern Arizona Airspace",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/UniqueID",
                "label": "OS4CSAPI UID",
                "value": SYSTEM_UID,
            },
        ],
        "classifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/SensorType",
                "label": "System Type",
                "value": "ADS-B feed adapter (crowd-sourced receiver network)",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
                "label": "Intended Application",
                "value": "Airspace surveillance; aircraft tracking; situational awareness",
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/SystemRole",
                "label": "Bootstrap Pattern",
                "value": "Pattern C feed adapter",
            },
        ],
        "contacts": [
            {
                "role": "operator",
                "organisationName": OPENSKY_CONTACT_ORG,
                "contactInfo": {
                    "onlineResource": {"linkage": OPENSKY_HOME},
                },
            },
            {
                "role": "publisher",
                "organisationName": "OS4CSAPI",
                "contactInfo": {
                    "onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"},
                },
            },
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
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "About OpenSky",
                "description": "Operator/about page for the OpenSky Network Association.",
                "link": {"href": OPENSKY_ABOUT, "type": "text/html"},
            },
        ],
        "characteristics": [
            {
                "name": "coverage_profile",
                "type": "DataRecord",
                "label": "Coverage Profile",
                "fields": [
                    {"type": "Text", "name": "coverage_label", "label": "Coverage Label", "value": config.get("description", "Configured OpenSky coverage window")},
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
                    {"type": "Quantity", "name": "publish_interval", "label": "Publish Interval", "uom": {"code": "s"}, "value": config.get("cadence_seconds", 300)},
                    {"type": "Count", "name": "credit_cost_per_request", "label": "Credit Cost Per Request", "value": bbox.get("credit_cost_per_request", 1)},
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
                    {
                        "type": "Quantity",
                        "name": "update_interval",
                        "definition": "http://qudt.org/vocab/quantitykind/Period",
                        "label": "Publish Interval",
                        "uom": {"code": "s"},
                        "value": config.get("cadence_seconds", 300),
                    },
                    {
                        "type": "Text",
                        "name": "observation_model",
                        "label": "Observation Model",
                        "value": "One aircraft state vector per CSAPI observation",
                    },
                    {
                        "type": "Text",
                        "name": "deduplication_rule",
                        "label": "Deduplication Rule",
                        "value": "Repeated aircraft reports with unchanged timestamps are skipped",
                    },
                    {
                        "type": "Text",
                        "name": "position_sources",
                        "label": "Position Sources",
                        "value": _position_source_summary(),
                    },
                ],
            },
        ],
        "position": {
            "type": "Point",
            "coordinates": [center_lon, center_lat],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }
