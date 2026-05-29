"""Small FMI Open Data WFS helpers for Finland publishers."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


FMI_WFS = "https://opendata.fmi.fi/wfs"
USER_AGENT = "OS4CSAPI FMI Publisher/1.0"


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _as_float(value) -> float | None:
    if value is None or value == "" or value == "NaN":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or parsed <= -99:
        return None
    return parsed


def parse_simple_wfs(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    rows: list[dict] = []
    for member in root.iter():
        if _local_name(member.tag) != "member":
            continue
        row: dict = {}
        for elem in member.iter():
            name = _local_name(elem.tag)
            text = (elem.text or "").strip()
            if not text:
                continue
            if name in ("Time", "ParameterName", "ParameterValue"):
                row[name] = text
            elif name == "pos":
                parts = text.split()
                if len(parts) >= 2:
                    row["lat"] = _as_float(parts[0])
                    row["lon"] = _as_float(parts[1])
        if row:
            rows.append(row)
    return rows


def build_simple_query_url(stored_query: str, station: dict, *, hours: int) -> str:
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(hours=hours)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "storedquery_id": stored_query,
        "starttime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endtime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "maxlocations": str(station.get("maxlocations", 1)),
    }
    if station.get("bbox"):
        params["bbox"] = station["bbox"]
    elif station.get("place"):
        params["place"] = station["place"]
    return FMI_WFS + "?" + urlencode(params)


def fetch_simple_observation(stored_query: str, station: dict, *, hours: int, parameters: list[str]) -> dict | None:
    url = build_simple_query_url(stored_query, station, hours=hours)
    req = Request(url, headers={"Accept": "application/xml", "User-Agent": USER_AGENT})
    with urlopen(req, timeout=60) as resp:
        rows = parse_simple_wfs(resp.read())

    by_time: dict[str, dict[str, float]] = {}
    source_payload: dict[str, dict[str, str | float | None]] = {}
    for row in rows:
        time_value = row.get("Time")
        param = row.get("ParameterName")
        if not time_value or not param:
            continue
        value = _as_float(row.get("ParameterValue"))
        by_time.setdefault(time_value, {})[param] = value
        source_payload.setdefault(time_value, {})[param] = value

    valid_times = [time_value for time_value, values in by_time.items() if any(values.get(param) is not None for param in parameters)]
    if not valid_times:
        return None

    phenomenon_time = sorted(valid_times)[-1]
    values = by_time[phenomenon_time]
    dt = datetime.fromisoformat(phenomenon_time.replace("Z", "+00:00")).astimezone(timezone.utc)
    return {
        "phenomenonTime": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timestamp": dt.timestamp(),
        "values": {param: values.get(param) for param in parameters},
        "sourceValues": source_payload.get(phenomenon_time, {}),
        "sourceUrl": url,
    }