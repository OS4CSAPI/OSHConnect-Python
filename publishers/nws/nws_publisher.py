#!/usr/bin/env python3
"""
nws_publisher.py — NWS surface weather observation publisher for CSAPI/OSH.

Fetches the latest observation for each configured station from api.weather.gov,
normalises to SI units, and publishes as CSAPI observations.

Station list is read from stations.json (same directory).

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (default: os4csapi-osh.duckdns.org)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (default: os4csapi)
    OSH_PASS           Auth password              (default: ogc134mm)

Usage:
    python -m publishers.nws.nws_publisher                     # run forever (60min cadence)
    python -m publishers.nws.nws_publisher --dry-run           # print only
    python -m publishers.nws.nws_publisher --once              # single cycle
    python -m publishers.nws.nws_publisher --interval 300      # 5min cadence
    python -m publishers.nws.nws_publisher --stations KTUS,KPHX  # subset

Requires: Python 3.12+, oshconnect
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import api_get, api_post, find_by_uid


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════

NWS_USER_AGENT = "os4csapi-publisher/1.0 (github.com/OS4CSAPI)"
NWS_BASE_URL = "https://api.weather.gov"
DS_OUTPUT_NAME = "nwsSurfaceObs"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["nws_stations"]


# ═══════════════════════════════════════════════════════════════════════════
#  NWS API fetch helpers
# ═══════════════════════════════════════════════════════════════════════════

def _safe_val(obj: dict | None) -> float | str:
    """Extract numeric value from NWS quantity object {unitCode, value, qualityControl}.
    Returns string "NaN" for missing values — the SWE JSON parser on the server
    accepts "NaN" for Quantity fields when the value is unavailable."""
    if obj is None:
        return "NaN"
    v = obj.get("value")
    if v is None:
        return "NaN"
    return float(v)


def fetch_latest_observation(station_id: str) -> dict | None:
    """Fetch the latest observation for a station from api.weather.gov.
    Returns normalised dict or None on failure."""
    url = f"{NWS_BASE_URL}/stations/{station_id}/observations/latest"
    req = Request(url, headers={
        "User-Agent": NWS_USER_AGENT,
        "Accept": "application/geo+json",
    })

    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except (HTTPError, Exception) as e:
        print(f"    [WARN] NWS fetch failed for {station_id}: {e}")
        return None

    props = data.get("properties", {})
    geom = data.get("geometry", {})
    coords = geom.get("coordinates", [None, None])

    # Parse timestamp
    raw_ts = props.get("timestamp", "")
    try:
        ts_dt = datetime.fromisoformat(raw_ts)
        ts_epoch = ts_dt.timestamp()
        ts_iso = ts_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        ts_epoch = time.time()
        ts_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "timestamp": ts_epoch,
        "phenomenonTime": ts_iso,
        "stationId": props.get("stationId", station_id),
        "stationName": props.get("stationName", ""),
        "lat_deg": coords[1] if len(coords) > 1 and coords[1] is not None else "NaN",
        "lon_deg": coords[0] if len(coords) > 0 and coords[0] is not None else "NaN",
        "elev_m": _safe_val(props.get("elevation")),
        "temperature_c": _safe_val(props.get("temperature")),
        "dewpoint_c": _safe_val(props.get("dewpoint")),
        "humidity_pct": _safe_val(props.get("relativeHumidity")),
        "wind_speed_kmh": _safe_val(props.get("windSpeed")),
        "wind_direction_deg": _safe_val(props.get("windDirection")),
        "wind_gust_kmh": _safe_val(props.get("windGust")),
        "barometric_pressure_pa": _safe_val(props.get("barometricPressure")),
        "visibility_m": _safe_val(props.get("visibility")),
        "textDescription": props.get("textDescription", ""),
        "rawMessage": props.get("rawMessage", ""),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Multi-station publisher
#
#  Unlike ISS (single system, single datastream), NWS has one system per
#  station. We manage multiple PublisherBase-like connections.
# ═══════════════════════════════════════════════════════════════════════════

class NWSPublisher:
    """Multi-station NWS weather publisher.

    Connects to one system+datastream per station, publishes observations
    for all stations in each cycle. Uses direct REST API calls (not oshconnect)
    to avoid serialization issues with NaN and pydantic timestamp parsing.
    """

    name = "NWS Weather Observation Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        self.stations = _load_stations()
        if station_filter:
            filt = set(s.upper() for s in station_filter)
            self.stations = [s for s in self.stations if s["id"].upper() in filt]

        self.osh_address = os.environ.get("OSH_ADDRESS", "os4csapi-osh.duckdns.org")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "os4csapi")
        self.osh_pass = os.environ.get("OSH_PASS", "ogc134mm")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")

        # station_id → datastream server ID (string)
        self._ds_ids: dict[str, str] = {}
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

        # Track last observation timestamp per station to avoid duplicates
        self._last_obs_ts: dict[str, float] = {}

        # REST config
        import base64
        self._base_url = f"https://{self.osh_address}/{self.osh_root}/api"
        self._auth = "Basic " + base64.b64encode(
            f"{self.osh_user}:{self.osh_pass}".encode()).decode()

    def _system_uid(self, station_id: str) -> str:
        return f"urn:os4csapi:system:nws:{station_id.lower()}:v1"

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

        print(f"  Ready: {len(self._ds_ids)}/{len(self.stations)} stations connected")

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
        """Fetch + publish observations for all stations. Returns count published."""
        published = 0
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")

        for st in self.stations:
            station_id = st["id"]
            ds_id = self._ds_ids.get(station_id)
            if ds_id is None and not dry_run:
                continue

            # Fetch from NWS
            obs_data = fetch_latest_observation(station_id)
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
            # The SWE Time field 'timestamp' maps to phenomenonTime in the O&M
            # envelope and must NOT appear in the result body.
            phenomenon_time = obs_data.pop("phenomenonTime")
            obs_data.pop("timestamp", None)
            obs = {
                "phenomenonTime": phenomenon_time,
                "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": obs_data,
            }

            if dry_run:
                temp = obs_data.get("temperature_c", "?")
                wind = obs_data.get("wind_speed_kmh", "?")
                desc = obs_data.get("textDescription", "")
                print(f"  [{ts}] {station_id}: [DRY] temp={temp}°C wind={wind}km/h — {desc}")
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    self._last_obs_ts[station_id] = obs_ts

                    temp = obs_data.get("temperature_c", "?")
                    wind = obs_data.get("wind_speed_kmh", "?")
                    desc = obs_data.get("textDescription", "")
                    print(f"  [{ts}] {station_id}: OK  temp={temp}°C wind={wind}km/h — {desc}")
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
        print(f"  Stations:  {len(self.stations)} ({', '.join(s['id'] for s in self.stations)})")
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
        description="NWS surface weather observation publisher for CSAPI/OSH")
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
    publisher = NWSPublisher(station_filter=station_filter)
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
