# Additional official references and helper URLs for bootstrap_usgs_nims.py

USGS_NIMS_DOCS = "https://api.waterdata.usgs.gov/nims/v0/docs"
USGS_NIMS_SITE_DISCOVERY = "https://api.waterdata.usgs.gov/nims/v0/cameras?siteId="
USGS_NIMS_RAWITEM_NOTE = "https://api.waterdata.usgs.gov/nims/v0/listFiles"


def _site_cameras_url(nwis_id: str) -> str:
    return f"{NIMS_API_BASE}cameras?siteId={nwis_id}"


def _list_files_rawitem_url(cam_id: str, limit: int = 5) -> str:
    return f"{NIMS_API_BASE}listFiles?camId={cam_id}&limit={limit}&recent=true&rawItem=true"
