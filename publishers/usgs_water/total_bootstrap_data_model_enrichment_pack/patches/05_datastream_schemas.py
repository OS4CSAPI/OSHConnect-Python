# Enriched datastream schema candidates

def _discharge_datastream_schema() -> dict:
    return {
        "outputName": DS_DISCHARGE_OUTPUT,
        "name": "Discharge",
        "description": (
            "Instantaneous discharge (streamflow) observations for the station-specific "
            "USGS NWIS instantaneous series. This datastream represents parameter code "
            "00060 with statistic_id 00011. Qualifier and approval status are passed "
            "through from the upstream USGS Water Data API response."
        ),
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
            {"title": "Latest Continuous Collection", "href": USGS_LATEST_CONTINUOUS, "rel": "collection"},
            {"title": "Time Series Metadata Collection", "href": USGS_TIME_SERIES_METADATA, "rel": "collection"},
            {"title": "Statistic Code 00011", "href": f"{USGS_STATISTIC_CODES}/items/00011?f=json", "rel": "describedby"}
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "USGS Discharge Observation",
                "description": (
                    "Instantaneous discharge value with station identifier, qualifier, and approval status. "
                    "The time field named timestamp is populated from phenomenonTime and must not be included "
                    "inside the result body."
                ),
                "fields": [
                    {
                        "type": "Time",
                        "name": "timestamp",
                        "label": "Observation Time",
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
                        "type": "Quantity",
                        "name": "discharge_cfs",
                        "label": "Discharge",
                        "definition": "http://www.opengis.net/def/property/OGC/0/Discharge",
                        "uom": {"code": "ft3/s"}
                    },
                    {
                        "type": "Text",
                        "name": "qualifier",
                        "label": "Data Qualifier",
                        "definition": "http://sensorml.com/ont/swe/property/QualityFlag"
                    },
                    {
                        "type": "Text",
                        "name": "approvalStatus",
                        "label": "Approval Status",
                        "definition": "http://sensorml.com/ont/swe/property/ApprovalStatus"
                    }
                ]
            }
        }
    }


def _gage_height_datastream_schema() -> dict:
    return {
        "outputName": DS_GAGE_HEIGHT_OUTPUT,
        "name": "Gage Height",
        "description": (
            "Instantaneous gage-height observations for the station-specific USGS NWIS "
            "instantaneous series. This datastream represents parameter code 00065 with "
            "statistic_id 00011. Qualifier and approval status are passed through from the "
            "upstream USGS Water Data API response."
        ),
        "documentation": [
            {"title": "USGS Water Data OGC API", "href": USGS_OGC_API, "rel": "documentation"},
            {"title": "Latest Continuous Collection", "href": USGS_LATEST_CONTINUOUS, "rel": "collection"},
            {"title": "Time Series Metadata Collection", "href": USGS_TIME_SERIES_METADATA, "rel": "collection"},
            {"title": "Statistic Code 00011", "href": f"{USGS_STATISTIC_CODES}/items/00011?f=json", "rel": "describedby"}
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": "USGS Gage Height Observation",
                "description": (
                    "Instantaneous gage-height value with station identifier, qualifier, and approval status. "
                    "The time field named timestamp is populated from phenomenonTime and must not be included "
                    "inside the result body."
                ),
                "fields": [
                    {
                        "type": "Time",
                        "name": "timestamp",
                        "label": "Observation Time",
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
                        "type": "Quantity",
                        "name": "gage_height_ft",
                        "label": "Gage Height",
                        "definition": "http://www.opengis.net/def/property/OGC/0/GageHeight",
                        "uom": {"code": "ft"}
                    },
                    {
                        "type": "Text",
                        "name": "qualifier",
                        "label": "Data Qualifier",
                        "definition": "http://sensorml.com/ont/swe/property/QualityFlag"
                    },
                    {
                        "type": "Text",
                        "name": "approvalStatus",
                        "label": "Approval Status",
                        "definition": "http://sensorml.com/ont/swe/property/ApprovalStatus"
                    }
                ]
            }
        }
    }
