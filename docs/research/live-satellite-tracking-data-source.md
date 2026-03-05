# Live Satellite Tracking as a CSAPI Data Source

**Date:** 2026-03-05  
**Status:** Research — refined after weigh-in  
**Revision:** 2 (incorporated CelesTrak format recommendations, drift corrections, architecture refinement)

---

## Prompt

> I would like to see if we could add a live data source that is made available on the internet. Like maybe model a satellite orbiting the earth in near real time? I saw a visualization like this at LASP (Laboratory for Atmospheric and Space Physics) — their lobby display shows current LASP-operated missions on a Leaflet map with NASA Visible Earth tiles and CelesTrak data. Could we do something similar?

---

## Core Concept

A **live external data source → OSH server** pipeline. Real orbital data flows in from CelesTrak, is propagated to current positions via SGP4, and published as standard CSAPI observations — discoverable by any client with zero custom integration.

```
CelesTrak (GP elements via gp.php, refreshed every 6–12 hours)
    → Publisher script (SGP4 propagation, generates position every 30–60s)
        → OSH Server (CSAPI observations)
            → Any CSAPI client discovers and displays it
```

This is how satellite tracking fundamentally works — even professional mission operations centers and LASP's lobby display use this architecture. The orbital elements are real data from the US Space Force 18th Space Defense Squadron catalog. The propagation (SGP4/SDP4) is a standard, well-understood model. The resulting positions are physically accurate to within a few km. This is not synthetic or simulated data — it is a real satellite's real orbit.

---

## Data Source: CelesTrak GP Query + OMM JSON

### Prefer structured formats over raw TLE

CelesTrak provides a standard query endpoint (`gp.php`) with multiple output formats. **Prefer JSON (OMM keywords)** over raw TLE text:

- `gp.php?CATNR=25544&FORMAT=JSON` — ISS by NORAD catalog number, JSON OMM output
- `gp.php?GROUP=stations&FORMAT=JSON` — space station group
- `gp.php?NAME=ISS&FORMAT=JSON` — search by name

JSON/OMM is cleaner to parse, avoids TLE's fixed-width format limitations (e.g., 5-digit catalog number constraint), and is the direction CelesTrak is moving.

Use `FORMAT=TLE` only when needed for legacy compatibility.

### Element freshness

GP elements degrade in accuracy over time. For LEO satellites like the ISS, accuracy can degrade beyond tight acquisition thresholds within 2–3 days depending on orbit and solar activity. For a demo pipeline:

- Re-fetch element sets at least every 6–12 hours
- Cache results and rate-limit responsibly
- CelesTrak provides publicly accessible GP element data; follow their documented query formats and provide attribution

### Propagation

- **satellite.js** (~30KB, MIT) implements SGP4 in JavaScript — takes OMM/TLE + timestamp, returns lat/lon/altitude
- Runs entirely client-side or in Node.js/Python
- Supports both TLE and OMM input formats
- Can compute full orbit ground tracks (past + predicted) in milliseconds
- The ISS completes an orbit every ~92 minutes, so it's always visually interesting

---

## Architecture Options

| Option | Approach | Effort | CSAPI Value |
|--------|----------|--------|-------------|
| **A** | Pure frontend — satellite.js + Leaflet, no server involvement | Low | Visual only, no CSAPI integration |
| **B** | Publish to OSH — publisher computes positions and POSTs as CSAPI observations | Medium | Full CSAPI round-trip: satellite is a discoverable system with datastreams. **Strongest interoperability proof** — existing clients display it with zero code changes |
| **C** | Hybrid — publish snapshots to OSH at 30–60s cadence + satellite.js client-side interpolation for smooth 1-second visual updates | Medium-High | Best visual UX + CSAPI credibility, but requires satellite-specific frontend code |

### Recommendation: Option B (default), Option C (stretch)

**Option B** is the strongest starting point for the project's goals:

- The satellite shows up on the existing Map page, Explorer, QGIS plugin, and Narasimha's notebook with **zero frontend changes**
- This is the whole interoperability point — CSAPI makes the domain irrelevant
- A UAS, a microphone array, and a satellite in Earth orbit are all just systems with datastreams

Option C can be layered on later if smooth visual presentation matters for demos. Start with B.

---

## CSAPI Modeling

| Resource | Value |
|----------|-------|
| **System** | `ISS (ZARYA)` (NORAD 25544) |
| **Procedure** | `sgp4-propagation` — metadata: source=CelesTrak, last element epoch, propagation model |
| **DataStream** | `position` — SWE record with `timestamp`, `lat`, `lon`, `alt_km` |
| **Observation frequency** | Publish every 30–60 seconds |

Could expand later to multiple satellites (Starlink, GPS constellation, LASP missions like CUTE, IMAP).

---

## Alternative "Pure Live Feed" Sources

If a pipeline with no local computation is preferred, some APIs return positions directly:

| Source | What | Notes |
|--------|------|-------|
| Open Notify (`api.open-notify.org/iss-now.json`) | ISS lat/lon | Free, rate-limited, ISS only |
| N2YO API | Satellite positions by NORAD ID | Free API key required |
| ADS-B Exchange / OpenSky | Live aircraft positions | Different domain, same CSAPI architecture |
| PurpleAir / OpenAQ | Live air quality sensor readings | Environmental domain |

For satellites, the GP elements → SGP4 approach is the industry standard and the most robust option. The computation step in the middle is normal for orbital mechanics.

---

## Publisher Implementation (not yet built)

The publisher would be a lightweight script (Python or Cloudflare Worker cron) that:

1. Fetches ISS OMM elements from CelesTrak gp.php (cached, refreshed every 6–12 hours)
2. Propagates to current time using SGP4 (satellite.js or sgp4 Python package)
3. POSTs a CSAPI observation to the OSH server's datastream endpoint
4. Runs on a 30–60 second interval

No implementation yet — this document is research only.
