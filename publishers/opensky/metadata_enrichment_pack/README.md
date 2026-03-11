# OpenSky Metadata Enrichment Pack

This pack is a metadata-focused enrichment set for `publishers/opensky/bootstrap_opensky.py`
in `OSHConnect-Python`.

It follows the same general pattern as the existing NWS and NDBC enrichment packs:

- patch-ready snippet files under `patches/`
- review notes under `notes/`
- source and reference manifests under `metadata/`
- a local representative asset under `assets/`

## Scope

This pack focuses on metadata and resource-description quality. It does **not**
change the OpenSky REST fetch logic or the observation publishing loop in
`opensky_publisher.py`.

## Why this pack exists

The current OpenSky bootstrap is already stronger than the original NWS/NDBC
baselines. It already includes:

- a clear Pattern C feed-adapter model
- a procedure with provenance and usage notes
- a system SensorML body with contacts, documents, characteristics, and capabilities
- a good datastream schema
- a deployment tree that matches the source architecture

The remaining gap is not basic structure. The remaining gap is curation:

- fuller explainability for auth modes, rate budgets, and configured cadence
- more explicit coverage metadata for the selected bounding box
- richer feed-adapter semantics in the system and deployment descriptions
- clearer datastream notes about snapshot semantics, deduplication, and nullable values
- a pack-local representative graphic and source manifest for future UI work

## What this pack includes

- `notes/AUDIT_AND_RECOMMENDATIONS.md`
- `notes/APPLY_ORDER.md`
- `metadata/source_urls.json`
- `metadata/coverage_auth_example.json`
- `metadata/position_source_reference.json`
- `assets/opensky_feed_adapter_generic.svg`
- `assets/official_image_reference.txt`
- `patches/01_constants_block.py`
- `patches/02_procedure_body.py`
- `patches/03_system_stub.py`
- `patches/04_system_sml.py`
- `patches/05_datastream_schema.py`
- `patches/06_deployment_blocks.py`
- `patches/07_config_enrichment_example.json`
- `patches/bootstrap_opensky_metadata_enriched_candidate_snippets.py`

## Recommended implementation order

1. Read `notes/AUDIT_AND_RECOMMENDATIONS.md`.
2. Review `metadata/source_urls.json` and confirm the official references still fit your desired story.
3. Apply the conservative metadata changes first:
   - better descriptions
   - more explicit documentation links
   - clearer coverage/auth/cadence notes
4. Apply the richer SensorML groupings once you are satisfied your OSH stack preserves them.
5. Treat the representative asset as optional UI/demo support, not a server dependency.

## Important note

This pack intentionally leans conservative on schema changes. The pack enriches
descriptions, manifests, and metadata structure more than it changes the runtime
SWE field list. That is deliberate: OpenSky already has a sound runtime path, so
the safest next step is to improve explainability without destabilizing the feed.
