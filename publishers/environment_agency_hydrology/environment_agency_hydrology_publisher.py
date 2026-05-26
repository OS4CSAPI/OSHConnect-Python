#!/usr/bin/env python3
"""
environment_agency_hydrology_publisher.py -- Environment Agency Hydrology
observation publisher for CSAPI/OSH.

Fetches the latest readings for curated Environment Agency measures from
stations.json and publishes one CSAPI observation per changed reading.
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
from urllib.parse import quote
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import api_get, find_by_uid


EA_READINGS_URL = "https://environment.data.gov.uk/hydrology/data/readings.json"


class UpstreamRateLimit(RuntimeError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def _retry_after_seconds(error: HTTPError) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers else None
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as f:
        return json.load(f)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-")


def _latest_reading_url(measure_uri: str) -> str:
    return f"{EA_READINGS_URL}?measure={quote(measure_uri, safe='')}&latest=true&_limit=1"


def _parse_source_time(raw_time: str) -> tuple[float, str]:
    if not raw_time:
        raise ValueError("missing dateTime")
    normalized = raw_time.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.timestamp(), dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_latest_reading(station: dict, measure: dict) -> dict | None:
    """Fetch and normalize the latest Environment Agency reading for one measure."""
    url = _latest_reading_url(measure["measureUri"])
    req = Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "OS4CSAPI Environment Agency Hydrology Publisher/1.0",
    })

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code == 429:
            raise UpstreamRateLimit(
                f"HTTP 429 Too Many Requests for {measure['measureNotation']}",
                _retry_after_seconds(exc),
            ) from exc
        raise
    except Exception as exc:
        print(f"    [WARN] EA fetch failed for {measure['measureNotation']}: {exc}")
        return None

    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    value = _as_float(item.get("value"))
    if value is None:
        return None

    timestamp, phenomenon_time = _parse_source_time(item.get("dateTime", ""))
    result_field = measure.get("resultField", "value")
    result = {
        "stationId": station["stationNotation"],
        "measureId": measure["measureNotation"],
        "parameter": measure["parameter"],
        result_field: value,
        "unit": measure["unit"],
        "valueType": measure.get("valueType", ""),
        "quality": str(item.get("quality", "")),
        "completeness": str(item.get("completeness", "")),
        "sourceUrl": url,
    }

    return {
        "timestamp": timestamp,
        "phenomenonTime": phenomenon_time,
        "date": item.get("date", ""),
        "value": value,
        "resultField": result_field,
        "result": result,
        "dedupeKey": (
            f"{measure['measureNotation']}|{phenomenon_time}|{value}|"
            f"{result['quality']}|{result['completeness']}"
        ),
    }


class EnvironmentAgencyHydrologyPublisher:
    name = "Environment Agency Hydrology Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        self.stations = _load_stations()
        if station_filter:
            wanted = set(s.strip() for s in station_filter if s.strip())
            self.stations = [s for s in self.stations if s["stationNotation"] in wanted]

        self.osh_address = os.environ.get("OSH_ADDRESS", "")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "")
        self.osh_pass = os.environ.get("OSH_PASS", "")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit(
                "ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.\n"
                "  Copy publishers/.env.example -> .env and set your server details."
            )

        self._base_url = os.environ.get(
            "OSH_BASE_URL",
            f"https://{self.osh_address}/{self.osh_root}/api",
        )
        self._is_go_server = "csapi-go" in self._base_url
        self._auth = "Basic " + base64.b64encode(
            f"{self.osh_user}:{self.osh_pass}".encode()).decode()

        self._ds_ids: dict[str, dict[str, str]] = {}
        self._seen: set[str] = set()
        self._ea_cooldown_until = 0.0
        self._request_delay = float(os.environ.get("EA_HYDROLOGY_REQUEST_DELAY", "1.0"))
        self._rate_limit_backoff = float(os.environ.get("EA_HYDROLOGY_429_BACKOFF", "900"))
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def _system_uid(self, station_notation: str) -> str:
        return f"urn:os4csapi:system:environment-agency-hydrology:{_uid_token(station_notation)}:v1"

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
        """Resolve station systems and datastream IDs by UID/outputName."""
        self._ds_ids.clear()
        connected = 0

        for station in self.stations:
            notation = station["stationNotation"]
            uid = self._system_uid(notation)
            sys_id = None
            station_ds: dict[str, str] = {}
            try:
                sys_id = find_by_uid(self._base_url, self._auth, "systems", uid, no_cache=True)
                if not sys_id:
                    print(f"  [WARN] System '{uid}' not found -- skipping {notation}")
                    continue

                ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
                if ds_list:
                    for item in ds_list.get("items", []):
                        output_name = item.get("outputName", "")
                        ds_id = item.get("id")
                        if output_name and ds_id:
                            station_ds[output_name] = ds_id
            except Exception as exc:
                if sys_id:
                    station_ds = self._raw_datastream_ids(sys_id)
                    if station_ds:
                        print(f"  [WARN] Used raw datastream fallback for {notation}: {exc}")
                    else:
                        print(f"  [WARN] Could not resolve datastreams for {notation}: {exc}")
                        continue
                else:
                    print(f"  [WARN] Could not resolve system for {notation}: {exc}")
                    continue

            expected = {m["outputName"] for m in station.get("measures", [])}
            missing = sorted(expected - set(station_ds))
            if missing:
                print(f"  [WARN] Missing datastreams for {notation}: {', '.join(missing)}")

            self._ds_ids[notation] = station_ds
            connected += 1
            ds_summary = ", ".join(f"{k}->{v}" for k, v in station_ds.items())
            print(f"  Connected: {notation} -> sys={sys_id} ds=[{ds_summary}]")

        print(f"  Ready: {connected}/{len(self.stations)} stations connected")
        if connected == 0:
            raise RuntimeError("No Environment Agency Hydrology stations connected")

    def connect_with_retry(self, max_attempts=10, base_delay=5.0, max_delay=120.0):
        for attempt in range(1, max_attempts + 1):
            try:
                return self.connect()
            except Exception as exc:
                if attempt == max_attempts:
                    raise
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                jitter = delay * 0.2 * (random.random() - 0.5)
                wait = delay + jitter
                print(f"  [WARN] Attempt {attempt}/{max_attempts} failed: {exc}")
                print(f"         Retrying in {wait:.1f}s...")
                time.sleep(wait)

    def _post_observation(self, ds_id: str, obs: dict):
        if self._is_go_server:
            result = obs.get("result", {})
            if "timestamp" not in result:
                result["timestamp"] = obs.get("phenomenonTime", "")
            elif not isinstance(result["timestamp"], str):
                result["timestamp"] = str(result["timestamp"])

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
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"HTTP {exc.code} POST {url}: {body_text}") from exc

    def publish_cycle(self, dry_run: bool = False) -> int:
        published = 0
        now = datetime.now(timezone.utc)
        ts_label = now.strftime("%H:%M:%S")

        for station in self.stations:
            notation = station["stationNotation"]
            station_ds = self._ds_ids.get(notation, {})

            for measure in station.get("measures", []):
                cooldown_remaining = self._ea_cooldown_until - time.time()
                if cooldown_remaining > 0:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] EA cooldown active; skipping fetches for {cooldown_remaining:.0f}s")
                    return published

                ds_id = station_ds.get(measure["outputName"])
                if ds_id is None and not dry_run:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {notation}/{measure['outputName']}: no datastream")
                    continue

                try:
                    latest = fetch_latest_reading(station, measure)
                except UpstreamRateLimit as exc:
                    backoff = exc.retry_after or self._rate_limit_backoff
                    self._ea_cooldown_until = time.time() + backoff
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] RATE LIMITED; backing off {backoff:.0f}s")
                    return published
                except Exception as exc:
                    self.stats["errors"] += 1
                    print(f"  [{ts_label}] {notation}/{measure['outputName']}: FETCH ERR {exc}")
                    continue

                if not latest:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {notation}/{measure['outputName']}: no data")
                    continue

                dedupe_key = latest["dedupeKey"]
                if dedupe_key in self._seen:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {notation}/{measure['outputName']}: unchanged, skipping")
                    continue

                obs = {
                    "phenomenonTime": latest["phenomenonTime"],
                    "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "result": latest["result"],
                }

                value_label = f"{latest['resultField']}={latest['value']} {measure['unit']}"
                if dry_run:
                    print(f"  [{ts_label}] {notation}/{measure['outputName']}: [DRY] {value_label} @ {latest['phenomenonTime']}")
                    self._seen.add(dedupe_key)
                else:
                    try:
                        self._post_observation(ds_id, obs)
                        self.stats["published"] += 1
                        published += 1
                        self._seen.add(dedupe_key)
                        print(f"  [{ts_label}] {notation}/{measure['outputName']}: OK  {value_label}")
                    except Exception as exc:
                        self.stats["errors"] += 1
                        print(f"  [{ts_label}] {notation}/{measure['outputName']}: ERR {exc}")

                time.sleep(self._request_delay)

        return published

    def run(self, *, interval: float = 900.0, dry_run: bool = False, once: bool = False):
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  Stations:  {len(self.stations)} ({', '.join(s['stationNotation'] for s in self.stations)})")
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
                print(f"  -- Cycle #{tick} --")
                try:
                    count = self.publish_cycle(dry_run=dry_run)
                    if count > 0 or dry_run:
                        consecutive_errors = 0
                    else:
                        consecutive_errors += 1
                except Exception as exc:
                    print(f"  [ERR] Cycle failed: {exc}")
                    consecutive_errors += 1
                    self.stats["errors"] += 1

                if consecutive_errors >= 5 and not dry_run:
                    print("  [WARN] Reconnecting...")
                    try:
                        self.connect_with_retry()
                        self.stats["reconnects"] += 1
                        consecutive_errors = 0
                    except Exception as exc:
                        print(f"  [ERR] Reconnect failed: {exc}")

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
        print(f"  Skipped:    {self.stats['skipped']} (unchanged/empty/missing)")
        print(f"  Errors:     {self.stats['errors']}")
        print(f"  Reconnects: {self.stats['reconnects']}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Environment Agency Hydrology publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=900.0,
                        help="Seconds between publish cycles (default: 900 = 15min)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but do not POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    parser.add_argument("--stations", type=str, default=None,
                        help="Comma-separated Environment Agency station notations to publish")
    args = parser.parse_args()

    station_filter = args.stations.split(",") if args.stations else None
    publisher = EnvironmentAgencyHydrologyPublisher(station_filter=station_filter)
    publisher.run(interval=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()
