# Phase 5 — Multi-Server Publisher Plan

**Status:** Proposed
**Date:** 2026-05-09
**Author:** OS4CSAPI / Sam Bolling
**Predecessors:** Phase 1 (Bootstrap), Phase 2 (Datastreams + ControlStreams), Phase 3 (Simulator route redesign), Phase 4 (NDJSON Replay Engine)
**Successors:** TBD — to be defined at Phase 5 close

---

## 1. Objective

Make the OSHConnect-Python publisher fleet usable against **any** CSAPI server we encounter — not just OpenSensorHub. Today the fleet hard-codes OSH conventions (Basic auth, GeoJSON `Feature` envelope, OM-JSON observations, `controlstreams` lowercase path, etc.) and partially adapts to the Go server through ad-hoc patches scattered across `publishers/bootstrap_helpers.py`. With the Phase 9 deployment of the live 52°North `connected-systems-pygeoapi` server, we now have **three** distinct CSAPI implementations the fleet should be able to publish to, plus the existing OSH and Go targets. This phase replaces ad-hoc per-server patching with a documented, profile-driven abstraction.

This is *not* an attempt to upstream changes to the original `Botts-Innovative-Research/OSHConnect-Python` library. As of Phase 5 the OS4CSAPI fork is a standalone project: a CSAPI client *library* plus a CSAPI *publisher fleet* that we own end-to-end.

---

## 2. Background and Provenance

This plan synthesizes findings from:

- **OSHConnect-Python issue #5** (open, P1): `ensure_procedure` / `ensure_deployment` silently lose all SensorML metadata; POSTs use the wrong content-type and payload shape.
- **OSHConnect-Python issue #4** (open): bootstrap idempotency `find_by_uid` reads only the first page; same single-page pattern repeated in `find_datastream` and `_discover_system_ds`; `limit=1000` is a fragile workaround.
- **`docs/research/Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md`** — the engineering report behind #5.
- **`docs/research/CSAPI_Go_Server_Integration_Report_2026-04-17.md`** — the per-server-quirk catalog accumulated during the Go server migration.
- **`docs/research/Publisher_Fleet_Portability_Plan.md`** — earlier planning that named portability as a goal but pre-dated the Go and pygeoapi servers.
- **External:** `ogc-client-CSAPI_2/docs/research/phase-9/03-52north-pygeoapi-deployment-findings.md` — Phase 9 deployment of `52North/connected-systems-pygeoapi` on Oracle Cloud, including the documented publisher-integration blocker (§8 of that report).
- **External:** `ogc-csapi-explorer/docs/governance/known-server-quirks.md` — the authoritative three-server quirks matrix (OSH, csa.demo.52north.org, pygeoapi-live), validated via the explorer's CRUD Smoke Test.

The Phase 9 deployment doc explicitly recommended:

> *"Instead of adapting the Go publisher, write a thin Python publisher that consumes the same OS4CSAPI event stream and emits pygeoapi-shaped payloads directly. The seeder already implements ~80% of that translation."*

Phase 5 makes that "thin Python publisher" a first-class capability of *this* repo rather than a separate one-off.

---

## 3. Target Server Matrix

| # | Server                        | Base URL                                                  | Auth   | Status        |
| - | ----------------------------- | --------------------------------------------------------- | ------ | ------------- |
| 1 | OpenSensorHub (OSH)           | `http://45.55.99.236:8080/sensorhub/api`                  | Basic  | Production target — current default |
| 2 | OS4CSAPI Go server            | `https://129-80-248-53.sslip.io/csapi-go`                 | None   | Production target — partially supported via in-line patches |
| 3 | 52°North pygeoapi (live)      | `https://129-80-248-53.sslip.io/csapi-pygeoapi`           | None   | New in Phase 9 — **not yet a publisher target** (blocker documented) |
| 4 | csa.demo.52north.org (public) | `https://csa.demo.52north.org`                            | None   | Read-only target — used for content-negotiation regression testing only |

Phase 5 success criteria are defined against servers 1, 2, and 3.

---

## 4. Problem Statement (per-server divergence the fleet currently can't handle)

Each row is a real, captured observation from the explorer's CRUD Smoke Test or from `seed_pygeoapi.py`:

| Concern                  | OSH                                                         | Go server                                       | pygeoapi (Phase 9)                                                                |
| ------------------------ | ----------------------------------------------------------- | ----------------------------------------------- | --------------------------------------------------------------------------------- |
| `POST /systems` shape    | CSAPI GeoJSON `Feature` (`type:"Feature"`, `properties{}`)  | CSAPI GeoJSON `Feature`                         | **Stripped JSON; no `Feature` envelope** — `Feature` triggers `AttrDict.get` crash |
| `POST /procedures` shape | CSAPI GeoJSON `Feature`                                     | CSAPI GeoJSON `Feature`                         | **SensorML JSON only** — `{ type, id, definition, ... }`                          |
| `POST /deployments` shape| CSAPI GeoJSON `Feature`                                     | CSAPI GeoJSON `Feature`                         | **SensorML JSON only**, and `deployedSystems` field causes server `KeyError`      |
| `POST /samplingFeatures` | accepted                                                    | accepted                                        | **405 Method Not Allowed** (read-only on this build)                              |
| `controlstreams` path    | **lowercase only** (`/controlstreams`)                      | camelCase (`/controlStreams`)                   | absent (not implemented)                                                          |
| `commands` endpoint      | only via `/controlstreams/{id}/commands`                    | top-level `/commands`                           | absent                                                                            |
| Pagination               | `limit=1000` workaround currently masks `next`-link bugs    | same                                            | `next` link present, must be followed                                             |
| Auth                     | Basic auth required                                         | none                                            | none                                                                              |
| `Accept` header behavior | **ignored** — must use `?f=` query parameter                | honored                                         | honored, but `Accept: application/json` returns CSAPI envelope; smljson/geojson route through alternate stores |
| Conformance advertised   | 20+ CSAPI classes                                           | partial CSAPI classes                           | only `ogcapi-common-1/1.0/conf/core` — no CSAPI classes despite working endpoints |
| SensorML round-trip      | accepts smljson on PUT but lossy on POST (issue #5 root)    | unverified                                      | required form for POSTs to systems/procedures/deployments                         |

The publisher fleet currently encodes a single, OSH-shaped path through this matrix. Every server quirk the team has hit so far has resulted in either an in-line `if`-branch in `bootstrap_helpers.py` or a workaround like `limit=1000`. This does not scale to a third target and is the structural reason Phase 9's publisher integration was abandoned.

---

## 5. Proposed Architecture

### 5.1 ServerProfile (new module)

A `ServerProfile` is a versioned, declarative description of *one* CSAPI server's quirks. The publisher fleet consumes a profile through the existing `Node` abstraction; there are no per-publisher conditionals.

**Proposed location:** `src/oshconnect/profiles/`.

**Proposed shape (sketch, not final API):**

```python
@dataclass(frozen=True)
class ServerProfile:
    name: str                                       # "osh" | "csapi-go" | "pygeoapi-live" | ...
    base_url_pattern: str                           # for matching/auto-detection
    auth: AuthStrategy                              # BasicAuth | NoAuth | BearerToken | ApiKey
    endpoints: EndpointMap                          # canonical kind -> path (handles /controlstreams casing)
    content_negotiation: ContentNegotiation         # Accept-honored vs ?f= override
    payload_shapes: PayloadShapeMap                 # per-resource POST/PUT body shape
    pagination: PaginationStrategy                  # next-link walker | limit=1000 | offset
    conformance_required: list[str]                 # used to fail-fast on unfit targets
    known_quirks: list[str]                         # human-readable; logged on connect
```

Three profiles ship with Phase 5: `osh`, `csapi-go`, `pygeoapi-live`. They are loaded by name from a YAML registry (stretch goal: share the registry with `ogc-csapi-explorer/docs/governance/known-server-quirks.md` so quirks are single-sourced).

### 5.2 Node opens with a profile and probes /conformance

On `Node.connect()` the client:

1. GETs `/` and `/conformance`.
2. Compares the advertised conformance classes to the profile's `conformance_required`.
3. Logs a single "server profile loaded" line listing the active quirks.
4. If a required class is absent, raises `ConformanceError` *before* the first publish — Phase 9's pygeoapi blocker would have surfaced here on connect rather than after four failed payload-rewrite attempts.

### 5.3 PayloadShape adapters

Three concrete adapters cover today's matrix:

- `CSAPIFeatureShape` — current OSH/Go default.
- `SensorMLJSONShape` — pygeoapi's required form for `/systems`, `/procedures`, `/deployments`.
- `StrippedJSONShape` — pygeoapi's `/systems` workaround for the `AttrDict` crash.

`bootstrap_helpers.py` calls `node.profile.shape_for("procedures").build(model)` instead of inlining the body. The existing SensorML round-trip work on the `fix/sml-content-type-and-shape` branch becomes the Pydantic v2 *source* model that the adapters serialize from — fixing #5 by construction rather than by patching the existing code path.

### 5.4 Pagination iterator

A single `paginate(node, url, params=None) -> Iterator[T]` replaces every `limit=1000` call site. It honors `links: rel=next` when present and falls back to offset-paging when absent. Closes #4 across `find_by_uid`, `find_datastream`, `_discover_system_ds`, and the `bootstrap_helpers` siblings.

### 5.5 HTTP resilience layer

`HTTPHelper` is wrapped (or replaced) with a layer that adds:

- per-request timeout (configurable, default 30s).
- `tenacity`-style retry on 429/503/connection errors with exponential backoff.
- bounded concurrency (Phase 4 replay engine already needs this; today it's ad-hoc).
- a typed exception hierarchy: `CSAPIError → ServerProfileError | ConformanceError | PayloadShapeError | RateLimitError | TransportError`.

### 5.6 Full PUT and DELETE coverage

Phase 5 closes the CRUD matrix for the resource types the fleet actively uses. Per the OS4CSAPI library audit (`ogc-client-CSAPI_2/docs/research/requirements/csapi-oshconnect-python-analysis.md` §3.3) the original library implements only CREATE+READ for most resources. Reconciliation (delete-and-republish) is currently impossible without falling back to raw HTTP, and that's the actual workflow when a publisher's source data corrects itself.

### 5.7 Smoke-test parity with the explorer

Add `python -m oshconnect.smoke_test --profile <name>` that runs the same CRUD matrix the explorer's Smoke Test page runs. Reuses `ServerProfile` and `PayloadShape`, and emits a result table identical in structure to the explorer's, so a publisher engineer and a UI engineer are reading the same dashboard when they ask "is this server fit to publish to?"

---

## 6. Scope

### In scope

- New `oshconnect.profiles` module with `osh`, `csapi-go`, `pygeoapi-live` profiles.
- Conformance probe on connect.
- PayloadShape adapters covering the three target servers.
- Pagination iterator (closes #4).
- SensorML Pydantic v2 models + round-trip POST (closes #5, supersedes the in-flight `fix/sml-content-type-and-shape` branch).
- HTTP resilience layer with typed exceptions.
- PUT and DELETE for `systems`, `procedures`, `deployments`, `datastreams`, `controlstreams`, `samplingFeatures` — guarded by the active profile (not all servers support all paths).
- `oshconnect.smoke_test` CLI parity with the explorer.
- One existing publisher (`USGS_Water` is the smallest with full bootstrap coverage) ported end-to-end onto the profile abstraction as the reference port.

### Out of scope

- Reworking the Phase 4 NDJSON Replay Engine — it consumes the new resilience layer, but its architecture is unchanged.
- Streaming (WebSocket / MQTT) auth strategies — Basic only is fine for Phase 5; bearer/OAuth is a Phase 6 concern.
- Upstreaming any of this to `Botts-Innovative-Research/OSHConnect-Python`. The fork is a standalone project.
- A pygeoapi-side fix for the `AttrDict` crash, the `samplingFeatures` 405, or the missing CSAPI conformance classes — those are upstream-server bugs, tracked in `52North/connected-systems-pygeoapi` and the Phase 9 deployment doc.
- Sharing the YAML quirks registry with the explorer in this phase — listed as a stretch goal in §5.1.

---

## 7. Deliverables

1. `src/oshconnect/profiles/{__init__.py, base.py, osh.py, csapi_go.py, pygeoapi_live.py, registry.yaml}`.
2. `src/oshconnect/payload_shapes/{__init__.py, csapi_feature.py, sensorml_json.py, stripped_json.py}`.
3. `src/oshconnect/pagination.py` — single `paginate()` iterator.
4. `src/oshconnect/http/{client.py, retry.py, exceptions.py}` — replaces / wraps `HTTPHelper`.
5. `src/oshconnect/sensorml/` — Pydantic v2 models for SystemSML, ProcedureSML, DeploymentSML; lossless round-trip tests against the seed data captured in `ogc-client-CSAPI_2/docs/research/phase-9/captures/oracle-pygeoapi/`.
6. `src/oshconnect/smoke_test.py` — CLI runner.
7. `publishers/usgs_water/` — ported as the reference profile-driven publisher; existing OSH-targeted behavior preserved by selecting `--profile osh`.
8. Tests:
   - Unit tests for each profile + payload shape (using `respx` against recorded responses).
   - Integration tests against OSH, Go, and pygeoapi-live (gated by `OSHCONNECT_LIVE=1`).
   - Round-trip SensorML fidelity tests fed by `Phase 9 captures/oracle-pygeoapi/`.
9. `docs/research/Phase5_Results_Report.md` — published at phase close, mirroring the format of `Phase1_Bootstrap_Results.md` and `Phase4_Replay_Engine_Results.md`.

---

## 8. Verification Matrix (acceptance criteria)

| # | Criterion                                                                                            | How verified |
| - | ---------------------------------------------------------------------------------------------------- | ------------ |
| 1 | `Node.connect(profile="pygeoapi-live")` succeeds and logs the active quirks                          | Live integration test |
| 2 | `usgs_water` publisher runs end-to-end against OSH, Go server, and pygeoapi-live without code change  | Three live runs, captures committed |
| 3 | `ensure_procedure` / `ensure_deployment` round-trip SensorML metadata losslessly (closes #5)         | Round-trip test against seed captures |
| 4 | All `find_by_uid`, `find_datastream`, `_discover_system_ds` call sites use `paginate()` (closes #4)  | `grep` audit + unit test on multi-page server stub |
| 5 | A publisher run that loses connectivity for 30s recovers without manual intervention                 | Toxiproxy / fault-injection test |
| 6 | `python -m oshconnect.smoke_test --profile pygeoapi-live` produces a results table comparable to the explorer's CRUD Smoke Test | Side-by-side capture |
| 7 | PUT and DELETE coverage exists for the six target resource types on at least one profile             | Unit tests + one live profile per resource |
| 8 | Removing the OSH `limit=1000` workarounds does not regress bootstrap idempotency                     | Existing bootstrap idempotency test passes |

---

## 9. Risks and Mitigations

| Risk                                                                              | Mitigation |
| --------------------------------------------------------------------------------- | ---------- |
| pygeoapi-live's quirks shift between releases (e.g. `samplingFeatures` regains POST) | Profiles are versioned; `Node.connect` re-probes `/conformance` on every run and warns on drift |
| Profile abstraction balloons into "yet another framework"                          | Hard cap: 3 profiles ship in Phase 5; no plugin loader, no DSL, no decorators. YAML registry only |
| Resilience layer hides real server bugs                                            | Retries are bounded and emit a structured warning per retry; integration tests explicitly assert `RateLimitError` / `TransportError` rather than treating all errors as transient |
| SensorML model layer drifts from real server payloads                              | Round-trip tests are seeded *from* live captures, not from hand-written fixtures |
| Reference port (`usgs_water`) succeeds but other publishers reveal hidden OSH-isms | After the reference port lands, run all 9 publishers in `--profile osh` mode against staging OSH; treat any difference from baseline as a bug |

---

## 10. Sequencing

A suggested sequence; adjust as discovered:

1. **5.1** — `ServerProfile` skeleton, three profiles, `/conformance` probe, exception hierarchy. No payload changes yet.
2. **5.2** — Pagination iterator + retire `limit=1000` workarounds (closes #4 mid-phase).
3. **5.3** — PayloadShape adapters + SensorML Pydantic models + round-trip tests (closes #5 by construction; supersedes `fix/sml-content-type-and-shape` branch).
4. **5.4** — HTTP resilience layer + typed exceptions.
5. **5.5** — PUT/DELETE coverage.
6. **5.6** — `oshconnect.smoke_test` CLI.
7. **5.7** — Reference port: `usgs_water` driven by profile; then full-fleet `--profile osh` regression run.
8. **5.8** — First successful `usgs_water` run against `pygeoapi-live` (Phase 5 acceptance gate).

---

## 11. What Phase 5 explicitly does *not* attempt

- It does **not** introduce a streaming auth refactor (OAuth2 / API-Key).
- It does **not** change the Phase 4 replay engine's architecture.
- It does **not** try to patch the live pygeoapi server. Its 405/AttrDict/`deployedSystems`-KeyError quirks are accepted as facts of life and encoded in the `pygeoapi-live` profile.
- It does **not** introduce a plugin system. Profiles are concrete classes plus a YAML file. Adding a fourth profile in a future phase is a code change.
- It does **not** depend on the TypeScript explorer or the `ogc-client-CSAPI_2` library at runtime. Cross-references in §2 are *informational only*; this repo remains a standalone Python project.

---

## 12. Open Questions

1. Should the YAML profile registry be vendored into this repo, or pulled at install time from `ogc-csapi-explorer/docs/governance/known-server-quirks.md`? Phase 5 vendors. Phase 6 may reconsider.
2. Do we want a single `Node` per profile, or should a `Node` accept profile *overrides* per call (e.g. forcing `Accept: application/sml+json` for one query)? Phase 5 ships per-Node only; per-call overrides are deferred.
3. Where does the OSH-specific `?f=` query rewriter live — in the profile, or in `HTTPHelper`? Leaning toward profile, because it's a quirk fact, not a transport fact.
4. The `fix/sml-content-type-and-shape` branch contains a partial fix to issue #5. Should it be merged before Phase 5 starts, or absorbed into 5.3? Recommend absorbing — the Pydantic model layer is a more durable fix than the patch series on that branch.
