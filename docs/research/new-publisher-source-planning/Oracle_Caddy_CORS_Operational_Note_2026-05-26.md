# Oracle Caddy CORS Operational Note - 2026-05-26

## Summary

The public Oracle endpoint at `https://129-80-248-53.sslip.io/sensorhub/api` is fronted by Caddy and proxies to SensorHub on `localhost:8181`.

Production Explorer loads OSH resources from Cloudflare Pages at `https://ogc-csapi-explorer.pages.dev`. Browser requests failed when both Caddy and SensorHub emitted CORS response headers, producing a duplicate `Access-Control-Allow-Origin` value such as:

```text
*, https://ogc-csapi-explorer.pages.dev
```

Browsers reject that response even though command-line clients can still read the endpoint.

## Live Fix

The Caddy reverse proxy for SensorHub should strip upstream CORS headers before Caddy emits the public CORS policy.

Relevant `/etc/caddy/Caddyfile` reverse proxy block:

```caddy
reverse_proxy localhost:8181 {
    header_down -Access-Control-Allow-Origin
    header_down -Access-Control-Allow-Credentials
    header_up Authorization "Basic <sensorhub-basic-auth>"
}
```

Do not commit the raw `Authorization` value to git. Keep it only in host-local server configuration or a host-local secret mechanism.

## Validation

After changing Caddy, validate the config and reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

Then verify the public endpoint from the production Explorer origin:

```powershell
$resp = Invoke-WebRequest -Method Head `
  -Uri 'https://129-80-248-53.sslip.io/sensorhub/api' `
  -Headers @{ Origin = 'https://ogc-csapi-explorer.pages.dev' }

$resp.Headers.GetEnumerator() |
  Where-Object { $_.Key -match 'Access-Control|Vary' } |
  ForEach-Object { "$($_.Key): $($_.Value -join ', ')" }
```

Expected result includes exactly one `Access-Control-Allow-Origin` value:

```text
Access-Control-Allow-Origin: *
```

The production Explorer smoke test should then reach `https://ogc-csapi-explorer.pages.dev/map`, finish loading features, and show the new source filters without a duplicate-origin CORS console error.

## 2026-05-26 Verification

The live Oracle host was patched and production-verified after the Met Office, BGS, Environment Agency Hydrology, and UK-AIR Explorer polish pass.

Observed production Explorer result:

- URL: `https://ogc-csapi-explorer.pages.dev/map`
- Feature count: `810 FEATURES`
- Source filters: `EA Hydrology4`, `UK-AIR4`, `BGS / UKGEOS9`, `Met Office15`
- CORS duplicate-origin error: not present
- Met Office deployed-system card: opened successfully with `Weather Observation Site`, recent readings, and the Charterhall weather-station representative image
- BGS deployed-system card: opened successfully with the UKGEOS borehole representative image and groundwater readings