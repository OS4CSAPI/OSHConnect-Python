# BGS SensorThings Publisher Implementation Plan

Date: 2026-05-26

## Status

Selected for publisher #3 after Environment Agency Hydrology and UK-AIR. This plan chooses the BGS SensorThings telemetry branch rather than the BGS earthquake GeoRSS branch because it adds a new standards-rich interoperability story and avoids duplicating the existing USGS earthquake event-feed pattern.

## Source

Primary source: BGS Sensor Data Service

- Landing page: https://sensors.bgs.ac.uk/
- API documentation: https://sensors.bgs.ac.uk/api.html
- SensorThings root: https://sensors.bgs.ac.uk/FROST-Server/v1.1
- OpenAPI endpoint: https://sensors.bgs.ac.uk/FROST-Server/v1.1/api
- Interactive docs: https://sensors-docs.bgs.ac.uk/

The service is an OGC SensorThings API v1.1 endpoint backed by FROST Server. It exposes Things, Locations, Datastreams, ObservedProperties, Sensors, FeaturesOfInterest, Observations, and MultiDatastreams.

## Access And Usage

The probed SensorThings endpoints responded publicly without authentication. Curated datastreams are restricted to records whose source metadata reports:

- `access_restriction`: `Unrestricted`
- `data_usage`: available under the Open Government Licence with BGS/UKRI acknowledgement language

The publisher will preserve the source `data_usage` text and include OGL/BGS documentation links in SensorML metadata. The curated sidecar normalizes the source acknowledgement text to ASCII as `Contains UKRI materials (c) UKRI [year]`.

## Live Probe Results

Verified endpoints:

- `https://sensors.bgs.ac.uk/FROST-Server/v1.1` returned SensorThings collection links.
- `https://sensors.bgs.ac.uk/FROST-Server/v1.1/Things?$top=5` returned BGS groundwater logger Things with rich properties.
- `https://sensors.bgs.ac.uk/FROST-Server/v1.1/Datastreams?$top=5&$expand=Thing,ObservedProperty,Sensor` returned expanded datastream metadata, units, observed areas, phenomenon time ranges, access restriction, and data usage.
- `https://sensors.bgs.ac.uk/FROST-Server/v1.1/Observations?$top=80&$orderby=phenomenonTime desc&$expand=Datastream($expand=Thing,ObservedProperty)` returned recent numeric observations from downhole hydro loggers.

Recent curated observation candidates included April 2026 measurements from:

- Downhole hydro logger GGA01
- Downhole hydro logger GGA05
- Downhole hydro logger GGA07

## Curated First Pass

Use three UKGEOS Glasgow downhole hydro loggers:

| Thing ID | Thing | Coordinates | Selected datastreams |
| --- | --- | --- | --- |
| 195 | Downhole hydro logger GGA01 | -4.200163, 55.839415 | water temperature, conductivity, water level maOD |
| 197 | Downhole hydro logger GGA05 | -4.199619, 55.837690 | water temperature, conductivity, water level maOD |
| 200 | Downhole hydro logger GGA07 | -4.201172, 55.838337 | water temperature, conductivity, water level maOD |

The selected set keeps the demo small, uses consistent observed properties across stations, and shows geothermal/groundwater telemetry rather than another generic environmental station network.

## CSAPI Model

Pattern: station-network model based on `publishers/environment_agency_hydrology` and `publishers/usgs_water`, with strict bootstrap practices from `publishers/aviation_wx` and `publishers/bootstrap_helpers.py`.

- Procedure: one BGS SensorThings telemetry ingestion procedure.
- Systems: one CSAPI system per BGS SensorThings Thing.
- Datastreams: one CSAPI datastream per selected BGS SensorThings Datastream.
- Deployments: one top-level BGS SensorThings demo deployment, one UKGEOS Glasgow grouping deployment, and one station deployment per logger.
- Observations: one CSAPI observation per latest changed SensorThings observation.

Observation result fields:

- `thingId`
- `sourceThingId`
- `sourceDatastreamId`
- `observedProperty`
- source-specific numeric field, such as `waterTemperatureC`, `conductivityUsCm`, or `waterLevelMaodM`
- `unit`
- `sourceObservationId`
- `sourceUrl`

## Runtime Strategy

- Load curated Things and Datastreams from `publishers/bgs_sensorthings/stations.json`.
- Fetch latest observation via `/Datastreams({id})/Observations?$top=1&$orderby=phenomenonTime desc`.
- Normalize SensorThings phenomenon/result timestamps to UTC ISO strings.
- Preserve source observation ID and `parameters.publish_yn`/`parameters.sen_id` when present.
- Dedupe by `datastreamId|sourceObservationId|phenomenonTime|value` during a running process.
- Support `--dry-run`, `--once`, `--interval`, and `--stations`.

## Explorer Readiness

Expected first-pass Explorer behavior should show three BGS deployed systems near Glasgow. If generic classification is weak, add Explorer symbol/role rules for BGS, SensorThings, UKGEOS, groundwater, and geothermal telemetry after the first live publish.

No station-specific image source was found during initial probing. If the card needs a visual anchor, use only accurately attributed representative UKGEOS/BGS media after separate image research, or leave the card without an image rather than implying a station-specific photograph.

## Validation Checklist

1. Compile the new Python modules.
2. Run dry-run publisher fetches.
3. Bootstrap to live OSH with `--force-sml`.
4. Run one live publish cycle.
5. Read back systems, datastreams, and observations from CSAPI.
6. Verify Explorer map/card visibility on the production OSH preset.
7. Document completion and any Explorer polish changes.
