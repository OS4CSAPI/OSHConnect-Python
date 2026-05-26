# Met Office DataHub Publisher Implementation Plan

Date: 2026-05-26

## Objective

Start the fourth new publisher from the original candidate set using Met Office Weather DataHub Land Observations.

This is an access-gated implementation: the publisher should not claim live readiness until a valid Weather DataHub subscription credential is available and tested.

## Source Summary

Met Office Weather DataHub Land Observations provides recent hourly weather observations from ground-based UK observing stations.

Research findings:

- Product: Land Observations
- Domain: roughly 150 UK station locations
- Format: JSON
- Timesteps: hourly observations for the past 48 hours
- Parameters: 9 documented parameters
- Update frequency: hourly
- Access: account/subscription/API credential required
- Free plan: up to 360 calls per day

Documented API flow:

1. Call `GET /observation-land/1/nearest` with latitude/longitude or geohash.
2. Cache the nearest land observation location/geohash.
3. Call `GET /observation-land/1/{geohash}` for observations from that location.

## Recommended Model

Use `publishers/usgs_water` as the primary station-network exemplar.

CSAPI resources:

- Procedure: `urn:os4csapi:procedure:met-office-datahub-land-observations:v1`
- Systems: one per curated Met Office land observation location
- Datastreams: one per selected meteorological parameter per location
- Deployment: one root demo deployment with child station deployments

Observation result fields should include:

- source phenomenon/result time
- source geohash or location identifier
- parameter name/code
- value
- unit
- source response metadata allowed by terms

## Curated Demo Set

Choose three locations after credentials are available and nearest-location lookup can be validated:

1. Coastal/weather-impact station
2. Urban or airport-adjacent station
3. Upland/rural reference station

Keep polling comfortably below the free-plan limit. For a three-station demo, hourly polling with one cached nearest lookup per station and one observations call per station per hour should be safe.

## Implementation Steps

1. Verify credentials and exact request shape.
2. Probe nearest-location lookup for candidate demo coordinates.
3. Save resolved geohash/location metadata in a sidecar file.
4. Implement `bootstrap_met_office_datahub.py` with minimal GeoJSON create stubs and rich SensorML updates.
5. Implement `met_office_datahub_publisher.py` with `--dry-run`, `--once`, and interval controls.
6. Add source docs, pricing/access notes, and terms links to SensorML documents.
7. Run dry-run probes, then bootstrap, then one live publish cycle.
8. Add Explorer role/symbol/thumbnail polish only after confirming source metadata and licensing for any representative image.

## Open Questions

- Exact API key header/query parameter for the subscribed product.
- Exact JSON field names for station metadata and parameter observations in live responses.
- Reuse/licensing terms for display thumbnails or Met Office brand imagery.
- Whether source terms allow storing selected response metadata in OSH/CSAPI for demo purposes.

## Current Repository Start

Created:

- `publishers/met_office_datahub/README.md`
- `publishers/met_office_datahub/__init__.py`

Updated:

- `publishers/README.md`
- `Publisher_Expansion_Status_Report_2026-05-26.md`