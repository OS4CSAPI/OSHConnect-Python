# Finland Source Endpoint Probe

Date: 2026-05-29

## Digitraffic Road Weather

Station metadata endpoint:

`https://tie.digitraffic.fi/api/weather/v1/stations`

Result: live GeoJSON `FeatureCollection` with 525 station features. Station geometry is Point coordinates in lon/lat order. Station properties include `id`, `name`, `collectionStatus`, `dataUpdatedTime`, and `state`.

Latest all-station data endpoint:

`https://tie.digitraffic.fi/api/weather/v1/stations/data`

Result: live JSON object with top-level `dataUpdatedTime` and `stations[]`. Each station has `id`, `dataUpdatedTime`, and `sensorValues[]` containing sensor `id`, `stationId`, `name`, `shortName`, `measuredTime`, `unit`, and `value`.

Station-specific latest data endpoint:

`https://tie.digitraffic.fi/api/weather/v1/stations/{id}/data`

Result: live JSON object for one station with the same `sensorValues[]` structure.

Verified fresh sample times during probe: 2026-05-29T20:47Z to 2026-05-29T20:51Z.

Selected Phase 1 curated stations:

| ID | Source name | Region |
| --- | --- | --- |
| 1014 | vt25_Hanko | Uusimaa south coast |
| 1003 | st110_Vihti_Myllylampi | Helsinki western approach |
| 2002 | vt8_Pyharanta_Ihode | Southwest Finland |
| 3036 | vt6_Lappeenranta_Karki | Southeast Finland |
| 4010 | vt12_Hollola_Hameenkoski | Central southern Finland |
| 12091 | kt92_Inari_Naatamo | Lapland / Inari |

Implementation choice: use station-specific latest endpoints for the runtime publisher to keep each fetch bounded and easy to diagnose. Preserve the full source `sensorValues[]` payload as compact JSON in the CSAPI observation result while also lifting common operational fields such as air temperature, road-surface temperature, wind speed, wind direction, precipitation, road condition, and warning code.

## Digitraffic Marine AIS

Latest vessel locations endpoint:

`https://meri.digitraffic.fi/api/ais/v1/locations`

Result: live gzip-compressed GeoJSON `FeatureCollection`. Global sample during probe returned about 18,442 AIS location features with source `dataUpdatedTime` around 2026-05-30T06:46Z to 2026-05-30T07:02Z. Feature geometry is Point coordinates in lon/lat order. Feature properties include MMSI, speed over ground, course over ground, navigation status, heading, ROT, position accuracy flags, and source timestamps.

Vessel metadata endpoint:

`https://meri.digitraffic.fi/api/ais/v1/vessels`

Result: live gzip-compressed JSON array keyed by MMSI with optional vessel name, callsign, IMO, destination, draught, ship type, reference points, and metadata timestamps.

Selected Phase 4 demo window:

| Field | Value |
| --- | --- |
| Latitude min/max | 59.0 / 60.8 |
| Longitude min/max | 22.5 / 28.7 |
| Region | Gulf of Finland / Helsinki approaches |
| Probe count | about 1,198 live vessels in bbox |
| Publish cap | 60 vessels per cycle |

Implementation choice: publish one bounded feed-adapter system and one `digitrafficMarineAisPosition` datastream. Runtime observations lift MMSI, vessel metadata, lat/lon, SOG, COG, heading, navigation status, ship type, destination, source update time, and compact source payload JSON. AIS sentinel values are normalized before publishing: SOG >= 102.2, COG >= 360, and heading >= 511 become `"NaN"`.

Live smoke on 2026-05-30: bootstrapped procedure `04ig`, system `06702`, datastream `07hg2`, root grouping deployment `06i02`, and feed deployment `06ig2` on the public SensorHub. The feed deployment is retained as the clickable metadata entry point for the AIS feed/query window; Explorer defers its display until the later map layers join the initial resource load so it does not appear as an out-of-band symbol before observations and other features. The first retained full cycle used millisecond offsets from source snapshot time so the server stores all vessels from the same Digitraffic snapshot; public proxy verification returned 62 AIS observations, including the 60-record 2026-05-30T07:02:25Z cycle.