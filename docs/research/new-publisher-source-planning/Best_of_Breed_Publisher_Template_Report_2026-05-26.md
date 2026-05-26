# Best-of-Breed Publisher Template Report

Date: 2026-05-26

## Purpose

This report records the initial research recommendation for selecting existing OSHConnect-Python publisher implementations as exemplars for four upcoming data-source publisher additions. The goal is to identify the strongest current patterns for richness, completeness, and accuracy before designing new publisher work.

## Executive Recommendation

Use a small template family rather than a single universal publisher template.

The strongest primary exemplar is `publishers/usgs_eq` for any new event-feed or feed-adapter source. It has the best combination of data-model rigor, authoritative metadata, clear CSAPI modeling, explicit runtime semantics, and enrichment planning.

For station networks, imagery feeds, or strict server compatibility work, use complementary exemplars:

| New source shape | Best existing example | Primary reason |
| --- | --- | --- |
| Event feed, alert feed, or one API stream | `publishers/usgs_eq` | Best Pattern C feed-adapter model, rich metadata, official source documentation, explicit event revision dedupe. |
| Fixed station network or physical sensor fleet | `publishers/usgs_water` | Richest station-level model, sidecar station metadata, multiple datastreams per system, strong official provenance. |
| Imagery, media, or camera feed | `publishers/usgs_nims` | Best media-feed pattern, image URL modeling, duplicate suppression, and companion datastream behavior. |
| Strict CSAPI/SensorML compatibility | `publishers/aviation_wx` plus `publishers/bootstrap_helpers.py` | Best reference for strict parser constraints, GeoJSON stub separation, and SensorML PUT behavior. |

## Evaluation Criteria

The recommendation is based on these qualities:

- Metadata richness: official documentation links, SensorML bodies, identifiers, classifiers, contacts, documents, deployments, and result schemas.
- Completeness: bootstrap script, runtime publisher, config or sidecar data, clean/bootstrap modes, dry-run behavior, operational notes, and enrichment plan.
- Accuracy: source semantics grounded in authoritative upstream documentation, explicit field meanings, correct observation model, and avoidance of misleading CSAPI resource modeling.
- Runtime robustness: duplicate suppression, rate-limit handling, reconnect behavior, server compatibility workarounds, and stable datastream discovery.
- Extensibility: clear boundaries between baseline runtime, optional enrichment, and future UI/client use.

## Findings

### 1. USGS Earthquake Is the Best Event-Feed Exemplar

`publishers/usgs_eq` should be the default starting point for event feeds, alert feeds, and API streams where the source is not a fleet of physical stations.

Key strengths:

- Correct Pattern C model: one procedure, one feed-adapter system, one datastream, and deployment grouping.
- Avoids the common modeling mistake of creating one CSAPI system per event.
- Uses authoritative USGS earthquake source documentation and records optional enrichment surfaces.
- Publishes one CSAPI observation per earthquake event.
- Deduplicates by `(eventId, updatedTime)`, so revised events are republished while unchanged feed entries are skipped.
- Includes a total bootstrap/data-model enrichment pack that documents source verification, omitted upstream fields, and future detail/FDSN enrichment boundaries.

Use this pattern when a new data source is conceptually a live feed rather than a set of deployed sensors.

### 2. USGS Water Is the Best Station-Network Exemplar

`publishers/usgs_water` should be the primary model for fixed stations, physical assets, and parameterized sensor networks.

Key strengths:

- One CSAPI system per monitoring location.
- Multiple datastreams per station, with explicit parameter semantics.
- Rich station sidecar data in `stations.json`.
- Strong official USGS Water Data OGC API references.
- SensorML captures station identifiers, classifiers, contacts, documents, characteristics, capabilities, and position.
- Runtime handles API keys, request delay, rate-limit backoff, station filtering, duplicate suppression, and datastream discovery quirks.

Use this pattern when the new source has named locations, sites, platforms, gauges, monitors, or other physical assets that should appear as systems.

### 3. USGS NIMS Is the Best Media/Imagery Exemplar

`publishers/usgs_nims` should be the reference for image-producing sources, camera feeds, and companion media datastreams.

Key strengths:

- Models imagery as a companion datastream on existing USGS Water systems.
- Captures image URL, thumbnail/full image concepts, media type, camera identity, and latest-file semantics.
- Handles upstream rate limits, cooldown/backoff, and duplicate suppression by filename.
- Uses a curated `cameras.json` sidecar.

Use this pattern when the new source produces media artifacts rather than conventional scalar observations.

### 4. Aviation WX Is the Best Strict-Compatibility Reference

`publishers/aviation_wx` is not necessarily the richest domain model overall, but it is the most useful example for strict CSAPI and SensorML compatibility constraints.

Key strengths:

- Documents strict parser behavior directly in the bootstrap.
- Separates small GeoJSON create stubs from rich SensorML update bodies.
- Records csapi-go-v2 compatibility quirks.
- Uses server-specific result normalization where required.
- Demonstrates multi-station runtime behavior with duplicate suppression.

Use this pattern as a guardrail for all new publishers, especially when targeting both OSH SensorHub and stricter CSAPI servers.

## Baseline Standard for New Publishers

Every new publisher should follow these conventions unless the data source clearly requires a different model:

- Use `publishers/bootstrap_helpers.py` for idempotent create/update/delete behavior.
- Create resources with minimal GeoJSON stubs, then PUT rich SensorML using `application/sml+json`.
- Use stable UIDs; never depend on server-assigned IDs in source code or config.
- Include authoritative source documentation links in procedure, system, datastream, and deployment metadata where appropriate.
- Define an explicit result schema with units, field definitions, and omitted-field notes if the upstream source is richer than the baseline result body.
- Add config or sidecar files for curated station/camera/source lists.
- Implement duplicate suppression using source-native identifiers and update timestamps where possible.
- Handle HTTP 429 or source throttling with cooldown/backoff behavior.
- Support `--dry-run`, `--once`, and interval control for safe validation.
- Keep baseline polling separate from optional enrichment or expensive detail fetches.

## Pattern Selection Rules

When the four candidate sources are provided, classify each first:

1. If it is a stream of events, alerts, tracks, reports, incidents, detections, or records from one API feed, start from `usgs_eq`.
2. If it is a list of physical stations or monitoring locations, start from `usgs_water`.
3. If it is a camera/image/media source, start from `usgs_nims`.
4. If it is a moving-object feed with many transient assets, use `usgs_eq` and compare against `opensky` for runtime-specific field handling.
5. If it must run against csapi-go-v2 or another strict server, review `aviation_wx` and `bootstrap_helpers.py` before finalizing the bootstrap payloads.

## Non-Preferred Starting Points

The following publishers remain useful references but should not be the primary template for new work:

- `publishers/iss`: useful for a simple moving-object demo, but too specialized and thin as a general template.
- Earlier NWS/NDBC/CO-OPS patterns: operationally valuable, but the repository research notes show they were candidates for further metadata enrichment.
- `publishers/opensky`: useful for moving-object feed semantics and bounding-box configuration, but less complete as the general best-of-breed exemplar than USGS EQ.

## Recommended Next Step

When the four new data sources are available, produce a per-source classification table with:

- source type and recommended exemplar,
- expected CSAPI model,
- proposed procedures/systems/datastreams/deployments,
- required sidecar/config files,
- dedupe key and revision strategy,
- rate-limit/backoff strategy,
- authoritative source documentation links,
- optional enrichment surfaces.

This should happen before implementation so the four publishers share a coherent design language rather than diverging into one-off scripts.
