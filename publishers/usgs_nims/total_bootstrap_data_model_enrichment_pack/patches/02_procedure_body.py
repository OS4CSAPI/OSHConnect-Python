# Enriched procedure body candidate

PROCEDURE_BODY = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "USGS NIMS Station Imagery v1",
        "description": (
            "Publishes image-reference observations from the USGS National Imagery Management "
            "System (NIMS). The current publisher model reuses existing USGS water monitoring "
            "station systems and attaches one selected imagery datastream per curated camera as "
            "a Pattern A companion datastream. Runtime polls NIMS listFiles, derives image time, "
            "constructs stable S3-hosted URLs for multiple image resolutions, and publishes URLs "
            "and metadata instead of binary image payloads."
        ),
        "keywords": [
            "USGS",
            "NIMS",
            "station imagery",
            "camera discovery",
            "listFiles",
            "image reference",
            "timelapse",
            "shared system",
            "Pattern A"
        ],
        "documentation": [
            {"title": "NIMS v0 Camera Discovery", "href": USGS_NIMS_CAMERAS, "rel": "documentation"},
            {"title": "NIMS v0 Image Listing", "href": USGS_NIMS_LIST_FILES, "rel": "documentation"},
            {"title": "NIMS v0 Swagger Docs", "href": USGS_NIMS_DOCS, "rel": "describedby"},
            {"title": "NIMS Image Bucket (S3)", "href": NIMS_S3_BASE, "rel": "alternate"},
            {"title": "USGS API Registration", "href": USGS_API_REGISTRATION, "rel": "related"},
            {"title": "USGS Water Data Home", "href": USGS_WATER_HOME, "rel": "about"}
        ],
        "contacts": [
            {
                "role": "operator",
                "organizationName": "U.S. Geological Survey",
                "website": USGS_WATER_HOME
            },
            {
                "role": "publisher",
                "organizationName": "OS4CSAPI",
                "website": "https://github.com/OS4CSAPI/OSHConnect-Python"
            }
        ],
        "lineage": {
            "source": "U.S. Geological Survey / National Imagery Management System (NIMS)",
            "upstream": (
                "Camera identity and directory metadata come from NIMS cameras responses. "
                "Newest image filenames come from listFiles. Resolution-specific URLs are "
                "constructed from the returned directory paths and filenames."
            ),
            "normalization": (
                "The current runtime uses listFiles string-array mode, parses image time from the "
                "filename pattern, and publishes imageUrl, thumbUrl, smallUrl, filename, mediaType, "
                "and optional timeLapseUrl in the observation result body."
            )
        },
        "usageConstraints": {
            "apiKeyNote": (
                "A USGS API key is recommended for higher request ceilings. Register at "
                "https://api.usgs.gov."
            ),
            "nimsVersionNote": (
                "NIMS v0 is the active verified endpoint as of 2026-03-11. The package keeps v0 URLs "
                "and does not assume a v1 migration path is live yet."
            ),
            "sharedSystemNote": (
                "This publisher uses Pattern A and reuses existing USGS water station systems. "
                "It does not create NIMS-specific systems."
            ),
            "selectionNote": (
                "The current curated model selects one camera per station system even though some "
                "NIMS sites now expose multiple live cameras."
            ),
            "rawItemNote": (
                "NIMS listFiles also supports rawItem=true responses with timestamp and file-size "
                "fields. The current runtime does not yet use that richer mode."
            ),
            "imageryNote": (
                "NIMS cameras may be daylight-only or 24x7. Refresh intervals vary by camera. "
                "Images may be stale during darkness, outages, or reduced capture windows."
            )
        },
        "validTime": [VALID_TIME_START, ".."]
    }
}
