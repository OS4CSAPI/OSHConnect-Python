# Met Office Exeter and Portsmouth Demo Site Check

Date: 2026-05-26

## Purpose

Determine whether Met Office Weather DataHub Land Observations has useful live locations in or near Exeter and Portsmouth for the CSAPI demo publisher set.

## Method

Used the existing Oracle host-local Met Office Land Observations key through `/etc/os4csapi/publisher-secrets.env` and its configured key file. The key was not printed, changed, rotated, or committed.

Queried the access-gated Land Observations `nearest` endpoint for:

- Exeter city
- Exeter Airport
- Portsmouth city
- Lee-on-Solent
- Southampton Airport

Then queried each returned geohash observation endpoint to confirm data availability.

## Findings

### Exeter

Recommended demo location: `Exeter Airport Area`

- Query points: Exeter city and Exeter Airport
- Returned Met Office geohash: `gcj8ds`
- Decoded geohash center: approximately `50.73761, -3.40027`
- Distance from Exeter city query: about `9.6 km`
- Distance from Exeter Airport query: about `1.0 km`
- Observation endpoint returned `48` records
- Sample fields: `datetime`, `humidity`, `mslp`, `pressure_tendency`, `temperature`, `visibility`, `weather_code`, `wind_direction`, `wind_gust`, `wind_speed`

Assessment: strong demo candidate. The resolved point is very close to Exeter Airport and gives the demo a southwest England weather reference.

### Portsmouth / East Solent

Recommended demo location: `Portsmouth / Thorney Island Area`

- Query points: Portsmouth city and Lee-on-Solent
- Returned Met Office geohash: `gcp34f`
- Decoded geohash center: approximately `50.81451, -0.92834`
- Distance from Portsmouth city query: about `11.2 km`
- Distance from Lee-on-Solent query: about `19.6 km`
- Observation endpoint returned `48` records
- Sample fields: `datetime`, `humidity`, `mslp`, `pressure_tendency`, `temperature`, `visibility`, `weather_code`, `wind_direction`, `wind_gust`, `wind_speed`

Assessment: useful south coast candidate, but it should not be labeled as a Portsmouth city-centre station. Use Portsmouth-adjacent or Thorney Island / east Solent language.

### Southampton Airport

- Query point: Southampton Airport
- Returned Met Office geohash: `gcnfur`
- Decoded geohash center: approximately `51.14960, -1.56555`
- Distance from Southampton Airport query: about `26.5 km`
- Observation endpoint returned `48` records

Assessment: valid data, but less compelling for this request than Exeter Airport and Portsmouth / Thorney Island.

## Changes Made

Added both recommended locations to:

- `publishers/met_office_datahub/stations.json`
- `publishers/met_office_global_spot/forecast_points.json`

For Land Observations, the resolved geohashes are stored in config to avoid repeated nearest lookups:

- `exeter-airport-area` -> `gcj8ds`
- `portsmouth-thorney-island-area` -> `gcp34f`

For Global Spot, the same curated point labels and coordinates are added as virtual forecast points so the future forecast card work can align observed and forecast demos without implying the forecast point is a physical sensor.

## Operational Notes

Adding two Land Observations locations increases the default Met Office Land Observations cycle from 3 to 5 locations. With geohashes cached in config, the publisher should make one observation endpoint request per location per cycle, still far below the documented 360 calls/day free-plan limit at hourly cadence.

The Global Spot default set also increases from 3 to 5 locations. At one hourly forecast API request per location per hour, the default operational cadence is about 120 calls/day, still below the documented 360 calls/day free-plan allowance.
