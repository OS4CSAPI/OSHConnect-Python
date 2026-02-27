#!/usr/bin/env python3
"""
ODAS CSAPI Phase 1 Bootstrap Script

Creates all 121 Part 1 resources on the OSH SensorHub server from the
Maximal ScenarioPack v2.3 (Fort Huachuca C-UAS scenario).

Resources are created in dependency order:
  1. Properties (31) — no dependencies
  2. Procedures (15) — no dependencies
  3. Systems (43) — hierarchical: top-level then subsystems
  4. Deployments (20) — @link references rewritten with id_map
  5. SamplingFeatures (12) — under root /samplingFeatures
  6. DeployedSystem links (7) — system.href rewritten with id_map

The resulting id_map (logical_id → server_id) is saved to id_map.json
for use by Phase 2 (datastream/controlstream creation).

Usage:
    python bootstrap.py [--server URL] [--dry-run]
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
RESOURCES_DIR = SCENARIO_DIR / "examples" / "resources"
CREATE_PROPS_DIR = SCENARIO_DIR / "examples" / "create_properties"
CREATE_DEPLOYED_SYS_DIR = SCENARIO_DIR / "examples" / "create_deployedSystems"

# ── System hierarchy ─────────────────────────────────────────────

# Top-level systems (POST to /systems)
TOP_LEVEL_SYSTEMS = ["AZ-MA-NET", "AZ-MA-1", "AZ-MA-2", "AZ-MA-3"]

# Nodes whose subsystems are created under them
PARENT_NODES = ["AZ-MA-1", "AZ-MA-2", "AZ-MA-3"]


def get_subsystem_ids(node: str) -> List[str]:
    """Return the child system IDs for a given parent node."""
    return [
        f"{node}-PLATFORM",
        f"{node}-MICARRAY",
        f"{node}-EDGE",
        f"{node}-COMMS",
        f"{node}-POWER",
        f"{node}-ACTUATOR",
    ] + [f"{node}-MIC{i}" for i in range(1, 8)]


# ── Deployment ordering ─────────────────────────────────────────

# These are created first (no relatedTo@link dependencies)
TOP_LEVEL_DEPLOYMENTS = ["AZ-DEP-AOI-001", "AZ-DEP-NET-001"]

# These reference AZ-DEP-AOI-001 via relatedTo@link
NODE_DEPLOYMENTS = ["AZ-DEP-AZ-MA-1", "AZ-DEP-AZ-MA-2", "AZ-DEP-AZ-MA-3"]


def get_sub_deployment_ids(node: str) -> List[str]:
    """Return the sub-deployment IDs for a given node (e.g. AZ-MA-1)."""
    return [
        f"AZ-DEP-{node}-MICARRAY",
        f"AZ-DEP-{node}-EDGE",
        f"AZ-DEP-{node}-COMMS",
        f"AZ-DEP-{node}-POWER",
        f"AZ-DEP-{node}-ACTUATOR",
    ]


# ── Deployed system link files ──────────────────────────────────

DEPLOYED_SYSTEM_LINKS: List[Tuple[str, str]] = [
    # (deployment_logical_id, filename)
    ("AZ-DEP-AOI-001", "create_deployedSystem_AZ-DEP-AOI-001__AZ-MA-1.json"),
    ("AZ-DEP-AOI-001", "create_deployedSystem_AZ-DEP-AOI-001__AZ-MA-2.json"),
    ("AZ-DEP-AOI-001", "create_deployedSystem_AZ-DEP-AOI-001__AZ-MA-3.json"),
    ("AZ-DEP-AOI-001", "create_deployedSystem_AZ-DEP-AOI-001__AZ-MA-NET.json"),
    ("AZ-DEP-AZ-MA-1", "create_deployedSystem_AZ-DEP-AZ-MA-1__AZ-MA-1.json"),
    ("AZ-DEP-AZ-MA-2", "create_deployedSystem_AZ-DEP-AZ-MA-2__AZ-MA-2.json"),
    ("AZ-DEP-AZ-MA-3", "create_deployedSystem_AZ-DEP-AZ-MA-3__AZ-MA-3.json"),
]

# ── Sampling feature ordering ───────────────────────────────────

GLOBAL_TRACKS = ["AZ-GTRK-0001", "AZ-GTRK-0002", "AZ-GTRK-0003"]


def get_node_track_ids(node: str) -> List[str]:
    return [f"{node}-TRK-{i}" for i in range(1, 4)]


# ─────────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────────


def convert_valid_time(data: dict) -> dict:
    """
    Convert validTime from object format {begin, end} to the array format
    that OSH SensorHub expects: ["2026-01-01T00:00:00Z", ".."].
    """
    props = data.get("properties", data)
    vt = props.get("validTime")
    if isinstance(vt, dict):
        begin = vt.get("begin", "2026-01-01T00:00:00Z")
        end = vt.get("end")
        if end is None:
            props["validTime"] = [begin, ".."]
        else:
            props["validTime"] = [begin, end]
    return data


def rewrite_links(data: dict, id_map: Dict[str, str]) -> dict:
    """
    Recursively rewrite @link href values using the id_map.
    Replaces paths like /sensorhub/api/deployments/AZ-DEP-AOI-001
    with /sensorhub/api/deployments/<server_id>.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "href" and isinstance(value, str):
                # Extract the logical ID from the href path
                for logical_id, server_id in id_map.items():
                    # Match /resource_type/LOGICAL_ID at the end of the path
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


# ─────────────────────────────────────────────────────────────────
# Server interaction
# ─────────────────────────────────────────────────────────────────


class Bootstrap:
    def __init__(self, server_base: str, auth: Tuple[str, str], dry_run: bool = False):
        self.server = server_base.rstrip("/")
        self.auth = auth
        self.dry_run = dry_run
        self.id_map: Dict[str, str] = {}
        self.session = requests.Session()
        self.session.auth = auth
        self.stats = {"created": 0, "failed": 0, "skipped": 0}

    def post_resource(
        self,
        endpoint: str,
        data: dict,
        content_type: str = "application/geo+json",
        logical_id: str = "",
    ) -> Optional[str]:
        """POST a resource and return the server-assigned ID."""
        url = f"{self.server}/{endpoint}"

        if self.dry_run:
            print(f"  [DRY-RUN] POST {endpoint} → {logical_id}")
            self.stats["skipped"] += 1
            return f"dry-{logical_id}"

        resp = self.session.post(
            url, json=data, headers={"Content-Type": content_type}
        )

        if resp.status_code in (200, 201):
            location = resp.headers.get("Location", "")
            server_id = location.rstrip("/").split("/")[-1]
            self.stats["created"] += 1
            return server_id
        elif resp.status_code == 409:
            # Conflict — resource with this UID already exists
            print(f"  ⚠ CONFLICT (409): {logical_id} already exists — skipping")
            self.stats["skipped"] += 1
            # Try to find the existing resource by UID
            return self._find_by_uid(endpoint, data)
        else:
            print(f"  ✗ FAILED ({resp.status_code}): {logical_id}")
            print(f"    {resp.text[:300]}")
            self.stats["failed"] += 1
            return None

    def _find_by_uid(self, endpoint: str, data: dict) -> Optional[str]:
        """Try to find an existing resource by its UID."""
        uid = None
        if "properties" in data:
            uid = data["properties"].get("uid")
        elif "uniqueId" in data:
            uid = data["uniqueId"]

        if not uid:
            return None

        # Strip to the collection path (e.g., "systems" from "systems/X/subsystems")
        collection = endpoint.split("/")[0]
        search_url = f"{self.server}/{collection}?uid={uid}"
        resp = self.session.get(search_url, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                return items[0].get("id")
        return None

    # ── Phase: Properties ────────────────────────────────────────

    def create_properties(self):
        """Create all 31 property resources."""
        print("\n═══ Phase 1a: Properties (31) ═══")
        prop_files = sorted(CREATE_PROPS_DIR.glob("create_property_*.json"))
        for f in prop_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            label = data.get("label", f.stem)
            logical_id = f"PROP-{label}"
            server_id = self.post_resource("properties", data, "application/json", logical_id)
            if server_id:
                self.id_map[logical_id] = server_id
                print(f"  ✓ {label} → {server_id}")

    # ── Phase: Procedures ────────────────────────────────────────

    def create_procedures(self):
        """Create all 15 procedure resources."""
        print("\n═══ Phase 1b: Procedures (15) ═══")
        proc_dir = RESOURCES_DIR / "procedures"
        proc_files = sorted(proc_dir.glob("*.geojson"))
        for f in proc_files:
            data = json.loads(f.read_text(encoding="utf-8"))
            data = convert_valid_time(data)
            logical_id = data.get("id", f.stem)
            server_id = self.post_resource("procedures", data, "application/geo+json", logical_id)
            if server_id:
                self.id_map[logical_id] = server_id
                print(f"  ✓ {logical_id} → {server_id}")

    # ── Phase: Systems ───────────────────────────────────────────

    def create_systems(self):
        """Create all 43 systems in hierarchical order."""
        print("\n═══ Phase 1c: Systems (43) ═══")

        sys_dir = RESOURCES_DIR / "systems"

        # --- Top-level systems ---
        print("  ── Top-level systems (4) ──")
        for sys_id in TOP_LEVEL_SYSTEMS:
            f = sys_dir / f"{sys_id}.geojson"
            if not f.exists():
                print(f"  ✗ File not found: {f}")
                self.stats["failed"] += 1
                continue

            data = json.loads(f.read_text(encoding="utf-8"))
            data = convert_valid_time(data)
            server_id = self.post_resource("systems", data, "application/geo+json", sys_id)
            if server_id:
                self.id_map[sys_id] = server_id
                print(f"  ✓ {sys_id} → {server_id}")

        # --- Subsystems for each parent node ---
        for node in PARENT_NODES:
            subsys_ids = get_subsystem_ids(node)
            parent_server_id = self.id_map.get(node)
            if not parent_server_id:
                print(f"  ✗ Cannot create subsystems: parent {node} not in id_map")
                self.stats["failed"] += len(subsys_ids)
                continue

            print(f"  ── Subsystems of {node} ({len(subsys_ids)}) ──")
            endpoint = f"systems/{parent_server_id}/subsystems"

            for sub_id in subsys_ids:
                f = sys_dir / f"{sub_id}.geojson"
                if not f.exists():
                    print(f"  ✗ File not found: {f}")
                    self.stats["failed"] += 1
                    continue

                data = json.loads(f.read_text(encoding="utf-8"))
                data = convert_valid_time(data)
                server_id = self.post_resource(endpoint, data, "application/geo+json", sub_id)
                if server_id:
                    self.id_map[sub_id] = server_id
                    print(f"  ✓ {sub_id} → {server_id}")

    # ── Phase: Deployments ───────────────────────────────────────

    def create_deployments(self):
        """Create all 20 deployments with @link rewriting."""
        print("\n═══ Phase 1d: Deployments (20) ═══")

        dep_dir = RESOURCES_DIR / "deployments"

        # --- Top-level: AOI + NET ---
        print("  ── Top-level deployments (2) ──")
        for dep_id in TOP_LEVEL_DEPLOYMENTS:
            f = dep_dir / f"{dep_id}.geojson"
            data = json.loads(f.read_text(encoding="utf-8"))
            data = convert_valid_time(data)
            server_id = self.post_resource("deployments", data, "application/geo+json", dep_id)
            if server_id:
                self.id_map[dep_id] = server_id
                print(f"  ✓ {dep_id} → {server_id}")

        # --- Node deployments (reference AOI via relatedTo@link) ---
        print("  ── Node deployments (3) ──")
        for dep_id in NODE_DEPLOYMENTS:
            f = dep_dir / f"{dep_id}.geojson"
            data = json.loads(f.read_text(encoding="utf-8"))
            data = convert_valid_time(data)
            data = rewrite_links(data, self.id_map)
            server_id = self.post_resource("deployments", data, "application/geo+json", dep_id)
            if server_id:
                self.id_map[dep_id] = server_id
                print(f"  ✓ {dep_id} → {server_id}")

        # --- Sub-deployments per node ---
        for node in PARENT_NODES:
            sub_dep_ids = get_sub_deployment_ids(node)
            print(f"  ── Sub-deployments of {node} ({len(sub_dep_ids)}) ──")
            for dep_id in sub_dep_ids:
                f = dep_dir / f"{dep_id}.geojson"
                if not f.exists():
                    print(f"  ✗ File not found: {f}")
                    self.stats["failed"] += 1
                    continue
                data = json.loads(f.read_text(encoding="utf-8"))
                data = convert_valid_time(data)
                server_id = self.post_resource("deployments", data, "application/geo+json", dep_id)
                if server_id:
                    self.id_map[dep_id] = server_id
                    print(f"  ✓ {dep_id} → {server_id}")

    # ── Phase: Sampling Features ─────────────────────────────────

    def create_sampling_features(self):
        """Create all 12 sampling features."""
        print("\n═══ Phase 1e: Sampling Features (12) ═══")

        sf_dir = RESOURCES_DIR / "samplingFeatures"

        # Global tracks
        print("  ── Global tracks (3) ──")
        for sf_id in GLOBAL_TRACKS:
            f = sf_dir / f"{sf_id}.geojson"
            data = json.loads(f.read_text(encoding="utf-8"))
            data = convert_valid_time(data)
            server_id = self.post_resource("samplingFeatures", data, "application/geo+json", sf_id)
            if server_id:
                self.id_map[sf_id] = server_id
                print(f"  ✓ {sf_id} → {server_id}")

        # Per-node tracks
        for node in PARENT_NODES:
            track_ids = get_node_track_ids(node)
            print(f"  ── Tracks of {node} ({len(track_ids)}) ──")
            for sf_id in track_ids:
                f = sf_dir / f"{sf_id}.geojson"
                if not f.exists():
                    print(f"  ✗ File not found: {f}")
                    self.stats["failed"] += 1
                    continue
                data = json.loads(f.read_text(encoding="utf-8"))
                data = convert_valid_time(data)
                server_id = self.post_resource(
                    "samplingFeatures", data, "application/geo+json", sf_id
                )
                if server_id:
                    self.id_map[sf_id] = server_id
                    print(f"  ✓ {sf_id} → {server_id}")

    # ── Phase: Deployed System links ─────────────────────────────

    def create_deployed_system_links(self):
        """Create all 7 deployed system links."""
        print("\n═══ Phase 1f: Deployed System Links (7) ═══")

        for dep_logical_id, filename in DEPLOYED_SYSTEM_LINKS:
            f = CREATE_DEPLOYED_SYS_DIR / filename
            if not f.exists():
                print(f"  ✗ File not found: {f}")
                self.stats["failed"] += 1
                continue

            data = json.loads(f.read_text(encoding="utf-8"))
            data = rewrite_links(data, self.id_map)

            # POST to /deployments/{deployment_server_id}/deployedSystems
            dep_server_id = self.id_map.get(dep_logical_id)
            if not dep_server_id:
                print(f"  ✗ Deployment {dep_logical_id} not in id_map — skipping {filename}")
                self.stats["failed"] += 1
                continue

            endpoint = f"deployments/{dep_server_id}/deployedSystems"
            server_id = self.post_resource(endpoint, data, "application/json", filename)
            if server_id:
                link_key = f"LINK-{filename}"
                self.id_map[link_key] = server_id
                print(f"  ✓ {filename} → {server_id}")

    # ── Main execution ───────────────────────────────────────────

    def run(self):
        """Execute the full bootstrap in dependency order."""
        print(f"{'=' * 60}")
        print(f"ODAS CSAPI Phase 1 Bootstrap")
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

        start = time.time()

        self.create_properties()
        self.create_procedures()
        self.create_systems()
        self.create_deployments()
        self.create_sampling_features()
        self.create_deployed_system_links()

        elapsed = time.time() - start

        # Save id_map
        id_map_path = SCRIPT_DIR / "id_map.json"
        id_map_path.write_text(json.dumps(self.id_map, indent=2), encoding="utf-8")

        print(f"\n{'=' * 60}")
        print(f"Bootstrap complete in {elapsed:.1f}s")
        print(f"  Created: {self.stats['created']}")
        print(f"  Skipped: {self.stats['skipped']}")
        print(f"  Failed:  {self.stats['failed']}")
        print(f"  id_map saved to: {id_map_path}")
        print(f"{'=' * 60}")

        if self.stats["failed"] > 0:
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="ODAS CSAPI Phase 1 Bootstrap")
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

    bootstrap = Bootstrap(args.server, (args.user, args.password), args.dry_run)
    bootstrap.run()


if __name__ == "__main__":
    main()
