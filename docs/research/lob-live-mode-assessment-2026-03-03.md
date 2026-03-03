# Lines of Bearing — Live Mode Assessment

**Date:** 2026-03-03  
**Author:** GitHub Copilot (session with S. Bolling)  
**Status:** Active Development  
**Branch:** `main` (ogc-csapi-explorer)  
**Commits:** `4b0c986`, `23e62fb`, `b5aac7c`, `178dd69`, `e4da800`, `5816d41`

---

## 1. Where We Started

The initial data simulator run was a firehose: it dumped hundreds of observations per node in rapid succession, all at once. The server accumulated them, and when the map loaded it pulled back ~500 per datastream. The result was **516 bearing lines** radiating from all 3 nodes simultaneously — impossible to read, no sense of time progression, just a starburst of chaos.

Additionally, Live Mode didn't work at all initially because `isLocationRelatedDatastream()` only matched GPS/location keywords. LOB, Track Update, Scene Summary, and Classification datastreams were **all filtered out**, so the observation layer iterator had nothing to render.

## 2. Where We Are Now

### Infrastructure Built (6 commits)

| Component | Commit | Description |
|-----------|--------|-------------|
| Live Mode toggle (desktop) | `4b0c986` | 5-second auto-refresh, checkbox in sidebar, green label + timestamp |
| Data simulator | `23e62fb` | `simulate_scenario.py` — standalone Python UAV flythrough, 8-waypoint arc, 4 obs types per detecting node per tick |
| Datastream filter fix | `b5aac7c` | Broadened `isLocationRelatedDatastream()` to match LOB/Track/SST/SSL/Scene/Classification by name and definition URI |
| Tightened Live Mode | `178dd69` | 10 obs per datastream limit, recency-based bearing coloring (newest = bright rose/thick → oldest = gray-blue/thin/faded) |
| Mobile Live Mode | `e4da800` | Bolt FAB button in TAK mobile controls, Layers sheet toggle with timestamp, pulsing green animation |
| 3km detection rings | `5816d41` | Scaled rings from 200/550/900m → 667/1833/3000m, synced simulator `detection_max_m` |

### Current Plumbing

- **Simulator** publishes 4 observation types per detecting node every 5 seconds with geometrically correct bearings computed from node→UAV positions
- **Live Mode** fetches only the last 10 observations per datastream and applies recency coloring
- **Detection rings** are scaled to 3km outer radius — overlapping coverage zones are clearly visible
- **Mobile** has full parity with desktop Live Mode toggle

### Known Server State

The sidebar currently shows **~1,456 Lines of Bearing** accumulated from the initial chaos run. In normal (non-live) mode, the map pulls up to 500 per datastream and renders them all, producing a dense mess. **Decision: keep the data on the server for now; lean on Live Mode to hide the residue. Purging will be revisited later.**

## 3. What the Demo Should Look Like

Based on a PowerPoint mockup created by the operator (orange annotation lines overlaid on the live map screenshot), the ideal visualization is:

1. **Each LOB originates at a sensor node** and extends outward along the computed bearing toward the UAV
2. **Multiple LOBs from the same node** fan slightly as the UAV moves — angular spread shows target motion
3. **Where LOBs from 2–3 nodes cross** = triangulation — the intersection zone is the estimated target position
4. **The lines are clean and readable** — approximately 3–5 per node visible at any time, not hundreds

This is the "money shot" for the demo: a human operator glances at the map and immediately sees where the drone is based on converging bearing lines.

## 4. Identified Gaps

### 4.1 Old Observation Residue
~1,400+ stale LOBs from the chaos run still exist on the server. In non-live mode, these all render. **Mitigation (current):** Live Mode hides them by fetching only the last 10. **Future option:** purge via DELETE or add a server-side time filter.

### 4.2 LOB Line Length and Visibility
Bearing lines extend a fixed distance from the sensor node. If too short, they look like stubby whiskers and don't show convergence. If too long, they clutter. The length needs to be tuned so that lines from adjacent nodes clearly intersect in the detection overlap zone.

### 4.3 Triangulation "Fix" Visualization
The PowerPoint naturally shows where lines cross, but we don't currently compute or highlight the intersection point. A future enhancement could plot the estimated target position (the "fix") as a distinct marker where 2+ LOBs converge — this is the classic DF (direction-finding) workflow.

### 4.4 Live Mode Observation Count Tuning
Currently set to 10 per datastream. With 3 LOB datastreams (one per node), that's up to 30 bearing lines at once. The PowerPoint mockup shows ~5–7 total, which feels right. Options:
- Drop to 3–5 per datastream for a cleaner look
- Keep 10 and rely on recency fading (old lines go near-invisible)

### 4.5 Non-Live Mode Story
When Live Mode is off, what should the map show? Full history is overwhelming. Options for future work:
- Default "last hour" or "last 50" time filter
- Forensic/replay mode with a time slider
- Simply guide users to enable Live Mode for operational view

## 5. Demo Narrative

> Three acoustic sensor nodes (AZ-MA-1, AZ-MA-2, AZ-MA-3) are deployed around a SNET in southern Arizona. A UAS enters the area. As it passes through the 3km detection envelopes, each node publishes lines of bearing in real-time via the OGC Connected Systems API. An operator watching the map sees converging LOBs and can visually triangulate the drone's position and track its movement across the sensor network.

## 6. Priority Next Steps

| Priority | Task | Rationale |
|----------|------|-----------|
| **P0** | Lean into Live Mode as the default operational view | Hides chaos residue, shows clean real-time picture |
| **P1** | Tune LOB line length for clear convergence at overlap zones | Makes triangulation visually obvious |
| **P1** | Re-run simulator with 3km detection range for fresh clean data | Validates the full pipeline end-to-end |
| **P2** | Computed triangulation marker at LOB intersection | Automates the "where is the drone?" answer |
| **P2** | UAV track trail showing movement through the sensor network | Adds temporal context to the real-time view |
| **P3** | Purge old chaos observations from server | Clean slate for production demos |
| **P3** | Time-slider / replay mode for forensic analysis | Post-event review capability |

## 7. Technical Reference

- **Oracle Server:** `https://os4csapi-osh.duckdns.org/sensorhub/api`
- **Deployed App:** `https://ogc-csapi-explorer.pages.dev/map`
- **Simulator Script:** `scripts/simulate_scenario.py`
- **Detection Range Config:** Lines 159–195 of `demo/src/pages/MapViewPage.vue`
- **Live Mode Logic:** Lines 141–145 (state), 1917–1923 (refresh), 1647–1721 (render)
- **Recency Styling:** `getRecencyBearingStyle()` at line ~232
- **Datastream IDs:**
  - AZ-MA-1: LOB=`0420`, Track=`042g`, Scene=`0440`, Classification=`0430`
  - AZ-MA-2: LOB=`0460`, Track=`0480`, Scene=`046g`, Classification=`0450`
  - AZ-MA-3: LOB=`049g`, Track=`04bg`, Scene=`04a0`, Classification=`048g`
- **Node Positions:**
  - AZ-MA-1: `31.6490196, -110.2758537`
  - AZ-MA-2: `31.6569236, -110.2659979`
  - AZ-MA-3: `31.6637961, -110.2515496`
