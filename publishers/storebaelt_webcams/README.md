# Storebaelt Webcams Publisher

> Archived 2026-06-04: do not run this publisher as an active public source.
> Storebaelt/Sund & Baelt replied to the permission request that the webcam service is being shut down and cannot be used as an OGC CSAPI demonstration case. The public Oracle publisher has been stopped/disabled and the CSAPI resources have been removed. This package remains only as a historical implementation pattern for camera metadata, poster freshness, and SWE field-order handling.

Publishes image-reference observations for the public Storebaelt traffic/weather webcams.

The source is an embedded live-video page, not a JSON API. The publisher uses the stable poster JPEG URLs exposed by the Mediathand player pages as the first ingestion target and preserves the public page and player URLs as provenance.

## Cameras

- Storebaelt Tower Webcam: `https://player.sob.m-dn.net/sb1-live.html`
- Sprogo Webcam: `https://player.sob.m-dn.net/sb2-live.html`

## Bootstrap

```bash
STOREBAELT_WEBCAMS_ALLOW_ARCHIVED=1 python -m publishers.storebaelt_webcams.bootstrap_storebaelt_webcams
```

Clean-only teardown remains available without the archive override:

```bash
python -m publishers.storebaelt_webcams.bootstrap_storebaelt_webcams --clean-only
```

## Run

```bash
STOREBAELT_WEBCAMS_ALLOW_ARCHIVED=1 python -m publishers.storebaelt_webcams.storebaelt_webcams_publisher --interval 300
```

Use `--dry-run --once` only for controlled historical testing.
