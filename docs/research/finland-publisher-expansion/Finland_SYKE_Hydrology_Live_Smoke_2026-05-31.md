# Finland SYKE Hydrology Live Smoke 2026-05-31

## Scope

Implemented and deployed the Phase 6 SYKE / vesi.fi hydrology publisher for Finland.

Source endpoints:

```text
https://rajapinnat.ymparisto.fi/api/Hydrologiarajapinta/1.0/odata/Paikka
https://rajapinnat.ymparisto.fi/api/Hydrologiarajapinta/1.0/odata/Vedenkorkeus
https://rajapinnat.ymparisto.fi/api/Hydrologiarajapinta/1.0/odata/Virtaama
```

No API key is required.

## Curated Stations

| Station | Name | Measures |
| --- | --- | --- |
| `0400520` | Jongunjoki, Viitakoski | water level, discharge |
| `0406010` | Sonkajärvi | water level, discharge |
| `0407410` | Keyritty | water level, discharge |
| `1403900` | Konnevesi - luusua | discharge |

SYKE uses measure-specific `Paikka_Id` values. The publisher groups those readings into station systems by shared physical station notation.

## Local Verification

Command:

```text
py -3 -m publishers.syke_hydrology.syke_hydrology_publisher --dry-run --once
```

Result:

```text
0400520/sykeWaterLevel: water_level_cm=195.0 cm
0400520/sykeDischarge: discharge_m3s=23.0 m3/s
0406010/sykeWaterLevel: water_level_cm=244.0 cm
0406010/sykeDischarge: discharge_m3s=28.0 m3/s
0407410/sykeWaterLevel: water_level_cm=61.0 cm
0407410/sykeDischarge: discharge_m3s=7.73 m3/s
1403900/sykeDischarge: discharge_m3s=37.5 m3/s
Seen: 7
Errors: 0
```

## Live Bootstrap

Bootstrap command on Oracle host:

```text
python3 -m publishers.syke_hydrology.bootstrap_syke_hydrology --force-sml
```

Created resources:

| Resource | ID |
| --- | --- |
| Procedure `urn:os4csapi:procedure:syke-hydrology:v1` | `04jg` |
| System `urn:os4csapi:system:syke-hydrology:0400520:v1` | `06802` |
| System `urn:os4csapi:system:syke-hydrology:0406010:v1` | `068g2` |
| System `urn:os4csapi:system:syke-hydrology:0407410:v1` | `06902` |
| System `urn:os4csapi:system:syke-hydrology:1403900:v1` | `069g2` |
| Datastream `0400520/sykeWaterLevel` | `07ig2` |
| Datastream `0400520/sykeDischarge` | `07j02` |
| Datastream `0406010/sykeWaterLevel` | `07jg2` |
| Datastream `0406010/sykeDischarge` | `07k02` |
| Datastream `0407410/sykeWaterLevel` | `07kg2` |
| Datastream `0407410/sykeDischarge` | `07l02` |
| Datastream `1403900/sykeDischarge` | `07lg2` |
| Root deployment `urn:os4csapi:deployment:syke-hydrology-demo:v1` | `06k02` |
| Group deployment `urn:os4csapi:deployment:syke-hydrology-stations:v1` | `06kg2` |

SensorHub returned HTTP 500 during system create / SensorML PUT for each station, matching the known SensorHub persistence quirk. The bootstrap recovered the persisted system IDs and datastreams were created successfully.

## Live Publish

One manual publish cycle on the Oracle host succeeded:

```text
Ready: 4/4 stations connected
0400520/sykeWaterLevel: OK  water_level_cm=195.0 cm
0400520/sykeDischarge: OK  discharge_m3s=23.0 m3/s
0406010/sykeWaterLevel: OK  water_level_cm=244.0 cm
0406010/sykeDischarge: OK  discharge_m3s=28.0 m3/s
0407410/sykeWaterLevel: OK  water_level_cm=61.0 cm
0407410/sykeDischarge: OK  discharge_m3s=7.73 m3/s
1403900/sykeDischarge: OK  discharge_m3s=37.5 m3/s
Published: 7
Errors: 0
```

Persistent service installed and started:

```text
syke-hydrology-publisher.service
```

Service log verification:

```text
Active: active (running)
Ready: 4/4 stations connected
Cycle #1 published all 7 readings with 0 errors
```

## Public Proxy Verification

Verified through:

```text
https://ogc-csapi-explorer.pages.dev/api/osh
```

Representative observation:

| Field | Value |
| --- | --- |
| System ID | `06802` |
| System name | `SYKE Hydrology Jongunjoki, Viitakoski` |
| Datastream ID | `07ig2` |
| Datastream output | `sykeWaterLevel` |
| Station | `0400520` |
| Phenomenon time | `2026-05-31T00:00:00Z` |
| Result time | `2026-05-31T08:39:07Z` |
| Water level | `195 cm` |
| SYKE flag | `108` |

## Notes

The publisher uses current same-day Finnish hydrology readings and a 15-minute cadence. Station SensorML includes a real representative water-level gauge photograph plus source links to SYKE / vesi.fi and each exact OData latest-reading query.
