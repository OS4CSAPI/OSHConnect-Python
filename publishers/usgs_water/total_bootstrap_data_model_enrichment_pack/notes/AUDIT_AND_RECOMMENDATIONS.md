# Audit and Recommendations

## Bottom line

Yes: the USGS water publisher is worth a dedicated total package that combines
bootstrap review, data-model clarification, and metadata enrichment.

Unlike the earliest NWS and NDBC states, the current USGS water bootstrap is not
thin or broken. It already has a good architecture. The value here is to make the
publisher more explicit, more authoritative, and easier to extend safely.

## What is already strong

- one shared observing procedure for all curated USGS water stations
- one system per monitoring location
- one datastream per parameter family, which keeps units and semantics stable
- a clear deployment tree with station-level `platform@link`
- successful use of the USGS Water Data OGC API rather than scraping or ad hoc parsing
- a compact observation payload that matches the current downstream need

## The main gaps

### 1. Procedure metadata under-describes the real upstream contract

The current procedure says the publisher uses the USGS Water Data OGC API, but it
does not fully expose the modern upstream shape:

- `latest-continuous` is live and appropriate for latest-only polling
- `time-series-metadata` is the authoritative place to understand series semantics
- `combined-metadata` exists and can supply richer station-plus-series context
- `statistic_id=00011` is the key instantaneous-series discriminator for this publisher

This matters because `parameter_code` alone is not enough to tell the full story.

### 2. System metadata leaves authoritative monitoring-location fields on the table

The live `monitoring-locations` and `combined-metadata` collections expose fields
that the current system metadata mostly omits:

- `agency_code`, `agency_name`, `district_code`
- `site_type_code`, `site_type`
- `altitude`, `altitude_accuracy`
- `vertical_datum`, `vertical_datum_name`
- `horizontal_positional_accuracy`
- `horizontal_position_method_name`
- `original_horizontal_datum_name`
- `uses_daylight_savings`

Those are high-value fields because they improve station credibility and support
better map, card, and detail-page rendering without changing runtime behavior.

### 3. Datastream metadata should anchor to the instantaneous series explicitly

Live verification showed an important subtlety: querying `time-series-metadata`
for `monitoring_location_id=USGS-09380000` and `parameter_code=00060` returned
both:

- a daily mean series (`statistic_id=00003`)
- an instantaneous points series (`statistic_id=00011`)

The current publisher correctly pulls from the `continuous` collection, but the
bootstrap does not explicitly encode this distinction in its metadata.

Recommendation:

- describe each datastream as the `00011` instantaneous series
- include direct links to `latest-continuous` and `time-series-metadata` queries
- document the role of `time_series_id` as upstream lineage, not as a stable
  design-time constant in `stations.json`

### 4. The curated station config can be richer without becoming brittle

The current `stations.json` is intentionally compact. That is reasonable for Phase 1.
But a metadata-focused pack can safely recommend optional fields such as:

- `agencyCode`
- `districtCode`
- `siteTypeCode`
- `siteType`
- `altitude_ft`
- `altitudeAccuracy_ft`
- `verticalDatum`
- `verticalDatumName`
- `horizontalAccuracyNote`
- `horizontalMethodName`
- `usesDaylightSavings`
- canonical source URLs per station and parameter

These additions improve bootstrap richness while keeping the runtime fetch logic
stable and simple.

### 5. The current runtime should eventually migrate from `continuous?limit=1`

The pack keeps runtime changes out of scope, but the recommendation is clear.

Because `latest-continuous` is live and purpose-built, it is the better endpoint
for latest-only polling than:

- `continuous/items?limit=1`

Benefits:

- clearer semantic intent
- less dependence on ordering assumptions
- better alignment between runtime behavior and documentation

### 6. The current result body is intentionally minimal; that is good, but it should be documented

The current result body includes:

- `stationId`
- `discharge_cfs` or `gage_height_ft`
- `qualifier`
- `approvalStatus`

That is a sound minimal contract. It avoids bloating every observation with fields
that are already stable at the datastream level.

However, the data-model notes should explicitly explain why these upstream fields
are *not* currently emitted:

- `parameter_code`
- `statistic_id`
- `time_series_id`
- `unit_of_measure`
- `last_modified`

They are real and important, but they are currently better represented as
datastream provenance or future optional result fields.

## Strongest recommendations

### Recommended now

- enrich procedure documentation and usage constraints
- enrich system SensorML with authoritative station metadata
- enrich datastream descriptions with `statistic_id=00011` and upstream collection links
- add sidecar data-model documentation and live-source examples
- add an optional enriched station JSON example

### Recommended next

- migrate the publisher to `latest-continuous` for latest-only polling
- track and document `time_series_id` more explicitly in datastream provenance
- decide whether `last_modified` belongs in future observation payloads or only in notes

### Recommended later

- add optional support for additional parameter families such as `00010` water temperature
- consider whether some station reference fields should be refreshed live rather than maintained manually

## What should not change right now

- do not redesign the one-system-per-station model
- do not split datastreams by approval status
- do not add heavy per-observation metadata unless a real consumer needs it
- do not replace the curated station list with nationwide discovery during this phase

The current architecture is sound. The highest-value work is semantic strengthening,
not model replacement.
