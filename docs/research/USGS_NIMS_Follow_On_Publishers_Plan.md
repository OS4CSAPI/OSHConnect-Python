# USGS / NIMS Public Data Publishers Follow-On Implementation Plan

_Last updated: 2026-03-11_

---

## 1. Purpose

This document is a **follow-on implementation plan** to the existing [Public_Data_Source_Publishers_Plan.md](Public_Data_Source_Publishers_Plan.md). Its purpose is to define the next expansion wave of public-data publishers focused specifically on **USGS water-data and imagery sources**, with a secondary USGS event-feed option for earthquakes.

This plan is organized into **sequential phases**, each building one complete publisher from reconnaissance through deployment. Each phase is self-contained: you finish one publisher before starting the next. This avoids half-built publishers and ensures every phase delivers a running service.

---

## 2. Scope and Relationship to the First Plan

This follow-on plan adds three USGS-aligned source tracks:

1. **USGS Water Data APIs** — fixed monitoring locations, time-series metadata, and water observations.
2. **USGS National Imagery Management System (NIMS)** — camera discovery and gaging-station imagery associated with USGS sites.
3. **USGS Earthquake Feeds** — optional event-feed publisher for real-time seismic events.

This plan does **not** replace the first public-data-source plan. It extends it with a USGS-focused work package and adopts the following sequencing rule:

> **Create all identified publishers first; defer selected cross-cutting enhancements until after publisher coverage is complete.**

---

## 3. Why These USGS Sources Are Good Additions

### 3.1 USGS Water Data APIs are unusually aligned with the CSAPI effort

USGS states that its Water Data APIs already expose water data through the **OGC API family of standards**, including access to monitoring locations, time-series metadata, and water measurements. The upstream data model is already modern, standards-oriented, and explicitly geospatial.

### 3.2 NIMS gives a second modality: station imagery

USGS documents that the National Imagery Management System (NIMS) provides programmatic access to **gaging-station imagery**, including camera discovery, image file listings, base paths for full-size and thumbnail images, "newest image" URLs, and time-lapse video paths. This creates a natural extension of the existing publisher model: fixed monitoring systems can expose both scalar observations and image-related datastreams.

### 3.3 Earthquakes provide a clean event-feed use case

USGS publishes real-time earthquake feeds in **GeoJSON, KML, QuakeML, CSV, and ATOM**, with the GeoJSON summary feed explicitly designed as a programmatic interface. This is a good candidate for a USGS event-stream demonstration that is not bound to fixed stations.

---

## 4. Planning Assumptions

- The existing OSHConnect-Python publisher pattern remains the implementation baseline: one bootstrap script for CSAPI Part 1 resources and one publisher script for fetch-normalize-publish behavior. The proven directory structure is:
  ```
  publishers/{source}/
    ├── __init__.py
    ├── bootstrap_{source}.py
    ├── {source}_publisher.py
    └── stations.json (or config.json)
  ```
- The project continues to prefer **deployed-system-first** and **normalized-first** modeling.
- The first goal is **working publishers**, not maximum metadata perfection.
- Each publisher will run as a persistent process on the Oracle VM (`129.80.248.53`), consistent with the existing NWS, NDBC, CO-OPS, Aviation WX, OpenSky, and ISS publishers.
- Some activities previously planned in the first roadmap remain deferred until all identified publishers have been stood up.

---

## 5. Shared Architecture Decisions

### 5.1 Continue the two-script publisher pattern

For each USGS source:
- `bootstrap_{source}.py` — creates CSAPI Part 1 metadata (procedure, deployment, systems, datastreams)
- `{source}_publisher.py` — polls upstream API, normalizes observations, publishes to OSH

### 5.2 Keep shared utilities centralized

Common logic should live in `publishers/base.py` and `publishers/bootstrap_helpers.py`:
- API-key handling (USGS API key via query parameter or `X-Api-Key` header)
- Pagination helpers (follow `next` links, never synthesize page URLs)
- Polling cadence helpers
- Image URL construction utilities
- Common metadata blocks for procedures and deployments

### 5.3 Canonical field discipline

Continue enforcing a small shared canonical observation vocabulary across all publishers. This becomes especially important when mixing numeric monitoring stations and imagery/event publishers.

### 5.4 Prefer curated station sets first

Do not begin with nationwide scale. Begin with intentionally chosen sites that support the demonstration well: **5–10 water stations**, **3–5 camera-equipped stations**, and **1 earthquake feed**.

---

## 6. Phase 0 — Prerequisites

**Goal:** Establish the prerequisites that all three publishers depend on. No code is written in this phase.

| Step | Task | Deliverable | Done? |
|---|---|---|---|
| 0.1 | **Obtain USGS API key** — register at https://api.usgs.gov and obtain a free API key. Without it, USGS rate limits will constrain development. All three publishers share one key. | API key stored in a `.env` file or environment variable on the VM | ☑ |
| 0.2 | **API reconnaissance — USGS Water Data** — probe the actual USGS Water Data endpoints to determine: (a) which base URL to use (legacy `waterservices.usgs.gov` vs newer `labs.waterdata.usgs.gov`), (b) the actual response JSON structure for monitoring locations and time-series values, (c) available parameters per site, (d) pagination behavior. | Written recon notes documenting base URL, response shapes, and selected stations | ☑ |
| 0.3 | **API reconnaissance — NIMS** — probe the NIMS camera discovery and image listing endpoints to determine: (a) whether NIMS v1 is live or v0 is the current version, (b) the camera discovery response format (`/cameras`), (c) the image listing response format (`/listFiles`), (d) URL construction patterns for full-size/thumbnail/newest images. | Written recon notes documenting endpoint version, response shapes, and URL patterns | ☑ |
| 0.4 | **API reconnaissance — USGS Earthquake** — fetch the GeoJSON summary feed (`earthquake.usgs.gov/earthquakes/feed/v1.0/summary/*.geojson`) to confirm response structure, event ID format, and update timestamp field. | Written recon notes documenting response shape and dedupe key | ☑ |
| 0.5 | **Station selection** — using the recon results, select: (a) 5–10 USGS water monitoring locations with reliable gage height and/or discharge data, (b) 3–5 of those stations (or nearby stations) that have NIMS cameras, (c) 1 earthquake feed variant (e.g., `all_hour.geojson` or `significant_month.geojson`). | `stations.json` draft for water, `cameras.json` draft for NIMS, feed URL for earthquake | ☑ |

**Exit criteria:** API key obtained, all three APIs probed with real responses examined, station/camera/feed selections made.

---

## 7. Phase 1 — USGS Water Monitoring Publisher

**Goal:** Build a complete publisher for selected USGS monitoring locations with numeric water observations.

### 7.1 Modeling Pattern

Use a **station-centric model** consistent with existing NWS/NDBC/CO-OPS publishers:

- **System**: one per selected USGS monitoring location
- **Procedure**: one USGS water-observation acquisition and normalization procedure
- **Deployment**: one top-level "USGS Water Monitoring" deployment, with one subdeployment per station (following the 1:1 deployment pairing pattern)
- **Datastreams**: 1–2 per station from the following candidates:
  - gage height / water level
  - discharge / streamflow
  - water temperature (where available)

### 7.2 Normalization

Normalize around a compact common observation shape:

- `phenomenonTime`
- `resultTime`
- `stationId`
- `parameterCode` or canonical observed-property key
- `value`
- `uom`
- `qualifier/status` if supplied
- optional `raw`

### 7.3 Implementation Steps

| Step | Task | Deliverable |
|---|---|---|
| 1.1 | **Create directory structure** | `publishers/usgs_water/__init__.py` |
| 1.2 | **Create station config** — finalize the curated station list from Phase 0 recon, including site IDs, names, coordinates, and selected parameter codes | `publishers/usgs_water/stations.json` |
| 1.3 | **Implement bootstrap** — create procedure, top-level deployment, per-station subdeployments with `platform@link`, per-station systems, and datastreams for selected parameters | `publishers/usgs_water/bootstrap_usgs_water.py` |
| 1.4 | **Run bootstrap on OSH** — execute against the live server, capture all created resource IDs | Bootstrap output with ID map |
| 1.5 | **Implement publisher** — polling client with API key support, `next`-link pagination handling, normalized observation builder, publish loop | `publishers/usgs_water/usgs_water_publisher.py` |
| 1.6 | **Local test** — run publisher locally, verify observations appear on OSH, check at least one full polling cycle produces correct data | Manual verification |
| 1.7 | **Deploy to VM** — copy publisher to Oracle VM, configure as a persistent process, verify it runs unattended | Running process on `129.80.248.53` |
| 1.8 | **Verify in Explorer** — confirm stations appear in the deployment tree, datastreams show observations, map pins are positioned correctly | Visual verification in demo app |

### 7.4 Risks

- Variable availability differs by site — some selected stations may lack a parameter. Handle gracefully (skip missing parameters, don't fail the whole station).
- Pagination and rate-limit handling must be correct. USGS documents maximum page sizes, `next` links, and API-key-based rate ceilings.
- The newer `labs.waterdata.usgs.gov` API may have different behavior than legacy `waterservices.usgs.gov` — the Phase 0 recon will determine which to use.

### 7.5 Acceptance Criteria

- [ ] Creates valid CSAPI metadata resources (procedure, deployment hierarchy, systems, datastreams)
- [ ] Publishes at least one numeric datastream per selected station
- [ ] Handles pagination correctly (follows `next` links)
- [ ] Uses API key correctly (query parameter or `X-Api-Key` header)
- [ ] Produces stable observations for at least one full polling cycle
- [ ] Stations visible in Explorer with correct map positions and data

**Exit criteria:** Water publisher running on VM, observations flowing, visible in Explorer.

---

## 8. Phase 2 — USGS NIMS Imagery Publisher

**Goal:** Build a companion publisher that exposes USGS gaging-station imagery as image-reference observations.

### 8.1 Modeling Pattern

Use **Pattern A — imagery as a companion datastream** on the same station system (preferred over creating separate camera systems):

- **System**: reuse the USGS monitoring location system from Phase 1 where the station has cameras, or create a new system for camera-only sites
- **Procedure**: one USGS NIMS image acquisition and normalization procedure
- **Deployment**: subdeployment under the USGS Water Monitoring deployment (or separate "USGS NIMS Imagery" deployment if stations don't overlap)
- **Datastream**: one imagery datastream per selected camera/site

### 8.2 Key Design Decision

Do **not** ingest binary images into the server. Instead:
- Use NIMS API discovery to identify camera-equipped sites
- Construct stable image URLs from the NIMS base paths
- Publish **image-reference observations** whose result records contain URLs, timestamps, media type, and camera identifiers
- Optionally cache or mirror images later if historical stability becomes necessary

This mirrors the BuoyCAM approach already proven in the NDBC publisher.

### 8.3 Observation Result Pattern

- `imageTime`
- `camId`
- `siteId`
- `imageUrl`
- `thumbUrl`
- `smallUrl`
- `mediaType`
- optional `timeLapseUrl`
- optional `filename`
- optional `raw`

### 8.4 Implementation Steps

| Step | Task | Deliverable |
|---|---|---|
| 2.1 | **Create directory structure** | `publishers/usgs_nims/__init__.py` |
| 2.2 | **Create camera config** — finalize the curated camera list from Phase 0 recon, including site IDs, camera IDs, and image base paths | `publishers/usgs_nims/cameras.json` |
| 2.3 | **Decide system reuse** — for stations that overlap with Phase 1 water stations, determine whether to add an imagery datastream to the existing system or create a new system. Document the decision. | Decision recorded |
| 2.4 | **Implement bootstrap** — create procedure, deployment structure, systems (or reuse), imagery datastreams per selected camera | `publishers/usgs_nims/bootstrap_usgs_nims.py` |
| 2.5 | **Run bootstrap on OSH** — execute against the live server, capture all created resource IDs | Bootstrap output with ID map |
| 2.6 | **Implement publisher** — camera discovery client, image listing client, URL constructor for `overlayDir`/`thumbDir`/`smallDir`, most-recent optimization using `_newest.jpg`, API-key support, publish loop | `publishers/usgs_nims/usgs_nims_publisher.py` |
| 2.7 | **Local test** — run publisher locally, verify image-reference observations appear on OSH with correct URLs | Manual verification |
| 2.8 | **Deploy to VM** — copy publisher to Oracle VM, configure as a persistent process | Running process on `129.80.248.53` |
| 2.9 | **Verify in Explorer** — confirm image observations appear, thumbnails render in the UI, newest-image pattern works for live display | Visual verification in demo app |

### 8.5 Key Constraints

- NIMS v0 is fully supported but legacy; USGS recommends migrating to v1 once available. Build the publisher so the endpoint base URL is configurable.
- Not every water site has camera imagery — handle missing cameras gracefully.
- The "newest image" pattern is excellent for live display but weaker for historic fidelity unless filenames are also stored.

### 8.6 Acceptance Criteria

- [ ] Discovers cameras for selected sites via NIMS API
- [ ] Constructs valid image URLs (full-size, thumbnail, small)
- [ ] Publishes image-reference observations with timestamps
- [ ] Thumbnails or small images render correctly in Explorer
- [ ] Handles stations without imagery gracefully (skip, don't fail)
- [ ] Endpoint version is configurable (v0/v1)

**Exit criteria:** NIMS publisher running on VM, image observations flowing, thumbnails visible in Explorer.

---

## 9. Phase 3 — USGS Earthquake Publisher (Optional but Recommended)

**Goal:** Build an event-feed publisher from the USGS GeoJSON earthquake feeds.

### 9.1 Modeling Pattern

Use a **feed-adapter event model**, not a fixed-station model:

- **System**: one "USGS Earthquake Feed" adapter system (do NOT create one system per earthquake)
- **Procedure**: one earthquake feed normalization procedure
- **Deployment**: one "USGS Earthquake Feed" deployment
- **Datastream**: one earthquake events datastream

### 9.2 Observation Result Pattern

- `eventId`
- `magnitude`
- `place`
- `time`
- `updatedTime`
- `longitude`
- `latitude`
- `depth`
- `status`
- `detailUrl`

### 9.3 Implementation Steps

| Step | Task | Deliverable |
|---|---|---|
| 3.1 | **Create directory structure** | `publishers/usgs_eq/__init__.py` |
| 3.2 | **Create feed config** — document the selected feed URL and polling interval | `publishers/usgs_eq/config.json` |
| 3.3 | **Implement bootstrap** — create procedure, system, deployment, one earthquake-events datastream | `publishers/usgs_eq/bootstrap_usgs_eq.py` |
| 3.4 | **Run bootstrap on OSH** — execute against the live server | Bootstrap output with ID map |
| 3.5 | **Implement publisher** — GeoJSON feed poller, event deduplication logic (keyed by event ID + updated timestamp), normalized observation builder, publish loop | `publishers/usgs_eq/usgs_eq_publisher.py` |
| 3.6 | **Local test** — run publisher locally, verify earthquake observations appear on OSH, confirm dedupe prevents duplicates across polling cycles | Manual verification |
| 3.7 | **Deploy to VM** — copy publisher to Oracle VM, configure as a persistent process | Running process on `129.80.248.53` |
| 3.8 | **Verify in Explorer** — confirm earthquake events appear on the map with correct locations, magnitudes render meaningfully | Visual verification in demo app |

### 9.4 Acceptance Criteria

- [ ] Polls the selected GeoJSON feed successfully
- [ ] Deduplicates events by event ID and updated timestamp
- [ ] Publishes earthquake observations that map correctly in Explorer
- [ ] Does not create one system per earthquake (single feed-adapter system)
- [ ] Handles feed errors gracefully (retry, don't crash)

**Exit criteria:** Earthquake publisher running on VM, events flowing, visible on map in Explorer.

---

## 10. Phase 4 — Harmonization and Deferred Work

**Goal:** Now that all identified publishers are running, revisit deferred work from the first plan.

This phase is intentionally vague — it is a placeholder for work that should only begin after Phases 1–3 deliver running publishers.

| Step | Task |
|---|---|
| 4.1 | **Decide water + imagery merge** — should the water publisher and NIMS publisher share station systems, or should they remain separate companions? The Phase 2 decision (step 2.3) may already have resolved this at a station level; this step evaluates whether to formalize the pattern project-wide. |
| 4.2 | **Metadata enrichment pass** — apply the same enrichment-pack approach used for NWS/NDBC/CO-OPS to the USGS publishers if it materially improves the Explorer experience. |
| 4.3 | **Explorer rendering enhancements** — any advanced visualization work (water-level charts, image galleries, earthquake magnitude rendering) that was deferred during publisher construction. |
| 4.4 | **Cross-publisher observation vocabulary audit** — verify that all publishers (NWS, NDBC, CO-OPS, Aviation WX, OpenSky, ISS, USGS Water, USGS NIMS, USGS EQ) use consistent canonical observation field names where applicable. |
| 4.5 | **Performance review** — evaluate polling cadences, rate-limit headroom, and observation volume across all publishers running simultaneously on the VM. |
| 4.6 | **Revisit first plan deferrals** — review `Public_Data_Source_Publishers_Plan.md` for any originally-deferred items that are now unblocked. |

---

## 11. What Is Explicitly Deferred Until Phase 4

The following categories of work are intentionally deferred until after all publishers are running:

- Advanced Explorer rendering enhancements beyond what is needed to prove each publisher
- Broader metadata second-pass enrichment packs not required for source credibility
- Non-essential packaging or repo refactoring not needed to stand up the next publisher
- Deeper per-object lifecycle modeling for feeds where feed-adapter modeling is sufficient
- Advanced analytics, fused overlays, and multi-source derived products
- Broad performance optimization beyond basic rate-limit-safe polling
- Docker/systemd formalization (publishers run as persistent processes first; containerization is a Phase 4+ activity)

This is not a statement that these activities are unimportant. It is a sequencing rule: **finish the publisher set first, then return to deferred polish and harmonization tasks**.

---

## 12. Summary: Phase Sequence and Exit Gates

| Phase | Publisher | Key Exit Gate |
|---|---|---|
| **Phase 0** | Prerequisites | API key obtained, all 3 APIs probed, stations/cameras/feeds selected |
| **Phase 1** | USGS Water Monitoring | Publisher running on VM, numeric observations flowing, visible in Explorer |
| **Phase 2** | USGS NIMS Imagery | Publisher running on VM, image-reference observations flowing, thumbnails visible in Explorer |
| **Phase 3** | USGS Earthquake (optional) | Publisher running on VM, earthquake events on map in Explorer |
| **Phase 4** | Harmonization | Deferred work addressed, cross-publisher consistency verified |

Each phase is completed before the next begins. No half-built publishers.

---

## 13. Bottom Line

This plan adds a strong **USGS expansion package** to the public-data-publisher roadmap. The most important strategic fact is that the water-data APIs are already OGC-oriented and NIMS already provides a documented imagery interface with camera discovery, image listings, and stable URL construction. That gives this project an unusually favorable path to adding **water monitoring**, **station imagery**, and optionally **event feeds** without resorting to fragile scraping or overly bespoke source logic.

The key sequencing rule:

> **Complete each phase before starting the next. Stand up each publisher as a running service before moving on. Defer polish and cross-cutting enhancements until all publishers are live.**
