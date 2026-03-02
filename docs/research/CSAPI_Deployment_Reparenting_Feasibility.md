# CSAPI Deployment Reparenting Feasibility Analysis

| Field | Value |
|---|---|
| **Date** | 2026-03-02 |
| **Author** | Claude (Opus 4.6) |
| **Status** | Design Analysis |
| **Scope** | Reorganizing deployment hierarchies on OSH; comparison to system reparenting |
| **Related Reports** | See §8 |

---

## 1  Question

> If we build a deployment hierarchy now — say, sensor string as a subdeployment under sensor net — and later want to insert a sensor field between them, how hard is it to move the sensor string to become a subdeployment of the sensor field instead?

And the follow-up:

> Is rearranging deployment relationships easier or harder than rearranging system/subsystem relationships directly?

---

## 2  Background: How Parent-Child Relationships Work in CSAPI

In the Connected Systems API, parent-child relationships for both **systems** and **deployments** are structural, not property-based. The relationship is established by the URL you POST to:

```
POST /deployments/{parentId}/subdeployments    ← creates a child deployment
POST /systems/{parentId}/subsystems            ← creates a child system
```

There is no `parent@link` field on either resource that can be PATCHed to repoint the relationship. **CSAPI does not define a "move" or "reparent" operation for either systems or deployments.**

This means reparenting in either case requires a **delete-and-recreate** cycle. The question is: how much collateral data must be migrated along with the resource being moved?

---

## 3  Reparenting a Deployment (Subdeployment Move)

### 3.1  Scenario

```
BEFORE:                              AFTER:
Sensor Net (deployment)              Sensor Net (deployment)
  └── String Alpha (sub-dep)           └── Sensor Field (sub-dep) ← NEW
        platform@link → MA-1                └── String Alpha (sub-dep) ← MOVED
        7 datastreams with                        platform@link → MA-1
          deployment@link → String Alpha          7 datastreams with
                                                    deployment@link → String Alpha (new ID)
```

### 3.2  Procedure

| Step | Operation | HTTP | Count | Difficulty |
|---|---|---|---|---|
| 1 | GET String Alpha deployment (full representation) | GET | 1 | Trivial |
| 2 | GET all datastreams whose `deployment@link` → String Alpha | GET | 1 | Trivial |
| 3 | Create Sensor Field sub-deployment under Sensor Net | POST | 1 | Trivial |
| 4 | DELETE String Alpha from current location | DELETE | 1 | Trivial |
| 5 | POST String Alpha under Sensor Field (gets **new internal ID**) | POST | 1 | Trivial |
| 6 | PUT each datastream to update `deployment@link` → new String Alpha ID | PUT | 7 | **Cost center** |
| 7 | Verify observations resolve through new deployment scope | GET | 1 | Trivial |

**Total: ~12 API calls** for a single node with 7 datastreams.

### 3.3  What Moves Automatically vs What Needs Updating

| Resource | Needs manual update? | Why |
|---|---|---|
| The deployment itself | Yes — must be deleted and recreated | No reparent API |
| `platform@link` (system → deployment) | Yes — reset on the new deployment | It's a property of the deployment |
| Datastreams | **Yes — `deployment@link` must be updated** | They point to the old deployment ID |
| Observations | **No** | They link to datastreams, not deployments |
| Control streams | **No** | They live on the system, not the deployment |
| Procedures | **No** | They're system-level resources |
| Sampling features | **No** | They're system-level resources |

### 3.4  Open Question: Can You PUT `deployment@link` on an Existing Datastream?

If OSH supports updating `deployment@link` via PUT on a datastream, the procedure is straightforward — 7 PUT requests after the move.

If OSH silently drops `deployment@link` on PUT (like it does with `deployedSystems@link` — see [OSH DeployedSystems Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md)), the fallback procedure per datastream is:

1. GET datastream definition + schema
2. GET all observations from that datastream
3. DELETE the datastream
4. POST new datastream with updated `deployment@link`
5. POST all observations to the new datastream

This is more expensive (~5× more API calls) but still automatable in a single script. A probe to test PUT behavior on `deployment@link` would resolve this uncertainty.

---

## 4  Reparenting a System (Subsystem Move)

### 4.1  Scenario

Suppose instead of using deployments as the organizational layer, you tried to express the sensor net → field → string hierarchy using **systems and subsystems** directly:

```
BEFORE:                                  AFTER:
Sensor Net System (system)               Sensor Net System (system)
  └── String Alpha (subsystem)             └── Sensor Field (subsystem) ← NEW
        7 datastreams                            └── String Alpha (subsystem) ← MOVED
        4 control streams                              7 datastreams
        N thousand observations                        4 control streams
        procedures                                     N thousand observations
        sampling features                              procedures
                                                       sampling features
```

### 4.2  Procedure

| Step | Operation | HTTP | Count | Difficulty |
|---|---|---|---|---|
| 1 | GET String Alpha system (full representation) | GET | 1 | Trivial |
| 2 | GET all datastreams with schemas | GET | 7 | Moderate |
| 3 | GET all control streams with schemas | GET | 4 | Moderate |
| 4 | GET all procedures | GET | ~3 | Trivial |
| 5 | GET all sampling features | GET | ~2 | Trivial |
| 6 | GET all observations from all datastreams | GET | **thousands** | **Very expensive** |
| 7 | GET all commands from all control streams | GET | variable | Moderate |
| 8 | Create Sensor Field subsystem under Sensor Net | POST | 1 | Trivial |
| 9 | DELETE String Alpha system from current location | DELETE | 1 | **Cascading delete risk** |
| 10 | POST String Alpha under Sensor Field (new ID) | POST | 1 | Trivial |
| 11 | POST all datastreams to new system | POST | 7 | Moderate |
| 12 | POST all control streams to new system | POST | 4 | Moderate |
| 13 | POST all procedures to new system | POST | ~3 | Moderate |
| 14 | POST all sampling features to new system | POST | ~2 | Moderate |
| 15 | POST all observations (with new datastream IDs) | POST | **thousands** | **Very expensive** |
| 16 | POST all commands (with new control stream IDs) | POST | variable | Moderate |

**Total: thousands of API calls.** Every resource owned by the system must be backed up, the system deleted, and everything recreated under the new parent.

### 4.3  What Must Move With the System

| Resource | Needs manual migration? | Impact |
|---|---|---|
| The system itself | Yes — must be deleted and recreated | No reparent API |
| All datastreams (definitions + schemas) | **Yes — they are owned by the system** | ~7 resources |
| All observations from all datastreams | **Yes — they are owned by the system's datastreams** | **Thousands of records** |
| All control streams (definitions + schemas) | **Yes — owned by the system** | ~4 resources |
| All commands | **Yes — owned by the control streams** | Variable |
| All procedures | **Yes — owned by the system** | ~3 resources |
| All sampling features | **Yes — owned by the system** | ~2 resources |
| All links (system@link, procedure@link, etc.) | **Yes — all internal IDs change** | Every cross-reference breaks |

### 4.4  Cascading Delete Risk

When you DELETE a system, OSH may cascade-delete all owned resources (datastreams, observations, control streams, commands). If you haven't backed everything up first, **the data is gone**.

We encountered exactly this risk in the MA-1 migration — the migration script (`migrate_az_ma_1.py`) includes extensive backup phases precisely because system deletion is destructive.

---

## 5  Head-to-Head Comparison

| Factor | Reparent a Deployment | Reparent a System |
|---|---|---|
| **API calls (typical 7-DS node)** | ~12 | **Thousands** |
| **Data at risk** | None (observations stay on datastreams) | **All observations, commands** |
| **Cascading delete risk** | Low — deployment has no owned data | **High — system owns everything** |
| **Internal ID changes** | Only the deployment ID | **Everything: system, datastreams, observations, control streams, commands** |
| **Cross-references to fix** | `deployment@link` on ~7 datastreams | `system@link`, `procedure@link`, `deployment@link` on every resource |
| **Downtime during migration** | Minimal — data remains queryable via system | **Full — data must be backed up, deleted, and recreated** |
| **Script complexity** | ~50 lines | **~500+ lines** (comparable to `migrate_az_ma_1.py`) |
| **Automation feasibility** | Easy single-purpose script | Possible but requires full migration framework |

---

## 6  Conclusion: Deployments as a Lightweight Organizational Proxy

**Deployments are dramatically easier to rearrange than systems.**

This is not accidental — it's an inherent property of the CSAPI data model:

- **Systems own data.** A system's identity is entangled with its datastreams, observations, control streams, commands, procedures, and sampling features. Moving a system means moving its entire data lineage.

- **Deployments organize data.** A deployment is a lightweight pointer structure. It carries `platform@link` (pointing to a system) and serves as a `deployment@link` target for datastreams. It does not own the data — it scopes access to it.

This makes deployments an **ideal organizational proxy layer**:

1. **Build your system hierarchy once** — model what physically exists (systems, subsystems, sensors, actuators). This is your stable data-ownership layer.

2. **Use deployments to express operational organization** — sensor nets, sensor fields, sensor strings, node assignments. This is your flexible organizational layer.

3. **When operational organization changes** — reparent deployments (~12 API calls), not systems (thousands of API calls + data migration risk).

### 6.1  The Analogy

Think of systems as filing cabinets (heavy, full of documents) and deployments as organizational charts (lightweight, easy to redraw).

If the Army reorganizes how sensor fields are grouped under sensor nets, you don't need to physically move the filing cabinets — you just redraw the org chart. That's what deployment reparenting gives you.

### 6.2  Practical Implication for ODAS

> **Don't hesitate to build the deployment hierarchy now.**

If you set up:

```
Sensor Net → String Alpha (sub-deployment)
```

and later need:

```
Sensor Net → Sensor Field → String Alpha (sub-deployment)
```

The cost is ~12 API calls and a 50-line script. Compare that to the value you get from day one: per-node observation scoping, clean navigation in the Explorer, and standards-aligned organizational structure.

The deployment layer exists precisely to be rearranged. Use it.

---

## 7  Recommendation: Confirm PUT Behavior on `deployment@link`

The one remaining unknown is whether OSH allows updating `deployment@link` on an existing datastream via PUT. A quick probe (similar to the [deployedSystems probe](OSH_DeployedSystems_Conformance_Probe.md)) would establish:

- **If PUT works**: reparenting cost is ~12 API calls. Trivial.
- **If PUT drops the field**: reparenting cost is ~50-70 API calls (delete/recreate datastreams + re-POST observations). More expensive but still automatable.

This probe should be run before the first reparenting event, not necessarily before building the hierarchy.

---

## 8  Related Reports

| Report | Topic |
|---|---|
| [CSAPI Deployment Modeling Standards Conformance](CSAPI_Deployment_Modeling_Standards_Conformance.md) | `deployedSystems` vs `platform@link` standards analysis; flat vs subdeployment models |
| [OSH DeployedSystems Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md) | Empirical proof that OSH silently drops `deployedSystems@link`; `deployment@link` observation scoping analysis |
| [AZ-MA-2/MA-3 Migration Procedure Analysis](AZ-MA-2_MA-3_Migration_Procedure_Analysis.md) | Migration strategy for the remaining two ODAS nodes; procedure modeling decisions |
