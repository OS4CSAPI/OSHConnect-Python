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

## Restore Matrix (Top-Level Summary)

| Resource Family | # Resources | Truth Source | Target Bootstrap | Verification Method | Owner |
|---|---|---|---|---|---|
| MA Node Systems (AZ-MA-1/2/3) | 3 systems | Backup SML files (`*_sml.json`) | `bootstrap_v5.py` | GET → diff against backup | UAS/LOB Simulator |
| MA Subsystems (13 × 3) | 39 subsystems | Backup SML files (`*_{SUBSYS}_sml.json`) | `bootstrap_v5.py` | GET → diff against backup | UAS/LOB Simulator |
| Support Systems (SET-A, MonSite, Relay) | 3 systems | **To be created** (WI-5) | `bootstrap_v5.py` | GET → check rich fields present | UAS/LOB Simulator |
| Procedures (ODAS demo) | 9 procedures | Backup files (`proc_*.json`) | `bootstrap_v5.py` | GET → diff against backup | UAS/LOB Simulator |
| Datastreams (ODAS demo) | 25 datastreams | bootstrap_v5.py inline + backup schemas | `bootstrap_v5.py` | GET → verify schema + link metadata | UAS/LOB Simulator |
| Control Streams (ODAS demo) | 9 control streams | bootstrap_v5.py inline + backup schemas | `bootstrap_v5.py` | GET → verify schema | UAS/LOB Simulator |
| Deployments (ODAS demo) | 13 deployments | bootstrap_v5.py inline | `bootstrap_v5.py` | GET → verify hierarchy + platform links | UAS/LOB Simulator |
| ISS Tracker | 1 system, 1 proc, 1 DS, 5 deployments | [ISS Enrichment Pack](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/docs/iss-enrichment-pack) templates (need SensorML conversion) + live server for current state | `bootstrap_iss.py` | GET → check rich fields present | ISS Publisher |
| LOB Triangulator | 1 system, 1 proc, 1 DS | **Live server** (until SML template created in WI-4) | `bootstrap_localizer.py` | GET → check rich fields present | LOB Localizer |

---

## Source-of-Truth Hierarchy

All bootstrap scripts must respect the following truth precedence:

1. **Backup SML files** (`scripts/migration_backup/`) — authoritative for all 42 MA system/subsystem definitions and 9 procedures. These files represent the hand-curated, field-verified metadata. Bootstrap scripts load and POST these files directly.
2. **Live server state** — authoritative for ISS Tracker and LOB Triangulator resources *only until* SML template files are created (WI-3, WI-4, WI-10). Once templates exist, they supersede the live state.
3. **Bootstrap scripts** — authoritative creation path. All resources must be reproducible from these scripts alone, with no manual API calls or one-off fixup scripts required.
4. **`migration_id_map.json` / `new_id_map.json`** — reference only. Server IDs are ephemeral; bootstrap scripts must discover or create by UID, never by hardcoded ID.

---

## Idempotency Requirement

All bootstrap scripts (v5, ISS, localizer) must be **idempotent** — safe to run repeatedly against either a clean or pre-populated server:

- **Discover by UID first** (GET with `uid` filter). If the resource exists, update it (PUT); if not, create it (POST).
- **Never duplicate** — running a bootstrap twice must not produce two copies of any resource.
- **Converge to truth** — if a resource exists but is stale, the bootstrap overwrites it with the canonical SML from the truth source.
- **Log clearly** — emit `CREATED <name>` or `UPDATED <name> (already existed)` for every resource touched.

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
**Enrichment Pack:** [`docs/iss-enrichment-pack/`](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/docs/iss-enrichment-pack) — target resource model, metadata profiles, deployment hierarchy, conceptual JSON templates (require SensorML conversion)

### 2.1 Current Server Resources (legacy — to be retired after WI-3)

| Resource Type | Name | UID | Server ID | SensorML Backup | Rich Metadata? |
|---|---|---|---|---|---|
| Procedure | ISS SGP4 Tracker | *(unknown — created ad-hoc)* | `045g` | **None** | **No** — bare |
| System | ISS Tracker (SGP4 Position Feed) | `urn:os4csapi:system:iss-tracker:v1` | `04ng` | **None** | **No** — bare (label + description only) |
| DataStream | ISS Position (SGP4) | *(server-assigned)* | `04fg` | **None** | Schema: `lat_deg`, `lon_deg`, `alt_km`, `velocity_km_s` |
| Deployment (root) | *(unknown name)* | *(unknown)* | `048g` | **None** | — |
| Deployment (leaf) | *(unknown name)* | *(unknown)* | `0490` | **None** | — |

### 2.2 Target Resource Model (from ISS Enrichment Pack)

The enrichment pack proposes a richer resource family. **Phase 1** implements the position-tracking resources; orbit-track resources are deferred until publisher code is written.

**Phase 1 (position tracking — implement in WI-3):**

| Resource Type | Name | Target UID | Source |
|---|---|---|---|
| Procedure | SGP4 Propagation v1 | `urn:os4csapi:procedure:sgp4-propagation:v1` | Pack template (needs SensorML conversion) |
| System | ISS Position Publisher | `urn:os4csapi:system:iss-position-publisher:v1` | Pack template (needs SensorML conversion) |
| DataStream | ISS Position (SGP4) | `urn:os4csapi:datastream:iss:position:wgs84:v1` | Existing 4-field schema + `velocity_km_s` |
| Deployment (root) | Orbital Tracking Demo | `urn:os4csapi:deployment:orbital-tracking-demo:v1` | Pack template |
| Deployment (L1) | LEO Objects | `urn:os4csapi:deployment:leo-objects:v1` | Pack template |
| Deployment (L2) | ISS Tracking Role | `urn:os4csapi:deployment:iss-tracking-role:v1` | Pack template |
| Deployment (leaf) | ISS Position Feed | `urn:os4csapi:deployment:iss-position-feed:v1` | Pack template |

**Deferred (orbit-track — no publisher code exists yet):**

| Resource Type | Name | Target UID |
|---|---|---|
| Procedure | Orbit Track Generation v1 | `urn:os4csapi:procedure:orbit-track-generation:v1` |
| System | ISS Orbit Track Publisher | `urn:os4csapi:system:iss-orbittrack-publisher:v1` |
| DataStream | ISS Orbit Ground Track | `urn:os4csapi:datastream:iss:orbit-ground-track:v1` |
| Deployment (leaf) | ISS Orbit Track Feed | `urn:os4csapi:deployment:iss-orbittrack-feed:v1` |

### 2.3 Metadata Enrichment Profile

The ISS Position Publisher system should include (sourced from pack + our audit):

- **keywords**: ISS, Zarya, NORAD 25544, satellite, SGP4, orbital propagation, space station, LEO
- **identifiers**: ShortName (ISS Position Publisher), NORAD ID (25544), COSPAR ID (1998-067A)
- **classifiers**: Platform Type (Space Station), Orbit Class (LEO), System Role (Position Publisher)
- **characteristics**: Orbital period (~92.7 min), inclination (51.6°), altitude range (408–420 km)
- **capabilities**: Position update rate (30s), propagation model (SGP4), TLE source (CelesTrak)
- **contacts**: NASA, CelesTrak, OS4CSAPI project
- **documents**: NASA ISS Overview, CelesTrak GP Data Formats, satellite.js library, ISS Wikipedia page

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

**Acceptance Criteria:**
- [ ] All 6 top-level systems created via `application/sml+json` POST (not `geo+json`)
- [ ] All 39 subsystems created via `application/sml+json` POST
- [ ] GET each system by UID returns SensorML with keywords, identifiers, classifiers, etc. matching backup files
- [ ] Script is idempotent: re-running against an existing server updates rather than duplicates

### WI-2: `bootstrap_v5.py` — Create Procedures Before Systems

**Priority: Critical**  
**Scope:** Add a Phase 0 that creates all 9 procedures from backup files before any system references them via `typeOf`.

**Files involved:** All 9 `proc_*.json` files in [`scripts/migration_backup/procedures/`](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/scripts/migration_backup/procedures)

**Acceptance Criteria:**
- [ ] All 9 procedures exist on server before any system `typeOf` references them
- [ ] GET each procedure by UID returns content matching backup JSON
- [ ] Bootstrap emits clear log for each procedure created/updated

### WI-3: Create `bootstrap_iss.py` — ISS Tracker Bootstrap

**Priority: Critical**  
**Scope:** The ISS Tracker is the only system on the server with **no creation script**. Write a bootstrap that creates:

- 1 procedure (SGP4 Propagation — `urn:os4csapi:procedure:sgp4-propagation:v1`)
- 1 system with rich SensorML (ISS Position Publisher — `urn:os4csapi:system:iss-position-publisher:v1`)
- 1 datastream (ISS Position with lat/lon/alt/velocity schema)
- 5 deployment nodes (Orbital Tracking Demo → LEO Objects → ISS Tracking Role → 2 feed leaves)

**Design Reference:** The [ISS Implementation Ready Pack v2](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/docs/iss-enrichment-pack) provides the target resource model, metadata enrichment profile, deployment hierarchy, and conceptual JSON templates. See detailed audit notes below.

> **ISS Pack Audit Notes (template conversion required):**
> - **System/Procedure JSONs are NOT valid SensorML** — they use flat `type`/`properties` structure instead of proper `application/sml+json` format (`PhysicalSystem`, `uniqueIdentifier`, `identificationList`, SWE inputs/outputs). Must be converted to SensorML JSON before POST.
> - **Pack proposes 2 systems + 2 procedures + 2 datastreams (position + orbit-track)**. The orbit-track resources are aspirational — no publisher code exists yet. **Phase 1 scope: position resources only.** Orbit-track resources deferred to a future phase when orbit-track publisher is implemented.
> - **Datastream schema expansion**: Pack proposes 10 fields (adds `noradId`, `assetName`, `sourceEpoch`, `sourceAgeSec`, `posErrorM`, `method`). Current publisher emits 4 fields (`timestamp`, `lat_deg`, `lon_deg`, `alt_km`). Decision: either expand the publisher or use existing 4-field schema + `velocity_km_s`. Recommend keeping `velocity_km_s` (already in existing DS) and deferring extra fields to a later publisher update.
> - **Deployment hierarchy**: Pack proposes 5-node tree (root → LEO Objects → ISS Tracking Role → 2 feed leaves). This replaces the current flat 2-node tree. The hierarchy design is sound and should be adopted.
> - **UIDs**: All follow `urn:os4csapi:*` convention — adopt as-is.
> - **Placeholders**: 6 `REPLACE_WITH_*` values in templates need to be filled (image URLs, system links).
> - **Existing resources** (`04ng`, `045g`, `04fg`, `048g`, `0490`) must be retired after new resources are proven working.

This script should also create a new SensorML backup file for the ISS Tracker system.

**Acceptance Criteria:**
- [ ] `bootstrap_iss.py` exists and runs end-to-end on a clean server
- [ ] Creates procedure, system, datastream, and deployment hierarchy
- [ ] System SensorML includes keywords, identifiers, classifiers, characteristics, capabilities, contacts, documents
- [ ] `iss_publisher_v2.py` discovers all resources by UID after a fresh bootstrap (no manual ID fixups)
- [ ] SML template file saved to `scripts/migration_backup/` (or equivalent ISS directory)
- [ ] Existing legacy resources (`04ng`, `045g`, `04fg`, `048g`, `0490`) retired after validation

### WI-4: Enrich `bootstrap_localizer.py` — Rich SensorML

**Priority: High**  
**Scope:** The localizer bootstrap currently creates bare GeoJSON. Enhance it to POST `application/sml+json` with keywords, identifiers, classifiers, characteristics, capabilities, contacts, and documents for both the procedure and the system.

This should also produce a backup SML file (e.g., `LOB_Triangulator_sml.json`) for consistency with the migration_backup pattern.

**Acceptance Criteria:**
- [ ] `bootstrap_localizer.py` creates system + procedure with `application/sml+json`
- [ ] GET system by UID returns rich SensorML (keywords, classifiers, characteristics, capabilities)
- [ ] `localizer.py` runtime discovers all resources by UID after fresh bootstrap
- [ ] SML template file saved alongside other backups

### WI-5: Enrich Support Systems — SET-A, MonSite, Relay

**Priority: High**  
**Scope:** These 3 top-level systems (SET-A, Monitoring Site Node 1, Relay/Repeater 001) have no SensorML backup files and no rich metadata. They need:

- SensorML backup files created (with keywords, identifiers, classifiers, descriptions of their military role)
- `bootstrap_v5.py` updated to POST them as `sml+json`

**Acceptance Criteria:**
- [ ] Backup SML files exist for SET-A, MonSite, and Relay
- [ ] Each file contains at minimum: keywords, identifiers, classifiers, description of operational role
- [ ] `bootstrap_v5.py` POSTs these as `sml+json`

### WI-6: Enrich Tripod Platform Subsystems

**Priority: Medium**  
**Scope:** All 3 Tripod Platform SML backup files are completely bare — no keywords, identifiers, classifiers, or characteristics. Enrich with:

- Physical specs (material: aluminum, height: 1.5m, weight rating)
- Manufacturer info
- Keywords (tripod, field-deployable, survey-grade)

**Acceptance Criteria:**
- [ ] All 3 Tripod Platform backup files contain physical specs, manufacturer info, and keywords
- [ ] GET by UID returns non-bare SensorML after bootstrap

### WI-7: Restore "Calibrate Orientation" Control Stream

**Priority: Medium**  
**Scope:** The backup contains a 4th control stream (Calibrate Orientation, [`cs_04d0.json`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/migration_backup/controlstreams/cs_04d0.json)) that `bootstrap_v4.py` does not create. Decide whether to restore it in v5 or archive the backup file.

**Acceptance Criteria:**
- [ ] Decision documented (restore or archive) with rationale
- [ ] If restored: control stream exists on server after v5 bootstrap
- [ ] If archived: backup file moved to `migration_backup/archived/` with README note

### WI-8: Datastream Link Metadata

**Priority: Medium**  
**Scope:** Backup datastreams include `procedure@link`, `deployment@link`, `featureOfInterest@link`, and `observedProperties` that v4 does not set. These improve CSAPI navigability. Add them to v5's datastream creation.

**Acceptance Criteria:**
- [ ] Datastreams created by v5 include `procedure@link`, `deployment@link`, and `observedProperties` where applicable
- [ ] GET datastream returns link fields matching backup metadata

### WI-9: Fix Stale Docstring in bootstrap_v4.py

**Priority: Low**  
**Scope:** The script header says "22 datastreams" but actually creates 25 (Detection Capabilities was added per-node). Fix the count.

**Acceptance Criteria:**
- [ ] Docstring count matches actual resource creation count

### WI-10: Create Backup SML Files for ISS Tracker and Localizer

**Priority: Medium**  
**Scope:** After WI-3 and WI-4 produce enriched SensorML, export the final SML from the server and save as backup files alongside the existing `migration_backup/` files. Ensures future re-bootstraps have a complete backup set.

**Acceptance Criteria:**
- [ ] ISS Tracker SML template file exists in backup directory
- [ ] LOB Triangulator SML template file exists in backup directory
- [ ] Re-running the corresponding bootstrap from these templates reproduces the same server state

---

## Known Intentional Gaps

The following items are **deliberately excluded** from the bootstrap restoration and should not be treated as bugs or missing work:

| Gap | Reason | Status |
|---|---|---|
| Tripod Platform SML is bare (no rich fields) | Physical platform with no sensors or processing — metadata would be speculative until field measurements are taken | **Intentional** — will be enriched if/when field data is available (see WI-6 for aspirational enrichment) |
| "Calibrate Orientation" control stream not in v4 | Dropped during v4 rewrite. Backup file exists (`cs_04d0.json`). Restore decision deferred to WI-7 | **Deferred** — pending WI-7 decision |
| Detection Capabilities datastream has no backup | Added after the migration that produced the backup files | **Expected** — schema defined inline in bootstrap script |
| ISS Tracker has no SML backup file | System was created manually via ad-hoc API calls before backup tooling existed | **To be resolved** by WI-3 + WI-10 |
| LOB Triangulator has no SML backup file | Bare bootstrap existed but never produced rich SML | **To be resolved** by WI-4 + WI-10 |
| SET-A, MonSite, Relay have no SML backup files | Support/organizational systems with no physical sensor metadata to back up at time of migration | **To be resolved** by WI-5 |

---

## Execution Order

```
Phase 0 — Template creation & standalone bootstraps
  WI-10 Create SML template files for ISS Tracker and Localizer (captures live server state as truth)
  WI-3  Create bootstrap_iss.py (ISS Tracker has no bootstrap at all — uses WI-10 template)
  WI-4  Enrich bootstrap_localizer.py with rich SensorML (uses WI-10 template)

Phase 1 — bootstrap_v5.py (replaces v4)
  WI-2  Procedure creation phase
  WI-1  SML+JSON system creation (load backup files)
  WI-5  Support system enrichment (SET-A, MonSite, Relay)
  WI-6  Tripod Platform enrichment
  WI-7  Calibrate Orientation control stream decision
  WI-8  Datastream link metadata
  WI-9  Docstring fix

Phase 2 — Verification
  Run post-bootstrap verification (see Verification & Smoke Tests below)
  Confirm all 3 runtime services start and publish successfully
```

---

## Verification & Smoke Tests

### Post-Bootstrap Verifier Script

A `verify_bootstrap.py` script should be created alongside each bootstrap script. It performs read-back verification:

1. **For every system/subsystem:** GET by UID, confirm HTTP 200, check that `keywords`, `identifiers`, and `classifiers` arrays are non-empty (for resources that should have rich SML).
2. **For every procedure:** GET by UID, confirm HTTP 200, check content matches backup file (byte-level or key-field comparison).
3. **For every datastream:** GET by system, confirm expected count, verify schema field names match expected set.
4. **For every deployment:** GET root, walk children, confirm hierarchy depth and platform links.
5. **Output:** Summary table of PASS/FAIL per resource, exit code 0 only if all pass.

### Runtime Smoke Tests

After bootstrapping, each runtime service should be started and verified:

| Service | Smoke Test | Pass Criteria |
|---|---|---|
| UAS Simulator (`simulator/main.py`) | Start → wait 30s → GET latest observation from any MA datastream | Non-empty observation with `resultTime` within last 60s |
| ISS Publisher (`iss_publisher_v2.py`) | Start → wait 30s → GET latest ISS Position observation | Non-empty observation with valid lat/lon/alt |
| LOB Localizer (`localizer.py`) | Start w/ simulator running → wait 60s → GET latest UAS Location Estimate | Non-empty observation with trackId and lat/lon |

### Diff-Against-Backup Test

For the 42 MA system/subsystem SML files and 9 procedure files, an automated test should:
1. GET the resource SML from the server (by UID)
2. Load the corresponding backup file
3. Compare key fields (keywords, identifiers, classifiers, characteristics, capabilities, contacts, documents)
4. Report any drift between server state and backup truth

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

### ISS Enrichment Pack (13 JSON templates + 12 planning docs)

| File | Type | GitHub URL |
|---|---|---|
| `system_iss_position_publisher.json` | System template (needs SML conversion) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/system_iss_position_publisher.json) |
| `system_iss_orbittrack_publisher.json` | System template (deferred — needs SML conversion) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/system_iss_orbittrack_publisher.json) |
| `procedure_sgp4_propagation_v1.json` | Procedure template (needs SML conversion) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/procedure_sgp4_propagation_v1.json) |
| `procedure_orbit_track_generation_v1.json` | Procedure template (deferred — needs SML conversion) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/procedure_orbit_track_generation_v1.json) |
| `datastream_satPositionWGS84.json` | Datastream schema (10-field — needs reconciliation with current 4-field) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/datastream_satPositionWGS84.json) |
| `datastream_orbitGroundTrack.json` | Datastream schema (deferred — no publisher) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/datastream_orbitGroundTrack.json) |
| `deployment_root_orbital_tracking_demo.json` | Deployment root | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/deployment_root_orbital_tracking_demo.json) |
| `deployment_leo_objects.json` | Deployment L1 | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/deployment_leo_objects.json) |
| `deployment_iss_tracking_role.json` | Deployment L2 | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/deployment_iss_tracking_role.json) |
| `deployment_iss_position_feed_leaf.json` | Deployment leaf (has placeholder) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/deployment_iss_position_feed_leaf.json) |
| `deployment_iss_orbit_track_feed_leaf.json` | Deployment leaf (deferred) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/deployment_iss_orbit_track_feed_leaf.json) |
| `observation_position_example.json` | Example observation | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/observation_position_example.json) |
| `observation_orbittrack_example.json` | Example observation (deferred) | [link](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/iss-enrichment-pack/json-templates/observation_orbittrack_example.json) |
| Planning docs (12 files) | Markdown/CSV | [directory](https://github.com/OS4CSAPI/ogc-csapi-explorer/tree/main/docs/iss-enrichment-pack) |
