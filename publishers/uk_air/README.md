# UK-AIR Publisher

Publishes a curated set of recent Defra UK-AIR air pollution readings into a CSAPI/OSH server.

The first-pass sidecar intentionally covers a small demo-safe set of pollutant products:

- nitrogen dioxide (`NO2`),
- ozone (`O3`),
- particulate matter (`PM10`),
- fine particulate matter (`PM2.5`).

Source data comes from the UK-AIR SOS / 52 North Timeseries REST API:

- https://uk-air.defra.gov.uk/data/about_sos
- https://uk-air.defra.gov.uk/data/sos/static/doc/api-doc/
- https://uk-air.defra.gov.uk/sos-ukair/api/v1/

## Bootstrap

```bash
python -m publishers.uk_air.bootstrap_uk_air --dry-run
python -m publishers.uk_air.bootstrap_uk_air
```

The bootstrap is idempotent and creates one procedure, one system per curated monitoring site, one datastream per curated pollutant timeseries, and a deployment hierarchy.

## Run

```bash
python -m publishers.uk_air.uk_air_publisher --dry-run --once
python -m publishers.uk_air.uk_air_publisher --once
python -m publishers.uk_air.uk_air_publisher --interval 3600
```

Use `--stations` with comma-separated curated site IDs, such as `camden-kerbside,toft-newton`, to publish a subset.

## Notes

- UK-AIR timeseries coordinates are exposed as `[lat, lon, alt]`; the bootstrap normalizes them to standard GeoJSON `[lon, lat]`.
- Normal polling reads a bounded recent window from `timeseries/{id}/getData` and publishes the latest valid value.
- Source timestamps are millisecond Unix epoch values and are normalized to UTC CSAPI phenomenon times.
- Source units such as `ug.m-3` are preserved in observation results as `unit`, while SWE schemas use the display-friendly `ug/m3` code.
- The first-pass model consolidates co-located pollutant streams only where the source metadata clearly supports it, such as Toft Newton PM10 and PM2.5.
- Explorer cards should show latest pollutant concentrations in the same latest-reading section used by other station-style publishers.
