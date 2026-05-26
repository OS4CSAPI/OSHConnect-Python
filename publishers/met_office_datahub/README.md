# Met Office Weather DataHub Publisher

Status: started, access-gated implementation target.

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

## Proposed CSAPI Model

Use the station-network pattern from `publishers/usgs_water`, with compatibility guardrails from `publishers/aviation_wx`.

- One procedure for Met Office Land Observations ingestion.
- One system per curated land observation location.
- One datastream per selected meteorological parameter per station.
- One deployment group for the curated Met Office demo set.
- Observations should preserve the source time, geohash/location identifier, observed parameter, value, unit, and source response metadata where permitted.

## Implementation Gate

Do not implement a live runtime until a `MET_OFFICE_DATAHUB_API_KEY` or equivalent subscription credential is available and the exact API request headers/query parameters are verified against the subscribed product.

When credentials are available, start with a small curated set of UK locations that complement existing demo publishers, for example:

- one coastal/weather-impact location,
- one urban or airport-adjacent location,
- one upland/rural reference location.

Keep total call volume comfortably below the free-plan limit during demo mode.