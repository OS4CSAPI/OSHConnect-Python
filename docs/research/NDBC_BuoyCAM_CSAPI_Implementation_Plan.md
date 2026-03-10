# NDBC BuoyCAM via OGC API - Connected Systems (CSAPI)
## Real, Executable, Implementable Plan

_Last updated: 2026-03-10_

## 1. Executive decision

Yes — implement BuoyCAM support.

But do **not** start with native binary-image ingestion as the first increment.
The most executable path with the current OSHConnect + CSAPI bootstrap/publisher pattern is:

1. **Bootstrap one additional image-oriented datastream per camera-equipped buoy**
2. **Publish image-reference observations as a normal SWE/JSON record**
3. **Cache each fetched image to an immutable URL before publishing**
4. **Teach CSAPI Explorer to render that URL as an image preview**

This gives you a standards-aligned, historically stable, and low-risk implementation.

---

## 2. Why this is the right plan

### 2.1 Standards basis

OGC API - Connected Systems Part 2 clearly supports image/video-style outputs through datastreams and observations. The standard includes examples of:

- UAV video footage tasking
- UAV picture tasking
- satellite imagery acquisition
- an observation carrying a PNG image using `result@link`

So camera products are in scope for CSAPI.

### 2.2 NDBC source reality

NDBC BuoyCAM provides a stable **latest-image endpoint** per station and a BuoyCAM status/map experience, but the public-facing URL pattern is fundamentally a **latest** image link, not an immutable historical asset reference.

That means this distinction matters:

- **Live dashboard use** → a latest-image URL is sufficient
- **Historical observation archive** → a latest-image URL is *not* sufficient by itself

If you publish only the NDBC latest-image URL into observations, old observations will no longer reliably represent the image that was current when the observation was created.

### 2.3 Current stack reality

Your existing publisher plan is built around:

- bootstrap scripts creating Part 1 resources and datastream schemas
- publisher scripts using OSHConnect to build observation payloads and push them
- normalized, JSON-friendly datastream result records

That pattern is already proven and is the lowest-risk implementation path for BuoyCAM too.

---

## 3. Recommended target architecture

## 3.1 Resource model decision

### Parent `System`
Keep the **existing buoy `System`** as the parent resource.

### New `DataStream`
Add a new datastream for each camera-equipped buoy, for example:

- `BuoyCAM Image`
- or `BuoyCAM Latest Image`

### Optional future refinement
Later, if you want tighter semantics, introduce a **camera subsystem** under the buoy platform and attach the image datastream there.

### Recommendation
For v1, **do not block on subsystem modeling**.
Put the image datastream on the buoy system and ship.

---

## 3.2 Observation model decision

### Chosen v1 pattern: image-reference observation record
Use a normal JSON/SWE record as the observation result, not raw inline binary.

Recommended result fields:

- `resultTime` / `phenomenonTime`
- `stationId`
- `imageUrl`
- `mediaType`
- `sourceImageTime`
- `cameraStatus`
- `storageMode`
- `sha256`
- `contentLength`
- `title`
- `sourcePageUrl`
- `latestImageUrl`

This is the most practical fit for the current OSHConnect insertion workflow.

### Why not native `result@link` first?
CSAPI supports image observations, but your current working publisher path is based on schema-driven JSON record insertion. A JSON record with image metadata plus an immutable image URL is far more likely to work immediately with:

- current OSHConnect patterns
- current datastream schema tooling
- current Explorer rendering logic

### Future v2 pattern
Once the first version is working end-to-end, evaluate a more native image-observation encoding using `result@link`.

---

## 3.3 Storage mode decision

This is the single most important implementation decision.

### Option A — external-latest mode
Observation stores only:

- `imageUrl = https://www.ndbc.noaa.gov/buoycam.php?station=46025`

**Pros**
- fastest to implement
- no local storage
- ideal for a live demo

**Cons**
- not historically stable
- old observations drift semantically because the URL changes content over time
- daylight / stale image conditions create confusing UX

### Option B — cached-immutable mode (**recommended**)
Flow:

1. poll station camera status
2. fetch current image bytes when a new image is available
3. compute hash + timestamp
4. save the image to an immutable path you control
5. publish observation referencing the immutable cached image URL

Example cached URL shape:

`https://<your-static-host>/buoycam/46025/2026/03/10/20260310T181500Z.jpg`

**Pros**
- historically correct observations
- stable Explorer rendering
- future-friendly for archive playback
- allows metadata such as file hash and byte size

**Cons**
- requires static file hosting or object storage
- slightly more code

### Decision
Use **cached-immutable mode** as the primary implementation target.

---

## 4. Concrete implementation plan

## Phase 0 — prerequisite decisions

Freeze these now:

1. **Image storage host**
   - simplest: static directory served from the same VM / reverse proxy
   - cleaner: object storage / CDN (R2, S3-compatible, etc.)

2. **Station scope**
   - start with the selected buoy set already in the NDBC bootstrap
   - only enable camera datastreams for stations confirmed to have BuoyCAMs

3. **Explorer support level**
   - v1: popup thumbnail + click-through image
   - v2: lightbox / carousel / historical browse

---

## Phase 1 — bootstrap changes

Create a new version of the NDBC bootstrap that adds BuoyCAM resources.

### 4.1 Add a camera-capability registry

Augment your station config with camera information.

Example:

```json
{
  "ndbc_buoys": [
    {
      "stationId": "46025",
      "name": "Santa Monica Basin",
      "hasBuoyCam": true,
      "buoyCamLatestUrl": "https://www.ndbc.noaa.gov/buoycam.php?station=46025",
      "buoyCamPageUrl": "https://www.ndbc.noaa.gov/buoycams.shtml",
      "stationPageUrl": "https://www.ndbc.noaa.gov/station_page.php?station=46025",
      "statusPageUrl": "https://www.ndbc.noaa.gov/buoycam_status.php"
    }
  ]
}
```

### 4.2 Add a BuoyCAM procedure resource

Create a separate procedure UID, for example:

- `urn:os4csapi:procedure:ndbc:buoycam-imagery:v1`

Procedure metadata should include:

- NDBC BuoyCAM overview URL
- latest-image FAQ URL
- status page URL
- station page URL pattern
- description of daylight-only behavior
- description of "latest image" semantics
- note that cached immutable storage is performed by OS4CSAPI publisher logic

### 4.3 Add one BuoyCAM datastream per camera buoy

Suggested naming:

- `BuoyCAM Image`

Suggested datastream metadata:

- `outputName`: `BuoyCAM Image`
- `type`: `observation`
- `live`: `true`
- description explaining that each observation represents one fetched image frame from the buoy camera pipeline

### 4.4 Define the datastream result schema

Recommended v1 JSON/SWE record:

```json
{
  "resultTime": "2026-03-10T18:15:00Z",
  "stationId": "46025",
  "sourceImageTime": "2026-03-10T18:10:00Z",
  "cameraStatus": "ok",
  "mediaType": "image/jpeg",
  "storageMode": "cached",
  "imageUrl": "https://static.example.org/buoycam/46025/2026/03/10/20260310T181000Z.jpg",
  "latestImageUrl": "https://www.ndbc.noaa.gov/buoycam.php?station=46025",
  "sourcePageUrl": "https://www.ndbc.noaa.gov/station_page.php?station=46025",
  "title": "NDBC BuoyCAM image for station 46025",
  "sha256": "...",
  "contentLength": 184221
}
```

If you want a status-only observation during outages, you can still publish with:

- `cameraStatus = "stale" | "no_camera" | "error"`
- `imageUrl = null`

But for the first iteration, it is cleaner to publish **image observations only when a new image is successfully cached**.

### 4.5 Do not modify an existing populated datastream schema

Create a **new datastream** for BuoyCAM imagery rather than trying to mutate an existing one after observations exist.

---

## Phase 2 — publisher implementation

Create a dedicated publisher script:

`publishers/ndbc/ndbc_buoycam_publisher.py`

### 5.1 Publisher responsibilities

The publisher should:

1. load configured camera-enabled stations
2. connect to OSH and discover BuoyCAM datastreams
3. poll BuoyCAM status / latest image endpoints
4. detect whether a new image exists
5. fetch image bytes
6. compute hash / size / timestamps
7. write image to immutable storage
8. build observation record
9. push observation
10. expose health / stats

### 5.2 Polling cadence

Default interval: **900 seconds (15 minutes)**

Reason:
- aligns with NDBC BuoyCAM page refresh timing
- avoids unnecessary load
- matches the source behavior closely enough for a demo and archive

### 5.3 New-image detection strategy

Use this priority order:

#### Preferred
Parse the BuoyCAM status page for the configured stations and compare the reported image timestamp to the last published timestamp.

#### Fallback
Fetch the latest image and compare the image hash to the last stored hash.

#### Combined best practice
Use both:
- status timestamp for cheap change detection
- image hash as the final dedupe proof

### 5.4 Local state store

Persist per-station state in a tiny JSON or SQLite file:

- `stationId`
- `lastSourceImageTime`
- `lastSha256`
- `lastPublishedObservationId`
- `lastError`
- `lastFetchTime`

This prevents duplicate observations after restarts.

### 5.5 Error handling states

Implement these normalized states:

- `ok`
- `stale`
- `no_camera`
- `invalid_station`
- `fetch_error`
- `storage_error`
- `parse_error`

### 5.6 Recommended publish policy

#### v1 publish policy
Publish **only when a new image is successfully cached**.

This keeps the imagery datastream clean and avoids filling it with non-image status messages.

#### optional v1.1
Add a second status datastream later if you want health telemetry.

---

## Phase 3 — Explorer implementation

This is required if you want to actually **see** the camera results in the app.

### 6.1 Minimal rendering rule

In the popup / observation detail renderer:

If the observation result contains:

- `mediaType` beginning with `image/`
- and a non-empty `imageUrl`

then render:

- thumbnail image
- click-through full image
- `sourceImageTime`
- `stationId`
- `cameraStatus`

### 6.2 Nice-to-have enhancements

- image enlarge/lightbox
- "open source page" link
- fallback message when latest image is stale
- sort imagery datastreams distinctly from met/wave datastreams

### 6.3 Historical browse

Because the cached URL is immutable, the app can later support scrolling through prior image observations without changing the server model.

---

## 5. Code-level file plan

Recommended additions under `OSHConnect-Python/publishers/ndbc/`:

```text
publishers/
  ndbc/
    bootstrap_ndbc.py                     # extend existing bootstrap
    ndbc_publisher.py                     # existing met/wave publisher if/when added
    ndbc_buoycam_publisher.py             # new
    camera_station_config.json            # optional curated config
    camera_status.py                      # parse status page + availability
    image_cache.py                        # immutable local/object storage helper
    state_store.py                        # dedupe / restart state
    schemas.py                            # BuoyCAM datastream schema builder
```

Recommended Explorer-side work:

```text
ogc-csapi-explorer/
  src/
    ... popup or observation renderer code ...
    ... image-preview utility ...
```

---

## 6. Implementation details you can hand to Codex/Claude

## 6.1 Bootstrap tasks

1. add `hasBuoyCam` boolean to station config
2. create `ensure_buoycam_procedure()`
3. create `ensure_buoycam_datastream()`
4. only create BuoyCAM datastreams for stations with `hasBuoyCam = true`
5. keep imagery as a separate datastream from met/wave data

## 6.2 Publisher tasks

1. implement `fetch_buoycam_status(station_id)`
2. implement `fetch_latest_buoycam_image(station_id)`
3. implement `cache_image_bytes(station_id, source_time, image_bytes)`
4. implement `compute_sha256(image_bytes)`
5. implement `load_state()` / `save_state()`
6. implement `build_buoycam_observation()`
7. implement `run_loop(interval=900)`

## 6.3 Explorer tasks

1. detect image-like observation results
2. render `<img>` when `imageUrl` exists
3. show metadata fields in popup
4. gracefully handle missing image / stale image

---

## 7. Acceptance criteria

Implementation is complete when all of the following are true:

### Bootstrap
- camera-capable buoys receive a BuoyCAM datastream
- non-camera buoys do not receive a BuoyCAM datastream
- the procedure and datastream metadata include NDBC BuoyCAM links and notes

### Publisher
- a newly available image produces exactly one new observation
- the image is saved at an immutable URL
- restarts do not duplicate observations
- stale/no-camera/error conditions are handled without crashing

### Explorer
- clicking a buoy shows the BuoyCAM datastream
- imagery observations display an actual image preview
- old observations still show the same image because the cached URL is immutable

---

## 8. Test plan

## 8.1 Unit tests

- parse BuoyCAM status page row
- detect station not present
- detect blank or stale timestamp
- hash dedupe works
- immutable path builder works
- observation payload validates against schema

## 8.2 Integration tests

- bootstrap creates procedure + datastreams idempotently
- publisher dry-run fetches and builds payload without posting
- publisher posts one observation for one new image
- restart publisher and confirm no duplicate post

## 8.3 Manual validation

Use one confirmed BuoyCAM station and one non-BuoyCAM station.

Expected:
- camera station gets images
- non-camera station never gets imagery observations
- Explorer popup renders the image for the camera station

---

## 9. Risks and mitigations

## Risk 1 — public latest-image URL is not historically stable

**Mitigation:** cache every fetched image to immutable storage before publishing.

## Risk 2 — daylight-only and stale-image periods

**Mitigation:** track `cameraStatus` and last source timestamp; do not assume frequent images at night.

## Risk 3 — some selected buoys have no camera

**Mitigation:** explicit `hasBuoyCam` station config + bootstrap gating.

## Risk 4 — native CSAPI image encoding may require more server/client work than current OSHConnect path

**Mitigation:** start with record-wrapped image references; revisit native `result@link` later.

## Risk 5 — Explorer currently treats everything like JSON text

**Mitigation:** add a narrow rendering rule for `mediaType=image/*` + `imageUrl`.

---

## 10. Recommended implementation order

1. extend station config with camera flags
2. extend `bootstrap_ndbc.py` with BuoyCAM procedure + datastreams
3. build `ndbc_buoycam_publisher.py`
4. implement immutable image cache storage
5. publish from one test station
6. add Explorer image rendering
7. expand to the full selected camera-capable buoy set
8. optionally add status datastream or native `result@link` refinement

---

## 11. Final recommendation

Build BuoyCAM support now, but build it as:

- **separate image datastreams**
- **publisher-fetched + cached immutable images**
- **JSON-record observations pointing to those immutable images**
- **a small Explorer image renderer**

That is the cleanest balance of:

- CSAPI legitimacy
- historical correctness
- OSHConnect compatibility
- implementation speed
- demo value

---

## 12. Source notes

### OGC CSAPI
- OGC API - Connected Systems Part 2: https://docs.ogc.org/is/23-002/23-002.html

### NDBC BuoyCAM / NDBC portal
- NDBC BuoyCAM overview: https://www.ndbc.noaa.gov/buoycams.shtml
- NDBC latest BuoyCAM image FAQ: https://www.ndbc.noaa.gov/faq/buoycamlinks.shtml
- NDBC BuoyCAM status: https://www.ndbc.noaa.gov/buoycam_status.php
- NDBC observations portal: https://www.ndbc.noaa.gov/observations.shtml
- NDBC station map/search: https://www.ndbc.noaa.gov/
- NDBC real-time data: https://www.ndbc.noaa.gov/faq/realtime.shtml
- NDBC historical data: https://www.ndbc.noaa.gov/historical_data.shtml

### Project context
- Existing publisher plan and shared publisher architecture
- Existing NDBC/NWS bootstrap work
- Existing Explorer auto-discovery behavior
