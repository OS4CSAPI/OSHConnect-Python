# Digitraffic Road Weather Publisher

Publishes a curated first Finland datasource: Fintraffic Digitraffic road-weather station observations.

Source endpoints:

- Station metadata: `https://tie.digitraffic.fi/api/weather/v1/stations`
- Latest all-station data: `https://tie.digitraffic.fi/api/weather/v1/stations/data`
- Station-specific data: `https://tie.digitraffic.fi/api/weather/v1/stations/{id}/data`

Initial curated stations are listed in `stations.json` and cover southern, western, eastern, central, and northern Finland.

## Bootstrap

```powershell
py publishers/digitraffic_road_weather/bootstrap_digitraffic_road_weather.py --dry-run
py publishers/digitraffic_road_weather/bootstrap_digitraffic_road_weather.py --force-sml
```

## Publish

```powershell
py publishers/digitraffic_road_weather/digitraffic_road_weather_publisher.py --dry-run --once
py publishers/digitraffic_road_weather/digitraffic_road_weather_publisher.py --once
```

Default publisher interval is 300 seconds.