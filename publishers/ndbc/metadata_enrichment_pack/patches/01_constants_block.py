# Drop-in constants and helper URL builders for `bootstrap_ndbc.py`

NDBC_HOME = "https://www.ndbc.noaa.gov/"
NDBC_WEB_DATA_GUIDE = "https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf"
NDBC_RT_DATA_DOC = "https://www.ndbc.noaa.gov/faq/rt_data_access.shtml"
NDBC_MEAS_DESC = "https://www.ndbc.noaa.gov/faq/measdes.shtml"
NDBC_STATUS_REPORT = "https://www.ndbc.noaa.gov/wstat.shtml"
NDBC_STATION_PAGE_BASE = "https://www.ndbc.noaa.gov/station_page.php?station="
NDBC_STATION_REALTIME_BASE = "https://www.ndbc.noaa.gov/station_realtime.php?station="
NDBC_STATION_HISTORY_BASE = "https://www.ndbc.noaa.gov/station_history.php?station="
NDBC_REALTIME_TEXT_BASE = "https://www.ndbc.noaa.gov/data/realtime2"
NDBC_BUOYCAM_FAQ = "https://www.ndbc.noaa.gov/faq/buoycamlinks.shtml"
NDBC_BUOYCAM_BASE = "https://www.ndbc.noaa.gov/buoycam.php?station="
NDBC_NETCDF = "https://dods.ndbc.noaa.gov/"

NDBC_CONTACT_EMAIL = "webmaster.ndbc@noaa.gov"
NDBC_CONTACT_ORG = "National Data Buoy Center"
NDBC_CONTACT_ADDRESS = "Building 3205, Stennis Space Center, MS 39529"

def _station_page_url(station_id: str) -> str:
    return f"{NDBC_STATION_PAGE_BASE}{station_id}"

def _station_realtime_url(station_id: str) -> str:
    return f"{NDBC_STATION_REALTIME_BASE}{station_id}"

def _station_history_url(station_id: str) -> str:
    return f"{NDBC_STATION_HISTORY_BASE}{station_id}"

def _station_realtime_text_url(station_id: str) -> str:
    return f"{NDBC_REALTIME_TEXT_BASE}/{station_id}.txt"

def _station_buoycam_url(station_id: str) -> str:
    return f"{NDBC_BUOYCAM_BASE}{station_id}"
