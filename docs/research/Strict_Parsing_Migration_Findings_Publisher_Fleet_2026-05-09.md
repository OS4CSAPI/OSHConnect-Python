# Strict-Parsing Migration Findings — Publisher Fleet vs. Upstream `connected-systems-go`

**Date:** 2026-05-09
**Author:** OS4CSAPI engineering (automated investigation, sbolling)
**Scope:** All nine `*-publisher-go` services in the OSHConnect-Python fleet
**Trigger:** Migration from frozen fork (`OS4CSAPI/connected-systems-go`, code-frozen 2026-04-16) to current upstream HEAD (`SomethingCreativeStudios/connected-systems-go @ d14d16d3`, 2026-05-09)
**Server under test:** `https://129-80-248-53.sslip.io/csapi-go-v2`
**Status:** Migration complete on the server side; **all 9 publishers fail to bootstrap** against the new server.
**Predecessor report:** [`Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md`](./Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md) (NWS-only finding; this report supersedes it with fleet-wide scope)

---

## 1. Executive Summary

On 2026-05-02, the upstream `connected-systems-go` server added strict JSON parsing (commit `a467aba0`, "Adding Strict Parsing… now unknown fields will cause a bad request with the path and field name"). Until 2026-05-09 the OS4CSAPI fleet had only ever been tested against pre-strict servers — primarily our own fork, which silently dropped any unknown JSON fields rather than rejecting them.

When the publishers were repointed at a freshly-built strict server, **every single one returned HTTP 400 on its first or second resource POST**. The rejection messages cluster into two distinct bug classes:

| Class | Field | Affected publishers | Real bug? |
|---|---|---|---|
| **A. Field placement bug** | `keywords` in `properties` | aviation-wx, coops, ndbc, nws, opensky, usgs-nims, usgs-water | **Yes — publisher** |
| **A. Field placement bug** | `documentation` in `properties` | usgs-eq | **Yes — publisher** |
| **A. Field placement bug** | `documents` in `properties` (see §6) | nws (force-sml path only) | **Yes — publisher** |
| **B. Wrong-resource link** | `procedure@link` in `properties` of a `system` POST | iss | **Yes — publisher** |

All four are publisher-side bugs. There is **no upstream regression**; strict parsing is correctly identifying real schema violations that pre-strict servers were silently swallowing.

The fleet has been carrying these bugs for the entire history of the repo. They were undetectable until today because no server ever pushed back.

---

## 2. How the bugs hid

### 2.1 The fork tolerated everything

`OS4CSAPI/connected-systems-go` (frozen 2026-04-16) accepted any JSON body and persisted whatever fields it recognised, silently discarding the rest. Every publisher in OSHConnect-Python was developed and tested exclusively against that server. The fleet's "green" test results never validated wire-format correctness — only that the `name`, `description`, `uid`, and `featureType` fields landed.

### 2.2 The corruption was downstream-invisible

Because the discarded fields (`keywords`, `documentation`, etc.) were never round-tripped, downstream consumers of the API — including our explorer and Smoke Test pages — never saw them either. There was no gap between "what the publisher sent" and "what the explorer rendered" that would have hinted at silent loss. The May 6 report ([`Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md`](./Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md)) caught the NWS case because a `--force-sml` PUT to a strict server was the first time anything pushed back. Today's mass migration produced the same finding at fleet scale.

### 2.3 The publisher template was wrong from the beginning

All eight non-ISS publishers share a near-identical procedure-body template that nests SensorML metadata inside the GeoJSON `properties` envelope. That layout has never been spec-conformant, but it has also never been tested. ISS has its own bug class (§5) inherited from a different copy-paste lineage.

---

## 3. The strict server's contract

Source of truth: `internal/model/domains/{system,procedure,datastream,observation,control_stream,command}.go` at upstream `d14d16d3`.

### 3.1 Procedure top-level fields (POST `/procedures` body shape)

The Go struct serialises **directly** to the Feature body — i.e. these are siblings of `type`, `geometry`, and `properties`, **not children of `properties`**:

```
type, geometry, properties, validTime,
keywords, identifiers, classifiers,
securityConstraints, legalConstraints,
contacts, documentation, history,
characteristics, capabilities,
typeOf, configuration, featuresOfInterest,
inputs, outputs, parameters, method, modes,
components, connections,
attachedTo, localReferenceFrames, localTimeFrames,
links, procedureType, type (process type), lang
```

`properties` itself is a small bag containing **only** `{uid, featureType, name, description}` — i.e. `common_shared.Properties` (CSAPI's GeoJSON-feature properties), not SensorML body content.

### 3.2 System top-level fields (POST `/systems`)

Same pattern. Crucially:
- `keywords` is top-level on a System, **not** inside `properties`.
- `documentation` is top-level on a System, **not** inside `properties`.
- `procedure@link` **does not exist on the System model at all** — neither top-level nor nested.

### 3.3 Where `procedure@link` actually lives

`procedure@link` is defined as a JSON-tagged field on **four** domain models, none of which is `System`:

| Model | File | Line |
|---|---|---|
| `command.go` | `internal/model/domains/command.go` | 31 |
| `control_stream.go` | `internal/model/domains/control_stream.go` | 25 |
| `datastream.go` | `internal/model/domains/datastream.go` | 26 |
| `observation.go` | `internal/model/domains/observation.go` | 16 |

A System never carries a `procedure@link`. The link from a system to its procedure is expressed via the `typeOf` field (which maps to `TypeOfID` and joins to a `Procedure`) at the top level of the System body.

---

## 4. What our publishers send (the bug shape)

Every non-ISS publisher's `PROCEDURE_BODY` looks like this (NWS shown; others identical in structure):

```python
PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "NWS Surface Observation v1",
        "description": "...",
        "keywords": ["NWS", "NOAA", "ASOS", "AWOS", ...],         # ← REJECTED
        "documentation": [{"title": "...", "href": "...", ...}],  # ← REJECTED
        "validTime": ["2026-01-01T00:00:00Z"],
        "contacts": [...],                                        # ← would also be rejected
    },
}
```

**Correct shape** under strict parsing:

```python
PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "keywords":      [...],                                       # top-level
    "documentation": [...],                                       # top-level
    "validTime":     ["2026-01-01T00:00:00Z"],                    # top-level
    "contacts":      [...],                                       # top-level
    "properties": {
        "uid":         PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name":        "NWS Surface Observation v1",
        "description": "...",
    },
}
```

This is a **structural relocation**, not a rename. Every field name our publishers use is correct; the nesting depth is wrong by one level.

---

## 5. The ISS publisher's separate bug

ISS is the one publisher that gets past procedure creation. It successfully POSTs two procedures (`urn:os4csapi:procedure:sgp4-propagation:v1`, `urn:os4csapi:procedure:orbit-track-generation:v1`) before failing on the first system.

The failure:

```
HTTP 400 POST /systems: {"error":"unknown field 'procedure@link' in properties"}
```

In `bootstrap_iss.py` lines 121 and 143, the publisher constructs a system body that includes:

```python
"properties": {
    ...
    "procedure@link": {
        "href": "...",
        ...
    },
}
```

There are **two** bugs stacked here:
1. **Wrong resource**: `procedure@link` does not belong on a System at all. It belongs on the Datastream that the System produces.
2. **Wrong nesting**: Even on the resources where `procedure@link` is valid, it is a top-level field, not a nested one.

The conceptual fix is to remove the `procedure@link` from the system body entirely and emit it on the datastream POST instead. The link from System → Procedure (when needed) is `typeOf`, which goes top-level on the System.

---

## 6. The original NWS `documents` finding revisited

The May 6 report identified `unknown field 'documents'` under a `--force-sml` PUT for NWS. That finding stands but should be reframed:

- The field name `documents` is not a misspelling per se — it is a leftover from the upstream Go server's earlier draft schema. Today the Go server uses `documentation` (the SensorML-correct name) at the top level.
- The path is also wrong: even if NWS had used `documentation`, the strict server would still reject it because NWS nests it inside `properties`. NWS therefore has **two** independent bugs that compose to one error, and either one alone would have been sufficient to fail.
- All other publishers use `documentation` (correct name) but with the same wrong nesting (`in properties`).

So: the May 6 fix (renaming `documents` → `documentation`) was necessary but not sufficient. The publishers also need to lift the field out of `properties`.

---

## 7. Per-publisher rejection details (2026-05-09 run)

Captured from `/tmp/bootstrap-logs/*.log` on the Oracle host after running each publisher's idempotent bootstrap module against `/csapi-go-v2`:

| Publisher | First failing request | Rejected field | Error path |
|---|---|---|---|
| aviation-wx | POST `/procedures` | `keywords` | in `properties` |
| coops | POST `/procedures` | `keywords` | in `properties` |
| ndbc | POST `/procedures` | `keywords` | in `properties` |
| nws | POST `/procedures` | `keywords` | in `properties` |
| opensky | POST `/procedures` | `keywords` | in `properties` |
| usgs-nims | POST `/procedures` | `keywords` | in `properties` |
| usgs-water | POST `/procedures` | `keywords` | in `properties` |
| usgs-eq | POST `/procedures` | `documentation` | in `properties` |
| iss | POST `/systems` (after 2 successful procedures) | `procedure@link` | in `properties` |

Server state at end of run: 2 procedures (ISS), 0 systems, 0 datastreams, 0 deployments. The fleet's loaders are now in their normal poll loops on `/csapi-go-v2`, all logging `System '…' not found — skipping` because no system was ever registered.

---

## 8. Why USGS-EQ uses `documentation` while others use `keywords`

These two error classes look like contradictions but aren't. Each publisher's bootstrap body lists multiple offending fields; the rejection just shows whichever one the Go decoder hit first (which is alphabetical / declaration order inside `properties`). Inspection of the actual bodies shows:

- **NWS** body has both `keywords` and `documentation` inside `properties`. `keywords` happens to come first in the JSON; that's what's reported.
- **USGS-EQ** body omits `keywords` entirely (no keywords list authored) but has `documentation` — so `documentation` is reported.

The fix is identical for both classes: lift every non-CSAPI-properties field out of `properties` into the top-level Feature body.

---

## 9. Why neither prior server caught any of this

| Server | Strict parsing | Status today |
|---|---|---|
| `OS4CSAPI/connected-systems-go` (fork, frozen 2026-04-16) | No | Torn down 2026-05-09 |
| `SomethingCreativeStudios/connected-systems-go @ ~Apr 30 (pre-strict)` (was `csapi-go-head`) | No | Still running |
| `SomethingCreativeStudios/connected-systems-go @ d14d16d3 (post-strict)` (now `csapi-go-v2`) | **Yes** | New gold standard |

The fleet has 17 systems and 1 deployment loaded into the pre-strict head server. Those resources passed schema validation only because there was no validation. Spot-checking any of them via `GET /systems/<id>` will show that `keywords`, `documentation`, `contacts`, etc. are absent from the response — they were dropped at ingest, not preserved.

---

## 10. Recommended remediation

This report is informational; concrete fixes belong in their own PRs. Sketch:

1. **Fleet-wide structural fix** (single shared change, applied to all 9 publishers):
   - Update `publishers/bootstrap_helpers.py` body builders (or each publisher's `PROCEDURE_BODY` / `SYSTEM_BODY` constant) to emit SensorML / CSWA fields at the top level of the Feature object instead of inside `properties`.
   - Keep only `{uid, featureType, name, description}` inside `properties`.
   - Affected fields confirmed today: `keywords`, `documentation`, `validTime`, `contacts`. Likely also: `identifiers`, `classifiers`, `characteristics`, `capabilities`, `securityConstraints`, `legalConstraints`, `typeOf`, `inputs`, `outputs`, `parameters`, `history`. Any of these we currently emit need the same lift.

2. **ISS-specific fix** (separate PR):
   - Remove `procedure@link` from the System body in `bootstrap_iss.py`.
   - Move that link to the Datastream creation body (where the strict server actually accepts it).
   - If a System → Procedure association is desired at the System level, use `typeOf` top-level instead.

3. **Regression prevention**:
   - Add a CI job that runs each publisher's bootstrap with `--dry-run` against a strict server (e.g., `/csapi-go-v2`) and asserts HTTP 200/201 on every body it would POST/PUT. This catches placement bugs before they reach production.
   - Consider adding a JSON-schema validation step in `bootstrap_helpers.api_post` that mirrors the strict server's whitelist, so dev-time loose servers don't reintroduce the same class of bug.

4. **Data audit on `/csapi-go-head`**:
   - Decide whether the data currently loaded there is worth keeping. Because every prior load silently dropped the SensorML-rich fields, any deployed view of "metadata richness" on that server is fictional. A clean reload after the fixes is the cheapest way to a correct corpus.

---

## 11. Open questions for SWG / spec review

1. Is the Go server's whitelist (top-level SensorML fields siblings of `properties`) the canonical CSAPI Part 1 shape, or a server-specific interpretation? Reading the OGC API – Connected Systems Part 1 draft is required before declaring the publishers wrong. This report assumes the strict server is correct because (a) its struct layout matches the JSON Schema in the upstream repo, and (b) the field names match the SensorML 2.0 root vocabulary, but that should be verified against the spec text.
2. Should SensorML metadata be POSTed on the initial `/procedures` request at all, or only via a follow-up `PUT /procedures/{id}` with `Content-Type: application/sml+json`? The strict server appears to accept both, but the dual-body flow our `--force-sml` path uses may itself be redundant if the GeoJSON POST already accepts the same fields top-level.

---

## 12. Migration log artefacts

For traceability:

- New server: pinned to `SomethingCreativeStudios/connected-systems-go @ d14d16d3` (HEAD on upstream `main` as of 2026-05-09 05:34 UTC).
- Strict-parse commit: `a467aba0e413c75cde02e4c881a836207763b6ec` (2026-05-02).
- Caddy backup before route changes: `/etc/caddy/Caddyfile.bak.pre-v2-20260510-015718` on the Oracle host.
- Per-publisher bootstrap output: `/tmp/bootstrap-logs/<publisher>-go.log` on the Oracle host.
- Bootstrap summary: `/tmp/bootstrap-summary.txt` on the Oracle host.
- Two old Go stacks (`/csapi-go` from the fork, `/csapi-go-upstream` pinned to a May 5 strict commit) were torn down with `docker compose down -v` after the v2 stack came up. Their volumes are gone.
- `csapi-go-head` (pre-strict, port 8283) was not touched; it remains the only Go server with publisher-loaded data, but that data is metadata-incomplete by the analysis above.

---

## 13. TL;DR

> Eight of nine publishers nest SensorML metadata (`keywords`, `documentation`, `contacts`, etc.) inside the GeoJSON `properties` envelope. The strict CSAPI server expects them at the top level of the Feature body, alongside `properties`. The ninth publisher (ISS) additionally puts `procedure@link` on a System resource where it doesn't belong. None of these bugs were ever caught because the only servers we tested against were schema-loose. Migrating to the spec-strict upstream HEAD made the entire fleet visible as broken in one afternoon. The fixes are mechanical: relocate fields out of `properties`, and put `procedure@link` on Datastreams instead of Systems.
