# Bootstrap Architecture Analysis and Recommendations

**Date:** 2026-03-11  
**Author:** Codex (GPT-5)  
**Status:** Analysis and recommendations  
**Scope:** Compare legacy bootstrap scripts in `ogc-csapi-explorer` with current bootstrap scripts in `OSHConnect-Python`, assess the current migration state, and recommend a durable target architecture.

---

## 1. Executive Summary

The migration from ad hoc bootstrap scripts in `ogc-csapi-explorer` to publisher-focused bootstraps in `OSHConnect-Python` is directionally correct and already producing real benefits. The extraction of the ISS bootstrap pattern into `publishers/bootstrap_helpers.py` is the key architectural improvement: it turns a proven one-off script into a reusable bootstrap substrate for public data source publishers.

The current `OSHConnect-Python` publisher bootstraps are noticeably better aligned with the repo's purpose than the older scenario-heavy scripts:

- `publishers/nws/bootstrap_nws.py`
- `publishers/ndbc/bootstrap_ndbc.py`
- `publishers/coops/bootstrap_coops.py`
- `publishers/aviation_wx/bootstrap_aviation_wx.py`
- `publishers/opensky/bootstrap_opensky.py`

They are more consistent, more idempotent, easier to reason about, and more explicit about metadata quality and operational behaviors (`--clean`, `--clean-only`, `--dry-run`, `--force-sml`).

However, the migration is incomplete. The main architectural gaps are:

1. The public-data bootstraps now share a common helper layer, but the four station-oriented publishers still duplicate nearly the same script skeleton.
2. The helper layer only covers procedures, systems, datastreams, and deployments. It does not cover subsystems, control streams, sampling features, deployed-system links, or the schema-normalization quirks needed by scenario bootstraps.
3. The repository still contains stale or historical "enrichment pack" artifacts that materially diverge from the live runtime bootstraps and can confuse future contributors.
4. Both repos still encode production-specific endpoint assumptions, credentials, and host/IP workarounds directly in source.
5. The repo boundary is still blurred: the ISS runtime moved into `OSHConnect-Python`, but the ISS bootstrap remains in `ogc-csapi-explorer`; scenario-specific bootstraps remain mixed alongside general publisher work.

The highest-value recommendations are:

- remove embedded credentials and production defaults from source;
- port the ISS bootstrap into `OSHConnect-Python`;
- either archive or clearly label the NWS/NDBC enrichment-pack artifacts as historical;
- factor the station-per-system publisher bootstraps into a more declarative shared layer;
- explicitly decide whether `OSHConnect-Python` is only a publisher demo repo, or the canonical bootstrap toolkit for all CSAPI resource families.

---

## 2. Corpus Reviewed

### 2.1 Current `OSHConnect-Python` bootstrap layer

- `publishers/bootstrap_helpers.py`
- `publishers/nws/bootstrap_nws.py`
- `publishers/ndbc/bootstrap_ndbc.py`
- `publishers/coops/bootstrap_coops.py`
- `publishers/aviation_wx/bootstrap_aviation_wx.py`
- `publishers/opensky/bootstrap_opensky.py`
- `scripts/bootstrap_phase2.py`

### 2.2 Historical and legacy bootstraps in `ogc-csapi-explorer`

- `scripts/bootstrap_iss.py`
- `scripts/bootstrap_uas.py`
- `scripts/bootstrap_localizer.py`
- `scripts/bootstrap_v25.py`
- `scripts/bootstrap_v3.1.py`
- `scripts/bootstrap_v4.py`

### 2.3 Existing research context in `OSHConnect-Python/docs/research`

- `Public_Data_Source_Publishers_Plan.md`
- `ISS_Publisher_Refactor_Plan.md`
- `NWS_NDBC_Hollow_SensorML_Metadata.md`
- `Phase1_Bootstrap_Results.md`
- `Localizer_Datastream_Deletion_Incident_2026-03-10.md`

### 2.4 Method

This analysis is based on:

- direct code reading of the scripts above;
- comparison of function structure and line counts;
- comparison of helper extraction vs duplicated legacy transport logic;
- inspection of git history in `OSHConnect-Python` for recent bootstrap-related changes;
- direct comparison of live runtime bootstraps against retained enrichment-pack artifacts.

---

## 3. Quick Size and Scope Comparison

### 3.1 Current `OSHConnect-Python` files

| File | Lines | Notes |
|---|---:|---|
| `publishers/bootstrap_helpers.py` | 333 | Shared transport, lookup, idempotent creation, cleanup, CLI args |
| `publishers/nws/bootstrap_nws.py` | 499 | 10-station NWS weather bootstrap |
| `publishers/ndbc/bootstrap_ndbc.py` | 713 | 5-buoy NDBC bootstrap with BuoyCAM support |
| `publishers/coops/bootstrap_coops.py` | 700 | 5-station coastal bootstrap with rich metadata |
| `publishers/aviation_wx/bootstrap_aviation_wx.py` | 503 | 5-airport METAR bootstrap |
| `publishers/opensky/bootstrap_opensky.py` | 422 | Single feed-adapter bootstrap |
| `scripts/bootstrap_phase2.py` | 342 | Scenario-oriented datastream/controlstream bootstrap |

### 3.2 Legacy `ogc-csapi-explorer` files

| File | Lines | Notes |
|---|---:|---|
| `scripts/bootstrap_localizer.py` | 382 | Small, direct single-purpose bootstrap |
| `scripts/bootstrap_iss.py` | 1024 | First mature publisher-style bootstrap; clear source of the helper pattern |
| `scripts/bootstrap_uas.py` | 1028 | Enrichment-oriented script over an existing scenario |
| `scripts/bootstrap_v25.py` | 960 | Migration/bootstrap script for scenario evolution |
| `scripts/bootstrap_v3.1.py` | 614 | Scenario hierarchy bootstrap with corrective logic |
| `scripts/bootstrap_v4.py` | 1401 | Full scenario-state authoritative bootstrap |

### 3.3 Interpretation

The public-data migration has reduced conceptual complexity even where individual scripts remain non-trivial. The important change is not simply fewer lines; it is the extraction of repeated concerns into a shared helper and the narrowing of each bootstrap to one data-source pattern.

At the same time, the current public-data bootstraps still repeat enough structure that another extraction step is justified.

---

## 4. Bootstrap Family Classification

The scripts naturally fall into four different families. Treating them all as the same kind of "bootstrap" obscures important differences.

| Family | Examples | Core job | Recommended home |
|---|---|---|---|
| Lightweight bootstrap | `bootstrap_localizer.py` | Create a small number of tightly related resources | Scenario-specific tools |
| Publisher bootstrap | `bootstrap_iss.py`, `bootstrap_nws.py`, `bootstrap_ndbc.py`, `bootstrap_coops.py`, `bootstrap_aviation_wx.py`, `bootstrap_opensky.py` | Provision procedures, systems, datastreams, deployments for a running publisher | `OSHConnect-Python/publishers/` |
| Enrichment bootstrap | `bootstrap_uas.py` | Update existing systems, add new streams, add deployment leaves | Scenario-specific tools |
| Scenario pack / migration bootstrap | `bootstrap_v25.py`, `bootstrap_v3.1.py`, `bootstrap_v4.py`, `scripts/bootstrap_phase2.py` | Bulk ingest or migrate a full scenario state including specialized CSAPI resource families | `scenarios/` or `migration/` tooling, not general publisher space |

This classification matters because the current helper layer only really covers the second family.

---

## 5. What Improved Materially

### 5.1 The ISS bootstrap pattern was successfully extracted

`publishers/bootstrap_helpers.py` explicitly states that it was extracted from the proven `bootstrap_iss.py` pattern. That is accurate. The helper now centralizes the core concerns that `bootstrap_iss.py` previously handled inline:

- auth header construction;
- HTTP GET/POST/PUT/DELETE with retry;
- UID lookup caching;
- idempotent creation of procedures, systems, datastreams, and deployments;
- `clean_resource()` cleanup behavior;
- common CLI args and summary printing.

This is the single biggest architectural win in the migration.

### 5.2 Public data bootstraps now match the repo's purpose

`OSHConnect-Python` is a better home for public-source publishers than `ogc-csapi-explorer`. The current publisher bootstraps:

- live next to their runtime publishers or source data configuration;
- use station inventories from `stations.json` or source-specific config files;
- model publisher-specific resource trees rather than full scenario state;
- read as reproducible provisioning tools, not historical migration artifacts.

This is a meaningful increase in maintainability and discoverability.

### 5.3 TLS handling improved in the shared helper layer

The legacy scripts `bootstrap_iss.py`, `bootstrap_uas.py`, `bootstrap_localizer.py`, and `bootstrap_v4.py` all hardcode production credentials and use TLS settings such as:

- `check_hostname = False`
- `verify_mode = ssl.CERT_NONE`

By contrast, `publishers/bootstrap_helpers.py` uses `CERT_REQUIRED` and hostname verification. That is a clear improvement, even though other deployment-specific assumptions remain.

### 5.4 The repo is learning from incidents

The NWS/NDBC metadata incident led to a real structural improvement:

- `ensure_system()` in `publishers/bootstrap_helpers.py` gained `force_sml`;
- public-data bootstraps now surface `--force-sml`;
- the fix is documented in `NWS_NDBC_Hollow_SensorML_Metadata.md`;
- subsequent bootstraps such as CO-OPS and OpenSky appear more deliberate about rich metadata.

This is a good sign. The codebase is not static; it is absorbing operational lessons.

### 5.5 OpenSky establishes a second reusable publisher pattern

The station-based publishers all implement a "one station = one system" pattern. `publishers/opensky/bootstrap_opensky.py` introduces a useful second pattern: a single feed-adapter system that publishes a stream of external entities.

That distinction is important:

- NWS/NDBC/COOPS/AviationWeather are fixed observation platforms;
- OpenSky is a feed adapter over a changing set of aircraft;
- ISS is conceptually closer to the feed-adapter pattern than the station pattern, despite its current bootstrap living elsewhere.

This suggests the architecture is maturing toward a small set of explicit bootstrap patterns rather than one-off scripts.

---

## 6. Main Architectural Gaps

### 6.1 The station-oriented bootstraps still duplicate the same skeleton

`bootstrap_nws.py`, `bootstrap_ndbc.py`, `bootstrap_coops.py`, and `bootstrap_aviation_wx.py` all implement essentially the same control structure:

- `_load_stations()`
- `_system_uid()`
- `_deploy_uid()`
- `_system_stub()`
- `_system_sml()`
- `_datastream_schema()`
- `_deploy_root()`
- `_deploy_group()`
- `_deploy_station()`
- `clean_all()`
- `bootstrap()`
- `main()`

NDBC adds `_buoycam_datastream_schema()`, but structurally it is still the same family.

This duplication creates several costs:

- every operational improvement must be propagated to four scripts;
- metadata-shape fixes can regress in one script but not others;
- new conventions must be manually kept in sync;
- the repo still encourages copy-edit programming instead of declarative reuse.

### Recommendation

Introduce a `station_bootstrap` base layer or declarative spec, for example:

- `StationBootstrapSpec`
- source-specific UID prefixes and deployment names
- per-source procedure body builder
- per-source system SML builder
- list of datastream builders
- source link/contact metadata bundles
- optional per-station extra datastreams (for example BuoyCAM)

The goal is not to erase source differences. The goal is to move the repeated orchestration into one place so each source file only supplies its domain-specific data model.

### 6.2 The helper layer is still too narrow for full bootstrap unification

`publishers/bootstrap_helpers.py` currently supports:

- procedures
- systems
- datastreams
- deployments

It does **not** support:

- subsystems
- control streams
- properties
- sampling features
- deployed-system links
- scenario-specific link rewriting
- type-first normalization for SWE structures

This is the core reason why the scenario bootstrap family still lives outside the shared layer.

The contrast is easy to see:

- `scripts/bootstrap_phase2.py` has to implement `rewrite_links()` and `ensure_type_first()`;
- `scripts/bootstrap_v4.py` manages subsystem creation, control streams, and `deployedSystemUIDs`;
- `scripts/bootstrap_uas.py` does enrichment of existing systems and additive streams under an already-bootstrapped scenario.

### Recommendation

Make an explicit decision:

**Option A: `OSHConnect-Python` is the canonical bootstrap toolkit.**  
If so, expand the helper layer to cover more CSAPI resource families and normalize the scenario bootstraps into the same architecture.

**Option B: `OSHConnect-Python` is primarily for publisher demos and public-source integrations.**  
If so, stop pretending the scenario bootstraps are on the same path. Move them under an explicitly separate scenario/migration namespace and document them as specialized tooling.

Right now the repo is between those two states.

### 6.3 ISS is the most obvious incomplete migration

Today the runtime has been partially migrated:

- `publishers/iss/iss_publisher.py` exists in `OSHConnect-Python`
- `scripts/bootstrap_iss.py` still only exists in `ogc-csapi-explorer`

That split is undesirable because the ISS publisher is historically the source of the bootstrap helper pattern and remains one of the cleanest demonstrations of the publisher architecture.

### Recommendation

Port `scripts/bootstrap_iss.py` to:

- `publishers/iss/bootstrap_iss.py`

This would:

- complete the ISS migration;
- remove the most obvious cross-repo split-brain case;
- provide a clean "feed publisher + bootstrap" example in one directory;
- allow the helper extraction to be validated against its original source case.

### 6.4 Enrichment-pack artifacts are now a drift risk

The repository still contains:

- `publishers/nws/metadata_enrichment_pack/patches/bootstrap_nws_enriched_candidate.py`
- `publishers/nws/metadata_enrichment_pack/source_basis/bootstrap_nws_reviewed_current.py`
- `publishers/ndbc/metadata_enrichment_pack/patches/bootstrap_ndbc_metadata_enriched_candidate_snippets.py`

These are no longer aligned with the live runtime bootstraps:

- the NWS source-basis file differs materially from `publishers/nws/bootstrap_nws.py`;
- the NWS patch candidate still reflects older metadata structures;
- the NDBC candidate is a partial snippet artifact, not a full runtime source.

This is not just cosmetic drift. It creates a practical maintenance hazard:

- a contributor may open the wrong file and edit stale logic;
- a future metadata fix could be applied to an artifact instead of the live bootstrap;
- reviewers must spend time reconstructing which file is authoritative.

### Recommendation

Choose one of these cleanup paths:

1. Add a prominent header banner to each artifact saying:
   - historical artifact;
   - not the source of truth;
   - replaced by `<live file path>` at `<commit hash>`.

2. Move the artifacts under a research/archive location and keep only the explanatory docs in place.

3. If the pack has served its purpose and the explanatory report is enough, delete the artifact code entirely.

My recommendation is option 1 immediately, then option 2 or 3 after confirming no one still uses the artifact files for manual patching.

### 6.5 Production defaults and credentials remain in source

This is the most serious issue in the current codebase.

Examples:

- `publishers/bootstrap_helpers.py` defaults `BOOTSTRAP_URL`, `OSH_USER`, and `OSH_PASS` to a live deployment and a real password;
- legacy scripts hardcode the same endpoint, username, password, and Oracle IP;
- `publishers/ndbc/bootstrap_ndbc.py` hardcodes a production BuoyCAM cache base URL;
- multiple scripts globally monkeypatch DNS for `os4csapi-osh.duckdns.org`.

Even where the code is operationally convenient, this is the wrong long-term baseline.

### Risks

- credentials are committed into source control;
- scripts implicitly target production when env vars are missing;
- operational behavior is harder to reason about because the fallback is not neutral;
- the DNS monkeypatch is global process state, not a local connection override.

### Recommendation

Priority 0:

1. Remove committed default passwords from source.
2. Fail fast if required env vars are absent, or use a local ignored config file.
3. Make host/IP override opt-in rather than implicit.
4. Eliminate `CERT_NONE` from any script still considered active.
5. Move deployment-specific URLs such as BuoyCAM cache base behind configuration.

If historical scripts must remain unchanged for forensic reasons, mark them clearly as archival or insecure-by-design so they are not treated as current operational tooling.

### 6.6 SensorML authoring is still too manual

The NWS/NDBC incident showed that hand-writing deep SensorML JSON structures is error-prone. The current public-data scripts are better, but they still assemble nested SensorML bodies by hand in each source file.

That is risky because:

- the structure is verbose;
- field-shape mistakes are easy to make;
- the same contact/document/characteristic patterns are repeated with local variations;
- regressions are hard to spot by inspection.

### Recommendation

Introduce small builder helpers for common SensorML shapes:

- contact builder
- document builder
- identifier/classifier builder
- grouped characteristic builder
- grouped capability builder
- common `validTime` helper

This does not need to become a giant abstraction. Even a modest shared builder module would reduce the chance of another silent-shape regression.

### 6.7 Naming and convention drift should be normalized

There is still visible convention drift across script generations:

- `outputName` values mix styles such as `issPosition`, `locationEstimate`, `nwsSurfaceObs`, `coopsCoastalObs`, `metarObs`, and `adsbState`;
- script generations alternate between `typeOf`, `typeOf@link`, and other linkage styles;
- some scripts embed all data inline, others externalize inventories;
- valid-time conventions vary by source and generation.

None of these are individually catastrophic, but together they increase cognitive load.

### Recommendation

Write a short bootstrap conventions document or section in the repo README covering:

- `outputName` style;
- when to use station-per-system vs feed-adapter modeling;
- `typeOf` / `typeOf@link` conventions;
- metadata expectations for procedures, systems, and deployments;
- cleanup semantics and CLI expectations.

---

## 7. Legacy-Script Triage Recommendations

Not every historical bootstrap should be migrated into `publishers/`.

| Script | Recommendation | Reason |
|---|---|---|
| `scripts/bootstrap_iss.py` | Migrate into `publishers/iss/` | Runtime already moved; strongest fit for current publisher architecture |
| `scripts/bootstrap_localizer.py` | Keep out of general publisher area | Scenario-specific fusion component, not a public-source publisher |
| `scripts/bootstrap_uas.py` | Keep as scenario enrichment tooling | Depends on existing scenario systems and deployment hierarchy |
| `scripts/bootstrap_v25.py` | Archive or relocate under scenario migration tooling | Historical scenario-state migration, not a reusable publisher bootstrap |
| `scripts/bootstrap_v3.1.py` | Archive or relocate under scenario migration tooling | Same reason |
| `scripts/bootstrap_v4.py` | Keep only if still authoritative for scenario rebuilds; otherwise archive | Full-state scenario bootstrap, broader than current helper scope |
| `scripts/bootstrap_phase2.py` | Keep, but relocate under scenario tooling | Specialized datastream/controlstream loader with server-quirk normalization |

This is important because "migrate everything" is not actually the right target. The better target is "put each bootstrap in the repo and directory that matches its role."

---

## 8. Recommended Target Architecture

### 8.1 Directory and responsibility model

### Public publishers

Keep public-source publishers under:

- `publishers/<source>/bootstrap_<source>.py`
- `publishers/<source>/<source>_publisher.py`

Examples:

- `publishers/iss/bootstrap_iss.py`
- `publishers/iss/iss_publisher.py`
- `publishers/nws/bootstrap_nws.py`
- `publishers/nws/nws_publisher.py`

### Scenario and migration tooling

Move or treat separately:

- `scenarios/<scenario>/bootstrap/`
- `scenarios/<scenario>/migration/`
- or `tools/scenario_bootstrap/`

The point is to separate "publisher demos" from "scenario-state migration and repair tooling."

### Shared bootstrap support

Evolve `publishers/bootstrap_helpers.py` into one of two directions:

1. **Minimal publisher-only layer**
   - keep it focused on procedures/systems/datastreams/deployments
   - add a station bootstrap base and metadata builders

2. **General bootstrap layer**
   - add subsystem/controlstream/sampling-feature/deployed-system support
   - absorb scenario bootstrap needs into the same abstraction family

Either is viable. The current halfway state is not.

### 8.2 Pattern taxonomy to formalize

I recommend explicitly documenting three active bootstrap patterns:

### Pattern A: Station-per-system publisher

Examples:

- NWS
- NDBC
- CO-OPS
- AviationWeather

Characteristics:

- inventory file of stations
- one procedure per source family
- one system per station
- one or more datastreams per station
- 3-level deployment tree: root -> group -> station

### Pattern B: Feed-adapter publisher

Examples:

- OpenSky
- ISS (recommended after migration)

Characteristics:

- one procedure
- one adapter system
- one or a few datastreams
- simple deployment tree
- observations represent external entities or generated products rather than a fixed physical station

### Pattern C: Scenario-specific enrichment/bootstrap

Examples:

- UAS
- localizer
- Phase 2
- v3.1 / v4 scenario bootstraps

Characteristics:

- depends on prior resource state;
- may add or fix only selected resource families;
- may require server-specific transforms or repairs;
- not a general publisher bootstrap and should not be forced into that mold.

---

## 9. Prioritized Action Plan

### 9.1 Priority 0 - Security and repo hygiene

1. Remove embedded production credentials and passwords from source.
2. Replace implicit production defaults with explicit configuration requirements.
3. Mark or relocate stale enrichment-pack artifacts.
4. Document which scripts are active, historical, or archival.

### 9.2 Priority 1 - Finish the most obvious migration

1. Port `scripts/bootstrap_iss.py` to `publishers/iss/bootstrap_iss.py`.
2. Add a short note in the ISS docs that the bootstrap and runtime now live together.

### 9.3 Priority 2 - Reduce duplication in station publishers

1. Add a shared station-bootstrap base or declarative spec.
2. Add shared SensorML metadata builders.
3. Normalize conventions for `outputName`, `typeOf`, and deployment naming.

### 9.4 Priority 3 - Decide the long-term scope of bootstrap helpers

1. Either expand helper coverage to scenario resources;
2. or move scenario tooling into a clearly separate area and stop treating it as part of the same abstraction track.

### 9.5 Priority 4 - Add lightweight automated validation

Recommended test coverage:

- smoke tests for bootstrap `--dry-run`;
- tests for `_system_sml()` required shapes;
- tests for datastream schema builders;
- tests that artifact files marked historical do not drift silently without explanation.

---

## 10. Specific Recommendations by File Group

### 10.1 `publishers/bootstrap_helpers.py`

Keep and strengthen it. It is the right foundation. Recommended changes:

- remove default secrets;
- make host override explicit;
- decide whether helper scope expands beyond current resource families;
- add small reusable metadata builders nearby.

### 10.2 `publishers/nws`, `publishers/ndbc`, `publishers/coops`, `publishers/aviation_wx`

Keep these in `publishers/`, but reduce duplication:

- factor common station bootstrap orchestration;
- preserve source-specific metadata richness;
- do not let each script remain a hand-maintained near-clone forever.

### 10.3 `publishers/opensky`

Treat this as the canonical feed-adapter example. It is useful because it proves the architecture is not limited to station inventories.

### 10.4 `publishers/iss`

Complete the story by bringing the bootstrap alongside the publisher.

### 10.5 `publishers/*/metadata_enrichment_pack`

Treat these as research artifacts unless there is an active workflow that still consumes them. If they remain, mark them clearly as non-authoritative.

### 10.6 `scripts/bootstrap_phase2.py`

Either:

- expand the shared helper layer until this kind of script fits naturally,

or:

- relocate it into scenario tooling and document that it serves a different bootstrap family.

### 10.7 `ogc-csapi-explorer/scripts/bootstrap_*`

These are valuable historical sources and still encode important operational knowledge, but they should no longer be allowed to define the architectural center of gravity for publisher provisioning.

---

## 11. Bottom Line

The migration is working. The repo is clearly moving from one-off operational scripts toward a real bootstrap architecture.

The extraction of the ISS pattern into `publishers/bootstrap_helpers.py` was the right move. The public-data publishers belong in `OSHConnect-Python`, and the current NWS/NDBC/CO-OPS/AviationWeather/OpenSky bootstraps are a meaningful improvement over the historical baseline.

The next step is not "write more scripts in the current style." The next step is to remove the remaining ambiguity:

- finish the ISS migration;
- separate publisher bootstraps from scenario migration tooling;
- reduce duplicated station-bootstrap orchestration;
- remove hardcoded production assumptions;
- retire or clearly archive stale enrichment artifacts.

If those steps are taken, the bootstrap layer will become much easier to evolve, safer to operate, and clearer for future contributors.
