# All Bootstraps Full-Scope Gap Analysis

## Appendix B. Current Fleet Dossiers

**Date:** 2026-03-12
**Scope:** current `OSHConnect-Python` public-data fleet, including the current ISS runtime slot as a missing-bootstrap case.

---

## B.1 NWS

**Primary path:** `publishers/nws/bootstrap_nws.py`
**Pattern family:** Station-per-system
**Current topology summary:** one procedure, ten station systems, one weather datastream per station, and a root/group/station deployment tree driven by `publishers/nws/stations.json`.

**Current strengths**

- The topology is clear and easy to explain to a new contributor.
- The bootstrap already benefits from the shared helper layer and `--force-sml`.
- The publisher has meaningful adjacent research and metadata-pack support.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The script clearly declares a ten-station, one-system-per-station resource model. |
| Procedure semantics | 3 | The observing procedure is real and source-linked, but still broad compared with actual ASOS/AWOS variation. |
| System semantics | 3 | Station systems are appropriate, but their station-specific observing context is only partially expressed. |
| Datastream semantics and result-schema precision | 3 | The flattened surface-observation record is usable, but it still compresses many weather semantics into one stream. |
| Deployment semantics and hierarchy quality | 3 | Root, group, and station leaves are functionally correct but thin as operational context. |
| Metadata richness and SensorML quality | 3 | Metadata is materially better than a bare shell, yet still below the richer pack candidate state. |
| Provenance and official-source traceability | 4 | Official NWS and ASOS URLs are embedded in the bootstrap and reinforced by pack artifacts. |
| Field semantics, units, vocabularies, and nullability discipline | 3 | Field names and units are generally sensible, but QC, null reasons, and vocabulary discipline remain limited. |
| Sidecar/config fidelity and source selection quality | 3 | `stations.json` is curated and readable, but it is still a relatively thin station-selection sidecar. |
| Bootstrap/runtime alignment | 4 | The runtime and bootstrap both center on NWS station observations and the same system/datastream pattern. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | It fully uses the helper layer and exposes the expected bootstrap controls. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 3 | The model fits the target standards well enough, but it still reflects SensorML fragility and broad result semantics. |
| Security, portability, and environment hygiene | 2 | Bootstrap-side env handling is solid, but the paired runtime still disables TLS verification. |
| Enrichment-pack or total-pack coverage and maturity | 4 | NWS has a substantial metadata pack with reviewed source-basis material and apply guidance. |
| Migration debt and canonical-home clarity | 4 | The bootstrap lives in the correct repo, though pack-to-live-bootstrap closure is still incomplete. |

**Top semantic gaps**

- One monolithic weather datastream still carries many observed-property meanings that could be made more explicit.
- The model does not yet distinguish station platform semantics from station observation package semantics in a richer way.
- Feature-of-interest and QC semantics remain implicit.

**Top metadata gaps**

- The best NWS enrichment work still lives adjacent to, rather than fully inside, the live bootstrap.
- Per-station sidecar enrichment remains thin.
- Rich SensorML depends on careful field shape and explicit re-PUT behavior.

**Top standards/conformance gaps**

- SensorML correctness is proven to be sensitive to server-accepted field shapes.
- The result schema is adequate SWE-style structure, but not yet a rigorous semantic contract.
- Deployment nodes are more organizational than semantically expressive.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- The station-family skeleton is still duplicated rather than declarative.
- There is no automated conformance probe proving rich SML round-trip success after bootstrap.

**Recommended target state**

NWS should become the canonical station-family reference once its mature pack content, round-trip verification, and runtime hygiene are fully integrated.

**Recommended next artifact**

`runtime follow-on`

---

## B.2 NDBC

**Primary path:** `publishers/ndbc/bootstrap_ndbc.py`
**Pattern family:** Station-per-system with imagery companion datastream support
**Current topology summary:** one core buoy-observation procedure, one optional BuoyCAM procedure, five buoy systems, one buoy datastream per buoy, optional imagery datastreams, and a root/group/buoy deployment tree driven by `publishers/ndbc/stations.json`.

**Current strengths**

- It is the most ambitious current station-family bootstrap because it spans met/ocean observations and imagery.
- Provenance is strong and explicitly linked to official NOAA/NDBC sources.
- The metadata pack is mature enough to support real review and adoption work.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The per-buoy topology and optional BuoyCAM extension are explicit and easy to trace. |
| Procedure semantics | 4 | The script distinguishes buoy observation semantics from imagery semantics better than most station-family peers. |
| System semantics | 3 | Per-buoy systems are sensible, but system-level semantics are still not fully pack-grade in the live bootstrap. |
| Datastream semantics and result-schema precision | 3 | The two datastream families are meaningful, but the buoy-observation record still aggregates multiple measurement concepts broadly. |
| Deployment semantics and hierarchy quality | 3 | The hierarchy is correct and discoverable, but not semantically deep. |
| Metadata richness and SensorML quality | 3 | Metadata is stronger than a minimal bootstrap, though the richest state still lives in pack materials. |
| Provenance and official-source traceability | 4 | Official NDBC docs, station pages, history, realtime text, and BuoyCAM references are well represented. |
| Field semantics, units, vocabularies, and nullability discipline | 3 | Measurement semantics are fairly strong, but the schema does not yet read like a full semantic contract. |
| Sidecar/config fidelity and source selection quality | 3 | `stations.json` is curated and the imagery relationship is represented, but sidecar semantics remain modest. |
| Bootstrap/runtime alignment | 4 | Bootstrap and runtimes align around buoy observation and optional imagery flows. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | The script uses the shared bootstrap contract effectively. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 3 | The model is coherent with the target standards, but the live artifact set still falls short of a final canonical expression. |
| Security, portability, and environment hygiene | 2 | Runtime TLS verification remains weak despite cleaner bootstrap-side env handling. |
| Enrichment-pack or total-pack coverage and maturity | 4 | NDBC has one of the most usable metadata enrichment packs in the current repo. |
| Migration debt and canonical-home clarity | 4 | The bootstrap is in the right place, with only pack-to-live-bootstrap closure still outstanding. |

**Top semantic gaps**

- The core buoy record still compresses multiple marine met and wave semantics into one broad stream.
- The relationship between buoy observations and BuoyCAM imagery is meaningful but not yet expressed as a canonical family pattern.
- QC and null semantics remain source-informed rather than fully normalized.

**Top metadata gaps**

- The most exhaustive station metadata still lives beside the bootstrap rather than completely inside it.
- Worked enrichment examples exist for only a subset of stations.
- Asset and document richness are stronger in the pack than in the live bootstrap.

**Top standards/conformance gaps**

- The station-family SML round-trip issue remains a cautionary precedent here as well.
- Observed-property decomposition is still broader than ideal for strict semantic precision.
- Deployment semantics remain functional rather than richly contextual.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- Station-family duplication still applies.
- BuoyCAM operational dependencies, especially cache serving, are documented but not elevated into a first-class fleet pattern.

**Recommended target state**

NDBC should become the canonical "multi-stream station publisher" reference once buoy and imagery semantics are packaged and hardened together as one deliberate model.

**Recommended next artifact**

`runtime follow-on`

---

## B.3 CO-OPS

**Primary path:** `publishers/coops/bootstrap_coops.py`
**Pattern family:** Station-per-system
**Current topology summary:** one water-level procedure, five station systems, one coastal-observation datastream per station, and a root/group/station deployment tree driven by `publishers/coops/stations.json`.

**Current strengths**

- Inline provenance and official references are stronger than its artifact maturity suggests.
- The bootstrap is cleanly structured and consistent with the helper layer.
- It already exposes `--force-sml`, showing that it learned from earlier SensorML issues.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The script clearly models one system and one datastream per selected CO-OPS station. |
| Procedure semantics | 3 | The water-level procedure is meaningful, but broader coastal observation semantics remain compressed. |
| System semantics | 3 | Station systems are appropriate, though their instrumentation and product breadth are only partly expressed. |
| Datastream semantics and result-schema precision | 3 | The datastream is useful, but "coastal observation" still gathers several semantics into one broad stream. |
| Deployment semantics and hierarchy quality | 3 | The deployment tree is serviceable and readable, but sparse. |
| Metadata richness and SensorML quality | 3 | The bootstrap is richer than a minimal shell, but it does not yet have pack-level depth. |
| Provenance and official-source traceability | 4 | The script embeds a strong set of official CO-OPS references, including MDAPI and DPAPI sources. |
| Field semantics, units, vocabularies, and nullability discipline | 3 | Field naming is reasonable, but quality flags and null semantics are not yet a fully explicit contract. |
| Sidecar/config fidelity and source selection quality | 3 | The sidecar is curated and manageable, but still light as a semantic source document. |
| Bootstrap/runtime alignment | 4 | The runtime and bootstrap share the same station family model and cadence expectations. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | It follows the current helper conventions cleanly. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 3 | The mapping is coherent, though not yet unusually precise. |
| Security, portability, and environment hygiene | 2 | Runtime TLS verification still weakens the end-to-end posture. |
| Enrichment-pack or total-pack coverage and maturity | 2 | There is no dedicated pack yet, so maturity is mostly bootstrap-only. |
| Migration debt and canonical-home clarity | 4 | The artifact lives in the right home and is not split across repos. |

**Top semantic gaps**

- Water-level semantics, met semantics, and product semantics are still broader than they need to be.
- The model does not yet distinguish product families clearly enough for a "most semantically precise" target state.
- Quality and datum semantics could be made more explicit.

**Top metadata gaps**

- No dedicated metadata pack exists.
- Station-level enrichment is relatively thin compared with NWS and NDBC.
- There is no canonical worked example proving the intended rich end state.

**Top standards/conformance gaps**

- Result-schema semantics are adequate, but not deeply normalized.
- Deployment semantics remain intentionally light.
- There is no separate artifact proving strong SensorML round-trip behavior.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- The station-family code skeleton remains duplicated.
- Without a pack, contributor review has to happen directly in the bootstrap file.

**Recommended target state**

CO-OPS should evolve into a stronger coastal-observation reference with clearer product-family semantics and a dedicated enrichment package.

**Recommended next artifact**

`metadata pack`

---

## B.4 Aviation WX

**Primary path:** `publishers/aviation_wx/bootstrap_aviation_wx.py`
**Pattern family:** Station-per-system
**Current topology summary:** one METAR decoding procedure, five airport systems, one METAR datastream per airport, and a root/group/station deployment tree driven by `publishers/aviation_wx/stations.json`.

**Current strengths**

- The bootstrap is structurally clear and aligned with the rest of the current fleet.
- Official AviationWeather API documentation is directly referenced.
- The runtime and bootstrap agree on a straightforward METAR publisher model.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The one-system-per-airport topology is simple and explicit. |
| Procedure semantics | 3 | The METAR decoder procedure is legitimate, but still fairly compact in its semantic description. |
| System semantics | 3 | Airport systems are appropriate, though airport context and equipment semantics are only lightly expressed. |
| Datastream semantics and result-schema precision | 3 | The METAR observation schema is useful, but not yet especially rich in vocabulary and nullability discipline. |
| Deployment semantics and hierarchy quality | 3 | The hierarchy is straightforward and sufficient, but sparse. |
| Metadata richness and SensorML quality | 2 | Metadata is present, yet noticeably thinner than NWS, NDBC, OpenSky, or the USGS packs. |
| Provenance and official-source traceability | 3 | Official AviationWeather sources are cited, but provenance depth remains modest. |
| Field semantics, units, vocabularies, and nullability discipline | 3 | The datastream contract is adequate, though not unusually precise. |
| Sidecar/config fidelity and source selection quality | 3 | The airport sidecar is curated but not deeply annotated. |
| Bootstrap/runtime alignment | 4 | The paired runtime and bootstrap clearly target the same METAR workflow. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | It cleanly follows the current fleet bootstrap conventions. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 3 | The implementation is coherent with the target model, but not yet strong enough to act as a canonical reference. |
| Security, portability, and environment hygiene | 2 | Runtime TLS verification remains disabled. |
| Enrichment-pack or total-pack coverage and maturity | 1 | No dedicated enrichment or total package exists yet. |
| Migration debt and canonical-home clarity | 4 | The artifact is in the correct repo and conceptually clear. |

**Top semantic gaps**

- The bootstrap models METAR delivery well enough, but not the fuller airport-observation semantic space.
- Airport, station, and procedure context remain compressed.
- There is no strong vocabulary strategy for aviation-specific codes and missing values.

**Top metadata gaps**

- No pack exists.
- Inline metadata remains relatively light.
- There are no worked enrichment examples or review notes for future contributors.

**Top standards/conformance gaps**

- The result schema is adequate rather than strong.
- SensorML richness is comparatively thin.
- Deployment semantics provide placement but not a rich operational story.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- This is still another copy of the station-family skeleton.
- Artifact support is too thin for long-term semantic stewardship.

**Recommended target state**

Aviation WX should be brought up to the metadata-pack baseline so it is no longer the thinnest member of the current station family.

**Recommended next artifact**

`metadata pack`

---

## B.5 OpenSky

**Primary path:** `publishers/opensky/bootstrap_opensky.py`
**Pattern family:** Pattern C feed adapter
**Current topology summary:** one ADS-B decoding procedure, one feed-adapter system, one state-vector datastream, and a small root/feed deployment tree driven by `publishers/opensky/config.json`.

**Current strengths**

- It is the clearest current expression of the feed-adapter pattern.
- The bootstrap already incorporates enrichment-pack ideas directly in the live script.
- Provenance, coverage, and operational budget thinking are unusually explicit for the current fleet.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The script clearly explains the single-system feed-adapter model and why it exists. |
| Procedure semantics | 4 | The procedure does real normalization work and is described as such. |
| System semantics | 4 | The system is intentionally modeled as a feed adapter rather than a false physical platform. |
| Datastream semantics and result-schema precision | 4 | The state-vector datastream is explicit and well suited to the source model. |
| Deployment semantics and hierarchy quality | 3 | The root/feed deployment tree is correct, though intentionally shallow. |
| Metadata richness and SensorML quality | 4 | The bootstrap plus pack materials already read like an intentional semantic product. |
| Provenance and official-source traceability | 4 | Official OpenSky docs, state-vector docs, and auth references are embedded directly in the model. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | Field semantics are meaningfully better than in the average station-family bootstrap. |
| Sidecar/config fidelity and source selection quality | 4 | `config.json` carries a real coverage and cadence policy, not just a thin demo list. |
| Bootstrap/runtime alignment | 4 | Bootstrap and runtime both center on one feed system producing one aircraft-state stream. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | It uses the shared helper layer well while still expressing a distinct family pattern. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 4 | The feed-adapter model is conceptually strong and coherent with the standards intent. |
| Security, portability, and environment hygiene | 2 | Runtime TLS verification remains disabled, and auth-aware hardening is still a follow-on task. |
| Enrichment-pack or total-pack coverage and maturity | 4 | A substantive metadata pack exists and has already influenced the live bootstrap. |
| Migration debt and canonical-home clarity | 4 | The artifact is clearly in the right home and clearly within the current fleet. |

**Top semantic gaps**

- The current model stops at state vectors and does not yet formalize richer downstream aircraft identity or track products.
- Quality, confidence, and null semantics can still be expanded.
- Coverage semantics are good, but not yet standardized as a fleet-level Pattern C contract.

**Top metadata gaps**

- The pack is strong, but not yet a full total package.
- There is room for more explicit data lineage per field.
- The procedure/system pair could still expose stronger source-method distinctions.

**Top standards/conformance gaps**

- The implementation is strong conceptually, but there is no fleet-wide canonical Pattern C template yet.
- Deployment semantics remain intentionally thin.
- Data quality semantics are not yet expressed as formally as the result schema itself.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- Credit-budget and auth-aware runtime behavior are not yet first-class.
- The fleet does not yet provide generic feed-adapter conformance tests.

**Recommended target state**

OpenSky should serve as the canonical Pattern C reference once runtime hardening and a more formal feed-adapter contract are added.

**Recommended next artifact**

`runtime follow-on`

---

## B.6 ISS Current Slot

**Primary path:** `publishers/iss/`
**Pattern family:** Intended Pattern C / dual-product publisher, but currently a missing canonical bootstrap
**Current topology summary:** `publishers/iss/iss_publisher.py` and `publishers/iss/Dockerfile` exist, but there is no current bootstrap file and the fleet README still points to `python -m publishers.iss.bootstrap_iss`.

**Current strengths**

- The runtime is already migrated into the current repo and uses the shared publisher framework.
- The current slot has a strong legacy bootstrap precedent available for migration.
- The intended dual-product model is clearer than a blank slot; it is just not yet materialized in the current repo.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 1 | The intended topology is inferable from the legacy bootstrap and README, but not present as a current bootstrap artifact. |
| Procedure semantics | 0 | No current `publishers/iss/bootstrap_iss.py` exists to define procedures in the active repo. |
| System semantics | 0 | No current bootstrap exists to define canonical systems in the active repo. |
| Datastream semantics and result-schema precision | 0 | No active bootstrap artifact defines the ISS datastream schemas in the current repo. |
| Deployment semantics and hierarchy quality | 0 | No current deployment bootstrap exists for ISS in `OSHConnect-Python`. |
| Metadata richness and SensorML quality | 0 | The active repo has no ISS bootstrap-side SensorML artifact to score. |
| Provenance and official-source traceability | 2 | The runtime and legacy precedent clearly point to CelesTrak, but the active bootstrap artifact is missing. |
| Field semantics, units, vocabularies, and nullability discipline | 1 | The runtime implies a structured observation contract, but no active bootstrap-side schema is present. |
| Sidecar/config fidelity and source selection quality | 0 | There is no active bootstrap-side sidecar or package for ISS. |
| Bootstrap/runtime alignment | 1 | A runtime exists, but the canonical bootstrap it depends on is absent in the same repo. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 0 | Without the bootstrap artifact, the active repo cannot yet reuse the helper layer here. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 1 | The intended model is strong by precedent, but the current active artifact state is still missing. |
| Security, portability, and environment hygiene | 3 | The migrated runtime is env-driven and cleaner than the legacy scripts, even though the bootstrap slot is missing. |
| Enrichment-pack or total-pack coverage and maturity | 0 | No current ISS package exists in `OSHConnect-Python`. |
| Migration debt and canonical-home clarity | 1 | The fleet intent is obvious, but the repo boundary is still unresolved. |

**Top semantic gaps**

- The current fleet lacks a canonical ISS bootstrap entirely.
- The intended dual-product position-and-track model is not yet represented in the active repo's bootstrap layer.
- No current active ISS artifact expresses deployment semantics in the same repo as the runtime.

**Top metadata gaps**

- No ISS metadata pack or total pack exists in the active repo.
- No active SensorML artifact exists to judge or improve.
- README guidance and actual artifact state are contradictory.

**Top standards/conformance gaps**

- There is no active bootstrap to score as a standards-aligned current artifact.
- The best standards-aligned ISS work remains stranded in the legacy repo.
- The active fleet is therefore semantically incomplete by construction.

**Top operational/mechanical gaps**

- New users are told to run a bootstrap that does not exist.
- Docker and runtime presence can mislead contributors into assuming bootstrap completeness.
- Migration work is blocked not by model uncertainty, but by artifact absence.

**Recommended target state**

ISS should exist as a first-class current bootstrap in `publishers/iss/`, preserving the strong dual-product legacy model while adopting current helper-layer and env conventions.

**Recommended next artifact**

`migration task`

---

## B.7 USGS Water

**Primary path:** `publishers/usgs_water/bootstrap_usgs_water.py`
**Pattern family:** Station-per-system with paired parameter streams
**Current topology summary:** one water-observation procedure, eight station systems, two datastreams per station (`usgsDischarge` and `usgsGageHeight`), and a root/group/station deployment tree driven by a comparatively rich `publishers/usgs_water/stations.json`.

**Current strengths**

- The datastream split is more semantically deliberate than the older station-family bootstraps.
- The sidecar is richer than a simple station list and includes parameter definitions.
- The bootstrap embeds strong official USGS OGC API references, including statistic semantics.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The station and two-datastream-per-station model is explicit and easy to audit. |
| Procedure semantics | 4 | The procedure and surrounding references reflect a real source-specific water-observation model. |
| System semantics | 3 | Station systems are appropriate, but system-level semantics still rely heavily on generic station framing. |
| Datastream semantics and result-schema precision | 4 | Splitting discharge and gage height into distinct datastreams is a meaningful semantic upgrade. |
| Deployment semantics and hierarchy quality | 3 | The deployment tree is correct but still relatively light. |
| Metadata richness and SensorML quality | 3 | Inline provenance is strong, yet the overall package state is weaker than the code suggests. |
| Provenance and official-source traceability | 4 | The script directly references the OGC API docs, collection endpoints, and statistic resources. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | The statistic-specific and parameter-specific framing is stronger than in the average station-family bootstrap. |
| Sidecar/config fidelity and source selection quality | 4 | `stations.json` includes comments, source notes, station entries, and parameter definitions rather than only IDs. |
| Bootstrap/runtime alignment | 4 | Bootstrap and runtime both center on USGS water stations and paired parameter streams. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | It follows the current helper pattern cleanly. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 4 | The datastream split and provenance story are conceptually strong, even if the package state is incomplete. |
| Security, portability, and environment hygiene | 2 | Runtime TLS verification remains the main weakness. |
| Enrichment-pack or total-pack coverage and maturity | 1 | A research note claims a total package path, but the actual package directory is missing on disk. |
| Migration debt and canonical-home clarity | 3 | The bootstrap itself is clearly in the right home, but package-state drift reduces canonical clarity. |

**Top semantic gaps**

- The system model is stronger than average, but still not yet fully package-backed.
- Water-observation semantics could go further on QC, datum, and null reasoning.
- Feature-of-interest semantics remain mostly implicit.

**Top metadata gaps**

- The claimed total pack is not present on disk.
- The repo therefore lacks a canonical package matching the research-note claim.
- Worked enrichment artifacts and source manifests are not yet materialized as current files.

**Top standards/conformance gaps**

- The datastream contract is good, but not yet backed by a full artifact suite.
- SensorML richness is not yet proven by a current pack.
- Deployment semantics remain more functional than expressive.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- Artifact-state inconsistency can mislead contributors about maturity.
- This is still another station-family skeleton rather than a declarative family instantiation.

**Recommended target state**

USGS water should become the strongest station-family public-data reference after its missing total-package artifact is actually materialized and treated as canonical.

**Recommended next artifact**

`total pack`

---

## B.8 USGS NIMS

**Primary path:** `publishers/usgs_nims/bootstrap_usgs_nims.py`
**Pattern family:** Pattern A companion datastream
**Current topology summary:** one imagery procedure, no new systems, one imagery datastream attached to each existing USGS water station system selected in `publishers/usgs_nims/cameras.json`, and a NIMS-specific root/group/station deployment tree.

**Current strengths**

- It is the clearest active example of a cross-publisher dependency pattern.
- The total package is present on disk and materially increases maturity.
- Sidecar and package materials already encode live-source verification and data-model reasoning.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The script clearly states that it adds imagery streams to pre-existing water systems. |
| Procedure semantics | 4 | The imagery procedure is real, source-specific, and explicitly documented. |
| System semantics | 4 | Reusing the water-station systems is conceptually strong for a companion-modality model. |
| Datastream semantics and result-schema precision | 4 | The image stream is clearly modeled as a distinct modality rather than folded into the water stream. |
| Deployment semantics and hierarchy quality | 4 | The dedicated NIMS deployment subtree expresses a deliberate operational context for the companion stream. |
| Metadata richness and SensorML quality | 4 | Bootstrap plus total-pack materials provide a strong semantic story and concrete enrichment artifacts. |
| Provenance and official-source traceability | 5 | The package includes live-source verification notes and explicit official source manifests. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | The data model and mapping artifacts make the imagery contract unusually explicit. |
| Sidecar/config fidelity and source selection quality | 4 | `cameras.json` is a real semantic sidecar, not just a demo list. |
| Bootstrap/runtime alignment | 3 | Alignment is good, but the runtime still encodes a selected-camera-per-station policy that should be more explicit. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | It uses the current helper layer well even while expressing a distinct family pattern. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 4 | The companion-datastream model is conceptually strong and well backed by package reasoning. |
| Security, portability, and environment hygiene | 2 | Runtime TLS verification still weakens end-to-end hygiene. |
| Enrichment-pack or total-pack coverage and maturity | 5 | A substantial total package is present and inspectable on disk. |
| Migration debt and canonical-home clarity | 4 | The artifact clearly belongs in the current repo and is materially present. |

**Top semantic gaps**

- The selected-camera-per-station assumption needs to be documented as policy or redesigned.
- The cross-publisher dependency on water systems should be formalized more explicitly.
- There is room to expose richer image-product semantics beyond the current image stream contract.

**Top metadata gaps**

- The current package is strong, but not yet integrated into a fleet-wide Pattern A standard.
- Some dependency semantics still live more in notes than in formal bootstrap contracts.
- Asset provenance and coverage semantics can still be deepened.

**Top standards/conformance gaps**

- Pattern A is conceptually strong here, but not yet codified across the fleet.
- Shared-system ownership semantics remain implicit.
- Feature-of-interest and deployment relationship semantics could be made more formal.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- Dependency on the water bootstrap is operationally real but not yet enforced through a stronger contract.
- Multi-camera-per-site evolution is not yet first-class.

**Recommended target state**

USGS NIMS should remain the reference Pattern A implementation, with the next step being clearer dependency semantics and an explicit policy on one-camera versus multi-camera site modeling.

**Recommended next artifact**

`runtime follow-on`

---

## B.9 USGS Earthquake

**Primary path:** `publishers/usgs_eq/bootstrap_usgs_eq.py`
**Pattern family:** Pattern C feed adapter
**Current topology summary:** one feed-normalizer procedure, one feed system, one earthquake-event datastream, and a root/feed deployment tree driven by `publishers/usgs_eq/config.json`.

**Current strengths**

- It is one of the strongest current examples of live-source-verified package maturity.
- The feed-adapter semantics are explicit and well aligned with the upstream event-feed model.
- The total package is present on disk and includes real supporting artifacts rather than only prose.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The script very clearly declares a one-system feed-adapter model for earthquake events. |
| Procedure semantics | 4 | The procedure is explicitly a feed normalizer rather than a placeholder observing procedure. |
| System semantics | 4 | Modeling the source as a feed system is conceptually strong and avoids false physical-platform semantics. |
| Datastream semantics and result-schema precision | 4 | The earthquake-event stream is well aligned to the source model and supported by package mapping artifacts. |
| Deployment semantics and hierarchy quality | 3 | The deployment tree is intentionally simple but appropriate. |
| Metadata richness and SensorML quality | 4 | The bootstrap and total pack jointly provide a strong semantic and metadata story. |
| Provenance and official-source traceability | 5 | The package explicitly ties the model to summary feeds, detail feeds, policy docs, ComCat, and FDSN sources. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | Field-term semantics and feed-variant mapping are stronger than in most of the fleet. |
| Sidecar/config fidelity and source selection quality | 4 | `config.json` contains meaningful feed-choice, cadence, and dedupe rationale rather than only a URL. |
| Bootstrap/runtime alignment | 4 | The runtime and bootstrap both center on the same feed-normalizer contract. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 4 | It fits the current helper layer cleanly while preserving distinct Pattern C behavior. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 4 | The conceptual mapping is strong and well reasoned. |
| Security, portability, and environment hygiene | 2 | Runtime TLS verification remains the main weakness. |
| Enrichment-pack or total-pack coverage and maturity | 5 | A substantial total package is present and materially complete. |
| Migration debt and canonical-home clarity | 4 | The artifact is clearly in the right repo and supported by present on-disk materials. |

**Top semantic gaps**

- Summary-feed semantics are strong, but detail-feed and FDSN crosswalk semantics can still be formalized further.
- Lifecycle and supersession behavior can be represented more explicitly in the semantic contract.
- Event-quality semantics can still be deepened.

**Top metadata gaps**

- The total package is strong, but not yet generalized into a canonical Pattern C reference template.
- Detail-event enrichment can still expand.
- The deployment story is intentionally thin compared with the rest of the semantic model.

**Top standards/conformance gaps**

- Pattern C is strong here, but not yet codified fleet-wide.
- OM-style lifecycle semantics remain partly implicit.
- Additional provenance fields could better formalize feed-versus-detail authority.

**Top operational/mechanical gaps**

- Runtime TLS verification is disabled.
- There is not yet a generic feed-adapter conformance probe suite for variant and lifecycle behavior.
- The runtime could still better expose feed-policy and supersession reasoning operationally.

**Recommended target state**

USGS EQ should serve as the strongest current Pattern C reference once lifecycle, detail-feed, and runtime hardening follow-ons are formalized.

**Recommended next artifact**

`runtime follow-on`
