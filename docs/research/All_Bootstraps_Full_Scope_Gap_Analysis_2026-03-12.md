# All Bootstraps Full-Scope Gap Analysis

**Date:** 2026-03-12
**Author:** Codex (GPT-5)
**Status:** Full-scope semantics-first gap analysis
**Scope:** current `OSHConnect-Python` public-data publisher fleet, legacy `csapi-explorer` bootstrap corpus, helper-layer and artifact-state analysis, and official-source review.

---

## 1. Executive Summary

The bootstrap program is directionally strong, but it is not yet canonically complete.

The current `OSHConnect-Python` fleet is no longer a loose collection of scripts. It already expresses three distinct bootstrap families:

- station-per-system publishers for fixed monitoring locations;
- Pattern A companion-datastream publishers for additional modalities attached to existing systems;
- Pattern C feed-adapter publishers for high-churn external entities and event feeds.

That is real architectural progress. It means the project is already operating with a recognizable public-data modeling language.

At the same time, the fleet still has four major full-scope gaps:

1. **Canonical completeness is broken.** `publishers/iss/iss_publisher.py` exists, but `publishers/iss/bootstrap_iss.py` does not. `publishers/README.md` still tells users to run the missing bootstrap. The current public-data fleet therefore has a real bootstrap hole.
2. **Artifact maturity is uneven.** NWS, NDBC, OpenSky, USGS NIMS, and USGS EQ have meaningful enrichment or total-package support. CO-OPS and Aviation WX do not. USGS water has a research note claiming a total package path that is not present in the current tree.
3. **Semantic maturity is uneven.** OpenSky, USGS NIMS, and USGS EQ now read like deliberate semantic models. NWS, NDBC, CO-OPS, Aviation WX, and USGS water are functionally solid, but they still carry varying degrees of metadata, vocabulary, and packaging debt.
4. **Operational hygiene lags the bootstrap layer.** The shared bootstrap helper now uses hostname verification and required certificates, but active publisher runtimes broadly still disable TLS verification on observation POSTs.

The strongest current fleet members are:

- `publishers/opensky/bootstrap_opensky.py`
- `publishers/usgs_nims/bootstrap_usgs_nims.py`
- `publishers/usgs_eq/bootstrap_usgs_eq.py`

The strongest legacy architectural reference is still:

- `scripts/bootstrap_iss.py`

The most important universal recommendation is not to add yet another publisher first. It is to consolidate the semantic and operational gains already achieved:

- fix runtime TLS verification;
- close the ISS canonical-home gap;
- codify the bootstrap families as first-class shared patterns;
- make artifact state explicit and trustworthy;
- add round-trip conformance probes so rich metadata is verified, not merely posted.

---

## 2. Corpus and Method

This report is based on five evidence classes:

1. direct reading of every active bootstrap in `OSHConnect-Python`;
2. direct reading of every legacy bootstrap in `csapi-explorer/scripts`;
3. direct reading of paired runtimes, sidecars, helper code, current packs, total packs, and prior research notes where they materially affected bootstrap judgment;
4. official standards review for CSAPI-connected design intent, SensorML, SOSA/SSN, SWE Common, and OM concepts;
5. official upstream source review for NWS, NDBC, CO-OPS, AviationWeather, OpenSky, CelesTrak, USGS Water, USGS NIMS, and USGS Earthquake resources.

The report is intentionally `semantics first`.

That means a bootstrap was not scored highly simply because it creates resources successfully. It had to communicate the right meaning, provenance, field semantics, and artifact maturity for that success to be durable.

The full scoring rubric, inventory, and source corpus are documented in:

- `All_Bootstraps_Full_Scope_Gap_Analysis_Appendix_A_Inventory_and_Rubric_2026-03-12.md`
- `All_Bootstraps_Full_Scope_Gap_Analysis_Appendix_D_Source_Corpus_and_Roadmap_2026-03-12.md`

---

## 3. Bootstrap Family Map

| Family | Current members | Legacy / adjacent members | Why It Matters |
|---|---|---|---|
| Station-per-system | NWS, NDBC, CO-OPS, Aviation WX, USGS Water | None directly, though ISS helper extraction influenced the shared mechanics | Dominant current public-data pattern; also the main source of duplicated bootstrap structure. |
| Pattern A companion datastream | USGS NIMS | None direct | First explicit cross-publisher dependency pattern in the active fleet. |
| Pattern C feed adapter | OpenSky, USGS EQ, intended ISS target | Legacy ISS is the strongest precedent | Best fit for feeds where the upstream source is not a stable set of fixed monitoring platforms. |
| Scenario / migration / enrichment | None as primary current publishers | ISS legacy bootstrap, UAS, localizer, v2.5, v3.1, v4, phase2 | Shows what the current helper layer still does not cover and what should not be confused with the public-data fleet. |

Two conclusions follow from this map:

1. The project should stop behaving as if "bootstrap" is one undifferentiated class of script.
2. The current helper layer is strong for public-data publishers, but it is not yet a general connected-systems bootstrap framework.

---

## 4. Fleet-Wide Heatmap Summary

### 4.1 Current fleet

| Bootstrap slot | Topology / model | Metadata | Provenance | Ops hygiene | Artifact maturity | Net read |
|---|---|---|---|---|---|---|
| NWS | Strong | Adequate | Strong | Weak | Strong | Functionally solid station bootstrap with real enrichment history, but still not a final canonical package. |
| NDBC | Strong | Adequate | Strong | Weak | Strong | Strongest current station-family variant, especially because it spans buoy and imagery semantics. |
| CO-OPS | Strong | Adequate | Strong | Weak | Partial | Good bootstrap with relatively thin artifact support compared to its code quality. |
| Aviation WX | Strong | Partial | Adequate | Weak | Minimal | Clear bootstrap shape, but semantically and artifact-wise thinner than the rest of the station family. |
| OpenSky | Strong | Strong | Strong | Weak | Strong | Best current feed-adapter reference in the fleet. |
| ISS current slot | Minimal | Missing | Partial | Adequate | Missing | Runtime exists, canonical bootstrap does not. |
| USGS Water | Strong | Adequate | Strong | Weak | Minimal | Semantically stronger than its artifact maturity suggests; package-state mismatch is the main blocker. |
| USGS NIMS | Strong | Strong | Strong | Weak | Exemplary | Best current Pattern A example, though still coupled to water-bootstrap assumptions. |
| USGS EQ | Strong | Strong | Exemplary | Weak | Exemplary | Best current source-traceability story in the active fleet. |

### 4.2 Legacy fleet

| Script | Architecture value | Metadata value | Security / portability | Current role |
|---|---|---|---|---|
| `bootstrap_iss.py` | Very high | Very high | Weak | Migration candidate and active precedent |
| `bootstrap_uas.py` | Medium | High | Weak | Historical artifact with reusable enrichment ideas |
| `bootstrap_localizer.py` | Medium | Low | Weak | Scenario-only focused bootstrap |
| `bootstrap_v25.py` | High | Medium | Weak | Historical migration bridge |
| `bootstrap_v3.1.py` | Medium | Low | Weak | Historical artifact |
| `bootstrap_v4.py` | Very high | Low | Weak | Scenario-only authoritative bootstrap |

The heatmap has one dominant pattern:

- `Semantics and provenance are improving faster than artifact trust and runtime hygiene.`

That is a good sign for architecture, but it is also a risk. The repo can appear more mature than it is if a reader confuses strong research notes or pack prose with actually present, canonical, on-disk artifacts.

---

## 5. Current-Fleet Findings

### 5.1 The station family is mature enough to standardize

NWS, NDBC, CO-OPS, Aviation WX, and USGS water all repeat the same operational skeleton:

- load a sidecar station list;
- build one procedure;
- build one system per station;
- build one or more datastreams per station;
- build a root deployment, a grouping deployment, and one leaf per station;
- support `--clean`, `--clean-only`, and `--dry-run`;
- rely on `publishers/bootstrap_helpers.py`.

This repetition is no longer accidental. It is a stable family. The project should treat it as such and extract a family-level builder instead of continuing copy-edit maintenance across five scripts.

### 5.2 The best current semantic designs are not the oldest ones

The most semantically deliberate current bootstraps are not the oldest public-data scripts. They are the ones backed by stronger recent artifact work:

- OpenSky for Pattern C feed adaptation;
- USGS NIMS for Pattern A companion-datastream modeling;
- USGS EQ for source-verified event-feed modeling.

These are important because they show that the repo is now capable of more than "one station, one datastream, one leaf deployment" thinking.

### 5.3 Artifact coverage is now a maturity discriminator

Two bootstraps with similar code quality can now differ materially in overall maturity depending on their adjacent artifacts.

Examples:

- CO-OPS has better inline provenance than its artifact state implies, but no pack.
- Aviation WX is structurally clear, but thin in both metadata and artifact depth.
- USGS water has good sidecar semantics, but its claimed total package is not actually present on disk.
- USGS NIMS and USGS EQ both benefit materially from total-package support that already exists and is inspectable.

Artifact maturity is now part of the implementation, not just documentation.

### 5.4 ISS remains the active fleet's largest contradiction

The current repo clearly intends ISS to be part of the publisher fleet:

- `publishers/iss/iss_publisher.py` exists;
- `publishers/iss/Dockerfile` exists;
- `publishers/docker-compose.yml` includes an ISS service;
- `publishers/README.md` still includes `python -m publishers.iss.bootstrap_iss`.

But the bootstrap itself is still missing.

This means the fleet cannot honestly claim full bootstrap coverage until ISS is migrated into `OSHConnect-Python`.

### 5.5 Runtime security posture is weaker than bootstrap security posture

This is the most operationally important current-fleet finding.

The helper layer uses certificate verification and hostname checks. The runtimes do not consistently inherit that discipline. Across the active runtime publishers, TLS verification is commonly disabled for outbound CSAPI POST operations.

This creates an avoidable architecture split:

- bootstrapping is relatively disciplined;
- continuous publishing is comparatively permissive.

That split should not survive into a canonical fleet.

---

## 6. Legacy-Fleet Findings

### 6.1 Legacy does not mean obsolete

Several legacy scripts still matter because they solve problems the current fleet either inherited from them or has not yet re-solved in a better way.

The best example is `scripts/bootstrap_iss.py`:

- it is still the strongest rich-SensorML publisher bootstrap precedent in the corpus;
- it is explicitly the source pattern for `publishers/bootstrap_helpers.py`;
- it models a dual-product publisher with a meaningful deployment tree;
- it already solves the missing current-fleet ISS bootstrap problem in concept.

### 6.2 The scenario scripts reveal the helper layer's boundary

`bootstrap_v4.py`, `bootstrap_v25.py`, and `bootstrap_phase2.py` show that the current helper layer is not yet a general bootstrap framework. It does not directly cover:

- subsystems;
- control streams;
- scenario graph import;
- complex deployment repair or migration logic;
- schema rewrites during migration.

This is not a criticism of the current helper layer. It is a boundary condition. The project should decide whether to keep that boundary or expand beyond it intentionally.

### 6.3 Legacy security and portability are still poor

The legacy scripts continue to expose patterns that should not be propagated:

- hardcoded production endpoints;
- embedded credentials;
- TLS verification disabled;
- server- and ID-specific assumptions inline in the script body.

These scripts are historically informative, but they should not be treated as drop-in current templates.

### 6.4 The scenario bootstraps are valuable mainly as references, not destinations

The right move for most of the legacy scenario corpus is not migration into the publisher repo. It is clearer separation:

- keep the useful ideas;
- keep the backup truth sources where they still matter;
- stop treating these scripts as peers of the public-data fleet in day-to-day contributor workflows.

---

## 7. Cross-Cutting Gap Taxonomy

### 7.1 Semantic-model gaps

- several station-family datastreams still flatten multiple observed-property concepts into one broad record without an explicit semantic contract for null reasons, QC, or per-field provenance;
- fixed-station publishers rarely model feature-of-interest semantics beyond the station system itself;
- Pattern A and Pattern C are present in code but not yet normalized as canonical vocabulary inside the project.

### 7.2 Metadata and SensorML gaps

- metadata richness is uneven across the active fleet;
- NWS/NDBC history shows that writing SensorML is not the same as preserving rich SensorML through server round-trips;
- some packs are mature enough to be relied on, but others are absent or only claimed by research notes.

### 7.3 Provenance and traceability gaps

- provenance quality varies widely by publisher;
- some bootstraps now embed substantial official-source references;
- others remain dependent on minimal inline URL sets or planning-note context;
- repo/documentation drift can now make provenance look stronger than the artifact state actually is.

### 7.4 Operational and security gaps

- active runtime TLS verification remains the biggest fleet-wide hygiene issue;
- station-family duplication makes operational improvements expensive to roll out uniformly;
- conformance verification is still too manual.

### 7.5 Repo-boundary and canonical-home gaps

- ISS bootstrap split across repos;
- scenario and public-data artifacts still share mental and physical neighborhoods that blur contributor expectations;
- research-note claims are not always synchronized with on-disk artifact reality.

---

## 8. Prioritized Recommendations By Tier

### 8.1 Tier 1: universal high-priority gaps

1. Restore TLS verification across active runtimes.
   Type: `runtime-follow-on`

2. Codify the bootstrap families as first-class shared patterns.
   Type: `bootstrap-only`

3. Publish and enforce an artifact-state taxonomy for packs, total packs, historical source bases, and research notes.
   Type: `archive/clarify`

4. Standardize provenance manifests and semantic-contract sidecars for every active publisher.
   Type: `metadata-only`

5. Add automated round-trip conformance probes for SensorML and result-schema retrieval.
   Type: `runtime-follow-on`

6. Close the ISS canonical-home gap.
   Type: `migration`

### 8.2 Tier 2: publisher-family gaps

1. Extract the station-per-system family builder.
   Type: `bootstrap-only`

2. Define a canonical Pattern C feed-adapter contract.
   Type: `metadata-only`

3. Define a canonical Pattern A dependency contract for companion datastreams.
   Type: `bootstrap-only`

4. Separate scenario-only bootstraps from public-data publisher workflows.
   Type: `archive/clarify`

### 8.3 Tier 3: per-bootstrap target-state work

1. NWS and NDBC: integrate the mature parts of their enrichment work into a verified, canonical runtime-plus-bootstrap state.
   Type: `runtime-follow-on`

2. CO-OPS and Aviation WX: bring them to pack parity with the better-supported publishers.
   Type: `metadata-only`

3. OpenSky: keep the current model but harden runtime behavior and quality semantics.
   Type: `runtime-follow-on`

4. USGS water: reconcile the missing total-pack directory and elevate the statistic-specific semantic contract into a canonical package.
   Type: `total-pack`

5. USGS NIMS and USGS EQ: extend the already-strong packages into clearer next-stage runtime and semantic guidance.
   Type: `runtime-follow-on`

### 8.4 Tier 4: legacy migration or archival cleanup

1. Migrate legacy ISS bootstrap into the current publisher repo.
   Type: `migration`

2. Archive or clearly label UAS, localizer, v2.5, v3.1, v4, and phase2 as scenario-specific or historical.
   Type: `archive/clarify`

3. Preserve reusable ideas from the legacy scenario family without preserving insecure transport and credential patterns.
   Type: `archive/clarify`

---

## 9. Decision Log and Assumptions

1. The report scores the current repository state, not the intended state described in older planning notes.
2. A claimed artifact that is absent from the current filesystem was treated as missing.
3. Runtime behavior was included only where it materially affected bootstrap confidence, especially for security and bootstrap/runtime alignment.
4. Legacy scenario scripts were treated as architecturally relevant even when they are not current publisher targets.
5. Standards-conformance scores are design-intent maturity judgments, not formal certification claims.
6. The report assumes the project goal is to maximize semantic clarity and reproducible richness, not merely to achieve minimal demo functionality.

---

## 10. Appendix Map

- `All_Bootstraps_Full_Scope_Gap_Analysis_Appendix_A_Inventory_and_Rubric_2026-03-12.md`
- `All_Bootstraps_Full_Scope_Gap_Analysis_Appendix_B_Current_Fleet_Dossiers_2026-03-12.md`
- `All_Bootstraps_Full_Scope_Gap_Analysis_Appendix_C_Legacy_Fleet_Dossiers_2026-03-12.md`
- `All_Bootstraps_Full_Scope_Gap_Analysis_Appendix_D_Source_Corpus_and_Roadmap_2026-03-12.md`

The appendices contain the per-bootstrap evidence tables, category scores, score justifications, and source corpus details that support the summary conclusions above.
