"""
Bootstrap candidate snippets for publishers/usgs_eq/bootstrap_usgs_eq.py

This file is intentionally not a full drop-in replacement. It is a curated bundle
of the most valuable metadata and provenance upgrades:

- stronger official references
- richer procedure and system metadata
- richer earthquake datastream semantics
- explicit summary-versus-detail source layering
- clearer deployment wording and feed-lifecycle provenance

The current Pattern C feed-adapter architecture is preserved.
"""

# 1. Additional constants and helper URLs
#
# - GeoJSON detail docs
# - feed lifecycle policy
# - event-terms docs
# - FDSN event API
# - helper URL builders for variant, detail, and targeted query links


# 2. Procedure semantics to preserve
#
# - one global feed-adapter procedure
# - summary feed is the default runtime surface
# - detail feed and FDSN query are selective enrichment companions
# - one observation per earthquake feature


# 3. System semantics to preserve
#
# - the system is not a physical seismic station
# - the system geometry is conceptual only
# - event geometry belongs in the observation result


# 4. Datastream semantics to preserve
#
# Current result fields remain:
# - eventId
# - magnitude
# - magType
# - place
# - eventTime
# - updatedTime
# - latitude
# - longitude
# - depth_km
# - status
# - eventType
# - title
# - detailUrl
#
# Important omitted-but-available summary fields worth documenting:
# - url
# - sig
# - alert
# - tsunami
# - net
# - types
# - nst
# - dmin
# - rms
# - gap


# 5. Most important model caveat
#
# The richest official event surface is exposed through detail documents and
# FDSN targeted queries. That does not mean the runtime should poll those
# surfaces for every event. The summary feed remains the correct default.
