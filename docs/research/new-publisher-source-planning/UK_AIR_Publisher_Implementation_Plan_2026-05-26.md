# UK-AIR Publisher Implementation Plan

Date: 2026-05-26

Status update: first-pass implementation, live bootstrap, live publish, and server read-back were completed on 2026-05-26. See `UK_AIR_Publisher_Completion_Report_2026-05-26.md` for validation details. Remaining follow-up is production Explorer visual review for marker styling, side-card polish, and any representative image decision.

## Purpose

This plan defines the second new publisher activity from the candidate-source triage: a UK-AIR air pollution publisher for OSHConnect-Python. The goal is to add a curated, public, standards-aligned air-quality station network to the OS4CSAPI demo, using the same disciplined workflow proven by Environment Agency Hydrology.

Primary source:

- Overview: https://uk-air.defra.gov.uk/data/about_sos
- SOS GetCapabilities: https://uk-air.defra.gov.uk/data/sos/service?service=SOS&request=GetCapabilities
- REST API docs: https://uk-air.defra.gov.uk/data/sos/static/doc/api-doc/
- REST API root: https://uk-air.defra.gov.uk/sos-ukair/api/v1/
- Stations: https://uk-air.defra.gov.uk/sos-ukair/api/v1/stations
- Timeseries: https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries

## Recommendation

Implement UK-AIR second because it has high demo value, open public access, standards alignment through SOS/52 North, and a strong environmental/public-health story. It is slightly more model-heavy than Environment Agency Hydrology because station, pollutant, timeseries, procedure, and feature identities need careful consolidation.

## Existing Pattern To Reuse

Primary exemplar: `publishers/usgs_water`.

Supporting references:

- `publishers/environment_agency_hydrology` for the newest station-network sidecar, bootstrap, runtime, latest-reading, and Explorer documentation pattern.
- `publishers/aviation_wx` for timestamp/unit normalization and compact station observations.
- `publishers/bootstrap_helpers.py` for idempotent resource creation and server-compatible bootstrap behavior.

## Proposed Publisher Location

Create a new publisher package:

```text
publishers/uk_air/
  __init__.py
  bootstrap_uk_air.py
  uk_air_publisher.py
  stations.json
  README.md
```

Use `uk_air` for path ergonomics while keeping resource names and descriptions explicit about Defra UK-AIR.

## Initial Scope

Start with a curated pollutant/station set rather than the full network.

Recommended first-pass products:

- nitrogen dioxide (`NO2`),
- particulate matter (`PM10`),
- fine particulate matter (`PM2.5`),
- ozone (`O3`) if stable recent data is available.

Suggested demo size:

- 4 to 6 monitoring stations,
- 1 to 3 pollutant timeseries per station,
- roughly 8 to 12 datastreams total.

Prefer a recognizable urban/regional cluster if the API makes consolidation clean. If station identities are pollutant-specific, start with a curated set of timeseries and consolidate physical stations only where the source metadata clearly supports it.

## Source API Notes

Known working endpoints from triage:

```text
https://uk-air.defra.gov.uk/sos-ukair/api/v1/
https://uk-air.defra.gov.uk/sos-ukair/api/v1/stations?limit=3
https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries?limit=3
https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/3
https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/3/getData?timespan=PT24H/2026-05-26T00:00:00Z
```

Important source characteristics:

- API is a 52 North Timeseries REST API backed by SOS concepts.
- Timeseries metadata includes station, phenomenon, category, procedure, feature, unit, first/last values, and source identifiers.
- Data timestamps are millisecond epoch values and must be normalized to UTC ISO strings.
- The service is beta and older-SOS-shaped, so source metadata should be preserved generously.

## Reconnaissance Tasks Before Coding

- Fetch a larger sample of stations and timeseries metadata.
- Determine whether station IDs represent physical sites or pollutant-specific station/timeseries views.
- Identify stable recent timeseries for the selected pollutants.
- Confirm exact latest-reading query shape and whether `getData` supports bounded recent windows reliably.
- Confirm unit strings and choose CSAPI/SWE-compatible `uom.code` mappings.
- Check whether quality/status flags are available in the REST response or only through deeper SOS metadata.

## Proposed CSAPI Model

### Procedure

Create one procedure:

```text
urn:os4csapi:procedure:uk-air:v1
```

Procedure metadata should describe:

- Defra UK-AIR air pollution monitoring,
- SOS/52 North source provenance,
- supported pollutants,
- public-health/environmental monitoring context,
- Open Government Licence attribution,
- API reference and SOS GetCapabilities links.

### Systems

Preferred model: one CSAPI system per physical air-quality monitoring station.

```text
urn:os4csapi:system:uk-air:{stationId}:v1
```

Fallback model: one system per curated timeseries if station consolidation is ambiguous in the source.

System metadata should include:

- station label,
- UK-AIR station ID and source station URL,
- latitude/longitude,
- site type or area metadata if available,
- curated pollutant coverage,
- SOS/REST provenance links,
- licensing and attribution note.

### Datastreams

Create one datastream per selected pollutant timeseries:

```text
urn:os4csapi:datastream:uk-air:{stationId}:{pollutantCode}:v1
```

Stable output-name examples:

```text
ukAirNO2
ukAirPM10
ukAirPM25
ukAirO3
```

Datastream metadata should preserve:

- source timeseries ID,
- pollutant code and pollutant URI,
- unit and unit URI/string,
- station ID and station label,
- procedure/feature/category references from the source,
- latest or recent data query URL.

### Deployments

Create a root deployment:

```text
urn:os4csapi:deployment:uk-air-demo:v1
```

Create a group deployment:

```text
urn:os4csapi:deployment:uk-air-stations:v1
```

Create one child deployment per curated station or timeseries system:

```text
urn:os4csapi:deployment:uk-air-{stationId}:v1
```

Deployment descriptions should include terms such as `UK-AIR`, `air quality`, `air pollution`, `monitoring station`, and pollutant names so Explorer classification and search are useful.

## Observation Model

Each observation result should include at minimum:

```text
timestamp
stationId
timeseriesId
pollutant
pollutantUri
value
unit
sourceUrl
```

Add quality/status fields if the source exposes them in a stable shape.

Use source phenomenon time for CSAPI `phenomenonTime`. Use ingestion time only for `resultTime` if needed by the server/client path.

## Explorer Behavior

### Symbol

Use the friendly emplaced environmental sensor family unless a more specific air-quality symbol exists in the current mapper. The likely initial SIDC should match the established station sensor family:

```text
SFGPEWRH-------
```

If this feels too water/weather-specific in visual review, add a UK-AIR-specific rule that still avoids the blank generic rectangle fallback.

### Latest Readings

The side card and popup should show current pollutant concentrations because that is the key demo value.

Suggested labels:

```text
NO2: 18 ug/m3
PM10: 12 ug/m3
PM2.5: 7 ug/m3
O3: 45 ug/m3
```

Use compact freshness and unit display. Preserve source unit strings in result payloads, but map to SWE-compatible units where required by CSAPI schemas.

### Image Strategy

Do not invent a station-specific photo unless the source exposes one. If a thumbnail is needed for side-card consistency, use a clearly labeled representative air-quality monitoring station image with source/license attribution, or defer imagery until a verified public image source is selected.

## Validation Plan

1. Probe source API for candidate stations/timeseries.
2. Create curated `stations.json` with verified recent data.
3. Compile bootstrap and runtime modules.
4. Run bootstrap dry-run.
5. Run live bootstrap against OSH.
6. Run publisher dry-run.
7. Run one live publisher cycle.
8. Read back CSAPI observations.
9. Verify Explorer map/card visibility on `OSH (OS4CSAPI)`.
10. Record live-demo verification and server compatibility findings.

## Known Risks

- Station identity may be pollutant-specific and require careful consolidation.
- Unit strings such as `ug.m-3` may need CSAPI/SWE-compatible schema mapping.
- The 52 North API is beta and may expose older SOS modeling conventions.
- Direct browser/proxy CORS behavior should be checked before relying on production-only validation.
- Current OSH system SensorML PUT failures may block rich system metadata updates; Explorer fallbacks should remain a last resort, not the default design.

## Initial Done Definition

UK-AIR first pass is done when:

- a curated station/timeseries sidecar is committed,
- bootstrap creates procedure, systems, datastreams, and deployments,
- runtime publishes latest pollutant observations,
- latest values are visible in Explorer side cards/popups,
- symbol classification is meaningful,
- docs and live-demo verification are written,
- commits are pushed.
