# Enriched datastream schema candidate

def _imagery_datastream_schema(cam: dict) -> dict:
    cam_id = cam["camId"]
    nwis_id = cam["nwisId"]
    station_name = cam.get("stationName", cam.get("camName", nwis_id))
    ingest_period = cam.get("ingestPeriod", "unknown")
    ingest_interval = cam.get("ingestIntervalMin", "unknown")
    timelapse_enabled = cam.get("TL_enabled", False)

    return {
        "outputName": DS_OUTPUT_NAME,
        "name": "NIMS Station Image",
        "description": (
            f"Image-reference observations from selected USGS NIMS camera {cam_id} at gaging "
            f"station {nwis_id} ({station_name}). This datastream is a Pattern A companion "
            f"datastream on the shared USGS water station system. Current camera capture mode is "
            f"{ingest_period} with an approximate {ingest_interval}-minute interval. "
            f"Timelapse enabled: {str(timelapse_enabled).lower()}."
        ),
        "documentation": [
            {"title": "NIMS Camera Discovery", "href": _camera_page_url(cam_id), "rel": "documentation"},
            {"title": "NIMS Site Discovery", "href": _site_cameras_url(nwis_id), "rel": "documentation"},
            {"title": "NIMS Image Listing", "href": _list_files_url(cam_id, 5), "rel": "documentation"},
            {"title": "NIMS Raw Item Listing", "href": _list_files_rawitem_url(cam_id, 5), "rel": "documentation"},
            {"title": "NIMS S3 Bucket", "href": NIMS_S3_BASE, "rel": "alternate"}
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "NIMS Image Reference",
                "description": (
                    "USGS NIMS image-reference metadata and resolution-specific URLs. "
                    "The time field named timestamp is populated from phenomenonTime and "
                    "must not be included inside the result body."
                ),
                "fields": [
                    {
                        "type": "Time",
                        "name": "timestamp",
                        "label": "Image Time",
                        "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime",
                        "referenceTime": "1970-01-01T00:00:00Z",
                        "uom": {"code": "s"}
                    },
                    {
                        "type": "Text",
                        "name": "stationId",
                        "label": "NWIS Site ID",
                        "definition": "http://sensorml.com/ont/swe/property/StationID"
                    },
                    {
                        "type": "Text",
                        "name": "camId",
                        "label": "Camera ID",
                        "definition": "http://sensorml.com/ont/swe/property/SensorID"
                    },
                    {
                        "type": "Text",
                        "name": "imageUrl",
                        "label": "Full-Size Image URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"
                    },
                    {
                        "type": "Text",
                        "name": "thumbUrl",
                        "label": "Thumbnail Image URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"
                    },
                    {
                        "type": "Text",
                        "name": "smallUrl",
                        "label": "720px Image URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/ImageURL"
                    },
                    {
                        "type": "Text",
                        "name": "mediaType",
                        "label": "Media Type",
                        "definition": "http://purl.org/dc/elements/1.1/format"
                    },
                    {
                        "type": "Text",
                        "name": "filename",
                        "label": "Image Filename",
                        "definition": "http://purl.org/dc/elements/1.1/identifier"
                    },
                    {
                        "type": "Text",
                        "name": "timeLapseUrl",
                        "label": "Timelapse Video URL",
                        "definition": "http://www.opengis.net/def/property/OGC/0/VideoURL",
                        "optional": true
                    }
                ]
            }
        }
    }
