# Apply Order

1. Add the constants and helper URL builders from `patches/01_constants_block.py`.
2. Replace the current `PROCEDURE_BODY` with `patches/02_procedure_body.py`.
3. Replace `_system_stub()` with `patches/03_system_stub.py`.
4. Replace `_system_sml()` with `patches/04_system_sml.py`.
5. Merge the description/documentation additions from `patches/05_datastream_schema.py`.
6. Merge the deployment description/link additions from `patches/06_deployment_blocks.py`.
7. Optionally enrich `stations.json` using `patches/07_station_json_enrichment_example.json`.
8. Add the representative asset reference from `metadata/buoycam_reference.md`
   and `assets/ndbc_buoy_icon.svg`.

## Safe rollout strategy

- First commit: metadata-only changes
- Second commit: optional enriched `stations.json`
- Third commit: optional station-specific BuoyCAM flags / links
