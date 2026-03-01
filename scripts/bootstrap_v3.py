#!/usr/bin/env python3
"""
ODAS CSAPI v3.0 — Part 1 Bootstrap

Creates the doctrine-aligned operational hierarchy and monitoring/reporting
layer from the v3.0 scenario pack (scenarios/ft-huachuca-v3.0/).

Resources created (in dependency order):
  1. Deployments (6)            — ICO > RSO > SSO > SNET > SFIELD > STRING
  2. Systems (3)                — SET-A, Monitoring Site Node 1, Relay 001
  3. Deployed-system links (3)  — SSO→SET, SNET→MonSite, SNET→Relay
  4. SENREP datastream (1)      — on SET-A (schema from scenario pack)

The resulting id_map (logical_id → server_id) is saved to id_map_v3.json
for use by subsequent phases.

IMPORTANT (memory):
  The rebuild approach is iterative. We build Part 1 first, verify it is
  correct, fix anything that needs fixing, then move to Part 2, etc.
  This script must create ONLY what is in the v3.0 Part 1 scenario pack —
  nothing more.

Usage:
    python bootstrap_v3.py                                    # Oracle (default)
    python bootstrap_v3.py --server URL --user X --password Y
    python bootstrap_v3.py --clean                            # pre-clean first
    python bootstrap_v3.py --dry-run                          # print only
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
SCENARIO_DIR = SCRIPT_DIR.parent / "scenarios" / "ft-huachuca-v3.0"
DEPLOYMENTS_DIR = SCENARIO_DIR / "examples" / "resources" / "deployments"
SYSTEMS_DIR = SCENARIO_DIR / "examples" / "resources" / "systems"
DEPLOYED_SYS_DIR = SCENARIO_DIR / "examples" / "resources" / "deployedSystems"
SCHEMAS_DIR = SCENARIO_DIR / "schemas" / "datastreams"

ID_MAP_PATH = SCRIPT_DIR / "id_map_v3.json"


# ── Deployment hierarchy (top-down creation order) ───────────────
#
# Tuple: (logical_id, parent_logical_id_or_None)
# Children are POSTed to /deployments/{parent_server_id}/deployments

DEPLOYMENT_HIERARCHY: List[Tuple[str, Optional[str]]] = [
    ("AZ-DEP-ICO-001", None),                       # top-level
    ("AZ-DEP-RSO-001", "AZ-DEP-ICO-001"),           # child of ICO
    ("AZ-DEP-SSO-001", "AZ-DEP-RSO-001"),           # child of RSO
    ("AZ-DEP-SNET-001", "AZ-DEP-SSO-001"),          # child of SSO
    ("AZ-DEP-FIELD-001", "AZ-DEP-SNET-001"),        # child of SNET
    ("AZ-DEP-STRING-ALPHA", "AZ-DEP-FIELD-001"),    # child of FIELD
]


# ── Systems (all top-level) ─────────────────────────────────────

SYSTEMS = ["AZ-SET-TEAM-A", "AZ-MON-SITE-1", "AZ-RELAY-001"]


# ── Deployed-system links ───────────────────────────────────────

DEPLOYED_SYSTEM_LINKS: List[Tuple[str, str]] = [
    # (deployment_logical_id, filename)
    ("AZ-DEP-SSO-001", "deployedSystem_AZ-DEP-SSO-001__AZ-SET-TEAM-A.json"),
    ("AZ-DEP-SNET-001", "deployedSystem_AZ-DEP-SNET-001__AZ-MON-SITE-1.json"),
    ("AZ-DEP-SNET-001", "deployedSystem_AZ-DEP-SNET-001__AZ-RELAY-001.json"),
]


# ── SENREP datastream ───────────────────────────────────────────

SENREP_SYSTEM = "AZ-SET-TEAM-A"
SENREP_SCHEMA_FILE = "senrep_OSH_v2.5.json"


# ─────────────────────────────────────────────────────────────────
# Utility functions
# ─────────────────────────────────────────────────────────────────


def convert_valid_time(data: dict) -> dict:
    """Convert validTime from {begin, end} to [begin, ".."] for OSH."""
    props = data.get("properties", data)
    vt = props.get("validTime")
    if isinstance(vt, dict):
        begin = vt.get("begin", "2026-01-01T00:00:00Z")
        end = vt.get("end")
        props["validTime"] = [begin, ".."] if end is None else [begin, end]
    return data


def prepare_deployment(data: dict, id_map: Dict[str, str]) -> dict:
    """
    Prepare a deployment GeoJSON for POST to /deployments.
    - Strips subdeployments@link (navigational, server-generated)
    - Rewrites partOf@link href using id_map (establishes hierarchy)
    - Converts validTime to OSH format
    """
    data = convert_valid_time(data)
    props = data.get("properties", {})
    # subdeployments@link is navigational — remove it
    props.pop("subdeployments@link", None)
    # partOf@link stays — rewrite href to server IDs
    data = rewrite_links(data, id_map)
    return data


def rewrite_links(data: dict, id_map: Dict[str, str]) -> dict:
    """Recursively rewrite href values using the id_map."""
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
    Recursively reorder dicts so 'type' is the first key.
    OSH SensorHub's SWE JSON parser requires 'type' as the first
    property in every SWE component object.
    """
    if isinstance(obj, dict):
        reordered = {k: ensure_type_first(v) for k, v in obj.items()}
        if "type" in reordered:
            result = {"type": reordered.pop("type")}
            result.update(reordered)
            return result
        return reordered
    elif isinstance(obj, list):
        return [ensure_type_first(item) for item in obj]
    return obj


# ─────────────────────────────────────────────────────────────────
# Bootstrap class
# ─────────────────────────────────────────────────────────────────


class BootstrapV3:
    def __init__(self, server_base: str, auth: Tuple[str, str], dry_run: bool = False):
        self.server = server_base.rstrip("/")
        self.auth = auth
        self.dry_run = dry_run
        self.id_map: Dict[str, str] = {}
        self.session = requests.Session()
        self.session.auth = auth
        self.stats = {"created": 0, "failed": 0, "skipped": 0, "deleted": 0}

    # ── HTTP helpers ─────────────────────────────────────────────

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

        try:
            resp = self.session.post(
                url,
                data=json.dumps(data),
                headers={"Content-Type": content_type, "Accept": "application/json"},
            )
        except requests.RequestException as e:
            print(f"  ✗ REQUEST ERROR: {logical_id} — {e}")
            self.stats["failed"] += 1
            return None

        if resp.status_code in (200, 201):
            location = resp.headers.get("Location", "")
            server_id = location.rstrip("/").split("/")[-1] if location else ""
            if server_id:
                self.stats["created"] += 1
                return server_id
            else:
                print(f"  ⚠ {resp.status_code} but no Location header: {logical_id}")
                self.stats["failed"] += 1
                return None
        elif resp.status_code == 409:
            print(f"  ⚠ CONFLICT (409): {logical_id} already exists")
            self.stats["skipped"] += 1
            return self._find_by_uid(endpoint, data)
        else:
            body = resp.text[:400]
            print(f"  ✗ FAILED ({resp.status_code}): {logical_id}")
            print(f"    {body}")
            self.stats["failed"] += 1
            return None

    def _find_by_uid(self, endpoint: str, data: dict) -> Optional[str]:
        """Try to find an existing resource by its UID."""
        uid = None
        if "properties" in data:
            uid = data["properties"].get("uid")
        if not uid:
            return None

        # Strip to collection path (e.g., "deployments" from "deployments/X/deployments")
        collection = endpoint.split("/")[0]
        search_url = f"{self.server}/{collection}?uid={uid}"
        try:
            resp = self.session.get(search_url, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    server_id = items[0].get("id")
                    print(f"    → found existing: {server_id}")
                    return server_id
        except requests.RequestException:
            pass
        return None

    def _find_resource_by_uid(self, collection: str, uid: str) -> Optional[str]:
        """Find a resource's server ID by UID in a collection."""
        search_url = f"{self.server}/{collection}?uid={uid}"
        try:
            resp = self.session.get(search_url, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    return items[0].get("id")
        except requests.RequestException:
            pass
        return None

    def _delete_resource(self, collection: str, server_id: str, label: str) -> bool:
        """Delete a resource by server ID. Tries force=true for cascade."""
        url = f"{self.server}/{collection}/{server_id}?force=true"
        if self.dry_run:
            print(f"  [DRY-RUN] DELETE {collection}/{server_id} ({label})")
            return True
        try:
            resp = self.session.delete(url)
            if resp.status_code in (200, 204):
                print(f"  🗑 Deleted {label} ({server_id})")
                self.stats["deleted"] += 1
                return True
            elif resp.status_code == 400:
                # Try without force
                resp2 = self.session.delete(f"{self.server}/{collection}/{server_id}")
                if resp2.status_code in (200, 204):
                    print(f"  🗑 Deleted {label} ({server_id})")
                    self.stats["deleted"] += 1
                    return True
                print(f"  ⚠ Delete failed for {label}: {resp2.status_code} — {resp2.text[:200]}")
                return False
            else:
                print(f"  ⚠ Delete failed for {label}: {resp.status_code} — {resp.text[:200]}")
                return False
        except requests.RequestException as e:
            print(f"  ⚠ Delete error for {label}: {e}")
            return False

    # ── Pre-clean ────────────────────────────────────────────────

    def clean(self):
        """Delete all existing v3.0 resources (reverse dependency order)."""
        print("\n═══ Pre-clean: removing existing v3.0 resources ═══")

        # 1. Delete deployments bottom-up
        print("  ── Deployments (bottom-up) ──")
        for dep_id, _ in reversed(DEPLOYMENT_HIERARCHY):
            f = DEPLOYMENTS_DIR / f"{dep_id}.geojson"
            if not f.exists():
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            uid = data.get("properties", {}).get("uid")
            if not uid:
                continue
            server_id = self._find_resource_by_uid("deployments", uid)
            if server_id:
                self._delete_resource("deployments", server_id, dep_id)
            else:
                print(f"  · {dep_id} not found (already clean)")

        # 2. Delete systems (and their datastreams via cascade)
        print("  ── Systems ──")
        for sys_id in SYSTEMS:
            f = SYSTEMS_DIR / f"{sys_id}.geojson"
            if not f.exists():
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            uid = data.get("properties", {}).get("uid")
            if not uid:
                continue
            server_id = self._find_resource_by_uid("systems", uid)
            if server_id:
                # Delete child datastreams first (in case cascade fails)
                self._delete_child_datastreams(server_id, sys_id)
                self._delete_resource("systems", server_id, sys_id)
            else:
                print(f"  · {sys_id} not found (already clean)")

        print(f"  Pre-clean complete: {self.stats['deleted']} resources deleted")

    def _delete_child_datastreams(self, sys_server_id: str, sys_label: str):
        """Delete all datastreams under a system."""
        url = f"{self.server}/systems/{sys_server_id}/datastreams"
        try:
            resp = self.session.get(url, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for ds in items:
                    ds_id = ds.get("id")
                    if ds_id:
                        self._delete_resource(
                            f"systems/{sys_server_id}/datastreams",
                            ds_id,
                            f"{sys_label}/ds-{ds_id}",
                        )
        except requests.RequestException:
            pass

    # ── Phase 1a: Deployments ────────────────────────────────────

    def create_deployments(self):
        """Create 6 deployments in doctrine hierarchy order."""
        print(f"\n{'═' * 3} Phase 1a: Deployments (6) {'═' * 3}")

        for dep_id, parent_id in DEPLOYMENT_HIERARCHY:
            f = DEPLOYMENTS_DIR / f"{dep_id}.geojson"
            if not f.exists():
                print(f"  ✗ File not found: {f.name}")
                self.stats["failed"] += 1
                continue

            data = json.loads(f.read_text(encoding="utf-8"))
            data = prepare_deployment(data, self.id_map)

            # If this deployment has a parent, verify parent was created
            if parent_id is not None and parent_id not in self.id_map:
                print(f"  ✗ Parent {parent_id} not in id_map — cannot create {dep_id}")
                self.stats["failed"] += 1
                continue

            # All deployments POST to /deployments (flat)
            # partOf@link in body establishes hierarchy
            endpoint = "deployments"

            server_id = self.post_resource(
                endpoint, data, "application/geo+json", dep_id
            )
            if server_id:
                self.id_map[dep_id] = server_id
                print(f"  ✓ {dep_id} → {server_id}")

    # ── Phase 1b: Systems ────────────────────────────────────────

    def create_systems(self):
        """Create 3 systems (all top-level)."""
        print(f"\n{'═' * 3} Phase 1b: Systems (3) {'═' * 3}")

        for sys_id in SYSTEMS:
            f = SYSTEMS_DIR / f"{sys_id}.geojson"
            if not f.exists():
                print(f"  ✗ File not found: {f.name}")
                self.stats["failed"] += 1
                continue

            data = json.loads(f.read_text(encoding="utf-8"))
            data = convert_valid_time(data)

            server_id = self.post_resource(
                "systems", data, "application/geo+json", sys_id
            )
            if server_id:
                self.id_map[sys_id] = server_id
                print(f"  ✓ {sys_id} → {server_id}")

    # ── Phase 1c: Deployed-system links ──────────────────────────

    def create_deployed_system_links(self):
        """Create deployed-system associations.

        NOTE: OSH SensorHub on Oracle does not currently support the
        /deployments/{id}/deployedSystems endpoint (returns 400).
        The /deployments/{id}/members endpoint creates duplicates.
        Deployed-system links are recorded in id_map for reference
        but creation is deferred until endpoint support is confirmed.
        """
        print(f"\n{'═' * 3} Phase 1c: Deployed-System Links (3) {'═' * 3}")
        print("  ⚠ DEFERRED: OSH server does not support /deployedSystems endpoint")
        print("    Associations recorded in id_map for future use.")
        print("    Hierarchy is established via partOf@link on deployments.")

        # Record the intended associations in id_map for reference
        for dep_logical_id, filename in DEPLOYED_SYSTEM_LINKS:
            label = filename.replace("deployedSystem_", "").replace(".json", "")
            link_key = f"LINK-{label}"
            self.id_map[link_key] = f"deferred:{dep_logical_id}"
            print(f"  · {label} → deferred")

    # ── Phase 1d: SENREP datastream ──────────────────────────────

    def create_senrep_datastream(self):
        """Create the SENREP datastream on SET-A."""
        print(f"\n{'═' * 3} Phase 1d: SENREP Datastream (1) {'═' * 3}")

        schema_file = SCHEMAS_DIR / SENREP_SCHEMA_FILE
        if not schema_file.exists():
            print(f"  ✗ Schema file not found: {SENREP_SCHEMA_FILE}")
            self.stats["failed"] += 1
            return

        set_server_id = self.id_map.get(SENREP_SYSTEM)
        if not set_server_id:
            print(f"  ✗ System {SENREP_SYSTEM} not in id_map — cannot create datastream")
            self.stats["failed"] += 1
            return

        schema_data = json.loads(schema_file.read_text(encoding="utf-8"))
        schema_data = ensure_type_first(schema_data)

        # Wrap the schema in a datastream creation payload
        ds_body = {
            "name": "SENREP (Sensor Report)",
            "description": "Doctrinal SENREP-style sensor report produced by SET.",
            "outputName": "senrep",
            "schema": {
                "obsFormat": "application/swe+json",
                "recordSchema": schema_data,
            },
        }

        endpoint = f"systems/{set_server_id}/datastreams"
        server_id = self.post_resource(endpoint, ds_body, "application/json", "SENREP")
        if server_id:
            self.id_map["DS-SENREP"] = server_id
            print(f"  ✓ SENREP → {server_id}")

    # ── Main execution ───────────────────────────────────────────

    def run(self, clean_first: bool = False):
        """Execute the full Part 1 bootstrap."""
        print(f"{'=' * 60}")
        print(f"ODAS CSAPI v3.0 — Part 1 Bootstrap")
        print(f"Server: {self.server}")
        print(f"Dry run: {self.dry_run}")
        print(f"Clean:   {clean_first}")
        print(f"{'=' * 60}")

        # Verify scenario pack exists
        if not SCENARIO_DIR.exists():
            print(f"✗ Scenario pack not found: {SCENARIO_DIR}")
            sys.exit(1)
        print(f"✓ Scenario pack: {SCENARIO_DIR}")

        # Verify server is reachable
        try:
            resp = self.session.get(
                f"{self.server}", headers={"Accept": "application/json"}
            )
            if resp.status_code != 200:
                print(f"✗ Server returned {resp.status_code}")
                sys.exit(1)
            print(f"✓ Server reachable")
        except requests.ConnectionError:
            print(f"✗ Cannot connect to {self.server}")
            sys.exit(1)

        start = time.time()

        if clean_first:
            self.clean()

        self.create_deployments()
        self.create_systems()
        self.create_deployed_system_links()
        self.create_senrep_datastream()

        elapsed = time.time() - start

        # Save id_map
        if not self.dry_run:
            ID_MAP_PATH.write_text(
                json.dumps(self.id_map, indent=2), encoding="utf-8"
            )

        print(f"\n{'=' * 60}")
        print(f"Part 1 bootstrap complete in {elapsed:.1f}s")
        print(f"  Created: {self.stats['created']}")
        print(f"  Skipped: {self.stats['skipped']}")
        print(f"  Failed:  {self.stats['failed']}")
        if clean_first:
            print(f"  Deleted: {self.stats['deleted']}")
        print(f"  id_map ({len(self.id_map)} entries) → {ID_MAP_PATH}")
        print(f"{'=' * 60}")

        if self.stats["failed"] > 0:
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="ODAS CSAPI v3.0 Part 1 Bootstrap"
    )
    parser.add_argument(
        "--server",
        default="http://os4csapi-osh.duckdns.org/sensorhub/api",
        help="OSH SensorHub API base URL (default: Oracle server)",
    )
    parser.add_argument(
        "--user",
        default="os4csapi",
        help="HTTP Basic auth username (default: os4csapi)",
    )
    parser.add_argument(
        "--password",
        default="ogc134mm",
        help="HTTP Basic auth password (default: ogc134mm)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing v3.0 resources before creating",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without executing",
    )
    args = parser.parse_args()

    bootstrap = BootstrapV3(args.server, (args.user, args.password), args.dry_run)
    bootstrap.run(clean_first=args.clean)


if __name__ == "__main__":
    main()
