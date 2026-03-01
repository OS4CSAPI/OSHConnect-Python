# Deployed-System Links Investigation Report

**Date:** 2025-07-22  
**Branch:** `scenario/v3.0-rebuild`  
**Author:** CSAPI Explorer / OS4CSAPI  
**Status:** CONFIRMED FINDING — Spec-Implementation Gap

---

## Executive Summary

During the v3.0 Part 1 bootstrap rebuild, we discovered that **deployed-system link associations** (the mechanism that relates Systems to Deployments) **cannot be created** on either of our OSH SensorHub servers. Cross-server testing proved this is **not a server configuration issue** — it is a gap between the OGC Connected Systems API specification and the OSH SensorHub implementation.

**Critical finding:** The v2.3 bootstrap had this same problem. Analysis of the v2.3 `id_map.json` reveals **155+ successful creates but ZERO `LINK-*` entries** — the 7 deployed-system link operations in v2.3 silently failed.

**Root cause:** The v2.3 and initial v3.0 scripts attempted to POST to `/deployments/{id}/deployedSystems`, but the OGC CSAPI Part 1 spec **does not define a POST endpoint** at that path. The `deployedSystems` association is specified as a property (`deployedSystems@link`) inside the Deployment GeoJSON body itself — it should be set when creating or updating the deployment, not via a separate sub-endpoint.

---

## Table of Contents

1. [Background — v3.0 Bootstrap Work](#1-background--v30-bootstrap-work)
2. [The Problem — deployedSystems Endpoint Failure](#2-the-problem--deployedsystems-endpoint-failure)
3. [Investigation — Was v2.3 Affected?](#3-investigation--was-v23-affected)
4. [Investigation — Server Configuration?](#4-investigation--server-configuration)
5. [Investigation — OGC CSAPI Spec Analysis](#5-investigation--ogc-csapi-spec-analysis)
6. [Root Cause Analysis](#6-root-cause-analysis)
7. [Correct Approach](#7-correct-approach)
8. [Recommendations](#8-recommendations)
9. [Appendix — Raw Test Results](#9-appendix--raw-test-results)

---

## 1. Background — v3.0 Bootstrap Work

### What Was Done

Built `scripts/bootstrap_v3.py` (539 lines) to populate Oracle OSH SensorHub with v3.0 Part 1 scenario pack resources. The script handles 4 phases:

| Phase | Resource Type          | Count | Status        |
|-------|------------------------|-------|---------------|
| 1     | Deployments (hierarchy)| 6     | ✅ All created |
| 2     | Systems                | 3     | ✅ All created |
| 3     | Deployed-system links  | 3     | ❌ DEFERRED   |
| 4     | SENREP datastream      | 1     | ✅ Created     |

### Deployment Hierarchy Created

```
ICO (040g) ← top-level
├── RSO (040h)
│   └── SSO / SET (040i)
│       ├── SNET / Mon Site (040j)
│       ├── SFIELD (040k)
│       └── STRING (040l)
```

All 6 deployments use flat POST to `/deployments` with `partOf@link` establishing parent-child relationships. This was itself a fix — the initial attempt used nested POST to `/deployments/{parentId}/deployments` which returned HTTP 400.

### Systems Created

| System | UID | Purpose |
|--------|-----|---------|
| SET-A  | `urn:x-ogc:040g:systems:SET-A` | Sensor Employment Team |
| MON-NODE-1 | `urn:x-ogc:040g:systems:MON-NODE-1` | Monitoring Node |
| RELAY-1 | `urn:x-ogc:040g:systems:RELAY-1` | Relay Node |

### Bootstrap Results (Oracle)

```
Summary: 10 created, 0 failed
Deployed-system links DEFERRED (3 associations recorded in id_map)
```

---

## 2. The Problem — deployedSystems Endpoint Failure

### Symptom

When attempting to create deployed-system associations by POSTing to  
`/deployments/{deployment_id}/deployedSystems`, both servers return HTTP 400:

```json
{"error": "Invalid resource name: 'deployedSystems'"}
```

### What We Tried

| Endpoint Pattern | Method | Result |
|-----------------|--------|--------|
| `/deployments/{id}/deployedSystems` | GET | 400 — "Invalid resource name" |
| `/deployments/{id}/deployedSystems` | POST | 400 — "Invalid resource name" |
| `/deployments/{id}/members` | GET | 200 — empty collection |
| `/deployments/{id}/members` | POST | 400 — "Missing 'type' property" |
| `/deployments/{id}/subdeployments` | GET | 200 — returns child deployments |
| `/deployments/{id}/systems` | GET | 400 — "Invalid resource name" |

POSTing a full system GeoJSON to `/members` returns 201, but creates a **new deployment resource** (a duplicate) rather than an association. This is incorrect behavior for our use case.

### Payload Tested (v3.0)

```json
{
  "system@link": {
    "href": "urn:x-ogc:040g:systems:SET-A",
    "title": "SET-A"
  },
  "configuration": { "setValues": [] }
}
```

Also tested with `system` (no `@link`), with and without `configuration`, and various other payload shapes — all return 400.

---

## 3. Investigation — Was v2.3 Affected?

### Yes. v2.3 had the exact same failure.

**Evidence:** The v2.3 `id_map.json` (produced by `scripts/bootstrap.py`) contains **155+ entries** representing all successfully created resources — but **zero `LINK-*` entries**. The v2.3 bootstrap attempted to create 7 deployed-system links. None succeeded.

### v2.3 Code (bootstrap.py, lines 390-420)

```python
def create_deployed_system_links(self):
    for filename in sorted(os.listdir(ds_dir)):
        # ...
        endpoint = f"deployments/{dep_server_id}/deployedSystems"
        self.post_resource(endpoint, data, "application/json", filename)
```

The v2.3 script used the **exact same endpoint pattern**: `/deployments/{id}/deployedSystems`

### v2.3 Payload Format

The v2.3 payloads (e.g., `AZ-DEP-AOI-001__AZ-MA-1.json`) were more detailed, including SWE-typed configuration values:

```json
{
  "system": { "href": "urn:x-ogc:040g:systems:az-ma-1", "title": "AZ-MA-1" },
  "description": "Deployment of AZ-MA-1 to AOI-001",
  "configuration": {
    "setValues": [
      { "type": "Quantity", "definition": "...", "label": "...", "uom": {...}, "value": 31.555 },
      { "type": "Count",   "definition": "...", "label": "...", "value": 5 }
    ]
  }
}
```

Even with this richer payload, the endpoint returned 400. **The endpoint itself does not exist on the server.**

### Conclusion

The deployed-system link feature has **never worked** on either server. The v2.3 bootstrap's error handling allowed execution to continue past these failures, making it appear as though the script completed successfully. The failures were silent.

---

## 4. Investigation — Server Configuration?

### No. Both servers exhibit identical behavior.

We tested both servers with the same endpoint probes:

| Server | Endpoint | GET | POST |
|--------|----------|-----|------|
| **Oracle** (`os4csapi-osh.duckdns.org`) | `/deployments/{id}/deployedSystems` | 400 | 400 |
| **Oracle** | `/deployments/{id}/members` | 200 (empty) | 400* |
| **Oracle** | `/deployments/{id}/subdeployments` | 200 (children) | — |
| **DigitalOcean** (`45.55.99.236:8080`) | `/deployments/{id}/deployedSystems` | 400 | 400 |
| **DigitalOcean** | `/deployments/{id}/members` | 200 (empty) | 400* |
| **DigitalOcean** | `/deployments/{id}/subdeployments` | 200 (children) | — |

*POST to `/members` with system link payload → `"Missing 'type' property in JSON object @ $.system"`

Both servers run the same OSH SensorHub implementation. The behavior is **identical** across both, confirming this is an implementation-level gap, not a deployment configuration issue.

---

## 5. Investigation — OGC CSAPI Spec Analysis

### What the Spec Says

**OGC API — Connected Systems — Part 1: Feature Resources** (OGC 23-001, v1.0, published 2025-07-16)

#### Deployment Associations (Clause 11.2.2, Table 11)

| Association | SOSA/SSN Mapping | Description | Cardinality |
|-------------|------------------|-------------|-------------|
| `deployedSystems` | `sosa:deployedSystem` | The list of Systems deployed during the Deployment, if any. | A list of System resources. **Required.** |
| `subdeployments` | — | The list of subdeployments that are part of the Deployment, if any. | A list of Deployment resources. **Required.** |

The `deployedSystems` association is a **required** association on Deployment resources.

#### GeoJSON Encoding (Clause 19.1.6, Table 43)

| Association | GeoJSON Mapping | Notes |
|-------------|----------------|-------|
| `deployedSystems` | `properties/deployedSystems@link` | **Value is a JSON Array of links to System resources.** |

> *"When inserting or modifying a link to a system stored locally, the link url (href property) shall be set to the uniqueID of the system to be linked."*

#### Spec Example (Deployment GeoJSON)

```json
{
  "type": "Feature",
  "properties": {
    "uid": "urn:x-ogc:deployments:D001",
    "name": "Saildrone - 2017 Arctic Mission",
    "deployedSystems@link": [
      {
        "href": "https://data.example.org/api/systems/41548?f=sml",
        "uid": "urn:x-saildrone:sensors:temp01",
        "title": "Air Temperature Sensor"
      },
      {
        "href": "https://data.example.org/api/systems/36584...",
        "uid": "...",
        "title": "..."
      }
    ]
  }
}
```

#### Create/Replace/Delete (Clause 17)

The transactional endpoints defined in the spec are:

| Resource | CREATE | REPLACE/DELETE |
|----------|--------|----------------|
| Systems | `POST {api_root}/systems` | `PUT/DELETE {api_root}/systems/{id}` |
| **Subsystems** | `POST {api_root}/systems/{parentId}/subsystems` | (at canonical URL) |
| Deployments | `POST {api_root}/deployments` | `PUT/DELETE {api_root}/deployments/{id}` |
| **Subdeployments** | `POST {api_root}/deployments/{parentId}/subdeployments` | (at canonical URL) |
| Procedures | `POST {api_root}/procedures` | `PUT/DELETE {api_root}/procedures/{id}` |
| Sampling Features | `POST {api_root}/systems/{sysId}/samplingFeatures` | `PUT/DELETE {api_root}/samplingFeatures/{id}` |

**There is NO `POST {api_root}/deployments/{id}/deployedSystems` endpoint defined in the spec.**

#### However, the conformance tests DO reference the endpoint for reading:

> Conformance test `/conf/advanced-filtering/deployment-by-system`:  
> *"Retrieve all deployed systems by issuing an HTTP GET request at `{deploymentCanonicalUrl}/deployedSystems?recursive=true`"*

This means `GET /deployments/{id}/deployedSystems` is expected to work as a **read-only** endpoint — but no transactional (POST) operation is defined for it.

---

## 6. Root Cause Analysis

### The Association Model

The OGC CSAPI spec treats `deployedSystems` as a **property of the Deployment resource itself**, not as a separately-managed sub-resource. In GeoJSON encoding, deployed system links are carried inside the deployment's `properties` object as `deployedSystems@link`.

### How It Should Work

```
┌──────────────────────────────────────────────┐
│  Deployment GeoJSON                          │
│  {                                           │
│    "properties": {                           │
│      "uid": "...",                           │
│      "name": "SSO / SET",                   │
│      "deployedSystems@link": [               │  ← SET HERE
│        {                                     │
│          "href": "urn:...:SET-A",            │
│          "title": "SET-A"                    │
│        }                                     │
│      ]                                       │
│    }                                         │
│  }                                           │
└──────────────────────────────────────────────┘
```

### What Both v2.3 and v3.0 Did Wrong

Both scripts attempted to **POST** a separate link resource to a sub-endpoint (`/deployments/{id}/deployedSystems`) that:

1. **Is not defined as a transactional endpoint** by the OGC CSAPI spec (Clause 17)
2. **Is not implemented** by OSH SensorHub at all (returns "Invalid resource name")

### Three Contributing Factors

| Factor | Description |
|--------|-------------|
| **Spec design** | The `deployedSystems` association is embedded in the deployment body, not managed via a separate endpoint. The spec does not define a POST operation at `/deployments/{id}/deployedSystems`. |
| **OSH implementation** | SensorHub does not expose `deployedSystems` as a sub-resource endpoint at all — not even for GET operations. Only `subdeployments` and `members` are implemented. |
| **Script design (v2.3/v3.0)** | Both bootstrap scripts treated deployed-system links as a separate POST-able resource, following the pattern used by subsystems and subdeployments. This pattern does not apply to deployed-system associations per the spec. |

---

## 7. Correct Approach

Based on the spec analysis, the correct approach to associate systems with deployments is:

### Option A: Include `deployedSystems@link` at Creation Time

When creating a deployment, include the `deployedSystems@link` array in the GeoJSON properties:

```json
{
  "type": "Feature",
  "properties": {
    "uid": "urn:x-ogc:040g:deployments:SSO-SET",
    "name": "SSO / SET",
    "featureType": "http://www.w3.org/ns/sosa/Deployment",
    "validTime": ["2025-01-01T00:00:00Z", ".."],
    "deployedSystems@link": [
      {
        "href": "urn:x-ogc:040g:systems:SET-A",
        "title": "Sensor Employment Team A"
      }
    ]
  },
  "geometry": { ... }
}
```

**Challenge:** Systems must be created before the deployment that references them, which may require reordering bootstrap phases. Alternatively, reference systems by UID (which is known ahead of time from the scenario pack).

### Option B: Update Deployment After Creating Systems

1. Create deployments (Phase 1)
2. Create systems (Phase 2)
3. PUT/PATCH to `/deployments/{id}` with `deployedSystems@link` populated (Phase 3)

This requires knowing the system UIDs or server IDs to construct the links.

### Option C: Include in Deployment and Let Server Resolve by UID

Per the spec footnote: *"When inserting or modifying a link to a system stored locally, the link url (href property) shall be set to the uniqueID of the system to be linked."*

This means we can use system UIDs in the href, and the server should resolve them. If systems are created first, the server should accept:

```json
"deployedSystems@link": [
  { "href": "urn:x-ogc:040g:systems:SET-A", "title": "SET-A" }
]
```

### Recommended Approach

**Option C** (via PUT update) is recommended:
1. Create deployments (current Phase 1) — already working
2. Create systems (current Phase 2) — already working
3. For each deployment-system association, PUT the deployment with `deployedSystems@link` populated, using system UIDs as href values

### ⚠️ Caveat

This approach has not been tested against OSH SensorHub yet. It is possible that the SensorHub implementation does not process `deployedSystems@link` in the deployment body. If the server strips or ignores this property, we will need to file a bug report with the OSH SensorHub project.

---

## 8. Recommendations

### Immediate Actions

1. **Update `bootstrap_v3.py`** to attempt Option C:
   - Reorder: Create systems first, then deployments with `deployedSystems@link` included
   - Or: Create deployments, then systems, then PUT-update deployments with `deployedSystems@link`
   - Test both approaches and document results

2. **Add explicit error reporting** for deployed-system link operations. The v2.3 silent failure pattern must not be repeated.

### If Option C Fails (Server Doesn't Process the Property)

3. **File an issue** on the [opensensorhub/osh-core](https://github.com/opensensorhub/osh-core) repository:
   - Title: "deployedSystems association not supported on Deployment resources"
   - Reference OGC 23-001 Clause 11.2.2 Table 11, Clause 19.1.6 Table 43
   - Note that `GET /deployments/{id}/deployedSystems` returns 400 (spec conformance test A.6 expects this to work)
   - Note that `deployedSystems@link` in deployment body may not be persisted

4. **Check osh-core source** for `deployedSystems` handling to understand implementation priority.

### Documentation

5. **Update v3.0 scenario pack README** to document the deployed-system association limitation.
6. This report should be referenced during Part 2 rebuild (datastreams and controlstreams may have similar association patterns).

---

## 9. Appendix — Raw Test Results

### Cross-Server Endpoint Probe (2025-07-22)

Tested against deployment IDs with known children on both servers.

#### Oracle Server (`os4csapi-osh.duckdns.org`)

```
GET  /deployments/{id}/deployedSystems   → 400  Invalid resource name: 'deployedSystems'
GET  /deployments/{id}/members           → 200  {"items": [], "numberMatched": 0, ...}
GET  /deployments/{id}/subdeployments    → 200  {"items": [...], "numberMatched": N, ...}
GET  /deployments/{id}/systems           → 400  Invalid resource name: 'systems'
POST /deployments/{id}/deployedSystems   → 400  Invalid resource name: 'deployedSystems'
POST /deployments/{id}/members           → 400  Missing 'type' property in JSON object @ $.system
```

#### DigitalOcean Server (`45.55.99.236:8080`)

```
GET  /deployments/{id}/deployedSystems   → 400  Invalid resource name: 'deployedSystems'
GET  /deployments/{id}/members           → 200  {"items": [], "numberMatched": 0, ...}
GET  /deployments/{id}/subdeployments    → 200  {"items": [...], "numberMatched": N, ...}
GET  /deployments/{id}/systems           → 400  Invalid resource name: 'systems'
POST /deployments/{id}/deployedSystems   → 400  Invalid resource name: 'deployedSystems'
POST /deployments/{id}/members           → 400  Missing 'type' property in JSON object @ $.system
```

### v2.3 id_map.json Analysis

```
Total entries: 155+
LINK-* entries: 0      ← deployed-system links never succeeded
PROP-* entries: ~31    ← properties created
PROC-* entries: ~15    ← procedures created
SYS-* entries: ~43     ← systems created
DEP-* entries: ~20     ← deployments created
SF-* entries: ~12      ← sampling features created
```

### v3.0 id_map_v3.json

```json
{
  "DEP-040g-ICO": "server_id_ICO",
  "DEP-040h-RSO": "server_id_RSO",
  "DEP-040i-SSO-SET": "server_id_SSO",
  "DEP-040j-SNET-MON": "server_id_SNET",
  "DEP-040k-SFIELD": "server_id_SFIELD",
  "DEP-040l-STRING": "server_id_STRING",
  "SYS-040g-SET-A": "server_id_SET_A",
  "SYS-040g-MON-NODE-1": "server_id_MON",
  "SYS-040g-RELAY-1": "server_id_RELAY",
  "LINK-SSO-SET__SET-A": "deferred:SET-A→SSO-SET",
  "LINK-SNET-MON__MON-NODE-1": "deferred:MON-NODE-1→SNET-MON",
  "LINK-SNET-MON__RELAY-1": "deferred:RELAY-1→SNET-MON",
  "DS-SENREP-SET-A": "server_id_SENREP"
}
```

---

## References

- **OGC 23-001** — OGC API — Connected Systems — Part 1: Feature Resources, v1.0 (2025-07-16)
  - Clause 11.2.2 (Deployment Associations, Table 11)
  - Clause 17.4 (CREATE Deployments)
  - Clause 19.1.6 (GeoJSON Deployment Encoding, Table 43)
  - Conformance Class A.6 (Subdeployments — references `deployedSystems` GET endpoint)
- **OSH SensorHub** — OpenSensorHub implementation of OGC CSAPI
  - Oracle instance: `http://os4csapi-osh.duckdns.org/sensorhub/api`
  - DigitalOcean instance: `http://45.55.99.236:8080/sensorhub/api`
- **OS4CSAPI/OSHConnect-Python** — Repository, branch `scenario/v3.0-rebuild`
  - `scripts/bootstrap.py` (v2.3 Phase 1)
  - `scripts/bootstrap_v3.py` (v3.0 Part 1)
  - `scenarios/ft-huachuca-v3.0/` (v3.0 scenario pack)
