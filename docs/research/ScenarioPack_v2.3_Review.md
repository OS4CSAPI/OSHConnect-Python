# Deep Review: ODAS CSAPI Maximal ScenarioPack v2.3

**Date:** 2026-02-26  
**Reviewer:** GitHub Copilot (Claude Opus 4.6)  
**Pack:** `ODAS_CSAPI_Maximal_ScenarioPack_FtHuachuca_v2.3.zip`  
**Target Server:** `http://45.55.99.236:8080/sensorhub/api` (OSH SensorHub)  
**Explorer Repo:** `OS4CSAPI/ogc-csapi-explorer` (branch `demo/acoustic-cuas-targeting`)  
**OSHConnect-Python Repo:** `OS4CSAPI/OSHConnect-Python`

---

## 1. Scale Assessment

This is a comprehensive data pack for a Counter-UAS acoustic sensor network scenario at Fort Huachuca, AZ.

| Category | Count | Details |
|---|---|---|
| Systems | 43 | 1 MA-NET + 3 nodes x (1 parent + 1 platform + 1 micarray + 7 mics + 1 edge + 1 comms + 1 power + 1 actuator) |
| Deployments | 20 | 1 AOI + 1 network + 3 node-level + 15 subdeployments (mic, edge, comms, power, actuator per node) |
| Procedures | 15 | 4 per node (ODAS, transform, health, cal) + 3 network (assoc, triang, classify) |
| Properties | 31 | Full registry: direction cosines, energy, track fields, bearings, classification labels, health metrics |
| SamplingFeatures | 12 | 3 global tracks + 9 per-sensor tracks (3 per node) |
| Datastream templates | 22 | 7 per sensor (SSL, SST, LOB, track, class, health, scene) + 1 triangulated positions |
| Controlstream templates | 13 | 4 per sensor actuator (ODAS control, start/stop, snapshot, cal) + 1 network mode |
| DeployedSystem links | 7 | AOI→(MA-1, MA-2, MA-3, MA-NET) + per-node deployment links |
| Observation NDJSON lines | ~12,600 | 300 seconds x (3 types x 3 sensors x 3 tracks + 3 scene types x 3 sensors + 300 triangulated + 10 events) |
| Command NDJSON lines | ~56 | 10 commands + 20 statuses + 26 create payloads |
| **Total Part 1 resources** | **121** | vs. 64 existing `urn:x-odas:*` resources on server |

## 2. What ChatGPT Got RIGHT

### 2.1 Schema Design — Excellent

Every DataRecord schema has Time as the first field (OSH requirement). SWE Common types are correctly used: `Time`, `Count`, `Quantity`, `Text`, `Category` with appropriate `constraint`/`AllowedValues`/`AllowedTokens`. UCUM unit codes are correct (`deg`, `s`, `m`, `1`, `Cel`, `MB`, `ms`).

### 2.2 Eight Distinct Datastream Types — Correct Inventory

- **SSL Potential Sources** — DataArray of {x, y, z, E} direction cosines
- **SST Tracked Sources** — DataArray of {id, tag, x, y, z, activity}
- **LOB** — flat: {trackId, bearingTrue, bearingStdDev, sensorLat, sensorLon}
- **Track Updates** — flat: {id, tag, x, y, z, activity, bearingTrue, elevation, bearingStdDev, classLabel, classConfidence}
- **Classification Probabilities** — flat: {trackId, p_uas, p_vehicle, p_footsteps, p_impulsive, p_unknown}
- **Triangulated Positions** — flat: {globalTrackId, lat, lon, posErrorM, nSensors, method}
- **Health** — flat: {cpuLoad, memUsedMB, tempC, latencyMs, uptimeS}
- **Scene Summary** — flat: {odasTimeStamp, trackCount, activityLevel}

### 2.3 Observation NDJSON Format — CSAPI-Compliant

Each line has `resultTime`, `phenomenonTime`, `result: {...}`. Per-track observations include `samplingFeature@id`. Per-sensor observations include `system`. Triangulated positions (network-level) omit `system` since they belong to MA-NET's datastream.

### 2.4 Three-Target Scenario — Smart Design

Track 1 = UAS (classLabel: "uas"), Track 2 = vehicle, Track 3 = footsteps. This gives three different classification types moving through the AOI simultaneously — perfect for the C-UAS demo.

### 2.5 Control Streams + Command Status Lifecycle — Complete

Five control stream types x 3 sensors, with CSAPI Part 2 command status codes (PENDING → ACCEPTED → COMPLETED/FAILED). The `http_create_payloads` folder provides ready-to-POST command bodies.

### 2.6 Dual Datastream Creation Paths

Nested (`/systems/{id}/datastreams`) and root (`/datastreams` with `system@link`) is a well-considered accommodation for different OSH server behaviors.

### 2.7 Replay Configuration Mapping

`replay_config.json` properly maps each datastream create template to its NDJSON replay source, tied to a system ID. This is the configuration a real replay engine needs.

## 3. Issues Requiring Attention

### 3.1 CRITICAL: Explorer Observation Format Mismatch

The Explorer's `extractBearings()` (MapViewPage.vue, lines 942-990) expects three specific shapes:

| Format | Explorer expects | ScenarioPack provides |
|---|---|---|
| LOB | `result.numBearings` + `result.bearing0.azimuth` | `result.bearingTrue` (flat, no `numBearings`) |
| SSL | `result.numSources` + `result.source0.{x,y,z,energy}` | `result.src` as an **array** `[{x,y,z,E}]` |
| SST | `result.numTracks` + `result.track0.{id,tag,x,y,z,activity}` | `result.src` as an **array** `[{id,tag,x,y,z,activity}]` |

The Explorer was written against the original `urn:x-odas:*` ingestion format where SSL/SST sources were indexed properties (`source0`, `source1`, `numSources`). The scenario pack uses a proper SWE DataArray with a `src` array — which is the **correct** CSAPI approach but doesn't match the current Explorer parsing.

**Impact:** If you push these observations to the server, the Explorer will receive them but bearing lines won't render.

**Recommended fix:** Update `extractBearings()` to also handle the array-based format (~30 min).

The **LOB** observations also conveniently include `sensorLat`/`sensorLon` in each result, which is actually **better** than relying on `systemLocationCache` since it's self-contained. The Explorer should be updated to parse LOBs from this format too.

### 3.2 Resource IDs Are Logical, Not Server-Assigned

Every resource uses human-readable IDs like `AZ-MA-1`, `AZ-DEP-AOI-001`, etc. When POSTed to OSH, the server assigns its own IDs (like `04g0`, `0480`). The `@link` references in templates use logical IDs: `"href": "/sensorhub/api/deployments/AZ-DEP-AZ-MA-1"`. **These hrefs will be wrong after creation.**

**Fix:** The bootstrap script must capture server-assigned IDs from `Location` headers and rewrite `@link` href values before POSTing dependent resources.

### 3.3 `obsFormat: "application/json"` in Datastream Create Templates

OSHConnect's `add_insert_datastream()` uses `application/swe+json` as the format. The templates specify `"obsFormat": "application/json"`. For DataArray-based schemas (SSL, SST), verify the server accepts both. The safer path is `application/swe+json` if using OSHConnect, or `application/json` if using direct HTTP POSTs.

### 3.4 Bare-Bones Replay Scaffold

`replay_ndjson.py` just counts lines. `generate_curl_replay.py` prints curl commands with `<DATASTREAM_ID>` placeholders. Neither actually replays data. The actual replay engine needs to be built using OSHConnect-Python for ongoing replay and direct HTTP for the one-time bootstrap.

### 3.5 System Count Consideration

The 7 individual microphone elements (MIC1-MIC7) per sensor add 21 systems that produce no datastreams and exist purely for SensorML fidelity. For complete CSAPI compliance, all 43 systems should be created. GitHub issues track each phase independently.

### 3.6 Missing `validTime` on Resources — FIXED

Several system and deployment resources were missing the `validTime` property. This has been remediated in all resource files checked into the repository (see `scenarios/ft-huachuca-v2.3/`). The standard `validTime` used is:

```json
"validTime": ["2026-01-01T00:00:00Z", ".."]
```

This indicates the resource is valid from January 1, 2026 onward with no defined end time, following the ISO 8601 open interval convention.

## 4. Design Decisions

The following decisions were made in consultation with the project lead:

1. **Clean slate or coexist?** → **Keep both.** The `urn:os4csapi:*` namespace is entirely separate from existing `urn:x-odas:*` resources on the server. Both will coexist.

2. **All 43 systems or functional 22?** → **All 43 systems.** Full CSAPI compliance with complete SensorML hierarchy including individual microphone elements.

3. **Direct HTTP or OSHConnect-Python for bootstrap?** → **Hybrid.** Direct HTTP (Python `requests` library with `APIHelper`) for the one-time resource bootstrap. OSHConnect-Python for ongoing NDJSON observation replay.

4. **Defer any work items?** → **No deferrals.** All phases (bootstrap, datastreams/controlstreams, Explorer update, replay engine, validation) will be tracked as individual GitHub issues and executed sequentially.

## 5. Implementation Game Plan

### Phase 1: Bootstrap (Create Resources on Server) — 1-2 hours

1. Write a Python bootstrap script using direct HTTP / `APIHelper` to POST resources in dependency order:
   - Properties (no dependencies, 31 resources)
   - Procedures (no dependencies, 15 resources)
   - Systems (hierarchical: MA-NET first, then 3 parent nodes, then subsystems as children — use `/systems/{parentId}/systems` endpoint)
   - Deployments (hierarchical: AOI first, then network + node deps, then sub-deps)
   - SamplingFeatures (under their parent systems)
   - DeployedSystem links (connect deployments → systems)
2. Capture every server-assigned ID in a `id_map: dict[str, str]` (logical → server)
3. Template-rewrite: before POSTing datastream/controlstream templates, rewrite all `@link.href` values using the id_map

### Phase 2: Create Datastreams + Controlstreams — 30 min

4. POST the 22 datastream create templates (using nested path: `/systems/{server_id}/datastreams`)
5. POST the 13 controlstream create templates
6. Capture datastream/controlstream server IDs into the id_map

### Phase 3: Update Explorer — 30 min

7. Update `extractBearings()` in MapViewPage.vue to handle:
   - Array-based SSL: `result.src[]` with `{x, y, z, E}`
   - Array-based SST: `result.src[]` with `{id, tag, x, y, z, activity}`
   - Flat LOB: `result.bearingTrue` + `result.sensorLat`/`result.sensorLon`
   - Flat track update: `result.bearingTrue` + `result.x/y/z` + `result.classLabel`

### Phase 4: Replay Engine — 1 hour

8. Build a Python NDJSON replay script that:
   - Reads `replay_config.json`
   - Maps each NDJSON file to its server-assigned datastream ID
   - Reads lines in time order, adjusting `resultTime`/`phenomenonTime` to `now + offset`
   - POSTs observations at the configured rate (1 Hz default)
   - Handles errors with retry/backoff
   - Respects the per-system routing (each observation line has `"system": "AZ-MA-1"` which must be mapped to the datastream under that system)

### Phase 5: Validate on Map — 30 min

9. Run the replay, open the Explorer, verify:
   - Systems appear on map with correct geometry
   - Bearing lines render from LOB + SSL + SST + track_update observations
   - Triangulated positions appear as new point features
   - Classification labels are visible in observation popups
   - Health and scene summary data visible in observation details
   - Control stream commands can be issued and status tracked

## 6. File Inventory

The complete scenario pack is checked into `scenarios/ft-huachuca-v2.3/` in the OSHConnect-Python repository with the following structure:

```
scenarios/ft-huachuca-v2.3/
├── README.md
├── diagrams/           (semantic model diagrams: .dot, .mmd, .png, .svg)
├── examples/
│   ├── create_controlstreams/    (13 JSON templates)
│   ├── create_datastreams/       (22 JSON templates, nested path)
│   ├── create_datastreams_root/  (22 JSON templates, root path with system@link)
│   ├── create_deployedSystems/   (7 JSON link resources)
│   ├── create_properties/        (31 JSON property definitions)
│   ├── resources/
│   │   ├── deployedSystems/      (7 JSON)
│   │   ├── deployments/          (20 GeoJSON)
│   │   ├── procedures/           (15 GeoJSON)
│   │   ├── properties/           (31 JSON)
│   │   ├── samplingFeatures/     (12 GeoJSON)
│   │   └── systems/              (43 GeoJSON)
│   └── sample_data/
│       ├── commands/             (NDJSON + HTTP create payloads)
│       └── observations/         (9 NDJSON files, ~12,600 lines total)
├── references/         (feasibility doc + ProfilePack v1.2 zip)
├── registers/          (CSV/JSON/MD catalogs for resources, schemas, properties, units, value sets)
├── schemas/
│   ├── controlstreams/  (5 SWE+JSON command schemas)
│   └── datastreams/     (8 SWE+JSON observation schemas)
└── simulator/
    └── oshconnect_replay/  (replay_config.json, scripts, README)
```

## 7. GitHub Issues Created

All implementation work is tracked as GitHub issues:

- **Phase 1** (OSHConnect-Python): Bootstrap — create resources on server
- **Phase 2** (OSHConnect-Python): Create datastreams + controlstreams
- **Phase 3** (ogc-csapi-explorer): Update `extractBearings()` for v2.3 observation formats
- **Phase 4** (OSHConnect-Python): Build NDJSON replay engine
- **Phase 5** (ogc-csapi-explorer): Validate end-to-end on map
