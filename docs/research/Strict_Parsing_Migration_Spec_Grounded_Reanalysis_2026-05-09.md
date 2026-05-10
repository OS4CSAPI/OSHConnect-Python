# Strict-Parsing Migration — Spec-Grounded Re-Analysis

**Date:** 2026-05-09 (issued same day as the initial findings)
**Author:** OS4CSAPI engineering (sbolling)
**Status:** **Supersedes** [`Strict_Parsing_Migration_Findings_Publisher_Fleet_2026-05-09.md`](./Strict_Parsing_Migration_Findings_Publisher_Fleet_2026-05-09.md) on remediation guidance.
**Scope:** Re-anchors the publisher-rejection findings against (a) the upstream commit that introduced strict parsing and (b) the OGC standards listed in [`ogc-client-CSAPI_2/docs/research/references.md`](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/phase-9/docs/research/references.md).

---

## 0. What changed between the two reports

The earlier report, written from the Go server's struct layout alone, concluded that publishers should **lift `keywords`/`documentation` out of `properties` to the top level of the GeoJSON Feature**. That conclusion **does not match the OGC 23-001 OpenAPI specification.** The spec puts SensorML metadata in a different encoding entirely, not at a different nesting level of the same encoding.

This report replaces section 4 ("the bug shape"), section 5 (ISS), and section 10 (remediation) of the prior document. Sections 7 and 9 (raw rejection data) remain valid and are not restated here.

---

## 1. The upstream commit

**Commit:** [`a467aba0e413c75cde02e4c881a836207763b6ec`](https://github.com/SomethingCreativeStudios/connected-systems-go/commit/a467aba0e413c75cde02e4c881a836207763b6ec)
**Author:** SomethingCreativeStudios (the upstream maintainer; not OS4CSAPI)
**Date:** 2026-05-02 ("last week" relative to today)
**Parent:** `c2ab201f502e8d92dadddd94096ce2d270e4d05c`
**Branch:** `main` (single linear commit, no PR)
**Title:** *"Adding Strict Parsing... now unknown fields will cause a bad request with the path and field name"*
**Diff size:** 17 files changed, +491 / −55

### 1.1 Was this in response to an issue we filed?

**No.** The commit:
- Was pushed directly to `main` (no PR).
- References no GitHub issue in its message.
- Was not preceded by any issue on `SomethingCreativeStudios/connected-systems-go` from the OS4CSAPI org. The two server-conformance issues we know we filed against this fork's tracker — [#5](https://github.com/OS4CSAPI/connected-systems-go/issues/5) (`?uid=` filter ignored) and [#11](https://github.com/OS4CSAPI/connected-systems-go/issues/11) (temporal parameters ignored) — are on the **OS4CSAPI fork**, not on the upstream `SomethingCreativeStudios` repo.
- The upstream repo currently has 7 open issues and 1 open PR; none of the issue titles describe an unknown-fields complaint.

The commit is the maintainer's own initiative. A plausible motive (from the diff: explicit handling of `IOItem`'s polymorphic JSON, named field errors for `TimeRange`, etc.) is to **catch publisher / client typos at the wire** rather than silently truncating them — exactly the failure mode our publishers exhibited.

### 1.2 What the commit actually does

Three structural pieces:

1. **`internal/model/common_shared/decode.go` (+202 / −4):**
   - Adds a generic `DecodeWithFieldErrors[T any](data []byte) (T, error)`.
   - Introduces `UnknownFieldError{Field, Path}` (path is dotted/indexed JSON path; field is the offending key).
   - Walks the target Go struct's reflected type alongside the raw JSON to compute the path of the first key that doesn't map to a declared, JSON-tagged field.
   - Honors `json.Unmarshaler` boundaries: unknown fields *inside* a type with a custom `UnmarshalJSON` (e.g. `IOItem`'s polymorphic handling) are explicitly tolerated. Strictness only applies to plain-struct decode paths.

2. **`internal/api/errors.go` (+10):**
   - Sanitizes the new `UnknownFieldError` into the user-facing 400 body. Without this hook, the path-aware error would have been wrapped and lost.
   - This is what produces the response we now see: `{"error":"unknown field 'keywords' in properties"}`.

3. **All deserializers wired through the new decoder:**
   - GeoJSON formatters: `deployment_geojson.go`, `feature_geojson.go`, `procedure_geojson.go`, `property_geojson.go`, `sampling_feature_geojson.go`, `system_geojson.go`.
   - SensorML formatters: `deployment_sensorml.go`, `procedure_sensorml.go`, `property_sensorml.go`, `sampling_feature_sensorml.go`, `system_sensorml.go`.
   - JSON formatters: `control_stream_json.go`.
   - Each replaces a previous `json.NewDecoder(reader).Decode(&geoJSON)` call with `common_shared.DecodeWithFieldErrors[...](body)`.

4. **Test scaffolding (+208):**
   - `decode_test.go` (110 lines) and `io_test.go` (98 lines) confirm the contract: unknown fields produce path-tagged 400s, but custom-unmarshaller types tolerate vendor extensions.

The change is internally well-engineered and intentional. It is **not a regression**, it is a deliberate tightening of the wire contract.

---

## 2. What the OGC standards actually say

References from [`ogc-client-CSAPI_2/docs/research/references.md`](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/phase-9/docs/research/references.md) cited below:
- OGC 23-001 (CSAPI Part 1 — Feature Resources)
- OGC 23-001 OpenAPI bundle ([`ogcapi-connectedsystems-1.bundled.oas31.yaml`](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/main/docs/research/standards/ogcapi-connectedsystems-1.bundled.oas31.yaml))
- OGC 23-002 (CSAPI Part 2 — Dynamic Data) and its bundled OAS
- OGC 23-000r1 (SensorML 3.0)
- RFC 7946 (GeoJSON)

### 2.1 Part 1 defines two encodings, not one

Per the OGC 23-001 OAS bundle, every Part 1 resource has **two** distinct schemas:

| Resource | GeoJSON shape | SensorML shape |
|---|---|---|
| Procedure | `procedure` (line 4690) | `procedure-2` (line 4709) |
| System | `system` (line 1908) | `system-2` (line ~5124) |
| Deployment | `deployment` (line 4560) | `deployment-2` (line 4737) |
| SamplingFeature | `samplingFeature` (line 4754) | `samplingFeature-2` |

Content negotiation (per OGC API – Common and confirmed by the GeoJSON / SensorML media-type registry in OGC 23-000r1) selects between them:
- `application/geo+json` (default) → the GeoJSON Feature shape.
- `application/sml+json` → the SensorML `DescribedObject` shape.

These are **not two views of the same body shape**. They are two different bodies for two different content types. The fields in one are not the fields in the other.

### 2.2 The GeoJSON shape's `properties` is closed and tiny

OGC 23-001 OAS, the `feature` schema (line 1835–1875), defines `properties` as an object with exactly four declared keys:

```yaml
properties:
  description: Feature properties
  type: object
  required: [featureType, uid, name]
  properties:
    featureType: { type: string }
    uid:         { type: string, format: uri }
    name:        { type: string, minLength: 1 }
    description: { type: string, minLength: 1 }
```

The Procedure-specific override (`procedure`, line 4690) refines `properties.featureType` to one of the SOSA procedure URIs (e.g. `sosa:ObservingProcedure`). The System and Deployment overrides do similar narrowing. **No override anywhere in OGC 23-001 adds new keys to `properties`.** The deployment override does add `validTime`, `platform@link`, and `deployedSystems@link` inside `properties` — that is the only deployment-specific extension and it is the only place `validTime` legitimately appears inside `properties` in the entire Part 1 GeoJSON schema family.

In particular: **`keywords`, `documents`, `documentation`, `contacts`, `identifiers`, `classifiers`, `characteristics`, `capabilities`, `history`, `validTime` (on a Procedure), `inputs`, `outputs`, `parameters`, etc., are not allowed inside `properties` of a Procedure or System GeoJSON Feature.** None of them are allowed at the top level of the GeoJSON Feature either, because the GeoJSON Feature schema only adds `id`, `geometry`, `bbox`, `properties`, and `links` to RFC 7946's base shape.

### 2.3 Where SensorML metadata legitimately lives

OGC 23-001 OAS, the `DescribedObject` schema (line 3432, `allOf` parent of `procedure-2` / `system-2` / `deployment-2`), defines these top-level fields:

```
type, id, description, uniqueId, label, lang,
keywords, identifiers, classifiers,
validTime, securityConstraints, legalConstraints,
characteristics, capabilities,
contacts, documents, history
```

These are **siblings of `type`**, not nested in any `properties` envelope. There is no `properties` key on `DescribedObject` at all — what looks like one in `procedure-2` is the PhysicalSystem/SimpleProcess/etc. process-type discriminator, not a GeoJSON `properties` envelope.

Critical: the spec field name is **`documents`** (plural noun), not `documentation`. `documentation` appears only on the `Event` schema (line 3413), which is the type used inside `history[]`. They are different fields with different meanings.

### 2.4 `procedure@link` is Part 2 only

The string `procedure@link` does not appear anywhere in OGC 23-001 OAS. In OGC 23-002 OAS it appears 5 times — exclusively on Datastreams, Observations, ControlStreams, and Commands. There is no Part 1 schema (System, Procedure, Deployment, SamplingFeature) in which `procedure@link` is valid.

The Part 1 link from a system to its procedure is `typeOf` (top-level on the `system-2` SensorML shape, per OGC 23-001 §7.6 and the SensorML 3.0 `typeOf` definition).

---

## 3. Where each party stands relative to the spec

### 3.1 The publishers (what they're sending)

All non-ISS publishers POST to `/procedures` with `Content-Type: application/json` (defaulting the server to GeoJSON), with a body that nests SensorML metadata inside `properties`:

```python
{
  "type": "Feature",
  "geometry": None,
  "properties": {
    "uid": ...,
    "featureType": "sosa:ObservingProcedure",
    "name": ...,
    "description": ...,
    "keywords": [...],          # NOT VALID in Part 1 GeoJSON properties
    "documentation": [...],     # NOT VALID in Part 1 GeoJSON properties (and wrong field name)
    "validTime": [...],         # NOT VALID in Part 1 GeoJSON properties (Procedure)
    "contacts": [...],          # NOT VALID in Part 1 GeoJSON properties
  }
}
```

This body is non-conformant with **OGC 23-001 §7** under either content type:
- As `application/geo+json`: properties keys exceed the closed set `{featureType, uid, name, description}`.
- As `application/sml+json`: the body lacks the SensorML `DescribedObject` shape entirely (no top-level `type`, `uniqueId`, `label`, etc.) — it isn't a SensorML document at all.

Under the pre-strict server, all six extra `properties` keys were silently discarded and the persisted Procedure was a stub with only `featureType`, `uid`, `name`, `description`. Downstream consumers received that stub, never the metadata the publisher believed it had submitted.

### 3.2 ISS publisher (separate bug)

`bootstrap_iss.py` puts `procedure@link` on a System body. Under OGC 23-001:
- `procedure@link` doesn't exist on Part 1 resources at all.
- The Part 1 way to associate a System with its Procedure is `typeOf` on the SensorML form, or the SOSA semantic relation captured in datastream/observation links from Part 2.

The strict server happens to reject this with the same error class as the SensorML-fields case because both are "unknown field on a System decode path". The two bugs share a symptom but are independent in the spec.

### 3.3 The Go server (`SomethingCreativeStudios/connected-systems-go @ d14d16d3`)

The server's `internal/model/domains/system.go` and `procedure.go` define top-level Go struct fields (with explicit `json:"keywords"`, `json:"documentation"`, etc.) on the **GeoJSON-decoded** struct. After today's strict-parsing commit, the server therefore:

- **Accepts** SensorML metadata at the top level of the GeoJSON Feature body (siblings of `properties`), which **OGC 23-001 does not authorise** in the GeoJSON encoding. This is a server-side conformance gap: the server is more permissive than the spec on the GeoJSON path.
- **Renames** `documents` → `documentation` (likely picking up the SensorML 3.0 root-level naming inconsistently — SensorML 3.0 itself uses `documentation` on some elements and `documents` on others, but OGC 23-001 normalises to `documents` on the wire). This is also a conformance gap; consumers writing to spec will be rejected.
- **Rejects** SensorML metadata inside `properties`, which is correct.

So the server's strict-parsing change exposed a real publisher bug, while the server itself remains slightly off-spec in the opposite direction. A spec-strict client would still fail against this server because `documents` (per OGC 23-001) would now be reported as unknown.

### 3.4 Summary table (replaces §3 of the prior report)

| Field placement | OGC 23-001 says | Publishers do | Go server does |
|---|---|---|---|
| `keywords` inside GeoJSON `properties` | invalid | yes (8/9) | rejects (correct) |
| `keywords` top-level on GeoJSON Feature | invalid | no | accepts (server too permissive) |
| `keywords` top-level on SensorML `DescribedObject` | **valid** | not used | accepts (correct) |
| `documents` (plural) top-level SensorML | **valid** | no | rejects with "unknown field" (server bug — wrong name) |
| `documentation` top-level SensorML | invalid (this name is for Events only) | no | accepts (server bug — wrong name) |
| `documentation` inside GeoJSON `properties` | invalid | yes (USGS-EQ) | rejects (correct outcome via wrong rule) |
| `procedure@link` on a Part 1 System | invalid | yes (ISS) | rejects (correct) |
| `procedure@link` on a Part 2 Datastream | **valid** (OGC 23-002) | not used | accepts (correct) |

---

## 4. Corrected remediation guidance

The prior report told publishers to lift fields from `properties` to the top level of the GeoJSON body. That's wrong by spec. Correct guidance:

### 4.1 Don't put SensorML metadata in a GeoJSON Procedure body at all

If a publisher only knows GeoJSON-shape Procedure metadata (uid + featureType + name + description), it should send exactly that — a thin Feature with a closed `properties` envelope:

```python
PROCEDURE_BODY_GEOJSON = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "featureType": "sosa:ObservingProcedure",
        "uid":         "urn:os4csapi:procedure:nws-surface-obs:v1",
        "name":        "NWS Surface Observation v1",
        "description": "...",
    },
}
api_post(base_url, "procedures", PROCEDURE_BODY_GEOJSON, auth,
         content_type="application/geo+json")
```

This passes both the OGC 23-001 OAS validation and the strict Go server today.

### 4.2 To carry SensorML metadata, send it as SensorML

Publishers that want to ship `keywords`, `contacts`, `documents`, `validTime`, `characteristics`, etc., should make a *second* call (PUT or replace-on-create) using the SensorML encoding:

```python
PROCEDURE_BODY_SML = {
    "type":     "SimpleProcess",
    "id":       "...",
    "uniqueId": "urn:os4csapi:procedure:nws-surface-obs:v1",
    "label":    "NWS Surface Observation v1",
    "definition": "sosa:ObservingProcedure",
    "keywords":      ["NWS", "ASOS", "AWOS", ...],
    "documents":     [{"name": "...", "link": {"href": "..."}}],
    "contacts":      [...],
    "validTime":     ["2026-01-01T00:00:00Z", "now"],
}
api_put(base_url, f"procedures/{proc_id}", PROCEDURE_BODY_SML, auth,
        content_type="application/sml+json")
```

This is the existing `--force-sml` path that the May 6 finding ([`Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md`](./Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md)) was already exercising. The May 6 fix to rename `documents` → `documentation` was actually moving **away** from the spec; that rename should be reverted in the publisher template, with a temporary local kludge to accommodate the Go server's mis-naming until [SomethingCreativeStudios/connected-systems-go#?](https://github.com/SomethingCreativeStudios/connected-systems-go/issues) is filed and fixed.

### 4.3 ISS specifically

Remove `procedure@link` from the `bootstrap_iss.py` System body. If a System → Procedure association is desired, encode it as `typeOf` on the SensorML form of the System (top-level), or via the Datastream's Part 2 `procedure@link` field once the publisher reaches that step.

### 4.4 Server-side issues to file upstream

Two distinct issues should be filed at `SomethingCreativeStudios/connected-systems-go`:

1. **Top-level SensorML fields on GeoJSON Procedure/System.** The Go GeoJSON struct accepts `keywords`, `documentation`, `contacts`, etc. as siblings of `properties`. OGC 23-001 §7 / `feature` schema does not permit this. These fields should be moved to (or only accepted via) the SensorML decode path. Reference: OAS bundle line 1835 (`feature.properties` closed shape) and lines 4690, 1908 (Procedure and System overrides).
2. **`documentation` vs `documents` field name.** OGC 23-001 OAS `DescribedObject.documents` (line 3508) defines the field as `documents`. The Go server's `internal/model/domains/system.go` and `procedure.go` use `documentation`. Renaming `documents` for `Event.documentation` is correct (line 3413); renaming it for `DescribedObject.documents` is not.

Both are server-side conformance gaps and should be tracked the same way [OS4CSAPI/connected-systems-go#5](https://github.com/OS4CSAPI/connected-systems-go/issues/5) and [#11](https://github.com/OS4CSAPI/connected-systems-go/issues/11) are tracked in [`references.md` § Known Server Conformance Gaps](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/phase-9/docs/research/references.md).

---

## 5. Updated recommended client behaviour for OSHConnect-Python

1. **Split `bootstrap_helpers.py` into `bootstrap_geojson.py` and `bootstrap_sensorml.py`** (or a single helper with a `format=` parameter). The GeoJSON path constructs a closed-`properties` Feature; the SensorML path constructs a `DescribedObject`. Stop mixing them.
2. **Default flow** for all 9 publishers becomes: POST GeoJSON to create the resource (gets the server-assigned id and the canonical link), then PUT SensorML to attach metadata. This is the pattern OGC 23-001 envisions and the only one that round-trips field-for-field through both pre-strict and strict servers.
3. **Verify round-trip**: after PUT, GET with `Accept: application/sml+json` and assert each top-level field that was sent is present in the response. This is the only way to detect either (a) a future server reverting strictness or (b) a publisher accidentally falling back to the GeoJSON path with SML payload.
4. **Spec-citation comments** in publisher source: each non-trivial field gets a `# OGC 23-001 §X.Y / DescribedObject.<field>` comment so future editors don't re-introduce the silent-loss pattern.

---

## 6. What this means for the `csapi-go-v2` rollout

- The fleet's existing publishers cannot bootstrap to the new server unmodified. Three publisher-side fix tracks are required (GeoJSON-properties cleanup, SensorML dual-path enablement, ISS `procedure@link` removal).
- The Go server itself has two upstream conformance gaps that will trip a spec-strict client even after the publishers are correct.
- Until both fronts converge, the explorer demo's "live data" preset should remain pointed at `csapi-go-head` (the pre-strict server, which still has 17 systems and 1 deployment loaded). That data is metadata-incomplete by §2.2 of this report, but it's the only live corpus we have today.
- A clean reload onto `csapi-go-v2` only makes sense *after* the publisher fixes ship and the two server issues are filed (and ideally resolved).

---

## 7. Cross-references

- [`Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md`](./Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md) — original NWS-only finding; its `documents` → `documentation` fix should now be reverted per §4.2.
- [`Strict_Parsing_Migration_Findings_Publisher_Fleet_2026-05-09.md`](./Strict_Parsing_Migration_Findings_Publisher_Fleet_2026-05-09.md) — fleet-wide rejection data still valid; remediation in §10 of that document is superseded by §4 here.
- Upstream commit: [`SomethingCreativeStudios/connected-systems-go@a467aba0`](https://github.com/SomethingCreativeStudios/connected-systems-go/commit/a467aba0e413c75cde02e4c881a836207763b6ec)
- OGC standards bundle in this workspace: [`ogc-client-CSAPI_2/docs/research/standards/ogcapi-connectedsystems-1.bundled.oas31.yaml`](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/main/docs/research/standards/ogcapi-connectedsystems-1.bundled.oas31.yaml) and [`ogcapi-connectedsystems-2.bundled.oas31.yaml`](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/main/docs/research/standards/ogcapi-connectedsystems-2.bundled.oas31.yaml)
- References inventory: [`ogc-client-CSAPI_2/docs/research/references.md`](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/blob/phase-9/docs/research/references.md)

---

## 8. TL;DR (corrected)

> The strict-parsing commit was the upstream maintainer's own initiative on 2026-05-02 — not in response to anything we filed. It correctly identifies real schema violations on the publisher side. **But the prior report's remediation guidance was wrong.** The OGC 23-001 standard does not permit `keywords`, `documents`, `contacts`, etc. anywhere in the GeoJSON Feature body — neither inside `properties` nor at the top level. They live in the **separate `application/sml+json` encoding**, top-level on `DescribedObject`. The fleet's correct fix is dual-content publication (POST GeoJSON, then PUT SensorML), not field relocation in the GeoJSON body. The Go server itself also has two minor conformance gaps (accepting SensorML fields on its GeoJSON path, and renaming `documents` to `documentation`) that should be filed upstream.

---

## 9. Empirical probe — 2026-05-09 evening (supersedes §3.3 and §4.4 conclusions)

After publishing the reanalysis above, we ran a direct probe against the live strict server `https://129-80-248-53.sslip.io/csapi-go-v2/` and against upstream issue [OS4CSAPI/connected-systems-go#10](https://github.com/OS4CSAPI/connected-systems-go/issues/10). Two of the conclusions in §3.3 and §4.4 turned out to be wrong on the wire and need correction.

### 9.1 The `documents` vs `documentation` situation is **not what §3.3 said**

**§3.3 claim (now wrong):** *"The server renames `documents` → `documentation`. Spec-correct clients will be rejected."*

**Empirical truth:** The Go upstream maintainer already partially fixed this in commit [`c2ab201`](https://github.com/SomethingCreativeStudios/connected-systems-go/commit/c2ab201f502e8d92dadddd94096ce2d270e4d05c) ("time range and better 400") — the `SystemSensorMLFeature` struct (`internal/model/domains/system.go:148`) now uses the spec-correct `json:"documents,omitempty"` tag. **PUT `/systems/{id}` with `Content-Type: application/sml+json`** routes through this fixed struct, so spec-correct `"documents":[...]` is **accepted** under strict parsing (HTTP 204) and round-trips back through `GET ?Accept: application/sml+json`. `"documentation":[...]` on the same path is **rejected** with `{"error":"unknown field 'documentation'"}` — the opposite of the §3.3 claim.

The maintainer described the bug as *"Typo in schema"* on the issue triage and shipped the fix on the SML output path. Per the user's follow-up audit on issue #10, **2 of 9 sites are corrected; 7 remain on `documentation`** — but those 7 are on Procedure, Deployment, SystemEvent, History, and the **GeoJSON-decoded `System`/`Procedure` input structs**, none of which are reachable from a spec-correct client using dual-content publish.

### 9.2 The PUT-SML route uses the OGC SensorML JSON encoding correctly

The strict server's PUT-SML route accepts and round-trips the canonical OGC SensorML JSON encoding *as written in OGC 23-001* — not the GeoJSON encoding's field names. Confirmed live:

| Field on PUT `/systems/{id}` `application/sml+json` | Result |
|---|---|
| `type: "PhysicalSystem"` | accepted |
| `uniqueId: "urn:..."` | accepted (✗ `uid` is rejected as unknown) |
| `label: "..."` | accepted (✗ `name` is rejected as unknown) |
| `definition: "http://www.w3.org/ns/sosa/Sensor"` | accepted (✗ `featureType` is rejected) |
| `description`, `keywords`, `identifiers`, `contacts`, `documents` | accepted, round-trip |
| `documentation` | **rejected** with `unknown field 'documentation'` |

GET `/systems/{id}` with `Accept: application/sml+json` returns the same field names — `uniqueId`, `label`, `definition`, `documents` etc. The encoding is symmetric and matches the OGC spec.

### 9.3 So why are publishers being rejected?

Not because of `documents`/`documentation` — that's a red herring as of c2ab201. Publishers are rejected because **they put SensorML metadata (`keywords`, `documentation`, `contacts`, `lineage`, `usageConstraints`, `validTime`, ...) inside `properties` of the GeoJSON POST body**. Strict parsing correctly rejects them as unknown fields in `properties`. This is exactly what §3.1 and §4 already said; §3.3 was a distraction.

### 9.4 Corrected upstream-issue-filing recommendation

The §4.4 issue list should be reduced from two issues to one:

- **DROP** the `documents` vs `documentation` upstream issue (#4.4 item 2). The maintainer already filed and partially fixed it on issue #10; the SML PUT round-trip path (the only path a spec-correct client uses) works. The remaining 7 sites are on internal Go structs that are never reached from a spec-correct dual-content client.
- **KEEP** the GeoJSON top-level SensorML acceptance issue (#4.4 item 1), but only if/when we observe a real consumer affected. It is currently latent because publishers do not put SML fields at the GeoJSON top level.

### 9.5 What this means for "make our shit work"

The fix is fully infrastructure-supported in `publishers/bootstrap_helpers.py` already — `upsert_system(stub, sml_body=...)` POSTs the GeoJSON stub then PUTs the SensorML body with `application/sml+json`. Publishers need to stop emitting SML fields inside `stub.properties` and emit them inside `sml_body` instead. Per-publisher this is mechanical:

| What goes in `stub.properties` | What goes in `sml_body` |
|---|---|
| `featureType`, `uid`, `name`, `description` | `type`, `uniqueId`, `label`, `definition`, `description` |
| (nothing else) | `keywords`, `identifiers`, `classifiers`, `contacts`, `documents`, `characteristics`, `capabilities`, `validTime`, `typeOf`, `lineage`, `usageConstraints`, `securityConstraints`, `legalConstraints`, ... |

This is the dual-content publish pattern §4.2 already prescribed. It works against `csapi-go-v2` empirically as of today.

### 9.6 Probe transcript reference

Run from `OSHConnect-Python` workspace, 2026-05-09 03:04–03:10 UTC, against `https://129-80-248-53.sslip.io/csapi-go-v2/`:

1. `POST /systems` (geo+json, closed properties) → 201 Created, `Location: /systems/9b31c57b-...`
2. `PUT /systems/{id}` (sml+json, top-level `uid`) → 400 `unknown field 'uid'`
3. `PUT /systems/{id}` (sml+json, top-level `uniqueId`/`label`/`definition`) → 204 No Content
4. `PUT /systems/{id}` (sml+json, + `documents`) → 204 No Content
5. `PUT /systems/{id}` (sml+json, + `documentation`) → 400 `unknown field 'documentation'`
6. `GET /systems/{id}` (sml+json) → 200 with `uniqueId`, `label`, `definition`, `documents`, `keywords`, `identifiers`, `contacts` round-tripped
7. `DELETE /systems/{id}` → 204 (cleanup)
