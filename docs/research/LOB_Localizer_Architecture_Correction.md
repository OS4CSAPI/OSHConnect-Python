# LOB Localizer — Architecture Correction

> **Supersedes:** Section 5 (Execution Model) of [LOB_Triangulation_Implementation_Spec.md](LOB_Triangulation_Implementation_Spec.md)  
> **Date:** 2026-03-03  
> **Updated:** 2026-03-03 — §3.2 dynamic discovery + Δt gate; §4.2 typeOf linkage now implemented  
> **Status:** Architectural decision record  
> **Decision:** The localizer MUST be a standalone CSAPI consumer/producer, NOT embedded in the simulator.

---

## 1. The Problem with the Previous Design

The original implementation spec (Section 5.1) prescribed running the triangulation logic **inside the simulator's tick loop**:

```
for each tick:
    1. compute UAV position
    2. POST LOB observations
    3. collect this tick's LOBs (already in memory)  ← problem
    4. triangulate → POST location estimate
```

This is architecturally wrong for three reasons:

### 1.1 It Bypasses the Standard

The simulator never reads from the server — it uses in-memory data from the same process. This makes the CSAPI server a write-only log rather than the interoperability hub it's supposed to be. The entire point of Connected Systems API is that **producers and consumers interact through the standard interface**, not through shared memory.

### 1.2 It Defeats the Demo Narrative

Our demo is showing that OGC API Connected Systems enables practical, loosely-coupled sensor fusion. If the fusion logic lives inside the simulator, we're demonstrating Python function calls, not standards-based interoperability. An audience member could rightly ask: "Why do you need CSAPI if everything runs in one process?"

### 1.3 It Cannot Generalize

If real ODAS hardware produced LOB observations, the embedded localizer would not work — it depends on the simulator's internal state. A standalone localizer that reads from the API works identically whether the data comes from a simulator, real hardware, or a replay engine.

---

## 2. Corrected Architecture

```
┌─────────────────┐                        ┌──────────────────┐
│                  │   POST /observations   │                  │
│   Simulator      │ ──────────────────────▶│                  │
│   (Producer)     │   LOB bearings         │                  │
│                  │   for MA-1, MA-2, MA-3 │                  │
└─────────────────┘                        │   CSAPI Server   │
                                           │   (Oracle VM     │
┌─────────────────┐   GET /observations    │    SensorHub)    │
│                  │ ◀─────────────────────│                  │
│   Localizer      │   Latest LOBs          │                  │
│   (Consumer +    │                        │                  │
│    Producer)     │   POST /observations   │                  │
│                  │ ──────────────────────▶│                  │
└─────────────────┘   Location Estimates    │                  │
                                           └──────────────────┘
┌─────────────────┐                               │
│                  │   GET /observations           │
│   Web App        │ ◀────────────────────────────┘
│   (Consumer)     │   LOBs + Location Estimates
│                  │
└─────────────────┘
```

**Three independent actors. Zero direct coupling. All communication through CSAPI.**

| Actor | Role | Knows About |
|-------|------|-------------|
| Simulator | Producer only | LOB datastream IDs (for POST) |
| Localizer | Consumer + Producer | LOB datastream IDs (for GET), Location Estimate datastream ID (for POST) |
| Web App | Consumer only | All datastream IDs (for GET) |

The localizer discovers its inputs and outputs by querying the server. It has no import path to the simulator, no shared state, no function calls between them. They are **decoupled by the standard**.

---

## 3. Localizer as a Standalone Process

### 3.1 LOB Input Schema (7 fields)

The localizer consumes LOB observations from 3 datastreams. Each LOB observation contains 7 fields:

| # | Field | Type | Description |
|---|-------|------|-------------|
| 1 | `timestamp` | Time | Epoch seconds |
| 2 | `trackId` | Count | Track ID |
| 3 | `bearingTrue` | Quantity (deg) | Bearing from sensor to target, 0–360° |
| 4 | `bearingStdDev` | Quantity (deg) | Bearing uncertainty |
| 5 | `sensorLat` | Quantity (deg) | Sensor latitude |
| 6 | `sensorLon` | Quantity (deg) | Sensor longitude |
| 7 | `classification` | Text | Target classification (e.g. "UAS") |

> **Authoritative schema source:** [`scripts/bootstrap_v4.py` line 536](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L536) in the csapi-explorer repo.

**Current LOB datastream IDs:**

| Node | DS ID | System ID |
|------|-------|-----------|
| AZ-MA-1 | `04c0` | `0420` |
| AZ-MA-2 | `04cg` | `0490` |
| AZ-MA-3 | `04d0` | `049g` |

> These IDs changed from `0420`/`0460`/`049g` after the schema was corrected (DELETE + POST with `classification` field added). The simulator discovers IDs dynamically by `outputName`.

### 3.2 Execution Loop

```python
# localizer.py — independent process
# ─────────────────────────────────────────────────────
# ZERO hardcoded datastream IDs.
# At startup, discover LOB inputs by querying each
# system's datastreams for the matching outputName.
# This is the same pattern the simulator uses
# (see engine.py → find_datastream_id()).
# ─────────────────────────────────────────────────────

# ── Configuration ────────────────────────────────────
SYSTEM_IDS      = ["0420", "0490", "049g"]   # MA-1, MA-2, MA-3
LOB_OUTPUT_NAME = "lob_bearing"              # outputName on the DS
POLL_INTERVAL   = 5                          # seconds — matches simulator tick
MAX_LOB_AGE_S   = 15                         # Δt staleness gate (see §3.3)
RESIDUAL_CAP    = 500                        # metres

# ── Startup: discover LOB datastream IDs ─────────────
def discover_lob_datastreams(system_ids, output_name):
    """Query the server for each system's LOB datastream ID.
       Returns {system_id: ds_id} or raises if any are missing."""
    lob_ds = {}
    for sys_id in system_ids:
        items = GET(f"/systems/{sys_id}/datastreams")["items"]
        match = [ds for ds in items if ds["outputName"] == output_name]
        if not match:
            raise RuntimeError(f"System {sys_id}: no DS with outputName={output_name}")
        lob_ds[sys_id] = match[0]["id"]
    return lob_ds

lob_datastreams = discover_lob_datastreams(SYSTEM_IDS, LOB_OUTPUT_NAME)
#   e.g.  {"0420": "04c0", "0490": "04cg", "049g": "04d0"}

# ── Main loop ────────────────────────────────────────
while running:
    now = time.time()

    # 1. CONSUME: Read latest LOB from each MA node
    #
    #    Portability note: `resultTime=latest` is an OSH Node
    #    convenience parameter.  For strict OGC-API compliance,
    #    the portable equivalent is:
    #        ?resultTime=../{now_iso}&limit=1
    #    which returns the most recent observation up to `now`.
    #    Both return the same single observation.
    lobs = []
    for sys_id, ds_id in lob_datastreams.items():
        obs = GET(f"/datastreams/{ds_id}/observations?resultTime=latest")
        if not obs or already_processed(obs):
            continue

        result = obs["result"]
        obs_time = result["timestamp"]           # epoch seconds

        # 2. STALENESS GATE: reject observations older than MAX_LOB_AGE_S
        #    This prevents stale data from contaminating a fix when a
        #    sensor goes offline or the simulator is paused/stopped.
        if abs(now - obs_time) > MAX_LOB_AGE_S:
            continue                              # stale — skip

        lobs.append({**result, "sys_id": sys_id})

    # 3. CORRELATE: Group by classification
    by_class = group_by(lobs, key=lambda l: l.get("classification", "UNKNOWN"))

    for cls, group in by_class.items():
        # 4. COMPUTE: Triangulate if 2+ LOBs
        if len(group) >= 2:
            estimate = wls_bearing_intersection(group)

            # 5. PRODUCE: Publish result back to the CSAPI server
            if estimate and estimate["residual_m"] <= RESIDUAL_CAP:
                POST(f"/datastreams/{LOCALIZER_DS}/observations", estimate)

    sleep(POLL_INTERVAL)
```

### 3.3 Key Design Properties

| Property | Value | Rationale |
|----------|-------|-----------|
| **Poll interval** | 5 seconds | Matches simulator tick rate and webapp Live Mode refresh |
| **Staleness gate (Δt)** | 15 seconds (`MAX_LOB_AGE_S`) | Rejects any LOB whose `phenomenonTime` is more than 15 s from wall-clock `now`. Prevents stale data from poisoning a fix when a sensor goes offline, the simulator stops, or network lag is extreme. Set to 3× poll interval by default — tight enough to reject dead data, loose enough to tolerate one missed poll cycle. |
| **Correlation window** | 10 seconds | LOBs from the same simulator tick land within ~1-2 s. When grouping LOBs into a fix, only LOBs whose timestamps are within 10 s of each other are eligible. This is separate from the staleness gate — staleness rejects old data absolutely; the correlation window rejects data that is fresh but temporally mismatched relative to other LOBs in the same fix. |
| **Minimum LOBs** | 2 | Need at least 2 bearings for a fix |
| **Residual cap** | 500 m | Rejects near-parallel bearing pairs with divergent intersections |
| **Deduplication** | Track `phenomenonTime` of last-processed LOBs | Avoid re-triangulating stale data |
| **Classification gate** | Group LOBs by `classification` field value | Only fuse same-type detections; classification now in LOB observation data |
| **Dynamic discovery** | DS IDs resolved at startup via `outputName` query | No hardcoded IDs — works unchanged when DS IDs change (e.g. after schema migration). Same pattern as `engine.py → find_datastream_id()`. |
| **`resultTime=latest` portability** | OSH convenience; portable fallback = `resultTime=../{now}&limit=1` | If porting to a non-OSH server, swap the query parameter. Both return the single most-recent observation. |

### 3.4 What the Localizer Does NOT Know

- The simulator's tick rate, route, or internal state
- Whether the data comes from real hardware or a simulator
- The webapp's existence
- How many consumers are reading its output

This is the hallmark of standards-based interoperability: **the localizer is a black-box processing node that communicates exclusively through CSAPI**.

---

## 4. Server Resource Registration

Before the localizer can operate, these CSAPI resources must exist on the server. This is the localizer's **bootstrap** step — run once.

### 4.1 Register the Procedure

```
POST /procedures
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:procedure:lob-wls-triangulation:v1",
    "name": "WLS LOB Triangulation v1",
    "description": "Weighted least-squares bearing-only geolocation. Consumes N≥2 lines of bearing from acoustic sensor nodes, computes optimal intersection point with inverse-variance weighting, and produces a location estimate with CEP50 uncertainty."
  }
}
```

**Note:** This procedure joins the 9 procedures already on the server (see Section 7 below). It describes the *method* — it doesn't execute anything.

### 4.2 Register the System (with typeOf linkage)

```
POST /systems
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:system:fusion:az-string-alpha-localizer",
    "name": "AZ-String-Alpha LOB Triangulator",
    "description": "Software fusion agent. Consumes LOB observations from AZ-MA-1/2/3 via CSAPI GET, computes UAS position via WLS bearing intersection, and publishes location estimates via CSAPI POST.",
    "typeOf": "urn:os4csapi:procedure:lob-wls-triangulation:v1"
  }
}
```

> **`typeOf` linkage:** The `typeOf` property is the SOSA/CSAPI-standard way to declare "this system implements that procedure." SensorHub OSH Node accepts `typeOf` on both POST (create) and PUT (update) — verified 2026-03-03. The value is a procedure UID (URN string); SensorHub resolves it to the internal procedure reference automatically.
>
> All 42 existing systems/subsystems on the server now have `typeOf` linkages (where applicable). See [System_Procedure_Linkage_Migration.md](System_Procedure_Linkage_Migration.md) for the full migration report. Infrastructure subsystems (tripod, comms, power) are intentionally unlinked — they are platforms, not instruments.

### 4.3 Create the Location Estimate DataStream

```
POST /systems/{localizer_system_id}/datastreams
{
  "name": "UAS Location Estimate",
  "outputName": "az_string_alpha_location_estimate",
  "obsFormat": "application/om+json",
  "resultSchema": { ... }
}
```

Schema: 9 fields — timestamp, trackId, estimatedLat, estimatedLon, cep50_m, classification, numContributingLobs, contributingSensors, residual_m. Full schema definition in [LOB_Triangulation_Implementation_Spec.md §2.2](LOB_Triangulation_Implementation_Spec.md).

---

## 5. Deployment Options

The localizer is a lightweight Python process (~200 lines, stdlib-only with `urllib` + `json` + `math`). It can run anywhere:

| Option | Pros | Cons |
|--------|------|------|
| **Local script** (`python localizer.py`) | Zero infra, easy debugging | Must be running on someone's machine |
| **Same Fly.io service** (new endpoint on os4csapi-simulator) | Already deployed, admin console integration | Couples hosting (not logic) with simulator |
| **Separate Fly.io app** | Full independence | Extra app on free tier |
| **Oracle VM** (alongside SensorHub) | Co-located with server, lowest latency | Requires SSH/VM access |
| **Background thread in webapp server** | No extra process | Wrong — webapp should be consumer-only |

**Recommended for demo:** Run as a local script or add a `/localizer/start` endpoint to the existing Fly.io simulator service. The hosting can be shared without coupling the logic — the localizer still reads from and writes to the CSAPI server exclusively.

---

## 6. Demo Narrative Impact

This architecture creates a compelling three-actor demo:

### Act 1: The Sensors Report
Start the simulator. Audience sees LOB bearing lines appear on the map in real time. "These acoustic sensors are publishing bearing observations through the OGC Connected Systems API."

### Act 2: The Fusion Agent Connects
Start the localizer. A new marker appears on the map — the estimated UAS position. "A separate application just connected. It's reading those same LOB observations through the API, computing a position fix, and publishing the result back. It has no direct connection to the sensors."

### Act 3: The Standard Enables It
"Both the sensor data and the fusion output use the same OGC API. The web application you're looking at discovered both automatically. If we replaced the simulated sensors with real ODAS hardware, the localizer and the web app would work identically — nobody needs to change their code."

This is a fundamentally different story than "we built a monolithic simulator that does everything internally." It demonstrates the **value proposition of CSAPI**: independent systems interoperating through a common standard.

---

## 7. Existing Server Procedures (Verified) + typeOf Linkages

Probed `GET /procedures?limit=50` on the live server. Nine procedures exist, all now linked to their implementing systems via `typeOf`:

| ID | UID | Description | Linked Systems |
|----|-----|-------------|---------------|
| `040g` | `urn:x-odas:procedure:pdm-mems-audio-capture` | PDM microphone sampling | 24 (3 micarrays + 21 mics) |
| `0410` | `urn:x-odas:procedure:srp-phat-beamforming` | SRP-PHAT angle-of-arrival | 0* |
| `041g` | `urn:x-odas:procedure:particle-filter-tracking` | Particle filter source tracking | 0* |
| `0420` | `urn:x-odas:procedure:ray-to-ray-triangulation` | Ray-to-ray intersection | 0* |
| `042g` | `urn:x-odas:procedure:odas-config-actuation` | ODAS configuration control | 3 (actuators) |
| `0430` | `urn:os4csapi:procedure:odas:az-ma-1:calibration:v1` | AZ-MA-1 calibration | 0† |
| `043g` | `urn:os4csapi:procedure:odas:az-ma-1:health-monitor:v1` | AZ-MA-1 health monitor | 0† |
| `0440` | `urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1` | AZ-MA-1 processing chain | 6 (3 MA + 3 edges) |
| `044g` | `urn:os4csapi:procedure:odas:az-ma-1:frame-transform:v1` | AZ-MA-1 frame transform | 0† |

\* No dedicated SSL/SST/triangulation subsystems registered yet — these procedures describe pipeline stages internal to the EDGE processor.  
† Calibration, health monitoring, and frame transforms are cross-cutting processes, not primary system functions.

The new `urn:os4csapi:procedure:lob-wls-triangulation:v1` will be the 10th — linked to the localizer system via `typeOf` at bootstrap time.

---

## 8. Relationship to Implementation Spec

Everything in the [LOB_Triangulation_Implementation_Spec.md](LOB_Triangulation_Implementation_Spec.md) has been updated to reflect the corrected architecture and schema:

| Original Spec Section | Status |
|----------------------|--------|
| §1 Current State | ✅ **Updated** — LOB schema now 7 fields (classification added); DS IDs updated to `04c0`/`04cg`/`04d0` |
| §2 Server Resources | ✅ Unchanged (Location Estimate output schema, system registration) |
| §3 Algorithm (WLS) | ✅ Unchanged |
| §4 Correlation Gate | ✅ **Updated** — classification gate now reads from observation data, not hardcoded |
| §5 Execution Model | ✅ **Superseded** — now references this document; standalone model is primary |
| §6 Python Implementation | ✅ **Updated** — §6.3 replaced with standalone localizer loop |
| §7 Bootstrapping | ✅ Unchanged |

---

## 9. Implementation Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `scripts/localizer.py` | Standalone consumer/producer — poll, correlate, triangulate, publish |
| 2 | `scripts/bootstrap_localizer.py` | One-time server registration (procedure, system, datastream) |
| 3 | Simulator service endpoint (optional) | `/localizer/start` and `/localizer/stop` on Fly.io for hosted operation |
| 4 | Admin console integration | Status panel for localizer alongside existing simulator controls |
| 5 | Webapp visualization | Location estimate marker + CEP50 circle on the map |
| 6 | Clear script update | Extend `clear_observations.py` to include the localizer datastream |
