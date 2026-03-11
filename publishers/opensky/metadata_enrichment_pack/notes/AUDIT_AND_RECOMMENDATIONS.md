# Audit and Recommendations

## Bottom line

Yes: the OpenSky bootstrap is mature enough that a dedicated metadata enrichment
pack is justified.

Unlike the early NWS/NDBC state, the current OpenSky bootstrap already has a
strong metadata baseline. The main opportunity is not to rescue a thin bootstrap;
it is to turn a technically accurate bootstrap into a more curated, demo-ready,
and reviewer-friendly one.

## What is already strong

- clear Pattern C modeling: one feed-adapter system, one datastream
- solid procedure description
- correct use of contacts/documents/characteristics/capabilities in SensorML
- explicit deployment linkage through `platform@link`
- config-backed cadence and bounding box
- meaningful datastream field semantics

## Main metadata gaps

### 1. Procedure provenance can do more of the explanatory work

The procedure already says what it does, but it can better expose:

- the state-vector field reference
- the configured auth mode story (anonymous vs OAuth2)
- the configured bounding-box cost model
- the fact that one aircraft state becomes one CSAPI observation
- the runtime deduplication rule for unchanged aircraft timestamps

### 2. The system needs a richer operating-profile story

The current SensorML body explains the source well, but it can more explicitly
carry:

- configured bounding-box label and area
- cadence and daily request budget
- auth mode and token-flow context
- position-source vocabulary (ADS-B, ASTERIX, MLAT, FLARM)
- feed-adapter semantics for reviewers who are not already familiar with Pattern C

### 3. The datastream metadata should describe runtime semantics, not just fields

The current datastream schema is good, but it does not fully explain:

- one observation per aircraft per cycle
- source-side bounding-box filtering
- null numeric handling in the current publisher (`"NaN"` string normalization)
- why `position_source` is a controlled vocabulary
- why callsign/squawk fields may be empty even when the record is valid

### 4. The deployment descriptions should foreground the demo geography

The deployment blocks are accurate, but they can better describe:

- this is an Arizona-focused airspace demo grouping
- the deployment is conceptual, not a single physical sensor emplacement
- the feed is selected to co-locate with the broader southern Arizona demo story

### 5. The source package is missing a sidecar manifest

OpenSky is less station-centric than NWS/NDBC, so the missing metadata is not a
station list. The missing sidecar is a compact explanation of:

- official source URLs
- configured coverage/auth/rate assumptions
- position-source semantics

That kind of sidecar is useful for both reviewers and future UI work.

## Recommended conservative additions

If you want the safest low-risk pass, add only:

- stronger descriptions
- more official documentation links
- clearer coverage/auth/cadence notes
- clearer deployment wording
- a representative local asset reference

## Recommended rich additions

If your OSH/CSAPI stack preserves the richer metadata cleanly, also add:

- coverage-profile metadata
- access-profile metadata
- position-source vocabulary in SensorML
- feed-adapter semantics and deduplication notes
- sidecar config-derived metadata examples

## Suggested application priorities

1. Procedure and datastream documentation links
2. System coverage/auth profile metadata
3. Deployment wording and demo-geography clarity
4. Sidecar manifests for config-derived semantics
5. Representative asset and future UI notes
