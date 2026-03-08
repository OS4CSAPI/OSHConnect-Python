# UAS / Localizer / SENREP — Implementation-Ready Pack Source Materials

> **Date:** 2026-03-08  
> **In response to:** `UAS_Localizer_SENREP_Helpful_Files_List.md`  
> **Repos:**  
> - Explorer/Demo/Scripts: [`OS4CSAPI/ogc-csapi-explorer`](https://github.com/OS4CSAPI/ogc-csapi-explorer)  
> - OSHConnect-Python/Docs: [`OS4CSAPI/OSHConnect-Python`](https://github.com/OS4CSAPI/OSHConnect-Python)

---

## 1. Current Bootstrap Scripts

The **authoritative** bootstrap is `bootstrap_v4.py`. Earlier versions are preserved in git but are superseded.

| Script | Lines | Role | GitHub URL |
|---|---|---|---|
| **`bootstrap_v4.py`** | 1537 | **Authoritative.** Creates ALL UAS/localizer/SENREP resources. Self-contained (no external files). | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py) |
| `bootstrap_localizer.py` | 435 | Creates localizer procedure, system, and datastream (3 resources). | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_localizer.py) |
| `bootstrap_v25.py` | 1080 | v2.5 pack — doctrine-aligned deployments + String Processor/Monitoring Team + AZ-MA-1 from backup. **Superseded by v4.** | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v25.py) |
| `bootstrap_v3.1.py` | 699 | Nested deployment hierarchy + deployedSystemUIDs fix. **Superseded by v4.** | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v3.1.py) |

### What `bootstrap_v4.py` creates

| Category | Count | Details |
|---|---|---|
| **Top-level systems** | 6 | SET-A, Monitoring Site, Relay, AZ-MA-1, AZ-MA-2, AZ-MA-3 |
| **MA subsystems** | 39 | 13 each × 3 nodes (tripod, micarray, edge, comms, power, actuator, mic1–7) |
| **Procedures** | 9 | Audio capture, beamforming, tracking, triangulation, actuation × per-node + shared |
| **Deployment hierarchy** | 10 nodes | ICO → R&S → SSO → SNET → Field 001 → String Alpha → 3 node emplacements + SET/MonSite/Relay emplacements |
| **Datastreams** | 22 | 1 SENREP on SET-A, 7 per MA node × 3 (classification probs, health, LOB, scene summary, SSL, SST, track updates) + detection capabilities per node |
| **Control streams** | 9 | 3 per MA node × 3 (odasControl, snapshot, startStop) |

### What `bootstrap_localizer.py` creates

| Resource Type | Name | UID |
|---|---|---|
| Procedure | WLS LOB Triangulation | `urn:os4csapi:procedure:lob-wls-triangulation:v1` |
| System | AZ String Alpha Localizer | `urn:os4csapi:system:fusion:az-string-alpha-localizer` |
| DataStream | Location Estimate (10-field) | `az_string_alpha_location_estimate` |

---

## 2. Representative Exported Resources

These are live server resources, accessible via the API. Server base URL: `https://os4csapi-osh.duckdns.org/sensorhub/api`  
Auth: `os4csapi:ogc134mm` (Basic `b3M0Y3NhcGk6b2djMTM0bW0=`)

### 2.1 Deployment (6-level hierarchy root)

```
GET /deployments?uid=urn:os4csapi:deployment:ico:ft-huachuca:001
```

Full deployment tree (topmost → leaf):

| Level | Name | UID | Server ID |
|---|---|---|---|
| L0 (root) | Intelligence Collection Op | `urn:os4csapi:deployment:ico:ft-huachuca:001` | `04dg` |
| L1 | Recon & Surveillance Op | `urn:os4csapi:deployment:rso:ft-huachuca:001` | `04e0` |
| L2 | Sensor Surveillance Op | `urn:os4csapi:deployment:sso:ft-huachuca:001` | `04eg` |
| L3 | Sensor Network | `urn:os4csapi:deployment:snet:ft-huachuca:001` | `04f0` |
| L4 | Sensor Field 001 | `urn:os4csapi:deployment:field:ft-huachuca:001` | `04fg` |
| L5 | String Alpha | `urn:os4csapi:deployment:string:ft-huachuca:001` | `04g0` |
| Leaf | Node 1 Emplacement | `urn:os4csapi:deployment:node:ft-huachuca:alpha:001` | `04gg` |
| Leaf | Node 2 Emplacement | `urn:os4csapi:deployment:node:ft-huachuca:alpha:002` | `04h0` |
| Leaf | Node 3 Emplacement | `urn:os4csapi:deployment:node:ft-huachuca:alpha:003` | `04hg` |
| Support | SET-A Emplacement | `urn:os4csapi:deployment:set:ft-huachuca:001` | — |
| Support | Monitoring Site Emplacement | `urn:os4csapi:deployment:monsite:ft-huachuca:001` | — |
| Support | Relay Emplacement | `urn:os4csapi:deployment:relay:ft-huachuca:001` | — |

Each leaf node has `platform@link` referencing its system UID.

### 2.2 System (AZ-MA-1 — richest example)

```
GET /systems?uid=urn:os4csapi:system:odas:az-ma-1
```

AZ-MA-1 has **full rich SensorML metadata** (restored from backup):
- Keywords, identifiers, classifiers, characteristics, capabilities, contacts, documents (photos)
- 13 subsystems (tripod platform + micarray + edge + comms + power + actuator + mic1–7)
- 7 datastreams + 3 control streams

Full SensorML backup: [`scripts/migration_backup/AZ-MA-1_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_sml.json)

### 2.3 System (Localizer — software fusion agent)

```
GET /systems?uid=urn:os4csapi:system:fusion:az-string-alpha-localizer
```

Created by [`bootstrap_localizer.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_localizer.py). Has `typeOf` → procedure `urn:os4csapi:procedure:lob-wls-triangulation:v1`.

### 2.4 System (SET-A — human operator team)

```
GET /systems?uid=urn:os4csapi:system:set:ft-huachuca:001
```

Sensor Employment Team A. Owns the SENREP datastream (server ID `044g`).

### 2.5 Procedure (ODAS Processing Chain)

```
GET /procedures?uid=urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1
```

Backup: [`scripts/migration_backup/procedures/proc_0480.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_0480.json)

### 2.6 Datastream (SENREP)

```
GET /datastreams/044g
GET /datastreams/044g/schema
```

20-field DataRecord. See full schema in Section 3.1 below.

### 2.7 Observation (LOB example)

```
GET /datastreams/04c0/observations?resultTime=latest
```

Returns the most recent LOB observation from AZ-MA-1.

---

## 3. Current Datastream Schemas

### 3.1 SENREP — Sensor Report (20 fields)

**System:** SET-A (`urn:os4csapi:system:set:ft-huachuca:001`)  
**OutputName:** `senrep`  
**Definition:** `https://os4csapi.org/def/csapi/senrepRecordOSH`  
**Source:** [bootstrap_v4.py L451](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L451)

| # | Field | SWE Type | UoM/Constraint | Description |
|---|---|---|---|---|
| 1 | `timestamp` | Time | epochSeconds | Report generation time |
| 2 | `title` | Text | — | Report title |
| 3 | `senderId` | Text | — | Reporting operator ID |
| 4 | `seqNo` | Count | — | Sequence number |
| 5 | `classification` | Text | — | Security classification |
| 6 | `releasably` | Text | — | Releasability marking |
| 7 | `dor` | Text | — | Date of report |
| 8 | `envirOpName` | Text | — | Environment/operation name |
| 9 | `strNo` | Text | — | String number |
| 10 | `detectTimeZ` | Text | — | Detection time (Zulu) |
| 11 | `qty` | Count | — | Quantity observed |
| 12 | `tgtTyp` | Category | VEHICL, UAS, PERS, UNKN | Target type |
| 13 | `subTyp` | Text | — | Sub-type |
| 14 | `spd` | Quantity | km/h | Speed |
| 15 | `dirCardinal` | Category | N,NE,E,SE,S,SW,W,NW | Direction of travel |
| 16 | `colLengthM` | Quantity | m | Column length |
| 17 | `etaLat` | Quantity | deg | Estimated position latitude |
| 18 | `etaLon` | Quantity | deg | Estimated position longitude |
| 19 | `etaTimeZ` | Text | — | Estimated time of arrival (Zulu) |
| 20 | `comments` | Text | — | Free-text remarks |

### 3.2 LOB — Line of Bearing (7 fields, per MA node)

**System:** Each MA node (`az-ma-{1,2,3}`)  
**OutputName:** `az_ma_{n}_lob`  
**Definition:** `lobRecordOSH`  
**Source:** [bootstrap_v4.py L548](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L548)

| # | Field | SWE Type | UoM/Constraint | Description |
|---|---|---|---|---|
| 1 | `timestamp` | Time | epochSeconds | Observation time |
| 2 | `trackId` | Count | — | Track identifier |
| 3 | `bearingTrue` | Quantity | deg (0–360) | True bearing to target |
| 4 | `bearingStdDev` | Quantity | deg | Bearing uncertainty |
| 5 | `sensorLat` | Quantity | deg | Sensor latitude |
| 6 | `sensorLon` | Quantity | deg | Sensor longitude |
| 7 | `classification` | Text | — | Acoustic classification label |

### 3.3 Location Estimate — Localizer Output (10 fields)

**System:** Localizer (`urn:os4csapi:system:fusion:az-string-alpha-localizer`)  
**OutputName:** `az_string_alpha_location_estimate`  
**Definition:** `locationEstimate`  
**Source:** [bootstrap_localizer.py L83](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_localizer.py#L83)

| # | Field | SWE Type | UoM | Description |
|---|---|---|---|---|
| 1 | `timestamp` | Time | epochSeconds | Fix time |
| 2 | `trackId` | Count | — | Track identifier |
| 3 | `estimatedLat` | Quantity | deg | Estimated latitude |
| 4 | `estimatedLon` | Quantity | deg | Estimated longitude |
| 5 | `cep50_m` | Quantity | m | 50% circular error probable |
| 6 | `classification` | Text | — | Classification label |
| 7 | `numContributingLobs` | Count | — | Number of LOBs used |
| 8 | `contributingSensors` | Text | — | CSV list of sensor names |
| 9 | `residual_m` | Quantity | m | Mean intersection residual |
| 10 | `contributingLobsJson` | Text | — | JSON array of contributing LOB data |

### 3.4 Detection Capabilities — Static Range Ring (7 fields, per MA node)

**OutputName:** `az_ma_{n}_detection_capabilities`  
**Definition:** `detectionCapabilitiesRecordOSH`  
**Source:** [add_detection_range.py L44](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/add_detection_range.py#L44)

| # | Field | SWE Type | UoM | Description |
|---|---|---|---|---|
| 1 | `timestamp` | Time | — | Configuration time |
| 2 | `shape` | Text | — | Detection shape (e.g., "circle") |
| 3 | `minRange_m` | Quantity | m | Minimum detection range |
| 4 | `nominalRange_m` | Quantity | m | Nominal detection range |
| 5 | `maxRange_m` | Quantity | m | Maximum detection range |
| 6 | `confidence` | Quantity | 0–1 | Confidence level |
| 7 | `basis` | Text | — | Basis for estimate (e.g., "estimated") |

### 3.5 Classification Probabilities (7 fields, per MA node)

**OutputName:** `az_ma_{n}_classification_probabilities`  
**Source:** [bootstrap_v4.py L499](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L499)

| # | Field | SWE Type | Description |
|---|---|---|---|
| 1 | `timestamp` | Time | — |
| 2 | `trackId` | Count | — |
| 3 | `p_uas` | Quantity | UAS probability |
| 4 | `p_vehicle` | Quantity | Vehicle probability |
| 5 | `p_footsteps` | Quantity | Footsteps probability |
| 6 | `p_impulsive` | Quantity | Impulsive probability |
| 7 | `p_unknown` | Quantity | Unknown probability |

### 3.6 Health Telemetry (6 fields, per MA node)

**OutputName:** `az_ma_{n}_health`  
**Source:** [bootstrap_v4.py L524](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L524)

| # | Field | SWE Type | UoM |
|---|---|---|---|
| 1 | `timestamp` | Time | — |
| 2 | `cpuLoad` | Quantity | % |
| 3 | `memUsedMB` | Quantity | MB |
| 4 | `tempC` | Quantity | °C |
| 5 | `latencyMs` | Quantity | ms |
| 6 | `uptimeS` | Quantity | s |

### 3.7 Scene Summary (4 fields, per MA node)

**OutputName:** `az_ma_{n}_scene_summary`  
**Source:** [bootstrap_v4.py L573](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L573)

| # | Field | SWE Type |
|---|---|---|
| 1 | `timestamp` | Time |
| 2 | `odasTimeStamp` | Time |
| 3 | `trackCount` | Count |
| 4 | `activityLevel` | Text |

### 3.8 SSL Potential Sources (uses DataArray)

**OutputName:** `az_ma_{n}_ssl_potential_sources`  
**Source:** [bootstrap_v4.py L595](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L595)  
Outer: `timestamp`, `odasTimeStamp`, `src` (DataArray of `{x, y, z, E}`)

### 3.9 SST Tracked Sources (uses DataArray)

**OutputName:** `az_ma_{n}_sst_tracked_sources`  
**Source:** [bootstrap_v4.py L634](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L634)  
Outer: `timestamp`, `odasTimeStamp`, `src` (DataArray of `{id, tag, x, y, z, activity}`)

### 3.10 Track Updates (13 fields, per MA node)

**OutputName:** `az_ma_{n}_track_updates`  
**Source:** [bootstrap_v4.py L677](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L677)

| # | Field | SWE Type |
|---|---|---|
| 1 | `timestamp` | Time |
| 2 | `odasTimeStamp` | Time |
| 3–5 | `id`, `tag` | Count, Text |
| 6–8 | `x`, `y`, `z` | Quantity |
| 9 | `activity` | Quantity |
| 10 | `bearingTrue` | Quantity |
| 11 | `elevation` | Quantity |
| 12 | `bearingStdDev` | Quantity |
| 13 | `classLabel`, `classConfidence` | Text, Quantity |

### 3.11 Track State (String Processor — v2.5)

**OutputName:** `track_state`  
**Source:** [bootstrap_v25.py L414](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v25.py#L414)  
Fields: `timestamp`, `globalTrackId`, `lat`, `lon`, `velEastMS`, `velNorthMS`, `speedMS`, `headingDeg`, `posErrorM`, `trackConfidence`, `nSensors`, `method`

### 3.12 Predicted Position (String Processor — v2.5)

**OutputName:** `predicted_position`  
**Source:** [bootstrap_v25.py L434](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v25.py#L434)  
Fields: `timestamp`, `globalTrackId`, `predTime`, `lat`, `lon`, `posErrorM`, `horizonS`, `model`

### Control Streams (3 per MA node)

| Name | Fields |
|---|---|
| `odasControl` | module, parameter, value, applyMode |
| `snapshot` | trackId, durationMs, format |
| `startStop` | action, modules |

---

## 4. Design Docs / ADR-Style Markdown

### Core Architecture & Workflow Design

| Document | Date | Summary | GitHub URL |
|---|---|---|---|
| **SENREP Workflow Design** | 2026-03-04 | Full sensor-to-report pipeline. Identity commitment at reporting tier. `contactId` as join key. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/research/SENREP_Workflow_Design.md) |
| **SENREP / Track FOI Review** | 2026-03-04 | Unanimous decisions: SENREP = Observation, Track = SamplingFeature, SET creates track, `contactId` = sole join key. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/research/SENREP_Track_FOI_Review.md) |
| **Track Visualization Gap Analysis** | 2026-03-04 | Gap: no visible track polyline on map. Recommends Phase 2.5 gold polyline for localizer fix history. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/research/Track_Visualization_Gap_Analysis.md) |
| **Demo Reset & SENREP Resilience** | 2026-03-04 | 3 reset tiers. Provenance fields `sourceFixObsId` and `sourceLobObsIds`. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/research/Demo_Reset_SENREP_Resilience.md) |
| **Demo Reset Hardening Review** | 2026-03 | Additional resilience design review. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/research/Demo_Reset_Hardening_Review.md) |
| **OSH Datastream Scope Leak** | 2026-03 | Documents the scope-leak bug: per-DS observation queries returning all observations. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/research/OSH_Datastream_Observation_Scope_Leak.md) |

### Implementation Plans

| Document | Summary | GitHub URL |
|---|---|---|
| **SENREP Demo Implementation Plan** | Phase 1–3 plan: bootstrap → red diamond markers → click-to-report panel. Status: Implemented. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/planning/SENREP_Demo_Implementation_Plan.md) |
| **Simulator Hardening Plan** | Resilience, concurrency, recovery. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/planning/Simulator_Hardening_Implementation_Plan.md) |
| **Bootstrap Metadata Restoration Plan** | Master plan covering all 10 Work Items (MA metadata, ISS resources, SENREP enrichment, etc.). | [link](https://github.com/OS4CSAPI/OSHConnect-Python/blob/main/docs/research/Bootstrap_Metadata_Restoration_Plan.md) |

### ODAS Data Model / Adapter Docs

| Document | Summary | GitHub URL |
|---|---|---|
| **SOSA/SSN-CSAPI Data Model** | Full ODAS resource model: SSL, SST, LOB, track update schemas. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/ODAS-CSAPI-Adapter-Simulator/sosa-ssn-csapi-data-model.md) |
| **Acoustic Bearing Visualization** | LOB line rendering design. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/ODAS-CSAPI-Adapter-Simulator/acoustic-bearing-visualization-report.md) |
| **Ingestion Report** | 64-resource ingestion trace. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/ODAS-CSAPI-Adapter-Simulator/ingestion-report.md) |
| **Map Visibility Fix** | Observation tracks rendering fixes. | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/ODAS-CSAPI-Adapter-Simulator/map-visibility-fix-report.md) |

---

## 5. Backup SensorML Files

All located in [`scripts/migration_backup/`](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup).

### Top-Level MA Systems (with full rich metadata)

| File | UID | GitHub URL |
|---|---|---|
| `AZ-MA-1_sml.json` | `urn:os4csapi:system:odas:az-ma-1` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_sml.json) |
| `AZ-MA-2_sml.json` | `urn:os4csapi:system:odas:az-ma-2` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_sml.json) |
| `AZ-MA-3_sml.json` | `urn:os4csapi:system:odas:az-ma-3` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_sml.json) |

Each has: keywords, identifiers, classifiers, characteristics, capabilities, contacts, documents (photos).

### Tripod Platforms

| File | UID | GitHub URL |
|---|---|---|
| `AZ-MA-1_Tripod_Platform_sml.json` | `urn:os4csapi:platform:az-ma-1:tripod` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_Tripod_Platform_sml.json) |
| `AZ-MA-2_Tripod_Platform_sml.json` | `urn:os4csapi:platform:az-ma-2:tripod` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_Tripod_Platform_sml.json) |
| `AZ-MA-3_Tripod_Platform_sml.json` | `urn:os4csapi:platform:az-ma-3:tripod` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_Tripod_Platform_sml.json) |

### AZ-MA-1 Subsystems (13 files)

All rich SensorML: `AZ-MA-1_{MICARRAY,EDGE,COMMS,POWER,ACTUATOR,MIC1-MIC7}_sml.json`  
UIDs: `urn:os4csapi:system:odas:az-ma-1:{component}`  
→ [Browse directory](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup)

AZ-MA-2 and AZ-MA-3 follow the identical pattern (13 subsystem files each).

**Total: 42 SensorML backup files + 2 ID maps.**

### Procedures (9 files)

| File | GitHub URL |
|---|---|
| `procedures/proc_0480.json` through `proc_04cg.json` | [Browse](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup/procedures) |

### Datastreams, Observations, Control Streams

| Directory | Files | GitHub URL |
|---|---|---|
| `datastreams/` | 14 (7 ds + 7 schemas) | [Browse](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup/datastreams) |
| `observations/` | 4 | [Browse](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup/observations) |
| `controlstreams/` | 8 (4 cs + 4 schemas) | [Browse](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup/controlstreams) |

---

## 6. Images, Diagrams, and Reference Media

### Images in the repo

| File | Description | GitHub URL |
|---|---|---|
| `demo/public/xmos-7mic-array.jpg` | Photo of the XMOS 7-microphone circular array hardware | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/demo/public/xmos-7mic-array.jpg) |
| `demo/public/qgis_csapi_screenshot.png` | QGIS screenshot showing CSAPI data on map | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/demo/public/qgis_csapi_screenshot.png) |
| `demo/public/csapi_dashboard.png` | CSAPI dashboard screenshot | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/demo/public/csapi_dashboard.png) |
| `demo/public/csapi_ml_dashboard.png` | CSAPI ML dashboard screenshot | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/demo/public/csapi_ml_dashboard.png) |
| `demo/public/os4csapi-icon.svg` | OS4CSAPI icon/logo (SVG) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/demo/public/os4csapi-icon.svg) |
| `demo/src/assets/os4csapi-logo.svg` | OS4CSAPI logo (SVG) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/demo/src/assets/os4csapi-logo.svg) |

### External reference images (already linked in SensorML)

| URL | Used in |
|---|---|
| `https://commons.wikimedia.org/wiki/File:XMOS_xCORE-200_Microphone_Array.jpg` | AZ-MA `documents[]` |
| ISS imagery from Wikimedia | ISS pack system templates |

### Diagrams not yet in repo

No architecture diagrams, deployment diagrams, localizer flowcharts, or SENREP screenshots have been committed yet. These would be valuable additions.

---

## 7. External Reference Links

### Already used in resource metadata or docs

| URL | Context |
|---|---|
| `https://www.xmos.com/microphone-aggregation/` | XMOS mic array vendor page (in MA system contacts) |
| `https://celestrak.org/NORAD/elements/gp.php` | CelesTrak GP element source (ISS publisher) |
| `https://en.wikipedia.org/wiki/International_Space_Station` | ISS reference (in ISS system documents) |
| `https://www.nasa.gov/international-space-station/` | NASA ISS overview |
| `https://github.com/brandon-rhodes/python-sgp4` | SGP4 library (in ISS system documents) |
| `https://os4csapi-osh.duckdns.org/sensorhub/api` | Live CSAPI server endpoint |
| `https://ogc-csapi-explorer.pages.dev` | Live demo webapp |
| `https://github.com/OS4CSAPI/ogc-csapi-explorer` | Explorer repo |
| `https://github.com/OS4CSAPI/OSHConnect-Python` | OSHConnect-Python repo |

### Standards references

| URL | Standard |
|---|---|
| `https://www.ogc.org/standard/sensorthings/` | OGC SensorThings (related) |
| `http://www.opengis.net/spec/ogcapi-connectedsystems-1/1.0` | OGC API Connected Systems Part 1 |
| `http://www.opengis.net/spec/ogcapi-connectedsystems-2/1.0` | OGC API Connected Systems Part 2 |
| `http://www.sensorml.com/sensorML-2.1/` | SensorML 2.1 |
| `http://www.opengis.net/spec/swecommon/2.0` | SWE Common 2.0 |

---

## 8. Naming / UID Conventions

### Pattern: `urn:os4csapi:{category}:{qualifier}:{instance}`

| Category | Pattern | Examples |
|---|---|---|
| **`system`** | `urn:os4csapi:system:{type}:{name}` | `system:odas:az-ma-1`, `system:set:ft-huachuca:001`, `system:fusion:az-string-alpha-localizer` |
| **`platform`** | `urn:os4csapi:platform:{parent}:{component}` | `platform:az-ma-1:tripod` |
| **`deployment`** | `urn:os4csapi:deployment:{echelon}:{location}:{number}` | `deployment:ico:ft-huachuca:001`, `deployment:node:ft-huachuca:alpha:001` |
| **`procedure`** | `urn:os4csapi:procedure:{name}:{version}` | `procedure:lob-wls-triangulation:v1`, `procedure:senrep:sop:v1` |
| **`track`** | `urn:os4csapi:track:{contactId}` | Dynamic, assigned at SENREP submission |
| **`sample`** | `urn:os4csapi:sample:globaltrack:{id}` | `sample:globaltrack:GT-0001` |

### External namespace

| Prefix | Usage | Examples |
|---|---|---|
| `urn:x-odas:procedure:` | ODAS-originated processing procedures | `pdm-mems-audio-capture`, `srp-phat-beamforming`, `particle-filter-tracking` |

### DataStream naming convention

Format: `{node_prefix}_{stream_type}` — examples:
- `az_ma_1_lob`, `az_ma_2_lob`, `az_ma_3_lob`
- `az_ma_1_classification_probabilities`
- `az_ma_1_health`, `az_ma_1_scene_summary`
- `az_ma_1_ssl_potential_sources`, `az_ma_1_sst_tracked_sources`
- `az_ma_1_track_updates`
- `az_ma_1_detection_capabilities`
- `az_string_alpha_location_estimate`
- `senrep`

### Definition URIs

| Definition | Used for |
|---|---|
| `https://os4csapi.org/def/csapi/senrepRecordOSH` | SENREP DataRecord |
| `lobRecordOSH` | LOB DataRecord |
| `locationEstimate` | Localizer output DataRecord |
| `detectionCapabilitiesRecordOSH` | Detection range DataRecord |
| `sosa:System` | System featureType |
| `sosa:ObservingProcedure` | Procedure featureType |

---

## 9. Known Server Limitations

### OSH (OpenSensorHub) Server Bugs

| ID | Description | Impact | Source |
|---|---|---|---|
| **Scope leak** | Per-datastream observation queries return observations from ALL datastreams, with mislabeled `datastream@id`. | Simulator and webapp both implement client-side deduplication/filtering. | [OSH_Datastream_Observation_Scope_Leak.md](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/research/OSH_Datastream_Observation_Scope_Leak.md) |
| **deployment@link dropped** | Server silently drops `deployment@link` properties on datastreams. | Cannot associate DS → deployment directly; must walk deployment tree to `platform@link`. | Scripts comment |
| **controlStream PUT crash** | PUT with CREATE-format field names → 500 error; without `schema` → 400 error (Catch-22). | Control streams effectively read-only after creation. | [crud-smoke-test-phase-2-findings.md](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/crud-smoke-test-phase-2-findings.md) |
| **Case-sensitive paths** | Server rejects camelCase in URL paths (`controlStreams` → must be `controlstreams`). | All URL construction must lowercase path segments. | Same source |
| **REST DS creation** | Server rejects REST-based datastream creation (all Content-Types fail). | Datastreams can only be created via the SWE Common INSERT result mechanism. | [e2e-write-operations-report.md](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/e2e-write-operations-report.md) |
| **Conformance gap** | Server implements Part 1 endpoints but doesn't declare Part 1 conformance classes. | Client must probe empirically rather than relying on conformance document. | [52north-part2-evaluation.md](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/52north-part2-evaluation.md) |
| **Commands nested-only** | 273 commands only accessible via `/controlstreams/{id}/commands`, not top-level `/commands`. | Must know parent CS ID to access commands. | [commands-nested-resource-analysis.md](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/webapp-demo/commands-nested-resource-analysis.md) |

### OSHConnect-Python Library Bugs

| Bug | Workaround | Source |
|---|---|---|
| `StreamableResource.__init__` fails | Patch `_mqtt_client = None` on Node before discovery | [iss_publisher_v3.py](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/iss_publisher_v3.py) |
| `find_system()` UID matching unreliable | Iterate `app._systems` manually | Same |
| `resource_id` not populated on discovered systems | Patch from raw REST response | Same |

### DataArray / Complex Type Limitations

| Limitation | Impact | Source |
|---|---|---|
| Webapp `parseField()` type whitelist | Doesn't support complex nested types in DataRecords (SSL, SST DataArray schemas display as raw JSON). | [issue-101](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/testing/demo-app-findings/issue-101-parse-data-record-complex-types.md) |
| Schema response wrapper | Server wraps schema in extra `resultSchema` property; client needs `data?.resultSchema ?? data`. | [issue-17](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/testing/demo-app-findings/issue-17-schema-response-parser.md) |
| Binary SWE encoding | Out of scope for client. Structural parsing only. | Assessment doc |

---

## 10. Runtime Components (Non-Bootstrap)

These are the **live runtime agents** that produce/consume observations:

### 10.1 Simulator — UAV Flythrough Engine

**Source:** [`simulator/engine.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/simulator/engine.py) + [`simulator/main.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/simulator/main.py)  
**Deployed as:** `simulator.service` on Oracle VM (`129.80.248.53`), port 8000, behind Caddy at `/simulator/*`

Simulates a single drone flying a 14-waypoint SW→NE trajectory through 3 acoustic sensor detection envelopes. For each tick:
- Computes bearing + detection probability per MA node
- Publishes LOB observations to each detecting node's LOB datastream
- Computes WLS bearing intersection (localizer) and publishes location estimate
- Seeds detection range observations on startup

### 10.2 Localizer — LOB Triangulation Agent

**Source:** [`scripts/localizer.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/localizer.py) (536 lines)  
**Deployed as:** `localizer.service` on Oracle VM

Standalone CSAPI consumer/producer:
1. **Consumes:** LOB observations from 3 MA nodes via `GET /datastreams/{id}/observations?resultTime=latest`
2. **Computes:** Weighted Least-Squares bearing intersection (A^T·W·A·x = A^T·W·b)
3. **Produces:** Location estimate observations via `POST /datastreams/{id}/observations`

Quality gates: staleness (15s), correlation window (10s), min LOBs (2), residual cap (500m).

### 10.3 ISS Publisher — Dual-Product Satellite Publisher

**Source:** [`scripts/iss_publisher_v3.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/iss_publisher_v3.py)  
**Deployed as:** `iss-publisher.service` on Oracle VM (currently running v2, v3 ready to deploy)

Two products: position (30s, 11 fields) + orbit ground-track (5min, 100-point prediction).

---

## 11. Demo Webapp — Map Visualization

**Source:** [`demo/src/pages/MapViewPage.vue`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/demo/src/pages/MapViewPage.vue) (5,010 lines)  
**Live:** [https://ogc-csapi-explorer.pages.dev](https://ogc-csapi-explorer.pages.dev)

### Rendered layers relevant to UAS/Localizer/SENREP

| Layer | Color | What it shows |
|---|---|---|
| Deployments | Green | All emplacement positions (recursive hierarchy walk) |
| Detection Ranges | Blue | Min/nominal/max range circles (667m / 1833m / 3000m) |
| Lines of Bearing | Rose | 3000m-length bearing lines from sensor nodes toward detected target |
| Location Estimates | Gold ⊕ | Triangulated UAS position with CEP50 uncertainty circle |
| SENREP Markers | Red ◆ | Human-submitted sensor reports with NATO-style symbology |
| Sampling Features | Purple | Track FOIs from SENREP submissions |
| Observation Tracks | Cyan | GPS trails, ISS orbit, localizer fix history |

### Key behaviors

- **Live mode:** 8-second polling cycle with thundering-herd prevention
- **LOB rendering:** In live mode, uses actual `contributingLobsJson` from localizer observation for exact bearing lines
- **Localizer fix aging:** Progressive fade >15s, disappears >60s
- **SENREP click-to-report:** Operator panel for submitting sensor reports from map context
- **Detection range discovery:** Scans `_detection_capabilities` datastreams per deployment; hardcoded fallbacks for ODAS nodes if API fails due to scope-leak bug

---

## Summary — Minimum Essential Files

If building a pack from the minimum set:

| What | File(s) | URL |
|---|---|---|
| **Bootstrap scripts** | `bootstrap_v4.py` + `bootstrap_localizer.py` | [v4](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py), [localizer](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_localizer.py) |
| **Live resource exports** | Query the API directly (see Section 2 for URLs) | `https://os4csapi-osh.duckdns.org/sensorhub/api` |
| **Schema definitions** | In bootstrap scripts (see Section 3 for all 12+ schemas) | Links in Section 3 |
| **Images** | `xmos-7mic-array.jpg`, `os4csapi-icon.svg`, dashboards | Section 6 |
| **UID conventions** | `urn:os4csapi:{category}:{qualifier}:{instance}` | Section 8 |
| **Rich SensorML backups** | 42 JSON files in `migration_backup/` | [Browse](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup) |
| **Design docs** | 6 research docs + 2 implementation plans | Section 4 |
| **Runtime agents** | `localizer.py`, `simulator/`, `iss_publisher_v3.py` | Section 10 |
| **Known limitations** | 7 server bugs + 3 library bugs + 3 client issues | Section 9 |
