# Simulator Route Redesign — River Channel Following

**Date:** 2026-03-03  
**Author:** GitHub Copilot (session with S. Bolling)  
**Status:** Implementation In Progress  
**Component:** `scripts/simulate_scenario.py`  

---

## Background

The original UAV simulator used an 8-point straight-line arc from WSW to ENE that passed directly through the sensor network. With the detection range scaled to 3km (outer ring), the UAV was detected from the very first tick — there was no "approach" phase, no transition from silence to detection. The simulation lacked a realistic narrative arc.

## Desired End State

The UAV should follow the **river/wash channel that runs north of all three sensor nodes** from southwest to northeast. This river is clearly visible on the OSM basemap in the CSAPI Explorer map view.

### Route Characteristics

1. **Start:** Well southwest of all detection envelopes (~4+ km from nearest node), outside all sensor coverage
2. **Path:** Follow the natural river channel running SW → NE, **north of all sensor positions**
3. **Enter detection:** UAV crosses into AZ-MA-1's 3km outer ring first from the west/northwest
4. **Multi-node detection:** As the UAV continues NE, it enters overlapping envelopes — MA-1 + MA-2, then all three
5. **Full coverage:** By the end of the route, the path has passed through the max detection range of all three sensors
6. **Exit:** UAV leaves the last detection envelope heading northeast

### Key Design Decisions

- **North of sensors:** The river runs entirely north of the node positions (MA-1 at 31.649°, MA-2 at 31.657°, MA-3 at 31.664°). The route stays at higher latitudes.
- **Natural meanders:** The river has real terrain curves — the path is not a smooth arc. This creates more dynamic LOB patterns as bearing angles shift with each curve.
- **Terrain-following logic:** A drone operator would follow a river channel for low-altitude concealment. This is tactically realistic.
- **~15-20 waypoints** needed to capture the river's curves faithfully, up from the original 8 straight-line points.

## Detection Narrative Arc

| Phase | Description | Observations Published |
|-------|-------------|----------------------|
| **1 — Approach** | UAV southwest of all envelopes, flying silently along river | None — nothing on map |
| **2 — Single-node** | UAV enters MA-1's outer ring from NW | Faint LOBs from one node only |
| **3 — Dual-node** | UAV in MA-1 + MA-2 overlap | Converging LOBs — partial triangulation |
| **4 — Triple-node** | UAV in the overlap zone of all 3 | Full triangulation — the "money shot" |
| **5 — Transition** | UAV exits some envelopes, enters others | Detection count shifts |
| **6 — Exit** | UAV leaves last envelope heading NE | LOBs stop — operator sees nothing new |

This 6-phase arc tells a complete acoustic detection story, from silence through detection through triangulation to departure.

## Technical Implementation

### What Changes
- **`UAV_WAYPOINTS`** — Replace 8 straight-line points with ~15-20 river-following points
- Points will be traced from the OSM basemap visible in the Explorer map view
- Start point pushed far enough SW that the approach phase is genuine (~4+ km from MA-1)
- End point pushed far enough NE to exit MA-3's envelope

### What Stays the Same
- Detection logic (`if dist <= node["detection_max_m"]`) — already correct, just needs better geometry
- All 4 observation types (LOB, Track Update, Scene Summary, Classification)
- CLI parameters (`--duration`, `--interval`, `--speed`, `--dry-run`)
- Datastream discovery and runtime ID resolution
- Bearing computation (node → UAV)
- Detection noise model (accuracy degrades with distance)

### Sensor Node Positions (Reference)
| Node | Latitude | Longitude |
|------|----------|-----------|
| AZ-MA-1 | 31.6490196 | -110.2758537 |
| AZ-MA-2 | 31.6569236 | -110.2659979 |
| AZ-MA-3 | 31.6637961 | -110.2515496 |

All node positions are **south of the river route**. The UAV passes north of them.

## Relationship to Prior Work

- **LOB Live Mode Assessment** ([lob-live-mode-assessment-2026-03-03.md](./lob-live-mode-assessment-2026-03-03.md)) — identified "re-run simulator with 3km detection range for fresh clean data" as P1
- **Simulator Portability Analysis** ([simulator-portability-analysis-2026-03-03.md](./simulator-portability-analysis-2026-03-03.md)) — confirmed simulator is CSAPI-portable; waypoint changes don't affect portability
- The route redesign addresses GAP 4.1 from the LOB assessment (old observation residue) by creating a cleaner, more purposeful data flow
