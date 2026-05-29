# Digitraffic Weathercam Publisher

Publishes image-reference observations for a curated set of Fintraffic Digitraffic road-weather camera presets associated with the Phase 1 Finland road-weather stations.

Source endpoints:

- Camera metadata: `https://tie.digitraffic.fi/api/weathercam/v1/stations`
- Station-specific latest preset metadata: `https://tie.digitraffic.fi/api/weathercam/v1/stations/{id}/data`
- Latest preset image: `https://weathercam.digitraffic.fi/{presetId}.jpg`
- Latest preset thumbnail: `https://weathercam.digitraffic.fi/{presetId}.jpg?thumbnail=true`

The publisher attaches one companion `digitrafficWeatherCamImage` datastream to each existing Digitraffic road-weather station system. This lets deployed-system cards render the camera imagery for the same station card.

## Bootstrap

```powershell
py publishers/digitraffic_weathercam/bootstrap_digitraffic_weathercam.py --dry-run
py publishers/digitraffic_weathercam/bootstrap_digitraffic_weathercam.py --force-sml
```

## Publish

```powershell
py publishers/digitraffic_weathercam/digitraffic_weathercam_publisher.py --dry-run --once
py publishers/digitraffic_weathercam/digitraffic_weathercam_publisher.py --once
```

Default publisher interval is 300 seconds.