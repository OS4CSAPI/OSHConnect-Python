# Bootstrap & Metadata Restoration Plan

**Date:** March 8, 2026  
**Status:** Planning  
**Server:** `https://os4csapi-osh.duckdns.org/sensorhub/api`  
**Repos:**  
- Explorer & Bootstrap Scripts: [OS4CSAPI/ogc-csapi-explorer](https://github.com/OS4CSAPI/ogc-csapi-explorer)  
- OSHConnect-Python: [OS4CSAPI/OSHConnect-Python](https://github.com/OS4CSAPI/OSHConnect-Python)  

---

## Problem Statement

The server hosts 8 top-level systems and 39 subsystems, created by three separate bootstrap pathways. Rich SensorML metadata (keywords, identifiers, classifiers, characteristics, capabilities, contacts, documents/photos) was recently restored from backup files via a one-time script, but **none of the bootstrap scripts would reproduce this metadata on a fresh server**. A clean re-bootstrap from any of the existing scripts would produce bare shells and lose all enriched metadata.

This plan catalogs every bootstrapped resource, maps it to its metadata source files, and defines the work items needed to ensure all bootstrap scripts produce fully enriched SensorML — so the server can be rebuilt from scratch without metadata loss.

---

## Current Bootstrap Architecture

There are **three independent bootstrap pathways**, each owning a distinct set of server resources:

| # | Bootstrap Script | Owner | Resources Created | Rich SensorML? |
|---|---|---|---|---|
| 1 | [`bootstrap_v4.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py) | UAS/LOB Demo Simulator | 6 systems, 39 subsystems, 25 datastreams, 9 control streams, 13 deployments | **No** — bare GeoJSON only |
| 2 | [`bootstrap_localizer.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_localizer.py) | LOB Triangulator (Localizer) | 1 system, 1 procedure, 1 datastream | **No** — bare GeoJSON only |
| 3 | *(none — created manually)* | ISS Tracker | 1 system, 1 procedure, 1 datastream, 2 deployments | **No** — bare GeoJSON only |

### Runtime Services (consumers, not bootstrappers)

| Service | Script | Depends On | Self-Bootstraps? |
|---|---|---|---|
| ISS Publisher | [`iss_publisher_v2.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/iss_publisher_v2.py) | ISS Tracker system + datastream pre-existing | **No** — discovers by UID |
| LOB Localizer | [`localizer.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/localizer.py) | Localizer system + datastream pre-existing | **No** — errors with "Run bootstrap_localizer.py first" |
| UAS Simulator | [`simulator/main.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/simulator/main.py) | All MA systems + datastreams pre-existing | **No** — writes to existing datastreams |

---

## Section 1: UAS/LOB Demo Data Simulator

**Bootstrap script:** [`bootstrap_v4.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py)  
**Backup directory:** [`scripts/migration_backup/`](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup)

### 1.1 Top-Level Systems (6)

| System Name | UID | Server ID | SensorML Backup File | Backup Has Rich Metadata? |
|---|---|---|---|---|
| Sensor Employment Team (SET-A) | `urn:os4csapi:system:set:ft-huachuca:001` | `040g` | **None** | N/A — no backup exists |
| Monitoring Site Node 1 | `urn:os4csapi:system:monitoring-site-node:ft-huachuca:001` | `0410` | **None** | N/A — no backup exists |
| Relay / Repeater 001 | `urn:os4csapi:system:relay:vhf-repeater:ft-huachuca:001` | `041g` | **None** | N/A — no backup exists |
| ODAS Mic Array Node AZ-MA-1 | `urn:os4csapi:system:odas:az-ma-1` | `0420` | [`AZ-MA-1_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_sml.json) | **Yes** — keywords, identifiers, classifiers, characteristics (DSP pipeline), capabilities, contacts, 6 documents |
| ODAS Mic Array Node AZ-MA-2 | `urn:os4csapi:system:odas:az-ma-2` | `0490` | [`AZ-MA-2_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_sml.json) | **Yes** — same as MA-1 |
| ODAS Mic Array Node AZ-MA-3 | `urn:os4csapi:system:odas:az-ma-3` | `049g` | [`AZ-MA-3_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_sml.json) | **Yes** — same as MA-1 |

### 1.2 Subsystems (13 per MA node × 3 = 39)

Each MA node has the following 13 subsystems. The table shows the AZ-MA-1 file; AZ-MA-2 and AZ-MA-3 follow the same `AZ-MA-{n}_{SUBSYS}_sml.json` naming pattern.

| Subsystem | UID Pattern | SensorML Backup (MA-1) | Rich Fields Present |
|---|---|---|---|
| Tripod Platform | `urn:os4csapi:platform:az-ma-{n}:tripod` | [`AZ-MA-1_Tripod_Platform_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_Tripod_Platform_sml.json) | **None** — bare shell |
| MICARRAY (7-mic array) | `urn:os4csapi:system:odas:az-ma-{n}:micarray` | [`AZ-MA-1_MICARRAY_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MICARRAY_sml.json) | keywords(10), identifiers(3: ShortName/Manufacturer/ModelNumber), classifiers(2), characteristics(4: physical), capabilities(6: rate/ADC/channels/tracked/freq), contacts(2: XMOS+IntRoLab), documents(6: photo/lib/papers/wiki/video) |
| EDGE (Raspberry Pi 4B) | `urn:os4csapi:system:odas:az-ma-{n}:edge` | [`AZ-MA-1_EDGE_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_EDGE_sml.json) | keywords(8), identifiers(1), classifiers(2), characteristics(5: runtime/OS/frame/hop/rate), contacts(1), documents(5: lib/papers/wiki/video) |
| COMMS | `urn:os4csapi:system:odas:az-ma-{n}:comms` | [`AZ-MA-1_COMMS_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_COMMS_sml.json) | keywords(7), identifiers(1), classifiers(1), contacts(1) |
| POWER | `urn:os4csapi:system:odas:az-ma-{n}:power` | [`AZ-MA-1_POWER_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_POWER_sml.json) | keywords(7), identifiers(1), classifiers(1), characteristics(2: battery/charging), contacts(1) |
| ACTUATOR (pan-tilt) | `urn:os4csapi:system:odas:az-ma-{n}:actuator` | [`AZ-MA-1_ACTUATOR_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_ACTUATOR_sml.json) | keywords(8), identifiers(1), classifiers(1), capabilities(2: pan 360°/tilt 90°), contacts(1) |
| MIC1 | `urn:os4csapi:system:odas:az-ma-{n}:mic1` | [`AZ-MA-1_MIC1_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC1_sml.json) | keywords(4), identifiers(1), classifiers(1), characteristics(2: transducer/position), capabilities(3: rate/depth/sensitivity), contacts(1), documents(1: photo) |
| MIC2 | `urn:os4csapi:system:odas:az-ma-{n}:mic2` | [`AZ-MA-1_MIC2_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC2_sml.json) | Same as MIC1 |
| MIC3 | `urn:os4csapi:system:odas:az-ma-{n}:mic3` | [`AZ-MA-1_MIC3_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC3_sml.json) | Same as MIC1 |
| MIC4 | `urn:os4csapi:system:odas:az-ma-{n}:mic4` | [`AZ-MA-1_MIC4_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC4_sml.json) | Same as MIC1 |
| MIC5 | `urn:os4csapi:system:odas:az-ma-{n}:mic5` | [`AZ-MA-1_MIC5_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC5_sml.json) | Same as MIC1 |
| MIC6 | `urn:os4csapi:system:odas:az-ma-{n}:mic6` | [`AZ-MA-1_MIC6_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC6_sml.json) | Same as MIC1 |
| MIC7 (center) | `urn:os4csapi:system:odas:az-ma-{n}:mic7` | [`AZ-MA-1_MIC7_sml.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC7_sml.json) | Same as MIC1 |

### 1.3 Procedures (9 in backup, 0 created by bootstrap_v4)

`bootstrap_v4.py` references 6 procedure UIDs via `typeOf` but **never creates any of them**. The backup contains 9 procedure files:

| Procedure Name | UID | Backup File | Referenced by v4 `typeOf`? |
|---|---|---|---|
| PDM MEMS Audio Capture | `urn:x-odas:procedure:pdm-mems-audio-capture` | [`proc_0480.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_0480.json) | **Yes** — MICARRAY, MIC1–MIC7 |
| SRP-PHAT Beamforming | `urn:x-odas:procedure:srp-phat-beamforming` | [`proc_048g.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_048g.json) | Defined but unused |
| Particle Filter Tracking | `urn:x-odas:procedure:particle-filter-tracking` | [`proc_0490.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_0490.json) | Defined but unused |
| Ray-to-Ray 3D Triangulation | `urn:x-odas:procedure:ray-to-ray-triangulation` | [`proc_049g.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_049g.json) | Defined but unused |
| ODAS Config Actuation | `urn:x-odas:procedure:odas-config-actuation` | [`proc_04a0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04a0.json) | **Yes** — ACTUATOR |
| AZ-MA-1 Calibration | `urn:os4csapi:procedure:odas:az-ma-1:calibration:v1` | [`proc_04b0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04b0.json) | No |
| AZ-MA-1 Health Monitor | `urn:os4csapi:procedure:odas:az-ma-1:health-monitor:v1` | [`proc_04bg.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04bg.json) | No |
| AZ-MA-1 Processing Chain | `urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1` | [`proc_04c0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04c0.json) | **Yes** — EDGE |
| AZ-MA-1 Frame Transform | `urn:os4csapi:procedure:odas:az-ma-1:frame-transform:v1` | [`proc_04cg.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04cg.json) | No |

### 1.4 Datastreams (25 created by v4, 7 in backup)

| Datastream Name Pattern | # Created | Backup File (MA-1) | Notes |
|---|---|---|---|
| SENREP (Sensor Report) | 1 (on SET-A) | **None** | — |
| AZ-MA-{n} SSL Potential Sources | 3 | [`ds_07fg2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07fg2.json) / [`schema_07fg2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07fg2.json) | — |
| AZ-MA-{n} SST Tracked Sources | 3 | [`ds_07g02.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07g02.json) / [`schema_07g02.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07g02.json) | — |
| AZ-MA-{n} LOB | 3 | [`ds_07gg2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07gg2.json) / [`schema_07gg2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07gg2.json) | — |
| AZ-MA-{n} Track Updates | 3 | [`ds_07h02.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07h02.json) / [`schema_07h02.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07h02.json) | — |
| AZ-MA-{n} Classification Probs | 3 | [`ds_07hg2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07hg2.json) / [`schema_07hg2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07hg2.json) | — |
| AZ-MA-{n} Health | 3 | [`ds_07i02.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07i02.json) / [`schema_07i02.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07i02.json) | — |
| AZ-MA-{n} Scene Summary | 3 | [`ds_07ig2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07ig2.json) / [`schema_07ig2.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07ig2.json) | — |
| AZ-MA-{n} Detection Capabilities | 3 | **None** | Added after migration; no backup |

### 1.5 Control Streams (9 created by v4, 4 in backup)

| Control Stream Name Pattern | # Created | Backup File (MA-1) |
|---|---|---|
| AZ-MA-{n} ODAS Control | 3 | [`cs_04dg.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04dg.json) / [`schema_04dg.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04dg.json) |
| AZ-MA-{n} Request Snapshot | 3 | [`cs_04e0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04e0.json) / [`schema_04e0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04e0.json) |
| AZ-MA-{n} Start Stop | 3 | [`cs_04eg.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04eg.json) / [`schema_04eg.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04eg.json) |
| AZ-MA-{n} Calibrate Orientation | **0** — not created by v4 | [`cs_04d0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04d0.json) / [`schema_04d0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04d0.json) |

### 1.6 Deployment Hierarchy (13 nodes)

| Deployment Name | UID | Platform Link |
|---|---|---|
| ICO (root) | `urn:os4csapi:deployment:ico:ft-huachuca:001` | — |
| └─ R&S Operation | `urn:os4csapi:deployment:rso:ft-huachuca:001` | — |
| &emsp;└─ SSO | `urn:os4csapi:deployment:sso:ft-huachuca:001` | SET-A |
| &emsp;&emsp;├─ SET-A Emplacement | `urn:os4csapi:deployment:set:ft-huachuca:001` | → SET-A System |
| &emsp;&emsp;└─ Sensor Network | `urn:os4csapi:deployment:snet:ft-huachuca:001` | MonSite + Relay |
| &emsp;&emsp;&emsp;├─ MonSite Emplacement | `urn:os4csapi:deployment:monsite:ft-huachuca:001` | → MonSite System |
| &emsp;&emsp;&emsp;├─ Relay Emplacement | `urn:os4csapi:deployment:relay:ft-huachuca:001` | → Relay System |
| &emsp;&emsp;&emsp;├─ Field 001 | `urn:os4csapi:deployment:field:ft-huachuca:001` | — (leaf) |
| &emsp;&emsp;&emsp;└─ String Alpha | `urn:os4csapi:deployment:string:ft-huachuca:001` | — |
| &emsp;&emsp;&emsp;&emsp;├─ Node 1 | `urn:os4csapi:deployment:node:ft-huachuca:alpha:001` | → AZ-MA-1 |
| &emsp;&emsp;&emsp;&emsp;├─ Node 2 | `urn:os4csapi:deployment:node:ft-huachuca:alpha:002` | → AZ-MA-2 |
| &emsp;&emsp;&emsp;&emsp;└─ Node 3 | `urn:os4csapi:deployment:node:ft-huachuca:alpha:003` | → AZ-MA-3 |

---

## Section 2: ISS Tracker

**Bootstrap script:** **None exists** — system was created manually via ad-hoc API calls  
**Runtime publisher:** [`iss_publisher_v2.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/iss_publisher_v2.py) (uses OSHConnect-Python, discovers by UID)  
**Legacy publisher:** [`iss_publisher.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/iss_publisher.py) (raw urllib, hardcoded IDs)  
**Implementation doc:** [`docs/implementation/iss-satellite-tracking-summary.md`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/implementation/iss-satellite-tracking-summary.md)

### 2.1 Server Resources (all manually created)

| Resource Type | Name | UID | Server ID | SensorML Backup | Rich Metadata? |
|---|---|---|---|---|---|
| Procedure | ISS SGP4 Tracker | *(unknown — created ad-hoc)* | `045g` | **None** | **No** — bare |
| System | ISS Tracker (SGP4 Position Feed) | `urn:os4csapi:system:iss-tracker:v1` | `04ng` | **None** | **No** — bare (label + description only) |
| DataStream | ISS Position (SGP4) | *(server-assigned)* | `04fg` | **None** | Schema: `lat_deg`, `lon_deg`, `alt_km`, `velocity_km_s` |
| Deployment (root) | *(unknown name)* | *(unknown)* | `048g` | **None** | — |
| Deployment (leaf) | *(unknown name)* | *(unknown)* | `0490` | **None** | — |

### 2.2 Metadata That Should Be Created

The ISS Tracker system (`04ng`) currently has zero SensorML rich fields. Suggested enrichment:

- **keywords**: ISS, Zarya, NORAD 25544, satellite, SGP4, orbital propagation, space station, LEO
- **identifiers**: ShortName (ISS), NORAD ID (25544), COSPAR ID (1998-067A)
- **classifiers**: Platform Type (Space Station), Orbit Class (LEO)
- **characteristics**: Orbital period (~92.7 min), inclination (51.6°), altitude range (408–420 km)
- **capabilities**: Position update rate (30s), propagation model (SGP4), TLE source (CelesTrak)
- **contacts**: NASA, CelesTrak
- **documents**: CelesTrak GP data source URL, ISS Wikipedia page, SGP4 reference, TLE format spec

---

## Section 3: LOB Triangulator (Localizer)

**Bootstrap script:** [`bootstrap_localizer.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_localizer.py)  
**Runtime service:** [`localizer.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/localizer.py)

### 3.1 Server Resources

| Resource Type | Name | UID | Server ID | SensorML Backup | Rich Metadata? |
|---|---|---|---|---|---|
| Procedure | WLS LOB Triangulation v1 | `urn:os4csapi:procedure:lob-wls-triangulation:v1` | *(server-assigned)* | **None** | **No** — bare GeoJSON (name + description only) |
| System | AZ-String-Alpha LOB Triangulator | `urn:os4csapi:system:fusion:az-string-alpha-localizer` | `04o0` | **None** | **No** — bare GeoJSON (name + description + typeOf) |
| DataStream | UAS Location Estimate | `az_string_alpha_location_estimate` | *(server-assigned)* | **None** | Schema: 10 fields (timestamp, trackId, lat, lon, cep50_m, classification, numContributingLobs, contributingSensors, residual_m, contributingLobsJson) |

### 3.2 Metadata That Should Be Created

The LOB Triangulator system (`04o0`) and its procedure currently have zero SensorML rich fields. Suggested enrichment:

- **keywords**: LOB, triangulation, WLS, bearing intersection, C-UAS, acoustic localization, fusion
- **identifiers**: ShortName (AZ-String-Alpha Localizer), Version (v1)
- **classifiers**: System Type (Fusion Agent), Algorithm Class (Weighted Least Squares)
- **characteristics**: Correlation window (10s), max LOB age (15s), min LOBs required (2), residual cap (500m), poll interval (5s)
- **capabilities**: CEP50 accuracy (varies), max simultaneous tracks (1), contributing sensor count (up to 3)
- **contacts**: Operator (OS4CSAPI project)
- **documents**: WLS bearing intersection algorithm reference

---

## Gap Analysis & Work Items

### WI-1: `bootstrap_v4.py` → `bootstrap_v5.py` — Use `sml+json` for Rich Metadata

**Priority: Critical**  
**Scope:** Rewrite system/subsystem creation to POST `application/sml+json` format instead of bare `application/geo+json`.

The backup SML files in [`scripts/migration_backup/`](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup) are the source of truth. The v5 bootstrap should:

1. Load MA-1 backup SML files directly
2. Derive MA-2/MA-3 via UID string substitution (same approach v4 already uses for GeoJSON)
3. POST all systems with `Content-Type: application/sml+json`

**Files involved:** All 42 `*_sml.json` files in [`scripts/migration_backup/`](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup)

### WI-2: `bootstrap_v5.py` — Create Procedures Before Systems

**Priority: Critical**  
**Scope:** Add a Phase 0 that creates all 9 procedures from backup files before any system references them via `typeOf`.

**Files involved:** All 9 `proc_*.json` files in [`scripts/migration_backup/procedures/`](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup/procedures)

### WI-3: Create `bootstrap_iss.py` — ISS Tracker Bootstrap

**Priority: Critical**  
**Scope:** The ISS Tracker is the only system on the server with **no creation script**. Write a bootstrap that creates:

- 1 procedure (ISS SGP4 Tracker)
- 1 system with rich SensorML (ISS Tracker)
- 1 datastream (ISS Position with lat/lon/alt/velocity schema)
- 2 deployment nodes

This script should also create a new SensorML backup file for the ISS Tracker system.

### WI-4: Enrich `bootstrap_localizer.py` — Rich SensorML

**Priority: High**  
**Scope:** The localizer bootstrap currently creates bare GeoJSON. Enhance it to POST `application/sml+json` with keywords, identifiers, classifiers, characteristics, capabilities, contacts, and documents for both the procedure and the system.

This should also produce a backup SML file (e.g., `LOB_Triangulator_sml.json`) for consistency with the migration_backup pattern.

### WI-5: Enrich Support Systems — SET-A, MonSite, Relay

**Priority: High**  
**Scope:** These 3 top-level systems (SET-A, Monitoring Site Node 1, Relay/Repeater 001) have no SensorML backup files and no rich metadata. They need:

- SensorML backup files created (with keywords, identifiers, classifiers, descriptions of their military role)
- `bootstrap_v5.py` updated to POST them as `sml+json`

### WI-6: Enrich Tripod Platform Subsystems

**Priority: Medium**  
**Scope:** All 3 Tripod Platform SML backup files are completely bare — no keywords, identifiers, classifiers, or characteristics. Enrich with:

- Physical specs (material: aluminum, height: 1.5m, weight rating)
- Manufacturer info
- Keywords (tripod, field-deployable, survey-grade)

### WI-7: Restore "Calibrate Orientation" Control Stream

**Priority: Medium**  
**Scope:** The backup contains a 4th control stream (Calibrate Orientation, [`cs_04d0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04d0.json)) that `bootstrap_v4.py` does not create. Decide whether to restore it in v5 or archive the backup file.

### WI-8: Datastream Link Metadata

**Priority: Medium**  
**Scope:** Backup datastreams include `procedure@link`, `deployment@link`, `featureOfInterest@link`, and `observedProperties` that v4 does not set. These improve CSAPI navigability. Add them to v5's datastream creation.

### WI-9: Fix Stale Docstring in bootstrap_v4.py

**Priority: Low**  
**Scope:** The script header says "22 datastreams" but actually creates 25 (Detection Capabilities was added per-node). Fix the count.

### WI-10: Create Backup SML Files for ISS Tracker and Localizer

**Priority: Medium**  
**Scope:** After WI-3 and WI-4 produce enriched SensorML, export the final SML from the server and save as backup files alongside the existing `migration_backup/` files. Ensures future re-bootstraps have a complete backup set.

---

## Execution Order

```
Phase 0 — Bootstrapping prerequisites
  WI-3  Create bootstrap_iss.py (ISS Tracker has no bootstrap at all)
  WI-4  Enrich bootstrap_localizer.py with rich SensorML

Phase 1 — bootstrap_v5.py (replaces v4)
  WI-2  Procedure creation phase
  WI-1  SML+JSON system creation (load backup files)
  WI-5  Support system enrichment (SET-A, MonSite, Relay)
  WI-6  Tripod Platform enrichment
  WI-7  Calibrate Orientation control stream decision
  WI-8  Datastream link metadata
  WI-9  Docstring fix

Phase 2 — Backup completeness
  WI-10 Export and save SML backups for ISS + Localizer
```

---

## File Inventory Summary

### All SensorML Backup Files (42)

| File | GitHub URL |
|---|---|
| `AZ-MA-1_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_sml.json) |
| `AZ-MA-1_Tripod_Platform_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_Tripod_Platform_sml.json) |
| `AZ-MA-1_MICARRAY_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MICARRAY_sml.json) |
| `AZ-MA-1_EDGE_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_EDGE_sml.json) |
| `AZ-MA-1_COMMS_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_COMMS_sml.json) |
| `AZ-MA-1_POWER_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_POWER_sml.json) |
| `AZ-MA-1_ACTUATOR_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_ACTUATOR_sml.json) |
| `AZ-MA-1_MIC1_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC1_sml.json) |
| `AZ-MA-1_MIC2_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC2_sml.json) |
| `AZ-MA-1_MIC3_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC3_sml.json) |
| `AZ-MA-1_MIC4_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC4_sml.json) |
| `AZ-MA-1_MIC5_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC5_sml.json) |
| `AZ-MA-1_MIC6_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC6_sml.json) |
| `AZ-MA-1_MIC7_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-1_MIC7_sml.json) |
| `AZ-MA-2_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_sml.json) |
| `AZ-MA-2_Tripod_Platform_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_Tripod_Platform_sml.json) |
| `AZ-MA-2_MICARRAY_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MICARRAY_sml.json) |
| `AZ-MA-2_EDGE_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_EDGE_sml.json) |
| `AZ-MA-2_COMMS_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_COMMS_sml.json) |
| `AZ-MA-2_POWER_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_POWER_sml.json) |
| `AZ-MA-2_ACTUATOR_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_ACTUATOR_sml.json) |
| `AZ-MA-2_MIC1_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MIC1_sml.json) |
| `AZ-MA-2_MIC2_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MIC2_sml.json) |
| `AZ-MA-2_MIC3_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MIC3_sml.json) |
| `AZ-MA-2_MIC4_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MIC4_sml.json) |
| `AZ-MA-2_MIC5_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MIC5_sml.json) |
| `AZ-MA-2_MIC6_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MIC6_sml.json) |
| `AZ-MA-2_MIC7_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-2_MIC7_sml.json) |
| `AZ-MA-3_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_sml.json) |
| `AZ-MA-3_Tripod_Platform_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_Tripod_Platform_sml.json) |
| `AZ-MA-3_MICARRAY_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MICARRAY_sml.json) |
| `AZ-MA-3_EDGE_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_EDGE_sml.json) |
| `AZ-MA-3_COMMS_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_COMMS_sml.json) |
| `AZ-MA-3_POWER_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_POWER_sml.json) |
| `AZ-MA-3_ACTUATOR_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_ACTUATOR_sml.json) |
| `AZ-MA-3_MIC1_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MIC1_sml.json) |
| `AZ-MA-3_MIC2_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MIC2_sml.json) |
| `AZ-MA-3_MIC3_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MIC3_sml.json) |
| `AZ-MA-3_MIC4_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MIC4_sml.json) |
| `AZ-MA-3_MIC5_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MIC5_sml.json) |
| `AZ-MA-3_MIC6_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MIC6_sml.json) |
| `AZ-MA-3_MIC7_sml.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/AZ-MA-3_MIC7_sml.json) |

### All Procedure Backup Files (9)

| File | GitHub URL |
|---|---|
| `proc_0480.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_0480.json) |
| `proc_048g.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_048g.json) |
| `proc_0490.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_0490.json) |
| `proc_049g.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_049g.json) |
| `proc_04a0.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04a0.json) |
| `proc_04b0.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04b0.json) |
| `proc_04bg.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04bg.json) |
| `proc_04c0.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04c0.json) |
| `proc_04cg.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/procedures/proc_04cg.json) |

### All Datastream Backup Files (14: 7 metadata + 7 schemas)

| File | GitHub URL |
|---|---|
| `ds_07fg2.json` + `schema_07fg2.json` | [ds](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07fg2.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07fg2.json) |
| `ds_07g02.json` + `schema_07g02.json` | [ds](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07g02.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07g02.json) |
| `ds_07gg2.json` + `schema_07gg2.json` | [ds](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07gg2.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07gg2.json) |
| `ds_07h02.json` + `schema_07h02.json` | [ds](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07h02.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07h02.json) |
| `ds_07hg2.json` + `schema_07hg2.json` | [ds](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07hg2.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07hg2.json) |
| `ds_07i02.json` + `schema_07i02.json` | [ds](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07i02.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07i02.json) |
| `ds_07ig2.json` + `schema_07ig2.json` | [ds](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/ds_07ig2.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/datastreams/schema_07ig2.json) |

### All Control Stream Backup Files (8: 4 metadata + 4 schemas)

| File | GitHub URL |
|---|---|
| `cs_04d0.json` + `schema_04d0.json` | [cs](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04d0.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04d0.json) |
| `cs_04dg.json` + `schema_04dg.json` | [cs](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04dg.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04dg.json) |
| `cs_04e0.json` + `schema_04e0.json` | [cs](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04e0.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04e0.json) |
| `cs_04eg.json` + `schema_04eg.json` | [cs](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04eg.json) / [schema](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/schema_04eg.json) |

### Bootstrap & Runtime Scripts

| File | GitHub URL |
|---|---|
| `bootstrap_v4.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py) |
| `bootstrap_v25.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v25.py) |
| `bootstrap_v3.1.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v3.1.py) |
| `bootstrap_localizer.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_localizer.py) |
| `localizer.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/localizer.py) |
| `iss_publisher_v2.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/iss_publisher_v2.py) |
| `iss_publisher.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/iss_publisher.py) |
| `simulator/main.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/simulator/main.py) |
| `simulator/engine.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/simulator/engine.py) |
| `restore_rich_metadata.py` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/restore_rich_metadata.py) |

### ID Map Files

| File | GitHub URL |
|---|---|
| `migration_id_map.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/migration_id_map.json) |
| `new_id_map.json` | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/new_id_map.json) |
