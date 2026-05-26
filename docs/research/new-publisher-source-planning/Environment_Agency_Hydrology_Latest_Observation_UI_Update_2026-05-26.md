# Environment Agency Hydrology Latest Observation UI Update

Date: 2026-05-26

## Purpose

Document the Explorer update that surfaces meaningful latest observation values for Environment Agency Hydrology station deployments in the map side card and click popup.

## Rationale

Environment Agency Hydrology station identity alone is less useful than station identity plus the latest observed value. The curated publisher emits compact readings for river level, river flow, rainfall, and groundwater level. These values are operationally legible, fit well in the Explorer card, and provide immediate confirmation that the station is live or stale.

## Implemented Explorer Behavior

The deployed-system card model now collects latest observations for up to the first three datastreams associated with the selected deployed system.

For each latest reading, the Explorer extracts and displays:

- datastream label,
- primary numeric/string result value,
- source unit,
- observation time from `phenomenonTime`,
- relative age,
- source quality label when present,
- derived freshness state: `current`, `recent`, `stale`, or `unknown`.

The side card renders a `Latest readings` section below `Outputs`. The map click popup renders the first one or two readings as a compact tooltip-style summary.

## Environment Agency Examples

Expected display examples include:

```text
River level: 0.181 m
River flow: 0.219 m3/s
Rainfall: 0.0 mm
Groundwater level: 53.8 mAOD
```

Groundwater readings can be source-accurate but stale. The Explorer therefore uses the source observation time (`phenomenonTime`) for freshness, not only the CSAPI publish/result time.

## Files Updated

Explorer implementation:

- `demo/src/composables/useDeployedSystemCard.ts`
- `demo/src/components/DeployedSystemCard.vue`
- `demo/src/pages/MapViewPage.vue`

Publisher/research documentation:

- `docs/research/new-publisher-source-planning/Environment_Agency_Hydrology_Publisher_Implementation_Plan_2026-05-26.md`
- `docs/research/new-publisher-source-planning/Environment_Agency_Hydrology_Publisher_Completion_Report_2026-05-26.md`
- `docs/research/new-publisher-source-planning/Environment_Agency_Hydrology_Explorer_Visibility_Check_2026-05-26.md`
- `publishers/environment_agency_hydrology/README.md`

## Notes

This implementation is not hardcoded to Environment Agency Hydrology. Any deployed-system card with datastream observations whose result payload contains a compact scalar value can benefit from the same display path.
