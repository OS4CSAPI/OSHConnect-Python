# Explorer New Source Thumbnail Research - 2026-05-26

## Scope

This note records the representative thumbnail choices for the new publisher expansion sources shown in the CSAPI Explorer deployed-system card.

The thumbnails are fallback visuals used when live OSH system SensorML metadata does not expose usable image links. They are representative of the source class, not station-specific unless noted.

## Environment Agency Hydrology

- Explorer image: `https://upload.wikimedia.org/wikipedia/commons/f/f0/Environment_Agency_Morton_River_Gauge_Station_-_geograph.org.uk_-_283345.jpg`
- Source page: Wikimedia Commons, `Environment Agency Morton River Gauge Station - geograph.org.uk - 283345.jpg`
- Author: Brian Green / Geograph
- License: CC BY-SA 2.0
- Rationale: Shows an Environment Agency river gauge station, matching the hydrology station/gauge publisher role.

## UK-AIR

Roadside/kerbside fallback:

- Explorer image: `https://upload.wikimedia.org/wikipedia/commons/0/0e/Air_Quality_Monitoring_Station_-_geograph.org.uk_-_2573031.jpg`
- Source page: Wikimedia Commons, `Air Quality Monitoring Station - geograph.org.uk - 2573031.jpg`
- Author: Jonathan Thacker / Geograph
- License: CC BY-SA 2.0
- Rationale: Shows a UK air-quality monitoring station appropriate for roadside/kerbside contexts such as Camden.

Background fallback:

- Explorer image: `https://upload.wikimedia.org/wikipedia/commons/7/75/Air-quality_monitoring_station%2C_Dundonald_-_geograph.org.uk_-_3201697.jpg`
- Source page: Wikimedia Commons, `Air-quality monitoring station, Dundonald - geograph.org.uk - 3201697.jpg`
- Author: Albert Bridge / Geograph
- License: CC BY-SA 2.0
- Rationale: Shows a representative UK air-quality monitoring station for non-roadside air-quality sites.

## BGS SensorThings / UKGEOS

- Explorer image: `https://www.ukgeos.ac.uk/assets/img/svgs/illustrations/borehole_dimmensions.svg`
- Source page: UKGEOS Glasgow Observatory / UKGEOS site assets
- License context: UKGEOS legal text says website data/material is made available under OGL where possible with acknowledgement `Contains NERC materials (c) NERC 2026`, but explicitly says photographic images are not subject to OGL and are identified separately to their copyright owners/license.
- Rationale: Use the official borehole-dimensions illustration as a representative non-photo visual for Glasgow Observatory borehole infrastructure. Avoid UKGEOS photographs unless a specific reusable image license is identified.

## Met Office Weather DataHub Land Observations

- Explorer image: `https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Charterhall_Met_Office_Weather_Station_-_Image_%5E1_-_geograph.org.uk_-_2754908.jpg/960px-Charterhall_Met_Office_Weather_Station_-_Image_%5E1_-_geograph.org.uk_-_2754908.jpg`
- Source page: Wikimedia Commons, `Charterhall Met Office Weather Station - Image #1 - geograph.org.uk - 2754908.jpg`
- Author: James T M Towill / Geograph
- License: CC BY-SA 2.0
- Rationale: Shows a Met Office weather station, matching the Weather DataHub Land Observations station-network model.

## Implementation Notes

The Explorer fallback constants live in `demo/src/composables/useDeployedSystemCard.ts` in the `ogc-csapi-explorer` repository. Symbol inference for the same sources lives in `demo/src/symbol-mapper.ts`.

These fallbacks should be replaced only if a better station-specific or source-official image with clear reuse terms is identified.