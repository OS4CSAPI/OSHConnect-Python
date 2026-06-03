#!/usr/bin/env python3
"""Publish Storebaelt webcam image-reference observations."""

import argparse
import base64
import email.utils
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


USER_AGENT = "OS4CSAPI Storebaelt Webcams Publisher/1.0"
DS_OUTPUT_NAME = "storebaeltWebcamImage"
DEFAULT_STALE_SECONDS = 15 * 60


def _load_cameras() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "cameras.json"), encoding="utf-8") as file:
        return json.load(file)["cameras"]


def _normalize_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _system_uid(camera_id: str) -> str:
    return f"urn:os4csapi:system:storebaelt-webcam:{camera_id}:v1"


def _parse_http_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _probe_image_url(url: str) -> dict:
    headers = {
        "Accept": "image/jpeg,*/*;q=0.8",
        "User-Agent": USER_AGENT,
    }
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        image_bytes = resp.read()
        return {
            "ok": True,
            "status": resp.status,
            "headers": dict(resp.headers),
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "byteLength": len(image_bytes),
        }


def fetch_latest_image(camera: dict) -> dict | None:
    poster_url = _normalize_url(camera["posterUrl"])
    player_url = _normalize_url(camera["playerUrl"])
    page_url = _normalize_url(camera["pageUrl"])
    try:
        probe = _probe_image_url(poster_url)
    except Exception as exc:
        print(f"    [WARN] Storebaelt webcam probe failed for {camera['id']}: {exc}")
        return None

    headers = probe.get("headers", {})
    content_type = headers.get("Content-Type") or headers.get("content-type") or "image/jpeg"
    last_modified = headers.get("Last-Modified") or headers.get("last-modified")
    etag = headers.get("ETag") or headers.get("etag") or ""
    content_length = headers.get("Content-Length") or headers.get("content-length") or ""
    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_last_modified = _parse_http_date(last_modified) or ""
    byte_length = str(probe.get("byteLength") or content_length or "")
    image_sha256 = str(probe.get("sha256") or "")
    dedupe_token = image_sha256 or etag or byte_length or captured_at

    return {
        "phenomenonTime": captured_at,
        "result": {
            "cameraId": camera["id"],
            "cameraTitle": camera["title"],
            "locationName": camera["locationName"],
            "imageUrl": poster_url,
            "latestImageUrl": poster_url,
            "posterUrl": poster_url,
            "thumbUrl": poster_url,
            "playerUrl": player_url,
            "pageUrl": page_url,
            "mediaType": content_type.split(";", 1)[0].strip() or "image/jpeg",
            "sourceType": "poster-image",
            "live": True,
            "httpStatus": int(probe.get("status") or 0),
            "etag": etag,
            "lastModified": last_modified or "",
            "sourceLastModifiedTime": source_last_modified,
            "contentLength": byte_length,
            "imageSha256": image_sha256,
            "sourceUrl": poster_url,
        },
        "dedupeKey": f"{camera['id']}|{dedupe_token}",
    }


class StorebaeltWebcamsPublisher:
    name = "Storebaelt Webcams Publisher"

    def __init__(self, camera_filter: list[str] | None = None):
        self.cameras = _load_cameras()
        if camera_filter:
            wanted = {item.strip() for item in camera_filter if item.strip()}
            self.cameras = [camera for camera in self.cameras if camera["id"] in wanted]

        self.osh_address = os.environ.get("OSH_ADDRESS", "")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "")
        self.osh_pass = os.environ.get("OSH_PASS", "")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit("ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.")

        self._base_url = os.environ.get("OSH_BASE_URL", f"https://{self.osh_address}/{self.osh_root}/api")
        self._auth = "Basic " + base64.b64encode(f"{self.osh_user}:{self.osh_pass}".encode()).decode()
        self._ds_ids: dict[str, str] = {}
        self._image_state: dict[str, dict] = {}
        self._request_delay = float(os.environ.get("STOREBAELT_WEBCAMS_REQUEST_DELAY", "0.5"))
        self._stale_seconds = int(os.environ.get("STOREBAELT_WEBCAMS_STALE_SECONDS", str(DEFAULT_STALE_SECONDS)))
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def connect(self):
        self._ds_ids.clear()
        connected = 0
        for camera in self.cameras:
            sys_id = find_by_uid(self._base_url, self._auth, "systems", _system_uid(camera["id"]), no_cache=True)
            if not sys_id:
                print(f"  [WARN] System not found for Storebaelt camera {camera['id']}")
                continue
            ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
            datastreams = {item.get("outputName", ""): item.get("id") for item in (ds_list or {}).get("items", [])}
            ds_id = datastreams.get(DS_OUTPUT_NAME)
            if not ds_id:
                print(f"  [WARN] Datastream {DS_OUTPUT_NAME} not found for camera {camera['id']}")
                continue
            self._ds_ids[camera["id"]] = ds_id
            self._seed_image_state(camera["id"], ds_id)
            connected += 1
            print(f"  Connected: {camera['id']} -> sys={sys_id} ds={ds_id}")
        print(f"  Ready: {connected}/{len(self.cameras)} cameras connected")
        if connected == 0:
            raise RuntimeError("No Storebaelt webcams connected")

    def connect_with_retry(self, max_attempts=10, base_delay=5.0, max_delay=120.0):
        for attempt in range(1, max_attempts + 1):
            try:
                return self.connect()
            except Exception as exc:
                if attempt == max_attempts:
                    raise
                wait = min(base_delay * (2 ** (attempt - 1)), max_delay) + random.random()
                print(f"  [WARN] Attempt {attempt}/{max_attempts} failed: {exc}; retrying in {wait:.1f}s")
                time.sleep(wait)

    def _post_observation(self, ds_id: str, obs: dict):
        url = f"{self._base_url}/datastreams/{ds_id}/observations"
        body = json.dumps(obs).encode()
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": self._auth,
                "Host": self.osh_address,
            },
        )
        try:
            with urlopen(req, timeout=30, context=ctx) as resp:
                if resp.status not in (200, 201, 204):
                    raise RuntimeError(f"HTTP {resp.status} POST {url}")
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"HTTP {exc.code} POST {url}: {body_text}") from exc

    def _seed_image_state(self, camera_id: str, ds_id: str):
        try:
            data = api_get(self._base_url, f"datastreams/{ds_id}/observations?limit=1&resultTime=latest", self._auth)
        except Exception as exc:
            print(f"  [WARN] Could not seed freshness state for {camera_id}: {exc}")
            return
        items = (data or {}).get("items") or []
        if not items:
            return
        obs = items[0]
        result = obs.get("result") or {}
        image_sha256 = result.get("imageSha256") or ""
        if not image_sha256:
            return
        observed_time = obs.get("phenomenonTime") or obs.get("resultTime") or _format_utc(datetime.now(timezone.utc))
        first_seen = result.get("firstSeenTime") or result.get("lastChangedTime") or observed_time
        last_changed = result.get("lastChangedTime") or first_seen
        last_seen = result.get("lastSeenTime") or observed_time
        self._image_state[camera_id] = {
            "imageSha256": image_sha256,
            "firstSeenTime": first_seen,
            "lastChangedTime": last_changed,
            "lastSeenTime": last_seen,
            "unchangedPollCount": int(result.get("unchangedPollCount") or 0),
        }

    def _apply_freshness_status(self, camera_id: str, latest: dict, poll_time: datetime) -> dict:
        result = dict(latest["result"])
        poll_time_iso = latest["phenomenonTime"]
        effective_poll_time = _parse_iso_utc(poll_time_iso) or poll_time
        image_sha256 = result.get("imageSha256") or latest["dedupeKey"].split("|", 1)[-1]
        previous = self._image_state.get(camera_id)
        image_changed = not previous or previous.get("imageSha256") != image_sha256

        if image_changed:
            first_seen = poll_time_iso
            last_changed = poll_time_iso
            unchanged_count = 0
        else:
            first_seen = previous.get("firstSeenTime") or poll_time_iso
            last_changed = previous.get("lastChangedTime") or first_seen
            unchanged_count = int(previous.get("unchangedPollCount") or 0) + 1

        last_changed_dt = _parse_iso_utc(last_changed) or effective_poll_time
        source_age_seconds = max(0, int((effective_poll_time - last_changed_dt).total_seconds()))
        if image_changed:
            staleness_status = "fresh"
        elif source_age_seconds >= self._stale_seconds:
            staleness_status = "stale"
        else:
            staleness_status = "unchanged"

        result.update({
            "imageChanged": image_changed,
            "firstSeenTime": first_seen,
            "lastSeenTime": poll_time_iso,
            "lastChangedTime": last_changed,
            "unchangedPollCount": unchanged_count,
            "stalenessStatus": staleness_status,
            "sourceAgeSeconds": source_age_seconds,
        })
        self._image_state[camera_id] = {
            "imageSha256": image_sha256,
            "firstSeenTime": first_seen,
            "lastChangedTime": last_changed,
            "lastSeenTime": poll_time_iso,
            "unchangedPollCount": unchanged_count,
        }
        latest = dict(latest)
        latest["result"] = result
        return latest

    def publish_cycle(self, dry_run: bool = False) -> int:
        published = 0
        now = datetime.now(timezone.utc)
        ts_label = now.strftime("%H:%M:%S")
        for camera in self.cameras:
            camera_id = camera["id"]
            ds_id = self._ds_ids.get(camera_id)
            if not dry_run and not ds_id:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {camera_id}: no datastream")
                continue
            latest = fetch_latest_image(camera)
            if not latest:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {camera_id}: no image metadata")
                continue
            latest = self._apply_freshness_status(camera_id, latest, now)
            obs = {
                "phenomenonTime": latest["phenomenonTime"],
                "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "result": latest["result"],
            }
            status = latest["result"].get("stalenessStatus", "unknown")
            changed = "changed" if latest["result"].get("imageChanged") else "unchanged"
            age = latest["result"].get("sourceAgeSeconds", 0)
            label = f"{latest['phenomenonTime']} {changed}/{status} age={age}s {latest['result']['imageUrl']}"
            if dry_run:
                print(f"  [{ts_label}] {camera_id}: [DRY] {label}")
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    print(f"  [{ts_label}] {camera_id}: OK {label}")
                except Exception as exc:
                    self.stats["errors"] += 1
                    print(f"  [{ts_label}] {camera_id}: ERR {exc}")
            time.sleep(self._request_delay)
        return published

    def run(self, *, interval: float = 300.0, dry_run: bool = False, once: bool = False):
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  Cameras:   {len(self.cameras)} ({', '.join(c['id'] for c in self.cameras)})")
        print(f"  Interval:  {interval}s")
        print(f"  Dry run:   {dry_run}\n")
        if not dry_run:
            print("  Connecting to OSH server...")
            self.connect_with_retry()
        tick = 0
        start_time = time.time()
        try:
            while True:
                tick += 1
                print(f"\n  -- Cycle #{tick} --")
                self.publish_cycle(dry_run=dry_run)
                if once:
                    break
                sleep_time = start_time + tick * interval - time.time()
                if sleep_time > 0:
                    print(f"  Sleeping {sleep_time:.0f}s until next cycle...")
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n\n  Ctrl+C -- stopping publisher.")
        print("\n" + "=" * 70)
        print(f"  Published:  {self.stats['published']}")
        print(f"  Skipped:    {self.stats['skipped']}")
        print(f"  Errors:     {self.stats['errors']}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Storebaelt webcam publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=300.0, help="Seconds between publish cycles")
    parser.add_argument("--dry-run", action="store_true", help="Print observations but do not POST them")
    parser.add_argument("--once", action="store_true", help="Publish one cycle then exit")
    parser.add_argument("--cameras", type=str, default=None, help="Comma-separated camera IDs to publish")
    args = parser.parse_args()
    camera_filter = args.cameras.split(",") if args.cameras else None
    StorebaeltWebcamsPublisher(camera_filter=camera_filter).run(interval=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()
