#!/usr/bin/env python3
"""Publish curated Finnish FMI weather observations."""

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
from publishers.fmi_common import fetch_simple_observation


STORED_QUERY = "fmi::observations::weather::simple"
DS_OUTPUT_NAME = "fmiWeatherObs"
PARAMETERS = ["t2m", "rh", "ws_10min", "wg_10min", "wd_10min", "r_1h", "p_sea", "vis", "n_man", "wawa"]


def _quantity(value):
    return "NaN" if value is None else value


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as file:
        return json.load(file)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _system_uid(station_id: str) -> str:
    return f"urn:os4csapi:system:fmi-weather:{_uid_token(station_id)}:v1"


def fetch_latest_reading(station: dict) -> dict | None:
    latest = fetch_simple_observation(STORED_QUERY, station, hours=3, parameters=PARAMETERS)
    if not latest:
        return None
    values = latest["values"]
    result = {
        "stationId": station["stationId"],
        "stationName": station["name"],
        "airTemperature_c": _quantity(values.get("t2m")),
        "relativeHumidity_pct": _quantity(values.get("rh")),
        "windSpeed_ms": _quantity(values.get("ws_10min")),
        "windGust_ms": _quantity(values.get("wg_10min")),
        "windDirection_deg": _quantity(values.get("wd_10min")),
        "precipitation1h_mm": _quantity(values.get("r_1h")),
        "pressureSeaLevel_hpa": _quantity(values.get("p_sea")),
        "sourceParametersJson": json.dumps(latest["sourceValues"], ensure_ascii=False, separators=(",", ":")),
        "sourceUrl": latest["sourceUrl"],
    }
    return {"phenomenonTime": latest["phenomenonTime"], "result": result, "dedupeKey": f"{station['stationId']}|{latest['phenomenonTime']}|{result['airTemperature_c']}|{result['relativeHumidity_pct']}"}


class FMIWeatherPublisher:
    name = "FMI Weather Publisher"

    def __init__(self, station_filter: list[str] | None = None):
        self.stations = _load_stations()
        if station_filter:
            wanted = {item.strip() for item in station_filter if item.strip()}
            self.stations = [station for station in self.stations if station["stationId"] in wanted]
        self.osh_address = os.environ.get("OSH_ADDRESS", ""); self.osh_port = int(os.environ.get("OSH_PORT", "443")); self.osh_user = os.environ.get("OSH_USER", ""); self.osh_pass = os.environ.get("OSH_PASS", ""); self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit("ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.")
        self._base_url = os.environ.get("OSH_BASE_URL", f"https://{self.osh_address}/{self.osh_root}/api"); self._auth = "Basic " + base64.b64encode(f"{self.osh_user}:{self.osh_pass}".encode()).decode(); self._ds_ids: dict[str, str] = {}; self._seen: set[str] = set(); self._request_delay = float(os.environ.get("FMI_WEATHER_REQUEST_DELAY", "1.0")); self.stats = {"published": 0, "errors": 0, "skipped": 0}

    def _raw_datastream_ids(self, sys_id: str) -> dict[str, str]:
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with urlopen(Request(f"{self._base_url}/systems/{sys_id}/datastreams", headers={"Accept": "application/json", "Authorization": self._auth}), timeout=30, context=ctx) as resp:
            text = resp.read().decode()
        found: dict[str, str] = {}; current_id = None
        for key, value in re.findall(r'"(id|outputName)"\s*:\s*"([^"]+)"', text):
            if key == "id": current_id = value
            elif key == "outputName" and current_id: found[value] = current_id; current_id = None
        return found

    def connect(self):
        self._ds_ids.clear(); connected = 0
        for station in self.stations:
            sys_id = find_by_uid(self._base_url, self._auth, "systems", _system_uid(station["stationId"]), no_cache=True)
            if not sys_id:
                print(f"  [WARN] System not found for station {station['stationId']}"); continue
            try:
                ds_list = api_get(self._base_url, f"systems/{sys_id}/datastreams", self._auth); streams = {item.get("outputName", ""): item.get("id") for item in (ds_list or {}).get("items", [])}
            except Exception:
                streams = self._raw_datastream_ids(sys_id)
            ds_id = streams.get(DS_OUTPUT_NAME)
            if not ds_id:
                print(f"  [WARN] Datastream {DS_OUTPUT_NAME} not found for station {station['stationId']}"); continue
            self._ds_ids[station["stationId"]] = ds_id; connected += 1; print(f"  Connected: {station['stationId']} -> sys={sys_id} ds={ds_id}")
        print(f"  Ready: {connected}/{len(self.stations)} stations connected")
        if connected == 0: raise RuntimeError("No FMI weather stations connected")

    def _post_observation(self, ds_id: str, obs: dict):
        url = f"{self._base_url}/datastreams/{ds_id}/observations"; body = json.dumps(obs).encode(); ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        req = Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": self._auth, "Host": self.osh_address})
        try:
            with urlopen(req, timeout=30, context=ctx) as resp:
                if resp.status not in (200, 201, 204): raise RuntimeError(f"HTTP {resp.status} POST {url}")
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} POST {url}: {exc.read().decode('utf-8', errors='replace')[:500]}") from exc

    def publish_cycle(self, dry_run: bool = False):
        now = datetime.now(timezone.utc); ts_label = now.strftime("%H:%M:%S")
        for station in self.stations:
            station_id = station["stationId"]; ds_id = self._ds_ids.get(station_id)
            if not dry_run and not ds_id: self.stats["skipped"] += 1; continue
            try: latest = fetch_latest_reading(station)
            except Exception as exc: self.stats["errors"] += 1; print(f"  [{ts_label}] {station_id}: FETCH ERR {exc}"); continue
            if not latest: self.stats["skipped"] += 1; print(f"  [{ts_label}] {station_id}: no data"); continue
            if latest["dedupeKey"] in self._seen: self.stats["skipped"] += 1; print(f"  [{ts_label}] {station_id}: unchanged, skipping"); continue
            obs = {"phenomenonTime": latest["phenomenonTime"], "resultTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "result": latest["result"]}; label = f"air={latest['result']['airTemperature_c']}C rh={latest['result']['relativeHumidity_pct']}% @ {latest['phenomenonTime']}"
            if dry_run: print(f"  [{ts_label}] {station_id}: [DRY] {label}"); self._seen.add(latest["dedupeKey"])
            else:
                try: self._post_observation(ds_id, obs); self.stats["published"] += 1; self._seen.add(latest["dedupeKey"]); print(f"  [{ts_label}] {station_id}: OK {label}")
                except Exception as exc: self.stats["errors"] += 1; print(f"  [{ts_label}] {station_id}: ERR {exc}")
            time.sleep(self._request_delay)

    def run(self, *, interval: float = 600.0, dry_run: bool = False, once: bool = False):
        print("=" * 70); print(f"  {self.name}"); print("=" * 70); print(f"  Server:    {self._base_url}"); print(f"  Stations:  {len(self.stations)}"); print(f"  Dry run:   {dry_run}\n")
        if not dry_run: self.connect()
        try:
            while True:
                self.publish_cycle(dry_run=dry_run)
                if once: break
                time.sleep(interval)
        finally:
            print("\n" + "=" * 70); print(f"  Published:  {self.stats['published']}"); print(f"  Skipped:    {self.stats['skipped']}"); print(f"  Errors:     {self.stats['errors']}"); print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="FMI weather publisher for CSAPI/OSH"); parser.add_argument("--interval", type=float, default=600.0); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--once", action="store_true"); parser.add_argument("--stations", type=str, default=None); args = parser.parse_args(); FMIWeatherPublisher(station_filter=args.stations.split(",") if args.stations else None).run(interval=args.interval, dry_run=args.dry_run, once=args.once)


if __name__ == "__main__":
    main()