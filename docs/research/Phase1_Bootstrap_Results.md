# Phase 1 Bootstrap Results Report

**Date:** 2026-02-26  
**Author:** GitHub Copilot (Claude Opus 4.6)  
**Issue:** [OS4CSAPI/OSHConnect-Python#2](https://github.com/OS4CSAPI/OSHConnect-Python/issues/2)  
**Commit:** `f38b3af` — _Phase 1 Bootstrap: create 121 Part 1 resources on OSH server_  
**Server:** `http://45.55.99.236:8080/sensorhub/api` (auth: `ogc:ogc`)

---

## 1. Objective

Write and execute a Python bootstrap script (`scripts/bootstrap.py`) to POST all **121 Part 1 resources** from the Maximal ScenarioPack v2.3 (Fort Huachuca C-UAS acoustic scenario) to the OSH SensorHub server, in correct dependency order, persisting the server-assigned ID map for use by Phase 2.

## 2. Execution Summary

| Metric | Value |
|---|---|
| Total POST requests | 128 (121 resources + 7 deployed system links) |
| Created (HTTP 201) | **128** |
| Failed | **0** |
| Execution time | 5.0 seconds |
| id_map entries | 121 (logical ID → server-assigned ID) |

## 3. Resources Created — Breakdown

### 3.1 Properties (31/31) — Verified

Observable properties defined under the SWE Common model (QUDT-based). All accessible at `GET /properties/{id}` and returned correctly.

| Server ID | Label | UID |
|---|---|---|
| `0440` | activity | `urn:os4csapi:property:activity` |
| `044g` | activityLevel | `urn:os4csapi:property:activityLevel` |
| `0450` | bearingStdDev | `urn:os4csapi:property:bearingStdDev` |
| `045g` | bearingTrue | `urn:os4csapi:property:bearingTrue` |
| `0460` | classConfidence | `urn:os4csapi:property:classConfidence` |
| ... | _(26 more)_ | ... |

**Full list in `scripts/id_map.json` under `PROP-*` keys.**

### 3.2 Procedures (15/15) — Verified

Processing algorithms from the ODAS pipeline. All accessible at `GET /procedures/{id}`.

| Category | Count | Example UID |
|---|---|---|
| Per-node (CAL, HEALTH, ODAS, TRANSFORM) | 12 (4 × 3 nodes) | `urn:os4csapi:procedure:odas:az-ma-1:calibration:v1` |
| Network-level (ASSOC, CLASSIFY, TRIANG) | 3 | `urn:os4csapi:procedure:odas:network:association:v1` |

### 3.3 Systems (43/43) — Verified

Full system-of-systems hierarchy with parent–child relationships confirmed on the server.

**Top-level systems (4):**

| Server ID | Name | UID | Subsystems |
|---|---|---|---|
| `04n0` | Ft Huachuca Acoustic Sensing Network (MA-NET) | `urn:os4csapi:system:odas:az-ma-net` | 0 |
| `04ng` | ODAS Mic Array Node AZ-MA-1 | `urn:os4csapi:system:odas:az-ma-1` | 13 |
| `04o0` | ODAS Mic Array Node AZ-MA-2 | `urn:os4csapi:system:odas:az-ma-2` | 13 |
| `04og` | ODAS Mic Array Node AZ-MA-3 | `urn:os4csapi:system:odas:az-ma-3` | 13 |

**Subsystems per node (13 each):** PLATFORM, MICARRAY, EDGE, COMMS, POWER, ACTUATOR, MIC1–MIC7.

**Hierarchy verification:**
```
GET /systems/04p0                  → 200 OK
  name: "AZ-MA-1 Tripod Platform"
  uid:  "urn:os4csapi:platform:az-ma-1:tripod"
  links: [{ rel: "parent", href: ".../systems/04ng?f=geojson" }]

GET /systems/04ng/subsystems       → 200 OK (13 items returned)
```

### 3.4 Deployments (20/20) — Verified

All accessible at `GET /deployments/{id}`.

| Category | Count | Example |
|---|---|---|
| Top-level (AOI, NET) | 2 | `AZ-DEP-AOI-001` → `04cg` |
| Node deployments | 3 | `AZ-DEP-AZ-MA-1` → `04dg` |
| Sub-deployments (MICARRAY, EDGE, COMMS, POWER, ACTUATOR × 3 nodes) | 15 | `AZ-DEP-AZ-MA-1-MICARRAY` → `04f0` |

Node deployments have `relatedTo@link` rewritten to reference the AOI deployment's server ID.

**Verification:**
```
GET /deployments/04cg?f=geojson    → 200 OK
  name: "AOI Deployment"
  uid:  "urn:os4csapi:deployment:aoi:ft-huachuca-range-01"
  geometry: Polygon (Ft. Huachuca bounding box)
  validTime: ["2026-02-26T00:00:00Z", ".."]
```

### 3.5 Sampling Features (12/12) — Created but NOT retrievable ⚠️

All 12 sampling features were accepted by the server (HTTP 201, `Location` header returned). However, they **cannot be retrieved** — `GET /samplingFeatures/{id}` returns **HTTP 500 Internal Server Error**.

**Root cause:** All 12 sampling features have `"geometry": null` in their GeoJSON. The OSH SensorHub server's serializer crashes when rendering null geometry on GET. This is a **server bug**, not a data error — `null` geometry is valid GeoJSON (RFC 7946 §3.2).

| Endpoint | Status | Notes |
|---|---|---|
| `POST /samplingFeatures` | 201 Created | ID returned in `Location` header |
| `GET /samplingFeatures/{id}` | 500 Internal Server Error | Null geometry serialization crash |
| `GET /samplingFeatures?uid=...` | 500 Internal Server Error | Collection endpoint also crashes |
| `GET /samplingFeatures?limit=50` | Partial 200 | Returns existing non-null features, then 500 mid-stream |

**Affected resources:**

| Logical ID | Server ID | UID |
|---|---|---|
| `AZ-GTRK-0001` | `052g` | `urn:os4csapi:sample:globaltrack:GT-0001` |
| `AZ-GTRK-0002` | `0530` | `urn:os4csapi:sample:globaltrack:GT-0002` |
| `AZ-GTRK-0003` | `053g` | `urn:os4csapi:sample:globaltrack:GT-0003` |
| `AZ-MA-{1,2,3}-TRK-{1,2,3}` | _(9 entries)_ | `urn:os4csapi:sample:...:local-track:...` |

**Potential workaround:** Re-create with a dummy Point geometry (e.g., the node's coordinates) instead of `null`. However, this might misrepresent the data semantically — tracks are abstract sampling features, not fixed locations.

### 3.6 Deployed System Links (7/7) — Accepted, not independently queryable ⚠️

All 7 deployed system link POSTs were accepted (HTTP 2xx). These link systems to their deployments with configuration metadata (e.g., sampling rate, microphone count).

| Deployment | Linked System | Notes |
|---|---|---|
| `AZ-DEP-AOI-001` | `AZ-MA-1`, `AZ-MA-2`, `AZ-MA-3`, `AZ-MA-NET` | 4 links |
| `AZ-DEP-AZ-MA-{1,2,3}` | `AZ-MA-{1,2,3}` | 3 links |

**Limitation:** The OSH SensorHub server does not expose a `/deployments/{id}/deployedSystems` sub-collection endpoint. `GET /deployments/{id}/deployedSystems` returns `400 Invalid resource name: 'deployedSystems'`. The deployment resources themselves also do not include deployed system links in their response body. This means the deployed system associations may be stored but are not accessible via the API.

## 4. Key Technical Discoveries

### 4.1 validTime Format Mismatch (Critical)

The ScenarioPack v2.3 resource files use an **object format** for `validTime`:
```json
{ "begin": "2026-01-01T00:00:00Z", "end": null }
```

The OSH SensorHub server requires an **ISO 8601 interval array format**:
```json
["2026-01-01T00:00:00Z", ".."]
```

Sending the object format results in **HTTP 400 Bad Request**. The bootstrap script converts on-the-fly:
- `{begin: X, end: null}` → `[X, ".."]`
- `{begin: X, end: Y}` → `[X, Y]`

This affects all GeoJSON resources (systems, procedures, deployments, sampling features = 90+ files).

### 4.2 Server Text Search (`?q=`) Does Not Match UIDs

The `?q=os4csapi` query parameter only searches `name` and `description` fields, not `uid`. To find resources by UID, use `?uid=urn:os4csapi:...` (but this is broken for sampling features due to the null geometry bug).

### 4.3 Server ID Collisions Across Resource Types

The server reuses the same ID space across different resource types. For example, `0560` is both a system (AZ-MA-3-PLATFORM) and a sampling feature (AZ-MA-2-TRK-2). This is by design — IDs are scoped to their collection endpoint.

## 5. Verification Matrix

| Resource Type | Expected | Created (201) | GET Verified | Status |
|---|---|---|---|---|
| Properties | 31 | 31 | 31 | ✅ PASS |
| Procedures | 15 | 15 | 15 | ✅ PASS |
| Systems | 43 | 43 | 43 | ✅ PASS |
| Deployments | 20 | 20 | 20 | ✅ PASS |
| Sampling Features | 12 | 12 | 0 | ⚠️ Created but 500 on GET |
| Deployed System Links | 7 | 7 | N/A | ⚠️ No query endpoint |
| **Total** | **128** | **128** | **109** | |

**109 of 121 core resources** are fully verified as accessible on the server. The remaining 12 (sampling features) are stored in the database but trigger a server bug on retrieval.

## 6. Artifacts

| File | Description |
|---|---|
| `scripts/bootstrap.py` | Bootstrap script (idempotent, supports `--dry-run`) |
| `scripts/id_map.json` | 121 entries mapping logical IDs to server-assigned IDs |
| `scripts/verify_server.py` | Server verification script |

## 7. Server Bugs Filed / To File

| Bug | Severity | Workaround |
|---|---|---|
| Sampling features with `null` geometry → 500 on GET | High | Re-create with dummy Point geometry |
| `deployedSystems` sub-collection not exposed on deployments | Medium | None — may need OSH server update |
| `validTime` rejects RFC 8601 object format, requires array | Medium | Convert to array format before POST |

## 8. Next Steps

1. **Phase 2 (Issue #1):** Create datastreams and controlstreams using the id_map
2. **Consider:** Re-creating sampling features with dummy geometry to unblock Phase 2 observation ingestion
3. **Consider:** Filing an upstream bug report on the OSH SensorHub for the null geometry serialization crash

## 9. How to Access These Resources

All resources are accessible via HTTP GET with Basic Auth (`ogc:ogc`). You can use a browser, `curl`, or any HTTP client:

```bash
# Root API
curl -u ogc:ogc http://45.55.99.236:8080/sensorhub/api

# System AZ-MA-1 (GeoJSON)
curl -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/systems/04ng?f=geojson"

# All subsystems of AZ-MA-1
curl -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/systems/04ng/subsystems"

# AOI Deployment (GeoJSON)
curl -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/deployments/04cg?f=geojson"

# A procedure
curl -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/procedures/04h0"

# A property
curl -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/properties/0440"

# All properties
curl -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/properties"
```

Or open directly in the browser (it may prompt for auth):
- **System AZ-MA-1:** http://45.55.99.236:8080/sensorhub/api/systems/04ng?f=geojson
- **Subsystems:** http://45.55.99.236:8080/sensorhub/api/systems/04ng/subsystems
- **AOI Deployment:** http://45.55.99.236:8080/sensorhub/api/deployments/04cg?f=geojson
- **All Properties:** http://45.55.99.236:8080/sensorhub/api/properties
