# Storebaelt On-Demand Live Webcam Enhancement Plan

**Date:** 2026-06-03  
**Scope:** Demand-driven live/HLS enhancement for the Storebaelt webcam publisher and Explorer UI.  
**Related background:** `Storebaelt_Webcam_Poster_Integration_Status_and_UX_Options_2026-06-03.md`

## Goal

Improve the Storebaelt webcam user experience without permanently running heavier live-video ingestion.

The baseline publisher should remain cheap and reliable: it continues publishing poster-image freshness/status observations at the normal cadence. A live/HLS mode should activate only when a client explicitly requests it, remain active only while that client renews a short lease, and shut itself off automatically when no users are watching.

## Key Source Finding: Poster Is Not the Live Feed

Follow-up validation showed that Storebaelt's poster JPEG and embedded live video can diverge materially. Explorer displayed a bright daylight still image while the Storebaelt embedded player showed a dark nighttime live view.

This is expected once the player HTML is inspected:

```html
<video poster="//stream.sob.m-dn.net/res/sb1-live.jpg">
   <source src="//stream.sob.m-dn.net/live/sb1/index.m3u8" type="application/vnd.apple.mpegurl">
</video>
```

The poster JPEG is a separate still asset. It is not guaranteed to be a recent frame from the HLS stream. Therefore, Phase 2 should not attempt to make the poster pipeline look more "live" by presentation alone. It should explicitly add a live-video path alongside the poster status path.

Known source surfaces:

| Camera | Poster JPEG | Player page | HLS playlist |
| --- | --- | --- | --- |
| Storebaelt Tower | `https://stream.sob.m-dn.net/res/sb1-live.jpg` | `https://player.sob.m-dn.net/sb1-live.html` | `https://stream.sob.m-dn.net/live/sb1/index.m3u8` |
| Sprogo | `https://stream.sob.m-dn.net/res/sb2-live.jpg` | `https://player.sob.m-dn.net/sb2-live.html` | `https://stream.sob.m-dn.net/live/sb2/index.m3u8` |

The HLS URLs should still be rediscovered/validated during implementation rather than hard-coded forever, because the provider can change player internals.

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

### Option D: Embedded player handoff as the immediate live path

The Explorer can treat `playerUrl` as the first reliable live view and open it in a new tab, panel, or modal iframe where browser/provider policy allows.

Benefits:

- Fastest way to give users the actual live picture.
- Avoids server-side HLS fetching, decoding, and frame caching.
- Uses the provider's intended playback surface.

Limitations:

- Does not produce CSAPI observations for live frames.
- May have iframe or cross-origin restrictions depending on player headers.
- Provides less integrated telemetry than a live lease/status service.

Recommendation: use this as the immediate UX fallback and as a baseline comparison while building the lease-based live service.

## Live Output Options

### Immediate output: poster status plus player/HLS references

Before adding frame extraction, the existing poster observation should carry enough reference metadata for clients to explain the source split:

- `posterUrl`
- `playerUrl`
- `pageUrl`
- optional future `hlsPlaylistUrl` after validation
- `stalenessStatus` for the poster asset
- `lastSeenTime` for latest poster check
- `lastChangedTime` for latest poster image change

This lets Explorer say, in effect: "The poster image is stale, but live video may still be available through the player."

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
- Confirm current HLS playlist paths:
   - `https://stream.sob.m-dn.net/live/sb1/index.m3u8`
   - `https://stream.sob.m-dn.net/live/sb2/index.m3u8`
- Identify whether HLS playlist URLs are stable, tokenized, or browser-bound.
- Determine whether browser direct playback is viable from Explorer's Cloudflare Pages origin.
- Determine whether the provider player page can be embedded safely, or whether it must open in a separate tab.
- Compare poster freshness against HLS segment freshness so the UI can avoid implying that a stale poster means stale live video.
- Measure bandwidth, latency, cache behavior, and segment cadence.
- Decide whether Phase 3 should expose only lease/live status first or also return a validated `hlsPlaylistUrl`.

### Phase 3: Live lease service prototype

- Add `storebaelt_webcams_live_service.py` or equivalent companion module.
- Implement lease API and per-camera lease table.
- Add bounded background worker activation per camera.
- Publish live status observations with no frame extraction first.
- During an active lease, validate the playlist URL and publish status such as `starting`, `live`, `playlist-unavailable`, or `blocked`.
- Do not extract frames in this phase unless direct HLS/player handoff proves unusable.

### Phase 4: Frame or playlist integration

- Add HLS playlist discovery and validation.
- Choose either direct playlist handoff, latest-frame extraction, or transient frame cache.
- Publish live status/frame-reference observations only while leases are active.

### Phase 5: Explorer live UX

- Add `Start Live` and live status states to Storebaelt webcam cards.
- Renew leases while the card is open.
- Stop renewing when the user leaves the card.
- Render live player/playlist when available, otherwise fall back to poster image and external player links.
- Keep poster status visible even during live mode so users understand the still-image source separately from the live stream.
- Use copy that distinguishes "poster image stale" from "live video unavailable."

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
| Poster image appears stale while live video is current | Treat poster status and live HLS status as separate surfaces; keep player/HLS link visible. |
| Hard-coded HLS URL changes upstream | Discover/validate from player page during Phase 2 or at live lease start. |

## Acceptance Criteria

- With no active Explorer webcam views, no HLS playlist or segment fetches occur.
- Opening a Storebaelt webcam card and selecting live mode activates only that camera.
- Closing the card or stopping renewals deactivates the camera after the TTL.
- Poster image and freshness status remain available even when live mode fails.
- The UI clearly distinguishes last checked time, image/frame changed time, and live activation state.
- The UI clearly distinguishes poster staleness from live video availability.
- If the poster JPEG is stale but the HLS/player is live, the card does not imply that the camera itself is stale.
- Oracle service logs show bounded, understandable live activation and idle behavior.

## Recommendation

Phase 1 is now the correct baseline: it makes poster freshness observable and prevents users from mistaking publisher silence for source silence.

For Phase 2, prioritize direct validation of the HLS/player path before building frame extraction. The immediate user need is to reach the real live view when the poster is stale. Frame extraction should remain a later choice, used only if direct player/HLS handoff cannot provide an acceptable Explorer experience or if CSAPI-native live frame observations become a hard requirement.

Then prototype the lease service with live status only before adding frame extraction. This keeps the design honest, observable, and reversible while preserving a path to a much better webcam experience.
