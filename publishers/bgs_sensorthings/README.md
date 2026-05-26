# BGS SensorThings Publisher

Publishes a curated subset of British Geological Survey Sensor Data Service observations into a CSAPI/OSH server.

The source is the public BGS SensorThings API v1.1 endpoint at:

- https://sensors.bgs.ac.uk/FROST-Server/v1.1

## Initial Scope

The first pass uses three UKGEOS Glasgow downhole hydro loggers:

| Site | SensorThings Thing | Selected datastreams |
| --- | --- | --- |
| `gga01-03` | `195` | water temperature, conductivity, water level maOD |
| `gga05-03` | `197` | water temperature, conductivity, water level maOD |
| `gga07-03` | `200` | water temperature, conductivity, water level maOD |

Curated source records are restricted to BGS datastreams that reported unrestricted access and Open Government Licence / UKRI acknowledgement usage text during probing.

The card thumbnail uses the official UKGEOS borehole-dimensions illustration at `https://www.ukgeos.ac.uk/assets/img/svgs/illustrations/borehole_dimmensions.svg` from the Glasgow Observatory page as a representative visual. It is not a station-specific photograph. UKGEOS legal text says photographic images are not covered by OGL, so the publisher intentionally avoids UKGEOS photographs unless a specific image license is available.

## Bootstrap

```bash
py -m publishers.bgs_sensorthings.bootstrap_bgs_sensorthings --dry-run
py -m publishers.bgs_sensorthings.bootstrap_bgs_sensorthings --force-sml
```

Use `--clean`, `--clean-only`, and `--force-sml` with the same semantics as the other publisher bootstraps.

## Publish

```bash
py -m publishers.bgs_sensorthings.bgs_sensorthings_publisher --dry-run --once
py -m publishers.bgs_sensorthings.bgs_sensorthings_publisher --once
```

Options:

- `--interval <seconds>`: polling interval, default `900`.
- `--stations gga01-03,gga05-03`: restrict to selected curated site IDs or source Thing IDs.
- `--dry-run`: fetch and normalize source observations without posting.
- `--once`: run one cycle and exit.

## CSAPI Model

- Procedure: `urn:os4csapi:procedure:bgs-sensorthings:v1`
- Systems: one per curated BGS SensorThings Thing.
- Datastreams: one per selected BGS SensorThings Datastream.
- Deployments: one BGS SensorThings demo root, one UKGEOS Glasgow group, and one deployment per hydro logger.

Observation results preserve:

- curated Thing/site ID
- source SensorThings Thing ID
- source SensorThings Datastream ID
- observed property
- numeric value and unit
- source Observation ID
- source publish flag when present
- latest-observation source URL

## Source Notes

BGS Sensor Data Service exposes SensorThings collections including Things, Locations, Datastreams, ObservedProperties, Sensors, FeaturesOfInterest, Observations, and MultiDatastreams. The curated publisher deliberately avoids BGS event datastreams and records with restrictive access metadata.

License and attribution should follow the source `data_usage` text. The curated records used here state Open Government Licence availability with UKRI acknowledgement language: `Contains UKRI materials (c) UKRI [year]`.
