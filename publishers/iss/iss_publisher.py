#!/usr/bin/env python3
"""
iss_publisher.py — ISS position publisher using the shared PublisherBase.

Migrated from csapi-explorer/scripts/iss_publisher_v3.py to use the common
publisher framework. Publishes position fixes from CelesTrak TLE + SGP4.

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)
    POS_SYSTEM_UID     Position system URN        (default: urn:os4csapi:system:iss-position-publisher:v1)
    POS_DS_NAME        Position datastream name   (default: ISS Position (SGP4))
    NORAD_ID           NORAD catalog number       (default: 25544)

Usage:
    python -m publishers.iss.iss_publisher                   # run forever (30s cadence)
    python -m publishers.iss.iss_publisher --dry-run         # print only
    python -m publishers.iss.iss_publisher --once            # single observation
    python -m publishers.iss.iss_publisher --interval 10     # 10s cadence
    python -m publishers.iss.iss_publisher --tle-refresh 7200
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.request import Request, urlopen

try:
    from sgp4.api import Satrec, WGS72
except ImportError:
    print("ERROR: sgp4 package not found. Install it with: pip install sgp4")
    sys.exit(1)

# Add parent dir to path so `publishers.base` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.base import PublisherBase


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════

NORAD_ID   = os.environ.get("NORAD_ID", "25544")
ASSET_NAME = os.environ.get("ASSET_NAME", "ISS (ZARYA)")
CELESTRAK_URL = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={NORAD_ID}&FORMAT=JSON"


# ═══════════════════════════════════════════════════════════════════════════
#  CelesTrak TLE + SGP4 (unchanged from v3)
# ═══════════════════════════════════════════════════════════════════════════

_cached_satrec: Satrec | None = None
_tle_fetched_at: float = 0.0
_tle_epoch_str: str = ""
_tle_epoch_dt: datetime | None = None
_tle_refresh_interval: float = 3600.0


def fetch_tle_from_celestrak() -> Satrec:
    global _cached_satrec, _tle_fetched_at, _tle_epoch_str, _tle_epoch_dt

    req = Request(CELESTRAK_URL, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    if isinstance(data, list) and len(data) > 0:
        omm = data[0]
    else:
        raise RuntimeError(f"Unexpected CelesTrak response: {str(data)[:200]}")

    sat = Satrec()
    sat.sgp4init(
        WGS72, 'i',
        int(omm.get("NORAD_CAT_ID", NORAD_ID)),
        _epoch_to_jdsatepoch(omm["EPOCH"]),
        float(omm.get("BSTAR", 0.0)),
        float(omm.get("MEAN_MOTION_DOT", 0.0)) / (2.0 * math.pi / 1440.0**2),
        float(omm.get("MEAN_MOTION_DDOT", 0.0)),
        float(omm["ECCENTRICITY"]),
        math.radians(float(omm["ARG_OF_PERICENTER"])),
        math.radians(float(omm["INCLINATION"])),
        math.radians(float(omm["MEAN_ANOMALY"])),
        float(omm["MEAN_MOTION"]) * 2.0 * math.pi / 1440.0,
        math.radians(float(omm["RA_OF_ASC_NODE"])),
    )

    _cached_satrec = sat
    _tle_fetched_at = time.time()
    _tle_epoch_str = omm.get("EPOCH", "unknown")
    try:
        _tle_epoch_dt = datetime.strptime(
            _tle_epoch_str, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        _tle_epoch_dt = None
    return sat


def _epoch_to_jdsatepoch(epoch_str: str) -> float:
    dt = datetime.strptime(epoch_str, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)
    jd, fr = _datetime_to_jd(dt)
    return (jd + fr) - 2433281.5


def get_satrec() -> Satrec:
    global _cached_satrec, _tle_fetched_at
    if _cached_satrec is None or (time.time() - _tle_fetched_at) > _tle_refresh_interval:
        fetch_tle_from_celestrak()
    return _cached_satrec


def propagate_to_geodetic(sat: Satrec, dt: datetime) -> tuple[float, float, float, float]:
    jd, fr = _datetime_to_jd(dt)
    e, r, v = sat.sgp4(jd, fr)
    if e != 0:
        raise RuntimeError(f"SGP4 propagation error code {e}")
    x, y, z = r
    vx, vy, vz = v
    lat, lon, alt = eci_to_geodetic(x, y, z, dt)
    velocity_km_s = math.sqrt(vx**2 + vy**2 + vz**2)
    return lat, lon, alt, velocity_km_s


def _datetime_to_jd(dt: datetime) -> tuple[float, float]:
    y, m = dt.year, dt.month
    d = dt.day
    if m <= 2:
        y -= 1
        m += 12
    A = y // 100
    B = 2 - A + A // 4
    jd_day = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5
    fr = (dt.hour + dt.minute / 60.0 + dt.second / 3600.0 +
          dt.microsecond / 3_600_000_000.0) / 24.0
    return jd_day, fr


def eci_to_geodetic(x_km, y_km, z_km, dt):
    a_e = 6378.135
    f = 1.0 / 298.26
    gmst = _gmst_rad(dt)
    cos_g, sin_g = math.cos(gmst), math.sin(gmst)
    x_ecef = x_km * cos_g + y_km * sin_g
    y_ecef = -x_km * sin_g + y_km * cos_g
    z_ecef = z_km
    lon = math.atan2(y_ecef, x_ecef)
    r_xy = math.sqrt(x_ecef**2 + y_ecef**2)
    e2 = 2 * f - f**2
    lat = math.atan2(z_ecef, r_xy)
    for _ in range(10):
        sin_lat = math.sin(lat)
        N = a_e / math.sqrt(1 - e2 * sin_lat**2)
        lat_new = math.atan2(z_ecef + e2 * N * sin_lat, r_xy)
        if abs(lat_new - lat) < 1e-12:
            break
        lat = lat_new
    sin_lat = math.sin(lat)
    N = a_e / math.sqrt(1 - e2 * sin_lat**2)
    alt = (r_xy / math.cos(lat) - N
           if abs(math.cos(lat)) > 1e-10
           else abs(z_ecef) - N * (1 - e2))
    return math.degrees(lat), math.degrees(lon), alt


def _gmst_rad(dt):
    jd, fr = _datetime_to_jd(dt)
    T = (jd + fr - 2451545.0) / 36525.0
    gmst_sec = (67310.54841 +
                (876600.0 * 3600 + 8640184.812866) * T +
                0.093104 * T**2 - 6.2e-6 * T**3)
    gmst_rad = (gmst_sec % 86400) / 86400.0 * 2 * math.pi
    if gmst_rad < 0:
        gmst_rad += 2 * math.pi
    return gmst_rad


def estimate_position_error_m(tle_age_sec: float) -> float:
    age_days = abs(tle_age_sec) / 86400.0
    return round((1.0 + 1.5 * age_days) * 1000.0, 1)


# ═══════════════════════════════════════════════════════════════════════════
#  ISS Publisher (extends PublisherBase)
# ═══════════════════════════════════════════════════════════════════════════

class ISSPublisher(PublisherBase):
    name = "ISS Satellite Publisher"
    system_uid = os.environ.get("POS_SYSTEM_UID",
                                "urn:os4csapi:system:iss-position-publisher:v1")
    ds_name = os.environ.get("POS_DS_NAME", "ISS Position (SGP4)")

    def __init__(self):
        # REST-only mode: bypass OSHConnect SDK when OSH_BASE_URL is set
        self._rest_mode = bool(os.environ.get("OSH_BASE_URL"))
        if self._rest_mode:
            import base64
            self.osh_address = os.environ.get("OSH_ADDRESS", "")
            self.osh_user = os.environ.get("OSH_USER", "")
            self.osh_pass = os.environ.get("OSH_PASS", "")
            self._base_url = os.environ["OSH_BASE_URL"]
            self._is_go_server = "csapi-go" in self._base_url
            self._auth = "Basic " + base64.b64encode(
                f"{self.osh_user}:{self.osh_pass}".encode()).decode()
            self._ds_id: str | None = None
            self.stats = {"published": 0, "errors": 0, "reconnects": 0}
        else:
            super().__init__()
            self._is_go_server = False

    def configure_cli(self, parser: argparse.ArgumentParser):
        parser.add_argument("--tle-refresh", type=float, default=3600.0,
                            help="Seconds between TLE refreshes (default: 3600)")
        parser.set_defaults(interval=30.0)  # ISS default is 30s, not 60s

    def on_startup(self, args):
        global _tle_refresh_interval
        if hasattr(args, 'tle_refresh'):
            _tle_refresh_interval = args.tle_refresh
        print("  Fetching TLE from CelesTrak...")
        try:
            fetch_tle_from_celestrak()
            print(f"  TLE epoch: {_tle_epoch_str}")
        except Exception as e:
            print(f"  FATAL: Could not fetch TLE: {e}")
            sys.exit(1)

    def connect(self):
        """Connect to server. Uses REST mode when OSH_BASE_URL is set, SDK otherwise."""
        if self._rest_mode:
            from publishers.bootstrap_helpers import api_get, find_by_uid
            sys_id = find_by_uid(self._base_url, self._auth, "systems", self.system_uid)
            if not sys_id:
                raise RuntimeError(f"System '{self.system_uid}' not found on server")
            ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
            if ds_list:
                for item in ds_list.get("items", []):
                    if item.get("outputName") == "issPosition":
                        self._ds_id = item.get("id")
                        break
            if not self._ds_id:
                raise RuntimeError(f"Datastream 'issPosition' not found under system {sys_id}")
            print(f"  Connected (REST): sys={sys_id} ds={self._ds_id}")
        else:
            return super().connect()

    def publish_obs(self, obs: dict) -> bool:
        """POST observation. Uses REST when in REST mode, SDK otherwise."""
        if self._rest_mode:
            import ssl
            url = f"{self._base_url}/datastreams/{self._ds_id}/observations"

            # Go server: coerce numeric timestamp to string
            if self._is_go_server:
                r = obs.get("result", {})
                if "timestamp" in r and not isinstance(r["timestamp"], str):
                    r["timestamp"] = str(r["timestamp"])

            body = json.dumps(obs).encode()
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = Request(url, data=body, method="POST", headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": self._auth,
            })
            try:
                with urlopen(req, timeout=30, context=ctx) as resp:
                    if resp.status not in (200, 201, 204):
                        raise RuntimeError(f"HTTP {resp.status}")
                self.stats["published"] += 1
                return True
            except Exception as e:
                self.stats["errors"] += 1
                raise
        else:
            return super().publish_obs(obs)

    def fetch(self) -> Any:
        sat = get_satrec()
        now = datetime.now(timezone.utc)
        lat, lon, alt_km, vel = propagate_to_geodetic(sat, now)
        return {"lat": lat, "lon": lon, "alt_km": alt_km, "vel": vel, "now": now}

    def build_obs(self, data: Any) -> dict:
        now = data["now"]
        iso = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

        tle_age_sec = 0.0
        source_epoch_iso = _tle_epoch_str
        if _tle_epoch_dt is not None:
            tle_age_sec = (now - _tle_epoch_dt).total_seconds()
            source_epoch_iso = _tle_epoch_dt.strftime("%Y-%m-%dT%H:%M:%S.") + \
                f"{_tle_epoch_dt.microsecond // 1000:03d}Z"

        return {
            "phenomenonTime": iso,
            "resultTime": iso,
            "result": {
                "timestamp": now.timestamp(),
                "lat_deg": round(data["lat"], 6),
                "lon_deg": round(data["lon"], 6),
                "alt_km": round(data["alt_km"], 3),
                "velocity_km_s": round(data["vel"], 3),
                "noradId": int(NORAD_ID),
                "assetName": ASSET_NAME,
                "sourceEpoch": source_epoch_iso,
                "sourceAgeSec": round(tle_age_sec, 1),
                "posErrorM": estimate_position_error_m(tle_age_sec),
                "method": "SGP4",
            },
        }


if __name__ == "__main__":
    ISSPublisher.cli()
