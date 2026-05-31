# Finland Oracle Service Deployment 2026-05-31

## Scope

Deployed the Finnish publisher set as persistent systemd services on the Oracle publisher host `129.80.248.53`.

Remote working tree:

```text
/home/ubuntu/oshconnect-python-publishers
```

Deployed repository revision:

```text
ee312b2 Wire Digitraffic weathercam publisher into fleet
```

All services use the host-local environment file:

```text
/etc/os4csapi/publisher-secrets.env
```

## Services Installed

| Service | Command | Cadence |
| --- | --- | --- |
| `digitraffic-marine-ais-publisher.service` | `python3 -u -m publishers.digitraffic_marine_ais.digitraffic_marine_ais_publisher --interval 300` | 5 min |
| `digitraffic-rail-trains-publisher.service` | `python3 -u -m publishers.digitraffic_rail_trains.digitraffic_rail_trains_publisher --interval 300` | 5 min |
| `digitraffic-road-weather-publisher.service` | `python3 -u -m publishers.digitraffic_road_weather.digitraffic_road_weather_publisher --interval 300` | 5 min |
| `digitraffic-weathercam-publisher.service` | `python3 -u -m publishers.digitraffic_weathercam.digitraffic_weathercam_publisher --interval 300` | 5 min |
| `fmi-weather-publisher.service` | `python3 -u -m publishers.fmi_weather.fmi_weather_publisher --interval 600` | 10 min |
| `fmi-air-quality-publisher.service` | `python3 -u -m publishers.fmi_air_quality.fmi_air_quality_publisher --interval 3600` | 1 h |
| `syke-hydrology-publisher.service` | `python3 -u -m publishers.syke_hydrology.syke_hydrology_publisher --interval 900` | 15 min |

Each service is enabled and active under systemd.

## First Service Cycles

Observed first service-managed cycles in `journalctl`:

| Source | Result |
| --- | --- |
| Digitraffic Marine AIS | 60 vessels published, 0 skipped, 0 errors |
| Digitraffic Rail Trains | 80 train positions published, 0 skipped, 0 errors |
| Digitraffic Road Weather | 6 stations connected and published, 0 visible errors |
| Digitraffic Weathercam | 6 cameras connected and published, 0 visible errors |
| FMI Weather | 6 stations connected and published, 0 visible errors |
| FMI Air Quality | 6 stations connected and published, 0 visible errors |
| SYKE Hydrology | 4 stations connected, 7 readings published, 0 errors |

## Public Verification

Verified through `https://ogc-csapi-explorer.pages.dev/api/osh` that fresh observations were visible for representative datastreams:

| Source | Datastream | Verified timestamp |
| --- | --- | --- |
| Digitraffic Marine AIS | `07hg2` | `2026-05-31T05:25:32Z` |
| Digitraffic Rail Trains | `07i02` | `2026-05-31T08:12:22Z` |
| Digitraffic Road Weather | `075g2` | `2026-05-31T05:25:24Z` |
| Digitraffic Weathercam | `078g2` | `2026-05-31T05:15:49Z` |
| FMI Weather | `07bg2` | `2026-05-31T05:20:00Z` |
| FMI Air Quality | `07eg2` | `2026-05-31T05:00:00Z` |
| SYKE Hydrology | `07ig2` | `2026-05-31T00:00:00Z` |
