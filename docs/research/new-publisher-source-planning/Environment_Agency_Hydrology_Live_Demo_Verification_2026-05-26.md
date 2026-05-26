# Environment Agency Hydrology Live Demo Verification

Date: 2026-05-26

## Purpose

Verify that the Environment Agency Hydrology publisher and Explorer UI updates are visible in the production CSAPI Explorer live demo experience.

## Deployment State

Explorer repository:

```text
OS4CSAPI/ogc-csapi-explorer main
8712d11 Show hydrology latest readings on map cards
5323b4d Show hydrology station thumbnail fallback
```

Publisher/documentation repository:

```text
OS4CSAPI/OSHConnect-Python main
a6acc37 Add Environment Agency hydrology publisher
87a8f77 Add hydrology station thumbnail metadata
```

The production Pages route served a new built JavaScript asset:

```text
https://ogc-csapi-explorer.pages.dev/assets/index-BWlscW-4.js
https://ogc-csapi-explorer.pages.dev/assets/index-BdKjP1gZ.js
```

The production asset contains the expected update strings:

- `Latest readings`
- `Groundwater level`
- `popup-latest-readings`
- `environment agency`
- `SFGPEWRH-------`
- `Environment_Agency_Morton_River_Gauge_Station`

The `index-BdKjP1gZ.js` bundle check confirmed the production Explorer includes the Environment Agency Hydrology representative gauge-photo fallback.

## Correct Live Demo Preset

The Environment Agency Hydrology resources are on the Explorer preset:

```text
OSH (OS4CSAPI)
https://129-80-248-53.sslip.io/sensorhub/api
```

They are not on the default `CSAPI-Go v2` preset:

```text
https://129-80-248-53.sslip.io/csapi-go-v2/
```

This distinction matters for live-demo validation. A user connected to `CSAPI-Go v2` will not see the Environment Agency Hydrology stations even though the live Explorer bundle is updated.

## Backend Observation Check

The live OSH backend returned latest observations for the curated Environment Agency datastreams:

| Datastream | Reading |
| --- | --- |
| `05ig` | River flow `0.219 m3/s`, `Unchecked`, phenomenon time `2026-05-26T08:30:00Z` |
| `05i0` | River level `0.181 m`, `Unchecked`, phenomenon time `2026-05-26T08:45:00Z` |
| `05j0` | Rainfall `0.0 mm`, `Unchecked`, phenomenon time `2026-05-26T08:45:00Z` |
| `05jg` | Groundwater level `53.8 mAOD`, `Unchecked`, stale phenomenon time `2026-04-20T07:00:00Z` |
| `05k0` | River flow `0.291 m3/s`, `Unchecked`, phenomenon time `2026-05-26T08:45:00Z` |

## Confirmed Publisher Refresh

A one-shot live publisher cycle was run after UI verification:

```powershell
py -m publishers.environment_agency_hydrology.environment_agency_hydrology_publisher --once
```

Result:

```text
Published: 5
Skipped:   0
Errors:    0
```

The confirmed refresh posted:

- Beggearn Huish river level: `0.18 m`
- Beggearn Huish river flow: `0.218 m3/s`
- Cosford rainfall: `0.0 mm`
- Burton Coggles groundwater level: `53.8 mAOD`
- Iwood river flow: `0.287 m3/s`

## Production Browser Verification

Production URL:

```text
https://ogc-csapi-explorer.pages.dev/map
```

Connection preset:

```text
OSH (OS4CSAPI)
```

Map load result:

```text
605+ FEATURES
```

Selected deployment:

```text
EA Hydrology Beggearn Huish
```

Verified UI behavior:

- The deployed-system card renders an image-backed STANAG symbol element instead of the old blank fallback rectangle.
- A representative hydrometric gauge photograph is available in system SensorML metadata for the deployed-system side-card thumbnail path. It is explicitly labeled as representative imagery, not station-specific imagery.
- Because the current OSH server rejects system SensorML PUTs with HTTP 500, the production Explorer also includes an Environment Agency Hydrology fallback thumbnail using that same representative photograph when SensorML media is unavailable.
- The card includes a `Latest readings` section.
- The card shows both Beggearn Huish readings:
  - River flow `0.219 m3/s`
  - River level `0.181 m`
- The card shows relative source observation age and quality:
  - `1h ago`
  - `recent`
  - `Unchecked`
- The map popup DOM includes `.popup-latest-readings` and compact rows:
  - River flow `0.219 m3/s`
  - River level `0.181 m`
  - `Latest 1h ago · Unchecked`

The browser viewport available during verification was narrow/mobile-sized, so the popup element existed in the DOM while the deployed-system detail sheet was the visible primary interaction surface. The popup latest-reading content was still present and populated.

## Remaining Warnings

The OSH endpoint still returns multiple HTTP 400 responses for some relationship-query paths during map loading. The Explorer recovers enough to load the map and render the Environment Agency station card. These warnings are consistent with earlier Explorer/server compatibility notes and did not block live-demo validation.

## Outcome

Live demo verification passed for Environment Agency Hydrology on the `OSH (OS4CSAPI)` preset.

Confirmed live-demo features:

- production bundle updated,
- correct OSH preset connected,
- EA hydrology resources visible on map,
- STANAG symbol no longer blank fallback,
- representative gauge photo metadata available for side-card thumbnail display,
- Explorer fallback thumbnail available while system SensorML PUTs are blocked server-side,
- deployed-system side card latest readings visible,
- map popup latest-reading content populated,
- backend latest observations available.
