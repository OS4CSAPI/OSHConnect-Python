# OSH Server Compatibility Issue Draft

Date: 2026-05-26

## Proposed Title

System SensorML PUT returns HTTP 500 and prevents publisher media metadata updates

## Summary

Environment Agency Hydrology bootstrap can create systems, datastreams, deployments, and observations successfully on the configured OSH endpoint, but system-level SensorML replacement currently fails with HTTP 500. Procedure SensorML PUT succeeds. The failure prevents new system metadata such as representative side-card image documents from reaching the live CSAPI resources through the normal SensorML path.

This is now visible as a publisher interoperability issue because station/system publishers rely on system SensorML `documents` metadata for rich Explorer cards, including thumbnails, source links, and attribution.

## Affected Endpoint

```text
https://os4csapi-osh.duckdns.org/sensorhub/api
```

Representative production preset:

```text
OSH (OS4CSAPI)
https://129-80-248-53.sslip.io/sensorhub/api
```

## Reproduction

From `OSHConnect-Python`:

```powershell
py -m publishers.environment_agency_hydrology.bootstrap_environment_agency_hydrology --force-sml
```

Observed output includes one warning per Environment Agency station system:

```text
[WARN] SML PUT skipped for system urn:os4csapi:system:environment-agency-hydrology:48513a18-e485-4317-ae92-93bf4f7f3e54:v1 (id=05j0): HTTP 500 PUT https://os4csapi-osh.duckdns.org/sensorhub/api/systems/05j0: {
  "status": 500,
  "message": "Internal server error"
}
```

Additional affected systems during the same run:

```text
urn:os4csapi:system:environment-agency-hydrology:d52d0eab-1e64-4d76-a1f2-e81c7948d2c0-435510:v1
urn:os4csapi:system:environment-agency-hydrology:c7e13884-4a02-4df3-b184-09aea28cf8e8-3-020:v1
urn:os4csapi:system:environment-agency-hydrology:959f3e4f-bb6e-4f4a-8082-0157eea99482:v1
```

## Expected Behavior

`PUT /systems/{id}` with `Content-Type: application/sml+json` should accept a valid SensorML JSON document for an existing system, consistent with procedure SensorML replacement behavior.

At minimum, the server should return a diagnostic 4xx response explaining which SensorML field is invalid instead of an opaque HTTP 500.

## Actual Behavior

The server returns HTTP 500 for every Environment Agency Hydrology system SensorML PUT attempted during `--force-sml`.

The bootstrap safely logs the failure and continues, so operational publishing still works:

- systems exist,
- datastreams exist,
- deployments exist,
- live observations publish successfully.

The missing system SensorML update still blocks normal rich metadata propagation.

## Demo Impact

Explorer side-card thumbnails normally come from system SensorML image documents. Because the system PUT fails, the Environment Agency Hydrology representative gauge photo cannot be relied on from live system SensorML metadata.

Temporary mitigation implemented in Explorer:

```text
OS4CSAPI/ogc-csapi-explorer@5323b4d Show hydrology station thumbnail fallback
```

Publisher metadata and docs update:

```text
OS4CSAPI/OSHConnect-Python@87a8f77 Add hydrology station thumbnail metadata
OS4CSAPI/OSHConnect-Python@c6fc2d9 Record hydrology thumbnail live verification
```

## Related Browser Finding

After reloading the production Explorer, the OSH external URL also produced a browser CORS diagnostic indicating duplicate `Access-Control-Allow-Origin` values:

```text
The 'Access-Control-Allow-Origin' header contains multiple values '*, https://ogc-csapi-explorer.pages.dev', but only one is allowed.
```

The app can still work through the configured proxy path, but this should be tracked as adjacent server/proxy header behavior if direct browser access is expected to remain supported.

## Suggested Labels

```text
bug
server-interop
sensorml
publisher-support
```

## Notes

The GitHub CLI was not available in the current environment and no issue-management tool was exposed, so this file is an issue-ready draft rather than a remotely created GitHub issue.
