"""
Bootstrap candidate snippets for publishers/usgs_nims/bootstrap_usgs_nims.py

This file is intentionally not a full drop-in replacement. It is a curated bundle
of the most valuable metadata and provenance upgrades:

- stronger official references
- richer procedure metadata
- richer imagery datastream metadata
- clearer Pattern A shared-system deployment wording
- richer camera-sidecar guidance for cameras.json

The current shared-system architecture is preserved.
"""

# 1. Additional constants and helper URLs

USGS_NIMS_DOCS = "https://api.waterdata.usgs.gov/nims/v0/docs"


def _site_cameras_url(nwis_id: str) -> str:
    return f"{NIMS_API_BASE}cameras?siteId={nwis_id}"


def _list_files_rawitem_url(cam_id: str, limit: int = 5) -> str:
    return f"{NIMS_API_BASE}listFiles?camId={cam_id}&limit={limit}&recent=true&rawItem=true"


# 2. Procedure semantics to preserve
#
# - Pattern A shared-system model
# - one selected camera per station system in the current curated package
# - listFiles string-array runtime with rawItem documented as a future option
# - image-reference observations rather than binary image ingest


# 3. Datastream semantics to preserve
#
# Result fields remain:
# - stationId
# - camId
# - imageUrl
# - thumbUrl
# - smallUrl
# - mediaType
# - filename
# - timeLapseUrl
#
# The timestamp field is still mapped from phenomenonTime and must not appear
# inside the result body.


# 4. Most important model caveat
#
# Live site-based camera discovery now returns multiple cameras for some curated
# NWIS sites. The current publisher model is therefore a selected-camera model,
# not a general many-camera-per-site model.
