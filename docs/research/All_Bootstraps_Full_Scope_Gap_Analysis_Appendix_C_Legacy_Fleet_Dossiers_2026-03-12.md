# All Bootstraps Full-Scope Gap Analysis

## Appendix C. Legacy Fleet Dossiers

**Date:** 2026-03-12
**Scope:** legacy bootstraps in `csapi-explorer/scripts` that still matter architecturally, historically, or as migration references.

**Standards note:** the `Standards conformance` row in each matrix was revalidated on 2026-03-12 against the corrected standards corpus in Appendix D, using current Connected Systems, SensorML 3.0, SWE Common 3.0, OMS 3.0, and W3C SSN/SOSA references where applicable.

---

## C.1 `bootstrap_iss.py`

**Path:** `scripts/bootstrap_iss.py`
**Current role classification:** Active precedent and migration candidate

**What still matters architecturally**

- It is the clearest legacy source of the current helper-layer pattern.
- It proves the dual-product ISS publisher model with meaningful procedures, systems, datastreams, and deployments.
- It shows a richer SensorML posture than most of the rest of the legacy corpus.

**What should not be propagated forward**

- Hardcoded production endpoint and credentials.
- Inline DNS override and permissive TLS handling.
- One-off transport logic that should now live in shared helpers.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The dual-product ISS topology is explicit, documented, and easy to follow. |
| Procedure semantics | 4 | The SGP4 and orbit-track procedures are clearly differentiated and meaningfully described. |
| System semantics | 4 | The split between position and orbit-track systems is semantically intentional rather than arbitrary. |
| Datastream semantics and result-schema precision | 4 | Both datastreams are clearly scoped and more explicit than most legacy examples. |
| Deployment semantics and hierarchy quality | 4 | The deployment tree meaningfully places the two publisher products into an operational hierarchy. |
| Metadata richness and SensorML quality | 5 | This is the richest and most convincing legacy SensorML bootstrap in the corpus. |
| Provenance and official-source traceability | 4 | The script ties its orbital semantics to CelesTrak and the SGP4 model in a way that is auditably meaningful. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | Field naming and result-record intent are substantially better than in most legacy scripts. |
| Sidecar/config fidelity and source selection quality | 2 | The script is coherent, but largely self-contained rather than supported by modern sidecars or package manifests. |
| Bootstrap/runtime alignment | 4 | It aligns well with the ISS publisher model it was designed to support. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 2 | It predates the helper layer and therefore duplicates transport and lifecycle logic inline. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 4 | Its conceptual mapping is strong enough to have informed the current helper architecture. |
| Security, portability, and environment hygiene | 1 | Embedded credentials and disabled TLS verification make it operationally unfit in its current form. |
| Enrichment-pack or total-pack coverage and maturity | 3 | It has meaningful adjacent enrichment context, but not in the same mature packaging style as the best current total packs. |
| Migration debt and canonical-home clarity | 1 | It is the clearest current example of a bootstrap living in the wrong repo for today's fleet. |

**Migration or archival recommendation**

Migrate this script into `publishers/iss/bootstrap_iss.py`, preserve its dual-product model and rich SensorML, and remove every legacy transport and credential anti-pattern in the process.

---

## C.2 `bootstrap_uas.py`

**Path:** `scripts/bootstrap_uas.py`
**Current role classification:** Historical artifact with reusable enrichment ideas

**What still matters architecturally**

- It demonstrates an additive enrichment workflow over an already-bootstrapped graph.
- It captures how procedures, datastreams, and deployment leaves can be introduced without recreating the whole scenario.
- It contains valuable examples of richer metadata on scenario systems that were otherwise thin.

**What should not be propagated forward**

- Hardcoded server assumptions and credentials.
- Reliance on existing server IDs and pre-created resources as the normal operating model.
- Treating a live server as too much of the source of truth.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 3 | The script's additive role is clear, but it depends heavily on prior scenario state. |
| Procedure semantics | 3 | The procedures are meaningful, though tightly bound to scenario concepts rather than reusable publisher models. |
| System semantics | 4 | The enrichment bodies add real system-level meaning that the older bare scripts lacked. |
| Datastream semantics and result-schema precision | 4 | The datastreams added by the script are semantically specific and more expressive than minimal placeholders. |
| Deployment semantics and hierarchy quality | 3 | The added deployment leaves are meaningful, but the script is not a full deployment model. |
| Metadata richness and SensorML quality | 4 | This is one of the richer legacy enrichment efforts from a metadata standpoint. |
| Provenance and official-source traceability | 2 | Provenance is mainly scenario-internal rather than tied to official external data sources. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | The added stream schemas are intentionally modeled and fairly expressive. |
| Sidecar/config fidelity and source selection quality | 3 | The script benefits from template-like enrichment logic, but not from a modern explicit sidecar contract. |
| Bootstrap/runtime alignment | 3 | It aligns to a scenario runtime context, but only if the pre-existing graph already exists. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 1 | It predates current helper reuse and remains tightly tied to the legacy server graph. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 3 | The model is reasonably strong, but still scenario-bound and operationally brittle. |
| Security, portability, and environment hygiene | 1 | It retains the same hardcoded server and TLS weaknesses as the rest of the old corpus. |
| Enrichment-pack or total-pack coverage and maturity | 3 | It is best understood as an enrichment script with meaningful adjacent template context rather than a full package. |
| Migration debt and canonical-home clarity | 1 | It should not move into the public-data fleet; it should instead be clearly labeled as scenario-specific. |

**Migration or archival recommendation**

Archive it as a scenario-specific enrichment reference and extract only the reusable metadata-enrichment ideas into better-isolated future tooling.

---

## C.3 `bootstrap_localizer.py`

**Path:** `scripts/bootstrap_localizer.py`
**Current role classification:** Scenario-only bootstrap

**What still matters architecturally**

- It is a clean minimal example of a focused bootstrap with one procedure, one system, and one datastream.
- It shows a straightforward path for a non-public-data derived product.
- It is easier to reason about than the larger scenario scripts.

**What should not be propagated forward**

- Hardcoded endpoint, credentials, and disabled TLS verification.
- Sparse metadata and deployment absence.
- Treating minimal structure as sufficient for canonical semantic completeness.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The one-procedure, one-system, one-datastream shape is very clear. |
| Procedure semantics | 3 | The triangulation procedure is real and conceptually meaningful. |
| System semantics | 2 | The system exists at the right level, but metadata richness is thin. |
| Datastream semantics and result-schema precision | 3 | The location-estimate datastream is purpose-built and reasonably clear. |
| Deployment semantics and hierarchy quality | 0 | The script does not create a meaningful deployment context on its own. |
| Metadata richness and SensorML quality | 1 | Metadata is sparse and remains closer to a bare bootstrap shell. |
| Provenance and official-source traceability | 1 | Provenance is almost entirely scenario-internal. |
| Field semantics, units, vocabularies, and nullability discipline | 3 | The result schema is functional, though not richly standardized. |
| Sidecar/config fidelity and source selection quality | 1 | The script is almost entirely inline and lacks a richer sidecar or package contract. |
| Bootstrap/runtime alignment | 3 | It fits the localizer runtime model, but only at a minimal level. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 1 | It uses custom inline transport rather than the current helper architecture. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 2 | The conceptual fit is fair, but the artifact is too thin to score strongly. |
| Security, portability, and environment hygiene | 1 | It inherits the legacy credential and TLS anti-patterns. |
| Enrichment-pack or total-pack coverage and maturity | 1 | There is no mature supporting package structure around it. |
| Migration debt and canonical-home clarity | 2 | It belongs to scenario tooling, but that boundary is not made explicit enough today. |

**Migration or archival recommendation**

Keep it only as a scenario-only reference for small focused bootstraps and do not treat it as a public-data publisher template.

---

## C.4 `bootstrap_v25.py`

**Path:** `scripts/bootstrap_v25.py`
**Current role classification:** Historical migration bridge

**What still matters architecturally**

- It shows how backup SensorML, procedures, datastreams, and control-stream assets were stitched back into a live graph.
- It demonstrates migration-time link rewriting, backup-file loading, and hybrid graph creation.
- It is one of the clearest legacy examples of combining inline new resources with imported backup truth.

**What should not be propagated forward**

- Its operational assumptions are still highly server-specific.
- It is too hybrid and transitional to act as a canonical steady-state bootstrap.
- It retains the same weak security and transport posture as the rest of the old scenario corpus.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The script is large, but its migration role and scenario layering are reasonably clear. |
| Procedure semantics | 3 | Procedures are meaningful, though still heavily tied to scenario doctrine and migration context. |
| System semantics | 4 | It models several distinct scenario system roles with more intention than the earlier bare scripts. |
| Datastream semantics and result-schema precision | 4 | It carries forward and reconstructs rich datastream semantics from backup resources. |
| Deployment semantics and hierarchy quality | 4 | The doctrine-aligned deployment hierarchy is intentional and more expressive than minimal trees. |
| Metadata richness and SensorML quality | 3 | It mixes strong backup-derived richness with transitional inline material. |
| Provenance and official-source traceability | 3 | Provenance is strong relative to repo-local backup truth, though not tied to public upstream sources. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | The backup-derived datastream and control-stream schemas carry real semantic detail. |
| Sidecar/config fidelity and source selection quality | 4 | Backup files, maps, and imported resources form a meaningful supporting corpus. |
| Bootstrap/runtime alignment | 2 | This is a migration bridge more than a clean current runtime partner. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 1 | It remains a large custom script rather than a reusable helper-based pattern. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 3 | The scenario graph is semantically rich, but the artifact is transitional and operationally brittle. |
| Security, portability, and environment hygiene | 1 | Legacy endpoint and TLS weaknesses remain. |
| Enrichment-pack or total-pack coverage and maturity | 2 | Supporting artifacts exist, but they are migration backups rather than a modern package. |
| Migration debt and canonical-home clarity | 1 | The script should remain historical, not canonical. |

**Migration or archival recommendation**

Retain it only as a historical migration bridge and mine it for reusable import techniques rather than for steady-state bootstrap patterns.

---

## C.5 `bootstrap_v3.1.py`

**Path:** `scripts/bootstrap_v3.1.py`
**Current role classification:** Historical artifact

**What still matters architecturally**

- It documents an earlier authoritative scenario-hierarchy model.
- It shows a nested deployment creation strategy that was considered reliable on the target server.
- It captures a stage in the scenario architecture before richer bootstrap families emerged.

**What should not be propagated forward**

- Inline everything architecture with hardcoded credentials.
- Bare or thin resource semantics passed off as authoritative completeness.
- Reliance on repair flags and server-specific fix-up behavior as the normal operating model.

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 4 | The script clearly centers on systems plus a nested deployment hierarchy. |
| Procedure semantics | 1 | Procedure treatment is minimal compared with later scripts. |
| System semantics | 2 | Systems are defined, but semantic richness is modest. |
| Datastream semantics and result-schema precision | 1 | Datastream semantics are not the main strength of this artifact and remain thin. |
| Deployment semantics and hierarchy quality | 4 | Deployment hierarchy construction is the script's clearest contribution. |
| Metadata richness and SensorML quality | 1 | Metadata remains close to a minimal authoritative shell rather than a rich semantic artifact. |
| Provenance and official-source traceability | 1 | Provenance is almost entirely internal to the scenario. |
| Field semantics, units, vocabularies, and nullability discipline | 2 | Field semantics exist where needed, but not at a rich or systematic level. |
| Sidecar/config fidelity and source selection quality | 1 | The script is self-contained and does not benefit from richer supporting sidecars. |
| Bootstrap/runtime alignment | 2 | It fits an earlier scenario runtime state, but not a modern public-data architecture. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 0 | It predates the helper model and does not provide a durable modern operator contract. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 2 | The deployment ideas are useful, but the rest of the semantic model is thin. |
| Security, portability, and environment hygiene | 1 | Credentials and server assumptions are embedded directly in the file. |
| Enrichment-pack or total-pack coverage and maturity | 0 | There is no modern enrichment or package layer around this script. |
| Migration debt and canonical-home clarity | 1 | This is best understood as a historical stage, not a current candidate. |

**Migration or archival recommendation**

Archive it as a historical scenario-hierarchy milestone and do not treat it as a current reference except for deployment-tree lessons.

---

## C.6 `bootstrap_v4.py`

**Path:** `scripts/bootstrap_v4.py`
**Current role classification:** Scenario-only authoritative bootstrap

**What still matters architecturally**

- It is the clearest full-scenario authority in the legacy corpus.
- It shows what the current helper layer still cannot express: subsystems, control streams, broad scenario hierarchies, and corrective logic.
- It remains the best scenario-side evidence for the complexity gap between publisher bootstraps and general connected-systems bootstrapping.

**What should not be propagated forward**

- Hardcoded credentials and disabled TLS verification.
- Treating huge inline scenario authority as the default contribution model for public-data work.
- Conflating "authoritative for one scenario" with "canonical for the fleet".

### Score matrix

| Category | Score | Justification |
|---|---:|---|
| Bootstrap topology clarity | 5 | Despite its size, the script declares a complete scenario graph with explicit phases and resource families. |
| Procedure semantics | 2 | Procedure use exists, but it is weaker and less complete than the system, datastream, and deployment work. |
| System semantics | 3 | The scenario systems are meaningful, though many remain only thinly enriched in the bootstrap itself. |
| Datastream semantics and result-schema precision | 4 | Datastream and control-stream schemas are one of the script's strongest areas. |
| Deployment semantics and hierarchy quality | 5 | This is the strongest deployment-hierarchy artifact in the legacy corpus. |
| Metadata richness and SensorML quality | 1 | Rich metadata is not the strength of the live bootstrap itself; much of that work lived elsewhere. |
| Provenance and official-source traceability | 2 | Provenance is mainly scenario-internal rather than official-source based. |
| Field semantics, units, vocabularies, and nullability discipline | 4 | The stream schemas are detailed enough to remain architecturally informative. |
| Sidecar/config fidelity and source selection quality | 3 | The script is mostly inline, but it sits within a broader scenario-support context. |
| Bootstrap/runtime alignment | 4 | It is still the best authoritative bootstrap for its scenario family. |
| Helper-layer reuse, idempotency, cleanup, and operator ergonomics | 1 | It predates the helper layer and remains too monolithic for modern reuse. |
| Standards conformance to CSAPI, SOSA/SSN, SensorML, SWE, and OM intent | 3 | The scenario graph intent is strong, but metadata and operational hygiene lag. |
| Security, portability, and environment hygiene | 1 | Operational security posture is weak. |
| Enrichment-pack or total-pack coverage and maturity | 1 | It does not have a modern pack structure even though it has adjacent backup and restoration context. |
| Migration debt and canonical-home clarity | 1 | It should remain scenario-only and clearly outside the public-data canonical path. |

**Migration or archival recommendation**

Preserve it as the authoritative scenario reference, but move it out of the conceptual path for public-data publisher contributors and do not use it as a template for new public-source work.
