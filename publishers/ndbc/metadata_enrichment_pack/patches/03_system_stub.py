# Replacement `_system_stub(station, proc_id)`

def _system_stub(station: dict, proc_id: str) -> dict:
    station_id = station["id"]
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
        },
        "properties": {
            "uid": _system_uid(station_id),
            "featureType": "sosa:Sensor",
            "name": f"NDBC {station_id} — {station['name']}",
            "description": (
                f"NOAA NDBC buoy station {station_id} at {station['name']}. "
                f"Platform type: {station.get('platform_type', 'buoy/platform unknown')}. "
                f"Water depth: {station.get('water_depth_m', '?')} m."
            ),
            "typeOf@link": {"href": proc_id, "title": "NDBC Buoy Observation v1"},
            "links": [
                {"rel": "about", "title": "NDBC Station Page", "href": _station_page_url(station_id)},
                {"rel": "alternate", "title": "Realtime Station Page", "href": _station_realtime_url(station_id)},
                {"rel": "alternate", "title": "Historical Station Page", "href": _station_history_url(station_id)},
            ],
            "validTime": [VALID_TIME_START, ".."],
        },
    }
