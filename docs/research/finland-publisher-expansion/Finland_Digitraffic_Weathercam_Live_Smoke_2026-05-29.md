# Finland Digitraffic Weathercam Live Smoke

Date: 2026-05-29

## Summary

Phase 2 Finland datasource is live on the OSH CSAPI server using Fintraffic Digitraffic weather camera latest-data and JPEG endpoints.

Resources created without `--clean`:

- Procedure: `urn:os4csapi:procedure:digitraffic-weathercam:v1`
- Root deployment: `urn:os4csapi:deployment:digitraffic-weathercam-demo:v1`
- Camera preset group deployment: `urn:os4csapi:deployment:digitraffic-weathercam-presets:v1`
- Six companion `digitrafficWeatherCamImage` datastreams attached to the existing Digitraffic road-weather station systems
- Six camera preset deployments linked to the existing road-weather station systems

The publisher uses each preset's measured time as `phenomenonTime` and publishes image-reference results with direct full-size JPEG and thumbnail URLs.

## Selected Cameras

| Road station | System ID | Camera station | Preset ID | Datastream ID | Match note |
| --- | --- | --- | --- | --- | --- |
| 1014 / vt25_Hanko | 05u0 | C01507 / vt25_Hanko | C0150701 | 078g2 | Co-located, 0.03 km |
| 1003 / st110_Vihti_Myllylampi | 05ug | C01506 / vt25_Myllylampi | C0150601 | 07902 | Co-located, 0.04 km |
| 2002 / vt8_Pyharanta_Ihode | 05v0 | C02551 / vt8_Laitila_Palttila | C0255101 | 079g2 | Nearest fresh VT8 camera, 10.88 km |
| 3036 / vt6_Lappeenranta_Karki | 05vg | C03572 / vt6_Lappeenranta_Lavola | C0357201 | 07a02 | Nearby VT6 camera, 1.02 km |
| 4010 / vt12_Hollola_Hameenkoski | 06002 | C04541 / kt54_Karkola_Jarvela | C0454101 | 07ag2 | Nearest fresh road camera, 13.82 km |
| 12091 / kt92_Inari_Naatamo | 060g2 | C14516 / kt92_Inari_Naatamo | C1451601 | 07b02 | Co-located, 0.0 km |

## Live Publish Result

One publisher cycle posted six observations successfully:

- Published: 6
- Skipped: 0
- Errors: 0

Latest public API verification through the Explorer proxy confirmed `mediaType=image/jpeg`, expected `camId`, and HTTP 200 for both `imageUrl` and `thumbUrl` for all six datastreams.

| Station / preset | Datastream ID | Latest phenomenon time | Image | Thumbnail |
| --- | --- | --- | --- | --- |
| 1014 / C0150701 | 078g2 | 2026-05-29T21:15:48Z | 200 | 200 |
| 1003 / C0150601 | 07902 | 2026-05-29T21:22:40Z | 200 | 200 |
| 2002 / C0255101 | 079g2 | 2026-05-29T21:22:56Z | 200 | 200 |
| 3036 / C0357201 | 07a02 | 2026-05-29T21:22:54Z | 200 | 200 |
| 4010 / C0454101 | 07ag2 | 2026-05-29T21:14:07Z | 200 | 200 |
| 12091 / C1451601 | 07b02 | 2026-05-29T21:20:55Z | 200 | 200 |

## Verification Commands

Validated:

- `py -m py_compile publishers/digitraffic_weathercam/bootstrap_digitraffic_weathercam.py publishers/digitraffic_weathercam/digitraffic_weathercam_publisher.py`
- `py publishers/digitraffic_weathercam/digitraffic_weathercam_publisher.py --dry-run --once`
- `py publishers/digitraffic_weathercam/bootstrap_digitraffic_weathercam.py --dry-run --force-sml`
- `py publishers/digitraffic_weathercam/bootstrap_digitraffic_weathercam.py --force-sml`
- `py publishers/digitraffic_weathercam/digitraffic_weathercam_publisher.py --once`
- Public proxy latest observation checks for datastreams `078g2`, `07902`, `079g2`, `07a02`, `07ag2`, and `07b02`

Explorer follow-up: no app code change was needed. The existing deployed-system card camera detection matches `Digitraffic Weather Camera Image`, and the existing `FIN Road Wx` source classifier already matches Digitraffic datastream names.