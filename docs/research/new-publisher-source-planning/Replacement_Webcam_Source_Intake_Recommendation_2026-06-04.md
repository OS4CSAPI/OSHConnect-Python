# Replacement Webcam Source Intake Recommendation

**Date:** 2026-06-04  
**Decision:** Proceed with Digitraffic (Fintraffic) road weather cameras as the next active webcam/media source for OS4CSAPI publisher work.

## Why This Source

Digitraffic is the strongest replacement based on both permission clarity and technical fit:

- Explicit open-data license: Creative Commons BY 4.0.
- Explicit attribution guidance provided by source owner.
- Public road weather camera APIs and image endpoints are reachable without private credentials.
- Camera metadata and image timing are available in structured APIs.
- Image endpoint supports ETag, enabling efficient freshness polling and conditional requests.
- Source provides clear request-behavior guidance (rate limits, headers, caching expectations).

## Evidence Collected

### Licensing and terms

- Digitraffic terms page states open data is licensed under CC BY 4.0.
- Attribution guidance includes preserving copyright notice, linking license, and noting modifications.
- Suggested attribution example: "Source: Fintraffic / digitraffic.fi, license CC 4.0 BY".

References:
- https://www.digitraffic.fi/en/terms-of-service/
- https://www.digitraffic.fi/en/support/instructions/

### API and media readiness

- Station metadata endpoint returned active camera stations:
  - https://tie.digitraffic.fi/api/weathercam/v1/stations
- Detailed station data returned preset IDs with measuredTime values:
  - https://tie.digitraffic.fi/api/weathercam/v1/stations/C01503/data
- Image endpoint returned HTTP 200 with JPEG content-type and ETag header:
  - https://weathercam.digitraffic.fi/C0150301.jpg

### Operational guidance from source

- Use Digitraffic-User header (non-PII app identifier).
- Default request limits are documented; weather camera images are rate limited.
- Conditional requests with If-None-Match and ETag are explicitly recommended.

## Secondary Candidate

TfL JamCams remains a viable fallback candidate:

- TfL transport-data terms grant broad usage rights including commercial/non-commercial use, with attribution and branding constraints.
- API responded successfully for JamCam place data in live checks.
- There is an app key registration flow and license obligations that require additional implementation and compliance handling.

References:
- https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service
- https://api-portal.tfl.gov.uk/
- https://api.tfl.gov.uk/Place/Type/JamCam

## Recommendation

Adopt Digitraffic as the next production candidate for publisher implementation.

Use a minimal first scope that mirrors the proven Storebaelt pattern while improving source-governance discipline:

1. Bootstrap
- Create Digitraffic procedure, systems, deployments, and datastreams for a small camera subset (for example 2 to 5 presets).

2. Publisher
- Poll image endpoints with Digitraffic-User header.
- Use HEAD or GET with If-None-Match for freshness-aware checks.
- Publish poster/image-reference observations with freshness fields:
  - imageChanged
  - firstSeenTime
  - lastSeenTime
  - lastChangedTime
  - unchangedPollCount
  - stalenessStatus
  - sourceAgeSeconds

3. Attribution and metadata
- Include source attribution and CC BY 4.0 license links in procedure/system metadata.
- Include modified-data notice where transformations occur.

4. Rate and reliability controls
- Respect published request restrictions.
- Keep poll intervals conservative.
- Add retry/backoff and explicit error telemetry.

5. Explorer UX reuse
- Reuse the existing camera card semantics:
  - poster status and freshness
  - clear distinction between still image and live/source context
  - source link actions

## Go/No-Go Checklist Before Coding

Go when all are true:

- Attribution text format is finalized and documented for Explorer and publisher metadata.
- Initial camera subset is selected and verified as in collection.
- Poll cadence is set to remain comfortably under restrictions.
- Disposition note for this source is created at project start, not after implementation.

No-go if any are true:

- License language changes away from CC BY 4.0 for applicable endpoints.
- Source indicates prohibitions conflicting with intended CSAPI demonstration use.
- APIs become unstable without viable fallback strategy.

## Immediate Next Step

Create a new publisher package using Digitraffic weather camera presets, starting with bootstrap plus a dry-run publisher for 2 to 5 cameras, then promote to active publishing after review.
