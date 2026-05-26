# Environment Agency Hydrology Explorer Visibility Check

Date: 2026-05-26

## Purpose

Verify that the newly implemented Environment Agency Hydrology publisher is visible and usable through the CSAPI Explorer, not only through backend bootstrap/publish commands.

## Backend Inventory Check

Checked the Explorer OSH endpoint:

`https://129-80-248-53.sslip.io/sensorhub/api`

All four curated Environment Agency Hydrology systems were present:

| Station | System ID | Datastreams with observations |
| --- | --- | --- |
| Beggearn Huish | `05j0` | `eaRiverFlow`, `eaRiverLevel` |
| Cosford | `05k0` | `eaRainfall` |
| Burton Coggles | `05kg` | `eaGroundwaterLevel` |
| Iwood | `05l0` | `eaRiverFlow` |

Each of the five datastreams returned at least one latest observation through the CSAPI API.

## Explorer Checks

Production Explorer URL:

`https://ogc-csapi-explorer.pages.dev/`

Selected server preset:

`OSH (OS4CSAPI)`

### Deployment List

The Explorer deployment list shows:

- ID: `05d0`
- Name: `Environment Agency Hydrology Demo`
- Type: `Feature`

### Deployment Detail

The deployment detail opens successfully and displays:

- Name: `Environment Agency Hydrology Demo`
- UID: `urn:os4csapi:deployment:environment-agency-hydrology-demo:v1`
- Description: `Top-level grouping for curated Environment Agency hydrology publisher resources.`
- Geometry: `Point (52.5000°, -2.5000°)`

The relationship graph displays:

- One station-group subdeployment: `Environment Agency Hydrology Stations (05dg)`
- Four station systems:
  - `EA Hydrology Beggearn Huish (05j0)`
  - `EA Hydrology Cosford (05k0)`
  - `EA Hydrology Burton Coggles (05kg)`
  - `EA Hydrology Iwood (05l0)`

### NATO / STANAG Symbol Follow-Up

Initial Explorer review showed the Environment Agency deployment using the generic fallback symbol: a blank friendly land-unit rectangle. That was not semantically useful for a hydrology station network.

The closest existing symbol family is the friendly emplaced sensor symbol already used for comparable water/weather station publishers:

- USGS Water monitoring stations
- CO-OPS tide/water-level stations
- NDBC buoy/weather stations
- NWS surface weather stations

The Explorer symbol mapper was updated so Environment Agency Hydrology keywords classify to the same legacy SIDC:

```text
SFGPEWRH-------
```

Bootstrap metadata was also updated so Environment Agency Hydrology deployments describe themselves as hydrology monitoring stations and water sensor systems, giving both current and future symbol-classification paths enough context.

The Environment Agency rule is placed before the generic `monitoring station` rule in the mapper so the water/weather sensor symbol wins for these deployments.

### System Detail

Opened the Beggearn Huish system from the deployment graph.

The system detail renders successfully:

- ID: `05j0`
- Name: `EA Hydrology Beggearn Huish`
- Type: `sosa:System`
- UID: `urn:os4csapi:system:environment-agency-hydrology:48513a18-e485-4317-ae92-93bf4f7f3e54:v1`
- Geometry: `Point (51.1463°, -3.3737°)`

The Explorer displays the intended rich station metadata, including:

- Environment Agency keyword/classifier metadata
- Station notation
- River name: `Washford River`
- Selection reason
- Curated measure labels
- Open Government Licence v3.0
- Environment Agency source document links
- Latest-reading query links for river level and river flow

### Datastream Drill-Down

Opened the system datastream relationship for Beggearn Huish.

The Explorer lists both expected datastreams:

- `05ig` — `River Flow`, output name `eaRiverFlow`
- `05i0` — `River Level`, output name `eaRiverLevel`

Opened `River Flow` detail successfully. The Explorer displays:

- Parent system: `05j0`
- Output name: `eaRiverFlow`
- Phenomenon time: `2026-05-26T08:30:00Z`
- Result time: `2026-05-26T09:19:25Z`
- Parsed datastream output through `parseDatastream()`
- Observation schema as `DataRecord` / `application/om+json`

The displayed observation schema includes the expected fields:

- `stationId`
- `measureId`
- `parameter`
- `flow_m3s`
- `unit`
- `valueType`
- `quality`
- `completeness`
- `sourceUrl`

### Latest Observation Side Card and Popup

Follow-up UI work now surfaces latest reading values directly in the Explorer map experience.

When an Environment Agency Hydrology station deployment is selected, the deployed-system side card includes a `Latest readings` section populated from the station datastreams. The map click popup also shows the first one or two latest readings for quick inspection before opening the full side card/detail path.

The display uses each observation's `phenomenonTime` to calculate freshness. This is important for hydrology because a reading can be source-accurate but stale, especially groundwater observations. The UI therefore marks stale values instead of relying only on the CSAPI `resultTime`.

Representative values from the current curated set:

- Beggearn Huish river flow: `0.219 m3/s`
- Beggearn Huish river level: `0.181 m`
- Cosford rainfall: `0.0 mm`
- Burton Coggles groundwater level: `53.8 mAOD` with stale source observation time
- Iwood river flow: `0.291 m3/s`

### Observation Drill-Down

Opened the River Flow observation relationship from the datastream detail.

The Explorer lists one observation for datastream `05ig`:

- Observation ID: `06pgt25kqn80c0000000`

This confirms the live observation posted by the runtime publisher is reachable through the Explorer UI.

## Map Check

The map page loaded a feature layer in an existing Explorer tab and reported approximately `496 FEATURES`. The map itself is canvas-rendered, so station names are not available as DOM text for direct search.

A fresh production map navigation also showed a temporary `LOADING...` state and several HTTP 400 console errors. The resource drill-down path remains operational and confirms the Environment Agency resources are visible and connected. The map behavior should be treated as a separate Explorer/server compatibility follow-up rather than a blocker for the publisher implementation.

## Noted Explorer/Server Warnings

The Explorer connection reported a CORS warning for the OSH endpoint:

`Access-Control-Allow-Origin` contained multiple values: `*, https://ogc-csapi-explorer.pages.dev`.

The Explorer still connected, but this duplicate CORS header should be cleaned up server-side because browsers treat multiple origin values as invalid in some fetch paths.

Additional 400s appeared when the Explorer tried some relationship queries, but the app recovered in several places using resource links. For example, the system detail reported:

`Server ignored query parameters — results corrected client-side: Server returned 400 for /deployments endpoint — resolved 1 item(s) via @link fields`

## Outcome

Explorer visibility is confirmed for the Environment Agency Hydrology publisher through the primary resource drill-down path:

Deployment → Station System → Datastream → Observation

The publisher resources are visible, parsed by the Explorer, and connected to live observations. Remaining issues are Explorer/server compatibility concerns around map loading, duplicate CORS headers, and some relationship-query 400s.
