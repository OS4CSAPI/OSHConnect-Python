# Digitraffic Rail Trains Publisher

Publishes live Finnish train position observations from the public Fintraffic Digitraffic Rail JSON API.

## Source Endpoints

- Latest train locations: `https://rata.digitraffic.fi/api/v1/train-locations/latest/`
- Live train metadata: `https://rata.digitraffic.fi/api/v1/live-trains`
- Station metadata: `https://rata.digitraffic.fi/api/v1/metadata/stations`

No API key is required.

## Commands

```bash
python -m publishers.digitraffic_rail_trains.bootstrap_digitraffic_rail_trains --dry-run --force-sml
python -m publishers.digitraffic_rail_trains.digitraffic_rail_trains_publisher --dry-run --once
python -m publishers.digitraffic_rail_trains.digitraffic_rail_trains_publisher --interval 300
```

The runtime publisher filters train locations to the configured Finland-wide bounding box and caps each cycle with `max_trains_per_cycle` from `config.json`.
