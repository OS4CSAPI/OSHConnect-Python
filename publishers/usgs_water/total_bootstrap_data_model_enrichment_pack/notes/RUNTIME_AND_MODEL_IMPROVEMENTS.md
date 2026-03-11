# Runtime and Model Improvements

This package is primarily a bootstrap, data-model, and enrichment handoff. It is
not a mandate to change runtime code immediately. Still, several follow-on
improvements are worth recording here so they are not lost.

## Highest-value runtime improvements

### 1. Switch latest-only polling to `latest-continuous`

Current runtime behavior:

- query `continuous/items`
- limit results
- take the newest item

Recommended future behavior:

- query `latest-continuous/items`

Why:

- better semantic fit
- cleaner documentation story
- less reliance on ordering assumptions

### 2. Consider tracking `time_series_id` in dedupe or provenance logic

Current dedupe is timestamp-based per station and parameter. That is acceptable.

Potential future improvement:

- retain `time_series_id` at the datastream-provenance layer
- optionally surface it in debug or audit logs

This is especially useful if upstream series semantics ever shift.

### 3. Decide whether `last_modified` belongs in the result body

Live upstream responses include `last_modified`.

Pros of emitting it:

- better auditability
- easier detection of upstream revisions

Cons:

- larger payloads
- more consumer contract surface
- may be redundant for many use cases

Recommended position:

- document it now
- defer emitting it until a concrete consumer needs it

## Data-model positions

### Keep the station model

The current one-system-per-station, two-datastreams-per-station model is sound.
Do not replace it with a feed-adapter model.

### Keep one datastream per parameter family

Because `00060` and `00065` carry stable units and meaning, one datastream per
parameter remains the right baseline.

### Do not create separate datastreams for provisional vs approved values

Approval state is observation-level metadata, not a datastream split criterion.

### Treat `statistic_id=00011` as datastream provenance

For the current publisher, instantaneous-vs-daily distinction is best modeled as
datastream metadata rather than as a runtime station-level choice.

## Optional future expansion

- add water temperature (`00010`) where consistently available
- assess whether NIMS imagery should share the same systems or attach as companion systems
- add fixture-based parser tests around qualifier shapes and null handling
