# Apply Order

Use this order if you want to adopt the package incrementally.

## 1. Read the evidence first

- `notes/LIVE_SOURCE_VERIFICATION_2026-03-11.md`
- `notes/AUDIT_AND_RECOMMENDATIONS.md`
- `data_model/RESOURCE_MODEL.md`

## 2. Apply conservative constant and documentation upgrades

Start with:

- `patches/01_constants_block.py`
- `patches/02_procedure_body.py`
- `patches/05_datastream_schemas.py`

These are the lowest-risk improvements and add immediate value.

## 3. Apply system-level SensorML enrichment

Next apply:

- `patches/03_system_stub.py`
- `patches/04_system_sml.py`

This is where most of the authoritative monitoring-location metadata enters.

## 4. Apply deployment wording and source-link upgrades

Then apply:

- `patches/06_deployment_blocks.py`

This keeps the deployment hierarchy the same but makes it more legible and
better grounded in official USGS source material.

## 5. Optionally enrich the curated station config

If you want the bootstrap to carry richer per-station metadata locally, review:

- `metadata/station_enrichment_template.json`
- `metadata/station_09380000_enriched_example.json`
- `patches/07_station_json_enrichment_example.json`

## 6. Review runtime follow-on recommendations separately

Do not mix runtime endpoint changes into the metadata pass unless you intend to
test them carefully. See:

- `notes/RUNTIME_AND_MODEL_IMPROVEMENTS.md`

The most important runtime recommendation is migration to `latest-continuous`.
