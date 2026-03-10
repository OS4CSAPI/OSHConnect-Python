# Replacement `_system_sml(station)`

def _system_sml(station: dict) -> dict:
    station_id = station["id"]
    owner = station.get("owner", "National Data Buoy Center")
    platform_type = station.get("platform_type", "Buoy / marine observing platform")
    payload_type = station.get("payload_type", "Unknown")
    characteristics = [
        {"label": "Owner / Maintainer", "value": owner},
        {"label": "Platform Type", "value": platform_type},
        {"label": "Payload Type", "value": payload_type},
    ]

    if "site_elevation_m" in station:
        characteristics.append({"label": "Site Elevation (m)", "value": station["site_elevation_m"]})
    if "air_temp_height_m" in station:
        characteristics.append({"label": "Air Temp Height (m)", "value": station["air_temp_height_m"]})
    if "anemometer_height_m" in station:
        characteristics.append({"label": "Anemometer Height (m)", "value": station["anemometer_height_m"]})
    if "barometer_height_m" in station:
        characteristics.append({"label": "Barometer Height (m)", "value": station["barometer_height_m"]})
    if "sea_temp_depth_m" in station:
        characteristics.append({"label": "Sea Temp Depth (m)", "value": station["sea_temp_depth_m"]})
    if "water_depth_m" in station:
        characteristics.append({"label": "Water Depth (m)", "value": station["water_depth_m"]})
    if "watch_circle_radius_yd" in station:
        characteristics.append({"label": "Watch Circle Radius (yd)", "value": station["watch_circle_radius_yd"]})
    if station.get("has_buoycam"):
        characteristics.append({"label": "BuoyCAM", "value": _station_buoycam_url(station_id)})

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(station_id),
        "uniqueId": _system_uid(station_id),
        "label": f"NDBC {station_id} — {station['name']}",
        "description": (
            f"Marine observing platform at {station['name']} ({station_id}) operated by NOAA's "
            f"National Data Buoy Center. This resource represents the station as exposed through "
            f"NDBC realtime and station web resources."
        ),
        "identifiers": [
            {"label": "OS4CSAPI UID", "value": _system_uid(station_id)},
            {"label": "NDBC Station Identifier", "value": station_id},
        ],
        "classifiers": [
            {"label": "System Type", "value": platform_type},
            {"label": "Operator", "value": owner},
            {"label": "Program", "value": "NOAA National Data Buoy Center"},
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": owner,
                "website": NDBC_HOME,
                "email": NDBC_CONTACT_EMAIL,
            }
        ],
        "documentation": [
            {"name": "NDBC Station Page", "url": _station_page_url(station_id)},
            {"name": "Realtime Station Page", "url": _station_realtime_url(station_id)},
            {"name": "Historical Station Page", "url": _station_history_url(station_id)},
            {"name": "Realtime Flat File", "url": _station_realtime_text_url(station_id)},
            {"name": "Measurement Descriptions and Units", "url": NDBC_MEAS_DESC},
            {"name": "Realtime Data Retrieval FAQ", "url": NDBC_RT_DATA_DOC},
            {"name": "Station Status Report", "url": NDBC_STATUS_REPORT},
            {"name": "BuoyCAM FAQ", "url": NDBC_BUOYCAM_FAQ},
        ],
        "characteristics": characteristics,
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }
