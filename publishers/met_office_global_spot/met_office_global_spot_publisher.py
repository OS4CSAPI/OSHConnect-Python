#!/usr/bin/env python3
"""
met_office_global_spot_publisher.py -- Met Office Weather DataHub Global Spot
hourly forecast publisher for CSAPI/OSH.

Fetches deterministic hourly forecasts for curated UK forecast points and
publishes one CSAPI observation per selected forecast parameter and valid time.
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
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import api_get, find_by_uid


DEFAULT_API_BASE = "https://data.hub.api.metoffice.gov.uk/sitespecific/v0"
DEFAULT_HOURLY_PATH = "/point/hourly"
FORECAST_TYPE = "Met Office Global Spot hourly deterministic forecast"


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
        if line.startswith((
            "MET_OFFICE_GLOBAL_SPOT_API_KEY=",
            "MET_OFFICE_SITE_SPECIFIC_FORECAST_API_KEY=",
            "MET_OFFICE_DATAHUB_API_KEY=",
        )):
            _, line = line.split("=", 1)
            line = line.strip()
        return line.strip().strip('"').strip("'")
    return None


def _configured_api_key() -> str | None:
    return (
        os.environ.get("MET_OFFICE_GLOBAL_SPOT_API_KEY")
        or os.environ.get("MET_OFFICE_SITE_SPECIFIC_FORECAST_API_KEY")
        or os.environ.get("MET_OFFICE_DATAHUB_API_KEY")
        or _read_secret_file(os.environ.get("MET_OFFICE_GLOBAL_SPOT_API_KEY_FILE"))
        or _read_secret_file(os.environ.get("MET_OFFICE_SITE_SPECIFIC_FORECAST_API_KEY_FILE"))
        or _read_secret_file(os.environ.get("MET_OFFICE_DATAHUB_API_KEY_FILE"))
    )


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "forecast_points.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_locations() -> list[dict]:
    return _load_config()["locations"]


def _load_parameters() -> list[dict]:
    return _load_config()["parameters"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _retry_after_seconds(error: HTTPError) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers else None
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


def _parse_source_time(raw_time: str) -> tuple[float, str]:
    if not raw_time:
        raise ValueError("missing forecast time")
    normalized = str(raw_time).replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.timestamp(), dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_float(value) -> float | None:
    if value is None or value == "" or value == "NaN":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not result == result:
        return None
    return result


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


def _record_time(record: dict) -> str | None:
    for key in ("validTime", "forecastTime", "time", "datetime", "dateTime", "timestamp", "endTime"):
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _issued_time(record: dict, root: dict | None = None) -> str | None:
    keys = ("issuedTime", "issueTime", "modelRunTime", "runTime", "forecastReferenceTime", "createdAt", "creationTime")
    for item in (record, root or {}):
        for key in keys:
            value = item.get(key) if isinstance(item, dict) else None
            if isinstance(value, str) and value:
                try:
                    _, normalized = _parse_source_time(value)
                    return normalized
                except Exception:
                    return value
    return None


def _value_for_parameter(record: dict, parameter: dict):
    aliases = parameter.get("aliases", []) + [parameter["resultField"], parameter["outputName"], parameter["label"]]
    alias_norm = {_norm_key(alias) for alias in aliases}
    for key, value in record.items():
        if _norm_key(str(key)) in alias_norm:
            return value
    for child_key in ("parameters", "values", "properties", "forecast", "data"):
        child = record.get(child_key)
        if isinstance(child, dict):
            for key, value in child.items():
                if _norm_key(str(key)) in alias_norm:
                    return value
    return None


def _candidate_records(data: dict, parameters: list[dict]) -> list[dict]:
    records: list[dict] = []
    for item in _walk_dicts(data):
        if not _record_time(item):
            continue
        if any(_value_for_parameter(item, parameter) is not None for parameter in parameters):
            records.append(item)
    return records


def _lead_time_hours(issued_time: str | None, valid_time: str) -> float | None:
    if not issued_time:
        return None
    try:
        issued_ts, _ = _parse_source_time(issued_time)
        valid_ts, _ = _parse_source_time(valid_time)
    except Exception:
        return None
    return round((valid_ts - issued_ts) / 3600.0, 2)


class MetOfficeGlobalSpotClient:
    def __init__(self):
        _load_local_env()
        self.api_key = _configured_api_key()
        if not self.api_key:
            raise SystemExit(
                "ERROR: MET_OFFICE_GLOBAL_SPOT_API_KEY must be set.\n"
                "  Store it in publishers/.env, the process environment, or set\n"
                "  MET_OFFICE_GLOBAL_SPOT_API_KEY_FILE to a host-local secret file."
            )
        self.base_url = os.environ.get("MET_OFFICE_GLOBAL_SPOT_BASE_URL", DEFAULT_API_BASE).rstrip("/")
        self.hourly_path = os.environ.get("MET_OFFICE_GLOBAL_SPOT_HOURLY_PATH", DEFAULT_HOURLY_PATH)
        self.key_header = os.environ.get("MET_OFFICE_DATAHUB_API_KEY_HEADER", "apikey")
        self.user_agent = "OS4CSAPI Met Office Global Spot Publisher/1.0"

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

    def _url_for_path(self, path: str, location: dict, query: dict[str, str]) -> str:
        path = path.format(
            lat=f"{location['lat']:.4f}",
            lon=f"{location['lon']:.4f}",
            latitude=f"{location['lat']:.4f}",
            longitude=f"{location['lon']:.4f}",
        )
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.base_url}/{path.lstrip('/')}"
        if "?" in url or "{" in path:
            return url
        return f"{url}?{urlencode(query)}"

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

    def hourly_forecast(self, location: dict) -> dict:
        paths = []
        for candidate in [
            self.hourly_path,
            "/point/hourly",
            "/global/hourly",
            "/hourly",
        ]:
            if candidate not in paths:
                paths.append(candidate)
        query_variants = [
            {"latitude": f"{location['lat']:.4f}", "longitude": f"{location['lon']:.4f}"},
            {"lat": f"{location['lat']:.4f}", "lon": f"{location['lon']:.4f}"},
        ]
        errors = []
        for path in paths:
            for query in query_variants:
                url = self._url_for_path(path, location, query)
                try:
                    data = self._get_json(url)
                    return {"sourceUrl": url, "raw": data}
                except UpstreamRateLimit:
                    raise
                except Exception as exc:
                    errors.append(str(exc))
        raise RuntimeError("hourly forecast lookup failed: " + " | ".join(errors[:4]))


class MetOfficeGlobalSpotPublisher:
    name = "Met Office DataHub Global Spot Hourly Forecast Publisher"

    def __init__(self, location_filter: list[str] | None = None):
        _load_local_env()
        self.locations = _load_locations()
        if location_filter:
            wanted = set(s.strip() for s in location_filter if s.strip())
            self.locations = [s for s in self.locations if s["id"] in wanted]
        self.parameters = _load_parameters()
        self.client = MetOfficeGlobalSpotClient()

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
        self._request_delay = float(os.environ.get("MET_OFFICE_GLOBAL_SPOT_REQUEST_DELAY", "1.0"))
        self._rate_limit_backoff = float(os.environ.get("MET_OFFICE_GLOBAL_SPOT_429_BACKOFF", "3600"))
        self._forecast_hours = float(os.environ.get("MET_OFFICE_GLOBAL_SPOT_FORECAST_HOURS", "24"))
        self._cooldown_until = 0.0
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def _system_uid(self, location_id: str) -> str:
        return f"urn:os4csapi:system:met-office-datahub-global-spot:{_uid_token(location_id)}:v1"

    def _raw_datastream_ids(self, sys_id: str) -> dict[str, str]:
        url = f"{self._base_url}/systems/{sys_id}/datastreams"
        headers = {"Accept": "application/json", "Authorization": self._auth}
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urlopen(Request(url, headers=headers), timeout=30, context=ctx) as resp:
            text = resp.read().decode()

        location_ds: dict[str, str] = {}
        current_id = None
        for key, value in re.findall(r'"(id|outputName)"\s*:\s*"([^"]+)"', text):
            if key == "id":
                current_id = value
            elif key == "outputName" and current_id:
                location_ds[value] = current_id
                current_id = None
        return location_ds

    def connect(self):
        self._ds_ids.clear()
        connected = 0
        for location in self.locations:
            location_id = location["id"]
            uid = self._system_uid(location_id)
            sys_id = None
            location_ds: dict[str, str] = {}
            try:
                sys_id = find_by_uid(self._base_url, self._auth, "systems", uid, no_cache=True)
                if not sys_id:
                    print(f"  [WARN] System '{uid}' not found -- skipping {location_id}")
                    continue
                ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
                if ds_list:
                    for item in ds_list.get("items", []):
                        output_name = item.get("outputName", "")
                        ds_id = item.get("id")
                        if output_name and ds_id:
                            location_ds[output_name] = ds_id
            except Exception as exc:
                if sys_id:
                    location_ds = self._raw_datastream_ids(sys_id)
                    if location_ds:
                        print(f"  [WARN] Used raw datastream fallback for {location_id}: {exc}")
                    else:
                        print(f"  [WARN] Could not resolve datastreams for {location_id}: {exc}")
                        continue
                else:
                    print(f"  [WARN] Could not resolve system for {location_id}: {exc}")
                    continue

            expected = {p["outputName"] for p in self.parameters}
            missing = sorted(expected - set(location_ds))
            if missing:
                print(f"  [WARN] Missing datastreams for {location_id}: {', '.join(missing)}")
            self._ds_ids[location_id] = location_ds
            connected += 1
            ds_summary = ", ".join(f"{k}->{v}" for k, v in location_ds.items())
            print(f"  Connected: {location_id} -> sys={sys_id} ds=[{ds_summary}]")

        print(f"  Ready: {connected}/{len(self.locations)} forecast points connected")
        if connected == 0:
            raise RuntimeError("No Met Office Global Spot forecast points connected")

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

    def _forecasts_for_location(self, location: dict) -> list[dict]:
        response = self.client.hourly_forecast(location)
        raw = response["raw"]
        records = _candidate_records(raw, self.parameters)
        now_ts = time.time()
        end_ts = now_ts + self._forecast_hours * 3600.0
        forecasts: list[dict] = []
        root_issued_time = _issued_time(raw) if isinstance(raw, dict) else None
        for record in records:
            raw_time = _record_time(record)
            if not raw_time:
                continue
            try:
                valid_ts, valid_time = _parse_source_time(raw_time)
            except Exception:
                continue
            if valid_ts < now_ts - 3600.0 or valid_ts > end_ts:
                continue
            issued_time = _issued_time(record, raw) or root_issued_time
            lead_time = _lead_time_hours(issued_time, valid_time)
            for parameter in self.parameters:
                value = _as_float(_value_for_parameter(record, parameter))
                if value is None:
                    continue
                result = {
                    "locationId": location["id"],
                    "forecastType": FORECAST_TYPE,
                    "issuedTime": issued_time or "",
                    "validTime": valid_time,
                    "leadTimeHours": lead_time if lead_time is not None else "NaN",
                    "parameter": parameter["label"],
                    parameter["resultField"]: value,
                    "unit": parameter["unit"],
                    "sourceUrl": response["sourceUrl"],
                }
                forecasts.append({
                    "location": location,
                    "parameter": parameter,
                    "phenomenonTime": valid_time,
                    "timestamp": valid_ts,
                    "value": value,
                    "result": result,
                    "dedupeKey": f"{location['id']}|{parameter['outputName']}|{issued_time or ''}|{valid_time}|{value}",
                    "sourceRecordKeys": sorted(str(k) for k in record.keys()),
                })
        return sorted(forecasts, key=lambda item: (item["timestamp"], item["parameter"]["outputName"]))

    def publish_cycle(self, dry_run: bool = False) -> int:
        published = 0
        now = datetime.now(timezone.utc)
        ts_label = now.strftime("%H:%M:%S")

        cooldown_remaining = self._cooldown_until - time.time()
        if cooldown_remaining > 0:
            self.stats["skipped"] += 1
            print(f"  [{ts_label}] Met Office Global Spot cooldown active; skipping fetches for {cooldown_remaining:.0f}s")
            return published

        for location in self.locations:
            location_id = location["id"]
            location_ds = self._ds_ids.get(location_id, {})
            try:
                forecast_items = self._forecasts_for_location(location)
            except UpstreamRateLimit as exc:
                backoff = exc.retry_after or self._rate_limit_backoff
                self._cooldown_until = time.time() + backoff
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] RATE LIMITED; backing off {backoff:.0f}s")
                return published
            except Exception as exc:
                self.stats["errors"] += 1
                print(f"  [{ts_label}] {location_id}: FETCH ERR {exc}")
                continue

            if not forecast_items:
                self.stats["skipped"] += 1
                print(f"  [{ts_label}] {location_id}: no recognized forecast values")
                continue

            for forecast in forecast_items:
                parameter = forecast["parameter"]
                output_name = parameter["outputName"]
                ds_id = location_ds.get(output_name)
                if ds_id is None and not dry_run:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {location_id}/{output_name}: no datastream")
                    continue

                if forecast["dedupeKey"] in self._seen:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {location_id}/{output_name}: unchanged, skipping")
                    continue

                obs = {
                    "phenomenonTime": forecast["phenomenonTime"],
                    "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "result": forecast["result"],
                }
                value_label = f"{parameter['label']}={forecast['value']} {parameter['unit']} valid {forecast['phenomenonTime']}"
                if dry_run:
                    print(f"  [{ts_label}] {location_id}/{output_name}: [DRY] {value_label}")
                    self._seen.add(forecast["dedupeKey"])
                else:
                    try:
                        self._post_observation(ds_id, obs)
                        self.stats["published"] += 1
                        published += 1
                        self._seen.add(forecast["dedupeKey"])
                        print(f"  [{ts_label}] {location_id}/{output_name}: OK  {value_label}")
                    except Exception as exc:
                        self.stats["errors"] += 1
                        print(f"  [{ts_label}] {location_id}/{output_name}: ERR {exc}")

            time.sleep(self._request_delay)

        return published

    def probe(self, location_id: str | None = None, dump_json: bool = False):
        locations = self.locations
        if location_id:
            locations = [s for s in self.locations if s["id"] == location_id]
        for location in locations:
            print(f"-- {location['id']} --")
            response = self.client.hourly_forecast(location)
            records = _candidate_records(response["raw"], self.parameters)
            print(f"source URL: {response['sourceUrl']}")
            print(f"candidate records: {len(records)}")
            if records:
                print("sample record keys: " + ", ".join(sorted(str(k) for k in records[0].keys())))
                recognized = []
                for parameter in self.parameters:
                    value = _value_for_parameter(records[0], parameter)
                    if value is not None:
                        recognized.append(f"{parameter['outputName']}={value}")
                print("recognized values: " + (", ".join(recognized) or "none in first record"))
            if dump_json:
                print(json.dumps(response["raw"], indent=2)[:4000])

    def run(self, *, interval: float = 3600.0, dry_run: bool = False, once: bool = False):
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    {self._base_url}")
        print(f"  API:       {self.client.base_url}")
        print(f"  Path:      {self.client.hourly_path}")
        print(f"  Locations: {len(self.locations)} ({', '.join(s['id'] for s in self.locations)})")
        print(f"  Parameters:{len(self.parameters)}")
        print(f"  Horizon:   {self._forecast_hours:g}h")
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
        description="Publish curated Met Office Global Spot hourly forecasts to CSAPI/OSH.")
    parser.add_argument("--interval", type=float, default=3600.0,
                        help="Polling interval in seconds")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and log forecasts without posting observations")
    parser.add_argument("--once", action="store_true",
                        help="Run one publish cycle and exit")
    parser.add_argument("--locations", type=str, default=None,
                        help="Comma-separated curated forecast point IDs to include")
    parser.add_argument("--probe", action="store_true",
                        help="Fetch forecasts and show recognized response shape")
    parser.add_argument("--dump-json", action="store_true",
                        help="With --probe, print the first part of the raw forecast JSON")
    args = parser.parse_args()

    location_filter = args.locations.split(",") if args.locations else None
    publisher = MetOfficeGlobalSpotPublisher(location_filter=location_filter)
    if args.probe:
        publisher.probe(location_id=location_filter[0] if location_filter and len(location_filter) == 1 else None,
                        dump_json=args.dump_json)
    else:
        publisher.run(interval=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()
