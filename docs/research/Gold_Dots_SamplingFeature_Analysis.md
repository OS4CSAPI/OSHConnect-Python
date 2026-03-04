# Gold Dots → SamplingFeature Gap Analysis

## Context

The LOB Localizer produces location-estimate observations (rendered as gold ⊕ dots
on the map) by fusing Lines of Bearing from three acoustic sensor nodes via Weighted
Least Squares triangulation. These observations are POSTed to a dedicated CSAPI
DataStream but currently lack any `featureOfInterest` / `samplingFeature` link.

This report evaluates the semantic gap and recommends a phased approach to closing it.

## Current Observation Payload

Each gold dot is POSTed as:

```json
{
  "phenomenonTime": "2026-03-03T18:42:01.123Z",
  "resultTime": "2026-03-03T18:42:01.123Z",
  "result": {
    "timestamp": 1741023721.123,
    "trackId": 1,
    "estimatedLat": 31.6578,
    "estimatedLon": -110.2634,
    "cep50_m": 68.4,
    "classification": "UAS",
    "numContributingLobs": 3,
    "contributingSensors": "AZ-MA-1,AZ-MA-2,AZ-MA-3",
    "residual_m": 42.1
  }
}
```

**What's missing:** No `samplingFeature@link` field. The track identity (`trackId: 1`,
`classification: "UAS"`) is embedded in the result blob where only our UI knows how
to interpret it — it is not a first-class CSAPI resource link.

Per SOSA/SSN, every `sosa:Observation` should reference a `sosa:FeatureOfInterest`
that identifies *what the observation is about*. Without this, the gold dots are
semantically "free-floating fixes" with no durable subject.

## Options Evaluated

### Option 1: Single SamplingFeature = Monitored Airspace (Recommended Now)

Create one SamplingFeature representing the **monitored airspace / area of interest**
(convex hull of the three sensor positions), and set every location-estimate
observation's `samplingFeature@link` to reference it.

| Criterion | Assessment |
|-----------|------------|
| Implementation cost | ~30 lines: 1 bootstrap POST + 1 field added to `build_location_estimate()` |
| Lifecycle management | None — the airspace is static |
| Semantic correctness | Answers "what is this observation about?" (the monitored airspace) |
| CSAPI conformance | Closes the `featureOfInterest` gap at minimum cost |
| UI impact | Zero — the app already renders SamplingFeatures on the map |

**Verdict:** Right choice for the current sprint. The sensor network is fixed, there
is exactly one UAV target, and the localizer operates over a single AOI. This adds
semantic completeness without engineering overhead.

### Option 2: Per-Track SamplingFeature (UAS-Track-001)

Create a SamplingFeature for each **track hypothesis identity** when the localizer
produces its first valid fix for a new `(trackId, classification)` tuple. All
subsequent fixes for that track reference the same SamplingFeature.

| Criterion | Assessment |
|-----------|------------|
| Implementation cost | Moderate — requires create-on-first-fix logic, ID caching, lifecycle management |
| Lifecycle management | Must handle track creation, potential track merging/splitting, stale track cleanup |
| Semantic correctness | Most precise: each observation links to the specific tracked entity |
| CSAPI conformance | Full conformance with observation → subject linkage |
| UI impact | Could enable track-grouped display, track history playback |

**Verdict:** Correct eventual architecture, but premature today. The localizer
hard-codes `trackId: 1` and there is exactly one UAV. Building track lifecycle
management for a single-target scenario adds complexity without user-visible benefit.
This becomes valuable when multi-target tracking is implemented.

### Option 3: Domain Feature (the UAV as a first-class object)

Model the UAV as a domain-level Feature in an external Features service, linked from
observations via a Feature reference.

| Criterion | Assessment |
|-----------|------------|
| Implementation cost | High — requires a Features service or external catalog |
| Semantic correctness | Ultimate correctness: the UAV is a real-world entity, not just a sampling artifact |
| CSAPI conformance | Beyond current scope — CSAPI Part 2 doesn't mandate external Feature services |

**Verdict:** Future work. Appropriate when integrating with a Common Operating Picture
or multi-domain fusion system.

## Recommendation

**Phase 1 (now):** Implement Option 1.
- Bootstrap script: POST one SamplingFeature to `/samplingFeatures` with the convex
  hull of {AZ-MA-1, AZ-MA-2, AZ-MA-3} as geometry
- `build_location_estimate()`: add `"samplingFeature@link": { "href": "/samplingFeatures/{id}" }`
  to the observation envelope
- Zero UI changes required

**Phase 2 (when multi-target tracking lands):** Upgrade to Option 2.
- Localizer creates a SamplingFeature per track on first valid fix
- Subsequent fixes reference the track's SamplingFeature
- UI gains track-grouped display and history

**Phase 3 (integration phase):** Evaluate Option 3 if a domain Feature service exists.

## Implementation Estimate

| Item | LOE |
|------|-----|
| Option 1 bootstrap script addition | ~15 lines |
| Option 1 observation payload change | ~5 lines in `build_location_estimate()` |
| Option 1 localizer startup (discover SF ID) | ~10 lines |
| **Total Option 1** | **~30 lines, <1 hour** |

---

*Filed: 2026-03-03 · Source: Copilot analysis of ChatGPT SamplingFeature report vs. actual codebase*
