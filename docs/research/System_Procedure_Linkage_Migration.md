# System → Procedure Linkage Migration

> **Date:** 2026-03-03  
> **Status:** Complete — 32 systems linked, 0 errors  
> **Commit:** [`0995eeb`](https://github.com/OS4CSAPI/ogc-csapi-explorer/commit/0995eeb) (csapi-explorer)  
> **Related:** [LOB_Localizer_Architecture_Correction.md](LOB_Localizer_Architecture_Correction.md) §4 (recommendation D)

---

## 1. Problem

All 42 systems and subsystems on the OSH Node server were missing the SOSA `typeOf` property. This meant there was no machine-readable link from any system to the procedure (method) it implements. The CSAPI Explorer showed "0 Procedures" on the detail view for every system.

This was identified as recommendation D in the ChatGPT review of the Architecture Correction doc.

---

## 2. Approach

### 2.1 Testing

Tested two approaches on the live server:

| Approach | Method | Result |
|----------|--------|--------|
| `typeOf` property on PUT | Add `typeOf` to `properties`, PUT the system | **✓ Persisted** |
| `systemKind@link` on PUT | Add `systemKind@link` to `properties`, PUT the system | Not tested (typeOf worked) |

**Decision:** Use the standard `typeOf` property. It's the SOSA/CSAPI-native way to express "this system implements that procedure."

### 2.2 Linkage Map

9 procedures already existed on the server. The linkage map:

#### Top-Level Systems (3)

| System | Procedure | Rationale |
|--------|-----------|-----------|
| AZ-MA-1 | `urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1` | The node's primary function is the ODAS DSP pipeline |
| AZ-MA-2 | (same) | Identical hardware |
| AZ-MA-3 | (same) | Identical hardware |

#### Subsystems (10 per node × 3 nodes = 30)

| Suffix | Procedure UID | Count |
|--------|--------------|-------|
| `micarray` | `urn:x-odas:procedure:pdm-mems-audio-capture` | 3 |
| `mic1`–`mic7` | `urn:x-odas:procedure:pdm-mems-audio-capture` | 21 |
| `edge` | `urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1` | 3 |
| `actuator` | `urn:x-odas:procedure:odas-config-actuation` | 3 |
| `tripod` | — (infrastructure) | 3 |
| `comms` | — (infrastructure) | 3 |
| `power` | — (infrastructure) | 3 |

**Total: 32 linked + 9 skipped (infrastructure) = 42 systems**

---

## 3. Execution

### 3.1 Migration Script

Created `scripts/link_procedures.py`:
- Discovers subsystems dynamically via `GET /systems/{id}/subsystems`
- Extracts subsystem type from UID suffix (e.g. `micarray`, `edge`, `mic3`)
- Looks up procedure UID from a linkage map
- GET → add `typeOf` → PUT for each system
- Verifies each linkage reads back after PUT

### 3.2 Results

```
── Top-Level MA Systems ──
  ✓ AZ-MA-1 (0420) → processing-chain:v1
  ✓ AZ-MA-2 (0490) → processing-chain:v1
  ✓ AZ-MA-3 (049g) → processing-chain:v1

── Subsystems (sample: AZ-MA-1) ──
  · AZ-MA-1 Tripod Platform (042g) — no procedure (infrastructure)
  ✓ AZ-MA-1 MICARRAY (0430) → pdm-mems-audio-capture
  ✓ AZ-MA-1 EDGE (043g) → processing-chain:v1
  · AZ-MA-1 COMMS (0440) — no procedure (infrastructure)
  · AZ-MA-1 POWER (044g) — no procedure (infrastructure)
  ✓ AZ-MA-1 ACTUATOR (0450) → odas-config-actuation
  ✓ AZ-MA-1 MIC1–MIC7 (045g–048g) → pdm-mems-audio-capture

Summary: 32 linked, 10 skipped, 0 errors
```

(AZ-MA-2 and AZ-MA-3 identical pattern.)

---

## 4. Bootstrap Integration

Updated `scripts/bootstrap_v4.py` to include `typeOf` in all system and subsystem definitions:

- Added 6 procedure UID constants at module level
- Added `typeOf` key to every system/subsystem dict that implements a procedure
- Both `create_systems()` and `create_subsystems()` now include `typeOf` in POST bodies
- Infrastructure subsystems (tripod/comms/power) explicitly commented as no-procedure

Future `--clean` + recreate will preserve all linkages automatically.

---

## 5. SensorHub Behavior Notes

- `typeOf` is accepted on both POST (create) and PUT (update)
- The value is a procedure **UID** (URN string), not a server ID
- SensorHub resolves the UID to the internal procedure reference automatically
- The property persists across server restarts (verified via GET after PUT)
- `typeOf` appears in both `application/geo+json` and `application/json` responses

---

## 6. Verification

After migration, verified MA-1 system and all 13 subsystems:

```
MA-1 (0420):  typeOf = urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1
  Tripod (042g):   typeOf = NONE (correct — infrastructure)
  MICARRAY (0430): typeOf = urn:x-odas:procedure:pdm-mems-audio-capture
  EDGE (043g):     typeOf = urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1
  COMMS (0440):    typeOf = NONE (correct — infrastructure)
  POWER (044g):    typeOf = NONE (correct — infrastructure)
  ACTUATOR (0450): typeOf = urn:x-odas:procedure:odas-config-actuation
  MIC1 (045g):     typeOf = urn:x-odas:procedure:pdm-mems-audio-capture
  MIC2–MIC7:       typeOf = urn:x-odas:procedure:pdm-mems-audio-capture
```

All 9 procedures on the server:

| ID | UID | Linked Systems |
|----|-----|---------------|
| `040g` | `pdm-mems-audio-capture` | 24 (3 micarrays + 21 individual mics) |
| `0410` | `srp-phat-beamforming` | 0 (no dedicated SSL subsystem registered) |
| `041g` | `particle-filter-tracking` | 0 (no dedicated SST subsystem registered) |
| `0420` | `ray-to-ray-triangulation` | 0 (reserved for future triangulation engine) |
| `042g` | `odas-config-actuation` | 3 (actuators) |
| `0430` | `calibration:v1` | 0 (calibration is a process, not a system function) |
| `043g` | `health-monitor:v1` | 0 (monitoring is a cross-cutting concern) |
| `0440` | `processing-chain:v1` | 6 (3 top-level MA + 3 edge processors) |
| `044g` | `frame-transform:v1` | 0 (coordinate transform is internal to the pipeline) |
