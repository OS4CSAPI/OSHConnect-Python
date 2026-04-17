#!/usr/bin/env python3
"""
coops_publisher.py — NOAA CO-OPS coastal observation publisher for CSAPI/OSH.

Fetches the latest water level, tide prediction, and meteorological data for each
configured station from the CO-OPS Data API, and publishes combined observations.

Station list is read from stations.json (same directory).

CO-OPS Data API:
  - Base: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
  - Products fetched per station:
      water_level     → observed water level, sigma, quality flag
      predictions     → predicted tide level
      air_temperature → air temp (°C)        [if sensor available]
      water_temperature → water temp (°C)    [if sensor available]
      wind            → speed/dir/gust (m/s) [if sensor available]
      air_pressure    → barometric (hPa/mb)  [if sensor available]
  - All requests use: datum=MLLW, units=metric, time_zone=gmt, format=json

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)

Usage:
    python -m publishers.coops.coops_publisher                         # run forever (6min cadence)
    python -m publishers.coops.coops_publisher --dry-run               # print only
    python -m publishers.coops.coops_publisher --once                  # single cycle
    python -m publishers.coops.coops_publisher --interval 600          # 10min cadence
    python -m publishers.coops.coops_publisher --stations 8518750,9414290  # subset

Requires: Python 3.10+
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

COOPS_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
DS_OUTPUT_NAME = "coopsCoastalObs"

# Common query params for all CO-OPS API requests
COMMON_PARAMS = "date=latest&units=metric&time_zone=gmt&application=os4csapi&format=json"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["coops_stations"]


# ═══════════════════════════════════════════════════════════════════════════
#  CO-OPS data fetching
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_product(station_id: str, product: str, extra_params: str = "") -> dict | None:
    """Fetch a single CO-OPS product for a station. Returns parsed JSON or None."""
    url = f"{COOPS_API_BASE}?station={station_id}&product={product}&{COMMON_PARAMS}"
    if extra_params:
        url += f"&{extra_params}"

    req = Request(url, headers={
        "User-Agent": "os4csapi-publisher/1.0 (github.com/OS4CSAPI)",
        "Accept": "application/json",
    })

    try:
        with urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            # CO-OPS returns {"error": {"message": "..."}} when no data
            if "error" in data:
                return None
            return data
    except (HTTPError, Exception) as e:
        print(f"    [WARN] CO-OPS fetch failed for {station_id}/{product}: {e}")
        return None


def _parse_float(val: str | None) -> float | str:
    """Parse a CO-OPS value string to float, or string 'NaN' if missing.

    Returns the string ``"NaN"`` (not ``float('nan')``) so that
    ``json.dumps`` produces a valid JSON string token that OSH SensorHub's
    Gson parser can accept.
    """
    if val is None or val == "" or val == "None":
        return "NaN"
    try:
        return float(val)
    except (ValueError, TypeError):
        return "NaN"


def fetch_latest_observation(station_id: str, station_meta: dict) -> dict | None:
    """Fetch and combine all available products for a station.

    Returns a flat dict suitable for the CSAPI observation result, or None on failure.
    """
    sensors = station_meta.get("sensors", ["water_level"])

    # 1. Water level (primary — required)
    wl_data = _fetch_product(station_id, "water_level", "datum=MLLW")
    if not wl_data or "data" not in wl_data or not wl_data["data"]:
        print(f"    [WARN] No water level data for {station_id}")
        return None

    wl_rec = wl_data["data"][0]  # latest record
    obs_time_str = wl_rec.get("t", "")  # "2026-03-11 00:30"

    # Parse timestamp
    try:
        obs_dt = datetime.strptime(obs_time_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        ts_epoch = obs_dt.timestamp()
        ts_iso = obs_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError) as e:
        print(f"    [WARN] Cannot parse timestamp for {station_id}: {e}")
        return None

    water_level = _parse_float(wl_rec.get("v"))
    sigma = _parse_float(wl_rec.get("s"))

    # 2. Predictions — get the closest prediction to the observation time
    prediction = "NaN"
    pred_data = _fetch_product(station_id, "predictions", "datum=MLLW")
    if pred_data and "predictions" in pred_data:
        # Find prediction closest to obs time
        best_pred = None
        best_diff = float("inf")
        for p in pred_data["predictions"]:
            try:
                pt = datetime.strptime(p["t"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                diff = abs((pt - obs_dt).total_seconds())
                if diff < best_diff:
                    best_diff = diff
                    best_pred = p
            except (ValueError, KeyError):
                continue
        if best_pred and best_diff <= 360:  # within 6 minutes
            prediction = _parse_float(best_pred.get("v"))

    # 3. Air temperature
    air_temp = "NaN"
    if "air_temperature" in sensors:
        at_data = _fetch_product(station_id, "air_temperature")
        if at_data and "data" in at_data and at_data["data"]:
            air_temp = _parse_float(at_data["data"][0].get("v"))

    # 4. Water temperature
    water_temp = "NaN"
    if "water_temperature" in sensors:
        wt_data = _fetch_product(station_id, "water_temperature")
        if wt_data and "data" in wt_data and wt_data["data"]:
            water_temp = _parse_float(wt_data["data"][0].get("v"))

    # 5. Wind
    wind_speed = "NaN"
    wind_dir = "NaN"
    wind_gust = "NaN"
    if "wind" in sensors:
        wind_data = _fetch_product(station_id, "wind")
        if wind_data and "data" in wind_data and wind_data["data"]:
            w = wind_data["data"][0]
            wind_speed = _parse_float(w.get("s"))
            wind_dir = _parse_float(w.get("d"))
            wind_gust = _parse_float(w.get("g"))

    # 6. Barometric pressure
    pressure = "NaN"
    if "air_pressure" in sensors:
        bp_data = _fetch_product(station_id, "air_pressure")
        if bp_data and "data" in bp_data and bp_data["data"]:
            pressure = _parse_float(bp_data["data"][0].get("v"))

    # Build result dict
    result = {
        "timestamp": ts_epoch,
        "phenomenonTime": ts_iso,
        "stationId": station_id,
        "lat_deg": station_meta.get("lat", "NaN"),
        "lon_deg": station_meta.get("lon", "NaN"),
        "water_level_m": water_level,
        "prediction_m": prediction,
        "sigma_m": sigma,
        "air_temp_c": air_temp,
        "water_temp_c": water_temp,
        "wind_speed_ms": wind_speed,
        "wind_direction_deg": wind_dir,
        "wind_gust_ms": wind_gust,
        "pressure_hpa": pressure,
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Multi-station publisher
# ═══════════════════════════════════════════════════════════════════════════

class COOPSPublisher:
    """Multi-station CO-OPS coastal publisher.

    Connects to one system+datastream per station, publishes observations
    for all stations in each cycle. Uses direct REST API calls.
    """

    name = "CO-OPS Coastal Observation Publisher"

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

        # station_id → datastream server ID
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
        return f"urn:os4csapi:system:coops:{station_id}:v1"

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

        # Go server workarounds
        if self._is_go_server:
            r = obs.get("result", {})
            for key, val in list(r.items()):
                if val == "NaN":
                    r[key] = 0.0
            # Go server requires timestamp in result (schema validation)
            if "timestamp" not in r:
                r["timestamp"] = obs.get("phenomenonTime", "")
            elif not isinstance(r["timestamp"], str):
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
        """Fetch + publish observations for all stations. Returns count published."""
        published = 0
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")

        for st in self.stations:
            station_id = st["id"]
            ds_id = self._ds_ids.get(station_id)
            if ds_id is None and not dry_run:
                continue

            # Fetch from CO-OPS
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
                wl = obs_data.get("water_level_m", "?")
                pred = obs_data.get("prediction_m", "?")
                at = obs_data.get("air_temp_c", "?")
                wt = obs_data.get("water_temp_c", "?")
                print(f"  [{ts}] {station_id}: [DRY] wl={wl}m pred={pred}m air={at}°C water={wt}°C")
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    self._last_obs_ts[station_id] = obs_ts

                    wl = obs_data.get("water_level_m", "?")
                    pred = obs_data.get("prediction_m", "?")
                    at = obs_data.get("air_temp_c", "?")
                    ws = obs_data.get("wind_speed_ms", "?")
                    print(f"  [{ts}] {station_id}: OK  wl={wl}m pred={pred}m air={at}°C wind={ws}m/s")
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  [{ts}] {station_id}: ERR {e}")

        return published

    def run(self, *, interval: float = 360.0, dry_run: bool = False, once: bool = False):
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
        description="CO-OPS coastal observation publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=360.0,
                        help="Seconds between publish cycles (default: 360)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    parser.add_argument("--stations", type=str, default=None,
                        help="Comma-separated station IDs to publish (default: all from stations.json)")
    args = parser.parse_args()

    station_filter = args.stations.split(",") if args.stations else None
    publisher = COOPSPublisher(station_filter=station_filter)
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
