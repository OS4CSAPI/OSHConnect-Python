# Storebaelt Phase 2A Live Playback Reconnaissance

**Date:** 2026-06-03  
**Scope:** Validate the cheapest live-video paths before building backend HLS lease/frame extraction services.

## Summary

The Storebaelt player and HLS source are usable enough that Explorer should try a direct live UX before any server-side frame extraction work.

Recommended next implementation path:

1. Add an Explorer `Open Live Video` modal/panel that embeds the Storebaelt player page in an iframe.
2. Keep the current external `Open Live Video` link as fallback.
3. Treat direct HLS playback with `hls.js` as the next option if we want a fully native in-card player.
4. Defer backend HLS frame extraction until direct iframe/player and browser HLS options are proven insufficient.

## Tested Source Surfaces

| Camera | Player page | HLS playlist | Poster JPEG |
| --- | --- | --- | --- |
| Storebaelt Tower | `https://player.sob.m-dn.net/sb1-live.html` | `https://stream.sob.m-dn.net/live/sb1/index.m3u8` | `https://stream.sob.m-dn.net/res/sb1-live.jpg` |
| Sprogo | `https://player.sob.m-dn.net/sb2-live.html` | `https://stream.sob.m-dn.net/live/sb2/index.m3u8` | `https://stream.sob.m-dn.net/res/sb2-live.jpg` |

Player page source confirms that the poster image and live stream are separate resources:

```html
<video poster="//stream.sob.m-dn.net/res/sb1-live.jpg">
  <source src="//stream.sob.m-dn.net/live/sb1/index.m3u8" type="application/vnd.apple.mpegurl">
</video>
```

The same structure exists for `sb2`.

## Header and Browser Findings

### Player pages

Observed headers for `sb1-live.html` and `sb2-live.html`:

- `200 OK`
- `Content-Type: text/html; charset=UTF-8`
- `Server: Netlify`
- No `X-Frame-Options` header observed.
- No blocking `Content-Security-Policy` frame directive observed in the header probe.
- JavaScript `fetch()` from `https://ogc-csapi-explorer.pages.dev` is blocked by CORS because the player page does not send `Access-Control-Allow-Origin`.
- Embedding as an iframe from the Explorer origin loaded successfully in browser testing.

Interpretation: Explorer should not fetch or parse the player page from browser code, but it can likely embed or open it as a live-video surface.

### HLS playlists

Observed headers for `index.m3u8`:

- `200 OK`
- `Content-Type: application/vnd.apple.mpegurl`
- `Cache-Control: public, max-age=1`
- `Server: MDN`

Browser-origin `fetch()` from `https://ogc-csapi-explorer.pages.dev` succeeded for:

- master playlist
- variant playlist
- `init.mp4`
- `.m4s` media segments

Browser fetch result type was `cors`, which means the stream resources are readable by browser-side HLS code.

### Native browser playback

Chromium reported no native support for `application/vnd.apple.mpegurl` / HLS through `video.canPlayType(...)`.

Interpretation: a plain `<video src="...index.m3u8">` should not be relied on for desktop Chromium/Edge. Direct in-card HLS playback would require `hls.js` or equivalent Media Source Extensions support.

## Playlist Shape

The HLS master playlists advertise multiple variants, including:

- 288x162 low-bandwidth variants
- 416x234
- 640x360
- 1024x576
- 1280x720

The first variant playlist inspected contained:

- `#EXT-X-TARGETDURATION:6`
- `#EXT-X-PROGRAM-DATE-TIME`, for example `2026-06-03T22:07:40.239Z`
- `#EXT-X-MAP:URI="init.mp4"`
- 6-second `.m4s` segments such as `33097.m4s`

Example segment headers:

- `200 OK`
- `Content-Type: video/iso.segment`
- `Cache-Control: public, max-age=120`

## Explorer Dependency Check

`demo/package.json` does not currently include `hls.js` or another HLS playback library.

That means:

- iframe/player modal is the lowest-risk, zero-dependency live UX;
- direct HLS in a native card player requires adding a new dependency and player lifecycle code;
- server-side extraction is not justified as the immediate next step.

## Recommended Implementation Decision

### First implementation: iframe/player modal

Add a webcam live-video modal in Explorer:

- Triggered by the existing `Open Live Video` action.
- Uses `cameraPlayerUrl` as the iframe source.
- Keeps `target="_blank"` fallback behavior available.
- Leaves poster freshness visible behind or below the live player.
- Labels the iframe/live view as provider live video, separate from CSAPI poster status.

Rationale:

- Uses the provider's intended player.
- Avoids adding `hls.js` immediately.
- Avoids backend compute and bandwidth.
- Directly answers the user confusion: the live video can be opened without implying the poster is live.

### Second implementation option: direct HLS with `hls.js`

If iframe UX is not acceptable, add `hls.js` and play `hlsPlaylistUrl` directly in the card or modal.

This is technically plausible because playlists and segments are CORS-readable from Explorer's origin. It would require:

- adding `hls.js` to `demo/package.json`;
- player lifecycle handling in Vue;
- choosing quality/ABR defaults;
- error handling and fallback to player page;
- possibly adding `hlsPlaylistUrl` to the Storebaelt poster observation payload or deriving it client-side from known camera IDs.

### Defer: backend frame extraction

Server-side HLS frame extraction should remain deferred unless:

- iframe embedding fails operationally;
- direct HLS playback with `hls.js` fails;
- CSAPI-native live frame observations become an explicit requirement;
- we need server-side snapshots for clients that cannot play video.

## Recommended Plan Update

Phase 2 should be split into:

- **Phase 2A:** Browser/player reconnaissance and Explorer iframe live modal.
- **Phase 2B:** Optional direct HLS prototype with `hls.js`.
- **Phase 3:** Lease/live status service, without frame extraction by default.
- **Phase 4:** Backend frame extraction only if the direct live paths are insufficient.

This keeps the live path useful, understandable, and low-cost while preserving the lease architecture for later operational control.
