# CSAPI Deployment Modeling — Standards Conformance Analysis

| Field | Value |
|---|---|
| **Date** | 2026-03-02 |
| **Author** | Claude (Opus 4.6) — reviewing ChatGPT (o3) standards analysis |
| **Status** | Standards Gap Analysis |
| **Scope** | `deployedSystems` vs `platform@link`, subdeployment semantics, OSH conformance |
| **Follows** | [AZ-MA-2/MA-3 Migration Procedure Analysis](AZ-MA-2_MA-3_Migration_Procedure_Analysis.md) |
| **Standard** | [OGC API — Connected Systems — Part 1](https://ogcapi.ogc.org/connectedsystems/) |

---

## 1  Context

During planning for the AZ-MA-2 and AZ-MA-3 migrations, ChatGPT (o3) was asked to evaluate how the OGC Connected Systems API standard prescribes the relationship between Deployments and Systems — specifically, how to correctly model three ODAS microphone-array nodes deployed on a single "String Alpha" deployment.

ChatGPT identified that the standard uses `deployedSystems` (a required, 1:many association) as the primary mechanism, and that OSH's apparent reliance on `platform@link` for system→deployment wiring may represent an implementation gap.

This report validates ChatGPT's standards reading, adds nuance on three points, and derives concrete action items for the migration.

---

## 2  Where the Standards Analysis Is Correct

### 2.1  `deployedSystems` Is the Primary System→Deployment Association

OGC CSAPI Part 1 defines a Deployment as "deployment of one or more Systems." The core association for this is `deployedSystems`, not `platform`. In the GeoJSON encoding, this appears as `properties/deployedSystems@link` — a JSON array of links to System resources.

**This directly addresses the 3-node problem.** One String Alpha deployment can hold `[AZ-MA-1, AZ-MA-2, AZ-MA-3]` in its `deployedSystems` array without any structural workaround.

### 2.2  `platform` Is for Physical Things, Not Systems

The standard defines `platform` as an optional, single Feature — and explicitly states the platform "can also be any feature (e.g., a building or a tree)." It is the physical object hosting the sensors, not the sensor system itself.

**What the MA-1 migration does today is semantically incorrect.** The migration script (`migrate_az_ma_1.py`, Phase 7) does:

```python
PUT /deployments/{string-alpha-id}
body: { "platform@link": { "href": "/sensorhub/api/systems/{ma-1-oracle-id}", ... } }
```

This uses `platform@link` to wire a *System* to a Deployment. Per the standard, that link should point to the physical monitoring site (a Feature), not to the ODAS system. The ODAS system belongs in `deployedSystems`.

### 2.3  The 1:Many Model Is Real

`deployedSystems@link` is a JSON array in both GeoJSON and SensorML-JSON encodings. The SensorML 3.0 `DeployedSystem` schema further supports per-deployed-system `configuration` objects, enabling node-specific settings without per-node procedure duplication.

### 2.4  Subdeployments Are Explicitly Standards-Aligned

The standard defines a Subdeployment conformance class with `{api_root}/deployments/{parentId}/subdeployments`. This is not a workaround — it is a first-class concept with its own requirements class.

---

## 3  Where Nuance Is Needed

### 3.1  "Required" Needs Qualification

ChatGPT states `deployedSystems` is "required." This is accurate at the conformance class level — the server **must expose the endpoint** (`GET /deployments/{id}/deployedSystems`). However, it does not mean every deployment instance must have at least one entry. A newly created deployment with zero assigned systems is valid.

The distinction matters because OSH can be "conformant at the schema level" (the endpoint exists) while still having a functional gap (nothing gets populated correctly on the write path). The question isn't whether OSH *returns* `deployedSystems` — it's whether it *accepts and persists* `deployedSystems@link` arrays on POST/PUT.

### 3.2  The OSH Gap Is Likely in the Write Path, Not Just the Read Path

From the MA-1 migration and the bootstrap scripts, we can confirm the current programmatic behavior:

- `migrate_az_ma_1.py` (Phase 7) uses `platform@link` to associate AZ-MA-1 with String Alpha
- `bootstrap_v25.py` also uses `platform@link` for all deployment→system wiring
- Neither script ever attempts `deployedSystems@link`

**We do not actually know if OSH rejects `deployedSystems@link`.** It has never been tested. The critical unknown is whether the implementation accepts a `deployedSystems@link` array on POST/PUT and correctly persists + indexes it, or whether it silently drops the field.

### 3.3  Subdeployments Are Not Just a Workaround — They're Operationally Superior

ChatGPT frames subdeployments as a "works-today workaround" in case OSH lacks `deployedSystems` support. This undersells their value. Even with full `deployedSystems` support, per-node subdeployments are the better operational model for ODAS arrays:

| Concern | Flat `deployedSystems` Only | Subdeployments |
|---|---|---|
| **Independent lifecycle** | Can't decommission Node 2 without editing the parent | End the Node 2 subdeployment's `validTime` |
| **`deployment@link` on datastreams** | All 21 datastreams point to String Alpha — can't filter by node | Each node's 7 datastreams point to their own sub-deployment |
| **Temporal fidelity** | All 3 nodes share one `validTime` range | Each node has its own deployment date |
| **Observation scoping** | `GET /deployments/{string-alpha}/observations` returns all 3 nodes mixed | `GET /deployments/{node-2}/observations` returns only Node 2 |
| **Per-node metadata** | Requires SensorML `DeployedSystem/configuration` (may not be implemented in OSH) | Each sub-deployment carries its own properties natively |

The standard's recursive aggregation rule further confirms this: a parent deployment's `deployedSystems` must include deployed systems from subdeployments when queried recursively. This means querying String Alpha returns all 3 nodes, while querying Node 2 returns only Node 2 — the best of both worlds.

---

## 4  The Ideal Standards-Conformant Model

The two approaches — `deployedSystems` and subdeployments — are *complementary, not competing*. The full standards-conformant model for the 3-node ODAS array is:

```
String Alpha (deployment)
  platform@link  → Monitoring Site Feature (physical location, NOT a system)
  deployedSystems = [AZ-MA-1, AZ-MA-2, AZ-MA-3]  ← aggregated from children
  │
  ├─ Node 1 (sub-deployment)
  │    deployedSystems = [AZ-MA-1]
  │    validTime: 2026-02-27 → now
  │
  ├─ Node 2 (sub-deployment)
  │    deployedSystems = [AZ-MA-2]
  │    validTime: TBD → now
  │
  └─ Node 3 (sub-deployment)
       deployedSystems = [AZ-MA-3]
       validTime: TBD → now
```

Key characteristics:
- **`platform`** points to a Feature (the physical monitoring site), not a System
- **`deployedSystems`** is used at every level — both parent and sub-deployments
- **Subdeployments** provide per-node lifecycle, temporal, and query isolation
- **Recursive aggregation** makes String Alpha automatically report all 3 nodes when traversed

---

## 5  Impact on Migration Plan

### 5.1  Immediate Action: Probe OSH

Before writing any migration code for MA-2/MA-3, execute a simple conformance probe:

```
POST /deployments
Content-Type: application/geo+json

{
  "type": "Feature",
  "properties": {
    "uid": "urn:test:probe:deployed-systems",
    "name": "DeployedSystems Probe",
    "featureType": "sosa:Deployment",
    "validTime": ["2026-03-01T00:00:00Z", ".."],
    "deployedSystems@link": [
      {
        "href": "/sensorhub/api/systems/{some-existing-id}",
        "type": "application/geo+json"
      }
    ]
  }
}
```

Expected outcomes:
- **201 Created + field persisted**: OSH supports `deployedSystems` — use it directly
- **201 Created + field silently dropped**: OSH accepts the POST but ignores the array — implementation gap confirmed
- **400 Bad Request**: OSH rejects the field — different kind of gap

This test takes 5 minutes and determines which path is available. Follow up with a GET to verify the field is actually returned.

### 5.2  Stop Using `platform@link` for System Association

Regardless of the probe outcome, the migration plan should be updated:

| Scenario | `platform@link` Use | `deployedSystems@link` Use |
|---|---|---|
| OSH supports `deployedSystems` | Point to a Monitoring Site Feature (or omit) | Wire systems via `deployedSystems@link` array |
| OSH drops `deployedSystems` | Continue as workaround, but annotate as non-conformant | File OSH bug, track as known gap |

### 5.3  Consider a Monitoring Site Feature

Per the standard, `platform` should point to the physical site. This could be:

- A `SamplingFeature` with the site's geolocation (Fort Huachuca coordinates)
- A plain GeoJSON Feature representing the monitoring site
- Created via `POST /samplingFeatures` or `POST /features` if OSH supports it

This is low priority relative to the migration itself, but is the correct long-term model.

### 5.4  Revised Sub-Deployment Wiring

The procedure analysis report proposed sub-deployments, which remains correct. The update is in *how* each sub-deployment associates its system:

**Before (current approach):**
```json
{ "platform@link": { "href": "/sensorhub/api/systems/{node-id}" } }
```

**After (standards-conformant):**
```json
{
  "deployedSystems@link": [
    { "href": "/sensorhub/api/systems/{node-id}", "type": "application/geo+json" }
  ]
}
```

If the OSH probe shows `deployedSystems` is not supported on the write path, fall back to `platform@link` with a documented deviation.

---

## 6  Summary of Findings

| Question | Answer |
|---|---|
| Is `deployedSystems` the correct standard mechanism for system→deployment? | **Yes.** It is the primary, required (at endpoint level) association. |
| Is `platform@link → System` correct per the standard? | **No.** `platform` should point to a physical Feature, not a System. |
| Can one Deployment hold multiple systems? | **Yes.** `deployedSystems@link` is a JSON array. |
| Are subdeployments a workaround? | **No.** They are a first-class standard concept and are operationally superior for this use case. |
| Does OSH support `deployedSystems@link` on POST/PUT? | **Unknown.** Never tested. Must probe before migration. |
| Should we use both `deployedSystems` and subdeployments? | **Yes.** They are complementary. Use subdeployments for per-node lifecycle; `deployedSystems` at each level for system association. |

---

## 7  Action Items

| # | Action | Priority | Effort |
|---|---|---|---|
| 1 | Probe OSH `deployedSystems@link` on POST/PUT | **Critical** — gates migration approach | 5 min |
| 2 | Update migration script to use `deployedSystems@link` (or document workaround) | High | 30 min |
| 3 | Fix MA-1 on Oracle: move system from `platform@link` to `deployedSystems@link` | Medium | 15 min |
| 4 | Create Monitoring Site Feature for String Alpha `platform` | Low | 30 min |
| 5 | File OSH bug if `deployedSystems` is not supported on write path | Conditional | 15 min |

---

## Appendix — Standards References

| Citation | Source |
|---|---|
| Deployment = "one or more Systems" | CSAPI Part 1, Deployment concept |
| `deployedSystems`: required, list of System resources | CSAPI Part 1, Table 11 (Deployment Associations) |
| `platform`: optional, single Feature (not just System) | CSAPI Part 1, Table 11; "can also be any feature" |
| GeoJSON `deployedSystems@link`: JSON array | CSAPI Part 1, GeoJSON encoding |
| SensorML `DeployedSystem`: array with per-system `configuration` | CSAPI Part 1, SML-JSON encoding; SensorML 3.0 schema |
| Subdeployment conformance class | CSAPI Part 1, `{api_root}/deployments/{parentId}/subdeployments` |
| Recursive aggregation rule | CSAPI Part 1: parent `deployedSystems` includes children's |
| `system` query parameter on `/deployments` | CSAPI Part 1: filter deployments by deployed system |
