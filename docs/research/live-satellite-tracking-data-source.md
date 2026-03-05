# Live Satellite Tracking as a CSAPI Data Source

**Date:** 2026-03-05  
**Status:** Research / Advisory — no implementation yet

---

## Prompt

> I would like to see if we could add a live data source that is made available on the internet. Like maybe model a satellite orbiting the earth in near real time? I saw a visualization like this at LASP (Laboratory for Atmospheric and Space Physics) — their lobby display shows current LASP-operated missions on a Leaflet map with NASA Visible Earth tiles and Celestrak.org TLE data. Could we do something similar?

---

## Analysis

### Data Source

- **Celestrak** provides free Two-Line Element (TLE) orbital data for thousands of satellites
- TLEs are small text records (~160 bytes each) describing a satellite's orbit — they're updated every few days
- The ISS is the classic choice (well-known, ~90 min orbit, always moving)

### Propagation

- **satellite.js** (~30KB, MIT) implements the SGP4 algorithm in JavaScript — it takes a TLE and a timestamp and returns lat/lon/altitude
- Runs entirely client-side, no server needed — you just call `propagate(satrec, date)` and get a position
- Can compute full orbit ground tracks (past + predicted) in milliseconds

### Three Architecture Options

| Option | Approach | Effort | CSAPI Value |
|--------|----------|--------|-------------|
| **A** | Pure frontend — satellite.js + Leaflet on a new page or the UAS Analytics map | Low | Visual only, no CSAPI integration |
| **B** | Publish to OSH — a small worker/script computes positions and POSTs them as CSAPI observations every N seconds | Medium | Full CSAPI round-trip: the satellite becomes a discoverable system with datastreams |
| **C** | Hybrid — satellite.js for smooth real-time viz, plus periodic snapshots published to OSH | Medium-High | Best demo: smooth visuals + proves CSAPI can ingest orbital data |

### Recommendation

**Option B** is the most compelling for the project's goals. You'd:

1. Create a "satellite" system on the OSH server (e.g., "ISS (ZARYA)")
2. Add a datastream for position observations (lon, lat, alt)
3. Run a lightweight publisher (Cloudflare Worker cron, or a Python script) that fetches the ISS TLE from Celestrak, propagates with SGP4, and POSTs a CSAPI observation every 30–60 seconds
4. The Explorer's existing Map page would automatically discover and display it — no frontend changes needed

This would demonstrate CSAPI handling a fundamentally different domain (space assets) with zero code changes to the client, which is a powerful interoperability proof point.

### Considerations

- Celestrak TLEs are free for non-commercial/educational use
- TLEs drift after ~3–5 days, so the publisher should re-fetch periodically
- The ISS completes an orbit every ~92 minutes, so it's always visually interesting
- Could expand later to multiple satellites (Starlink, GPS constellation, LASP missions like CUTE)
