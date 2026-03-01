# AZ-MA-1 Migration Feasibility Report: DO → Oracle OSH

> **Date:** 2026-03-01  
> **Author:** CSAPI Explorer Research Agent  
> **Status:** Research Complete — Migration Approved  
> **Source Server:** DigitalOcean OSH (`http://45.55.99.236:8080/sensorhub/api`)  
> **Target Server:** Oracle OSH (`https://os4csapi-osh.duckdns.org/sensorhub/api`)

---

## 1. Executive Summary

**Verdict: YES, fully possible.** Every artifact comprising the ODAS Mic Array Node AZ-MA-1 system can be recreated on the Oracle OSH server via standard OGC Connected Systems API POST/PUT operations. The migration involves ~47 API calls across 7 deterministic phases.

### Key Structural Changes

| Change | From (DO) | To (Oracle) |
|---|---|---|
| **Parent relationship** | Subsystem of AZ-MA-NET (`04n0`) | **Top-level system** (no parent) |
| **Deployment association** | Own deployment clone hierarchy (6 deployments) | **Deployed system** of Sensor String Alpha (`0430`) |
| **Deployment clones** | 6 (Deployment AZ-MA-1 + 5 sub-deployments) | **None** — removed entirely |
| **Everything else** | Full SensorML, subsystems, datastreams, controls, obs | **Preserved as-is** |

---

## 2. Source Inventory (DO Server)

### 2.1 Top-Level System: AZ-MA-1

| Field | Value |
|---|---|
| **Server ID** | `04ng` |
| **UID** | `urn:os4csapi:system:odas:az-ma-1` |
| **featureType** | `sosa:System` |
| **Name** | ODAS Mic Array Node AZ-MA-1 |
| **Geometry** | Point `[-110.272897, 31.663006]` |
| **Parent** | `04n0` (AZ-MA-NET) — **TO BE REMOVED** |
| **SensorML richness** | keywords, identifiers (ShortName, LongName), classifiers (SensorType, IntendedApplication), characteristics (ODAS DSP Pipeline with 5 fields), capabilities (4 acoustic capabilities), contacts (IntRoLab), documents (6 references including ODAS GitHub, papers, wiki, demo video) |
| **validTime** | `2026-01-01T00:00:00Z / ..` |

**Full description:**
> ODAS 7-microphone circular PDM MEMS array node deployed at Ft. Huachuca, AZ. Position 1 (north). Performs real-time sound source localization (SSL), sound source tracking (SST), and line-of-bearing (LOB) estimation using the ODAS (Open embeddeD Audition System) DSP pipeline. Subsystems include tripod platform, mic array, edge processor, comms module, power supply, and pan-tilt actuator.

### 2.2 Subsystems (13 total)

All subsystems share the same Point geometry `[-110.272897, 31.663006]` and `validTime: 2026-01-01T00:00:00Z / ..`.

| DO ID | Name | featureType | UID |
|---|---|---|---|
| `04pg` | MICARRAY | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic-array` |
| `04q0` | EDGE | `sosa:Platform` | `urn:os4csapi:system:odas:az-ma-1:edge` |
| `04qg` | COMMS | `sosa:Platform` | `urn:os4csapi:system:odas:az-ma-1:comms` |
| `04r0` | POWER | `sosa:Platform` | `urn:os4csapi:system:odas:az-ma-1:power` |
| `04rg` | ACTUATOR | `sosa:Actuator` | `urn:os4csapi:system:odas:az-ma-1:actuator` |
| `04s0` | MIC1 | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic1` |
| `04sg` | MIC2 | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic2` |
| `04t0` | MIC3 | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic3` |
| `04tg` | MIC4 | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic4` |
| `04u0` | MIC5 | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic5` |
| `04ug` | MIC6 | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic6` |
| `04v0` | MIC7 | `sosa:Sensor` | `urn:os4csapi:system:odas:az-ma-1:mic7` |
| `05cg` | Tripod Platform | `sosa:Platform` | `urn:os4csapi:system:odas:az-ma-1:tripod-platform` |

**Note:** None of the subsystems have their own datastreams. All datastreams are on the parent system (`04ng`), and all control streams are on the ACTUATOR subsystem (`04rg`).

### 2.3 Datastreams (7 total, all on parent system `04ng`)

| DO ID | Name | Observations | Schema Summary |
|---|---|---|---|
| `07fg2` | SSL Potential Sources | 0 | DataRecord → DataArray of `{x, y, z, E}` direction cosines |
| `07g02` | SST Tracked Sources | 0 | DataRecord → DataArray of `{id, tag, x, y, z, activity}` |
| `07gg2` | LOB | 0 | `{timestamp, trackId, bearingTrue, bearingStdDev, sensorLat, sensorLon}` |
| `07h02` | Track Updates | **3** | `{timestamp, odasTimeStamp, id, tag, x, y, z, activity, bearingTrue, elevation, bearingStdDev, classLabel, classConfidence}` |
| `07hg2` | Classification Probabilities | **3** | `{timestamp, trackId, p_uas, p_vehicle, p_footsteps, p_impulsive, p_unknown}` |
| `07i02` | Health | **3** | `{timestamp, cpuLoad, memUsedMB, tempC, latencyMs, uptimeS}` |
| `07ig2` | Scene Summary | **3** | `{timestamp, odasTimeStamp, trackCount, activityLevel}` |

**Important:** No datastreams reference procedures (`proc=` is empty on all 7). This simplifies migration — no procedure-to-datastream linking needed.

**Observation time range (where present):** `2026-02-27T17:41:21Z` to `2026-02-27T18:16:16Z`

#### Sample Observations

**Track Update:** `bearingTrue=123.89, classLabel="footsteps", classConfidence=0.85`  
**Classification:** `p_footsteps=0.816, p_unknown=0.122`  
**Health:** `cpuLoad=0.424, memUsedMB=883.5, tempC=49.92, latencyMs=38.12`  
**Scene Summary:** `trackCount=3, activityLevel=0.65`

### 2.4 Control Streams (4 total, all on ACTUATOR subsystem `04rg`)

| DO ID | Name | inputName | Controlled Properties |
|---|---|---|---|
| `04d0` | Calibrate Orientation | `calibration` | headingTrueDeg (0–360°), offsetCalDeg (±180°), note |
| `04dg` | ODAS Control | `odasControl` | module (sne/ssl/sst/sss/classify/general), parameter, value, applyMode (immediate/nextFrame/nextRestart) |
| `04e0` | Request Snapshot | `snapshot` | trackId, durationMs (10–60000), format (wav/flac/json) |
| `04eg` | Start Stop | `startStop` | action (start/stop/restart), modules CSV |

### 2.5 Procedures (9 total)

#### Generic ODAS Procedures (shared across MA-1/2/3)

| DO ID | UID | Name | Description |
|---|---|---|---|
| `0480` | `urn:x-odas:procedure:pdm-mems-audio-capture` | PDM MEMS Microphone Audio Capture | PDM microphone sampling. XMOS xCORE decimation: PDM→PCM at 16 kHz. Frame 256, hop 128, USB Audio Class 1.0. |
| `048g` | `urn:x-odas:procedure:srp-phat-beamforming` | SRP-PHAT Steered Response Power Beamforming | SSL via GCC-PHAT cross-correlation, hemisphere scan, DOA estimation. Outputs up to 4 potential sources as `(x,y,z,E)` unit-sphere vectors. |
| `0490` | `urn:x-odas:procedure:particle-filter-tracking` | Particle Filter Sound Source Tracking | SST via sequential Monte Carlo. Three motion states (stationary 10%, constant velocity 40%, acceleration 50%). Bayesian hypothesis testing for observation association. H=500 particles. |
| `049g` | `urn:x-odas:procedure:ray-to-ray-triangulation` | Multi-Array Ray-to-Ray 3D Triangulation | 3D position from distributed DOAs (IROS 2017, Lauzon et al.). Ray-to-Ray shortest distance (Schneider & Eberly 2002). Min 2 arrays, 3+ recommended. NTP sync required. |
| `04a0` | `urn:x-odas:procedure:odas-config-actuation` | ODAS Runtime Configuration Actuation | Runtime parameter modification. Atomic and batch updates for E_T, T_new, F_new, T_remove, H, mic gain, frame rate. |

#### AZ-MA-1-Specific Procedures

| DO ID | UID | Name | Description |
|---|---|---|---|
| `04b0` | `urn:os4csapi:procedure:odas:az-ma-1:calibration:v1` | Calibration Proc (AZ-MA-1) | *(empty)* |
| `04bg` | `urn:os4csapi:procedure:odas:az-ma-1:health-monitor:v1` | Health Proc (AZ-MA-1) | *(empty)* |
| `04c0` | `urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1` | ODAS Processing Chain (AZ-MA-1) | *(empty)* |
| `04cg` | `urn:os4csapi:procedure:odas:az-ma-1:frame-transform:v1` | Transform (AZ-MA-1) | *(empty)* |

### 2.6 Sampling Features

None on AZ-MA-1 or any subsystems.

### 2.7 Deployment Clones (NOT Migrating)

These exist on the DO server and are **deliberately excluded** from migration:

| DO ID | Name | Parent |
|---|---|---|
| `04dg` | Deployment AZ-MA-1 | AOI `04cg` |
| `04f0` | Deployment AZ-MA-1-MICARRAY | `04dg` |
| `04fg` | Deployment AZ-MA-1-EDGE | `04dg` |
| `04g0` | Deployment AZ-MA-1-COMMS | `04dg` |
| `04gg` | Deployment AZ-MA-1-POWER | `04dg` |
| `04h0` | Deployment AZ-MA-1-ACTUATOR | `04dg` |

---

## 3. Target State (Oracle Server)

### 3.1 Current Oracle Inventory (pre-migration)

**Systems (3):**

| ID | Name | featureType | Geometry |
|---|---|---|---|
| `040g` | Sensor Employment Team (SET-A) | `sosa:Platform` | Point `[-110.2524769, 31.6380757]` |
| `0410` | Monitoring Site Node 1 | `sosa:Platform` | Point `[-110.2525675, 31.6383956]` |
| `041g` | Relay / Repeater 001 | `sosa:Platform` | Point `[-110.2554653, 31.6429133]` |

**Deployments (6):**

```
ICO (040g) ── Point
  └─ RSO (0410) ── Point
       └─ SSO (041g) ── LineString
            └─ SNET (0420) ── LineString
                 ├─ Field (042g) ── null (derived)
                 └─ String Alpha (0430) ── null (derived)
```

**Procedures:** None (0)

### 3.2 Post-Migration State

After migration, Oracle will have:
- **4 systems** (SET-A, MonSite, Relay, **AZ-MA-1** as top-level)
- **13 subsystems** under AZ-MA-1
- **6 deployments** (unchanged) — with String Alpha now linking to AZ-MA-1
- **9 procedures** (first procedures on Oracle)
- **7 datastreams** with full SWE Common schemas
- **4 control streams** on ACTUATOR subsystem
- **12 observations** across 4 datastreams

### 3.3 System-to-Deployment Link

The DO server uses `platform@link` in deployment properties to connect a deployment to a system. We will PUT an updated Sensor String Alpha (`0430`) deployment adding:

```json
{
  "platform@link": {
    "href": "https://os4csapi-osh.duckdns.org/sensorhub/api/systems/{new-ma1-id}",
    "rel": "platform",
    "title": "AZ-MA-1"
  }
}
```

This is the same pattern successfully used on the DO server (verified: Deployment AZ-MA-1 `04dg` links to system `04ng` via `platform@link`).

---

## 4. Migration Plan — 7 Phases

| Phase | Action | API Method | Endpoint | Count |
|---|---|---|---|---|
| **1** | Create procedures | `POST` × 9 | `/procedures` | 9 |
| **2** | Create AZ-MA-1 (top-level) | `POST` × 1 | `/systems` | 1 |
| **3** | Create subsystems | `POST` × 13 | `/systems/{ma1}/subsystems` | 13 |
| **4** | Create datastreams | `POST` × 7 | `/systems/{ma1}/datastreams` | 7 |
| **5** | Create control streams | `POST` × 4 | `/systems/{actuator}/controlstreams` | 4 |
| **6** | Create observations | `POST` × 12 | `/datastreams/{ds}/observations` | 12 |
| **7** | Link to String Alpha | `GET+PUT` × 1 | `/deployments/0430` | 1 |

**Total: ~47 API calls**

### Phase Details

#### Phase 1: Procedures (9 POSTs)
Create all 9 procedures at `/procedures`. The 5 generic ODAS procedures have rich multi-paragraph descriptions. The 4 AZ-MA-1-specific ones have names/UIDs only (empty descriptions — same as source). Procedures are server-global and not system-scoped.

#### Phase 2: Top-Level System (1 POST)
POST AZ-MA-1 SensorML to `/systems` (NOT `/systems/{parent}/subsystems`). This makes it a root-level system with no parent. Full SensorML payload from backup file `AZ-MA-1_sml.json`.

#### Phase 3: Subsystems (13 POSTs)
POST each subsystem's SensorML to `/systems/{ma1-id}/subsystems`. Full SensorML payloads from 13 backup files in `scripts/migration_backup/`.

#### Phase 4: Datastreams (7 POSTs)
POST each datastream to `/systems/{ma1-id}/datastreams`. Each needs: `name`, `outputName`, `observedProperties`, `validTime`, and `resultSchema` (full SWE Common DataRecord definitions captured).

#### Phase 5: Control Streams (4 POSTs)
POST each control stream to `/systems/{actuator-id}/controlstreams`. Each needs: `name`, `inputName`, `controlledProperties`, `validTime`, and `parametersSchema`.

#### Phase 6: Observations (12 POSTs)
POST observations to the 4 datastreams that have data (Track Updates, Classification, Health, Scene Summary × 3 each). Each observation includes `phenomenonTime`, `resultTime`, and the full result record.

#### Phase 7: Deployment Link (1 GET+PUT)
GET Sensor String Alpha (`0430`) from Oracle, add `platform@link` pointing to the newly-created AZ-MA-1 system ID, strip `links`, PUT back. Same proven pattern used for geometry updates.

---

## 5. Existing Backups

SensorML backup files already exist in the CSAPI Explorer repository at `scripts/migration_backup/`:

```
AZ-MA-1_sml.json              (top-level system)
AZ-MA-1_ACTUATOR_sml.json
AZ-MA-1_COMMS_sml.json
AZ-MA-1_EDGE_sml.json
AZ-MA-1_MIC1_sml.json
AZ-MA-1_MIC2_sml.json
AZ-MA-1_MIC3_sml.json
AZ-MA-1_MIC4_sml.json
AZ-MA-1_MIC5_sml.json
AZ-MA-1_MIC6_sml.json
AZ-MA-1_MIC7_sml.json
AZ-MA-1_MICARRAY_sml.json
AZ-MA-1_POWER_sml.json
AZ-MA-1_Tripod_Platform_sml.json
```

These contain the full SensorML payloads ready for POST (type `PhysicalSystem`).

---

## 6. Full Datastream Schema Reference

### 6.1 SSL Potential Sources

```json
{
  "type": "DataRecord",
  "name": "az_ma_1_ssl_potential_sources",
  "definition": "https://os4csapi.org/def/odas/ssl/potentialSourcesRecordOSH",
  "label": "SSL potential sources",
  "fields": [
    { "type": "Time", "name": "timestamp", "uom": { "code": "s" } },
    { "type": "Count", "name": "odasTimeStamp" },
    {
      "type": "DataArray", "name": "src",
      "elementType": {
        "fields": [
          { "type": "Quantity", "name": "x", "uom": { "code": "1" }, "constraint": [-1.0, 1.0] },
          { "type": "Quantity", "name": "y", "uom": { "code": "1" }, "constraint": [-1.0, 1.0] },
          { "type": "Quantity", "name": "z", "uom": { "code": "1" }, "constraint": [-1.0, 1.0] },
          { "type": "Quantity", "name": "E", "uom": { "code": "1" } }
        ]
      }
    }
  ]
}
```

### 6.2 SST Tracked Sources

```json
{
  "type": "DataRecord",
  "name": "az_ma_1_sst_tracked_sources",
  "fields": [
    { "type": "Time", "name": "timestamp" },
    { "type": "Count", "name": "odasTimeStamp" },
    {
      "type": "DataArray", "name": "src",
      "elementType": {
        "fields": [
          { "type": "Count", "name": "id" },
          { "type": "Text", "name": "tag", "constraint": ["dynamic", "static", ""] },
          { "type": "Quantity", "name": "x" }, { "type": "Quantity", "name": "y" }, { "type": "Quantity", "name": "z" },
          { "type": "Quantity", "name": "activity" }
        ]
      }
    }
  ]
}
```

### 6.3 LOB (Line of Bearing)

```json
{
  "type": "DataRecord",
  "name": "az_ma_1_lob",
  "fields": [
    { "type": "Time", "name": "timestamp" },
    { "type": "Count", "name": "trackId" },
    { "type": "Quantity", "name": "bearingTrue", "uom": "deg", "constraint": [0.0, 360.0] },
    { "type": "Quantity", "name": "bearingStdDev", "uom": "deg" },
    { "type": "Quantity", "name": "sensorLat", "uom": "deg", "constraint": [-90.0, 90.0] },
    { "type": "Quantity", "name": "sensorLon", "uom": "deg", "constraint": [-180.0, 180.0] }
  ]
}
```

### 6.4 Track Updates

```json
{
  "type": "DataRecord",
  "name": "az_ma_1_track_updates",
  "fields": [
    { "type": "Time", "name": "timestamp" },
    { "type": "Count", "name": "odasTimeStamp" },
    { "type": "Count", "name": "id" },
    { "type": "Text", "name": "tag" },
    { "type": "Quantity", "name": "x" }, { "type": "Quantity", "name": "y" }, { "type": "Quantity", "name": "z" },
    { "type": "Quantity", "name": "activity" },
    { "type": "Quantity", "name": "bearingTrue", "uom": "deg" },
    { "type": "Quantity", "name": "elevation", "uom": "deg" },
    { "type": "Quantity", "name": "bearingStdDev", "uom": "deg" },
    { "type": "Category", "name": "classLabel", "constraint": ["uas", "vehicle", "footsteps", "impulsive", "unknown"] },
    { "type": "Quantity", "name": "classConfidence", "constraint": [0.0, 1.0] }
  ]
}
```

### 6.5 Classification Probabilities

```json
{
  "type": "DataRecord",
  "name": "az_ma_1_classification_probabilities",
  "fields": [
    { "type": "Time", "name": "timestamp" },
    { "type": "Count", "name": "trackId" },
    { "type": "Quantity", "name": "p_uas", "constraint": [0.0, 1.0] },
    { "type": "Quantity", "name": "p_vehicle", "constraint": [0.0, 1.0] },
    { "type": "Quantity", "name": "p_footsteps", "constraint": [0.0, 1.0] },
    { "type": "Quantity", "name": "p_impulsive", "constraint": [0.0, 1.0] },
    { "type": "Quantity", "name": "p_unknown", "constraint": [0.0, 1.0] }
  ]
}
```

### 6.6 Health

```json
{
  "type": "DataRecord",
  "name": "az_ma_1_health",
  "fields": [
    { "type": "Time", "name": "timestamp" },
    { "type": "Quantity", "name": "cpuLoad", "uom": "1", "constraint": [0.0, 1.0] },
    { "type": "Quantity", "name": "memUsedMB", "uom": "MB" },
    { "type": "Quantity", "name": "tempC", "uom": "Cel" },
    { "type": "Quantity", "name": "latencyMs", "uom": "ms" },
    { "type": "Quantity", "name": "uptimeS", "uom": "s" }
  ]
}
```

### 6.7 Scene Summary

```json
{
  "type": "DataRecord",
  "name": "az_ma_1_scene_summary",
  "fields": [
    { "type": "Time", "name": "timestamp" },
    { "type": "Count", "name": "odasTimeStamp" },
    { "type": "Count", "name": "trackCount" },
    { "type": "Quantity", "name": "activityLevel", "uom": "1", "constraint": [0.0, 1.0] }
  ]
}
```

---

## 7. Control Stream Schema Reference

### 7.1 Calibrate Orientation

```json
{
  "type": "DataRecord", "name": "calibration",
  "fields": [
    { "type": "Quantity", "name": "headingTrueDeg", "uom": "deg", "constraint": [0.0, 360.0] },
    { "type": "Quantity", "name": "offsetCalDeg", "uom": "deg", "constraint": [-180.0, 180.0] },
    { "type": "Text", "name": "note" }
  ]
}
```

### 7.2 ODAS Control

```json
{
  "type": "DataRecord", "name": "odasControl",
  "fields": [
    { "type": "Category", "name": "module", "constraint": ["sne", "ssl", "sst", "sss", "classify", "general"] },
    { "type": "Text", "name": "parameter" },
    { "type": "Text", "name": "value" },
    { "type": "Category", "name": "applyMode", "constraint": ["immediate", "nextFrame", "nextRestart"] }
  ]
}
```

### 7.3 Request Snapshot

```json
{
  "type": "DataRecord", "name": "snapshot",
  "fields": [
    { "type": "Count", "name": "trackId" },
    { "type": "Quantity", "name": "durationMs", "uom": "ms", "constraint": [10.0, 60000.0] },
    { "type": "Category", "name": "format", "constraint": ["wav", "flac", "json"] }
  ]
}
```

### 7.4 Start/Stop

```json
{
  "type": "DataRecord", "name": "startStop",
  "fields": [
    { "type": "Category", "name": "action", "constraint": ["start", "stop", "restart"] },
    { "type": "Text", "name": "modules" }
  ]
}
```

---

## 8. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Oracle server returned 500 on `GET /deployments/0430?f=sml3` | Low | Use GeoJSON format for deployment PUT (same proven pattern as geometry updates) |
| `deployedSystems` endpoint returned 400 "Invalid resource name" | Low | Use `platform@link` property instead (verified on DO server) |
| UID collisions if UIDs already exist on Oracle | Low | Oracle has zero ODAS content; all UIDs are unique to this migration |
| Observation `phenomenonTime` range must match exactly | Low | Replicate exact timestamps from source server |
| Server may reject SensorML POST for procedures | Medium | Fall back to simpler JSON format if needed; test with one procedure first |
| New system ID unknown until POST response | Low | Script captures Location header from POST response to chain subsequent calls |
| Oracle server `platform@link` format may differ from DO | Medium | GET deployment first, inspect existing property format, then PUT matching structure |

---

## 9. What We're Deliberately NOT Migrating

| Resource | DO ID | Reason |
|---|---|---|
| AZ-MA-NET parent system | `04n0` | AZ-MA-1 becomes standalone top-level on Oracle |
| Deployment AZ-MA-1 | `04dg` | No deployment clones — system links directly to String Alpha |
| Deployment AZ-MA-1-MICARRAY | `04f0` | Deployment clone — not needed |
| Deployment AZ-MA-1-EDGE | `04fg` | Deployment clone — not needed |
| Deployment AZ-MA-1-COMMS | `04g0` | Deployment clone — not needed |
| Deployment AZ-MA-1-POWER | `04gg` | Deployment clone — not needed |
| Deployment AZ-MA-1-ACTUATOR | `04h0` | Deployment clone — not needed |
| AZ-MA-2 system + resources | `04vg` | Out of scope |
| AZ-MA-3 system + resources | `050g` | Out of scope |

---

## 10. Summary Statistics

| Metric | Value |
|---|---|
| **Total API calls** | ~47 |
| **Resources created** | 46 (9 procedures + 1 system + 13 subsystems + 7 datastreams + 4 control streams + 12 observations) |
| **Resources updated** | 1 (String Alpha deployment) |
| **SensorML backup files available** | 14 (system + 13 subsystems) |
| **Datastream schemas captured** | 7 (full SWE Common DataRecord definitions) |
| **Control stream schemas captured** | 4 (full command parameter schemas) |
| **Estimated script complexity** | Moderate — deterministic sequence, no branching logic |
