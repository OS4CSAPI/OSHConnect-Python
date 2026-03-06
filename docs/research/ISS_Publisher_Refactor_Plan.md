# ISS Publisher Refactor Plan — Dogfooding OSHConnect-Python

**Date:** 2025-07-06
**Status:** Proposed
**Scope:** Refactor `scripts/iss_publisher.py` in `ogc-csapi-explorer` to use OSHConnect-Python instead of raw HTTP calls
**Repository:** [OS4CSAPI/ogc-csapi-explorer](https://github.com/OS4CSAPI/ogc-csapi-explorer)

---

## 1. Background

The ISS satellite tracking publisher (`scripts/iss_publisher.py`, 425 lines) is a live data publisher that fetches NORAD GP element sets from CelesTrak, propagates them with SGP4, and publishes geodetic positions (lat, lon, alt) as CSAPI observations to the OS4CSAPI OSH server every 30 seconds.

The publisher was built rapidly during the ISS satellite tracking feature sprint and uses **raw `urllib.request` HTTP calls** throughout — hand-rolling auth headers, TLS context, JSON serialization, error handling, and URL construction. It does not use OSHConnect-Python at all.

**The entire reason for building the ISS publisher was to dogfood the CSAPI ecosystem.** Using OSHConnect-Python for this publisher would close the loop: the library that exists to make CSAPI integration easier would itself be validated by a real, continuously-running production workload.

---

## 2. Current Architecture

### What the publisher does today

| Concern | Current Implementation | Lines |
|---|---|---|
| **Server connection** | Hardcoded `BASE_URL`, manual `Basic` auth header, custom `ssl.SSLContext` with verification disabled | ~20 |
| **HTTP transport** | `urllib.request.Request` + `urlopen()` with manual JSON encode/decode, error parsing | ~40 |
| **API calls** | `api_post()`, `api_put()`, `api_get()` wrappers that build URLs by string concatenation | ~15 |
| **CelesTrak TLE fetch** | `urllib.request` to CelesTrak OMM JSON endpoint, parse into `sgp4.Satrec` | ~50 |
| **SGP4 propagation** | `Satrec.sgp4()` → ECI → ECEF → geodetic (custom math) | ~100 |
| **Observation building** | Hand-built `om+json` dict with `phenomenonTime`, `resultTime`, `result` | ~15 |
| **Observation publishing** | `api_post(f"datastreams/{DATASTREAM_ID}/observations", obs)` | ~5 |
| **Main loop** | `while True` with tick-aligned sleep, TLE refresh check, error recovery, stats | ~80 |
| **CLI** | `argparse` for `--interval`, `--dry-run`, `--once`, `--tle-refresh` | ~25 |

### Server resources (pre-provisioned)

| Resource | ID | Description |
|---|---|---|
| System | `04ng` | ISS Tracker |
| DataStream | `04fg` | ISS Position |
| Procedure | `045g` | ISS Tracking Procedure |
| Root Deployment | `048g` | ISS Tracking Deployment |
| Leaf Deployment | `0490` | ISS Instance |

### Dependencies

- Python 3.10+
- `sgp4` (pip install sgp4)
- No other third-party packages — stdlib only (`urllib`, `ssl`, `json`, `math`, `time`, `argparse`)

### Deployment

- Oracle Cloud ARM VM (`129.80.248.53`)
- systemd service: `iss-publisher.service`
- Runs as `ubuntu` user, auto-restarts on failure
- Free-tier persistent compute — no cost, always on

---

## 3. What OSHConnect-Python Replaces

### 3.1 Server Connection & Auth

**Before (raw):**
```python
BASE_URL = "https://os4csapi-osh.duckdns.org/sensorhub/api"
AUTH_USER = "os4csapi"
AUTH_PASS = "ogc134mm"
_AUTH_HEADER = "Basic " + base64.b64encode(f"{AUTH_USER}:{AUTH_PASS}".encode()).decode()
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE
```

**After (OSHConnect-Python):**
```python
from oshconnect import OSHConnect, Node

app = OSHConnect("iss-publisher")
node = Node(
    protocol="https",
    address="os4csapi-osh.duckdns.org",
    port=443,
    username="os4csapi",
    password="ogc134mm",
    server_root="sensorhub",
)
app.add_node(node)
```

**What's eliminated:** Manual base64 encoding, SSL context management, URL construction.

### 3.2 HTTP Transport & API Helpers

**Before (raw):** 40+ lines of `_request()` with manual `Request` construction, `urlopen()`, `HTTPError` parsing, JSON decode, Location header extraction.

**After:** Entirely handled by `Node.get_api_helper()` internally. All CRUD operations go through `APIHelper.create_resource()`, `retrieve_resource()`, etc.

**What's eliminated:** The entire `_request()`, `api_post()`, `api_put()`, `api_get()` block (~55 lines).

### 3.3 System & DataStream Discovery

**Before (raw):** Hardcoded resource IDs (`SYSTEM_ID = "04ng"`, `DATASTREAM_ID = "04fg"`), no discovery.

**After:**
```python
app.discover_systems()
system = app.find_system("urn:osh:sensor:iss-tracker")  # discover by UID
system.discover_datastreams()
ds = system.datastreams[0]  # or find by name
```

**Functional benefit:** The publisher no longer needs hardcoded resource IDs. If the server is rebuilt and IDs change, discovery-by-UID still works. This is one of the most important improvements.

### 3.4 Observation Publishing

**Before (raw):**
```python
obs = {
    "phenomenonTime": iso,
    "resultTime": iso,
    "result": {"timestamp": ..., "lat_deg": ..., "lon_deg": ..., "alt_km": ...},
}
api_post(f"datastreams/{DATASTREAM_ID}/observations", obs)
```

**After (OSHConnect-Python, HTTP):**
```python
ds.insert_observation_dict({
    "phenomenonTime": iso,
    "resultTime": iso,
    "result": {"timestamp": ..., "lat_deg": ..., "lon_deg": ..., "alt_km": ...},
})
```

**After (OSHConnect-Python, MQTT — optional upgrade):**
```python
ds.insert({
    "resultTime": iso,
    "result": {"timestamp": ..., "lat_deg": ..., "lon_deg": ..., "alt_km": ...},
})
```

**Functional benefit:** MQTT publishing is available as a transport option, which would deliver observations to subscribers with lower latency than HTTP POST. This is particularly relevant since the webapp polls for observations — with MQTT, future real-time subscriptions become possible.

---

## 4. What OSHConnect-Python Does NOT Replace

These concerns are ISS-publisher-specific and remain as-is:

| Concern | Why it stays |
|---|---|
| **CelesTrak TLE fetch** | Domain-specific — fetches NORAD OMM data, not a CSAPI operation |
| **SGP4 propagation** | Orbital mechanics (sgp4 library + custom ECI→geodetic math) |
| **Main loop with tick-aligned sleep** | Application-level scheduling |
| **CLI argument parsing** | Application-level UX |
| **Observation result structure** | Schema-specific `{timestamp, lat_deg, lon_deg, alt_km}` |

The `sgp4` dependency and ~150 lines of orbital mechanics code are completely orthogonal to the CSAPI transport layer and should remain untouched.

---

## 5. Functional Benefits

### 5.1 Eliminates Hardcoded Resource IDs
The current publisher hardcodes `SYSTEM_ID = "04ng"` and `DATASTREAM_ID = "04fg"`. If the server database is rebuilt, these IDs will change and the publisher silently fails. With OSHConnect-Python, the publisher discovers resources by **UID** (`urn:osh:sensor:iss-tracker`), which is stable across server rebuilds.

### 5.2 Structured Error Handling
The current `_request()` function does basic `HTTPError` catch-and-reraise. OSHConnect-Python's `APIHelper` provides structured error handling with proper status code interpretation and retry semantics.

### 5.3 MQTT Transport Option
The library supports MQTT publishing via `datastream.insert()`. This is a lower-latency transport path that could benefit real-time subscribers. The current HTTP-only approach means 30s polling cycles. MQTT would deliver observations to any subscriber in near-real-time. This is not required for the initial refactor, but becomes trivially available.

### 5.4 Library Validation (Dogfooding)
A continuously-running publisher exercising `Node`, `System`, `Datastream`, and `insert_observation_dict()` in production provides ongoing validation of the library's reliability. Any regressions in OSHConnect-Python will surface through ISS publisher failures.

### 5.5 Reduced Boilerplate
~55 lines of HTTP transport code and ~20 lines of auth/TLS setup are replaced by a 6-line `Node` constructor. The refactored publisher should be approximately **350 lines** (down from 425), with the reduction entirely in transport plumbing.

### 5.6 Future-Proofing
If we later add features like:
- Automatic system provisioning (create system + datastream if they don't exist)
- Control stream for commanding the publisher (change cadence, pause, etc.)
- Multi-datastream publishing (e.g., separate velocity or orbital elements stream)

These are all first-class operations in OSHConnect-Python and would require no additional HTTP plumbing.

---

## 6. Deployment Approach

### Requirements
- **Free:** No additional cost beyond current Oracle Cloud free-tier VM
- **Stable:** Same reliability as current systemd service
- **Persistent:** Auto-starts on boot, auto-restarts on failure

### Plan: Same VM, Same systemd, New Dependency

The deployment model does not change. The refactored publisher runs on the same Oracle Cloud VM under the same systemd unit.

**Changes required:**

1. **Install OSHConnect-Python** on the Oracle VM:
   ```bash
   pip install oshconnect
   # or, if installing from the repo directly:
   pip install git+https://github.com/OS4CSAPI/OSHConnect-Python.git
   ```

2. **Update `iss-publisher.service`** — no changes needed to the unit file itself, since the Python executable and script path remain the same.

3. **Verify `sgp4` compatibility** — sgp4 is pure Python, no conflicts with OSHConnect-Python's deps (pydantic, requests, aiohttp, etc.).

4. **Python version** — OSHConnect-Python requires Python >= 3.12. The Oracle VM currently runs Python 3.10. **This is the only deployment friction point** — Python must be upgraded to 3.12+ before the refactor can be deployed.

### Deployment Steps

| Step | Command | Risk |
|---|---|---|
| 1. Upgrade Python to 3.12+ | `sudo apt install python3.12` or build from source | Low (free-tier VM, no other Python services) |
| 2. Create venv | `python3.12 -m venv /opt/iss-publisher/venv` | None |
| 3. Install deps | `venv/bin/pip install sgp4 oshconnect` | None |
| 4. Test dry-run | `venv/bin/python iss_publisher.py --dry-run --once` | None |
| 5. Stop old service | `sudo systemctl stop iss-publisher` | Brief outage (~1 min) |
| 6. Update ExecStart path | Point to new venv Python | None |
| 7. Start new service | `sudo systemctl start iss-publisher` | None |
| 8. Verify observations | Check webapp map for ISS marker movement | None |

**Total expected downtime:** Under 2 minutes.

### Rollback Plan

The old `iss_publisher.py` remains in git history. If the refactored version has issues:
1. `git checkout HEAD~1 -- scripts/iss_publisher.py`
2. `sudo systemctl restart iss-publisher`

---

## 7. Migration Steps

### Phase 1: Refactor Transport Layer (Core)

Replace raw HTTP with OSHConnect-Python, keeping the same behavior:

1. **Replace imports**: Remove `urllib`, `ssl`, `base64`. Add `from oshconnect import OSHConnect, Node`.
2. **Replace config block**: Replace `BASE_URL`, `AUTH_*`, `_ssl_ctx` with `Node()` constructor.
3. **Add discovery**: Replace hardcoded `SYSTEM_ID`/`DATASTREAM_ID` with `discover_systems()` + `find_system()` + `discover_datastreams()`.
4. **Replace `api_post()`**: Use `ds.insert_observation_dict()` for observation publishing.
5. **Remove `_request()`, `api_post()`, `api_put()`, `api_get()`**: These are fully replaced.
6. **Keep everything else**: CelesTrak fetch, SGP4 propagation, main loop, CLI, observation builder — all unchanged.

### Phase 2: Validate (Required)

1. Run `--dry-run --once` to verify propagation math is unaffected.
2. Run `--once` to verify a single observation posts successfully.
3. Run for 5 minutes with `--interval 30` and verify observations appear on the webapp.
4. Deploy to Oracle VM and monitor for 1 hour.

### Phase 3: Optional Enhancements (Future)

These are not part of the initial refactor but become easy afterward:

- **MQTT publishing**: Switch from `insert_observation_dict()` (HTTP) to `insert()` (MQTT) for lower latency.
- **Auto-provisioning**: If system/datastream don't exist, create them via `create_and_insert_system()` + `add_insert_datastream()`.
- **Health endpoint**: Add a simple HTTP endpoint that reports publisher status (for monitoring).
- **Control stream**: Accept commands (change cadence, pause/resume) via CSAPI control stream.

---

## 8. Estimated Refactored Code Structure

```python
#!/usr/bin/env python3
"""
iss_publisher.py — Live ISS position publisher for OS4CSAPI.
Refactored to use OSHConnect-Python for CSAPI transport.
"""

import argparse, json, math, sys, time, traceback
from datetime import datetime, timezone
from urllib.request import Request, urlopen  # retained for CelesTrak only

from sgp4.api import Satrec, WGS72
from oshconnect import OSHConnect, Node

# ── Config ──────────────────────────────────────────────────────
SERVER_ADDRESS = "os4csapi-osh.duckdns.org"
SERVER_PORT    = 443
SERVER_ROOT    = "sensorhub"
AUTH_USER      = "os4csapi"
AUTH_PASS      = "ogc134mm"
SYSTEM_UID     = "urn:osh:sensor:iss-tracker"

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON"

# ── OSHConnect Setup ────────────────────────────────────────────
def connect_and_discover():
    """Connect to OSH server and discover ISS system + datastream."""
    app = OSHConnect("iss-publisher")
    node = Node(
        protocol="https", address=SERVER_ADDRESS, port=SERVER_PORT,
        username=AUTH_USER, password=AUTH_PASS, server_root=SERVER_ROOT,
    )
    app.add_node(node)
    app.discover_systems()
    system = app.find_system(SYSTEM_UID)
    if not system:
        raise RuntimeError(f"System '{SYSTEM_UID}' not found on server")
    system.discover_datastreams()
    datastreams = system.datastreams  # or equivalent accessor
    if not datastreams:
        raise RuntimeError(f"No datastreams found for system '{SYSTEM_UID}'")
    return app, node, system, datastreams[0]

# ── CelesTrak + SGP4 (unchanged) ───────────────────────────────
# ... fetch_tle_from_celestrak(), get_satrec(),
#     propagate_to_geodetic(), eci_to_geodetic(), etc.
#     ~150 lines, completely untouched

# ── Observation builder (unchanged) ────────────────────────────
def build_observation(lat, lon, alt_km, now):
    iso = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    return {
        "phenomenonTime": iso, "resultTime": iso,
        "result": {"timestamp": now.timestamp(),
                   "lat_deg": round(lat, 6),
                   "lon_deg": round(lon, 6),
                   "alt_km": round(alt_km, 3)},
    }

# ── Main loop ──────────────────────────────────────────────────
def run(*, interval=30.0, dry_run=False, once=False, tle_refresh=3600.0):
    app, node, system, ds = connect_and_discover()
    sat = fetch_tle_from_celestrak()
    # ... same loop as before, but publish with:
    #     ds.insert_observation_dict(obs)
    # instead of:
    #     api_post(f"datastreams/{DATASTREAM_ID}/observations", obs)
```

---

## 9. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Python 3.12 upgrade breaks sgp4 | Low | sgp4 supports 3.12; test in venv first |
| OSHConnect-Python alpha instability | Medium | Pin version; keep raw fallback in git history |
| MQTT port not exposed on server | Low | Initial refactor uses HTTP only (`insert_observation_dict`) |
| Library import adds startup latency | Low | One-time cost (~2s); negligible for a 30s-cadence publisher |
| `discover_systems()` fails on server restart | Medium | Add retry loop with backoff at startup |

---

## 10. Success Criteria

- [ ] Refactored publisher runs for 24h on Oracle VM with zero missed observations
- [ ] No hardcoded resource IDs remain (all discovery-based)
- [ ] `--dry-run` and `--once` modes work identically to the current version
- [ ] Publisher auto-recovers from server restarts within 2 minutes
- [ ] Line count reduced by at least 50 lines (transport boilerplate removed)
- [ ] OSHConnect-Python exercised in a real, continuous production workload

---

## 11. Summary

The ISS publisher is the ideal candidate for OSHConnect-Python dogfooding: it's a simple, single-stream publisher with a clear CSAPI surface (connect → discover → publish observations). The refactor replaces ~75 lines of raw HTTP plumbing with ~10 lines of library calls while adding meaningful functional improvements (discovery-based resource resolution, structured error handling, MQTT transport option).

The deployment model is unchanged — same Oracle VM, same systemd service, same free-tier compute. The only friction point is upgrading Python from 3.10 to 3.12+ on the VM.

This refactor transforms the ISS publisher from an ad-hoc HTTP script into a proper validation workload for the OSHConnect-Python library, fulfilling the original dogfooding intent.
