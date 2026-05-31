# OSHConnect Publisher Fleet

A fleet of real-time data publishers that fetch observations from public APIs
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
| **Environment Agency Hydrology** | EA river level, flow, rainfall, groundwater | 15 min |
| **UK-AIR** | Defra UK-AIR NO2, O3, PM10, PM2.5 | 1 h |
| **BGS SensorThings** | BGS UKGEOS Glasgow groundwater/geothermal telemetry | 15 min |
| **Met Office DataHub** | Land Observations hourly weather data | Access-gated / 1 h |
| **Met Office Global Spot** | Site-specific deterministic hourly forecasts | Access-gated / 1 h |
| **Digitraffic Marine AIS** | Finnish Fintraffic/Digitraffic AIS vessel positions | 5 min |
| **Digitraffic Road Weather** | Finnish Fintraffic/Digitraffic road-weather stations | 5 min |
| **Digitraffic Weathercam** | Finnish Fintraffic/Digitraffic road-camera image references | 5 min |
| **FMI Weather** | Finnish Meteorological Institute weather observations | 10 min |
| **FMI Air Quality** | Finnish Meteorological Institute air-quality observations | 1 h |

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
python -m publishers.environment_agency_hydrology.bootstrap_environment_agency_hydrology
python -m publishers.uk_air.bootstrap_uk_air
python -m publishers.bgs_sensorthings.bootstrap_bgs_sensorthings
# Met Office DataHub is access-gated; see publishers/met_office_datahub/README.md
python -m publishers.met_office_datahub.bootstrap_met_office_datahub
# Met Office Global Spot is access-gated; see publishers/met_office_global_spot/README.md
python -m publishers.met_office_global_spot.bootstrap_met_office_global_spot
python -m publishers.digitraffic_marine_ais.bootstrap_digitraffic_marine_ais
python -m publishers.digitraffic_road_weather.bootstrap_digitraffic_road_weather
python -m publishers.digitraffic_weathercam.bootstrap_digitraffic_weathercam
python -m publishers.fmi_weather.bootstrap_fmi_weather
python -m publishers.fmi_air_quality.bootstrap_fmi_air_quality
python -m publishers.iss.bootstrap_iss
```

### 3. Run (Docker Compose)

```bash
cd publishers
docker compose up -d          # start all
docker compose up -d nws      # start one
docker compose --profile access-gated up -d met-office-datahub
docker compose --profile access-gated up -d met-office-global-spot
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
| `PUBLISHERS_ENV_FILE` | No | Standalone runtime override for the env file loaded by publishers that support local env loading |
| `OSH_FORCE_IP` | No | Force DNS resolution to a specific IP |
| `USGS_API_KEY` | No | USGS API key for higher rate limits |
| `MET_OFFICE_LAND_OBSERVATIONS_API_KEY` | For Met Office | Met Office Weather DataHub Land Observations subscription key |
| `MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE` | For Met Office | Host-local file containing the Land Observations key; useful for Oracle/systemd secrets |
| `MET_OFFICE_GLOBAL_SPOT_API_KEY` | For Met Office Global Spot | Met Office Weather DataHub Site-Specific Forecast / Global Spot subscription key |
| `MET_OFFICE_GLOBAL_SPOT_API_KEY_FILE` | For Met Office Global Spot | Host-local file containing the Global Spot key; useful for Oracle/systemd secrets |
| `BUOYCAM_CACHE_ROOT` | No | Local directory for BuoyCAM image cache |
| `BUOYCAM_CACHE_BASE_URL` | No | Public URL serving the cached images |

## Notes

- **BuoyCAM** requires a static file server (e.g. Nginx) to serve cached
  JPEG images. Set `BUOYCAM_CACHE_ROOT` to the local directory and
  `BUOYCAM_CACHE_BASE_URL` to the matching public URL.
- **OpenSky** uses the unauthenticated public API. Rate limit is 100 req/day.
- **USGS Water / NIMS** benefit from an optional `USGS_API_KEY`.
- **Environment Agency Hydrology** uses public OGL Hydrology API JSON endpoints
  and polls only the curated measures in `stations.json`.
- **UK-AIR** uses public OGL SOS / 52 North Timeseries REST endpoints and polls
  only the curated pollutant timeseries in `stations.json`.
- **BGS SensorThings** uses the public BGS Sensor Data Service SensorThings API
  and polls only curated unrestricted UKGEOS Glasgow datastreams in `stations.json`.
- **Met Office DataHub** uses the access-gated Land Observations API and reads
  `MET_OFFICE_LAND_OBSERVATIONS_API_KEY` from the environment, or
  `MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE` from a host-local secret file. It
  caches nearest geohash lookups in ignored runtime state to stay within the
  free-plan call budget. In Docker Compose it is behind the `access-gated`
  profile, so public publishers can still start without a Met Office key.
- **Met Office Global Spot** uses the access-gated Site-Specific Forecast API
  and reads `MET_OFFICE_GLOBAL_SPOT_API_KEY` from the environment, or
  `MET_OFFICE_GLOBAL_SPOT_API_KEY_FILE` from a host-local secret file. It
  publishes deterministic hourly forecast values for virtual forecast points,
  not physical sensor observations, and is also behind the `access-gated`
  Docker Compose profile.
- **Digitraffic Weathercam** attaches image-reference observations to curated
  Digitraffic road-weather station systems, using direct Fintraffic JPEG and
  thumbnail URLs for road camera presets.
- All publishers use `--interval <seconds>` and `--dry-run` CLI flags.
