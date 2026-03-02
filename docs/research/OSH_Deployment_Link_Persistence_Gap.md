# OSH Deployment Association Persistence Gap

## Impact Analysis for ODAS Deployment Modeling Strategy

**Date:** 2026-03-02  
**Author:** AI Research Agent (GitHub Copilot / Claude Opus 4.6)  
**Status:** Confirmed — empirically validated on Oracle OSH instance  
**Blocking:** Deployment-scoped datastream queries  
**Related reports:**
- [OSH_DeployedSystems_Conformance_Probe.md](OSH_DeployedSystems_Conformance_Probe.md) — `deployedSystems@link` silently dropped
- [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) — 1:1 deployment–system pairing pattern
- [CSAPI_Deployment_Reparenting_Feasibility.md](CSAPI_Deployment_Reparenting_Feasibility.md) — hierarchy restructuring via API
- [CSAPI_Deployment_Semantics_Analysis.md](CSAPI_Deployment_Semantics_Analysis.md) — deployment as "operational assignment"

---

## 1. Executive Summary

On 2026-03-02, while executing the Node 1 sub-deployment creation under Sensor String Alpha on our Oracle OSH instance, we discovered that **OSH silently drops `deployment@link` on datastreams** — the same class of conformance gap previously documented for `deployedSystems@link` on deployments.

Combined with the already-known failure of deployment-scoped query endpoints (`/deployments/{id}/datastreams` → HTTP 400), this means **none of the three spec-defined mechanisms for associating datastreams with deployments are functional on OSH**.

The deployment hierarchy we built is structurally correct and the Node 1 sub-deployment was successfully created, but the "deployment as data filter" use case — the primary reason we wanted deployment-scoped access — **cannot be realized on OSH today**.

---

## 2. What We Did

### 2.1 The Restructure Operation

We executed a live restructure of the Oracle deployment hierarchy for AZ-MA-1:

**Before:**
```
String Alpha (0430)
  platform@link → /systems/0420 (AZ-MA-1)
  [7 datastreams on AZ-MA-1, all with deployment@link = none]
```

**After:**
```
String Alpha (0430)
  [no platform@link — now a collective]
  └── Node 1 (043g)                    ← NEW
        platform@link → /systems/0420 (AZ-MA-1)
```

| Step | Action | Result |
|------|--------|--------|
| 1 | Probe `deployment@link` via PUT on datastream | PUT accepted (HTTP 204), field **silently dropped** on read-back |
| 2 | Create Node 1 sub-deployment under String Alpha | **HTTP 201** — id=`043g` |
| 3 | Set `deployment@link` on 8 datastreams → Node 1 | **SKIPPED** — probe proved field is dropped |
| 4 | Remove `platform@link` from String Alpha | **HTTP 204** — verified removed |
| 5 | Verify final state | Node 1 exists, `platform@link` correct, String Alpha cleaned |

Node 1 was created successfully. The hierarchy restructure itself worked perfectly.

### 2.2 The Probe Protocol

To test whether `deployment@link` can be persisted on datastream resources, we used the following protocol:

1. `GET /systems/0420/datastreams/0430` — fetch "Classification Probabilities" datastream with its schema
2. `GET /datastreams/0430/schema` — fetch SWE record schema (required by OSH for PUT)
3. Build PUT payload: original datastream + schema + injected `deployment@link` with sentinel title `"PROBE-TEST-MARKER"`
4. `PUT /systems/0420/datastreams/0430` — server returns **HTTP 204** (success)
5. `GET /systems/0420/datastreams/0430` — read back: **`deployment@link` is absent**

The PUT succeeds (the server does not reject it), but the field does not persist. This is identical to OSH's behavior with `deployedSystems@link` on deployments, documented in [OSH_DeployedSystems_Conformance_Probe.md](OSH_DeployedSystems_Conformance_Probe.md).

---

## 3. The Three-Mechanism Failure

The CSAPI specification (OGC 23-001 Part 1, OGC 23-002 Part 2) defines three ways to associate a datastream with a deployment:

### Mechanism 1: `deployment@link` on DataStream (Part 2)

Per **OGC 23-002 §7.3.2**, a DataStream resource MAY include a `deployment@link` property linking it to the Deployment during which it was active.

| Spec Behavior | OSH Behavior |
|--------------|--------------|
| PUT/POST with `deployment@link` persists the association | PUT returns 204 but field is **silently dropped** |
| GET returns `deployment@link` when set | GET **never** returns `deployment@link` |

**Status: NOT FUNCTIONAL**

### Mechanism 2: Deployment-scoped query endpoints (Part 2)

Per **OGC 23-002 conformance class A.2**, `GET /deployments/{depId}/datastreams` returns datastreams whose parent system was deployed during the referenced deployment, with `validTime` intersection.

| Spec Behavior | OSH Behavior |
|--------------|--------------|
| Returns filtered datastream collection | Returns **HTTP 400** |
| Intersects deployment `validTime` with datastream `validTime` | Not implemented |
| Similarly for `/deployments/{depId}/systems` | Also returns **HTTP 400** |

**Status: NOT IMPLEMENTED**

### Mechanism 3: `deployedSystems@link` on Deployment (Part 1)

Per **OGC 23-001 §8.5 Table 10**, a Deployment resource includes `deployedSystems@link` (array, **required**) listing the systems deployed during it.

| Spec Behavior | OSH Behavior |
|--------------|--------------|
| PUT/POST with `deployedSystems@link` persists | PUT returns 204 but field is **silently dropped** |
| GET returns `deployedSystems@link` array | GET **never** returns this field |

**Status: NOT FUNCTIONAL** (documented in [OSH_DeployedSystems_Conformance_Probe.md](OSH_DeployedSystems_Conformance_Probe.md))

### Summary

| Mechanism | Direction | Spec Status | OSH Status |
|-----------|-----------|-------------|------------|
| `deployment@link` on DataStream | DataStream → Deployment | Optional (Part 2) | Silently dropped |
| `/deployments/{id}/datastreams` | Deployment → DataStreams | Required (Part 2 A.2) | HTTP 400 |
| `/deployments/{id}/systems` | Deployment → Systems | Required (Part 2 A.2) | HTTP 400 |
| `deployedSystems@link` on Deployment | Deployment → Systems | Required (Part 1) | Silently dropped |
| `platform@link` on Deployment | Deployment → Platform | Optional (Part 1) | **Works** ✓ |
| Subdeployments endpoint | Deployment → Children | Required (Part 1) | **Works** ✓ |

**The only functional deployment association on OSH is `platform@link`.**

---

## 4. What This Means for Our Plans

### 4.1 What We Wanted To Do

Our deployment modeling strategy, developed across six research reports and the MA-1 migration, was built on this architectural vision:

1. **Military-operational deployment hierarchy** — ICO → R&S → SSO → Sensor Net → Sensor Field → Sensor String → Node
2. **Deployment as data filter** — query `GET /deployments/{nodeId}/datastreams` to get only the datastreams from the system deployed at that node
3. **Temporal scoping** — when a sensor is redeployed from Node 1 to Node 3, the historical data stays associated with Node 1's `validTime` window
4. **Multi-node string management** — String Alpha eventually has Nodes 1–N, each with their own deployed system, and a single deployment-scoped query returns just that node's data
5. **Deployment-centric observation access** — the Explorer webapp navigates from deployment tree → deployment-scoped datastreams → live observations

### 4.2 What Actually Works

| Planned Capability | Status | Notes |
|-------------------|--------|-------|
| Deep deployment hierarchy (6+ levels) | **WORKS** | ICO → R&S → SSO → SNet → Field → String → Node all created successfully |
| `platform@link` on leaf deployments | **WORKS** | Node 1 → AZ-MA-1 association persists and is queryable |
| Subdeployment navigation | **WORKS** | `GET /deployments/{id}/subdeployments` returns child deployments |
| Deployment as label/metadata | **WORKS** | Name, description, UID, validTime, geometry all persist |
| Deployment-scoped datastream query | **BROKEN** | HTTP 400 — not implemented |
| Deployment-scoped system query | **BROKEN** | HTTP 400 — not implemented |
| `deployment@link` on datastreams | **BROKEN** | Silently dropped — cannot tag data with its deployment context |
| `deployedSystems@link` on deployments | **BROKEN** | Silently dropped — cannot list deployed systems from deployment side |
| Temporal deployment window filtering | **BROKEN** | Requires deployment-scoped endpoints to intersect `validTime` |

### 4.3 The Gap in Plain Terms

We built a carefully modeled military deployment hierarchy — and it *exists* correctly on the server — but we **cannot query through it**. The hierarchy is a well-formed tree of metadata that does not connect to the observation data.

The deployment tree is like a filing cabinet with perfectly labeled drawers, folders, and tabs — but the documents inside aren't filed in them. They're all in one unsorted pile (the system's datastreams), and the labels on the drawers are ornamental.

To get AZ-MA-1's datastreams today, a client must query `GET /systems/0420/datastreams` — which returns all 7 datastreams regardless of deployment. The deployment hierarchy adds no filtering, no scoping, and no temporal windowing.

### 4.4 Impact on Each Stakeholder

**Explorer webapp:**
- The deployment tree view works for navigation and display
- But clicking a deployment cannot show "just this deployment's data" via a single API call
- The webapp must follow `platform@link` to the system, then query the system's datastreams — the deployment is a UI-only concept, not a data access path
- The existing `tryLinkFallback()` workaround in `ResourceDetail.vue` remains the only viable path

**Migration scripts (MA-2, MA-3):**
- Sub-deployment creation under String Alpha will work (same pattern as Node 1)
- But there is no benefit to creating per-node deployments unless the server eventually supports deployment-scoped queries
- The extra hierarchy adds API round-trip cost with no query benefit

**ODAS Adapter:**
- The adapter creates datastreams under systems, not deployments
- Without `deployment@link` persistence, the adapter cannot stamp each datastream with its deployment context
- If AZ-MA-1 is redeployed from Node 1 to Node 3, there is no server-side mechanism to know which observations belong to which deployment period

**Interoperability testing:**
- 52North *does* return `deployedSystems@link` on deployments (per the ingestion report)
- A multi-server test would show divergent behavior for the same resources
- This is a real conformance gap, not an optional feature

---

## 5. What `platform@link` Actually Gives Us

Despite the gaps, `platform@link` on deployments **does** provide value:

### 5.1 Forward Navigation (Deployment → System → Data)

```
GET /deployments/043g                     → Node 1, platform@link → /systems/0420
GET /systems/0420/datastreams             → 7 datastreams
GET /systems/0420/datastreams/0430/observations → live data
```

This three-hop path works. The deployment guides the client to the right system, and the system owns the data. It's indirect but functional.

### 5.2 Reverse Navigation (System → Deployment)

```
GET /deployments?recursive=true           → all deployments (flat list)
Client-side filter: find where platform@link.href contains "/systems/0420"
```

This is expensive (fetches all deployments) but works. Our Explorer already does this.

### 5.3 Hierarchy Display

```
GET /deployments                          → root-level deployments
GET /deployments/{id}/subdeployments      → children at each level
Recurse to build tree
```

This works perfectly. The hierarchy is real and navigable.

### 5.4 What `platform@link` Cannot Do

- **Filter datastreams by deployment** — the system's datastreams are all-or-nothing
- **Temporal scoping** — if AZ-MA-1 moves from Node 1 to Node 3, both nodes' `platform@link` historically point to the same system; there's no time-windowed data separation
- **Multi-system deployments** — a deployment with multiple `platform@link` entries would need client-side aggregation across multiple system endpoints
- **Deployment-scoped observation queries** — cannot ask "show me all observations from this deployment window"

---

## 6. Classification

### 6.1 OSH Conformance Assessment

| OGC Requirement | Reference | Conformance |
|-----------------|-----------|-------------|
| Deployment SHALL include `deployedSystems@link` | OGC 23-001 §8.5 Table 10 | **NON-CONFORMANT** — field silently dropped |
| DataStream MAY include `deployment@link` | OGC 23-002 §7.3.2 | **NON-CONFORMANT** — field silently dropped (optional per spec, but implementation should persist if submitted) |
| `/deployments/{depId}/datastreams` endpoint | OGC 23-002 A.2 Req 8-9 | **NOT IMPLEMENTED** — HTTP 400 |
| `/deployments/{depId}/systems` endpoint | OGC 23-002 A.2 Req 6-7 | **NOT IMPLEMENTED** — HTTP 400 |
| `/deployments/{depId}/subdeployments` endpoint | OGC 23-001 §8.5 | **CONFORMANT** ✓ |
| `platform@link` persistence on Deployment | OGC 23-001 §8.5 Table 10 | **CONFORMANT** ✓ |

### 6.2 Severity

**HIGH for deployment-scoped data access use cases.**

This is not a cosmetic issue or minor missing field. The entire "deployment as data filter" architectural pattern — which is the primary use case for modeling deployments in a sensor network — is non-functional. The deployment hierarchy exists as metadata that cannot influence data access.

**LOW for deployment hierarchy management.**

The hierarchy CRUD operations (create, read, update, delete subdeployments) all work correctly. If the use case is only to organize and label deployments for display purposes, OSH is fully functional.

---

## 7. Recommended Path Forward

### 7.1 Short Term — What To Do Now

1. **Keep the Node 1 sub-deployment.** The hierarchy is correct and will be valuable when OSH adds deployment-scoped query support. Deleting it would lose correctly-modeled work.

2. **Proceed with MA-2 and MA-3 migrations.** Create additional systems on Oracle for the other array nodes, but **defer creating their sub-deployments** until deployment-scoped queries work. The migration value is in the system + datastream content, not the deployment association.

3. **Explorer client-side workaround.** When the user clicks a deployment in the tree:
   - Follow `platform@link` → system
   - Fetch that system's datastreams
   - Display them as "this deployment's data" in the UI
   - This gives the *appearance* of deployment-scoped queries without server support

4. **Document in `known-server-quirks.md`.** Add entries for `deployment@link` silently dropped and `/deployments/{id}/datastreams` returning 400.

### 7.2 Medium Term — OSH Feature Requests

These are the OSH enhancements that would unblock our architecture:

| Priority | Feature | Impact |
|----------|---------|--------|
| **P1** | Persist `deployedSystems@link` on Deployment resources | Enables deployment → system resolution without client-side scanning |
| **P1** | Implement `/deployments/{depId}/datastreams` endpoint | Enables deployment-scoped data access (the core use case) |
| **P2** | Persist `deployment@link` on DataStream resources | Enables datastream → deployment reverse navigation |
| **P2** | Implement `/deployments/{depId}/systems` endpoint | Enables deployment → systems association query |
| **P3** | `validTime` intersection on deployment-scoped queries | Enables temporal deployment window filtering |

### 7.3 Long Term — Architecture Implications

If OSH does not implement deployment-scoped queries, we have two strategic options:

**Option A: Client-side deployment resolution (current approach)**
- Explorer walks `platform@link` → system → datastreams
- Works today, but cannot do temporal scoping or cross-deployment aggregation
- Requires N+1 API calls for a string with N nodes

**Option B: Middleware proxy layer**
- Stand up a thin API layer that accepts deployment-scoped queries
- Resolves `platform@link` on the server side, aggregates results
- Returns CSAPI-conformant responses
- Higher operational complexity, but enables spec-conformant client behavior

**Option C: Switch to 52North for deployment-heavy use cases**
- 52North *does* persist `deployedSystems@link` and may support deployment-scoped endpoints
- However, 52North's Part 2 (dynamic data) support is broken for other reasons
- Not viable as a complete solution today

---

## 8. Cumulative `@link` Persistence Matrix

Combining all probes across our research history:

| `@link` Field | Resource Type | OSH Behavior | 52North Behavior | Spec Status |
|---------------|---------------|--------------|-------------------|-------------|
| `systemKind@link` | System | **Persists** ✓ | Persists ✓ | Optional |
| `platform@link` | Deployment | **Persists** ✓ | Persists ✓ | Optional |
| `deployedSystems@link` | Deployment | **Dropped** ✗ | Persists ✓ | **Required** |
| `deployment@link` | DataStream | **Dropped** ✗ | Unknown | Optional |
| `procedure@link` | DataStream | Unknown | Unknown | Optional |
| `featureOfInterest@link` | DataStream | Unknown | Unknown | Optional |
| `samplingFeature@link` | DataStream | Unknown | Unknown | Optional |
| `system@link` | DataStream | Read-only ✓ | Read-only ✓ | Read-only |

Pattern: OSH persists `@link` fields that point **from child → parent** in its internal hierarchy (`systemKind@link` on systems, `platform@link` on deployments, `system@link` on datastreams). It drops `@link` fields that represent **cross-cutting associations** (`deployedSystems@link`, `deployment@link`).

This suggests OSH's internal data model treats deployments and systems as separate, non-intersecting trees with `platform@link` as the sole bridge between them.

---

## 9. Proof Artifacts

| Artifact | Location |
|----------|----------|
| Creation script | `scripts/create_node1_subdeployment.py` |
| Probe output (terminal) | Documented in §2.2 above |
| Node 1 on Oracle | `GET https://os4csapi-osh.duckdns.org/sensorhub/api/deployments/043g` |
| String Alpha (cleaned) | `GET https://os4csapi-osh.duckdns.org/sensorhub/api/deployments/0430` |
| Prior conformance probe | [OSH_DeployedSystems_Conformance_Probe.md](OSH_DeployedSystems_Conformance_Probe.md) |
| Prior design pattern analysis | [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) |

---

## 10. Conclusion

The Node 1 sub-deployment was created successfully. The deployment hierarchy is structurally correct and well-modeled. But OSH's inability to persist `deployment@link` on datastreams — combined with the already-known absence of `deployedSystems@link` persistence and deployment-scoped query endpoints — means the deployment tree is navigational metadata only. It cannot filter, scope, or contextualize observation data.

This is the cumulative picture of a **three-mechanism failure**: every standard-defined path from "deployment" to "data" is broken on OSH. The only working link is `platform@link` (deployment → system), which enables forward navigation but not deployment-scoped data access.

Our deployment hierarchy is an investment in correct modeling that will pay off when OSH implements the missing conformance requirements. Until then, the Explorer must resolve deployment→data associations client-side via `platform@link` chains.
