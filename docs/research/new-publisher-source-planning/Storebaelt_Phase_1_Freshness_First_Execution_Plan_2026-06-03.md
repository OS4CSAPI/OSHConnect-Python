# Storebaelt Phase 1 Freshness-First Execution Plan

**Date:** 2026-06-03  
**Scope:** Recommended next implementation step for the Storebaelt webcam publisher and Explorer UI.  
**Decision:** Do the poster/freshness hardening first, and keep it separate from the later on-demand live/HLS webcam enhancement.

## Related Documents

- `Storebaelt_Webcam_Poster_Integration_Status_and_UX_Options_2026-06-03.md` explains the current poster-image integration, why unchanged images can appear stale, and the UX options for freshness/status reporting.
- `Storebaelt_On_Demand_Live_Webcam_Enhancement_Plan_2026-06-03.md` describes the later lease-based live/HLS enhancement that activates only when a client requests it and shuts down when not in use.
- `Publisher_Thumbnail_Remediation_Plan_2026-05-29.md` provides broader context for image/thumbnail handling in the publisher fleet.
- `Oracle_New_Publisher_Service_Sanity_Check_2026-05-26.md` provides deployment sanity-check context for new Oracle publisher services.

## Recommendation

Proceed with the Phase 1 poster/freshness updates now, as a contained production hardening pass. Treat the improved live/HLS webcam experience as Phase 2, beginning only after the baseline poster-source UX is truthful and useful.

Phase 1 fixes the problem currently visible in Explorer regardless of whether the HLS path later proves easy, fragile, tokenized, CORS-blocked, or CPU-heavy. It makes the current integration honest: users can see when the publisher last checked the source, when the image content last changed, and whether the camera source appears stale.

## Why Keep Phase 1 Separate from Live/HLS

### 1. The data semantics are different

Poster freshness is a durable baseline observation stream. Live/HLS mode is a transient, user-triggered enhancement. Mixing them too early risks muddying what observation timestamps mean.

Phase 1 should make these concepts explicit:

- poll/check time
- image content change time
- unchanged duration
- stale/unavailable status

Live/HLS can later add separate live activation state, frame time, lease state, and source latency.

### 2. The operational profile is different

Poster polling is cheap, predictable, and always-on. Live/HLS capture is heavier and should be demand-driven. Keeping them separate preserves a boring, reliable baseline publisher while allowing the later live worker to be bounded by leases, TTLs, rate limits, and idle shutdown.

### 3. The UI needs Phase 1 concepts either way

Even if live/HLS works well, Explorer still needs to explain poster freshness, fallback state, last check time, and stale status whenever live mode is off or unavailable. Phase 1 builds the UI vocabulary that the live enhancement will reuse.

## Phase 1 Implementation Tasks

### Publisher tasks

1. Change the Storebaelt publisher to publish heartbeat/status observations every 5 minutes, even when the poster image hash has not changed.
2. Preserve image content dedupe metadata, but do not suppress the heartbeat observation.
3. Add result fields such as:
   - `imageChanged`
   - `firstSeenTime`
   - `lastSeenTime`
   - `lastChangedTime`
   - `unchangedPollCount`
   - `stalenessStatus`
   - `sourceAgeSeconds`
4. Keep `imageSha256`, `imageUrl`, `posterUrl`, `playerUrl`, and `pageUrl` in the result payload.
5. Update the Storebaelt datastream schema to include the new fields.
6. Add focused tests for changed-image and unchanged-image cycles.
7. Verify local dry-run behavior against the public Storebaelt poster URLs.

### Explorer tasks

1. Update the deployed-system card logic for webcam/image datastreams.
2. Display:
   - latest image
   - last checked
   - image changed
   - unchanged duration
   - stale badge
   - public page link
   - embedded player link
3. Make the card distinguish between:
   - publisher alive but image unchanged
   - source stale
   - source unavailable
   - no observation yet
4. Keep the poster image visible when live mode is unavailable or not yet implemented.

### Deployment tasks

1. Deploy the publisher changes to Oracle.
2. Re-run or update bootstrap if schema changes require it.
3. Restart `storebaelt-webcams-publisher.service`.
4. Confirm service logs show heartbeat observations with zero errors.
5. Confirm Explorer displays the updated freshness state.

## Phase 1 Acceptance Criteria

- Storebaelt observations continue to arrive every 5 minutes even if the poster image bytes do not change.
- Observation payloads clearly identify whether image content changed.
- Explorer does not make a 20+ minute unchanged image look like a dead publisher.
- Explorer shows separate last-checked and image-changed times.
- Stale images are represented as a source freshness state, not as a silent failure.
- Existing poster image display remains functional.
- No HLS/video capture is introduced in Phase 1.

## Phase 2 Boundary

Do not start HLS extraction, playlist capture, generated thumbnails, or direct live-video playback as part of Phase 1.

Phase 2 should begin with the lease-based plan in `Storebaelt_On_Demand_Live_Webcam_Enhancement_Plan_2026-06-03.md` after Phase 1 is deployed and observed. That later track should use an explicit client request and TTL renewal model so heavier live capture activates only while a user is viewing the resource.

## Next Concrete Task

Implement Phase 1 as the next code task:

1. Update `publishers/storebaelt_webcams/storebaelt_webcams_publisher.py`.
2. Update `publishers/storebaelt_webcams/bootstrap_storebaelt_webcams.py`.
3. Update `tests/test_storebaelt_webcams_publisher.py`.
4. Update Explorer's deployed-system card freshness display.
5. Deploy and verify on Oracle and the live Explorer site.
