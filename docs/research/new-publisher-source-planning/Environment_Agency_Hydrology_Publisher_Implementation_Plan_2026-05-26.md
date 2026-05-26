# Environment Agency Hydrology Publisher Implementation Plan

Date: 2026-05-26

## Purpose

This plan defines the first new publisher activity from the candidate-source triage: an Environment Agency Hydrological Open Data publisher for OSHConnect-Python. The goal is to create a curated, demo-safe, standards-aware publisher for live and recent hydrology readings from England, modeled consistently with the existing best-of-breed station-network publishers.

Primary source:

- Dataset listing: https://www.data.gov.uk/dataset/98a4d46e-23e7-4430-883c-9e5f14645e8f/hydrological-open-data
- Hydrology explorer: https://environment.data.gov.uk/hydrology/
- API reference: https://environment.data.gov.uk/hydrology/doc/reference
- Stations JSON: https://environment.data.gov.uk/hydrology/id/stations.json
- Measures JSON: https://environment.data.gov.uk/hydrology/id/measures.json

## Recommendation

Implement this first because it has the best combination of:

- public machine-readable access,
- Open Government Licence metadata,
- high demonstration value,
- station-network modeling fit,
- similarity to the mature `publishers/usgs_water` pattern.

The initial implementation should be deliberately curated rather than fleet-wide. Start with a small set of stations and measure series, prove the bootstrap and runtime loop, then expand only if the demo story needs it.

## Existing Pattern To Reuse

Primary exemplar: `publishers/usgs_water`.

Supporting references:

- `publishers/bootstrap_helpers.py` for idempotent CSAPI creation, strict GeoJSON stub handling, SensorML PUT, clean modes, and summary reporting.
- `publishers/aviation_wx` for strict server compatibility notes and robust direct REST observation posting.
- `publishers/usgs_nims` only if later hydrology station imagery or related media links become useful.

## Proposed Publisher Location

Create a new publisher package:

```text
publishers/environment_agency_hydrology/
  __init__.py
  bootstrap_environment_agency_hydrology.py
  environment_agency_hydrology_publisher.py
  stations.json
  README.md
```

Potential shorter package name if preferred:

```text
publishers/ea_hydrology/
```

Recommendation: use `environment_agency_hydrology` for clarity in docs and logs unless path length or command ergonomics becomes annoying.

## Initial Scope

### Data Products

Start with a curated set of station/measure combinations across these parameter families:

- river level,
- river flow,
- rainfall,
- groundwater level if stable examples are available.

Do not ingest all available stations or measures in the first pass.

### Suggested Demo Size

Target initial size:

- 5 to 10 stations,
- 1 to 3 measures per station,
- 10 to 20 datastreams total.

This is enough to demonstrate a real hydrological network without creating a noisy or fragile operational footprint.

### Geographic Curation

Pick one of these approaches before implementation:

1. **Narrative cluster**: stations in a coherent catchment or region.
2. **Parameter diversity**: stations chosen to cover level, flow, rainfall, and groundwater even if geographically dispersed.
3. **Recognizable sites**: stations near known towns/landmarks for a more legible map demo.

Recommendation for the first implementation pass: use parameter diversity first, then refine geography if needed.

## Source API Notes

The Environment Agency API uses linked-data style paths and format suffixes. During triage, these forms worked:

```text
https://environment.data.gov.uk/hydrology/id/stations.json?_limit=3
https://environment.data.gov.uk/hydrology/id/measures.json?_limit=5
https://environment.data.gov.uk/hydrology/id/measures.json?parameter=level&_limit=5
https://environment.data.gov.uk/hydrology/id/measures.json?parameter=rainfall&_limit=5
```

Important: use `_limit`, `.json`, and documented API conventions. A plain `limit=3` style probe returned HTTP 400 for stations during triage.

API metadata advertises multiple output formats including JSON, GeoJSON, CSV, RDF, TTL, and HTML. Use JSON for the publisher runtime and bootstrap sidecar generation.

## Proposed CSAPI Model

### Procedure

Create one procedure:

```text
urn:os4csapi:procedure:environment-agency-hydrology:v1
```

Procedure metadata should describe:

- Environment Agency Hydrological Open Data,
- telemetry and archive provenance,
- supported parameters,
- quality-control/provisional-data caveat,
- Open Government Licence attribution,
- API reference links.

### Systems

Create one CSAPI system per curated hydrology station:

```text
urn:os4csapi:system:environment-agency-hydrology:{stationNotation}:v1
```

System metadata should include:

- station label,
- Environment Agency station notation/ID,
- latitude/longitude,
- station type if available,
- river/catchment/location metadata if available,
- source station URL,
- available curated measures,
- representative hydrometric gauge photo metadata for Explorer side-card thumbnails,
- licensing and attribution note.

Environment Agency station resources do not expose station-specific photos. Use an explicitly labeled representative Environment Agency river-gauge photograph rather than implying that the image is the exact selected station. Preserve attribution and license metadata in SensorML document links.

### Datastreams

Create one datastream per selected Environment Agency measure:

```text
urn:os4csapi:datastream:environment-agency-hydrology:{stationNotation}:{parameter}:{period}:{unitOrStatistic}:v1
```

The datastream `outputName` should be stable and concise. Possible examples:

```text
eaRiverLevel
eaRiverFlow
eaRainfall
eaGroundwaterLevel
```

If one station has multiple measures for the same parameter, append a statistic or period suffix:

```text
eaRiverLevelInstantaneous
eaRiverLevelDailyMax
eaRainfallDailyTotal
```

Datastream metadata should preserve:

- source measure URI,
- parameter and parameterName,
- observedProperty URI and label,
- unit and unit URI if available,
- period and periodName,
- valueType/statistic,
- observation type,
- source readings query URL.

### Deployments

Create a root deployment:

```text
urn:os4csapi:deployment:environment-agency-hydrology-demo:v1
```

Create a group deployment for curated stations:

```text
urn:os4csapi:deployment:environment-agency-hydrology-stations:v1
```

Create station child deployments linked to each station system:

```text
urn:os4csapi:deployment:environment-agency-hydrology-{stationNotation}:v1
```

### Explorer / NATO Symbol Classification

The Explorer's deployed-system cards classify deployment symbols from resource keywords, names, descriptions, platform titles, and UIDs. Environment Agency Hydrology should use the same friendly emplaced sensor symbol family as the existing water/weather station publishers, especially USGS Water, CO-OPS, NDBC, and NWS.

Implementation guidance:

- Keep deployment names and descriptions explicit about `Environment Agency`, `hydrology`, `monitoring station`, `river level`, `river flow`, `rainfall`, and `groundwater`.
- In the Explorer symbol mapper, classify Environment Agency Hydrology deployments as friendly emplaced sensors using the same legacy SIDC already used by comparable station publishers: `SFGPEWRH-------`.
- Place the Environment Agency rule before the generic `monitoring station` rule so the hydrology-specific water/weather sensor symbol wins.
- Do not leave Environment Agency Hydrology to the generic deployment fallback, which renders as a blank friendly land-unit rectangle and does not communicate that these are environmental sensor stations.

### Explorer Latest Observation Display

Environment Agency Hydrology stations should surface latest observation values in the Explorer deployed-system side card and map click popup. For these sensors, the latest reading is often the most meaningful quick-look information because station metadata alone does not tell the viewer the current hydrologic state.

Display guidance:

- Fetch latest observations for the selected station's primary datastreams, capped to a small number for UI and API safety.
- Use source observation time (`phenomenonTime`) for freshness and staleness calculations, not only CSAPI `resultTime`.
- Show compact value rows with label, value, unit, relative age, quality, and stale/current status.
- Preserve source-specific units such as `mAOD` for groundwater values even when CSAPI SWE schemas use UCUM-compatible `m` internally.
- Keep map popup text shorter than the side card: show the first one or two latest readings and a compact freshness/quality line.

Representative side-card values:

```text
River level: 0.181 m
River flow: 0.219 m3/s
Rainfall: 0.0 mm
Groundwater level: 53.8 mAOD
```

This should be implemented generically in the Explorer deployed-system card path so other station-style publishers can benefit from the same latest-reading summary.

## Observation Model

Each CSAPI observation should represent one reading from one Environment Agency measure.

Recommended result fields:

```json
{
  "timestamp": 1770000000,
  "stationId": "station notation",
  "measureId": "measure notation or URI",
  "parameter": "level",
  "parameterName": "Level",
  "value": 1.23,
  "unit": "m",
  "period": 900,
  "periodName": "15 min",
  "valueType": "instantaneous",
  "qualifier": "",
  "qualityStatus": "",
  "sourceUrl": "https://environment.data.gov.uk/..."
}
```

If the source returns a specific `dateTime`, map it to `phenomenonTime`. Use the publisher clock only for `resultTime` if the CSAPI server requires it.

## Runtime Strategy

### Fetching

Runtime should:

1. Load curated stations and measures from `stations.json`.
2. Resolve CSAPI system/datastream IDs dynamically by UID and outputName.
3. Poll only selected measure IDs.
4. Fetch recent/latest readings for each selected measure.
5. Normalize values and timestamps.
6. Skip duplicates already published in the current process.
7. POST observations to the matching CSAPI datastream.

### Dedupe

Use a dedupe key based on source-native identifiers:

```text
{measureUri}|{dateTime}|{value}
```

If the source exposes reading IDs, prefer:

```text
{readingId}
```

If values are revised after publication and no reading ID exists, consider republishing when `(measureUri, dateTime)` is unchanged but the value or quality/status changes.

### Polling Interval

Initial default interval:

```text
900 seconds
```

Rationale: the source includes mainly 15-minute high-resolution data and real-time telemetry. A 15-minute cadence is conservative and demo-friendly.

Support CLI overrides:

```text
--interval
--once
--dry-run
--stations
```

### Rate and Source Courtesy

Even though no rate limit was discovered during triage, implement conservative behavior:

- request timeout,
- retry/backoff for transient failures,
- HTTP 429 handling if encountered,
- per-cycle request cap,
- no fleet-wide unbounded polling.

## Bootstrap Strategy

Bootstrap should:

1. Read `stations.json`.
2. Create or update the procedure.
3. Create station systems using minimal GeoJSON stubs.
4. PUT rich SensorML for each system.
5. Create selected datastreams under each station system.
6. Create deployment hierarchy.
7. Support `--clean`, `--clean-only`, `--dry-run`, and `--force-sml`.

Use `bootstrap_helpers.py` rather than custom REST boilerplate.

## Sidecar Data Strategy

`stations.json` should be curated and explicit, not a cached dump of the full API.

Suggested shape:

```json
{
  "stations": [
    {
      "stationNotation": "...",
      "label": "...",
      "lat": 51.0,
      "lon": -1.0,
      "stationUrl": "https://environment.data.gov.uk/hydrology/id/stations/...",
      "selectionReason": "river level demo station",
      "measures": [
        {
          "measureUri": "https://environment.data.gov.uk/hydrology/id/measures/...",
          "notation": "...",
          "parameter": "level",
          "parameterName": "Level",
          "period": 900,
          "periodName": "15 min",
          "valueType": "instantaneous",
          "unit": "m",
          "outputName": "eaRiverLevel"
        }
      ]
    }
  ]
}
```

During implementation, create a small discovery script or one-time research command to propose candidate stations/measures, then hand-curate the JSON.

## Implementation Phases

### Phase 0: Source Reconnaissance

Tasks:

- Read API reference sections for stations, measures, and readings.
- Confirm latest-reading query syntax for a single known measure.
- Identify fields returned by station, measure, and reading resources.
- Confirm licensing/attribution metadata in API responses.
- Pick initial station/measure set.

Exit criteria:

- `stations.json` has 5-10 curated stations and selected measures.
- One sample latest-reading query is verified for every selected measure.

### Phase 1: Bootstrap

Tasks:

- Add package directory and `__init__.py`.
- Implement `bootstrap_environment_agency_hydrology.py`.
- Define procedure body and SensorML system bodies.
- Define datastream schemas per parameter type.
- Define deployment tree.
- Run bootstrap in dry-run mode.

Exit criteria:

- Dry-run output is coherent.
- Bootstrap can create resources on the target CSAPI/OSH server.
- Re-running bootstrap is idempotent.

### Phase 2: Runtime Publisher

Tasks:

- Implement source fetch helpers.
- Implement timestamp/value normalization.
- Implement dynamic CSAPI datastream discovery.
- Implement duplicate suppression.
- Implement dry-run and once modes.
- Implement conservative polling loop.

Exit criteria:

- `--dry-run --once` prints normalized observations.
- `--once` publishes to the correct datastreams.
- Re-running `--once` does not duplicate unchanged readings within the same process.

### Phase 3: Validation and Demo Integration

Tasks:

- Verify systems, datastreams, deployments, and observations in OSH/CSAPI.
- Confirm map visibility and metadata inspectability in the Explorer.
- Add README usage notes.
- Add any required Docker Compose entry if this publisher should run continuously.
- Run lint/tests or targeted smoke checks consistent with repository practice.

Exit criteria:

- Selected stations appear as systems.
- Datastreams have rich metadata and source links.
- Latest observations are visible and correctly typed.
- The publisher can be stopped/restarted safely.

## Testing Plan

Recommended tests:

- Unit tests for station/measure parsing from fixture JSON.
- Unit tests for reading normalization.
- Unit tests for dedupe key behavior.
- Dry-run smoke test against live Environment Agency API.
- Bootstrap dry-run smoke test.
- Optional live CSAPI integration smoke test if credentials/server are available.

Avoid broad live tests that poll many stations. Keep live tests curated and fast.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Full API is too large | Use curated `stations.json`; never fleet-poll by default. |
| Query syntax is format-sensitive | Use `.json` and documented `_limit`/linked-data conventions. |
| Values can be provisional/revised | Preserve quality/status fields and source timestamps; consider revision-aware dedupe. |
| Multiple measures per parameter cause naming ambiguity | Include period/statistic in outputName and datastream UID when needed. |
| CSAPI strict parser rejects rich create stubs | Use `bootstrap_helpers.py` and the GeoJSON stub + SensorML PUT pattern. |
| Source latency or empty latest responses | Log skipped measures, keep prior state, and avoid treating empty source response as fatal. |

## Acceptance Criteria

The first implementation should be considered complete when:

- A curated Environment Agency Hydrology publisher package exists.
- Bootstrap creates procedure, systems, datastreams, and deployments idempotently.
- Runtime publishes current/recent observations for the curated measures.
- Source metadata, licensing, station identity, parameter semantics, and units are visible in CSAPI metadata.
- The publisher supports `--dry-run`, `--once`, `--interval`, and station filtering.
- The implementation avoids hardcoded server IDs and discovers CSAPI IDs by UID/outputName.
- A README explains setup, bootstrap, runtime, and source limitations.

## Initial Work Order

1. Research exact readings API query patterns for measure-specific latest data.
2. Build a candidate station/measure table from live API responses.
3. Select the curated first-pass station list.
4. Implement bootstrap.
5. Implement runtime publisher.
6. Validate against OSH/CSAPI.
7. Document usage and limitations.

## Open Decisions

- Package name: `environment_agency_hydrology` versus `ea_hydrology`.
- First-pass geography: coherent catchment versus parameter-diverse station set.
- Datastream granularity for stations with several periods/statistics.
- Whether to include water-quality units in the first version or keep the first pass to hydrometric readings only.

## Recommended Decision Defaults

Unless later source reconnaissance changes the picture:

- Use package name `environment_agency_hydrology`.
- Use a parameter-diverse curated station set.
- Start with hydrometric readings only: level, flow, rainfall, groundwater.
- Model one station as one CSAPI system and one selected measure as one datastream.
- Use `usgs_water` as the primary implementation guide.
