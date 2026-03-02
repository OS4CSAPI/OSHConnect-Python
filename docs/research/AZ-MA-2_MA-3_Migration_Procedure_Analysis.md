# AZ-MA-2 / MA-3 Migration — Procedure Modeling Analysis

| Field | Value |
|---|---|
| **Date** | 2026-03-02 |
| **Author** | Claude (Opus 4.6) — cross-review with ChatGPT (o3) |
| **Status** | Pre-Migration Analysis |
| **Scope** | Procedure UID strategy, deployment restructuring, revised execution plan |
| **Depends On** | [AZ-MA-1 Migration Activity Report](https://github.com/OS4CSAPI/OSHConnect-Python/blob/scenario/v3.0-rebuild/docs/research/AZ-MA-1_Migration_Activity_Report.md) |

---

## 1  Background

AZ-MA-1 was successfully migrated from the DigitalOcean (DO) hub to the Oracle Cloud hub on 2026-02-27, producing 34 resources and 7,465 observations with zero failures. Two additional ODAS nodes — **AZ-MA-2** and **AZ-MA-3** — remain on the DO server and need to be migrated using the same Connected Systems API approach.

During planning, a cross-review between Claude and ChatGPT surfaced a critical data-modeling question: **Should the four "node-specific" procedures created during MA-1's migration be replicated per-node, or refactored to generic (node-agnostic) UIDs?**

This report presents a data-backed answer by auditing every procedure and datastream backup file.

---

## 2  Procedure Inventory

The DO server holds **9 procedures** that were backed up and migrated for MA-1. They fall into two categories:

### 2.1  Generic ODAS Procedures (5)

These are node-agnostic — they describe the algorithm/hardware, not a specific deployment.

| DO ID | UID | Name | Has Description |
|---|---|---|---|
| `0480` | `urn:x-odas:procedure:pdm-mems-audio-capture` | PDM MEMS Microphone Audio Capture | **Yes** — detailed PDM→PCM pipeline, frame/hop sizes, USB transport |
| `048g` | `urn:x-odas:procedure:srp-phat-beamforming` | SRP-PHAT Steered Response Power Beamforming | **Yes** — GCC-PHAT, hemisphere scan, DOA estimation |
| `0490` | `urn:x-odas:procedure:particle-filter-tracking` | Particle Filter Sound Source Tracking | **Yes** — sequential Monte Carlo, 3 motion states, Bayesian assignation |
| `049g` | `urn:x-odas:procedure:ray-to-ray-triangulation` | Multi-Array Ray-to-Ray 3D Triangulation | **Yes** — IROS 2017 algorithm, K-array averaging, particle refinement |
| `04a0` | `urn:x-odas:procedure:odas-config-actuation` | ODAS Runtime Configuration Actuation | **Yes** — parameter validation, atomic/batch updates, controllable params listed |

These 5 already use generic `urn:x-odas:procedure:*` UIDs and have rich technical descriptions. They were migrated once during MA-1 (Oracle IDs: `040g`–`042g`) and **do not need to be migrated again**.

### 2.2  Node-Specific Procedures (4)

These were created with per-node UIDs during the original DO bootstrap.

| DO ID | Oracle ID | UID | Name | `featureType` | Has Description |
|---|---|---|---|---|---|
| `04b0` | `0430` | `urn:os4csapi:procedure:odas:az-ma-1:calibration:v1` | Calibration Proc (AZ-MA-1) | `sosa:Procedure` | **No** — empty shell |
| `04bg` | `043g` | `urn:os4csapi:procedure:odas:az-ma-1:health-monitor:v1` | Health Proc (AZ-MA-1) | `sosa:Procedure` | **No** — empty shell |
| `04c0` | `0440` | `urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1` | ODAS Processing Chain (AZ-MA-1) | `sosa:ObservingProcedure` | **No** — empty shell |
| `04cg` | `044g` | `urn:os4csapi:procedure:odas:az-ma-1:frame-transform:v1` | Transform (AZ-MA-1) | `sosa:Procedure` | **No** — empty shell |

Each of these contains **only**: `uid`, `featureType`, `name`, `validTime`. No `description`, no `inputs`/`outputs`, no `parameters`, no `characteristics`. They are pure placeholders.

**Contrast with the generic procedures** — e.g., `proc_0480` (PDM MEMS) has a 3-sentence technical description, and `proc_04a0` (Config Actuation) lists every controllable parameter. The node-specific procedures have zero substance.

---

## 3  Datastream → Procedure Reference Map

Every datastream uses a `procedure@link` field to declare which procedure produced its observations. The complete mapping for MA-1's 7 datastreams:

| Datastream | DO DS ID | Procedure Referenced | Proc DO ID |
|---|---|---|---|
| SSL Potential Sources | `07fg2` | ODAS Processing Chain (AZ-MA-1) | `04c0` |
| SST Tracked Sources | `07g02` | ODAS Processing Chain (AZ-MA-1) | `04c0` |
| LOB | `07gg2` | ODAS Processing Chain (AZ-MA-1) | `04c0` |
| Track Updates | `07h02` | ODAS Processing Chain (AZ-MA-1) | `04c0` |
| Classification Probabilities | `07hg2` | Classification Proc (shared) | `04hg` *(not in the 9 migrated)* |
| Health | `07i02` | Health Proc (AZ-MA-1) | `04bg` |
| Scene Summary | `07ig2` | ODAS Processing Chain (AZ-MA-1) | `04c0` |

### 3.1  Key Findings

1. **Only 2 of 4 node-specific procedures are actually referenced** by datastreams:
   - `04c0` (Processing Chain) — referenced by **5 datastreams** (SSL, SST, LOB, Track Updates, Scene Summary)
   - `04bg` (Health) — referenced by **1 datastream** (Health)

2. **2 node-specific procedures are completely orphaned** — nothing references them:
   - `04b0` (Calibration) — zero datastream references, zero control stream references
   - `04cg` (Frame Transform) — zero datastream references, zero control stream references

3. **Classification (`04hg`)** is a shared procedure that was **not** part of the 9 migrated procedures — it already exists as a separate shared resource on DO.

4. **Control streams** (4 total, all on the Actuator subsystem) do **not** carry `procedure@link` fields.

---

## 4  Recommendation: Refactor to Generic UIDs

**ChatGPT's recommendation is correct.** The 4 node-specific procedures should be refactored to node-agnostic UIDs before migrating MA-2 and MA-3.

### 4.1  Rationale

| Factor | Per-Node (Current) | Generic (Proposed) |
|---|---|---|
| Content differentiation | Zero — all 4 are identical empty shells | N/A — one copy describes the concept once |
| Semantic accuracy | Misleading — implies MA-1 has a unique calibration process | Correct — the *procedure* is the same for all nodes |
| Scalability | 4 procedures × N nodes = 4N empty resources | 4 procedures total, shared by all nodes |
| Maintenance | Must update N copies for any description change | Single source of truth |
| SOSA/SSN alignment | `sosa:Procedure` describes the *method*, not the *platform* | Correct use of the ontology |
| Orphan cleanup | 2 orphaned procedures already exist per node | Orphans can be deleted or described properly |

### 4.2  Proposed New UIDs

| Current UID | Proposed UID | Notes |
|---|---|---|
| `urn:os4csapi:procedure:odas:az-ma-1:calibration:v1` | `urn:os4csapi:procedure:odas:calibration:v1` | Drop `az-ma-1` segment |
| `urn:os4csapi:procedure:odas:az-ma-1:health-monitor:v1` | `urn:os4csapi:procedure:odas:health-monitor:v1` | Drop `az-ma-1` segment |
| `urn:os4csapi:procedure:odas:az-ma-1:processing-chain:v1` | `urn:os4csapi:procedure:odas:processing-chain:v1` | Drop `az-ma-1` segment |
| `urn:os4csapi:procedure:odas:az-ma-1:frame-transform:v1` | `urn:os4csapi:procedure:odas:frame-transform:v1` | Drop `az-ma-1` segment |

### 4.3  Implementation Steps (Oracle Server)

The 4 procedures already exist on Oracle (IDs: `0430`, `043g`, `0440`, `044g`). The fix is a **PUT** to each:

1. `PUT /sensorhub/api/procedures/0430` — update `uid` to `...odas:calibration:v1`, update `name` to "ODAS Calibration Procedure"
2. `PUT /sensorhub/api/procedures/043g` — update `uid` to `...odas:health-monitor:v1`, update `name` to "ODAS Health Monitor Procedure"
3. `PUT /sensorhub/api/procedures/0440` — update `uid` to `...odas:processing-chain:v1`, update `name` to "ODAS Processing Chain"
4. `PUT /sensorhub/api/procedures/044g` — update `uid` to `...odas:frame-transform:v1`, update `name` to "ODAS Frame Transform"

> **No datastream changes required.** Datastreams reference procedures by server-local ID (`/sensorhub/api/procedures/0440`), not by UID. The `procedure@link.href` values stay the same.

### 4.4  Orphan Decision

The 2 orphaned procedures (Calibration `0430` and Frame Transform `044g`) can either be:
- **Kept** — add descriptions and reference them from future control streams or datastreams
- **Deleted** — they carry no observations and nothing links to them

Recommendation: **Keep them** and add real descriptions during the UID refactor. Even if unused today, they represent legitimate concepts in the ODAS processing pipeline.

---

## 5  Deployment Restructuring

### 5.1  Current State

```
String Alpha (deployment)
  └─ platform@link → AZ-MA-1 (system)
```

String Alpha currently links directly to AZ-MA-1 with a single `platform@link`. There is no structural accommodation for additional nodes.

### 5.2  Proposed Structure

```
String Alpha (deployment)
  ├─ Node 1 (sub-deployment) ─ platform@link → AZ-MA-1
  ├─ Node 2 (sub-deployment) ─ platform@link → AZ-MA-2
  └─ Node 3 (sub-deployment) ─ platform@link → AZ-MA-3
```

Each ODAS node gets its own sub-deployment under String Alpha. This:
- Enables per-node lifecycle management (e.g., decommissioning Node 2 without affecting others)
- Follows the existing hierarchy pattern (ICO → RSO → SSO → SNET → Field → String Alpha → Node N)
- Allows each node's datastreams to carry a `deployment@link` pointing to its own sub-deployment

### 5.3  Restructuring Steps

1. **Create 3 sub-deployments** under String Alpha:
   - `POST /sensorhub/api/deployments/{string-alpha-id}/members` with UIDs like `urn:os4csapi:deployment:string:ft-huachuca:001:node-1`
2. **Move MA-1's `platform@link`** from String Alpha down to Node 1
3. **Wire MA-2 and MA-3** `platform@link` on Node 2 and Node 3 respectively after migration

---

## 6  Revised Migration Execution Plan

### Phase 0 — Pre-Migration Refactor (One-Time)

| Step | Action | Risk |
|---|---|---|
| 0a | PUT to rename 4 procedure UIDs on Oracle (generic) | Low — no datastream breakage (linked by ID) |
| 0b | Add descriptions to all 4 now-generic procedures | Zero — additive change |
| 0c | Create 3 sub-deployments under String Alpha | Low — additive |
| 0d | Move MA-1 `platform@link` from String Alpha to Node 1 sub-deployment | Medium — verify MA-1 datastreams still resolve |
| 0e | Verify MA-1 still fully operational on Oracle | Gate — do not proceed if broken |

### Phase 1 — Per-Node Migration (Repeated for MA-2, MA-3)

| Step | Action | Notes |
|---|---|---|
| 1 | Pull SensorML from DO for target node | Already backed up: `sys_04o0.json` (MA-2), `sys_04og.json` (MA-3) + 13 subsystems each |
| 2 | POST top-level system + 13 nested members to Oracle | Same structure as MA-1; UID swap from `az-ma-1` → `az-ma-2`/`az-ma-3` |
| 3 | Skip procedure creation | All 9 procedures already exist on Oracle |
| 4 | Wire `platform@link` on Node 2/Node 3 sub-deployment | `PUT /deployments/{node-N}/platformLink` |
| 5 | Create 7 datastreams with `procedure@link` → existing Oracle procedure IDs | Reuse `0440` (Processing Chain), `043g` (Health), classification proc |
| 6 | Create 4 control streams on Actuator subsystem | Same schema as MA-1 |
| 7 | Pull and replay observations from DO | ~7,465 per node at 50ms throttle + 2s/200 pause |
| 8 | Verify resource counts and observation integrity | Automated verification script |

### Phase 2 — Post-Migration Validation

- Confirm all 3 nodes visible in CSAPI Explorer webapp
- Verify deployment hierarchy: String Alpha → Node 1/2/3 → system links
- Spot-check observation time ranges and counts
- Validate `procedure@link` resolution on all 21 datastreams (7 × 3 nodes)

---

## 7  Backup Inventory for MA-2 / MA-3

### 7.1  Available (Already Backed Up)

| Resource Type | MA-2 | MA-3 |
|---|---|---|
| Top-level SensorML | `sys_04o0.json` | `sys_04og.json` |
| Platform | `sys_04vg.json` | `sys_0560.json` |
| MicArray | `sys_0500.json` | `sys_056g.json` |
| Edge | `sys_050g.json` | `sys_0570.json` |
| Comms | `sys_0510.json` | `sys_057g.json` |
| Power | `sys_051g.json` | `sys_0580.json` |
| Actuator | `sys_0520.json` | `sys_058g.json` |
| Mic1–Mic7 | `sys_052g`–`sys_055g` | `sys_0590`–`sys_05c0` |

### 7.2  Not Yet Backed Up (Must Pull from DO Before Migration)

| Resource Type | Notes |
|---|---|
| Datastream definitions (7 per node) | Can clone from MA-1 schemas, swap UIDs and system references |
| Datastream schemas (7 per node) | Identical to MA-1 — same observation types |
| Control stream definitions (4 per node) | Can clone from MA-1, swap UIDs |
| Control stream schemas (4 per node) | Identical to MA-1 |
| Observations | Must pull live from DO; volume ~7,465 per node |

> **Risk**: If the DO server goes offline before observations are pulled, those time series are lost. **Priority action**: Back up MA-2 and MA-3 observations from DO immediately.

---

## 8  Effort Estimate

| Task | Time |
|---|---|
| Phase 0 (refactor + restructure) | ~1 hour |
| Phase 1 per node (script + execute) | ~1 hour |
| Phase 2 (validation) | ~30 min |
| **Total** | **~3.5 hours** |

This assumes the parameterized script is built from the existing `migrate_az_ma_1.py` with config-driven node selection, removing hardcoded MA-1 references.

---

## 9  Open Questions

1. **Is the DO server (`45.55.99.236:8080`) still online?** If not, observations cannot be pulled live and must be synthetically reconstructed or the time series accepted as lost.
2. **Should the Classification procedure (`04hg` on DO) be migrated?** It's referenced by the Classification Probabilities datastream but wasn't part of the original 9. If it already exists on Oracle under a different ID, datastreams just need the correct `procedure@link`.
3. **Should orphaned procedures (Calibration, Frame Transform) get real descriptions?** Recommended yes, but optional.

---

## Appendix A — Complete DO → Oracle ID Map (MA-1)

From `migration_id_map.json`:

| Resource | DO ID | Oracle ID |
|---|---|---|
| Proc: PDM MEMS | `0480` | `040g` |
| Proc: SRP-PHAT | `048g` | `0410` |
| Proc: Particle Filter | `0490` | `041g` |
| Proc: Triangulation | `049g` | `0420` |
| Proc: Config Actuation | `04a0` | `042g` |
| Proc: Calibration | `04b0` | `0430` |
| Proc: Health | `04bg` | `043g` |
| Proc: Processing Chain | `04c0` | `0440` |
| Proc: Transform | `04cg` | `044g` |
| Sys: AZ-MA-1 (top) | `04ng` | `0420` |
| Sys: Platform | `04p0` | `042g` |
| Sys: MicArray | `04pg` | `0430` |
| Sys: Edge | `04q0` | `043g` |
| Sys: Comms | `04qg` | `0440` |
| Sys: Power | `04r0` | `044g` |
| Sys: Actuator | `04rg` | `0450` |
| Sys: Mic1–Mic7 | `04s0`–`04v0` | `045g`–`048g` |
| DS: SSL | `07fg2` | `0410` |
| DS: SST | `07g02` | `041g` |
| DS: LOB | `07gg2` | `0420` |
| DS: Track Updates | `07h02` | `042g` |
| DS: Classification | `07hg2` | `0430` |
| DS: Health | `07i02` | `043g` |
| DS: Scene Summary | `07ig2` | `0440` |
| CS: Calibrate Orientation | `04d0` | `040g` |
| CS: ODAS Config | `04dg` | `0410` |
| CS: Pipeline Control | `04e0` | `041g` |
| CS: Gain Override | `04eg` | `0420` |

## Appendix B — DO System IDs for MA-2 / MA-3

From `new_id_map.json`:

| Role | MA-2 DO ID | MA-3 DO ID |
|---|---|---|
| Top-level | `04o0` | `04og` |
| Platform | `04vg` | `0560` |
| MicArray | `0500` | `056g` |
| Edge | `050g` | `0570` |
| Comms | `0510` | `057g` |
| Power | `051g` | `0580` |
| Actuator | `0520` | `058g` |
| Mic1 | `052g` | `0590` |
| Mic2 | `0530` | `059g` |
| Mic3 | `053g` | `05a0` |
| Mic4 | `0540` | `05ag` |
| Mic5 | `054g` | `05b0` |
| Mic6 | `0550` | `05bg` |
| Mic7 | `055g` | `05c0` |
