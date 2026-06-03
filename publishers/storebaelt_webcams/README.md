# Storebaelt Webcams Publisher

Publishes image-reference observations for the public Storebaelt traffic/weather webcams.

The source is an embedded live-video page, not a JSON API. The publisher uses the stable poster JPEG URLs exposed by the Mediathand player pages as the first ingestion target and preserves the public page and player URLs as provenance.

## Cameras

- Storebaelt Tower Webcam: `https://player.sob.m-dn.net/sb1-live.html`
- Sprogo Webcam: `https://player.sob.m-dn.net/sb2-live.html`

## Bootstrap

```bash
python -m publishers.storebaelt_webcams.bootstrap_storebaelt_webcams
```

## Run

```bash
python -m publishers.storebaelt_webcams.storebaelt_webcams_publisher --interval 300
```

Use `--dry-run --once` to inspect observations without posting.
