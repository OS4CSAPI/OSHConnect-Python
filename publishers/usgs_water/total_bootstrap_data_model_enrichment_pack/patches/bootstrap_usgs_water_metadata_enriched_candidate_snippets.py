"""
Bootstrap candidate snippets for publishers/usgs_water/bootstrap_usgs_water.py

This file is intentionally not a full drop-in replacement. It is a curated bundle
of the most valuable metadata and provenance upgrades:

- stronger official references
- richer procedure metadata
- richer monitoring-location SensorML metadata
- explicit statistic_id 00011 datastream semantics
- better deployment wording and source links

The current station-centric architecture is preserved.
"""

# 1. Additional constants and URL helpers

USGS_COLLECTIONS_HTML = "https://api.waterdata.usgs.gov/ogcapi/v0/collections?f=html"
USGS_OGC_DOCS = "https://api.waterdata.usgs.gov/docs/ogcapi/"
USGS_LATEST_CONTINUOUS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous"
USGS_TIME_SERIES_METADATA = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/time-series-metadata"
USGS_COMBINED_METADATA = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/combined-metadata"
USGS_PARAMETER_CODES = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/parameter-codes"
USGS_STATISTIC_CODES = "https://api.waterdata.usgs.gov/ogcapi/v0/collections/statistic-codes"
USGS_API_REGISTRATION = "https://api.usgs.gov/"
STATISTIC_INSTANTANEOUS = "00011"


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


# 2. Procedure semantics to preserve
#
# - document monitoring-locations, latest-continuous, time-series-metadata, and combined-metadata
# - state explicitly that current datastreams represent statistic_id 00011 instantaneous values
# - keep the current station-centric resource model


# 3. System metadata to enrich
#
# Prefer carrying these authoritative monitoring-location fields in SensorML when
# available in stations.json or derived sidecars:
#
# - agencyCode, agencyName, districtCode
# - siteTypeCode, siteType
# - altitude_ft, altitudeAccuracy_ft
# - verticalDatum, verticalDatumName
# - horizontalAccuracyNote, horizontalMethodName, horizontalDatumName
# - usesDaylightSavings
# - monitoringLocationUrl, latestContinuous00060Url, latestContinuous00065Url
# - timeSeries00060Url, timeSeries00065Url


# 4. Datastream semantics to preserve
#
# - usgsDischarge -> parameter_code 00060, statistic_id 00011, unit ft^3/s
# - usgsGageHeight -> parameter_code 00065, statistic_id 00011, unit ft
# - qualifier and approvalStatus come from upstream observation properties
# - timestamp is mapped from phenomenonTime and must not appear in result bodies


# 5. Deployment guidance
#
# Keep:
# - one root deployment
# - one grouping deployment
# - one station deployment per system
#
# Improve:
# - official source links
# - explanation that each leaf deployment anchors one monitoring location and two
#   parameter datastreams in the curated OS4CSAPI demonstration set
