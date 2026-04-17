#!/usr/bin/env python3
"""
opensky_publisher.py — OpenSky Network ADS-B state vector publisher for CSAPI/OSH.

Fetches aircraft state vectors from the OpenSky Network REST API for a bounding
box over southern Arizona, and publishes each aircraft's state as an individual
observation to a single CSAPI datastream (Pattern C: feed adapter).

OpenSky Network API:
  - Endpoint: https://opensky-network.org/api/states/all?lamin=...&lomin=...&lamax=...&lomax=...
  - Anonymous: 400 credits/day, 10s time resolution
  - Returns JSON: { "time": <epoch>, "states": [ [icao24, callsign, ...], ... ] }
  - State vector fields (index → name):
      0: icao24        1: callsign       2: origin_country
      3: time_position 4: last_contact   5: longitude
      6: latitude      7: baro_altitude  8: on_ground
      9: velocity     10: true_track    11: vertical_rate
     12: sensors      13: geo_altitude  14: squawk
     15: spi          16: position_source

Configuration is read from config.json (same directory).

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)

Usage:
    python -m publishers.opensky.opensky_publisher                    # run forever (5min cadence)
    python -m publishers.opensky.opensky_publisher --dry-run          # print only
    python -m publishers.opensky.opensky_publisher --once             # single cycle
    python -m publishers.opensky.opensky_publisher --interval 600     # 10min cadence

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

OPENSKY_API_URL = "https://opensky-network.org/api/states/all"
SYSTEM_UID = "urn:os4csapi:system:opensky-feed:v1"
DS_OUTPUT_NAME = "adsbState"

# Position source code → label
POS_SOURCE_MAP = {0: "ADS-B", 1: "ASTERIX", 2: "MLAT", 3: "FLARM"}


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "config.json")) as f:
        return json.load(f)["opensky"]


# ═══════════════════════════════════════════════════════════════════════════
#  OpenSky data fetching
# ═══════════════════════════════════════════════════════════════════════════

def _safe_float(val) -> float | str:
    """Convert a value to float, or string 'NaN' if None/unparseable.

    Returns the string ``"NaN"`` (not ``float('nan')``) so that
    ``json.dumps`` produces a valid JSON token that OSH SensorHub's
    Gson parser can accept.
    """
    if val is None:
        return "NaN"
    try:
        return float(val)
    except (ValueError, TypeError):
        return "NaN"


def fetch_state_vectors(bbox: dict) -> tuple[int, list[list]] | None:
    """Fetch aircraft state vectors from OpenSky for the configured bounding box.

    Returns (api_time, state_vectors_list) or None on failure.
    """
    url = (
        f"{OPENSKY_API_URL}"
        f"?lamin={bbox['lamin']}&lomin={bbox['lomin']}"
        f"&lamax={bbox['lamax']}&lomax={bbox['lomax']}"
    )

    req = Request(url, headers={
        "User-Agent": "os4csapi-publisher/1.0 (github.com/OS4CSAPI)",
        "Accept": "application/json",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            api_time = data.get("time", 0)
            states = data.get("states") or []
            return (api_time, states)
    except HTTPError as e:
        if e.code == 429:
            retry_after = e.headers.get("X-Rate-Limit-Retry-After-Seconds", "?")
            print(f"    [WARN] Rate limited (429). Retry after {retry_after}s")
        else:
            print(f"    [WARN] OpenSky API HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}")
        return None
    except Exception as e:
        print(f"    [WARN] OpenSky API fetch failed: {e}")
        return None


def parse_state_vector(sv: list, api_time: int) -> dict | None:
    """Parse a single OpenSky state vector array into a flat observation dict.

    Returns dict suitable for CSAPI observation result, or None if no valid position.
    State vector indices:
      0: icao24, 1: callsign, 2: origin_country, 3: time_position,
      4: last_contact, 5: longitude, 6: latitude, 7: baro_altitude,
      8: on_ground, 9: velocity, 10: true_track, 11: vertical_rate,
      12: sensors, 13: geo_altitude, 14: squawk, 15: spi, 16: position_source
    """
    if len(sv) < 17:
        return None

    # Skip aircraft without a valid position
    lat = sv[6]
    lon = sv[5]
    if lat is None or lon is None:
        return None

    # Use time_position if available, otherwise last_contact, otherwise api_time
    ts = sv[3] or sv[4] or api_time
    try:
        ts_epoch = float(ts)
    except (ValueError, TypeError):
        ts_epoch = float(api_time)

    obs_dt = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
    ts_iso = obs_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    icao24 = sv[0] or ""
    callsign = (sv[1] or "").strip()
    origin_country = sv[2] or ""
    on_ground = sv[8] if sv[8] is not None else False
    squawk = sv[14] or ""
    pos_source_code = sv[16] if len(sv) > 16 else 0
    pos_source = POS_SOURCE_MAP.get(pos_source_code, f"Unknown({pos_source_code})")

    return {
        "timestamp": ts_epoch,
        "phenomenonTime": ts_iso,
        "icao24": icao24,
        "callsign": callsign,
        "origin_country": origin_country,
        "lat_deg": _safe_float(lat),
        "lon_deg": _safe_float(lon),
        "baro_altitude_m": _safe_float(sv[7]),
        "geo_altitude_m": _safe_float(sv[13]),
        "velocity_ms": _safe_float(sv[9]),
        "true_track_deg": _safe_float(sv[10]),
        "vertical_rate_ms": _safe_float(sv[11]),
        "on_ground": str(on_ground).lower(),
        "squawk": squawk,
        "position_source": pos_source,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Feed publisher
# ═══════════════════════════════════════════════════════════════════════════

class OpenSkyPublisher:
    """OpenSky Network ADS-B feed adapter publisher.

    Single system + single datastream. Each observation is one aircraft's
    state vector. Multiple observations published per cycle.
    """

    name = "OpenSky ADS-B Publisher"

    def __init__(self):
        self.config = _load_config()
        self.bbox = self.config["bounding_box"]

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

        self._ds_id: str | None = None
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0, "aircraft_seen": 0}

        # Track last observation per aircraft to skip truly identical reports
        self._last_seen: dict[str, float] = {}  # icao24 → last_contact epoch

        # REST config
        import base64
        self._base_url = os.environ.get(
            "OSH_BASE_URL",
            f"https://{self.osh_address}/{self.osh_root}/api",
        )
        self._is_go_server = "csapi-go" in self._base_url
        self._auth = "Basic " + base64.b64encode(
            f"{self.osh_user}:{self.osh_pass}".encode()).decode()

    def connect(self):
        """Resolve system and datastream ID via REST API."""
        sys_id = find_by_uid(self._base_url, self._auth, "systems", SYSTEM_UID)
        if not sys_id:
            raise RuntimeError(f"System '{SYSTEM_UID}' not found on server")

        ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
        if ds_list:
            for item in ds_list.get("items", []):
                if item.get("outputName") == DS_OUTPUT_NAME:
                    self._ds_id = item.get("id")
                    break

        if not self._ds_id:
            raise RuntimeError(f"Datastream '{DS_OUTPUT_NAME}' not found under system {sys_id}")

        print(f"  Connected: sys={sys_id} ds={self._ds_id}")

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

    def _post_observation(self, obs: dict):
        """POST an observation to the server using direct REST (allows NaN serialization)."""
        import ssl

        # Go server rejects "NaN" strings — replace with 0.0 for numeric fields
        if self._is_go_server:
            r = obs.get("result", {})
            for key, val in r.items():
                if val == "NaN":
                    r[key] = 0.0

        url = f"{self._base_url}/datastreams/{self._ds_id}/observations"
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
        """Fetch state vectors and publish observations. Returns count published."""
        published = 0
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")

        result = fetch_state_vectors(self.bbox)
        if result is None:
            self.stats["errors"] += 1
            print(f"  [{ts}] API fetch failed")
            return 0

        api_time, states = result
        print(f"  [{ts}] Received {len(states)} aircraft from OpenSky (api_time={api_time})")

        cycle_published = 0
        cycle_skipped = 0
        cycle_errors = 0

        for sv in states:
            obs_data = parse_state_vector(sv, api_time)
            if obs_data is None:
                cycle_skipped += 1
                continue

            icao24 = obs_data["icao24"]
            obs_ts = obs_data.get("timestamp", 0)

            # Skip if this exact aircraft+timestamp was already published
            if obs_ts and obs_ts == self._last_seen.get(icao24):
                cycle_skipped += 1
                continue

            # Build observation envelope
            phenomenon_time = obs_data.pop("phenomenonTime")
            if self._is_go_server:
                # Go server validates all schema fields are present;
                # keep timestamp but coerce to string (Time type requirement)
                obs_data["timestamp"] = str(obs_data["timestamp"])
            else:
                obs_data.pop("timestamp", None)
            obs = {
                "phenomenonTime": phenomenon_time,
                "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": obs_data,
            }

            if dry_run:
                cs = obs_data.get("callsign", "")
                alt = obs_data.get("baro_altitude_m", "?")
                spd = obs_data.get("velocity_ms", "?")
                trk = obs_data.get("true_track_deg", "?")
                gnd = obs_data.get("on_ground", "?")
                print(f"    [DRY] {icao24} {cs:8s} alt={alt}m spd={spd}m/s trk={trk}° gnd={gnd}")
                cycle_published += 1
            else:
                try:
                    self._post_observation(obs)
                    self.stats["published"] += 1
                    published += 1
                    cycle_published += 1
                    self._last_seen[icao24] = obs_ts
                except Exception as e:
                    self.stats["errors"] += 1
                    cycle_errors += 1
                    if cycle_errors <= 3:
                        print(f"    [{ts}] ERR {icao24}: {e}")
                    elif cycle_errors == 4:
                        print(f"    [{ts}] (suppressing further errors this cycle)")

        self.stats["skipped"] += cycle_skipped
        self.stats["aircraft_seen"] += cycle_published

        print(f"  [{ts}] Cycle complete: {cycle_published} published, {cycle_skipped} skipped, {cycle_errors} errors")

        # Prune stale entries from _last_seen (aircraft no longer in bbox)
        # Keep only aircraft seen in the last 30 minutes
        cutoff = time.time() - 1800
        stale = [k for k, v in self._last_seen.items() if v < cutoff]
        for k in stale:
            del self._last_seen[k]

        return published

    def run(self, *, interval: float = 300.0, dry_run: bool = False, once: bool = False):
        """Main publisher loop."""
        bbox = self.bbox
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  Bbox:      lat {bbox['lamin']}–{bbox['lamax']}, lon {bbox['lomin']}–{bbox['lomax']}")
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
        print(f"  Published:     {self.stats['published']}")
        print(f"  Aircraft seen: {self.stats['aircraft_seen']}")
        print(f"  Skipped:       {self.stats['skipped']} (no position / unchanged)")
        print(f"  Errors:        {self.stats['errors']}")
        print(f"  Reconnects:    {self.stats['reconnects']}")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="OpenSky Network ADS-B publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=300.0,
                        help="Seconds between publish cycles (default: 300)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    args = parser.parse_args()

    publisher = OpenSkyPublisher()
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
