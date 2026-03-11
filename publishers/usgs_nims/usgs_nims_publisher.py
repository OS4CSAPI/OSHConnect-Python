#!/usr/bin/env python3
"""
usgs_nims_publisher.py — USGS NIMS gaging-station imagery publisher for CSAPI/OSH.

Polls each camera's latest image via the NIMS v0 /listFiles API, extracts the
timestamp from the filename, constructs S3-hosted image URLs for overlay/thumb/720px
resolutions, and publishes image-reference observations.

Camera list is read from cameras.json (same directory).
Imagery datastreams live on the existing USGS water station systems (Pattern A).

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (default: os4csapi-osh.duckdns.org)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (default: os4csapi)
    OSH_PASS           Auth password              (default: ogc134mm)
    USGS_API_KEY       USGS API key               (optional, improves rate limits)

Usage:
    python -m publishers.usgs_nims.usgs_nims_publisher                      # run forever (15min)
    python -m publishers.usgs_nims.usgs_nims_publisher --dry-run            # print only
    python -m publishers.usgs_nims.usgs_nims_publisher --once               # single cycle
    python -m publishers.usgs_nims.usgs_nims_publisher --interval 300       # 5min cadence
    python -m publishers.usgs_nims.usgs_nims_publisher --cameras 09380000,08171000  # subset by nwisId

Requires: Python 3.10+, no external dependencies beyond stdlib.
"""

import argparse
import base64
import json
import os
import random
import re
import ssl
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

NIMS_API_BASE = "https://api.waterdata.usgs.gov/nims/v0"
DS_OUTPUT_NAME = "usgsNimsImage"

# Regex to extract timestamp from NIMS filename:
#   {camId}___YYYY-MM-DDTHH-mm-ssZ.jpg
FILENAME_TS_RE = re.compile(r"___(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})Z\.jpg$")


def _load_cameras() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "cameras.json")) as f:
        return json.load(f)["cameras"]


def _parse_filename_timestamp(filename: str) -> datetime | None:
    """Extract UTC datetime from a NIMS image filename.

    Filename format: {camId}___YYYY-MM-DDTHH-mm-ssZ.jpg
    """
    m = FILENAME_TS_RE.search(filename)
    if not m:
        return None
    raw = m.group(1)  # e.g. "2026-03-11T23-15-02"
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H-%M-%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  NIMS API fetch helpers
# ═══════════════════════════════════════════════════════════════════════════

def fetch_latest_image(cam: dict, api_key: str | None = None) -> dict | None:
    """Fetch the most recent image filename for a camera and construct URLs.

    Returns a dict with: imageTime (datetime), filename, imageUrl, thumbUrl, smallUrl,
    timeLapseUrl, mediaType, or None on failure.
    """
    cam_id = cam["camId"]
    url = f"{NIMS_API_BASE}/listFiles?camId={cam_id}&limit=1&recent=true"
    if api_key:
        url += f"&apiKey={api_key}"

    headers = {"Accept": "application/json"}
    req = Request(url, headers=headers)

    try:
        with urlopen(req, timeout=20) as resp:
            files = json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    except Exception as e:
        print(f"    [WARN] NIMS listFiles failed for {cam_id}: {e}")
        return None

    if not files or not isinstance(files, list) or len(files) == 0:
        return None

    filename = files[0]
    image_time = _parse_filename_timestamp(filename)
    if image_time is None:
        print(f"    [WARN] Cannot parse timestamp from filename: {filename}")
        return None

    # Construct URLs from camera directory paths
    overlay_dir = cam.get("overlayDir", "")
    thumb_dir = cam.get("thumbDir", "")
    small_dir = cam.get("smallDir", "")

    result = {
        "imageTime": image_time,
        "filename": filename,
        "imageUrl": f"{overlay_dir}{filename}",
        "thumbUrl": f"{thumb_dir}{filename}",
        "smallUrl": f"{small_dir}{filename}",
        "mediaType": "image/jpeg",
    }

    # Add timelapse URL if enabled
    if cam.get("TL_enabled"):
        tl_dir = cam.get("tlDir", "")
        result["timeLapseUrl"] = f"{tl_dir}{cam_id}_720.mp4"
    else:
        result["timeLapseUrl"] = ""

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  Publisher
# ═══════════════════════════════════════════════════════════════════════════

class USGSNimsPublisher:
    """Multi-camera USGS NIMS imagery publisher.

    Connects to one imagery datastream per camera (on existing water station systems),
    publishes image-reference observations each cycle.
    """

    name = "USGS NIMS Imagery Publisher"

    def __init__(self, camera_filter: list[str] | None = None):
        self.cameras = _load_cameras()
        if camera_filter:
            filt = set(camera_filter)
            self.cameras = [c for c in self.cameras if c["nwisId"] in filt]

        self.osh_address = os.environ.get("OSH_ADDRESS", "os4csapi-osh.duckdns.org")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "os4csapi")
        self.osh_pass = os.environ.get("OSH_PASS", "ogc134mm")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        self.api_key = os.environ.get("USGS_API_KEY", None)

        # nwisId → imagery datastream server ID
        self._ds_ids: dict[str, str] = {}
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

        # Track last image filename per camera to avoid duplicate publishes
        self._last_filename: dict[str, str] = {}

        # REST config
        self._base_url = f"https://{self.osh_address}/{self.osh_root}/api"
        self._auth = "Basic " + base64.b64encode(
            f"{self.osh_user}:{self.osh_pass}".encode()).decode()

    def _system_uid(self, nwis_id: str) -> str:
        return f"urn:os4csapi:system:usgs-water:{nwis_id}:v1"

    def connect(self):
        """Resolve system and imagery datastream IDs for each camera via REST API."""
        connected = 0
        for cam in self.cameras:
            nwis_id = cam["nwisId"]
            uid = self._system_uid(nwis_id)
            sys_id = find_by_uid(self._base_url, self._auth, "systems", uid)
            if not sys_id:
                print(f"  [WARN] System '{uid}' not found — skipping {nwis_id}")
                continue

            # Find imagery datastream
            ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
            ds_id = None
            if ds_list:
                for item in ds_list.get("items", []):
                    if item.get("outputName") == DS_OUTPUT_NAME:
                        ds_id = item.get("id")
                        break

            if not ds_id:
                print(f"  [WARN] Datastream '{DS_OUTPUT_NAME}' not found for "
                      f"{nwis_id} — skipping")
                continue

            self._ds_ids[nwis_id] = ds_id
            connected += 1
            print(f"  Connected: {nwis_id} ({cam['camId']}) → sys={sys_id} ds={ds_id}")

        print(f"  Ready: {connected}/{len(self.cameras)} cameras connected")

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
        """POST an observation to the server."""
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
        """Fetch + publish imagery observations for all cameras. Returns count published."""
        published = 0
        now = datetime.now(timezone.utc)
        ts_label = now.strftime("%H:%M:%S")

        for cam in self.cameras:
            nwis_id = cam["nwisId"]
            cam_id = cam["camId"]
            ds_id = self._ds_ids.get(nwis_id)
            if ds_id is None and not dry_run:
                continue

            # Fetch latest image from NIMS
            try:
                img = fetch_latest_image(cam, api_key=self.api_key)
            except Exception as e:
                self.stats["errors"] += 1
                print(f"  [{ts_label}] {nwis_id}/{cam_id}: FETCH ERR {e}")
                continue

            if img is None:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {nwis_id}/{cam_id}: no image available")
                continue

            # Skip if same filename as last cycle (image hasn't changed)
            if img["filename"] == self._last_filename.get(nwis_id):
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {nwis_id}/{cam_id}: unchanged, skipping")
                continue

            # Build observation envelope
            image_time: datetime = img["imageTime"]
            phenomenon_time = image_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            result = {
                "stationId": nwis_id,
                "camId": cam_id,
                "imageUrl": img["imageUrl"],
                "thumbUrl": img["thumbUrl"],
                "smallUrl": img["smallUrl"],
                "mediaType": img["mediaType"],
                "filename": img["filename"],
                "timeLapseUrl": img.get("timeLapseUrl", ""),
            }

            obs = {
                "phenomenonTime": phenomenon_time,
                "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": result,
            }

            if dry_run:
                print(f"  [{ts_label}] {nwis_id}/{cam_id}: [DRY] {img['filename']}")
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    self._last_filename[nwis_id] = img["filename"]
                    print(f"  [{ts_label}] {nwis_id}/{cam_id}: OK  {img['filename']}")
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  [{ts_label}] {nwis_id}/{cam_id}: ERR {e}")

            # Be polite to NIMS API
            time.sleep(0.5)

        return published

    def run(self, *, interval: float = 900.0, dry_run: bool = False, once: bool = False):
        """Main publisher loop."""
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    https://{self.osh_address}:{self.osh_port}/{self.osh_root}/api")
        print(f"  Cameras:   {len(self.cameras)} ({', '.join(c['nwisId'] for c in self.cameras)})")
        print(f"  Interval:  {interval}s")
        print(f"  API key:   {'set' if self.api_key else 'not set'}")
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
                print(f"  -- Cycle #{tick} --")

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
            print("\n\n  Ctrl+C -- stopping publisher.")

        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print(f"  Summary ({elapsed:.0f}s elapsed)")
        print(f"  Published:  {self.stats['published']}")
        print(f"  Skipped:    {self.stats['skipped']} (unchanged/no image)")
        print(f"  Errors:     {self.stats['errors']}")
        print(f"  Reconnects: {self.stats['reconnects']}")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="USGS NIMS gaging-station imagery publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=900.0,
                        help="Seconds between publish cycles (default: 900 = 15min)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    parser.add_argument("--cameras", type=str, default=None,
                        help="Comma-separated NWIS site IDs to publish (default: all from cameras.json)")
    args = parser.parse_args()

    camera_filter = args.cameras.split(",") if args.cameras else None
    publisher = USGSNimsPublisher(camera_filter=camera_filter)
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
