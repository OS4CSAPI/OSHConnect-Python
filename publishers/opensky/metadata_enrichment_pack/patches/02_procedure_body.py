# Replacement `PROCEDURE_BODY`

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
        "keywords": [
            "ADS-B",
            "aircraft",
            "tracking",
            "OpenSky",
            "transponder",
            "airspace",
            "state vector",
            "feed adapter",
            "Pattern C",
            "southern Arizona",
        ],
        "documentation": [
            {"title": "OpenSky Network", "href": OPENSKY_HOME, "rel": "about"},
            {"title": "OpenSky REST API", "href": OPENSKY_API_DOC, "rel": "documentation"},
            {"title": "OpenSky State Vector Fields", "href": OPENSKY_STATE_VECTORS_DOC, "rel": "describedby"},
            {"title": "About OpenSky", "href": OPENSKY_ABOUT, "rel": "about"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": OPENSKY_CONTACT_ORG,
                "website": OPENSKY_CONTACT_URL,
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python",
            },
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
            "sourceProtocol": "HTTPS",
            "sourceFormat": "JSON object with top-level `time` and `states[][]` array payload",
            "authModeNote": "Current demo configuration uses anonymous access. OAuth2-supported access is available for higher credit budgets.",
            "rateLimitNote": "At the current demo cadence (300s) and current 12 sq deg window, the feed consumes about 288 credits/day.",
            "coverageNote": "Current demo window is southern Arizona: lat 31.0-34.0, lon -113.0--109.0 (12 sq deg).",
            "qualityControlNote": (
                "Position source varies by aircraft record and may reflect ADS-B, ASTERIX, MLAT, "
                "or FLARM provenance."
            ),
        },
        "validTime": [VALID_TIME_START, ".."],
    },
}
