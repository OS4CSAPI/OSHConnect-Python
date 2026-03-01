# AZ-MA-1 Migration Feasibility Report: DO → Oracle OSH

> **Date:** 2026-03-01 (Revised)  
> **Author:** CSAPI Explorer Research Agent  
> **Status:** Research Complete — Migration Approved  
> **Source Server:** DigitalOcean OSH (`http://45.55.99.236:8080/sensorhub/api`)  
> **Target Server:** Oracle OSH (`https://os4csapi-osh.duckdns.org/sensorhub/api`)
>
> **Revision Note (2026-03-01):** Updated Section 3.3 to adopt a dual-write strategy (`deployedSystems@link` + `platform@link`) based on review feedback. Added Section 3.4 documenting the `sosa:Platform` vs `sosa:System` semantic decision for existing Oracle systems. Updated Phase 7 and risk table accordingly.
>
> **Revision Note (2026-03-01, v2):** Corrected observation counts from 3 per datastream (12 total) to actual counts totaling ~7,465. Updated total API call count from ~47 to ~7,500. Corrected procedure references on datastreams. Dry-run POST test validated on Oracle (201 Created + 204 Deleted). Migration script written and validated.

---

## 1. Executive Summary

**Verdict: YES, fully possible.** Every artifact comprising the ODAS Mic Array Node AZ-MA-1 system can be recreated on the Oracle OSH server via standard OGC Connected Systems API POST/PUT operations. The migration involves ~7,500 API calls across 7 deterministic phases.

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
| `07h02` | Track Updates | **1,864** | `{timestamp, odasTimeStamp, id, tag, x, y, z, activity, bearingTrue, elevation, bearingStdDev, classLabel, classConfidence}` |
| `07hg2` | Classification Probabilities | **1,868** | `{timestamp, trackId, p_uas, p_vehicle, p_footsteps, p_impulsive, p_unknown}` |
| `07i02` | Health | **1,867** | `{timestamp, cpuLoad, memUsedMB, tempC, latencyMs, uptimeS}` |
| `07ig2` | Scene Summary | **1,866** | `{timestamp, odasTimeStamp, trackCount, activityLevel}` |

**Important:** All 7 datastreams have `procedure@link` references: 5 datastreams (`07fg2`, `07g02`, `07gg2`, `07h02`, `07ig2`) reference procedure `04c0` (ODAS Processing Chain), 1 (`07hg2`) references `04hg` (classification procedure, shared with AZ-MA-NET), and 1 (`07i02`) references `04bg` (Health Proc). The migration script preserves these procedure-to-datastream links by remapping DO procedure IDs to their Oracle equivalents.

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
- **~7,465 observations** across 4 datastreams

### 3.3 System-to-Deployment Link Strategy (Dual-Write)

> **Design Decision (2026-03-01):** We adopt a **dual-write strategy** for the deployment↔system association. The migration script will write both `deployedSystems@link` (the correct OGC standard mechanism) and `platform@link` (the OSH-compatible fallback) in the same PUT payload.

#### Background

The OGC Connected Systems standard (23-001, Table 11) defines `deployedSystems` as a **Required** association on Deployment resources, encoded as an inline GeoJSON property `properties/deployedSystems@link` — a JSON array of links to System resources (Table 43). This is the architecturally correct, scalable mechanism: it supports many-to-one (multiple systems per deployment), which is essential for v3.0 where Sensor String Alpha will eventually host MA-1, MA-2, and MA-3.

However, OSH SensorHub **silently strips `deployedSystems@link` on write** and never returns it on read. This is a documented conformance gap (see [OSH_DeployedSystems_Conformance_Gap.md](./OSH_DeployedSystems_Conformance_Gap.md)). The server only persists single-object `@link` properties like `platform@link`.

#### Dual-Write Payload

The Phase 7 PUT to Sensor String Alpha (`0430`) will include **both** properties:

```json
{
  "type": "Feature",
  "id": "0430",
  "properties": {
    "uid": "urn:os4csapi:deployment:string:ft-huachuca:001",
    "featureType": "sosa:Deployment",
    "name": "Sensor String Alpha (line-of-emplacement)",
    "validTime": ["2026-02-27T00:00:00Z", ".."],

    "deployedSystems@link": [
      {
        "href": "https://os4csapi-osh.duckdns.org/sensorhub/api/systems/{new-ma1-id}",
        "uid": "urn:os4csapi:system:odas:az-ma-1",
        "title": "ODAS Mic Array Node AZ-MA-1"
      }
    ],

    "platform@link": {
      "href": "https://os4csapi-osh.duckdns.org/sensorhub/api/systems/{new-ma1-id}",
      "rel": "platform",
      "title": "AZ-MA-1"
    }
  }
}
```

#### What Happens Today vs Future

| Property | OSH Behavior Today | When OSH Fixes Gap |
|---|---|---|
| `deployedSystems@link` | **Silently stripped** — no effect | Will be persisted and returned; becomes the primary association |
| `platform@link` | **Persisted and returned** — working fallback | Becomes secondary/optional; retained for "physical host" semantics |

#### Why Not `platform@link` Alone?

`platform@link` is semantically different from `deployedSystems@link`:

- **`sosa:deployedOnPlatform`** (platform@link) = "the physical thing the deployment sits on" — 1:1, single object
- **`sosa:deployedSystem`** (deployedSystems@link) = "the systems participating in this deployment" — 1:many, array

Using `platform@link` alone works for a single sensor, but breaks when String Alpha hosts MA-1 + MA-2 + MA-3 — `platform@link` can only reference one system. The dual-write approach ensures:

1. The correct standard association is always **in the payload** (even if OSH strips it today)
2. The `platform@link` fallback keeps the association visible to clients today
3. When OSH eventually persists `deployedSystems@link`, the data is already correct — no migration needed

#### CSAPI Explorer Client Compatibility

The Explorer codebase already implements the correct fallback chain in `DataModelDiagram.vue`:

1. Try `deployedSystems@link` (standard mechanism)
2. Fall back to `platform@link` (OSH workaround)
3. Fall back to `deployedSystemUIDs` (legacy string-based)

This means the client is already future-proof for the day OSH fixes the conformance gap.

### 3.4 featureType Semantics: `sosa:Platform` vs `sosa:System`

> **Design Decision (2026-03-01):** After review, the existing Oracle systems use a mix of `sosa:Platform` that warrants partial correction for v3.0 consistency.

#### The Debate

The three existing systems on Oracle were all bootstrapped with `featureType: sosa:Platform`. An external review flagged this as a semantic inconsistency with the v3.0 scenario pack direction, which models these as Systems with "platform-ness" handled via metadata or decomposition. The question: should these be `sosa:System` or `sosa:Platform`?

#### SOSA/SSN Semantics

In the SOSA/SSN ontology:
- **`sosa:Platform`** — "An entity that hosts other entities, particularly Sensors, Actuators, Samplers, and other Platforms." It's fundamentally about **physical hosting** — the thing other things are mounted on or deployed to.
- **`sosa:System`** — "A System is a unit of abstraction for pieces of infrastructure that implement Procedures." It's about **functional composition** — a logical unit that may contain sensors, platforms, and other subsystems.

#### Per-System Analysis and Decision

| System | Current | Decision | Rationale |
|---|---|---|---|
| **SET-A** (Sensor Employment Team) | `sosa:Platform` | **Change to `sosa:System`** | SET-A is an organizational/operational unit (a team of people + equipment). It doesn't physically "host" sensors — it *employs* them. `sosa:System` correctly models it as a functional composite. |
| **Monitoring Site Node 1** | `sosa:Platform` | **Keep as `sosa:Platform`** | MonSite is a physical location/installation where sensors are mounted. It literally hosts other entities (tripods, arrays, relays). `sosa:Platform` is semantically correct per the SOSA definition. |
| **Relay / Repeater 001** | `sosa:Platform` | **Keep as `sosa:Platform`** | The relay is physical communications infrastructure that hosts antennas and radios. It's a platform in the SOSA sense — other things are deployed on it. |

#### Action

The SET-A `featureType` correction (`sosa:Platform` → `sosa:System`) will be applied in the next bootstrap revision. It is **not a migration blocker** — it's a pre-existing issue unrelated to the AZ-MA-1 migration itself.

The AZ-MA-1 system being migrated uses `sosa:System`, which is correct and consistent with v3.0 direction.

---

## 4. Migration Plan — 7 Phases

| Phase | Action | API Method | Endpoint | Count |
|---|---|---|---|---|
| **1** | Create procedures | `POST` × 9 | `/procedures` | 9 |
| **2** | Create AZ-MA-1 (top-level) | `POST` × 1 | `/systems` | 1 |
| **3** | Create subsystems | `POST` × 13 | `/systems/{ma1}/subsystems` | 13 |
| **4** | Create datastreams | `POST` × 7 | `/systems/{ma1}/datastreams` | 7 |
| **5** | Create control streams | `POST` × 4 | `/systems/{actuator}/controlstreams` | 4 |
| **6** | Create observations | `POST` × ~7,465 | `/datastreams/{ds}/observations` | ~7,465 |
| **7** | Link to String Alpha | `GET+PUT` × 1 | `/deployments/0430` | 1 |

**Total: ~7,500 API calls**

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

#### Phase 6: Observations (~7,465 POSTs)
POST observations to the 4 datastreams that have data: Track Updates (1,864), Classification Probabilities (1,868), Health (1,867), Scene Summary (1,866). Each observation includes `phenomenonTime`, `resultTime`, and the full result record. Observations are posted one-at-a-time with progress logging every 500 and a small throttle delay every 100 to avoid overwhelming the server.

#### Phase 7: Deployment Link — Dual-Write (1 GET+PUT)
GET Sensor String Alpha (`0430`) from Oracle, add both `deployedSystems@link` (standard, array) and `platform@link` (OSH fallback, single object) pointing to the newly-created AZ-MA-1 system ID, strip `links`, PUT back. OSH will silently strip `deployedSystems@link` today but preserve `platform@link`. See Section 3.3 for full rationale.

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
| `deployedSystems@link` silently stripped by OSH | **Known** | Dual-write strategy: include both `deployedSystems@link` and `platform@link` in PUT payload. OSH preserves `platform@link` as fallback; `deployedSystems@link` will activate when OSH fixes the conformance gap. See [OSH_DeployedSystems_Conformance_Gap.md](./OSH_DeployedSystems_Conformance_Gap.md). |
| `platform@link` limited to 1:1 (single system per deployment) | Medium | Acceptable for initial MA-1 migration. When MA-2/MA-3 are added, `deployedSystems@link` must be working or an alternative approach (e.g., multiple `platform@link`-bearing subdeployments) will be needed. |
| UID collisions if UIDs already exist on Oracle | Low | Oracle has zero ODAS content; all UIDs are unique to this migration |
| Observation `phenomenonTime` range must match exactly | Low | Replicate exact timestamps from source server |
| Server may reject SensorML POST for procedures | Medium | Fall back to simpler JSON format if needed; test with one procedure first |
| New system ID unknown until POST response | Low | Script captures Location header from POST response to chain subsequent calls |
| SET-A `featureType` is `sosa:Platform` instead of `sosa:System` | Low | Pre-existing issue, not a migration blocker. Will be corrected in next bootstrap revision. See Section 3.4. |

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
| **Total API calls** | ~7,500 |
| **Resources created** | ~7,499 (9 procedures + 1 system + 13 subsystems + 7 datastreams + 4 control streams + ~7,465 observations) |
| **Resources updated** | 1 (String Alpha deployment) |
| **SensorML backup files available** | 14 (system + 13 subsystems) |
| **Datastream schemas captured** | 7 (full SWE Common DataRecord definitions) |
| **Control stream schemas captured** | 4 (full command parameter schemas) |
| **Estimated script complexity** | Moderate — deterministic sequence, no branching logic |
