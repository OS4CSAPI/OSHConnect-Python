# ODAS → CSAPI Scenario Pack — Ft Huachuca (v3.0, Part 1 — Revised2)

## Scope
Part 1 models the **doctrine-aligned operational hierarchy** and the **monitoring / reporting layer** (no sensor systems yet).

## Canonical hierarchy
ICO (deployment) >
RSO (subdeployment) >
SSO (subdeployment) with deployed system **SET** >
SNET (subdeployment) with deployed systems **Monitoring Site Node** + **Relay/Repeater** >
SFIELD (subdeployment) >
STRING (subdeployment)

## Reporting rule (important)
**SENREP is modeled as a datastream produced by the SET.**
The Monitoring Site Node is the enabling operational node (equipment + comms), but the *process ownership and reporting authority* is the SET.

- SENREP schema: `schemas/datastreams/senrep_OSH_v2.5.json`
- Example SENREP observations: `examples/sample_data/observations/senrep.ndjson`

## Diagrams
See `diagrams/` for:
- `v3_0_hierarchy.(png|svg)` — doctrine hierarchy + deployed systems
- `v3_0_dataflow.(png|svg)` — end-to-end dataflow with ownership (SET produces SENREP)
