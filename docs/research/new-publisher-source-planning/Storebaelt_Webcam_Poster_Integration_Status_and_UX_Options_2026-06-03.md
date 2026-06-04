# Storebaelt Webcam Poster Integration Status and UX Options

> **Retired 2026-06-04:** The integration was removed from the public OSH demo after Storebaelt/Sund & Baelt replied that the webcam service is being shut down and cannot be used as an OGC CSAPI demonstration case. See `Storebaelt_Source_Retirement_Disposition_2026-06-04.md`.

**Date:** 2026-06-03  
**Scope:** Storebaelt public traffic/weather webcam publisher behavior, image freshness semantics, and UI/UX optimization options.

**Follow-on plan:** `Storebaelt_On_Demand_Live_Webcam_Enhancement_Plan_2026-06-03.md` describes the recommended lease-based design for demand-driven live/HLS mode.

## Current Integration Behavior

The Storebaelt integration is intentionally conservative: it publishes references to the two stable poster JPEG URLs, not frames pulled from the HLS live video stream.

For each 5 minute publisher cycle, the runtime:

1. Fetches the poster JPEG bytes from:
   - `https://stream.sob.m-dn.net/res/sb1-live.jpg`
   - `https://stream.sob.m-dn.net/res/sb2-live.jpg`
2. Computes a SHA-256 hash of the JPEG bytes.
3. Uses the current poll time as `phenomenonTime`.
4. Publishes a heartbeat observation with freshness fields even when the image hash is unchanged.

The first implementation skipped duplicate hashes, but Phase 1 changed this behavior. The latest observation now represents the latest successful source check. The image-content freshness is represented separately by fields such as `imageChanged`, `lastSeenTime`, `lastChangedTime`, `sourceAgeSeconds`, and `stalenessStatus`.

This distinction matters: the observation can be recent while the poster image itself is old. A recent observation with `imageChanged: false` means the publisher is alive and checked the source, not that Storebaelt produced a new camera frame.

## Why It Works This Way

The poster JPEG endpoint has weak capture metadata. During deployment, the HTTP `Last-Modified` header was observed to be stale from 2022, so it cannot be trusted as the camera capture time.

Hashing the actual image bytes is currently the most reliable way to know whether the still image changed.

The current integration is therefore best described as a **latest available poster image reference publisher**, not a true live webcam frame publisher.

If the image is more than 20 minutes old, one of these is probably true:

- Storebaelt's poster JPEG endpoint only refreshes intermittently.
- The camera/player backend is paused, cached, or only updating the HLS stream while leaving poster JPEGs stale.
- The browser/player may show fresher HLS video, but the poster JPEG resource currently ingested by OSHConnect has not changed.

This is not necessarily a publisher failure. It means the current source surface is stable but not guaranteed live.

## Poster JPEG vs Live HLS Player Finding

During follow-up validation, the Explorer card showed a bright daylight still image while the Storebaelt embedded player showed a dark nighttime live view. This was initially confusing because both surfaces appear to represent the same webcam.

The cause is that Storebaelt exposes two different media surfaces:

- Poster JPEG used by OSHConnect/Explorer:
   - `https://stream.sob.m-dn.net/res/sb1-live.jpg`
   - `https://stream.sob.m-dn.net/res/sb2-live.jpg`
- Embedded player pages:
   - `https://player.sob.m-dn.net/sb1-live.html`
   - `https://player.sob.m-dn.net/sb2-live.html`

The player page uses the JPEG only as the HTML video poster image. The actual live video source is HLS:

```html
<video poster="//stream.sob.m-dn.net/res/sb1-live.jpg">
   <source src="//stream.sob.m-dn.net/live/sb1/index.m3u8" type="application/vnd.apple.mpegurl">
</video>
```

Observed HLS playlist paths:

- `https://stream.sob.m-dn.net/live/sb1/index.m3u8`
- likely counterpart: `https://stream.sob.m-dn.net/live/sb2/index.m3u8`

This means the poster JPEG can be stale while the HLS stream is current. In the observed case, the poster hash matched the published CSAPI observation exactly, so OSHConnect and Explorer were faithfully showing the current poster resource. The mismatch was upstream: Storebaelt's poster JPEG was not representative of the live video stream at that moment.

### UX Implication

The UI must not label the poster image as simply "live" without qualification. It should communicate that this is the latest checked poster image and separately expose the embedded/live player path. The current Explorer heartbeat strip is the right direction because it says things such as:

```text
Checked 11m ago; image unchanged for 20m
STALE
```

That statement is about the poster JPEG, not the HLS stream. A user may still open the player and see current live video.

### Engineering Implication

The poster publisher should remain the durable baseline because it is cheap, stable, and CSAPI-observation-friendly. But it should be treated as an image-reference/status feed, not a video-live feed. Any UI or downstream client that wants current visual reality must use the HLS/player surface or a derived on-demand live snapshot.

## Optimization Options

### 1. Add Freshness and Status Fields

Add explicit freshness fields to Storebaelt webcam observations, for example:

- `sourceAgeSeconds`
- `imageChanged`
- `firstSeenTime`
- `lastSeenTime`
- `lastChangedTime`
- `unchangedPollCount`
- `stalenessStatus`: `fresh`, `unchanged`, `stale`, or `unavailable`
- `playerUrl`
- `pageUrl`

This would let the UI say "image unchanged for 22 min" instead of forcing users to infer that state from the latest observation timestamp.

### 2. Publish Heartbeat Observations

Instead of skipping unchanged hashes entirely, publish a lightweight observation every cycle with the same image URL and hash but `imageChanged: false`.

Benefits:

- The UI always shows that the publisher is alive.
- Users can distinguish "service polling successfully but camera unchanged" from "publisher stopped."
- The latest observation can represent latest poll/check time, while separate fields represent image content freshness.

Tradeoffs:

- More observations are stored.
- The UI must distinguish poll time from image-change time, otherwise latest observation time could be mistaken for latest camera frame time.

For the current demo UX, heartbeat observations are the highest-value baseline improvement and have been implemented for Storebaelt. The remaining UX challenge is making the poster-vs-HLS distinction obvious enough that users understand why a stale poster can coexist with a live player.

### 3. Keep Dedupe but Expose Service Health Separately

The publisher could keep the current clean observation stream and expose health/status elsewhere.

This preserves observation sparsity, but the Explorer is already observation-oriented, so this option may be less visible and less useful to users unless paired with additional UI work.

### 4. Investigate HLS / Media Playlist Ingestion

The embedded Mediathand/Video.js player uses live HLS streams. A deeper integration could ingest or expose one of these instead:

- current HLS playlist URL
- latest HLS segment URL
- periodic frame extraction from the stream
- generated thumbnails from the stream

Benefits:

- More genuinely live webcam behavior.
- Better fit for a resource users perceive as a live video feed.

Tradeoffs:

- More brittle than stable poster JPEG URLs.
- Higher bandwidth and CPU cost.
- Possible CORS, token, caching, or player-provider changes.
- Requires a policy decision about whether OSHConnect stores derived images or only publishes references.

This should be treated as a second-phase enhancement, not the default first fix.

If implemented, live/HLS ingestion should be demand-driven. The publisher should not continuously pull live video while no client is viewing the resource. The recommended pattern is a short-lived lease with TTL: Explorer requests live mode for a specific camera, renews the lease while the webcam card is open, and lets the live worker deactivate automatically when renewals stop. See `Storebaelt_On_Demand_Live_Webcam_Enhancement_Plan_2026-06-03.md` for the detailed plan.

### 5. Improve Explorer UI for Webcam Deployments

For Storebaelt webcam deployments, the Explorer card should show:

- latest poster image, explicitly treated as poster/still imagery rather than guaranteed live video
- "last checked" time
- "image changed" time
- "unchanged for X min"
- a stale badge beyond a threshold such as 15 or 30 minutes
- link to the embedded live player
- link to the public Storebaelt webcam page

This makes the user experience honest and robust even when the poster endpoint stalls.

## Recommended Path

Recommended implementation order:

1. Keep the publisher heartbeat/status observations every 5 minutes.
2. Preserve `imageSha256`, `imageChanged`, `firstSeenTime`, `lastChangedTime`, and latest poll/check time in the result payload.
3. Keep Explorer's deployed-system card focused on the distinction between poster check time and image-change time.
4. Label/link the embedded player as the actual live video path when present.
5. Avoid implying the poster JPEG is live when `stalenessStatus` is `unchanged` or `stale`.
6. Research HLS extraction only after the poster-source UX is truthful and useful.
7. For live/HLS mode, follow the lease-based on-demand plan so heavier capture work activates only when a client requests it and shuts down when not in use.

This gives a better user experience without prematurely building a fragile video ingestion pipeline.
