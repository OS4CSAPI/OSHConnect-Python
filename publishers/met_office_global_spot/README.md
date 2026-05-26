# Met Office Global Spot Forecast Publisher

Status: initial implementation for the access-gated Met Office Weather DataHub Site-Specific Forecast / Global Spot product. Live validation requires a `MET_OFFICE_GLOBAL_SPOT_API_KEY` subscription key.

This publisher is separate from `publishers/met_office_datahub`, which publishes observed Land Observations station telemetry. Global Spot values are deterministic forecasts for configured points, not readings from physical sensors.

## Source

- Weather DataHub landing page: https://datahub.metoffice.gov.uk/
- Site-specific forecast overview: https://datahub.metoffice.gov.uk/docs/g/category/site-specific/overview
- Site-specific pricing: https://datahub.metoffice.gov.uk/pricing/site-specific
- Weather DataHub docs: https://datahub.metoffice.gov.uk/docs

The subscribed product context from planning notes is `/sitespecific/v0`, API name `SiteSpecificForecast`, with a free-plan allowance of 360 calls/day.

## CSAPI Model

- One procedure for Met Office Global Spot hourly forecast retrieval.
- One virtual forecast-point system per curated location.
- One datastream per selected forecast parameter.
- One deployment group for curated Global Spot forecast points.
- Each published observation uses forecast valid time as `phenomenonTime` and preserves issued time, valid time, lead time, parameter, unit, source URL, and forecast type in the result payload.

These resources intentionally avoid claiming the forecast points are physical stations.

## Configuration

Store the API key outside git. In this workspace the preferred local file is `publishers/.env`, which is ignored by git.

```text
MET_OFFICE_GLOBAL_SPOT_API_KEY=...
```

On live hosts, prefer a service environment variable or a root-owned secret file:

```text
MET_OFFICE_GLOBAL_SPOT_API_KEY_FILE=/etc/os4csapi/secrets/met-office-global-spot.key
```

The key file may contain the raw key on the first non-comment line, or one of these assignments:

```text
MET_OFFICE_GLOBAL_SPOT_API_KEY=...
MET_OFFICE_SITE_SPECIFIC_FORECAST_API_KEY=...
MET_OFFICE_DATAHUB_API_KEY=...
```

Optional overrides:

```text
MET_OFFICE_GLOBAL_SPOT_BASE_URL=https://data.hub.api.metoffice.gov.uk/sitespecific/v0
MET_OFFICE_GLOBAL_SPOT_HOURLY_PATH=/point/hourly
MET_OFFICE_GLOBAL_SPOT_FORECAST_HOURS=24
MET_OFFICE_DATAHUB_API_KEY_HEADER=apikey
MET_OFFICE_GLOBAL_SPOT_REQUEST_DELAY=1.0
MET_OFFICE_GLOBAL_SPOT_429_BACKOFF=3600
```

`MET_OFFICE_GLOBAL_SPOT_HOURLY_PATH` may be an absolute URL, a path under the base URL, or a format string containing `{lat}`, `{lon}`, `{latitude}`, and `{longitude}`.

## Commands

Probe the authenticated API and inspect response shape:

```bash
python -m publishers.met_office_global_spot.met_office_global_spot_publisher --probe --locations london-heathrow-area
```

Run a dry publisher cycle without POSTing to OSH:

```bash
python -m publishers.met_office_global_spot.met_office_global_spot_publisher --dry-run --once
```

Bootstrap CSAPI resources:

```bash
python -m publishers.met_office_global_spot.bootstrap_met_office_global_spot
```

Run one live publish cycle:

```bash
python -m publishers.met_office_global_spot.met_office_global_spot_publisher --once
```

## Implementation Notes

The initial curated points mirror the Met Office Land Observations demo geography: London Heathrow, Stornoway, and Cairngorm. At one hourly API request per point per cycle, a one-hour cadence uses 72 calls/day, comfortably below the 360 calls/day free-plan allowance.

The runtime client has a configurable endpoint path because public DataHub pages confirm the Site-Specific Forecast / Global Spot product and `/sitespecific/v0` context, but the exact hourly endpoint path should be validated with the live subscribed API before production service installation.
