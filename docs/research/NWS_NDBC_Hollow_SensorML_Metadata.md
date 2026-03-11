# NWS / NDBC Hollow SensorML Metadata

## SML Field-Shape Mismatch → Server Returns Empty Shells

**Date:** 2026-06-10  
**Author:** AI Research Agent (GitHub Copilot / Claude Opus 4.6)  
**Status:** Confirmed — empirically validated on Oracle OSH instance  
**Severity:** Medium — feature degradation, no data loss  
**Affects:** All 10 NWS weather stations, all 5 NDBC buoy systems  
**Related reports:**
- [OSH_Deployment_Link_Persistence_Gap.md](OSH_Deployment_Link_Persistence_Gap.md) — same class of silent-drop behavior
- [OSH_DeployedSystems_Conformance_Probe.md](OSH_DeployedSystems_Conformance_Probe.md) — OSH field acceptance probes

---

## 1. Executive Summary

The NWS weather station and NDBC buoy system cards in the CSAPI Explorer display **hollow metadata** — characteristic groups with empty arrays, contacts with role only (no organization name), and zero documentation links — despite the bootstrap scripts writing SensorML bodies that include all of this data.

Root cause is **two compounding problems**:

1. **SML field-shape mismatch:** The `_system_sml()` functions in `bootstrap_nws.py` and `bootstrap_ndbc.py` use an ad-hoc JSON structure that does not match the SensorML JSON encoding expected by OSH SensorHub. The server accepts the PUT without error but **silently drops unrecognized field shapes**, returning hollow shells on subsequent GET.

2. **Skip-if-exists logic:** `ensure_system()` in `bootstrap_helpers.py` skips the SML PUT if the system UID already exists. Even if the SML body is later corrected, re-running the bootstrap will not apply the fix to existing systems.

ISS and ODAS AZ-MA-1 systems display rich metadata because their bootstraps use the correct SensML JSON field shapes.

---

## 2. Evidence

### 2.1 Server Responses Compared

Fetched via `GET /systems/{id}` with `Accept: application/sml+json`:

| Field | ISS (`04og`) | ODAS AZ-MA-1 (`0420`) | NWS KTUS (`0520`) | NDBC 44025 (`0570`) |
|-------|-------------|----------------------|-------------------|---------------------|
| keywords | 10 items | 8 items | **none** | **none** |
| identifiers | 4 (with `definition` URIs) | 2 (with `definition` URIs) | 2 (no `definition`) | 2 (no `definition`) |
| classifiers | 3 (with `definition` URIs) | 2 (with `definition` URIs) | 3 (no `definition`) | 3 (no `definition`) |
| characteristics | 4 items in 1 group | 5 items in 1 group | **3 empty group shells** | **5+ empty group shells** |
| capabilities | 4 items in 1 group | 4 items in 1 group | **absent** | **absent** |
| contacts | 3 full (org + address) | 1 full (org + address) | **2 role-only stubs** | **1 role-only stub** |
| documents | 5 (href + type) | 7 (href + type) | **absent entirely** | **absent entirely** |

### 2.2 Bootstrap SML Bodies Are Non-Empty

Both `bootstrap_nws.py::_system_sml()` (line 189) and `bootstrap_ndbc.py::_system_sml()` (line 215) write rich SML dicts with contacts, documentation, and characteristics populated. The data is present in the PUT body; the server drops it during deserialization.

---

## 3. Root Cause: Field Shape Mismatches

### 3.1 `contacts` — Wrong Key Names and Flat Structure

**ISS (correct SML JSON):**
```json
{
    "role": "http://sensorml.com/ont/swe/property/Operator",
    "organisationName": "NASA — National Aeronautics and Space Administration",
    "contactInfo": {
        "website": "https://www.nasa.gov/international-space-station/",
        "address": {
            "city": "Washington",
            "administrativeArea": "DC",
            "country": "United States"
        }
    }
}
```

**NWS / NDBC (broken):**
```json
{
    "role": "operator",
    "organizationName": "National Weather Service",
    "website": "https://api.weather.gov"
}
```

| Issue | Detail |
|-------|--------|
| `organisationName` vs `organizationName` | SML JSON uses British spelling (`organisat**i**on`); American spelling is silently ignored |
| `contactInfo` wrapper missing | `website` and `email` must be nested under `contactInfo`; flat top-level keys are unrecognized |
| `role` value | Should be a full SensorML ontology URI, not a bare word |

### 3.2 `documents` — Wrong Top-Level Key and Link Structure

**ISS (correct):**
```json
"documents": [
    {
        "role": "http://dbpedia.org/resource/Web_page",
        "name": "NASA ISS Overview",
        "description": "Official NASA overview...",
        "link": {
            "href": "https://www.nasa.gov/...",
            "type": "text/html"
        }
    }
]
```

**NWS / NDBC (broken):**
```json
"documentation": [
    {"name": "NWS Station Resource", "url": "https://api.weather.gov/stations/KTUS"}
]
```

| Issue | Detail |
|-------|--------|
| Key name | SML JSON uses `"documents"`, not `"documentation"` |
| Link shape | Must use `"link": {"href": "...", "type": "..."}` not flat `"url"` |
| Missing `role` | Each document should have a `role` URI |
| Missing `description` | Optional but contributes to display richness |

### 3.3 `characteristics` — Flat Items Instead of Grouped SWE Components

**ISS (correct):**
```json
"characteristics": [
    {
        "label": "Orbital Parameters",
        "characteristics": [
            {
                "type": "Quantity",
                "name": "orbital_period",
                "definition": "http://qudt.org/vocab/quantitykind/Period",
                "label": "Orbital Period",
                "uom": {"code": "min"},
                "value": 92.7
            }
        ]
    }
]
```

**NWS (broken):**
```json
"characteristics": [
    {"label": "Reporting Cadence", "value": "Hourly routine observations..."}
]
```

| Issue | Detail |
|-------|--------|
| Missing group wrapper | Outer array must contain **group objects** with a `label` and nested `characteristics` array |
| Missing SWE typing | Inner items must have `type` (Quantity, Text, etc.), `name`, `definition` |
| Missing `uom` | Quantity values need `"uom": {"code": "..."}` |

### 3.4 `identifiers` / `classifiers` — Missing `definition` URIs

**ISS (correct):**
```json
{"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": "ISS Position Publisher"}
```

**NWS / NDBC (broken):**
```json
{"label": "OS4CSAPI UID", "value": "urn:os4csapi:system:nws:ktus:v1"}
```

OSH SensorHub may silently drop identifiers/classifiers when the `definition` URI is absent.

---

## 4. Secondary Issue: `ensure_system()` Skip-If-Exists

In `publishers/bootstrap_helpers.py`, `ensure_system()` checks `find_by_uid()` and returns early if the system already exists:

```python
existing = find_by_uid(base_url, auth, "systems", uid)
if existing:
    print(f"  [SKIP] System {uid} already exists (id={existing})")
    return existing
```

This means:
- Systems created **before** the SML enrichment was added never received the SML PUT.
- Even after fixing the field shapes, re-running the bootstrap **will not apply the corrected SML** unless the skip logic is bypassed.

**Fix:** Add a `--force-sml` flag that forces the SML PUT even for existing systems.

---

## 5. Affected Systems

### NWS Weather Stations (10)
| Station | UID |
|---------|-----|
| KTUS | `urn:os4csapi:system:nws:ktus:v1` |
| KDMA | `urn:os4csapi:system:nws:kdma:v1` |
| KFHU | `urn:os4csapi:system:nws:kfhu:v1` |
| KLUF | `urn:os4csapi:system:nws:kluf:v1` |
| KPHX | `urn:os4csapi:system:nws:kphx:v1` |
| KDCA | `urn:os4csapi:system:nws:kdca:v1` |
| KIAD | `urn:os4csapi:system:nws:kiad:v1` |
| KNYG | `urn:os4csapi:system:nws:knyg:v1` |
| KDAY | `urn:os4csapi:system:nws:kday:v1` |
| KFFO | `urn:os4csapi:system:nws:kffo:v1` |

### NDBC Buoys (5)
| Station | UID |
|---------|-----|
| 44025 | `urn:os4csapi:system:ndbc:44025:v1` |
| 41009 | `urn:os4csapi:system:ndbc:41009:v1` |
| 42036 | `urn:os4csapi:system:ndbc:42036:v1` |
| 46025 | `urn:os4csapi:system:ndbc:46025:v1` |
| 46013 | `urn:os4csapi:system:ndbc:46013:v1` |

---

## 6. Fix Plan

1. **Fix `_system_sml()` in `bootstrap_nws.py`:** Rewrite contacts, documents, and characteristics to match the ISS SensorML JSON schema. Add `definition` URIs to identifiers and classifiers. Add keywords.

2. **Fix `_system_sml()` in `bootstrap_ndbc.py`:** Same structural corrections.

3. **Add `--force-sml` to `ensure_system()`:** Allow the SML PUT to run even when the system already exists.

4. **Re-PUT SML** to all 15 systems on the Oracle instance.

5. **Verify** by fetching `application/sml+json` and confirming nested fields are populated.

---

## 7. Impact on CSAPI Explorer

The `useDeployedSystemCard.ts` composable in `csapi-explorer` correctly reads all SML fields (`documents`, `contacts`, `characteristics`, `capabilities`). Once the server returns properly-structured SML, the NWS and NDBC system cards will display:

- **Thumbnail image** from documents with `image/*` type
- **Documentation links** from documents
- **Owner / operator** from contacts with `organisationName`
- **Characteristics table** from nested SWE components
- **Capabilities table** from capabilities groups
