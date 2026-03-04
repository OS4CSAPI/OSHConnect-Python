# OSH `samplingFeature@link` Persistence Gap on Observations

## Summary

OSH accepts `samplingFeature@link` on Observation POST requests (HTTP 201) but **silently discards the field** — it is not returned on subsequent GET. This prevents CSAPI-native linkage between Observations and their Feature of Interest (FOI), which is the mechanism CSAPI Part 2 provides for answering "what is this observation about?"

| Operation | Result |
|-----------|--------|
| `POST /samplingFeatures` (create FOI) | **201 Created** — persists and round-trips correctly |
| `POST /datastreams/{id}/observations` with `samplingFeature@link` | **201 Created** — accepted without error |
| `GET /observations/{id}` (read back) | **`samplingFeature@link` absent** — silently dropped |

This is the same "silent acceptance + silent discard" pattern documented in [Issue #1](https://github.com/OS4CSAPI/osh-core/issues/1) for `deployedSystems@link` and `deployment@link`.

---

## Environment

- **Server:** OSH (OpenSensorHub) CSAPI instance on Oracle Cloud
- **API root:** `https://os4csapi-osh.duckdns.org/sensorhub/api`
- **Date tested:** 2026-03-03
- **Encoding tested:** `application/om+json`
- **Client tooling:** PowerShell `Invoke-WebRequest` (raw HTTP)

---

## Context: Why This Matters

The LOB Localizer system fuses Lines of Bearing from three acoustic sensor nodes to produce
location-estimate Observations (rendered as gold ⊕ dots on the map). These observations
currently have no `featureOfInterest` link — they are semantically "free-floating fixes"
with no durable subject identity.

Per SOSA/SSN, every `sosa:Observation` should reference a `sosa:FeatureOfInterest` that
identifies what the observation is about. CSAPI Part 2 provides `samplingFeature@link` as
the mechanism for this association.

The intended model:
- **SamplingFeature** `UAS-Track-001` = the tracked UAS target identity
- **Observations** (gold dots) = individual computed fixes, each linked to the track via `samplingFeature@link`

---

## Reproduction

### Step 1: Create SamplingFeature (works correctly)

```http
POST /sensorhub/api/samplingFeatures HTTP/1.1
Content-Type: application/json
Authorization: Basic ****

{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:foi:uas-track-001",
    "name": "UAS-Track-001",
    "description": "Tracked UAS target identity for the AZ String Alpha sensor network.",
    "featureType": "http://www.opengis.net/def/samplingFeatureType/OGC-OM/2.0/SF_SamplingPoint"
  }
}
```

**Response:**
```
HTTP 201 Created
Location: /samplingFeatures/040g
```

**Read-back (correct):**
```http
GET /sensorhub/api/samplingFeatures/040g HTTP/1.1
Accept: application/json
```
```json
{
  "type": "Feature",
  "id": "040g",
  "geometry": null,
  "properties": {
    "uid": "urn:os4csapi:foi:uas-track-001",
    "featureType": "http://www.opengis.net/def/samplingFeatureType/OGC-OM/2.0/SF_SamplingPoint",
    "name": "UAS-Track-001",
    "description": "Tracked UAS target identity for the AZ String Alpha sensor network."
  }
}
```

✅ SamplingFeature persists and round-trips correctly.

### Step 2: POST Observation with `samplingFeature@link`

```http
POST /sensorhub/api/datastreams/04f0/observations HTTP/1.1
Content-Type: application/om+json
Authorization: Basic ****

{
  "phenomenonTime": "2026-03-04T03:13:18.886Z",
  "resultTime": "2026-03-04T03:13:18.886Z",
  "samplingFeature@link": {
    "href": "/samplingFeatures/040g",
    "uid": "urn:os4csapi:foi:uas-track-001",
    "title": "UAS-Track-001"
  },
  "result": {
    "timestamp": 1772593998.953,
    "trackId": 1,
    "estimatedLat": 31.658,
    "estimatedLon": -110.270,
    "cep50_m": 50.0,
    "classification": "UAS",
    "numContributingLobs": 3,
    "contributingSensors": "AZ-MA-1,AZ-MA-2,AZ-MA-3",
    "residual_m": 30.0
  }
}
```

**Response:**
```
HTTP 201 Created
Location: /observations/041sthkupk339jq9g0
```

✅ Accepted without error.

### Step 3: Read back the Observation (field dropped)

```http
GET /sensorhub/api/observations/041sthkupk339jq9g0 HTTP/1.1
Accept: application/om+json
```

```json
{
  "id": "041sthkupk339jq9g0",
  "datastream@id": "04f0",
  "phenomenonTime": "2026-03-04T03:13:18.886Z",
  "resultTime": "2026-03-04T03:13:18.886Z",
  "result": {
    "timestamp": 1772593998.953,
    "trackId": 1,
    "estimatedLat": 31.658,
    "estimatedLon": -110.27,
    "cep50_m": 50.0,
    "classification": "UAS",
    "numContributingLobs": 3,
    "contributingSensors": "AZ-MA-1,AZ-MA-2,AZ-MA-3",
    "residual_m": 30.0
  }
}
```

❌ **`samplingFeature@link` is completely absent from the response.** The field was silently discarded.

---

## Observed Pattern (Cumulative)

This is the third instance of the silent-accept/silent-discard pattern:

| `@link` Field | Resource Type | Spec Reference | Persists? |
|---------------|--------------|----------------|-----------|
| `deployedSystems@link` | Deployment | OGC 23-001 §8.5 | ❌ Dropped ([Issue #1](https://github.com/OS4CSAPI/osh-core/issues/1)) |
| `deployment@link` | DataStream | OGC 23-002 §7.3.2 | ❌ Dropped ([Issue #1](https://github.com/OS4CSAPI/osh-core/issues/1)) |
| **`samplingFeature@link`** | **Observation** | **OGC 23-002 §8.3.5** | **❌ Dropped (this issue)** |
| `platform@link` | Deployment | OGC 23-001 §8.5 | ✅ Works |
| `system@link` | DataStream | OGC 23-002 §7.3.2 | ✅ Works (read-only) |

The pattern remains consistent: OSH persists `@link` fields that follow its internal
parent→child hierarchy but silently discards cross-cutting associations.

---

## Impact

Without `samplingFeature@link` persistence, CSAPI clients cannot:
- Query observations by FOI (`GET /observations?samplingFeature={id}`)
- Group observations by the thing they are about
- Build track-grouped displays from the API alone

### Current Workaround

The localizer embeds `trackId` and `classification` in the observation result blob.
Clients group observations client-side by matching these fields against a known
SamplingFeature registry. This works but bypasses the CSAPI association model entirely.

---

## Suggested Resolution

**Option A — Persist `samplingFeature@link` on Observations:**
1. Store the FOI association when provided on POST/PUT
2. Return it on GET (both individual and collection queries)
3. Support filtering: `GET /observations?samplingFeature={id}`

**Option B — Reject unsupported fields:**
1. Return HTTP 422 if `samplingFeature@link` is provided but not supported
2. This makes the gap visible to clients at write time

---

*Filed: 2026-03-03 · Tested against live OSH instance · Test observation cleaned up after verification (DELETE 204)*
