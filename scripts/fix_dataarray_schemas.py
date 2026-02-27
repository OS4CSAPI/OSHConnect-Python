#!/usr/bin/env python3
"""
Fix SSL/SST DataArray elementCount on OSH SensorHub.

The OSH SensorHub SWE JSON parser does not support variable-length
(implicit-size) DataArrays.  This one-shot helper PUTs a fixed
``elementCount.value = 3`` into the six SSL and SST datastream schemas
so that observation POSTs succeed.

Run this once before the first ``replay.py`` invocation.

Usage:
    python fix_dataarray_schemas.py [--server URL]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Tuple

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
ID_MAP_PATH = SCRIPT_DIR / "id_map.json"

# Datastreams whose schemas contain a DataArray "src" field
TARGETS = [
    "DS-az-ma-1_ssl_potential_sources",
    "DS-az-ma-2_ssl_potential_sources",
    "DS-az-ma-3_ssl_potential_sources",
    "DS-az-ma-1_sst_tracked_sources",
    "DS-az-ma-2_sst_tracked_sources",
    "DS-az-ma-3_sst_tracked_sources",
]

FIXED_ELEMENT_COUNT = 3  # each SSL/SST observation has exactly 3 sources


def fix_schemas(server: str, auth: Tuple[str, str]):
    s = requests.Session()
    s.auth = auth
    server = server.rstrip("/")

    id_map: Dict[str, str] = json.loads(ID_MAP_PATH.read_text(encoding="utf-8"))
    fixed = 0

    for key in TARGETS:
        ds_id = id_map.get(key)
        if not ds_id:
            print(f"  ⚠ {key} not in id_map — skipping")
            continue

        # Fetch current schema
        r = s.get(f"{server}/datastreams/{ds_id}/schema",
                  headers={"Accept": "application/json"})
        if r.status_code != 200:
            print(f"  ✗ GET schema {key}: {r.status_code}")
            continue
        schema = r.json()

        # Check if already fixed
        needs_fix = False
        for field in schema.get("resultSchema", {}).get("fields", []):
            if field.get("type") == "DataArray":
                ec = field.get("elementCount", {})
                if "value" not in ec or ec["value"] != FIXED_ELEMENT_COUNT:
                    field["elementCount"] = {
                        "type": "Count",
                        "name": "elementCount",
                        "value": FIXED_ELEMENT_COUNT,
                    }
                    needs_fix = True

        if not needs_fix:
            print(f"  ✓ {key} already fixed")
            continue

        # Fetch full datastream resource and PUT with updated schema
        r2 = s.get(f"{server}/datastreams/{ds_id}",
                   headers={"Accept": "application/json"})
        ds = r2.json()
        ds["schema"] = schema
        for k in ["id", "links", "observedProperties", "resultType", "formats"]:
            ds.pop(k, None)

        r3 = s.put(f"{server}/datastreams/{ds_id}",
                   data=json.dumps(ds),
                   headers={
                       "Content-Type": "application/json",
                       "Accept": "application/json",
                   })
        if r3.status_code == 204:
            print(f"  ✓ {key} ({ds_id}) fixed → elementCount={FIXED_ELEMENT_COUNT}")
            fixed += 1
        else:
            print(f"  ✗ {key} PUT: {r3.status_code} {r3.text[:200]}")

    print(f"\nDone — {fixed} schemas updated")


def main():
    p = argparse.ArgumentParser(description="Fix DataArray elementCount on SSL/SST datastreams")
    p.add_argument("--server", default="http://45.55.99.236:8080/sensorhub/api")
    p.add_argument("--user", default="ogc")
    p.add_argument("--password", default="ogc")
    args = p.parse_args()
    fix_schemas(args.server, (args.user, args.password))


if __name__ == "__main__":
    main()
