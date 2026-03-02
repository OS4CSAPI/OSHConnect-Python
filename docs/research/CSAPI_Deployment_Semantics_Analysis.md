# Semantic Analysis: What Is a CSAPI Deployment When Paired 1:1 with a System?

| Field | Value |
|---|---|
| **Date** | 2026-03-02 |
| **Author** | Claude (Opus 4.6) |
| **Status** | Ontological / Semantic Analysis |
| **Scope** | Precise meaning of a Deployment resource when used as a "deployed system" proxy |
| **Related Reports** | See §8 |

---

## 1  The Question

When we follow the [1:1 system-deployment pairing pattern](CSAPI_Deployed_Systems_Design_Pattern.md) — creating a deployment for every operationally significant system — what exactly *is* that deployment resource?

Is it:
- A deployment **of** that system?
- A deployment **for** that system?
- A representation of that system's **deployed state**?
- Effectively, a **deployed system**?

The semantics determine how users, developers, and standards bodies should think about and talk about the resource. Getting this wrong leads to wrong expectations about lifecycle, data ownership, and deletion behavior.

---

## 2  What the Ontology Says

CSAPI is built on the **SOSA/SSN ontology** (W3C/OGC Semantic Sensor Network Ontology). In SOSA:

> **`sosa:Deployment`** — *"Describes the Deployment of one or more Systems for a particular purpose."*

In pure SOSA, a Deployment is an **activity** — the *act* of deploying. It is a verb dressed up as a noun. "The deployment of MA-1 to Node 1" is an event that happened, with a start time, a location, and a purpose.

This is a common pattern in ontologies: reifying an activity as a class so it can carry properties. The activity "deploying MA-1" becomes the thing "Deployment X" so you can attach temporal extent, spatial location, and relationships to it.

---

## 3  What the REST API Does to That Concept

CSAPI takes the SOSA activity concept and reifies it further — as a **persistent GeoJSON Feature** with:

- A server-assigned **ID** (e.g., `057g`)
- A stable **UID** (e.g., `urn:os4csapi:deployment:node:ft-huachuca:alpha:001`)
- **Geometry** (point, polygon, etc.)
- **Temporal extent** (`validTime`)
- **Named properties** (`name`, `description`, `featureType`)
- **Association links** (`platform@link` → system)
- **Nested sub-resources** (`subdeployments`)
- **Query scoping behavior** (deployment-scoped datastreams and observations via `deployment@link`)

The moment you do this, the semantics shift. It is no longer just "something that happened" — it is a **standing record** that exists as long as the operational assignment is active, and persists as historical record after the assignment ends.

This is a subtle but critical transformation:

| Concept | SOSA Ontology | CSAPI REST API |
|---|---|---|
| Nature | Activity (verb-as-noun) | Persistent Feature resource (noun) |
| Identity | Implicit | Server-assigned ID + stable UID |
| Lifecycle | Instantaneous or bounded | Created, updated, persists after `validTime` ends |
| Queryability | SPARQL triple patterns | REST endpoints, GeoJSON, nested collections |
| Behavior | None (data only) | Scopes observation queries, supports subdeployment hierarchy |

A REST resource has **identity, state, and persistence**. An activity doesn't. By making Deployment a first-class REST resource, the standard turned "the act of deploying" into "the record of an operational assignment" — and gave it behavior (query scoping) that activities don't have.

---

## 4  Evaluating Each Candidate Interpretation

### 4.1  "A deployment OF that system"

This is the **grammatically faithful** reading of the standard's language: "a Deployment describes the deployment of one or more systems."

**What it captures correctly:**
- The deployment is fundamentally about the system — the system is the subject of the activity
- The system pre-exists the deployment (you deploy something that already exists)
- Multiple deployments can exist for the same system (MA-1 deployed to Node 1 in January, Node 2 in July)

**What it misses:**
- It frames the deployment as a **historical record** — documentation of something that happened
- It doesn't capture the ongoing operational relevance — users don't want to browse "things that happened to MA-1," they want to see what MA-1 is doing *now, in its current role*
- The "of" preposition makes the deployment subordinate to the system, when in practice the deployment is the user-facing entity and the system is the implementation detail

**Verdict:** Accurate to the ontology but underserves the user's mental model. This framing relegates the deployment to documentation rather than operational interface.

### 4.2  "A deployment FOR that system"

This implies the deployment is a **container or slot** that was prepared, and the system was placed into it. "We set up a deployment for MA-1."

**What it captures correctly:**
- There's a sense of intentionality — someone decided this system should be fielded
- The deployment has its own preparatory lifecycle (location chosen, role defined, timeline established)

**What it gets wrong:**
- It inverts the dependency. It suggests the deployment exists first and the system fills it, like an empty socket waiting for a plug
- In practice, deployments are created *because* a system is being fielded — the system is the cause, the deployment is the effect
- The `platform@link` goes from deployment → system, not the other way around. The deployment references the system; the system doesn't reference the deployment
- It implies the deployment exists in service of the system, when actually the deployment serves the *operational mission*

**Verdict:** Misleading. It suggests the deployment has independent existence without a system, and inverts the causal relationship.

### 4.3  "A representation of that system's deployed state"

This frames the deployment as a **state descriptor** — metadata about the system's current operational condition.

**What it captures correctly:**
- The deployment does capture where the system is, when it was placed there, and what role it fills
- That is indeed the system's "deployed state" — the set of facts that are true about its current fielded condition
- It correctly implies the deployment is derivative of the system (the state belongs to the system)

**What it misses:**
- "State" implies a snapshot or a property — something that lives *on* the system
- But the deployment is a **separate first-class resource** with its own identity, its own hierarchy (subdeployments), and its own query-scoping behavior
- The deployment isn't just a description of the system — it has its own capabilities:
  - It can be a parent of subdeployments
  - It scopes observation queries via `deployment@link`
  - It has its own temporal extent independent of the system
  - It persists as a historical record after the system is removed
- A "state" doesn't have children, doesn't scope queries, and doesn't persist independently

**Verdict:** Warm, but undersells the deployment's first-class nature. The deployment is more than a state descriptor — it's an independent entity with behavior.

### 4.4  "Effectively, a deployed system"

This is what the user sees. When you click "Node 1 — AZ-MA-1" in the Explorer and see its 7 datastreams and observations, you're looking at *what presents as* a deployed system.

**What it captures correctly:**
- This is the user's mental model, and it's valid for interaction purposes
- The deployment layer *does* serve as the "deployed systems" collection
- Browsing deployments = browsing deployed systems (from the user's perspective)
- Querying a deployment's observations = querying a deployed system's observations

**What it gets dangerously wrong:**
- The deployment is **not literally the system**. They are separate resources with different IDs, different lifecycles, and different ownership semantics
- The deployment **does not own data**. Datastreams belong to the system. Observations belong to datastreams. The deployment merely scopes queries
- **Deleting a deployment does not delete data** — this is a feature, not a bug, but users who think "deployment = deployed system" might expect deletion to decommission the system and purge its data
- **Two deployments can reference the same system** (sequential operational assignments). If "deployment = deployed system," which one is the system?

**Verdict:** Correct from the user's perspective, dangerous from the implementer's perspective. Useful as a presentation-layer abstraction, harmful as a data-model belief.

---

## 5  The Most Precise Interpretation

None of the four candidates fully captures what a 1:1-paired Deployment actually is. The most precise single statement:

> **A Deployment is the operational identity of a system in a specific role, at a specific place, during a specific time.**

### 5.1  Unpacking Each Phrase

**"Operational identity"** — The deployment is how the system is known in the operational context. MA-1 is the hardware identity; "Node 1, String Alpha, North Sector" is the operational identity. The deployment carries the operational identity. Users navigate by operational identity, not hardware identity.

**"Of a system"** — The deployment is anchored to a system via `platform@link`. Without a system, the deployment is an empty role. The system provides the data, the sensors, the processing chain — everything that generates observations. The deployment provides the context in which those observations matter.

**"In a specific role"** — The same physical system (MA-1) can have different operational identities at different times:
- "Node 1 on String Alpha" from January–June
- "Node 2 on String Bravo" from July onward

Each role is a distinct deployment. The system persists across roles; the deployment marks each assignment.

**"At a specific place"** — The deployment has geometry. The system might not have inherent spatiality — a processing chain, for example, has no location. It acquires a location only because it's deployed somewhere. The deployment carries the "where."

**"During a specific time"** — `validTime` bounds the deployment temporally. The system persists indefinitely (it exists whether deployed or sitting in a warehouse). The deployment exists only for the duration of the assignment.

### 5.2  The Two-Layer Mental Model

This interpretation produces a clean separation:

```
┌─────────────────────────────────────────────────┐
│  SYSTEM = "what it is"                          │
│                                                 │
│  • Permanent (exists from manufacture onward)   │
│  • Hardware-bound identity (serial number, UID) │
│  • Owns all data (datastreams, observations)    │
│  • Physical composition (subsystems, sensors)   │
│  • Location-agnostic (can be deployed anywhere) │
│  • Time-agnostic (persists through assignments) │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  DEPLOYMENT = "what it's doing"                 │
│                                                 │
│  • Temporal (bounded by validTime)              │
│  • Role-bound identity (position, assignment)   │
│  • Scopes data (deployment@link on datastreams) │
│  • Organizational hierarchy (sub-deployments)   │
│  • Location-specific (where the system is)      │
│  • Mission-specific (why the system is there)   │
└─────────────────────────────────────────────────┘

A "deployed system" is not a single resource — it is the
INTERSECTION of a system and a deployment.

The system provides: data, physical identity, sensors, processing
The deployment provides: role, location, time window, org structure, query scoping
```

### 5.3  If Forced to Choose Two Words

If forced to choose the single most precise two-word label for what a CSAPI Deployment resource is when paired 1:1 with a system:

> **Operational assignment.**

Not the system. Not the act of deploying. Not a container. Not a state. The **assignment** of a system to a role.

An assignment is:
- **Lightweight** — it's a record, not a data store
- **Rearrangeable** — you can reassign without moving data ([~12 API calls](CSAPI_Deployment_Reparenting_Feasibility.md))
- **Temporally bounded** — it has a start and end
- **Organizationally nested** — assignments fit into hierarchies (net → field → string → node)
- **Independently identifiable** — it has its own ID and UID

These are exactly the properties that make the deployment valuable as the user-facing "deployed system" abstraction.

---

## 6  Implications for User-Facing Language

### 6.1  What Users Should Be Told

For **operators and program managers** (non-technical users):

> A deployment is a system's **assignment** — "MA-1 is assigned to Node 1 on String Alpha." The assignment has a location, a time window, and a place in the org chart. The system has the sensors, the data, and the processing chain.

> When you browse "Deployments," you're browsing **operational assignments**. When you click one, you see the data produced by the system during that assignment.

### 6.2  What Developers Should Be Told

For **API consumers and integration developers**:

> A Deployment resource is an operational assignment with query-scoping behavior. It is linked to a system via `platform@link` and serves as a `deployment@link` target for datastreams. Deployment-scoped queries (`GET /deployments/{id}/observations`) return data filtered by the `deployment@link` association, not by data ownership.

> **Critical distinction**: Deployments do not own data. Systems do. Deleting a deployment does not delete observations. Creating a deployment does not create datastreams.

### 6.3  Terminology Guide

| When users say... | They mean... | The API concept is... |
|---|---|---|
| "Deployed system" | A system in its operational role | Deployment + System (intersection) |
| "Where is MA-1?" | Where is it assigned? | Deployment geometry |
| "What is MA-1 seeing?" | Its observations in current assignment | `GET /deployments/{id}/observations` |
| "Move MA-1 to Bravo" | Reassign it | Close old deployment, create new one |
| "Decommission MA-1" | End its assignment | Set `validTime` end on deployment |
| "All deployed systems at Huachuca" | Currently active assignments | `GET /deployments?validTime=now` |
| "MA-1's history" | All its assignments over time | Multiple deployments, same `platform@link` target |
| "Node 1's history" | Everything that happened at that position | Single deployment (or sequence), may span system swaps |

### 6.4  The Subtle but Critical Distinction

Note the difference between the last two rows:

- **"MA-1's history"** = all deployments where `platform@link → MA-1` (follows the hardware)
- **"Node 1's history"** = the deployment(s) with UID `urn:...:node:alpha:001` regardless of which system was wired (follows the role)

The system gives you the hardware lens. The deployment gives you the role lens. Users may want either. The 1:1 pairing pattern supports both queries equally.

---

## 7  How This Resolves the Design Debate

### 7.1  The Ongoing Discussion

Across this series of reports, we've progressively answered a chain of questions:

1. **How should we model the system-deployment relationship?**
   → [Standards Conformance](CSAPI_Deployment_Modeling_Standards_Conformance.md): `platform@link` on subdeployments, not flat `deployedSystems`

2. **Does OSH actually support the flat alternative?**
   → [Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md): No — `deployedSystems@link` is silently dropped

3. **How hard is it to reorganize the hierarchy later?**
   → [Reparenting Feasibility](CSAPI_Deployment_Reparenting_Feasibility.md): ~12 API calls (deployments) vs thousands (systems)

4. **Should we pair every significant system with a deployment?**
   → [Design Pattern](CSAPI_Deployed_Systems_Design_Pattern.md): Yes — deployments become the "deployed systems" view

5. **What exactly IS that paired deployment?** (this report)
   → The operational assignment of a system to a role, with its own identity and query-scoping behavior

### 7.2  How the Semantic Analysis Reinforces the Architecture

Understanding the deployment as an "operational assignment" reinforces every prior decision:

| Decision | How the semantic model supports it |
|---|---|
| Per-node subdeployments | Each node position is a distinct operational assignment |
| `platform@link` wiring | The assignment points to the assignee (system) |
| `deployment@link` on datastreams | Data is tagged with the assignment under which it was produced |
| Subdeployment hierarchy | Assignments nest: net → field → string → node |
| Reparenting = cheap | Reassigning is cheap; moving data is expensive |
| Hardware swap = new assignment | Same position, different system, new (or updated) assignment |
| `validTime` scoping | Assignments are time-bounded; systems are permanent |

### 7.3  What This Means for the CSAPI Explorer

The webapp should present deployments as the primary navigation layer for operational users. The recommended UI language:

- Navigation label: **"Deployed Systems"** (not "Deployments")
- Detail view header: **"Node 1 — AZ-MA-1"** (role + hardware)
- Breadcrumb: **ODAS Net > String Alpha > Node 1**
- Secondary link: **"View System Details →"** (for users who need physical composition)

This gives users the "deployed systems" view they expect while preserving the underlying system/deployment distinction for developers who need to understand data ownership.

---

## 8  Related Reports

| Report | Topic | How It Connects |
|---|---|---|
| [CSAPI Deployment Modeling Standards Conformance](CSAPI_Deployment_Modeling_Standards_Conformance.md) | `deployedSystems` vs `platform@link` standards analysis | Establishes why per-node subdeployments with `platform@link` are correct |
| [OSH DeployedSystems Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md) | Empirical proof that OSH drops `deployedSystems@link` | Proves the flat alternative doesn't work; motivates 1:1 pairing |
| [CSAPI Deployment Reparenting Feasibility](CSAPI_Deployment_Reparenting_Feasibility.md) | Cost of reorganizing deployment vs system hierarchies | Confirms "operational assignments" are cheap to rearrange |
| [Deployed Systems Design Pattern](CSAPI_Deployed_Systems_Design_Pattern.md) | 1:1 system-deployment pairing as a first-class pattern | Establishes the pattern this report provides the semantic foundation for |
| [AZ-MA-2/MA-3 Migration Procedure Analysis](AZ-MA-2_MA-3_Migration_Procedure_Analysis.md) | Migration strategy for remaining ODAS nodes | Practical context where these semantic decisions apply |
