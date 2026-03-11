# Additional official references and series helpers for bootstrap_usgs_water.py

USGS_COLLECTIONS_HTML = "https://api.waterdata.usgs.gov/ogcapi/v0/collections?f=html"
USGS_OGC_DOCS = "https://api.waterdata.usgs.gov/docs/ogcapi/"
USGS_LATEST_CONTINUOUS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous"
USGS_TIME_SERIES_METADATA = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/time-series-metadata"
USGS_COMBINED_METADATA = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/combined-metadata"
USGS_PARAMETER_CODES = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/parameter-codes"
USGS_STATISTIC_CODES = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/statistic-codes"
USGS_API_REGISTRATION = "https://api.usgs.gov/"

STATISTIC_INSTANTANEOUS = "00011"
STATISTIC_INSTANTANEOUS_NAME = "Instantaneous"


def _latest_continuous_url(nwis_id: str, parameter_code: str) -> str:
    return (
        f"{USGS_LATEST_CONTINUOUS}/items"
        f"?monitoring_location_id=USGS-{nwis_id}"
        f"&parameter_code={parameter_code}"
        f"&limit=5"
    )


def _time_series_metadata_url(nwis_id: str, parameter_code: str) -> str:
    return (
        f"{USGS_TIME_SERIES_METADATA}/items"
        f"?monitoring_location_id=USGS-{nwis_id}"
        f"&parameter_code={parameter_code}"
        f"&limit=10"
    )


def _combined_metadata_url(nwis_id: str, parameter_code: str) -> str:
    return (
        f"{USGS_COMBINED_METADATA}/items"
        f"?monitoring_location_id=USGS-{nwis_id}"
        f"&parameter_code={parameter_code}"
        f"&limit=10"
    )
