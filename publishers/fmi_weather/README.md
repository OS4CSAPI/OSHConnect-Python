# FMI Weather Publisher

Publishes recent Finnish Meteorological Institute weather observations from FMI Open Data WFS simple observations.

Source endpoint:

- `https://opendata.fmi.fi/wfs`
- Stored query: `fmi::observations::weather::simple`

The first curated slice covers Helsinki, Turku, Oulu, Rovaniemi, Kuopio, and Vaasa. Each station has one `fmiWeatherObs` datastream with temperature, humidity, wind, precipitation, pressure, source parameters, and source URL.

## Bootstrap

```powershell
py publishers/fmi_weather/bootstrap_fmi_weather.py --dry-run --force-sml
py publishers/fmi_weather/bootstrap_fmi_weather.py --force-sml
```

## Publish

```powershell
py publishers/fmi_weather/fmi_weather_publisher.py --dry-run --once
py publishers/fmi_weather/fmi_weather_publisher.py --once
```

Default publisher interval is 600 seconds.