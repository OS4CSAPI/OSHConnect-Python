# Finland Digitraffic Road Weather Live Smoke

Date: 2026-05-29

## Summary

Phase 1 Finland datasource is live on the OSH CSAPI server using Fintraffic Digitraffic road-weather station latest-data endpoints.

Resources created without `--clean`:

- Procedure: `urn:os4csapi:procedure:digitraffic-road-weather:v1`
- Root deployment: `urn:os4csapi:deployment:digitraffic-road-weather-demo:v1`
- Station group deployment: `urn:os4csapi:deployment:digitraffic-road-weather-stations:v1`
- Six station systems and `roadWeatherObs` datastreams

Two station system creates returned the known SensorHub HTTP 500-after-create/SensorML-PUT warning path and were recovered by UID lookup. Live SensorML checks confirmed `Publish Interval=300s` for five station systems. Station `12091` remained observation-live after a targeted deployment/datastream restore, but SensorHub still returned HTTP 500 for SensorML PUT on that system.

## Live Publish Result

One publisher cycle posted six observations successfully:

| Station ID | System ID | Datastream ID | Latest phenomenon time | Air C | Road C |
| --- | --- | --- | --- | --- | --- |
| 1014 | 05u0 | 075g2 | 2026-05-29T20:57:24Z | 9.0 | 14.7 |
| 1003 | 05ug | 07602 | 2026-05-29T20:57:54Z | 10.7 | 16.1 |
| 2002 | 05v0 | 076g2 | 2026-05-29T20:56:54Z | 6.2 | 10.2 |
| 3036 | 05vg | 07702 | 2026-05-29T20:57:54Z | 8.5 | 9.5 |
| 4010 | 06002 | 077g2 | 2026-05-29T20:57:54Z | 8.5 | 12.6 |
| 12091 | 060g2 | 07802 | 2026-05-29T21:06:54Z | 7.9 | 8.7 |

Publisher output summary: initial all-station cycle `Published: 6`, `Skipped: 0`, `Errors: 0`; follow-up 12091 restore cycle `Published: 1`, `Skipped: 0`, `Errors: 0`.

## Verification Commands

Validated:

- `py -m py_compile publishers/digitraffic_road_weather/bootstrap_digitraffic_road_weather.py publishers/digitraffic_road_weather/digitraffic_road_weather_publisher.py`
- `py publishers/digitraffic_road_weather/digitraffic_road_weather_publisher.py --dry-run --once`
- `py publishers/digitraffic_road_weather/bootstrap_digitraffic_road_weather.py --dry-run --force-sml`
- `py publishers/digitraffic_road_weather/bootstrap_digitraffic_road_weather.py --force-sml`
- `py publishers/digitraffic_road_weather/digitraffic_road_weather_publisher.py --once`

Explorer follow-up: `demo/src/pages/MapViewPage.vue` now classifies Digitraffic/Fintraffic road-weather observation datastreams as `FIN Road Wx`.