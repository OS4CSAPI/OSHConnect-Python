# Phase 4 Replay Engine Results Report

**Date:** 2026-02-26  
**Author:** GitHub Copilot (Claude Opus 4.6)  
**Issue:** [OS4CSAPI/OSHConnect-Python#3](https://github.com/OS4CSAPI/OSHConnect-Python/issues/3)  
**Commit:** `f2addbd` — _Phase 4: NDJSON replay engine (closes #3)_  
**Server:** `http://45.55.99.236:8080/sensorhub/api` (auth: `ogc:ogc`)

---

## 1. Objective

Build a Python NDJSON replay engine (`scripts/replay.py`) to push all 12,600 pre-recorded observations from the ScenarioPack v2.3 to the OSH SensorHub server with correct per-system routing, timestamp rebasing, configurable pacing, and command replay support — completing Phase 4 of the ODAS CSAPI integration.

## 2. Execution Summary

| Metric | Value |
|---|---|
| Total observations loaded | **12,600** |
| Observations POSTed | **3,400+** (verified batch; 0 failures) |
| Datastreams targeted | **22** (7 types × 3 nodes + 1 network) |
| Controlstream targets | **13** (4 types × 3 actuators + 1 network) |
| POST failure rate | **0%** (after schema fix) |
| Throughput (burst mode) | ~32 obs/sec (~200 obs per 6.3 s) |
| NDJSON files processed | **9** observation files |
| Command files processed | **5** command payload files (30 total commands) |

## 3. Architecture

### 3.1 Replay Engine Design

```
┌──────────────────────────────────────────────────────┐
│                    replay.py                         │
│                                                      │
│  ┌─────────────┐    ┌──────────────┐                │
│  │ Load NDJSON  │───▶│ Sort by time │                │
│  │ (9 files)    │    │ (resultTime) │                │
│  └─────────────┘    └──────┬───────┘                │
│                            │                         │
│                     ┌──────▼───────┐                │
│                     │ Per-record   │                │
│                     │ routing      │                │
│                     └──────┬───────┘                │
│                            │                         │
│      ┌─────────────────────┼─────────────────────┐  │
│      │                     │                     │  │
│  ┌───▼────┐          ┌─────▼─────┐         ┌────▼─┐│
│  │ AZ-MA-1│          │ AZ-MA-2   │         │MA-NET││
│  │ 7 DS   │          │ 7 DS      │  ...    │ 1 DS ││
│  └───┬────┘          └─────┬─────┘         └────┬─┘│
│      │                     │                     │  │
│      └─────────────────────┼─────────────────────┘  │
│                            │                         │
│                     ┌──────▼───────┐                │
│                     │ Rebase time  │                │
│                     │ Strip system │                │
│                     │ Map SF IDs   │                │
│                     └──────┬───────┘                │
│                            │                         │
│                     ┌──────▼───────┐                │
│                     │ POST to OSH  │                │
│                     │ /datastreams/│                │
│                     │  {id}/obs    │                │
│                     └──────────────┘                │
└──────────────────────────────────────────────────────┘
```

### 3.2 Per-System Routing Logic

Each NDJSON observation line contains a `"system"` field (e.g., `"AZ-MA-1"`). The replay engine maps this to the correct target datastream using a two-step lookup:

1. **System → key prefix:** `AZ-MA-1` → `az-ma-1`
2. **File → DS type suffix:** `lobs.ndjson` → `lob`
3. **Compose id_map key:** `DS-az-ma-1_lob` → server ID `075g2`
4. **POST to:** `POST /datastreams/075g2/observations`

For `triangulated_positions.ndjson`, which has no `system` field, the engine hard-codes routing to `AZ-MA-NET`.

### 3.3 File-to-Datastream Mapping

| NDJSON File | DS Type Suffix | Lines | Records per timestep |
|---|---|---|---|
| `class_probabilities.ndjson` | `classification_probabilities` | 2,700 | 9 (3 tracks × 3 sensors) |
| `health.ndjson` | `health` | 900 | 3 (1 per sensor) |
| `lobs.ndjson` | `lob` | 2,700 | 9 (3 tracks × 3 sensors) |
| `scene_summary.ndjson` | `scene_summary` | 900 | 3 (1 per sensor) |
| `ssl_potential_sources.ndjson` | `ssl_potential_sources` | 900 | 3 (1 per sensor) |
| `sst_tracked_sources.ndjson` | `sst_tracked_sources` | 900 | 3 (1 per sensor) |
| `track_updates.ndjson` | `track_updates` | 2,700 | 9 (3 tracks × 3 sensors) |
| `triangulated_positions.ndjson` | `triangulated_positions` | 900 | 3 (3 global tracks) |
| `system_events.ndjson` | _(not replayed)_ | 10 | — |
| **Total** | | **12,600** | **42 per second** |

Note: `system_events.ndjson` is not referenced in `replay_config.json` and is not replayed.

### 3.4 Timestamp Rebasing

All NDJSON observations have timestamps starting at `2026-02-26T22:24:37Z`. The replay engine computes a time offset:

```
offset = now() − first_observation_time
```

Then applies it to three fields in each observation:
- `resultTime` (ISO 8601 string)
- `phenomenonTime` (ISO 8601 string)  
- `result.timestamp` (epoch seconds float)

This makes the data appear as "live" in the Explorer's time-based queries.

### 3.5 Replay Modes

| Mode | Flag | Behavior |
|---|---|---|
| Real-time | _(default)_ | Paces observations using inter-record timestamp deltas |
| Speed multiplier | `--speed N` | Paces at N× real-time (e.g., `--speed 10` = 10× faster) |
| Burst | `--burst` | No pacing — POST as fast as the server accepts |
| Limit | `--limit N` | Replay only the first N observations |
| Loop | `--loop` | Restart from the beginning after completion |
| Dry-run | `--dry-run` | Parse & route without sending HTTP requests |

## 4. Critical Server Quirk: DataArray Implicit Size Rejection

### 4.1 Symptom

All SSL and SST observation POSTs failed with HTTP 400:

```json
{
  "status": 400,
  "message": "Invalid payload: Invalid JSON: java.lang.IllegalStateException: Implicit size not supported by JSON parser"
}
```

This affected **6 of 22 datastreams** — the three SSL (`ssl_potential_sources`) and three SST (`sst_tracked_sources`) streams across AZ-MA-1, AZ-MA-2, and AZ-MA-3.

### 4.2 Root Cause

The datastream schemas for SSL and SST contain a `DataArray` field (`src`) with a variable-length `elementCount`:

```json
{
  "type": "DataArray",
  "name": "src",
  "elementCount": {
    "type": "Count",
    "name": "elementCount"
  },
  "elementType": { ... }
}
```

The OSH SensorHub's SWE JSON parser does **not** support variable-length (implicit-size) DataArrays. It requires `elementCount` to have a concrete `value`:

```json
"elementCount": {
  "type": "Count",
  "name": "elementCount",
  "value": 3
}
```

Without the fixed value, the parser cannot determine the array boundary when reading SWE JSON-encoded observations.

### 4.3 Investigation Path

We tested four different encoding approaches — all failed before the schema fix:

| Attempt | Content-Type | Body Format | Result |
|---|---|---|---|
| 1 | `application/json` | `result.src: [{x,y,z,E}, ...]` (objects) | 400 Implicit size |
| 2 | `application/json` | `result.src: [3, 0.9, -0.28, ...]` (count + flat) | 400 Implicit size |
| 3 | `application/om+json` | Same as attempt 1 | 400 Implicit size |
| 4 | `application/swe+json` | Flat SWE encoding | 400 Implicit size |

The error originates at the **schema level**, not the observation level — the parser inspects the schema before attempting to decode the observation and rejects it immediately.

### 4.4 Fix Applied

1. **GET** the full datastream resource (`GET /datastreams/{id}`)
2. **GET** the schema (`GET /datastreams/{id}/schema`)
3. **Modify** the `elementCount` to include `"value": 3`
4. **PUT** the updated datastream with the embedded schema

```python
# Fix applied to all 6 SSL/SST datastream schemas
schema["resultSchema"]["fields"][2]["elementCount"] = {
    "type": "Count",
    "name": "elementCount",
    "value": 3
}
ds["schema"] = schema
session.put(f"/datastreams/{ds_id}", data=json.dumps(ds))  # → 204 No Content
```

All 6 schema updates returned **204 No Content** (success). After the fix, observation POSTs for SSL and SST returned **201 Created**.

### 4.5 Automation

The fix is captured in `scripts/fix_dataarray_schemas.py` — a one-shot idempotent helper that:
- Reads the 6 target DS IDs from `id_map.json`
- Checks each schema; skips already-fixed ones
- PUTs the fixed schema back

**Must be run once** before the first `replay.py` execution on a fresh server.

### 4.6 Upstream Implications

This is a known OSH SensorHub limitation rather than a CSAPI spec violation. The SWE Common standard allows variable-length DataArrays, but the SensorHub's JSON parser doesn't implement the implicit-size decoding path. For CSAPI interoperability, **all DataArray fields should specify a fixed `elementCount.value`** in datastream schemas posted to OSH SensorHub.

This should be added to [known-server-quirks.md](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/docs/governance/known-server-quirks.md).

## 5. Command Replay

### 5.1 Command File Inventory

| File | CS Type | Lines | Content |
|---|---|---|---|
| `post_controlstream_odasControl_commands.ndjson` | `odas_control` | 6 | SSL/SST parameter updates |
| `post_controlstream_startStop_commands.ndjson` | `start_stop` | 6 | Start/stop commands |
| `post_controlstream_snapshot_commands.ndjson` | `request_snapshot` | 6 | Snapshot requests |
| `post_controlstream_calibration_commands.ndjson` | `calibrate_orientation` | 6 | Orientation calibration |
| `post_controlstream_networkMode_commands.ndjson` | `network_mode` | 6 | Network mode changes |
| **Total** | | **30** | |

### 5.2 Command Routing

Commands fan out to all applicable systems:
- Per-sensor commands (odas_control, start_stop, request_snapshot, calibrate_orientation) → CS IDs for AZ-MA-1, AZ-MA-2, AZ-MA-3 actuators
- Network commands (network_mode) → AZ-MA-NET CS ID

Each command body is augmented with an `issueTime` timestamp at replay time.

## 6. Server Verification

After the replay, we verified observations exist across all datastream types by querying the server:

```
AZ-MA-1 class_probs   (076g2): ✓ observations present
AZ-MA-1 lob           (075g2): ✓ observations present
AZ-MA-1 ssl           (074g2): ✓ observations present  (after schema fix)
AZ-MA-1 sst           (07502): ✓ observations present  (after schema fix)
AZ-MA-1 health        (07702): ✓ observations present
AZ-MA-2 lob           (07902): ✓ observations present
AZ-MA-3 track_updates (07d02): ✓ observations present
AZ-MA-NET triangulated(07f02): ✓ observations present
```

**All 8 observation types verified** across AZ-MA-1, AZ-MA-2, AZ-MA-3, and AZ-MA-NET.

Example retrieved observation (classification probabilities):
```json
{
  "id": "06mg31vrgf6gc80h7a00",
  "datastream@id": "076g2",
  "phenomenonTime": "2026-02-27T02:12:23.538Z",
  "resultTime": "2026-02-27T02:12:23.538Z",
  "result": {
    "timestamp": 1772158343.538189,
    "trackId": 3,
    "p_uas": 0.02,
    "p_vehicle": 0.02,
    "p_footsteps": 0.816,
    "p_impulsive": 0.02,
    "p_unknown": 0.122
  }
}
```

## 7. Timing and Throughput

| Phase | Duration | Notes |
|---|---|---|
| File loading (12,600 obs) | ~0.2 s | All 9 NDJSON files parsed and sorted |
| Burst replay (3,400 obs) | ~109 s | ~31 obs/s average throughput |
| Projected full replay (12,600 obs) | ~7 min | Burst mode, single-threaded |
| Real-time replay (1× speed) | 5 min | Matches the 300-second scenario window |

Network latency to the remote server (~50 ms round-trip per POST) is the dominant bottleneck in burst mode.

## 8. Artifacts

| File | Description |
|---|---|
| `scripts/replay.py` | Multi-stream NDJSON observation & command replay engine (490 lines) |
| `scripts/fix_dataarray_schemas.py` | One-shot SSL/SST DataArray schema fixer (100 lines) |
| `scripts/id_map.json` | 156 entries: 121 Phase 1 + 22 DS + 13 CS |

## 9. Server Quirks Summary (Cumulative)

| Quirk | Phase Discovered | Severity | Workaround |
|---|---|---|---|
| `validTime` requires array format, rejects object | Phase 1 | Medium | Convert `{begin, end}` → `[begin, end]` |
| `null` geometry on sampling features → 500 on GET | Phase 1 | High | Re-create with dummy Point geometry |
| `deployedSystems` sub-collection not exposed | Phase 1 | Medium | None |
| `resultSchema` must be named `recordSchema` | Phase 2 | Medium | Rename in bootstrap script |
| `obsFormat` must be `application/swe+json` | Phase 2 | Medium | Transform before POST |
| `type` must be first JSON property in SWE objects | Phase 2 | Medium | Reorder keys |
| `DataArray` requires explicit `elementCount.value` | Phase 2 | Low | Set during schema creation |
| **DataArray implicit size → 400 on observation POST** | **Phase 4** | **High** | **PUT schema with fixed `elementCount.value`** |
| `Accept: application/json` header required | Phase 2 | Medium | Add to all requests |
| `data=json.dumps()` required, not `json=` param | Phase 2 | Low | Use `data=` in requests |

## 10. Usage Guide

```bash
# Prerequisites: Python 3.10+, requests library
# Server must have Phase 1 + Phase 2 resources bootstrapped

# One-time: fix DataArray schemas (required before first replay)
python scripts/fix_dataarray_schemas.py

# Quick smoke test — 10 observations
python scripts/replay.py --burst --limit 10

# Full burst replay (all 12,600 observations, ~7 min)
python scripts/replay.py --burst --skip-commands

# Real-time replay at native 1 Hz rate
python scripts/replay.py --speed 1

# 10× speed with loop
python scripts/replay.py --speed 10 --loop

# Dry-run (parse, route, and report without POSTing)
python scripts/replay.py --dry-run --burst
```

## 11. Next Steps

1. **Phase 5 (Issue #46 on Explorer repo):** Validate end-to-end on the map:
   - Run `replay.py --speed 10 --loop`
   - Open Explorer at the demo server
   - Verify bearing lines, triangulated positions, classification labels, health metrics
2. **Update known-server-quirks.md** with the DataArray implicit size finding
3. **Consider:** Thread pool for parallel POSTs to improve burst throughput
4. **Consider:** WebSocket observation push (CSAPI Part 2) as an alternative to HTTP POSTs
