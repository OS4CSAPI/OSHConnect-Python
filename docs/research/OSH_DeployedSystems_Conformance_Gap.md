# OSH SensorHub: `deployedSystems@link` Conformance Gap Analysis

**Date:** 2026-02-27 (Revised)  
**Server:** OSH SensorHub v2.x at `http://45.55.99.236:8080/sensorhub/api`  
**Standard:** [OGC API — Connected Systems — Part 1: Feature Resources 1.0.0](https://docs.ogc.org/is/23-001/23-001.html) (OGC 23-001)  
**Related Reports:**  
- [OSH Deployment Hierarchy and System Association](./OSH_Deployment_Hierarchy_and_System_Association.md)  
- [OSH Cascade Delete Experiment](./OSH_Cascade_Delete_Experiment.md)  
- [OSH Ghost Resource / Stale Index Bug](./OSH_Ghost_Resource_Stale_Index_Bug.md)

> **Revision Note:** This report corrects the initial version published on 2026-02-27. The original report incorrectly claimed that the standard requires a `/deployments/{id}/deployedSystems` sub-resource endpoint. Upon closer reading, the standard defines `deployedSystems` as an **inline GeoJSON property** (`properties/deployedSystems@link`), _not_ as a sub-resource endpoint. The actual conformance gap is narrower but still significant: the server silently strips this inline property and never returns it.

---

## 1. Executive Summary

The `deployedSystems` association is the **only standard mechanism** for linking a Deployment resource to the System resources that participate in that deployment. In the GeoJSON encoding (Table 43), it maps to an **inline property** (`properties/deployedSystems@link`) — a JSON array of links embedded directly in the deployment's GeoJSON `properties`, the same pattern as `platform@link`.

Our testing reveals that OSH SensorHub **silently strips the `deployedSystems@link` property on write and never returns it on read**. When a deployment is created or replaced via PUT with `deployedSystems@link` in the payload, the server accepts the request without error but discards the property. Subsequent GET requests return the deployment without any `deployedSystems@link` data, even though `platform@link` in the same payload _is_ correctly persisted and returned.

Additionally, the reverse navigation endpoint (`/systems/{sysId}/deployments`, required by Requirement 17) returns HTTP 302 redirects instead of API responses.

These gaps make it impossible for API clients to programmatically discover which systems are deployed where, undermining the fundamental SOSA/SSN `sosa:deployedSystem` relationship.

---

## 2. What the Standard Requires

### 2.1 The `deployedSystems` Association (Clause 11.2.2, Table 11)

Table 11 defines the associations of a Deployment resource:

| Association | SOSA/SSN Mapping | Description | Target | Obligation |
|---|---|---|---|---|
| platform | `sosa:deployedOnPlatform` | The platform on which the systems are deployed | A single Feature resource | Optional |
| **deployedSystems** | `sosa:deployedSystem` | The list of Systems deployed during the Deployment, if any | A list of System resources | **Required** |
| subdeployments | — | The list of subdeployments | A list of Deployment resources | Required |

### 2.2 GeoJSON Encoding: Inline Property, Not an Endpoint (Clause 19.1.6, Table 43)

Table 43 specifies exactly how each Deployment association maps to GeoJSON. This is the crucial distinction:

| Association | GeoJSON Path | Encoding | Pattern |
|---|---|---|---|
| platform | `properties/platform@link` | Weblink to a System resource | **Inline property** |
| **deployedSystems** | **`properties/deployedSystems@link`** | **JSON Array of links to System resources** | **Inline property** |
| parentDeployment | `links` | Weblink to a Deployment resource | HATEOAS link |
| subdeployments | `links` | Weblink to a Deployment resources endpoint | HATEOAS link |

Key observation: `deployedSystems` uses the same pattern as `platform` — an **inline property** inside `properties`, NOT a HATEOAS link in the `links` array. There is no `ogc-rel:deployedSystems` link relation type defined in Table 3. Clause 11.4 defines only three endpoint types for deployments:

1. **Canonical resources endpoint**: `{api_root}/deployments` (Req 16)
2. **Canonical resource endpoint**: `{api_root}/deployments/{id}` (Req 14)
3. **Nested from System**: `{api_root}/systems/{sysId}/deployments` (Req 17)

There is **no** `/deployments/{id}/deployedSystems` sub-resource endpoint defined in the standard.

The standard's normative GeoJSON example shows the expected encoding:

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

### 2.3 Reverse Navigation: System → Deployments (Clause 11.4.3, Requirement 17)

The standard does define a real endpoint for the reverse direction:

> **Requirement /req/deployment/ref-from-system:**  
> - The `deployments` association in a System resource representation SHALL be implemented as a link to a Deployment resources endpoint at path `{api_root}/systems/{sysId}/deployments`.  
> - The endpoint SHALL only expose the Deployment resources where the System with ID sysId was deployed.

This is conditional: it only applies when the server implements both the System Features and Deployment Features requirements classes _and_ provides the `deployments` association in System representations. The `deployments` association itself is Optional per Table 5.

### 2.4 Recursive Association Resolution (Clause 12.6, Table 13)

When a Deployment has subdeployments, the `deployedSystems` inline property should aggregate systems from the entire hierarchy:

| Association | Rule |
|---|---|
| **deployedSystems** | The Systems deployed during the Deployment **and all its subdeployments, recursively**. |

This means the `deployedSystems@link` array in a parent deployment's GeoJSON should include systems from all child and grandchild deployments, not just directly associated ones.

### 2.5 Standard Ambiguity: Conformance Test Procedures

While the normative encoding requirements (Tables 43, 52) consistently define `deployedSystems` as an inline property, some **conformance test procedures** in Annex A reference a sub-resource URL pattern:

- **A.10 `/conf/advanced-filtering/deployment-by-system`**: _"Retrieve all deployed systems by issuing an HTTP GET request at `{deploymentCanonicalUrl}/deployedSystems?recursive=true`."_

- **A.10 `/conf/advanced-filtering/deployment-by-obsprop`**: Same pattern.

- **A.6 `/conf/subdeployment/recursive-assoc`**: _"If the Deployment resource contains a link with relation type deployedSystems, verify that all deployed systems are returned. Issue an HTTP GET request to the link URL."_

These test procedures suggest the standard authors may have intended a sub-resource endpoint (or at minimum a HATEOAS link) for `deployedSystems`, even though the normative encoding tables only define an inline property. This is an **inconsistency between the encoding requirements and the conformance test procedures** that should be raised with the OGC CSAPI working group.

---

## 3. What the Server Actually Does

### 3.1 The `deployedSystems@link` Inline Property Is Silently Stripped

**This is the core issue.** When a deployment is created or replaced via HTTP PUT with `deployedSystems@link` in the GeoJSON payload, the server accepts the request (HTTP 204) but discards the property.

```http
PUT /sensorhub/api/deployments/049g HTTP/1.1
Content-Type: application/geo+json

{
  "properties": {
    "platform@link": {
      "href": "http://45.55.99.236:8080/sensorhub/api/systems/04fg",
      "uid": "urn:x-odas:platform:xcore-mic-board-001",
      "title": "ODAS — XMOS xCORE-200 Microphone Array Board #001"
    },
    "deployedSystems@link": [
      {
        "href": "http://45.55.99.236:8080/sensorhub/api/systems/04fg",
        "title": "XMOS Array Board"
      }
    ]
  }
}
```

Response: HTTP 204 No Content (accepted).

Subsequent GET:

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

`platform@link` is preserved. `deployedSystems@link` is **gone** — silently discarded.

### 3.2 No Deployment Has `deployedSystems@link` in Its Response

Across all 18 deployments on the server, none returns `deployedSystems@link` in any form:

| Deployment ID | Name | `platform@link` | `deployedSystems@link` |
|---|---|---|---|
| `0480` | Demo - Field Campaign 2026 | — | ❌ Absent |
| `048g` | Demo - North Site Deployment | — | ❌ Absent |
| `049g` | Conference Room 3A — Single Array | ✅ Present | ❌ Absent |
| `04a0` | Campus Perimeter — 3-Array Triangulation | ✅ Present | ❌ Absent |
| `04cg` | AOI Deployment | — | ❌ Absent |

### 3.3 Reverse Navigation Also Fails (Requirement 17)

The System → Deployments endpoint required by Req 17 returns HTTP 302:

```http
GET /sensorhub/api/systems/04fg/deployments HTTP/1.1
Authorization: Basic b2djOm9nYw==

HTTP/1.1 302 Found
Location: http://45.55.99.236:8080/sensorhub
```

No System resource on the server includes an `ogc-rel:deployments` link in its HATEOAS `links` array. The reverse direction is completely non-functional.

### 3.4 Non-Standard Sub-Resource Paths Return 302

For completeness: accessing `/deployments/{id}/deployedSystems` or `/deployments/{id}/systems` also returns HTTP 302 → Vaadin landing page. While the standard doesn't require these endpoints (see §2.2 above), the 302-to-Vaadin pattern is the server's default response for _any_ unrecognized path, confirming there is no handler for deployment-system association queries.

---

## 4. Impact Analysis

### 4.1 The Deployment ↔ System Link Is Invisible

The fundamental question driving the SOSA/SSN Deployment concept is: _"Which systems participated in which deployments?"_ Without `deployedSystems@link`, this question has **no API answer**.

A client browsing a Deployment sees:
- ✅ Name, description, location, validTime
- ✅ Subdeployments (hierarchy)
- ✅ Platform reference (`platform@link`)
- ❌ **Deployed Systems — always absent**

### 4.2 Broken Bidirectional Navigation

The standard defines a bidirectional relationship:

```
Deployment ──deployedSystems@link──▶ System(s)   [inline property — STRIPPED]
System     ──/systems/{id}/deployments──▶ Deployment(s)  [Req 17 — 302 REDIRECT]
```

Both directions are non-functional. The association is completely severed.

### 4.3 Impact on CSAPI Explorer Demo

Our Explorer demo's "Deployed Systems" panel previously attempted to hit a `/{id}/systems` sub-resource endpoint that the standard doesn't define. The server returned 302 → HTML, which the fetch layer treated as success with garbage data → panel showed 0 items.

The fix (implemented alongside this report revision) reads from `deployedSystems@link` inline properties first, with `platform@link` as a fallback for servers like OSH that strip `deployedSystems@link`.

### 4.4 Impact on Operational Use Cases

For our ODAS C-UAS acoustic sensor demo:
- 3 Deployments each have `platform@link` pointing to their XMOS microphone array system
- But `deployedSystems@link` (which should list the individual microphone sensors, DSP subsystems, etc.) is always empty
- An operational query like _"Which sensors are actively deployed at the campus perimeter?"_ cannot be answered through the standard inline property

---

## 5. Root Cause Analysis

### 5.1 The Property Persistence Pattern

The server's GeoJSON parser appears to handle `@link` properties selectively:

| Property | Persisted | Returned | Pattern |
|---|---|---|---|
| `platform@link` | ✅ Yes | ✅ Yes | Single object link |
| `systemKind@link` | ✅ Yes | ✅ Yes | Single object link |
| `sampledFeature@link` | ✅ Yes | ✅ Yes | Single object link |
| **`deployedSystems@link`** | ❌ No | ❌ No | **Array of object links** |

The distinguishing factor appears to be that `deployedSystems@link` is a **JSON Array** of links, while the properties that work (`platform@link`, `systemKind@link`) are **single objects**. The server's GeoJSON ingestion pipeline likely does not handle `@link` properties with array values.

### 5.2 Conformance Assessment

| Requirement | Standard Section | What It Requires | Status |
|---|---|---|---|
| Deployment associations (Table 11) | §11.2.2 | `deployedSystems` = Required | ❌ FAIL (stripped on write, absent on read) |
| GeoJSON deployment mappings (Table 43) | §19.1.6 | `properties/deployedSystems@link` | ❌ FAIL (never returned) |
| System → Deployments endpoint (Req 17) | §11.4.3 | `{api_root}/systems/{sysId}/deployments` | ❌ FAIL (302 redirect) |
| Recursive associations (Table 13) | §12.6 | `deployedSystems` aggregated across subdeployments | ❌ FAIL (no data to aggregate) |
| GeoJSON deployment schema (Req 83) | §19.1.6 | Response valid against `deployment.json` schema | ⚠️ Partial (schema may allow empty) |

---

## 6. Workarounds

### 6.1 `platform@link` as a Partial Proxy (Implemented)

The server preserves `platform@link`, which identifies the top-level system (platform) on which the deployment operates:

```json
"platform@link": {
  "href": "http://server/api/systems/04fg",
  "rel": "platform",
  "title": "ODAS — XMOS xCORE-200 Microphone Array Board #001"
}
```

Our CSAPI Explorer demo now reads this as a fallback when `deployedSystems@link` is absent, resolving the platform system and displaying it in the Deployed Systems panel with a note that the data comes from `platform@link` rather than the standard `deployedSystems@link` property.

**Limitations:**
- `platform@link` identifies where the deployment happens (the platform), not _what_ is deployed (the sensors/subsystems)
- Per SOSA ontology, `sosa:deployedOnPlatform` ≠ `sosa:deployedSystem` — they are semantically different relations
- Only provides a single system reference, not the full list of deployed subsystems
- `platform@link` is Optional per the standard, so not guaranteed to be present

### 6.2 Client-Side Subsystem Inference

A more detailed workaround extends 6.1:

1. Resolve `platform@link` to get the platform system ID
2. Fetch `GET /systems/{platformId}/subsystems?recursive=true`
3. Infer that platform + subsystems are the "deployed systems"

This is semantically imprecise (subsystems are permanent components, not deployment-scoped) but useful for display purposes.

---

## 7. Recommendations

### 7.1 For the OSH SensorHub Team

1. **Persist and return `deployedSystems@link`** — When a Deployment is created or replaced with a `deployedSystems@link` array in the GeoJSON payload, the server should store the array of links and include them in subsequent GET responses, just as it does for `platform@link`.

2. **Implement the `/systems/{sysId}/deployments` endpoint** (Req 17) — This is an explicitly required endpoint when both System and Deployment features are supported.

3. **Clarify array `@link` property handling** — The issue may be a general parser limitation with array-valued `@link` properties. If so, other array `@link` properties (e.g., links to features of interest) may be affected too.

### 7.2 For CSAPI Explorer / Client Developers

1. **Read from inline properties first** — For `deployedSystems`, read `properties['deployedSystems@link']` from the already-fetched deployment resource rather than hitting a sub-resource endpoint. The standard defines this as inline data.

2. **Fall back to `platform@link`** — When `deployedSystems@link` is absent, resolve `platform@link` and display it with a note about the data source.

3. **Note the standard ambiguity** — The conformance test procedures reference `/deployedSystems` URLs that the encoding requirements don't define. Client libraries should be prepared for both inline-property and endpoint-based patterns.

### 7.3 For the OGC CSAPI Standard

1. **Resolve the encoding-vs-test inconsistency** — The normative encoding requirements (Tables 43, 52) define `deployedSystems` as inline data, but conformance test procedures (Annex A.6, A.10) reference `{deploymentCanonicalUrl}/deployedSystems?recursive=true` as a fetchable endpoint. The standard should clarify whether there is also a sub-resource endpoint, or the test procedures should be updated to read from inline properties.

2. **Add a `deployedSystems@link` round-trip conformance test** — The current test suite validates the GeoJSON schema structure but does not explicitly test that `deployedSystems@link` survives a PUT/GET cycle. Adding such a test would catch the exact gap we observed.

---

## 8. Comparison: `deployedSystems@link` vs Other Inline Properties

| Property | Write (PUT/POST) | Read (GET) | Type | Status |
|---|---|---|---|---|
| `platform@link` | ✅ Persisted | ✅ Returned | Single object | **Working** |
| `systemKind@link` | ✅ Persisted | ✅ Returned | Single object | **Working** |
| `sampledFeature@link` | ✅ Persisted | ✅ Returned | Single object | **Working** |
| **`deployedSystems@link`** | ❌ Silently stripped | ❌ Never returned | **Array of objects** | **NOT WORKING** |

The pattern suggests a systematic issue with **array-valued** `@link` properties in the server's GeoJSON parser.

---

## 9. Comparison: Endpoint-Based vs Inline Associations

| Association | Standard Mechanism | Server Support | Notes |
|---|---|---|---|
| `subsystems` | Sub-resource endpoint (`/systems/{id}/subsystems`) | ✅ Working | Parent/child pattern |
| `subdeployments` | Sub-resource endpoint (`/deployments/{id}/subdeployments`) | ✅ Working | Parent/child pattern |
| `datastreams` | Sub-resource endpoint (`/systems/{id}/datastreams`) | ✅ Working | Parent/child pattern |
| `samplingFeatures` | Sub-resource endpoint (`/systems/{id}/samplingFeatures`) | ✅ Working | Parent/child pattern |
| `platform@link` | Inline property | ✅ Working | Single object link |
| **`deployedSystems@link`** | **Inline property** | ❌ Stripped | **Array of object links** |
| `/systems/{id}/deployments` | Nested endpoint (Req 17) | ❌ 302 redirect | Cross-resource association |

---

## 10. Conclusion

The `deployedSystems@link` gap is a significant conformance issue, though narrower than initially reported. The standard defines `deployedSystems` as an **inline GeoJSON property** (like `platform@link`), not as a sub-resource endpoint. The server's failure to persist and return this inline property means the core `sosa:deployedSystem` relationship is invisible through the API.

Combined with the non-functional `/systems/{sysId}/deployments` reverse endpoint, the Deployment ↔ System relationship is completely severed in both directions. Clients cannot discover which systems participate in which deployments through any standard mechanism.

The `platform@link` property provides a partial workaround (identifying the platform hosting a deployment), but it is semantically different from `deployedSystems` and insufficient for deployments involving multiple independent systems.

We also identified an **inconsistency in the OGC standard** between the encoding requirements (which define `deployedSystems` as inline) and the conformance test procedures (which reference it as an endpoint URL). Clarification from the CSAPI working group would benefit both server implementors and client developers.

---

## Appendix A: Test Commands

```bash
# Verify deployedSystems@link is stripped on write
curl -s -u ogc:ogc -X PUT "http://45.55.99.236:8080/sensorhub/api/deployments/049g" \
  -H "Content-Type: application/geo+json" \
  -d '{
    "type": "Feature", "id": "049g",
    "properties": {
      "uid": "urn:x-odas:deployment:office-array-001",
      "featureType": "http://www.w3.org/ns/sosa/Deployment",
      "name": "Conference Room 3A — Single Array Deployment",
      "validTime": ["2026-02-01T00:00:00Z", "2027-02-01T00:00:00Z"],
      "platform@link": {
        "href": "http://45.55.99.236:8080/sensorhub/api/systems/04fg",
        "uid": "urn:x-odas:platform:xcore-mic-board-001"
      },
      "deployedSystems@link": [
        {"href": "http://45.55.99.236:8080/sensorhub/api/systems/04fg", "title": "Test"}
      ]
    }
  }'
# → HTTP 204 (accepted)

# Verify it was stripped
curl -s -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/deployments/049g" | python -m json.tool
# → platform@link present, deployedSystems@link absent

# Test reverse navigation (Req 17 — returns 302)
curl -s -u ogc:ogc -v "http://45.55.99.236:8080/sensorhub/api/systems/04fg/deployments" 2>&1 | grep "HTTP/"
# → HTTP/1.1 302 Found

# Verify platform@link IS returned
curl -s -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/deployments/049g" | python -m json.tool | grep -A3 "platform@link"
```

## Appendix B: Relevant Standard Sections

| Section | Topic | Key Finding |
|---|---|---|
| Clause 11.2.2, Table 11 | Deployment Associations | `deployedSystems` = Required, target = list of Systems |
| Clause 11.4 | Deployment Endpoints | Only 3 endpoints defined — no `/deployedSystems` sub-resource |
| Clause 11.4.3, Req 17 | System → Deployments | `{api_root}/systems/{sysId}/deployments` SHALL be supported (conditional) |
| Clause 12.6, Table 13 | Recursive Associations | `deployedSystems` aggregated across subdeployments |
| Clause 19.1.6, Table 43 | GeoJSON Encoding | `deployedSystems` → `properties/deployedSystems@link` (inline array) |
| Clause 19.2.6, Table 52 | SensorML Encoding | `deployedSystems` → inline `deployedSystems` array |
| Table 3 | Link Relations | No `ogc-rel:deployedSystems` — confirms not a HATEOAS link |
| Annex A.6 | Subdeployment Tests | References "link with relation type deployedSystems" (inconsistency) |
| Annex A.10 | Advanced Filtering Tests | References `{url}/deployedSystems?recursive=true` (inconsistency) |
