#!/usr/bin/env python3
"""Comprehensive server verification for Phase 1 bootstrap results."""
import json
from pathlib import Path
import requests

s = requests.Session()
s.auth = ("ogc", "ogc")
BASE = "http://45.55.99.236:8080/sensorhub/api"

# Load id_map from bootstrap
ID_MAP = json.loads((Path(__file__).parent / "id_map.json").read_text())

def check_resource(endpoint, server_id):
    """GET a single resource by ID, return (ok, data_or_status)."""
    r = s.get(f"{BASE}/{endpoint}/{server_id}", headers={"Accept": "application/json"})
    if r.status_code == 200:
        try:
            return True, r.json()
        except Exception:
            return True, {}
    return False, r.status_code

def get_collection(endpoint, limit=200):
    r = s.get(f"{BASE}/{endpoint}?limit={limit}", headers={"Accept": "application/json"})
    return r.json().get("items", [])

print("=" * 70)
print("PHASE 1 BOOTSTRAP — SERVER VERIFICATION REPORT")
print("=" * 70)

# Categorize id_map entries
prop_ids = {k: v for k, v in ID_MAP.items() if k.startswith("PROP-")}
proc_ids = {k: v for k, v in ID_MAP.items() if "PROC" in k}
sys_ids = {k: v for k, v in ID_MAP.items() if k.startswith("AZ-MA-") and "DEP" not in k and "PROC" not in k and "TRK" not in k and "GTRK" not in k}
dep_ids = {k: v for k, v in ID_MAP.items() if k.startswith("AZ-DEP-")}
sf_ids = {k: v for k, v in ID_MAP.items() if "TRK" in k or "GTRK" in k}

# ── PROPERTIES ──
print(f"\n{'─'*40}")
ok_count = 0
for logical, sid in sorted(prop_ids.items()):
    ok, data = check_resource("properties", sid)
    if ok:
        ok_count += 1
print(f"PROPERTIES: {ok_count} / {len(prop_ids)} verified on server")
# Show a few
all_props = get_collection("properties")
os4csapi_props = [p for p in all_props if "os4csapi" in p.get("uniqueId", "")]
for p in os4csapi_props[:5]:
    print(f"  [{p['id']}] {p.get('label','')}  uid={p.get('uniqueId','')}")
if len(os4csapi_props) > 5:
    print(f"  ... and {len(os4csapi_props)-5} more")

# ── PROCEDURES ──
print(f"\n{'─'*40}")
ok_count = 0
for logical, sid in sorted(proc_ids.items()):
    ok, data = check_resource("procedures", sid)
    if ok:
        ok_count += 1
    else:
        print(f"  MISSING: {logical} -> {sid} (HTTP {data})")
print(f"PROCEDURES: {ok_count} / {len(proc_ids)} verified on server")
for logical, sid in sorted(proc_ids.items())[:3]:
    ok, data = check_resource("procedures", sid)
    if ok:
        name = data.get("properties",{}).get("name","")
        uid = data.get("properties",{}).get("uid","")
        print(f"  [{sid}] {name}  uid={uid}")
if len(proc_ids) > 3:
    print(f"  ... and {len(proc_ids)-3} more")

# ── SYSTEMS ──
print(f"\n{'─'*40}")
ok_count = 0
top_level = []
subsystems = []
for logical, sid in sorted(sys_ids.items()):
    ok, data = check_resource("systems", sid)
    if ok:
        ok_count += 1
        has_parent = any(l.get("rel") == "parent" for l in data.get("links", []))
        if has_parent:
            subsystems.append((logical, sid, data))
        else:
            top_level.append((logical, sid, data))
    else:
        print(f"  MISSING: {logical} -> {sid} (HTTP {data})")
print(f"SYSTEMS: {ok_count} / {len(sys_ids)} verified on server")
print(f"  Top-level: {len(top_level)}")
print(f"  Subsystems: {len(subsystems)}")
for logical, sid, data in top_level:
    name = data.get("properties",{}).get("name","")
    uid = data.get("properties",{}).get("uid","")
    print(f"  [{sid}] {name}  uid={uid}")
    # count subsystems
    sub_items = get_collection(f"systems/{sid}/subsystems")
    if sub_items:
        print(f"       └── {len(sub_items)} subsystems")
        for sub in sub_items[:3]:
            print(f"           [{sub['id']}] {sub.get('properties',{}).get('name','')}")
        if len(sub_items) > 3:
            print(f"           ... and {len(sub_items)-3} more")

# ── DEPLOYMENTS ──
print(f"\n{'─'*40}")
ok_count = 0
for logical, sid in sorted(dep_ids.items()):
    ok, data = check_resource("deployments", sid)
    if ok:
        ok_count += 1
    else:
        print(f"  MISSING: {logical} -> {sid} (HTTP {data})")
print(f"DEPLOYMENTS: {ok_count} / {len(dep_ids)} verified on server")
for logical, sid in sorted(dep_ids.items())[:5]:
    ok, data = check_resource("deployments", sid)
    if ok:
        name = data.get("properties",{}).get("name","")
        uid = data.get("properties",{}).get("uid","")
        print(f"  [{sid}] {name}  uid={uid}")
if len(dep_ids) > 5:
    print(f"  ... and {len(dep_ids)-5} more")

# ── SAMPLING FEATURES ──
print(f"\n{'─'*40}")
ok_count = 0
for logical, sid in sorted(sf_ids.items()):
    ok, data = check_resource("samplingFeatures", sid)
    if ok:
        ok_count += 1
    else:
        print(f"  MISSING: {logical} -> {sid} (HTTP {data})")
print(f"SAMPLING FEATURES: {ok_count} / {len(sf_ids)} verified on server")
for logical, sid in sorted(sf_ids.items())[:3]:
    ok, data = check_resource("samplingFeatures", sid)
    if ok:
        name = data.get("properties",{}).get("name","")
        uid = data.get("properties",{}).get("uid","")
        print(f"  [{sid}] {name}  uid={uid}")
if len(sf_ids) > 3:
    print(f"  ... and {len(sf_ids)-3} more")

# ── DEEP SPOT CHECKS ──
print(f"\n{'─'*40}")
print("DEEP SPOT CHECKS (GeoJSON format)")

# System with geometry
r = s.get(f"{BASE}/systems/04ng?f=geojson")
d = r.json()
print(f"\n  System AZ-MA-1 (04ng):")
print(f"    name: {d['properties']['name']}")
print(f"    uid: {d['properties']['uid']}")
print(f"    validTime: {d['properties'].get('validTime')}")
print(f"    geometry: {d['geometry']['type']} @ {d['geometry']['coordinates']}")

# Subsystem with parent link
r = s.get(f"{BASE}/systems/04p0?f=geojson")
d = r.json()
parent_link = [l for l in d.get("links", []) if l["rel"] == "parent"]
print(f"\n  Subsystem AZ-MA-1-PLATFORM (04p0):")
print(f"    name: {d['properties']['name']}")
print(f"    uid: {d['properties']['uid']}")
print(f"    parent: {parent_link[0]['href'] if parent_link else 'MISSING!'}")

# Deployment with geometry
r = s.get(f"{BASE}/deployments/04cg?f=geojson")
d = r.json()
print(f"\n  Deployment AZ-DEP-AOI-001 (04cg):")
print(f"    name: {d['properties']['name']}")
print(f"    uid: {d['properties']['uid']}")
print(f"    geometry: {d['geometry']['type']}")
print(f"    validTime: {d['properties'].get('validTime')}")

# ── DIRECT URL ACCESSIBILITY ──
print(f"\n{'─'*40}")
print("DIRECT RESOURCE URLs (browser-accessible with ogc:ogc auth)")
print(f"\n  Root API:      {BASE}")
print(f"  AZ-MA-1:       {BASE}/systems/04ng?f=geojson")
print(f"  Subsystems:    {BASE}/systems/04ng/subsystems")
print(f"  AOI Deploy:    {BASE}/deployments/04cg?f=geojson")
print(f"  Procedure:     {BASE}/procedures/04h0")
print(f"  Samp.Feature:  {BASE}/samplingFeatures/052g")
print(f"  Property:      {BASE}/properties/0440")

# ── SUMMARY ──
totals = {}
for label, ids, endpoint in [
    ("Properties", prop_ids, "properties"),
    ("Procedures", proc_ids, "procedures"),
    ("Systems", sys_ids, "systems"),
    ("Deployments", dep_ids, "deployments"),
    ("Sampling Features", sf_ids, "samplingFeatures"),
]:
    count = 0
    for _, sid in ids.items():
        ok, _ = check_resource(endpoint, sid)
        if ok:
            count += 1
    totals[label] = (count, len(ids))

grand_ok = sum(v[0] for v in totals.values())
grand_exp = sum(v[1] for v in totals.values())

print(f"\n{'='*70}")
print("VERIFICATION SUMMARY")
for label, (ok, exp) in totals.items():
    status = "PASS" if ok == exp else "FAIL"
    print(f"  {label:20s} {ok:>3} / {exp}  {status}")
print(f"  {'─'*30}")
print(f"  {'TOTAL':20s} {grand_ok:>3} / {grand_exp}  {'ALL VERIFIED' if grand_ok==grand_exp else 'MISMATCH'}")
print(f"{'='*70}")
