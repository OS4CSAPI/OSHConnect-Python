#!/usr/bin/env python3
"""
base.py — Shared publisher base class for all OSHConnect CSAPI publishers.

Encapsulates the proven ISS publisher pattern:
  - OSHConnect connection with exponential backoff + jitter
  - System/datastream discovery by UID + name
  - Observation POST via Datastream.insert_observation_dict()
  - Stats tracking, reconnection on consecutive failures
  - Common CLI arguments (--dry-run, --once, --interval)

Subclasses implement:
  - fetch()         → fetch data from external source
  - build_obs()     → convert fetched data to observation dict(s)
  - configure_cli() → add source-specific CLI arguments (optional)
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from oshconnect import OSHConnect, Node, Datastream

try:
    from oshconnect import OSHConnect as _OSHConnect, Node as _Node, Datastream as _Datastream
    _HAS_OSHCONNECT = True
except ImportError:
    _OSHConnect = _Node = _Datastream = None  # type: ignore[assignment,misc]
    _HAS_OSHCONNECT = False


class PublisherBase:
    """Common base for all OSHConnect CSAPI publishers."""

    # ── Subclass must set these ──────────────────────────────────────
    name: str = "unnamed-publisher"       # Human-readable name for logging
    system_uid: str = ""                  # urn:os4csapi:system:...
    ds_name: str = ""                     # Datastream name to discover

    # ── Connection config (from env vars) ────────────────────────────
    osh_address: str = ""
    osh_port: int = 443
    osh_user: str = ""
    osh_pass: str = ""
    osh_root: str = "sensorhub"

    # ── Runtime state ────────────────────────────────────────────────
    app: OSHConnect | None = None
    node: Node | None = None
    datastream: Datastream | None = None
    stats: dict[str, int]

    # Reconnect after this many consecutive errors
    reconnect_threshold: int = 5

    def __init__(self):
        self.osh_address = os.environ.get("OSH_ADDRESS", "")
        self.osh_port = int(os.environ.get("OSH_PORT", "443"))
        self.osh_user = os.environ.get("OSH_USER", "")
        self.osh_pass = os.environ.get("OSH_PASS", "")
        self.osh_root = os.environ.get("OSH_ROOT", "sensorhub")
        if not self.osh_address or not self.osh_user or not self.osh_pass:
            raise SystemExit(
                "ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.\n"
                "  Copy publishers/.env.example → .env and set your server details."
            )
        self.stats = {"published": 0, "errors": 0, "reconnects": 0}

    # ── Abstract methods (subclass MUST implement) ───────────────────

    def fetch(self) -> Any:
        """Fetch data from the external source. Return whatever build_obs needs."""
        raise NotImplementedError

    def build_obs(self, data: Any) -> dict | list[dict]:
        """Convert fetched data into one or more observation dicts.

        Each dict must have:
          { "phenomenonTime": "...", "resultTime": "...", "result": {...} }
        Return a single dict or a list of dicts.
        """
        raise NotImplementedError

    # ── Optional hooks ───────────────────────────────────────────────

    def configure_cli(self, parser: argparse.ArgumentParser):
        """Add source-specific CLI arguments. Override in subclass."""
        pass

    def on_startup(self, args: argparse.Namespace):
        """Called once after connection, before the main loop. Override for init tasks."""
        pass

    def on_publish(self, obs: dict):
        """Called after each successful publish. Override for custom logging."""
        pass

    # ── OSHConnect connection ────────────────────────────────────────

    def _discover_system_ds(self):
        """Find system by UID and datastream by name. Populates self.datastream."""
        from oshconnect.csapi4py.constants import APIResourceTypes

        if not self.app._systems:
            self.app.discover_systems()

            # Patch resource IDs (OSHConnect-Python bug workaround)
            raw_res = self.node.get_api_helper().retrieve_resource(
                APIResourceTypes.SYSTEM, req_headers={})
            if raw_res.ok:
                uid_to_id = {}
                for item in raw_res.json().get("items", []):
                    uid = item.get("properties", {}).get("uid", "")
                    rid = item.get("id", "")
                    if uid and rid:
                        uid_to_id[uid] = rid
                for s in self.app._systems:
                    if s.urn in uid_to_id:
                        s._resource_id = uid_to_id[s.urn]

        # Find system
        system = None
        for s in self.app._systems:
            if s.urn == self.system_uid:
                system = s
                break
        if system is None:
            available = [s.urn for s in self.app._systems]
            raise RuntimeError(
                f"System '{self.system_uid}' not found. Available: {available}")

        # Find datastream
        if not hasattr(self.node, '_mqtt_client'):
            self.node._mqtt_client = None

        ds_resources = system.discover_datastreams()
        ds = None
        for res in ds_resources:
            if res.name == self.ds_name:
                ds = _Datastream(parent_node=self.node, datastream_resource=res)
                break

        if ds is None:
            available = [r.name for r in ds_resources]
            raise RuntimeError(
                f"Datastream '{self.ds_name}' not found for system '{self.system_uid}'. "
                f"Available: {available}")

        self.datastream = ds
        return system, ds

    def connect(self):
        """Connect to OSH server and discover system + datastream."""
        if not _HAS_OSHCONNECT:
            print("  FATAL: oshconnect package not found. Install with:")
            print("    pip install git+https://github.com/OS4CSAPI/OSHConnect-Python.git")
            sys.exit(1)

        self.app = _OSHConnect(self.name)
        self.node = _Node(
            protocol="https",
            address=self.osh_address,
            port=self.osh_port,
            username=self.osh_user,
            password=self.osh_pass,
            server_root=self.osh_root,
        )
        self.app.add_node(self.node)

        if not hasattr(self.node, '_mqtt_client'):
            self.node._mqtt_client = None

        system, ds = self._discover_system_ds()
        print(f"  Connected: system={system.urn}, ds={ds._underlying_resource.name} "
              f"(id={ds.get_id()})")
        return system, ds

    def connect_with_retry(self, max_attempts: int = 10, base_delay: float = 5.0,
                           max_delay: float = 120.0):
        """Connect with exponential backoff + jitter."""
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
        raise RuntimeError("connect_with_retry: exhausted all attempts")

    # ── Observation publishing ───────────────────────────────────────

    def publish_obs(self, obs: dict) -> bool:
        """POST a single observation dict to the datastream. Returns True on success."""
        if self.datastream is None:
            raise RuntimeError("Not connected — call connect() first")
        try:
            self.datastream.insert_observation_dict(obs)
            self.stats["published"] += 1
            self.on_publish(obs)
            return True
        except Exception as e:
            self.stats["errors"] += 1
            raise

    # ── Main loop ────────────────────────────────────────────────────

    def run(self, *, interval: float = 60.0, dry_run: bool = False,
            once: bool = False):
        """Main publisher loop: fetch → build → publish → sleep."""
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"  Server:      https://{self.osh_address}:{self.osh_port}/{self.osh_root}/api")
        print(f"  System UID:  {self.system_uid}")
        print(f"  Datastream:  {self.ds_name}  (every {interval}s)")
        print(f"  Dry run:     {dry_run}")
        print()

        # Connect
        if not dry_run:
            print("  Connecting to OSH server...")
            self.connect_with_retry()

        # Startup hook
        self.on_startup(argparse.Namespace(
            interval=interval, dry_run=dry_run, once=once))

        tick = 0
        consecutive_errors = 0
        start_time = time.time()

        print()
        try:
            while True:
                now = datetime.now(timezone.utc)
                tick += 1

                # Fetch
                try:
                    data = self.fetch()
                except Exception as e:
                    print(f"  [ERR] Fetch failed: {e}")
                    consecutive_errors += 1
                    if not once:
                        time.sleep(interval)
                    continue

                # Build observation(s)
                try:
                    obs_list = self.build_obs(data)
                    if isinstance(obs_list, dict):
                        obs_list = [obs_list]
                except Exception as e:
                    print(f"  [ERR] Build failed: {e}")
                    consecutive_errors += 1
                    if not once:
                        time.sleep(interval)
                    continue

                # Publish
                ts = now.strftime("%H:%M:%S")
                for obs in obs_list:
                    if dry_run:
                        r = obs.get("result", {})
                        summary = ", ".join(f"{k}={v}" for k, v in list(r.items())[:5])
                        print(f"  [{ts}] #{tick:5d} [DRY] {summary}")
                    else:
                        try:
                            self.publish_obs(obs)
                            consecutive_errors = 0
                            r = obs.get("result", {})
                            summary = ", ".join(f"{k}={v}" for k, v in list(r.items())[:4])
                            print(f"  [{ts}] #{tick:5d} OK  {summary}")
                        except Exception as e:
                            consecutive_errors += 1
                            print(f"  [{ts}] #{tick:5d} ERR {e}")

                # Reconnect if too many errors
                if consecutive_errors >= self.reconnect_threshold and not dry_run:
                    print(f"  [WARN] {self.reconnect_threshold} consecutive errors, reconnecting...")
                    try:
                        self.connect_with_retry()
                        self.stats["reconnects"] += 1
                        consecutive_errors = 0
                    except Exception as re_err:
                        print(f"  [ERR] Reconnect failed: {re_err}")

                if once:
                    break

                # Drift-compensated sleep
                next_tick = start_time + tick * interval
                sleep_time = next_tick - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n\n  Ctrl+C — stopping publisher.")

        # Summary
        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print(f"  Summary ({elapsed:.0f}s elapsed)")
        print(f"  Published:    {self.stats['published']}")
        print(f"  Errors:       {self.stats['errors']}")
        print(f"  Reconnects:   {self.stats['reconnects']}")
        print("=" * 70)

    # ── CLI entry point ──────────────────────────────────────────────

    @classmethod
    def cli(cls):
        """Build CLI parser and run. Call from `if __name__ == '__main__':`."""
        instance = cls()
        parser = argparse.ArgumentParser(description=instance.name)
        parser.add_argument("--interval", type=float, default=60.0,
                            help="Seconds between publish cycles (default: 60)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Print observations but don't POST them")
        parser.add_argument("--once", action="store_true",
                            help="Publish a single cycle then exit")

        # Let subclass add its own args
        instance.configure_cli(parser)

        args = parser.parse_args()
        instance.run(
            interval=args.interval,
            dry_run=args.dry_run,
            once=args.once,
        )
