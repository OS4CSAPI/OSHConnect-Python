# Publisher Thumbnail Remediation Plan

Date: 2026-05-29
Status: Planning

## Purpose

This plan closes the remaining deployed-system card thumbnail gaps for publisher systems that either lack media metadata or currently resolve to a misleading representative image. The goal is to improve card clarity without destabilizing publisher behavior, CSAPI resource identity, or Explorer map defaults.

## Current Thumbnail Coverage

Most station-style publishers already have acceptable thumbnail coverage through either SensorML `documents` media links or Explorer fallback logic:

| Publisher | Current state |
| --- | --- |
| `nws` | Representative ASOS station image in bootstrap SensorML. |
| `aviation_wx` | Representative ASOS/AWOS station image in bootstrap SensorML. |
| `ndbc` | NDBC station hardware photo path and BuoyCAM image observations. |
| `coops` | NOAA CO-OPS station photo path. |
| `iss` | NASA ISS photograph. |
| `usgs_water` | NIMS camera thumbnail lookup where available. |
| `usgs_nims` | Image observations are the core product. |
| `environment_agency_hydrology` | Representative hydrometric gauge photo. |
| `uk_air` | Representative air-quality station imagery. |
| `bgs_sensorthings` | UKGEOS borehole infrastructure illustration. |
| `met_office_datahub` | Explorer fallback for Met Office land-observation station imagery. |

Remaining gaps:

1. `opensky`
2. `usgs_eq`
3. `met_office_global_spot`

## Gap 1: OpenSky Feed Adapter

### Problem

`publishers/opensky/bootstrap_opensky.py` includes an `image` object in a properties-like structure, but the Explorer deployed-system card extracts thumbnails from SensorML `documents`/`documentation` entries whose link MIME type starts with `image/` or whose role/name includes photo/thumbnail/preview. The current OpenSky image is also a relative path:

`./metadata_enrichment_pack/assets/opensky_feed_adapter_generic.svg`

That relative path is not suitable for production Explorer rendering.

### Desired outcome

OpenSky deployed-system cards should render a representative aviation/feed-adapter thumbnail that communicates aircraft tracking or ADS-B coverage, without implying the system is a single physical aircraft sensor.

### Preferred fix

Update `publishers/opensky/bootstrap_opensky.py` so `_system_sml()` includes a production-resolvable image document in the `documents` list:

```json
{
  "role": "http://dbpedia.org/resource/Photograph",
  "name": "Representative ADS-B Aircraft Tracking Image",
  "description": "Representative image for the OpenSky ADS-B feed-adapter coverage system; not a station-specific photograph.",
  "link": {"href": "<hosted image URL>", "type": "image/jpeg"}
}
```

Candidate image requirements:

- stable HTTPS URL,
- permissive license or official source terms that allow reuse,
- aviation / ADS-B / air traffic control / receiver-network visual language,
- not misleading as a specific aircraft observation.

### Fallback option

If no clean external image is selected quickly, add an Explorer-side fallback in `demo/src/composables/useDeployedSystemCard.ts` for text matching `opensky`, `ads-b`, or `aircraft tracking`. This is faster but less portable than SensorML metadata because other CSAPI clients will not benefit.

### Verification

- Re-run OpenSky bootstrap idempotently against a safe target server.
- Confirm the system SensorML contains an image document with an absolute HTTPS URL.
- Open the production Explorer card and verify the image loads with nonzero natural dimensions.
- Confirm OpenSky aircraft observations and map styling are unchanged.

## Gap 2: USGS Earthquake Feed

### Problem

`publishers/usgs_eq/bootstrap_usgs_eq.py` has strong documentation links but no image/thumbnail document. The deployed-system card therefore has no visual signal for the earthquake feed-adapter system.

### Desired outcome

USGS EQ deployed-system cards should render a representative seismic/earthquake thumbnail that clearly identifies the system as an event feed, not a physical fixed station.

### Preferred fix

Add an image document to `_system_sml()` in `publishers/usgs_eq/bootstrap_usgs_eq.py`.

Candidate image requirements:

- official USGS or public-domain seismic/earthquake visual preferred,
- stable HTTPS URL,
- either `image/jpeg`, `image/png`, or `image/svg+xml`,
- description should state that it is representative feed imagery, not an event-specific image.

Suggested document shape:

```json
{
  "name": "Representative Earthquake Feed Image",
  "description": "Representative visual for the USGS Earthquake Hazards feed adapter; event observations carry their own locations and metadata.",
  "link": {"href": "<hosted image URL>", "type": "image/jpeg"}
}
```

### Fallback option

Add an Explorer-side representative thumbnail fallback for text matching `usgs earthquake`, `earthquake hazards`, `seismic event`, or `earthquake feed`. This should remain secondary to a real SensorML media document.

### Verification

- Re-run `python -m publishers.usgs_eq.bootstrap_usgs_eq` idempotently on a safe target.
- Verify the `USGS Earthquake Feed` card renders the selected thumbnail.
- Verify event observations still display magnitude, place, depth, status, and USGS detail links.
- Confirm publisher dedup behavior is unchanged.

## Gap 3: Met Office Global Spot Forecast

### Problem

`met_office_global_spot` systems are virtual forecast points, not physical deployed sensors. Explorer's current broad Met Office fallback can assign a land-observation station photograph to Global Spot forecast cards, which is visually polished but semantically misleading.

### Desired outcome

Met Office Global Spot cards should use forecast-appropriate imagery or no physical station image. The thumbnail should communicate forecast/model/data service semantics rather than implying an instrumented station exists at the forecast point.

### Preferred fix

Add a more specific Explorer fallback before the generic Met Office land-observation fallback in `demo/src/composables/useDeployedSystemCard.ts`:

1. Match `global spot`, `site-specific forecast`, or `forecast point` first.
2. Return a forecast/model/data-service image, not a station photo.
3. Keep `met_office_datahub` land observations using the existing weather-station fallback.

If a clean hosted image is found, also add a SensorML image document in `publishers/met_office_global_spot/bootstrap_met_office_global_spot.py` so the metadata is portable.

### Candidate image requirements

- official Met Office brand/data-service page image if reuse terms permit, or a neutral forecast/map visualization with permissive licensing,
- stable HTTPS URL,
- no suggestion of a physical station or observation mast,
- description should explicitly say `forecast point` and `not a physical sensor`.

### Verification

- Rebuild Explorer and inspect the Global Spot deployed-system card.
- Confirm `met_office_datahub` land-observation cards still use the station photo fallback.
- Confirm forecast summaries remain visible and labeled as forecasts.

## Implementation Order

1. Research and select image sources for OpenSky, USGS EQ, and Met Office Global Spot.
2. Prefer publisher SensorML document fixes for OpenSky and USGS EQ.
3. Add Explorer-specific fallback only where metadata propagation is blocked or a virtual-system distinction is needed.
4. Re-run targeted bootstraps idempotently on the target CSAPI server.
5. Rebuild Explorer if fallback logic changes.
6. Smoke test deployed-system cards in production or staging.
7. Document the completion result in `docs/research/new-publisher-source-planning/`.

## Acceptance Criteria

- OpenSky card has a visible aviation/feed-adapter thumbnail.
- USGS EQ card has a visible seismic/event-feed thumbnail.
- Met Office Global Spot no longer uses a physical land-observation station photo unless source metadata explicitly provides one.
- No existing station-style publisher loses its current thumbnail.
- No publisher UID, datastream output name, or deployment hierarchy changes.
- No map default, layer toggle, OpenSky icon, or latest-reading behavior changes.

## Files Likely To Change

Publisher repo:

- `publishers/opensky/bootstrap_opensky.py`
- `publishers/usgs_eq/bootstrap_usgs_eq.py`
- `publishers/met_office_global_spot/bootstrap_met_office_global_spot.py` if a portable SensorML image is selected

Explorer repo, only if fallback logic is needed:

- `demo/src/composables/useDeployedSystemCard.ts`

## Safety Notes

- Do not rerun destructive bootstrap cleanup flags.
- Do not modify publisher observation schemas for this work.
- Avoid broad Explorer text matching that accidentally changes unrelated Met Office land-observation thumbnails.
- If live OSH still rejects some system SensorML updates, use Explorer fallback as a pragmatic production bridge and record the server behavior in the completion report.
