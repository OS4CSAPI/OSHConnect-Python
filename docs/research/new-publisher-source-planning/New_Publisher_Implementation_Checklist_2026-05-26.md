# New Publisher Implementation Checklist

Date: 2026-05-26

## Purpose

This checklist captures the repeatable workflow proven during the Environment Agency Hydrology implementation. Use it as the baseline for the next publisher sources so each integration reaches the same standard: researched, scoped, implemented, documented, visible in Explorer, and verified against the live demo path.

## 1. Source Triage

- Confirm the source is real, public, and machine-readable.
- Identify official documentation, API root, sample list endpoint, sample data endpoint, and license terms.
- Probe endpoints directly and record exact working query shapes.
- Capture quirks early, especially auth, rate limits, pagination, timestamp format, units, and non-standard parameters.
- Decide whether the source should be implemented now, deferred, or split into multiple publisher opportunities.

## 2. Existing Pattern Selection

- Choose the closest mature publisher as the primary exemplar.
- Prefer station-network patterns for fixed monitoring sites.
- Prefer event-feed patterns for earthquakes, alerts, or incident streams.
- Prefer image/media patterns only when the source actually exposes useful media.
- Record any server compatibility constraints from prior publishers before coding.

## 3. Curated First Pass

- Start with a small demo-safe sidecar, not a full-network ingestion.
- Include enough variety to prove the data model.
- Choose stations/events that are geographically legible in Explorer.
- Keep runtime polling bounded and predictable.
- Preserve original source IDs in metadata and observations, even if CSAPI UIDs need sanitized tokens.

## 4. CSAPI Model

- Define one procedure for the source ingestion method.
- Define systems around physical stations, platforms, or logical event sources.
- Define one datastream per observed property/product/statistic combination.
- Define deployments that make map placement and hierarchy explicit.
- Include source URLs, license links, units, parameter names, quality flags, and provenance in metadata.

## 5. Bootstrap

- Use shared bootstrap helpers where possible.
- Create minimal GeoJSON stubs first, then richer SensorML through PUT where the server accepts it.
- Support `--dry-run`, `--clean`, `--clean-only`, and `--force-sml`.
- Log and recover from known server compatibility failures without hiding them.
- Compile and run the bootstrap locally before touching the live server.

## 6. Runtime Publisher

- Load curated source definitions from a sidecar file.
- Fetch only latest or bounded recent readings in normal operation.
- Normalize timestamps to UTC.
- Preserve source quality, completeness, revision, and status metadata when available.
- Dedupe unchanged readings during a running process.
- Support `--dry-run`, `--once`, `--interval`, and source-subset flags.

## 7. Explorer Readiness

- Verify the map can classify the publisher with an appropriate STANAG/MIL-STD-2525 symbol.
- Add source-specific symbol rules only when generic rules produce a poor result.
- Make side-card summaries meaningful for the domain.
- Surface latest observations where the current value is useful to a viewer.
- Add image/media metadata only when it is accurate, licensed, and clearly attributed.
- Use explicit representative-image language when exact station imagery is unavailable.

## 8. Validation

- Compile changed Python modules.
- Run dry-run source fetches.
- Run bootstrap against the live OSH endpoint.
- Run one live publish cycle.
- Verify backend observations directly.
- Verify Explorer visibility on the correct preset.
- Verify production bundle content after pushing Explorer changes.
- Record any server warnings separately from publisher failures.

## 9. Documentation

- Add or update the publisher README.
- Add an implementation plan before coding.
- Add a completion report after first working publish.
- Add a live-demo verification report after Explorer validation.
- Record server compatibility issues as issue-ready drafts or remote issues.
- Keep image attribution and license notes close to the implementation and report.

## 10. Commit And Push

- Keep publisher and Explorer commits separate when they live in separate repositories.
- Verify `git status --short` before each commit.
- Push immediately when the user expects live-demo behavior.
- Recheck the deployed production bundle or runtime after push.

## Minimum Done Definition

A new publisher is not done until all of these are true:

- curated bootstrap succeeds or documented server limitations are isolated,
- runtime can publish at least one clean live cycle,
- observations can be read back from CSAPI,
- Explorer can find and explain the resources,
- side-card/popup output is domain-meaningful,
- docs explain source, model, commands, validation, and limitations,
- commits are pushed to the relevant repositories.
