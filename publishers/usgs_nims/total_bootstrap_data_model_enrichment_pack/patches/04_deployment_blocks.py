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
            "name": "USGS NIMS Imagery Demo",
            "description": (
                "Top-level CSAPI deployment grouping for USGS NIMS gaging-station imagery "
                "published by OSHConnect-Python. Imagery datastreams are companion datastreams "
                "attached to existing USGS water monitoring station systems under the Pattern A model."
            ),
            "documentation": [
                {"title": "NIMS Camera Discovery", "href": USGS_NIMS_CAMERAS, "rel": "documentation"},
                {"title": "NIMS Swagger Docs", "href": USGS_NIMS_DOCS, "rel": "describedby"},
                {"title": "NIMS S3 Image Bucket", "href": NIMS_S3_BASE, "rel": "alternate"},
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
            "name": "USGS NIMS Camera Stations",
            "description": (
                "Grouping deployment for the curated set of USGS NIMS camera-equipped gaging "
                "stations. Each child deployment represents one selected camera linked to one "
                "existing USGS water station system."
            ),
            "documentation": [
                {"title": "NIMS Camera Discovery", "href": USGS_NIMS_CAMERAS, "rel": "documentation"},
                {"title": "USGS Water OGC API", "href": USGS_OGC_API, "rel": "related"}
            ],
            "validTime": [VALID_TIME_START, ".."]
        }
    }


def _deploy_camera(cam: dict, system_server_id: str) -> dict:
    nwis_id = cam["nwisId"]
    cam_id = cam["camId"]
    station_name = cam.get("stationName", cam.get("camName", nwis_id))
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [cam["lon"], cam["lat"]]
        },
        "properties": {
            "uid": _deploy_uid(nwis_id),
            "featureType": "sosa:Deployment",
            "name": f"NIMS Camera {nwis_id}",
            "description": (
                f"CSAPI deployment node for selected NIMS camera {cam_id} at USGS gaging station "
                f"{nwis_id} ({station_name}). This deployment links imagery observations to the "
                "existing shared USGS water station system rather than creating a separate camera system."
            ),
            "externalLinks": [
                {"href": _camera_page_url(cam_id), "title": "NIMS Camera Discovery", "rel": "canonical"},
                {"href": _site_cameras_url(nwis_id), "title": "NIMS Site Discovery", "rel": "related"},
                {"href": _list_files_url(cam_id, 10), "title": "NIMS Recent Images", "rel": "latest-version"},
                {"href": _list_files_rawitem_url(cam_id, 10), "title": "NIMS Recent Images (rawItem)", "rel": "related"},
                {"href": _timelapse_url(cam), "title": "NIMS Timelapse Video", "rel": "alternate"}
            ],
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": system_server_id,
                "uid": _system_uid(nwis_id),
                "title": f"USGS {nwis_id}"
            }
        }
    }
