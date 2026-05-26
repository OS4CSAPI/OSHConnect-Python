# Environment Agency Hydrology Publisher Completion Report

Date: 2026-05-26

## Summary

The first prioritized new publisher source, Environment Agency Hydrology, has been implemented and proven against the configured OS4CSAPI server. The work produced a new station-network publisher package that bootstraps curated Environment Agency hydrology resources into CSAPI and publishes live/latest readings for river level, river flow, rainfall, and groundwater level.

This completes the planned first implementation step from the Environment Agency Hydrology publisher plan.

## Completed Work

### Publisher Package

Added a new package:

`publishers/environment_agency_hydrology/`

Files added:

- `__init__.py`
- `stations.json`
- `README.md`
- `bootstrap_environment_agency_hydrology.py`
- `environment_agency_hydrology_publisher.py`

The package follows the station-network pattern used by the mature USGS Water publisher, with a curated sidecar that keeps the initial runtime footprint small and predictable.

### Curated Source Coverage

The first-pass sidecar covers four Environment Agency stations and five selected measures:

| Station | EA station notation | Measure coverage |
| --- | --- | --- |
| Beggearn Huish | `48513a18-e485-4317-ae92-93bf4f7f3e54` | River level, river flow |
| Cosford | `d52d0eab-1e64-4d76-a1f2-e81c7948d2c0_435510` | Rainfall |
| Burton Coggles | `c7e13884-4a02-4df3-b184-09aea28cf8e8_3_020` | Groundwater level |
| Iwood | `959f3e4f-bb6e-4f4a-8082-0157eea99482` | River flow |

Iwood station coordinates were rechecked against the live Environment Agency station resource and corrected to `51.363977, -2.78889`.

### Bootstrap Implementation

The bootstrap creates:

- One procedure: `urn:os4csapi:procedure:environment-agency-hydrology:v1`
- One CSAPI system per curated Environment Agency station
- One datastream per selected measure
- A root deployment, station group deployment, and one station deployment per system

The bootstrap uses the shared idempotent helper pattern:

- GeoJSON stubs for initial CSAPI resource creation
- SensorML PUT for richer procedure/system metadata where accepted by the server
- Datastream schemas with SWE DataRecord fields
- `--dry-run`, `--clean`, `--clean-only`, and `--force-sml` support

CSAPI UIDs sanitize Environment Agency station notation before embedding it in resource identifiers. This avoids server instability around source identifiers that contain underscores while preserving the original Environment Agency notation in metadata and observations.

Deployment descriptions now explicitly identify the resources as Environment Agency hydrology monitoring stations and water sensor systems. This gives the Explorer symbol classifier enough semantic signal to avoid the generic blank friendly land-unit rectangle fallback.

### Explorer Symbol Classification

Environment Agency Hydrology was aligned with the existing water/weather station publishers for NATO/STANAG display. The closest established symbol family is the friendly emplaced sensor symbol already used for USGS Water, CO-OPS, NDBC, and NWS station resources.

The Explorer symbol mapper was updated so Environment Agency Hydrology keywords such as `environment agency`, `ea hydrology`, `hydrology`, `river level`, `river flow`, `rainfall`, and `groundwater` classify to the same legacy SIDC:

```text
SFGPEWRH-------
```

This replaces the previous fallback behavior where the deployment rendered as a blank blue rectangle.

The Environment Agency rule is intentionally ordered before the generic `monitoring station` rule so hydrology stations use the water/weather sensor symbol family rather than the broader monitoring-site symbol.

### Explorer Latest Observation Display

The Explorer deployed-system card path was updated to show meaningful latest observation values for station-style deployments, including Environment Agency Hydrology.

Implemented behavior:

- The card model fetches latest observations for up to the first three datastreams on the selected deployed system.
- The side card renders a `Latest readings` section with label, value, unit, relative observation age, freshness state, and source quality when present.
- The map click popup renders the first one or two latest readings as a compact quick-look summary.
- Freshness is calculated from `phenomenonTime`, preserving the distinction between observed time and CSAPI publish/result time.
- Stale values, such as older groundwater readings, are explicitly marked instead of appearing as current data.

The implementation is generic rather than Environment Agency-only, so comparable environmental station publishers can reuse the same side-card and popup behavior.

### Runtime Publisher Implementation

The runtime publisher:

- Loads curated station/measure definitions from `stations.json`
- Queries Environment Agency readings with the proven shape:
  - `https://environment.data.gov.uk/hydrology/data/readings.json?measure=<encoded-measure-uri>&latest=true&_limit=1`
- Normalizes readings into CSAPI observation results
- Preserves source measure identity, station identity, parameter, value type, unit, quality, completeness, and source URL
- Treats source timestamps as UTC/GMT when no explicit offset is present
- Discovers CSAPI system and datastream IDs dynamically from server UIDs/output names
- Dedupe-skips unchanged readings during a running process
- Supports `--dry-run`, `--once`, `--interval`, and `--stations`
- Includes basic upstream HTTP 429 cooldown behavior

## Validation Results

### Local Validation

Python compile validation passed for both new modules:

- `publishers/environment_agency_hydrology/bootstrap_environment_agency_hydrology.py`
- `publishers/environment_agency_hydrology/environment_agency_hydrology_publisher.py`

Editor diagnostics reported no errors for the new package files or the updated publisher README.

### Source-Only Dry Run

The runtime dry run successfully fetched and normalized all five curated readings with zero errors:

- Beggearn Huish river level
- Beggearn Huish river flow
- Cosford rainfall
- Burton Coggles groundwater level
- Iwood river flow

### Server Bootstrap

The live bootstrap completed against:

`https://os4csapi-osh.duckdns.org/sensorhub/api`

Created or confirmed resources included:

- Environment Agency Hydrology procedure
- Four station systems
- Five datastreams
- Root deployment
- Station group deployment
- Four station deployments

### Live Publish Cycle

A live one-shot publish cycle succeeded:

- Published: `5`
- Errors: `0`
- Skipped: `0`
- Reconnects: `0`

The publisher connected to all four systems and posted one observation for each curated measure.

## Server Compatibility Findings

Several server-specific behaviors were discovered and handled during implementation:

### System POST Can Return 500 After Successful Creation

The server sometimes returned HTTP 500 during system creation even though the system had actually been created. The bootstrap now detects this pattern by re-querying the expected UID after a 500 from `/systems` and recovering the created server ID when present.

### Source IDs Need CSAPI-Safe UID Tokens

Environment Agency station notations can contain underscores. The bootstrap now uses sanitized tokens in CSAPI UIDs while preserving the original source notation in station metadata and observation results.

An orphan raw-underscore Cosford system from an early failed attempt was checked after cleanup and no longer existed.

### Groundwater Unit Needs UCUM-Compatible Schema Code

Environment Agency groundwater level is reported as `mAOD`, which is source-accurate but not accepted as a UCUM code in the SWE schema. The datastream schema now uses `m` as the UCUM-compatible `uom.code`, while the runtime result still reports the source unit as `mAOD` and the result field remains `groundwater_level_mAOD`.

### Runtime Result Fields Must Match Schema Order

The server enforces the DataRecord result fields strictly. The runtime was adjusted so observation result fields match the created datastream schema exactly.

### System SensorML PUT Currently Fails on This Server

Procedure SensorML is accepted. System SensorML PUTs currently return HTTP 500 for all Environment Agency station systems on the configured server. This does not block the operational path: systems, datastreams, deployments, and live observations are present and working. The bootstrap logs the skipped SensorML PUTs and continues.

## Documentation Updates

Updated `publishers/README.md` to include Environment Agency Hydrology in the publisher fleet and bootstrap command list.

Added package-local usage documentation in `publishers/environment_agency_hydrology/README.md`, including:

- Bootstrap commands
- Runtime commands
- Source API notes
- Groundwater representation notes
- Quality metadata notes

## Current Operational Commands

Bootstrap:

```powershell
py -m publishers.environment_agency_hydrology.bootstrap_environment_agency_hydrology
```

Dry-run runtime:

```powershell
py -m publishers.environment_agency_hydrology.environment_agency_hydrology_publisher --dry-run --once
```

Publish one live cycle:

```powershell
py -m publishers.environment_agency_hydrology.environment_agency_hydrology_publisher --once
```

Run continuously at the default 15-minute cadence:

```powershell
py -m publishers.environment_agency_hydrology.environment_agency_hydrology_publisher
```

## Completion Status

The Environment Agency Hydrology publisher implementation is complete for the first curated pass.

Completed acceptance points:

- Curated Environment Agency source selection exists
- Bootstrap package exists
- Runtime publisher exists
- Dry run succeeds
- Server bootstrap succeeds enough to create operational CSAPI resources
- Live observation publishing succeeds
- Publisher fleet documentation is updated

Recommended follow-on work:

- Add a scheduled/service runner entry if this publisher should run continuously with the production fleet
- Investigate the server-side HTTP 500 on system SensorML PUTs if rich system metadata display becomes a requirement
- Expand the curated sidecar after the demo path is stable, prioritizing additional fresh groundwater and river-flow measures
