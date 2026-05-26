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

Oracle live validation completed after host-local key installation:

- The previously supplied Met Office Weather Models, Global Spot / Site-Specific Forecast, and Land Observations keys were recovered from the local Copilot transcript and merged into `/etc/os4csapi/publisher-secrets.env` without printing raw values.
- A live Global Spot probe against `/sitespecific/v0/point/hourly` succeeded for London Heathrow Area with 49 candidate forecast records and recognized forecast temperature, humidity, wind speed, precipitation probability, and weather-code fields.
- The Global Spot bootstrap resources already existed on OSH: 5 virtual forecast systems, 30 forecast datastreams, and the deployment hierarchy.
- The first live publish attempt inserted 0 observations because OSH rejected an empty `leadTimeHours` decimal field. The publisher now preserves the field shape and uses OSH's supported `NaN` decimal sentinel when the upstream response lacks an issued/model-run time needed to compute lead time.
- Before installing a persistent service, the publisher was updated to persist recently published forecast dedupe keys in `publishers/met_office_global_spot/state.json`, so service restarts do not repost the same forecast horizon.
- After the fix, one live Global Spot `--once` cycle published 625 forecast observations with 0 errors and 0 skipped records.
- CSAPI verification against datastream `06hg2` returned a live forecast observation with forecast type `Met Office Global Spot hourly deterministic forecast`, valid time `2026-05-26T19:00:00Z`, result time `2026-05-26T19:35:34Z`, air temperature `29.9`, and `leadTimeHours=NaN`.
- Production Explorer reloaded to 905 map features after the Global Spot resources and observations were live. Selecting `Met Office Global Spot Portsmouth / Thorney Island Area` rendered a dedicated Forecast section and did not render Latest readings or Recent trend for forecast datastreams.

## Live Validation Boundary

The local `publishers/.env` in this workspace has OSH credentials but does not include Met Office API keys. Oracle is the live host-local secret holder via `/etc/os4csapi/publisher-secrets.env`; do not print or commit raw values.

Do not install a persistent Global Spot service until the live forecast card UI polish is deployed and one more smoke check confirms the production bundle hides unknown lead time instead of displaying the `NaN` sentinel.

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

1. Commit and push the publisher `leadTimeHours` sentinel fix and focused parser tests.
2. Commit and push the Explorer UI polish that hides unknown lead time values.
3. Verify Cloudflare Pages production bundle after deployment and re-check the Global Spot Portsmouth / Thorney Island card.
4. Seed the Oracle publisher state from the currently published forecast horizon, then install and start the persistent Oracle systemd service.

## Explorer Follow-Up

Explorer should add a forecast-specific card section only for true forecast datastreams. This must be additive:

- preserve thumbnails,
- preserve BuoyCAM and NIMS camera imagery,
- preserve water-monitoring media/source links,
- preserve latest readings and recent trends for observed telemetry,
- avoid labeling observed telemetry as forecast,
- avoid labeling Global Spot forecast points as physical deployed sensors.
