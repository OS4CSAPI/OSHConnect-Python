# OSH SensorHub: Datastream Creation Format Requirements

**Date:** 2026-02-27  
**Server:** OSH SensorHub v2.x at `http://45.55.99.236:8080/sensorhub/api`  
**Standard:** [OGC API — Connected Systems — Part 2: Dynamic Data 1.0](https://docs.ogc.org/DRAFTS/23-002.html) (OGC 23-002)  
**Related Reports:**  
- [OSH DeployedSystems Conformance Gap](./OSH_DeployedSystems_Conformance_Gap.md)  
- [OSH Deployment Hierarchy and System Association](./OSH_Deployment_Hierarchy_and_System_Association.md)  
- [Phase 1 Bootstrap Results](./Phase1_Bootstrap_Results.md)  
- [Scenario Pack v2.3 Review](./ScenarioPack_v2.3_Review.md)

---

## 1. Executive Summary

Creating datastreams on OSH SensorHub via `POST /systems/{sysId}/datastreams` requires adherence to **three undocumented format rules** that diverge from what the CSAPI Part 2 standard implies and what the Scenario Pack v2.5 templates provide. Violating any of these rules produces either a **silent 302 redirect** (masking the real error) or a **cryptic 400 error**, with no actionable guidance from the server.

This report documents each requirement with HTTP-level evidence, explains the error-masking redirect behavior, and provides corrected payload examples. These findings were discovered during the Scenario Pack v2.5 upgrade on 2026-02-27.

### The Three Requirements

| # | Requirement | What the Standard/Templates Use | What OSH Requires | Error If Wrong |
|---|---|---|---|---|
| S-9 | `obsFormat` value | `"application/json"` | `"application/swe+json"` | **302 → login page** (silent) |
| S-16 | Schema wrapper key | `"resultSchema"` | `"recordSchema"` | **302 → login page** (silent) |
| S-15 | JSON property ordering | `"name"` first in field objects | `"type"` **must** be first | **400** with parse error |

---

## 2. Problem Discovery Timeline

During the Scenario Pack v2.5 bootstrap, all datastream creation requests failed while deployments, systems, and procedures succeeded. The investigation path:

1. **Initial symptom**: Python `urllib.request` reported `"Unsupported format: application/json"` — but this was actually HTML from the OSH login page after a 302 redirect was silently followed.

2. **Content-Type hunt** (false trail): Tested `application/json`, `application/swe+json`, `application/geo+json`, `application/om+json` as Content-Type headers. All failed identically. The outer Content-Type header was never the issue — it must be `application/json`.

3. **302 redirect discovery**: Using `curl -v` revealed the server was returning `302 Found → /sensorhub` (the Vaadin login page), not a proper 400 error. Python's `urllib.request.urlopen()` silently followed the redirect, issued a GET to the login page, then reported the HTML parsing error.

4. **Root cause isolation**: Comparing against the original `ingest-part2.py` script (which successfully created datastreams in an earlier session) revealed the three format differences documented here.

5. **S-15 ordering fix**: After fixing S-9 and S-16, requests still failed with HTTP 400: `"Required 'type' property as first member of JSON object"`. The SWE schema JSON objects had `"name"` before `"type"` due to Python dict ordering from the scenario pack templates.

---

## 3. Requirement S-9: `obsFormat` Must Be `application/swe+json`

### 3.1 What the Standard Says

CSAPI Part 2 §14 and the SWE Common Data Model (OGC 08-094r2) define observation encoding formats. The `obsFormat` field in the datastream schema specifies how observations will be encoded. The standard supports multiple formats including `application/json`, `application/swe+json`, `application/swe+csv`, and `application/swe+binary`.

The Scenario Pack v2.5 templates use `application/json` in the `obsFormat` field:

```json
{
  "name": "StringProc Track State",
  "type": "observation",
  "live": true,
  "schema": {
    "obsFormat": "application/json",
    "resultSchema": { ... }
  }
}
```

### 3.2 What OSH Requires

OSH SensorHub **only accepts** `"application/swe+json"` as the `obsFormat` value during datastream creation. Using `"application/json"` (or any other MIME type) causes a **302 redirect** to the Vaadin login page.

### 3.3 HTTP Evidence

**Failing request** (`obsFormat: "application/json"`):

```http
POST /sensorhub/api/systems/05f0/datastreams HTTP/1.1
Host: 45.55.99.236:8080
Authorization: Basic b2djOm9nYw==
Content-Type: application/json

{"name":"Test","outputName":"test","schema":{"obsFormat":"application/json",
 "recordSchema":{"type":"DataRecord","label":"test",
 "fields":[{"type":"Text","name":"v","label":"V",
 "definition":"http://example.org/v"}]}}}

HTTP/1.1 302 Found
Location: http://45.55.99.236:8080/sensorhub
Content-Length: 0
```

**Successful request** (`obsFormat: "application/swe+json"`):

```http
POST /sensorhub/api/systems/05f0/datastreams HTTP/1.1
Host: 45.55.99.236:8080
Authorization: Basic b2djOm9nYw==
Content-Type: application/json

{"name":"Test","outputName":"test","schema":{"obsFormat":"application/swe+json",
 "recordSchema":{"type":"DataRecord","label":"test",
 "fields":[{"type":"Text","name":"v","label":"V",
 "definition":"http://example.org/v"}]}}}

HTTP/1.1 201 Created
Location: /datastreams/07q02
Content-Length: 0
```

### 3.4 Paradox: Read-Back Shows `application/om+json`

After successful creation with `obsFormat: "application/swe+json"`, reading the datastream schema back via `GET /datastreams/{id}/schema` returns:

```json
{
  "obsFormat": "application/om+json",
  "resultSchema": { ... }
}
```

The server internally remaps `application/swe+json` → `application/om+json`. The read-back format (`application/om+json`) cannot be used for creation — it is rejected with the same 302.

### 3.5 Impact on Observations

Despite this creation-time format requirement, **observations are POSTed using `Content-Type: application/json`** with a standard O&M JSON body (`phenomenonTime`, `resultTime`, `result`). The `obsFormat` field affects only datastream creation validation, not observation ingestion.

---

## 4. Requirement S-16: Schema Wrapper Key Is `recordSchema`

### 4.1 What the Standard/Templates Say

The Scenario Pack v2.5 datastream creation templates use `"resultSchema"` as the schema wrapper key:

```json
{
  "schema": {
    "obsFormat": "application/json",
    "resultSchema": { "$ref": "schemas/datastreams/track_state_OSH_v2.5.json" }
  }
}
```

The CSAPI Part 2 standard references both `resultSchema` and `recordSchema` in different contexts.

### 4.2 What OSH Requires

OSH SensorHub requires `"recordSchema"` as the wrapper key. Using `"resultSchema"` causes the same **302 redirect** to the login page.

**Failing:**
```json
{ "schema": { "obsFormat": "application/swe+json", "resultSchema": { ... } } }
```
→ HTTP 302

**Successful:**
```json
{ "schema": { "obsFormat": "application/swe+json", "recordSchema": { ... } } }
```
→ HTTP 201

### 4.3 Read-Back Uses `resultSchema`

Paradoxically, when reading the schema back via `GET /datastreams/{id}/schema`, the server returns the key as `"resultSchema"`:

```json
{
  "obsFormat": "application/om+json",
  "resultSchema": {
    "type": "DataRecord",
    "name": "track_state",
    "definition": "https://os4csapi.org/def/csapi/trackStateRecordOSH",
    "label": "Track State (string-level)",
    "fields": [ ... ]
  }
}
```

The write and read use **different key names** for the same data:

| Direction | Key Used |
|---|---|
| POST (create) | `recordSchema` |
| GET (read) | `resultSchema` |

This asymmetry means a naïve "read schema, modify, write back" workflow will fail, because the key returned by the server is not accepted by the same server for creation.

---

## 5. Requirement S-15: `type` Must Be First JSON Property

### 5.1 What the Standard Says

JSON objects are defined as unordered collections of key-value pairs by RFC 8259. JSON Schema and SWE Common do not mandate property ordering. The CSAPI standard does not require any specific JSON key ordering.

### 5.2 What OSH Requires

OSH SensorHub's SWE Common JSON parser requires `"type"` to be the **first property** in every SWE Common object (DataRecord, Quantity, Text, Time, Count, Category, etc.). If any other property appears first, the server returns HTTP 400 with an error pinpointing the offending position.

### 5.3 HTTP Evidence

**Failing request** (`"name"` before `"type"` in field objects):

```http
POST /sensorhub/api/systems/05f0/datastreams HTTP/1.1
Content-Type: application/json

{"name":"Test","outputName":"test","schema":{
  "obsFormat":"application/swe+json",
  "recordSchema":{"type":"DataRecord","label":"test",
    "fields":[{"name":"v","type":"Text","label":"V",
               "definition":"http://example.org/v"}]}}}

HTTP/1.1 400 Bad Request

{
  "status": 400,
  "message": "Invalid JSON: Required 'type' property as first member
              of JSON object @ $.schema.recordSchema.fields[0].name"
}
```

**Successful request** (`"type"` first in all objects):

```json
{
  "fields": [
    {
      "type": "Text",
      "name": "v",
      "label": "V",
      "definition": "http://example.org/v"
    }
  ]
}
```

→ HTTP 201

### 5.4 Scope: All SWE Common Objects

This requirement applies **recursively** to every SWE Common typed object in the schema hierarchy:

- The top-level `DataRecord` must have `"type": "DataRecord"` as its first key
- Every field in the `fields` array must have `"type"` first (e.g., `"type": "Quantity"`, `"type": "Text"`)
- Nested `DataRecord` objects within fields must also have `"type"` first
- Constraint objects with `"type": "AllowedValues"` or `"type": "AllowedTokens"` must have `"type"` first
- The UoM `"code"` or `"label"` keys do NOT need ordering (they are not SWE Common typed objects)

### 5.5 Client-Side Workaround

Languages that preserve insertion order in dictionaries (Python 3.7+, modern JavaScript) can solve this by constructing objects with `"type"` first. For objects received from JSON files or third-party schemas where `"type"` is not first, a recursive reordering function is needed:

```python
def reorder_type_first(obj):
    """Recursively ensure 'type' is the first key in all dicts."""
    if isinstance(obj, dict):
        result = {}
        if "type" in obj:
            result["type"] = reorder_type_first(obj["type"])
        for k, v in obj.items():
            if k != "type":
                result[k] = reorder_type_first(v)
        return result
    elif isinstance(obj, list):
        return [reorder_type_first(item) for item in obj]
    return obj
```

---

## 6. The 302 Redirect Error-Masking Problem

### 6.1 Behavior

When the server rejects a datastream creation payload (due to wrong `obsFormat`, wrong schema key, or invalid structure), it returns **HTTP 302 Found** with `Location: http://{host}/sensorhub` instead of a proper 400 error with a JSON error body.

```http
HTTP/1.1 302 Found
Cache-Control: must-revalidate,no-cache,no-store
Location: http://45.55.99.236:8080/sensorhub
Content-Length: 0
```

### 6.2 Why This Is Catastrophic for Debugging

1. **HTTP client libraries follow redirects by default.** Python's `urllib.request.urlopen()`, JavaScript's `fetch()`, and most HTTP libraries automatically follow 302 redirects. The client never sees the 302 — it sees the response from the redirect target.

2. **The redirect target is the Vaadin web UI.** The `/sensorhub` path serves an HTML login page. When the client follows the redirect and sends a GET with `Content-Type: application/json`, the Vaadin servlet tries to parse the request, fails, and returns an HTML error page containing `"Unsupported format"` text.

3. **The error message is misleading.** The `"Unsupported format"` text in the HTML response refers to the Vaadin servlet's content negotiation, not the original datastream creation failure. This led to an extensive (and ultimately fruitless) investigation of Content-Type headers when the real issue was the request body format.

4. **No diagnostic information is available.** The 302 response has zero content length — no JSON error body, no `message`, no pointer to which field was wrong. The only way to diagnose the issue is to use `curl -v` or set `allow_redirects=False` / `MaximumRedirection 0` and observe the 302.

### 6.3 Recommendation

The server should return HTTP 400 with a JSON error body for all payload validation failures, analogous to the S-15 type-ordering error which correctly returns:

```json
{
  "status": 400,
  "message": "Invalid JSON: Required 'type' property as first member of JSON object @ $.schema.recordSchema.fields[0].name"
}
```

This pattern is correctly implemented for S-15 violations but not for S-9 or S-16 violations.

### 6.4 Client-Side Mitigation

All HTTP POST/PUT requests to OSH should disable automatic redirect following:

**Python:**
```python
class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Don't follow

opener = urllib.request.build_opener(NoRedirectHandler)
response = opener.open(request)
```

Or with `requests`:
```python
r = requests.post(url, json=payload, auth=("ogc","ogc"),
                  allow_redirects=False, timeout=30)
```

**JavaScript/TypeScript:**
```javascript
const response = await fetch(url, {
  method: 'POST',
  redirect: 'manual',  // Don't follow 302s
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

---

## 7. Correct Datastream Creation Payload

### 7.1 Minimal Working Example

```json
{
  "name": "StringProc Track State",
  "outputName": "track_state",
  "schema": {
    "obsFormat": "application/swe+json",
    "recordSchema": {
      "type": "DataRecord",
      "definition": "https://os4csapi.org/def/csapi/trackStateRecordOSH",
      "label": "Track State (string-level)",
      "fields": [
        {
          "type": "Time",
          "name": "timestamp",
          "definition": "https://os4csapi.org/def/odas/time/epochSeconds",
          "label": "Epoch seconds",
          "uom": { "code": "s" },
          "referenceTime": "1970-01-01T00:00:00Z"
        },
        {
          "type": "Quantity",
          "name": "lat",
          "definition": "https://os4csapi.org/def/csapi/lat",
          "label": "Latitude",
          "uom": { "code": "deg" }
        },
        {
          "type": "Text",
          "name": "method",
          "definition": "https://os4csapi.org/def/csapi/method",
          "label": "Method"
        }
      ]
    }
  }
}
```

### 7.2 Required vs Optional Fields in the Payload

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Display name for the datastream |
| `outputName` | Recommended | Used as the `name` attribute in the recordSchema read-back; aids observation routing |
| `schema.obsFormat` | **Yes** | Must be `"application/swe+json"` |
| `schema.recordSchema` | **Yes** | Must use `recordSchema` (not `resultSchema`) |
| `schema.recordSchema.type` | **Yes** | Must be `"DataRecord"` and must be **first** key |
| `schema.recordSchema.fields[].type` | **Yes** | Must be the **first** key in each field object |
| `schema.recordSchema.fields[].name` | Yes | Unique field identifier |
| `schema.recordSchema.fields[].definition` | Yes | URI definition for the observed property |
| `description` | No | Accepted but not required |
| `type` (top-level) | No | `"observation"` — accepted but not required by OSH |
| `live` | No | `true/false` — accepted but not required |

### 7.3 Observation POST (After Datastream Exists)

Once a datastream is created, observations are POSTed to its observations endpoint using standard O&M JSON:

```http
POST /sensorhub/api/datastreams/{dsId}/observations HTTP/1.1
Content-Type: application/json

{
  "resultTime": "2026-02-27T20:10:01Z",
  "phenomenonTime": "2026-02-27T20:10:01Z",
  "result": {
    "timestamp": 1772223001,
    "lat": 31.6582,
    "method": "triangulate+cv-filter"
  }
}
```

→ HTTP 201 Created

---

## 8. SWE Common Field Type Reference (OSH-Compatible)

Each field type has specific required properties. All must have `"type"` as the first JSON key.

### 8.1 Quantity (numeric with unit)

```json
{
  "type": "Quantity",
  "name": "speedMS",
  "definition": "https://os4csapi.org/def/csapi/speedMS",
  "label": "Speed",
  "uom": { "code": "m/s" },
  "constraint": { "type": "AllowedValues", "intervals": [[0, 100]] }
}
```

### 8.2 Text (string)

```json
{
  "type": "Text",
  "name": "method",
  "definition": "https://os4csapi.org/def/csapi/method",
  "label": "Method"
}
```

### 8.3 Time (temporal)

```json
{
  "type": "Time",
  "name": "timestamp",
  "definition": "https://os4csapi.org/def/odas/time/epochSeconds",
  "label": "Epoch seconds",
  "uom": { "code": "s", "label": "seconds" },
  "referenceTime": "1970-01-01T00:00:00Z"
}
```

### 8.4 Count (integer)

```json
{
  "type": "Count",
  "name": "nSensors",
  "definition": "https://os4csapi.org/def/csapi/nSensors",
  "label": "Contributing sensors"
}
```

### 8.5 Category (enumerated string)

```json
{
  "type": "Category",
  "name": "tgtTyp",
  "definition": "https://os4csapi.org/def/csapi/tgtTyp",
  "label": "Target type",
  "constraint": { "type": "AllowedTokens", "values": ["VEHICL","UAS","PERS","UNKN"] }
}
```

### 8.6 Nested DataRecord

```json
{
  "type": "DataRecord",
  "name": "source0",
  "label": "Potential Source #0",
  "fields": [
    { "type": "Quantity", "name": "x", "label": "DOA X", "definition": "...", "uom": {"code": "1"} },
    { "type": "Quantity", "name": "energy", "label": "Energy", "definition": "...", "uom": {"code": "1"} }
  ]
}
```

---

## 9. Comparison: Scenario Pack Templates vs OSH Requirements

### 9.1 Scenario Pack v2.5 Template (Failing)

```json
{
  "name": "StringProc Track State",
  "description": "Derived track state from string processor.",
  "type": "observation",
  "live": true,
  "phenomenonTimeInterval": "PT1S",
  "resultTimeInterval": "PT1S",
  "deployment@link": { "href": "/sensorhub/api/deployments/AZ-DEP-STRING-ALPHA", "title": "AZ-DEP-STRING-ALPHA" },
  "procedure@link": { "href": "/sensorhub/api/procedures/AZ-PROC-TRIANG-CHAIN", "title": "AZ-PROC-TRIANG-CHAIN" },
  "featureOfInterest@link": { "href": "/sensorhub/api/deployments/AZ-DEP-AOI-001", "title": "AOI" },
  "schema": {
    "obsFormat": "application/json",
    "resultSchema": { "$ref": "schemas/datastreams/track_state_OSH_v2.5.json" }
  }
}
```

**Issues:**
1. ❌ `obsFormat: "application/json"` → must be `"application/swe+json"`
2. ❌ `resultSchema` → must be `recordSchema`
3. ❌ `$ref` → OSH does not resolve JSON Schema `$ref` — the schema must be inlined
4. ⚠️ `deployment@link`, `procedure@link`, `featureOfInterest@link` → silently stripped (accepted but not persisted, similar to `deployedSystems@link` in deployments)
5. ⚠️ The referenced schema files have `"name"` before `"type"` in field objects → will hit S-15

### 9.2 Corrected OSH-Compatible Version

```json
{
  "name": "StringProc Track State",
  "outputName": "track_state",
  "schema": {
    "obsFormat": "application/swe+json",
    "recordSchema": {
      "type": "DataRecord",
      "definition": "https://os4csapi.org/def/csapi/trackStateRecordOSH",
      "label": "Track State (string-level)",
      "fields": [
        { "type": "Time", "name": "timestamp", "definition": "...", "label": "Epoch seconds", "uom": {"code":"s"}, "referenceTime": "1970-01-01T00:00:00Z" },
        { "type": "Text", "name": "globalTrackId", "definition": "...", "label": "Global track ID" },
        { "type": "Quantity", "name": "lat", "definition": "...", "label": "Latitude", "uom": {"code":"deg"} },
        { "type": "Quantity", "name": "lon", "definition": "...", "label": "Longitude", "uom": {"code":"deg"} }
      ]
    }
  }
}
```

---

## 10. Verified Datastreams Created

Using the corrected format, all three v2.5 datastreams were successfully created:

| Datastream | ID | Parent System | System ID | Obs Count |
|---|---|---|---|---|
| StringProc Track State | `07q02` | STRPROC-ALPHA | `05f0` | 1 (sample) |
| StringProc Predicted Position | `07qg2` | STRPROC-ALPHA | `05f0` | 1 (sample) |
| Monitoring SENREP | `07r02` | MON-TEAM-A | `05eg` | 1 (sample) |

Each datastream was verified via `GET /datastreams/{id}` and `GET /datastreams/{id}/schema` to confirm schema persistence and observation queryability.

---

## 11. Summary of OSH Quirks for Datastream Creation

| ID | Quirk | Workaround | Error Pattern |
|---|---|---|---|
| **S-9** | `obsFormat` must be `"application/swe+json"` | Hardcode the value | 302 redirect (silent) |
| **S-15** | `"type"` must be first key in SWE objects | Recursive key reordering | 400 with parse error |
| **S-16** | Schema key must be `"recordSchema"` | Use `recordSchema` for writes | 302 redirect (silent) |
| **S-17** | 302 redirect on invalid payload (not 400) | Disable redirect following | Masks all errors |
| **S-18** | `@link` properties on datastreams silently stripped | None (metadata lost) | Silently accepted |
| **S-19** | `$ref` not resolved in schemas | Inline all schemas | Likely 302 or ignored |
| **S-20** | Read-back uses different keys than write (`resultSchema` vs `recordSchema`, `application/om+json` vs `application/swe+json`) | Map keys between read/write | Asymmetric API |

---

## 12. Recommendations

### 12.1 For OSH SensorHub Team

1. **Return 400 with JSON error body for all validation failures** — The 302 redirect on invalid payloads is the single most impactful usability issue. It makes debugging nearly impossible without `curl -v` or redirect-disabled clients.

2. **Accept `"application/json"` as `obsFormat`** — The standard allows it, and the server already accepts `application/json` observations. The creation-time restriction is inconsistent.

3. **Accept `"resultSchema"` as an alias for `"recordSchema"`** — The standard uses both terms. The read-back endpoint already returns `resultSchema`. Creating a write/read asymmetry is a conformance and usability issue.

4. **Accept any JSON key ordering** — JSON is order-independent per RFC 8259. Requiring `"type"` first is a parser implementation detail that should not leak to the API contract.

### 12.2 For Scenario Pack Authors

1. **Use `"application/swe+json"` as `obsFormat`** in all datastream creation templates
2. **Use `"recordSchema"` as the schema wrapper key** for OSH compatibility
3. **Inline all schemas** instead of using `$ref` — OSH does not resolve references
4. **Ensure `"type"` is the first key** in all SWE Common typed objects
5. **Add `"outputName"` field** — used by OSH as the internal schema `name` attribute

### 12.3 For Client Library Developers

1. **Disable redirect following** on all mutating requests (POST, PUT, DELETE) to OSH
2. **Implement `reorder_type_first()`** as a pre-processing step before serialization
3. **Map schema keys** between write (`recordSchema`) and read (`resultSchema`) contexts
4. **Do not assume read-back format matches write format** — the server transforms both the key name and the MIME type value

---

## Appendix A: Test Commands

```bash
# ── Test S-9: Wrong obsFormat (→ 302) ──
curl -s -o /dev/null -w "%{http_code}" \
  -u ogc:ogc -H "Content-Type: application/json" \
  -d '{"name":"Test","outputName":"t","schema":{"obsFormat":"application/json","recordSchema":{"type":"DataRecord","label":"t","fields":[{"type":"Text","name":"v","label":"V","definition":"urn:test"}]}}}' \
  "http://45.55.99.236:8080/sensorhub/api/systems/05f0/datastreams"
# → 302

# ── Test S-16: Wrong schema key (→ 302) ──
curl -s -o /dev/null -w "%{http_code}" \
  -u ogc:ogc -H "Content-Type: application/json" \
  -d '{"name":"Test","outputName":"t","schema":{"obsFormat":"application/swe+json","resultSchema":{"type":"DataRecord","label":"t","fields":[{"type":"Text","name":"v","label":"V","definition":"urn:test"}]}}}' \
  "http://45.55.99.236:8080/sensorhub/api/systems/05f0/datastreams"
# → 302

# ── Test S-15: Wrong key order (→ 400) ──
curl -s -u ogc:ogc -H "Content-Type: application/json" \
  -d '{"name":"Test","outputName":"t","schema":{"obsFormat":"application/swe+json","recordSchema":{"type":"DataRecord","label":"t","fields":[{"name":"v","type":"Text","label":"V","definition":"urn:test"}]}}}' \
  "http://45.55.99.236:8080/sensorhub/api/systems/05f0/datastreams"
# → {"status":400,"message":"Invalid JSON: Required 'type' property as first member of JSON object @ $.schema.recordSchema.fields[0].name"}

# ── Correct payload (→ 201) ──
curl -s -o /dev/null -w "%{http_code}" \
  -u ogc:ogc -H "Content-Type: application/json" \
  -d '{"name":"Test","outputName":"t","schema":{"obsFormat":"application/swe+json","recordSchema":{"type":"DataRecord","label":"t","fields":[{"type":"Text","name":"v","label":"V","definition":"urn:test"}]}}}' \
  "http://45.55.99.236:8080/sensorhub/api/systems/05f0/datastreams"
# → 201

# ── Verify read-back uses different keys ──
# (Replace {dsId} with the Location header value)
curl -s -u ogc:ogc "http://45.55.99.236:8080/sensorhub/api/datastreams/{dsId}/schema" | python -m json.tool
# → Shows "resultSchema" (not "recordSchema") and "application/om+json" (not "application/swe+json")
```

## Appendix B: Cross-Reference to Prior Research

| Topic | Report | Key Finding |
|---|---|---|
| `@link` property stripping | [DeployedSystems Conformance Gap](./OSH_DeployedSystems_Conformance_Gap.md) | Array-valued `@link` properties silently stripped |
| 302 redirect as error response | This report (§6) | Server returns 302 instead of 400 for payload validation failures |
| Deployment hierarchy creation | [Deployment Hierarchy](./OSH_Deployment_Hierarchy_and_System_Association.md) | `validTime` must be array format `["begin", ".."]` |
| Ghost resources after delete | [Ghost Resource Bug](./OSH_Ghost_Resource_Stale_Index_Bug.md) | Stale index entries survive DELETE |
| Phase 1 bootstrap discoveries | [Phase 1 Results](./Phase1_Bootstrap_Results.md) | Initial format requirements for systems/deployments |

## Appendix C: Deployment `validTime` Format (Related Discovery)

During the same v2.5 bootstrap session, we confirmed that deployment `validTime` must use the array format, not the object format:

**Failing (object format from templates):**
```json
"validTime": { "begin": "2026-02-27T00:00:00Z", "end": null }
```
→ HTTP 400

**Successful (array format):**
```json
"validTime": ["2026-02-27T00:00:00Z", ".."]
```
→ HTTP 201

The `".."` sentinel represents an open-ended interval (ongoing deployment).
