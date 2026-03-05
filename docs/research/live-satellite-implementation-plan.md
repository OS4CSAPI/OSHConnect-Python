# Live Satellite Tracking — Implementation Plan

**Date:** 2026-03-05  
**Status:** Approved — not yet implemented  
**Prerequisites:** [live-satellite-tracking-data-source.md](live-satellite-tracking-data-source.md) (research)  
**Input:** Deployed-System-First Data Model review (weigh-in document, simplified per OS4CSAPI team review)

---

## Design Decisions

### Simplifications applied to the weigh-in proposal

The weigh-in document proposed a 4-level deployment tree with 2 systems, 2 leaf deployments, and a DataArray-based orbit track datastream. After review, the following simplifications were adopted:

1. **One system, not two.** The position feed and orbit track are produced by the same script, same propagation, same element set — two outputs of one process. This mirrors the ODAS mic arrays (one system, multiple datastreams).

2. **Flat deployment tree.** The intermediate layers ("LEO Objects", "ISS Tracking Role") are empty categories with no siblings for v1. They can be added later when multiple satellites justify grouping.

3. **SamplingFeature LineString for orbit track, not a DataArray observation.** The Explorer already renders SamplingFeature LineStrings (built for UAS tracks). This is zero new client code. A DataArray inside an observation is semantically valid but adds serialization complexity and requires client-side rendering logic that doesn't exist yet.

4. **One procedure, not two.** Both outputs (point position + orbit track) use the same SGP4 propagation. One procedure describes the method.

5. **Minimal DS1 schema for v1.** Core fields only: `timestamp`, `lat_deg`, `lon_deg`, `alt_km`. Quality metadata (`posErrorM`, `sourceAgeSec`) can be added later.

---

## Resource Model (v1)

```
Orbital Tracking Demo (deployment)               [root]
└── ISS (ZARYA) Tracker (subdeployment, leaf)     [deployed system]
      platform@link → ISS Tracker System
```

| Resource | Type | Value |
|----------|------|-------|
| **Deployment** | Root | `Orbital Tracking Demo` |
| **Subdeployment** | Leaf (deployed system) | `ISS (ZARYA) Tracker` — `platform@link` → System |
| **System** | Occupant | `ISS Tracker` — one system, publishes both position and track |
| **Procedure** | Method | `sgp4-propagation` — source=CelesTrak, model=SGP4 |
| **DataStream** | Under System | `satPositionWGS84` — point positions every 30s |
| **SamplingFeature** | Orbit footprint | `ISS Orbit Track` — LineString geometry, updated every 5 min |

### System metadata

```json
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:system:iss-tracker:v1",
    "name": "ISS Tracker (SGP4 Position Feed)",
    "description": "Publishes near-real-time ISS positions derived from CelesTrak orbital elements via SGP4 propagation."
  }
}
```

### Procedure metadata

```json
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:procedure:sgp4-propagation:v1",
    "name": "SGP4 Orbital Propagation",
    "description": "Converts GP/OMM orbital elements + timestamp into geodetic position (lat, lon, alt) using the SGP4/SDP4 algorithm. Element source: CelesTrak gp.php."
  }
}
```

### DataStream schema (satPositionWGS84)

SWE DataRecord with fields:

| Field | SWE Type | Unit | Description |
|-------|----------|------|-------------|
| `timestamp` | Time | ISO 8601 | Time the position is valid for |
| `lat_deg` | Quantity | deg | WGS84 latitude |
| `lon_deg` | Quantity | deg | WGS84 longitude |
| `alt_km` | Quantity | km | Altitude above WGS84 ellipsoid |

Publishing cadence: every 30 seconds.

### SamplingFeature (ISS Orbit Track)

- **Geometry:** GeoJSON LineString — 180 points spanning 90 minutes (45 min past + 45 min future), sampled every 30 seconds
- **Update cadence:** Every 5 minutes (the track shifts slowly)
- **Rendering:** The Explorer Map page already displays SamplingFeature LineStrings — no frontend changes needed

---

## Deployment Tree Rationale

The deployment-first pattern is preserved per OS4CSAPI convention:

- `GET /deployments` returns the "Orbital Tracking Demo" alongside the existing "Intelligence Collection Operation"
- `GET /deployments/{id}/subdeployments` returns the ISS tracker leaf
- The leaf's `platform@link` wires to the system, which owns the datastream
- Any CSAPI client browsing deployments discovers the satellite tracking capability alongside the ODAS scenario

This demonstrates CSAPI handling **two fundamentally different domains** (ground-based acoustic sensing + orbital mechanics) on the same server, discoverable through the same API, with the same client code.

---

## Publisher Architecture

- **Runtime:** Python script as a systemd service on the Oracle VM (see research doc for rationale)
- **Dependencies:** `sgp4` (Python package, reference SGP4 implementation), `requests`
- **Loop:**
  1. Fetch ISS OMM elements from CelesTrak `gp.php?CATNR=25544&FORMAT=JSON` (cached, refreshed every 6 hours)
  2. Propagate to current time → POST Observation to `satPositionWGS84` datastream
  3. Every 5 minutes: propagate 180 points across 90 minutes → PUT SamplingFeature with updated LineString
  4. Sleep 30 seconds, repeat
- **Target:** `localhost:8181` (OSH SensorHub API, no network round-trip)
- **systemd:** `iss-publisher.service` — `Restart=always`, `RestartSec=5`

---

## What existing clients will see (no code changes)

| Client | What happens |
|--------|-------------|
| **Explorer Map page** | ISS appears as a point feature (from system position). Orbit track appears as a LineString (from SamplingFeature). Map auto-zooms to include it. |
| **Explorer resource browser** | "ISS Tracker" system appears in the systems list. Datastream and observations are browsable. |
| **QGIS plugin (Dr. Simoes)** | Discovers the ISS tracker system and datastream through standard CSAPI endpoints. |
| **Narasimha's notebook** | Auto-discovery loop finds the new system and datastream. Can pull position observations into a DataFrame. |

---

## Future expansions (not in v1)

- Additional satellites (Starlink, GPS constellation, LASP missions)
- "LEO Objects" / "GEO Objects" grouping subdeployments
- Quality metadata fields (`posErrorM`, `sourceAgeSec`, `method`)
- DS2 DataArray orbit track observation (richer than SamplingFeature, for clients that support it)
- Client-side `satellite.js` interpolation for smooth 1-second visual updates (Option C from research doc)
