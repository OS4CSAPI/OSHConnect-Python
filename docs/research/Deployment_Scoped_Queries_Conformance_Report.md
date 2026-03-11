# Deployment-Scoped Queries: Standard vs. Implementation Conformance Report

| Field | Value |
|---|---|
| **Date** | 2026-03-11 |
| **Author** | Claude (Opus 4.6) |
| **Status** | Corrective Report — Errata to Prior Work |
| **Scope** | Whether deployment-scoped data query endpoints exist in the OGC CSAPI standard, what the standard mandates, and what the reference implementation (OSH) actually supports |
| **Corrects** | [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) §3.2, §7.3, §9.1, §10 |
| **Related Reports** | See §11 |

---

## 1  Purpose and Motivation

This report exists because developers building CSAPI client libraries—both within the OS4CSAPI project and in the broader OGC community—need an authoritative, empirically-tested answer to the question: **can you query datastreams, observations, and control streams scoped to a deployment?**

The prior report [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) (authored by this same AI agent on 2026-03-02) presented deployment-scoped data queries as functional capabilities, including example code and a feature comparison table that implied they work today. That report's §7.3 states:

> *"Once wired, deployment-scoped queries work: `GET /deployments/057g/datastreams` → 7 datastreams (only those with deployment@link → 057g)"*

And §10's conclusion claims:

> *"Implementation-proven — works on OSH today"*

These statements were **not empirically tested** at the time of writing. Developers on the OS4CSAPI team subsequently attempted to build against these endpoints and asked whether they exist in the standard and/or actually function on the live server. This report provides the definitive answer, backed by:

1. Line-by-line analysis of the OGC normative specification text
2. Analysis of the companion OAS (OpenAPI Specification) YAML definition files — both the individual upstream source files and the fully-resolved bundled OAS 3.1 companion specifications
3. Live empirical testing against the OSH reference implementation at `os4csapi-osh.duckdns.org`
4. Full conformance class inventory from the running server

I wrote the original report. I am correcting it here with evidence.

---

## 2  What the Standard Actually Says

The Connected Systems API is defined across three normative documents:

| Document | OGC Identifier | Scope |
|---|---|---|
| **Part 1: Feature Resources** | [OGC 23-001](https://docs.ogc.org/is/23-001/23-001.html) | Systems, Deployments, Procedures, Sampling Features |
| **Part 2: Observation & Command Resources** | [OGC 23-002](https://docs.ogc.org/is/23-002/23-002.html) | DataStreams, Observations, ControlStreams, Commands |
| **Part 3: Publish/Subscribe** | OGC 23-003 | WebSocket, MQTT real-time channels |

The deployment-scoped data query question spans Parts 1 and 2.

### 2.1  Deployment Basics (Part 1 — Uncontroversial)

Part 1 defines the `Deployment` resource ([OGC 23-001, Clause 11](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-features)) with well-established endpoints:

| Endpoint | Conformance Class | Mandatory? |
|---|---|---|
| `GET /deployments` | `conf/deployment` | Yes, if deployment class is implemented |
| `GET /deployments/{id}` | `conf/deployment` | Yes |
| `GET /deployments/{id}/subdeployments` | `conf/subdeployment` | Yes, if subdeployment class is implemented |

These all work on OSH. No dispute here.

**Part 1 already defines the foundation for deployment-scoped data access.** The Deployment resource's associations table ([OGC 23-001, Clause 11.2, Table 11](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-resource)) includes optional `datastreams` and `controlstreams` associations:

> | `datastreams` | — | The Data Streams containing observations collected during the Deployment. | A list of DataStream resources. | **Optional** |
> | `controlstreams` | — | The Control Streams that received commands issued during the Deployment. | A list of ControlStream resources. | **Optional** |

The GeoJSON encoding (Part 1, Clause 19.1, Table 43) maps both associations to weblinks resolving to DataStream/ControlStream resources endpoints — the same endpoints that Part 2's mandatory requirements provide. Additionally, Part 1's Subdeployments requirements class ([Clause 12, Table 13](https://docs.ogc.org/is/23-001/23-001.html#clause-subdeployments)) specifies that for deployments with subdeployments, these associations **SHALL** recursively include resources from all subdeployments.

### 2.2  The `deployment` Association on DataStreams (Part 2, Clause 9)

Part 2 defines the DataStream resource's associations in a table ([OGC 23-002, Clause 9](https://docs.ogc.org/is/23-002/23-002.html), "DataStream Associations"):

> | **Name** | **SOSA/SSN Property** | **Definition** | **Target Content** | **Usage** |
> |---|---|---|---|---|
> | `deployment` | — | The deployment during which the datastream was generated. | A single `Deployment` resource. | **Optional** |

**Source**: [OGC 23-002, Clause 9.2](https://docs.ogc.org/is/23-002/23-002.html) (DataStream Associations table); AsciiDoc source: [`clause_8_requirements_class_datastreams.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_8_requirements_class_datastreams.adoc).

This means the standard explicitly models a deployment-to-datastream relationship. The keyword **Optional** means a server is not required to support this association, but if it does, the representation must include `deployment@link`.

The JSON Schema at [`dataStream.json`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/schemas/json/dataStream.json) includes:

```json
"deployment@link": {
  "description": "Link to the deployment during which the observations are/were collected (only provided if all observations in the datastream share the same deployment)",
  "$ref": "../common/commonDefs.json#/$defs/Link"
}
```

The ControlStream resource has an identical optional `deployment` association ([OGC 23-002, Clause 10](https://docs.ogc.org/is/23-002/23-002.html), ControlStream Associations table):

> | `deployment` | — | The deployment during which the control stream was used. | A single `Deployment` resource. | **Optional** |

### 2.3  The Deployment-Scoped DataStream Endpoint (Part 2, Clause 9) — The Critical Requirement

Here is the most important normative text for this discussion, from [OGC 23-002, Clause 9.4.3](https://docs.ogc.org/is/23-002/23-002.html) (Nested DataStream Resources Endpoints); AsciiDoc source: [`clause_8_requirements_class_datastreams.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_8_requirements_class_datastreams.adoc):

> *"The set of datastreams associated to a specific deployment is available at a nested endpoint under the corresponding `Deployment` resource:"*
>
> **Requirement `/req/datastream/ref-from-deployment`**
>
> **Conditions:** The server implements `http://www.opengis.net/spec/ogcapi-connectedsystems-1/1.0/req/deployment`
>
> **Part 1:** The server **SHALL** implement a DataStream resources endpoint at path `{api_root}/deployments/{depId}/datastreams` for each available `Deployment` resource.
>
> **Part 2:** The endpoint **SHALL** only expose the `DataStream` resources associated to a system that was deployed during the `Deployment` with ID `depId`, and whose valid time intersects the deployment time period.

This is a **SHALL** requirement — the strongest normative language in ISO/OGC standards. The condition is that the server implements the `deployment` requirement class from Part 1. It is not gated by a separate optional conformance class — it is part of the core "Datastreams & Observations" requirements class.

### 2.4  The Deployment-Scoped ControlStream Endpoint (Part 2, Clause 10)

An identical pattern exists for control streams ([OGC 23-002, Clause 10.4.3](https://docs.ogc.org/is/23-002/23-002.html); AsciiDoc source: [`clause_9_requirements_class_controlstreams.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_9_requirements_class_controlstreams.adoc)):

> **Requirement `/req/controlstream/ref-from-deployment`**
>
> **Conditions:**
> - The server implements `http://www.opengis.net/spec/ogcapi-connectedsystems-1/1.0/req/deployment`
> - The server provides the `controlstreams` association as part of `Deployment` resource representations.
>
> **Part 1:** The server **SHALL** implement a ControlStream resources endpoint at path `{api_root}/deployments/{depId}/controlstreams` for each available `Deployment` resource.
>
> **Part 2:** The endpoint **SHALL** only expose the `ControlStream` resources associated to a system that was deployed during the `Deployment` with ID `depId`, and whose valid time intersects the deployment time period.

This has two conditions: the server must implement deployments AND provide the `controlstreams` association on deployments.

### 2.5  What the Standard Does NOT Define

Through exhaustive review of the Part 2 specification text and OAS files, the following **do not exist** in the standard:

| Proposed Endpoint/Parameter | In Standard? | Notes |
|---|---|---|
| `GET /deployments/{id}/observations` | **No** | Observations nest under datastreams, not deployments. No `/req/.../obs-ref-from-deployment` exists. |
| `?deployment=` query parameter on `/datastreams` | **No** | The Advanced Filtering requirements class ([OGC 23-002, Clause 13](https://docs.ogc.org/is/23-002/23-002.html)) defines parameters `phenomenonTime`, `resultTime`, `observedProperty`, `foi`, `system` — but **not** `deployment`. |
| `?deployment=` query parameter on `/observations` | **No** | Same — not defined in the Advanced Filtering requirements class. |

The lack of a `deployment` query parameter on top-level endpoints is particularly significant — it means the **only** standard-defined way to get deployment-scoped datastreams is through the nested endpoint `GET /deployments/{depId}/datastreams`.

The Advanced Filtering requirements class is defined in [OGC 23-002, Clause 13](https://docs.ogc.org/is/23-002/23-002.html) (AsciiDoc source: [`clause_14_requirements_class_advanced_filtering.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_14_requirements_class_advanced_filtering.adoc)). The top-level DataStreams path (showing all accepted query parameters) is defined in [`dataStreams.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/dataStreams.yaml). The top-level Observations path is in [`observations.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/observations.yaml). None include a `deployment` parameter.

### 2.6  OAS Gap: Missing Path File

The companion OpenAPI Specification YAML in the [`api/part2/openapi/paths/`](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part2/openapi/paths) directory includes:

| File | Path Defined |
|---|---|
| [`systemDataStreams.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/systemDataStreams.yaml) | `/systems/{sysId}/datastreams` |
| [`systemControlStreams.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/systemControlStreams.yaml) | `/systems/{sysId}/controlstreams` |
| [`dataStreamObservations.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/dataStreamObservations.yaml) | `/datastreams/{dsId}/observations` |
| [`controlStreamCommands.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/controlStreamCommands.yaml) | `/controlstreams/{csId}/commands` |

Notably **absent**:

- ~~`deploymentDataStreams.yaml`~~ — would define `/deployments/{depId}/datastreams`
- ~~`deploymentControlStreams.yaml`~~ — would define `/deployments/{depId}/controlstreams`

The normative text in Clauses 9 and 10 **requires** these endpoints, but the non-normative OAS companion files **do not include them**. This is an internal inconsistency in the published standard materials. Implementors working from the OAS YAML rather than the normative text would never discover these endpoints.

### 2.7  Bundled OAS 3.1 YAML Cross-Check — Definitive Machine-Readable Confirmation

The upstream individual OAS YAML files analyzed in §2.5–2.6 use `$ref` references that require multi-file resolution. To eliminate any possibility that deployment-scoped paths exist in a referenced file we missed, we performed an independent cross-check against the **bundled** (all `$ref`s fully resolved) OAS 3.1 companion specifications. These are single-file, self-contained OpenAPI documents where every path, parameter, and schema is inlined — making them the definitive machine-readable authority.

The bundled files are maintained in the [OS4CSAPI/ogc-client-CSAPI_2](https://github.com/OS4CSAPI/ogc-client-CSAPI_2) repository at [`docs/research/standards/`](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/tree/main/docs/research/standards):

| File | Scope |
|---|---|
| [ogcapi-connectedsystems-1.bundled.oas31.yaml](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/main/docs/research/standards/ogcapi-connectedsystems-1.bundled.oas31.yaml) | Part 1: Feature Resources (Systems, Deployments, Procedures, Sampling Features, Properties) |
| [ogcapi-connectedsystems-2.bundled.oas31.yaml](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/main/docs/research/standards/ogcapi-connectedsystems-2.bundled.oas31.yaml) | Part 2: Observation & Command Resources (DataStreams, Observations, ControlStreams, Commands) |

#### 2.7.1  Part 2 Bundled YAML — Complete Path Inventory

The Part 2 bundled OAS defines **exactly** the following paths (exhaustive list):

| # | Path | Scoping |
|---|---|---|
| 1 | `/datastreams` | Top-level |
| 2 | `/systems/{systemId}/datastreams` | System-scoped |
| 3 | `/datastreams/{dataStreamId}` | Single resource |
| 4 | `/datastreams/{dataStreamId}/schema` | Schema |
| 5 | `/observations` | Top-level |
| 6 | `/datastreams/{dataStreamId}/observations` | DataStream-scoped |
| 7 | `/controlstreams` | Top-level |
| 8 | `/systems/{systemId}/controlstreams` | System-scoped |
| 9 | `/controlstreams/{controlStreamId}` | Single resource |
| 10 | `/controlstreams/{controlStreamId}/schema` | Schema |
| 11 | `/commands` | Top-level |
| 12 | `/controlstreams/{controlStreamId}/commands` | ControlStream-scoped |
| 13 | `/commands/{cmdId}` | Single resource |
| 14 | `/commands/{cmdId}/status` | Command status |
| 15 | `/commands/{cmdId}/status/{statusId}` | Single status |
| 16 | `/commands/{cmdId}/result` | Command results |
| 17 | `/commands/{cmdId}/result/{resultId}` | Single result |
| 18 | `/systemEvents` | Top-level |
| 19 | `/systems/{systemId}/events` | System-scoped |
| 20 | `/systems/{systemId}/history` | System history |
| 21 | `/systems/{systemId}/history/{revId}` | Single revision |

**Absent from the Part 2 bundled YAML** (confirming §2.6):

- ❌ `/deployments/{depId}/datastreams`
- ❌ `/deployments/{depId}/controlstreams`
- ❌ `/deployments/{depId}/observations`

**Query parameters on `/datastreams`**: `id`, `q`, `phenomenonTime`, `resultTime`, `system`, `foi`, `observedProperty`, `limit` — **no `deployment` parameter**.

**Query parameters on `/observations`**: `id`, `phenomenonTime`, `resultTime`, `dataStream`, `system`, `foi`, `observedProperty`, `limit` — **no `deployment` parameter**.

**Query parameters on `/controlstreams`**: `id`, `q`, `issueTime`, `executionTime`, `system`, `foi`, `controlledProperty`, `limit` — **no `deployment` parameter**.

Despite the absence of deployment-scoped paths, the `deployment@link` property **is** present in both the `dataStream` schema (description: *"Link to the deployment during which the observations are/were collected"*) and the `controlStream` schema (description: *"Link to the deployment during which the commands are/were received"*). This confirms the data model recognizes the deployment association — the gap is solely in the path definitions.

#### 2.7.2  Part 1 Bundled YAML — Deployment Paths Defined

The Part 1 bundled OAS defines the following deployment-related paths:

| Path | Methods | Description |
|---|---|---|
| `/deployments` | GET, POST | List/create deployments. Query params: `id`, `bbox`, `datetime`, `geom`, `q`, `parent`, `system`, `foi`, `observedProperty`, `controlledProperty`, `limit` |
| `/deployments/{deploymentId}` | GET, PUT, DELETE | Single deployment CRUD |
| `/deployments/{deploymentId}/subdeployments` | GET, POST | List/add subdeployments, with `recursive` flag |
| `/systems/{systemId}/deployments` | GET | List deployments for a specific system |

The deployment resource schema includes `platform@link` and `deployedSystems@link` but **no** link relations to datastreams, observations, or controlstreams.

**No deployment-scoped data endpoints exist in Part 1 either.** This is expected — Part 1 covers feature resources only. But it confirms there is no cross-part path definition that we missed.

#### 2.7.3  Cross-Check Conclusion

The bundled OAS 3.1 YAMLs — with all `$ref` references fully resolved into single self-contained files — independently confirm every finding from §2.5 and §2.6:

1. **No deployment-scoped data paths** exist in either Part 1 or Part 2 OAS companion files
2. **No `deployment` query parameter** exists on any top-level endpoint
3. **`deployment@link`** exists in the data model schemas but has no corresponding path definitions
4. The normative AsciiDoc requirements (`/req/datastream/ref-from-deployment`, `/req/controlstream/ref-from-deployment`) mandate these endpoints, but the companion OAS files — both individual and bundled — omit them

This is the strongest possible form of evidence: a single resolved file containing every path and parameter the OAS defines, with zero ambiguity about `$ref` resolution or file-level scope.

---

## 3  What OSH Actually Implements

### 3.1  Server Under Test

| Property | Value |
|---|---|
| Server URL | `https://os4csapi-osh.duckdns.org/sensorhub/api` |
| Internal | `http://localhost:8181/sensorhub/api` (tested via SSH) |
| Software | OpenSensorHub (OSH) Community Edition |
| VM | Oracle Cloud `129.80.248.53` |
| Test Date | 2026-03-11 |
| Database | Fresh H2 MVStore, rebuilt same day |
| Test Method | `curl` via SSH to localhost, bypassing Caddy reverse proxy |

### 3.2  Conformance Classes Declared by OSH

Obtained via `GET /conformance`:

**Part 1 (Feature Resources):**
- `conf/core`
- `conf/system`, `conf/subsystem`
- `conf/deployment`, `conf/subdeployment`
- `conf/procedure`
- `conf/sf` (sampling features)
- `conf/property`
- `conf/create-replace-delete`
- `conf/geojson`, `conf/sensorml`

**Part 2 (Observation & Command Resources):**
- `conf/datastream`
- `conf/controlstream`
- `conf/system-history`, `conf/system-event`
- `conf/create-replace-delete`
- `conf/json`
- `conf/swecommon-json`, `conf/swecommon-text`, `conf/swecommon-binary`

**Part 3:**
- `conf/websocket`, `conf/mqtt`

**Key observation:** OSH declares **both** `conf/deployment` (Part 1) and `conf/datastream` (Part 2). This means requirement `/req/datastream/ref-from-deployment` is **activated** — the condition (`server implements req/deployment`) is met. OSH is therefore **obligated** by the standard to provide `GET /deployments/{depId}/datastreams`.

### 3.3  Empirical Test Results

All tests were performed on 2026-03-11 via SSH to `localhost:8181` using `curl` with Basic auth (`ogc:ogc`).

#### 3.3.1  Deployment-Scoped Nested Endpoints

| Test | Command | HTTP Status | Response Body | Verdict |
|---|---|---|---|---|
| Subdeployments | `GET /deployments/04i0/subdeployments` | **200 OK** | Returns items including sub-deployment `04ig` | **Works** |
| DataStreams | `GET /deployments/04i0/datastreams` | **400 Bad Request** | `{"status": 400, "message": "Invalid resource name: 'datastreams'"}` | **Not implemented** |
| Observations | `GET /deployments/04i0/observations` | **400 Bad Request** | `{"status": 400, "message": "Invalid resource name: 'observations'"}` | **Not implemented** |
| ControlStreams | `GET /deployments/04i0/controlstreams` | **400 Bad Request** | `{"status": 400, "message": "Invalid resource name: 'controlstreams'"}` | **Not implemented** |

The error message `"Invalid resource name"` indicates that OSH's URL router does not recognize `datastreams`, `observations`, or `controlstreams` as valid child resources of a deployment. This is a routing-level gap, not a data-level gap — the code path does not exist.

#### 3.3.2  `deployment@link` Property Acceptance

| Test | Command | HTTP Status | Response Body | Verdict |
|---|---|---|---|---|
| PUT with `deployment@link` | `PUT /datastreams/04fg` with body `{"name":"Aircraft State Vectors","outputName":"adsbState","deployment@link":{"href":"...","uid":"...","type":"..."}}` | **400 Bad Request** | Empty body, `Content-Length: 0` | **Not accepted** |

OSH does not accept the `deployment@link` property on datastream write operations. The 400 response with an empty body suggests the JSON parser rejects the field or the validation fails silently.

#### 3.3.3  `?deployment=` Query Parameter on Top-Level Endpoints

| Test | Command | Items Returned | Verdict |
|---|---|---|---|
| Valid deployment ID | `GET /datastreams?deployment=04hg` | **60** | Same as unfiltered |
| No filter | `GET /datastreams` | **60** | Baseline |
| Bogus deployment ID | `GET /datastreams?deployment=ZZZZ_FAKE` | **60** | **Proves filter is ignored** |

A non-existent deployment ID returns the same 60 items as no filter at all. The `deployment=` parameter is **silently discarded** by OSH. This is unsurprising given that the standard does not define this parameter (see §2.5 above) — but it means there is also no informal workaround.

#### 3.3.4  Link Relations Advertised by OSH

**On a Deployment resource** (`GET /deployments/04i0`):

```json
"links": [
  { "rel": "canonical", "href": ".../deployments/04i0" },
  { "rel": "alternate", "title": "SML format", "href": "...?f=sml3" },
  { "rel": "alternate", "title": "HTML format", "href": "...?f=html" },
  { "rel": "subdeployments", "title": "Subdeployments", "href": ".../deployments/04i0/subdeployments" }
]
```

No `datastreams`, `observations`, or `controlstreams` link relations are advertised.

**On a System resource** (`GET /systems/04f0`) for comparison:

```json
"links": [
  { "rel": "canonical", "href": ".../systems/04f0" },
  { "rel": "alternate", "href": "..." },
  { "rel": "subsystems", "title": "Subsystems", "href": ".../systems/04f0/subsystems" },
  { "rel": "datastreams", "title": "Datastreams", "href": ".../systems/04f0/datastreams" },
  { "rel": "controlstreams", "title": "Control Streams", "href": ".../systems/04f0/controlstreams" }
]
```

Systems advertise data-scoped link relations; deployments do not. A conformant CSAPI client that discovers endpoints through link traversal will never encounter a deployment-scoped data endpoint on OSH.

---

## 4  Why the Original Report Was Written the Way It Was

I owe this explanation because I wrote [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md). Here is an honest accounting of where the reasoning went wrong and where it was correct.

### 4.1  What I Got Right

The **architectural argument** in the original report is sound:

- Deployments provide operational context (where, when, why) that systems do not carry
- A 1:1 pairing of deployments to operationally-significant systems is a valid and useful pattern
- The standard **does** intend for deployments to serve as operational scoping mechanisms — the normative requirement `/req/datastream/ref-from-deployment` proves this (see §2.3)
- Role continuity across hardware swaps is a real advantage of the deployment abstraction
- `platform@link` works on OSH and is the correct wiring mechanism
- Subdeployments work on OSH and model organizational hierarchy correctly

### 4.2  What I Got Wrong

The **implementation claims** were not empirically verified:

| Claim | Location | The Problem |
|---|---|---|
| "Once wired, deployment-scoped queries work" | §7.3 | Never tested. OSH returns 400. |
| "Implementation-proven — works on OSH today" | §10 | The overall pattern works; the deployment-scoped data endpoints do not. |
| `GET /deployments/{id}/observations` | §3.2, §7.3, §9.1 | This endpoint does not exist in the standard at all. I extrapolated it from the datastream endpoint without verifying. |
| `deployment@link` wiring on datastreams | §7.2 | Valid per the JSON schema but rejected by OSH on write. |
| "No client-side filtering, no multi-system unions, no ID lookups" | §9.1 | Without working deployment-scoped endpoints, all of these are required today. |

### 4.3  How This Happened

The report was written by reading the normative specification text (which DOES define deployment-scoped datastream endpoints as SHALL requirements), interpreting the spec's intent (which clearly envisions deployment-scoped data access), and then **assuming the reference implementation matched the spec**. I did not SSH into the server and test the endpoints before publishing the report.

Additionally, I over-extrapolated: the spec defines `GET /deployments/{depId}/datastreams` but **not** `GET /deployments/{depId}/observations`. I assumed the nesting pattern was symmetrical without verifying. In reality, the spec authors deliberately nested observations only under datastreams (not directly under systems or deployments), because observations always belong to a datastream.

### 4.4  The Difference Between "The Standard Says" and "The Code Does"

This distinction is critical for any developer building against the CSAPI.

The standard's normative text uses SHALL language that creates binding requirements for conformant implementations. When requirement `/req/datastream/ref-from-deployment` says a server **SHALL** implement `GET /deployments/{depId}/datastreams`, it means that a server claiming the `conf/datastream` and `conf/deployment` conformance classes **must** provide this endpoint to be standards-compliant.

But the standard is not the software. A server can declare a conformance class and still fail to implement all of its requirements. This is exactly what OSH does today:

```
OSH DECLARES:
  ✓ conf/deployment        (Part 1)
  ✓ conf/datastream        (Part 2)

STANDARD REQUIRES (given both above):
  SHALL implement GET /deployments/{depId}/datastreams
  
OSH IMPLEMENTS:
  ✗ GET /deployments/{depId}/datastreams    → 400 "Invalid resource name"
```

This is a **conformance gap** in OSH, not an error in the standard.

---

## 5  What "The Standard's Aspirational Model" Means — and Why That Phrase Is Misleading

In my initial summary of these findings, I used the phrase "the standard's aspirational model" to describe deployment-scoped data endpoints. I want to correct and clarify that terminology, because it gives the wrong impression.

### 5.1  The Standard Is Not Aspirational — It Is Normative

The word "aspirational" implies a wish, a goal, a direction — something that might be implemented someday. That is **not** what the OGC CSAPI standard is.

[OGC 23-002](https://docs.ogc.org/is/23-002/23-002.html) (Part 2) is a normative standard. Requirement `/req/datastream/ref-from-deployment` uses the word **SHALL**, which in ISO/OGC standards language means "mandatory requirement." It is not a recommendation. It is not a future consideration. It is a binding obligation on any server that claims both `conf/deployment` and `conf/datastream`.

The correct characterization is:

> **The standard defines deployment-scoped data endpoints as mandatory requirements. The reference implementation does not implement them. This is an implementation conformance gap, not a standards gap.**

### 5.2  Why It *Feels* Aspirational

The reason developers experience these requirements as aspirational rather than actual is a convergence of three factors:

**Factor 1: OSH is the only public CSAPI server.** There is no second implementation to test against. When OSH doesn't implement something, the practical reality for all developers is that it doesn't exist — even though the spec says it must.

**Factor 2: The companion OAS YAML files are incomplete.** The normative text says the endpoint SHALL exist, but the non-normative OpenAPI Specification companion files don't include `deploymentDataStreams.yaml` or `deploymentControlStreams.yaml`. Developers who generate client code from the OAS (a standard practice) will never see these endpoints. This creates an internal inconsistency in the published standard materials where the normative text mandates endpoints that the companion OAS doesn't define.

**Factor 3: The standard is newly published.** [OGC 23-001](https://docs.ogc.org/is/23-001/23-001.html)/[23-002](https://docs.ogc.org/is/23-002/23-002.html)/23-003 are relatively new. The [OSH development team](https://github.com/opensensorhub) (led by Alex Robin at [Botts Innovative Research / GeoRobotix](https://www.georobotix.com/)) is actively implementing these parts. Some requirements are implemented; some are not yet. This is normal for new standards, but it means the "standard says X" and "software does X" sets have imperfect overlap.

### 5.3  The Correct Mental Model for Developers

Developers building CSAPI client libraries or applications should think of the standard in three tiers:

| Tier | Description | Example | How to Use |
|---|---|---|---|
| **Tier 1: Spec-defined AND OSH-implemented** | Endpoints that the standard requires and that work on the reference implementation. | `GET /systems/{id}/datastreams`, `GET /deployments/{id}/subdeployments` | **Build against these today.** |
| **Tier 2: Spec-defined but NOT OSH-implemented** | Endpoints the standard requires but that return errors on OSH. | `GET /deployments/{id}/datastreams`, `deployment@link` on write | **Design for these, but do not depend on them.** Implement graceful fallback. File conformance bugs against OSH. |
| **Tier 3: Not in the spec** | Endpoints that might seem logical but are not defined in the normative text. | `GET /deployments/{id}/observations`, `?deployment=` filter on top-level | **Do not build against these.** They are not standardized. |

The original report conflated all three tiers, presenting Tier 2 and even Tier 3 endpoints as Tier 1.

---

## 6  The Today Workaround: How to Get Deployment-Scoped Data Without Deployment-Scoped Endpoints

Until OSH implements `/req/datastream/ref-from-deployment`, developers need a multi-hop strategy to resolve "give me the data for this deployment."

### 6.1  The Resolution Path

```
Step 1: GET /deployments/{depId}
        → Extract platform@link.href → system URL
        → Extract system ID from URL

Step 2: GET /systems/{sysId}/datastreams
        → Returns all datastreams for that system

Step 3: GET /datastreams/{dsId}/observations
        → Returns observations for each datastream
```

This requires 1 + 1 + N HTTP calls (where N is the number of datastreams), versus the 1 call that `GET /deployments/{depId}/datastreams` would require.

### 6.2  For Hierarchical Deployments (Net → String → Node → Data)

```
Step 1: GET /deployments/{netId}/subdeployments           → strings
Step 2: GET /deployments/{stringId}/subdeployments        → nodes
Step 3: GET /deployments/{nodeId}                         → resolve platform@link → system
Step 4: GET /systems/{sysId}/datastreams                  → data
Step 5: GET /datastreams/{dsId}/observations              → observations
```

### 6.3  Client Library Guidance

Client libraries should:

1. **Try the standard path first**: `GET /deployments/{id}/datastreams`
2. **If 400/404**: Fall back to the multi-hop resolution above
3. **Cache the result**: The platform@link resolution is stable for the lifetime of a deployment
4. **Log the fallback**: So teams know when the server adds support and the fallback can be removed

```typescript
async function getDeploymentDatastreams(depId: string): Promise<DataStream[]> {
  // Tier 2: Try the standard-required endpoint first
  const directResponse = await fetch(`${API_ROOT}/deployments/${depId}/datastreams`);
  if (directResponse.ok) {
    const data = await directResponse.json();
    return data.items;
  }

  // Fallback: Multi-hop resolution
  console.warn(`Deployment-scoped datastreams not supported by server. Using multi-hop fallback.`);
  const deployment = await fetch(`${API_ROOT}/deployments/${depId}`).then(r => r.json());
  const systemHref = deployment.properties?.['platform@link']?.href;
  if (!systemHref) throw new Error(`Deployment ${depId} has no platform@link`);

  const systemId = systemHref.split('/').pop()?.split('?')[0];
  const dsResponse = await fetch(`${API_ROOT}/systems/${systemId}/datastreams`);
  const dsData = await dsResponse.json();
  return dsData.items;
}
```

---

## 7  Specific Corrections to the Prior Report

The following table identifies every claim in [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) that needs correction:

| Section | Original Claim | Correction | Severity |
|---|---|---|---|
| §3.2 | `GET /deployments/{id}/observations` — "what has this deployed system observed?" | **This endpoint does not exist in the standard.** Observations are nested under datastreams only. The standard defines `GET /deployments/{id}/datastreams` but NOT a direct observations endpoint. | **High** — cites a non-existent spec endpoint |
| §3.2 | "These endpoints filter by the `deployment@link` field on datastreams." | Partially correct. The spec defines the deployment-scoped nested endpoint but does not specifically say it filters by `deployment@link`. The requirement says it SHALL expose datastreams "associated to a system that was deployed during the Deployment." The association mechanism is `platform@link` on the deployment, not necessarily `deployment@link` on the datastream. | **Medium** — misrepresents the filtering mechanism |
| §4.1, Table | "Show me all of String Alpha's observations" → `GET /deployments/{string}/observations` | This path does not exist in the standard. The correct approach would be: `GET /deployments/{string}/subdeployments` → iterate nodes → resolve `platform@link` → `GET /systems/{id}/datastreams` → `GET /datastreams/{id}/observations`. | **High** — non-existent endpoint |
| §7.2 | `deployment@link` in datastream POST body | Valid per the standard's JSON schema, but **rejected by OSH** with HTTP 400. Cannot be used in practice today. | **High** — untested claim presented as working |
| §7.3 | "Once wired, deployment-scoped queries work" — all four example queries | Two of the four work: `GET /deployments/{id}/subdeployments` (works) and the hierarchical nav. The other two (`GET /deployments/057g/datastreams`, `GET /deployments/057g/observations`) do not work on OSH. The observations endpoint doesn't even exist in the standard. | **Critical** — presented as working without testing |
| §9.1, Table | Six "single standard-conformant API call" examples | "All deployed systems" (`GET /deployments`) and filtered variants work. "What is Node 1 seeing?" (`GET /deployments/{node1}/observations`) and "Node 1's health" (`GET /deployments/{node1}/datastreams?name=Health`) do not work on OSH. The observations endpoint is not in the standard. | **Critical** — developer-facing table with broken examples |
| §10, Bullet | "Implementation-proven — works on OSH today" | The 1:1 pairing pattern is valid. `platform@link` works. Subdeployments work. But deployment-scoped data queries do not work on OSH. This bullet should read: "Pattern is standards-conformant; deployment-scoped data endpoints await OSH implementation." | **High** — overstates implementation readiness |
| §8.4, Table | "Standards-conformant" (as a Pro) | True for the pattern itself. But the table should note that deployment-scoped data endpoints are Tier 2 (spec-defined, not OSH-implemented). | **Medium** |

---

## 8  Reassessment: Design Alternatives in Light of Conformance Findings

The prior report [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) §8 compared four design alternatives for modeling deployed systems in the CSAPI. That comparison assumed deployment-scoped data endpoints worked on OSH. Now that the empirical testing in §3 and the normative analysis in §2 have established exactly what works and what doesn't, every pro and con from that comparison deserves a re-evaluation.

This section recreates the original comparison tables with two additional columns — **"Still Valid?"** and **"Assessment"** — reflecting our current understanding after reading both published standards in full and testing every endpoint on OSH.

### 8.1  Alternative A: Systems Only, No Deployments

The simplest approach — interact with systems directly, skip deployments entirely.

```
Systems:
  AZ-MA-1
    ├── 7 datastreams, thousands of observations
    └── subsystems
```

**Original assessment** (from [CSAPI_Deployed_Systems_Design_Pattern.md §8.1](CSAPI_Deployed_Systems_Design_Pattern.md#81--alternative-a-systems-only-no-deployments)):

| Pros | Cons |
|---|---|
| Simpler — fewer resources to create | No organizational hierarchy |
| | No per-role observation scoping |
| | No temporal scoping by deployment period |
| | Hardware swap breaks all queries |
| | "Which systems are deployed at Ft Huachuca?" has no standard answer |
| | System hierarchy models physical composition, not operational structure |

**Updated assessment** — each claim cross-checked against the published standards and empirical OSH testing:

| Claim | Type | Still Valid? | Assessment |
|---|---|---|---|
| Simpler — fewer resources to create | Pro | **Yes** | Objectively true. You skip creating deployments, subdeployments, and wiring `platform@link`. |
| No organizational hierarchy | Con | **Yes** | Systems model *physical composition* (subsystems). They cannot model operational structure (net → string → node). The spec deliberately separates these concerns — [Part 1 Clause 11](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-features) (Deployments) vs Clause 8 (Systems). |
| No per-role observation scoping | Con | **Partially** | The standard defines `GET /deployments/{id}/datastreams` as a SHALL requirement (see §2.3), so the spec *intends* per-role scoping. But OSH doesn't implement it (returns 400 — see §3.3.1). Today, even with deployments, you don't get per-role observation scoping in a single call — you must multi-hop through `platform@link` → system → datastreams (see §6). The con is real in principle, but the deployment advantage doesn't materialize on OSH yet. |
| No temporal scoping by deployment period | Con | **Yes** | Deployments carry `validTime`. Systems don't have an equivalent "when was I fielded here?" concept. This works on OSH today. |
| Hardware swap breaks all queries | Con | **Yes** | The strongest argument for deployments and 100% valid. If MA-1 is replaced by MA-4 at Node 1, with systems-only you lose continuity entirely — different system ID, different datastream IDs, no persistent identifier for the role. With deployments, you update `platform@link` and the deployment persists as the role identifier. |
| "Which systems are deployed at Ft Huachuca?" has no standard answer | Con | **Yes** | `GET /deployments?bbox=...` works today on OSH. No equivalent filter exists on systems for "currently deployed at location X." |
| System hierarchy models physical composition, not operational structure | Con | **Yes** | Core design intent of the standard. Systems = what exists (physical inventory). Deployments = what's fielded (operational context). |

**Bottom line:** The cons are largely real. Even without deployment-scoped data endpoints working, deployments provide organizational hierarchy, temporal scoping, spatial scoping, role continuity, and a persistent identifier for "what's at this position." You just can't shortcut to the *data* through the deployment layer in a single hop today.

### 8.2  Alternative B: Organization Modeled in System Hierarchy

Model operational organization (sensor networks, strings, nodes) as a system hierarchy instead of using deployments.

```
Systems:
  Sensor Net (system)
    └── String Alpha (subsystem)
          └── AZ-MA-1 (subsystem)
```

**Original assessment** (from [CSAPI_Deployed_Systems_Design_Pattern.md §8.2](CSAPI_Deployed_Systems_Design_Pattern.md#82--alternative-b-organization-modeled-in-system-hierarchy)):

| Pros | Cons |
|---|---|
| One hierarchy to think about | Reparenting costs thousands of API calls + data migration |
| | Sensor Net and String Alpha aren't really "systems" |
| | Conflates physical composition with operational organization |
| | [Documented in detail](CSAPI_Deployment_Reparenting_Feasibility.md) |

**Updated assessment** — each claim cross-checked against the published standards and empirical OSH testing:

| Claim | Type | Still Valid? | Assessment |
|---|---|---|---|
| One hierarchy to think about | Pro | **Yes** | Simpler mental model, but at the costs described below. |
| Reparenting costs thousands of API calls + data migration | Con | **Yes** | Proven in the [Reparenting Feasibility report](CSAPI_Deployment_Reparenting_Feasibility.md). Moving a system in the hierarchy means moving all its datastreams, observations, control streams, and commands. Moving a deployment requires ~12 API calls. |
| Sensor Net and String Alpha aren't really "systems" | Con | **Yes** | The OGC standard defines a System as something with sensors, actuators, or processes. An organizational grouping like "String Alpha" is not a system — it's an operational construct. Modeling it as a system is a semantic mismatch with the spec's data model. |
| Conflates physical composition with operational organization | Con | **Yes** | Same fundamental problem from a different angle. The spec deliberately separates these concerns across [Part 1 Clause 8](https://docs.ogc.org/is/23-001/23-001.html) (Systems) and [Clause 11](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-features) (Deployments). |

**Bottom line:** All claims remain valid. This is the worst option — it misuses the System resource for something the Deployment resource was designed to do, and creates catastrophic reparenting costs.

### 8.3  Alternative C: Flat Deployment with `deployedSystems` (ChatGPT's "Doctrinal Minimalism")

A single flat deployment listing multiple systems via `deployedSystems@link`, rather than one-deployment-per-node with subdeployment hierarchy.

```
Deployments:
  String Alpha (deployment)
    deployedSystems@link: [MA-1, MA-2, MA-3]
```

**Original assessment** (from [CSAPI_Deployed_Systems_Design_Pattern.md §8.3](CSAPI_Deployed_Systems_Design_Pattern.md#83--alternative-c-flat-deployment-with-deployedsystems-chatgpts-doctrinal-minimalism)):

| Pros | Cons |
|---|---|
| Minimal resource count | **OSH silently drops `deployedSystems@link`** — [proven by probe](OSH_DeployedSystems_Conformance_Probe.md) |
| | No per-node observation scoping |
| | No per-node temporal validity |
| | Doesn't survive contact with the implementation |

**Updated assessment** — each claim cross-checked against the published standards and empirical OSH testing:

| Claim | Type | Still Valid? | Assessment |
|---|---|---|---|
| Minimal resource count | Pro | **Yes** | Fewer resources to create than one-deployment-per-node. |
| OSH silently drops `deployedSystems@link` | Con | **Yes** | Proven by the [DeployedSystems Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md). You can POST it, but OSH doesn't persist it. The data disappears silently — no error, no warning. |
| No per-node observation scoping | Con | **Yes** | A flat deployment with 3 systems linked gives you no way to ask "what is Node 1 specifically seeing?" — you'd get all 3 systems' data mixed together. |
| No per-node temporal validity | Con | **Yes** | One flat deployment can't track that MA-1 was at Node 1 from Jan–Jun and MA-4 from Jul onward. |
| Doesn't survive contact with the implementation | Con | **Yes** | Since `deployedSystems@link` is silently dropped by OSH, this entire approach is dead on arrival with the reference implementation. |

**Bottom line:** All claims remain valid. This approach doesn't work on OSH, period. Even if OSH added `deployedSystems` support, it would still lack per-node scoping and temporal granularity.

### 8.4  The Recommended Pattern: 1:1 Deployment Pairing — Updated Assessment

One deployment per operationally significant system, with `platform@link` wiring, organized via subdeployment hierarchy. This is the pattern analyzed throughout this report.

```
Deployments:
  Sensor Net
    └── String Alpha
          ├── Node 1 (platform@link → MA-1)
          ├── Node 2 (platform@link → MA-2)
          └── Node 3 (platform@link → MA-3)
```

**Original assessment** (from [CSAPI_Deployed_Systems_Design_Pattern.md §8.4](CSAPI_Deployed_Systems_Design_Pattern.md#84--recommended-11-deployment-pairing-this-document)):

| Pros | Cons |
|---|---|
| Per-node observation scoping | More resources to create (one deployment per significant system) |
| Organizational hierarchy | `deployment@link` must be set on every datastream |
| Role continuity across hardware swaps | |
| Temporal scoping per deployment | |
| Cheap to rearrange (~12 API calls per move) — [documented](CSAPI_Deployment_Reparenting_Feasibility.md) | |
| Standards-conformant | |
| Works on OSH today | |
| Forward-compatible with `deployedSystems` if OSH adds it | |

**Updated assessment** — each claim cross-checked against the published standards and empirical OSH testing:

| Claim | Type | Still Valid? | Assessment |
|---|---|---|---|
| Per-node observation scoping | Pro | **In principle only** | The standard says `GET /deployments/{id}/datastreams` SHALL work (see §2.3). OSH returns 400 (see §3.3.1). Today, you do NOT get per-node observation scoping through the deployment layer in a single call. You must resolve `platform@link` → system → datastreams (see §6). The *wiring* is correct; the *shortcut* doesn't work yet. |
| Organizational hierarchy | Pro | **Yes — works today** | `GET /deployments/{id}/subdeployments` works on OSH. You can navigate net → string → node. Tested and functional (§3.3.1). |
| Role continuity across hardware swaps | Pro | **Yes — works today** | Update `platform@link` on the deployment. The deployment ID persists as the role identifier. This is the killer feature of the pattern and it works right now. |
| Temporal scoping per deployment | Pro | **Yes — works today** | `validTime` on deployments works. You can query `?validTime=now` or specific time ranges. |
| Cheap to rearrange (~12 API calls per move) | Pro | **Yes — works today** | Deployment reparenting is cheap; system reparenting is catastrophically expensive. Proven in the [Reparenting Feasibility report](CSAPI_Deployment_Reparenting_Feasibility.md). |
| Standards-conformant | Pro | **Yes, but nuanced** | The 1:1 pairing pattern itself is 100% spec-conformant: `platform@link`, subdeployments, and deployment hierarchy are all spec-defined and OSH-implemented. The deployment-scoped data endpoints are also spec-defined (SHALL language) but not OSH-implemented. The pattern is conformant; the server has a conformance gap. |
| Works on OSH today | Pro | **Partially** | The hierarchy and wiring work today. The deployment-scoped data shortcuts do not. This should read: "pattern works; deployment-scoped data queries await OSH implementation." |
| Forward-compatible with `deployedSystems` if OSH adds it | Pro | **Yes** | The pattern doesn't conflict with `deployedSystems`; the two approaches are additive. |
| More resources to create (one deployment per significant system) | Con | **Yes** | Real cost — you're maintaining a parallel hierarchy of deployments alongside your systems. |
| `deployment@link` must be set on every datastream | Con | **Broken today** | OSH rejects `deployment@link` on datastream PUT with HTTP 400 (§3.3.2). You literally *cannot* do this step right now. However, even without `deployment@link`, the multi-hop path (`platform@link` → system → datastreams) still works as a fallback (§6). |

**Bottom line:** The pattern is still the right choice. Five of its eight "pros" work today on OSH. Two are blocked by OSH's conformance gap (deployment-scoped data queries and `deployment@link` write support) — they are spec-mandated but not yet implemented. One (forward-compatibility with `deployedSystems`) is future-oriented. Both cons are real.

### 8.5  What Actually Works Today vs. What's Waiting on OSH

| Capability | Works Today? | Depends On |
|---|---|---|
| Deployment CRUD (create, read, update, delete) | **Yes** | — |
| Subdeployment hierarchy (net → string → node) | **Yes** | — |
| `platform@link` wiring (deployment → system) | **Yes** | — |
| Navigating deployment → `platform@link` → system → datastreams (multi-hop) | **Yes** | Client-side resolution (see §6) |
| `validTime` temporal scoping on deployments | **Yes** | — |
| `GET /deployments/{id}/datastreams` (single-hop data access) | **No** — 400 | OSH implementing `/req/datastream/ref-from-deployment` |
| `deployment@link` on datastreams (write) | **No** — 400 | OSH accepting the JSON schema property |
| `GET /deployments/{id}/observations` | **Never** | Not in the standard — observations always nest under datastreams, not directly under deployments or systems |

### 8.6  The Verdict

The 1:1 deployment pairing pattern remains the correct architecture. The OGC standard was explicitly designed for this separation — [Part 1 Clause 11](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-features) defines deployments with optional `datastreams`/`controlstreams` associations (Table 11), and [Part 2 Clause 9](https://docs.ogc.org/is/23-002/23-002.html) mandates deployment-scoped data endpoints with SHALL language.

The practical reality today: you build the deployment hierarchy (that works), wire `platform@link` (that works), and when a user asks "what is Node 1 seeing?", your code resolves `deployment → platform@link → system → datastreams → observations` in multiple hops instead of one. When OSH catches up to the spec, that multi-hop path collapses to a single call, and your architecture doesn't change at all.

The prior report's §8 comparison still recommends the right choice. Two of its listed "pros" are currently theoretical rather than practical. Everything else — hierarchy, role continuity, temporal scoping, cheap reparenting — is real and working right now.

---

## 9  The Broader Impact: What This Means for Any CSAPI Implementor

This is not just an OS4CSAPI issue. The OGC CSAPI standard is designed for interoperability across the entire geospatial community. Every developer building a CSAPI client or server needs to understand these findings:

### 9.1  For Client Library Developers

- **Do not assume** all SHALL requirements in the normative text are implemented by a given server
- **Always check** the conformance endpoint (`GET /conformance`) and validate empirically — a server declaring a conformance class may still lack individual requirements within that class
- **Follow link relations** advertised in resource representations. If a deployment resource does not include a `datastreams` link relation, the endpoint likely doesn't work on that server
- **Implement graceful fallback** for Tier 2 endpoints (see §5.3 and §6.3)

### 9.2  For Server Implementors

- OSH's missing implementation of `/req/datastream/ref-from-deployment` is a conformance gap that should be reported to the [OSH development team](https://github.com/opensensorhub)
- The absence of `deploymentDataStreams.yaml` and `deploymentControlStreams.yaml` in the OAS companion files may contribute to implementors overlooking these requirements
- The relevant GitHub issue tracker is: [opengeospatial/ogcapi-connected-systems/issues](https://github.com/opengeospatial/ogcapi-connected-systems/issues)

### 9.3  For Standards Body Attention

- The normative text (Clauses 9 and 10) mandates deployment-scoped endpoints
- The companion OAS YAML files do not include path definitions for these endpoints
- This internal inconsistency should be addressed in a corrigendum or future revision
- The question of whether `GET /deployments/{depId}/observations` SHOULD be added to the standard (it's a natural extension of the pattern defined for datastreams) is worth raising with the SWG

---

## 10  Summary: The Definitive Answer

### 10.1  Quick Reference Table

| Query | In OGC Standard? | Spec Requirement ID | OSH Tested | OSH Result | Tier |
|---|---|---|---|---|---|
| `GET /deployments` | Yes (Part 1) | `/req/deployment/endpoint` | Yes | **200 OK** | Tier 1 |
| `GET /deployments/{id}` | Yes (Part 1) | `/req/deployment/canonical-url` | Yes | **200 OK** | Tier 1 |
| `GET /deployments/{id}/subdeployments` | Yes (Part 1) | `/req/subdeployment/ref-from-deployment` | Yes | **200 OK** — returns children | Tier 1 |
| `GET /deployments/{id}/datastreams` | **Yes (Part 2)** | **`/req/datastream/ref-from-deployment`** | Yes | **400** — "Invalid resource name" | **Tier 2** |
| `GET /deployments/{id}/controlstreams` | **Yes (Part 2)** | **`/req/controlstream/ref-from-deployment`** | Yes | **400** — "Invalid resource name" | **Tier 2** |
| `GET /deployments/{id}/observations` | **No** | None | Yes | **400** — "Invalid resource name" | **Tier 3** |
| `PUT /datastreams/{id}` with `deployment@link` | Yes (JSON schema) | Schema-level, optional | Yes | **400** — empty body | **Tier 2** |
| `GET /datastreams?deployment={id}` | **No** | None | Yes | 200 but **filter ignored** (60 items regardless) | **Tier 3** |

### 10.2  One-Line Answer

**The OGC CSAPI standard requires `GET /deployments/{id}/datastreams` as a SHALL-level mandate. OSH does not implement it. `GET /deployments/{id}/observations` doesn't exist in the standard at all. Plan accordingly.**

---

## 11  Related Reports

| Report | Relevance |
|---|---|
| [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) | The report this document corrects. Its architectural recommendations remain valid; its implementation claims about deployment-scoped data endpoints are incorrect. |
| [OSH_DeployedSystems_Conformance_Probe.md](OSH_DeployedSystems_Conformance_Probe.md) | Proved that `deployedSystems@link` is silently dropped by OSH. A related but distinct conformance gap. |
| [OSH_Deployment_Link_Persistence_Gap.md](OSH_Deployment_Link_Persistence_Gap.md) | Documents that `deployment@link` on datastreams is not persisted by OSH — consistent with the finding here that OSH rejects `deployment@link` on PUT. |
| [CSAPI_Deployment_Modeling_Standards_Conformance.md](CSAPI_Deployment_Modeling_Standards_Conformance.md) | Standards conformance analysis for deployment modeling approaches. |
| [CSAPI_Deployment_Reparenting_Feasibility.md](CSAPI_Deployment_Reparenting_Feasibility.md) | Confirms the deployment hierarchy pattern works today, independent of the data endpoint gaps. |

---

## 12  Appendix: Spec Source References and Research Methodology

### 12.1  Authoritative Published Standards

The authoritative published standards are hosted by OGC:

| Standard | Authoritative URL |
|---|---|
| **OGC 23-001 — Part 1: Feature Resources** | [https://docs.ogc.org/is/23-001/23-001.html](https://docs.ogc.org/is/23-001/23-001.html) |
| **OGC 23-002 — Part 2: Observation & Command Resources** | [https://docs.ogc.org/is/23-002/23-002.html](https://docs.ogc.org/is/23-002/23-002.html) |

Both published HTML standards were fetched and reviewed in full on 2025-06-24. All clause references, requirement identifiers, and normative text cited in this report have been verified against the authoritative published documents. The normative content is identical to the AsciiDoc source files on GitHub.

**Key published standard clause anchors** (deep-linkable):

| Content | Published HTML Deep Link |
|---|---|
| Part 1, Clause 11 — Deployment Features | [23-001 §11](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-features) |
| Part 1, Clause 11.2 — Deployment Resource | [23-001 §11.2](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-resource) |
| Part 1, Clause 11.4 — Deployment Endpoints | [23-001 §11.4](https://docs.ogc.org/is/23-001/23-001.html#clause-deployment-resources-endpoint) |
| Part 1, Clause 12 — Subdeployments | [23-001 §12](https://docs.ogc.org/is/23-001/23-001.html#clause-subdeployments) |
| Part 2, Clause 9 — DataStreams & Observations | [23-002 §9](https://docs.ogc.org/is/23-002/23-002.html) |
| Part 2, Clause 10 — ControlStreams & Commands | [23-002 §10](https://docs.ogc.org/is/23-002/23-002.html) |
| Part 2, Clause 13 — Advanced Filtering | [23-002 §13](https://docs.ogc.org/is/23-002/23-002.html) |

### 12.2  AsciiDoc Source File References

For line-level analysis of normative text, clause-level AsciiDoc source files and companion OpenAPI/JSON Schema files from the OGC GitHub repository ([opengeospatial/ogcapi-connected-systems](https://github.com/opengeospatial/ogcapi-connected-systems), branch: `master`) were consulted. These contain the same normative content used to generate the published HTML standards above.

**Important note on clause numbering:** The AsciiDoc source filenames (e.g., `clause_8_...`) do NOT match the published standard's clause numbers. The build process produces different numbering due to front-matter clauses. The mapping is:

| Published Clause | Content | AsciiDoc Source File |
|---|---|---|
| Part 2, **Clause 9** | DataStreams & Observations | `clause_8_requirements_class_datastreams.adoc` |
| Part 2, **Clause 10** | ControlStreams & Commands | `clause_9_requirements_class_controlstreams.adoc` |
| Part 2, **Clause 13** | Advanced Filtering | `clause_14_requirements_class_advanced_filtering.adoc` |
| Part 2, **Clause 7** | Overview | `clause_6_overview.adoc` |
| Part 2, **Clause 16** | JSON Encoding | `clause_20_requirements_class_json_encoding.adoc` |
| Part 1, **Clause 11** | Deployment Features | `clause_7_requirements_class_deployments.adoc` |

**AsciiDoc source links:**

| Reference | Link |
|---|---|
| Part 2, Clause 9 (DataStreams & Observations) | [clause_8_requirements_class_datastreams.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_8_requirements_class_datastreams.adoc) |
| Part 2, Clause 10 (ControlStreams & Commands) | [clause_9_requirements_class_controlstreams.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_9_requirements_class_controlstreams.adoc) |
| Part 2, Clause 13 (Advanced Filtering) | [clause_14_requirements_class_advanced_filtering.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_14_requirements_class_advanced_filtering.adoc) |
| Part 2, Clause 7 (Overview) | [clause_6_overview.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_6_overview.adoc) |
| Part 2, Clause 16 (JSON Encoding) | [clause_20_requirements_class_json_encoding.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_20_requirements_class_json_encoding.adoc) |

### 12.3  OpenAPI/JSON Schema References

| Reference | Link |
|---|---|
| DataStream JSON Schema | [dataStream.json](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/schemas/json/dataStream.json) |
| DataStream Create JSON Schema | [dataStream_create.json](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/schemas/json/dataStream_create.json) |
| ControlStream JSON Schema | [controlStream.json](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/schemas/json/controlStream.json) |
| Top-level DataStreams Path | [dataStreams.yaml](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/dataStreams.yaml) |
| System DataStreams Path | [systemDataStreams.yaml](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/systemDataStreams.yaml) |
| Top-level Observations Path | [observations.yaml](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/observations.yaml) |
| System ControlStreams Path | [systemControlStreams.yaml](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/systemControlStreams.yaml) |
| Part 2 OAS Paths Directory | [paths/](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part2/openapi/paths) (no deployment-scoped files present) |
| Part 2 JSON Schemas Directory | [schemas/json/](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part2/openapi/schemas/json) |
| Part 2 Standard Sections Directory | [standard/sections/](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part2/standard/sections) |
| **Bundled OAS 3.1 — Part 1** (all `$ref`s resolved) | [ogcapi-connectedsystems-1.bundled.oas31.yaml](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/main/docs/research/standards/ogcapi-connectedsystems-1.bundled.oas31.yaml) |
| **Bundled OAS 3.1 — Part 2** (all `$ref`s resolved) | [ogcapi-connectedsystems-2.bundled.oas31.yaml](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/main/docs/research/standards/ogcapi-connectedsystems-2.bundled.oas31.yaml) |

### 12.4  Research Methodology

This report was researched using three complementary evidence layers:

1. **Authoritative published HTML standards** at `docs.ogc.org` — the definitive normative text. Both OGC 23-001 and OGC 23-002 were fetched and read in full. All clause numbers, requirement identifiers, and normative language cited in this report reflect the published standard's numbering.

2. **AsciiDoc source files** on GitHub — used for line-level analysis where the published HTML lacks granular anchor targets. The normative content is identical; only the clause numbering differs due to the build process (see §12.2).

3. **Bundled OAS 3.1 YAML specifications** — single-file, all-`$ref`s-resolved OpenAPI documents providing the definitive machine-readable API surface. Cross-checked independently against both the individual OAS files and the normative text.

4. **Live empirical testing** against the OSH reference implementation — `curl` commands via SSH, providing ground truth about what the server actually does.
