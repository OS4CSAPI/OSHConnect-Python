#!/usr/bin/env python3
"""Publish curated Finnish Digitraffic road-weather observations to CSAPI/OSH."""

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


USER_AGENT = "OS4CSAPI Digitraffic Road Weather Publisher/1.0"


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as file:
        return json.load(file)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:digitraffic-road-weather:{_uid_token(station_id)}:v1"


def _station_data_url(station_id: str) -> str:
    return f"https://tie.digitraffic.fi/api/weather/v1/stations/{station_id}/data"


def _parse_time(value: str) -> tuple[float, str]:
    if not value:
        raise ValueError("missing timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.timestamp(), dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _sensor_map(sensor_values: list[dict]) -> dict[str, dict]:
    return {str(item.get("name", "")): item for item in sensor_values if item.get("name")}


def _numeric(sensor: dict | None):
    if not sensor:
        return None
    value = sensor.get("value")
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _source_sensor_payload(sensor_values: list[dict]) -> list[dict]:
    payload = []
    for item in sensor_values:
        payload.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "shortName": item.get("shortName"),
            "measuredTime": item.get("measuredTime"),
            "unit": item.get("unit"),
            "value": item.get("value"),
        })
    return payload


def fetch_latest_reading(station: dict) -> dict | None:
    url = _station_data_url(station["stationId"])
    req = Request(url, headers={"Accept": "application/json", "Accept-Encoding": "gzip", "User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except Exception as exc:
        print(f"    [WARN] Digitraffic fetch failed for {station['stationId']}: {exc}")
        return None

    sensor_values = data.get("sensorValues") or []
    if not sensor_values:
        return None

    _, phenomenon_time = _parse_time(data.get("dataUpdatedTime") or sensor_values[0].get("measuredTime"))
    sensors = _sensor_map(sensor_values)
    result = {
        "stationId": station["stationId"],
        "stationName": station["sourceName"],
        "airTemperature_c": _numeric(sensors.get("ILMA")),
        "roadSurfaceTemperature_c": _numeric(sensors.get("TIE_1")),
        "windSpeed_ms": _numeric(sensors.get("KESKITUULI")),
        "windDirection_deg": _numeric(sensors.get("TUULENSUUNTA")),
        "precipitation": _numeric(sensors.get("SADE")),
        "roadConditionCode": str(_numeric(sensors.get("KELI_1")) or ""),
        "warningCode": str(_numeric(sensors.get("VAROITUS_1")) or ""),
        "sensorValuesJson": json.dumps(_source_sensor_payload(sensor_values), ensure_ascii=False, separators=(",", ":")),
        "sourceUrl": url,
    }
    return {
        "phenomenonTime": phenomenon_time,
        "value": result["airTemperature_c"],
        "result": result,
        "dedupeKey": f"{station['stationId']}|{phenomenon_time}|{result['airTemperature_c']}|{result['roadSurfaceTemperature_c']}|{result['warningCode']}",
    }


class DigitrafficRoadWeatherPublisher:
    name = "Digitraffic Road Weather Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        self.stations = _load_stations()
        if station_filter:
            wanted = {item.strip() for item in station_filter if item.strip()}
            self.stations = [station for station in self.stations if station["stationId"] in wanted]

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
        self._request_delay = float(os.environ.get("DIGITRAFFIC_ROAD_WEATHER_REQUEST_DELAY", "0.5"))
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def _raw_datastream_ids(self, sys_id: str) -> dict[str, str]:
        url = f"{self._base_url}/systems/{sys_id}/datastreams"
        headers = {"Accept": "application/json", "Authorization": self._auth}
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(Request(url, headers=headers), timeout=30, context=ctx) as resp:
            text = resp.read().decode()
        station_ds: dict[str, str] = {}
        current_id = None
        for key, value in re.findall(r'"(id|outputName)"\s*:\s*"([^"]+)"', text):
            if key == "id":
                current_id = value
            elif key == "outputName" and current_id:
                station_ds[value] = current_id
                current_id = None
        return station_ds

    def connect(self):
        self._ds_ids.clear()
        connected = 0
        for station in self.stations:
            station_id = station["stationId"]
            sys_id = find_by_uid(self._base_url, self._auth, "systems", _system_uid(station_id), no_cache=True)
            if not sys_id:
                print(f"  [WARN] System not found for station {station_id}")
                continue
            try:
                ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
                datastreams = {item.get("outputName", ""): item.get("id") for item in (ds_list or {}).get("items", [])}
            except Exception:
                datastreams = self._raw_datastream_ids(sys_id)
            ds_id = datastreams.get("roadWeatherObs")
            if not ds_id:
                print(f"  [WARN] Datastream roadWeatherObs not found for station {station_id}")
                continue
            self._ds_ids[station_id] = ds_id
            connected += 1
            print(f"  Connected: {station_id} -> sys={sys_id} ds={ds_id}")
        print(f"  Ready: {connected}/{len(self.stations)} stations connected")
        if connected == 0:
            raise RuntimeError("No Digitraffic road-weather stations connected")

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
        if self._is_go_server:
            obs.setdefault("result", {}).setdefault("timestamp", obs.get("phenomenonTime", ""))
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
        for station in self.stations:
            station_id = station["stationId"]
            ds_id = self._ds_ids.get(station_id)
            if not dry_run and not ds_id:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {station_id}: no datastream")
                continue
            try:
                latest = fetch_latest_reading(station)
            except Exception as exc:
                self.stats["errors"] += 1
                print(f"  [{ts_label}] {station_id}: FETCH ERR {exc}")
                continue
            if not latest:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {station_id}: no data")
                continue
            if latest["dedupeKey"] in self._seen:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {station_id}: unchanged, skipping")
                continue
            obs = {"phenomenonTime": latest["phenomenonTime"], "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": latest["result"]}
            label = f"air={latest['result']['airTemperature_c']}C road={latest['result']['roadSurfaceTemperature_c']}C @ {latest['phenomenonTime']}"
            if dry_run:
                print(f"  [{ts_label}] {station_id}: [DRY] {label}")
                self._seen.add(latest["dedupeKey"])
            else:
                try:
                    self._post_observation(ds_id, obs)
                    self.stats["published"] += 1
                    published += 1
                    self._seen.add(latest["dedupeKey"])
                    print(f"  [{ts_label}] {station_id}: OK {label}")
                except Exception as exc:
                    self.stats["errors"] += 1
                    print(f"  [{ts_label}] {station_id}: ERR {exc}")
            time.sleep(self._request_delay)
        return published

    def run(self, *, interval: float = 300.0, dry_run: bool = False, once: bool = False):
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  Stations:  {len(self.stations)} ({', '.join(s['stationId'] for s in self.stations)})")
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
    parser = argparse.ArgumentParser(description="Digitraffic Road Weather publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=300.0, help="Seconds between publish cycles")
    parser.add_argument("--dry-run", action="store_true", help="Print observations but do not POST them")
    parser.add_argument("--once", action="store_true", help="Publish one cycle then exit")
    parser.add_argument("--stations", type=str, default=None, help="Comma-separated Digitraffic station IDs to publish")
    args = parser.parse_args()
    station_filter = args.stations.split(",") if args.stations else None
    DigitrafficRoadWeatherPublisher(station_filter=station_filter).run(interval=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()