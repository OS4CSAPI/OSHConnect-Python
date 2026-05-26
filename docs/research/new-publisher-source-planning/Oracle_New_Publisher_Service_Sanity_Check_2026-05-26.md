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

The Oracle service inventory shows `met-office-datahub-publisher.service` installed and running as the persistent service for the newest access-gated publisher.

No persistent systemd units were discovered for Environment Agency Hydrology, UK-AIR, or BGS SensorThings during this check. Those publishers have been bootstrapped and one-shot published successfully, and their live CSAPI root deployments remain present, but they are not yet represented by dedicated Oracle scheduler/service units in the same way as Met Office.

## Public CORS Check

Production-origin CORS check from `https://ogc-csapi-explorer.pages.dev` returned a single public origin header:

```text
Access-Control-Allow-Origin: *
```

This confirms the live Caddy fix is still in place and avoids the previous duplicate-origin browser failure.

## Controlled-Repo Issue Draft

The local environment did not provide a GitHub issue tool, `gh` CLI, or GitHub API token at the time of this check. If an issue is filed, file it only in a controlled OS4CSAPI repository, preferably `OS4CSAPI/OSHConnect-Python`.

Suggested title:

```text
Install persistent Oracle services for EA Hydrology, UK-AIR, and BGS publishers
```

Suggested body:

```markdown
## Summary

Environment Agency Hydrology, UK-AIR, and BGS SensorThings were implemented, bootstrapped, one-shot published, and verified in production Explorer, but the Oracle host currently only has Met Office installed as a persistent new-publisher service.

## Current State

- `met-office-datahub-publisher.service` is installed and active.
- No dedicated systemd units were discovered for:
  - Environment Agency Hydrology
  - UK-AIR
  - BGS SensorThings / UKGEOS
- Live CSAPI root deployments are present:
  - `urn:os4csapi:deployment:environment-agency-hydrology-demo:v1` -> `05d0`
  - `urn:os4csapi:deployment:uk-air-demo:v1` -> `05g0`
  - `urn:os4csapi:deployment:bgs-sensorthings-demo:v1` -> `05ig`
  - `urn:os4csapi:deployment:met-office-datahub-demo:v1` -> `05l0`

## Proposed Work

Add host-local systemd service/timer units or equivalent scheduler entries for the three one-shot-verified publishers, using the existing Oracle service pattern and without committing any secrets.

## Acceptance Criteria

- Environment Agency Hydrology publishes on a bounded recurring cadence.
- UK-AIR publishes on a bounded recurring cadence.
- BGS SensorThings publishes on a bounded recurring cadence appropriate for its source update frequency.
- Units use host-local environment/secret files only.
- `systemctl status` and journal checks are documented.
- Production Explorer still loads the public endpoint without CORS-blocked OSH requests.
```