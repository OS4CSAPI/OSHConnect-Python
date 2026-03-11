# USGS Water Total Bootstrap, Data Model, and Enrichment Pack

This package is a comprehensive handoff bundle for the current `publishers/usgs_water`
publisher in `OSHConnect-Python`.

It is intentionally broader than the earlier metadata-only packs. It includes:

- a reviewed data-model section
- live-source verification notes
- a metadata-enrichment pack
- ready-to-apply bootstrap snippet candidates
- a package manifest suitable for zipping and external sharing

The package was assembled after cross-referencing:

- the current local `bootstrap_usgs_water.py`
- the current local `usgs_water_publisher.py`
- the current local `stations.json`
- existing NWS, NDBC, and OpenSky enrichment-pack patterns
- live USGS Water Data OGC API responses verified on 2026-03-11

## Scope

This package is designed to improve and document the USGS water publisher without
forcing risky runtime changes into the current production codepath.

It does three things:

1. documents the current architecture and observation contract
2. provides a richer metadata-enrichment layer for bootstrap resources
3. captures the most important follow-on runtime and modeling recommendations

## Why this package exists

The current USGS water publisher is already a strong Phase 1 implementation:

- one shared observing procedure
- one system per USGS monitoring location
- two datastreams per station
- a clean deployment tree
- a working publisher against the USGS Water Data OGC API

That baseline is sound. The main opportunity is to turn it into a better-documented,
better-evidenced, more semantically explicit publisher package.

The most important findings from live verification are:

- the USGS Water Data OGC API still exposes `monitoring-locations`, `continuous`,
  `latest-continuous`, `time-series-metadata`, and `combined-metadata`
- `latest-continuous` is available and is a better latest-only runtime target than
  `continuous?limit=1`
- `time-series-metadata` can return multiple series for the same station and parameter
  code, including both daily and instantaneous statistics
- `combined-metadata` is rich, but consumers must filter carefully or they may
  accidentally bind to the wrong statistic family

## Package layout

- `bundle_manifest.json`
- `notes/`
- `data_model/`
- `metadata/`
- `assets/`
- `patches/`

## Recommended reading order

1. `notes/LIVE_SOURCE_VERIFICATION_2026-03-11.md`
2. `notes/AUDIT_AND_RECOMMENDATIONS.md`
3. `data_model/RESOURCE_MODEL.md`
4. `metadata/source_urls.json`
5. `patches/bootstrap_usgs_water_metadata_enriched_candidate_snippets.py`

## Implementation stance

This pack is conservative where the current runtime is already good and explicit
where the current metadata is too thin.

It does not assume every recommended runtime improvement should be applied
immediately. In particular:

- metadata enrichment is recommended now
- stronger datastream provenance is recommended now
- `latest-continuous` migration is recommended next
- richer result-body fields are optional and should be adopted only if downstream
  consumers benefit from the added payload size and contract complexity
