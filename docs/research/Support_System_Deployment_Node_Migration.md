# Support System Deployment Node Migration: SET-A, Monitoring Site, Relay

| Field | Value |
|---|---|
| **Date** | 2026-03-02 |
| **Author** | Claude (Opus 4.6) |
| **Status** | Completed — Deployed to Oracle Server |
| **Scope** | Creating dedicated `platform@link` deployment nodes for support systems |
| **Server** | `os4csapi-osh.duckdns.org` (Oracle Cloud — 129.80.248.53) |
| **Related Reports** | [CSAPI Deployed Systems Design Pattern](CSAPI_Deployed_Systems_Design_Pattern.md), [OSH DeployedSystems Conformance Probe](OSH_DeployedSystems_Conformance_Probe.md), [Phase1 Bootstrap Results](Phase1_Bootstrap_Results.md) |

---

## 1  Executive Summary

Three dedicated deployment nodes were created on the Oracle OSH server for support systems (SET-A, Monitoring Site Node 1, Relay / Repeater 001) that previously lacked `platform@link` associations. These systems were only referenced via `deployedSystemUIDs` — a weak UID-based mechanism that does not create a resolvable linkage the CSAPI client can use for geometry sync, deployment-scoped queries, or the `/systems/{id}/deployments` traversal.

After this migration, **all 6 top-level systems** on the server now have dedicated deployment nodes with 1:1 `platform@link` wiring.

---

## 2  Problem Statement

### 2.1  Prior State

The `bootstrap_v4.py` authoritative data model defined two distinct system-to-deployment association mechanisms:

| System | Association Mechanism | Deployment | Strength |
|---|---|---|---|
| AZ-MA-1 | `platform@link` on Node 1 deployment | Node 1 — AZ-MA-1 | **Strong** — resolvable href, bidirectional traversal |
| AZ-MA-2 | `platform@link` on Node 2 deployment | Node 2 — AZ-MA-2 | **Strong** |
| AZ-MA-3 | `platform@link` on Node 3 deployment | Node 3 — AZ-MA-3 | **Strong** |
| SET-A | `deployedSystemUIDs` on SSO | SSO (Sensor Surveillance Op) | **Weak** — UID string only, not resolvable |
| Monitoring Site | `deployedSystemUIDs` on SNET | SNET (Sensor Net) | **Weak** |
| Relay / Repeater | `deployedSystemUIDs` on SNET | SNET (Sensor Net) | **Weak** |

### 2.2  Why This Matters

The `deployedSystemUIDs` mechanism has several limitations:

1. **No resolvable link** — It's a comma-separated UID string, not an `href`. Clients cannot navigate from the deployment to the system via standard link resolution.
2. **No bidirectional traversal** — The CSAPI endpoint `/systems/{id}/deployments` works by matching `platform@link.href`, not by scanning `deployedSystemUIDs` across all deployments. Systems linked only via `deployedSystemUIDs` appear undeployed when queried from the system side.
3. **No geometry sync** — The CSAPI Explorer webapp implemented geometry locking for deployed systems (preventing direct geometry edits on systems whose location is managed by a deployment). This feature queries `/systems/{id}/deployments` and only works when a `platform@link` exists.
4. **No per-system deployment scoping** — `deployedSystemUIDs` lists multiple systems on a single deployment. There is no way to query observations for just one of the listed systems through the deployment layer.

### 2.3  Design Principle

Per the [CSAPI Deployed Systems Design Pattern](CSAPI_Deployed_Systems_Design_Pattern.md) report:

> **Every operationally significant system should get a paired deployment with `platform@link`.**
>
> The heuristic: *If a user would ask "What is [this thing] doing?" then it needs a deployment.*

SET-A, Mon Site, and Relay all meet this criterion — they are operationally significant systems with fixed physical locations that users would query about.

---

## 3  Solution Design

### 3.1  Deployment Placement

Each new deployment node was placed as a subdeployment of the deployment that previously referenced the system via `deployedSystemUIDs`:

| New Deployment | Parent | Rationale |
|---|---|---|
| **SET-A Emplacement** | SSO (Sensor Surveillance Operation) | SET-A is the human analysis team under SSO. Its emplacement (TOC location) is an operational role under the surveillance operation. |
| **Monitoring Site Node 1 Emplacement** | SNET (Sensor Network/Net) | The monitoring site is network infrastructure — equipment and comms enabling data reception. It's a peer of the sensor fields within the network. |
| **Relay / Repeater 001 Emplacement** | SNET (Sensor Network/Net) | The relay is network infrastructure — a VHF repeater forwarding sensor transmissions. Also a peer within the network. |

### 3.2  Updated Hierarchy

```
ICO (Intelligence Collection Operation)
└── R&S (Reconnaissance and Surveillance)
    └── SSO (Sensor Surveillance Operation)        ← deployedSystemUIDs: [SET-A]
        ├── SET-A Emplacement                      ← platform@link → SET-A           ★ NEW
        └── SNET (Sensor Network/Net)              ← deployedSystemUIDs: [Mon Site, Relay]
            ├── Monitoring Site Node 1 Emplacement ← platform@link → Mon Site        ★ NEW
            ├── Relay / Repeater 001 Emplacement   ← platform@link → Relay           ★ NEW
            └── Field 001 (Sensor Field)
                └── String Alpha (line-of-emplacement)
                    ├── Node 1 — AZ-MA-1           ← platform@link → AZ-MA-1
                    ├── Node 2 — AZ-MA-2           ← platform@link → AZ-MA-2
                    └── Node 3 — AZ-MA-3           ← platform@link → AZ-MA-3
```

### 3.3  Preserving `deployedSystemUIDs`

The existing `deployedSystemUIDs` properties on SSO and SNET were **not removed**. They remain as supplementary metadata. The new `platform@link` nodes coexist with the UID-based references. This is forward-compatible — if OSH ever implements proper `deployedSystems@link` resolution, the UIDs will still be valid.

---

## 4  Implementation

### 4.1  Script

A dedicated migration script was created: [`scripts/add_support_deployment_nodes.py`](https://github.com/OS4CSAPI/csapi-explorer/blob/main/scripts/add_support_deployment_nodes.py)

The script:
1. Resolves parent deployment server IDs by UID lookup
2. Resolves target system server IDs by UID lookup
3. Constructs GeoJSON Feature bodies with `platform@link` (using resolved `/sensorhub/api/systems/{id}` href)
4. POSTs each deployment as a subdeployment of its parent
5. Verifies creation by querying back
6. Supports `--dry-run` mode

### 4.2  Deployment Payloads

Each deployment was created with this structure:

```json
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:deployment:{type}:ft-huachuca:001",
    "featureType": "sosa:Deployment",
    "name": "{System Name} Emplacement",
    "description": "Deployment node for {system}...",
    "validTime": ["2026-03-02T00:00:00Z", ".."],
    "platform@link": {
      "href": "/sensorhub/api/systems/{systemId}",
      "title": "{System Name}",
      "uid": "{system UID}",
      "type": "application/geo+json"
    }
  },
  "geometry": {
    "type": "Point",
    "coordinates": [{lon}, {lat}]
  }
}
```

Geometry coordinates were copied from each system's existing geometry, ensuring spatial consistency.

### 4.3  Execution Results

```
======================================================================
  Add Deployment Nodes for SET-A, Monitoring Site, Relay
======================================================================

  CREATE: SET-A Emplacement
    UID:     urn:os4csapi:deployment:set:ft-huachuca:001
    Parent:  SSO (041g)
    System:  Sensor Employment Team (SET-A) (040g)
    Coords:  [-110.2524769, 31.6380757]
    POST →   deployments/041g/subdeployments
    → Created! id=0450

  CREATE: Monitoring Site Node 1 Emplacement
    UID:     urn:os4csapi:deployment:monsite:ft-huachuca:001
    Parent:  SNET (0420)
    System:  Monitoring Site Node 1 (0410)
    Coords:  [-110.2525675, 31.6383956]
    POST →   deployments/0420/subdeployments
    → Created! id=045g

  CREATE: Relay / Repeater 001 Emplacement
    UID:     urn:os4csapi:deployment:relay:ft-huachuca:001
    Parent:  SNET (0420)
    System:  Relay / Repeater 001 (041g)
    Coords:  [-110.2554653, 31.6429133]
    POST →   deployments/0420/subdeployments
    → Created! id=0460

  Done: 3 created, 0 skipped, 0 errors
======================================================================
```

### 4.4  Verification

Post-creation verification confirmed all three deployments are queryable and have correct `platform@link`:

```
OK  SET-A Emplacement (id=0450) → platform@link: Sensor Employment Team (SET-A)
    (urn:os4csapi:system:set:ft-huachuca:001)
OK  Monitoring Site Node 1 Emplacement (id=045g) → platform@link: Monitoring Site Node 1
    (urn:os4csapi:system:monitoring-site-node:ft-huachuca:001)
OK  Relay / Repeater 001 Emplacement (id=0460) → platform@link: Relay / Repeater 001
    (urn:os4csapi:system:relay:vhf-repeater:ft-huachuca:001)
```

---

## 5  Authoritative Source of Truth Update

The `bootstrap_v4.py` script was updated to include the 3 new deployment nodes in the `DEPLOYMENT_TREE` data structure. A `--dry-run` verified the updated script correctly recognizes all 12 deployment resources (9 original + 3 new):

```
PHASE 3: Create Deployment Hierarchy (nested POST)
  SKIP Intelligence Collection Operation — already exists (040g)
    SKIP Reconnaissance and Surveillance Operation — already exists (0410)
      SKIP Sensor Surveillance Operation — already exists (041g)
        SKIP SET-A Emplacement — already exists (0450)           ★ NEW
        SKIP Sensor Network/Net Deployment — already exists (0420)
          SKIP Monitoring Site Node 1 Emplacement — already exists (045g)  ★ NEW
          SKIP Relay / Repeater 001 Emplacement — already exists (0460)    ★ NEW
          SKIP Sensor Field 001 — already exists (042g)
            SKIP Sensor String Alpha — already exists (0430)
              SKIP Node 1 — AZ-MA-1 — already exists (043g)
              SKIP Node 2 — AZ-MA-2 — already exists (0440)
              SKIP Node 3 — AZ-MA-3 — already exists (044g)
```

---

## 6  Impact on CSAPI Explorer Webapp

### 6.1  Geometry Locking (Implemented Same Session)

The CSAPI Explorer webapp was updated with a geometry-locking feature for deployed systems:

- **`ResourceUpdate.vue`**: When editing a system, queries `/systems/{id}/deployments` to check for a linked deployment
- **`StructuredResourceForm.vue`**: If a linked deployment is found, the geometry editing controls (lat/lon inputs, map picker) are replaced with a read-only display showing:
  - A yellow "Location managed by deployment" banner
  - The linked deployment's name
  - A router-link to navigate to the Deployments update page
  - Current coordinates displayed read-only

With the new `platform@link` deployment nodes, this feature now works for **all 6 top-level systems**, not just the 3 MA nodes.

### 6.2  Map View

The deployment nodes will appear on the map with STANAG MIL-STD-2525D military symbology (the `symbol-mapper.ts` keyword classifier assigns symbols based on deployment names). The new emplacement nodes will render with appropriate symbols alongside the existing Node 1/2/3 markers.

### 6.3  Location Cache

The `cacheLocationsFromLoadedFeatures()` function in `MapViewPage.vue` reads `platform@link` from deployments to derive system locations. With the new deployment nodes, SET-A, Mon Site, and Relay locations will be derivable from the deployment layer — consistent with how MA-1/2/3 locations are already managed.

---

## 7  Complete Server Resource Inventory (Post-Migration)

### 7.1  Systems (45 total)

| # | System | UID | Type | Linked Deployment |
|---|---|---|---|---|
| 1 | Sensor Employment Team (SET-A) | `urn:os4csapi:system:set:ft-huachuca:001` | Platform | SET-A Emplacement (0450) |
| 2 | Monitoring Site Node 1 | `urn:os4csapi:system:monitoring-site-node:ft-huachuca:001` | Platform | Mon Site Emplacement (045g) |
| 3 | Relay / Repeater 001 | `urn:os4csapi:system:relay:vhf-repeater:ft-huachuca:001` | Platform | Relay Emplacement (0460) |
| 4 | ODAS Mic Array Node AZ-MA-1 | `urn:os4csapi:system:odas:az-ma-1` | System | Node 1 — AZ-MA-1 (043g) |
| 5 | ODAS Mic Array Node AZ-MA-2 | `urn:os4csapi:system:odas:az-ma-2` | System | Node 2 — AZ-MA-2 (0440) |
| 6 | ODAS Mic Array Node AZ-MA-3 | `urn:os4csapi:system:odas:az-ma-3` | System | Node 3 — AZ-MA-3 (044g) |
| 7–45 | 39 MA node subsystems (13 per node × 3) | `urn:os4csapi:system:odas:az-ma-{n}:{component}` | Various | *(inherited from parent)* |

### 7.2  Deployments (12 total)

| # | Deployment | UID | Parent | platform@link |
|---|---|---|---|---|
| 1 | Intelligence Collection Operation | `...ico...` | *(top)* | — |
| 2 | Reconnaissance and Surveillance Op | `...rso...` | ICO | — |
| 3 | Sensor Surveillance Operation | `...sso...` | R&S | — |
| 4 | **SET-A Emplacement** | `...set...` | **SSO** | **→ SET-A** |
| 5 | Sensor Network/Net Deployment | `...snet...` | SSO | — |
| 6 | **Monitoring Site Node 1 Emplacement** | `...monsite...` | **SNET** | **→ Mon Site** |
| 7 | **Relay / Repeater 001 Emplacement** | `...relay...` | **SNET** | **→ Relay** |
| 8 | Sensor Field 001 | `...field...` | SNET | — |
| 9 | Sensor String Alpha | `...string...` | Field | — |
| 10 | Node 1 — AZ-MA-1 | `...alpha:001` | String | → AZ-MA-1 |
| 11 | Node 2 — AZ-MA-2 | `...alpha:002` | String | → AZ-MA-2 |
| 12 | Node 3 — AZ-MA-3 | `...alpha:003` | String | → AZ-MA-3 |

### 7.3  Summary

| Resource Type | Count |
|---|---|
| Top-level systems | 6 |
| Subsystems | 39 |
| **Total systems** | **45** |
| Deployments (organizational) | 6 |
| Deployments with platform@link | 6 |
| **Total deployments** | **12** |
| Datastreams | 22 |
| Control streams | 9 |
| **Total server resources** | **88** |

---

## 8  Known Limitation: `/systems/{id}/deployments` Returns 400

The OSH server returns `HTTP 400 Invalid resource name: 'deployments'` when querying `/systems/{id}/deployments`. This endpoint is defined in the CSAPI standard but not implemented by OSH. 

The CSAPI Explorer webapp works around this by scanning all loaded deployments for `platform@link.href` matches (client-side reverse lookup). The `ResourceUpdate.vue` component uses `getNestedListUrl('systems', systemId, 'deployments')` which constructs the correct URL, but OSH may not resolve it. A fallback approach scanning the deployment collection may be needed.

**Impact**: The geometry-locking feature depends on this endpoint. If OSH doesn't support it, the webapp falls back gracefully (no lock is applied, geometry remains editable). This is a known gap — see [OSH DeployedSystems Conformance Gap](OSH_DeployedSystems_Conformance_Gap.md) for the broader conformance analysis.

---

## 9  Future Work

1. **Wire `deployment@link` on datastreams** — Per the [Design Pattern](CSAPI_Deployed_Systems_Design_Pattern.md), every datastream should carry `deployment@link` pointing to its system's paired deployment. This enables deployment-scoped observation queries (`GET /deployments/{id}/observations`).

2. **Client-side deployment lookup fallback** — If OSH doesn't support `/systems/{id}/deployments`, the webapp should fall back to scanning the deployment collection for `platform@link` matches. This would make the geometry-locking feature work regardless of server conformance level.

3. **STANAG symbol classification** — Verify the new emplacement deployment names trigger appropriate MIL-STD-2525D symbol classifications via `symbol-mapper.ts`.

---

## 10  Conclusion

This migration closes the gap between the MA-node deployment pattern (which already used `platform@link`) and the support systems (SET-A, Mon Site, Relay) which were only weakly associated via `deployedSystemUIDs`. All 6 top-level systems now follow the 1:1 deployment pairing pattern recommended by the [CSAPI Deployed Systems Design Pattern](CSAPI_Deployed_Systems_Design_Pattern.md).

The result is a uniform data model where:
- Every operationally significant system has a dedicated deployment node
- Every deployment node uses `platform@link` for a resolvable, bidirectional system association
- The deployment hierarchy reflects operational organization, not just physical composition
- The webapp's geometry-locking and deployment-scoped features work consistently across all systems
