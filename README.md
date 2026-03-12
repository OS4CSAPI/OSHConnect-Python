# OSHConnect-Python

A Python library + publisher fleet for [OGC Connected Systems API (CSAPI)](https://ogcapi.ogc.org/connectedsystems/) servers such as [OpenSensorHub](https://opensensorhub.org/).

## What's in this repo

| Directory | What it does |
|-----------|-------------|
| `src/` | **OSHConnect library** — Python client for CSAPI (systems, datastreams, observations, real-time, batch) |
| `publishers/` | **Publisher fleet** — 9 real-time data publishers that fetch from public APIs and push observations |
| `scripts/` | One-off admin/migration scripts |
| `scenarios/` | Scenario packs for testing |
| `tests/` | Unit tests for the library |
| `docs/` | Research notes, design docs, conformance reports |

## Quick Start — Publisher Fleet

The publisher fleet fetches live data from NWS, NDBC, CO-OPS, AviationWeather,
OpenSky, USGS Water, USGS NIMS, USGS Earthquake, and ISS (CelesTrak) — and
publishes observations to your CSAPI server.

### Prerequisites

- Python 3.12+
- A running CSAPI server (e.g. OpenSensorHub) with admin credentials
- Docker & Docker Compose (for containerised deployment, optional)

### 1. Clone & configure

```bash
git clone https://github.com/OS4CSAPI/OSHConnect-Python.git
cd OSHConnect-Python/publishers

# Create your config from the template
cp .env.example .env
```

Edit `.env` with your server details:

```dotenv
OSH_ADDRESS=myserver.example.com
OSH_PORT=443
OSH_USER=admin
OSH_PASS=my-secret-password
OSH_ROOT=sensorhub
```

### 2. Bootstrap your server

Bootstraps create the procedures, systems, datastreams, and deployment hierarchy
on your server. They are idempotent — safe to re-run.

```bash
# Load env vars
export $(grep -v '^#' .env | xargs)

# Run each bootstrap (order doesn't matter)
python -m publishers.nws.bootstrap_nws
python -m publishers.ndbc.bootstrap_ndbc
python -m publishers.coops.bootstrap_coops
python -m publishers.aviation_wx.bootstrap_aviation_wx
python -m publishers.opensky.bootstrap_opensky
python -m publishers.usgs_water.bootstrap_usgs_water
python -m publishers.usgs_nims.bootstrap_usgs_nims
python -m publishers.usgs_eq.bootstrap_usgs_eq
python -m publishers.iss.bootstrap_iss
```

> **Windows (PowerShell):** Instead of `export`, set each variable:
> ```powershell
> Get-Content publishers\.env | ForEach-Object {
>     if ($_ -match '^([^#]\S+?)=(.*)$') {
>         [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
>     }
> }
> ```

### 3. Start publishers

**Option A — Docker Compose** (recommended for production):

```bash
cd publishers
docker compose up -d          # start all 10 services
docker compose logs -f nws    # follow one service
docker compose ps             # check status
docker compose down           # stop all
```

**Option B — Standalone** (for development/testing):

```bash
export $(grep -v '^#' .env | xargs)
python -m publishers.nws.nws_publisher --interval 3600
python -m publishers.nws.nws_publisher --dry-run    # print without publishing
python -m publishers.nws.nws_publisher --once        # single cycle then exit
```

### 4. Verify

Open your server's API explorer at `https://<your-server>/sensorhub/api` and
check that systems, datastreams, and observations are appearing.

## Publisher Fleet Summary

| Service | Data Source | Default Cadence |
|---------|-----------|----------------|
| ISS | CelesTrak TLE → SGP4 | 30 s |
| NWS | NOAA NWS Surface Obs | 1 h |
| NDBC | NOAA NDBC Buoy Met | 1 h |
| NDBC BuoyCAM | NOAA NDBC Camera JPEGs | 15 min |
| CO-OPS | NOAA Tide Stations | 6 min |
| Aviation WX | FAA METAR | 5 min |
| OpenSky | ADS-B Aircraft Tracking | 5 min |
| USGS Water | NWIS Water Monitoring | 15 min |
| USGS NIMS | NWIS Camera Imagery | 15 min |
| USGS EQ | Earthquake Hazards | 60 s |

See [publishers/README.md](publishers/README.md) for detailed environment variables,
architecture diagram, and per-publisher notes.

## OSHConnect Library

```bash
pip install git+https://github.com/OS4CSAPI/OSHConnect-Python.git
```

API Documentation: [https://botts-innovative-research.github.io/OSHConnect-Python/](https://botts-innovative-research.github.io/OSHConnect-Python/)

## License

See [LICENSE](LICENSE).