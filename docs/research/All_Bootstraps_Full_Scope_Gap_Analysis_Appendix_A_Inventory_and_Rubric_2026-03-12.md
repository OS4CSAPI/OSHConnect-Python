# All Bootstraps Full-Scope Gap Analysis

## Appendix A. Inventory and Rubric

**Date:** 2026-03-12
**Scope:** current `OSHConnect-Python` bootstrap fleet, legacy `csapi-explorer` bootstrap corpus, and the adjacent artifacts required to judge bootstrap completeness and semantic maturity.

---

## A.1 Inventory Principles

This appendix treats the bootstrap corpus as one system with three layers:

1. `Current fleet`: bootstraps or bootstrap slots that belong to the active public-data publisher architecture.
2. `Legacy fleet`: older scenario, enrichment, migration, and precedent bootstraps still relevant for architectural comparison.
3. `Adjacent artifacts`: helper layers, sidecars, pack directories, and repo-level docs that materially affect bootstrap maturity even when they are not themselves primary bootstraps.

The scoring corpus is intentionally broader than "Python files named `bootstrap_*.py`". A bootstrap that cannot be understood without its sidecar, helper, pack, or runtime alignment should not be judged in isolation.

---

## A.2 Current Fleet Inventory

| Slot | Primary Path | Runtime / Adjacent Path | Pattern Family | Supporting Sidecar(s) | Artifact State | Notes |
|---|---|---|---|---|---|---|
| NWS | `publishers/nws/bootstrap_nws.py` | `publishers/nws/nws_publisher.py` | Station-per-system | `publishers/nws/stations.json` | Metadata pack present | Ten-station weather demo with historical SensorML restoration work and `--force-sml` support. |
| NDBC | `publishers/ndbc/bootstrap_ndbc.py` | `publishers/ndbc/ndbc_publisher.py`, `publishers/ndbc/ndbc_buoycam_publisher.py` | Station-per-system plus optional imagery companion stream | `publishers/ndbc/stations.json` | Metadata pack present | Five-buoy demo; strongest station-family precedent for dual datastream families. |
| CO-OPS | `publishers/coops/bootstrap_coops.py` | `publishers/coops/coops_publisher.py` | Station-per-system | `publishers/coops/stations.json` | No pack | Solid functional bootstrap with richer inline references than its artifact maturity would suggest. |
| Aviation WX | `publishers/aviation_wx/bootstrap_aviation_wx.py` | `publishers/aviation_wx/aviation_wx_publisher.py` | Station-per-system | `publishers/aviation_wx/stations.json` | No pack | Clear METAR bootstrap with a relatively thin enrichment layer compared to NWS and NDBC. |
| OpenSky | `publishers/opensky/bootstrap_opensky.py` | `publishers/opensky/opensky_publisher.py` | Pattern C feed adapter | `publishers/opensky/config.json` | Metadata pack present | First explicit non-station public-data pattern in the current fleet. |
| ISS | `publishers/iss/` bootstrap slot only | `publishers/iss/iss_publisher.py` | Intended Pattern C / dual-product publisher, but bootstrap missing | None | Missing canonical bootstrap artifact | Runtime exists in the correct repo, but `publishers/iss/bootstrap_iss.py` does not exist and `publishers/README.md` still claims it does. |
| USGS Water | `publishers/usgs_water/bootstrap_usgs_water.py` | `publishers/usgs_water/usgs_water_publisher.py` | Station-per-system with paired parameter streams | `publishers/usgs_water/stations.json` | Research note present, total pack directory missing | Stronger sidecar semantics than the older station family, but repo state does not match the prior total-pack claim. |
| USGS NIMS | `publishers/usgs_nims/bootstrap_usgs_nims.py` | `publishers/usgs_nims/usgs_nims_publisher.py` | Pattern A companion datastream | `publishers/usgs_nims/cameras.json` | Total pack present | Depends on water-station systems already existing; this dependency is central to its architecture. |
| USGS EQ | `publishers/usgs_eq/bootstrap_usgs_eq.py` | `publishers/usgs_eq/usgs_eq_publisher.py` | Pattern C feed adapter | `publishers/usgs_eq/config.json` | Total pack present | Most explicit current example of a feed-normalizer bootstrap backed by live-source verification notes. |

---

## A.3 Legacy Fleet Inventory

| Script | Path | Role Classification | Core Job | What Still Matters |
|---|---|---|---|---|
| ISS bootstrap | `scripts/bootstrap_iss.py` | Active precedent and migration candidate | Dual-product publisher bootstrap with rich SensorML and deployment hierarchy | Source pattern for `publishers/bootstrap_helpers.py`; strongest precedent for a missing current-fleet bootstrap. |
| UAS enrichment bootstrap | `scripts/bootstrap_uas.py` | Historical artifact with reusable enrichment ideas | Enrich existing systems, add datastreams, create deployment leaves | Valuable for metadata enrichment patterns and "augment existing graph" workflows. |
| Localizer bootstrap | `scripts/bootstrap_localizer.py` | Scenario-only bootstrap | Create one procedure, one system, one datastream for triangulation output | Good minimal example of a focused single-purpose bootstrap, but not a public-data publisher template. |
| v2.5 bootstrap | `scripts/bootstrap_v25.py` | Historical migration bridge | Bulk-create a doctrine-aligned scenario layer and ingest selected backup resources | Important evidence for how scenario migration pressure shaped later scripts. |
| v3.1 bootstrap | `scripts/bootstrap_v3.1.py` | Historical artifact | Inline authoritative scenario bootstrap with nested deployments and fix-up logic | Useful for deployment-hierarchy lessons, not for public-data publisher reuse. |
| v4 bootstrap | `scripts/bootstrap_v4.py` | Scenario-only authoritative bootstrap | Large-scale scenario bootstrap with systems, subsystems, datastreams, control streams, and deployments | Best evidence for what the helper layer still cannot express. |

---

## A.4 Adjacent Artifact Inventory

| Artifact | Path | Why It Matters |
|---|---|---|
| Shared helper layer | `publishers/bootstrap_helpers.py` | Canonical transport, lookup, idempotent creation, cleanup, and `--force-sml` behavior for the current fleet. |
| Publisher fleet README | `publishers/README.md` | Declares the intended fleet topology and currently contains a stale ISS bootstrap command. |
| Scenario phase bootstrap | `scripts/bootstrap_phase2.py` | Shows the specialized datastream/controlstream scenario tooling that current public-data helpers do not cover. |
| NWS metadata restoration note | `docs/research/NWS_NDBC_Hollow_SensorML_Metadata.md` | Documents a real SensorML field-shape failure mode that changed helper behavior and current bootstrap expectations. |
| Bootstrap architecture report | `docs/research/Bootstrap_Architecture_Analysis_and_Recommendations_2026-03-11.md` | Provides the earlier family classification and migration-gap framing used as background here. |
| USGS water total-pack note | `docs/research/USGS_Water_Total_Bootstrap_Data_Model_Enrichment_Pack_2026-03-11.md` | Claims a package directory that is not present in the current repo state; this mismatch is a first-class finding. |
| Existing enrichment packs | `publishers/nws/metadata_enrichment_pack`, `publishers/ndbc/metadata_enrichment_pack`, `publishers/opensky/metadata_enrichment_pack` | These determine current artifact maturity even when the live bootstrap script has not fully absorbed every proposed enrichment. |
| Existing total packs | `publishers/usgs_nims/total_bootstrap_data_model_enrichment_pack`, `publishers/usgs_eq/total_bootstrap_data_model_enrichment_pack` | These materially raise the maturity of those publishers beyond bootstrap-only status. |

---

## A.5 Pattern-Family Classification

### A.5.1 Station-per-system family

Members:

- `publishers/nws/bootstrap_nws.py`
- `publishers/ndbc/bootstrap_ndbc.py`
- `publishers/coops/bootstrap_coops.py`
- `publishers/aviation_wx/bootstrap_aviation_wx.py`
- `publishers/usgs_water/bootstrap_usgs_water.py`

Shared shape:

- one procedure for a source-specific observing method;
- one system per fixed monitoring location;
- one or more datastreams per station system;
- one root deployment, one grouping deployment, and one deployment leaf per station;
- a sidecar station list that decides demo scope.

Shared strengths:

- clear topology;
- direct source-to-system mapping;
- good fit for explorer demos;
- easy idempotent cleanup and re-bootstrap.

Shared gaps:

- duplicated script skeletons;
- little normalization of observed-property vocabularies across the family;
- limited feature-of-interest modeling;
- runtime security posture lags behind bootstrap security posture.

### A.5.2 Pattern A companion-datastream family

Member:

- `publishers/usgs_nims/bootstrap_usgs_nims.py`

Shape:

- create a new procedure and deployment subtree;
- attach one additional datastream to systems created by another publisher family;
- use a separate sidecar to describe the companion stream inventory.

Why it matters:

- it is the clearest current example of cross-publisher dependency inside the public-data fleet;
- it raises questions about canonical ownership of shared systems, deployment hierarchy boundaries, and pack completeness across coupled publishers.

### A.5.3 Pattern C feed-adapter family

Members:

- `publishers/opensky/bootstrap_opensky.py`
- `publishers/usgs_eq/bootstrap_usgs_eq.py`
- intended current ISS target model

Shape:

- one procedure describing normalization or feed adaptation;
- one feed system representing the upstream service adapter;
- one datastream whose observations each correspond to one upstream entity or event;
- a small deployment tree placing the adapter into an operational context.

Why it matters:

- this is the correct family for high-churn entities where the source is not a fixed sensor platform set;
- it gives the current fleet its first reusable alternative to station-per-system modeling.

### A.5.4 Scenario and migration family

Members:

- `scripts/bootstrap_localizer.py`
- `scripts/bootstrap_uas.py`
- `scripts/bootstrap_v25.py`
- `scripts/bootstrap_v3.1.py`
- `scripts/bootstrap_v4.py`
- adjacent: `scripts/bootstrap_phase2.py`

Shape:

- scenario graph creation, enrichment, or migration;
- deployment hierarchies deeper than the current public-data fleet;
- resource families beyond the current helper layer, including subsystems and control streams;
- stronger dependence on repo-local backups or scenario truth than on public upstream docs.

Why it matters:

- these scripts are architecturally important even when they are not current public-data publisher templates;
- they reveal the gap between the current helper layer and full connected-systems bootstrapping needs.

---

## A.6 Scoring Scale

| Score | Meaning | Interpretation |
|---|---|---|
| 0 | Missing | The category is absent or contradicted by the current artifact state. |
| 1 | Minimal | The category exists in name only or only through indirect precedent. |
| 2 | Partial | Some correct elements are present, but important gaps materially limit accuracy, reproducibility, or confidence. |
| 3 | Adequate | The category is solid enough for current use, but not yet robust or semantically complete. |
| 4 | Strong | The category is intentionally designed, well-supported, and close to a durable target state. |
| 5 | Exemplary | The category is unusually complete, well-evidenced, and suitable as a canonical reference. |
| N/A | Not applicable | The category does not meaningfully apply to the bootstrap's role; a justification is still required. |

---

## A.7 Category Definitions

| Category | What Was Scored |
|---|---|
| Bootstrap topology clarity | Whether the script clearly declares the resource family it creates, the scope of that family, and the parent-child relationships. |
| Procedure semantics | Whether the procedure resource meaningfully explains the observing or normalization method rather than serving as a placeholder. |
| System semantics | Whether systems are modeled at the right conceptual level and described with role-appropriate semantics. |
| Datastream semantics and result-schema precision | Whether the datastream split and result schema communicate precise observed-property meaning, typing, and shape. |
| Deployment semantics and hierarchy quality | Whether deployments express an intentional operational context rather than a minimally sufficient tree. |
| Metadata richness and SensorML quality | Whether rich SensorML fields are present, well-shaped, and durable enough to survive round-trips. |
| Provenance and official-source traceability | Whether the bootstrap and its adjacent artifacts make upstream source authority explicit and auditable. |
| Field semantics, units, vocabularies, and nullability discipline | Whether result fields are named, typed, unitized, and qualified in a way that reduces semantic ambiguity. |
| Sidecar/config fidelity and source selection quality | Whether sidecars are structured, curated, and semantically aligned with the actual source model. |
| Bootstrap/runtime alignment | Whether the bootstrap's topology, stream names, and semantics match the behavior of the paired runtime publisher. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | Whether the script benefits from the shared helper model or otherwise provides reliable repeatability and safe operations. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | Whether the resource model is coherent with the major standards ideas the project is trying to express. |
| Security, portability, and environment hygiene | Whether credentials, TLS, environment handling, and repo portability are handled in a way fit for modern operational use. |
| Enrichment-pack or total-pack coverage and maturity | Whether the bootstrap has a current supporting artifact package and whether that package is actually present and usable. |
| Migration debt and canonical-home clarity | Whether the bootstrap lives in the right repo and whether contributors can tell which artifact is authoritative. |

---

## A.8 Scoring Conventions Used In The Dossiers

- `Bootstrap-focused`: scores are anchored to the bootstrap and its directly adjacent artifacts, not to the scientific quality of the upstream dataset.
- `Repo-state aware`: an artifact claimed only by a research note but absent on disk was scored as missing or inconsistent, not as present.
- `Current-state only`: scores reflect the repository state on 2026-03-12, not the intended state described in older planning documents.
- `Semantics first`: a functionally working bootstrap can still score only "adequate" if it under-specifies provenance, vocabulary, or field meaning.
- `Runtime-sensitive`: runtime behavior was considered when it directly changes confidence in the bootstrap contract, especially for bootstrap/runtime alignment and security posture.

---

## A.9 Inventory-Level Observations

1. The current fleet now spans three real public-data modeling families, not one: station-per-system, companion-datastream, and feed-adapter.
2. The helper layer is canonical for current public-data bootstraps, but it still does not cover large portions of the legacy scenario space.
3. Artifact maturity is uneven: NWS, NDBC, OpenSky, USGS NIMS, and USGS EQ have meaningful package support; CO-OPS, Aviation WX, and the current ISS slot do not; USGS water is inconsistent between note and filesystem.
4. The single largest canonical-home gap is still ISS: runtime in `OSHConnect-Python`, bootstrap precedent in `csapi-explorer`, stale README command in the current repo.
5. The single largest cross-cutting implementation gap is the split between a relatively disciplined bootstrap layer and runtime publishers that still broadly disable TLS verification.
