# OSH SensorHub: `deployedSystems` Conformance Gap Analysis

**Date:** 2026-02-27  
**Server:** OSH SensorHub v2.x at `http://45.55.99.236:8080/sensorhub/api`  
**Standard:** [OGC API — Connected Systems — Part 1: Feature Resources 1.0.0](https://docs.ogc.org/is/23-001/23-001.html) (OGC 23-001)  
**Related Reports:**  
- [OSH Deployment Hierarchy and System Association](./OSH_Deployment_Hierarchy_and_System_Association.md)  
- [OSH Cascade Delete Experiment](./OSH_Cascade_Delete_Experiment.md)  
- [OSH Ghost Resource / Stale Index Bug](./OSH_Ghost_Resource_Stale_Index_Bug.md)

---

## 1. Executive Summary

The `deployedSystems` association is one of the most important relationships defined by the OGC Connected Systems API (CSAPI) standard. It is the **only standard mechanism** for linking Deployment resources to the System resources that participate in those deployments. Our testing reveals that the OSH SensorHub reference implementation **does not implement the `deployedSystems` endpoint**, returning HTTP 302 redirects to the Vaadin admin UI instead of API responses. This is not a minor omission — it breaks a **Required** association defined in Clause 11 of the standard and cascades into failures across multiple conformance classes including advanced filtering, recursive association resolution, and the core semantic model. The gap makes it impossible for API clients to programmatically discover which systems are deployed where, undermining the fundamental SOSA/SSN relationship between `ssn:Deployment` and `sosa:deployedSystem`.

---

## 2. What the Standard Requires

### 2.1 The `deployedSystems` Association (Clause 11.2.2)

Table 11 of the CSAPI Part 1 standard defines the associations of a Deployment resource:

| Association | SOSA/SSN Mapping | Description | Target | Obligation |
|---|---|---|---|---|
| **platform** | `sosa:deployedOnPlatform` | The platform on which the systems are deployed | A single Feature resource | Optional |
| **deployedSystems** | `sosa:deployedSystem` | The list of Systems deployed during the Deployment | A list of System resources | **Required** |
| **subdeployments** | — | The list of subdeployments | A list of Deployment resources | **Required** |

The `deployedSystems` association has **Required** obligation. Every Deployment resource representation SHALL include this association.

### 2.2 GeoJSON Encoding (Clause 19.1.6)

Table 43 of the standard specifies exactly how `deployedSystems` maps to GeoJSON:

| Association | GeoJSON Path | Encoding |
|---|---|---|
| platform | `properties/platform@link` | Weblink resolving to a System resource |
| **deployedSystems** | `properties/deployedSystems@link` | **JSON Array of links to System resources** |
| subdeployments | `links` (rel=`subdeployments`) | Weblink resolving to a Deployment resources endpoint |

The standard provides a normative example showing the expected encoding:

```json
{
  "type": "Feature",
  "id": "iv3f2kcq27gfi",
  "properties": {
    "uid": "urn:x-ogc:deployments:D001",
    "name": "Saildrone - 2017 Arctic Mission",
    "platform@link": {
      "href": "https://data.example.org/api/systems/27559?f=sml",
      "uid": "urn:x-saildrone:platforms:SD-1003",
      "title": "Saildrone SD-1003"
    },
    "deployedSystems@link": [
      {
        "href": "https://data.example.org/api/systems/41548?f=sml",
        "uid": "urn:x-saildrone:sensors:temp01",
        "title": "Air Temperature Sensor"
      },
      {
        "href": "https://data.example.org/api/systems/36584",
        "uid": "urn:x-saildrone:sensors:wind01",
        "title": "Wind Sensor"
      }
    ]
  }
}
```

### 2.3 Reverse Navigation: System → Deployments (Clause 11.4.3)

The standard also requires the reverse direction — from a System to its Deployments:

> **Requirement /req/deployment/ref-from-system:**  
> - The `deployments` association in a System resource representation SHALL be implemented as a link to a Deployment resources endpoint at path `{api_root}/systems/{sysId}/deployments`.  
> - The endpoint SHALL only expose the Deployment resources where the System with ID sysId was deployed.

Table 5 of the standard defines the System's `deployments` association:

| Association | SOSA/SSN Mapping | Description | Obligation |
|---|---|---|---|
| deployments | `sosa:hasDeployment` | The Deployments that the System is part of | Optional |

### 2.4 Recursive Association Resolution (Clause 12.6)

When a Deployment has subdeployments, the standard requires that the `deployedSystems` association **recursively aggregates** systems from all subdeployments:

> **Requirement /req/subdeployment/recursive-assoc (Table 13):**  
> - `deployedSystems`: The Systems deployed during the Deployment **and all its subdeployments, recursively**.

This is critical for hierarchical deployment models. A parent deployment (e.g., "Field Campaign 2026") should return all systems deployed across its entire tree of subdeployments.

### 2.5 Advanced Filtering Dependencies (Clause 16.6)

Multiple advanced filtering capabilities depend on the `deployedSystems` association:

| Filter | Requirement ID | Behavior |
|---|---|---|
| `?system={id}` | `/req/advanced-filtering/deployment-by-system` | Find deployments where a specific system is deployed |
| `?observedProperty={id}` | `/req/advanced-filtering/deployment-by-obsprop` | Find deployments by observed property (via deployedSystems) |
| `?controlledProperty={id}` | `/req/advanced-filtering/deployment-by-controlprop` | Find deployments by controlled property (via deployedSystems) |

All three filters require resolving `deployedSystems` to function. From Annex A abstract test `/conf/advanced-filtering/deployment-by-obsprop`:

> "Retrieve all deployed systems by issuing an HTTP GET request at `{deploymentCanonicalUrl}/deployedSystems?recursive=true`. For each Deployed System resource in the returned collection: Retrieve the system description..."

Without `deployedSystems`, **none of these queries can work**.

---

## 3. What the Server Actually Does

### 3.1 The `deployedSystems` Endpoint Returns HTTP 302

Testing the endpoint on multiple deployments:

```http
GET /sensorhub/api/deployments/0480/deployedSystems HTTP/1.1
Authorization: Basic b2djOm9nYw==

HTTP/1.1 302 Found
Location: http://45.55.99.236:8080/sensorhub
```

Following the redirect leads to the Vaadin admin landing page — not an API response:

```html
<!doctype html>
<html>
  <head><title>OpenSensorHub Landing Page</title></head>
  <body>
    <div id="sensorhub-470871803" class="v-app sensorhub landingui">
      <noscript>You have to enable javascript...</noscript>
    </div>
  </body>
</html>
```

This behavior was confirmed across **all deployment resources** on the server:

| Deployment ID | Name | `/deployedSystems` Result |
|---|---|---|
| `0480` | Demo - Field Campaign 2026 | HTTP 302 → Vaadin |
| `048g` | Demo - North Site Deployment | HTTP 302 → Vaadin |
| `049g` | Conference Room 3A — Single Array | HTTP 302 → Vaadin |
| `04a0` | Campus Perimeter — 3-Array Triangulation | HTTP 302 → Vaadin |
| `04cg` | AOI Deployment | HTTP 302 → Vaadin |
| `04d0` | Network Deployment | HTTP 302 → Vaadin |

**Every deployment returns the same 302 redirect.** The `/deployedSystems` sub-resource endpoint is simply not implemented.

### 3.2 The `deployedSystems@link` Property Is Not Returned

When retrieving a deployment resource individually, the `deployedSystems@link` property is absent from the GeoJSON representation even when a `platform@link` is present:

```json
{
  "type": "Feature",
  "id": "049g",
  "properties": {
    "uid": "urn:x-odas:deployment:office-array-001",
    "featureType": "http://www.w3.org/ns/sosa/Deployment",
    "name": "Conference Room 3A — Single Array Deployment",
    "platform@link": {
      "href": "http://45.55.99.236:8080/sensorhub/api/systems/04fg",
      "rel": "platform",
      "title": "ODAS — XMOS xCORE-200 Microphone Array Board #001"
    }
  }
}
```

Note: `platform@link` IS preserved and returned (the server correctly stores it). But `deployedSystems@link` is **completely absent** from every deployment response.

### 3.3 The `deployedSystems@link` Property Is Silently Stripped on Write

We previously documented (in [OSH_Deployment_Hierarchy_and_System_Association.md](./OSH_Deployment_Hierarchy_and_System_Association.md)) that when a deployment is created or replaced via HTTP PUT with a `deployedSystems@link` array in the payload, **the server silently strips the property**. It is accepted without error but never stored or returned.

```
PUT /sensorhub/api/deployments/049g HTTP/1.1
Content-Type: application/geo+json

{
  "properties": {
    "platform@link": { "href": "...", "uid": "...", "title": "..." },
    "deployedSystems@link": [
      { "href": "http://45.55.99.236:8080/sensorhub/api/systems/04fg", "title": "Array Board" }
    ]
  }
}

→ HTTP 204 No Content (accepted)
→ Subsequent GET: platform@link present, deployedSystems@link ABSENT
```

### 3.4 Reverse Navigation Also Fails

The System → Deployments reverse navigation endpoint is equally non-functional:

```http
GET /sensorhub/api/systems/04fg/deployments HTTP/1.1

HTTP/1.1 302 Found
Location: http://45.55.99.236:8080/sensorhub
```

No System resource includes a `deployments` link in its HATEOAS `links` array either.

### 3.5 Server Conformance Declaration

Despite the above failures, the server's `/conformance` endpoint declares conformance to both the Deployment and Subdeployment requirements classes:

```
http://www.opengis.net/spec/ogcapi-connectedsystems-1/1.0/conf/deployment
http://www.opengis.net/spec/ogcapi-connectedsystems-1/1.0/conf/subdeployment
```

This is an **incorrect conformance claim**. Per Clause 11.2.2, the `deployedSystems` association has Required obligation and must be implemented as part of the Deployment conformance class. The declared conformance should either be qualified (partial) or the endpoint should be implemented.

---

## 4. Impact Analysis

### 4.1 Which Systems Are Deployed Where? — UNANSWERABLE

The fundamental question driving the SOSA/SSN Deployment concept is: *"Which systems participated in which deployments?"* Without `deployedSystems`, this question has **no API answer**.

A client browsing a Deployment resource sees:
- ✅ Name, description, location, validTime
- ✅ Subdeployments (hierarchy)
- ✅ Platform reference (`platform@link`)  
- ❌ **Deployed Systems — always empty/missing**

### 4.2 Broken Bidirectional Navigation

The CSAPI standard defines a bidirectional relationship:

```
System  ──sosa:hasDeployment──▶  Deployment
                                    │
Deployment ──sosa:deployedSystem──▶  System
```

Both directions fail:
- `GET /deployments/{id}/deployedSystems` → 302 redirect
- `GET /systems/{id}/deployments` → 302 redirect
- No `deployments` link in System HATEOAS links
- No `deployedSystems@link` property in Deployment JSON

The relationship between Systems and Deployments is **completely severed**.

### 4.3 Cascading Query Failures

Without `deployedSystems`, the following standard-defined queries cannot function:

1. **"Find all deployments involving system X"** — `?system={id}` filter (Req 48)
2. **"Find deployments observing temperature"** — `?observedProperty={id}` filter (Req 50)
3. **"Find deployments controlling valves"** — `?controlledProperty={id}` filter (Req 51)
4. **Recursive deployment aggregation** — parent deployment showing all systems across subdeployments (Req 23)

These queries are defined in the Advanced Filtering conformance class, but they fundamentally depend on the `deployedSystems` association being resolvable.

### 4.4 Impact on CSAPI Explorer

In our CSAPI Explorer demo application, the Deployments detail page includes a "Deployed Systems" panel that always shows **"0 — None found"** for every deployment on this server. The data model diagram cannot render the `Deployment → System` edge with live data. This makes the deployment section of the Explorer appear incomplete despite full standard coverage in the client code.

### 4.5 Impact on Operational Use Cases

For our ODAS C-UAS acoustic sensor demo, we have:
- 3 Deployments (single-array, campus triangulation, network hierarchy)
- Each deployment has a `platform@link` pointing to the XMOS microphone array system
- But the `deployedSystems` relationship is invisible through the API

This means an operational query like *"Which sensors are currently deployed at the campus perimeter?"* cannot be answered through standard API navigation. A client would need to scan all deployments and extract `platform@link` as a workaround — which only covers the platform, not the full set of deployed subsystems (the 7 microphone sensors, the DSP processing pipeline, etc.).

---

## 5. Root Cause Analysis

### 5.1 The 302 Redirect Pattern

The HTTP 302 redirect to `/sensorhub` (the Vaadin admin UI root) is the server's default behavior for **any unrecognized sub-resource path**. This is the same pattern observed for other unimplemented endpoints. The server's servlet dispatcher does not have a handler registered for the `/deployments/{id}/deployedSystems` path, so the request falls through to the default Vaadin redirect.

### 5.2 Likely Implementation Status

Based on the evidence:

1. **The sub-resource endpoint** (`/deployments/{id}/deployedSystems`) is **not implemented** — no servlet handler registered
2. **The `deployedSystems@link` property** is **not stored** — silently stripped on ingestion
3. **The reverse navigation endpoint** (`/systems/{id}/deployments`) is **not implemented**
4. **The internal data model** may not have a table/mapping for the system-deployment association

The `platform@link` property IS stored and returned correctly, suggesting the server's deployment data model has a `platform` foreign-key field but lacks a many-to-many `deployedSystems` junction table.

### 5.3 Conformance Class Assessment

| Conformance Class | URI | Requirement | Status |
|---|---|---|---|
| Deployment Features | `/conf/deployment` | `deployedSystems` Required association | ❌ FAIL |
| Deployment Features | `/conf/deployment` | `/req/deployment/ref-from-system` | ❌ FAIL |
| Subdeployments | `/conf/subdeployment` | `/req/subdeployment/recursive-assoc` | ❌ FAIL |
| Advanced Filtering | `/conf/advanced-filtering` | `deployment-by-system` | ❌ FAIL |
| Advanced Filtering | `/conf/advanced-filtering` | `deployment-by-obsprop` | ❌ FAIL |
| Advanced Filtering | `/conf/advanced-filtering` | `deployment-by-controlprop` | ❌ FAIL |
| GeoJSON Format | `/conf/geojson` | `deployment-mappings` (Table 43) | ❌ FAIL |

---

## 6. Workarounds

### 6.1 `platform@link` as a Partial Proxy

The server does preserve `platform@link`, which identifies the **platform** (top-level system) on which systems are deployed. For simple scenarios where a single platform hosts sensors, this provides partial information:

```json
"platform@link": {
  "href": "http://server/api/systems/04fg",
  "uid": "urn:x-odas:platform:xcore-mic-board-001",
  "title": "ODAS — XMOS xCORE-200 Microphone Array Board #001"
}
```

Limitations:
- Only tells you the **platform**, not the individual sensors/subsystems deployed
- Per the SOSA ontology, `deployedOnPlatform` and `deployedSystem` are **different relationships** — the platform is where the deployment happens, the deployed systems are what gets deployed
- A deployment may involve multiple independent systems (not just one platform)
- `platform@link` is Optional per the standard, so not guaranteed to be present

### 6.2 Client-Side Join via Subsystem Discovery

A more complete workaround involves:

1. Read `platform@link` from the deployment to get the platform system ID
2. Fetch `GET /systems/{platformId}/subsystems?recursive=true` to discover all subsystems
3. Infer that all subsystems of the platform are "deployed" during this deployment

This works for our ODAS scenario but is **semantically incorrect** — subsystems of a platform are permanently attached components, not deployment-scoped associations. A platform might have subsystems that are NOT deployed during a particular deployment (e.g., a disabled sensor).

### 6.3 External State Management

For applications requiring system-deployment mappings, the association can be maintained client-side:

- Store `{deploymentId, systemId, role}` tuples in a local database
- Populate during ingestion/bootstrap
- Accept that the mapping is not accessible through the standard API

This is the approach we currently use in CSAPI Explorer's bootstrap scripts, but it breaks the standard's principle of API-discoverable relationships.

---

## 7. Recommendations

### 7.1 For the OSH SensorHub Team

1. **Implement the `/deployments/{id}/deployedSystems` endpoint** — This is a Required association per the standard. The endpoint should return a System resources collection with GeoJSON format support.

2. **Store and return `deployedSystems@link`** — When a Deployment is created or replaced with a `deployedSystems@link` array, persist the links and include them in subsequent GET responses.

3. **Implement the `/systems/{id}/deployments` endpoint** — The reverse navigation endpoint for System → Deployments.

4. **Update conformance claims** — If implementation is deferred, the `/conf/deployment` conformance claim should be qualified or removed until the full requirements class is implemented.

### 7.2 For CSAPI Explorer / Client Developers

1. **Use `platform@link` as a fallback** — When `deployedSystems` is empty, display the platform link as a related system with a note that full deployed system enumeration is not available.

2. **Detect and surface the gap** — Show a user-visible indicator (e.g., "Server does not support deployedSystems") rather than just showing "0 — None found".

3. **Implement subsystem inference** — As a best-effort, resolve `platform@link` → subsystems to populate the deployed systems panel.

### 7.3 For the OGC CSAPI Standard

1. **Consider a dedicated conformance class** for `deployedSystems` — Currently, it is bundled into the Deployment Features requirements class. Since it involves a cross-resource-type relationship (Deployment ↔ System) that is significantly more complex to implement than simple deployment CRUD, a separate conformance class (similar to how `subsystems` are separated from `system`) would allow servers to declare partial compliance more honestly.

2. **Add conformance test for `deployedSystems@link` persistence** — The Abstract Test Suite (Annex A.5) tests the deployment endpoint and GeoJSON schema, but does not explicitly test that `deployedSystems@link` round-trips through a PUT/GET cycle.

---

## 8. Comparison with Working Associations

| Association | Write Support | Read Support | Endpoint | Status |
|---|---|---|---|---|
| `subsystems` | ✅ POST to parent | ✅ HATEOAS link | `/systems/{id}/subsystems` | **Working** |
| `subdeployments` | ✅ POST to parent | ✅ HATEOAS link | `/deployments/{id}/subdeployments` | **Working** |
| `platform@link` | ✅ PUT preserves | ✅ Returned in JSON | inline property | **Working** |
| `systemKind@link` | ✅ PUT preserves | ✅ Returned in JSON | inline property | **Working** |
| `samplingFeatures` | ✅ POST to parent | ✅ HATEOAS link | `/systems/{id}/samplingFeatures` | **Working** |
| `datastreams` | ✅ POST to parent | ✅ HATEOAS link | `/systems/{id}/datastreams` | **Working** |
| **`deployedSystems`** | ❌ Silently stripped | ❌ Never returned | ❌ 302 redirect | **NOT IMPLEMENTED** |
| **`deployments` (from System)** | ❌ N/A | ❌ No link | ❌ 302 redirect | **NOT IMPLEMENTED** |

The pattern is clear: sub-resource relationships that use the **parent/child creation pattern** (POST to `/{parentId}/{childType}`) work correctly. The `deployedSystems` relationship is different — it's a **many-to-many association** between two independent resource types (Deployments and Systems) that both exist at the top level. This cross-cutting association pattern appears to be the one the server has not yet implemented.

---

## 9. Conclusion

The missing `deployedSystems` support is the **most significant conformance gap** we have identified in OSH SensorHub's CSAPI implementation. Unlike the ghost resource bug (a data integrity issue) or the cascade delete quirks (edge-case behavior), this gap removes an entire semantic relationship from the API surface. The `sosa:deployedSystem` relationship is central to the SOSA/SSN ontology's deployment model — it is the mechanism by which the physical world (sensors deployed at locations) connects to the observation data model. Without it, deployments are metadata islands: they have names, descriptions, locations, and hierarchy, but they cannot answer the question they exist to answer — *"What systems are deployed here?"*

This gap should be prioritized as a **blocking issue** for any application that needs to model real-world sensor deployment scenarios through the standard API.

---

## Appendix A: Test Commands

```bash
# Test deployedSystems endpoint (all return HTTP 302)
curl -s -u ogc:ogc -v "http://45.55.99.236:8080/sensorhub/api/deployments/0480/deployedSystems" 2>&1 | grep "HTTP/"
curl -s -u ogc:ogc -v "http://45.55.99.236:8080/sensorhub/api/deployments/048g/deployedSystems" 2>&1 | grep "HTTP/"
curl -s -u ogc:ogc -v "http://45.55.99.236:8080/sensorhub/api/deployments/049g/deployedSystems" 2>&1 | grep "HTTP/"

# Test reverse navigation (System → Deployments, also returns 302)
curl -s -u ogc:ogc -v "http://45.55.99.236:8080/sensorhub/api/systems/04fg/deployments" 2>&1 | grep "HTTP/"

# Verify platform@link IS returned (works correctly)
curl -s -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/deployments/049g" | python -m json.tool | grep -A3 "platform@link"

# Check server conformance claims
curl -s -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/conformance" | python -m json.tool | grep deployment
```

## Appendix B: Relevant Standard Sections

| Section | Topic | URL |
|---|---|---|
| Clause 11.2.2 | Deployment Associations (Table 11) | [23-001 §11.2.2](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-resource) |
| Clause 11.4.3 | Nested Deployment Endpoint (System→Deployments) | [23-001 §11.4.3](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-resources-endpoint) |
| Clause 12.6 | Recursive Deployment Associations (Table 13) | [23-001 §12.6](https://docs.ogc.org/is/23-001/23-001.html#clause-subdeployments) |
| Clause 16.6.3 | Deployed System Filter | [23-001 §16.6.3](https://docs.ogc.org/is/23-001/23-001.html) |
| Clause 19.1.6 | GeoJSON Deployment Encoding (Table 43) | [23-001 §19.1.6](https://docs.ogc.org/is/23-001/23-001.html) |
| Annex A.5 | Deployment Features Conformance Tests | [23-001 Annex A.5](https://docs.ogc.org/is/23-001/23-001.html) |
| Annex A.6 | Subdeployment Conformance Tests | [23-001 Annex A.6](https://docs.ogc.org/is/23-001/23-001.html) |
