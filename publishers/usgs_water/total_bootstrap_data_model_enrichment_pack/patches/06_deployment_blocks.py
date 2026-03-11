# Enriched deployment block candidates

def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-100.0, 39.0]
        },
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "USGS Water Monitoring Demo",
            "description": (
                "Top-level CSAPI deployment grouping for curated USGS water monitoring resources "
                "published by OSHConnect-Python. This grouping covers station-centric systems and "
                "their discharge and gage-height datastreams sourced from the USGS Water Data OGC API."
            ),
            "documentation": [
                {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
                {"title": "USGS Collections", "href": USGS_COLLECTIONS_HTML, "rel": "describedby"},
                {"title": "USGS Water Data Home", "href": USGS_WATER_HOME, "rel": "about"}
            ],
            "validTime": [VALID_TIME_START, ".."]
        }
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [-100.0, 39.0]
        },
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "USGS Water Monitoring Stations",
            "description": (
                "Grouping deployment for the curated multi-state USGS monitoring-location set used "
                "by the OS4CSAPI demonstration. Each child deployment pairs one curated USGS station "
                "with one CSAPI system and two datastreams."
            ),
            "documentation": [
                {"title": "Monitoring Locations Collection", "href": f"{USGS_OGC_API}collections/monitoring-locations", "rel": "collection"},
                {"title": "Time Series Metadata Collection", "href": USGS_TIME_SERIES_METADATA, "rel": "collection"}
            ],
            "validTime": [VALID_TIME_START, ".."]
        }
    }


def _deploy_station(station: dict, system_server_id: str) -> dict:
    nwis_id = station["nwisId"]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]]
        },
        "properties": {
            "uid": _deploy_uid(nwis_id),
            "featureType": "sosa:Deployment",
            "name": f"USGS {nwis_id} Station Feed",
            "description": (
                f"CSAPI deployment node for USGS monitoring location {nwis_id} ({station['name']}). "
                "This node anchors the station system and its discharge and gage-height datastreams "
                "to the curated USGS Water Data OGC API publisher model."
            ),
            "externalLinks": [
                {
                    "href": station.get("monitoringLocationUrl", _monitoring_location_url(nwis_id)),
                    "title": "USGS Monitoring Location",
                    "rel": "canonical"
                },
                {
                    "href": station.get("latestContinuous00060Url", _latest_continuous_url(nwis_id, "00060")),
                    "title": "Latest Continuous - Discharge",
                    "rel": "latest-version"
                },
                {
                    "href": station.get("latestContinuous00065Url", _latest_continuous_url(nwis_id, "00065")),
                    "title": "Latest Continuous - Gage Height",
                    "rel": "latest-version"
                }
            ],
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(nwis_id),
                "title": f"USGS {nwis_id}"
            }
        }
    }
