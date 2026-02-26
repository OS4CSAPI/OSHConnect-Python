"""CSAPI replay helper (HTTP-focused, no OSHConnect dependency).

Generates curl commands for:
  - creating datastreams/controlstreams from templates
  - replaying NDJSON observations/commands

It does not execute requests; it prints commands.
"""
import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
CFG = ROOT / "simulator" / "oshconnect_replay" / "replay_config.json"

def main():
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    api_root = cfg["api_root"].rstrip("/")
    user = cfg["auth"]["username"]
    pw = cfg["auth"]["password"]

    print("# ---- DataStreams (create + replay observations) ----")
    for ds in cfg["datastreams"]:
        tpl = ROOT / ds["createTemplate"]
        nd = ROOT / ds["ndjson"]
        sys_id = ds["systemId"]
        create_url = f"{api_root}/systems/{sys_id}/datastreams"
        print(f"\n# Create datastream for system {sys_id}")
        print(f"curl -u {user}:{pw} -H 'Content-Type: application/json' -d @{tpl} '{create_url}'")
        print("# Replay observations (replace <DATASTREAM_ID>)")
        print(f"curl -u {user}:{pw} -H 'Content-Type: application/json' --data-binary '@{nd}' '{api_root}/datastreams/<DATASTREAM_ID>/observations'")

    print("\n# ---- ControlStreams (create + post commands) ----")
    for cs in cfg["controlstreams"]:
        tpl = ROOT / cs["createTemplate"]
        nd = ROOT / cs["createPayloads"]
        sys_id = cs["systemId"]
        create_url = f"{api_root}/systems/{sys_id}/controlstreams"
        print(f"\n# Create controlstream for system {sys_id}")
        print(f"curl -u {user}:{pw} -H 'Content-Type: application/json' -d @{tpl} '{create_url}'")
        print("# Post command-create payloads (replace <CONTROLSTREAM_ID>)")
        print(f"curl -u {user}:{pw} -H 'Content-Type: application/json' --data-binary '@{nd}' '{api_root}/controlstreams/<CONTROLSTREAM_ID>/commands'")

if __name__ == '__main__':
    main()
