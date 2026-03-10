#!/usr/bin/env python3
"""
image_cache.py — Immutable image cache for BuoyCAM imagery.

Saves fetched images to a date-partitioned directory structure and returns
the public URL for the cached file. Designed for use with a Caddy file_server
route on the same VM.

Directory layout:
  /var/www/buoycam/<stationId>/<YYYY>/<MM>/<DD>/<YYYYMMDD>T<HHMMSS>Z.jpg

Public URL:
  https://os4csapi-osh.duckdns.org/buoycam/<stationId>/<YYYY>/<MM>/<DD>/<YYYYMMDD>T<HHMMSS>Z.jpg
"""

import os
from datetime import datetime, timezone


# Default paths — overrideable via environment
CACHE_ROOT = os.environ.get("BUOYCAM_CACHE_ROOT", "/var/www/buoycam")
CACHE_BASE_URL = os.environ.get(
    "BUOYCAM_CACHE_BASE_URL",
    "https://os4csapi-osh.duckdns.org/buoycam",
)


def immutable_path(station_id: str, fetch_time: datetime) -> str:
    """Build the local filesystem path for a cached image.

    Returns e.g. /var/www/buoycam/46025/2026/03/10/20260310T181500Z.jpg
    """
    ts = fetch_time.strftime("%Y%m%dT%H%M%SZ")
    ymd = fetch_time.strftime("%Y/%m/%d")
    return os.path.join(CACHE_ROOT, station_id, ymd, f"{ts}.jpg")


def immutable_url(station_id: str, fetch_time: datetime) -> str:
    """Build the public URL for a cached image.

    Returns e.g. https://os4csapi-osh.duckdns.org/buoycam/46025/2026/03/10/20260310T181500Z.jpg
    """
    ts = fetch_time.strftime("%Y%m%dT%H%M%SZ")
    ymd = fetch_time.strftime("%Y/%m/%d")
    return f"{CACHE_BASE_URL}/{station_id}/{ymd}/{ts}.jpg"


def save_image(station_id: str, fetch_time: datetime, image_bytes: bytes) -> str:
    """Write image bytes to the immutable cache path.

    Creates parent directories as needed. Returns the local file path.
    """
    path = immutable_path(station_id, fetch_time)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path
