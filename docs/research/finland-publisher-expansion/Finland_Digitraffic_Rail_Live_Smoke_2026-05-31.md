# Finland Digitraffic Rail Live Smoke 2026-05-31

## Scope

Implemented and deployed the Phase 5 Digitraffic Rail live-trains publisher for Finland.

Source endpoints:

```text
https://rata.digitraffic.fi/api/v1/train-locations/latest/
https://rata.digitraffic.fi/api/v1/live-trains
```

No API key is required.

## Local Verification

Command:

```text
py -3 -m publishers.digitraffic_rail_trains.digitraffic_rail_trains_publisher --dry-run --once
```

Result:

```text
Received 80 train positions from Digitraffic Rail
Cycle complete: 80 published, 0 skipped, 0 errors
```

## Live Bootstrap

Bootstrap command on Oracle host:

```text
python3 -m publishers.digitraffic_rail_trains.bootstrap_digitraffic_rail_trains --force-sml
```

Created resources:

| Resource | ID |
| --- | --- |
| Procedure `urn:os4csapi:procedure:digitraffic-rail-trains:v1` | `04j0` |
| System `urn:os4csapi:system:digitraffic-rail-trains-feed:v1` | `067g2` |
| Datastream `digitrafficRailTrainPosition` | `07i02` |
| Root deployment `urn:os4csapi:deployment:digitraffic-rail-trains-demo:v1` | `06j02` |
| Feed deployment `urn:os4csapi:deployment:digitraffic-rail-trains-feed:v1` | `06jg2` |

SensorHub returned HTTP 500 during the system SensorML PUT, matching the known SensorHub quirk where resource persistence can still succeed. The system and datastream were verified afterward through the public proxy.

## Live Publish

One manual publish cycle on the Oracle host succeeded:

```text
Connected: sys=067g2 ds=07i02
Received 80 train positions from Digitraffic Rail
Cycle complete: 80 published, 0 skipped, 0 errors
```

Persistent service installed and started:

```text
digitraffic-rail-trains-publisher.service
```

Service log verification:

```text
Active: active (running)
Connected: sys=067g2 ds=07i02
Received 80 train positions from Digitraffic Rail
Cycle complete: 80 published, 0 skipped, 0 errors
```

## Public Proxy Verification

Verified through:

```text
https://ogc-csapi-explorer.pages.dev/api/osh
```

Representative latest observation response:

| Field | Value |
| --- | --- |
| System ID | `067g2` |
| System name | `Digitraffic Rail Live Trains Feed - Finland` |
| Datastream ID | `07i02` |
| Datastream output | `digitrafficRailTrainPosition` |
| Sample train | `11190` |
| Sample category | `Locomotive` |
| Sample operator | `vr` |
| Sample timestamp | `2026-05-31T08:12:22Z` |

## Notes

The publisher uses a Finland-wide bounding box and caps each cycle at 80 train positions to avoid overwhelming the Explorer map while keeping the source explicitly Finnish.
