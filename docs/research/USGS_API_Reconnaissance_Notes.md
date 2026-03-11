# USGS API Reconnaissance Notes

_Probed: 2026-03-11_

These notes document the results of hitting all three USGS API families live. This is Phase 0 step 0.2–0.4 of the [USGS/NIMS Follow-On Publishers Plan](USGS_NIMS_Follow_On_Publishers_Plan.md).

---

## 1. USGS Water Data API (OGC API — Features)

### 1.1 Base URL

```
https://api.waterdata.usgs.gov/ogcapi/v0/
```

This is the **new OGC-compliant API** — not the legacy `waterservices.usgs.gov/nwis/iv/`. Both work, but the new API returns clean GeoJSON and supports cursor-based pagination. **Recommendation: use the new OGC API as the primary source.**

### 1.2 Collections

| Collection | Path | Description |
|---|---|---|
| Monitoring Locations | `/collections/monitoring-locations/items` | Site metadata as GeoJSON Features |
| Continuous Values | `/collections/continuous/items` | Real-time 15-min observations |
| Daily Values | `/collections/daily/items` | Historical daily aggregates |
| Time Series Metadata | `/collections/time-series-metadata/items` | Metadata about time series (units, thresholds, date ranges) |

Documentation links:
- OpenAPI spec: `https://api.waterdata.usgs.gov/ogcapi/v0/openapi?f=html`
- Endpoint catalog: `https://api.waterdata.usgs.gov/ogcapi/v0/collections?f=html`
- Long-form docs: `https://api.waterdata.usgs.gov/docs/ogcapi/`

### 1.3 Monitoring Location Response Shape

`GET /ogcapi/v0/collections/monitoring-locations/items/USGS-09380000?f=json`

```json
{
  "type": "Feature",
  "id": "USGS-09380000",
  "geometry": {
    "type": "Point",
    "coordinates": [-111.58787222, 36.86433333]
  },
  "properties": {
    "id": "USGS-09380000",
    "agency_code": "USGS",
    "agency_name": "U.S. Geological Survey",
    "monitoring_location_number": "09380000",
    "monitoring_location_name": "COLORADO RIVER AT LEES FERRY, AZ",
    "state_code": "04",
    "state_name": "Arizona",
    "county_name": "Coconino County",
    "site_type_code": "ST",
    "site_type": "Stream",
    "hydrologic_unit_code": "140700061105",
    "altitude": 3109.13,
    "altitude_accuracy": 0.09,
    "vertical_datum": "NAVD88",
    "drainage_area": 111800.0,
    "time_zone_abbreviation": "MST",
    "uses_daylight_savings": "N"
  },
  "links": [
    {"rel": "self", "href": "...?f=json"},
    {"rel": "alternate", "href": "...?f=jsonld"},
    {"rel": "alternate", "href": "...?f=html"}
  ]
}
```

Key fields for publisher: `id`, `monitoring_location_name`, `geometry.coordinates`, `site_type_code`, `state_name`, `time_zone_abbreviation`.

### 1.4 Continuous Values Response Shape

`GET /ogcapi/v0/collections/continuous/items?monitoring_location_id=USGS-09380000&parameter_code=00060&limit=5&f=json`

```json
{
  "type": "FeatureCollection",
  "numberReturned": 5,
  "features": [
    {
      "type": "Feature",
      "id": "71439235-3eff-4f99-a732-17c4c294e498",
      "geometry": null,
      "properties": {
        "id": "71439235-3eff-4f99-a732-17c4c294e498",
        "time_series_id": "a62122d8ff094125b63bb2f73410b2b4",
        "monitoring_location_id": "USGS-09380000",
        "parameter_code": "00060",
        "statistic_id": "00011",
        "time": "2025-03-11T20:15:00+00:00",
        "value": "9880",
        "unit_of_measure": "ft^3/s",
        "approval_status": "Approved",
        "qualifier": null,
        "last_modified": "2025-08-08T19:58:54.427722+00:00"
      }
    }
  ],
  "links": [
    {
      "rel": "next",
      "href": "...?cursor=YTYy...&monitoring_location_id=USGS-09380000&parameter_code=00060&limit=5",
      "type": "application/geo+json",
      "title": "Items (next)"
    }
  ]
}
```

### 1.5 Queryable Fields (Continuous)

| Field | Type | Notes |
|---|---|---|
| `monitoring_location_id` | string | e.g. `USGS-09380000` |
| `parameter_code` | string | e.g. `00060` (discharge), `00065` (gage height) |
| `statistic_id` | string | e.g. `00011` |
| `time` | string (ISO 8601) | Primary instant |
| `value` | string | Numeric value as string |
| `unit_of_measure` | string | e.g. `ft^3/s`, `ft` |
| `approval_status` | string | e.g. `Approved`, `Provisional` |
| `qualifier` | string | Nullable |
| `last_modified` | string (ISO 8601) | |
| `time_series_id` | string | UUID linking to time-series-metadata |

### 1.6 Pagination

**Cursor-based**. The response contains a `links` array with a `rel: "next"` entry whose `href` includes a `cursor` parameter. Follow the `next` link until it no longer appears. Do **not** synthesize cursor values.

### 1.7 Key Parameter Codes

| Code | Description | Unit |
|---|---|---|
| `00060` | Discharge (streamflow) | ft³/s |
| `00065` | Gage height | ft |
| `00010` | Water temperature | °C |

### 1.8 Legacy NWIS API (backup)

The legacy API at `waterservices.usgs.gov/nwis/iv/` also works and returns similar data in a WaterML-JSON envelope:

```
GET https://waterservices.usgs.gov/nwis/iv/?format=json&sites=09380000&parameterCd=00060,00065&period=P1D
```

Response shape: `value.timeSeries[n].values[0].value[n].dateTime/value/qualifiers`, with site metadata in `sourceInfo` and variable metadata in `variable`. This is a fallback if the new API has issues.

---

## 2. USGS NIMS Imagery API

### 2.1 Base URL

```
https://api.waterdata.usgs.gov/nims/v0/
```

This is **NIMS v0** (current and live). The plan mentioned a migration path to v1 — as of this recon, v0 is the only available version. Swagger docs: `https://api.waterdata.usgs.gov/nims/v0/docs`.

**Important:** The old `apps.usgs.gov/nims/` endpoint returns 403. The `apps.usgs.gov/hivis/` URL loads a visualization web app (HIVIS), not an API. Use `api.waterdata.usgs.gov/nims/v0/` exclusively.

### 2.2 Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/cameras` | GET | Camera discovery — returns array of camera objects |
| `/listFiles` | GET | Image filename listing for a specific camera |

### 2.3 Camera Inventory (live as of 2026-03-11)

| Metric | Count |
|---|---|
| Total cameras | 1,137 |
| Active (not hidden) | 989 |
| Hidden | 148 |
| Active with valid NWIS ID | 962 |
| States covered | 46 |

States: AK, AL, AZ, CA, CO, CT, DC, DE, FL, GA, GU, ID, IL, IN, KS, KY, LA, MA, MD, ME, MI, MN, MO, MT, NC, ND, NE, NJ, NM, NV, NY, OH, OK, OR, PA, PR, RI, SC, SD, TX, UT, VA, WA, WI, WV, WY

### 2.4 Camera Object Shape

`GET /nims/v0/cameras?limit=5`

Returns a JSON array (not wrapped in an envelope):

```json
[
  {
    "camId": "CO_Blue_River_Below_Dillon",
    "nwisId": "09050700",
    "camName": "Blue River Below Dillon",
    "camDesc": "Blue River Below Dillon, CO",
    "lat": "39.625542",
    "lng": "-106.0664082",
    "stateAbrv": "CO",
    "tz": "US/Mountain",
    "defaultPCode": "00065",
    "createdDate": "2022-10-04T17:48:46.068Z",
    "modifiedDate": "2022-10-04T17:48:46.068Z",
    "newestImageDT": "2026-03-11T20:00:09.000Z",
    "TL_enabled": true,
    "TL_lastGeneratedDT": "2026-03-11T18:02:32.879Z",
    "TL_lastImageUsedDT": "2026-03-11T18:00:09.000Z",
    "hideCam": false,
    "overlayDir": "https://usgs-nims-images.s3.amazonaws.com/overlay/CO_Blue_River_Below_Dillon/",
    "thumbDir": "https://usgs-nims-images.s3.amazonaws.com/thumbnail/CO_Blue_River_Below_Dillon/",
    "smallDir": "https://usgs-nims-images.s3.amazonaws.com/720/CO_Blue_River_Below_Dillon/",
    "tlDir": "https://usgs-nims-images.s3.amazonaws.com/timelapse/CO_Blue_River_Below_Dillon/",
    "ingest": {
      "period": "daylight",
      "intr": 15,
      "specificArr": []
    },
    "locus": "aws"
  }
]
```

Key fields for publisher: `camId`, `nwisId`, `camName`, `lat`, `lng`, `stateAbrv`, `newestImageDT`, `overlayDir`, `thumbDir`, `smallDir`, `tlDir`, `TL_enabled`.

### 2.5 listFiles Response Shape

`GET /nims/v0/listFiles?camId=CO_Blue_River_Below_Dillon&limit=3&recent=true`

Returns a plain JSON array of filename strings:

```json
[
  "CO_Blue_River_Below_Dillon___2026-03-11T20-00-09Z.jpg",
  "CO_Blue_River_Below_Dillon___2026-03-11T19-45-10Z.jpg",
  "CO_Blue_River_Below_Dillon___2026-03-11T19-30-09Z.jpg"
]
```

Parameters: `camId` (required), `limit` (default 1000, max 50000), `recent` (default true), `after`/`before` (ISO 8601 date filters), `rawItem` (returns objects with camId, filename, timestamp, fs instead of strings).

### 2.6 Image URL Construction

Combine the camera's directory URLs with a filename from listFiles:

| Size | Pattern | Example Size |
|---|---|---|
| Full/overlay | `{overlayDir}{filename}` | ~1 MB |
| 720px small | `{smallDir}{filename}` | ~85 KB |
| Thumbnail | `{thumbDir}{filename}` | ~15 KB |
| Timelapse | `{tlDir}{camId}_720.mp4` | varies |

**Verified working** — all three image sizes return HTTP 200 with `image/jpeg` content type.

### 2.7 Filename Pattern

```
{camId}___YYYY-MM-DDTHH-mm-ssZ.jpg
```

Note: three underscores between camId and timestamp. Timestamp uses dashes instead of colons (filesystem-safe ISO 8601).

### 2.8 Newest Image Pattern

The `___newest.jpg` shortcut URL does **NOT** work on S3 directly (returns 404). To get the newest image, use:

```
GET /nims/v0/listFiles?camId={camId}&limit=1&recent=true
```

Then construct the URL from the returned filename.

### 2.9 Filtering Cameras

The `/cameras` endpoint supports these query parameters:
- `camId` — single camera by ID
- `siteId` — cameras by NWIS site ID
- `state` — cameras by state abbreviation
- `limit` — max results
- `returnFields` — comma-separated field list to limit response size

### 2.10 NIMS-to-Water-API Station Linking

The `nwisId` field links directly to the USGS monitoring location. The NIMS `nwisId` is the numeric part of the OGC API's `USGS-{nwisId}` identifier. For example:
- NIMS: `nwisId: "09050700"`
- OGC API: `monitoring_location_id: "USGS-09050700"`

This confirms that water stations and camera stations can be linked by nwisId.

---

## 3. USGS Earthquake GeoJSON Feed

### 3.1 Base URL

```
https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed_variant}.geojson
```

### 3.2 Available Feed Variants

| Feed | Description |
|---|---|
| `all_hour.geojson` | All earthquakes, past hour |
| `all_day.geojson` | All earthquakes, past day |
| `all_week.geojson` | All earthquakes, past week |
| `all_month.geojson` | All earthquakes, past month |
| `significant_hour.geojson` | Significant only, past hour |
| `significant_day.geojson` | Significant only, past day |
| `significant_week.geojson` | Significant only, past week |
| `significant_month.geojson` | Significant only, past month |
| `1.0_hour.geojson` | M1.0+ past hour |
| `2.5_day.geojson` | M2.5+ past day |
| `4.5_week.geojson` | M4.5+ past week |

### 3.3 Response Shape

`GET /feed/v1.0/summary/all_hour.geojson`

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "generated": 1773259620000,
    "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
    "title": "USGS All Earthquakes, Past Hour",
    "status": 200,
    "api": "2.3.0",
    "count": 5
  },
  "features": [
    {
      "type": "Feature",
      "id": "aka2026eyfank",
      "geometry": {
        "type": "Point",
        "coordinates": [-149.632, 61.644, 16.2]
      },
      "properties": {
        "mag": 3.7,
        "place": "2 km NW of Meadow Lakes, Alaska",
        "time": 1773259458958,
        "updated": 1773259575570,
        "tz": null,
        "url": "https://earthquake.usgs.gov/earthquakes/eventpage/aka2026eyfank",
        "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/aka2026eyfank.geojson",
        "felt": null,
        "cdi": null,
        "mmi": null,
        "alert": null,
        "status": "automatic",
        "tsunami": 0,
        "sig": 211,
        "net": "ak",
        "code": "a2026eyfank",
        "ids": ",aka2026eyfank,",
        "sources": ",ak,",
        "types": ",origin,phase-data,",
        "nst": 113,
        "dmin": 0.2,
        "rms": 1.2,
        "gap": 40,
        "magType": "ml",
        "type": "earthquake",
        "title": "M 3.7 - 2 km NW of Meadow Lakes, Alaska"
      }
    }
  ]
}
```

### 3.4 Key Fields for Publisher

| Field | Type | Notes |
|---|---|---|
| `id` | string | Event ID (e.g. `aka2026eyfank`) — **dedupe key** |
| `properties.mag` | float | Magnitude |
| `properties.place` | string | Human-readable location |
| `properties.time` | int | Unix epoch ms — event time |
| `properties.updated` | int | Unix epoch ms — last update time (**dedupe key**) |
| `properties.status` | string | `automatic` or `reviewed` |
| `properties.type` | string | `earthquake`, `quarry blast`, etc. |
| `properties.title` | string | e.g. "M 3.7 - 2 km NW of Meadow Lakes, Alaska" |
| `properties.detail` | string | URL to detailed GeoJSON for this event |
| `geometry.coordinates` | array | `[longitude, latitude, depth_km]` |

### 3.5 Pagination

**None.** The feed is a single JSON document with all matching events. No pagination needed.

### 3.6 Dedupe Strategy

Event ID (`feature.id`) + updated timestamp (`properties.updated`). If the same event ID appears with a newer `updated` value, it should be treated as a revision, not a duplicate.

### 3.7 No API Key Required

The earthquake feed does not require an API key. It is a static-ish GeoJSON file regenerated by the server at regular intervals.

---

## 4. Summary of Findings

| Source | Base URL | Auth | Pagination | Status |
|---|---|---|---|---|
| Water Data (OGC API) | `api.waterdata.usgs.gov/ogcapi/v0/` | API key recommended | Cursor-based `next` links | ✅ Working |
| Water Data (legacy NWIS) | `waterservices.usgs.gov/nwis/iv/` | None required | None (single response) | ✅ Working (backup) |
| NIMS v0 | `api.waterdata.usgs.gov/nims/v0/` | API key recommended | limit/offset via params | ✅ Working |
| Earthquake Feed | `earthquake.usgs.gov/earthquakes/feed/v1.0/summary/` | None | None (single document) | ✅ Working |

### What Worked Differently Than Expected

1. The `labs.waterdata.usgs.gov` URL from earlier documentation is **dead** (403). The correct URL is `api.waterdata.usgs.gov`.
2. The NIMS `___newest.jpg` shortcut on S3 returns **404**. Use `listFiles?recent=true&limit=1` instead.
3. The old `apps.usgs.gov/nims/` endpoint returns **403**. NIMS moved to `api.waterdata.usgs.gov/nims/v0/`.
4. The OGC API continuous values return `geometry: null` for individual observations (geometry is on the monitoring location, not on each reading). This is fine — we get coordinates from the monitoring location and attach them to the system.

### Ready for Station Selection

All three APIs are confirmed working and response structures are documented. Next step: **Phase 0 Step 0.5 — select curated stations, cameras, and earthquake feed variant**.
