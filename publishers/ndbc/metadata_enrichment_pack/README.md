# NDBC Buoy Metadata Enrichment Pack

This pack is a metadata-focused enrichment set for `publishers/ndbc/bootstrap_ndbc.py`
in `OSHConnect-Python`.

It is designed to upgrade the existing buoy bootstrap from a solid functional baseline
to a richer, more explorable CSAPI representation with:

- official NOAA/NDBC documentation links
- procedure provenance and usage notes
- richer per-station SensorML metadata
- station page / realtime / historical / BuoyCAM links
- optional enriched `stations.json` fields
- representative buoy asset support
- a worked station example (42002)

## Scope

This pack focuses on metadata and resource-description quality, not parser logic.
It does **not** change the realtime text parsing or observation publishing flow.

## Why this pack exists

The current buoy bootstrap already has a good structure:
- one observing procedure
- one system per buoy
- one datastream per buoy
- a deployment tree
- a marine-oriented SWE DataRecord

But official NDBC resources expose much richer metadata than the current bootstrap carries:
station pages, realtime/historical pages, measurement definitions, status pages,
and optional BuoyCAM image links.
