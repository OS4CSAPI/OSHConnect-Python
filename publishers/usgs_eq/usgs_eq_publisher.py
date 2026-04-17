#!/usr/bin/env python3
"""
usgs_eq_publisher.py — USGS Earthquake Feed publisher for CSAPI/OSH.

Fetches earthquake events from the USGS GeoJSON summary feed and publishes
each event as an individual observation to a single CSAPI datastream
(Pattern C: feed adapter).

USGS Earthquake Hazards Program API:
  - Endpoint: https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson
  - No API key required
  - Returns GeoJSON FeatureCollection
  - Updated by USGS every ~60 seconds
  - Typical response: 200-400 features, ~300 KB

Deduplication:
  - Key: (feature.id, properties.updated) tuple
  - Skip events already published with the same (id, updated)
  - Re-publish if updated timestamp changes (event revision)

Configuration is read from config.json (same directory).

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)

Usage:
    python -m publishers.usgs_eq.usgs_eq_publisher                    # run forever (60s cadence)
    python -m publishers.usgs_eq.usgs_eq_publisher --dry-run          # print only
    python -m publishers.usgs_eq.usgs_eq_publisher --once             # single cycle
    python -m publishers.usgs_eq.usgs_eq_publisher --interval 120     # 2-min cadence

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

SYSTEM_UID = "urn:os4csapi:system:usgs-eq-feed:v1"
DS_OUTPUT_NAME = "earthquakeEvent"


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "config.json")) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════
#  USGS Earthquake data fetching
# ═══════════════════════════════════════════════════════════════════════════

def fetch_earthquakes(feed_url: str) -> tuple[int, list[dict]] | None:
    """Fetch earthquake features from the USGS GeoJSON feed.

    Returns (generated_epoch_ms, features_list) or None on failure.
    """
    req = Request(feed_url, headers={
        "User-Agent": "os4csapi-publisher/1.0 (github.com/OS4CSAPI)",
        "Accept": "application/json",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            generated = data.get("metadata", {}).get("generated", 0)
            features = data.get("features") or []
            return (generated, features)
    except HTTPError as e:
        print(f"    [WARN] USGS API HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}")
        return None
    except Exception as e:
        print(f"    [WARN] USGS API fetch failed: {e}")
        return None


def parse_earthquake(feature: dict) -> dict | None:
    """Parse a single GeoJSON earthquake feature into an observation dict.

    Returns dict suitable for CSAPI observation result, or None if invalid.
    """
    event_id = feature.get("id")
    if not event_id:
        return None

    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])

    # Need at least lon, lat
    if not coords or len(coords) < 2:
        return None

    lon = coords[0]
    lat = coords[1]
    depth_km = coords[2] if len(coords) > 2 else 0.0

    # Event time and updated time (epoch ms)
    event_time_ms = props.get("time", 0)
    updated_ms = props.get("updated", 0)
    mag = props.get("mag")
    mag_type = props.get("magType", "")
    place = props.get("place", "")
    status = props.get("status", "")
    event_type = props.get("type", "earthquake")
    title = props.get("title", "")
    detail_url = props.get("detail", "")

    # Convert event time to ISO for phenomenonTime
    if event_time_ms:
        event_dt = datetime.fromtimestamp(event_time_ms / 1000.0, tz=timezone.utc)
        phenomenon_time = event_dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{event_time_ms % 1000:03d}Z"
    else:
        phenomenon_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "event_id": event_id,
        "updated_ms": updated_ms,
        "phenomenonTime": phenomenon_time,
        "result": {
            "eventId": event_id,
            "magnitude": float(mag) if mag is not None else "NaN",
            "magType": mag_type or "unknown",
            "place": place or "Unknown location",
            "eventTime": event_time_ms,
            "updatedTime": updated_ms,
            "latitude": float(lat),
            "longitude": float(lon),
            "depth_km": float(depth_km) if depth_km is not None else 0.0,
            "status": status or "automatic",
            "eventType": event_type,
            "title": title,
            "detailUrl": detail_url,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Feed publisher
# ═══════════════════════════════════════════════════════════════════════════

class USGSEarthquakePublisher:
    """USGS Earthquake Feed adapter publisher.

    Single system + single datastream. Each observation is one earthquake event.
    Multiple observations published per cycle (only new/revised events).
    """

    name = "USGS Earthquake Publisher"

    def __init__(self):
        self.config = _load_config()
        self.feed_url = self.config.get(
            "feedUrl",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
        )

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
        self.stats = {
            "published": 0,
            "errors": 0,
            "reconnects": 0,
            "skipped": 0,
            "events_seen": 0,
            "revisions": 0,
        }

        # Dedupe cache: event_id → updated_ms
        # If event_id exists and updated_ms matches, skip
        # If event_id exists but updated_ms changed, re-publish (revision)
        self._seen: dict[str, int] = {}

        # REST config
        import base64
        self._base_url = os.environ.get(
            "OSH_BASE_URL",
            f"https://{self.osh_address}/{self.osh_root}/api",
        )
        self._coerce_time_to_str = "csapi-go" in self._base_url
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
        """POST an observation to the server."""
        import ssl

        # Go CSAPI server requires Time fields as strings
        if self._coerce_time_to_str:
            r = obs.get("result", {})
            for key in ("eventTime", "updatedTime"):
                if key in r and not isinstance(r[key], str):
                    r[key] = str(r[key])

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
        """Fetch earthquake feed and publish new/revised events. Returns count published."""
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")

        result = fetch_earthquakes(self.feed_url)
        if result is None:
            self.stats["errors"] += 1
            print(f"  [{ts}] API fetch failed")
            return 0

        generated, features = result
        print(f"  [{ts}] Received {len(features)} earthquakes from USGS (generated={generated})")

        cycle_published = 0
        cycle_skipped = 0
        cycle_revisions = 0
        cycle_errors = 0

        for feature in features:
            parsed = parse_earthquake(feature)
            if parsed is None:
                cycle_skipped += 1
                continue

            event_id = parsed["event_id"]
            updated_ms = parsed["updated_ms"]

            # Dedupe check
            prev_updated = self._seen.get(event_id)
            if prev_updated is not None:
                if prev_updated == updated_ms:
                    # Same event, not revised — skip
                    cycle_skipped += 1
                    continue
                else:
                    # Revised event — re-publish
                    cycle_revisions += 1

            # Build observation envelope
            obs = {
                "phenomenonTime": parsed["phenomenonTime"],
                "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": parsed["result"],
            }

            if dry_run:
                mag = parsed["result"].get("magnitude", "?")
                place = parsed["result"].get("place", "?")
                depth = parsed["result"].get("depth_km", "?")
                is_rev = " [REVISED]" if prev_updated is not None else ""
                print(f"    [DRY] {event_id} M{mag} depth={depth}km {place}{is_rev}")
                cycle_published += 1
                self._seen[event_id] = updated_ms
            else:
                try:
                    self._post_observation(obs)
                    self.stats["published"] += 1
                    cycle_published += 1
                    self._seen[event_id] = updated_ms
                except Exception as e:
                    self.stats["errors"] += 1
                    cycle_errors += 1
                    if cycle_errors <= 3:
                        print(f"    [{ts}] ERR {event_id}: {e}")
                    elif cycle_errors == 4:
                        print(f"    [{ts}] (suppressing further errors this cycle)")

        self.stats["skipped"] += cycle_skipped
        self.stats["events_seen"] += cycle_published
        self.stats["revisions"] += cycle_revisions

        rev_note = f", {cycle_revisions} revised" if cycle_revisions else ""
        print(f"  [{ts}] Cycle complete: {cycle_published} published, "
              f"{cycle_skipped} skipped{rev_note}, {cycle_errors} errors")

        # Prune stale entries — keep only events seen in the last 48 hours
        # (all_day feed has at most 24h of events, 48h gives margin for slow revisions)
        cutoff_ms = int(time.time() * 1000) - (48 * 3600 * 1000)
        stale = [k for k, v in self._seen.items() if v < cutoff_ms]
        if stale:
            for k in stale:
                del self._seen[k]
            print(f"    Pruned {len(stale)} stale entries from dedupe cache "
                  f"({len(self._seen)} remaining)")

        return cycle_published

    def run(self, *, interval: float = 60.0, dry_run: bool = False, once: bool = False):
        """Main publisher loop."""
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  Feed URL:  {self.feed_url}")
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
        print(f"  Events seen:   {self.stats['events_seen']}")
        print(f"  Revisions:     {self.stats['revisions']}")
        print(f"  Skipped:       {self.stats['skipped']} (unchanged / invalid)")
        print(f"  Errors:        {self.stats['errors']}")
        print(f"  Reconnects:    {self.stats['reconnects']}")
        print(f"  Dedupe cache:  {len(self._seen)} entries")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="USGS Earthquake Feed publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=60.0,
                        help="Seconds between publish cycles (default: 60)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    args = parser.parse_args()

    publisher = USGSEarthquakePublisher()
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
