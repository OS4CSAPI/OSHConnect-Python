import requests, json

s = requests.Session()
s.auth = ("os4csapi", "ogc134mm")
base = "http://os4csapi-osh.duckdns.org/sensorhub/api"

# Check ICO (040g) subdeployments - should contain RSO
r = s.get(f"{base}/deployments/040g/subdeployments", headers={"Accept": "application/json"})
items = r.json().get("items", [])
print(f"ICO subdeployments ({len(items)}):")
for i in items:
    print(f"  {i.get('id')}: {i.get('properties', {}).get('name')}")

# Check full deployment list
r2 = s.get(f"{base}/deployments", headers={"Accept": "application/json"})
items2 = r2.json().get("items", [])
print(f"\nAll deployments ({len(items2)}):")
for i in items2:
    props = i.get("properties", {})
    print(f"  {i.get('id')}: {props.get('name')} — partOf: {props.get('partOf@link', {}).get('href', 'none')}")

# Check systems + datastreams
r3 = s.get(f"{base}/systems", headers={"Accept": "application/json"})
items3 = r3.json().get("items", [])
print(f"\nAll systems ({len(items3)}):")
for i in items3:
    sid = i.get("id")
    name = i.get("properties", {}).get("name")
    # Check datastreams
    r4 = s.get(f"{base}/systems/{sid}/datastreams", headers={"Accept": "application/json"})
    ds = r4.json().get("items", [])
    ds_names = [d.get("name", "?") for d in ds]
    print(f"  {sid}: {name} — datastreams: {ds_names if ds_names else 'none'}")
