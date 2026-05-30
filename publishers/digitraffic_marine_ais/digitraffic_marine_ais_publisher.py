#!/usr/bin/env python3
"""Publish Digitraffic Marine AIS vessel positions to CSAPI/OSH."""

import argparse
import base64
import gzip
import json
import os
import random
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import api_get, find_by_uid


SYSTEM_UID = "urn:os4csapi:system:digitraffic-marine-ais-feed:v1"
DS_OUTPUT_NAME = "digitrafficMarineAisPosition"
LOCATIONS_URL = "https://meri.digitraffic.fi/api/ais/v1/locations"
VESSELS_URL = "https://meri.digitraffic.fi/api/ais/v1/vessels"

NAV_STATUS = {
    0: "Under way using engine",
    1: "At anchor",
    2: "Not under command",
    3: "Restricted manoeuvrability",
    4: "Constrained by draught",
    5: "Moored",
    6: "Aground",
    7: "Engaged in fishing",
    8: "Under way sailing",
    15: "Undefined",
}


def _load_config() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "config.json"), encoding="utf-8") as file:
        return json.load(file)["digitraffic_marine_ais"]


def _safe_float(value) -> float | str:
    if value is None:
        return "NaN"
    try:
        return float(value)
    except (TypeError, ValueError):
        return "NaN"


def _safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _ais_speed(value) -> float | str:
    speed = _safe_float(value)
    if speed == "NaN" or speed >= 102.2:
        return "NaN"
    return speed


def _ais_course(value) -> float | str:
    course = _safe_float(value)
    if course == "NaN" or course >= 360:
        return "NaN"
    return course


def _ais_heading(value) -> float | str:
    heading = _safe_float(value)
    if heading == "NaN" or heading >= 511:
        return "NaN"
    return heading


def _fetch_json(url: str):
    req = Request(url, headers={
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Digitraffic-User": "OS4CSAPI publisher github.com/OS4CSAPI",
        "User-Agent": "os4csapi-publisher/1.0 (github.com/OS4CSAPI)",
    })
    with urlopen(req, timeout=60) as response:
        raw = response.read()
        if response.headers.get("Content-Encoding", "").lower() == "gzip" or raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def _offset_phenomenon_time(source_time: str, offset_ms: int) -> str:
    try:
        base = datetime.strptime(source_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return source_time
    shifted = base + timedelta(milliseconds=offset_ms)
    return shifted.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _in_bbox(feature: dict, bbox: dict) -> bool:
    coords = feature.get("geometry", {}).get("coordinates") or []
    if len(coords) < 2:
        return False
    lon, lat = coords[0], coords[1]
    return bbox["lomin"] <= lon <= bbox["lomax"] and bbox["lamin"] <= lat <= bbox["lamax"]


def _load_vessel_metadata() -> dict[int, dict]:
    try:
        vessels = _fetch_json(VESSELS_URL)
    except Exception as exc:
        print(f"    [WARN] Vessel metadata fetch failed: {exc}")
        return {}
    result: dict[int, dict] = {}
    for vessel in vessels if isinstance(vessels, list) else []:
        try:
            result[int(vessel.get("mmsi"))] = vessel
        except (TypeError, ValueError):
            continue
    return result


def fetch_ais_positions(config: dict, *, include_metadata: bool = True) -> tuple[str, list[dict]]:
    data = _fetch_json(LOCATIONS_URL)
    source_time = data.get("dataUpdatedTime") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bbox = config["bounding_box"]
    max_vessels = int(config.get("max_vessels_per_cycle", 60))
    features = [feature for feature in data.get("features", []) if _in_bbox(feature, bbox)]

    vessels_by_mmsi = _load_vessel_metadata() if include_metadata else {}
    parsed = []
    for feature in features:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        try:
            mmsi_int = int(props.get("mmsi") or feature.get("mmsi"))
        except (TypeError, ValueError):
            continue
        metadata = vessels_by_mmsi.get(mmsi_int, {})
        nav_code = props.get("navStat")
        try:
            nav_code_int = int(nav_code)
        except (TypeError, ValueError):
            nav_code_int = -1
        sog = _ais_speed(props.get("sog"))
        parsed.append({
            "mmsi": str(mmsi_int),
            "vesselName": _safe_text(metadata.get("name")),
            "callSign": _safe_text(metadata.get("callSign")),
            "imo": _safe_text(metadata.get("imo")),
            "lat_deg": _safe_float(coords[1]),
            "lon_deg": _safe_float(coords[0]),
            "sog_kts": sog,
            "cog_deg": _ais_course(props.get("cog")),
            "heading_deg": _ais_heading(props.get("heading")),
            "navStatus": NAV_STATUS.get(nav_code_int, f"Unknown({nav_code})"),
            "shipType": _safe_text(metadata.get("shipType")),
            "destination": _safe_text(metadata.get("destination")),
            "sourceDataUpdatedTime": source_time,
            "sourcePayloadJson": json.dumps({"location": props, "vessel": metadata}, separators=(",", ":"), ensure_ascii=False),
            "_sortSpeed": -1.0 if sog == "NaN" else float(sog),
        })

    parsed.sort(key=lambda item: (item["_sortSpeed"], item["mmsi"]), reverse=True)
    for item in parsed:
        item.pop("_sortSpeed", None)
    return source_time, parsed[:max_vessels]


class DigitrafficMarineAISPublisher:
    name = "Digitraffic Marine AIS Publisher"

    def __init__(self):
        self.config = _load_config()
        self.osh_address = os.environ.get("OSH_ADDRESS", "")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "")
        self.osh_pass = os.environ.get("OSH_PASS", "")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit("ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.")
        scheme = "http" if self.osh_port == 80 else "https"
        self._base_url = os.environ.get("OSH_BASE_URL", f"{scheme}://{self.osh_address}/{self.osh_root}/api")
        self._is_go_server = "csapi-go" in self._base_url
        self._auth = "Basic " + base64.b64encode(f"{self.osh_user}:{self.osh_pass}".encode()).decode()
        self._ds_id: str | None = None
        self._last_seen: dict[str, str] = {}
        self.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0, "vessels_seen": 0}

    def connect(self):
        self._ds_id = None
        sys_id = find_by_uid(self._base_url, self._auth, "systems", SYSTEM_UID, no_cache=True)
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
            except Exception as exc:
                if attempt == max_attempts:
                    raise
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                wait = delay + delay * 0.2 * (random.random() - 0.5)
                print(f"  [WARN] Attempt {attempt}/{max_attempts} failed: {exc}")
                print(f"         Retrying in {wait:.1f}s...")
                time.sleep(wait)

    def _post_observation(self, obs: dict):
        if self._is_go_server:
            for key, value in obs.get("result", {}).items():
                if value == "NaN":
                    obs["result"][key] = 0.0
        url = f"{self._base_url}/datastreams/{self._ds_id}/observations"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = Request(url, data=json.dumps(obs).encode("utf-8"), method="POST", headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": self._auth, "Host": self.osh_address})
        try:
            with urlopen(req, timeout=30, context=ctx) as response:
                if response.status not in (200, 201, 204):
                    raise RuntimeError(f"HTTP {response.status} POST {url}")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"HTTP {exc.code} POST {url}: {body}") from exc

    def publish_cycle(self, *, dry_run: bool = False, include_metadata: bool = True) -> int:
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S")
        try:
            source_time, vessels = fetch_ais_positions(self.config, include_metadata=include_metadata)
        except Exception as exc:
            self.stats["errors"] += 1
            print(f"  [{ts}] AIS fetch failed: {exc}")
            return 0

        print(f"  [{ts}] Received {len(vessels)} AIS vessels from Digitraffic (source={source_time})")
        cycle_published = 0
        cycle_skipped = 0
        cycle_errors = 0
        for index, result in enumerate(vessels):
            mmsi = result["mmsi"]
            fingerprint = f"{source_time}:{result['lat_deg']}:{result['lon_deg']}:{result['sog_kts']}:{result['cog_deg']}"
            if self._last_seen.get(mmsi) == fingerprint:
                cycle_skipped += 1
                continue
            obs = {"phenomenonTime": _offset_phenomenon_time(source_time, index), "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": result}
            if dry_run:
                name = result.get("vesselName") or result.get("callSign") or ""
                print(f"    [DRY] {mmsi} {name[:24]:24s} lat={result['lat_deg']} lon={result['lon_deg']} sog={result['sog_kts']}kn")
                cycle_published += 1
            else:
                try:
                    self._post_observation(obs)
                    self._last_seen[mmsi] = fingerprint
                    self.stats["published"] += 1
                    cycle_published += 1
                except Exception as exc:
                    self.stats["errors"] += 1
                    cycle_errors += 1
                    if cycle_errors <= 3:
                        print(f"    [{ts}] ERR {mmsi}: {exc}")
                    elif cycle_errors == 4:
                        print(f"    [{ts}] (suppressing further errors this cycle)")
        self.stats["skipped"] += cycle_skipped
        self.stats["vessels_seen"] += cycle_published
        print(f"  [{ts}] Cycle complete: {cycle_published} published, {cycle_skipped} skipped, {cycle_errors} errors")
        return cycle_published

    def run(self, *, interval: float, dry_run: bool, once: bool, include_metadata: bool):
        bbox = self.config["bounding_box"]
        print("=" * 70); print(f"  {self.name}"); print("=" * 70)
        print(f"  Server:    {self._base_url}"); print(f"  BBox:      lat {bbox['lamin']}-{bbox['lamax']}, lon {bbox['lomin']}-{bbox['lomax']}"); print(f"  Max/cycle: {self.config.get('max_vessels_per_cycle', 60)}"); print(f"  Interval:  {interval}s"); print(f"  Dry run:   {dry_run}\n")
        if not dry_run:
            print("  Connecting to OSH server...")
            self.connect_with_retry()
        tick = 0
        consecutive_errors = 0
        start = time.time()
        try:
            while True:
                tick += 1
                print(f"\n  -- Cycle #{tick} --")
                count = self.publish_cycle(dry_run=dry_run, include_metadata=include_metadata)
                consecutive_errors = 0 if count > 0 else consecutive_errors + 1
                if consecutive_errors >= 5 and not dry_run:
                    print("  [WARN] Reconnecting...")
                    self.connect_with_retry()
                    self.stats["reconnects"] += 1
                    consecutive_errors = 0
                if once:
                    break
                sleep_time = max(0, start + tick * interval - time.time())
                print(f"  Sleeping {sleep_time:.0f}s until next cycle...")
                time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n  Ctrl+C -- stopping publisher.")
        elapsed = time.time() - start
        print("\n" + "=" * 70); print(f"  Summary ({elapsed:.0f}s elapsed)"); print(f"  Published:    {self.stats['published']}"); print(f"  Vessels seen: {self.stats['vessels_seen']}"); print(f"  Skipped:      {self.stats['skipped']}"); print(f"  Errors:       {self.stats['errors']}"); print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Digitraffic Marine AIS publisher for CSAPI/OSH")
    parser.add_argument("--interval", type=float, default=None, help="Seconds between publish cycles")
    parser.add_argument("--dry-run", action="store_true", help="Print observations but do not POST them")
    parser.add_argument("--once", action="store_true", help="Run one cycle then exit")
    parser.add_argument("--no-metadata", action="store_true", help="Skip vessel metadata enrichment endpoint")
    args = parser.parse_args()
    publisher = DigitrafficMarineAISPublisher()
    interval = args.interval if args.interval is not None else float(publisher.config.get("cadence_seconds", 300))
    publisher.run(interval=interval, dry_run=args.dry_run, once=args.once, include_metadata=not args.no_metadata)


if __name__ == "__main__":
    main()