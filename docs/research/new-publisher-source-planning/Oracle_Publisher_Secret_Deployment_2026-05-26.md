# Oracle Publisher Secret Deployment

This is the acceptable production pattern for API keys used by live publishers on the Oracle host.

## Principle

Publisher code must stay configurable and secret-free. The repository may contain variable names, `.env.example` placeholders, Docker Compose interpolation, and systemd instructions, but not raw provider keys.

The live Oracle host should inject keys through one of these host-local mechanisms:

- systemd `EnvironmentFile=` with mode `0600`, owned by `root`;
- service-specific root-owned key files referenced by `*_API_KEY_FILE` environment variables;
- Docker Compose `.env` on the host, also mode `0600`, if the publisher is run via Compose.

## Current Key-Backed Publishers

| Publisher | Required? | Variable |
| --- | --- | --- |
| USGS Water | Optional, improves rate limits | `USGS_API_KEY` |
| USGS NIMS | Optional, improves rate limits | `USGS_API_KEY` |
| Met Office Land Observations | Required | `MET_OFFICE_LAND_OBSERVATIONS_API_KEY` |

The Oracle deploy/bootstrap script also expects `OSH_PASS` from the caller's environment or a host-local environment file. Server credentials should follow the same rule as provider API keys: never commit the raw value.

Met Office also supports `MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE`, which should point at a host-local file containing the raw key or an assignment line.

## systemd Pattern

Create a shared environment file on Oracle:

```bash
sudo install -d -m 700 -o root -g root /etc/os4csapi
sudo install -m 600 -o root -g root /dev/null /etc/os4csapi/publisher-secrets.env
sudoedit /etc/os4csapi/publisher-secrets.env
```

Example contents, with placeholders only:

```text
USGS_API_KEY=<usgs-key-if-used>
MET_OFFICE_LAND_OBSERVATIONS_API_KEY=<met-office-land-observations-key>
OSH_PASS=<osh-admin-password>
```

Then add a drop-in to each service that needs the keys:

```bash
sudo systemctl edit met-office-datahub-publisher-go
```

Drop-in contents:

```ini
[Service]
EnvironmentFile=/etc/os4csapi/publisher-secrets.env
```

Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart met-office-datahub-publisher-go
sudo journalctl -u met-office-datahub-publisher-go -n 80 --no-pager
```

For USGS Water and USGS NIMS, use the same `EnvironmentFile=` drop-in on `usgs-water-publisher-go` and `usgs-nims-publisher-go` when the API key is available.

## Secret File Pattern

For a single-service Met Office secret file:

```bash
sudo install -d -m 700 -o root -g root /etc/os4csapi/secrets
sudo install -m 600 -o root -g root /dev/null /etc/os4csapi/secrets/met-office-land-observations.key
sudoedit /etc/os4csapi/secrets/met-office-land-observations.key
```

The file should contain only the key or this assignment:

```text
MET_OFFICE_LAND_OBSERVATIONS_API_KEY=<met-office-land-observations-key>
```

The service environment then uses:

```ini
[Service]
Environment=MET_OFFICE_LAND_OBSERVATIONS_API_KEY_FILE=/etc/os4csapi/secrets/met-office-land-observations.key
```

Standalone publisher runs may also point at a shared host-local env file:

```ini
[Service]
Environment=PUBLISHERS_ENV_FILE=/etc/os4csapi/publisher-secrets.env
```

## Docker Compose Pattern

When running `publishers/docker-compose.yml` on Oracle, store keys in the host-local `publishers/.env` file. That file is ignored by git and must not be copied into commits or support bundles.

```text
USGS_API_KEY=<usgs-key-if-used>
MET_OFFICE_LAND_OBSERVATIONS_API_KEY=<met-office-land-observations-key>
```

Met Office is an opt-in access-gated Compose service:

```bash
docker compose --profile access-gated up -d met-office-datahub
```