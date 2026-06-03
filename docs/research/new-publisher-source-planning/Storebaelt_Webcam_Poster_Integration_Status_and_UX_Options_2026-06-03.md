# Storebaelt Webcam Poster Integration Status and UX Options

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
4. Publishes an observation only if the image hash is new for that running service process.

That final dedupe step explains why the Explorer UI can show a latest image observation that is 20+ minutes old. If Storebaelt's poster JPEG endpoint keeps serving the exact same image bytes, the publisher treats it as unchanged and skips publishing duplicates.

This is deliberate data hygiene. It avoids filling CSAPI with repeated observations that point to the same still image while implying that new image content was captured.

## Why It Works This Way

The poster JPEG endpoint has weak capture metadata. During deployment, the HTTP `Last-Modified` header was observed to be stale from 2022, so it cannot be trusted as the camera capture time.

Hashing the actual image bytes is currently the most reliable way to know whether the still image changed.

The current integration is therefore best described as a **latest available poster image reference publisher**, not a true live webcam frame publisher.

If the image is more than 20 minutes old, one of these is probably true:

- Storebaelt's poster JPEG endpoint only refreshes intermittently.
- The camera/player backend is paused, cached, or only updating the HLS stream while leaving poster JPEGs stale.
- The browser/player may show fresher HLS video, but the poster JPEG resource currently ingested by OSHConnect has not changed.

This is not necessarily a publisher failure. It means the current source surface is stable but not guaranteed live.

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

For the current demo UX, heartbeat observations are likely the highest-value improvement.

### 3. Keep Dedupe but Expose Service Health Separately

The publisher could keep the current clean observation stream and expose health/status elsewhere.

This preserves observation sparsity, but the Explorer is already observation-oriented, so this option may be less visible and less useful to users unless paired with additional UI work.

### 4. Investigate HLS / Media Playlist Ingestion

The embedded Mediathand/Video.js player likely uses live HLS streams. A deeper integration could ingest one of these instead:

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

- latest poster image
- "last checked" time
- "image changed" time
- "unchanged for X min"
- a stale badge beyond a threshold such as 15 or 30 minutes
- link to the embedded live player
- link to the public Storebaelt webcam page

This makes the user experience honest and robust even when the poster endpoint stalls.

## Recommended Path

Recommended implementation order:

1. Change the publisher to publish heartbeat/status observations every 5 minutes.
2. Preserve `imageSha256`, `imageChanged`, `firstSeenTime`, `lastChangedTime`, and latest poll/check time in the result payload.
3. Update the datastream schema to include those fields.
4. Update Explorer's deployed-system card to display "last checked" separately from "image changed."
5. Add a stale badge when the same image has persisted longer than a threshold.
6. Research HLS extraction only after the poster-source UX is truthful and useful.
7. For live/HLS mode, follow the lease-based on-demand plan so heavier capture work activates only when a client requests it and shuts down when not in use.

This gives a better user experience without prematurely building a fragile video ingestion pipeline.
