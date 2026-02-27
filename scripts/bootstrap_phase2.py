#!/usr/bin/env python3
"""
ODAS CSAPI Phase 2 Bootstrap Script

Creates all 22 datastream templates and 13 controlstream templates on the
OSH SensorHub server, using the id_map from Phase 1.

Datastreams (22):
  - 7 types per node (SSL, SST, LOB, track_updates, classification_probs,
    health, scene_summary) × 3 nodes = 21
  - 1 network-level triangulated_positions on AZ-MA-NET

Controlstreams (13):
  - 4 types per node (calibrate_orientation, odas_control, request_snapshot,
    start_stop) × 3 nodes = 12
  - 1 network-level network_mode on AZ-MA-NET

Usage:
    python bootstrap_phase2.py [--server URL] [--dry-run]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# ── Paths ────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
SCENARIO_DIR = SCRIPT_DIR.parent / "scenarios" / "ft-huachuca-v2.3"
DS_DIR = SCENARIO_DIR / "examples" / "create_datastreams"
CS_DIR = SCENARIO_DIR / "examples" / "create_controlstreams"
ID_MAP_PATH = SCRIPT_DIR / "id_map.json"

# ── Datastream file→system mapping ───────────────────────────────
#
# Each datastream is POSTed to /systems/{parent}/datastreams
# The parent system is determined by the filename prefix.

DATASTREAM_FILES: List[Tuple[str, str]] = [
    # (parent_system_logical_id, filename)
    # AZ-MA-1
    ("AZ-MA-1", "create_datastream_az-ma-1_ssl_potential_sources.json"),
    ("AZ-MA-1", "create_datastream_az-ma-1_sst_tracked_sources.json"),
    ("AZ-MA-1", "create_datastream_az-ma-1_lob.json"),
    ("AZ-MA-1", "create_datastream_az-ma-1_track_updates.json"),
    ("AZ-MA-1", "create_datastream_az-ma-1_classification_probabilities.json"),
    ("AZ-MA-1", "create_datastream_az-ma-1_health.json"),
    ("AZ-MA-1", "create_datastream_az-ma-1_scene_summary.json"),
    # AZ-MA-2
    ("AZ-MA-2", "create_datastream_az-ma-2_ssl_potential_sources.json"),
    ("AZ-MA-2", "create_datastream_az-ma-2_sst_tracked_sources.json"),
    ("AZ-MA-2", "create_datastream_az-ma-2_lob.json"),
    ("AZ-MA-2", "create_datastream_az-ma-2_track_updates.json"),
    ("AZ-MA-2", "create_datastream_az-ma-2_classification_probabilities.json"),
    ("AZ-MA-2", "create_datastream_az-ma-2_health.json"),
    ("AZ-MA-2", "create_datastream_az-ma-2_scene_summary.json"),
    # AZ-MA-3
    ("AZ-MA-3", "create_datastream_az-ma-3_ssl_potential_sources.json"),
    ("AZ-MA-3", "create_datastream_az-ma-3_sst_tracked_sources.json"),
    ("AZ-MA-3", "create_datastream_az-ma-3_lob.json"),
    ("AZ-MA-3", "create_datastream_az-ma-3_track_updates.json"),
    ("AZ-MA-3", "create_datastream_az-ma-3_classification_probabilities.json"),
    ("AZ-MA-3", "create_datastream_az-ma-3_health.json"),
    ("AZ-MA-3", "create_datastream_az-ma-3_scene_summary.json"),
    # Network
    ("AZ-MA-NET", "create_datastream_az-ma-net_triangulated_positions.json"),
]

# ── Controlstream file→system mapping ────────────────────────────
#
# Controlstreams reference the ACTUATOR subsystem via system@link.
# We POST to /systems/{actuator}/controlstreams.

CONTROLSTREAM_FILES: List[Tuple[str, str]] = [
    # (actuator_system_logical_id, filename)
    # AZ-MA-1
    ("AZ-MA-1-ACTUATOR", "create_controlstream_az-ma-1_calibrate_orientation.json"),
    ("AZ-MA-1-ACTUATOR", "create_controlstream_az-ma-1_odas_control.json"),
    ("AZ-MA-1-ACTUATOR", "create_controlstream_az-ma-1_request_snapshot.json"),
    ("AZ-MA-1-ACTUATOR", "create_controlstream_az-ma-1_start_stop.json"),
    # AZ-MA-2
    ("AZ-MA-2-ACTUATOR", "create_controlstream_az-ma-2_calibrate_orientation.json"),
    ("AZ-MA-2-ACTUATOR", "create_controlstream_az-ma-2_odas_control.json"),
    ("AZ-MA-2-ACTUATOR", "create_controlstream_az-ma-2_request_snapshot.json"),
    ("AZ-MA-2-ACTUATOR", "create_controlstream_az-ma-2_start_stop.json"),
    # AZ-MA-3
    ("AZ-MA-3-ACTUATOR", "create_controlstream_az-ma-3_calibrate_orientation.json"),
    ("AZ-MA-3-ACTUATOR", "create_controlstream_az-ma-3_odas_control.json"),
    ("AZ-MA-3-ACTUATOR", "create_controlstream_az-ma-3_request_snapshot.json"),
    ("AZ-MA-3-ACTUATOR", "create_controlstream_az-ma-3_start_stop.json"),
    # Network
    ("AZ-MA-NET", "create_controlstream_az-ma-net_network_mode.json"),
]


# ─────────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────────


def rewrite_links(data: dict, id_map: Dict[str, str]) -> dict:
    """
    Recursively rewrite @link href values using the id_map.
    Replaces paths like /sensorhub/api/deployments/AZ-DEP-AOI-001
    with /sensorhub/api/deployments/<server_id>.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "href" and isinstance(value, str):
                for logical_id, server_id in id_map.items():
                    pattern = f"/{re.escape(logical_id)}$"
                    if re.search(pattern, value):
                        data[key] = re.sub(pattern, f"/{server_id}", value)
                        break
            else:
                rewrite_links(value, id_map)
    elif isinstance(data, list):
        for item in data:
            rewrite_links(item, id_map)
    return data


def ensure_type_first(obj: Any) -> Any:
    """
    Recursively reorder dicts so that 'type' is the first key.
    OSH SensorHub's SWE JSON parser requires 'type' as the first
    property in every SWE component object.
    Also injects elementCount into DataArray fields if missing
    (required by OSH SensorHub).
    """
    if isinstance(obj, dict):
        # Reorder children first
        reordered_values = {k: ensure_type_first(v) for k, v in obj.items()}

        # Inject elementCount for DataArray if missing
        if reordered_values.get("type") == "DataArray" and "elementCount" not in reordered_values:
            reordered_values["elementCount"] = {"type": "Count"}

        # Move 'type' to front if present
        if "type" in reordered_values:
            result = {"type": reordered_values.pop("type")}
            result.update(reordered_values)
            return result
        return reordered_values
    elif isinstance(obj, list):
        return [ensure_type_first(item) for item in obj]
    return obj


def transform_datastream(data: dict) -> dict:
    """
    Transform a datastream template to the format OSH SensorHub requires:
      - Rename schema.resultSchema → schema.recordSchema
      - Change schema.obsFormat → "application/swe+json"
      - Reorder SWE fields so 'type' is always the first property
      - Add outputName if missing (derived from name)
    """
    schema = data.get("schema", {})

    # Rename resultSchema → recordSchema
    if "resultSchema" in schema:
        schema["recordSchema"] = schema.pop("resultSchema")

    # Fix obsFormat
    if schema.get("obsFormat") == "application/json":
        schema["obsFormat"] = "application/swe+json"

    # Ensure 'type' is first key in all SWE component objects
    if "recordSchema" in schema:
        schema["recordSchema"] = ensure_type_first(schema["recordSchema"])

    # Add outputName if missing (derive from name via snake_case)
    if "outputName" not in data and "name" in data:
        name = data["name"]
        output_name = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
        data["outputName"] = output_name

    return data


def transform_controlstream(data: dict) -> dict:
    """
    Transform a controlstream template to the format OSH SensorHub requires:
      - Change schema.commandFormat → "application/swe+json"
      - Reorder SWE fields so 'type' is always the first property
    (parametersSchema and inputName are already correct in the templates.)
    """
    schema = data.get("schema", {})

    # Fix commandFormat
    if schema.get("commandFormat") == "application/json":
        schema["commandFormat"] = "application/swe+json"

    # Ensure 'type' is first key in all SWE component objects
    if "parametersSchema" in schema:
        schema["parametersSchema"] = ensure_type_first(schema["parametersSchema"])

    return data


# ─────────────────────────────────────────────────────────────────
# Server interaction
# ─────────────────────────────────────────────────────────────────


class Phase2Bootstrap:
    def __init__(self, server_base: str, auth: Tuple[str, str], dry_run: bool = False):
        self.server = server_base.rstrip("/")
        self.auth = auth
        self.dry_run = dry_run
        self.id_map: Dict[str, str] = {}
        self.session = requests.Session()
        self.session.auth = auth
        self.stats = {"created": 0, "failed": 0, "skipped": 0}

    def load_id_map(self):
        """Load Phase 1 id_map."""
        if not ID_MAP_PATH.exists():
            print(f"✗ id_map not found at {ID_MAP_PATH}")
            print("  Run bootstrap.py (Phase 1) first.")
            sys.exit(1)
        self.id_map = json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))
        print(f"✓ Loaded id_map with {len(self.id_map)} entries")

    def post_resource(
        self,
        endpoint: str,
        data: dict,
        content_type: str = "application/json",
        logical_id: str = "",
    ) -> Optional[str]:
        """POST a resource and return the server-assigned ID."""
        url = f"{self.server}/{endpoint}"

        if self.dry_run:
            print(f"  [DRY-RUN] POST {endpoint} → {logical_id}")
            self.stats["skipped"] += 1
            return None  # Don't return fake IDs — avoids id_map contamination

        resp = self.session.post(
            url,
            data=json.dumps(data),
            headers={
                "Content-Type": content_type,
                "Accept": "application/json",
            },
        )

        if resp.status_code == 201:
            location = resp.headers.get("Location", "")
            server_id = location.rstrip("/").split("/")[-1] if location else ""
            if server_id:
                self.stats["created"] += 1
                return server_id
            else:
                print(f"  ⚠ 201 but no Location header: {logical_id}")
                self.stats["failed"] += 1
                return None
        elif resp.status_code == 409:
            print(f"  ⚠ CONFLICT (409): {logical_id} already exists — skipping")
            self.stats["skipped"] += 1
            return None
        else:
            ct = resp.headers.get('Content-Type', '')
            body = resp.text[:400] if 'json' in ct else f'[{ct}] (non-JSON response)'
            print(f"  ✗ FAILED ({resp.status_code}): {logical_id}")
            print(f"    {body}")
            self.stats["failed"] += 1
            return None

    # ── Datastreams ──────────────────────────────────────────────

    def create_datastreams(self):
        """Create all 22 datastream templates."""
        print(f"\n{'═' * 3} Phase 2a: Datastreams (22) {'═' * 3}")

        for parent_sys, filename in DATASTREAM_FILES:
            f = DS_DIR / filename
            if not f.exists():
                print(f"  ✗ File not found: {f}")
                self.stats["failed"] += 1
                continue

            data = json.loads(f.read_text(encoding="utf-8"))
            data = rewrite_links(data, self.id_map)
            data = transform_datastream(data)

            parent_server_id = self.id_map.get(parent_sys)
            if not parent_server_id:
                print(f"  ✗ System {parent_sys} not in id_map — skipping {filename}")
                self.stats["failed"] += 1
                continue

            endpoint = f"systems/{parent_server_id}/datastreams"
            logical_id = filename.replace("create_datastream_", "").replace(".json", "")

            server_id = self.post_resource(endpoint, data, "application/json", logical_id)
            if server_id:
                ds_key = f"DS-{logical_id}"
                self.id_map[ds_key] = server_id
                print(f"  ✓ {logical_id} → {server_id}")

    # ── Controlstreams ───────────────────────────────────────────

    def create_controlstreams(self):
        """Create all 13 controlstream templates."""
        print(f"\n{'═' * 3} Phase 2b: Controlstreams (13) {'═' * 3}")

        for actuator_sys, filename in CONTROLSTREAM_FILES:
            f = CS_DIR / filename
            if not f.exists():
                print(f"  ✗ File not found: {f}")
                self.stats["failed"] += 1
                continue

            data = json.loads(f.read_text(encoding="utf-8"))
            data = rewrite_links(data, self.id_map)
            data = transform_controlstream(data)

            actuator_server_id = self.id_map.get(actuator_sys)
            if not actuator_server_id:
                print(f"  ✗ System {actuator_sys} not in id_map — skipping {filename}")
                self.stats["failed"] += 1
                continue

            endpoint = f"systems/{actuator_server_id}/controlstreams"
            logical_id = filename.replace("create_controlstream_", "").replace(".json", "")

            server_id = self.post_resource(endpoint, data, "application/json", logical_id)
            if server_id:
                cs_key = f"CS-{logical_id}"
                self.id_map[cs_key] = server_id
                print(f"  ✓ {logical_id} → {server_id}")

    # ── Main execution ───────────────────────────────────────────

    def run(self):
        """Execute the full Phase 2 bootstrap."""
        print(f"{'=' * 60}")
        print(f"ODAS CSAPI Phase 2 Bootstrap")
        print(f"Server: {self.server}")
        print(f"Dry run: {self.dry_run}")
        print(f"{'=' * 60}")

        # Verify server is reachable
        try:
            resp = self.session.get(f"{self.server}", headers={"Accept": "application/json"})
            if resp.status_code != 200:
                print(f"✗ Server returned {resp.status_code}")
                sys.exit(1)
            print(f"✓ Server reachable")
        except requests.ConnectionError:
            print(f"✗ Cannot connect to {self.server}")
            sys.exit(1)

        self.load_id_map()

        start = time.time()

        self.create_datastreams()
        self.create_controlstreams()

        elapsed = time.time() - start

        # Save updated id_map (Phase 1 + Phase 2) — skip during dry-run
        if not self.dry_run:
            ID_MAP_PATH.write_text(json.dumps(self.id_map, indent=2), encoding="utf-8")

        print(f"\n{'=' * 60}")
        print(f"Phase 2 bootstrap complete in {elapsed:.1f}s")
        print(f"  Created: {self.stats['created']}")
        print(f"  Skipped: {self.stats['skipped']}")
        print(f"  Failed:  {self.stats['failed']}")
        print(f"  id_map now has {len(self.id_map)} entries (saved to {ID_MAP_PATH})")
        print(f"{'=' * 60}")

        if self.stats["failed"] > 0:
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ODAS CSAPI Phase 2 Bootstrap")
    parser.add_argument(
        "--server",
        default="http://45.55.99.236:8080/sensorhub/api",
        help="OSH SensorHub API base URL",
    )
    parser.add_argument(
        "--user", default="ogc", help="HTTP Basic auth username"
    )
    parser.add_argument(
        "--password", default="ogc", help="HTTP Basic auth password"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without executing",
    )
    args = parser.parse_args()

    bootstrap = Phase2Bootstrap(args.server, (args.user, args.password), args.dry_run)
    bootstrap.run()


if __name__ == "__main__":
    main()
