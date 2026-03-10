# NWS Bootstrap Metadata Enrichment Pack

This pack is a ready-to-review metadata enrichment bundle for `publishers/nws/bootstrap_nws.py`.

## What this pack includes

- a reviewed snapshot of the current `bootstrap_nws.py`
- an enriched candidate version with fuller metadata
- a unified diff patch
- JSON templates for procedure, system, datastream, and deployment enrichment
- an asset-ready representative ASOS station graphic
- a source manifest with official NWS documentation and image references
- an audit summary and implementation notes

## Purpose

The current NWS bootstrap already has a strong functional spine. This pack is for the next step: making the NWS metadata feel complete, curated, and demo-ready.

The enrichment goals are:

1. improve provenance and explainability
2. add official documentation and endpoint URLs
3. add operator / program / support context
4. add a representative system image reference
5. tighten deployment wording so the Arizona subset is described accurately

## Recommended implementation order

1. review `AUDIT_AND_RECOMMENDATIONS.md`
2. inspect `patches/bootstrap_nws_metadata_enrichment.diff`
3. apply the candidate changes selectively
4. validate that any new custom metadata fields are accepted by your OSH / CSAPI stack
5. if needed, keep only the conservative subset: better descriptions, links, keywords, and image metadata

## Important note

The included `assets/nws_asos_station_generic.svg` is a clean local placeholder / representative graphic suitable for demo metadata packs.
An official NWS ASOS photo does exist and is referenced in `assets/official_image_reference.txt`, but the binary image could not be fetched directly into this session.
