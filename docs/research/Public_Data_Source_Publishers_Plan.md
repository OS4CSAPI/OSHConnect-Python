# Public Data Source Publishers — Executable Plan

_Created: 2026-03-10_
_Status: PLANNING_

---

## Context

The ISS publisher (`iss_publisher_v3.py` in `csapi-explorer/scripts/`) has proven the OSHConnect-Python → CSAPI pipeline:

- OSHConnect handles connection, system/datastream discovery, and observation POST
- A bootstrap script registers procedures, systems, datastreams, and deployment trees on the server
- A publisher script runs in a `while True` loop, fetching data from an external source and publishing observations at a fixed cadence
- The CSAPI Explorer web app discovers and visualizes everything automatically

This document turns a source evaluation into an executable plan for building additional publishers following the same proven pattern.

---

## Architecture: the proven ISS pattern

Each new data source follows a two-script pattern:

```
bootstrap_{source}.py     — register CSAPI resources (procedures, systems, datastreams, deployments)
{source}_publisher.py     — fetch external data → build observations → POST via OSHConnect
```

Both scripts live in the OSHConnect-Python repo (not csapi-explorer) since they are the OSHConnect-Python client's primary showcase and integration tests.

### Bootstrap script responsibilities

1. Register `Procedure` resources describing the data-processing method
2. Register `System` resources with `typeOf` linking to the procedure
3. Register `Datastream` resources under each system with SWE DataRecord schemas
4. Register a `Deployment` tree placing the systems in operational context
5. Idempotent: skip-if-exists, support `--clean` for teardown/recreate

### Publisher script responsibilities

1. Connect to OSH server via OSHConnect (`OSHConnect` → `Node` → discover system → discover datastream)
2. Fetch data from the external API at a configured cadence
3. Build observation payloads conforming to the datastream's schema
4. POST observations via OSHConnect's `Datastream.push_observation()` (or equivalent)
5. Handle reconnection, TLE/data refresh, and error recovery
6. CLI flags: `--dry-run`, `--once`, `--interval`, `--help`

---

## Source evaluation summary

### Tier 1 — lowest friction, highest demo value

| # | Source | Type | Auth | Cadence | CSAPI pattern |
|---|--------|------|------|---------|---------------|
| 1 | **Open Notify ISS** | Moving platform | None | 5–30s | Single system, position datastream |
| 2 | **NWS API** (api.weather.gov) | Fixed stations / forecasts | None (User-Agent required) | 1h (obs), 6h (fcst) | Station-per-system, weather datastreams |
| 3 | **AviationWeather.gov** | Fixed stations / METAR/TAF | None | ~1h (METAR), 6h (TAF) | Airport-per-system, aviation-wx datastreams |
| 4 | **NOAA NDBC** | Fixed buoys | None | 10min–1h | Buoy-per-system, met/wave datastreams |
| 5 | **NOAA CO-OPS** | Fixed coastal stations | None | 6min (water level) | Station-per-system, tide/current datastreams |

### Tier 2 — real tracking, more friction

| # | Source | Type | Auth | Cadence | CSAPI pattern |
|---|--------|------|------|---------|---------------|
| 6 | **OpenSky Network** | Aircraft tracking | OAuth2 (or anon with limits) | 5–10s | Feed-adapter system or per-aircraft systems |
| 7 | **AISHub** | Vessel tracking | Membership | ≥60s | Feed-adapter system or per-vessel systems |
| 8 | **CelesTrak GP** | Orbital propagation | None | 30s (publish), TLE refresh 1h | Already implemented (ISS v3 uses this) |

### Tier 3 — paid / commercial

| # | Source | Type | Auth | Notes |
|---|--------|------|------|-------|
| 9 | FlightAware AeroAPI | Aviation | API key + subscription | Upgrade path |
| 10 | MarineTraffic API | Maritime | Sales account | Upgrade path |

---

## Executable implementation plan

### Phase 1 — Fixed-station environmental demos (weeks 1–3)

These are the highest-value-per-effort publishers because fixed stations map 1:1 to CSAPI systems and require no object-lifecycle management.

#### Publisher 1: NWS Weather Observations + Forecasts

**External API:** `https://api.weather.gov/stations/{stationId}/observations/latest`
**Update cadence:** 60 min (observations), 360 min (forecasts)
**Auth:** None (User-Agent header required per NWS policy)

**CSAPI resources to bootstrap:**

```
Procedure:   urn:os4csapi:procedure:nws-surface-observation:v1
Systems:     urn:os4csapi:system:nws:{stationId}  (one per station)
Datastreams: "Surface Observation"  per station
             "Point Forecast"      per station (optional)
Deployment:  urn:os4csapi:deployment:nws-weather-demo:v1
```

**Observation schema (normalized):**

```json
{
  "timestamp": 1773100000.0,
  "stationId": "KTUS",
  "stationName": "Tucson International Airport",
  "lat_deg": 32.1161,
  "lon_deg": -110.9413,
  "temperature_c": 28.3,
  "dewpoint_c": 8.9,
  "humidity_pct": 25,
  "wind_speed_kmh": 15.0,
  "wind_direction_deg": 220,
  "wind_gust_kmh": null,
  "barometric_pressure_pa": 101325,
  "visibility_m": 16093,
  "description": "Fair",
  "raw_metar": "KTUS 091856Z 22008KT 10SM FEW250 28/09 A2993"
}
```

**Station selection for demo:** 3–5 stations near Fort Huachuca / southern Arizona:
- KTUS (Tucson), KDMA (Davis-Monthan), KFHU (Fort Huachuca), KLUF (Luke AFB), KPHX (Phoenix)

**Estimated effort:** 1 day bootstrap, 1 day publisher

---

#### Publisher 2: NOAA NDBC Buoy Observations

**External API:** `https://www.ndbc.noaa.gov/data/realtime2/{stationId}.txt` (or JSON via DODS)
**Update cadence:** 30–60 min
**Auth:** None

**CSAPI resources to bootstrap:**

```
Procedure:   urn:os4csapi:procedure:ndbc-buoy-observation:v1
Systems:     urn:os4csapi:system:ndbc:{stationId}  (one per buoy)
Datastreams: "Marine Met Observation"  per buoy
             "Wave Observation"        per buoy (if wave data available)
Deployment:  urn:os4csapi:deployment:ndbc-buoy-demo:v1
```

**Observation schema (normalized):**

```json
{
  "timestamp": 1773100000.0,
  "stationId": "46025",
  "lat_deg": 33.749,
  "lon_deg": -119.053,
  "wind_speed_ms": 5.2,
  "wind_direction_deg": 290,
  "wind_gust_ms": 7.1,
  "wave_height_m": 1.8,
  "dominant_wave_period_s": 8.0,
  "mean_wave_direction_deg": 270,
  "air_temp_c": 15.3,
  "water_temp_c": 16.1,
  "pressure_hpa": 1015.2,
  "visibility_nmi": null
}
```

**Station selection:** 3–5 Pacific/Gulf buoys with good data availability

**Estimated effort:** 1 day bootstrap, 1 day publisher

---

#### Publisher 3: NOAA CO-OPS Tides & Currents

**External API:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
**Update cadence:** 6 min (verified water levels), 60 min (met data)
**Auth:** None

**CSAPI resources to bootstrap:**

```
Procedure:   urn:os4csapi:procedure:coops-water-level:v1
             urn:os4csapi:procedure:coops-met-observation:v1 (optional)
Systems:     urn:os4csapi:system:coops:{stationId}
Datastreams: "Water Level"      per station
             "Met Observation"  per station (optional)
Deployment:  urn:os4csapi:deployment:coops-coastal-demo:v1
```

**Observation schema (water level):**

```json
{
  "timestamp": 1773100000.0,
  "stationId": "8723214",
  "stationName": "Virginia Key, Biscayne Bay, FL",
  "lat_deg": 25.7317,
  "lon_deg": -80.1617,
  "water_level_m": 0.234,
  "prediction_m": 0.198,
  "datum": "MLLW",
  "quality": "v",
  "sigma": 0.003
}
```

**Station selection:** 3–5 coastal stations (mix of East/West/Gulf)

**Estimated effort:** 1 day bootstrap, 1 day publisher

---

#### Publisher 4: AviationWeather.gov METAR/TAF

**External API:** `https://aviationweather.gov/api/data/metar?ids={icao}&format=json`
**Update cadence:** 60 min (METAR), 360 min (TAF)
**Auth:** None

**CSAPI resources to bootstrap:**

```
Procedure:   urn:os4csapi:procedure:metar-decoder:v1
             urn:os4csapi:procedure:taf-decoder:v1  (optional)
Systems:     urn:os4csapi:system:awx:{icaoId}
Datastreams: "METAR Observation"  per station
             "TAF Forecast"       per station (optional)
Deployment:  urn:os4csapi:deployment:aviation-weather-demo:v1
```

**Observation schema (METAR, normalized):**

```json
{
  "timestamp": 1773100000.0,
  "icaoId": "KTUS",
  "stationName": "Tucson Intl",
  "lat_deg": 32.1161,
  "lon_deg": -110.9413,
  "elev_m": 779,
  "temperature_c": 28.3,
  "dewpoint_c": 8.9,
  "wind_speed_kt": 8,
  "wind_direction_deg": 220,
  "wind_gust_kt": null,
  "visibility_sm": 10.0,
  "altimeter_inhg": 29.93,
  "flight_category": "VFR",
  "cloud_layers": [{"cover": "FEW", "base_ft_agl": 25000}],
  "raw_metar": "KTUS 091856Z 22008KT 10SM FEW250 28/09 A2993",
  "raw_text": "KTUS 091856Z 22008KT 10SM FEW250 28/09 A2993 RMK AO2"
}
```

**Station selection:** Same AZ stations as NWS publisher (KTUS, KDMA, KFHU, KLUF, KPHX)

**Estimated effort:** 1 day bootstrap, 1 day publisher

---

### Phase 2 — Live tracking feeds (weeks 4–5)

#### Publisher 5: OpenSky Aircraft Tracking

**External API:** `https://opensky-network.org/api/states/all?lamin=...&lomin=...&lamax=...&lomax=...`
**Update cadence:** 10s (authenticated), 30s (anonymous — but limited)
**Auth:** OAuth2 token or anonymous (with aggressive rate limits)

**CSAPI resources to bootstrap (Pattern C — feed adapter):**

```
Procedure:   urn:os4csapi:procedure:opensky-adsb-decoder:v1
System:      urn:os4csapi:system:opensky-feed:v1
Datastream:  "Aircraft State Vectors"
Deployment:  urn:os4csapi:deployment:airspace-tracking-demo:v1
```

**Observation schema (one obs per aircraft-state snapshot):**

```json
{
  "timestamp": 1773100000.0,
  "icao24": "a12345",
  "callsign": "UAL1234",
  "origin_country": "United States",
  "lat_deg": 32.5,
  "lon_deg": -110.8,
  "baro_altitude_m": 10668,
  "geo_altitude_m": 10700,
  "velocity_ms": 230.5,
  "true_track_deg": 135.0,
  "vertical_rate_ms": 0.0,
  "on_ground": false,
  "squawk": "1200",
  "spi": false,
  "category": 3,
  "source": "OpenSky"
}
```

**Bounding box for demo:** Southern Arizona airspace
**Key risk:** OpenSky auth changes in 2025 may require OAuth2 token flow

**Estimated effort:** 1 day bootstrap, 2 days publisher (auth + multi-object handling)

---

#### Publisher 6: AISHub Vessel Tracking

**External API:** `https://data.aishub.net/ws.php?username={key}&format=1&output=json&latmin=...&lonmin=...&latmax=...&lonmax=...`
**Update cadence:** 60s (minimum per AISHub policy)
**Auth:** Membership / API key

**CSAPI resources to bootstrap (Pattern C — feed adapter):**

```
Procedure:   urn:os4csapi:procedure:ais-nmea-decoder:v1
System:      urn:os4csapi:system:aishub-feed:v1
Datastream:  "AIS Position Reports"
Deployment:  urn:os4csapi:deployment:maritime-tracking-demo:v1
```

**Observation schema (one obs per vessel report):**

```json
{
  "timestamp": 1773100000.0,
  "mmsi": "367000000",
  "vessel_name": "PACIFIC TRADER",
  "imo": 9123456,
  "lat_deg": 33.72,
  "lon_deg": -118.27,
  "sog_kt": 12.5,
  "cog_deg": 285.0,
  "heading_deg": 283,
  "nav_status": 0,
  "ship_type": 70,
  "draught_m": 8.5,
  "destination": "LONG BEACH",
  "source": "AISHub"
}
```

**Bounding box for demo:** LA/Long Beach port area or Gulf of Mexico
**Key risk:** AISHub requires membership application

**Estimated effort:** 1 day bootstrap, 1.5 days publisher

---

### Phase 3 — Graduation upgrades (week 6+)

- Replace Open Notify ISS with CelesTrak GP _(already done — v3 uses CelesTrak)_
- Add per-aircraft `System` creation for tracked aircraft (OpenSky Pattern B)
- Add per-vessel `System` creation for tracked vessels (AISHub Pattern B)
- Add FlightAware AeroAPI or MarineTraffic API if budget allows
- Add richer SWE/domain-specific schemas alongside normalized schemas

---

## Shared infrastructure

### Common publisher base class

All publishers share 80%+ of their boilerplate. Extract a shared base:

```python
# oshconnect_publishers/base.py

class PublisherBase:
    """Common base for all OSHConnect CSAPI publishers."""

    def __init__(self, name: str, system_uid: str, ds_name: str):
        self.name = name
        self.system_uid = system_uid
        self.ds_name = ds_name
        self.app = None
        self.node = None
        self.datastream = None
        self.stats = {"published": 0, "errors": 0, "reconnects": 0}

    def connect(self):
        """Connect to OSH server and discover system + datastream."""
        ...

    def connect_with_retry(self, max_attempts=10, base_delay=5.0):
        """Connect with exponential backoff + jitter."""
        ...

    def publish(self, observation: dict, dry_run: bool = False):
        """POST a single observation."""
        ...

    def run_loop(self, interval: float, fetch_fn, build_fn, **kwargs):
        """Main loop: fetch → build → publish → sleep."""
        ...

    @staticmethod
    def add_common_args(parser: argparse.ArgumentParser):
        """Add --dry-run, --once, --interval, --help to any publisher CLI."""
        ...
```

### Common bootstrap helpers

Likewise, extract idempotent resource-creation helpers:

```python
# oshconnect_publishers/bootstrap_helpers.py

def ensure_procedure(base_url, auth, uid, body): ...
def ensure_system(base_url, auth, uid, body, sml_body=None): ...
def ensure_datastream(base_url, auth, system_id, output_name, schema): ...
def ensure_deployment(base_url, auth, uid, body, parent_id=None): ...
def find_by_uid(base_url, auth, resource_type, uid): ...
```

### Deployment model

All publishers deploy as persistent processes. Options (in order of recommendation):

1. **Fly.io** — already proven for the simulator; $0 for small instances, easy Dockerfile
2. **Oracle Cloud VM** — already running OSH + ISS publisher; just add more `screen`/`systemd` processes
3. **GitHub Actions scheduled workflow** — works for low-cadence publishers (>5 min cadence)

---

## Engineering assessment and recommendations

### What this plan gets right

1. **Proven pattern.** The ISS publisher has been running 24/7 for weeks without intervention. Every new publisher follows the exact same OSHConnect connection → discovery → publish loop. The risk of the pattern itself is near zero.

2. **Fixed-station sources first.** NWS/NDBC/CO-OPS/AviationWeather are the right Phase 1 choices. They are zero-auth, high-reliability government APIs with stable schemas. Each station maps 1:1 to a CSAPI System — no object-lifecycle decisions, no identity management, no cardinality explosion. This is exactly the right order.

3. **Normalized-first schemas.** Starting with flat JSON result objects and adding SWE DataRecord richness later is pragmatic. The ISS publisher proved this: a simple `result` dict with typed fields works immediately with OSH SensorHub and renders in CSAPI Explorer without any schema negotiation.

4. **Feed-adapter pattern for tracking.** Using a single "feed" system for OpenSky/AISHub (Pattern C) avoids the combinatorial explosion of creating thousands of per-aircraft or per-vessel systems. This is the correct first approach — you can graduate to per-object systems later once the pipeline is stable.

5. **Demo geography convergence.** Selecting AZ-area weather stations and using southern AZ bounding boxes for aircraft tracking puts all demo data in the same map viewport as the existing acoustic-sensing / UAS detection demo. Users see a rich, coherent operational picture instead of scattered unrelated feeds.

### Risks and mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| NWS API enforces strict User-Agent policy; bare requests may get 403 | Low | Set `User-Agent: os4csapi-publisher/1.0 (contact@os4csapi.org)` in all NWS requests |
| OpenSky OAuth2 token flow is underdocumented for new accounts | Medium | Start anonymous with AZ bounding box (small area = fewer states = less rate-limit pressure); budget time for OAuth2 integration |
| AISHub membership approval is not instant | Low | Apply now; start with NDBC/CO-OPS for maritime demo while waiting |
| NDBC real-time text files change format occasionally | Low | Parse defensively; alert on schema mismatch |
| Running 6+ publisher processes on the Oracle VM may stress it | Medium | Monitor memory; consider Fly.io for non-critical publishers |
| OSH SensorHub scope-leak bug may contaminate new datastreams | Medium | Already handled in CSAPI Explorer; publisher-side is unaffected |

### What I would change

1. **Repo location.** The plan says publishers live in `OSHConnect-Python`. I partially agree — they are the best showcase of OSHConnect as a client library. But the bootstrap scripts use raw HTTP (no OSHConnect dependency) and are tightly coupled to the server's resource model. I would structure it as:

   ```
   OSHConnect-Python/
     publishers/
       base.py                    ← shared publisher base class
       bootstrap_helpers.py       ← shared bootstrap utilities
       nws/
         bootstrap_nws.py
         nws_publisher.py
       ndbc/
         bootstrap_ndbc.py
         ndbc_publisher.py
       coops/
         bootstrap_coops.py
         coops_publisher.py
       aviation_wx/
         bootstrap_aviation_wx.py
         aviation_wx_publisher.py
       opensky/
         bootstrap_opensky.py
         opensky_publisher.py
       aishub/
         bootstrap_aishub.py
         aishub_publisher.py
       iss/
         bootstrap_iss.py          ← migrated from csapi-explorer/scripts/
         iss_publisher_v3.py       ← migrated from csapi-explorer/scripts/
     docs/research/
       Public_Data_Source_Publishers_Plan.md  ← this document
   ```

   The existing ISS scripts should migrate from `csapi-explorer/scripts/` to `OSHConnect-Python/publishers/iss/` to consolidate all publishers in one place.

2. **Extract the base class before building publisher 2.** The temptation will be to copy-paste `iss_publisher_v3.py` and modify it. Resist this. The ISS publisher has ~200 lines of OSHConnect boilerplate (connect, retry, reconnect, stats, CLI args) that should be extracted into `base.py` before the second publisher is written. This pays for itself immediately on publisher 3+.

3. **One Dockerfile per publisher, compose for the fleet.** Rather than running bare Python processes in `screen` sessions:

   ```yaml
   # docker-compose.yml in OSHConnect-Python/publishers/
   services:
     iss:
       build: ./iss
       restart: always
       environment:
         - OSH_ADDRESS=os4csapi-osh.duckdns.org
     nws:
       build: ./nws
       restart: always
     ndbc:
       build: ./ndbc
       restart: always
     ...
   ```

   This makes the fleet manageable, restartable, and deployable to any Docker host.

4. **Add a health/status endpoint.** The ISS publisher is silent unless you're watching its stdout. For a fleet of 6+ publishers, add a tiny HTTP health endpoint (FastAPI or even a raw socket) that reports last-publish time, error count, and uptime. The simulator already does this.

5. **Phase 1 priority order.** I would reorder Phase 1 slightly:

   1. **NWS** — richest API, most fields, strongest institutional credibility
   2. **AviationWeather.gov METAR** — nearly identical pattern to NWS but aviation domain
   3. **NOAA CO-OPS** — water levels are visually compelling and refresh fast (6 min)
   4. **NOAA NDBC** — similar to CO-OPS but buoys are offshore (less visual overlap with existing AZ demo)

   I'd do NWS + AviationWeather first because they share the AZ geography with the existing demo, creating the richest composite picture soonest.

6. **Station configuration as JSON, not hardcoded.** Instead of hardcoding station IDs in each bootstrap script, use a `stations.json` config file:

   ```json
   {
     "nws_stations": ["KTUS", "KDMA", "KFHU", "KLUF", "KPHX"],
     "ndbc_buoys": ["46025", "46086", "41009"],
     "coops_stations": ["8723214", "9410660", "8726520"],
     "aviation_stations": ["KTUS", "KDMA", "KFHU", "KLUF", "KPHX"]
   }
   ```

   This makes it trivial for someone demoing in a different region to swap in local stations without editing code.

### Build-order recommendation

| Week | Deliverable | Est. effort |
|------|-------------|-------------|
| 1 | Extract `base.py` + `bootstrap_helpers.py` from ISS publisher; migrate ISS to `publishers/iss/` | 1 day |
| 1 | NWS publisher (bootstrap + publisher + Dockerfile) | 2 days |
| 2 | AviationWeather.gov METAR publisher | 1.5 days |
| 2 | NOAA CO-OPS publisher | 1.5 days |
| 3 | NOAA NDBC publisher | 1.5 days |
| 3 | Docker Compose for fleet; deploy to Oracle or Fly.io | 1 day |
| 4 | OpenSky publisher (auth research + implementation) | 3 days |
| 5 | AISHub publisher (pending membership approval) | 2 days |
| 5 | CSAPI Explorer enhancements for new data types | 2 days |

**Total estimated effort: ~16 working days across 5 weeks.**

---

## CSAPI Explorer integration notes

The web app (`MapViewPage.vue`) auto-discovers systems, deployments, and datastreams. New publishers will appear automatically on the map if:

1. Systems have geometry (location) set via bootstrap
2. Datastream observations include lat/lon fields that `extractLatLonFromResult()` can parse
3. Deployment trees link systems via `platform@link`

For weather stations and buoys, the map will show fixed markers at station locations. For tracking feeds (OpenSky, AISHub), the observations contain per-object coordinates that will appear as observation points.

Specific Explorer enhancements that would improve the experience:
- Weather popup showing temperature/wind/pressure instead of raw JSON
- Buoy popup with wave state visualization
- Aircraft/vessel popup with callsign, altitude, speed
- Layer toggle per publisher source (NWS, NDBC, aviation, etc.)

These are follow-on tasks in `csapi-explorer`, not blockers for the publishers.

---

## Reference links

### APIs

- NWS API: https://www.weather.gov/documentation/services-web-api
- AviationWeather.gov: https://aviationweather.gov/api/data/
- NOAA NDBC: https://www.ndbc.noaa.gov/
- NOAA CO-OPS: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
- Open-Meteo: https://open-meteo.com/en/docs
- OpenSky: https://openskynetwork.github.io/opensky-api/rest.html
- AISHub: https://www.aishub.net/api
- CelesTrak: https://www.celestrak.org/NORAD/documentation/gp-data-formats.php

### Existing code (proven patterns)

- ISS bootstrap: `csapi-explorer/scripts/bootstrap_iss.py` (1120 lines)
- ISS publisher v3: `csapi-explorer/scripts/iss_publisher_v3.py` (639 lines)
- UAV simulator: `csapi-explorer/simulator/` (engine.py + main.py)
- OSHConnect-Python fork: https://github.com/OS4CSAPI/OSHConnect-Python
