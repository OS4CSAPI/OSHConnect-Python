#!/usr/bin/env python3
"""
aviation_wx_publisher.py — AviationWeather.gov METAR publisher for CSAPI/OSH.

Fetches the latest METAR observations for configured stations from the
AviationWeather.gov REST API, and publishes them to CSAPI.

Station list is read from stations.json (same directory).

AviationWeather.gov API:
  - Endpoint: https://aviationweather.gov/api/data/metar?ids={icao1},{icao2}&format=json
  - No authentication required
  - Returns JSON array of decoded METAR objects
  - Fields: icaoId, temp, dewp, wdir, wspd, visib, altim, slp,
            rawOb, lat, lon, elev, name, cover, clouds[], fltCat, obsTime

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)

Usage:
    python -m publishers.aviation_wx.aviation_wx_publisher                    # run forever (5min cadence)
    python -m publishers.aviation_wx.aviation_wx_publisher --dry-run          # print only
    python -m publishers.aviation_wx.aviation_wx_publisher --once             # single cycle
    python -m publishers.aviation_wx.aviation_wx_publisher --interval 600     # 10min cadence
    python -m publishers.aviation_wx.aviation_wx_publisher --stations KTUS,KPHX  # subset

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

AWX_API_URL = "https://aviationweather.gov/api/data/metar"
DS_OUTPUT_NAME = "metarObs"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["aviation_wx_stations"]


# ═══════════════════════════════════════════════════════════════════════════
#  AviationWeather data fetching
# ═══════════════════════════════════════════════════════════════════════════

def _parse_float(val) -> float | str:
    """Parse a value to float, or string 'NaN' if missing/unparseable.

    Returns the string ``"NaN"`` (not ``float('nan')``) so that
    ``json.dumps`` produces a valid JSON string token that OSH SensorHub's
    Gson parser can accept.
    """
    if val is None or val == "" or val == "None":
        return "NaN"
    # Handle string values like "10+" for visibility
    if isinstance(val, str):
        val = val.rstrip("+")
        try:
            return float(val)
        except (ValueError, TypeError):
            return "NaN"
    try:
        return float(val)
    except (ValueError, TypeError):
        return "NaN"


def fetch_all_metars(station_ids: list[str]) -> list[dict] | None:
    """Fetch METAR data for all stations in a single API call.

    Returns list of decoded METAR objects, or None on failure.
    """
    ids_str = ",".join(station_ids)
    url = f"{AWX_API_URL}?ids={ids_str}&format=json"

    req = Request(url, headers={
        "User-Agent": "os4csapi-publisher/1.0 (github.com/OS4CSAPI)",
        "Accept": "application/json",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not isinstance(data, list):
                print(f"    [WARN] AWX API returned non-list: {type(data)}")
                return None
            return data
    except (HTTPError, Exception) as e:
        print(f"    [WARN] AWX API fetch failed: {e}")
        return None


def parse_metar_observation(metar: dict, station_meta: dict) -> dict | None:
    """Parse a single METAR JSON object into a flat observation dict.

    Returns dict suitable for CSAPI observation result, or None on failure.
    """
    icao_id = metar.get("icaoId", "")

    # Parse observation time (epoch seconds)
    obs_time = metar.get("obsTime")
    if obs_time is None:
        print(f"    [WARN] No obsTime for {icao_id}")
        return None

    try:
        ts_epoch = float(obs_time)
        obs_dt = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
        ts_iso = obs_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError, OSError) as e:
        print(f"    [WARN] Cannot parse obsTime for {icao_id}: {e}")
        return None

    # Parse core fields
    temp_c = _parse_float(metar.get("temp"))
    dewp_c = _parse_float(metar.get("dewp"))
    wind_dir = _parse_float(metar.get("wdir"))
    wind_speed = _parse_float(metar.get("wspd"))
    visibility = _parse_float(metar.get("visib"))  # can be "10+" → 10.0
    altimeter = _parse_float(metar.get("altim"))
    slp = _parse_float(metar.get("slp"))

    # Convert altimeter from hPa to inHg (1 hPa = 0.02953 inHg)
    if isinstance(altimeter, (int, float)):
        altimeter_inhg = round(altimeter * 0.02953, 2)
    else:
        altimeter_inhg = "NaN"

    # Flight category
    flt_cat = metar.get("fltCat", "UNK") or "UNK"

    # Cloud cover — dominant cover from the API "cover" field
    cloud_cover = metar.get("cover", "CLR") or "CLR"

    # Lowest cloud base from clouds array
    clouds = metar.get("clouds", []) or []
    cloud_base_ft = "NaN"
    if clouds:
        for layer in clouds:
            base = layer.get("base")
            if base is not None:
                cloud_base_ft = _parse_float(base)
                break  # first (lowest) layer

    # Raw METAR
    raw_ob = metar.get("rawOb", "") or ""

    # Build result
    result = {
        "timestamp": ts_epoch,
        "phenomenonTime": ts_iso,
        "stationId": icao_id,
        "lat_deg": station_meta.get("lat", metar.get("lat", "NaN")),
        "lon_deg": station_meta.get("lon", metar.get("lon", "NaN")),
        "temp_c": temp_c,
        "dewp_c": dewp_c,
        "wind_dir_deg": wind_dir,
        "wind_speed_kt": wind_speed,
        "visibility_sm": visibility,
        "altimeter_inhg": altimeter_inhg,
        "slp_hpa": slp,
        "flight_category": flt_cat,
        "cloud_cover": cloud_cover,
        "cloud_base_ft": cloud_base_ft,
        "rawMessage": raw_ob,
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Multi-station publisher
# ═══════════════════════════════════════════════════════════════════════════

class AviationWxPublisher:
    """Multi-station AviationWeather METAR publisher.

    Connects to one system+datastream per station, publishes observations
    for all stations in each cycle. Uses direct REST API calls.
    """

    name = "AviationWeather METAR Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        self.stations = _load_stations()
        if station_filter:
            filt = set(s.strip().upper() for s in station_filter)
            self.stations = [s for s in self.stations if s["icao_id"] in filt]

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

        # station icao_id → datastream server ID
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

    def _system_uid(self, icao_id: str) -> str:
        return f"urn:os4csapi:system:awx:{icao_id.lower()}:v1"

    def connect(self):
        """Resolve system and datastream IDs for each station via REST API."""
        for st in self.stations:
            uid = self._system_uid(st["icao_id"])
            sys_id = find_by_uid(self._base_url, self._auth, "systems", uid)
            if not sys_id:
                print(f"  [WARN] System '{uid}' not found — skipping {st['icao_id']}")
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
                print(f"  [WARN] Datastream '{DS_OUTPUT_NAME}' not found for {st['icao_id']} — skipping")
                continue

            self._ds_ids[st["icao_id"]] = ds_id
            print(f"  Connected: {st['icao_id']} → sys={sys_id} ds={ds_id}")

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

        req = Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": self._auth,
            "Host": self.osh_address,
        })

        try:
            with urlopen(req, timeout=30, context=ctx) as resp:
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

        # Fetch all METARs in one API call
        station_ids = [st["icao_id"] for st in self.stations]
        metars = fetch_all_metars(station_ids)
        if metars is None:
            self.stats["errors"] += 1
            print(f"  [{ts}] API fetch failed for all stations")
            return 0

        # Build lookup by ICAO ID
        metar_by_id: dict[str, dict] = {}
        for m in metars:
            icao = m.get("icaoId", "")
            if icao:
                metar_by_id[icao] = m

        for st in self.stations:
            icao_id = st["icao_id"]
            ds_id = self._ds_ids.get(icao_id)
            if ds_id is None and not dry_run:
                continue

            metar = metar_by_id.get(icao_id)
            if metar is None:
                self.stats["errors"] += 1
                print(f"  [{ts}] {icao_id}: no METAR in API response")
                continue

            obs_data = parse_metar_observation(metar, st)
            if obs_data is None:
                self.stats["errors"] += 1
                continue

            # Skip if observation timestamp hasn't changed
            obs_ts = obs_data.get("timestamp", 0)
            if obs_ts and obs_ts == self._last_obs_ts.get(icao_id):
                self.stats["skipped"] += 1
                print(f"  [{ts}] {icao_id}: unchanged, skipping")
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
                temp = obs_data.get("temp_c", "?")
                wind = obs_data.get("wind_speed_kt", "?")
                vis = obs_data.get("visibility_sm", "?")
                fcat = obs_data.get("flight_category", "?")
                raw = obs_data.get("rawMessage", "")[:60]
                print(f"  [{ts}] {icao_id}: [DRY] {temp}°C wind={wind}kt vis={vis}SM {fcat}")
                print(f"         RAW: {raw}")
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    self._last_obs_ts[icao_id] = obs_ts

                    temp = obs_data.get("temp_c", "?")
                    wind = obs_data.get("wind_speed_kt", "?")
                    vis = obs_data.get("visibility_sm", "?")
                    fcat = obs_data.get("flight_category", "?")
                    print(f"  [{ts}] {icao_id}: OK  {temp}°C wind={wind}kt vis={vis}SM {fcat}")
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  [{ts}] {icao_id}: ERR {e}")

        return published

    def run(self, *, interval: float = 300.0, dry_run: bool = False, once: bool = False):
        """Main publisher loop."""
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    https://{self.osh_address}:{self.osh_port}/{self.osh_root}/api")
        print(f"  Stations:  {len(self.stations)} ({', '.join(s['icao_id'] for s in self.stations)})")
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
        description="AviationWeather METAR publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=300.0,
                        help="Seconds between publish cycles (default: 300)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    parser.add_argument("--stations", type=str, default=None,
                        help="Comma-separated ICAO IDs to publish (default: all from stations.json)")
    args = parser.parse_args()

    station_filter = args.stations.split(",") if args.stations else None
    publisher = AviationWxPublisher(station_filter=station_filter)
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
