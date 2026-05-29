#!/usr/bin/env python3
"""Publish Finnish Digitraffic weather camera image-reference observations."""

import argparse
import base64
import gzip
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


USER_AGENT = "OS4CSAPI Digitraffic Weathercam Publisher/1.0"
DS_OUTPUT_NAME = "digitrafficWeatherCamImage"


def _load_cameras() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "cameras.json"), encoding="utf-8") as file:
        return json.load(file)["cameras"]


def _system_uid(road_weather_station_id: str) -> str:
    return f"urn:os4csapi:system:digitraffic-road-weather:{road_weather_station_id}:v1"


def _station_data_url(camera_station_id: str) -> str:
    return f"https://tie.digitraffic.fi/api/weathercam/v1/stations/{camera_station_id}/data"


def _image_url(preset_id: str) -> str:
    return f"https://weathercam.digitraffic.fi/{preset_id}.jpg"


def _thumb_url(preset_id: str) -> str:
    return f"{_image_url(preset_id)}?thumbnail=true"


def _parse_time(value: str) -> tuple[float, str]:
    if not value:
        raise ValueError("missing timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.timestamp(), dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_json(url: str) -> dict:
    req = Request(url, headers={"Accept": "application/json", "Accept-Encoding": "gzip", "User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding", "").lower() == "gzip":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def fetch_latest_image(camera: dict) -> dict | None:
    source_url = _station_data_url(camera["cameraStationId"])
    try:
        data = _get_json(source_url)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except Exception as exc:
        print(f"    [WARN] Digitraffic weathercam fetch failed for {camera['cameraStationId']}: {exc}")
        return None

    presets = data.get("presets") or []
    preset = next((item for item in presets if item.get("id") == camera["presetId"]), None)
    if not preset:
        return None

    _, phenomenon_time = _parse_time(preset.get("measuredTime") or data.get("dataUpdatedTime"))
    preset_id = camera["presetId"]
    image_url = _image_url(preset_id)
    return {
        "phenomenonTime": phenomenon_time,
        "result": {
            "stationId": camera["roadWeatherStationId"],
            "camId": preset_id,
            "imageUrl": image_url,
            "thumbUrl": _thumb_url(preset_id),
            "latestImageUrl": image_url,
            "mediaType": "image/jpeg",
            "sourceUrl": source_url,
        },
        "dedupeKey": f"{camera['roadWeatherStationId']}|{preset_id}|{phenomenon_time}",
    }


class DigitrafficWeathercamPublisher:
    name = "Digitraffic Weathercam Publisher"

    def __init__(self, camera_filter: list[str] | None = None):
        self.cameras = _load_cameras()
        if camera_filter:
            wanted = {item.strip() for item in camera_filter if item.strip()}
            self.cameras = [camera for camera in self.cameras if camera["presetId"] in wanted or camera["roadWeatherStationId"] in wanted]

        self.osh_address = os.environ.get("OSH_ADDRESS", "")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "")
        self.osh_pass = os.environ.get("OSH_PASS", "")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit("ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.")

        self._base_url = os.environ.get("OSH_BASE_URL", f"https://{self.osh_address}/{self.osh_root}/api")
        self._is_go_server = "csapi-go" in self._base_url
        self._auth = "Basic " + base64.b64encode(f"{self.osh_user}:{self.osh_pass}".encode()).decode()
        self._ds_ids: dict[str, str] = {}
        self._seen: set[str] = set()
        self._request_delay = float(os.environ.get("DIGITRAFFIC_WEATHERCAM_REQUEST_DELAY", "0.5"))
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def _raw_datastream_ids(self, sys_id: str) -> dict[str, str]:
        url = f"{self._base_url}/systems/{sys_id}/datastreams"
        headers = {"Accept": "application/json", "Authorization": self._auth}
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(Request(url, headers=headers), timeout=30, context=ctx) as resp:
            text = resp.read().decode()
        datastreams: dict[str, str] = {}
        current_id = None
        for key, value in re.findall(r'"(id|outputName)"\s*:\s*"([^"]+)"', text):
            if key == "id":
                current_id = value
            elif key == "outputName" and current_id:
                datastreams[value] = current_id
                current_id = None
        return datastreams

    def connect(self):
        self._ds_ids.clear()
        connected = 0
        for camera in self.cameras:
            station_id = camera["roadWeatherStationId"]
            sys_id = find_by_uid(self._base_url, self._auth, "systems", _system_uid(station_id), no_cache=True)
            if not sys_id:
                print(f"  [WARN] System not found for road-weather station {station_id}")
                continue
            try:
                ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
                datastreams = {item.get("outputName", ""): item.get("id") for item in (ds_list or {}).get("items", [])}
            except Exception:
                datastreams = self._raw_datastream_ids(sys_id)
            ds_id = datastreams.get(DS_OUTPUT_NAME)
            if not ds_id:
                print(f"  [WARN] Datastream {DS_OUTPUT_NAME} not found for station {station_id}")
                continue
            self._ds_ids[camera["presetId"]] = ds_id
            connected += 1
            print(f"  Connected: {station_id}/{camera['presetId']} -> sys={sys_id} ds={ds_id}")
        print(f"  Ready: {connected}/{len(self.cameras)} cameras connected")
        if connected == 0:
            raise RuntimeError("No Digitraffic weather cameras connected")

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
        req = Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": self._auth, "Host": self.osh_address})
        try:
            with urlopen(req, timeout=30, context=ctx) as resp:
                if resp.status not in (200, 201, 204):
                    raise RuntimeError(f"HTTP {resp.status} POST {url}")
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"HTTP {exc.code} POST {url}: {body_text}") from exc

    def publish_cycle(self, dry_run: bool = False) -> int:
        published = 0
        now = datetime.now(timezone.utc)
        ts_label = now.strftime("%H:%M:%S")
        for camera in self.cameras:
            preset_id = camera["presetId"]
            ds_id = self._ds_ids.get(preset_id)
            if not dry_run and not ds_id:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {preset_id}: no datastream")
                continue
            try:
                latest = fetch_latest_image(camera)
            except Exception as exc:
                self.stats["errors"] += 1
                print(f"  [{ts_label}] {preset_id}: FETCH ERR {exc}")
                continue
            if not latest:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {preset_id}: no image metadata")
                continue
            if latest["dedupeKey"] in self._seen:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {preset_id}: unchanged, skipping")
                continue
            obs = {"phenomenonTime": latest["phenomenonTime"], "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": latest["result"]}
            label = f"{latest['phenomenonTime']} {latest['result']['imageUrl']}"
            if dry_run:
                print(f"  [{ts_label}] {preset_id}: [DRY] {label}")
                self._seen.add(latest["dedupeKey"])
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    self._seen.add(latest["dedupeKey"])
                    print(f"  [{ts_label}] {preset_id}: OK {label}")
                except Exception as exc:
                    self.stats["errors"] += 1
                    print(f"  [{ts_label}] {preset_id}: ERR {exc}")
            time.sleep(self._request_delay)
        return published

    def run(self, *, interval: float = 300.0, dry_run: bool = False, once: bool = False):
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  Cameras:   {len(self.cameras)} ({', '.join(c['presetId'] for c in self.cameras)})")
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
    parser = argparse.ArgumentParser(description="Digitraffic Weathercam publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=300.0, help="Seconds between publish cycles")
    parser.add_argument("--dry-run", action="store_true", help="Print observations but do not POST them")
    parser.add_argument("--once", action="store_true", help="Publish one cycle then exit")
    parser.add_argument("--cameras", type=str, default=None, help="Comma-separated preset IDs or road-weather station IDs to publish")
    args = parser.parse_args()
    camera_filter = args.cameras.split(",") if args.cameras else None
    DigitrafficWeathercamPublisher(camera_filter=camera_filter).run(interval=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()