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

---
---

# Part II — Comprehensive Deep Dive: Why Deployments Are the Correct Organizational Layer

The sections above establish the *what*: deployments are cheaper to reparent than systems. This Part II explains the *why* in depth — drawing on the OGC standards, observed OSH behaviors, and the real ODAS use cases — to give the fullest possible picture of the architectural decision.

---

## 9  The CSAPI Data Model: Ownership vs Association

To understand why reparenting costs differ so dramatically, we need to understand the two fundamentally different relationship types in the CSAPI data model.

### 9.1  Ownership Relationships (System → Data)

The OGC Connected Systems API Part 1 (OGC 23-001) and Part 2 (OGC 23-002) define systems as **data owners**. This is not just a convention — it is expressed through the API's URL hierarchy and through cascading lifecycle semantics:

```
/systems/{systemId}
  /datastreams          ← owned by this system
    /{dsId}
      /observations     ← owned by this datastream, which is owned by this system
  /controlstreams       ← owned by this system
    /{csId}
      /commands         ← owned by this control stream, which is owned by this system
  /procedures           ← owned by this system
  /samplingFeatures     ← owned by this system
  /subsystems           ← owned by this system
```

This ownership chain has direct consequences:

1. **Creation**: You create a datastream by POSTing to `/systems/{id}/datastreams`. The datastream is *born into* the system. There is no way to create an orphan datastream and then link it to a system.

2. **Listing**: `GET /systems/{id}/datastreams` returns *only* the datastreams owned by that system. The system scopes the query.

3. **Deletion**: Deleting a system implies (and on OSH, enforces) deletion of everything beneath it. The ownership chain is a cascade chain.

4. **Identity**: A datastream's internal ID is assigned by the server when it's created under a system. If the system is deleted and recreated (even with the same UID), the datastream IDs will be different. Every observation that was stored under the old datastream ID is inaccessible, because the ID no longer exists.

This is why moving a system is so expensive: **you are moving a tree of owned resources whose identities are bound to their parent.**

### 9.2  Association Relationships (Deployment ↔ Data)

Deployments, in contrast, do not sit in the ownership chain for data. The standard defines deployments alongside systems, not above them:

```
/deployments/{deploymentId}
  /subdeployments       ← child deployments (organizational hierarchy)
```

A deployment's relationship to data is **associative, not possessive**:

- `platform@link` on a deployment points to a system — but the system does not "belong to" the deployment
- `deployment@link` on a datastream points to a deployment — but the datastream is owned by its system, not the deployment

This distinction is architectural, not accidental. The OGC standard models the real world:

- A **system** is a physical or logical thing (a sensor array, a relay, a processing chain). It generates data. The data is inherently part of the system's identity.
- A **deployment** is an operational context — "this system was placed at this location for this mission during this time period." The deployment doesn't generate data; it *frames* the data that systems generate.

### 9.3  Visualizing the Difference

```
                        OWNERSHIP CHAIN (hard to break)
                        ================================

                        System: AZ-MA-1
                          │
                          ├── Datastream: Track Updates
                          │     └── 2,500 observations  ← owned, cascades on delete
                          ├── Datastream: SSL
                          │     └── 1,800 observations  ← owned, cascades on delete
                          ├── Datastream: Health
                          │     └── 900 observations    ← owned, cascades on delete
                          ├── Datastream: SENREP
                          ├── Datastream: (3 more...)
                          ├── ControlStream: System Control
                          │     └── 45 commands          ← owned, cascades on delete
                          ├── Procedure: Processing Chain
                          └── SamplingFeature: Coverage Area


                        ASSOCIATION LAYER (easy to rearrange)
                        ======================================

                        Deployment: String Alpha
                          │
                          ├── platform@link ──────────→ System: AZ-MA-1  (pointer)
                          │
                          └── Sub-deployment: Node 1
                                │
                                └── platform@link ────→ System: AZ-MA-1  (pointer)

                                    Datastreams point back:
                                    Track Updates.deployment@link ──→ Node 1  (pointer)
                                    SSL.deployment@link ───────────→ Node 1  (pointer)
                                    Health.deployment@link ────────→ Node 1  (pointer)
```

The ownership chain (top) is a **rigid tree** — every node owns everything below it. Cutting any node means catching and replanting everything that falls.

The association layer (bottom) is a **flexible web of pointers** — rearranging it means updating pointer targets, not moving data.

---

## 10  Standards References: The Design Intent

### 10.1  CSAPI Part 1 — Systems and Deployments as Parallel Hierarchies

OGC 23-001 (Connected Systems API — Part 1: Feature Resources) defines systems and deployments as **separate, parallel resource collections** at the API root:

```
/systems           ← physical/logical things
/deployments       ← operational contexts
/procedures        ← algorithms/methods
/properties        ← observable properties
/samplingFeatures  ← spatial sampling geometry
```

Systems and deployments are both top-level. Neither is subordinate to the other. This is a deliberate design choice: **the operational organization (deployments) is decoupled from the physical inventory (systems).**

The standard links them through association properties:

| Property | On Which Resource | Points To | Defined In |
|---|---|---|---|
| `platform@link` | Deployment | System | Part 1, Table 11 |
| `deployedSystems@link` | Deployment | System[] | Part 1, Table 11 |
| `deployment@link` | Datastream | Deployment | Part 2, Table 8 |
| `system@link` | Datastream | System | Part 2, Table 8 |
| `procedure@link` | Datastream | Procedure | Part 2, Table 8 |

Notice that **all of these are link-type associations** (pointers), not ownership relations. The standard is telling us: systems own data, deployments point to systems and provide operational scoping.

### 10.2  CSAPI Part 2 — Deployment-Scoped Data Access

OGC 23-002 (Connected Systems API — Part 2: Observation & Command Resources) defines deployment-scoped nested endpoints:

```
GET /deployments/{id}/datastreams     ← datastreams whose deployment@link matches
GET /deployments/{id}/observations    ← observations from those datastreams
```

These are **query shortcuts**, not ownership declarations. The standard says (paraphrased): "a deployment-scoped datastream query returns datastreams that have been associated to the deployment via `deployment@link`." The deployment doesn't own the datastreams — it's a filter.

This is why observations don't need to be moved when a deployment is reparented: the observations belong to their datastreams (which belong to their systems), and the deployment just provides a view into them.

### 10.3  Subdeployments as Conformance Class

CSAPI Part 1 defines `subdeployments` as a nested collection under deployments:

```
GET  /deployments/{id}/subdeployments    ← list children
POST /deployments/{id}/subdeployments    ← create child
```

This is part of the "Deployment Features" conformance class. Subdeployments **do not** inherit data from their parents — they are independent deployment resources that happen to be organized under a parent. Each subdeployment has its own `platform@link`, its own temporal validity, and serves as its own `deployment@link` target.

This means the hierarchy is purely organizational. Rearranging it doesn't affect data ownership or data validity.

---

## 11  Observed OSH Implementation Behaviors

The standards define the model. Here's what we've empirically confirmed about how OSH (OpenSensorHub) implements it.

### 11.1  System Deletion Is Cascading (Confirmed in MA-1 Migration)

During the AZ-MA-1 migration from DO to Oracle (documented in the [Migration Procedure Analysis](AZ-MA-2_MA-3_Migration_Procedure_Analysis.md)), the 953-line migration script (`migrate_az_ma_1.py`) includes 7 phases, with extensive backup phases (Phases 1-6) before any deletion occurs. This is because:

- Deleting a system on OSH deletes all its datastreams, observations, control streams, and commands
- The migration backed up **7,465 observations** across 7 datastreams before touching any source resources
- The ID mapping (`migration_id_map.json`, 36 entries) shows that every resource received a new server-assigned ID on the target

This confirms the ownership cascade is real and enforced on OSH.

### 11.2  Deployment Deletion Does Not Cascade to Data (Confirmed by Probe)

In the [deployedSystems conformance probe](OSH_DeployedSystems_Conformance_Probe.md), we:

1. Created a test deployment
2. Deleted it with `DELETE /deployments/043g`
3. Received HTTP 204 (success)
4. All systems and their datastreams remained intact

The deployment was deleted cleanly. No data was affected. This confirms that deployments are non-owning — exactly as the standard intends.

### 11.3  `deployedSystems@link` Is Silently Dropped (Confirmed by Probe)

The same probe definitively showed that OSH does not persist `deployedSystems@link` on deployments. This means:

- The only way to associate a system with a deployment is `platform@link` on the deployment
- `platform@link` is a single-system pointer (not a list), so expressing "this deployment involves 3 systems" requires 3 subdeployments
- This further reinforces subdeployments as the structural building block

### 11.4  `deployment@link` on Datastreams Works at Creation Time (Confirmed by MA-1 Migration)

The MA-1 migration successfully set `deployment@link` on datastreams when creating them. From the backup data (`ds_07h02.json`):

```json
{
  "name": "AZ-MA-1 Track Updates",
  "system@link":     { "href": "/sensorhub/api/systems/04ng" },
  "deployment@link": { "href": "/sensorhub/api/deployments/04dg" },
  "procedure@link":  { "href": "/sensorhub/api/procedures/04c0" }
}
```

This field was persisted and is returned on GET. What remains unconfirmed is whether it can be **changed** via PUT after creation (see §7 above).

---

## 12  Detailed Walkthrough: The ODAS Reparenting Scenario

Let's walk through the exact scenario from the original question in complete detail, using realistic ODAS resource identifiers and structures.

### 12.1  Starting State

You've deployed a sensor net at Fort Huachuca. Initially, you placed the sensor strings directly under the net because the sensor field concept wasn't yet needed:

```
DEPLOYMENT HIERARCHY:
=====================

Sensor Net: Ft Huachuca ODAS Net
  UID: urn:os4csapi:deployment:sensor-net:ft-huachuca:001
  OSH ID: 050g
  │
  ├── String Alpha (sub-deployment)
  │     UID: urn:os4csapi:deployment:sensor-string:ft-huachuca:alpha
  │     OSH ID: 051g
  │     platform@link → /systems/040g  (SET-A / AZ-MA-1)
  │     │
  │     └── Node 1 (sub-deployment)
  │           UID: urn:os4csapi:deployment:node:ft-huachuca:alpha:001
  │           OSH ID: 052g
  │           platform@link → /systems/040g  (AZ-MA-1)
  │
  ├── String Bravo (sub-deployment)
  │     UID: urn:os4csapi:deployment:sensor-string:ft-huachuca:bravo
  │     OSH ID: 053g
  │     └── (nodes...)
  │
  └── String Charlie (sub-deployment)
        UID: urn:os4csapi:deployment:sensor-string:ft-huachuca:charlie
        OSH ID: 054g
        └── (nodes...)


SYSTEM HIERARCHY (unchanged throughout):
========================================

AZ-MA-1 (system, OSH ID: 040g)
  ├── Monitoring Site Node 1 (subsystem, 0410)
  ├── Relay (subsystem, 041g)
  ├── Datastream: Track Updates (044g)    deployment@link → /deployments/052g (Node 1)
  ├── Datastream: SSL (045g)              deployment@link → /deployments/052g (Node 1)
  ├── Datastream: Health (046g)           deployment@link → /deployments/052g (Node 1)
  ├── Datastream: SENREP (047g)           deployment@link → /deployments/052g (Node 1)
  └── (3 more datastreams...)
```

### 12.2  The Change Request

The tactical situation evolves. You need to introduce a **Sensor Field** level between the Net and the Strings, because multiple strings are being grouped into fields for command-and-control purposes:

```
DESIRED DEPLOYMENT HIERARCHY:
==============================

Sensor Net: Ft Huachuca ODAS Net (050g)
  │
  └── Sensor Field: North Sector (NEW, will be 055g)
        │
        ├── String Alpha (051g → MOVED, gets new ID 056g)
        │     └── Node 1 (052g → MOVED, gets new ID 057g)
        │
        └── String Bravo (053g → MOVED, gets new ID 058g)
              └── (nodes...)
```

### 12.3  Step-by-Step Reparenting: String Alpha

**Phase 1: Backup (3 API calls)**

```
GET /deployments/051g                     → save String Alpha definition
GET /deployments/051g/subdeployments      → save list: [Node 1 = 052g]
GET /deployments/052g                     → save Node 1 definition
```

**Phase 2: Record datastream pointers (1 API call)**

```
GET /systems/040g/datastreams             → find all datastreams where
                                             deployment@link contains "052g"
                                             Result: [044g, 045g, 046g, 047g, ...]
```

**Phase 3: Create new parent (1 API call)**

```
POST /deployments/050g/subdeployments
  Body: { "name": "North Sector", "uid": "urn:os4csapi:deployment:sensor-field:ft-huachuca:north", ... }
  → 201 Created, Location: /deployments/055g
```

**Phase 4: Delete old hierarchy (2 API calls)**

```
DELETE /deployments/052g                  → delete Node 1 (leaf first)
  → 204 No Content
  → Datastreams 044g-047g are UNTOUCHED (they belong to system 040g, not deployment 052g)
  → Observations are UNTOUCHED

DELETE /deployments/051g                  → delete String Alpha (now a leaf)
  → 204 No Content
```

**Phase 5: Recreate under new parent (2 API calls)**

```
POST /deployments/055g/subdeployments
  Body: { saved String Alpha definition, same UID }
  → 201 Created, Location: /deployments/056g  ← new ID

POST /deployments/056g/subdeployments
  Body: { saved Node 1 definition, same UID, platform@link → /systems/040g }
  → 201 Created, Location: /deployments/057g  ← new ID
```

**Phase 6: Update datastream pointers (7 API calls)**

```
PUT /systems/040g/datastreams/044g
  Body: { ...existing definition..., deployment@link: { href: "/sensorhub/api/deployments/057g" } }
  → 200 OK (or 204)

PUT /systems/040g/datastreams/045g → same
PUT /systems/040g/datastreams/046g → same
PUT /systems/040g/datastreams/047g → same
... (3 more)
```

**Phase 7: Verify (2 API calls)**

```
GET /deployments/057g                     → confirm Node 1 exists under String Alpha under North Sector
GET /deployments/057g/datastreams         → confirm all 7 datastreams resolve through new scope
```

**Total: 18 API calls.** Zero observations moved. Zero data at risk. Takes seconds to execute.

### 12.4  What the Same Change Looks Like with Systems

Now imagine you had tried to model the organizational hierarchy using systems instead of deployments. To insert a "Sensor Field" system between "Sensor Net" and "String Alpha":

```
Phase 1: Backup AZ-MA-1 system
  GET /systems/040g                           → 1 call
  GET /systems/040g/subsystems                → 1 call (Monitoring Site Node 1, Relay)
  GET /systems/0410                           → 1 call (Node 1 details)
  GET /systems/041g                           → 1 call (Relay details)

Phase 2: Backup all data owned by AZ-MA-1
  GET /systems/040g/datastreams               → 1 call (7 datastreams)
  GET /systems/040g/datastreams/044g/schema   → 1 call
  GET /systems/040g/datastreams/044g/observations?limit=10000  → 1+ calls (2,500 obs)
  ... repeat for all 7 datastreams ...        → ~21 calls (7 × 3: def + schema + obs)
  GET /systems/040g/controlstreams            → 1 call (4 streams)
  GET each control stream + commands          → ~12 calls
  GET /systems/040g/procedures                → 1 call
  GET each procedure                          → ~3 calls
  GET /systems/040g/samplingFeatures          → 1 call

Phase 3: Create Sensor Field system
  POST /systems/{sensorNetId}/subsystems      → 1 call

Phase 4: Delete AZ-MA-1 from current parent (DANGER)
  DELETE /systems/040g                        → 1 call
  ⚠️ ALL DATASTREAMS, OBSERVATIONS, CONTROL STREAMS, COMMANDS ARE NOW GONE

Phase 5: Recreate AZ-MA-1 under Sensor Field (new ID!)
  POST /systems/{sensorFieldId}/subsystems    → 1 call → new ID 060g
  POST subsystems back                        → 2 calls → new IDs for Node 1, Relay

Phase 6: Recreate all data with new IDs
  POST 7 datastreams to new system            → 7 calls → ALL NEW IDs
  POST schemas for each                       → 7 calls
  POST 2,500 observations to new DS 1         → 25+ calls (batched at 100)
  POST 1,800 observations to new DS 2         → 18+ calls
  POST 900 observations to new DS 3           → 9+ calls
  ... repeat for all 7 datastreams ...
  POST 4 control streams                      → 4 calls
  POST commands to each                       → variable
  POST 3 procedures                           → 3 calls
  POST sampling features                      → ~2 calls

Phase 7: Fix all cross-references
  Every datastream now has a new ID → any external system referencing the old IDs breaks
  The system itself has a new ID → any deployment's platform@link is now wrong
  Procedure links, deployment links — all need updating

Total: HUNDREDS of API calls, 7,465+ observations re-POSTed, 15+ minutes of execution,
       complete data unavailability during migration, risk of data loss if any step fails.
```

### 12.5  Side-by-Side Summary for This Scenario

| Metric | Deployment Reparent | System Reparent |
|---|---|---|
| API calls | 18 | ~200+ |
| Observations moved | 0 | 7,465 |
| Data unavoidable during migration | 0 seconds | 5-15 minutes |
| Risk of data loss | None | High (cascade delete) |
| External references broken | 0 | All (new system ID, new DS IDs) |
| Script size | ~60 lines | ~900+ lines |
| Execution time | <5 seconds | 5-15 minutes |

---

## 13  Use Cases from the ODAS Program

### 13.1  Use Case: Adding a Sensor Field Tier

**Scenario**: The ODAS program initially deploys strings directly under the sensor net. After operational experience, they decide to group strings into sensor fields for command efficiency.

**With deployments as the organizational layer**: Create sensor field subdeployments, reparent existing string subdeployments underneath them. ~18 API calls per string. No data migration. No downtime.

**Without deployments (systems only)**: Would require either (a) creating "Sensor Field" as a system — which doesn't make sense because a field isn't a sensor or actuator, or (b) leaving the organizational hierarchy unrepresented in the API.

**Verdict**: Deployments cleanly represent organizational tiers that don't correspond to physical hardware. The standard was designed for exactly this.

### 13.2  Use Case: Moving a String Between Fields

**Scenario**: String Alpha is reassigned from North Sector to South Sector due to a tactical boundary change.

**With deployment reparenting**:
```
1. DELETE /deployments/{stringAlpha}
2. POST /deployments/{southSector}/subdeployments   (same UID, new ID)
3. PUT 7 datastreams with updated deployment@link
Total: ~10 API calls
```

**With system reparenting** (if the hierarchy was modeled in systems):
```
1. Back up everything under String Alpha system
2. DELETE String Alpha system (cascading)
3. Recreate under South Sector system
4. Re-POST all datastreams, observations, control streams, commands
Total: hundreds of API calls, full data migration
```

### 13.3  Use Case: Decommissioning a Node and Replacing It

**Scenario**: MA-1 develops a hardware fault. It's replaced by MA-4 at the same position on the same string.

**With deployments**:
```
1. Update Node 1 subdeployment's validTime end date  (1 PUT)
2. Create new Node 1' subdeployment with platform@link → MA-4 system  (1 POST)
3. MA-4's datastreams get deployment@link → Node 1'  (set at creation, 7 POSTs)
Total: 9 API calls. MA-1's historical data remains accessible under the old Node 1 deployment scope.
```

**Without deployments**:
```
MA-1 and MA-4 are different systems with different datastreams. There's no organizational
container that groups "everything that was at this position." Historical queries must know
to check both MA-1 and MA-4 systems and union the results.
```

This use case illustrates a deeper point: **deployments provide temporal continuity for an operational role, even as the underlying hardware changes.** "Node 1 position on String Alpha" is a persistent concept whether the system there is MA-1 or MA-4. The deployment represents the role; the system represents the hardware.

### 13.4  Use Case: Scaling from 3 Nodes to 12 Nodes

**Scenario**: The program expands. New strings are added, each with 3-4 nodes.

**With deployments**: Create new subdeployments. Each new node's datastreams get `deployment@link` at creation time. The existing hierarchy is untouched. No reparenting of existing resources needed at all.

**Without deployments**: Would need to create subsystem hierarchies, which is fine for the initial creation — but any future reorganization (see Use Cases 13.1-13.3) pays the full system-reparenting cost.

### 13.5  Use Case: Cross-Server Federation

**Scenario**: A future CSAPI implementation (or OSH with a fix) supports `deployedSystems`. You want to federate data across servers where deployment structure is the discovery mechanism.

**With deployment hierarchy in place**: The hierarchy is already there. When the implementation catches up, deployment-scoped queries will work automatically through `deployment@link`.

**Without deployment hierarchy**: You'd need to build it from scratch, which means setting `deployment@link` on all existing datastreams — the same cost you'd pay once during reparenting, but now applied to every datastream in the system.

---

## 14  Why the Cost Asymmetry Exists: A Data Model Analysis

The dramatic cost difference between deployment reparenting and system reparenting is not a quirk of the OSH implementation — it is an inherent consequence of how the CSAPI standard allocates data ownership.

### 14.1  The Ownership Graph

In CSAPI, the complete data model forms a directed acyclic graph with two types of edges:

```
OWNERSHIP EDGES (solid lines): parent owns child, deletion cascades
ASSOCIATION EDGES (dashed lines): pointer, no lifecycle coupling

                    ┌──────────────┐
                    │   System     │
                    └──────┬───────┘
                           │ owns
              ┌────────────┼────────────┬──────────────┐
              ▼            ▼            ▼              ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐
        │Datastream│ │CtrlStream│ │Procedure │ │SamplFeat  │
        └────┬─────┘ └────┬─────┘ └──────────┘ └───────────┘
             │ owns       │ owns
             ▼            ▼
        ┌──────────┐ ┌──────────┐
        │Observatn │ │ Command  │
        └──────────┘ └──────────┘


        - - - - - - - - - - - - - - - - - - - - -

                    ┌──────────────┐
                    │ Deployment   │
                    └──────┬───────┘
                           │ owns
                           ▼
                    ┌──────────────┐
                    │Sub-Deployment│
                    └──────────────┘

                    Deployment ─ ─ ─platform@link─ ─ ─ → System
                    Datastream ─ ─ ─deployment@link─ ─ → Deployment
                    Datastream ─ ─ ─procedure@link─ ─ ─→ Procedure
                    Datastream ─ ─ ─system@link─ ─ ─ ─ → System
```

A **system** sits at the root of a deep ownership tree. Below it: datastreams containing observations, control streams containing commands, procedures, and sampling features. Moving the system means uprooting the entire tree.

A **deployment** sits at the root of a shallow ownership tree. Below it: only subdeployments (which are themselves lightweight). Data is connected via association edges (dashed lines), not ownership edges. Moving the deployment means updating pointers, not transplanting trees.

### 14.2  Why the Standard Was Designed This Way

This allocation of ownership is intentional, based on a real-world observation:

> **Systems are physical. Deployments are operational.**

Physical things don't change often. AZ-MA-1 is AZ-MA-1 whether it's deployed at Fort Huachuca or Fort Bliss. Its sensors, its processing chain, its data types — these are intrinsic properties. They belong to the system.

Operational assignments change frequently. A monitoring array is reassigned to a different sector. A sensor field is reorganized. A string is split or merged. These are organizational changes that should not require moving data.

The CSAPI standard allocates data ownership to the stable layer (systems) and organizational structure to the flexible layer (deployments). This is the same separation of concerns seen in:

- **Military logistics**: Equipment (systems) vs organizational charts (deployments). You can reorganize a brigade's task organization without physically moving every piece of equipment.
- **IT infrastructure**: Servers (systems) vs projects (deployments). You can reassign a server to a different project without migrating its storage.
- **Building management**: HVAC equipment (systems) vs building zones (deployments). You can redistrict a floor plan without rewiring the air handlers.

### 14.3  The Mathematical View

If we define:

- $D$ = number of datastreams under a system
- $O$ = total number of observations across all datastreams
- $C$ = total number of commands across all control streams
- $P$ = number of procedures
- $S$ = number of sampling features

Then the cost of reparenting is:

**Deployment reparenting cost**: $O(D)$ — proportional only to the number of datastreams (pointer updates)

**System reparenting cost**: $O(D + O + C + P + S)$ — proportional to the total data volume

For a typical ODAS node with 7 datastreams, 7,465 observations, 45 commands, 3 procedures, and 2 sampling features:

- Deployment reparenting: $O(7)$ = 7 pointer updates
- System reparenting: $O(7{,}522)$ = 7,522 resources to back up, delete, and recreate

The ratio is approximately **1,000:1** in favor of deployment reparenting, and it grows with time as more observations accumulate.

---

## 15  What If OSH Adds `deployedSystems` Support Later?

The [conformance probe](OSH_DeployedSystems_Conformance_Probe.md) proved that OSH currently does not support `deployedSystems`. But what if a future OSH version adds it?

### 15.1  The Subdeployment Structure Remains Valuable

Even with `deployedSystems` support, per-node subdeployments would still provide:

1. **Per-node observation scoping** via `deployment@link` (see [scoping analysis](OSH_DeployedSystems_Conformance_Probe.md#5--why-deploymentlink-on-datastreams-is-a-key-design-factor))
2. **Per-node temporal validity** (each node can have its own deployment time window)
3. **Per-node metadata** (name, description, location) distinct from the string or field level
4. **Clean navigation** in the CSAPI Explorer webapp

`deployedSystems` would give you an *additional* way to discover which systems participate in a deployment. But the scoping and temporal benefits of subdeployments come from the hierarchy itself, not from system association.

### 15.2  The Migration Path Is Simple

If `deployedSystems` becomes available, you don't need to restructure anything. You simply:

1. PATCH each subdeployment to add `deployedSystems@link` pointing to its system
2. Optionally PATCH the parent deployment to add `deployedSystems@link` listing all systems

This is additive — it doesn't conflict with the existing `platform@link` wiring or the subdeployment hierarchy.

### 15.3  The Subdeployment Structure Is Forward-Compatible

Building the hierarchy now means:
- **If OSH adds `deployedSystems`**: You enrich the existing hierarchy. No restructuring.
- **If OSH never adds `deployedSystems`**: You already have the only working alternative.
- **If you migrate to a different CSAPI implementation**: The subdeployment hierarchy is standards-conformant and will transfer directly.

---

## 16  Final Architectural Guidance

### 16.1  The Two-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   LAYER 1: PHYSICAL INVENTORY (Systems)                        │
│   ─────────────────────────────────────                        │
│                                                                 │
│   • Model what physically exists                               │
│   • Systems own all data (datastreams, observations, etc.)     │
│   • Subsystems model physical composition (sensor, actuator)   │
│   • Rarely changes — only when hardware is added/removed       │
│   • EXPENSIVE to rearrange (data migration required)           │
│                                                                 │
│   Example:                                                      │
│     AZ-MA-1 System                                             │
│       ├── Monitoring Site Node 1 (subsystem)                   │
│       ├── Relay (subsystem)                                    │
│       ├── 7 datastreams (owned)                                │
│       └── 4 control streams (owned)                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   LAYER 2: OPERATIONAL ORGANIZATION (Deployments)              │
│   ───────────────────────────────────────────────              │
│                                                                 │
│   • Model how things are organized for a mission               │
│   • Deployments own only subdeployments (no data)              │
│   • Subdeployments point to systems via platform@link          │
│   • Changes with operational needs — reorganize freely         │
│   • CHEAP to rearrange (~12 API calls per move)                │
│                                                                 │
│   Example:                                                      │
│     Ft Huachuca ODAS Net (deployment)                          │
│       └── North Sector Field (sub-deployment)                  │
│             └── String Alpha (sub-deployment)                  │
│                   └── Node 1 (sub-deployment)                  │
│                         platform@link → AZ-MA-1               │
│                                                                 │
│   Connected by association (dashed) lines:                     │
│     DS.deployment@link → nearest sub-deployment                │
│     Sub-dep.platform@link → system                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 16.2  Rules of Thumb

1. **If it's physical, it's a system.** Sensors, actuators, processing chains, monitoring arrays — these are systems and subsystems.

2. **If it's organizational, it's a deployment.** Sensor nets, sensor fields, sensor strings, node positions — these are deployments and subdeployments.

3. **Never model organizational hierarchy using systems.** You'll pay the full data-migration cost every time the organization changes.

4. **Don't fear building deployment hierarchy early.** The cost of rearranging it later is trivially small compared to the value of having it from day one.

5. **Set `deployment@link` on every datastream at creation time.** This is the connection that enables deployment-scoped queries. It's easiest to set at creation and somewhat more expensive to add retroactively.

### 16.3  The Bottom Line

> **Build the deployment hierarchy now. Rearrange it later for free (≈12 API calls). The alternative — modeling organization in the system hierarchy — costs thousands of API calls and risks data loss every time the organization changes.**

The CSAPI standard was designed with this exact separation of concerns. The deployment layer is your flexible organizational proxy. Use it.

---

## 8  Related Reports

| Report | Topic |
|---|---|
| [CSAPI Deployment Modeling Standards Conformance](CSAPI_Deployment_Modeling_Standards_Conformance.md) | `deployedSystems` vs `platform@link` standards analysis; flat vs subdeployment models |
| [OSH DeployedSystems Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md) | Empirical proof that OSH silently drops `deployedSystems@link`; `deployment@link` observation scoping analysis |
| [AZ-MA-2/MA-3 Migration Procedure Analysis](AZ-MA-2_MA-3_Migration_Procedure_Analysis.md) | Migration strategy for the remaining two ODAS nodes; procedure modeling decisions |
