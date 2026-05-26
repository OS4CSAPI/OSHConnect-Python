#!/usr/bin/env python3
"""
met_office_datahub_publisher.py -- Met Office Weather DataHub Land Observations
publisher for CSAPI/OSH.

Fetches recent hourly observations for curated UK lookup locations and publishes
one CSAPI observation per selected parameter.
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
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import api_get, find_by_uid


DEFAULT_API_BASE = "https://data.hub.api.metoffice.gov.uk/observation-land/1"
STATE_PATH = Path(__file__).with_name("state.json")


class UpstreamRateLimit(RuntimeError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


def _load_local_env():
    env_path = Path(os.environ.get("PUBLISHERS_ENV_FILE") or Path(__file__).resolve().parents[1] / ".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _read_secret_file(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(os.path.expanduser(path_value.strip().strip('"').strip("'")))
    if not path.exists():
        raise SystemExit(f"ERROR: configured API key file does not exist: {path}")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("MET_OFFICE_LAND_OBSERVATIONS_API_KEY=", "MET_OFFICE_DATAHUB_API_KEY=")):
            _, line = line.split("=", 1)
            line = line.strip()
        return line.strip().strip('"').strip("'")
    return None


def _configured_api_key() -> str | None:
    return (
        os.environ.get("MET_OFFICE_LAND_OBSERVATIONS_API_KEY")
        or os.environ.get("MET_OFFICE_DATAHUB_API_KEY")
        or _read_secret_file(os.environ.get("MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE"))
        or _read_secret_file(os.environ.get("MET_OFFICE_DATAHUB_API_KEY_FILE"))
    )


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_stations() -> list[dict]:
    return _load_config()["stations"]


def _load_parameters() -> list[dict]:
    return _load_config()["parameters"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _parse_source_time(raw_time: str) -> tuple[float, str]:
    if not raw_time:
        raise ValueError("missing observation time")
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


_CARDINAL_DEGREES = {
    "N": 0.0,
    "NNE": 22.5,
    "NE": 45.0,
    "ENE": 67.5,
    "E": 90.0,
    "ESE": 112.5,
    "SE": 135.0,
    "SSE": 157.5,
    "S": 180.0,
    "SSW": 202.5,
    "SW": 225.0,
    "WSW": 247.5,
    "W": 270.0,
    "WNW": 292.5,
    "NW": 315.0,
    "NNW": 337.5,
}

_PRESSURE_TENDENCY_CODES = {
    "F": -1.0,
    "S": 0.0,
    "R": 1.0,
}


def _numeric_value_for_parameter(value, parameter: dict) -> float | None:
    if value is None:
        return None
    output_name = parameter.get("outputName")
    if output_name == "wind_direction" and isinstance(value, str):
        return _CARDINAL_DEGREES.get(value.strip().upper())
    if output_name == "pressure_tendency" and isinstance(value, str):
        return _PRESSURE_TENDENCY_CODES.get(value.strip().upper())
    return _as_float(value)


def _retry_after_seconds(error: HTTPError) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers else None
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _find_first_key(data: dict, wanted: list[str]) -> str | None:
    normalized = {_norm_key(k) for k in wanted}
    for item in _walk_dicts(data):
        for key, value in item.items():
            if _norm_key(key) in normalized and value not in (None, ""):
                return str(value)
    return None


def _find_location_payload(data: dict) -> dict:
    geohash = _find_first_key(data, ["geohash", "geoHash", "locationGeohash"])
    location_id = _find_first_key(data, ["id", "locationId", "stationId", "siteId", "name"])
    name = _find_first_key(data, ["name", "locationName", "stationName", "siteName"])
    lat = None
    lon = None
    for item in _walk_dicts(data):
        if lat is None:
            lat = _as_float(item.get("lat") or item.get("latitude"))
        if lon is None:
            lon = _as_float(item.get("lon") or item.get("lng") or item.get("longitude"))
        coords = item.get("coordinates")
        if isinstance(coords, list) and len(coords) >= 2 and lon is None and lat is None:
            lon = _as_float(coords[0])
            lat = _as_float(coords[1])
    return {
        "geohash": geohash,
        "locationId": location_id,
        "name": name,
        "lat": lat,
        "lon": lon,
    }


def _candidate_records(data: dict) -> list[dict]:
    time_keys = {"time", "timestamp", "datetime", "dateTime", "observationTime", "validTime", "endTime"}
    records: list[dict] = []
    for item in _walk_dicts(data):
        if any(key in item for key in time_keys):
            records.append(item)
    if records:
        return records
    features = data.get("features") if isinstance(data, dict) else None
    if isinstance(features, list):
        for feature in features:
            props = feature.get("properties") if isinstance(feature, dict) else None
            if isinstance(props, dict):
                records.append(props)
    return records


def _record_time(record: dict) -> str | None:
    for key in ("datetime", "dateTime", "observationTime", "timestamp", "time", "validTime", "endTime"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _value_for_parameter(record: dict, parameter: dict):
    aliases = parameter.get("aliases", []) + [parameter["resultField"], parameter["outputName"], parameter["label"]]
    alias_norm = {_norm_key(alias) for alias in aliases}
    for key, value in record.items():
        if _norm_key(str(key)) in alias_norm:
            return value
    parameters = record.get("parameters") or record.get("values") or record.get("properties")
    if isinstance(parameters, dict):
        for key, value in parameters.items():
            if _norm_key(str(key)) in alias_norm:
                return value
    return None


def _select_latest(records: list[dict], parameter: dict) -> tuple[dict, str, float] | None:
    candidates = []
    for record in records:
        raw_time = _record_time(record)
        value = _value_for_parameter(record, parameter)
        numeric = _numeric_value_for_parameter(value, parameter)
        if raw_time and numeric is not None:
            try:
                timestamp, phenomenon_time = _parse_source_time(raw_time)
            except Exception:
                continue
            candidates.append((timestamp, phenomenon_time, numeric, record))
    if not candidates:
        return None
    timestamp, phenomenon_time, numeric, record = sorted(candidates, key=lambda item: item[0])[-1]
    return record, phenomenon_time, numeric


class MetOfficeDataHubClient:
    def __init__(self):
        _load_local_env()
        self.api_key = _configured_api_key()
        if not self.api_key:
            raise SystemExit(
                "ERROR: MET_OFFICE_LAND_OBSERVATIONS_API_KEY must be set.\n"
                "  Store it in publishers/.env, the process environment, or set\n"
                "  MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE to a host-local secret file."
            )
        self.base_url = os.environ.get("MET_OFFICE_LAND_OBSERVATIONS_BASE_URL", DEFAULT_API_BASE).rstrip("/")
        self.key_header = os.environ.get("MET_OFFICE_DATAHUB_API_KEY_HEADER", "apikey")
        self.user_agent = "OS4CSAPI Met Office DataHub Publisher/1.0"

    def _headers(self) -> dict:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.key_header.lower() == "authorization":
            headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            headers[self.key_header] = self.api_key
        return headers

    def _get_json(self, url: str) -> dict:
        req = Request(url, headers=self._headers())
        try:
            with urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429:
                raise UpstreamRateLimit("Met Office Weather DataHub rate limit", _retry_after_seconds(exc)) from exc
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"HTTP {exc.code} GET {url}: {body}") from exc

    def nearest(self, lat: float, lon: float) -> dict:
        query_variants = [
            {"lat": f"{lat:.2f}", "lon": f"{lon:.2f}"},
            {"latitude": f"{lat:.2f}", "longitude": f"{lon:.2f}"},
        ]
        errors = []
        for query in query_variants:
            url = f"{self.base_url}/nearest?{urlencode(query)}"
            try:
                data = self._get_json(url)
                payload = _find_location_payload(data)
                payload["sourceUrl"] = url
                payload["raw"] = data
                return payload
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError("nearest lookup failed: " + " | ".join(errors))

    def observations(self, geohash: str) -> dict:
        url = f"{self.base_url}/{quote(str(geohash), safe='')}"
        data = self._get_json(url)
        return {"sourceUrl": url, "raw": data}


class MetOfficeDataHubPublisher:
    name = "Met Office DataHub Land Observations Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        _load_local_env()
        self.stations = _load_stations()
        if station_filter:
            wanted = set(s.strip() for s in station_filter if s.strip())
            self.stations = [s for s in self.stations if s["id"] in wanted]
        self.parameters = _load_parameters()
        self.client = MetOfficeDataHubClient()
        self.state = self._load_state()

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
        self._request_delay = float(os.environ.get("MET_OFFICE_DATAHUB_REQUEST_DELAY", "1.0"))
        self._rate_limit_backoff = float(os.environ.get("MET_OFFICE_DATAHUB_429_BACKOFF", "3600"))
        self._cooldown_until = 0.0
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def _load_state(self) -> dict:
        if not STATE_PATH.exists():
            return {"locations": {}}
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"locations": {}}

    def _save_state(self):
        STATE_PATH.write_text(json.dumps(self.state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _system_uid(self, station_id: str) -> str:
        return f"urn:os4csapi:system:met-office-datahub-land-observations:{_uid_token(station_id)}:v1"

    def _resolve_location(self, station: dict) -> dict:
        cached = self.state.setdefault("locations", {}).get(station["id"], {})
        if cached.get("geohash"):
            return cached
        if station.get("geohash"):
            cached = {"geohash": station["geohash"], "name": station.get("name", station["id"])}
            self.state["locations"][station["id"]] = cached
            self._save_state()
            return cached
        location = self.client.nearest(station["lat"], station["lon"])
        if not location.get("geohash"):
            raise RuntimeError(f"nearest response for {station['id']} did not expose a geohash")
        safe_location = {k: v for k, v in location.items() if k != "raw"}
        self.state["locations"][station["id"]] = safe_location
        self._save_state()
        return safe_location

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
            station_id = station["id"]
            uid = self._system_uid(station_id)
            sys_id = None
            station_ds: dict[str, str] = {}
            try:
                sys_id = find_by_uid(self._base_url, self._auth, "systems", uid, no_cache=True)
                if not sys_id:
                    print(f"  [WARN] System '{uid}' not found -- skipping {station_id}")
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
                        print(f"  [WARN] Used raw datastream fallback for {station_id}: {exc}")
                    else:
                        print(f"  [WARN] Could not resolve datastreams for {station_id}: {exc}")
                        continue
                else:
                    print(f"  [WARN] Could not resolve system for {station_id}: {exc}")
                    continue

            expected = {p["outputName"] for p in self.parameters}
            missing = sorted(expected - set(station_ds))
            if missing:
                print(f"  [WARN] Missing datastreams for {station_id}: {', '.join(missing)}")
            self._ds_ids[station_id] = station_ds
            connected += 1
            ds_summary = ", ".join(f"{k}->{v}" for k, v in station_ds.items())
            print(f"  Connected: {station_id} -> sys={sys_id} ds=[{ds_summary}]")

        print(f"  Ready: {connected}/{len(self.stations)} stations connected")
        if connected == 0:
            raise RuntimeError("No Met Office DataHub stations connected")

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

    def _latest_for_station(self, station: dict) -> list[dict]:
        location = self._resolve_location(station)
        response = self.client.observations(location["geohash"])
        raw = response["raw"]
        records = _candidate_records(raw)
        observations: list[dict] = []
        for parameter in self.parameters:
            selected = _select_latest(records, parameter)
            if not selected:
                continue
            record, phenomenon_time, value = selected
            timestamp, _ = _parse_source_time(phenomenon_time)
            result = {
                "locationId": station["id"],
                "geohash": location["geohash"],
                "parameter": parameter["label"],
                parameter["resultField"]: value,
                "unit": parameter["unit"],
                "sourceUrl": response["sourceUrl"],
            }
            observations.append({
                "station": station,
                "parameter": parameter,
                "phenomenonTime": phenomenon_time,
                "timestamp": timestamp,
                "value": value,
                "result": result,
                "dedupeKey": f"{station['id']}|{parameter['outputName']}|{phenomenon_time}|{value}",
                "sourceRecordKeys": sorted(str(k) for k in record.keys()),
            })
        return observations

    def publish_cycle(self, dry_run: bool = False) -> int:
        published = 0
        now = datetime.now(timezone.utc)
        ts_label = now.strftime("%H:%M:%S")

        cooldown_remaining = self._cooldown_until - time.time()
        if cooldown_remaining > 0:
            self.stats["skipped"] += 1
            print(f"  [{ts_label}] Met Office cooldown active; skipping fetches for {cooldown_remaining:.0f}s")
            return published

        for station in self.stations:
            station_id = station["id"]
            station_ds = self._ds_ids.get(station_id, {})
            try:
                latest_items = self._latest_for_station(station)
            except UpstreamRateLimit as exc:
                backoff = exc.retry_after or self._rate_limit_backoff
                self._cooldown_until = time.time() + backoff
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] RATE LIMITED; backing off {backoff:.0f}s")
                return published
            except Exception as exc:
                self.stats["errors"] += 1
                print(f"  [{ts_label}] {station_id}: FETCH ERR {exc}")
                continue

            if not latest_items:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {station_id}: no recognized parameter readings")
                continue

            for latest in latest_items:
                parameter = latest["parameter"]
                output_name = parameter["outputName"]
                ds_id = station_ds.get(output_name)
                if ds_id is None and not dry_run:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {station_id}/{output_name}: no datastream")
                    continue

                if latest["dedupeKey"] in self._seen:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {station_id}/{output_name}: unchanged, skipping")
                    continue

                obs = {
                    "phenomenonTime": latest["phenomenonTime"],
                    "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "result": latest["result"],
                }
                value_label = f"{parameter['label']}={latest['value']} {parameter['unit']}"
                if dry_run:
                    print(f"  [{ts_label}] {station_id}/{output_name}: [DRY] {value_label} @ {latest['phenomenonTime']}")
                    self._seen.add(latest["dedupeKey"])
                else:
                    try:
                        self._post_observation(ds_id, obs)
                        self.stats["published"] += 1
                        published += 1
                        self._seen.add(latest["dedupeKey"])
                        print(f"  [{ts_label}] {station_id}/{output_name}: OK  {value_label}")
                    except Exception as exc:
                        self.stats["errors"] += 1
                        print(f"  [{ts_label}] {station_id}/{output_name}: ERR {exc}")

            time.sleep(self._request_delay)

        return published

    def probe(self, station_id: str | None = None, dump_json: bool = False):
        stations = self.stations
        if station_id:
            stations = [s for s in self.stations if s["id"] == station_id]
        for station in stations:
            print(f"-- {station['id']} --")
            location = self._resolve_location(station)
            print(f"nearest geohash: {location.get('geohash')}  name: {location.get('name') or location.get('locationId') or 'unknown'}")
            response = self.client.observations(location["geohash"])
            records = _candidate_records(response["raw"])
            print(f"candidate records: {len(records)}")
            if records:
                print("sample record keys: " + ", ".join(sorted(str(k) for k in records[-1].keys())))
            if dump_json:
                print(json.dumps(response["raw"], indent=2)[:4000])

    def run(self, *, interval: float = 3600.0, dry_run: bool = False, once: bool = False):
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  API:       {self.client.base_url}")
        print(f"  Stations:  {len(self.stations)} ({', '.join(s['id'] for s in self.stations)})")
        print(f"  Parameters:{len(self.parameters)}")
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
        description="Publish curated Met Office Land Observations readings to CSAPI/OSH.")
    parser.add_argument("--interval", type=float, default=3600.0,
                        help="Polling interval in seconds")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and log readings without posting observations")
    parser.add_argument("--once", action="store_true",
                        help="Run one publish cycle and exit")
    parser.add_argument("--stations", type=str, default=None,
                        help="Comma-separated curated location IDs to include")
    parser.add_argument("--probe", action="store_true",
                        help="Resolve nearest locations and show recognized response shape")
    parser.add_argument("--dump-json", action="store_true",
                        help="With --probe, print the first part of the raw observation JSON")
    args = parser.parse_args()

    station_filter = args.stations.split(",") if args.stations else None
    publisher = MetOfficeDataHubPublisher(station_filter=station_filter)
    if args.probe:
        publisher.probe(station_id=station_filter[0] if station_filter and len(station_filter) == 1 else None,
                        dump_json=args.dump_json)
    else:
        publisher.run(interval=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()