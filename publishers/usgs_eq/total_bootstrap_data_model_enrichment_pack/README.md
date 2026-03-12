# USGS Earthquake Total Bootstrap, Data Model, and Enrichment Pack

This package is a comprehensive handoff bundle for the current
`publishers/usgs_eq` publisher in `OSHConnect-Python`.

It is broader than a metadata-only enrichment pack. It includes:

- a reviewed Pattern C feed-adapter data-model section
- live-source verification notes against current official USGS earthquake feeds
- metadata sidecars and worked examples
- ready-to-apply bootstrap snippet candidates
- a package manifest suitable for zipping and external sharing

The package was assembled after cross-referencing:

- the current local `bootstrap_usgs_eq.py`
- the current local `usgs_eq_publisher.py`
- the current local `config.json`
- the current local USGS API reconnaissance notes
- the current follow-on publishers plan
- live USGS earthquake feed, detail, lifecycle, and FDSN resources verified on 2026-03-12

## Scope

This package is designed to improve and document the USGS earthquake publisher
without forcing risky runtime or architecture changes into the current codepath.

It does three things:

1. documents the current Pattern C feed-adapter model
2. provides a richer metadata-enrichment layer for earthquake procedure,
   system, datastream, and deployment resources
3. captures the highest-value follow-on runtime and model recommendations

## Why this package exists

The current USGS earthquake publisher already has a coherent architecture:

- one shared earthquake normalization procedure
- one global feed-adapter system
- one earthquake-events datastream
- one simple deployment tree
- one working publisher that emits one observation per earthquake event

That baseline is sound. The main value of this package is to make the current
design more explicit, more authoritative, and easier to extend safely.

The most important findings from live verification are:

- the `all_day` summary feed is live and currently reports 287 events
- the `significant_month` summary feed is live and currently reports 11 events
- each summary feature includes a per-event `detail` link
- the detail feed adds a `products` structure with contributor-specific
  resources such as `origin`, `phase-data`, `nearby-cities`, and `scitech-link`
- the FDSN `query.geojson` service exposes the same richer event surface and is
  best treated as a companion or future backfill source, not a required
  replacement for the summary feed
- the feed lifecycle policy states production feeds are available for at least
  six months and receive at least 30 days notice before deprecation

## Package layout

- `bundle_manifest.json`
- `notes/`
- `data_model/`
- `metadata/`
- `assets/`
- `patches/`

## Recommended reading order

1. `notes/LIVE_SOURCE_VERIFICATION_2026-03-12.md`
2. `notes/AUDIT_AND_RECOMMENDATIONS.md`
3. `data_model/RESOURCE_MODEL.md`
4. `metadata/source_urls.json`
5. `patches/bootstrap_usgs_eq_metadata_enriched_candidate_snippets.py`

## Implementation stance

This pack is conservative where the current runtime is already correct and
explicit where the current metadata and data-model story are still thin.

It does not assume every possible enrichment should be applied immediately. In particular:

- metadata enrichment is recommended now
- richer datastream semantics and official-source provenance are recommended now
- detail-feed and FDSN-event-service alignment are documented now
- summary-feed polling remains the recommended default runtime path
- selective detail enrichment for significant or revised events is optional

## Important architecture notes

This pack keeps the current Pattern C model:

- no system-per-earthquake expansion
- no per-event bootstrap resources
- no requirement to poll the detail feed on every cycle

That means the richest enrichment targets are:

- the earthquake normalization procedure
- the feed-adapter system metadata
- the earthquake datastream schema and documentation
- the deployment metadata and feed-variant documentation

It also means the package explicitly documents the current omission of several
available upstream fields such as `sig`, `tsunami`, `alert`, `net`, `url`, and
detail `products`, so future extensions can be made intentionally rather than
accidentally.
