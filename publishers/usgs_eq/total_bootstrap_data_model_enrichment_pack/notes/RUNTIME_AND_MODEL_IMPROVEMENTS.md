# Runtime And Model Improvements

This note deliberately goes beyond metadata-only enrichment. It records the most
important next categories of improvement for the USGS earthquake publisher.

## 1. Runtime reliability

High-value follow-ons:

- persist the dedupe cache across process restarts if duplicate replay becomes a real problem
- record cycle-level feed metadata such as `generated` for stronger provenance
- distinguish upstream fetch failure from downstream publish failure in metrics and logs
- add fixture-based regression tests for both summary parsing and publication envelopes

## 2. Result semantics

The first optional fields worth adding are:

- `eventPageUrl`
- `significance`
- `tsunami`
- `alertLevel`
- `network`

These extend user value without requiring full detail-feed ingestion.

## 3. Detail-feed enrichment strategy

If the project later decides to enrich events with detail products, do it selectively.

Good selection policies:

- significant events only
- alert-bearing events only
- revised events only
- operator-triggered backfill

Bad policy:

- fetch detail for every event on every cycle by default

## 4. Data quality handling

Current follow-ons that deserve explicit review:

- replace string `NaN` with a cleaner null strategy for missing magnitude
- decide whether `status` alone is enough, or whether detail-level `review-status`
  should sometimes be used
- decide whether quality indicators like `gap`, `rms`, and `nst` matter enough to
  enter the default result contract

## 5. Source strategy

The current source layering is good and should stay explicit:

- summary feed for polling
- detail feed for selective enrichment
- FDSN event query for targeted retrieval and future backfill

The package should not blur those roles.

## 6. Explorer-facing opportunities

If the demo application later wants richer earthquake presentation, the most
useful extensions are:

- badge rendering from `alert`
- sorting or prominence from `sig`
- tsunami icon from `tsunami`
- direct link-out using `url`
- optional detail panel populated from selective detail fetches
