# OSH Strict SWE Observation Field Order and Datastream Immutability

**Date:** 2026-06-03  
**Context:** Storebaelt webcam publisher Phase 1 freshness heartbeat deployment on the Oracle OSH/CSAPI server.

## Summary

The Storebaelt freshness-heartbeat deployment exposed two important OSH/OGC CSAPI implementation constraints:

1. Existing datastream record structures cannot be updated after observations exist.
2. Observation result JSON must follow the datastream SWE `DataRecord` field order exactly.

Both behaviors are important for publisher authors because they affect schema evolution, bootstrap strategy, and runtime payload construction.

## Finding 1: Datastream Record Structures Are Immutable After Observations

Attempting to update the Storebaelt datastream schema in place failed after the datastream already had observations.

Observed server response:

```text
HTTP 400 PUT /datastreams/{id}
Cannot update the record structure or encoding of a datastream if it already has observations
```

This means publisher developers should treat a datastream's `schema.resultSchema.fields` as effectively immutable once observations have been written.

### Practical Implications

- Add result fields before first production publishing whenever possible.
- For new publishers, run schema dry-runs and local observation serialization checks before deploying the service.
- For existing datastreams with observations, schema changes require one of these migration paths:
  - create a new datastream/output name/version;
  - delete and recreate the datastream if historical observations can be discarded;
  - create a companion status datastream for new fields;
  - keep old schema and encode optional status in existing fields only if semantically acceptable.

For Storebaelt, the datastreams were brand new and only contained initial observations, so we deleted and recreated just the two Storebaelt datastreams while preserving systems, deployments, and procedures.

## Finding 2: SWE Observation Result Field Order Is Strict

After the Storebaelt datastreams were recreated with the updated schema, the first heartbeat payload still failed because the JSON object emitted `sourceUrl` before the newly added freshness fields.

Observed server response:

```text
HTTP 400 POST /datastreams/{id}/observations
Invalid payload: Invalid JSON: Expected field 'imageChanged' but was 'sourceUrl'
```

The result payload contained all required fields, but not in the exact order declared by the SWE `DataRecord` schema. OSH's SWE JSON parser treated that as invalid.

### Practical Implications

- Runtime observation payloads must preserve insertion order matching the datastream schema.
- In Python publishers, build `result` dictionaries in schema order and avoid appending new fields after a trailing field that already appears later in the schema.
- If enriching a result after initial construction, move any trailing fields as needed so the final insertion order matches the schema.
- Add tests that check result key order for strict SWE datastreams.

For Storebaelt, the fix was to temporarily pop `sourceUrl`, add the freshness fields, and then reinsert `sourceUrl` so the runtime payload matched schema order.

## Recommended Publisher Pattern

When designing or changing a datastream schema:

1. Declare the SWE `DataRecord` fields in the exact desired runtime order.
2. Construct result objects in the same order.
3. Add regression tests asserting key order for any publisher that mutates/enriches result dictionaries.
4. Deploy schema changes before starting the service.
5. If observations already exist, do not assume `PUT /datastreams/{id}` can alter the schema.
6. Prefer a new datastream or companion status stream for non-disposable production histories.

## Storebaelt-Specific Resolution

The Storebaelt Phase 1 freshness heartbeat deployment used this migration path:

1. Stop `storebaelt-webcams-publisher.service`.
2. Pull and compile the updated publisher code on Oracle.
3. Attempt in-place datastream schema update; observe OSH immutability rejection.
4. Delete and recreate only the two Storebaelt webcam datastreams.
5. Restart the service.
6. Observe strict field-order rejection.
7. Patch runtime payload ordering and add a regression test.
8. Redeploy and verify both changed and unchanged heartbeat observations are accepted.

Final verified behavior:

- First post after datastream recreation: two `changed/fresh` observations accepted.
- Manual unchanged one-shot cycle: two `unchanged/unchanged` observations accepted.

## Broader CSAPI Lesson

CSAPI publisher implementations should not treat SWE result schemas as loose JSON contracts. In OSH, they are typed, ordered record structures. That is good for interoperability, but it means publisher code must be deliberate about schema versioning and JSON object field order.
