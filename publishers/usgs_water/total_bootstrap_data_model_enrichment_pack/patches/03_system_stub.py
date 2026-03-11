# Enriched system stub candidate

def _system_stub(station: dict, proc_id: str) -> dict:
    nwis_id = station["nwisId"]
    site_type = station.get("siteType", station.get("siteTypeCode", "Stream"))

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _system_uid(nwis_id),
            "featureType": "sosa:Sensor",
            "name": f"USGS {nwis_id} - {station['name']}",
            "description": (
                f"USGS monitoring location {nwis_id} ({station['fullName']}) in "
                f"{station.get('county', '')}, {station['state']}. This system represents the "
                "curated station-level water observing resource published by OSHConnect-Python, "
                "with discharge and gage-height datastreams derived from the USGS Water Data OGC API."
            ),
            "typeOf@link": {"href": proc_id, "title": "USGS Water Observation v1"},
            "keywords": [
                "USGS",
                "NWIS",
                "water monitoring",
                "hydrology",
                site_type,
                nwis_id,
                station["stateAbbr"]
            ],
            "validTime": [VALID_TIME_START, ".."]
        }
    }
