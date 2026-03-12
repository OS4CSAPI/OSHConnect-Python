# USGS NIMS Total Bootstrap, Data Model, and Enrichment Pack

This package is a comprehensive handoff bundle for the current
`publishers/usgs_nims` publisher in `OSHConnect-Python`.

It is broader than a metadata-only enrichment pack. It includes:

- a reviewed data-model section
- live-source verification notes
- metadata sidecars and worked examples
- ready-to-apply bootstrap snippet candidates
- a package manifest suitable for zipping and external sharing

The package was assembled after cross-referencing:

- the current local `bootstrap_usgs_nims.py`
- the current local `usgs_nims_publisher.py`
- the current local `cameras.json`
- the current local USGS API reconnaissance notes
- the current USGS water publisher package and shared-system pattern
- live USGS NIMS API responses verified on 2026-03-11

## Scope

This package is designed to improve and document the USGS NIMS imagery publisher
without forcing risky runtime or architecture changes into the current codepath.

It does three things:

1. documents the current Pattern A shared-system model
2. provides a richer metadata-enrichment layer for NIMS procedure, datastream,
   deployment, and camera sidecar metadata
3. captures the most important follow-on runtime and model recommendations

## Why this package exists

The current USGS NIMS publisher already has a coherent architecture:

- one shared imagery procedure
- one imagery datastream per curated camera
- datastreams attached to existing USGS water station systems
- one NIMS-specific deployment tree
- one working publisher that emits image-reference observations instead of binary images

That baseline is sound. The main value of this package is to make the current
design more explicit, more authoritative, and easier to extend safely.

The most important findings from live verification are:

- `cameras?camId=...` currently returns a single camera object
- `cameras?siteId=...` can return multiple cameras for one NWIS site
- `listFiles` supports both plain filename arrays and richer `rawItem=true` objects
- resolution-specific image URLs and timelapse URLs resolve successfully from the
  NIMS S3 bucket
- the current publisher model assumes one selected camera per shared station system

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
5. `patches/bootstrap_usgs_nims_metadata_enriched_candidate_snippets.py`

## Implementation stance

This pack is conservative where the current runtime is already good and explicit
where the current metadata and data-model story are too thin.

It does not assume every future enhancement should be applied immediately. In particular:

- metadata enrichment is recommended now
- stronger camera-side provenance is recommended now
- multi-camera-per-site generalization is documented but not forced into the
  current package
- runtime contract expansion beyond the current image-reference payload is optional

## Important architecture note

This pack keeps the current Pattern A shared-system model:

- no new NIMS-specific systems are created
- imagery datastreams remain companion datastreams on existing USGS water systems

That means the richest enrichment targets are:

- the NIMS procedure
- the NIMS datastream schema and descriptions
- NIMS-specific deployments
- the curated `cameras.json` sidecar

It also means the package explicitly documents the current one-camera-per-station
assumption and the live evidence that some sites now expose multiple cameras.
