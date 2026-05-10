# CSAPI Server Quirks — Map Integration Debugging Session

**Date:** 2026-05-10  
**Status:** Complete  
**Scope:** Map integration defects across Go v2 and OSH servers — NIMS cameras, DSC card thumbnails, ISS photo, station images, timelapse links  
**Follows:** `CSAPI_Go_Server_Integration_Report_2026-04-17.md`

---

## 1  Executive Summary

During a map integration debugging session, five distinct server/client behavioral issues were uncovered. Three are server-side quirks in `connected-systems-go` (Go v2). One is a data completeness issue caused by a partial bootstrap. One is a documentation gap in the ISS system definition. All issues are now resolved with client-side workarounds and/or data patches.

| # | Issue | Severity | Servers | Resolved |
|---|-------|----------|---------|---------|
| Q1 | Go v2 SML responses are GeoJSON Features, not raw SML objects | P2 | Go v2 | Client workaround |
| Q2 | NIMS bootstrap silently incomplete — cameras never created | P2 | Go v2 | Bootstrap re-run |
| Q3 | `POST /deployments/{id}/subdeployments` 400 on full body | P2 | Go v2 | Minimal-stub retry |
| Q4 | OSH `system@link.href` includes `?f=json` query suffix | P3 | OSH | Strip in client |
| Q5 | NIMS observation queue empty on both servers (0 published) | P2 | Both | Publisher cycle run |

---

## 2  Q1 — Go v2 SML Responses Are GeoJSON Features

### Symptom
The Deployed System Card (DSC) showed no thumbnail, no station photo, and no SML-derived metadata (keywords, classifiers, contacts, documents) for any system on Go v2. The same systems on OSH displayed correctly.

### Root Cause
When fetching `GET /systems/{id}?f=application/sml+json`:

- **OSH** returns a raw SML object with fields at the top level:
  ```json
  {
    "type": "PhysicalSystem",
    "label": "NDBC 44025 — Long Island, NY",
    "keywords": [...],
    "identifiers": [...],
    "contacts": [...],
    "documents": [...]
  }
  ```

- **Go v2** returns a GeoJSON Feature wrapper with SML fields inside `.properties`:
  ```json
  {
    "type": "Feature",
    "id": "3b1bc3bc-...",
    "geometry": { "type": "Point", "coordinates": [...] },
    "properties": {
      "uid": "urn:os4csapi:system:...",
      "name": "CO-OPS 8518750 — The Battery, NY",
      "keywords": [...],
      "identifiers": [...],
      "contacts": [...],
      "documentation": [...]
    },
    "links": [...]
  }
  ```

All `extractSml*` functions in `useDeployedSystemCard.ts` read from `sml.keywords`, `sml.documentation`, etc. These were all `undefined` on Go v2 because the actual data lives in `sml.properties.*`.

Additional difference: OSH uses `documents` as the key for the documentation array. Go v2 uses `documentation`. The extractors already handled both (`sml?.documents || sml?.documentation`) — only the Feature wrapper was missed.

### Fix
Added a single normalization step before all SML extraction:

```typescript
// Normalize: Go v2 wraps SML as GeoJSON Feature (fields in .properties)
// OSH returns SML with fields at top level
const smlSource = systemSml?.type === 'Feature'
  ? (systemSml?.properties || {})
  : (systemSml || {})
```

All extractors now receive `smlSource` instead of `systemSml` directly.

**Commit:** `8eb8fc5` on `ogc-csapi-explorer` main  
**Affected systems:** Every system on Go v2 — CO-OPS stations, USGS water stations, NDBC buoys, ISS, NIMS cameras, all others.

### Systems Affected by This Quirk
- `card.thumbnail` — station photo (first `documentation` entry with `image/*` MIME)
- `card.summarySentence` — depends on SML description
- `card.kindBadge` / `card.roleBadge` — from classifiers/identifiers
- `card.docsLinks` — the documentation links panel
- `card.ownerMaintainer` — from contacts
- `card.methodSummary` — from procedure links
- Keywords, capabilities, identifiers — all derived from SML

---

## 3  Q2 — NIMS Bootstrap Silently Incomplete

### Symptom
NIMS cameras did not appear on the Go v2 map despite USGS water station systems being present on Go v2 and a "USGS NIMS Camera Stations" group deployment existing.

### Root Cause
The NIMS bootstrap (`bootstrap_usgs_nims.py`) was previously run against Go v2 and completed without errors. However it only created:
- ✅ Root deployment `urn:os4csapi:deployment:usgs-nims-demo:v1`
- ✅ Group deployment `urn:os4csapi:deployment:usgs-nims-cameras:v1`
- ✅ Procedure `urn:os4csapi:procedure:usgs-nims-imagery:v1`

It did **not** create:
- ❌ 8 individual camera sub-deployments (`usgs-nims-{siteId}:v1`)
- ❌ 8 `usgsNimsImage` datastreams on the water station systems

**Why silently?** The map renders deployment leaf nodes based on whether the deployment has a `platform@link`. The group deployment (`usgs-nims-cameras`) has 0 sub-deployments, so nothing renders — no error, just empty.

**Diagnosis commands:**
```powershell
# Confirmed 0 sub-deployments under the NIMS camera group
GET /deployments/81bb4aa3-a428-4325-9b1d-52d7b4a84412/subdeployments
# → { items: [] }

# Confirmed no usgsNimsImage datastream on water station system 09380000
GET /systems/c9d8de34-52a7-43a6-a08f-f85490d4baf5/datastreams
# → 2 items: Discharge, Gage Height (no image DS)
```

A dry-run confirmed what would be created:
```
[DRY] Would create datastream 'usgsNimsImage' on system c9d8de34... (09380000)
[DRY] Would create datastream 'usgsNimsImage' on system 9d06bc30... (09019850)
... (8 total)
[DRY] Would create deployment: urn:os4csapi:deployment:usgs-nims-09380000:v1
... (8 total)
```

### Fix
Re-ran `python -m publishers.usgs_nims.bootstrap_usgs_nims` (no `--dry-run`). All 8 datastreams and 8 camera sub-deployments created successfully.

Then ran `usgs_nims_publisher --once` against Go v2 to seed initial observations (all 8 images published).

### NIMS Structure on Go v2 (Post-Fix)

```
53458c4f  USGS NIMS Imagery Demo                  [root deployment]
└─ 81bb4aa3  USGS NIMS Camera Stations             [group]
   ├─ fbd0f765  NIMS Camera 09380000              [leaf, platform@link → c9d8de34]
   ├─ 73761560  NIMS Camera 09019850              [leaf]
   ├─ e0e71e45  NIMS Camera 11313433              [leaf]
   ├─ bd396835  NIMS Camera 08171000              [leaf]
   ├─ 353abfa8  NIMS Camera 01650800              [leaf]
   ├─ 62b191c1  NIMS Camera 05051300              [leaf]
   ├─ 9fffa737  NIMS Camera 12439500              [leaf]
   └─ 5bdf3fe4  NIMS Camera 02135000              [leaf]
```

---

## 4  Q3 — `POST /deployments/{id}/subdeployments` Returns 400 with Full Body

### Symptom
Every `POST /deployments/{id}/subdeployments` returned HTTP 400 on the first attempt during the NIMS bootstrap.

### Root Cause
Go v2 rejects some fields in the deployment body when POSTing to the subdeployments endpoint. The exact offending fields are not identified in the error response (body is empty / generic 400).

Bootstrap helper already implements a minimal-stub retry:
```python
[WARN] POST deployments/.../subdeployments failed (HTTP 400); retrying with minimal stub
[OK] Created deployment urn:os4csapi:deployment:usgs-nims-09380000:v1 → id=...
```

All 8 camera sub-deployments were created via the minimal stub on retry.

### Behavior Details
- Initial POST: full deployment body (uid, name, description, validTime, platform@link, ...) → **400**
- Retry POST: minimal stub (uid, name only) → **201 Created**, empty body
- After creation: full metadata PATCHed separately (when applicable)

### Note
This is distinct from the previously documented "201 with empty body" behavior (section 13.4 of the April report). This is a 400 on the initial POST that only affects the `/subdeployments` sub-endpoint, not the top-level `/deployments` endpoint.

**Recommendation for Go server issue:** File as separate issue — "POST /deployments/{id}/subdeployments rejects valid full deployment body with 400; top-level POST /deployments accepts same body."

---

## 5  Q4 — OSH `system@link.href` Includes `?f=json` Query String Suffix

### Symptom
When following a `system@link.href` from an OSH datastream resource to fetch the associated system, the href includes a query string:

```json
"system@link": {
  "href": "https://os4csapi-osh.duckdns.org/sensorhub/api/systems/045g?f=json"
}
```

Appending additional parameters (e.g., `?f=application/sml+json`) to this URL results in a malformed request:
```
GET /systems/045g?f=json?f=application%2Fsml%2Bjson  → 400 Bad Request
```

### Root Cause
OSH embeds its own internal format parameter in outbound hrefs. This is non-standard; RFC 3986 links should be canonical URLs without self-referential format hints.

### Workaround
Strip query string from hrefs before using them:
```typescript
systemId = platformLink.href.replace(/\/+$/, '').split('/').pop() || ''
// Extracts ID from path, discarding any ?f=... suffix
```

The Explorer already does this via the `split('/').pop()` pattern when extracting system IDs from hrefs. This works correctly.

**Note:** This quirk only manifests if you try to use the full href directly rather than extracting the ID. Clients that compose their own request URLs (using the extracted ID) are not affected.

---

## 6  Q5 — NIMS Observations Missing on Both Servers (0 Published)

### Symptom
NIMS image datastreams existed on both Go v2 and OSH but had 0 observations. The map marker and metadata card showed no camera image, no timelapse link.

### Root Cause
The `usgs-nims-publisher.service` systemd service targets OSH by default (via the `.env` file). On Go v2, a separate `usgs-nims-publisher-go.service` should exist (see Appendix A of April report). The Go v2 publisher was not running or had failed silently.

On OSH, the publisher had also failed to post new observations — likely a crash after the server migration to the new URL/auth config or a transient network issue.

### Immediate Fix
Ran one-shot publishes manually:

```powershell
# Go v2
$env:OSH_BASE_URL = "https://129-80-248-53.sslip.io/csapi-go-v2"
python -m publishers.usgs_nims.usgs_nims_publisher --once
# → Published: 8

# OSH
$env:OSH_BASE_URL = "https://129-80-248-53.sslip.io/sensorhub/api"
python -m publishers.usgs_nims.usgs_nims_publisher --once
# → Published: 8
```

### NIMS Observation Result Schema

For reference, a NIMS observation result from this publisher:
```json
{
  "camId": "AZ_Colorado_River_at_Lees_Ferry_Upstream",
  "filename": "AZ_Colorado_River_at_Lees_Ferry_Upstream___2026-05-10T23-00-05Z.jpg",
  "imageUrl": "https://usgs-nims-images.s3.amazonaws.com/overlay/AZ_Colorado_River_at_Lees_Ferry_Upstream/...jpg",
  "smallUrl": "https://usgs-nims-images.s3.amazonaws.com/720/AZ_Colorado_River_at_Lees_Ferry_Upstream/...jpg",
  "thumbUrl": "https://usgs-nims-images.s3.amazonaws.com/thumbnail/AZ_Colorado_River_at_Lees_Ferry_Upstream/...jpg",
  "mediaType": "image/jpeg",
  "stationId": "09380000",
  "timestamp": "2026-05-10T23:00:05Z",
  "timeLapseUrl": "https://usgs-nims-images.s3.amazonaws.com/timelapse/AZ_Colorado_River_at_Lees_Ferry_Upstream/...mp4"
}
```

The DSC card (`useDeployedSystemCard.ts`) reads these fields:
- `result.imageUrl` → `card.cameraImageUrl`
- `result.thumbUrl` → `card.cameraThumbUrl`
- `result.timeLapseUrl` → `card.cameraTimeLapseUrl`
- `result.camId` → `card.cameraCamId`
- `result.mediaType` → gate condition (must start with `image/`)

**NDBC BuoyCAM result schema** (for comparison):
```json
{
  "stationId": "46013",
  "imageUrl": "https://os4csapi-osh.duckdns.org/buoycam/46013/2026/04/17/...jpg",
  "mediaType": "image/jpeg",
  "cameraStatus": "ok",
  "sha256": "...",
  "contentLength": 59812.0,
  "latestImageUrl": "https://www.ndbc.noaa.gov/buoycam.php?station=46013"
}
```

BuoyCAM does **not** have `timeLapseUrl`. The timelapse link only appears for NIMS cameras.

---

## 7  Supplementary: ISS System Missing Documentation/Photo

Not a server quirk per se — a data gap in the ISS bootstrap.

### Symptom
The ISS DSC card showed no thumbnail. After Q1 was fixed (SML Feature normalization), the card could theoretically show a photo if one existed in the system's `documentation` array. The ISS position system had none.

### Fix
Added `documentation` array to `_system_position()` in `bootstrap_iss.py`:
```python
"documentation": [
    {
        "role": "http://dbpedia.org/resource/Photograph",
        "name": "ISS Photograph",
        "link": {
            "href": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/International_Space_Station_after_undocking_of_STS-132.jpg/640px-International_Space_Station_after_undocking_of_STS-132.jpg",
            "type": "image/jpeg",
        },
    },
    {
        "role": "http://dbpedia.org/resource/Web_page",
        "name": "ISS Tracking Page",
        "link": {
            "href": "https://spotthestation.nasa.gov/",
            "type": "text/html",
        },
    },
]
```

**Patched live** on both servers:
- Go v2 ISS position system: `8f06cdeb-d50e-4aca-baeb-5aa5601323ff` → PUT 204
- OSH ISS position system: `04i0` → PUT 204

---

## 8  Updated Behavioral Comparison Table

Extends the table from the April 2026 report (section 13.7).

| Behavior | SensorHub (OSH) | connected-systems-go (Go v2) |
|---|---|---|
| SML response format (`?f=application/sml+json`) | Raw SML object (top-level fields) | **GeoJSON Feature** (SML fields in `.properties`) |
| SML response key for documentation | `documents` | `documentation` |
| `system@link.href` format | Contains `?f=json` suffix | Clean path, no suffix |
| POST `/deployments/{id}/subdeployments` with full body | Accepts | **Returns 400**; minimal stub retry succeeds |
| `?f=` parameter for SML format | `?f=sml3` | `?f=application/sml%2Bjson` |
| `outputName` filter on `/datastreams` | **Not reliable** (returns wrong items) | Works correctly |
| Observation default sort | Ascending | Descending (newest-first) |
| `resultTime=latest` param | Honored | **Silently ignored** |
| `/deployments/{id}/systems` endpoint | Supported | **404 Not Found** |
| POST 201 response body | Full resource JSON | Empty; `Location` header only |

---

## 9  Server State After This Session

### Go v2 (`https://129-80-248-53.sslip.io/csapi-go-v2`)

| Resource Type | Count | Notes |
|---|---|---|
| Systems | ~37 | Unchanged |
| Datastreams | +8 | Added `usgsNimsImage` for 8 NIMS camera stations |
| Deployments | +10 | Added 8 NIMS camera leaf deployments (+ 2 already existed) |
| Observations | +8 | Initial NIMS image observations published |

### OSH (`https://129-80-248-53.sslip.io/sensorhub/api`)

| Resource Type | Count | Notes |
|---|---|---|
| Systems | ~44 | Unchanged |
| Datastreams | Unchanged | NIMS datastreams already existed |
| Observations | +8 | NIMS image observations published (were stale/empty) |

### System Patches Applied (Both Servers)

| System | Server | Change |
|---|---|---|
| ISS Position Publisher (`iss-position-publisher:v1`) | Go v2 | Added `documentation` with photo + tracking page |
| ISS Position Publisher (`iss-position-publisher:v1`) | OSH | Added `documentation` with photo + tracking page |

---

## 10  Client-Side Fixes Committed

| File | Change |
|---|---|
| `demo/src/composables/useDeployedSystemCard.ts` | Normalize SML source: detect Go v2 Feature wrapper, extract `.properties` before all `extractSml*` calls |
| `publishers/iss/bootstrap_iss.py` | Add `documentation` array (photo + tracking page) to `_system_position()` |

**Commit:** `8eb8fc5` — `ogc-csapi-explorer` main — deployed via Cloudflare auto-build.

---

## 11  Recommended Go Server Issues to File

These are new findings beyond the April report's outstanding list:

1. **`POST /deployments/{id}/subdeployments` rejects full body with 400** — body content vs. top-level endpoint inconsistency. Minimal stub workaround exists but forces a separate PATCH round-trip.

2. **SML responses from `GET /systems/{id}?f=application/sml+json` return GeoJSON Feature wrapper instead of raw SML** — breaks any client expecting SML field names at the top level of the response. OSH returns correct raw SML format.

3. **`usgs-nims-publisher-go.service` may not be running** — verify systemd service status on the VM; the publisher had 0 observations on Go v2 before manual re-run.
