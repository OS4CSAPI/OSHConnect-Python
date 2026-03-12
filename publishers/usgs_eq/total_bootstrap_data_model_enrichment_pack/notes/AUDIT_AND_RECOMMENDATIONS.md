# Audit And Recommendations

## What is already solid

The current earthquake publisher is already well-positioned compared with an
early prototype:

- it uses the correct Pattern C feed-adapter model
- it avoids the major modeling mistake of creating one system per earthquake
- it uses the summary feed as the default runtime surface
- it deduplicates by `(event id, updated timestamp)`, which matches official semantics
- it exposes a useful `detailUrl` in the result body for client-side drill-down

That means the goal of this package is not to redesign the publisher. The goal
is to make the current implementation more explicit, more authoritative, and
easier to extend safely.

## Main gaps

### 1. Official provenance is still thinner than it should be

The current bootstrap links the summary feed docs and ComCat docs, but it does
not yet fully surface:

- GeoJSON detail-feed docs
- feed lifecycle policy
- event-terms docs
- FDSN event API docs

These are all official USGS sources and should be linked in the metadata.

### 2. The datastream schema under-documents available summary-feed semantics

The current result contract is intentionally lean, but the bootstrap does not
make the omitted fields explicit. In practice, the upstream summary feed already
provides useful semantics such as:

- significance
- tsunami indicator
- alert level
- contributor network
- station-count and uncertainty-style fields

Documenting those omitted fields is important even if the runtime keeps the
baseline contract unchanged.

### 3. The package should separate summary-driven runtime from detail-driven enrichment

The biggest modeling boundary in this publisher is not station vs feed. It is:

- summary feed for baseline runtime
- detail feed or FDSN query for selective enrichment

That boundary is currently implicit. It should be explicit.

### 4. A few runtime behaviors are still better described as follow-on improvements

The current package request is primarily bootstrap, data model, metadata, and
data sidecars. Still, a strong pack should record the main runtime follow-ons:

- current `NaN` string handling for null magnitude is not ideal
- dedupe cache does not persist across restarts
- resultTime uses publisher clock instead of feed generated time
- the publisher currently does not expose `url`, `sig`, `tsunami`, or `alert`

These are not blockers for the current package, but they should be recorded.

## Recommendations to apply now

### 1. Keep Pattern C unchanged

Do not introduce per-event systems, per-region systems, or detail-driven
bootstrap resources. The current one-procedure, one-system, one-datastream,
two-deployment model is correct for a real-time earthquake feed.

### 2. Enrich the official references aggressively

Add the following official references to the procedure, system, datastream, and
deployment metadata where appropriate:

- GeoJSON Summary docs
- GeoJSON Detail docs
- Feed Lifecycle Policy
- ComCat documentation
- Event Terms documentation
- FDSN Event API docs

### 3. Document the feed variant strategy

The current config choice of `all_day` is still sensible, but the bootstrap and
pack should document that:

- `all_day` is the default recommended variant
- `significant_month` is the best low-volume alternative
- variant selection is a config decision, not a data-model rewrite

### 4. Document omitted summary fields as first-class semantics

Even if the default result contract does not expand yet, the datastream metadata
should explicitly mention the existence and meaning of:

- `sig`
- `alert`
- `tsunami`
- `net`
- `url`
- `types`
- `nst`
- `dmin`
- `rms`
- `gap`

This prevents future users from assuming the upstream feed is thinner than it is.

### 5. Preserve summary feed as the default runtime surface

Do not turn the base publisher into a detail-polling pipeline. The summary feed
is the correct polling target. Detail or FDSN fetches should remain selective
enhancements for cases such as:

- significant events
- revised events
- backfill workflows
- analyst drill-down

## Recommendations to document now but implement later

### 1. Optional result-body expansion

If the UI or downstream clients need richer event data, the best optional fields
to add first are:

- `eventPageUrl`
- `significance`
- `tsunami`
- `alertLevel`
- `network`

Those provide high user value without requiring full product ingestion.

### 2. Selective detail enrichment policy

If the project ever adds detail fetches, it should do so with clear triggers.
Good triggers would be:

- `alert` is not null
- `sig` exceeds a threshold
- the feed variant is `significant_*`
- an event is revised after first publication

### 3. Runtime quality improvements

Strong follow-on improvements include:

- use explicit null-handling for missing magnitude
- optionally record feed generated time for provenance
- persist dedupe state across restarts if duplication after restart becomes an issue
- add fixture-based tests for summary and detail parsing

## Bottom line

The current earthquake publisher does not need a conceptual redesign. It needs
a robust documentation-and-enrichment layer that:

- states the Pattern C model clearly
- anchors the bootstrap to current official USGS docs
- documents the richer semantics already available upstream
- defines where future detail-driven enrichment belongs

That is the purpose of this pack.
