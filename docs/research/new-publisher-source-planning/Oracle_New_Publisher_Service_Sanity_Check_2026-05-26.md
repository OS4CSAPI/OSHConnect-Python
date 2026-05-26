# Oracle New Publisher Service Sanity Check - 2026-05-26

## Summary

After the production Explorer CORS and new-source visibility fixes, the Oracle host and public CSAPI endpoint were checked for the four newly added publisher sources:

- Environment Agency Hydrology
- UK-AIR
- BGS SensorThings / UKGEOS
- Met Office Weather DataHub Land Observations

## Live Endpoint Read-Back

Public endpoint checked:

```text
https://129-80-248-53.sslip.io/sensorhub/api
```

Root deployment read-back succeeded for all four new publisher demos:

| Source | Deployment UID | Server ID | Result |
| --- | --- | --- | --- |
| Environment Agency Hydrology | `urn:os4csapi:deployment:environment-agency-hydrology-demo:v1` | `05d0` | present |
| UK-AIR | `urn:os4csapi:deployment:uk-air-demo:v1` | `05g0` | present |
| BGS SensorThings | `urn:os4csapi:deployment:bgs-sensorthings-demo:v1` | `05ig` | present |
| Met Office DataHub | `urn:os4csapi:deployment:met-office-datahub-demo:v1` | `05l0` | present |

## Oracle Service State

Core public path services were active:

```text
caddy.service: active
sensorhub.service: active
met-office-datahub-publisher.service: active
```

The initial check found only `met-office-datahub-publisher.service` installed as a persistent service for the newest publisher set. Environment Agency Hydrology, UK-AIR, and BGS SensorThings were already bootstrapped and one-shot published, but they were not yet represented by dedicated Oracle systemd units.

That operational gap was closed on 2026-05-26. A durable full-repo working tree was installed at:

```text
/home/ubuntu/oshconnect-python-publishers
```

It was seeded from controlled repo commit:

```text
13de4a1d8821ebb09cda35531afe3935eb538a55
```

The following persistent services were installed, enabled, and started:

| Service | Module | Interval | First managed cycle |
| --- | --- | ---: | --- |
| `environment-agency-hydrology-publisher.service` | `publishers.environment_agency_hydrology.environment_agency_hydrology_publisher` | 900s | 5 published, 0 errors |
| `uk-air-publisher.service` | `publishers.uk_air.uk_air_publisher` | 3600s | 4 published, 0 errors |
| `bgs-sensorthings-publisher.service` | `publishers.bgs_sensorthings.bgs_sensorthings_publisher` | 21600s | 9 published, 0 errors |

All three services use the existing host-local environment file pattern:

```ini
EnvironmentFile=/etc/os4csapi/publisher-secrets.env
```

No raw credentials are stored in git.

Post-install status check showed all three new services as `enabled` and `active`. Journals showed each service connected to all curated systems, posted its first managed cycle, and entered its sleep interval before the next cycle.

## Public CORS Check

Production-origin CORS check from `https://ogc-csapi-explorer.pages.dev` returned a single public origin header:

```text
Access-Control-Allow-Origin: *
```

This confirms the live Caddy fix is still in place and avoids the previous duplicate-origin browser failure.

## Latest Observation Spot Check

Representative latest-observation read-back after service installation:

| Source | Datastream ID | Result |
| --- | --- | --- |
| Environment Agency Hydrology river level | `05i0` | latest observation returned |
| UK-AIR NO2 | `05kg` | latest observation returned |
| BGS water temperature | `05mg` | latest observation returned |
| Met Office air temperature | `05r0` | latest observation returned |

The BGS source currently reports older observations from 2026-04-13, which matches the upstream latest value observed during the publisher completion work. This is stale source data, not a service failure.