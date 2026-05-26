# Environment Agency Hydrology Publisher

Publishes a curated set of live/recent Environment Agency Hydrology readings into a CSAPI/OSH server.

The first-pass sidecar intentionally covers a small demo-safe set of hydrology products:

- river level,
- river flow,
- rainfall,
- groundwater level.

Source data comes from the Environment Agency Hydrology API:

- https://environment.data.gov.uk/hydrology/
- https://environment.data.gov.uk/hydrology/doc/reference

## Bootstrap

```bash
python -m publishers.environment_agency_hydrology.bootstrap_environment_agency_hydrology --dry-run
python -m publishers.environment_agency_hydrology.bootstrap_environment_agency_hydrology
```

The bootstrap is idempotent and creates one procedure, one system per curated station, one datastream per curated measure, and a deployment hierarchy.

## Run

```bash
python -m publishers.environment_agency_hydrology.environment_agency_hydrology_publisher --dry-run --once
python -m publishers.environment_agency_hydrology.environment_agency_hydrology_publisher --once
python -m publishers.environment_agency_hydrology.environment_agency_hydrology_publisher --interval 900
```

Use `--stations` with comma-separated Environment Agency station notations to publish a subset.

## Notes

- The API is format-sensitive; this publisher uses `.json` endpoints and `_limit` query parameters.
- `latest=true` is used for normal polling.
- Groundwater appears as `level` data with groundwater-specific measure notation and `mAOD` units.
- Values can be provisional or revised; result payloads preserve source `quality`, `completeness`, and validation-count fields when present.
- Explorer NATO/STANAG display should use the friendly emplaced sensor symbol family (`SFGPEWRH-------`), matching USGS Water, CO-OPS, NDBC, and NWS station publishers.
- Explorer deployed-system cards and map click popups display latest readings from the station datastreams. Freshness is based on source `phenomenonTime`, so stale groundwater values remain visibly stale even if they were published into CSAPI recently.
