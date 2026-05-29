# Finland Publisher Expansion Plan

Date: 2026-05-29
Status: Planning
Repository: OSHConnect-Python

## Purpose

This folder tracks the planned Finland-origin data-source expansion for the OS4CSAPI publisher fleet. The goal is to add Finnish public-data publishers that match the quality and operational shape of the existing fleet while preserving the proven CSAPI pattern:

- idempotent bootstrap scripts,
- stable source-derived UIDs,
- curated sidecar station/source config,
- source-native identifiers and URLs preserved in observation results,
- dry-run, once, interval, and subset CLI support,
- completion reports and live smoke evidence before production use.

## Current Publisher Baseline

The existing publisher fleet reviewed for this activity includes:

| Publisher | Source family | Pattern to reuse |
| --- | --- | --- |
| `iss` | CelesTrak TLE / SGP4 | Moving-platform position publisher |
| `nws` | NOAA weather stations | Fixed station weather observations |
| `aviation_wx` | AviationWeather METAR | Airport weather observations |
| `ndbc` | NOAA buoys and BuoyCAM | Marine station observations and imagery |
| `coops` | NOAA tides and currents | Coastal water-level station observations |
| `opensky` | ADS-B aircraft states | Moving-object feed adapter |
| `usgs_water` | USGS water monitoring | Hydrology station observations |
| `usgs_nims` | USGS station imagery | Image-reference observations on existing systems |
| `usgs_eq` | USGS earthquake feed | Event-feed publisher |
| `environment_agency_hydrology` | UK hydrology | Curated latest readings by measure |
| `uk_air` | UK air quality | Fixed air-quality station observations |
| `bgs_sensorthings` | UKGEOS SensorThings telemetry | Curated geoscience telemetry |
| `met_office_datahub` | UK land observations | Access-gated weather observations |
| `met_office_global_spot` | UK point forecasts | Access-gated forecast observations |

The Finland expansion should live in the same `publishers/` package model, with each new source receiving a bootstrap module, runtime publisher module, README, sidecar config, tests where practical, and a completion report under this folder.

## Source Research Summary

### Finnish Meteorological Institute Open Data

Primary URL: `https://en.ilmatieteenlaitos.fi/open-data`
Machine endpoint: `https://opendata.fmi.fi/wfs?request=GetCapabilities`

Relevant datasets:

- weather station observations,
- point weather forecasts,
- air quality observations,
- road weather observations,
- sea and ocean observations,
- wave buoys and mareographs,
- aviation weather reports with FMI's published disclaimer.

Verified during research:

- WFS capabilities endpoint returned XML successfully.
- Helsinki weather observation stored-query sample returned a WFS feature collection.
- Helsinki air-quality stored-query sample returned a WFS feature collection.

Implementation fit:

- Best analogs: `nws`, `uk_air`, `met_office_datahub`, `met_office_global_spot`, `ndbc`, `coops`.
- Main technical issue: parse WFS XML/GML or use an existing FMI Open Data client library, then normalize to CSAPI observations.
- Recommended first scope: one weather-observation publisher and one air-quality publisher, sharing a small FMI WFS helper.

### Fintraffic Digitraffic Road

Primary URL: `https://www.digitraffic.fi/en/road-traffic/`
Swagger: `https://tie.digitraffic.fi/swagger/`

Relevant APIs:

- road weather stations: `/api/weather/v1/stations`, `/api/weather/v1/stations/data`, station history endpoints,
- weather cameras: `/api/weathercam/v1/stations`, `/api/weathercam/v1/stations/data`, image URLs under `weathercam.digitraffic.fi`,
- traffic measurement system stations: `/api/tms/v1/stations`, `/api/tms/v1/stations/data`,
- traffic messages and roadworks,
- variable signs,
- road maintenance vehicle latest locations,
- walking and cycling counters.

Verified during research:

- road weather station metadata returned live GeoJSON,
- road weather latest data returned live JSON,
- weather camera metadata returned live GeoJSON,
- TMS station metadata returned live GeoJSON.

Implementation fit:

- Best analogs: `nws`, `ndbc_buoycam`, `opensky`, `environment_agency_hydrology`.
- Best first Finland publisher because it offers high visual value, no credentials, station geometry, frequent updates, and camera imagery.
- Recommended first scope: curated road weather station observations plus a separate road weather camera image-reference publisher.

### Fintraffic Digitraffic Marine

Primary URL: `https://www.digitraffic.fi/en/marine-traffic/`
Swagger: `https://meri.digitraffic.fi/swagger/`

Relevant APIs:

- AIS vessel locations: `/api/ais/v1/locations`,
- AIS vessel metadata: `/api/ais/v1/vessels`,
- port calls,
- winter navigation,
- sea state estimation from smart AtoN sites,
- AtoN faults,
- MQTT-over-WebSocket vessel and sea-state streams.

Verified during research:

- AIS latest locations returned a live GeoJSON feature collection.

Implementation fit:

- Best analogs: `opensky`, `ndbc`, `coops`.
- Good moving-object demo source that originates from Finland's traffic data infrastructure.
- Recommended first scope: feed-adapter system publishing latest AIS vessel observations for a bounded Finland area or curated vessel subset.

### Fintraffic Digitraffic Railway

Primary URL: `https://www.digitraffic.fi/en/railway-traffic/`
GraphQL: `https://rata.digitraffic.fi/api/v2/graphql`
GTFS-RT locations: `https://rata.digitraffic.fi/api/v1/trains/gtfs-rt-locations`

Relevant APIs:

- currently running trains with latest locations,
- timetables, delays, compositions,
- GTFS and GTFS-RT feeds,
- passenger information messages.

Verified during research:

- GTFS-RT location endpoint returned protobuf successfully.
- Documentation includes GraphQL examples for latest train locations.

Implementation fit:

- Best analogs: `opensky` and `iss`, with richer operational metadata.
- Recommended first scope: GraphQL JSON publisher for currently running trains before adding protobuf GTFS-RT parsing.

### SYKE / Vesi.fi Hydrology

Primary URL: `https://www.vesi.fi/en/`

Relevant domains:

- water level,
- discharge and general water situation,
- flood status,
- snow, ice, soil frost,
- groundwater,
- citizen observations.

Verified during research:

- public site presents current water situation products and identifies SYKE, FMI, Flood Centre, and related Finnish agencies as producers.

Implementation fit:

- Best analogs: `environment_agency_hydrology`, `usgs_water`, `bgs_sensorthings`.
- Requires an additional API reconnaissance pass before coding because the clean machine endpoint is less obvious than FMI or Digitraffic.

## Recommended Implementation Order

### Phase 0: Reconnaissance Hardening

Deliverables:

- `docs/research/finland-publisher-expansion/Finland_Source_Endpoint_Probe_2026-05-29.md`
- endpoint probe scripts or notes for FMI WFS, Digitraffic Road, Digitraffic Marine, Digitraffic Rail, and SYKE/Vesi.fi,
- source licensing and attribution notes,
- selected demo regions and station/source subsets.

Exit criteria:

- each Phase 1 candidate has at least one live, no-secret endpoint probe,
- source timestamps, geometry fields, and source IDs are documented,
- any rate limits or attribution requirements are captured.

### Phase 1: Digitraffic Road Weather

Package target: `publishers/digitraffic_road_weather/`

Scope:

- curated set of 5 to 8 Finnish road weather stations,
- one CSAPI system per road weather station,
- one datastream per station for latest road-weather sensor values,
- preserve station ID, sensor IDs, sensor names, units, source update time, and source URL.

Bootstrap resources:

- procedure UID: `urn:os4csapi:procedure:digitraffic-road-weather:v1`,
- deployment UID: `urn:os4csapi:deployment:digitraffic-road-weather-demo:v1`,
- system UID pattern: `urn:os4csapi:system:digitraffic-road-weather:{stationId}:v1`,
- datastream output name: `roadWeatherObs`.

Runtime source endpoints:

- station metadata: `https://tie.digitraffic.fi/api/weather/v1/stations`,
- latest readings: `https://tie.digitraffic.fi/api/weather/v1/stations/{id}/data` or all-stations latest data.

Acceptance criteria:

- dry-run prints current observations for every curated station,
- bootstrap is idempotent against OSH,
- live publisher posts one observation per station per cycle with 0 errors,
- Explorer map cards show current latest readings and road-weather role classification.

### Phase 2: Digitraffic Road Weather Cameras

Package target: `publishers/digitraffic_weathercam/`

Scope:

- curated set of camera presets associated with Phase 1 stations where possible,
- image-reference observations using Digitraffic image URLs,
- optional thumbnail support via `thumbnail=true`.

Bootstrap resources:

- procedure UID: `urn:os4csapi:procedure:digitraffic-weathercam:v1`,
- datastream output name: `digitrafficWeatherCamImage`.

Runtime source endpoints:

- camera metadata: `https://tie.digitraffic.fi/api/weathercam/v1/stations`,
- camera latest data: `https://tie.digitraffic.fi/api/weathercam/v1/stations/{id}/data`,
- image URL pattern: `https://weathercam.digitraffic.fi/{presetId}.jpg`.

Acceptance criteria:

- cards display live or recent camera imagery,
- image timestamps and preset IDs are preserved,
- no local image cache is required unless direct image hotlinking becomes unreliable.

### Phase 3: FMI Weather And Air Quality

Package targets:

- `publishers/fmi_weather/`,
- `publishers/fmi_air_quality/`,
- optional shared helper: `publishers/fmi_common.py` or package-local utility module.

Scope:

- start with Helsinki plus 3 to 5 additional Finnish cities/stations,
- weather parameters such as temperature, humidity, wind speed/direction, pressure, precipitation,
- air-quality parameters such as NO2, O3, PM10, PM2.5 where available.

Runtime source endpoint:

- `https://opendata.fmi.fi/wfs`

Likely stored queries:

- `fmi::observations::weather::simple`,
- `fmi::observations::airquality::hourly::simple`,
- forecast stored queries after observation publishers are stable.

Implementation choice:

- Prefer a small, well-tested XML/GML parser if the simple stored-query output is stable.
- Consider the `fmiopendata` Python library only if it materially reduces parser risk without adding awkward packaging constraints.

Acceptance criteria:

- weather and air-quality observations publish with current phenomenon times,
- station/source metadata and FMI attribution are preserved,
- Explorer cards classify FMI weather and air-quality sites distinctly from UK/NOAA sources.

### Phase 4: Digitraffic Marine AIS

Package target: `publishers/digitraffic_marine_ais/`

Scope:

- feed-adapter system for live vessel observations,
- optional curated bounding box around Helsinki/Gulf of Finland or Archipelago Sea,
- publish latest AIS state vectors with MMSI, course, speed, heading, navigation status, and source timestamps.

Runtime source endpoints:

- latest locations: `https://meri.digitraffic.fi/api/ais/v1/locations`,
- vessel metadata: `https://meri.digitraffic.fi/api/ais/v1/vessels`.

Acceptance criteria:

- live vessel icons appear on Explorer map without overwhelming feature count,
- source MMSI and vessel metadata are preserved,
- stale vessel positions are filtered or marked explicitly.

### Phase 5: Digitraffic Railway Live Trains

Package target: `publishers/digitraffic_rail_trains/`

Scope:

- currently running trains via GraphQL,
- publish latest train positions with train number, operator, speed, timestamp, and route context,
- later extension to GTFS-RT if useful.

Runtime source endpoints:

- GraphQL: `https://rata.digitraffic.fi/api/v2/graphql`,
- optional GTFS-RT: `https://rata.digitraffic.fi/api/v1/trains/gtfs-rt-locations`.

Acceptance criteria:

- current train locations are published with source timestamps,
- first implementation avoids protobuf unless GraphQL proves insufficient,
- map styling distinguishes trains from aircraft and vessels.

### Phase 6: SYKE / Vesi.fi Hydrology

Package target: to be named after the confirmed API surface.

Scope:

- identify stable API endpoints for water level, discharge, groundwater, snow, ice, or flood observations,
- curate a small national demo set,
- reuse `environment_agency_hydrology` and `usgs_water` patterns.

Acceptance criteria before implementation:

- direct machine endpoint is identified,
- license/attribution is clear,
- latest observation timestamps and station geometry can be retrieved without scraping a user-facing map page.

## Shared Engineering Tasks

1. Add a Finland source classification layer in Explorer only after the first publisher is live.
2. Keep publisher code independent of Explorer UI changes.
3. Reuse current bootstrap helper patterns and stable UID conventions.
4. Add representative thumbnails only when source media is absent and attribution is clean.
5. Add completion reports after each publisher reaches live smoke status.
6. Update `publishers/README.md` and Docker Compose/systemd deployment notes after each accepted source.

## Risks And Controls

| Risk | Control |
| --- | --- |
| FMI WFS XML/GML parsing complexity | Start with simple stored queries and fixture tests; isolate parser in a helper. |
| Digitraffic all-stations feeds are large | Curate station IDs first; use station-specific endpoints or filter client-side with care. |
| Moving-object feeds overwhelm Explorer | Start with bounding boxes, sample caps, and stale filtering. |
| Source labels and units are Finnish/domain-specific | Preserve source names and units; add normalized display labels separately. |
| SYKE API surface unclear | Do not implement until a stable machine endpoint is verified. |
| Demo regressions in existing publishers | Keep Finland packages additive; avoid modifying shared base behavior unless covered by tests. |

## Immediate Next Steps

1. Create `Finland_Source_Endpoint_Probe_2026-05-29.md` with concrete probe results and selected station candidates.
2. Implement `publishers/digitraffic_road_weather/stations.json` with 5 to 8 curated stations.
3. Build `bootstrap_digitraffic_road_weather.py` using existing idempotent bootstrap helpers.
4. Build `digitraffic_road_weather_publisher.py` with `--dry-run`, `--once`, `--interval`, and `--stations`.
5. Run local dry-run and fixture tests.
6. Bootstrap to the target CSAPI server only after dry-run source freshness is verified.
7. Smoke test in Explorer and document the result in this folder.
