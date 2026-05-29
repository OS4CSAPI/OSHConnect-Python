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