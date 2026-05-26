# BGS SensorThings Publisher Completion Report

Date: 2026-05-26

## Summary

Implemented the third new publisher: BGS SensorThings telemetry. This publisher uses the public British Geological Survey Sensor Data Service OGC SensorThings API and publishes a curated UKGEOS Glasgow groundwater/geothermal telemetry subset into OSH/CSAPI.

The chosen branch was BGS SensorThings telemetry, not BGS earthquake GeoRSS, because it adds a standards-rich SensorThings-to-CSAPI interoperability story and avoids overlapping the existing USGS earthquake publisher.

## Implemented Files

- `publishers/bgs_sensorthings/stations.json`
- `publishers/bgs_sensorthings/bootstrap_bgs_sensorthings.py`
- `publishers/bgs_sensorthings/bgs_sensorthings_publisher.py`
- `publishers/bgs_sensorthings/README.md`
- `docs/research/new-publisher-source-planning/BGS_SensorThings_Publisher_Implementation_Plan_2026-05-26.md`
- `publishers/README.md` updated with fleet entry and bootstrap command

Explorer production polish was implemented separately in the Explorer repository:

- BGS role inference: `Groundwater Telemetry Site`
- BGS symbol rule: fixed Sensor Emplaced style
- latest-reading label fix for `Water Level maOD`
- representative thumbnail fallback using the official UKGEOS borehole-dimensions illustration

## Source

- BGS Sensor Data Service: https://sensors.bgs.ac.uk/
- SensorThings API root: https://sensors.bgs.ac.uk/FROST-Server/v1.1
- API docs: https://sensors.bgs.ac.uk/api.html
- Interactive docs: https://sensors-docs.bgs.ac.uk/

Curated datastreams were selected from BGS records reporting unrestricted access and Open Government Licence / UKRI acknowledgement data usage language.

## Curated Systems

| Curated site | SensorThings Thing ID | Name | Coordinates |
| --- | --- | --- | --- |
| `gga01-03` | `195` | Downhole hydro logger GGA01 | -4.200163, 55.839415 |
| `gga05-03` | `197` | Downhole hydro logger GGA05 | -4.199619, 55.837690 |
| `gga07-03` | `200` | Downhole hydro logger GGA07 | -4.201172, 55.838337 |

Each system has three datastreams:

- Water Temperature
- Conductivity
- Water Level maOD

## Live Bootstrap

Command run:

```bash
py -m publishers.bgs_sensorthings.bootstrap_bgs_sensorthings --force-sml
```

Created live resources:

- Procedure: `urn:os4csapi:procedure:bgs-sensorthings:v1`, server ID `04e0`
- Deployments:
  - root `05ig`
  - group `05j0`
  - `gga01-03` deployment `05jg`
  - `gga05-03` deployment `05k0`
  - `gga07-03` deployment `05kg`
- Systems:
  - `gga01-03` system `05n0`
  - `gga05-03` system `05ng`
  - `gga07-03` system `05o0`
- Datastreams:
  - `gga01-03`: `05mg`, `05n0`, `05ng`
  - `gga05-03`: `05o0`, `05og`, `05p0`
  - `gga07-03`: `05pg`, `05q0`, `05qg`

## Server Compatibility Notes

The live OSH server repeated a known behavior seen in earlier publisher work: some system POST requests returned HTTP 500 after the resource had actually been created. The bootstrap recovered those system IDs by UID and continued successfully.

SensorML PUT for the recovered BGS systems returned HTTP 500. The GeoJSON stubs, datastreams, deployments, and observations were still created successfully, and Explorer was able to render BGS deployed-system cards using the available deployment/system/datastream metadata. Rich SensorML system metadata should be treated as a follow-up compatibility item rather than a blocker for the live demo path.

## Live Publish

Command run:

```bash
py -m publishers.bgs_sensorthings.bgs_sensorthings_publisher --once
```

The first live cycle published eight readings before output ended; `gga07-03` was rerun explicitly to confirm the final station end-to-end:

```bash
py -m publishers.bgs_sensorthings.bgs_sensorthings_publisher --once --stations gga07-03
```

The `gga07-03` rerun published 3 observations, 0 skipped, 0 errors.

## CSAPI Read-Back

Latest observation read-back succeeded for all nine BGS datastreams.

Representative values:

| Site | Datastream | Value | Phenomenon time |
| --- | --- | ---: | --- |
| `gga01-03` | Water Temperature | 12.4466 C | 2026-04-13T00:00:00Z |
| `gga01-03` | Conductivity | 1689.2874 uS/cm | 2026-04-13T00:00:00Z |
| `gga01-03` | Water Level maOD | 9.5584026158 m | 2026-04-13T00:00:00Z |
| `gga05-03` | Water Temperature | 11.5819 C | 2026-04-13T00:00:00Z |
| `gga05-03` | Conductivity | 1693.9048 uS/cm | 2026-04-13T00:00:00Z |
| `gga05-03` | Water Level maOD | 10.0791145586 m | 2026-04-13T00:00:00Z |
| `gga07-03` | Water Temperature | 11.454 C | 2026-04-13T00:00:00Z |
| `gga07-03` | Conductivity | 1669.0203 uS/cm | 2026-04-13T00:00:00Z |
| `gga07-03` | Water Level maOD | 9.5070321891 m | 2026-04-13T00:00:00Z |

## Explorer Verification

Production Explorer found the BGS deployments after filtering by `BGS` and narrowing visible layers to deployments/systems.

Verified card after Explorer polish deployment:

- `BGS GGA07 UKGEOS Deployment`
- system subtitle: `BGS GGA07 Downhole Hydro Logger`
- outputs: Conductivity, Water Level maOD, Water Temperature
- role badge: `GROUNDWATER TELEMETRY SITE`
- representative thumbnail: official UKGEOS borehole-dimensions illustration
- latest readings: Conductivity, Water Level maOD, Water Temperature
- source links: BGS SensorThings Thing, BGS SensorThings API Docs, Open Government Licence v3.0

Explorer polish was pushed and deployed to improve the card from generic `Deployed System` to `Groundwater Telemetry Site` and to keep `Water Level maOD` as the latest-reading label. Production bundle checks confirmed the new JS contains the BGS role/symbol/label updates, and the browser card check confirmed the visible production card text.

## Thumbnail Research And Licensing

The BGS/UKGEOS Glasgow Observatory page includes relevant visual assets, including photographs and official illustrations. UKGEOS legal text states that data/material on the website is made available under the Open Government Licence where possible with acknowledgement `Contains NERC materials (c) NERC 2026`, but also explicitly says photographic images are not subject to OGL and are identified separately to their copyright owners/license.

Because no station-specific licensed photograph was identified during this pass, the BGS card uses the official UKGEOS borehole-dimensions illustration as a representative, non-photographic visual for Glasgow Observatory borehole infrastructure. The implementation labels it as representative, not station-specific.

## Remaining Follow-Up

- Investigate the live OSH SensorML PUT 500 for BGS systems if richer system metadata becomes necessary.
- Consider replacing the representative illustration only if a station-specific photograph with clear reuse terms is identified.
