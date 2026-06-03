# Storebaelt On-Demand Live Webcam Enhancement Plan

**Date:** 2026-06-03  
**Scope:** Demand-driven live/HLS enhancement for the Storebaelt webcam publisher and Explorer UI.  
**Related background:** `Storebaelt_Webcam_Poster_Integration_Status_and_UX_Options_2026-06-03.md`

## Goal

Improve the Storebaelt webcam user experience without permanently running heavier live-video ingestion.

The baseline publisher should remain cheap and reliable: it continues publishing poster-image freshness/status observations at the normal cadence. A live/HLS mode should activate only when a client explicitly requests it, remain active only while that client renews a short lease, and shut itself off automatically when no users are watching.

## Design Principle

Use a **lease with TTL**.

A client does not permanently enable live processing. Instead, it requests a short-lived live session for one camera. While the client is actively displaying the webcam, it renews the lease. If renewals stop, the live worker expires the lease and stops HLS work for that camera.

Example lease state:

```text
cameraId -> liveUntil
```

Runtime behavior:

- `now < liveUntil`: live capture is active for that camera.
- `now >= liveUntil`: live capture is stopped for that camera.
- new lease request: extend `liveUntil`.

## Recommended Architecture

### Existing service

`storebaelt-webcams-publisher.service`

Responsibilities:

- poll poster JPEG endpoints every 5 minutes
- compute image hashes
- publish poster/status/freshness observations
- remain the durable, low-cost baseline publisher

### New companion service

`storebaelt-webcams-live.service`

Responsibilities:

- expose a small live-session control surface
- maintain in-memory leases per camera
- activate HLS discovery/frame capture only for leased cameras
- publish live status/frame-reference observations while active
- stop per-camera work when leases expire

The live service can run continuously with near-zero work while idle, or later be made socket-activated if operational simplicity permits.

## Activation Interface Options

### Option A: Small publisher-side HTTP API

Initial pragmatic interface:

```http
POST /live/storebaelt/{cameraId}/lease
Content-Type: application/json

{ "ttlSeconds": 60, "mode": "latestFrame" }
```

Response:

```json
{
  "cameraId": "storebaelt-tower",
  "liveUntil": "2026-06-03T21:10:00Z",
  "active": true,
  "mode": "latestFrame",
  "status": "starting"
}
```

Additional endpoints:

- `GET /live/storebaelt/{cameraId}/status`
- `DELETE /live/storebaelt/{cameraId}/lease` as an optional explicit stop signal

This is the fastest and clearest first implementation.

### Option B: CSAPI control stream

Longer-term, model live activation as a CSAPI control stream such as `requestLiveWebcam`.

Command fields:

- `cameraId`
- `ttlSeconds`
- `mode`: `latestFrame`, `frameEveryNSeconds`, or `playlistMetadata`
- optional `quality`

This is more standards-aligned, but it depends on Explorer and server control-stream maturity. It should be treated as a follow-on migration path after the small HTTP control surface proves the workflow.

### Option C: Direct client HLS playback after discovery

The live service discovers/validates the HLS URL and returns it to Explorer, but the browser plays the stream directly.

This can provide the most live-feeling experience, but it depends on CORS, token behavior, and player compatibility. It is useful to evaluate, but should not be the only plan.

## Live Output Options

### Preferred first output: live status plus frame-reference observations

While a lease is active, the live service should publish a lightweight observation containing:

- `cameraId`
- `liveActive`
- `liveMode`
- `leaseUntil`
- `hlsPlaylistUrl` when safely shareable
- `frameUrl` or `latestFrameUrl` when available
- `frameTime`
- `frameSha256` if a frame is fetched/generated
- `sourceLatencySeconds` when derivable
- `status`: `starting`, `live`, `stale`, `error`, or `idle`
- `errorMessage` only when needed and safe to expose

This keeps Explorer aligned with the existing observation-driven UI model.

### Alternative output: transient frame cache

If generated frame images are needed, the live service can write latest frames to a short-lived local/cache path and publish a URL to that frame.

This avoids storing image bytes in CSAPI observations, but requires an image-serving path and cache cleanup policy.

## Explorer UX Plan

Add webcam-specific controls to the deployed-system card:

1. Always show poster status:
   - latest poster image
   - last checked time
   - image changed time
   - unchanged duration
   - stale badge when threshold is exceeded

2. Add a `Start Live` control:
   - visible for Storebaelt webcam deployments
   - starts a 60 second lease for the selected camera
   - changes to `Live` or `Starting` status while active

3. Renew the lease while the user is actively viewing:
   - renew every 30 seconds for a 60 second TTL
   - stop renewing when the card is closed, route changes, or tab visibility is lost for a configured grace period

4. Show live fallback links:
   - embedded player URL
   - public Storebaelt webcam page

5. Fail gracefully:
   - if live activation fails, keep poster image visible
   - show a compact `Live unavailable` state with the player link

## Publisher Runtime Behavior

The live service should be polite and bounded:

- one worker task per active camera
- max TTL accepted per lease, for example 120 seconds
- default TTL 60 seconds
- minimum renewal interval enforced server-side
- stop HLS fetch/decode immediately after idle timeout
- do not fetch HLS for cameras without active leases
- avoid publishing unchanged live frames unless publishing heartbeat/status is intentional

Recommended default live cadence while active:

- status heartbeat every 5-10 seconds
- frame extraction every 5-15 seconds, depending on observed source behavior and CPU cost

## Data Model Additions

Create a separate live/status datastream per Storebaelt camera, or extend the existing webcam image datastream only if the result schema remains clear.

Preferred: separate output name such as `storebaeltWebcamLiveStatus`.

Candidate result fields:

- `cameraId`
- `cameraTitle`
- `liveActive`
- `liveMode`
- `leaseUntil`
- `status`
- `hlsPlaylistUrl`
- `frameUrl`
- `latestFrameUrl`
- `frameTime`
- `frameSha256`
- `sourceLatencySeconds`
- `playerUrl`
- `pageUrl`
- `errorMessage`

Keep poster-source fields in the existing `storebaeltWebcamImage` output so long-term poster freshness remains easy to understand.

## Implementation Phases

### Phase 1: Poster freshness heartbeat

- Publish heartbeat/status observations every 5 minutes, even when the poster image hash is unchanged.
- Add fields such as `imageChanged`, `firstSeenTime`, `lastChangedTime`, `lastSeenTime`, `unchangedPollCount`, and `stalenessStatus`.
- Update Explorer to separate `last checked` from `image changed`.

### Phase 2: Live source reconnaissance

- Inspect the Mediathand/Video.js player network behavior.
- Identify whether HLS playlist URLs are stable, tokenized, or browser-bound.
- Determine whether browser direct playback is viable.
- Measure bandwidth, latency, and cache behavior.

### Phase 3: Live lease service prototype

- Add `storebaelt_webcams_live_service.py` or equivalent companion module.
- Implement lease API and per-camera lease table.
- Add bounded background worker activation per camera.
- Publish live status observations with no frame extraction first.

### Phase 4: Frame or playlist integration

- Add HLS playlist discovery and validation.
- Choose either direct playlist handoff, latest-frame extraction, or transient frame cache.
- Publish live status/frame-reference observations only while leases are active.

### Phase 5: Explorer live UX

- Add `Start Live` and live status states to Storebaelt webcam cards.
- Renew leases while the card is open.
- Stop renewing when the user leaves the card.
- Render live frame/playlist when available, otherwise fall back to poster image and external player links.

### Phase 6: Operational hardening

- Add systemd unit for the live service.
- Add rate limits and max active leases.
- Add logs/metrics for active lease count, source errors, and frame extraction failures.
- Add cleanup for transient frames if used.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| HLS URLs are tokenized or unstable | Discover per lease; cache only briefly; retain external player fallback. |
| CORS blocks direct browser playback | Use server-side frame extraction or transient frame cache. |
| Live extraction is CPU/bandwidth heavy | Activate only under lease; cap concurrent cameras and frame cadence. |
| Source terms discourage heavy polling | Keep poster mode as default; use low live cadence; only fetch while user-requested. |
| Latest observation time is confused with frame capture time | Store poll/check time and frame/image change time separately. |
| Explorer leaves leases active after navigation | TTL expiration is authoritative; client stop signal is only an optimization. |

## Acceptance Criteria

- With no active Explorer webcam views, no HLS playlist or segment fetches occur.
- Opening a Storebaelt webcam card and selecting live mode activates only that camera.
- Closing the card or stopping renewals deactivates the camera after the TTL.
- Poster image and freshness status remain available even when live mode fails.
- The UI clearly distinguishes last checked time, image/frame changed time, and live activation state.
- Oracle service logs show bounded, understandable live activation and idle behavior.

## Recommendation

Proceed with Phase 1 first, because it fixes the current stale-image confusion regardless of HLS viability. Then prototype the lease service with live status only before adding frame extraction. This keeps the design honest, observable, and reversible while preserving a path to a much better webcam experience.
