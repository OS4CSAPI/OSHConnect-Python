# Audit and Recommendations

## Bottom line

Yes: the USGS NIMS imagery publisher is worth a dedicated total package that
combines bootstrap review, data-model clarification, and metadata enrichment.

The current bootstrap is not weak. It already has a coherent and defensible model.
The reason for this package is not rescue. The reason is to make the current model
explicit, authoritative, and future-safe.

## What is already strong

- clear Pattern A modeling: NIMS imagery as a companion datastream on existing USGS water systems
- no binary image ingest; observations carry URLs and metadata only
- a shared NIMS procedure with solid baseline provenance
- a dedicated NIMS deployment tree that does not try to delete or recreate shared water systems
- a simple runtime that derives observation time from the filename pattern and emits stable URL fields

## The main gaps

### 1. The package needs to explain the shared-system model more directly

NIMS is different from USGS water.

The bootstrap does not create NIMS-specific systems. It reuses existing USGS water
station systems. That means the data-model story is:

- procedure: NIMS-specific
- system: shared with USGS water
- datastream: NIMS-specific companion datastream
- deployment tree: NIMS-specific

That distinction should be explicit in the package because it affects how future
extensions should be designed.

### 2. The current model assumes one selected camera per station system

This is the most important live finding.

As verified on 2026-03-11:

- site `09380000` currently exposes 2 live cameras
- site `09019850` currently exposes 4 live cameras

But the current publisher and bootstrap use:

- one fixed `outputName` (`usgsNimsImage`)
- one dedupe slot per `nwisId`
- one curated camera entry per station in `cameras.json`

That means the current design is intentionally a one-camera-per-station selection
model, not a general multi-camera-per-site model.

This is acceptable for the current curated demonstration set, but it must be
documented clearly.

### 3. Camera-side metadata is richer than the current datastream descriptions expose

Live `cameras` responses expose fields that the current bootstrap mostly leaves in
`cameras.json` rather than elevating into metadata structure:

- `camName`
- `camDesc`
- `modifiedDate`
- `newestImageDT`
- `TL_enabled`
- `ingest.period`
- `ingest.intr`
- `locus`

These fields are high-value because they explain cadence, daylight limitations,
timelapse support, and camera identity.

### 4. `listFiles` has a richer mode than the current package documents

The current publisher uses the plain string-array mode:

- `/listFiles?camId=...&limit=1&recent=true`

Live verification confirmed that:

- `rawItem=true` returns structured items with `camId`, `filename`, `timestamp`, and `fs`

That matters because future runtime or metadata work may want:

- image file size
- server-supplied timestamp rather than filename-only parsing
- richer audit evidence for image identity

### 5. URL resolution is a first-class part of the model and should be documented as such

Live verification confirmed HTTP 200 for:

- overlay image URL
- thumbnail image URL
- 720px image URL
- timelapse video URL

This is more than a convenience. It is core provenance for the publisher because
the actual observation payload is a URL package, not a scalar measurement.

## Strongest recommendations

### Recommended now

- enrich procedure metadata with camera discovery, site-filter, rawItem, and S3 resolution notes
- enrich datastream metadata with cadence, daylight/247, timelapse, and URL-resolution semantics
- enrich deployment descriptions with the shared-system Pattern A story
- add camera-side sidecars and worked examples
- explicitly document the one-camera-per-station assumption in the package

### Recommended next

- decide whether multi-camera sites should remain curated to one camera or be generalized
- if generalizing, choose one of:
  - multiple datastreams per shared station with distinct output names
  - separate camera systems
  - a camera-group feed-adapter model
- decide whether `rawItem=true` should become the runtime default

### Recommended later

- consider richer observation payloads with file size or upstream timestamp if a consumer needs them
- evaluate whether timelapse support should be represented more explicitly in metadata or UI

## What should not change right now

- do not replace the Pattern A shared-system model unless there is a real need to support many cameras per site
- do not ingest binary images into OSH
- do not broaden the runtime result body unless a real consumer needs more than the current URL-focused contract
- do not conflate NIMS imagery metadata with water-system metadata unless the shared-system story is kept clear

The current model is sound. The highest-value work is to document its boundaries,
carry richer camera provenance, and record the multi-camera constraint honestly.
