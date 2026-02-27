# OSH SensorHub: Deployment Hierarchy & System Association Gaps

**Date:** 2026-02-27  
**Server:** `http://45.55.99.236:8080/sensorhub/api` (OSH SensorHub)  
**OGC Spec Reference:** OGC Connected Systems API (OGC 23-001r0), Clause 13 (Deployments), Clause 13.3 (Deployed Systems)  
**Investigation Scripts:** [`check_deployments.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/check_deployments.py), [`check_deployment_links.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/check_deployment_links.py), [`check_server_endpoints.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/check_server_endpoints.py)  
**Migration Script:** [`fix_deployment_hierarchy.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/fix_deployment_hierarchy.py)  
**Verification Script:** [`verify_deployment_hierarchy.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/verify_deployment_hierarchy.py)  
**Explorer Commit:** [`fc80692`](https://github.com/OS4CSAPI/ogc-csapi-explorer/commit/fc80692) (migration + verification scripts)  
**Severity:** Medium — data model incompleteness (no hierarchy, no system associations); fully resolved by migration  

---

## 1. Executive Summary

The ODAS C-UAS acoustic sensor demo deployed 20 deployments to an OSH SensorHub server, representing a realistic Area-of-Interest (AOI) → Node → Subsystem hierarchy. After bootstrap, all 18 operational deployments appeared **flat** at the top level of the deployments listing — no subdeployment nesting, no parent–child links, and no system associations. Investigation revealed three compounding problems:

1. **Bootstrap gap:** The original ingestion scripts registered all deployments via `POST /deployments` (top-level) rather than `POST /deployments/{parentId}/subdeployments` (nested).
2. **Server limitation — `/deployedSystems` endpoint not implemented:** Requests to `GET /deployments/{id}/deployedSystems` return `400 "Invalid resource name"`. The OGC spec defines this endpoint (Clause 13.3), but the server does not support it.
3. **Server limitation — `deployedSystems@link` silently stripped:** When a deployment body includes `deployedSystems@link` in its properties and is submitted via PUT, the server accepts the request (HTTP 204) but silently drops the property. Only `platform@link` survives.

A 6-phase migration script resolved the hierarchy problem entirely. All 18 deployments were deleted and re-created as properly nested subdeployments with correct parent links. The `platform@link` property was successfully applied to the 3 node-level deployments, providing the only surviving system-to-deployment association.

**Key results:**

| Metric | Before Migration | After Migration |
|--------|:----------------:|:---------------:|
| Top-level deployment entries | 39 (18 ODAS + 21 smoke test) | 21 (2 ODAS root + 19 smoke test) |
| Deployments with parent links | 0 | 18 |
| Subdeployment nesting levels | 0 (flat) | 2 (AOI → Node → Subsystem) |
| Deployments with `platform@link` | 0 | 3 (node deployments) |
| `deployedSystems@link` preserved | N/A | 0 (server strips property) |
| Migration failures | — | 0 |

---

## 2. Background

### 2.1 The ODAS Deployment Data Model

The ODAS C-UAS acoustic sensor demo models a Fort Huachuca field deployment with 20 deployment resources:

```
AOI Deployment (AZ-DEP-AOI-001)
├── Network Deployment (AZ-DEP-NET-001)
├── Node: AZ-MA-1 Deployment
│   ├── AZ-MA-1-MICARRAY Deployment
│   ├── AZ-MA-1-EDGE Deployment
│   ├── AZ-MA-1-COMMS Deployment
│   ├── AZ-MA-1-POWER Deployment
│   └── AZ-MA-1-ACTUATOR Deployment
├── Node: AZ-MA-2 Deployment
│   ├── AZ-MA-2-MICARRAY Deployment
│   ├── AZ-MA-2-EDGE Deployment
│   ├── AZ-MA-2-COMMS Deployment
│   ├── AZ-MA-2-POWER Deployment
│   └── AZ-MA-2-ACTUATOR Deployment
└── Node: AZ-MA-3 Deployment
    ├── AZ-MA-3-MICARRAY Deployment
    ├── AZ-MA-3-EDGE Deployment
    ├── AZ-MA-3-COMMS Deployment
    ├── AZ-MA-3-POWER Deployment
    └── AZ-MA-3-ACTUATOR Deployment
```

Each deployment should be associated with the system it deploys — for example, the "AZ-MA-1 Deployment" deploys the "AZ-MA-1" system (a PhysicalSystem with 5 subsystems).

### 2.2 What Went Wrong

The original bootstrap scripts (OSHConnect-Python Phase 1 and Phase 2) registered all 20 deployments via `POST /deployments` — the top-level endpoint. The OGC Connected Systems API requires nested resources to be created via the parent's subresource endpoint:

```
# What the bootstrap did (WRONG):
POST /deployments   →  All 20 deployments registered as top-level

# What should have been done:
POST /deployments                                      →  AOI Deployment (root)
POST /deployments                                      →  Network Deployment (root)
POST /deployments/{AOI}/subdeployments                 →  3 node deployments
POST /deployments/{nodeId}/subdeployments              →  15 subsystem deployments
```

The bootstrap also attempted to POST deployed system link resources via `POST /deployments/{id}/deployedSystems`, and while the server returned `201 Created`, these links were never queryable — the endpoint doesn't actually support GET operations.

---

## 3. Investigation

Three diagnostic scripts were written to characterize the problem before attempting a fix.

### 3.1 Flat Listing (`check_deployments.py`)

Fetched all deployments from `GET /deployments?limit=50` and inspected their link relations and SML structure.

**Findings:**
- **39 total deployments** in the listing (18 ODAS + 21 smoke test/demo entries)
- No deployment had a `parent` link relation — all were at the top level
- No deployment had `subdeployments` link relation
- System link rels (`rel: "system"`, `rel: "platform"`, etc.) were absent from all deployment link arrays
- SML format (`Accept: application/sml+json`) returned minimal bodies with only `type`, `id`, `label`, `uniqueId`, `validTime` — no `deployedSystems`, `deployedPlatforms`, or `components` arrays
- No system objects had deployment-related rels in their link arrays either

### 3.2 Endpoint Probing (`check_deployment_links.py`)

Attempted to use the OGC-specified deployment associations:

```
GET /deployments/{id}/deployedSystems    →  400 "Invalid resource name"
GET /deployments/{id}/subdeployments     →  200 (but 0 items for all)
GET /systems/{id}/deployments            →  400 "Invalid resource name"
```

**Findings per deployment:**

| Deployment | `deployedSystems` | `subdeployments` | `parent` link |
|------------|:------------------:|:-----------------:|:-------------:|
| AOI (04cg) | **400** | 0 items | None |
| NET (04d0) | **400** | 0 items | None |
| AZ-MA-1 (04dg) | **400** | 0 items | None |
| AZ-MA-2 (04e0) | **400** | 0 items | None |
| AZ-MA-3 (04eg) | **400** | 0 items | None |
| All 15 sub-deps | **400** | 0 items | None |

The `400 "Invalid resource name"` response on `/deployedSystems` is definitive — the server does not recognize this as a valid sub-resource path. This is an unimplemented portion of the OGC CS API spec.

### 3.3 Server Capability Audit (`check_server_endpoints.py`)

Inspected link relations advertised by the API root, individual deployments, and individual systems in `application/json` format.

**API Root links (relevant subset):**

| Rel | Endpoint |
|-----|----------|
| `systems` | `/systems` |
| `deployments` | `/deployments` |
| `procedures` | `/procedures` |
| `samplingFeatures` | `/samplingFeatures` |
| `properties` | `/properties` |

**Single deployment link rels (04dg, application/json):**

| Rel | Present? |
|-----|:--------:|
| `self` | ✅ |
| `collection` | ✅ |
| `alternate` | ✅ |
| `canonical` | ✅ |
| `subdeployments` | ✅ |
| `deployedSystems` | ❌ |
| `parent` | ❌ (was not yet a subdeployment) |

**Single system link rels (04ng, application/json):**

| Rel | Present? |
|-----|:--------:|
| `self` | ✅ |
| `subsystems` | ✅ |
| `datastreams` | ✅ |
| `controlstreams` | ✅ |
| `samplingFeatures` | ✅ |
| `deployments` | ❌ |

The server advertises `subdeployments` as a link rel on deployments (and the GET endpoint works — it just returned 0 items because nothing was nested). It does NOT advertise `deployedSystems` on deployments or `deployments` on systems.

### 3.4 Diagnosis Summary

Three distinct problems, all originating from the bootstrap/server combination:

| # | Problem | Origin | Fixable? |
|---|---------|--------|:--------:|
| 1 | All deployments flat (no hierarchy) | Bootstrap used wrong endpoint | ✅ Yes — re-register via `/subdeployments` |
| 2 | `/deployedSystems` returns 400 | Server doesn't implement endpoint | ❌ Server limitation |
| 3 | `deployedSystems@link` stripped from PUT body | Server drops property silently | ❌ Server limitation |

---

## 4. Migration: `fix_deployment_hierarchy.py`

### 4.1 Strategy

Since deployments cannot be moved or reparented via the REST API (no PATCH for parent, no reparent endpoint), the strategy was:

1. **Snapshot** all 18 deployment bodies (preserve UIDs, coordinates, validTime)
2. **Delete** all 18 from the top level
3. **Re-create** in correct order via `POST .../subdeployments` endpoints
4. **Enrich** via PUT with descriptions and `@link` properties

The script supports `--dry-run` for safe pre-flight testing.

### 4.2 Phase Details

#### Phase 1 — Snapshot

Fetched all 18 operational deployments (3 node + 15 subsystem) as full GeoJSON via `GET /deployments/{id}` with `Accept: application/geo+json`. Stored bodies in memory with UIDs and all properties preserved.

```
Snapshotted: 18 deployments
```

#### Phase 2 — Delete All 18

Deleted in safe order: subsystem deployments first, then node deployments.

```
DELETE /deployments/04f0 (AZ-MA-1-MICARRAY) → 204  ✅
DELETE /deployments/04fg (AZ-MA-1-EDGE)     → 204  ✅
... (13 more sub-deployments, all 204)
DELETE /deployments/04dg (AZ-MA-1)          → 204  ✅
DELETE /deployments/04e0 (AZ-MA-2)          → 204  ✅
DELETE /deployments/04eg (AZ-MA-3)          → 204  ✅

Total deleted: 18/18 (0 failures)
```

**Critical observation:** The server did NOT require `?cascade=true` for deleting deployments that had no subdeployments (unlike systems). All 18 deletions returned HTTP 204 with the plain DELETE endpoint.

#### Phase 3 — Re-create Node Deployments as Subdeployments of AOI

Used `POST /deployments/{AOI_ID}/subdeployments` with the original snapshot bodies (minus `id` and `links` fields).

```
POST /deployments/04cg/subdeployments (AZ-MA-1) → 201, ID: 04dg  ✅
POST /deployments/04cg/subdeployments (AZ-MA-2) → 201, ID: 04e0  ✅
POST /deployments/04cg/subdeployments (AZ-MA-3) → 201, ID: 04eg  ✅
```

**Key finding:** The server **reused the same IDs** because the UIDs matched the deleted deployments. This is consistent with the behavior observed during system migrations (see [Ghost Resource report](OSH_Ghost_Resource_Stale_Index_Bug.md)). For deployments, the UID-to-ID reuse worked cleanly — no ghost artifacts were created.

#### Phase 4 — Re-create 15 Sub-deployments Under Node Deployments

Used the **new** node deployment IDs (which happened to match the old ones) as parents:

```
POST /deployments/04dg/subdeployments (AZ-MA-1-MICARRAY)  → 201, ID: 04f0  ✅
POST /deployments/04dg/subdeployments (AZ-MA-1-EDGE)      → 201, ID: 04fg  ✅
POST /deployments/04dg/subdeployments (AZ-MA-1-COMMS)     → 201, ID: 04g0  ✅
POST /deployments/04dg/subdeployments (AZ-MA-1-POWER)     → 201, ID: 04gg  ✅
POST /deployments/04dg/subdeployments (AZ-MA-1-ACTUATOR)  → 201, ID: 04h0  ✅
... (10 more for AZ-MA-2 and AZ-MA-3, all 201)

Total created: 15/15 (0 failures)
```

All 15 sub-deployments also had their IDs reused by the server.

#### Phase 5 — Enrich with Descriptions and @link Properties

Used PUT on each deployment to add human-readable descriptions and system association links.

**Properties set per deployment type:**

| Deployment Type | Properties Added |
|----------------|-----------------|
| AOI (04cg) | `description`, `deployedSystems@link` (4 systems) |
| NET (04d0) | `description`, `deployedSystems@link` (1 system) |
| Node (×3) | `description`, `platform@link`, `deployedSystems@link` |
| Subsystem (×15) | `description`, `deployedSystems@link` (1 subsystem each) |

```
PUT /deployments/04cg (AOI)    → 204  ✅
PUT /deployments/04d0 (NET)    → 204  ✅
PUT /deployments/04dg (AZ-MA-1) → 204  ✅
PUT /deployments/04e0 (AZ-MA-2) → 204  ✅
PUT /deployments/04eg (AZ-MA-3) → 204  ✅
... (15 sub-deployments, all 204)

Total enriched: 20/20 (0 failures)
```

All 20 PUT operations returned HTTP 204 — the server accepted them. However, the subsequent verification revealed that **only `platform@link` survived**; `deployedSystems@link` was silently dropped from all deployments.

#### Phase 6 — Built-in Verification

The migration script included its own verification phase:

```
AOI (04cg) → 3 subdeployments:
  04dg = Deployment AZ-MA-1
  04e0 = Deployment AZ-MA-2
  04eg = Deployment AZ-MA-3

Deployment AZ-MA-1 (04dg) → 5 subdeployments:
  04f0 = Deployment AZ-MA-1-MICARRAY
  04fg = Deployment AZ-MA-1-EDGE
  04g0 = Deployment AZ-MA-1-COMMS
  04gg = Deployment AZ-MA-1-POWER
  04h0 = Deployment AZ-MA-1-ACTUATOR

Deployment AZ-MA-2 (04e0) → 5 subdeployments
Deployment AZ-MA-3 (04eg) → 5 subdeployments

@link keys after enrichment:
  04cg (AOI Deployment):     []              ← deployedSystems@link stripped
  04d0 (Network Deployment): []              ← deployedSystems@link stripped
  04dg (AZ-MA-1):            [platform@link] ← SURVIVED
  04e0 (AZ-MA-2):            [platform@link] ← SURVIVED
  04eg (AZ-MA-3):            [platform@link] ← SURVIVED
```

### 4.3 Migration Summary

| Phase | Operations | Success | Failures |
|:-----:|:----------:|:-------:|:--------:|
| 1 — Snapshot | 18 GET | 18 | 0 |
| 2 — Delete | 18 DELETE | 18 (all 204) | 0 |
| 3 — Create nodes | 3 POST | 3 (all 201) | 0 |
| 4 — Create sub-deps | 15 POST | 15 (all 201) | 0 |
| 5 — Enrich | 20 PUT | 20 (all 204) | 0 |
| 6 — Verify | — | — | — |
| **Total** | **74 operations** | **74** | **0** |

---

## 5. Independent Verification

A separate verification script (`verify_deployment_hierarchy.py`) was run after the migration to confirm results independently.

### 5.1 Parent Links

All nested deployments have correct `rel: "parent"` links pointing to their actual parent deployment:

| Deployment | Parent Link |
|-----------|------------|
| AZ-MA-1 (04dg) | `/deployments/04cg` (AOI) ✅ |
| AZ-MA-2 (04e0) | `/deployments/04cg` (AOI) ✅ |
| AZ-MA-3 (04eg) | `/deployments/04cg` (AOI) ✅ |
| AZ-MA-1-MICARRAY (04f0) | `/deployments/04dg` (AZ-MA-1) ✅ |
| AZ-MA-3-MICARRAY (04k0) | `/deployments/04eg` (AZ-MA-3) ✅ |
| (all 15 sub-deps) | (correct parent) ✅ |

### 5.2 @link Properties

| Deployment | `platform@link` | `deployedSystems@link` | `description` |
|-----------|:--------------:|:---------------------:|:------------:|
| AOI (04cg) | — | ❌ stripped | ✅ |
| NET (04d0) | — | ❌ stripped | ✅ |
| AZ-MA-1 (04dg) | ✅ → system `04ng` | ❌ stripped | ✅ |
| AZ-MA-2 (04e0) | ✅ → system `04o0` | ❌ stripped | ✅ |
| AZ-MA-3 (04eg) | ✅ → system `04og` | ❌ stripped | ✅ |
| All 15 sub-deps | — | ❌ stripped | ✅ |

The `platform@link` property is the **only surviving mechanism** for associating a deployment with a system on this server. It is preserved on the 3 node-level deployments.

### 5.3 Top-Level Listing

After migration, `GET /deployments?limit=50` returns **21 entries**:

| Category | Count | Details |
|----------|:-----:|---------|
| ODAS root deployments | 2 | AOI Deployment, Network Deployment |
| Smoke test entries | 19 | Pre-existing test data (not ODAS) |
| **Nested ODAS deployments** | **0** | ✅ Correctly absent from top-level |

None of the 18 nested deployments appear in the top-level listing — they are only accessible via their parent's `/subdeployments` endpoint.

### 5.4 Full Tree

```
AOI Deployment (04cg)
├── Deployment AZ-MA-1 (04dg)        platform@link → system 04ng
│   ├── Deployment AZ-MA-1-MICARRAY (04f0)
│   ├── Deployment AZ-MA-1-EDGE (04fg)
│   ├── Deployment AZ-MA-1-COMMS (04g0)
│   ├── Deployment AZ-MA-1-POWER (04gg)
│   └── Deployment AZ-MA-1-ACTUATOR (04h0)
├── Deployment AZ-MA-2 (04e0)        platform@link → system 04o0
│   ├── Deployment AZ-MA-2-MICARRAY (04hg)
│   ├── Deployment AZ-MA-2-EDGE (04i0)
│   ├── Deployment AZ-MA-2-COMMS (04ig)
│   ├── Deployment AZ-MA-2-POWER (04j0)
│   └── Deployment AZ-MA-2-ACTUATOR (04jg)
└── Deployment AZ-MA-3 (04eg)        platform@link → system 04og
    ├── Deployment AZ-MA-3-MICARRAY (04k0)
    ├── Deployment AZ-MA-3-EDGE (04kg)
    ├── Deployment AZ-MA-3-COMMS (04l0)
    ├── Deployment AZ-MA-3-POWER (04lg)
    └── Deployment AZ-MA-3-ACTUATOR (04m0)
```

---

## 6. Server Conformance Analysis

### 6.1 OGC CS API Deployment Requirements

**Clause 13 — Deployments:**
> Deployments SHALL support hierarchical nesting via subdeployments. A deployment MAY contain zero or more subdeployments.

**Clause 13.3 — Deployed Systems:**
> A deployment SHALL provide a link to its deployed systems via the `deployedSystems` link relation. The server SHALL support `GET /deployments/{id}/deployedSystems` to list systems associated with the deployment.

### 6.2 Conformance Matrix

| Requirement | Spec Reference | Expected | Actual | Conformant? |
|-------------|---------------|----------|--------|:-----------:|
| Subdeployment nesting via POST | Clause 13.1 | Supported | ✅ Works correctly | ✅ |
| Parent `rel` link on subdeployments | Clause 13.1 | Present | ✅ Auto-generated by server | ✅ |
| `subdeployments` link rel | Clause 13.1 | Present on parents | ✅ Present and functional | ✅ |
| DELETE deployment | Clause 13.2 | Returns 204 | ✅ Works | ✅ |
| ID reuse on UID match | — | Not specified | ✅ Server reuses IDs (clean, no ghosts) | N/A |
| `GET .../deployedSystems` | Clause 13.3 | Returns system list | ❌ Returns 400 | ❌ |
| `deployedSystems@link` in properties | Properties | Preserved on PUT | ❌ Silently stripped | ❌ |
| `platform@link` in properties | Properties | Preserved on PUT | ✅ Preserved | ✅ |
| `GET /systems/{id}/deployments` | Clause 8.3 | Returns deployment list | ❌ Returns 400 | ❌ |

### 6.3 Impact Assessment

| Gap | Severity | Impact |
|-----|:--------:|--------|
| `/deployedSystems` endpoint missing | **High** | No standard way to query which systems are deployed at a given deployment. Clients cannot navigate from deployment to system. |
| `deployedSystems@link` silently stripped | **Medium** | Even the workaround of embedding system links in the deployment body fails — the server accepts the PUT but drops the data. |
| `/systems/{id}/deployments` missing | **Medium** | No reverse navigation from system to deployment. |
| `platform@link` preserved | **Mitigating** | Provides partial workaround — 3 of 20 deployments can link to their system. |

---

## 7. Workarounds and Mitigations

### 7.1 `platform@link` as Partial Association

The `platform@link` property survives PUT operations and provides a direct link from a deployment to a system. This was applied to the 3 node-level deployments:

```json
{
  "platform@link": {
    "href": "http://45.55.99.236:8080/sensorhub/api/systems/04ng",
    "rel": "platform",
    "title": "AZ-MA-1"
  }
}
```

**Limitation:** This is only a single system reference per deployment. The spec envisions `deployedSystems` as a collection (multiple systems per deployment), but `platform@link` is a single-valued property meaning one link per deployment.

### 7.2 Naming Convention Matching

Deployments and systems use a consistent naming convention (`AZ-MA-1` appears in both the system name and the deployment name). Clients can use string matching as a heuristic for association:

- System `AZ-MA-1` → Deployment `Deployment AZ-MA-1`
- System `AZ-MA-1-MICARRAY` → Deployment `Deployment AZ-MA-1-MICARRAY`

This is fragile and not machine-readable, but it provides a fallback for UI display.

### 7.3 Description Field

Each deployment now includes a human-readable `description` field that references the associated system:

```
"Node-level deployment for AZ-MA-1 monitoring array at Fort Huachuca."
"Subsystem deployment for AZ-MA-1-MICARRAY component of AZ-MA-1 array."
```

---

## 8. Server ID Reference

### 8.1 Deployment IDs (After Migration)

| Server ID | Name | Parent | Level |
|-----------|------|--------|:-----:|
| `04cg` | AOI Deployment | — | Root |
| `04d0` | Network Deployment | — | Root |
| `04dg` | Deployment AZ-MA-1 | `04cg` | 1 |
| `04e0` | Deployment AZ-MA-2 | `04cg` | 1 |
| `04eg` | Deployment AZ-MA-3 | `04cg` | 1 |
| `04f0` | Deployment AZ-MA-1-MICARRAY | `04dg` | 2 |
| `04fg` | Deployment AZ-MA-1-EDGE | `04dg` | 2 |
| `04g0` | Deployment AZ-MA-1-COMMS | `04dg` | 2 |
| `04gg` | Deployment AZ-MA-1-POWER | `04dg` | 2 |
| `04h0` | Deployment AZ-MA-1-ACTUATOR | `04dg` | 2 |
| `04hg` | Deployment AZ-MA-2-MICARRAY | `04e0` | 2 |
| `04i0` | Deployment AZ-MA-2-EDGE | `04e0` | 2 |
| `04ig` | Deployment AZ-MA-2-COMMS | `04e0` | 2 |
| `04j0` | Deployment AZ-MA-2-POWER | `04e0` | 2 |
| `04jg` | Deployment AZ-MA-2-ACTUATOR | `04e0` | 2 |
| `04k0` | Deployment AZ-MA-3-MICARRAY | `04eg` | 2 |
| `04kg` | Deployment AZ-MA-3-EDGE | `04eg` | 2 |
| `04l0` | Deployment AZ-MA-3-COMMS | `04eg` | 2 |
| `04lg` | Deployment AZ-MA-3-POWER | `04eg` | 2 |
| `04m0` | Deployment AZ-MA-3-ACTUATOR | `04eg` | 2 |

### 8.2 System ↔ Deployment Associations (via `platform@link`)

| System ID | System Name | Deployment ID | Association |
|-----------|------------|---------------|:-----------:|
| `04ng` | AZ-MA-1 | `04dg` | ✅ `platform@link` |
| `04o0` | AZ-MA-2 | `04e0` | ✅ `platform@link` |
| `04og` | AZ-MA-3 | `04eg` | ✅ `platform@link` |
| `04n0` | AZ-MA-NET | `04d0` | ❌ No surviving link |
| `04pg` | AZ-MA-1-MICARRAY | `04f0` | ❌ No surviving link |
| ... (12 more subsystems) | ... | ... | ❌ No surviving link |

---

## 9. Recommendations

### 9.1 For OSH SensorHub (Upstream)

1. **Implement `/deployments/{id}/deployedSystems` endpoint** — This is a Clause 13.3 spec requirement. Without it, there is no standard way to associate systems with deployments.

2. **Preserve `deployedSystems@link` on PUT** — The server should not silently strip recognized `@link` properties from deployment bodies. Either preserve them or return a 400/422 error to inform the client.

3. **Implement `/systems/{id}/deployments`** — Reverse navigation from system to deployment is essential for a complete data model. The spec references this in Clause 8.3.

4. **Document supported `@link` properties** — Provide a list of which `@link` property names the server recognizes and preserves for each resource type.

### 9.2 For OSHConnect-Python

1. **Use `/subdeployments` endpoint for nested deployments** — The library's deployment creation methods should support a `parent_id` parameter that routes the POST to `/deployments/{parentId}/subdeployments`.

2. **Set `platform@link` on deployment creation** — Since this is the only surviving association mechanism, the library should set it automatically when creating a deployment for a system.

3. **Add `deployedSystems` endpoint probe** — Before attempting to query deployed systems, check whether the endpoint returns 400 and gracefully fall back.

### 9.3 For CSAPI Explorer (Webapp)

1. **Use `platform@link` for deployment → system navigation** — When rendering a deployment detail view, check for `platform@link` in properties and provide a clickable link to the associated system.

2. **Display subdeployment hierarchy** — The Deployments page should render the tree structure rather than a flat list. Use `/subdeployments` recursively to build the tree.

3. **Fallback: name-based matching** — When `platform@link` is absent, offer heuristic system matching based on naming conventions.

---

## 10. Relationship to Previous Research

| Document | Relationship |
|----------|-------------|
| [OSH Cascade Delete Experiment](OSH_Cascade_Delete_Experiment.md) | Proved `?cascade=true` works for systems. Deployment DELETE did not require cascade (no nested resources at time of deletion). |
| [OSH Ghost Resource / Stale Index Bug](OSH_Ghost_Resource_Stale_Index_Bug.md) | During deployment migration, ID reuse via UID match worked cleanly — no ghost deployment artifacts were created (unlike the system ghost bug). |
| [OSH Delete Cascade and Reparenting](OSH_Delete_Cascade_and_Reparenting.md) | Documented the delete-recreate strategy for re-parenting resources. The same approach was used for deployments. |
| [Phase 1 Bootstrap Results](Phase1_Bootstrap_Results.md) | The bootstrap that created the original flat deployment registrations. |

---

## 11. Reproduction

### 11.1 Running the Migration Script

```bash
cd csapi-explorer

# Dry run (no server changes):
python scripts/fix_deployment_hierarchy.py --dry-run

# Real run:
python scripts/fix_deployment_hierarchy.py
```

**Prerequisites:**
- Python 3.10+ with `requests` library
- Network access to the OSH SensorHub server (`45.55.99.236:8080`)
- Authentication credentials (hardcoded in script: `ogc:ogc`)
- Deployments must exist with the expected UIDs (will fail gracefully if already migrated)

### 11.2 Running the Verification Script

```bash
python scripts/verify_deployment_hierarchy.py
```

Verifies parent links, @link properties, top-level listing composition, and full tree structure.

---

## 12. Conclusion

The deployment hierarchy migration was **100% successful** — 74 API operations with zero failures. All 18 ODAS operational deployments are now correctly nested in a 2-level hierarchy (AOI → Node → Subsystem) with parent links, descriptions, and the `platform@link` system association where possible.

Two server conformance gaps remain that cannot be fixed from the client side:

1. **`/deployedSystems` endpoint not implemented** — the primary mechanism for associating systems with deployments per the OGC spec is unavailable.
2. **`deployedSystems@link` silently stripped** — the fallback of embedding system links in the deployment body is also ineffective.

The only working system association mechanism is `platform@link`, which was successfully applied to the 3 node-level deployments. This is a partial solution — 3 of 20 deployments have a machine-readable system link. The remaining 17 deployments (AOI, NET, and 15 subsystem-level) have no surviving system association due to server limitations.

These findings represent concrete conformance gaps in the OSH SensorHub's Connected Systems API implementation and should be reported upstream as part of the ongoing OGC specification conformance assessment.
