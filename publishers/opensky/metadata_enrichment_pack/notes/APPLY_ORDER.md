# Apply Order

1. Add the constants and helper builders from `patches/01_constants_block.py`.
2. Replace the current `PROCEDURE_BODY` with `patches/02_procedure_body.py`.
3. Merge the richer link/profile metadata from `patches/03_system_stub.py`.
4. Replace `_system_sml()` with `patches/04_system_sml.py`.
5. Merge the description/documentation/characteristic additions from `patches/05_datastream_schema.py`.
6. Merge the deployment description and link additions from `patches/06_deployment_blocks.py`.
7. Optionally enrich `config.json` using `patches/07_config_enrichment_example.json`.

## Safe rollout strategy

- First commit: metadata-only bootstrap changes
- Second commit: optional `config.json` descriptive enrichments
- Third commit: optional UI/demo asset references

## Validation checklist

- bootstrap still creates the procedure successfully
- system stub still posts successfully
- SensorML PUT still succeeds
- datastream creation still succeeds
- deployment creation still succeeds
- Explorer still renders the feed system and deployment cards
- new metadata fields are preserved by the server, or degrade harmlessly if stripped
