# USGS / NIMS Public Data Publishers Follow-On Implementation Plan

_Last updated: 2026-03-11_

## 1. Purpose

This document is a **follow-on implementation plan** to the existing `Public_Data_Source_Publishers_Plan.md`. Its purpose is to define the next expansion wave of public-data publishers focused specifically on **USGS water-data and imagery sources**, with a secondary USGS event-feed option for earthquakes.

This plan assumes the first plan remains the governing roadmap for the broader public-source publisher initiative, but **some cross-cutting and polish activities from that first plan are intentionally deferred** until after all currently identified publishers have been created. That means this document prioritizes **source onboarding and working publishers first**, while postponing selected secondary activities such as extra polish, advanced Explorer UX work, and non-essential metadata refinement until the broader source set is complete.

## 2. Scope and relationship to the first plan

This follow-on plan adds three USGS-aligned source tracks:

1. **USGS Water Data OGC APIs** — fixed monitoring locations, time-series metadata, and water observations.
2. **USGS National Imagery Management System (NIMS)** — camera discovery and gaging-station imagery associated with USGS sites.
3. **USGS Earthquake feeds** — optional event-feed publisher for real-time seismic events.

This plan does **not** replace the first public-data-source plan. Instead, it extends it with a new USGS-focused work package and adopts the following sequencing rule:

> **Create all identified publishers first; defer selected cross-cutting enhancements until after publisher coverage is complete.**

Concretely, that means the emphasis is on standing up functioning publishers for water stations, imagery, and optional earthquake events before spending time on broader cleanup work such as advanced UI polish, richer visualization layers, or second-round metadata-pack work beyond what is needed to make each source credible and explorable.

## 3. Why these USGS sources are good additions

### 3.1 USGS water-data APIs are unusually aligned with the CSAPI effort

USGS states that its Water Data APIs already expose water data through the **OGC API family of standards**, including access to monitoring locations, time-series metadata, and water measurements. That makes this source unusually well aligned with an OGC API - Connected Systems demonstration because the upstream data model is already modern, standards-oriented, and explicitly geospatial. citeturn496793view1turn992799search0turn992799search9

### 3.2 NIMS gives a second modality: station imagery

USGS documents that the National Imagery Management System (NIMS) provides programmatic access to **gaging-station imagery**, including camera discovery, image file listings, base paths for full-size and thumbnail images, “newest image” URLs, and time-lapse video paths. This creates a natural extension of the existing publisher model: fixed monitoring systems can expose both scalar observations and image-related datastreams. citeturn496793view1turn100693view0

### 3.3 Earthquakes provide a clean event-feed use case

USGS also publishes real-time earthquake feeds in **GeoJSON, KML, QuakeML, CSV, and ATOM**, with the GeoJSON summary feed explicitly intended as a programmatic interface. This is a good candidate when the project wants a USGS event-stream demonstration that is not bound to fixed stations. citeturn970860search3turn970860search4

## 4. Planning assumptions

This plan is based on the following assumptions:

- The existing OSHConnect-Python publisher pattern remains the implementation baseline: one bootstrap script for CSAPI Part 1 resources and one publisher/runtime script for fetch-normalize-publish behavior.
- The project continues to prefer **deployed-system-first** and **normalized-first** modeling.
- The project is willing to obtain a **free USGS API key** for higher rate limits when needed. USGS documents that API keys raise the effective rate ceiling and are passed via query parameter or `X-Api-Key` header. Without a key, the newer APIs are more constrained. citeturn496793view1turn970860search1turn970860search2turn970860search5
- The first goal is **working publishers**, not maximum metadata perfection.
- Some activities previously planned in the first roadmap remain deferred until all identified publishers, including these USGS ones, have been stood up.

## 5. Recommended source portfolio and priority

### Priority 1 — USGS Water Monitoring Publisher

Build a publisher for **USGS monitoring locations and time-series metadata**, with an initial focus on a small curated set of water stations.

Why first:
- closest fit to the existing station/datastream model,
- upstream source is already OGC-oriented,
- allows immediate integration into the same fixed-system presentation model used for NWS, NDBC, and CO-OPS. citeturn496793view1turn992799search0turn992799search9

### Priority 2 — USGS NIMS Imagery Publisher

Build a companion imagery publisher for a curated subset of camera-equipped USGS gaging sites.

Why second:
- strongly complements the water monitoring publisher,
- introduces image and optional time-lapse observation patterns,
- gives the project a second real-world image source after BuoyCAM. citeturn100693view0

### Priority 3 — USGS Earthquake Publisher (optional but recommended)

Build an event-feed publisher from the USGS GeoJSON earthquake feeds.

Why third:
- clean event-stream use case,
- easy visual impact,
- broadens the public-source demo portfolio beyond environmental station networks. citeturn970860search3turn970860search4

## 6. Source-by-source implementation strategy

## 6.1 USGS Water Monitoring Publisher

### 6.1.1 Objective

Create a CSAPI publisher that represents selected USGS monitoring locations as systems and exposes one or more datastreams per site for water-related measurements and time-series metadata.

### 6.1.2 Why this is the best first USGS implementation

USGS’s Water Data APIs already expose:
- **monitoring locations**,
- **time series metadata**,
- OGC-compliant resource behavior,
- and water measurements in standardized formats. citeturn496793view1turn992799search0turn992799search9

That means the project does not need to invent a fragile scraping approach or heavily reverse-engineer the source.

### 6.1.3 Recommended initial modeling pattern

Use a **station-centric model**:

- **System**: one per selected USGS monitoring location.
- **Procedure**: a USGS water-observation acquisition and normalization procedure.
- **Deployment**: one top-level USGS Water monitoring deployment group, optionally with regional or watershed subgrouping later.
- **Datastreams**: begin with one or two curated datastream families per site rather than trying to mirror the full USGS catalog immediately.

Recommended first datastream candidates:
- water level or gage height,
- discharge/streamflow where available,
- water temperature where available,
- optional site-status or time-series metadata datastream if useful for explanation.

### 6.1.4 Normalization guidance

Normalize around a compact common observation shape:

- `phenomenonTime`
- `resultTime`
- `stationId`
- `parameterCode` or canonical observed-property key
- `value`
- `uom`
- `qualifier/status` if supplied
- optional `raw`

Keep source-specific richness in metadata rather than forcing every upstream field into the first version.

### 6.1.5 Bootstrap deliverables

- `publishers/usgs_water/bootstrap_usgs_water.py`
- `publishers/usgs_water/stations.json`
- one procedure resource
- one deployment root
- one system per station
- one datastream per initial variable family

### 6.1.6 Runtime publisher deliverables

- `publishers/usgs_water/usgs_water_publisher.py`
- station discovery or station-file loader
- polling client with API key support
- pagination handling, because USGS documents paginated responses and advises clients to follow returned `next` links rather than synthesizing them. citeturn970860search5
- normalized observation builder
- publish loop

### 6.1.7 Risks

- variable availability differs by site,
- overly ambitious station/parameter selection could create noisy data-model branching,
- pagination and rate-limit handling need to be implemented correctly. USGS notes maximum page sizes and `next` links, plus API-key-based rate limits. citeturn992799search7turn970860search1turn970860search5

### 6.1.8 Recommendation

Start with **5–10 carefully chosen stations** and **1–2 variables per station**, not full catalog parity.

## 6.2 USGS NIMS Imagery Publisher

### 6.2.1 Objective

Create a CSAPI publisher that exposes **USGS gaging-station imagery** as image-reference observations and optionally time-lapse media metadata.

### 6.2.2 Why NIMS is worth doing

NIMS explicitly supports:
- camera discovery via `/cameras`,
- image-file listings via `/listFiles`,
- construction of full-size, thumbnail, and 720px image URLs,
- a stable “newest image” pattern,
- and time-lapse video URLs via `tlDir + camId + '_720.mp4'`. citeturn100693view0

That is a strong fit for the kind of image-capable CSAPI demonstration you have already been moving toward with BuoyCAM.

### 6.2.3 Recommended implementation decision

Do **not** start by ingesting binary images into the server.

Instead:
- use NIMS API discovery to identify camera-equipped sites,
- construct stable image URLs,
- publish **image-reference observations** whose result records contain URLs, timestamps, media type, and camera identifiers,
- optionally cache or mirror images later if historical stability becomes necessary.

This mirrors the practical decision already used in other image-source planning: get the CSAPI and Explorer behavior working first, then decide if local image persistence is worth the added operational burden.

### 6.2.4 Modeling pattern

Two good patterns exist.

#### Pattern A — imagery as a companion datastream on the same station system

- **System**: USGS monitoring location
- **Datastream A**: numeric water observations
- **Datastream B**: latest/stored imagery observations

This is the preferred first pattern because it keeps the imagery directly associated with the water station.

#### Pattern B — camera as child system

- **System**: USGS monitoring location
- **Sub-system / linked system**: individual camera
- **Datastream**: image observations for that camera

This is richer but should be deferred until the first version is stable.

### 6.2.5 Observation result pattern

Recommended image observation result fields:

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

### 6.2.6 Bootstrap deliverables

- `publishers/usgs_nims/bootstrap_usgs_nims.py`
- `publishers/usgs_nims/cameras.json`
- one procedure resource
- deployment grouping for NIMS-enabled stations
- one imagery datastream per selected site or per selected camera

### 6.2.7 Runtime publisher deliverables

- `publishers/usgs_nims/usgs_nims_publisher.py`
- camera discovery client (`/cameras`)
- image listing client (`/listFiles`)
- URL constructor for `overlayDir`, `thumbDir`, `smallDir`
- most-recent optimization using `_newest.jpg` when appropriate
- optional time-lapse URL construction
- API-key support and rate-limit awareness. USGS states that NIMS uses the same API-key system and returns rate-limit headers. citeturn100693view0turn970860search1

### 6.2.8 Key constraints

- NIMS v0 is fully supported but legacy, and USGS recommends migrating to v1 once available. Build the publisher so the endpoint version is configurable. citeturn100693view0
- Not every water site has camera imagery.
- The easiest “newest image” pattern is excellent for live display but weaker for historic fidelity unless filenames are also stored.

### 6.2.9 Recommendation

Select a **small curated set of stations with cameras** and build a station-linked imagery datastream first.

## 6.3 USGS Earthquake Publisher (optional)

### 6.3.1 Objective

Create a CSAPI event-feed publisher using the USGS GeoJSON earthquake feeds.

### 6.3.2 Why it belongs in the portfolio

USGS explicitly presents its GeoJSON earthquake feeds as a programmatic interface, and the service offers real-time feeds plus more detailed event information. citeturn970860search3turn970860search4

### 6.3.3 Recommended model

Use a **feed-adapter event model**, not a fixed-station model:

- **System**: USGS Earthquake feed adapter
- **Datastream**: earthquake events
- **Observation/Event result**:
  - event ID
  - magnitude
  - place
  - time
  - updated time
  - longitude
  - latitude
  - depth
  - status
  - detail URL

Do not create one `System` per earthquake.

### 6.3.4 Deliverables

- `publishers/usgs_eq/bootstrap_usgs_eq.py`
- `publishers/usgs_eq/usgs_eq_publisher.py`
- one procedure
- one system
- one datastream
- polling / dedupe logic keyed by event ID and updated timestamp

### 6.3.5 Recommendation

Treat this as **recommended but optional**. It is a strong public-source addition, but it does not need to block delivery of the water + imagery work.

## 7. What is explicitly deferred from the first plan

This follow-on plan assumes the project is currently optimizing for **publisher coverage first**. Therefore, the following categories of work are intentionally deferred until after all identified publishers are built:

- advanced Explorer rendering enhancements beyond what is needed to prove each publisher,
- broader metadata second-pass enrichment packs that are not required for source credibility,
- non-essential packaging or repo refactoring not needed to stand up the next publisher,
- deeper per-object lifecycle modeling for feeds where feed-adapter modeling is sufficient,
- advanced analytics, fused overlays, and multi-source derived products,
- broad performance optimization beyond basic rate-limit-safe polling.

This is not a statement that these activities are unimportant. It is simply a sequencing rule: **finish the publisher set first, then return to deferred polish and harmonization tasks**.

## 8. Shared architecture decisions for this follow-on effort

### 8.1 Continue the two-script publisher pattern

For each USGS source, use:
- `bootstrap_{source}.py`
- `{source}_publisher.py`

### 8.2 Keep shared utilities centralized

Common logic should live in shared publisher helpers where possible:
- API-key handling
- pagination helpers
- polling cadence helpers
- image URL construction utilities
- common metadata blocks for procedures and deployments

### 8.3 Canonical field discipline

Across all public-source publishers, continue enforcing a small shared canonical observation vocabulary where feasible. This becomes especially important when mixing numeric monitoring stations and imagery/event publishers.

### 8.4 Prefer curated station sets first

Do not begin with nationwide scale. Begin with intentionally chosen sites that support the demonstration well.

## 9. Recommended implementation sequence

### Phase A — prep and selection

1. Freeze the deferred-work rule from the first plan.
2. Obtain one USGS API key for development and testing. USGS offers free keys and documents both query-parameter and header-based usage. citeturn970860search1turn970860search2
3. Select:
   - 5–10 water monitoring locations,
   - 3–5 NIMS-enabled camera sites,
   - optional earthquake feed variants.

### Phase B — water publisher

4. Implement `bootstrap_usgs_water.py`
5. Implement `usgs_water_publisher.py`
6. Validate station creation, datastream creation, paging, and sample observations

### Phase C — NIMS publisher

7. Implement `bootstrap_usgs_nims.py`
8. Implement `usgs_nims_publisher.py`
9. Validate image URL construction, newest-image behavior, and Explorer preview rendering

### Phase D — optional earthquake publisher

10. Implement `bootstrap_usgs_eq.py`
11. Implement `usgs_eq_publisher.py`
12. Validate event dedupe and map rendering

### Phase E — harmonization after source coverage improves

13. Revisit deferred polish items from the first plan
14. Decide whether water+imagery should be merged into one richer site model or kept as companion publishers
15. Add second-pass metadata enrichment only where it materially improves usability

## 10. Proposed acceptance criteria

### USGS Water Publisher

- Creates valid CSAPI metadata resources
- Publishes at least one numeric datastream for each selected station
- Handles paging correctly
- Uses API key support correctly
- Produces stable observations for at least one polling cycle

### USGS NIMS Publisher

- Discovers cameras for selected sites
- Constructs valid image URLs
- Publishes image-reference observations with timestamps
- Supports thumbnail or small-image rendering in Explorer
- Handles stations without imagery gracefully

### USGS Earthquake Publisher

- Polls a chosen GeoJSON feed successfully
- Deduplicates events by event identifier/update timestamp
- Publishes event observations that map correctly in Explorer

## 11. Recommended near-term decision

If only one new USGS track is started immediately, begin with:

1. **USGS Water Monitoring Publisher**
2. **USGS NIMS Imagery Publisher**
3. **USGS Earthquake Publisher**

That order is recommended because the first two form a coherent, station-centric pair and are directly relevant to the existing environmental/public-observation storyline, while the earthquake feed is valuable but more optional.

## 12. Bottom line

This follow-on plan adds a strong **USGS expansion package** to the public-data-publisher roadmap.

The most important strategic fact is that the water-data APIs are already OGC-oriented and NIMS already provides a documented imagery interface with camera discovery, image listings, and stable URL construction. That gives this project an unusually favorable path to adding **water monitoring**, **station imagery**, and optionally **event feeds** without resorting to fragile scraping or overly bespoke source logic. citeturn496793view1turn100693view0turn970860search3

The key sequencing rule remains:

> **Stand up the remaining identified publishers first, including these USGS ones, and defer selected polish and cross-cutting enhancements until publisher coverage is complete.**
