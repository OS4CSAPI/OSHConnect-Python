# Finland FMI Weather And Air Quality Live Smoke

Date: 2026-05-29

## Summary

Phase 3 Finland datasource is live on the OSH CSAPI server using Finnish Meteorological Institute Open Data WFS simple stored queries.

Resources created without `--clean`:

- Weather procedure: `urn:os4csapi:procedure:fmi-weather:v1`
- Weather root deployment: `urn:os4csapi:deployment:fmi-weather-demo:v1`
- Weather station group deployment: `urn:os4csapi:deployment:fmi-weather-stations:v1`
- Six weather systems with one `fmiWeatherObs` datastream each
- Air-quality procedure: `urn:os4csapi:procedure:fmi-air-quality:v1`
- Air-quality root deployment: `urn:os4csapi:deployment:fmi-air-quality-demo:v1`
- Air-quality station group deployment: `urn:os4csapi:deployment:fmi-air-quality-stations:v1`
- Six air-quality systems with one `fmiAirQualityObs` datastream each

The FMI simple XML/GML responses provide coordinates, phenomenon time, parameter name, and parameter value. Publisher code preserves the source URL and full source parameter map in each observation result.

One air-quality system, `hyytiala-forest-background`, hit the known SensorHub HTTP 500-after-create/SensorML-PUT path. UID recovery succeeded, the datastream was created, and live observations are visible through the public API.

## Live Weather Publish Result

One publisher cycle posted six weather observations successfully:

- Published: 6
- Skipped: 0
- Errors: 0

| Station | System ID | Datastream ID | Latest phenomenon time | Air C | RH % |
| --- | --- | --- | --- | --- | --- |
| Helsinki Kaisaniemi | 06102 | 07bg2 | 2026-05-29T21:40:00Z | 10.5 | 69.0 |
| Turku Artukainen | 061g2 | 07c02 | 2026-05-29T21:40:00Z | 7.1 | 70.0 |
| Oulu Vihreasaari | 06202 | 07cg2 | 2026-05-29T21:40:00Z | 5.4 | 92.0 |
| Rovaniemi Apukka | 062g2 | 07d02 | 2026-05-29T21:40:00Z | 11.9 | 47.0 |
| Kuopio Maaninka | 06302 | 07dg2 | 2026-05-29T21:30:00Z | 5.8 | 93.0 |
| Vaasa Airport | 063g2 | 07e02 | 2026-05-29T21:40:00Z | 8.1 | 88.0 |

## Live Air-Quality Publish Result

One publisher cycle posted six air-quality observations successfully:

- Published: 6
- Skipped: 0
- Errors: 0

| Station | System ID | Datastream ID | Latest phenomenon time | NO2 | O3 | PM10 |
| --- | --- | --- | --- | --- | --- | --- |
| Uto Baltic Background | 06402 | 07eg2 | 2026-05-29T21:00:00Z | 2.2 | 66.1 | 2.4 |
| Hyytiala Forest Background | 064g2 | 07f02 | 2026-05-29T21:00:00Z | 0.5 | 67.2 | NaN |
| Oulanka Background | 06502 | 07fg2 | 2026-05-29T21:00:00Z | 0.7 | 67.0 | NaN |
| Sodankyla Arctic Research | 065g2 | 07g02 | 2026-05-29T21:00:00Z | NaN | 59.0 | NaN |
| Pallas Background | 06602 | 07gg2 | 2026-05-29T21:00:00Z | 0.2 | 72.9 | 2.8 |
| Virolahti Background | 066g2 | 07h02 | 2026-05-29T21:00:00Z | 2.9 | 35.3 | 4.9 |

FMI sometimes reports missing numeric values as `NaN`; SensorHub accepts these only as the string token `NaN`, not JSON null.

## Verification Commands

Validated:

- `py -m py_compile publishers/fmi_common.py publishers/fmi_weather/bootstrap_fmi_weather.py publishers/fmi_weather/fmi_weather_publisher.py publishers/fmi_air_quality/bootstrap_fmi_air_quality.py publishers/fmi_air_quality/fmi_air_quality_publisher.py`
- `py publishers/fmi_weather/fmi_weather_publisher.py --dry-run --once`
- `py publishers/fmi_air_quality/fmi_air_quality_publisher.py --dry-run --once`
- `py publishers/fmi_weather/bootstrap_fmi_weather.py --dry-run --force-sml`
- `py publishers/fmi_air_quality/bootstrap_fmi_air_quality.py --dry-run --force-sml`
- `py publishers/fmi_weather/bootstrap_fmi_weather.py --force-sml`
- `py publishers/fmi_air_quality/bootstrap_fmi_air_quality.py --force-sml`
- `py publishers/fmi_weather/fmi_weather_publisher.py --once`
- `py publishers/fmi_air_quality/fmi_air_quality_publisher.py --once`
- Public proxy latest observation checks for datastreams `07bg2`, `07c02`, `07cg2`, `07d02`, `07dg2`, `07e02`, `07eg2`, `07f02`, `07fg2`, `07g02`, `07gg2`, and `07h02`

Explorer follow-up: `demo/src/pages/MapViewPage.vue` now classifies FMI weather datastreams as `FMI Weather` and FMI air-quality datastreams as `FMI AQ`, preventing them from falling into generic Met Office or UK-AIR buckets.