# UK-AIR Publisher Completion Report - 2026-05-26

## Summary

Implemented the first-pass UK-AIR publisher package for OSHConnect-Python and bootstrapped it into the live OSH SensorHub backend used by the CSAPI Explorer `OSH (OS4CSAPI)` preset.

The new publisher models three curated UK-AIR monitoring sites and four pollutant timeseries:

| Site | Pollutant | UK-AIR timeseries | Datastream |
| --- | --- | ---: | --- |
| Camden Kerbside | NO2 | 3 | `ukAirNO2` |
| Auchencorth Moss | O3 | 24 | `ukAirO3` |
| Toft Newton | PM10 | 5125 | `ukAirPM10` |
| Toft Newton | PM2.5 | 5130 | `ukAirPM25` |

## Files Added

- `publishers/uk_air/__init__.py`
- `publishers/uk_air/stations.json`
- `publishers/uk_air/README.md`
- `publishers/uk_air/bootstrap_uk_air.py`
- `publishers/uk_air/uk_air_publisher.py`

## Files Updated

- `publishers/README.md`
  - Added UK-AIR to the publisher fleet table.
  - Added the UK-AIR bootstrap command.
  - Added source/API notes for the UK-AIR SOS / 52 North Timeseries REST API.

## Implementation Notes

- Source API: `https://uk-air.defra.gov.uk/sos-ukair/api/v1/`
- Timeseries list endpoint: `https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries`
- Recent data endpoint pattern: `timeseries/{id}/getData?timespan=PT72H/{utcEnd}`
- UK-AIR exposes point coordinates as `[lat, lon, alt]`; `stations.json` preserves normalized `lat` and `lon`, and the bootstrap writes standard GeoJSON ordering as `[lon, lat]`.
- UK-AIR timestamps are millisecond Unix epoch values; the runtime normalizes them to CSAPI UTC phenomenon times.
- UK-AIR source units are exposed as `ug.m-3`; the CSAPI observation payload uses display text `ug/m3` while preserving pollutant-specific result fields such as `no2_ugm3` and `pm25_ugm3`.
- Runtime filtering ignores missing, `NaN`, and sentinel `<= -99` values.

## Live Bootstrap Result

Command:

```powershell
py -m publishers.uk_air.bootstrap_uk_air
```

Result:

- Created procedure `urn:os4csapi:procedure:uk-air:v1` with server id `04dg`.
- Created systems:
  - `urn:os4csapi:system:uk-air:camden-kerbside:v1` -> `05lg`
  - `urn:os4csapi:system:uk-air:auchencorth-moss:v1` -> `05m0`
  - `urn:os4csapi:system:uk-air:toft-newton:v1` -> `05mg`
- Created datastreams:
  - `ukAirNO2` -> `05kg`
  - `ukAirO3` -> `05l0`
  - `ukAirPM10` -> `05lg`
  - `ukAirPM25` -> `05m0`
- Created deployments:
  - `urn:os4csapi:deployment:uk-air-demo:v1` -> `05g0`
  - `urn:os4csapi:deployment:uk-air-stations:v1` -> `05gg`
  - `urn:os4csapi:deployment:uk-air-camden-kerbside:v1` -> `05h0`
  - `urn:os4csapi:deployment:uk-air-auchencorth-moss:v1` -> `05hg`
  - `urn:os4csapi:deployment:uk-air-toft-newton:v1` -> `05i0`

The bootstrap helper stripped unsupported datastream `documentation` and `uid` fields before POST. This matches current server behavior and kept the operational datastream creation path clean.

## Live Publish Result

Initial live publish found that the server-accepted datastream schema did not include the runtime `timestamp` field in the observation result. The runtime payload was adjusted so `stationId` is the first result field, matching the schema accepted by OSH.

Command after the adjustment:

```powershell
py -m publishers.uk_air.uk_air_publisher --once
```

Result:

- Published: 4
- Skipped: 0
- Errors: 0

Published readings:

| Site / stream | Phenomenon time | Value |
| --- | --- | --- |
| Camden Kerbside `ukAirNO2` | `2026-05-26T09:00:00Z` | `NO2=27.731 ug/m3` |
| Auchencorth Moss `ukAirO3` | `2026-05-26T09:00:00Z` | `O3=67.854 ug/m3` |
| Toft Newton `ukAirPM10` | `2026-05-26T09:00:00Z` | `PM10=45.1 ug/m3` |
| Toft Newton `ukAirPM25` | `2026-05-26T09:00:00Z` | `PM2.5=18.396 ug/m3` |

## Server Read-Back Verification

Latest-observation read-back from live OSH confirmed the stored results:

| Datastream id | Result field | Value | Phenomenon time |
| --- | --- | ---: | --- |
| `05kg` | `no2_ugm3` | `27.731` | `2026-05-26T09:00:00Z` |
| `05l0` | `o3_ugm3` | `67.854` | `2026-05-26T09:00:00Z` |
| `05lg` | `pm10_ugm3` | `45.1` | `2026-05-26T09:00:00Z` |
| `05m0` | `pm25_ugm3` | `18.396` | `2026-05-26T09:00:00Z` |

## Explorer-Facing Visibility Check

The Explorer-facing OSH endpoint at `https://129-80-248-53.sslip.io/sensorhub/api` returned the new UK-AIR resources by UID.

Verified examples:

- `systems?uid=urn:os4csapi:system:uk-air:camden-kerbside:v1&limit=1000` returned system id `05lg`.
- `deployments?uid=urn:os4csapi:deployment:uk-air-demo:v1&limit=1000` returned one item.
- `deployments?uid=urn:os4csapi:deployment:uk-air-stations:v1&limit=1000` returned one item.

## Validation Commands

```powershell
py -m py_compile publishers\uk_air\bootstrap_uk_air.py publishers\uk_air\uk_air_publisher.py
py -m publishers.uk_air.uk_air_publisher --dry-run --once
py -m publishers.uk_air.bootstrap_uk_air --dry-run
py -m publishers.uk_air.bootstrap_uk_air
py -m publishers.uk_air.uk_air_publisher --once
```

All final validation commands completed successfully.

## Follow-Up Items

1. Open the production Explorer map with the `OSH (OS4CSAPI)` preset and visually confirm marker styling, side-card labels, and popup latest-reading display for UK-AIR deployments.
2. If the marker falls back to a blank/generic NATO symbol, add a targeted UK-AIR / air-quality keyword mapping in the Explorer symbol mapper.
3. Consider adding a representative monitoring-station image/fallback after the visual pass, following the Environment Agency Hydrology pattern.
4. Consider expanding the curated sidecar after demo validation, especially for additional urban NO2/PM sites and rural background stations.
