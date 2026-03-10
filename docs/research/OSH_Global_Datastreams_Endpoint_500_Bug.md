# OSH Server Bug: Global `/datastreams` Endpoint Returns 500 Internal Server Error

**Date:** 2026-03-10
**Severity:** High — silently breaks all frontend features that depend on global datastream discovery
**Server:** `os4csapi-osh.duckdns.org:443` (Oracle VM, OSH SensorHub)

## Summary

The global `/sensorhub/api/datastreams` endpoint crashes mid-response with a `500 Internal Server Error` after serializing the first datastream. The error is appended inline to the JSON body, producing malformed output that cannot be parsed by any client.

This bug silently prevents the demo webapp from discovering ISS satellite tracking datastreams, rendering the ISS invisible on the map despite the ISS publisher running normally and fresh observations existing on the server.

## Reproduction

```bash
# limit=1 → OK (returns senrep datastream 044g)
curl -sk -u os4csapi:ogc134mm \
  "https://os4csapi-osh.duckdns.org/sensorhub/api/datastreams?limit=1"
# → valid JSON, 1 item

# limit=2 → CRASH (server fails serializing the 2nd datastream)
curl -sk -u os4csapi:ogc134mm \
  "https://os4csapi-osh.duckdns.org/sensorhub/api/datastreams?limit=2"
# → malformed JSON: valid 1st item followed by {"status":500,"message":"Internal server error"}
```

### Malformed response structure

```json
{
  "items": [
    { "id": "044g", "name": "SENREP (Sensor Report)", ... }
  ]{
  "status": 500,
  "message": "Internal server error"
}
```

Note the missing comma and the error object appended directly after the closing `]` — this is not valid JSON.

## Impact

### ISS Satellite Tracking (PRIMARY)

The demo app's `MapViewPage.vue` relies on `buildSystemLocationCache()` Phase C, which calls `/datastreams?limit=200` to discover all datastreams globally. The ISS system (`04og`) and its deployment (`048g`) both have **null geometry** — the ISS position is entirely observation-derived. The discovery flow is:

1. Phase A: Static geometry → ISS has none → skipped
2. Phase B: Subsystem propagation → ISS is not a subsystem → skipped
3. Phase C: Global datastream fetch → **BROKEN** → ISS datastream `04gg` never enters `locationDatastreamList`
4. Result: No orbit track, no observation points, no ISS marker on the map

### Per-System Datastream Fetches (SECONDARY)

The system `04o0` (AZ String Alpha Localizer) also returns a 500 when querying its datastreams directly:

```bash
curl -sk -u os4csapi:ogc134mm \
  "https://os4csapi-osh.duckdns.org/sensorhub/api/systems/04o0/datastreams"
# → 500 Internal Server Error
```

This suggests a corrupted or incompatible datastream schema registered under the localizer system. It is likely the same root cause — the server's JSON serializer encounters a datastream it cannot serialize and throws an unhandled exception.

## What Still Works

Individual datastream access by ID is unaffected:

| Datastream | ID   | Individual GET | Status |
|------------|------|----------------|--------|
| SENREP     | 044g | ✅ 200         | OK     |
| ISS Position | 04gg | ✅ 200       | OK     |
| ISS Orbit Track | 04h0 | ✅ 200   | OK     |
| NWS KTUS   | 04ig | ✅ 200         | OK     |
| NWS KDMA   | 04j0 | ✅ 200         | OK     |
| NWS KFHU   | 04jg | ✅ 200         | OK     |
| NWS KLUF   | 04k0 | ✅ 200         | OK     |
| NWS KPHX   | 04kg | ✅ 200         | OK     |

Per-system datastream queries work for all systems **except** `04o0` (localizer).

ISS observations are fresh (latest: `2026-03-10T05:20:36Z`). The ISS publisher is running normally on the Oracle VM.

## Root Cause Hypothesis

The server's global datastream listing iterates all registered datastreams in internal ID order. After the senrep datastream (`044g`), the next datastream in order belongs to one of the AZ-MA systems. The server encounters a datastream whose schema it cannot serialize to JSON (possibly a corrupted or edge-case schema from the localizer bootstrap) and throws an unhandled exception mid-stream.

Because OSH uses streaming JSON serialization, the first item is already flushed to the client before the error occurs. The error handler then appends the 500 body to the already-started response, producing invalid JSON.

## Client-Side Workaround

The demo app has been patched to **not depend on the global `/datastreams` endpoint** for ISS discovery. Instead, after `enrichDeployments()` discovers systems linked via `platform@link` in the deployment tree, a supplementary datastream fetch is performed for those newly-discovered system IDs. This bypasses the broken global endpoint entirely.

See: `csapi-explorer` commit for the fix in `demo/src/pages/MapViewPage.vue`.

## Recommended Server-Side Investigation

1. Check OSH SensorHub server logs for the full Java stack trace when `/datastreams?limit=2` is requested
2. Identify which datastream in H2/PostgreSQL storage triggers the serialization failure
3. If the localizer system's (`04o0`) datastream is corrupted, consider deleting and re-bootstrapping it
4. Add try/catch around individual datastream serialization in the global listing handler so one bad record doesn't poison the entire response
