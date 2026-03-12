# Publisher Full-Scope Enrichment Prioritization Plan

**Date:** 2026-03-12
**Author:** Codex (GPT-5)
**Purpose:** define the recommended one-by-one execution order for full-scope publisher enrichment across the current `OSHConnect-Python` public-data fleet.
**Scope:** `nws`, `ndbc`, `coops`, `aviation_wx`, `opensky`, `iss`, `usgs_water`, `usgs_nims`, `usgs_eq`
**Relationship to prior analysis:** this plan operationalizes the findings in `All_Bootstraps_Full_Scope_Gap_Analysis_2026-03-12.md` and its appendices.

---

## 1. Executive Decision

Do not enrich the publishers in alphabetical order, by repo age, or only by which one looks weakest.

The recommended sequence is:

1. `ISS`
2. `USGS Water`
3. `NWS`
4. `USGS EQ`
5. `OpenSky`
6. `NDBC`
7. `USGS NIMS`
8. `CO-OPS`
9. `Aviation WX`

This is not a pure maturity ranking. It is a `rework-minimizing, semantics-first execution order` designed to:

- close the biggest current-fleet contradiction first;
- resolve dependency roots before dependent publishers;
- establish canonical templates before catch-up work;
- convert the strongest current ideas into reusable patterns early;
- delay the lowest-leverage catch-up work until the family conventions are already stable.

---

## 2. Prioritization Logic

The order above was chosen using six criteria.

### 2.1 Canonical completeness

If a publisher slot is supposed to exist in the active fleet but is materially incomplete, that gap should be closed early because it corrupts the credibility of the whole corpus.

This is why `ISS` is first.

### 2.2 Dependency roots

If one publisher depends on another publisher's systems, semantics, or sidecars, the upstream publisher should usually be enriched first.

This is why `USGS Water` must precede `USGS NIMS`.

### 2.3 Pattern-template leverage

The first few enrichments should define reusable family standards:

- canonical station-family enrichment expectations;
- canonical Pattern C feed-adapter expectations;
- canonical Pattern A companion-datastream expectations.

This is why `NWS`, `USGS EQ`, and `OpenSky` are early, and why `CO-OPS` and `Aviation WX` are late.

### 2.4 Artifact-state risk

Publishers whose current artifact state is contradictory, misleading, or absent should be addressed before publishers that are already materially present and inspectable.

This is why `ISS` and `USGS Water` are ahead of already-packaged publishers like `USGS NIMS` and `USGS EQ`.

### 2.5 Marginal fleet value

An enrichment should be prioritized earlier if finishing it gives the rest of the fleet a better template, stronger test discipline, or clearer vocabulary.

This is why `NWS` is ahead of `CO-OPS` and `Aviation WX`, and why `USGS EQ` is ahead of a second-pass refinement on already-strong `USGS NIMS`.

### 2.6 Catch-up should come after template stabilization

The thinnest publishers should not be first if their enrichment would otherwise be designed in a vacuum.

This is why `CO-OPS` and especially `Aviation WX` are late-phase work rather than first-phase work.

---

## 3. Phase 0 Guardrails

Before the first publisher enrichment begins, define these fleet-level guardrails once and then reuse them for every publisher:

1. a standard `full-scope package contract`
   - required folders
   - required manifests
   - required worked examples
   - required patch candidates
   - required source-corpus notes
2. a standard `semantic acceptance checklist`
   - procedure
   - system
   - datastream
   - deployment
   - feature-of-interest
   - provenance
   - units and null semantics
3. a standard `round-trip verification checklist`
   - POST
   - GET back
   - SensorML inspection
   - result-schema inspection
   - observation write-path verification
4. a standard `runtime hardening checklist`
   - TLS verification
   - auth handling
   - retry and dedupe policy
   - logging and observability
5. a standard `artifact state label`
   - `metadata pack`
   - `total pack`
   - `source basis`
   - `historical artifact`
   - `migration artifact`

This preflight is important because otherwise the first three enrichments will each reinvent package shape and acceptance criteria.

---

## 4. Ordered Publisher Plan

| Rank | Publisher | Why This Position | Primary Outcome | Main Dependency / Leverage |
|---|---|---|---|---|
| 1 | ISS | The active fleet is currently incomplete; the bootstrap slot is missing even though the runtime and README imply it exists. | Migrate ISS into a canonical current bootstrap and package. | Removes the single clearest architecture contradiction in the fleet. |
| 2 | USGS Water | It is a dependency root for NIMS and currently has an artifact-state mismatch. | Materialize the missing total package and make water the canonical USGS station reference. | Unblocks clean NIMS follow-on work and repairs repo-state trust. |
| 3 | NWS | It is the best place to formalize station-family round-trip SensorML acceptance criteria. | Convert strong pack work into a canonical live-plus-package station reference. | Sets the first real station-family enrichment template. |
| 4 | USGS EQ | It is already one of the strongest full packages and can define the canonical Pattern C total-pack standard. | Harden Pattern C lifecycle, provenance, and event semantics. | Establishes a reusable feed-adapter template. |
| 5 | OpenSky | It is the other major Pattern C publisher and already has strong metadata foundations. | Graduate OpenSky from metadata-pack maturity to total-pack maturity. | Reuses the Pattern C template established in USGS EQ. |
| 6 | NDBC | It is the richest station-family multi-stream case and should become the canonical station-plus-imagery reference. | Convert NDBC into the canonical multi-stream station publisher package. | Reuses station-family conventions from NWS and informs imagery semantics for later work. |
| 7 | USGS NIMS | It is already strong, but its dependency semantics should be refined only after water and family templates are stable. | Formalize companion-datastream dependency semantics and policy constraints. | Depends on clean USGS Water semantics and benefits from earlier imagery-pattern work. |
| 8 | CO-OPS | It lacks a pack, but its enrichment should borrow already-proven station-family structure rather than invent its own. | Create a full package and sharpen coastal product semantics. | Reuses station-family scaffolding from NWS and NDBC. |
| 9 | Aviation WX | It is the thinnest current publisher, but also the one with the least leverage on the rest of the fleet. | Bring Aviation WX up to full-package parity without using it as the template setter. | Best done after station-family conventions are already frozen. |

---

## 5. Recommended Waves

### Wave 1. Canonical blockers and dependency roots

1. `ISS`
2. `USGS Water`
3. `NWS`

This wave fixes the biggest fleet contradiction, repairs the most important current artifact mismatch, and establishes the first canonical station-family enrichment method.

### Wave 2. Canonical family references

4. `USGS EQ`
5. `OpenSky`
6. `NDBC`
7. `USGS NIMS`

This wave completes the strongest reusable family references:

- Pattern C total-package reference;
- second Pattern C implementation;
- multi-stream station-family reference;
- Pattern A companion-datastream reference.

### Wave 3. Catch-up and parity

8. `CO-OPS`
9. `Aviation WX`

This wave uses already-proven conventions to bring the remaining station-family publishers to full-package parity with much lower design risk.

---

## 6. Publisher-by-Publisher Intent

### 6.1 ISS

**Why first**

- The current fleet is semantically incomplete while ISS remains a runtime without a current bootstrap.
- The migration path is unusually well defined because `scripts/bootstrap_iss.py` already exists as a strong precedent.
- The project should not start a long enrichment program while one advertised active publisher is still missing its bootstrap artifact.

**What "full-scope enrichment" means here**

- migrate `bootstrap_iss.py` into `publishers/iss/`
- modernize it to current helper-layer and env conventions
- produce a current ISS package, not just a migrated script
- preserve the dual-product model and rich SensorML
- remove every legacy credential, TLS, and hardcoded-endpoint anti-pattern

**Exit condition**

ISS is no longer a special-case hole in the active fleet.

### 6.2 USGS Water

**Why second**

- `USGS NIMS` depends on it structurally
- the current repo has a claimed total pack that is not actually present on disk
- the water publisher is already semantically stronger than its artifact state suggests

**What "full-scope enrichment" means here**

- materialize the missing total package
- reconcile research-note claims with actual on-disk artifacts
- preserve and extend the strong parameter/statistic semantics
- formalize datum, QC, null, and feature-of-interest semantics more explicitly

**Exit condition**

USGS Water becomes the canonical USGS station-family base that NIMS can depend on without ambiguity.

### 6.3 NWS

**Why third**

- NWS is the best place to institutionalize the lessons from the historical SensorML field-shape failure
- it already has substantial adjacent metadata-pack work
- it can become the station-family proof point for round-trip validation discipline

**What "full-scope enrichment" means here**

- converge the best metadata-pack content into a live canonical package
- codify station-family semantic-contract conventions
- add explicit round-trip verification expectations
- deepen QC, null, and feature-of-interest semantics

**Exit condition**

NWS becomes the reference station-family enrichment against which later station publishers are judged.

### 6.4 USGS EQ

**Why fourth**

- it is already one of the strongest current total packages
- it can define the canonical Pattern C total-package template with the least uncertainty
- its lifecycle, provenance, and crosswalk semantics are unusually rich and reusable

**What "full-scope enrichment" means here**

- turn strong current package materials into the authoritative Pattern C template
- deepen summary/detail/FDSN crosswalk semantics
- formalize lifecycle, supersession, and quality semantics
- define the feed-adapter artifact and acceptance pattern other Pattern C publishers should follow

**Exit condition**

USGS EQ becomes the canonical Pattern C reference package.

### 6.5 OpenSky

**Why fifth**

- OpenSky is already a strong Pattern C implementation, but it still trails USGS EQ in package maturity
- once USGS EQ defines the full Pattern C standard, OpenSky can be upgraded without inventing a second incompatible model

**What "full-scope enrichment" means here**

- graduate from metadata pack to total package
- formalize auth-aware and budget-aware operational semantics
- deepen data quality, provenance, and coverage semantics
- align its package shape to the Pattern C standard frozen in the previous step

**Exit condition**

The fleet has two aligned Pattern C references rather than one strong feed-adapter and one separate event-feed model.

### 6.6 NDBC

**Why sixth**

- NDBC is the richest current station-family multi-stream case
- it benefits from earlier station-family and Pattern C decisions
- it is the best place to formalize how imagery-related semantics coexist with a fixed-station observation model

**What "full-scope enrichment" means here**

- convert the existing metadata pack into a total-package-grade artifact
- deepen the buoy-plus-imagery relationship model
- sharpen QC, null, and provenance semantics
- decide whether NDBC becomes the canonical "multi-stream station" reference

**Exit condition**

The station family now has a strong simple reference and a strong multi-stream reference.

### 6.7 USGS NIMS

**Why seventh**

- it is already strong and materially present
- its next gains depend more on dependency clarification than on raw metadata creation
- it benefits from earlier USGS Water and imagery-related lessons

**What "full-scope enrichment" means here**

- formalize the dependency contract on USGS Water systems
- decide whether selected-camera-per-station is permanent policy or transitional implementation
- deepen coverage, product, and asset provenance semantics
- align Pattern A packaging to the conventions proven earlier

**Exit condition**

USGS NIMS becomes the canonical Pattern A reference with explicit dependency semantics.

### 6.8 CO-OPS

**Why eighth**

- it is a good publisher, but not a template setter
- it currently lacks a pack
- its enrichment can be done faster and more cleanly after station-family conventions are settled

**What "full-scope enrichment" means here**

- create a full package from scratch
- sharpen product-family, datum, and coastal semantics
- apply already-proven station-family packaging and validation discipline

**Exit condition**

CO-OPS reaches full-package parity without forcing the project to learn station-family lessons the hard way.

### 6.9 Aviation WX

**Why ninth**

- it is the thinnest current publisher
- it has the least leverage on the rest of the fleet
- it will benefit most from arriving after the station-family conventions and package contract are already stable

**What "full-scope enrichment" means here**

- create its first full package
- deepen airport/system/procedure semantics
- formalize aviation vocabulary and null/missing-value handling
- bring it to parity without turning it into the family template

**Exit condition**

Aviation WX is no longer the semantic and artifact outlier of the current fleet.

---

## 7. Program-Level Checkpoints

Do not run the whole program as nine disconnected tasks. Use checkpoints.

### Checkpoint A: after ISS and USGS Water

Lock down:

- the standard package contract
- the migration-artifact policy
- the dependency-root policy

### Checkpoint B: after NWS and USGS EQ

Lock down:

- canonical station-family acceptance criteria
- canonical Pattern C acceptance criteria
- round-trip verification expectations

### Checkpoint C: after OpenSky, NDBC, and USGS NIMS

Lock down:

- final Pattern C conventions
- final multi-stream station conventions
- final Pattern A dependency conventions

### Checkpoint D: after CO-OPS and Aviation WX

Run a parity review to confirm the lagging station-family publishers now meet the same artifact and semantic baseline as the rest of the fleet.

---

## 8. Recommended Operating Rule

For this program, `done` should mean more than "a richer bootstrap file exists."

For each publisher, completion should require:

- a current bootstrap aligned to the target model
- a materially present package on disk
- corrected and verified provenance corpus
- explicit semantic-contract notes
- round-trip verification evidence
- a runtime follow-on list if runtime work remains outside the package scope

If the project follows that rule, the enrichment program will produce a canonical fleet rather than a collection of better comments.

