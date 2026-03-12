# Runtime and Model Improvements

This package is primarily a bootstrap, data-model, and enrichment handoff. It is
not a mandate to change runtime code immediately. Still, several follow-on
improvements are worth recording.

## Highest-value runtime and model improvements

### 1. Decide whether one-camera-per-site remains the explicit project rule

The current publisher assumes:

- one selected camera per shared water station system
- one fixed output name per station system

This is fine for the current curated set, but it should remain an intentional rule,
not an accidental hidden constraint.

### 2. If multi-camera support is needed, redesign deliberately

The current architecture will not generalize cleanly to multiple live cameras per
site without design work.

Reason:

- a shared station system currently receives one NIMS datastream with fixed `outputName`
- dedupe is keyed by `nwisId`

Viable future options:

- multiple datastreams on the shared station system with camera-specific output names
- one camera system per camera
- a feed-adapter model for grouped camera streams

### 3. Consider moving runtime fetches to `rawItem=true`

Current runtime uses plain filename arrays. That is good enough.

Potential future benefit of `rawItem=true`:

- explicit upstream timestamp
- file size (`fs`)
- cleaner provenance than filename parsing alone

Recommended position:

- document it now
- adopt it only if a consumer wants the extra metadata

### 4. Decide whether richer observation fields are worth the contract cost

Current observation result fields are:

- `stationId`
- `camId`
- `imageUrl`
- `thumbUrl`
- `smallUrl`
- `mediaType`
- `filename`
- `timeLapseUrl`

Possible future additions:

- `fileSizeBytes`
- `cameraName`
- `captureMode`
- `ingestIntervalMin`
- `upstreamTimestamp`

Recommended position:

- keep the current result body small for now
- treat richer camera identity and cadence as datastream or sidecar metadata first

## Data-model positions

### Keep the shared-system Pattern A model for the current curated set

The current companion-datastream pattern is still the right baseline because it
keeps station identity unified across water and imagery.

### Keep binary media out of OSH

Image-reference observations remain the correct design. Do not push JPEG or MP4
blobs into the observation store.

### Keep camera-specific provenance in sidecars or datastream metadata first

Fields such as `TL_enabled`, `ingest.period`, `ingest.intr`, and `newestImageDT`
are better treated as metadata unless a concrete UI or analytics consumer needs
them in every observation.
