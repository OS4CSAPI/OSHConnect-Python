# LOB Localizer — SOSA/SSN Semantic Mapping

**Date:** 2026-03-03  
**Status:** Implementation analysis — mapping of the LOB localizer to SOSA/SSN ontology and CSAPI resource model  
**Related:** [LOB_Localizer_Architecture_Correction.md](LOB_Localizer_Architecture_Correction.md)

---

## Purpose

This document explains what the gold UAS location estimate dots on the webapp map *are* semantically — how they conform to the SOSA/SSN ontology, SWE Common data encoding, and the OGC API — Connected Systems (CSAPI) resource model. It also documents what is registered on the server, the observation workflow, and known standards conformance gaps.

---

## 1. SOSA/SSN Ontology Mapping

The localizer is an **`ssn:System`** — the exact same design pattern as the Multi-Array Triangulation Engine (`triangulation-engine-001`) in the reference ODAS data model (`sosa-ssn-csapi-data-model.md` §1.7). It is a computational fusion system, not a physical sensor.

| SOSA/SSN Concept | Localizer Instance | Notes |
|---|---|---|
| `ssn:System` | AZ-String-Alpha LOB Triangulator | `featureType: sosa:System` — a composite processing entity |
| `sosa:Procedure` | WLS LOB Triangulation v1 | `sosa:ObservingProcedure` — the algorithm description |
| `sosa:Observation` | Each gold dot on the map | A single location estimate fix |
| `sosa:Result` | 9-field `DataRecord` (lat, lon, CEP50, classification, residual, etc.) | Conforms to SWE Common encoding |
| `sosa:ObservableProperty` | UAS estimated position | The *derived* property being observed (not a raw sensor measurement) |
| `ssn:Input` | N≥2 LOB observations from MA-1/2/3 | Consumed via CSAPI GET — `sosa:Observation` results from upstream sensors |
| `ssn:Output` | Location estimate observation | Published via CSAPI POST to the localizer's DataStream |

### SOSA Relationship Chain

```
sosa:Procedure (WLS LOB Triangulation v1)
    ↑ ssn:implements (systemKind / typeOf)
ssn:System (AZ-String-Alpha LOB Triangulator)
    → DataStream (az_string_alpha_location_estimate)
        → sosa:Observation (each gold dot)
            → sosa:Result { estimatedLat, estimatedLon, cep50_m, ... }
```

### Comparison to Reference Model

The localizer follows the same `ssn:System` pattern as the ODAS Triangulation Engine:

| Attribute | Triangulation Engine (Reference) | LOB Localizer (Implemented) |
|---|---|---|
| `featureType` | `sosa:System` | `sosa:System` (implied by `typeOf`) |
| `geometry` | `null` (computational, not physical) | `null` |
| `assetType` | `Process` | (not set — should be `Process`) |
| Procedure link | `systemKind@link` | `typeOf` (see §4 gap) |
| Input source | DOA vectors from multiple arrays | LOB observations from 3 MA nodes |
| Output | Triangulated 3D position | WLS 2D position + CEP50 |
| DataStream schema | GeoJSON Point + uncertainty ellipse | SWE DataRecord (9 scalar fields) |

---

## 2. CSAPI Server Resources

`bootstrap_localizer.py` registers three resources on the server. All three follow OGC API — Connected Systems Part 1 (systems, procedures) and Part 2 (datastreams, observations).

### 2.1 Procedure (Part 1)

```
UID:  urn:os4csapi:procedure:lob-wls-triangulation:v1
ID:   0450
Name: WLS LOB Triangulation v1
Type: sosa:Procedure (implicitly sosa:ObservingProcedure)
```

Describes the **algorithm**, not the system instance. Weighted least-squares bearing intersection with inverse-variance weighting. Analogous to the "Ray-to-Ray Triangulation Procedure" in the ODAS reference model.

### 2.2 System (Part 1)

```
UID:  urn:os4csapi:system:fusion:az-string-alpha-localizer
ID:   04n0
Name: AZ-String-Alpha LOB Triangulator
```

A **software agent** — no physical location, no geometry. References the procedure via `typeOf`. This system is the `sosa:Sensor` (in the broad SOSA sense where a sensor is "an entity that provides information about a property") that produces all location estimate observations.

### 2.3 DataStream (Part 2)

```
ID:         04f0
outputName: az_string_alpha_location_estimate
Name:       UAS Location Estimate
Schema:     SWE Common DataRecord (9 fields)
```

Attached to the System above. Carries the observation schema — a SWE Common `DataRecord` with the following fields:

| # | Field Name | SWE Type | Definition URI | UoM |
|---|---|---|---|---|
| 1 | `timestamp` | Time | `odas/time/epochSeconds` | s |
| 2 | `trackId` | Count | `odas/trackId` | — |
| 3 | `estimatedLat` | Quantity | `fusion/estimatedLat` | deg |
| 4 | `estimatedLon` | Quantity | `fusion/estimatedLon` | deg |
| 5 | `cep50_m` | Quantity | `fusion/cep50` | m |
| 6 | `classification` | Text | `odas/classification` | — |
| 7 | `numContributingLobs` | Count | `fusion/numContributingLobs` | — |
| 8 | `contributingSensors` | Text | `fusion/contributingSensors` | — |
| 9 | `residual_m` | Quantity | `fusion/residual` | m |

Definition URIs use the `https://os4csapi.org/def/fusion/` and `https://os4csapi.org/def/odas/` namespaces.

---

## 3. Observation Structure

Each gold dot on the map is a **`sosa:Observation`** POSTed to `datastreams/04f0/observations`:

```json
{
  "phenomenonTime": "2026-03-03T01:45:12.345Z",
  "resultTime": "2026-03-03T01:45:12.345Z",
  "result": {
    "timestamp": 1741052712.345,
    "trackId": 1,
    "estimatedLat": 31.667123,
    "estimatedLon": -110.258456,
    "cep50_m": 45.2,
    "classification": "UAS",
    "numContributingLobs": 3,
    "contributingSensors": "AZ-MA-1,AZ-MA-2,AZ-MA-3",
    "residual_m": 37.7
  }
}
```

The `result` conforms to the SWE Common `DataRecord` schema registered on the DataStream. Every field maps to a definition URI — this is the SWE Common mechanism for semantic interoperability.

### SOSA Property Mapping for Each Observation

| SOSA Property | Value |
|---|---|
| `sosa:madeBySensor` | System `04n0` (via DataStream → System link) |
| `sosa:usedProcedure` | Procedure `0450` (via System → typeOf link) |
| `sosa:observedProperty` | Estimated UAS position (via DataStream definition URIs) |
| `sosa:hasResult` | The `result` object |
| `sosa:resultTime` | When the WLS computation completed |
| `sosa:phenomenonTime` | When the estimated position applies (≈ same as resultTime for real-time fusion) |

---

## 4. Workflow — Pure CSAPI Actor Pattern

The localizer operates as a **CSAPI actor** — it only interacts through the API. No direct coupling between producers, the fusion agent, or consumers.

```
MA-1/2/3 (sosa:Sensor) ──POST──► LOB DataStreams (Part 2)
                                       │
                            ◄──GET──┘  (poll latest observation)
                                       │
Localizer (ssn:System)  ── WLS compute ──► Location Estimate DataStream (Part 2)
                                                     │
                                          ◄──GET──┘  (webapp polls latest)
                                                     │
                                            Webapp renders gold ⊕ marker
```

### Three-Actor Loose Coupling

1. **Producers** — The simulator (or real ODAS hardware) POSTs LOB observations to MA-1/2/3 DataStreams.
2. **Fusion Agent** — The localizer GETs the latest LOBs, runs WLS intersection, POSTs the location estimate.
3. **Consumer** — The webapp GETs the latest location estimate and renders it on the map.

The localizer doesn't know or care whether the LOBs come from the simulator, from real ODAS hardware, or from a replay file. All communication is mediated through CSAPI observations. This is the defining characteristic of the architecture: **zero direct coupling, full CSAPI mediation**.

### Quality Gates

The localizer applies several gates before publishing a fix:

| Gate | Threshold | Purpose |
|---|---|---|
| Staleness | `MAX_LOB_AGE_S = 15s` | Reject LOBs older than 3× the poll interval |
| Deduplication | Per-DS observation ID tracking | Don't reprocess the same observation |
| Minimum LOBs | `MIN_LOBS = 2` | Need ≥2 bearings for geometric fix |
| Correlation window | `CORRELATION_WINDOW = 10s` | LOBs in a group must be temporally close |
| Residual cap | `RESIDUAL_CAP = 500m` | Reject fixes where bearing lines are wildly inconsistent |

---

## 5. Standards Conformance Gaps

The current implementation is functionally complete but has several cosmetic gaps relative to full SOSA/SSN/CSAPI standards conformance:

### 5.1 No `observedProperties` Link

The DataStream should reference a `Property` resource (CSAPI Part 1) for "estimated UAS position". We did not register a Property resource. OSH does not enforce this, but full conformance requires:

```json
{
  "observedProperties": [
    "urn:os4csapi:property:fusion:estimated-uas-position"
  ]
}
```

**Remediation:** Register a Property resource and add the link to the DataStream definition.

### 5.2 No `featureOfInterest`

Each observation should link to a `sosa:FeatureOfInterest` — the airspace being monitored or the UAS track itself. We don't reference one.

**Remediation:** Create a SamplingFeature representing the monitored airspace (similar to the "Acoustic Monitoring Zone" in the reference model) and link observations to it.

### 5.3 `typeOf` vs `systemKind@link`

The System definition uses `typeOf` to reference the Procedure:

```json
{ "properties": { "typeOf": "urn:os4csapi:procedure:lob-wls-triangulation:v1" } }
```

The CSAPI spec and the reference model prefer the `systemKind@link` pattern:

```json
{
  "systemKind@link": {
    "href": "{api_root}/procedures/0450",
    "rel": "systemKind",
    "title": "WLS LOB Triangulation v1"
  }
}
```

Both are accepted by OSH. The `typeOf` approach uses a UID while `systemKind@link` uses a resolvable href.

### 5.4 No `ssn:Deployment`

The localizer is not registered under any `ssn:Deployment`. Since it's a hosted cloud service (Fly.io), it arguably has no physical deployment location. However, a deployment record would complete the provenance chain and document *when* the localizer was activated.

### 5.5 Missing `assetType` and `featureType`

The System registration doesn't explicitly set `featureType: sosa:System` or `assetType: Process`. These would improve discoverability and allow the webapp to render the localizer in system hierarchy views.

---

## 6. Hosting Architecture

The localizer runs as a background thread inside the Fly.io simulator service (`os4csapi-simulator.fly.dev`), not as a separate service. This is documented in [LOB_Localizer_Architecture_Correction.md](LOB_Localizer_Architecture_Correction.md) §5.

| Component | Location | Endpoints |
|---|---|---|
| Simulator engine | `simulator/engine.py` | WLS algorithm, discovery, observation builders |
| FastAPI wrapper | `simulator/main.py` | `/localizer/start`, `/localizer/stop`, `/localizer/status` |
| Admin UI | `demo/src/pages/SimulatorAdminPage.vue` | LOB Localizer panel with status + controls |
| Standalone script | `scripts/localizer.py` | CLI for local debugging (same algorithm) |
| Bootstrap | `scripts/bootstrap_localizer.py` | One-time server registration |

---

## References

- [W3C SOSA/SSN Ontology](https://www.w3.org/TR/vocab-ssn/) — §4.3 System, §4.4 Observation
- [OGC API — Connected Systems Part 1](https://docs.ogc.org/is/23-001/23-001.html) — Systems, Procedures, Deployments
- [OGC API — Connected Systems Part 2](https://docs.ogc.org/is/23-002/23-002.html) — DataStreams, Observations
- [OGC SWE Common 3.0](https://docs.ogc.org/is/24-014/24-014.html) — DataRecord schema encoding
- [LOB_Localizer_Architecture_Correction.md](LOB_Localizer_Architecture_Correction.md) — Architecture design and deliverables
- [sosa-ssn-csapi-data-model.md](../../docs/webapp-demo/ODAS-CSAPI-Adapter-Simulator/sosa-ssn-csapi-data-model.md) — Reference ODAS data model
