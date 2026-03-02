# Deployments as First-Class "Deployed Systems": Design Pattern Analysis

| Field | Value |
|---|---|
| **Date** | 2026-03-02 |
| **Author** | Claude (Opus 4.6) |
| **Status** | Design Pattern Recommendation |
| **Scope** | Using CSAPI Deployments as the primary user-facing "deployed system" abstraction |
| **Related Reports** | See §8 |

---

## 1  Problem Statement

The OGC Connected Systems API defines `Systems` and `Deployments` as separate first-class resource types. Systems own all data (datastreams, observations, control streams, commands). Deployments provide operational context (where, when, why a system was fielded).

However, the user base — particularly military operators and program managers — thinks in terms of **deployed systems**: "What is MA-1 doing at Node 1 right now?" They don't naturally separate the hardware identity from its operational role.

The CSAPI standard does not define a resource called "Deployed System." But **does it need to?** This report argues that the existing `Deployment` resource, when paired 1:1 with an operationally significant system, *is* the "deployed system" concept — and that both the standard and the OSH implementation fully support this pattern.

---

## 2  The Proposed Pattern: 1:1 System-Deployment Pairing

For every operationally significant system, create a corresponding deployment (or subdeployment) that serves as its **operational face**:

```
USER-FACING LAYER (Deployments)             DATA LAYER (Systems)
════════════════════════════════             ═══════════════════

Ft Huachuca ODAS Net (deployment)
  └── String Alpha (sub-deployment)
        │
        ├── "Node 1" (sub-deployment)       AZ-MA-1 (system)
        │     platform@link ──────────────→   ├── 7 datastreams
        │     ↑                                ├── 4 control streams
        │     └── deployment@link on DS ──────┘
        │
        ├── "Node 2" (sub-deployment)       AZ-MA-2 (system)
        │     platform@link ──────────────→   ├── 7 datastreams
        │     ↑                                ├── 4 control streams
        │     └── deployment@link on DS ──────┘
        │
        └── "Node 3" (sub-deployment)       AZ-MA-3 (system)
              platform@link ──────────────→   ├── 7 datastreams
              ↑                                ├── 4 control streams
              └── deployment@link on DS ──────┘
```

Users interact with the deployment layer. The deployment scopes queries. The system layer owns the data behind the scenes.

---

## 3  Standards Basis

### 3.1  What the Standard Says About Deployments

OGC 23-001 (Connected Systems API — Part 1: Feature Resources) §7.5 defines a Deployment as:

> *"A Deployment describes the deployment of one or more systems for a particular purpose at a particular place and time."*

The key properties a deployment carries:

| Property | What It Gives You |
|---|---|
| `name`, `description` | User-friendly operational labeling (can differ from system name) |
| `validTime` | When this deployment is/was active — temporal scoping |
| `location` / `geometry` | Where the system is deployed — spatial scoping |
| `platform@link` | Which system backs this deployment |
| Subdeployments | Organizational hierarchy (nets, fields, strings, nodes) |

A system's `name` is **what it is**: "AZ-MA-1 Monitoring Array."

A deployment's `name` is **what role it fills**: "Node 1, String Alpha, North Sector."

The deployment adds operational semantics that the system doesn't carry. This is by design — the standard separates physical identity from operational assignment.

### 3.2  What the Standard Says About Deployment-Scoped Queries

OGC 23-002 (Connected Systems API — Part 2: Observation & Command Resources) defines deployment-scoped nested endpoints:

```
GET /deployments/{id}/datastreams      ← "what is this deployed system producing?"
GET /deployments/{id}/observations     ← "what has this deployed system observed?"
```

These endpoints filter by the `deployment@link` field on datastreams. They exist specifically so consumers can query data **through the operational lens** rather than the hardware lens.

This is the standard saying: *deployments are how you present data to operational users.*

### 3.3  `platform@link` as the Wiring Mechanism

The standard defines `platform@link` on deployments (Part 1, Table 11) as a link to the system that is deployed. On OSH, this is the **only working mechanism** for associating systems with deployments — the `deployedSystems@link` alternative was proven non-functional in the [conformance probe](OSH_DeployedSystems_Conformance_Probe.md).

This makes the 1:1 pairing natural: one deployment, one `platform@link`, one system.

---

## 4  Why This Is Better Than Querying Systems Directly

### 4.1  Feature Comparison

| User Concern | Query via System | Query via Deployment |
|---|---|---|
| "What is MA-1 seeing right now?" | Works | Works |
| "What was at Node 1 position last month?" | Requires knowing MA-1 was there then | Direct query — deployment tracks the role |
| "Show me all of String Alpha's observations" | Must union 3 system queries manually | `GET /deployments/{string}/observations` |
| MA-1 is replaced by MA-4 at same position | Completely different system ID, new DS IDs | Same deployment, update `platform@link` — continuity preserved |
| "Which systems are currently deployed?" | No standard filter mechanism | `GET /deployments?validTime=now` |
| Organizational navigation (net → field → string → node) | Systems don't model operational structure | Deployment hierarchy = org chart |
| Per-node observation scoping | Must filter by system ID in query params | `deployment@link` gives free scoping |

### 4.2  The Critical Advantage: Role Continuity

Consider the lifecycle of a field position:

> Node 1 on String Alpha is a persistent operational role. The hardware occupying it may change — MA-1 today, MA-4 next quarter, MA-7 next year.

With **systems only**: Every hardware swap creates a new system with new datastream IDs. Historical queries must know every system that ever occupied the role and union their results. There is no persistent identifier for "Node 1."

With **deployment as the deployed system**: The deployment is the persistent identifier for the role. When hardware swaps:

```
TIMELINE:

Jan 2026 ─────────────────── Jun 2026 ─────────────────── Dec 2026
          │                           │                           │
          │  Deployment: Node 1       │  Deployment: Node 1       │
          │  platform@link → MA-1     │  platform@link → MA-4     │
          │  validTime: Jan..Jun      │  validTime: Jul..         │
          │                           │                           │
          │  DS.deployment@link → D   │  DS.deployment@link → D   │
          │  (MA-1 observations)      │  (MA-4 observations)      │
```

Or, for cleaner temporal separation, two sequential sub-deployments:

```
String Alpha (deployment)
  └── Node 1 — Phase 1 (sub-deployment)
  │     platform@link → MA-1
  │     validTime: Jan 2026 .. Jun 2026
  │     DS.deployment@link references this
  │
  └── Node 1 — Phase 2 (sub-deployment)
        platform@link → MA-4
        validTime: Jul 2026 ..
        DS.deployment@link references this
```

Either way, the deployment layer provides **role continuity** that the system layer cannot.

---

## 5  Which Systems Need a Paired Deployment?

Not every system needs its own deployment. The pattern applies to **operationally significant systems** — the ones users would look for by name or role.

### 5.1  Systems That SHOULD Get a Deployment

These are systems that users think of as "deployed things":

| System Type | Why It Needs a Deployment |
|---|---|
| AZ-MA-1, MA-2, MA-3 (monitoring arrays) | Each occupies a field position, users query per-node data |
| Relay nodes | Deployed at specific locations, users check relay health |
| Any system that generates observations users query directly | Deployment provides scoped access |
| Any system that occupies a named operational role | Deployment carries the role name |

### 5.2  Systems That Do NOT Need a Deployment

These are internal components — subsystems that are part of a parent system's physical composition:

| System Type | Why It Doesn't Need a Deployment |
|---|---|
| Monitoring Site Node 1 (subsystem of MA-1) | Internal component, data flows through parent's datastreams |
| Relay (subsystem of MA-1) | Internal component |
| Acoustic Sensor (subsystem) | Physical sensor, not an operational role |
| Processing Chain (subsystem) | Algorithm, not a deployed thing |
| Actuator (subsystem) | Command target, accessed through parent system |

### 5.3  The Heuristic

> **If a user would ask "What is [this thing] doing?" then it needs a deployment.**
>
> If a user would ask "What components does [this thing] have?" then it's a subsystem inside a system.

"What is MA-1 doing?" → needs a deployment.
"What sensors does MA-1 have?" → those sensors are subsystems, no deployment needed.

---

## 6  What This Looks Like in the CSAPI Explorer

The webapp already navigates by deployment hierarchy. If users' mental model is "deployed systems," the deployment tree in the Explorer **is** the deployed-systems view:

```
┌──────────────────────────────────────────────┐
│  CSAPI Explorer — Deployments                │
│                                              │
│  ▾ Ft Huachuca ODAS Net                     │
│    ▾ String Alpha                            │
│      ► Node 1 (AZ-MA-1)    ← click          │
│      ► Node 2 (AZ-MA-2)                     │
│      ► Node 3 (AZ-MA-3)                     │
│    ▸ String Bravo                            │
│    ▸ String Charlie                          │
│                                              │
├──────────────────────────────────────────────┤
│  Node 1 (AZ-MA-1)                           │
│                                              │
│  Location: 31.64°N, 110.25°W                │
│  Active since: 2026-01-15                    │
│  System: AZ-MA-1 Monitoring Array            │
│                                              │
│  Datastreams (7):                            │
│    ► Track Updates          1,247 obs        │
│    ► SSL                      834 obs        │
│    ► Health Status            412 obs        │
│    ► SENREP                    56 obs        │
│    ► ...                                     │
│                                              │
│  [View on Map]  [View System Details]        │
└──────────────────────────────────────────────┘
```

Clicking a deployment shows its datastreams (filtered by `deployment@link`). The user sees "what this deployed system is producing" without needing to know about the system/deployment distinction.

The "View System Details" link navigates to the system resource for users who want to see physical composition (subsystems, procedures, sampling features). But for day-to-day operational use, the deployment view is sufficient.

---

## 7  Implementation Details

### 7.1  Creating the Paired Deployment

```python
# System already exists: AZ-MA-1 = system ID 040g

deployment_payload = {
    "type": "Feature",
    "geometry": { "type": "Point", "coordinates": [-110.25, 31.64] },
    "properties": {
        "featureType": "sosa:Deployment",
        "uid": "urn:os4csapi:deployment:node:ft-huachuca:alpha:001",
        "name": "Node 1 — AZ-MA-1",
        "description": "AZ-MA-1 Monitoring Array deployed as Node 1, String Alpha, Ft Huachuca",
        "validTime": ["2026-01-15T00:00:00Z", ".."],
        "platform@link": {
            "href": "/sensorhub/api/systems/040g",
            "uid": "urn:os4csapi:system:set:ft-huachuca:001",
            "type": "application/geo+json"
        }
    }
}

# POST as sub-deployment under String Alpha
POST /deployments/{stringAlphaId}/subdeployments
→ 201 Created, Location: /deployments/057g
```

### 7.2  Wiring Datastreams

Every datastream on the system gets `deployment@link` pointing to its paired deployment:

```python
datastream_payload = {
    "name": "Track Updates",
    "outputName": "trackUpdates",
    "system@link": { "href": "/sensorhub/api/systems/040g" },
    "deployment@link": { "href": "/sensorhub/api/deployments/057g" },
    "procedure@link": { "href": "/sensorhub/api/procedures/04c0" },
    "observedProperties": [...],
    "schema": { ... }
}

POST /systems/040g/datastreams
→ 201 Created
```

### 7.3  Querying Through the Deployment

Once wired, deployment-scoped queries work:

```
# What is Node 1 producing?
GET /deployments/057g/datastreams
→ 7 datastreams (only those with deployment@link → 057g)

# What has Node 1 observed?
GET /deployments/057g/observations
→ all observations from those datastreams

# What's happening across String Alpha?
GET /deployments/{stringAlpha}/subdeployments
→ [Node 1, Node 2, Node 3]

# What's the full org chart?
GET /deployments/{sensorNet}/subdeployments  → strings
GET /deployments/{string}/subdeployments     → nodes
```

### 7.4  Hardware Swap

When MA-1 is replaced by MA-4 at the same position:

```python
# Option A: Update platform@link on existing deployment (keeps same deployment ID)
PUT /deployments/057g
Body: { ...same props..., "platform@link": { "href": "/sensorhub/api/systems/{ma4Id}" } }

# Option B: Close old deployment, create new one (cleaner temporal separation)
PUT /deployments/057g
Body: { ...same props..., "validTime": ["2026-01-15T00:00:00Z", "2026-06-30T23:59:59Z"] }

POST /deployments/{stringAlpha}/subdeployments
Body: { "name": "Node 1 — AZ-MA-4", "platform@link": → MA-4, "validTime": ["2026-07-01T00:00:00Z", ".."] }
```

Either way, the historical data from MA-1's tenure is preserved and queryable through its deployment scope.

---

## 8  Comparison to Alternatives

### 8.1  Alternative A: Systems Only, No Deployments

```
Systems:
  AZ-MA-1
    ├── 7 datastreams, thousands of observations
    └── subsystems
```

| Pros | Cons |
|---|---|
| Simpler — fewer resources to create | No organizational hierarchy |
| | No per-role observation scoping |
| | No temporal scoping by deployment period |
| | Hardware swap breaks all queries |
| | "Which systems are deployed at Ft Huachuca?" has no standard answer |
| | System hierarchy models physical composition, not operational structure |

### 8.2  Alternative B: Organization Modeled in System Hierarchy

```
Systems:
  Sensor Net (system)
    └── String Alpha (subsystem)
          └── AZ-MA-1 (subsystem)
```

| Pros | Cons |
|---|---|
| One hierarchy to think about | Reparenting costs thousands of API calls + data migration |
| | Sensor Net and String Alpha aren't really "systems" |
| | Conflates physical composition with operational organization |
| | [Documented in detail](CSAPI_Deployment_Reparenting_Feasibility.md) |

### 8.3  Alternative C: Flat Deployment with `deployedSystems` (ChatGPT's "Doctrinal Minimalism")

```
Deployments:
  String Alpha (deployment)
    deployedSystems@link: [MA-1, MA-2, MA-3]
```

| Pros | Cons |
|---|---|
| Minimal resource count | **OSH silently drops `deployedSystems@link`** — [proven by probe](OSH_DeployedSystems_Conformance_Probe.md) |
| | No per-node observation scoping |
| | No per-node temporal validity |
| | Doesn't survive contact with the implementation |

### 8.4  Recommended: 1:1 Deployment Pairing (This Document)

```
Deployments:
  Sensor Net
    └── String Alpha
          ├── Node 1 (platform@link → MA-1)
          ├── Node 2 (platform@link → MA-2)
          └── Node 3 (platform@link → MA-3)
```

| Pros | Cons |
|---|---|
| Per-node observation scoping | More resources to create (one deployment per significant system) |
| Organizational hierarchy | `deployment@link` must be set on every datastream |
| Role continuity across hardware swaps | |
| Temporal scoping per deployment | |
| Cheap to rearrange (~12 API calls per move) — [documented](CSAPI_Deployment_Reparenting_Feasibility.md) | |
| Standards-conformant | |
| Works on OSH today | |
| Forward-compatible with `deployedSystems` if OSH adds it | |

---

## 9  The "Deployed Systems" View for End Users

### 9.1  What Users See

With this pattern, the question "show me deployed systems" has a direct API answer:

```
GET /deployments
```

The deployment collection *is* the deployed-systems collection. Each deployment's `platform@link` tells you which system is behind it. The deployment hierarchy tells you how they're organized.

For filtered queries:

| User Question | API Query |
|---|---|
| "All deployed systems" | `GET /deployments` |
| "Deployed systems at Ft Huachuca" | `GET /deployments?bbox=-110.5,31.5,-110.0,31.8` |
| "Currently active deployed systems" | `GET /deployments?validTime=now` |
| "Deployed systems in String Alpha" | `GET /deployments/{stringAlpha}/subdeployments` |
| "What is Node 1 seeing?" | `GET /deployments/{node1}/observations` |
| "Node 1's health" | `GET /deployments/{node1}/datastreams?name=Health` |

Every one of these is a single standard-conformant API call. No client-side filtering, no multi-system unions, no ID lookups.

### 9.2  What Users Don't Need to Know

Users don't need to understand that:
- "Node 1" is a deployment, not a system
- The data lives on system 040g's datastreams
- `deployment@link` is the wiring mechanism
- The system has subsystems (Monitoring Site Node, Relay, etc.)

They see a tree of deployed systems. They click one. They see its data. The deployment abstraction hides the system/deployment distinction entirely.

---

## 10  Conclusion

The "deployed system as a first-class resource" concept is not something that needs to be invented — it already exists in the CSAPI standard as the `Deployment` resource. The standard's design intent is exactly this separation:

- **Systems** = physical inventory (what exists)
- **Deployments** = operational context (what's fielded, where, when, in what role)

The 1:1 pairing pattern makes this explicit:

1. Every operationally significant system gets a paired deployment
2. The deployment carries the operational name, location, time window, and org hierarchy
3. Datastreams are wired to deployments via `deployment@link`
4. Users interact with the deployment layer — it's their "deployed systems" view
5. The system layer holds the data and physical composition, accessed when needed

This pattern is:
- **Standards-conformant** — uses `platform@link`, subdeployments, and `deployment@link` exactly as defined
- **Implementation-proven** — works on OSH today, unlike `deployedSystems@link` which [does not](OSH_DeployedSystems_Conformance_Probe.md)
- **Cheap to reorganize** — deployment reparenting costs [~12 API calls](CSAPI_Deployment_Reparenting_Feasibility.md), not thousands
- **Forward-compatible** — enrichable with `deployedSystems` if/when OSH supports it

> **Deployments are the "deployed systems" resource. The standard already built it. Use it.**

---

## 11  Related Reports

| Report | Topic | Relevance |
|---|---|---|
| [CSAPI Deployment Modeling Standards Conformance](CSAPI_Deployment_Modeling_Standards_Conformance.md) | `deployedSystems` vs `platform@link` standards analysis; flat vs subdeployment models | Establishes that subdeployments with `platform@link` are the correct wiring approach |
| [OSH DeployedSystems Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md) | Empirical proof that OSH silently drops `deployedSystems@link`; `deployment@link` observation scoping analysis | Proves the flat `deployedSystems` alternative doesn't work; documents per-node scoping via `deployment@link` |
| [CSAPI Deployment Reparenting Feasibility](CSAPI_Deployment_Reparenting_Feasibility.md) | Cost analysis of reorganizing deployment vs system hierarchies; two-layer architecture guidance | Confirms deployments are cheap (~12 API calls) to rearrange, making the pattern low-risk |
| [AZ-MA-2/MA-3 Migration Procedure Analysis](AZ-MA-2_MA-3_Migration_Procedure_Analysis.md) | Migration strategy for the remaining two ODAS nodes; procedure modeling decisions | Documents the practical migration context where this pattern will be applied |
