# OSH SensorHub Observation Count API Gap

**Date:** 2026-03-10  
**Server:** os4csapi-osh.duckdns.org (OSH SensorHub Community Edition)  
**Affects:** Admin tooling, observation store monitoring, purge workflows

## Summary

The OSH SensorHub server does not return `numberMatched` or `numberReturned`
in observation collection responses, contrary to the OGC Connected Systems API
(CSAPI) specification which defines these fields. This makes it impossible to
efficiently query the total observation count for a given datastream without
fetching the full result set.

## Specification Reference

Per OGC API – Connected Systems Part 2 (Observations & Commands), Section 7.5,
observation collection responses SHOULD include:

| Field             | Type    | Description                                      |
|-------------------|---------|--------------------------------------------------|
| `numberMatched`   | integer | Total number of observations matching the query  |
| `numberReturned`  | integer | Number of observations in the current page       |
| `items`           | array   | The observation records                          |
| `links`           | array   | Pagination links (`next`, `prev`)                |

## Observed Behavior

### Request: `limit=0` (count-only query)

```
GET /sensorhub/api/datastreams/04gg/observations?limit=0
Authorization: Basic <credentials>
```

**Expected response:**
```json
{
  "numberMatched": 6291,
  "numberReturned": 0,
  "items": [],
  "links": []
}
```

**Actual response:**
```json
{
  "items": [],
  "links": [
    {
      "rel": "next",
      "href": ".../observations?limit=0&offset=0",
      "type": "application/json"
    }
  ]
}
```

- `numberMatched` — **absent**
- `numberReturned` — **absent**
- A `next` link is returned even though `limit=0` was specified (questionable)

### Request: `limit=1` (single observation)

```
GET /sensorhub/api/datastreams/04gg/observations?limit=1
```

**Response keys:** `items`, `links` — no count metadata.

### Request: `limit=200` (normal page)

**Response keys:** `items` (200 entries), `links` — still no count metadata.

## Impact

1. **No efficient count query.** The only way to determine how many
   observations exist in a datastream is to page through the entire collection.
2. **Admin tooling workaround.** The Observation Store panel in the admin
   console now fetches with `limit=10000` and counts the `items` array. If a
   `next` link is present at that boundary, it displays "10,000+" as an
   overflow indicator. This is bandwidth-intensive but functional.
3. **Purge estimation.** Before purging, the admin UI cannot tell the user
   exactly how many observations will be deleted if the count exceeds 10,000.

## Measured Observation Volumes

Queried 2026-03-10 with `limit=10000`:

| Publisher | Datastream              | DS ID  | Count  |
|-----------|------------------------|--------|--------|
| ISS       | Position SGP4          | `04gg` | 6,291  |
| ISS       | Orbit Ground Track     | `04h0` | 6,291  |
| NWS       | KTUS Surface Obs       | `04qg` | 9      |
| NWS       | (10 stations × ~9 ea)  | —      | ~90    |
| NDBC      | Met Obs (5 buoys)      | —      | ~50    |
| NDBC      | BuoyCAM (5 buoys)      | —      | ~25    |
| CO-OPS    | Coastal Obs (5 stns)   | —      | ~50    |

Total publisher observations: approximately **12,800**.

## Workaround Implemented

In `demo/src/composables/useObsStore.ts`:

```typescript
// OSH SensorHub does not support numberMatched, so we fetch with a large
// limit and count items. If a "next" link is present, more obs exist.
const COUNT_LIMIT = 10000

const { ok, data } = await apiFetch(
  `/datastreams/${dsId}/observations?limit=${COUNT_LIMIT}`
)

if (ok && data) {
  const items = data.items ?? []
  const links = data.links ?? []
  const hasNext = links.some((l: any) => l.rel === 'next')

  // Prefer numberMatched if server ever implements it
  if (typeof data.numberMatched === 'number' && data.numberMatched > 0) {
    count = data.numberMatched
  } else {
    count = items.length
  }

  // Flag overflow
  if (hasNext && count === COUNT_LIMIT) {
    overflow = true  // display as "10,000+"
  }
}
```

## Recommendation

If contributing upstream to OSH SensorHub, the observation store handler
should be updated to include `numberMatched` in collection responses. The
H2 database backing store supports `SELECT COUNT(*)` which could supply this
without scanning the full result set. The `limit=0` pattern (count-only) is
widely used in OGC API implementations and should return the total without
fetching any observation payloads.
