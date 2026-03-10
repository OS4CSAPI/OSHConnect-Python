# Localizer Datastream Deletion Incident — 2026-03-10

## Summary

Deleting two corrupted localizer datastreams (`04hg` and `04i0`) from the OSH
server to fix a global `/datastreams?limit=200` HTTP 500 error inadvertently
broke the live-mode LOB bearing line rendering pipeline in the webapp.

## Timeline

| Time (approx.) | Event |
|---|---|
| Pre-incident | NWS weather station publisher bootstrap completed (5 stations, 17 resources) |
| T+0 | Global `/datastreams?limit=200` returns HTTP 500 mid-response (corrupted H2 serialization) |
| T+1 | ISS invisible on map — `buildSystemLocationCache()` Phase C depends on the broken endpoint |
| T+2 | Root cause identified: DS `04hg` (Location Estimate) and `04i0` (Enriched SENREP v1.1) under localizer system `04o0` have corrupted metadata. Individual `/datastreams/{id}` returns 500, but sub-endpoints (`/schema`, `/observations`) work fine |
| T+3 | **Both datastreams deleted** (`DELETE /datastreams/04hg` → 204, `DELETE /datastreams/04i0` → 204) |
| T+4 | Global endpoint immediately fixed — 32 items, valid JSON. ISS visible again |
| T+5 | Simulator started — LOB observations publishing correctly (0 errors), but no bearing lines visible on map |
| T+6 | Root cause of rendering failure identified (this incident) |

## Architecture Overview

The LOB rendering pipeline has three independent components communicating
solely through the CSAPI server:

```
┌────────────┐      raw LOBs       ┌──────────┐     location estimates    ┌────────┐
│ Simulator  │ ──── POST ────────► │ OSH      │ ◄──── GET / POST ─────── │Localizer│
│ (FastAPI)  │   per MA node DS    │ Server   │   localizer DS (04hg)    │ (script)│
└────────────┘                     └──────────┘                          └────────┘
                                        │
                                   GET datastreams
                                        │
                                   ┌────▼────┐
                                   │ Webapp  │
                                   │ (Vue 3) │
                                   └─────────┘
```

### Webapp Live-Mode LOB Rendering Flow

1. **`discoverLocalizerDatastream()`** (MapViewPage.vue ~L1959) — searches
   global datastream listing for a DS with `outputName` containing
   `location_estimate` → sets `localizerDatastreamId`

2. **`loadLocationEstimates()`** (~L2003) — returns early if
   `!localizerDatastreamId`. Otherwise fetches latest observation, renders:
   - Fix marker (estimated UAS position)
   - CEP50 circle (uncertainty)
   - Contributing LOB bearing lines parsed from `result.contributingLobsJson`

3. **`loadObservationLayers()`** (~L2907) — standalone LOB rendering is
   **deliberately suppressed in live mode** (`!isLive` guard) because live
   mode expects LOBs to come from the localizer's embedded
   `contributingLobsJson` (zero temporal mismatch design).

### What Broke

Deleting `04hg` removed the localizer's datastream from the server. Consequences:

| Component | Impact |
|---|---|
| Webapp `discoverLocalizerDatastream()` | Returns `null` → `localizerDatastreamId` stays null |
| Webapp `loadLocationEstimates()` | Returns immediately (early exit on `!localizerDatastreamId`) |
| Webapp `loadObservationLayers()` | Standalone LOBs still suppressed by `!isLive` guard |
| **Net effect** | **Zero LOB bearing lines rendered in live mode** |
| `scripts/localizer.py` | Would fail at startup — `discover_localizer_ds()` finds no DS |
| Simulator `/clear` and `/reset` | Reference deleted IDs `04hg` and `04i0` — would 404 silently |

## Root Cause Chain

```
NWS bootstrap → H2 serialization bug corrupts localizer DS metadata
  → global /datastreams returns 500
    → agent deletes corrupted DS to fix 500
      → localizer pipeline broken (no DS target for estimates)
        → live-mode LOB rendering has no fallback → blank map
```

## Affected Resources

| Resource | Server ID | Status |
|---|---|---|
| Localizer system | `04o0` | Exists, 0 datastreams |
| Location Estimate DS | `04hg` (was) | **DELETED** — needs re-creation |
| Enriched SENREP v1.1 DS | `04i0` (was) | **DELETED** — referenced by simulator `/reset` |
| UAS Location Estimate DS | `04g0` | Referenced in `SIM_DS_IDS` — returns 404 (pre-existing) |

## Hardcoded ID References

- `simulator/main.py` `SIM_DS_IDS`: contains `04g0` (404) and `04hg` (deleted)
- `simulator/main.py` `SENREP_DS_IDS`: contains `04i0` (deleted)
- Both only used by `/clear` and `/reset` endpoints — simulation loop itself discovers DS IDs dynamically

## Fix Plan

1. **Re-bootstrap localizer datastream**: Run `scripts/bootstrap_localizer.py`
   to create a new Location Estimate DS under system `04o0`. Procedure and
   system already exist → only the DS needs creation.

2. **Run the localizer**: Start `scripts/localizer.py` alongside the simulator
   so it can consume raw LOBs and publish location estimates with embedded
   `contributingLobsJson`.

3. **Update hardcoded DS IDs**: Replace deleted `04hg` with the new DS ID in
   `simulator/main.py` `SIM_DS_IDS`. Remove `04i0` from `SENREP_DS_IDS`
   (or re-bootstrap if needed). Remove `04g0` if it's permanently gone.

## Lessons Learned

1. **Never delete a datastream without tracing all downstream consumers.**
   The localizer DS was not just a data sink — it was the sole source of
   live-mode LOB rendering in the webapp.

2. **The `!isLive` guard on standalone LOB rendering creates a single point
   of failure.** If the localizer DS is unavailable, live mode has NO fallback
   for bearing line rendering. Consider adding a fallback to render standalone
   LOBs when `localizerDatastreamId` is null.

3. **Hardcoded DS IDs are fragile.** The simulator's `/clear` and `/reset`
   endpoints silently skip 404s, masking the fact that referenced resources
   no longer exist.

## References

- Prior incident: `csapi-explorer/docs/incidents/2026-03-10-datastreams-500-localizer-corruption.md`
- Prior bug report: `OSHConnect-Python/docs/research/OSH_Global_Datastreams_Endpoint_500_Bug.md`
- Architecture doc: `OSHConnect-Python/docs/research/LOB_Localizer_Architecture_Correction.md`
- Bootstrap script: `csapi-explorer/scripts/bootstrap_localizer.py`
- Localizer script: `csapi-explorer/scripts/localizer.py`
