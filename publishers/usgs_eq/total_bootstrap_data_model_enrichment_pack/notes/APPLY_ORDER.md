# Apply Order

Use this order if the package is applied back into `bootstrap_usgs_eq.py` or used
as the basis for a formal enrichment pass.

1. Read `notes/LIVE_SOURCE_VERIFICATION_2026-03-12.md`.
2. Read `data_model/RESOURCE_MODEL.md`.
3. Add the constants and helper URLs from `patches/01_constants_block.py`.
4. Enrich the procedure metadata using `patches/02_procedure_body.py`.
5. Enrich the system metadata using `patches/03_system_metadata.py`.
6. Enrich the datastream documentation and schema notes using `patches/04_datastream_schema.py`.
7. Enrich deployment metadata using `patches/05_deployment_blocks.py`.
8. Review `patches/06_config_recommendation.json` before changing the runtime feed variant.
9. Keep runtime follow-on items in `notes/RUNTIME_AND_MODEL_IMPROVEMENTS.md` separate from metadata-only changes.

## Important sequencing rule

Do not mix metadata enrichment with runtime contract expansion in the same pass
unless there is a specific consumer need. The safe path is:

- metadata now
- runtime field expansion later

## Fastest high-value subset

If only the most valuable metadata upgrades are applied, do these first:

1. official source URLs
2. datastream omitted-field documentation
3. feed lifecycle policy references
4. explicit statement that detail and FDSN are enrichment companions, not the default polling surface
