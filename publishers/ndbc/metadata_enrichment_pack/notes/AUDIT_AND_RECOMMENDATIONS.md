# Audit and Recommendations

## Determination

Yes — the buoy bootstrap is worth a dedicated metadata enrichment pass.

## Current strengths in `bootstrap_ndbc.py`

The existing bootstrap already establishes a sound CSAPI pattern:
- one shared observing procedure for NOAA NDBC buoy observations
- one system per buoy
- one datastream per buoy
- a deployment tree
- a marine SWE `DataRecord`
- realtime ingest from NDBC `realtime2` flat-file feeds

This is a strong baseline. The gap is not architecture; it is metadata richness.

## Why enrichment is justified

Official NDBC resources expose more authoritative metadata than the current bootstrap carries:
- station pages
- realtime station pages
- historical station pages
- measurement descriptions and units
- web data guide
- station status pages
- optional BuoyCAM support

That means the buoy resources can be upgraded from "working demo systems" to
"well-documented operational observing systems".

## Highest-value metadata additions

### Procedure metadata
Add:
- NDBC homepage
- web data guide
- realtime data retrieval documentation
- measurement descriptions and units
- station status page
- contact details
- cadence and quality-control notes

### System metadata
Add:
- station page URL
- realtime page URL
- historical page URL
- direct realtime flat-file URL
- owner / maintainer
- platform type
- payload type
- site elevation
- air-temp / anemometer / barometer heights when known
- sea-temp depth
- water depth
- watch-circle radius
- optional BuoyCAM URL
- representative image/icon reference

### Datastream metadata
Add:
- description
- documentation links
- provenance note
- cadence / QC note
- flat-file source URL pattern

### Deployment metadata
Add:
- deployment-scope explanation
- authoritative NDBC links
- operational-status context

## Implementation note

This pack deliberately keeps metadata curation separate from parsing logic.
That reduces risk and keeps the patch easy to review.
