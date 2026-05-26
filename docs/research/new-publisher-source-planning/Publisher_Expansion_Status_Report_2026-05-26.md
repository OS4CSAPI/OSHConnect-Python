# Publisher Expansion Status Report

Date: 2026-05-26

## Summary

The first three new publisher sources are implemented, documented, pushed, and live-smoke tested against the OS4CSAPI OSH endpoint:

- Environment Agency Hydrology
- UK-AIR
- BGS SensorThings / UKGEOS Glasgow telemetry

The fourth candidate, Met Office Weather DataHub Land Observations, has been started as an access-gated implementation target. The source is valuable, but requires account/subscription credentials before a live publisher can be completed honestly.

## GitHub Issue Filed

Created OS4CSAPI-controlled issue:

- OS4CSAPI/OSHConnect-Python#7: `System SensorML PUT returns HTTP 500 for publisher system metadata updates`

The issue tracks the repeated live OSH `PUT /systems/{id}` SensorML HTTP 500 behavior seen during rich system metadata updates. This affects normal propagation of image/source/legal metadata, even though systems, datastreams, deployments, and observations publish successfully.

## Production Smoke Sweep

Production Explorer assets were checked after the BGS thumbnail deploy:

- Production JS: `/assets/index-C5SpiU1M.js`
- Production CSS: `/assets/index-D9hdi0bV.css`
- CSS response: HTTP 200, `text/css`
- BGS thumbnail fallback URL present in production JS

Production CSAPI deployment read-back confirmed these publisher groups:

| Publisher | Deployment ID | UID |
| --- | --- | --- |
| Environment Agency Hydrology | `05d0` | `urn:os4csapi:deployment:environment-agency-hydrology-demo:v1` |
| UK-AIR | `05g0` | `urn:os4csapi:deployment:uk-air-demo:v1` |
| BGS SensorThings | `05ig` | `urn:os4csapi:deployment:bgs-sensorthings-demo:v1` |

Live publisher smoke results:

| Publisher | Result |
| --- | --- |
| Environment Agency Hydrology | Connected 4/4 stations, published 5 observations, 0 errors |
| UK-AIR | Connected 3/3 stations, published 4 observations, 0 errors |
| BGS SensorThings | Source dry-run fetched 9/9 curated observations, 0 errors; live run connected 3/3 stations and began posting the same curated readings |

Browser production card verification:

- BGS `BGS GGA07 UKGEOS Deployment` card rendered the official UKGEOS borehole-dimensions SVG thumbnail.
- The image loaded with natural size `320x237`.
- BGS card retained `Groundwater Telemetry Site`, latest readings, source links, and legal/attribution links.

Map-click automation for EA and UK-AIR became unreliable in the shared narrow browser viewport, so the smoke record uses production deployment read-back plus live publisher publish-cycle validation for those two. Earlier completion reports already record their production card verification.

## Reusable Implementation Pattern

The new publisher standard is now clear:

1. Research source access, licensing, and API shape before implementation.
2. Curate a small demo-safe station/source set in a sidecar file.
3. Bootstrap minimal GeoJSON stubs first, then rich SensorML PUTs.
4. Use stable UIDs and idempotent bootstrap helpers.
5. Publish one observation per source-native latest reading.
6. Preserve source IDs, source URLs, observed property, unit, and timestamp in result metadata.
7. Add Explorer role/symbol/label/thumbnail polish when the source introduces a new domain category.
8. Document residual server/source quirks immediately in the completion report or a GitHub issue.

## Known Residuals

- Live OSH system SensorML PUT still returns HTTP 500 for affected station-system updates. Tracked in OS4CSAPI/OSHConnect-Python#7.
- Explorer representative thumbnail fallbacks remain necessary for demo-quality cards when live system SensorML metadata cannot be updated.
- Met Office Weather DataHub cannot be completed without subscription credentials, even though the free plan allows limited daily call volume.

## Publisher #4 Start

Met Office Weather DataHub Land Observations is the fourth source from the original candidate set.

Research confirmed:

- Land Observations covers roughly 150 UK station locations.
- The API provides hourly JSON observations for the past 48 hours.
- The product currently advertises 9 parameters.
- The documented API flow is nearest-location lookup, then observation retrieval by geohash.
- Nearest-location lookup results should be cached.
- A free plan exists up to 360 calls per day, but registration/subscription/API credentials are required.

Created starter package:

- `publishers/met_office_datahub/README.md`
- `publishers/met_office_datahub/__init__.py`

Recommended next implementation step after credentials are available:

1. Verify the exact subscribed API base URL and authentication header.
2. Probe `GET /observation-land/1/nearest` for 3 curated demo locations.
3. Cache geohash/location metadata in a sidecar file.
4. Create bootstrap and runtime publisher using the `usgs_water` station-network model.