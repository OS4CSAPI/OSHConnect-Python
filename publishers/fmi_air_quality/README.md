# FMI Air Quality Publisher

Publishes recent Finnish Meteorological Institute hourly air-quality observations from FMI Open Data WFS simple observations.

Source endpoint:

- `https://opendata.fmi.fi/wfs`
- Stored query: `fmi::observations::airquality::hourly::simple`

The first curated slice covers six Finnish background monitoring locations selected from live FMI coordinate responses. Each station has one `fmiAirQualityObs` datastream with NO2, O3, PM10, PM2.5, air-quality index, source parameters, and source URL.

## Bootstrap

```powershell
py publishers/fmi_air_quality/bootstrap_fmi_air_quality.py --dry-run --force-sml
py publishers/fmi_air_quality/bootstrap_fmi_air_quality.py --force-sml
```

## Publish

```powershell
py publishers/fmi_air_quality/fmi_air_quality_publisher.py --dry-run --once
py publishers/fmi_air_quality/fmi_air_quality_publisher.py --once
```

Default publisher interval is 3600 seconds.