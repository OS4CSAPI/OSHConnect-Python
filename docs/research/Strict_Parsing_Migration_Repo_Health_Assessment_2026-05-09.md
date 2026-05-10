# Strict-Parsing Migration — Repo Health Assessment

**Date:** 2026-05-09
**Branch:** `fix/aviation-wx-strict-parsing-2026-05-09`
**Scope:** Honest assessment of whether the strict-parsing publisher refactor is improving the OSHConnect-Python repository, with a thorough catalog of upstream `csapi-go-v2` server issues discovered during the work.
**Companion documents:**
- `Strict_Parsing_Aviation_WX_Pilot_Engineering_Report_2026-05-09.md` (per-resource empirical schema)
- `Strict_Parsing_Migration_Findings_Publisher_Fleet_2026-05-09.md` (fleet-wide findings)
- `Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md` (OGC 23-001 grounding)

---

## 1. Executive Summary

The strict-parsing migration is a **net positive** for the repository, but the
gain is narrow and is partially offset by real regressions. This report
separates the wins from the costs, then exhaustively catalogs the upstream
`csapi-go-v2` (Go reference server) issues we discovered while doing the work,
so the team can read them, file them upstream, and decide which workarounds
have an expiry date.

**Bottom line:**

- Net positive on **portability**, **OGC 23-001 conformance**, and **documented
  empirical knowledge**.
- Net negative on **metadata fidelity over the wire** (lossy round-trip vs. the
  legacy OSH server) and **maintenance surface area** (mechanical workarounds
  copy-pasted into each publisher).
- **Four upstream defects** identified in `csapi-go-v2`. Two are clear bugs,
  one is an asymmetric/incomplete fix, one is a server-side internal error.
  Each is described in §4 with reproducer probes.

---

## 2. What Is Genuinely Improving

### 2.1 Server portability expanded

Each refactored publisher now works against **both** server families:

| Server | Behavior before refactor | Behavior after refactor |
|---|---|---|
| OSH SensorHub (legacy, permissive) | ✅ Worked (silently dropped extra props) | ✅ Still works |
| `csapi-go-v2` (strict, OGC 23-001) | ❌ Rejected with `unknown field` 400s | ✅ Works |

Closed-properties is a **strict subset** of what OSH accepts, so we are not
losing OSH support. We are gaining a second deployment target. This matters
because the OGC reference implementation is the long-term direction; OSH is
the legacy comfort zone.

### 2.2 Architectural separation is now correct

The pre-refactor pattern was:

```
POST /systems  Content-Type: application/geo+json
{
  "type": "Feature",
  "properties": {
    "uid": "...",
    "featureType": "sosa:Sensor",
    "name": "...",
    "description": "...",
    "typeOf@link": {...},          ← not in OGC 23-001 GeoJSON properties
    "links": [...],                ← not in OGC 23-001 GeoJSON properties
    "validTime": [...],            ← not in OGC 23-001 GeoJSON properties
    "keywords": [...],             ← SensorML field, wrong encoding
    "documentation": [...],        ← SensorML field, wrong encoding
    "contacts": [...],             ← SensorML field, wrong encoding
    "lineage": {...},              ← SensorML field, wrong encoding
    "characteristics": [...],      ← SensorML field, wrong encoding
    "capabilities": [...]          ← SensorML field, wrong encoding
  }
}
```

OSH accepted this because it ignored everything outside its known set. The
strict server refused. **The strict server is correct.** OGC 23-001 §
"Resource creation" specifies that GeoJSON `properties` for systems carries
a closed set of fields, and SensorML metadata is conveyed via a separate
`application/sml+json` representation (typically PUT after POST).

The refactored pattern is:

```
POST /systems  Content-Type: application/geo+json   ← stub only
{
  "type": "Feature",
  "geometry": {...},
  "properties": {
    "featureType": "sosa:Sensor",
    "uid": "...",
    "name": "...",
    "description": "..."
  }
}

PUT /systems/{id}  Content-Type: application/sml+json   ← rich metadata
{
  "type": "PhysicalSystem",
  "id": "...",
  "uniqueId": "...",
  "label": "...",
  "keywords": [...],
  "identifiers": [...],
  "classifiers": [...],
  "contacts": [...],
  "documents": [...],
  "position": {...}
}
```

This is the standards-compliant shape. Future readers of the codebase will
not have to reason about why a SensorML `keywords` field is living inside a
GeoJSON `properties` block — because it isn't anymore.

### 2.3 Empirical schema captured as durable knowledge

The pilot engineering report (`Strict_Parsing_Aviation_WX_Pilot_Engineering_Report_2026-05-09.md`)
records **per-resource, per-method field acceptance**, derived from live
probes on `https://129-80-248-53.sslip.io/csapi-go-v2/` (no auth). This is
re-usable for:

- Every remaining publisher in the fleet (7 still TODO).
- Any future consumer code that wants to know which fields will survive a
  round trip.
- Filing upstream issues with concrete reproducers.

Without this document, each engineer would re-run the same probes by hand
and infer the same constraints from 400 responses.

### 2.4 Helper infrastructure proven under load

`publishers/bootstrap_helpers.py` already exposed `ensure_procedure(...,
sml_body=...)`, `ensure_system(..., sml_body=...)`, and
`ensure_deployment(..., sml_body=..., parent_id=...)`. The
`OS4CSAPI_STRICT_BOOTSTRAP=1` environment guardrail raises `RuntimeError`
on closed-properties leakage during dry-run. Both have now been validated
against a real strict server with two publishers (aviation-wx, NDBC). They
work; reuse for the remaining seven publishers is mechanical.

### 2.5 Architectural defects in upstream surfaced

The migration forced four latent defects in `csapi-go-v2` to surface (§4).
Without strict parsing, these would have remained invisible: the legacy OSH
server's permissiveness was hiding them. We now have reproducible probes
for each.

---

## 3. What Is *Not* Improving (and Honest Costs)

### 3.1 Information loss over the wire

The strict server rejects fields that the OGC SensorML JSON encoding defines
as legitimate. Concretely, on `PUT /systems/{id}` with
`application/sml+json`, the server returns 400 for:

- `characteristics` — used by every refactored publisher to expose physical
  properties (heights, depths, owner, platform type, payload type, etc.).
- `capabilities` — used to expose publisher capabilities (update interval,
  data source).

We have **dropped these from the wire** and added a `NOTE:` comment. The
information lives in source code only; the server holds none of it. A
consumer hitting the strict server gets less metadata than the same consumer
hitting OSH.

We also do not currently send `lineage` or `usageConstraints` — they were
in `properties` (wrong encoding) before and we did not migrate them into the
SML body because no SML JSON binding location for them was confirmed
acceptable by the strict server. They are still in source code as comments.

This is a **regression in metadata fidelity** vs. the legacy server. It is
recoverable as soon as upstream accepts the fields, but until then,
consumers see less.

### 3.2 No automated test coverage was added

Every validation in this work is **manual live-run** against the public
instance:

- Dry-run with `OS4CSAPI_STRICT_BOOTSTRAP=1` to catch property leakage.
- `--clean` live-run to confirm 2xx on POST + PUT.
- Manual `urllib.request` round-trip GET as `application/sml+json`.

If the upstream server changes (e.g., upstream fixes the procedure typo,
or accepts `characteristics`), we will not learn about it until the next
manual run. Recommended (§6) is at least one contract test per publisher
that pins the closed-properties shape and asserts SML round-trip.

### 3.3 Mechanical pattern is being copy-pasted

Each publisher refactor is the same surgery:

1. Split `PROCEDURE_BODY` → `_STUB` + `_SML`.
2. Strip `_system_stub` to closed properties.
3. Drop `characteristics`/`capabilities` from `_system_sml`.
4. Strip `_datastream_schema` of `uid`/`documentation`/`characteristics`/Time
   `referenceTime`.
5. Strip deployment stubs.
6. Wire `sml_body=` and `force_sml=` into `ensure_procedure(...)` calls.

Done by hand on aviation-wx (5 systems) and NDBC (2 procedures, 5 systems,
dual datastream schemas). Seven publishers remain (coops, iss, nws,
opensky, usgs_eq, usgs_nims, usgs_water). Without an extracted helper,
every fix to an upstream defect (e.g., when the procedure `documentation`
typo is fixed) requires editing N publishers.

### 3.4 Workarounds carry "unfixed upstream typo" notes inline

Every refactored procedure body contains a comment like:

```python
# NOTE: csapi-go-v2 ProcedureSensorMLFeature has the c2ab201 typo unfixed;
# use 'documentation' (not 'documents'). /systems uses 'documents'.
"documentation": [...]
```

This is correct today and will be wrong tomorrow once upstream lands the
matching rename on `ProcedureSensorMLFeature`. Without an extracted helper,
the cleanup will be a cross-file find/replace exercise.

---

## 4. Upstream `csapi-go-v2` Issues Found

This is the catalog of bugs and asymmetries we observed in the OGC reference
Go server (`https://129-80-248-53.sslip.io/csapi-go-v2/`) while doing the
migration. Each entry includes: **what we observed**, **why we believe it is
a defect**, **reproducer**, **current workaround in our code**, **expiry
condition** (what upstream change retires the workaround).

> **Server context:** This is the server post-commit `a467aba0` (strict
> parsing landed) and post-commit `c2ab201` (a partial typo fix renaming
> `documentation` → `documents` on SystemSensorMLFeature). The defects below
> are observed *after* both of those commits.

### 4.1 Issue #1 — Procedure SensorML asymmetric typo: `documentation` not renamed

**Severity:** P1 — blocks any client trying to write SensorML to `/procedures`
using OGC-spec field names.

**Observed behavior:**

`PUT /systems/{id}` with `Content-Type: application/sml+json` accepts
`"documents": [...]` (the spec-correct field name) and returns 204.

`PUT /procedures/{id}` with the same content type and the same payload
shape returns:

```
HTTP 400: unknown field 'documents'
```

It only accepts `"documentation": [...]` — the *typo* version that was
supposed to be renamed by upstream commit `c2ab201`.

**Why it's a defect:**

`c2ab201` was an upstream rename intended to replace `documentation`
(typo) with `documents` (spec-correct) across all SensorML-bearing
features. The change landed on `SystemSensorMLFeature` but not on
`ProcedureSensorMLFeature`. This is an *incomplete refactor* — both
endpoints should have the same field-name contract.

**Reproducer (verbatim probe):**

```python
import urllib.request, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
sml = {
    "type": "SimpleProcess",
    "id": "<procedure-id>", "uniqueId": "<uid>",
    "label": "test",
    "documents": [{"role": "http://example.org/doc", "name": "x",
                   "link": {"href": "http://example.org/", "type": "text/html"}}],
}
req = urllib.request.Request(
    "https://129-80-248-53.sslip.io/csapi-go-v2/procedures/<id>",
    method="PUT", data=json.dumps(sml).encode(),
    headers={"Content-Type": "application/sml+json"})
urllib.request.urlopen(req, context=ctx)
# → HTTPError 400: unknown field 'documents'
```

Switch the key to `"documentation"` and the same request returns 204.

**Current workaround:**

In every refactored publisher's procedure SML body:

```python
PROCEDURE_SML = {
    ...
    # NOTE: csapi-go-v2 ProcedureSensorMLFeature has the c2ab201 typo unfixed;
    # use 'documentation' (not 'documents'). /systems uses 'documents'.
    "documentation": [...],
}
```

System SML bodies use the spec-correct `"documents"`.

**Expiry condition:**

Upstream applies the `c2ab201` rename to `ProcedureSensorMLFeature`. After
that, every `PROCEDURE_SML` in our publishers needs `documentation` →
`documents`.

**Suggested upstream fix:** mechanical — same patch as `c2ab201` applied to
`ProcedureSensorMLFeature` JSON struct tag.

---

### 4.2 Issue #2 — System SensorML rejects `characteristics` and `capabilities`

**Severity:** P1 — blocks legitimate SensorML metadata for physical systems.

**Observed behavior:**

`PUT /systems/{id}` with `Content-Type: application/sml+json` returns 400
when the body contains either:

```json
"characteristics": [
  {"label": "Station Properties", "characteristics": [...]}
]
```

or

```json
"capabilities": [
  {"definition": "...", "label": "...", "capabilities": [...]}
]
```

Error text: `unknown field 'characteristics'` (or `'capabilities'`).

**Why it's a defect:**

`characteristics` and `capabilities` are **first-class fields in the OGC
SensorML 2.0 JSON encoding** (and in the SensorML 2.0 XML schema before
that). They are not extensions; they are the documented mechanism for
exposing static physical properties (`characteristics`) and operational
parameters (`capabilities`) of a system.

The OGC API – Connected Systems standard does not modify SensorML in a way
that removes these fields. Their absence from the server's accepted set is
a gap, not a deliberate exclusion.

**Reproducer:**

Take any minimal accepted SML body (label + identifiers), add either:

```python
"characteristics": [{"label": "x", "characteristics": [
    {"type": "Text", "name": "owner", "label": "Owner", "value": "NOAA"}
]}]
```

PUT it. 400 with `unknown field 'characteristics'`. Same for `capabilities`.

**Current workaround:**

Drop both fields. Add a code comment explaining the loss:

```python
# NOTE: characteristics/capabilities are part of OGC SensorML JSON encoding
# but the strict csapi-go-v2 server does not accept them on
# SystemSensorMLFeature (empirical probe 2026-05-09). Equivalent atoms
# preserved via identifiers/classifiers/position. char_items (owner,
# platform_type, payload_type, heights/depths) are not serialised here;
# restore once upstream adds these fields back.
```

In aviation-wx and NDBC, this means **per-station physical metadata**
(barometer height, anemometer height, water depth, sea-temp depth, watch
circle radius, etc.) is dropped on the wire. It exists only in the
publisher source.

**Expiry condition:**

Upstream `SystemSensorMLFeature` accepts `characteristics` and
`capabilities`. After that, restore the `char_items` and `capabilities`
blocks in every publisher's `_system_sml()`.

**Suggested upstream fix:** add JSON struct tags / decoder fields for
`characteristics` and `capabilities` matching the SensorML 2.0 JSON binding.

---

### 4.3 Issue #3 — System SensorML returns HTTP 500 on `typeOf`

**Severity:** P2 — server-side crash rather than a clean 400; blocks
representation of system→procedure linkage in SML.

**Observed behavior:**

`PUT /systems/{id}` with an SML body containing:

```json
"typeOf": {"href": "<procedure-id>", "title": "..."}
```

returns **HTTP 500** (not 400). Body is an opaque server error string,
not the structured `unknown field` message used elsewhere.

**Why it's a defect:**

A server should never return 500 on a malformed (or unsupported) field in a
client request. The expected behavior is either:

- 400 with `unknown field 'typeOf'` (consistent with how the server handles
  every other unrecognized field), or
- 204, treating `typeOf` as a valid SensorML linkage element.

A 500 implies an unhandled panic or nil-deref deeper in the decoder, which
is a server bug independent of whether `typeOf` should be accepted.

**Reproducer:**

```python
sml = {"type": "PhysicalSystem", "id": "<id>", "uniqueId": "<uid>",
       "label": "x",
       "typeOf": {"href": "<procedure-id>"}}
# PUT /systems/<id> as application/sml+json → 500
```

**Current workaround:**

System↔procedure linkage is **not represented at all** in our SML bodies.
The legacy `typeOf@link` lived in GeoJSON `properties` (rejected by closed
parsing) and the SML-side `typeOf` returns 500. We document the linkage
only as a `definition: "sosa:System"` URI on the SML root, which is
strictly weaker.

**Expiry condition:**

Upstream returns 4xx instead of 500 for `typeOf` (so we can probe further),
and ideally accepts the linkage. Until then, we cannot encode the
system→procedure association in SML at all.

**Suggested upstream fix:** at minimum, route unknown SensorML root fields
through the same `unknown field` 400 path as everything else. Then decide
whether `typeOf` should be accepted.

---

### 4.4 Issue #4 — Datastream rejects `referenceTime` on SWE Time field

**Severity:** P2 — forces dropping a documented SWE Common attribute.

**Observed behavior:**

`POST /datastreams` with a result schema field of:

```json
{"type": "Time", "name": "timestamp",
 "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime",
 "referenceTime": "1970-01-01T00:00:00Z",
 "uom": {"code": "s"}}
```

returns 400. Removing `referenceTime` makes the same request succeed.

**Why it's a defect (or at minimum, a documentation gap):**

`referenceTime` is part of the SWE Common 2.0 spec for the `Time`
component, indicating the epoch for the time scale. Its rejection by a
server claiming SWE Common conformance suggests either:

- The server's SWE Common Time decoder is incomplete, or
- The server's accepted SWE Common subset is narrower than advertised and
  is undocumented.

Either way, clients have no way to know without probing.

**Reproducer:**

POST a datastream with the field above; remove `referenceTime`; POST again.
The first 400s, the second 201s.

**Current workaround:**

Drop `referenceTime` from every Time field in every datastream schema.
The implicit epoch is now whatever the server defaults to (presumably Unix
epoch given `uom: s`, but unspecified).

**Expiry condition:**

Server accepts SWE Common `referenceTime` on Time fields, OR upstream
documents the supported SWE Common subset.

---

### 4.5 Issue #5 (lower severity) — Datastream rejects top-level `uid`

**Severity:** P3 — minor; UID reuse pattern denied, but server assigns its
own.

**Observed behavior:**

`POST /datastreams` with `{"uid": "urn:..."}` at the top level returns 400.
Removing the field succeeds; the server assigns its own ID.

**Why it's a defect (or design choice):**

The OGC API – Connected Systems standard does allow client-supplied UIDs
on creation in some bindings, to enable idempotent provisioning. The
server's behavior is a valid implementation choice but should be
documented.

**Current workaround:** drop `uid` from datastream schemas.

**Expiry condition:** documented or accepted.

---

### 4.6 Issue #6 (informational) — `/deployments` rejects `parent@link` in properties

**Severity:** Informational. Not a bug — just confirming the expected
encoding.

**Observed behavior:** `parent@link` in deployment GeoJSON properties is
rejected. Parent linkage must be conveyed via the request URL path or a
separate mechanism (we use `parent_id=` parameter in the helper, which
issues a separate request).

**Why it's not a defect:** Closed-properties is correct per OGC 23-001.
We mention it here so readers don't waste time probing.

---

## 5. Summary Table of Upstream Issues

| # | Endpoint | Field | Status | Severity | Defect type | Workaround |
|---|---|---|---|---|---|---|
| 1 | PUT /procedures | `documents` | Rejected; `documentation` works | P1 | Asymmetric/incomplete typo fix (post-`c2ab201`) | Use typo `documentation` in procedure SML only |
| 2 | PUT /systems | `characteristics`, `capabilities` | Rejected | P1 | Missing JSON binding for spec-defined fields | Drop fields; metadata loss |
| 3 | PUT /systems | `typeOf` | HTTP 500 | P2 | Server panic + linkage gap | Drop linkage from SML |
| 4 | POST /datastreams | SWE Time `referenceTime` | Rejected | P2 | Incomplete SWE Common decoder | Drop field; implicit epoch |
| 5 | POST /datastreams | top-level `uid` | Rejected | P3 | Possibly intentional; undocumented | Let server assign ID |
| 6 | POST /deployments | `parent@link` in properties | Rejected | Informational | Not a defect | Use `parent_id=` helper param |

---

## 6. Recommendations

In priority order:

### 6.1 (After ~3 publishers) Extract a shared SML/stub builder

Create `publishers/sml_builders.py` exposing:

```python
def system_stub(uid: str, name: str, description: str, *,
                geometry: dict, feature_type: str = "sosa:Sensor") -> dict: ...

def procedure_stub(uid: str, name: str, description: str, *,
                   valid_time_start: str = VALID_TIME_START) -> dict: ...

def deployment_stub(uid: str, name: str, description: str, *,
                    geometry: dict, valid_time_start: str = VALID_TIME_START,
                    platform_link: dict | None = None) -> dict: ...

def procedure_sml(uid: str, label: str, description: str, *,
                  keywords: list[str], documentation: list[dict],
                  contacts: list[dict], identifiers: list[dict] | None = None,
                  use_documentation_typo: bool = True) -> dict: ...
```

The `use_documentation_typo` flag lives in **exactly one place**. When
upstream Issue #1 is fixed, flip the default to `False` and the entire
fleet picks up the change.

### 6.2 Add contract tests per publisher

Each publisher gets one fast offline test that:

1. Calls `_system_stub(...)`, `_system_sml(...)`, etc.
2. Asserts stub `properties.keys()` is a subset of `{featureType, uid, name, description, validTime, platform@link}`.
3. Asserts SML body contains required spec fields and no fields known to
   crash the server (Issue #3).
4. Round-trips against a recorded fixture if possible.

This catches regressions before live-run.

### 6.3 File the upstream issues

For each of Issues #1–#5, file an issue against the `csapi-go-v2`
repository with the reproducer in §4. Issue #1 is a one-line patch; Issue
#3 is a server stability fix; Issues #2/#4 are JSON-binding gaps.

This gives every workaround in our code an **expiry condition** rather
than open-ended technical debt.

### 6.4 Track metadata loss explicitly

Add a section to the project README (or a `STRICT_PARSING_LIMITATIONS.md`)
listing the fields currently dropped on the wire when targeting
`csapi-go-v2`:

- `characteristics` (per-system physical properties).
- `capabilities` (publisher operational parameters).
- `typeOf` linkage in SML.
- `lineage`, `usageConstraints` (currently in source comments only).
- `referenceTime` on SWE Time fields.

So consumers know what they will not get.

### 6.5 Decide on legacy OSH long-term posture

The strict parsing migration prepares us for the OGC reference server.
Choose explicitly:

- **(a) Dual support indefinitely** — keep both paths working.
- **(b) Strict-only on a date** — set a sunset date for OSH-only fields
  (none currently; both code paths produce identical output today).
- **(c) Strict-first, OSH best-effort** — current implicit posture.

Option (c) is fine if documented. Right now it's implicit.

---

## 7. Net Position

**Improvements (durable):**

1. Two publishers (aviation-wx, NDBC) are portable across both server
   families.
2. Stub/SML separation matches OGC 23-001.
3. Empirical schema is captured in three companion documents.
4. Helper infrastructure (`bootstrap_helpers.ensure_*`) is validated.
5. Four upstream defects identified with reproducers.

**Costs (mitigatable but real):**

1. Metadata fidelity regressed against `csapi-go-v2` until upstream
   accepts `characteristics`/`capabilities`/etc.
2. No automated test coverage; validation is manual.
3. Mechanical pattern is being copy-pasted; needs extraction after a few
   more publishers.
4. Workarounds carry inline `NOTE:` comments that will need cleanup once
   upstream fixes land.

**Verdict:** The work is improving the repository in standards-conformance
and portability. It is *not* free; it is buying alignment with the OGC
reference server at the cost of metadata fidelity until upstream catches
up. The trade is correct. The cost should be tracked, not hidden.

---

## 8. Appendix — Probe Environment

- **Server:** `https://129-80-248-53.sslip.io/csapi-go-v2/`
- **Auth:** none (public probe instance).
- **TLS:** self-signed; probes use `ssl.CERT_NONE`. Production code uses
  the helper's TLS context.
- **Date of probes:** 2026-05-09.
- **Reference commits in upstream Go server:** `a467aba0` (strict parsing),
  `c2ab201` (partial typo rename — limited to `SystemSensorMLFeature`).
- **Reference branch in this repo:** `fix/aviation-wx-strict-parsing-2026-05-09`.

