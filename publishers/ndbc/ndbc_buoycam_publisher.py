#!/usr/bin/env python3
"""
ndbc_buoycam_publisher.py — NDBC BuoyCAM image publisher for CSAPI/OSH.

For each camera-equipped buoy:
  1. Fetches the latest BuoyCAM JPEG from NDBC
  2. Computes SHA-256; skips if identical to last published image
  3. Caches the image to an immutable local path (served by Caddy)
  4. Publishes a JSON observation record referencing the cached URL

State is persisted in buoycam_state.json to survive restarts without
duplicating observations.

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)
    BUOYCAM_CACHE_ROOT Local image cache dir      (default: /var/www/buoycam)
    BUOYCAM_CACHE_BASE_URL  Public base URL       (required for image publishing)

Usage:
    python -m publishers.ndbc.ndbc_buoycam_publisher                    # run forever (15min)
    python -m publishers.ndbc.ndbc_buoycam_publisher --dry-run          # print only
    python -m publishers.ndbc.ndbc_buoycam_publisher --once             # single cycle
    python -m publishers.ndbc.ndbc_buoycam_publisher --interval 300     # 5min cadence
    python -m publishers.ndbc.ndbc_buoycam_publisher --stations 46025   # single station

Requires: Python 3.10+, no external dependencies.
"""

import argparse
import base64
import hashlib
import json
import os
import random
import ssl
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import api_get, find_by_uid
from publishers.ndbc.image_cache import immutable_url, save_image


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════

NDBC_BUOYCAM_BASE = "https://www.ndbc.noaa.gov/buoycam.php?station="
BUOYCAM_DS_OUTPUT_NAME = "ndbcBuoyCamImage"

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "buoycam_state.json")


def _load_stations() -> list[dict]:
    """Load camera-equipped buoy list from stations.json."""
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json")) as f:
        all_stations = json.load(f)["ndbc_buoys"]
    return [s for s in all_stations if s.get("has_buoycam")]


# ═══════════════════════════════════════════════════════════════════════════
#  State persistence
# ═══════════════════════════════════════════════════════════════════════════

def _load_state() -> dict:
    """Load per-station dedup state from JSON file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_state(state: dict):
    """Persist per-station dedup state."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        print(f"    [WARN] Could not save state: {e}")


# ═══════════════════════════════════════════════════════════════════════════
#  Image fetching + hashing
# ═══════════════════════════════════════════════════════════════════════════

def fetch_buoycam_image(station_id: str) -> tuple[bytes, str] | None:
    """Fetch the latest BuoyCAM JPEG for a station.

    Returns (image_bytes, content_type) or None on failure.
    """
    url = f"{NDBC_BUOYCAM_BASE}{station_id}"
    req = Request(url, headers={
        "User-Agent": "os4csapi-buoycam-publisher/1.0 (github.com/OS4CSAPI)",
        "Accept": "image/jpeg, image/*",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            ct = resp.headers.get("Content-Type", "image/jpeg")
            data = resp.read()
            if len(data) < 500:
                # Too small — likely an error page, not a real image
                print(f"    [WARN] {station_id}: response too small ({len(data)} bytes), skipping")
                return None
            return data, ct
    except (HTTPError, Exception) as e:
        print(f"    [WARN] {station_id}: BuoyCAM fetch failed: {e}")
        return None


def compute_sha256(data: bytes) -> str:
    """Compute hex SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
#  Publisher
# ═══════════════════════════════════════════════════════════════════════════

class BuoyCamPublisher:
    """Multi-station NDBC BuoyCAM image publisher."""

    name = "NDBC BuoyCAM Image Publisher"

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

        self._base_url = os.environ.get(
            "OSH_BASE_URL",
            f"https://{self.osh_address}/{self.osh_root}/api",
        )
        self._is_go_server = "csapi-go" in self._base_url
        self._auth = "Basic " + base64.b64encode(
            f"{self.osh_user}:{self.osh_pass}".encode()).decode()

        # station_id → buoycam datastream server ID
        self._ds_ids: dict[str, str] = {}

        # Per-station dedup state
        self._state = _load_state()

        self.stats = {"published": 0, "errors": 0, "skipped": 0, "reconnects": 0}

    def _system_uid(self, station_id: str) -> str:
        return f"urn:os4csapi:system:ndbc:{station_id}:v1"

    def connect(self):
        """Resolve BuoyCAM datastream IDs for each camera-equipped station."""
        for st in self.stations:
            uid = self._system_uid(st["id"])
            sys_id = find_by_uid(self._base_url, self._auth, "systems", uid)
            if not sys_id:
                print(f"  [WARN] System '{uid}' not found — skipping {st['id']}")
                continue

            # Find BuoyCAM datastream by output name
            ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
            ds_id = None
            if ds_list:
                for item in ds_list.get("items", []):
                    if item.get("outputName") == BUOYCAM_DS_OUTPUT_NAME:
                        ds_id = item.get("id")
                        break

            if not ds_id:
                print(f"  [WARN] BuoyCAM datastream not found for {st['id']} — skipping")
                continue

            self._ds_ids[st["id"]] = ds_id
            print(f"  Connected: {st['id']} → sys={sys_id} ds={ds_id}")

        print(f"  Ready: {len(self._ds_ids)}/{len(self.stations)} cameras connected")

    def connect_with_retry(self, max_attempts=10, base_delay=5.0, max_delay=120.0):
        """Connect with exponential backoff."""
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
        """POST an observation to the server."""
        # Go server workarounds
        if self._is_go_server:
            r = obs.get("result", {})
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
        """Fetch + cache + publish BuoyCAM images for all stations."""
        published = 0
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")

        for st in self.stations:
            station_id = st["id"]
            ds_id = self._ds_ids.get(station_id)
            if ds_id is None and not dry_run:
                continue

            # Fetch latest image
            result = fetch_buoycam_image(station_id)
            if result is None:
                self.stats["errors"] += 1
                continue

            image_bytes, content_type = result
            img_hash = compute_sha256(image_bytes)

            # Dedup: skip if hash matches last published
            station_state = self._state.get(station_id, {})
            if img_hash == station_state.get("lastSha256"):
                self.stats["skipped"] += 1
                print(f"  [{ts}] {station_id}: unchanged (hash match), skipping")
                continue

            # Cache image to immutable path
            fetch_time = now
            if not dry_run:
                try:
                    local_path = save_image(station_id, fetch_time, image_bytes)
                except Exception as e:
                    print(f"  [{ts}] {station_id}: cache write failed: {e}")
                    self.stats["errors"] += 1
                    continue

            cached_url = immutable_url(station_id, fetch_time)
            latest_url = f"{NDBC_BUOYCAM_BASE}{station_id}"

            # Build observation record
            # Note: timestamp (SWE Time field) is excluded from result —
            # server auto-fills it from phenomenonTime, matching met obs pattern.
            obs = {
                "phenomenonTime": fetch_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "resultTime": fetch_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": {
                    "stationId": station_id,
                    "imageUrl": cached_url,
                    "mediaType": "image/jpeg",
                    "cameraStatus": "ok",
                    "sha256": img_hash,
                    "contentLength": len(image_bytes),
                    "latestImageUrl": latest_url,
                },
            }

            if dry_run:
                print(f"  [{ts}] {station_id}: [DRY] new image {len(image_bytes)} bytes "
                      f"hash={img_hash[:12]}... → {cached_url}")
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1

                    # Update state
                    self._state[station_id] = {
                        "lastSha256": img_hash,
                        "lastFetchTime": fetch_time.isoformat(),
                        "lastContentLength": len(image_bytes),
                    }
                    _save_state(self._state)

                    print(f"  [{ts}] {station_id}: OK  {len(image_bytes)} bytes "
                          f"hash={img_hash[:12]}...")
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  [{ts}] {station_id}: ERR {e}")

        return published

    def run(self, *, interval: float = 900.0, dry_run: bool = False, once: bool = False):
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
        print(f"  Skipped:    {self.stats['skipped']} (unchanged)")
        print(f"  Errors:     {self.stats['errors']}")
        print(f"  Reconnects: {self.stats['reconnects']}")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="NDBC BuoyCAM image publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=900.0,
                        help="Seconds between publish cycles (default: 900)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    parser.add_argument("--stations", type=str, default=None,
                        help="Comma-separated station IDs (default: all camera-equipped)")
    args = parser.parse_args()

    station_filter = args.stations.split(",") if args.stations else None
    publisher = BuoyCamPublisher(station_filter=station_filter)
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
