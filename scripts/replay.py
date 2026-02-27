#!/usr/bin/env python3
"""
ODAS CSAPI Phase 4 — NDJSON Replay Engine

Replays pre-recorded observation and command NDJSON data against the OSH
SensorHub server in real-time (or at a configurable speed multiplier).

Features:
  - Multi-stream time-ordered replay across all 9 observation NDJSON files
  - Per-system routing: fan-out from per-file data to per-system datastreams
  - Timestamp rebasing: offsets all times to "now" for live look
  - Command replay alongside observations
  - Retry with exponential backoff
  - Graceful Ctrl+C shutdown
  - Configurable speed multiplier, loop mode, burst mode, and limit

Usage:
    python replay.py                       # 1× real-time
    python replay.py --speed 10            # 10× faster
    python replay.py --burst               # no pacing, max throughput
    python replay.py --burst --limit 50    # quick smoke-test (50 obs)
    python replay.py --loop                # loop forever
    python replay.py --dry-run             # parse & route without POSTing
"""

import argparse
import json
import signal
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ── Paths ────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIO_DIR = SCRIPT_DIR.parent / "scenarios" / "ft-huachuca-v2.3"
OBS_DIR = SCENARIO_DIR / "examples" / "sample_data" / "observations"
CMD_DIR = SCENARIO_DIR / "examples" / "sample_data" / "commands" / "http_create_payloads"
ID_MAP_PATH = SCRIPT_DIR / "id_map.json"

# ── NDJSON filename → datastream type suffix ─────────────────────
# Keys must match the id_map convention:  DS-{system}_{type}

FILE_TO_DS_TYPE = {
    "class_probabilities.ndjson": "classification_probabilities",
    "health.ndjson": "health",
    "lobs.ndjson": "lob",
    "scene_summary.ndjson": "scene_summary",
    "ssl_potential_sources.ndjson": "ssl_potential_sources",
    "sst_tracked_sources.ndjson": "sst_tracked_sources",
    "track_updates.ndjson": "track_updates",
    "triangulated_positions.ndjson": "triangulated_positions",
}

# system field value  →  id_map key prefix (lowercase with hyphens)
SYSTEM_KEY_MAP = {
    "AZ-MA-1": "az-ma-1",
    "AZ-MA-2": "az-ma-2",
    "AZ-MA-3": "az-ma-3",
    "AZ-MA-NET": "az-ma-net",
}

# ── Command file → controlstream type suffix ─────────────────────

CMD_FILE_TO_CS_TYPE = {
    "post_controlstream_odasControl_commands.ndjson": "odas_control",
    "post_controlstream_startStop_commands.ndjson": "start_stop",
    "post_controlstream_snapshot_commands.ndjson": "request_snapshot",
    "post_controlstream_calibration_commands.ndjson": "calibrate_orientation",
    "post_controlstream_networkMode_commands.ndjson": "network_mode",
}

# Per CS type, which system key prefixes to fan-out to
CMD_SYSTEM_MAP = {
    "odas_control": ["az-ma-1", "az-ma-2", "az-ma-3"],
    "start_stop": ["az-ma-1", "az-ma-2", "az-ma-3"],
    "request_snapshot": ["az-ma-1", "az-ma-2", "az-ma-3"],
    "calibrate_orientation": ["az-ma-1", "az-ma-2", "az-ma-3"],
    "network_mode": ["az-ma-net"],
}


class ReplayEngine:
    """Reads NDJSON observation / command files, routes each record to the
    correct server datastream / controlstream, and POSTs with real-time
    pacing (or burst mode)."""

    def __init__(
        self,
        server: str,
        auth: Tuple[str, str],
        speed: float = 1.0,
        loop: bool = False,
        burst: bool = False,
        dry_run: bool = False,
        skip_commands: bool = False,
        limit: int = 0,
    ):
        self.server = server.rstrip("/")
        self.speed = speed
        self.loop = loop
        self.burst = burst
        self.dry_run = dry_run
        self.skip_commands = skip_commands
        self.limit = limit
        self.session = requests.Session()
        self.session.auth = auth
        self.id_map: Dict[str, str] = {}
        self.running = True
        self._reset_stats()

        # Graceful shutdown on Ctrl+C
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    # ── helpers ──────────────────────────────────────────────────

    def _reset_stats(self):
        self.stats = {"posted": 0, "failed": 0, "retried": 0, "skipped": 0}

    def _shutdown(self, _signum, _frame):
        print("\n⏹  Shutting down gracefully...")
        self.running = False

    # ── id_map ───────────────────────────────────────────────────

    def load_id_map(self) -> bool:
        if not ID_MAP_PATH.exists():
            print(f"✗ id_map not found at {ID_MAP_PATH}")
            return False
        self.id_map = json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))
        ds_count = sum(1 for k in self.id_map if k.startswith("DS-"))
        cs_count = sum(1 for k in self.id_map if k.startswith("CS-"))
        print(f"✓ Loaded id_map: {len(self.id_map)} entries ({ds_count} DS, {cs_count} CS)")
        return True

    def resolve_ds_id(self, system: str, ds_type: str) -> Optional[str]:
        """system + type  ➜  server datastream ID."""
        prefix = SYSTEM_KEY_MAP.get(system)
        if not prefix:
            return None
        return self.id_map.get(f"DS-{prefix}_{ds_type}")

    def resolve_sf_id(self, logical_id: str) -> Optional[str]:
        """Map a logical samplingFeature ID to the server-assigned ID."""
        return self.id_map.get(logical_id)

    # ── load observations ────────────────────────────────────────

    def load_observations(self) -> List[Dict]:
        all_obs: List[Dict] = []
        for filename, ds_type in FILE_TO_DS_TYPE.items():
            filepath = OBS_DIR / filename
            if not filepath.exists():
                print(f"  ⚠ Missing: {filename}")
                continue
            lines = filepath.read_text(encoding="utf-8").strip().splitlines()
            count = 0
            for line_num, raw in enumerate(lines, 1):
                try:
                    obs = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"  ⚠ Bad JSON {filename}:{line_num}")
                    continue
                system = obs.get("system")
                if ds_type == "triangulated_positions":
                    system = "AZ-MA-NET"  # no system field in this file
                if not system:
                    continue
                all_obs.append({
                    "obs": obs,
                    "system": system,
                    "ds_type": ds_type,
                    "resultTime": obs.get("resultTime", ""),
                })
                count += 1
            print(f"  ✓ {filename}: {count} records")

        all_obs.sort(key=lambda x: x["resultTime"])
        print(f"\n✓ Total observations loaded: {len(all_obs)}")
        return all_obs

    # ── load commands ────────────────────────────────────────────

    def load_commands(self) -> List[Dict]:
        all_cmds: List[Dict] = []
        if not CMD_DIR.exists():
            return all_cmds
        for filename, cs_type in CMD_FILE_TO_CS_TYPE.items():
            filepath = CMD_DIR / filename
            if not filepath.exists():
                continue
            lines = filepath.read_text(encoding="utf-8").strip().splitlines()
            for raw in lines:
                try:
                    cmd = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                all_cmds.append({"cmd": cmd, "cs_type": cs_type})
            print(f"  ✓ Commands: {filename}: {len(lines)} entries")
        print(f"✓ Total commands loaded: {len(all_cmds)}")
        return all_cmds

    # ── observation body preparation ─────────────────────────────

    @staticmethod
    def _parse_iso(s: str) -> datetime:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    @staticmethod
    def _format_iso(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    def prepare_body(self, entry: Dict, time_offset: timedelta) -> Dict:
        """Strip routing metadata, rebase timestamps, map samplingFeature."""
        obs = dict(entry["obs"])

        # Strip routing-only field
        obs.pop("system", None)

        # Map samplingFeature@id  →  server ID (if available)
        sf_id = obs.get("samplingFeature@id")
        if sf_id:
            server_id = self.resolve_sf_id(sf_id)
            if server_id:
                obs["samplingFeature@id"] = server_id

        # Rebase resultTime / phenomenonTime
        for field in ("resultTime", "phenomenonTime"):
            val = obs.get(field)
            if val and isinstance(val, str):
                try:
                    dt = self._parse_iso(val) + time_offset
                    obs[field] = self._format_iso(dt)
                except ValueError:
                    pass

        # Rebase result.timestamp (epoch seconds)
        result = obs.get("result")
        if isinstance(result, dict) and "timestamp" in result:
            result["timestamp"] = result["timestamp"] + time_offset.total_seconds()

        return obs

    # ── HTTP posting ─────────────────────────────────────────────

    def _post(self, url: str, body: Dict, retries: int = 3) -> bool:
        if self.dry_run:
            self.stats["skipped"] += 1
            return True
        for attempt in range(retries):
            try:
                resp = self.session.post(
                    url,
                    data=json.dumps(body),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=10,
                )
                if resp.status_code in (200, 201, 204):
                    self.stats["posted"] += 1
                    return True
                if resp.status_code == 400:
                    self.stats["failed"] += 1
                    if self.stats["failed"] <= 5:
                        print(f"  ✗ 400 → {url}")
                        print(f"    {resp.text[:300]}")
                    return False
                # Retryable error
                if attempt < retries - 1:
                    self.stats["retried"] += 1
                    time.sleep(2 ** attempt)
                else:
                    self.stats["failed"] += 1
                    if self.stats["failed"] <= 10:
                        print(f"  ✗ {resp.status_code} → {url}")
                    return False
            except requests.RequestException:
                if attempt < retries - 1:
                    self.stats["retried"] += 1
                    time.sleep(2 ** attempt)
                else:
                    self.stats["failed"] += 1
                    return False
        return False

    def post_observation(self, ds_id: str, body: Dict) -> bool:
        return self._post(f"{self.server}/datastreams/{ds_id}/observations", body)

    def post_command(self, cs_id: str, body: Dict) -> bool:
        return self._post(f"{self.server}/controlstreams/{cs_id}/commands", body, retries=1)

    # ── replay loops ─────────────────────────────────────────────

    def replay_observations(self, observations: List[Dict]):
        if not observations:
            print("No observations to replay.")
            return

        total = len(observations)
        if self.limit:
            total = min(total, self.limit)

        first_time = self._parse_iso(observations[0]["resultTime"])
        now = datetime.now(timezone.utc)
        time_offset = now - first_time
        first_epoch = first_time.timestamp()
        replay_start = time.monotonic()
        unresolved: set = set()

        print(f"\n{'═'*60}")
        print(f"▶  Replaying {total} observations")
        mode = "burst" if self.burst else f"{self.speed}×"
        print(f"   Mode: {mode}  |  Loop: {self.loop}")
        print(f"   Source window : {observations[0]['resultTime']} → {observations[min(total,len(observations))-1]['resultTime']}")
        print(f"   Rebased to   : {self._format_iso(now)}")
        print(f"{'═'*60}\n")

        for i in range(total):
            if not self.running:
                break
            entry = observations[i]

            # Resolve target datastream
            ds_id = self.resolve_ds_id(entry["system"], entry["ds_type"])
            if not ds_id:
                key = f"DS-{SYSTEM_KEY_MAP.get(entry['system'], '?')}_{entry['ds_type']}"
                if key not in unresolved:
                    print(f"  ⚠ Unresolved DS: {key}")
                    unresolved.add(key)
                self.stats["skipped"] += 1
                continue

            # Time pacing (skip in burst mode)
            if not self.burst:
                obs_time = self._parse_iso(entry["resultTime"])
                scheduled = (obs_time.timestamp() - first_epoch) / self.speed
                elapsed = time.monotonic() - replay_start
                wait = scheduled - elapsed
                while wait > 0 and self.running:
                    time.sleep(min(wait, 0.1))
                    wait -= 0.1
                if not self.running:
                    break

            body = self.prepare_body(entry, time_offset)
            self.post_observation(ds_id, body)

            # Progress
            if (i + 1) % 200 == 0 or i == total - 1:
                pct = (i + 1) / total * 100
                el = time.monotonic() - replay_start
                print(
                    f"  [{pct:5.1f}%] {i+1}/{total}  "
                    f"posted={self.stats['posted']}  "
                    f"failed={self.stats['failed']}  "
                    f"elapsed={el:.1f}s"
                )

    def replay_commands(self, commands: List[Dict]):
        if not commands:
            return
        print(f"\n{'─'*40}\nReplaying {len(commands)} commands\n{'─'*40}")
        for entry in commands:
            if not self.running:
                break
            cs_type = entry["cs_type"]
            body = dict(entry["cmd"])
            # Add issueTime for the server
            body["issueTime"] = self._format_iso(datetime.now(timezone.utc))
            targets = CMD_SYSTEM_MAP.get(cs_type, [])
            for sys_prefix in targets:
                cs_id = self.id_map.get(f"CS-{sys_prefix}_{cs_type}")
                if cs_id:
                    ok = self.post_command(cs_id, body)
                    if ok and not self.dry_run:
                        print(f"  ✓ {cs_type} → {sys_prefix}")
                else:
                    self.stats["skipped"] += 1

    # ── main entry point ─────────────────────────────────────────

    def run(self):
        hdr = (
            f"{'='*60}\n"
            f"ODAS CSAPI Phase 4 — NDJSON Replay Engine\n"
            f"Server : {self.server}\n"
            f"Mode   : {'burst' if self.burst else f'{self.speed}×'}  "
            f"Loop: {self.loop}  Dry-run: {self.dry_run}\n"
            f"{'='*60}"
        )
        print(hdr)

        # Connectivity check
        try:
            r = self.session.get(
                self.server, headers={"Accept": "application/json"}, timeout=10
            )
            if r.status_code != 200:
                print(f"✗ Server returned {r.status_code}")
                sys.exit(1)
            print("✓ Server connected")
        except requests.ConnectionError as e:
            print(f"✗ Cannot connect: {e}")
            sys.exit(1)

        if not self.load_id_map():
            sys.exit(1)

        # Load data
        print(f"\n{'─'*40}\nLoading observation files\n{'─'*40}")
        observations = self.load_observations()

        commands: List[Dict] = []
        if not self.skip_commands:
            print(f"\n{'─'*40}\nLoading command files\n{'─'*40}")
            commands = self.load_commands()

        # Replay loop
        iteration = 0
        while self.running:
            iteration += 1
            if iteration > 1:
                print(f"\n{'═'*60}\n▶  Loop iteration {iteration}\n{'═'*60}")

            self.replay_observations(observations)

            if not self.skip_commands and commands and self.running:
                self.replay_commands(commands)

            if not self.loop:
                break
            if self.running:
                print("\n⟳  Looping… (Ctrl+C to stop)")
                self._reset_stats()

        # Summary
        print(f"\n{'='*60}")
        print(
            f"Replay {'stopped' if not self.running else 'complete'}\n"
            f"  Posted  : {self.stats['posted']}\n"
            f"  Failed  : {self.stats['failed']}\n"
            f"  Retried : {self.stats['retried']}\n"
            f"  Skipped : {self.stats['skipped']}"
        )
        print(f"{'='*60}")


def main():
    p = argparse.ArgumentParser(description="ODAS CSAPI Phase 4 — NDJSON Replay Engine")
    p.add_argument("--server", default="http://45.55.99.236:8080/sensorhub/api")
    p.add_argument("--user", default="ogc")
    p.add_argument("--password", default="ogc")
    p.add_argument("--speed", type=float, default=1.0,
                   help="Replay speed multiplier (default: 1.0 = real-time)")
    p.add_argument("--burst", action="store_true",
                   help="Disable pacing — POST as fast as possible")
    p.add_argument("--loop", action="store_true",
                   help="Loop replay continuously until Ctrl+C")
    p.add_argument("--limit", type=int, default=0,
                   help="Replay only the first N observations (0 = all)")
    p.add_argument("--dry-run", action="store_true",
                   help="Parse and route without sending HTTP requests")
    p.add_argument("--skip-commands", action="store_true",
                   help="Replay observations only, skip commands")
    args = p.parse_args()

    ReplayEngine(
        server=args.server,
        auth=(args.user, args.password),
        speed=args.speed,
        loop=args.loop,
        burst=args.burst,
        dry_run=args.dry_run,
        skip_commands=args.skip_commands,
        limit=args.limit,
    ).run()


if __name__ == "__main__":
    main()
