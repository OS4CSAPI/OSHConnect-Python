# Met Office Weather DataHub Publisher

Status: implemented as an access-gated Land Observations publisher; live validation requires `MET_OFFICE_LAND_OBSERVATIONS_API_KEY` in the local environment.

This publisher slot is reserved for the fourth candidate source from the new-publisher expansion research: Met Office Weather DataHub Land Observations.

## Source

- Weather DataHub landing page: https://datahub.metoffice.gov.uk/
- Observations overview: https://datahub.metoffice.gov.uk/docs/g/category/observations/overview
- Land Observations API documentation: https://datahub.metoffice.gov.uk/docs/g/category/observations/type/land-observations/api-documentation
- Observations pricing: https://datahub.metoffice.gov.uk/pricing/observations

## Current Research Notes

Met Office Land Observations provides recent historical weather observations from ground-based instruments across roughly 150 UK station locations. The public documentation describes hourly JSON observations for the past 48 hours, with 9 parameters and an hourly update cadence.

The API flow is documented as:

1. Call `GET /observation-land/1/nearest` with latitude/longitude or geohash to identify the nearest land observation location.
2. Cache the nearest-location result.
3. Call `GET /observation-land/1/{geohash}` to retrieve observations for that land location.

The service is account/subscription gated. The public pricing page lists a free Land Observations plan up to 360 calls per day, but access still requires registration, product selection, subscription, and API credentials.

The subscribed API context supplied for this implementation is `/observation-land/1` with API name `CDP_Observation_Land`.

## Proposed CSAPI Model

Use the station-network pattern from `publishers/usgs_water`, with compatibility guardrails from `publishers/aviation_wx`.

- One procedure for Met Office Land Observations ingestion.
- One system per curated land observation location.
- One datastream per selected meteorological parameter per station.
- One deployment group for the curated Met Office demo set.
- Observations should preserve the source time, geohash/location identifier, observed parameter, value, unit, and source response metadata where permitted.

## Configuration

Store the API key outside git. In this workspace the preferred location is `publishers/.env`, which is ignored by the repository `.gitignore`.

```text
MET_OFFICE_LAND_OBSERVATIONS_API_KEY=...
```

On live hosts, prefer a service environment variable or a root-owned secret file instead of a repo-local `.env`:

```text
MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE=/etc/os4csapi/secrets/met-office-land-observations.key
```

The key file may contain the raw key on the first non-comment line, or `MET_OFFICE_LAND_OBSERVATIONS_API_KEY=...`.

Optional overrides:

```text
MET_OFFICE_LAND_OBSERVATIONS_BASE_URL=https://data.hub.api.metoffice.gov.uk/observation-land/1
MET_OFFICE_DATAHUB_API_KEY_HEADER=apikey
MET_OFFICE_DATAHUB_REQUEST_DELAY=1.0
MET_OFFICE_DATAHUB_429_BACKOFF=3600
```

## Commands

Probe the authenticated API and inspect response shape:

```bash
python -m publishers.met_office_datahub.met_office_datahub_publisher --probe --stations london-heathrow-area
```

Run a dry publisher cycle without POSTing to OSH:

```bash
python -m publishers.met_office_datahub.met_office_datahub_publisher --dry-run --once
```

Bootstrap CSAPI resources:

```bash
python -m publishers.met_office_datahub.bootstrap_met_office_datahub
```

Run one live publish cycle:

```bash
python -m publishers.met_office_datahub.met_office_datahub_publisher --once
```

## Implementation Notes

The publisher resolves and caches the nearest Met Office Land Observations geohash for each curated lookup point in `state.json`. That file is ignored by git through the repository's `publishers/**/state.json` rule. This keeps recurring publish cycles comfortably below the 360 calls/day free-plan limit.

When credentials are available, start with a small curated set of UK locations that complement existing demo publishers, for example:

- one coastal/weather-impact location,
- one urban or airport-adjacent location,
- one upland/rural reference location.

Keep total call volume comfortably below the free-plan limit during demo mode.