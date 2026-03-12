# OSHConnect Publisher Fleet

A fleet of 9 real-time data publishers that fetch observations from public APIs
and push them into a [CSAPI](https://ogcapi.ogc.org/connectedsystems/)-compliant
server (e.g. [OpenSensorHub](https://opensensorhub.org/)).

## Publishers

| Service | Data Source | Default Cadence |
|---------|-----------|----------------|
| **ISS** | CelesTrak TLE → SGP4 propagation | 30 s |
| **NWS** | NOAA NWS Surface Observations | 1 h |
| **NDBC** | NOAA NDBC Buoy Met Data | 1 h |
| **NDBC BuoyCAM** | NOAA NDBC Camera Imagery | 15 min |
| **CO-OPS** | NOAA CO-OPS Tide Stations | 6 min |
| **Aviation WX** | FAA AviationWeather METAR | 5 min |
| **OpenSky** | OpenSky Network ADS-B | 5 min |
| **USGS Water** | USGS NWIS Water Monitoring | 15 min |
| **USGS NIMS** | USGS NIMS Camera Imagery | 15 min |
| **USGS EQ** | USGS Earthquake Hazards | 60 s |

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (for containerised deployment)
- A running CSAPI server with admin credentials

### 1. Configure

```bash
cp .env.example .env
# Edit .env with your server details:
#   OSH_ADDRESS, OSH_PORT, OSH_USER, OSH_PASS, OSH_ROOT
```

### 2. Bootstrap

Bootstraps are idempotent — safe to re-run. They create the procedures,
systems, datastreams, and deployment hierarchy on your server.

```bash
# Set the env vars (or source .env)
export $(grep -v '^#' .env | xargs)

# Run one bootstrap at a time:
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

### 3. Run (Docker Compose)

```bash
cd publishers
docker compose up -d          # start all
docker compose up -d nws      # start one
docker compose logs -f nws    # follow logs
docker compose ps             # status
docker compose down            # stop all
```

### 4. Run (Standalone)

```bash
export $(grep -v '^#' .env | xargs)
python -m publishers.nws.nws_publisher --interval 3600
```

## Architecture

```
┌─────────────┐    Bootstrap (one-time)     ┌──────────────┐
│  bootstrap_  │ ──────────────────────────► │              │
│  *.py        │  creates procedures,        │  CSAPI       │
│              │  systems, datastreams,      │  Server      │
└─────────────┘  deployments                │  (OSH)       │
                                             │              │
┌─────────────┐    Publisher (continuous)    │              │
│  *_publisher │ ──────────────────────────► │              │
│  .py         │  POSTs observations every   │              │
│              │  N seconds                  │              │
└─────────────┘                              └──────────────┘
       ▲
       │  Fetches from
       ▼
┌─────────────┐
│  Public API  │  NWS, NDBC, USGS, etc.
└─────────────┘
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OSH_ADDRESS` | **Yes** | Server hostname (e.g. `myserver.example.com`) |
| `OSH_PORT` | **Yes** | Server port (usually `443`) |
| `OSH_USER` | **Yes** | Auth username |
| `OSH_PASS` | **Yes** | Auth password |
| `OSH_ROOT` | **Yes** | Server root path (usually `sensorhub`) |
| `BOOTSTRAP_URL` | No | Override the full bootstrap API URL |
| `OSH_FORCE_IP` | No | Force DNS resolution to a specific IP |
| `USGS_API_KEY` | No | USGS API key for higher rate limits |
| `BUOYCAM_CACHE_ROOT` | No | Local directory for BuoyCAM image cache |
| `BUOYCAM_CACHE_BASE_URL` | No | Public URL serving the cached images |

## Notes

- **BuoyCAM** requires a static file server (e.g. Nginx) to serve cached
  JPEG images. Set `BUOYCAM_CACHE_ROOT` to the local directory and
  `BUOYCAM_CACHE_BASE_URL` to the matching public URL.
- **OpenSky** uses the unauthenticated public API. Rate limit is 100 req/day.
- **USGS Water / NIMS** benefit from an optional `USGS_API_KEY`.
- All publishers use `--interval <seconds>` and `--dry-run` CLI flags.
