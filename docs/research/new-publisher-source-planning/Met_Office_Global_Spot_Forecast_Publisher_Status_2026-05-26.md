# Met Office Global Spot Forecast Publisher Status

Date: 2026-05-26

## Purpose

Record the first implementation slice for the Met Office Weather DataHub Global Spot / Site-Specific Forecast publisher and the remaining live-validation work.

## Implementation Status

Implemented and pushed in commit `3aaa637` (`Add Met Office Global Spot forecast publisher`).

New package:

- `publishers/met_office_global_spot/`
- `publishers/met_office_global_spot/bootstrap_met_office_global_spot.py`
- `publishers/met_office_global_spot/met_office_global_spot_publisher.py`
- `publishers/met_office_global_spot/forecast_points.json`
- `publishers/met_office_global_spot/README.md`
- `publishers/met_office_global_spot/Dockerfile`
- `tests/test_met_office_global_spot_parser.py`

Fleet wiring:

- `publishers/.env.example` documents Global Spot key and endpoint overrides.
- `publishers/docker-compose.yml` includes access-gated `met-office-global-spot` service.
- `publishers/README.md` lists the Global Spot publisher and bootstrap/run commands.

## Source Model

Global Spot is treated as true forecast data, not observed telemetry.

The CSAPI model uses:

- one forecasting procedure for Met Office Global Spot hourly retrieval,
- one virtual forecast-point system per curated location,
- one datastream per selected forecast parameter,
- one deployment group for curated Global Spot forecast points,
- one observation per selected forecast parameter and valid time.

Published result payloads preserve:

- forecast type,
- issued time,
- valid time,
- lead time in hours,
- curated point ID,
- parameter name,
- value and unit,
- source URL.

This is intentionally separate from `publishers/met_office_datahub`, which publishes Land Observations from physical observation locations.

## Curated Initial Slice

Forecast points:

- London Heathrow Area
- Exeter Airport Area
- Portsmouth / Thorney Island Area
- Stornoway Coastal Area
- Cairngorm Upland Area

Forecast parameters:

- Forecast Air Temperature
- Forecast Relative Humidity
- Forecast Wind Speed
- Forecast Wind Gust
- Forecast Precipitation Probability
- Forecast Weather Code

With five locations at one request per location per hour, the default operational cadence is about 120 requests/day, comfortably below the documented 360 calls/day free-plan allowance.

## Validation Completed

Local validation completed without printing or changing credentials:

- Python compile passed for the new bootstrap, publisher, and parser test files.
- Bootstrap dry run successfully constructed the procedure, 5 virtual systems, 30 datastreams, and deployment hierarchy.
- Focused parser tests passed: `2 passed`.
- Repository was pushed cleanly to `origin/main` at `3aaa637`.

Oracle validation completed without printing or changing credentials:

- Production Explorer loaded 846 features after the Exeter and Portsmouth Land Observations deployment, up from the earlier 810-feature view.
- The Portsmouth / Thorney Island Met Office label rendered on the production map.
- A sanitized Global Spot probe using the currently installed Land Observations key reached `/sitespecific/v0/point/hourly`, but Met Office returned HTTP 403 `Resource forbidden` for that forecast resource.
- The fallback path `/sitespecific/v0/global/hourly` returned HTTP 404, which supports keeping `/point/hourly` as the current default while treating forecast-product subscription access as the blocker.
- Oracle bootstrap dry run for Global Spot succeeded with 5 virtual forecast systems, 30 forecast datastreams, and 7 deployment resources; no forecast resources were written because live forecast API access is not yet available.

## Live Validation Boundary

The local `publishers/.env` in this workspace has OSH credentials but does not currently include a Global Spot / Site-Specific Forecast key. The Oracle host also currently has only the Met Office Land Observations key installed. A sanitized Oracle probe confirmed that key is not authorized for the Site-Specific Forecast resource: `/sitespecific/v0/point/hourly` returns HTTP 403 `Resource forbidden`.

Do not install a persistent Global Spot service or publish forecast observations until a Site-Specific Forecast / Global Spot key is installed host-locally.

The runtime is deliberately configurable for the final subscribed endpoint check:

```text
MET_OFFICE_GLOBAL_SPOT_API_KEY=...
MET_OFFICE_GLOBAL_SPOT_API_KEY_FILE=/etc/os4csapi/secrets/met-office-global-spot.key
MET_OFFICE_GLOBAL_SPOT_BASE_URL=https://data.hub.api.metoffice.gov.uk/sitespecific/v0
MET_OFFICE_GLOBAL_SPOT_HOURLY_PATH=/point/hourly
MET_OFFICE_GLOBAL_SPOT_FORECAST_HOURS=24
MET_OFFICE_DATAHUB_API_KEY_HEADER=apikey
```

`MET_OFFICE_GLOBAL_SPOT_HOURLY_PATH` can be an absolute URL, a path under the base URL, or a format string containing `{lat}`, `{lon}`, `{latitude}`, and `{longitude}`.

## Next Steps

1. Place the existing Site-Specific Forecast / Global Spot key in a host-local secret file or environment variable without rotating or printing it.
2. Run `python -m publishers.met_office_global_spot.met_office_global_spot_publisher --probe --locations london-heathrow-area` to confirm the response shape now that `/point/hourly` is the likely endpoint path.
3. If the endpoint path differs from `/point/hourly`, set `MET_OFFICE_GLOBAL_SPOT_HOURLY_PATH` rather than changing credentials.
4. Run `python -m publishers.met_office_global_spot.bootstrap_met_office_global_spot --force-sml` on the target OSH server.
5. Run `python -m publishers.met_office_global_spot.met_office_global_spot_publisher --dry-run --once` and then one live `--once` cycle.
6. Verify Explorer behavior: forecast points must be labeled as forecast, and existing rich source cards such as BuoyCAM and water monitoring media must remain unchanged.
7. Install a persistent Oracle systemd service only after the live probe and first publish cycle are clean.

## Explorer Follow-Up

Explorer should add a forecast-specific card section only for true forecast datastreams. This must be additive:

- preserve thumbnails,
- preserve BuoyCAM and NIMS camera imagery,
- preserve water-monitoring media/source links,
- preserve latest readings and recent trends for observed telemetry,
- avoid labeling observed telemetry as forecast,
- avoid labeling Global Spot forecast points as physical deployed sensors.
