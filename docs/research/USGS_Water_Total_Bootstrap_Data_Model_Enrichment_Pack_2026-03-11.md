# USGS Water Total Bootstrap, Data Model, and Enrichment Pack

**Date:** 2026-03-11  
**Author:** Codex  
**Status:** Created, packaged, and intended for repository handoff  
**Scope:** `publishers/usgs_water` total package including bootstrap guidance, data-model review, metadata enrichment, and zip artifact

---

## 1. Executive Summary

A new comprehensive USGS water package was created under:

- `publishers/usgs_water/total_bootstrap_data_model_enrichment_pack`

This package is broader than the earlier metadata-only packs. It includes:

- a reviewed resource-model description
- live-source verification notes against the current USGS Water Data OGC API
- metadata sidecars and worked examples
- bootstrap patch candidates for richer procedure, system, datastream, and deployment metadata
- a shareable zip artifact of the full package

The package is designed to keep the current station-centric publisher architecture
while materially improving provenance, semantic clarity, and future maintainability.

---

## 2. Why a Larger Package Was Justified

The USGS water publisher is already stronger than the early NWS/NDBC baselines.
It already has:

- one shared procedure
- one system per monitoring location
- two datastreams per station
- a coherent deployment tree
- a working runtime using the USGS Water Data OGC API

So the right move was not to redesign it. The right move was to package the
current implementation properly:

- make the data model explicit
- anchor the bootstrap to current live USGS semantics
- identify where metadata enrichment is safe now
- record where runtime follow-on improvements should happen later

---

## 3. Live Research Findings That Matter

The package was informed by live verification on 2026-03-11 against the USGS
Water Data OGC API.

The most important findings were:

1. `latest-continuous` is live and is the better latest-only runtime target than `continuous?limit=1`.
2. `time-series-metadata` can return multiple series for one station and parameter code, including daily and instantaneous variants.
3. `combined-metadata` is rich, but it must be filtered carefully or it may bind to the wrong statistic family.
4. `monitoring-locations` exposes more authoritative system metadata than the current bootstrap carries.
5. The active OGC API path is still `v0`, so the package intentionally keeps `v0` URLs.

The most important semantic conclusion is this:

For the current publisher, datastreams should be documented as the
`statistic_id=00011` instantaneous series. `parameter_code` alone is not a
precise enough description.

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
- live worked examples from the current USGS API
- an enriched station template
- a worked enriched station example for `09380000`

### 4.4 Assets

The `assets/` section contains:

- a generic local USGS water station SVG
- a note explaining why no single official station image was bundled

### 4.5 Bootstrap patch candidates

The `patches/` section contains:

- constants and helper URLs
- an enriched procedure body
- an enriched system stub
- an enriched SensorML system body
- enriched datastream schema candidates
- enriched deployment blocks
- an enriched station JSON example
- a compact candidate snippet summary

---

## 5. Design Position

This package makes a deliberate distinction between:

- what should be changed now
- what should be documented now but implemented later

### Recommended now

- richer procedure provenance
- richer station SensorML metadata
- more explicit datastream semantics and collection links
- optional enriched station-config sidecars
- better documentation of the current observation contract

### Recommended later

- move latest-only polling to `latest-continuous`
- decide whether `time_series_id` or `last_modified` should ever become result-body fields
- consider additional parameter families such as `00010`

This keeps the package robust without forcing unnecessary runtime churn.

---

## 6. Bottom Line

The new USGS water package is not just a metadata patch. It is a reviewed handoff
bundle for the current publisher:

- architecture clarified
- live upstream semantics verified
- enrichment candidates prepared
- zip artifact produced for transport and review

That is the right level of packaging for a publisher that is already functional
and now needs to become more explicit, more authoritative, and easier to extend.
