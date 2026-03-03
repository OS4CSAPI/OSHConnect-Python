# Data Simulator Portability Analysis

**Date:** 2026-03-03  
**Author:** GitHub Copilot (session with S. Bolling)  
**Status:** Analysis  
**Component:** `scripts/simulate_scenario.py`  

---

## Question

Would our data simulator (`simulate_scenario.py`) work with another OGC API — Connected Systems server, or is it coupled to OpenSensorHub (OSH)?

## Verdict

**~90% portable.** The simulator speaks pure CSAPI. The coupling is to **our data model** (the ODAS system hierarchy and datastream schemas), not to OSH itself. With a different conformant server bootstrapped with the same schemas, only the base URL and credentials would need to change.

---

## What's Standard CSAPI (Works With Any Conformant Server)

| Operation | Standard Basis | Used In Simulator |
|-----------|---------------|-------------------|
| `GET /systems?uid=...` | Part 1 — System discovery by UID | `find_system_id()` |
| `GET /datastreams?system=...` | Part 1 — Datastream discovery by parent system | `find_datastream_id()` |
| `POST /datastreams/{id}/observations` | Part 2 — Observation creation | All `build_*_observation()` functions |
| `phenomenonTime` / `resultTime` / `result` structure | O&M / SWE Common | Every observation payload |
| HTTP Basic Auth | Generic HTTP | Session auth header |

All API interactions use standard OGC API — Connected Systems endpoints. Zero use of:
- OSH admin API
- SOS legacy endpoints
- OSH proprietary extensions
- OSH-specific headers or content negotiation

## What's Coupled to Our Deployment (Not OSH-Specific)

### 1. System UIDs (Hardcoded)
```python
NODES = [
    {"uid": "urn:os4csapi:system:odas:az-ma-1", ...},
    {"uid": "urn:os4csapi:system:odas:az-ma-2", ...},
    {"uid": "urn:os4csapi:system:odas:az-ma-3", ...},
]
```
The simulator discovers system IDs at runtime by querying these UIDs. Another server would need the same systems registered, or the UIDs would need to be parameterized.

### 2. Datastream Name Matching (Convention-Based)
```python
find_datastream_id("az_ma_1_lob")
find_datastream_id("az_ma_2_track_updates")
```
Discovery searches datastreams by naming convention. Different deployments with different naming would fail the lookup unless the mapping is configurable.

### 3. Observation Result Payloads (Schema-Coupled)
```json
{
  "bearingTrue": 241.7,
  "sensorLat": 31.649,
  "sensorLon": -110.276,
  "elevation": 0.0
}
```
The `result` fields (`bearingTrue`, `sensorLat`, `sensorLon`, `classLabel`, `classConfidence`, `activity`, etc.) match the SWE Common DataRecord schemas defined in `bootstrap_v4.py`. Any server hosting datastreams with **the same schemas** would accept these observations. A server with different schemas would reject them or silently discard fields.

### 4. Base-32 Resource IDs (Dynamic)
The OSH server returns base-32 encoded IDs (`0420`, `042g`, `04bg`, etc.). These are **discovered at runtime**, not hardcoded — so this is not a portability issue. Any server's ID format (numeric, UUID, etc.) would work since the simulator uses the discovered values.

## The Simulator + Bootstrap Relationship

The simulator and `bootstrap_v4.py` are a **matched pair**:

```
bootstrap_v4.py          simulate_scenario.py
─────────────────        ─────────────────────
Defines systems    →     Discovers systems by UID
Defines datastreams →    Discovers datastreams by name
Defines schemas    →     Publishes observations matching those schemas
Creates on server  →     Writes to server
```

Together they form a complete client-side CSAPI workflow:
1. **Bootstrap** creates the data model (systems, datastreams, schemas)
2. **Simulator** produces observations conforming to that data model

This pair would work on any Part 1 + Part 2 conformant server (e.g., 52°North, Frost Server, SensorThings-backed implementations) given that server correctly implements the `POST /datastreams/{id}/observations` endpoint.

## Portability Improvements (Future)

To make the simulator fully server-agnostic:

| Item | Effort | Impact |
|------|--------|--------|
| Externalize system UIDs to config file | Low | Decouple from specific deployment |
| Externalize datastream name patterns | Low | Support different naming conventions |
| Parameterize server URL + auth method | Low | Already partially done (CLI `--server`) |
| Support OAuth2 / API key auth | Medium | Required for non-Basic-Auth servers |
| Externalize result schemas to templates | Medium | Support arbitrary datastream definitions |
| Add `--purge-before-run` flag | Low | Clean old observations before fresh run |

The first three items would take ~30 minutes. The full list would make the simulator a general-purpose CSAPI observation publisher.

## Tested Against

| Server | Version | Status |
|--------|---------|--------|
| OpenSensorHub (OSH) | Node API v2.3 | ✅ Working — primary test target |
| 52°North STA | — | Not tested |
| Frost Server | — | Not tested |
| Other CSAPI impl. | — | Not tested |

## Conclusion

The simulator is architecturally portable. It speaks CSAPI, not OSH. The coupling is to the **data model** (system UIDs, datastream names, observation schemas) which is deployment-specific, not implementation-specific. Running `bootstrap_v4.py` followed by `simulate_scenario.py` against any conformant server should work with only URL/credential changes.

This is a meaningful finding for the OS4CSAPI project: it validates that the tooling we're building is interoperable in principle, not just against a single server implementation.
