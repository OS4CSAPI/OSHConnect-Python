# USGS NIMS Total Bootstrap, Data Model, and Enrichment Pack

**Date:** 2026-03-11  
**Author:** Codex  
**Status:** Created, packaged, and intended for repository handoff  
**Scope:** `publishers/usgs_nims` total package including bootstrap guidance, data-model review, metadata enrichment, and zip artifact

---

## 1. Executive Summary

A new comprehensive USGS NIMS package was created under:

- `publishers/usgs_nims/total_bootstrap_data_model_enrichment_pack`

This package is broader than a metadata-only pack. It includes:

- a reviewed resource-model description
- live-source verification notes against the current NIMS API and S3 URL behavior
- metadata sidecars and worked examples
- bootstrap patch candidates for richer procedure, datastream, deployment, and camera sidecar metadata
- a shareable zip artifact of the full package

The package is designed to preserve the current Pattern A shared-system model
while materially improving provenance, semantic clarity, and future maintainability.

---

## 2. Why a Larger Package Was Justified

The USGS NIMS publisher is already stronger than a raw prototype. It already has:

- one shared NIMS imagery procedure
- one imagery datastream per curated selected camera
- reuse of the existing USGS water station systems
- a coherent NIMS-specific deployment tree
- a working runtime that publishes image-reference observations

So the right move was not to redesign it blindly. The right move was to package
the current implementation properly:

- make the Pattern A shared-system model explicit
- anchor the bootstrap to current live NIMS semantics
- identify which metadata enrichments are safe now
- record where the current one-camera-per-station assumption becomes a real constraint

---

## 3. Live Research Findings That Matter

The package was informed by live verification on 2026-03-11 against the current
USGS NIMS API.

The most important findings were:

1. `cameras?camId=...` returns a single camera object with rich directory and cadence metadata.
2. `listFiles` supports both plain filename arrays and `rawItem=true` structured objects.
3. `siteId` discovery can return multiple cameras for one NWIS site.
4. Resolution-specific image URLs and timelapse URLs resolve successfully from the NIMS S3 bucket.
5. The active API path is still `v0`, so the package intentionally keeps `v0` URLs.

The most important modeling conclusion is this:

The current publisher is not a general many-camera-per-site publisher. It is a
selected-camera-per-station publisher attached to reused USGS water systems.

That is a sound model for the current curated set, but it should be documented as
an explicit design choice rather than treated as if the upstream API naturally
exposes only one camera per site.

---

## 4. Package Contents

### 4.1 Notes

The `notes/` section contains:

- live source verification
- audit and recommendations
- apply order
- runtime and model follow-on guidance

### 4.2 Data model

The `data_model/` section contains:

- a resource-model walkthrough
- machine-readable inventory
- current observation-contract documentation
- upstream-to-CSAPI field mapping

### 4.3 Metadata and examples

The `metadata/` section contains:

- official source URLs
- live worked examples from the current NIMS API
- a curated-site live camera-count snapshot
- direct URL-resolution verification
- enriched camera templates and worked examples

### 4.4 Assets

The `assets/` section contains:

- a generic local NIMS camera SVG
- a note explaining why no single official dynamic camera image was bundled

### 4.5 Bootstrap patch candidates

The `patches/` section contains:

- constants and helper URLs
- an enriched procedure body
- an enriched imagery datastream schema
- enriched deployment blocks
- an enriched camera JSON example
- a compact candidate snippet summary

---

## 5. Design Position

This package makes a deliberate distinction between:

- what should be changed now
- what should be documented now but implemented later

### Recommended now

- richer procedure provenance
- richer imagery datastream metadata
- clearer shared-system deployment wording
- optional enriched camera-config sidecars
- better documentation of the current image-reference observation contract

### Recommended later

- decide whether the one-camera-per-station rule remains the project policy
- if not, redesign explicitly for multi-camera sites
- evaluate whether `rawItem=true` should become the runtime default
- decide whether file size or upstream timestamp belong in future observation payloads

This keeps the package robust without forcing unnecessary runtime churn.

---

## 6. Bottom Line

The new USGS NIMS package is not just a metadata patch. It is a reviewed handoff
bundle for the current publisher:

- architecture clarified
- live upstream semantics verified
- enrichment candidates prepared
- zip artifact produced for transport and review

That is the right level of packaging for a publisher that is already functional
and now needs to become more explicit, more authoritative, and easier to extend.
