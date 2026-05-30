# Digitraffic Marine AIS Publisher

Publishes live vessel positions from Fintraffic Digitraffic Marine AIS for a bounded Gulf of Finland demo window.

The publisher uses a CSAPI feed-adapter system, one datastream, and a deployment marker at the configured query-window center. The deployment marker is a metadata entry point for the feed adapter, while the live map experience comes from vessel observations. Each publish cycle filters the public AIS latest-location feed to the configured bbox, caps the cycle to `max_vessels_per_cycle`, enriches records with vessel metadata where available, and emits one observation per vessel.

```powershell
py publishers\digitraffic_marine_ais\bootstrap_digitraffic_marine_ais.py --dry-run
py publishers\digitraffic_marine_ais\digitraffic_marine_ais_publisher.py --dry-run --once
```

Source endpoints:

- `https://meri.digitraffic.fi/api/ais/v1/locations`
- `https://meri.digitraffic.fi/api/ais/v1/vessels`

Attribution follows Digitraffic terms of use.