#!/usr/bin/env python3
"""
ndbc_publisher.py — NOAA NDBC buoy observation publisher for CSAPI/OSH.

Fetches the latest observation for each configured buoy from NDBC realtime2 text
feeds, parses fixed-width columns, and publishes as CSAPI observations.

Station list is read from stations.json (same directory).

NDBC realtime2 format:
  - URL: https://www.ndbc.noaa.gov/data/realtime2/{stationId}.txt
  - Two header lines (# prefixed), then data lines (newest first)
  - Fields: YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
  - Units already SI: m/s, m, s, degT, hPa, degC, nmi
  - Missing values: MM

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)

Usage:
    python -m publishers.ndbc.ndbc_publisher                     # run forever (60min cadence)
    python -m publishers.ndbc.ndbc_publisher --dry-run           # print only
    python -m publishers.ndbc.ndbc_publisher --once              # single cycle
    python -m publishers.ndbc.ndbc_publisher --interval 300      # 5min cadence
    python -m publishers.ndbc.ndbc_publisher --stations 44025,41009  # subset

Requires: Python 3.12+
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import api_get, find_by_uid


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════

NDBC_BASE_URL = "https://www.ndbc.noaa.gov/data/realtime2"
DS_OUTPUT_NAME = "ndbcBuoyObs"

# Column indices in NDBC realtime2 data lines (after splitting on whitespace)
# #YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
#  0   1  2  3  4   5    6   7   8    9  10  11  12   13   14   15  16  17   18
COL_YY = 0; COL_MM = 1; COL_DD = 2; COL_HH = 3; COL_MN = 4
COL_WDIR = 5; COL_WSPD = 6; COL_GST = 7
COL_WVHT = 8; COL_DPD = 9; COL_APD = 10; COL_MWD = 11
COL_PRES = 12; COL_ATMP = 13; COL_WTMP = 14; COL_DEWP = 15
COL_VIS = 16; COL_PTDY = 17; COL_TIDE = 18


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["ndbc_buoys"]


# ═══════════════════════════════════════════════════════════════════════════
#  NDBC data parsing
# ═══════════════════════════════════════════════════════════════════════════

def _parse_val(raw: str) -> float | str:
    """Parse a single NDBC value. Returns float or 'NaN' for missing (MM)."""
    if raw == "MM" or raw == "":
        return "NaN"
    try:
        return float(raw)
    except (ValueError, TypeError):
        return "NaN"


def fetch_latest_observation(station_id: str, station_meta: dict) -> dict | None:
    """Fetch and parse the latest observation for a buoy from NDBC realtime2.
    Returns normalised dict or None on failure."""
    url = f"{NDBC_BASE_URL}/{station_id}.txt"
    req = Request(url, headers={
        "User-Agent": "os4csapi-publisher/1.0 (github.com/OS4CSAPI)",
    })

    try:
        with urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except (HTTPError, Exception) as e:
        print(f"    [WARN] NDBC fetch failed for {station_id}: {e}")
        return None

    # Parse: skip header lines (start with #), take first data line
    data_line = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        data_line = stripped
        break

    if not data_line:
        print(f"    [WARN] No data lines in response for {station_id}")
        return None

    cols = data_line.split()
    if len(cols) < 16:
        print(f"    [WARN] Unexpected column count ({len(cols)}) for {station_id}")
        return None

    # Parse timestamp from YY MM DD hh mm
    try:
        yr = int(cols[COL_YY])
        mo = int(cols[COL_MM])
        dy = int(cols[COL_DD])
        hr = int(cols[COL_HH])
        mn = int(cols[COL_MN])
        obs_dt = datetime(yr, mo, dy, hr, mn, tzinfo=timezone.utc)
        ts_epoch = obs_dt.timestamp()
        ts_iso = obs_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, IndexError) as e:
        print(f"    [WARN] Cannot parse timestamp for {station_id}: {e}")
        return None

    # Build result dict — read all standard columns
    result = {
        "timestamp": ts_epoch,
        "phenomenonTime": ts_iso,
        "stationId": station_id,
        "lat_deg": station_meta.get("lat", "NaN"),
        "lon_deg": station_meta.get("lon", "NaN"),
        "wind_direction_deg": _parse_val(cols[COL_WDIR]),
        "wind_speed_ms": _parse_val(cols[COL_WSPD]),
        "wind_gust_ms": _parse_val(cols[COL_GST]),
        "wave_height_m": _parse_val(cols[COL_WVHT]),
        "dominant_wave_period_s": _parse_val(cols[COL_DPD]),
        "avg_wave_period_s": _parse_val(cols[COL_APD]),
        "mean_wave_direction_deg": _parse_val(cols[COL_MWD]) if len(cols) > COL_MWD else "NaN",
        "pressure_hpa": _parse_val(cols[COL_PRES]) if len(cols) > COL_PRES else "NaN",
        "air_temp_c": _parse_val(cols[COL_ATMP]) if len(cols) > COL_ATMP else "NaN",
        "water_temp_c": _parse_val(cols[COL_WTMP]) if len(cols) > COL_WTMP else "NaN",
        "dewpoint_c": _parse_val(cols[COL_DEWP]) if len(cols) > COL_DEWP else "NaN",
        "visibility_nmi": _parse_val(cols[COL_VIS]) if len(cols) > COL_VIS else "NaN",
        "pressure_tendency_hpa": _parse_val(cols[COL_PTDY]) if len(cols) > COL_PTDY else "NaN",
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Multi-station publisher
# ═══════════════════════════════════════════════════════════════════════════

class NDBCPublisher:
    """Multi-station NDBC buoy publisher.

    Connects to one system+datastream per buoy, publishes observations
    for all buoys in each cycle. Uses direct REST API calls.
    """

    name = "NDBC Buoy Observation Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        self.stations = _load_stations()
        if station_filter:
            filt = set(s.strip() for s in station_filter)
            self.stations = [s for s in self.stations if s["id"] in filt]

        self.osh_address = os.environ.get("OSH_ADDRESS", "")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "")
        self.osh_pass = os.environ.get("OSH_PASS", "")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit(
                "ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.\n"
                "  Copy publishers/.env.example → .env and set your server details."
            )

        # station_id → datastream server ID (string)
        self._ds_ids: dict[str, str] = {}
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

        # Track last observation timestamp per station to avoid duplicates
        self._last_obs_ts: dict[str, float] = {}

        # REST config
        import base64
        self._base_url = os.environ.get(
            "OSH_BASE_URL",
            f"https://{self.osh_address}/{self.osh_root}/api",
        )
        self._is_go_server = "csapi-go" in self._base_url
        self._auth = "Basic " + base64.b64encode(
            f"{self.osh_user}:{self.osh_pass}".encode()).decode()

    def _system_uid(self, station_id: str) -> str:
        return f"urn:os4csapi:system:ndbc:{station_id}:v1"

    def connect(self):
        """Resolve system and datastream IDs for each station via REST API."""
        for st in self.stations:
            uid = self._system_uid(st["id"])
            sys_id = find_by_uid(self._base_url, self._auth, "systems", uid)
            if not sys_id:
                print(f"  [WARN] System '{uid}' not found — skipping {st['id']}")
                continue

            # Find datastream by output name
            ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
            ds_id = None
            if ds_list:
                for item in ds_list.get("items", []):
                    if item.get("outputName") == DS_OUTPUT_NAME:
                        ds_id = item.get("id")
                        break

            if not ds_id:
                print(f"  [WARN] Datastream '{DS_OUTPUT_NAME}' not found for {st['id']} — skipping")
                continue

            self._ds_ids[st["id"]] = ds_id
            print(f"  Connected: {st['id']} → sys={sys_id} ds={ds_id}")

        print(f"  Ready: {len(self._ds_ids)}/{len(self.stations)} buoys connected")

    def connect_with_retry(self, max_attempts=10, base_delay=5.0, max_delay=120.0):
        for attempt in range(1, max_attempts + 1):
            try:
                return self.connect()
            except Exception as e:
                if attempt == max_attempts:
                    raise
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                jitter = delay * 0.2 * (random.random() - 0.5)
                wait = delay + jitter
                print(f"  [WARN] Attempt {attempt}/{max_attempts} failed: {e}")
                print(f"         Retrying in {wait:.1f}s...")
                time.sleep(wait)

    def _post_observation(self, ds_id: str, obs: dict):
        """POST an observation to the server using direct REST (allows NaN serialization)."""
        import ssl
        from urllib.request import Request as _Req, urlopen as _urlopen

        # Go server workarounds
        if self._is_go_server:
            r = obs.get("result", {})
            for key, val in list(r.items()):
                if val == "NaN":
                    r[key] = 0.0
            # Coerce numeric timestamp to string
            if "timestamp" in r and not isinstance(r["timestamp"], str):
                r["timestamp"] = str(r["timestamp"])

        url = f"{self._base_url}/datastreams/{ds_id}/observations"
        body = json.dumps(obs).encode()

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = _Req(url, data=body, method="POST", headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._auth,
            "Host": self.osh_address,
        })

        try:
            with _urlopen(req, timeout=30, context=ctx) as resp:
                if resp.status not in (200, 201, 204):
                    raise RuntimeError(f"HTTP {resp.status} POST {url}")
        except HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"HTTP {e.code} POST {url}: {body_text}") from e

    def publish_cycle(self, dry_run: bool = False) -> int:
        """Fetch + publish observations for all buoys. Returns count published."""
        published = 0
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")

        for st in self.stations:
            station_id = st["id"]
            ds_id = self._ds_ids.get(station_id)
            if ds_id is None and not dry_run:
                continue

            # Fetch from NDBC
            obs_data = fetch_latest_observation(station_id, st)
            if obs_data is None:
                self.stats["errors"] += 1
                continue

            # Skip if observation timestamp hasn't changed
            obs_ts = obs_data.get("timestamp", 0)
            if obs_ts and obs_ts == self._last_obs_ts.get(station_id):
                self.stats["skipped"] += 1
                print(f"  [{ts}] {station_id}: unchanged, skipping")
                continue

            # Build observation envelope
            phenomenon_time = obs_data.pop("phenomenonTime")
            obs_data.pop("timestamp", None)
            obs = {
                "phenomenonTime": phenomenon_time,
                "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": obs_data,
            }

            if dry_run:
                wind = obs_data.get("wind_speed_ms", "?")
                wave = obs_data.get("wave_height_m", "?")
                wt = obs_data.get("water_temp_c", "?")
                at = obs_data.get("air_temp_c", "?")
                print(f"  [{ts}] {station_id}: [DRY] wind={wind}m/s wave={wave}m air={at}°C water={wt}°C")
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    self._last_obs_ts[station_id] = obs_ts

                    wind = obs_data.get("wind_speed_ms", "?")
                    wave = obs_data.get("wave_height_m", "?")
                    wt = obs_data.get("water_temp_c", "?")
                    at = obs_data.get("air_temp_c", "?")
                    print(f"  [{ts}] {station_id}: OK  wind={wind}m/s wave={wave}m air={at}°C water={wt}°C")
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  [{ts}] {station_id}: ERR {e}")

        return published

    def run(self, *, interval: float = 3600.0, dry_run: bool = False, once: bool = False):
        """Main publisher loop."""
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    https://{self.osh_address}:{self.osh_port}/{self.osh_root}/api")
        print(f"  Buoys:     {len(self.stations)} ({', '.join(s['id'] for s in self.stations)})")
        print(f"  Interval:  {interval}s")
        print(f"  Dry run:   {dry_run}")
        print()

        if not dry_run:
            print("  Connecting to OSH server...")
            self.connect_with_retry()

        tick = 0
        consecutive_errors = 0
        start_time = time.time()
        print()

        try:
            while True:
                tick += 1
                print(f"  ── Cycle #{tick} ──")

                try:
                    n = self.publish_cycle(dry_run=dry_run)
                    if n > 0:
                        consecutive_errors = 0
                    else:
                        consecutive_errors += 1
                except Exception as e:
                    print(f"  [ERR] Cycle failed: {e}")
                    consecutive_errors += 1
                    self.stats["errors"] += 1

                # Reconnect on sustained failures
                if consecutive_errors >= 5 and not dry_run:
                    print("  [WARN] Reconnecting...")
                    try:
                        self.connect_with_retry()
                        self.stats["reconnects"] += 1
                        consecutive_errors = 0
                    except Exception as re_err:
                        print(f"  [ERR] Reconnect failed: {re_err}")

                if once:
                    break

                next_tick = start_time + tick * interval
                sleep_time = next_tick - time.time()
                if sleep_time > 0:
                    print(f"  Sleeping {sleep_time:.0f}s until next cycle...")
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\n  Ctrl+C — stopping publisher.")

        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print(f"  Summary ({elapsed:.0f}s elapsed)")
        print(f"  Published:  {self.stats['published']}")
        print(f"  Skipped:    {self.stats['skipped']} (unchanged obs)")
        print(f"  Errors:     {self.stats['errors']}")
        print(f"  Reconnects: {self.stats['reconnects']}")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="NDBC buoy observation publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=3600.0,
                        help="Seconds between publish cycles (default: 3600)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    parser.add_argument("--stations", type=str, default=None,
                        help="Comma-separated station IDs to publish (default: all from stations.json)")
    args = parser.parse_args()

    station_filter = args.stations.split(",") if args.stations else None
    publisher = NDBCPublisher(station_filter=station_filter)
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
