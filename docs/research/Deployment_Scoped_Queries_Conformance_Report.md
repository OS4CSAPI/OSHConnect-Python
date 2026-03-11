# Deployment-Scoped Queries: Standard vs. Implementation Conformance Report

| Field | Value |
|---|---|
| **Date** | 2026-03-11 |
| **Author** | Claude (Opus 4.6) |
| **Status** | Corrective Report — Errata to Prior Work |
| **Scope** | Whether deployment-scoped data query endpoints exist in the OGC CSAPI standard, what the standard mandates, and what the reference implementation (OSH) actually supports |
| **Corrects** | [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) §3.2, §7.3, §9.1, §10 |
| **Related Reports** | See §10 |

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
| **Part 1: Feature Resources** | [OGC 23-001](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part1) | Systems, Deployments, Procedures, Sampling Features |
| **Part 2: Observation & Command Resources** | [OGC 23-002](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part2) | DataStreams, Observations, ControlStreams, Commands |
| **Part 3: Publish/Subscribe** | [OGC 23-003](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part3) | WebSocket, MQTT real-time channels |

The deployment-scoped data query question spans Parts 1 and 2.

### 2.1  Deployment Basics (Part 1 — Uncontroversial)

Part 1 defines the `Deployment` resource ([OGC 23-001, §7.5](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part1/standard/sections/clause_7_requirements_class_deployments.adoc)) with well-established endpoints:

| Endpoint | Conformance Class | Mandatory? |
|---|---|---|
| `GET /deployments` | `conf/deployment` | Yes, if deployment class is implemented |
| `GET /deployments/{id}` | `conf/deployment` | Yes |
| `GET /deployments/{id}/subdeployments` | `conf/subdeployment` | Yes, if subdeployment class is implemented |

These all work on OSH. No dispute here.

### 2.2  The `deployment` Association on DataStreams (Part 2, Clause 8)

Part 2 defines the DataStream resource's associations in a table (clause 8, "DataStream Associations"):

> | **Name** | **SOSA/SSN Property** | **Definition** | **Target Content** | **Usage** |
> |---|---|---|---|---|
> | `deployment` | — | The deployment during which the datastream was generated. | A single `Deployment` resource. | **Optional** |

**Source**: [`clause_8_requirements_class_datastreams.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_8_requirements_class_datastreams.adoc), DataStream Associations table.

This means the standard explicitly models a deployment-to-datastream relationship. The keyword **Optional** means a server is not required to support this association, but if it does, the representation must include `deployment@link`.

The JSON Schema at [`dataStream.json`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/schemas/json/dataStream.json) includes:

```json
"deployment@link": {
  "description": "Link to the deployment during which the observations are/were collected (only provided if all observations in the datastream share the same deployment)",
  "$ref": "../common/commonDefs.json#/$defs/Link"
}
```

The ControlStream resource has an identical optional `deployment` association ([clause 9](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_9_requirements_class_controlstreams.adoc), "ControlStream Associations table"):

> | `deployment` | — | The deployment during which the control stream was used. | A single `Deployment` resource. | **Optional** |

### 2.3  The Deployment-Scoped DataStream Endpoint (Part 2, Clause 8) — The Critical Requirement

Here is the most important normative text for this discussion, reproduced verbatim from [`clause_8_requirements_class_datastreams.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_8_requirements_class_datastreams.adoc), under "Nested DataStream Resources Endpoints":

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

### 2.4  The Deployment-Scoped ControlStream Endpoint (Part 2, Clause 9)

An identical pattern exists for control streams in [`clause_9_requirements_class_controlstreams.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_9_requirements_class_controlstreams.adoc):

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
| `?deployment=` query parameter on `/datastreams` | **No** | The Advanced Filtering requirements class (clause 14) defines parameters `phenomenonTime`, `resultTime`, `observedProperty`, `foi`, `system` — but **not** `deployment`. |
| `?deployment=` query parameter on `/observations` | **No** | Same — not defined in the Advanced Filtering requirements class. |

The lack of a `deployment` query parameter on top-level endpoints is particularly significant — it means the **only** standard-defined way to get deployment-scoped datastreams is through the nested endpoint `GET /deployments/{depId}/datastreams`.

The Advanced Filtering requirements class is defined in [`clause_14_requirements_class_advanced_filtering.adoc`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_14_requirements_class_advanced_filtering.adoc). The top-level DataStreams path (showing all accepted query parameters) is defined in [`dataStreams.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/dataStreams.yaml). The top-level Observations path is in [`observations.yaml`](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/openapi/paths/observations.yaml). None include a `deployment` parameter.

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

The normative text in clauses 8 and 9 **requires** these endpoints, but the non-normative OAS companion files **do not include them**. This is an internal inconsistency in the published standard materials. Implementors working from the OAS YAML rather than the normative AsciiDoc text would never discover these endpoints.

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

[OGC 23-002](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part2) (Part 2) is a normative standard. Requirement `/req/datastream/ref-from-deployment` uses the word **SHALL**, which in ISO/OGC standards language means "mandatory requirement." It is not a recommendation. It is not a future consideration. It is a binding obligation on any server that claims both `conf/deployment` and `conf/datastream`.

The correct characterization is:

> **The standard defines deployment-scoped data endpoints as mandatory requirements. The reference implementation does not implement them. This is an implementation conformance gap, not a standards gap.**

### 5.2  Why It *Feels* Aspirational

The reason developers experience these requirements as aspirational rather than actual is a convergence of three factors:

**Factor 1: OSH is the only public CSAPI server.** There is no second implementation to test against. When OSH doesn't implement something, the practical reality for all developers is that it doesn't exist — even though the spec says it must.

**Factor 2: The companion OAS YAML files are incomplete.** The normative text says the endpoint SHALL exist, but the non-normative OpenAPI Specification companion files don't include `deploymentDataStreams.yaml` or `deploymentControlStreams.yaml`. Developers who generate client code from the OAS (a standard practice) will never see these endpoints. This creates an internal inconsistency in the published standard materials where the normative text mandates endpoints that the companion OAS doesn't define.

**Factor 3: The standard is newly published.** [OGC 23-001](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part1)/[23-002](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part2)/[23-003](https://github.com/opengeospatial/ogcapi-connected-systems/tree/master/api/part3) are relatively new. The [OSH development team](https://github.com/opensensorhub) (led by Alex Robin at [Botts Innovative Research / GeoRobotix](https://www.georobotix.com/)) is actively implementing these parts. Some requirements are implemented; some are not yet. This is normal for new standards, but it means the "standard says X" and "software does X" sets have imperfect overlap.

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

## 8  The Broader Impact: What This Means for Any CSAPI Implementor

This is not just an OS4CSAPI issue. The OGC CSAPI standard is designed for interoperability across the entire geospatial community. Every developer building a CSAPI client or server needs to understand these findings:

### 8.1  For Client Library Developers

- **Do not assume** all SHALL requirements in the normative text are implemented by a given server
- **Always check** the conformance endpoint (`GET /conformance`) and validate empirically — a server declaring a conformance class may still lack individual requirements within that class
- **Follow link relations** advertised in resource representations. If a deployment resource does not include a `datastreams` link relation, the endpoint likely doesn't work on that server
- **Implement graceful fallback** for Tier 2 endpoints (see §5.3 and §6.3)

### 8.2  For Server Implementors

- OSH's missing implementation of `/req/datastream/ref-from-deployment` is a conformance gap that should be reported to the [OSH development team](https://github.com/opensensorhub)
- The absence of `deploymentDataStreams.yaml` and `deploymentControlStreams.yaml` in the OAS companion files may contribute to implementors overlooking these requirements
- The relevant GitHub issue tracker is: [opengeospatial/ogcapi-connected-systems/issues](https://github.com/opengeospatial/ogcapi-connected-systems/issues)

### 8.3  For Standards Body Attention

- The normative text (clauses 8 and 9) mandates deployment-scoped endpoints
- The companion OAS YAML files do not include path definitions for these endpoints
- This internal inconsistency should be addressed in a corrigendum or future revision
- The question of whether `GET /deployments/{depId}/observations` SHOULD be added to the standard (it's a natural extension of the pattern defined for datastreams) is worth raising with the SWG

---

## 9  Summary: The Definitive Answer

### 9.1  Quick Reference Table

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

### 9.2  One-Line Answer

**The OGC CSAPI standard requires `GET /deployments/{id}/datastreams` as a SHALL-level mandate. OSH does not implement it. `GET /deployments/{id}/observations` doesn't exist in the standard at all. Plan accordingly.**

---

## 10  Related Reports

| Report | Relevance |
|---|---|
| [CSAPI_Deployed_Systems_Design_Pattern.md](CSAPI_Deployed_Systems_Design_Pattern.md) | The report this document corrects. Its architectural recommendations remain valid; its implementation claims about deployment-scoped data endpoints are incorrect. |
| [OSH_DeployedSystems_Conformance_Probe.md](OSH_DeployedSystems_Conformance_Probe.md) | Proved that `deployedSystems@link` is silently dropped by OSH. A related but distinct conformance gap. |
| [OSH_Deployment_Link_Persistence_Gap.md](OSH_Deployment_Link_Persistence_Gap.md) | Documents that `deployment@link` on datastreams is not persisted by OSH — consistent with the finding here that OSH rejects `deployment@link` on PUT. |
| [CSAPI_Deployment_Modeling_Standards_Conformance.md](CSAPI_Deployment_Modeling_Standards_Conformance.md) | Standards conformance analysis for deployment modeling approaches. |
| [CSAPI_Deployment_Reparenting_Feasibility.md](CSAPI_Deployment_Reparenting_Feasibility.md) | Confirms the deployment hierarchy pattern works today, independent of the data endpoint gaps. |

---

## 11  Appendix: Spec Source References

All spec references are from the OGC Connected Systems API GitHub repository at [opengeospatial/ogcapi-connected-systems](https://github.com/opengeospatial/ogcapi-connected-systems) (branch: `master`), which is the normative source for the published standard:

| Reference | Link |
|---|---|
| Part 2, Clause 8 (DataStreams & Observations) | [clause_8_requirements_class_datastreams.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_8_requirements_class_datastreams.adoc) |
| Part 2, Clause 9 (ControlStreams & Commands) | [clause_9_requirements_class_controlstreams.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_9_requirements_class_controlstreams.adoc) |
| Part 2, Clause 14 (Advanced Filtering) | [clause_14_requirements_class_advanced_filtering.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_14_requirements_class_advanced_filtering.adoc) |
| Part 2, Clause 6 (Overview) | [clause_6_overview.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_6_overview.adoc) |
| Part 2, Clause 20 (JSON Encoding) | [clause_20_requirements_class_json_encoding.adoc](https://github.com/opengeospatial/ogcapi-connected-systems/blob/master/api/part2/standard/sections/clause_20_requirements_class_json_encoding.adoc) |
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
