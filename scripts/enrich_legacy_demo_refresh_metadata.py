#!/usr/bin/env python3
"""Add refresh metadata to legacy scenario/demo systems.

These systems are not normal scheduled public-data publishers. They are legacy
scenario resources whose observations are produced by simulator/demo runs or by
operator action. This script preserves the current SensorML and adds a
card-readable refresh metadata capability so Explorer does not imply a false
polling cadence.
"""

import argparse
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from publishers.bootstrap_helpers import get_config, _auth_header


SYSTEMS = [
    {
        "id": "040g",
        "label": "SET-A",
        "refresh_rate": "Scenario-driven / not scheduled",
        "query_mode": "Operator-authored SENREP reports are created by scenario workflow, not a fixed poller",
    },
    {
        "id": "0410",
        "label": "Monitoring Site 001",
        "refresh_rate": "Scenario-driven / not scheduled",
        "query_mode": "Monitoring-site support metadata changes only during scenario updates",
    },
    {
        "id": "041g",
        "label": "Relay",
        "refresh_rate": "Scenario-driven / not scheduled",
        "query_mode": "Relay support metadata changes only during scenario updates",
    },
    {
        "id": "0420",
        "label": "ODAS Mic Array Node AZ-MA-1",
        "refresh_rate": "Scenario-driven / simulator active",
        "query_mode": "ODAS observations are emitted by scenario simulator runs when active",
    },
    {
        "id": "0490",
        "label": "ODAS Mic Array Node AZ-MA-2",
        "refresh_rate": "Scenario-driven / simulator active",
        "query_mode": "ODAS observations are emitted by scenario simulator runs when active",
    },
    {
        "id": "049g",
        "label": "ODAS Mic Array Node AZ-MA-3",
        "refresh_rate": "Scenario-driven / simulator active",
        "query_mode": "ODAS observations are emitted by scenario simulator runs when active",
    },
    {
        "id": "04o0",
        "label": "AZ String Alpha Localizer",
        "refresh_rate": "Scenario-driven / simulator active",
        "query_mode": "Localizer estimates are emitted when recent scenario LOB observations are available",
    },
]


def _request_json(url: str, auth: str, *, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method, headers={
        "Authorization": auth,
        "Accept": "application/sml+json",
        "Content-Type": "application/sml+json",
    })
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {raw[:400]}") from exc


def _refresh_capability(entry: dict) -> dict:
    return {
        "definition": "http://www.w3.org/ns/ssn/systems/SystemCapability",
        "label": "Refresh Metadata",
        "capabilities": [
            {
                "type": "Text",
                "name": "refresh_rate",
                "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
                "label": "Refresh Rate",
                "value": entry["refresh_rate"],
            },
            {
                "type": "Text",
                "name": "source_query_mode",
                "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
                "label": "Source Query Mode",
                "value": entry["query_mode"],
            },
        ],
    }


def _merge_refresh_metadata(sml: dict, entry: dict) -> dict:
    capabilities = [
        item for item in sml.get("capabilities", [])
        if item.get("label") != "Refresh Metadata" and item.get("name") != "refresh_metadata"
    ]
    capabilities.append(_refresh_capability(entry))
    updated = dict(sml)
    updated["capabilities"] = capabilities
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich legacy demo systems with truthful refresh metadata.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and show intended updates without PUT")
    args = parser.parse_args()

    config = get_config()
    base_url = config["base_url"].rstrip("/")
    auth = _auth_header(config["user"], config["password"])

    for entry in SYSTEMS:
        url = f"{base_url}/systems/{entry['id']}?f=sml3"
        sml = _request_json(url, auth)
        label = sml.get("label") or sml.get("name") or entry["label"]
        updated = _merge_refresh_metadata(sml, entry)
        if args.dry_run:
            print(f"[DRY] {entry['id']} {label}: Refresh Rate={entry['refresh_rate']}")
            continue
        try:
            _request_json(f"{base_url}/systems/{entry['id']}", auth, method="PUT", body=updated)
            print(f"[SML] {entry['id']} {label}: Refresh Rate={entry['refresh_rate']}")
        except RuntimeError as exc:
            print(f"[WARN] PUT returned warning for {entry['id']} {label}: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())