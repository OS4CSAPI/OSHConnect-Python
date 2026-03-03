# Detection Range — Server Migration Report

> **Date:** 2026-03-03  
> **Status:** Complete  
> **Repo:** OS4CSAPI/ogc-csapi-explorer  
> **Principle:** No faked data — all information flows through the Connected Systems API standard.

---

## 1. Problem Statement

The frontend (`MapViewPage.vue`) contained a hardcoded `DETECTION_RANGE_CONFIGS` object with identical detection range values copy-pasted for each of the three MA sensor nodes. This meant:

- Detection range rings on the map were **fabricated by the frontend**, not discovered from the server.
- If range values changed (different hardware, recalibration, new node), the frontend code had to be manually updated.
- The architecture violated the core demo narrative: all sensor metadata should flow through the OGC Connected Systems API.

The comment in the code even acknowledged this:

> *"Client-side config: keyed by system UID. When the server supports custom properties, this can be replaced with a read from the system's `detectionRange` property."*

## 2. Investigation — SensorML Capabilities

Before implementing the datastream approach, we tested whether SensorHub could store detection range values as SensorML **capabilities** or **characteristics** on the system resource. Four approaches were tried:

| Approach | Method | Result |
|----------|--------|--------|
| GeoJSON custom property | PUT `/systems/0420` with `detectionRange` in `properties` | **Silently dropped** — OSH only persists known GeoJSON properties |
| SensorML `capabilities` with `fields` | PUT `?f=sml3` with `fields: [Quantity...]` | **400 Bad Request** |
| SensorML `capabilities` with `field` (singular) | PUT `?f=sml3` with `field: [Quantity...]` | **204** but fields silently dropped — only envelope persisted |
| SensorML `characteristics` with `field` | PUT `?f=sml3` with `field: [Quantity...]` | **204** but fields silently dropped — only envelope persisted |

**Conclusion:** OSH Node's persistence layer accepts capability/characteristic group envelopes but does not persist SWE component values within them. This is a server limitation, not a format issue.

## 3. Solution — Detection Capabilities Datastream

The proper CSAPI approach: create a **detection_capabilities datastream** on each MA system and post the range values as an observation. This is:

- **Discoverable** — frontend finds it by querying `/systems/{id}/datastreams`
- **Timestamped** — observations carry `phenomenonTime`
- **Standard-compliant** — data flows through the API like everything else
- **Updatable** — POST a new observation if ranges change (recalibration, new hardware)

### 3.1 Datastream Schema

| # | Field | Type | Definition | Description |
|---|-------|------|------------|-------------|
| 1 | `timestamp` | Time | `epochSeconds` | Epoch seconds |
| 2 | `shape` | Text | `detectionShape` | Detection area shape (e.g. "circular") |
| 3 | `minRange_m` | Quantity (m) | `detectionMinRange` | Minimum detection range |
| 4 | `nominalRange_m` | Quantity (m) | `detectionNominalRange` | Nominal detection range |
| 5 | `maxRange_m` | Quantity (m) | `detectionMaxRange` | Maximum detection range |
| 6 | `confidence` | Quantity (0–1) | `detectionConfidence` | Detection confidence level |
| 7 | `basis` | Text | `detectionBasis` | Basis of estimate |

> **Authoritative schema source:** [`scripts/bootstrap_v4.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py) — added to `AZMA1_DATASTREAMS`, auto-cloned for MA-2/MA-3 via `_clone_for_node()`.

### 3.2 Created Datastreams

| Node | System ID | DS ID | outputName |
|------|-----------|-------|------------|
| AZ-MA-1 | `0420` | `04dg` | `az_ma_1_detection_capabilities` |
| AZ-MA-2 | `0490` | `04e0` | `az_ma_2_detection_capabilities` |
| AZ-MA-3 | `049g` | `04eg` | `az_ma_3_detection_capabilities` |

### 3.3 Observation Values (identical for all 3 — same hardware)

```json
{
  "timestamp": 1772581445.3,
  "shape": "circular",
  "minRange_m": 667,
  "nominalRange_m": 1833,
  "maxRange_m": 3000,
  "confidence": 0.7,
  "basis": "estimated"
}
```

### 3.4 Verification

```
GET /datastreams/04dg/observations?limit=1
→ 200 OK
→ result.maxRange_m = 3000.0 ✓
→ result.shape = "circular" ✓
→ result.confidence = 0.7 ✓
```

## 4. Frontend Changes

### 4.1 Removed

The entire hardcoded `DETECTION_RANGE_CONFIGS` constant (lines 146–197) was deleted — 3 copies of identical fake data keyed by system UID.

### 4.2 Added

**`fetchDetectionRangeConfigs()`** — async function that:
1. Iterates all primary systems
2. For each, queries `/systems/{id}/datastreams` to find one whose `outputName` ends with `_detection_capabilities`
3. Reads the latest observation from that datastream
4. Resolves the system's UID via `/systems/{id}`
5. Populates `detectionRangeConfigs[uid]` with rings built from the observation data

### 4.3 Updated

- `buildDetectionRanges()` — reads from server-populated `detectionRangeConfigs` instead of the hardcoded constant
- Call site in the load sequence — now awaits `fetchDetectionRangeConfigs()` before `buildDetectionRanges()`
- Feature `rawData` — replaced `asOf`/`altitude` with `phenomenonTime` from the observation

### 4.4 Build Verification

- `vue-tsc --noEmit` — **0 errors**
- `vite build` — **success** (705 modules, 8.48s)

## 5. Other Files Updated

| File | Change |
|------|--------|
| `scripts/bootstrap_v4.py` | Added detection_capabilities datastream to `AZMA1_DATASTREAMS` (auto-cloned for MA-2/MA-3) |
| `scripts/clear_observations.py` | Added DS IDs `04dg`, `04e0`, `04eg` to `ALL_DS_IDS` |
| `simulator/main.py` | Same — added 3 new DS IDs |
| `scripts/add_detection_range.py` | **New** — one-time migration script that created the datastreams and posted observations |
| `scripts/fix_lob_schema.py` | **New** — earlier migration script (LOB schema fix, classification field) |

## 6. Audit — Other Hardcoded Values

While investigating, we audited the entire frontend for other instances of faked data:

| Item | Location | Verdict |
|------|----------|---------|
| `classification || 'UAS'` | `extractBearings()` LOB branch | **Fixed** — removed fallback, reads `result.classification` from server only |
| `BEARING_LINE_LENGTH_M = 3000` | MapViewPage.vue line 1521 | **OK** — rendering constant (how long to draw the line visually), not pretending to be server data |
| `energy: 1.0` | LOB bearing extraction | **OK** — rendering default for line opacity; LOB schema has no energy field; comment explains it |
| `"classification": "UAS"` in simulator/engine.py | `build_lob_observation()` | **OK** — the simulator is a *producer*; this is the value it publishes through the standard |

## 7. Architecture Alignment

This change completes the elimination of hardcoded data in the frontend. The demo now demonstrates:

```
Server (SensorHub)
  └── System: AZ-MA-1
        ├── Datastream: LOB (bearings + classification)        ← sensor produces
        ├── Datastream: Detection Capabilities (range values)  ← sensor metadata
        ├── Datastream: SSL, SST, Health, etc.                 ← sensor produces
        └── ...

Frontend (Web App)
  └── Discovers ALL of the above via GET requests
  └── Draws detection rings from observation data
  └── Draws bearing lines from LOB observations
  └── Shows classification labels from server data
  └── Zero hardcoded sensor metadata
```

Every piece of information the user sees on the map now flows through the OGC Connected Systems API.
