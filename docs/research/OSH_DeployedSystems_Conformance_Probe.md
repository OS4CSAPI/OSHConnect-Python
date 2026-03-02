# OSH `deployedSystems` Conformance Probe & Deployment Scoping Analysis

| Field | Value |
|---|---|
| **Date** | 2026-03-02 |
| **Author** | Claude (Opus 4.6) |
| **Status** | Empirical Probe Results + Design Analysis |
| **Scope** | `deployedSystems@link` persistence on OSH, `deployment@link` observation scoping, structural implications |
| **Follows** | [AZ-MA-2/MA-3 Migration Procedure Analysis](AZ-MA-2_MA-3_Migration_Procedure_Analysis.md) |
| **Follows** | [CSAPI Deployment Modeling Standards Conformance](CSAPI_Deployment_Modeling_Standards_Conformance.md) |

---

## 1  Background

The preceding [standards conformance analysis](CSAPI_Deployment_Modeling_Standards_Conformance.md) identified that the OGC Connected Systems API standard uses `deployedSystems` as the primary mechanism for associating Systems with Deployments, and raised the question of whether OSH (OpenSensorHub) actually supports this on the write path.

Both Claude and ChatGPT (o3) converged on the same action item: **run a conformance probe** — POST a deployment with `deployedSystems@link` containing multiple systems, GET it back, and see what survives.

This document reports the probe results and their implications for the ODAS 3-node deployment structure.

---

## 2  Probe Methodology

The probe was executed live against the Oracle Cloud OSH instance (`os4csapi-osh.duckdns.org`) on 2026-03-02.

**Steps:**
1. Identify 3 existing systems on Oracle (SET-A `040g`, Monitoring Site Node 1 `0410`, Relay `041g`)
2. POST a test deployment with `deployedSystems@link` containing all 3 systems
3. GET the deployment back in GeoJSON format — check for `deployedSystems@link` in properties
4. GET the deployment back in SensorML-JSON format — check for `deployedSystems`
5. GET the nested endpoints (`/deployments/{id}/deployedSystems`, `/deployments/{id}/systems`)
6. DELETE the test deployment

**Payload sent:**
```json
{
  "type": "Feature",
  "geometry": { "type": "Point", "coordinates": [-110.25, 31.64] },
  "properties": {
    "featureType": "sosa:Deployment",
    "uid": "urn:test:probe:deployed-systems-conformance:001",
    "name": "PROBE: deployedSystems conformance test",
    "validTime": ["2026-03-01T00:00:00Z", ".."],
    "deployedSystems@link": [
      { "href": "/sensorhub/api/systems/040g", "uid": "urn:os4csapi:system:set:ft-huachuca:001", "type": "application/geo+json" },
      { "href": "/sensorhub/api/systems/0410", "uid": "urn:os4csapi:system:monitoring-site-node:ft-huachuca:001", "type": "application/geo+json" },
      { "href": "/sensorhub/api/systems/041g", "uid": "urn:os4csapi:system:relay:vhf-repeater:ft-huachuca:001", "type": "application/geo+json" }
    ]
  }
}
```

---

## 3  Probe Results

| Test | HTTP Status | Result |
|---|---|---|
| POST deployment with `deployedSystems@link` (3 systems) | **201 Created** | Accepted — but field silently dropped |
| GET back (GeoJSON) — check `deployedSystems@link` | **200** | **❌ Not present.** Properties contain only: `uid`, `featureType`, `name`, `description`, `validTime` |
| GET back (SensorML-JSON) — check `deployedSystems` | **200** | **❌ Not present.** Top-level keys: `type`, `id`, `geometry`, `properties`, `links` |
| GET `/deployments/{id}/deployedSystems` | **400** | `"Invalid resource name: 'deployedSystems'"` |
| GET `/deployments/{id}/systems` | **400** | `"Invalid resource name: 'systems'"` |
| DELETE test deployment | **204** | Cleaned up successfully |

### 3.1  Interpretation

**OSH does not implement `deployedSystems` at any level:**

1. **Write path**: OSH accepts the POST without error but **silently discards** the `deployedSystems@link` array. It does not reject the field, validate it, or persist it.

2. **Read path (inline)**: Neither GeoJSON nor SML-JSON responses include `deployedSystems` or `deployedSystems@link` in the deployment representation.

3. **Read path (nested endpoint)**: The standard-defined nested endpoint (`/deployments/{id}/deployedSystems` or `/deployments/{id}/systems`) is **not implemented** — OSH returns HTTP 400 "Invalid resource name."

This confirms the implementation gap both analyses predicted. The standard requires `deployedSystems` as a core deployment association; OSH doesn't support it at all.

---

## 4  Consequence: Subdeployments Are Required, Not Optional

The preceding [standards conformance analysis](CSAPI_Deployment_Modeling_Standards_Conformance.md) outlined two models:

- **Flat model**: One STRING deployment with `deployedSystems = [MA-1, MA-2, MA-3]`
- **Subdeployment model**: Per-node subdeployments under STRING, each with `platform@link` → its system

ChatGPT (o3) proposed the flat model as the "minimum viable structure" and framed subdeployments as a "works-today workaround." **The probe eliminates the flat model.** Since OSH discards `deployedSystems@link`, the only mechanism to associate a system with a deployment is `platform@link` on a subdeployment.

Per-node subdeployments are not a workaround — they are the **only available path** on OSH.

---

## 5  Why `deployment@link` on Datastreams Is a Key Design Factor

Beyond system association, the deployment structure directly determines **observation query scoping** via the `deployment@link` field on datastreams. This was not addressed in the previous reports and is critical for the design decision.

### 5.1  What Is `deployment@link`?

Every datastream can carry a `deployment@link` field — a pointer declaring which deployment produced its observations. From AZ-MA-1's actual backup data (`ds_07h02.json`):

```json
{
  "name": "AZ-MA-1 Track Updates",
  "system@link":     { "href": "/sensorhub/api/systems/04ng" },
  "deployment@link": { "href": "/sensorhub/api/deployments/04dg" },
  "procedure@link":  { "href": "/sensorhub/api/procedures/04c0" },
  ...
}
```

Each datastream links to three things:
- **`system@link`** — which system produced it (AZ-MA-1)
- **`procedure@link`** — which algorithm generated it (Processing Chain)
- **`deployment@link`** — which deployment it belongs to (currently points to String Alpha)

### 5.2  How CSAPI Part 2 Uses It

The standard defines **nested endpoints on deployments** that use `deployment@link` to filter data:

```
GET /deployments/{id}/datastreams    → datastreams whose deployment@link points here
GET /deployments/{id}/observations   → observations from those datastreams
```

This is the **primary query mechanism for operationally scoped data**. When someone asks *"What is String Alpha seeing right now?"*, the answer is:

```
GET /deployments/{string-alpha}/observations
```

The deployment is the operational lens through which data is viewed.

### 5.3  Impact on the Two Structural Models

#### Scenario A: One STRING deployment — all datastreams point to it

```
STRING Alpha (deployment)
  ├── MA-1 Track Updates      → deployment@link → STRING
  ├── MA-1 SSL                → deployment@link → STRING
  ├── MA-1 Health             → deployment@link → STRING
  ├── MA-2 Track Updates      → deployment@link → STRING
  ├── MA-2 SSL                → deployment@link → STRING
  ├── MA-2 Health             → deployment@link → STRING
  ├── MA-3 Track Updates      → deployment@link → STRING
  ├── MA-3 SSL                → deployment@link → STRING
  └── MA-3 Health             → deployment@link → STRING
```

Query behavior:
- `GET /deployments/{string}/datastreams` → **21 datastreams**, all nodes mixed
- `GET /deployments/{string}/observations` → **all observations from all 3 nodes**, mixed
- *"Show me only Node 2's health"* → must client-side filter by system ID, or use a compound query (`?system={ma-2-id}`) **if the server supports it**
- *"Compare Node 1 vs Node 3 detection rates"* → must fetch everything and split client-side

#### Scenario B: Per-node subdeployments — each node's datastreams point to its own

```
STRING Alpha (deployment)
  ├── Node 1 (sub-deployment)
  │     ├── MA-1 Track Updates      → deployment@link → Node 1
  │     ├── MA-1 SSL                → deployment@link → Node 1
  │     └── MA-1 Health             → deployment@link → Node 1
  ├── Node 2 (sub-deployment)
  │     ├── MA-2 Track Updates      → deployment@link → Node 2
  │     ├── MA-2 SSL                → deployment@link → Node 2
  │     └── MA-2 Health             → deployment@link → Node 2
  └── Node 3 (sub-deployment)
        ├── MA-3 Track Updates      → deployment@link → Node 3
        ├── MA-3 SSL                → deployment@link → Node 3
        └── MA-3 Health             → deployment@link → Node 3
```

Query behavior:
- `GET /deployments/{node-2}/datastreams` → **only Node 2's 7 datastreams**
- `GET /deployments/{node-2}/observations` → **only Node 2's observations**
- `GET /deployments/{string}/subdeployments` → lists all 3 nodes
- *"Show me Node 2's health"* → direct query, zero filtering
- *"Compare Node 1 vs Node 3"* → two clean queries, each returning only its node's data

> **Note:** The standard says parent deployments should recursively aggregate children's `deployedSystems` (and by extension, datastreams/observations). If OSH implements this, `GET /deployments/{string}/observations` would still return all 3 nodes' data. If not, you query each sub-deployment individually — still cleaner than client-side filtering.

### 5.4  Impact on the CSAPI Explorer and Map View

The webapp already uses deployment-scoped queries. When a user clicks a deployment in the Explorer or on the Map, it fetches that deployment's datastreams and observations:

- **Scenario A**: Clicking String Alpha shows an undifferentiated wall of 21 datastreams from 3 nodes
- **Scenario B**: The user navigates STRING → Node 2 → sees exactly Node 2's 7 datastreams

This is the difference between "deployment as a bucket" and "deployment as an operational scope."

### 5.5  The Operational Question

> **"Will anyone ever want to look at one node's data without the other two?"**

For ODAS acoustic microphone arrays, the answer is almost certainly **yes**:

- Check if a specific node's health is degrading
- Compare bearing measurements between nodes to validate triangulation
- Verify individual node calibration
- Isolate a node that's producing anomalous data
- Monitor a node's observation latency independently

These are all single-node queries that per-node subdeployments serve natively.

---

## 6  Revised Structural Recommendation

Given the probe results, the recommended structure is:

```
STRING Alpha (deployment)
  platform@link → (optional: physical site Feature)
  │
  ├── Node 1 (sub-deployment)
  │     platform@link → AZ-MA-1 system
  │     7 datastreams: deployment@link → Node 1
  │     4 control streams on Actuator subsystem
  │
  ├── Node 2 (sub-deployment)
  │     platform@link → AZ-MA-2 system
  │     7 datastreams: deployment@link → Node 2
  │     4 control streams on Actuator subsystem
  │
  └── Node 3 (sub-deployment)
        platform@link → AZ-MA-3 system
        7 datastreams: deployment@link → Node 3
        4 control streams on Actuator subsystem
```

This is:
- **Necessary** — OSH doesn't support `deployedSystems`, so `platform@link` on subdeployments is the only wiring mechanism
- **Operationally useful** — per-node `deployment@link` gives free observation scoping without client-side filtering
- **Standards-aligned** — subdeployments are a first-class CSAPI conformance class
- **Not over-engineering** — it's the minimum structure that works on the actual implementation

### 6.1  What Changes for MA-1 (Already Migrated)

1. Create "Node 1" sub-deployment under String Alpha
2. Move MA-1's `platform@link` from String Alpha down to Node 1
3. Update MA-1's 7 datastreams: `deployment@link` → Node 1 sub-deployment (instead of String Alpha)
4. Verify MA-1 observations still resolve through the Node 1 deployment scope

### 6.2  What MA-2 and MA-3 Get from Day One

- Each gets its own sub-deployment (Node 2, Node 3) created under String Alpha
- `platform@link` wired at the sub-deployment level
- All datastreams carry `deployment@link` → their own sub-deployment
- Clean per-node observation scoping from the start

---

## 7  Open Action: File OSH Bug

The probe confirms a clear conformance gap:

| Standard Requirement | OSH Behavior |
|---|---|
| `deployedSystems@link` must be persisted on POST/PUT | Silently discarded |
| GET deployment must include `deployedSystems@link` | Not returned |
| `GET /deployments/{id}/deployedSystems` endpoint must exist | Returns 400 "Invalid resource name" |

This should be filed as a bug against the OSH CSAPI implementation, referencing CSAPI Part 1 Table 11 (Deployment Associations) and the `deployedSystems` requirements class.

---

## Appendix A — Full Probe GeoJSON Response

The complete response from `GET /deployments/043g` (the test deployment) after POST with `deployedSystems@link`:

```json
{
  "type": "Feature",
  "id": "043g",
  "geometry": {
    "type": "Point",
    "coordinates": [-110.25, 31.64]
  },
  "properties": {
    "uid": "urn:test:probe:deployed-systems-conformance:001",
    "featureType": "sosa:Deployment",
    "name": "PROBE: deployedSystems conformance test",
    "description": "Temporary deployment for testing deployedSystems@link persistence. Safe to delete.",
    "validTime": ["2026-03-01T00:00:00Z", ".."]
  },
  "links": [
    { "rel": "canonical", "href": "http://os4csapi-osh.duckdns.org:8181/sensorhub/api/deployments/043g", "type": "application/json" },
    { "rel": "alternate", "title": "This deployment resource in SensorML format", "href": "http://os4csapi-osh.duckdns.org:8181/sensorhub/api/deployments/043g?f=sml3", "type": "application/sml+json" },
    { "rel": "alternate", "title": "This deployment resource in HTML format", "href": "http://os4csapi-osh.duckdns.org:8181/sensorhub/api/deployments/043g?f=html", "type": "text/html" }
  ]
}
```

Note: `deployedSystems@link` is completely absent from `properties`. The 3-system array sent on POST was silently discarded.

## Appendix B — Nested Endpoint Error Responses

```
GET /deployments/043g/deployedSystems → 400
{ "status": 400, "message": "Invalid resource name: 'deployedSystems'" }

GET /deployments/043g/systems → 400
{ "status": 400, "message": "Invalid resource name: 'systems'" }
```

Neither the standards-named endpoint (`deployedSystems`) nor the shorthand (`systems`) is recognized by OSH under the deployments resource.
