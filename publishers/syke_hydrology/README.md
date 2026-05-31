# SYKE Hydrology Publisher

Publishes curated Finnish hydrology observations from the public SYKE Hydrologiarajapinta OData API.

## Source Endpoints

- OData base: `https://rajapinnat.ymparisto.fi/api/Hydrologiarajapinta/1.0/odata`
- Stations: `Paikka`
- Water level: `Vedenkorkeus`
- Discharge: `Virtaama`

No API key is required.

## Commands

```bash
python -m publishers.syke_hydrology.bootstrap_syke_hydrology --dry-run --force-sml
python -m publishers.syke_hydrology.syke_hydrology_publisher --dry-run --once
python -m publishers.syke_hydrology.syke_hydrology_publisher --interval 900
```

The station set in `stations.json` intentionally stays small and Finnish-focused: selected stations have same-day readings and clean coordinates.
