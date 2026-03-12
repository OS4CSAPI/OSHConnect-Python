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

These are the safest improvements and add immediate provenance value.

## 3. Apply datastream-level enrichment

Next apply:

- `patches/03_datastream_schema.py`

This is where most NIMS-specific metadata value lives because the current model
reuses shared USGS water systems.

## 4. Apply deployment wording and shared-system clarification

Then apply:

- `patches/04_deployment_blocks.py`

This keeps the architecture unchanged while making the Pattern A story much clearer.

## 5. Optionally enrich the curated camera config

If you want the bootstrap to carry richer camera-side metadata locally, review:

- `metadata/camera_enrichment_template.json`
- `metadata/camera_AZ_upstream_enriched_example.json`
- `patches/05_camera_json_enrichment_example.json`

## 6. Review model follow-on recommendations separately

Do not mix multi-camera generalization into the metadata pass unless you intend
to change the publisher contract. See:

- `notes/RUNTIME_AND_MODEL_IMPROVEMENTS.md`

The most important model follow-on question is whether the current one-camera-per-site
selection should remain explicit project policy or evolve into a multi-camera model.
