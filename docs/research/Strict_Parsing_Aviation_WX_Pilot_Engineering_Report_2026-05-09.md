# Aviation-WX Strict-Parsing Pilot — Engineering Report

**Date:** 2026-05-09
**Author:** OS4CSAPI / OSHConnect-Python team
**Branch:** `fix/aviation-wx-strict-parsing-2026-05-09`
**Commits:** `ca2b794` (research §9 update), `9206be0` (publisher fix)
**Target server:** `https://129-80-248-53.sslip.io/csapi-go-v2/` (`connected-systems-go` post-`a467aba0` strict parsing, `c2ab201` partial typo fix)
**Companion document:** [Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md](Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md) §9

---

## 1. Summary

The aviation-wx publisher has been refactored to publish cleanly against
the strict-parsing csapi-go-v2 server. End-to-end live run produced
**zero rejections**: 1 procedure, 5 systems with full SensorML, 5
datastreams, and a 3-tier deployment tree (root + group + 5 station
deployments). Round-trip verification confirms keywords, identifiers,
classifiers, contacts, documents, position, and links are all preserved
on systems.

This document captures the empirically-derived schema for each resource
type so the same recipe can be propagated mechanically to the remaining
8 publishers (`coops`, `iss`, `ndbc`, `nws`, `opensky`, `usgs_eq`,
`usgs_nims`, `usgs_water`).

---

## 2. The encoding contract (one-line statement)

> Strict csapi-go-v2 enforces OGC 23-001's closed `feature.properties`
> schema. **All SensorML metadata must be PUT separately** as
> `application/sml+json` against the resource path after the
> `application/geo+json` POST creates the resource.

The two-step pattern (already implemented in
[publishers/bootstrap_helpers.py](../../publishers/bootstrap_helpers.py)
as `ensure_procedure(stub, sml_body=...)`,
`ensure_system(stub, sml_body=...)`,
`ensure_deployment(stub, sml_body=..., parent_id=...)`):

1. `POST /{collection}` with `Content-Type: application/geo+json` —
   stub body has only the closed properties set.
2. `PUT /{collection}/{id}` with `Content-Type: application/sml+json` —
   SensorML JSON encoding (`uniqueId`, `label`, `definition`, …).

---

## 3. Empirically-derived schemas (per-resource)

### 3.1 `POST /systems` — GeoJSON Feature

| `properties` field | Strict server |
| --- | --- |
| `featureType`, `uid`, `name`, `description` | ✅ accepted |
| `typeOf@link`, `procedure@link`, `links`, `validTime`, `keywords`, `documentation`, `contacts`, anything else | ❌ **400 unknown field** |

### 3.2 `PUT /systems/{id}` — SensorML JSON encoding

| Field | Status |
| --- | --- |
| `type`, `uniqueId`, `label`, `definition`, `description` | ✅ |
| `keywords`, `identifiers`, `classifiers`, `contacts`, `documents` (✱) | ✅ |
| `position`, `validTime`, `history`, `securityConstraints`, `legalConstraints`, `links` | ✅ |
| `characteristics`, `capabilities` | ❌ **400 unknown field** — surprising; OGC 12-000r2 SensorML JSON encoding fields |
| `typeOf` | ⚠️ **HTTP 500 "Failed to update system"** — server-side defect |
| GeoJSON-encoding names (`uid`, `name`, `featureType`) | ❌ **400** |

(✱) On `/systems` use the canonical name **`documents`** — fixed by upstream commit `c2ab201`.

### 3.3 `POST /procedures` — GeoJSON Feature

| `properties` field | Strict server |
| --- | --- |
| `featureType`, `uid`, `name`, `description`, **`validTime`** | ✅ accepted (note: `validTime` IS allowed here) |
| `keywords`, `links`, anything else | ❌ **400 unknown field** |

### 3.4 `PUT /procedures/{id}` — SensorML JSON encoding

| Field | Status |
| --- | --- |
| `type`, `uniqueId`, `label`, `definition`, `description` | ✅ |
| `keywords`, `identifiers`, `contacts`, `validTime` | ✅ |
| **`documentation`** (typo) | ✅ accepted |
| **`documents`** (canonical) | ❌ **400 unknown field** |

> **⚠ Asymmetry vs. `/systems`:** the `c2ab201` upstream fix landed
> only on `SystemSensorMLFeature`, not on `ProcedureSensorMLFeature`.
> Until the follow-up commit lands, the procedure SML PUT requires
> the typo'd field name `documentation`. Track this as upstream issue
> follow-up to OS4CSAPI/connected-systems-go #10.

### 3.5 `POST /deployments` — GeoJSON Feature

| `properties` field | Strict server |
| --- | --- |
| `featureType`, `uid`, `name`, `description`, **`validTime`**, **`platform@link`** | ✅ |
| `documentation`, `parent@link`, `links`, anything else | ❌ **400 unknown field** |

`platform@link` accepts `{href, uid, title}`. Sub-deployments use
`POST /deployments/{parent_id}/subdeployments`.

### 3.6 `POST /systems/{system_id}/datastreams` — Part 2 schema body

| Body field | Status |
| --- | --- |
| `name`, `description`, `outputName`, `phenomenonTime`, `observedProperties`, `formats` | ✅ |
| `schema.obsFormat` = `application/om+json` | ✅ |
| `schema.resultSchema.type` = `DataRecord` | ✅ |
| `schema.resultSchema.fields[].uom` (Time + Quantity) | ✅ |
| `documentation`, `characteristics` | ❌ **400 unknown field** |
| Time field `referenceTime` | ❌ **400 unknown field in schema.resultSchema.fields[N]** |
| Datastream `uid` (top-level) | ❌ rejected — server assigns its own |

---

## 4. Concrete changes applied to aviation-wx

| File / location | Before | After |
| --- | --- | --- |
| `PROCEDURE_BODY` (single dict) | SensorML metadata (`keywords`, `documentation`, `contacts`, `lineage`, `usageConstraints`) inside `properties` | Split into `PROCEDURE_BODY_STUB` (closed properties + `validTime`) and `PROCEDURE_SML` (full SensorML JSON, uses `documentation` typo per §3.4) |
| `_system_stub()` | `properties.{typeOf@link, links, validTime}` | Closed properties only — typeOf/links/validTime moved into `_system_sml()` (where supported) |
| `_system_sml()` | Included `characteristics` + `capabilities` arrays | Dropped both (server rejects); equivalent info preserved via `identifiers`, `classifiers`, `position`, `documents` |
| `_datastream_schema()` | `documentation`, `characteristics`, top-level `uid`, Time field `referenceTime` | All removed; only server-accepted fields retained |
| `_deploy_root() / _deploy_group()` | `documentation` array | Removed; closed properties + `validTime` only |
| `_deploy_station()` | `links` array | Removed; `platform@link` retained |
| `bootstrap()` proc call | `ensure_procedure(..., PROCEDURE_BODY)` | `ensure_procedure(..., PROCEDURE_BODY_STUB, sml_body=PROCEDURE_SML, force_sml=force_sml)` |

---

## 5. Live verification

Command: `python -m publishers.aviation_wx.bootstrap_aviation_wx --clean`
against `BOOTSTRAP_URL=https://129-80-248-53.sslip.io/csapi-go-v2`.

```
── Procedures ──
  [OK] Created procedure urn:os4csapi:procedure:metar-decoder:v1 → id=765585ac…
── Systems + Datastreams ──
  [OK] Created system urn:os4csapi:system:awx:ktus:v1 → id=d84d684b…
  [OK] Created datastream 'metarObs' → id=b82bc9d4…
  [… × 5 stations …]
── Deployments ──
  [OK] Created deployment urn:os4csapi:deployment:awx-metar-demo:v1 → id=084e5584…
  [OK] Created deployment urn:os4csapi:deployment:awx-stations:v1   → id=ce8b5807…
  [OK] Created deployment urn:os4csapi:deployment:awx-ktus:v1       → id=b3bcc331…
  [… × 5 stations …]
```

Round-trip GET `application/sml+json` for KDMA returned full SensorML
with `keywords`, `identifiers`, `classifiers`, `contacts`, `documents`,
`position`, `links`, `validTime`, `definition`, `uniqueId`, `label`,
`description` all populated as published.

---

## 6. Information loss disclosure

Two SensorML structures previously published cannot currently round-trip:

1. **`characteristics`** (operator, station type, FAA identifier,
   field elevation as a grouped SWE DataRecord). Equivalent atoms are
   preserved via `identifiers` (Short/Long Name, ICAO ID),
   `classifiers` (Sensor Type, Intended Application), and `position`
   (geodetic). Field elevation is currently lost from SML; `description`
   text retains it as prose.
2. **`capabilities`** (publisher publish-interval, data-source).
   Equivalent provenance is preserved in `documents` and in the
   procedure SML's `documentation` array.

Both losses are server-side limitations of csapi-go-v2 (see §3.2); when
upstream restores `characteristics`/`capabilities` we can re-enable
those blocks unchanged.

---

## 7. Recipe for fleet propagation

Apply per-publisher in order (same pattern, mechanical):

1. **Identify GeoJSON stubs** for procedures, systems, deployments.
   Anything in `properties` outside §3.1 / §3.3 / §3.5 must move out.
2. **Build companion SML bodies** using OGC SensorML JSON encoding:
   `uniqueId` / `label` / `definition` / `description` /
   `keywords` / `identifiers` / `classifiers` / `contacts` /
   `documents` (or `documentation` for procedures, see §3.4) /
   `position` / `links`.
3. **Wire `sml_body=` argument** on `ensure_procedure` /
   `ensure_system` / `ensure_deployment` calls. Pass
   `force_sml=force_sml` so the `--force-sml` CLI flag works.
4. **Strip datastream schemas** of `documentation`, `characteristics`,
   top-level `uid`, and Time field `referenceTime`.
5. **Validate**: dry-run first
   (`OS4CSAPI_STRICT_BOOTSTRAP=1 python -m publishers.<NAME>.bootstrap_<NAME> --dry-run`).
   Then live: `--clean` (idempotent reset), then plain
   bootstrap to confirm SKIP-on-second-run. Then `curl … -H 'Accept: application/sml+json'` round-trip on at least one resource per type.
6. **Commit per-publisher** with a message like
   `fix(<publisher>): split GeoJSON stubs from SensorML bodies for strict csapi-go-v2`.

The `OS4CSAPI_STRICT_BOOTSTRAP=1` guardrail in
[bootstrap_helpers.py](../../publishers/bootstrap_helpers.py)
(`_warn_if_sml_fields_in_stub`) raises `RuntimeError` on any leaked
SML field — recommended for the dry-run.

---

## 8. Outstanding upstream issues (file separately)

1. **OS4CSAPI/connected-systems-go #10 follow-up**: replicate the
   `c2ab201` `documents`/`documentation` rename onto
   `ProcedureSensorMLFeature` (see §3.4).
2. **`ProcedureSensorMLFeature` HTTP 500 path**: any unknown SML field
   surfaces as `{"error":"Failed to update procedure"}` HTTP 500 instead
   of a clean 400 with a field name. (Compare clean 400 on `/systems`
   PUT.) Defensive parsing or a clearer error path is warranted.
3. **`SystemSensorMLFeature.characteristics` / `.capabilities` rejection**:
   these fields are first-class in OGC 12-000r2 SensorML JSON encoding
   and OGC 23-001 references the SML schema by reference. Either the
   server should accept them or document that it does not. (See §3.2.)
4. **`SystemSensorMLFeature.typeOf` HTTP 500**: same defensive-parsing
   point as #2 — should be 400 with a field-name error or it should
   simply work. (See §3.2.)

---

## 9. Next actions

- [x] aviation-wx: refactored, dry-run + live verified, committed.
- [ ] coops: apply recipe.
- [ ] iss: apply recipe.
- [ ] ndbc: apply recipe.
- [ ] nws: apply recipe.
- [ ] opensky: apply recipe.
- [ ] usgs_eq: apply recipe.
- [ ] usgs_nims: apply recipe.
- [ ] usgs_water: apply recipe.
- [ ] After all 9 land, open PR vs. `main`, link this report and the §9 reanalysis.
- [ ] File the four upstream issues from §8 against `OS4CSAPI/connected-systems-go`.
