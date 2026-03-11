# Live Source Verification

**Verified date:** 2026-03-11

This package was not built from local assumptions alone. The following upstream
USGS Water Data OGC API resources were queried live on 2026-03-11 and used to
shape the package.

## Verified live endpoints

- `https://api.waterdata.usgs.gov/ogcapi/v0?f=json`
- `https://api.waterdata.usgs.gov/ogcapi/v0/openapi?f=json`
- `https://api.waterdata.usgs.gov/ogcapi/v0/collections/monitoring-locations/items/USGS-09380000?f=json`
- `https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous/items?monitoring_location_id=USGS-09380000&parameter_code=00060&limit=2&f=json`
- `https://api.waterdata.usgs.gov/ogcapi/v0/collections/time-series-metadata/items?monitoring_location_id=USGS-09380000&parameter_code=00060&limit=2&f=json`
- `https://api.waterdata.usgs.gov/ogcapi/v0/collections/combined-metadata/items?monitoring_location_id=USGS-09380000&parameter_code=00060&limit=2&f=json`
- `https://api.waterdata.usgs.gov/ogcapi/v0/collections/parameter-codes/items/00060?f=json`
- `https://api.waterdata.usgs.gov/ogcapi/v0/collections/statistic-codes/items/00011?f=json`

## Verified API surface

Live OpenAPI inspection confirmed that the current API still publishes, among
many others, these relevant collections:

- `monitoring-locations`
- `continuous`
- `latest-continuous`
- `daily`
- `time-series-metadata`
- `combined-metadata`
- `parameter-codes`
- `statistic-codes`

## Most important observations

### 1. `latest-continuous` is live

Sample live response for station `09380000`, parameter `00060`:

- `monitoring_location_id: USGS-09380000`
- `parameter_code: 00060`
- `statistic_id: 00011`
- `time_series_id: a62122d8ff094125b63bb2f73410b2b4`
- `time: 2026-03-11T21:00:00+00:00`
- `value: "8490"`
- `unit_of_measure: ft^3/s`
- `approval_status: Provisional`
- `qualifier: null`
- `last_modified: 2026-03-11T21:11:25.114399+00:00`

This strongly supports future migration of latest-only polling to the
`latest-continuous` collection.

### 2. `monitoring-locations` carries richer station metadata than the current bootstrap uses

Verified fields include:

- `agency_code`
- `agency_name`
- `district_code`
- `site_type_code`
- `site_type`
- `hydrologic_unit_code`
- `altitude`
- `altitude_accuracy`
- `vertical_datum`
- `vertical_datum_name`
- `horizontal_positional_accuracy`
- `horizontal_position_method_name`
- `original_horizontal_datum_name`
- `time_zone_abbreviation`
- `uses_daylight_savings`

These fields justify a richer SensorML system body.

### 3. `time-series-metadata` can return multiple series for one station and parameter

For station `09380000` and parameter `00060`, the live query returned both:

- daily mean series with `statistic_id=00003`
- instantaneous series with `statistic_id=00011`

This is a key modeling insight. It means:

- `parameter_code` alone does not uniquely identify the intended series
- the bootstrap should describe the current datastreams as the instantaneous
  `00011` series
- any future enrichment using `combined-metadata` or `time-series-metadata`
  must filter deliberately

### 4. `combined-metadata` is rich but easy to misuse

The live combined-metadata query merged monitoring-location and series details,
but the first returned item for the sample query represented a daily series.

That does not make the endpoint wrong. It means the consumer must treat it as a
rich metadata source, not as a shortcut that automatically resolves the desired
instantaneous series.

### 5. The API is still on `v0`

As of 2026-03-11, the active OGC API path is still:

- `https://api.waterdata.usgs.gov/ogcapi/v0/`

This package therefore keeps `v0` URLs and does not speculate about a newer
version path.
