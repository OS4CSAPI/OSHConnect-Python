#!/usr/bin/env python3
"""
usgs_water_publisher.py — USGS water monitoring observation publisher for CSAPI/OSH.

Fetches continuous instantaneous values (discharge + gage height) for each
configured station from the USGS Water Data OGC API, normalises, and publishes
as CSAPI observations.

Station list is read from stations.json (same directory).

Configure via environment variables:
    OSH_ADDRESS        Server hostname            (required)
    OSH_PORT           Server port                (default: 443)
    OSH_USER           Auth username              (required)
    OSH_PASS           Auth password              (required)
    USGS_API_KEY       USGS API key               (optional, improves rate limits)

Usage:
    python -m publishers.usgs_water.usgs_water_publisher                        # run forever (15min cadence)
    python -m publishers.usgs_water.usgs_water_publisher --dry-run              # print only
    python -m publishers.usgs_water.usgs_water_publisher --once                 # single cycle
    python -m publishers.usgs_water.usgs_water_publisher --interval 300         # 5min cadence
    python -m publishers.usgs_water.usgs_water_publisher --stations 09380000,08171000  # subset

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

USGS_OGC_API = "https://api.waterdata.usgs.gov/ogcapi/v0"

# Output names must match bootstrap
DS_DISCHARGE_OUTPUT = "usgsDischarge"
DS_GAGE_HEIGHT_OUTPUT = "usgsGageHeight"

# Parameter code → output name mapping
PARAM_MAP = {
    "00060": DS_DISCHARGE_OUTPUT,
    "00065": DS_GAGE_HEIGHT_OUTPUT,
}

# Parameter code → result field name
PARAM_FIELD = {
    "00060": "discharge_cfs",
    "00065": "gage_height_ft",
}

# How many recent observations to fetch per station per parameter
FETCH_LIMIT = 5


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
    with open(os.path.join(here, "stations.json")) as f:
        return json.load(f)["stations"]


# ═══════════════════════════════════════════════════════════════════════════
#  USGS API fetch helpers
# ═══════════════════════════════════════════════════════════════════════════

def fetch_continuous_values(nwis_id: str, parameter_code: str,
                            api_key: str | None = None,
                            limit: int = FETCH_LIMIT) -> list[dict]:
    """Fetch recent continuous instantaneous values from USGS OGC API.

    Returns a list of normalized observation dicts, newest first.
    Each dict has: timestamp (epoch), phenomenonTime (ISO), stationId, value, qualifier, approvalStatus.
    """
    url = (
        f"{USGS_OGC_API}/collections/continuous/items"
        f"?monitoring_location_id=USGS-{nwis_id}"
        f"&parameter_code={parameter_code}"
        f"&limit={limit}"
        f"&f=json"
    )

    headers = {"Accept": "application/geo+json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    req = Request(url, headers=headers)

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 404:
            return []
        if e.code == 429:
            raise UpstreamRateLimit(
                f"HTTP 429 Too Many Requests for {nwis_id}/{parameter_code}",
                _retry_after_seconds(e),
            ) from e
        raise
    except Exception as e:
        print(f"    [WARN] USGS fetch failed for {nwis_id}/{parameter_code}: {e}")
        return []

    features = data.get("features", [])
    results = []

    for feat in features:
        props = feat.get("properties", {})

        # Parse time
        raw_time = props.get("time", "")
        try:
            ts_dt = datetime.fromisoformat(raw_time)
            ts_epoch = ts_dt.timestamp()
            ts_iso = ts_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, TypeError):
            continue  # skip malformed timestamps

        value = props.get("value")
        if value is None:
            continue  # skip null values

        # Qualifier can be a list (e.g. ['ICE']) — join to comma-separated string
        raw_qual = props.get("qualifier", "")
        qualifier_str = ",".join(raw_qual) if isinstance(raw_qual, list) else str(raw_qual)

        results.append({
            "timestamp": ts_epoch,
            "phenomenonTime": ts_iso,
            "stationId": nwis_id,
            "value": float(value),
            "qualifier": qualifier_str,
            "approvalStatus": props.get("approval_status", ""),
        })

    # Sort newest first
    results.sort(key=lambda r: r["timestamp"], reverse=True)
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Publisher
# ═══════════════════════════════════════════════════════════════════════════

class USGSWaterPublisher:
    """Multi-station USGS water monitoring publisher.

    Connects to two datastreams per station (discharge + gage height),
    publishes the latest observations each cycle.
    """

    name = "USGS Water Monitoring Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        self.stations = _load_stations()
        if station_filter:
            filt = set(station_filter)
            self.stations = [s for s in self.stations if s["nwisId"] in filt]

        self.osh_address = os.environ.get("OSH_ADDRESS", "")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "")
        self.osh_pass = os.environ.get("OSH_PASS", "")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        self.api_key = os.environ.get("USGS_API_KEY", None)
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit(
                "ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.\n"
                "  Copy publishers/.env.example → .env and set your server details."
            )

        # nwisId → {param_code → ds_server_id}
        self._ds_ids: dict[str, dict[str, str]] = {}
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

        # Track last observation timestamp per (station, param) to avoid duplicates
        self._last_obs_ts: dict[str, float] = {}
        self._usgs_cooldown_until = 0.0
        self._request_delay = float(os.environ.get("USGS_REQUEST_DELAY", "2.0"))
        self._rate_limit_backoff = float(os.environ.get("USGS_429_BACKOFF", "900"))

        # REST config
        self._base_url = os.environ.get(
            "OSH_BASE_URL",
            f"https://{self.osh_address}/{self.osh_root}/api",
        )
        self._is_go_server = "csapi-go" in self._base_url
        self._auth = "Basic " + base64.b64encode(
            f"{self.osh_user}:{self.osh_pass}".encode()).decode()

    def _system_uid(self, nwis_id: str) -> str:
        return f"urn:os4csapi:system:usgs-water:{nwis_id}:v1"

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
                if value == DS_DISCHARGE_OUTPUT:
                    station_ds["00060"] = current_id
                elif value == DS_GAGE_HEIGHT_OUTPUT:
                    station_ds["00065"] = current_id
                current_id = None
        return station_ds

    def connect(self):
        """Resolve system and datastream IDs for each station via REST API."""
        self._ds_ids.clear()
        connected = 0
        for st in self.stations:
            nwis_id = st["nwisId"]
            uid = self._system_uid(nwis_id)
            sys_id = None
            station_ds = {}
            try:
                sys_id = find_by_uid(self._base_url, self._auth, "systems", uid, no_cache=True)
                if not sys_id:
                    print(f"  [WARN] System '{uid}' not found -- skipping {nwis_id}")
                    continue

                ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth)
                if ds_list:
                    for item in ds_list.get("items", []):
                        output_name = item.get("outputName", "")
                        ds_id = item.get("id")
                        if output_name == DS_DISCHARGE_OUTPUT and ds_id:
                            station_ds["00060"] = ds_id
                        elif output_name == DS_GAGE_HEIGHT_OUTPUT and ds_id:
                            station_ds["00065"] = ds_id
            except Exception as e:
                if sys_id:
                    station_ds = self._raw_datastream_ids(sys_id)
                    if station_ds:
                        print(f"  [WARN] Used raw datastream fallback for {nwis_id}: {e}")
                    else:
                        print(f"  [WARN] Could not resolve datastreams for {nwis_id}: {e}")
                        continue
                else:
                    print(f"  [WARN] Could not resolve system for {nwis_id}: {e}")
                    continue

            if not station_ds:
                print(f"  [WARN] No datastreams found for {nwis_id} -- skipping")
                continue

            self._ds_ids[nwis_id] = station_ds
            connected += 1
            ds_summary = ", ".join(f"{k}->{v}" for k, v in station_ds.items())
            print(f"  Connected: {nwis_id} -> sys={sys_id} ds=[{ds_summary}]")

        print(f"  Ready: {connected}/{len(self.stations)} stations connected")
        if connected == 0:
            raise RuntimeError("No USGS Water stations connected")

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
        """Fetch + publish observations for all stations. Returns count published."""
        published = 0
        now = datetime.now(timezone.utc)
        ts_label = now.strftime("%H:%M:%S")

        for st in self.stations:
            nwis_id = st["nwisId"]
            station_ds = self._ds_ids.get(nwis_id, {})

            for param_code in st.get("parameterCodes", []):
                cooldown_remaining = self._usgs_cooldown_until - time.time()
                if cooldown_remaining > 0:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] USGS cooldown active; skipping fetches for {cooldown_remaining:.0f}s")
                    return published

                ds_id = station_ds.get(param_code)
                if ds_id is None and not dry_run:
                    continue

                field_name = PARAM_FIELD.get(param_code, param_code)

                # Fetch from USGS
                try:
                    values = fetch_continuous_values(
                        nwis_id, param_code,
                        api_key=self.api_key, limit=1)
                except UpstreamRateLimit as e:
                    backoff = e.retry_after or self._rate_limit_backoff
                    self._usgs_cooldown_until = time.time() + backoff
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {nwis_id}/{param_code}: RATE LIMITED; backing off {backoff:.0f}s")
                    return published
                except Exception as e:
                    self.stats["errors"] += 1
                    print(f"  [{ts_label}] {nwis_id}/{param_code}: FETCH ERR {e}")
                    continue

                if not values:
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {nwis_id}/{param_code}: no data")
                    continue

                latest = values[0]

                # Skip if observation timestamp hasn't changed
                dedup_key = f"{nwis_id}:{param_code}"
                obs_ts = latest["timestamp"]
                if obs_ts == self._last_obs_ts.get(dedup_key):
                    self.stats["skipped"] += 1
                    print(f"  [{ts_label}] {nwis_id}/{param_code}: unchanged, skipping")
                    continue

                # Build observation envelope
                # The SWE Time field 'timestamp' maps to phenomenonTime in the O&M
                # envelope and must NOT appear in the result body.
                # Result fields must follow schema order: stationId, {value_field}, qualifier, approvalStatus
                phenomenon_time = latest["phenomenonTime"]
                result = {
                    "stationId": nwis_id,
                    field_name: latest["value"],
                    "qualifier": latest.get("qualifier", ""),
                    "approvalStatus": latest.get("approvalStatus", ""),
                }

                obs = {
                    "phenomenonTime": phenomenon_time,
                    "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "result": result,
                }

                if dry_run:
                    print(f"  [{ts_label}] {nwis_id}/{param_code}: [DRY] {field_name}={latest['value']}")
                else:
                    try:
                        self._post_observation(ds_id, obs)
                        self.stats["published"] += 1
                        published += 1
                        self._last_obs_ts[dedup_key] = obs_ts
                        print(f"  [{ts_label}] {nwis_id}/{param_code}: OK  {field_name}={latest['value']}")
                    except Exception as e:
                        self.stats["errors"] += 1
                        print(f"  [{ts_label}] {nwis_id}/{param_code}: ERR {e}")

                time.sleep(self._request_delay)

        return published

    def run(self, *, interval: float = 900.0, dry_run: bool = False, once: bool = False):
        """Main publisher loop."""
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:    https://{self.osh_address}:{self.osh_port}/{self.osh_root}/api")
        print(f"  Stations:  {len(self.stations)} ({', '.join(s['nwisId'] for s in self.stations)})")
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
        print(f"  Skipped:    {self.stats['skipped']} (unchanged/empty)")
        print(f"  Errors:     {self.stats['errors']}")
        print(f"  Reconnects: {self.stats['reconnects']}")
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="USGS water monitoring observation publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=900.0,
                        help="Seconds between publish cycles (default: 900 = 15min)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print observations but don't POST them")
    parser.add_argument("--once", action="store_true",
                        help="Publish a single cycle then exit")
    parser.add_argument("--stations", type=str, default=None,
                        help="Comma-separated NWIS site IDs to publish (default: all from stations.json)")
    args = parser.parse_args()

    station_filter = args.stations.split(",") if args.stations else None
    publisher = USGSWaterPublisher(station_filter=station_filter)
    publisher.run(
        interval=args.interval,
        dry_run=args.dry_run,
        once=args.once,
    )


if __name__ == "__main__":
    main()
