# CSAPI-Go Server Integration Report

**Date:** 2026-04-17
**Status:** Complete
**Scope:** Dual-publish the entire OS4CSAPI publisher fleet to the connected-systems-go server

---

## 1  Executive Summary

OS4CSAPI has deployed a second Connected Systems API server — [connected-systems-go](https://github.com/OS4CSAPI/connected-systems-go) — alongside the existing OSH SensorHub. This report documents the integration effort: server architecture, behavioral differences discovered during live testing, workarounds applied, publishers migrated to date, and the plan to complete the remaining fleet.

**Final state:** 10 of 10 publishers dual-publishing on the Go server. 37 systems, 58 datastreams, 11 procedures, 58 deployments bootstrapped. All services running as systemd units with observations flowing. 10 GitHub issues filed against the Go server covering bugs, behavioral differences, and missing features. BuoyCAM image URL fix deployed (absolute URLs via `BUOYCAM_CACHE_BASE_URL` env var).

---

## 2  Server Architecture

### 2.1  Deployment Topology

| Component | SensorHub | connected-systems-go |
|---|---|---|
| **URL** | `https://129-80-248-53.sslip.io/sensorhub/api` | `https://129-80-248-53.sslip.io/csapi-go/` |
| **Host** | Oracle Cloud VM (same host) | Oracle Cloud VM (same host) |
| **Port** | 8181 (behind Caddy) | 8282 (behind Caddy) |
| **Runtime** | Java / OSH SensorHub | Go binary / Docker |
| **Storage** | H2 embedded DB | PostgreSQL + PostGIS |
| **Auth** | HTTP Basic (`os4csapi` / `ogc134mm`) | None (tolerates auth headers) |
| **IDs** | Short numeric (e.g., `0520`) | UUIDs (e.g., `a1b2c3d4-...`) |
| **Reverse proxy** | Caddy route `/sensorhub/*` | Caddy route `/csapi-go/*` |
| **Explorer preset** | "OSH SensorHub" | "CSAPI-Go" |

### 2.2  Docker Deployment

The Go server runs as a Docker container on the Oracle VM:

```
docker run -d \
  --name csapi-go \
  --restart unless-stopped \
  -p 8282:8282 \
  -e DATABASE_URL=postgres://... \
  connected-systems-go:latest
```

Caddy reverse-proxies `/csapi-go/*` to `localhost:8282`.

### 2.3  Explorer Integration

The [ogc-csapi-explorer](https://github.com/OS4CSAPI/ogc-csapi-explorer) demo app includes:

- **CF Pages proxy:** `demo/functions/api/csapi-go/[[path]].ts` → forwards to Go server
- **Vite dev proxy:** `demo/vite.config.ts` → local dev routing
- **Server selector:** "CSAPI-Go" option on the connection page (no auth required)

---

## 3  Behavioral Differences Discovered

During live integration testing, we identified 10+ differences between connected-systems-go and OSH SensorHub. These have been filed as GitHub issues on [OS4CSAPI/connected-systems-go](https://github.com/OS4CSAPI/connected-systems-go/issues).

### 3.1  Bugs (P1–P2)

#### Issue #1 — Datastream `uid` empty-string unique constraint violation

- **GitHub:** [OS4CSAPI/connected-systems-go#1](https://github.com/OS4CSAPI/connected-systems-go/issues/1)
- **Severity:** P1-Critical
- **Problem:** POST a datastream without `uid` → server stores `uid = ""`. Second POST (also without `uid`) fails with a PostgreSQL unique constraint violation.
- **Workaround:** Always provide an explicit `uid` on datastream creation.
- **Code change:** All `ensure_datastream()` calls now include `"uid": "urn:os4csapi:datastream:..."`.

#### Issue #2 — DELETE does not cascade FK constraints

- **GitHub:** [OS4CSAPI/connected-systems-go#2](https://github.com/OS4CSAPI/connected-systems-go/issues/2)
- **Severity:** P1-Critical
- **Problem:** DELETE on a parent resource (deployment, system) fails with a raw PostgreSQL FK violation instead of cascading or returning a structured `409` error.
- **Workaround:** Delete child resources bottom-up (observations → datastreams → systems → deployments).
- **Impact:** Bootstrap `--clean` operations must be carefully ordered.

### 3.2  Research Spikes (P3–P4)

#### Issue #3 — Time fields must be ISO 8601 strings

- **GitHub:** [OS4CSAPI/connected-systems-go#3](https://github.com/OS4CSAPI/connected-systems-go/issues/3)
- **Severity:** P3-Minor
- **Comparison:** SensorHub accepts both numeric epoch values and ISO strings. Go server rejects numerics.
- **Workaround:** Publishers detect `"csapi-go"` in the base URL and coerce time fields to strings.
- **Code change (USGS EQ):**
  ```python
  self._coerce_time_to_str = "csapi-go" in self._base_url
  # In _post_observation():
  if self._coerce_time_to_str:
      for key in ("eventTime", "updatedTime"):
          if key in r and not isinstance(r[key], str):
              r[key] = str(r[key])
  ```

#### Issue #4 — Rejects `"NaN"` strings for numeric fields

- **GitHub:** [OS4CSAPI/connected-systems-go#4](https://github.com/OS4CSAPI/connected-systems-go/issues/4)
- **Severity:** P3-Minor
- **Comparison:** SensorHub accepts `"NaN"` as a Gson-compatible token. Go server rejects it for schema-declared numeric fields.
- **Workaround:** Publishers detect the Go server and replace `"NaN"` with `0.0`.
- **Code change (OpenSky):**
  ```python
  self._is_go_server = "csapi-go" in self._base_url
  # In _post_observation():
  if self._is_go_server:
      for key, val in r.items():
          if val == "NaN":
              r[key] = 0.0
  ```
- **Trade-off:** `0.0` is semantically different from "no data" — for altitude, 0 means sea level.

#### Issue #5 — Strict schema validation (all declared fields required)

- **GitHub:** [OS4CSAPI/connected-systems-go#5](https://github.com/OS4CSAPI/connected-systems-go/issues/5)
- **Severity:** P3-Minor
- **Comparison:** SensorHub accepts observations with a subset of schema-declared fields. Go server requires ALL fields present.
- **Workaround:** Publishers include every declared field in every observation (e.g., duplicating `resultTime` as `result.timestamp`).
- **Code change (OpenSky):** Keep `timestamp` field in the observation result even though it duplicates `resultTime`.

#### Issue #6 — Returns `@link` objects only, not flat `@id` strings

- **GitHub:** [OS4CSAPI/connected-systems-go#6](https://github.com/OS4CSAPI/connected-systems-go/issues/6)
- **Severity:** P4-Informational
- **Comparison:** SensorHub returns `"system@id": "0520"`. Go server returns `"system@link": { "href": "systems/<uuid>" }`.
- **Impact:** Broke the Explorer's map view (0 datastreams shown) and the library's parent-system resolution.
- **Workaround (Explorer):** `extractSystemId()` helper with `system@link.href` fallback. Pushed as commit `2f0869a`.
- **Workaround (Library):** `parseBaseStream()` in `part2.ts` checks `system@link.href` → `system@id` chain. Filed as [ogc-client-CSAPI_2#166](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/issues/166).

### 3.3  Additional Behavioral Differences (Discovered During Fleet Migration)

These were discovered during the full fleet migration. Key items have since been filed as GitHub issues.

#### Unique constraint on datastream `unique_identifier` (global scope)

- **Severity:** P2-Major
- **Problem:** PostgreSQL `idx_datastreams_unique_identifier` enforces global uniqueness across ALL datastreams, not just within a system. Multi-station publishers initially shared one UID template (e.g., `urn:os4csapi:datastream:nws:nwsSurfaceObs:v1`) for all stations — the second station's datastream creation failed.
- **Workaround:** All multi-station publishers now generate per-station UIDs: `urn:os4csapi:datastream:nws:{station_id}:nwsSurfaceObs:v1`.
- **Files changed:** `bootstrap_nws.py`, `bootstrap_ndbc.py`, `bootstrap_coops.py`, `bootstrap_aviation_wx.py`, `bootstrap_usgs_water.py`, `bootstrap_usgs_nims.py`.
- **Note:** Related to Issue #1 (UID handling). Not filed as a separate issue.

#### `?uid=` query parameter ignored

- **GitHub:** [OS4CSAPI/connected-systems-go#7](https://github.com/OS4CSAPI/connected-systems-go/issues/7)
- **Severity:** P2-Major
- **Problem:** `GET /systems?uid=urn:os4csapi:...` returns ALL systems (unfiltered) instead of the matching one. Combined with the default pagination limit of 10, `find_by_uid()` missed resources beyond the first page.
- **Workaround:** `find_by_uid()` now appends `&limit=1000` to all queries and matches client-side.
- **File changed:** `bootstrap_helpers.py`.

#### Default pagination limit too low

- **GitHub:** [OS4CSAPI/connected-systems-go#9](https://github.com/OS4CSAPI/connected-systems-go/issues/9)
- **Severity:** P2-Major
- **Problem:** Go server defaults to `limit=10` for all collection endpoints. With 37 systems, 58 datastreams, and 58 deployments, default queries miss the majority of resources. SensorHub defaults to 100.
- **Workaround:** All client code appends explicit `&limit=100` or `&limit=1000` to queries.
- **Impact:** Affects Explorer UI (map shows only 10 of 37 systems), bootstrap scripts, and library consumers.

#### `/deployments` only returns top-level deployments

- **GitHub:** [OS4CSAPI/connected-systems-go#8](https://github.com/OS4CSAPI/connected-systems-go/issues/8)
- **Severity:** P3-Minor
- **Problem:** `GET /deployments` does not include sub-deployments in results. Sub-deployments are only accessible via `GET /deployments/{parent_id}/subdeployments`.
- **Workaround:** `ensure_deployment()` now searches `deployments/{parent_id}/subdeployments` when `parent_id` is provided.
- **File changed:** `bootstrap_helpers.py`.

#### Strict result schema validation (timestamp required)

- **Severity:** P3-Minor (extends Issue #5)
- **Problem:** Go server validates that observation results contain ALL fields defined in the datastream schema, including `timestamp`. Publishers were popping `timestamp` from results (SensorHub auto-fills it from `phenomenonTime`), causing `result.timestamp is required by datastream schema` errors.
- **Workaround:** All publishers now re-add `timestamp` from `phenomenonTime` when targeting Go server.
- **Files changed:** All 8 publisher files.
- **Note:** Extension of Issue #5. Not filed as a separate issue.

#### SensorML `documents` array silently dropped

- **GitHub:** [OS4CSAPI/connected-systems-go#10](https://github.com/OS4CSAPI/connected-systems-go/issues/10)
- **Severity:** P2-Major
- **Problem:** The Go server silently drops the `documents` array from SensorML on ingest or output. Querying `GET /systems?resultFormat=sml` returns `identifiers`, `classifiers`, `contacts`, `position` — but NO `documents`. Publishers send `documents` with photo URLs, thumbnails, and documentation links, but they are lost.
- **Impact:** System thumbnails broken in the Explorer (`extractSmlMedia()` reads `sml.documents`). Any media links, datasheets, or documentation URLs attached to systems are inaccessible.
- **Workaround:** None available (requires Go server code fix). Explorer shows blank thumbnails for all Go server systems.
- **Verification:** `GET /systems?resultFormat=sml` on Go server — response has no `documents` field. Same query on SensorHub returns full `documents` array with photo URLs.

### 3.4  Full Behavioral Comparison

| Behavior | SensorHub | connected-systems-go |
|---|---|---|
| Collection key for geo-resources | `items` | `features` (GeoJSON) |
| Collection key for datastreams | `items` | `items` |
| ID format | Short numeric | UUID |
| Auth requirement | Required (HTTP Basic) | None (headers tolerated) |
| Datastream UID on create | Optional (auto-generated) | Effectively required (see #1) |
| Datastream UID scope | Per-system | Global unique constraint |
| `?uid=` filter parameter | Supported | Ignored (returns all) — #7 |
| Default pagination limit | 100 | 10 — #9 |
| `/deployments` listing | All (flat) | Top-level only — #8 |
| `result.timestamp` field | Auto-filled from phenomenonTime | Required in result body |
| SensorML `documents` array | Preserved on ingest/output | Silently dropped — #10 |

---

## 4  Code Changes Applied

### 4.1  Shared Infrastructure — `bootstrap_helpers.py`

| Change | Detail | Commit |
|---|---|---|
| GeoJSON support | `find_by_uid()` checks both `items` and `features` keys | `e022ef2` |
| `OSH_BASE_URL` | `get_config()` reads `OSH_BASE_URL` env var as server URL fallback | `906ae33` |
| Pagination fix | `find_by_uid()` appends `&limit=1000` to all queries | `92f584b` |
| Subdeployment search | `ensure_deployment()` searches `deployments/{parent_id}/subdeployments` when `parent_id` set | `3a02268` |

### 4.2  USGS Earthquake Publisher

**Files changed:** `bootstrap_usgs_eq.py`, `usgs_eq_publisher.py`

| Change | Detail |
|---|---|
| `uid` on datastream | Added to bootstrap: `"uid": "urn:os4csapi:datastream:usgs-eq-feed:earthquakeEvent:v1"` |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var to target Go server |
| Time coercion | `_coerce_time_to_str` flag — converts `eventTime`/`updatedTime` to strings when targeting Go |

**Systemd services:**
- `usgs-eq-publisher.service` → SensorHub
- `usgs-eq-publisher-go.service` → Go server (env: `OSH_BASE_URL=https://129-80-248-53.sslip.io/csapi-go`)

**Confirmed:** 300 published, 0 errors per cycle on both servers.

### 4.3  OpenSky ADS-B Publisher

**Files changed:** `bootstrap_opensky.py`, `opensky_publisher.py`

| Change | Detail |
|---|---|
| `uid` on datastream | Added to bootstrap: `"uid": "urn:os4csapi:datastream:opensky-feed:adsbState:v1"` |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var |
| `_is_go_server` flag | Detects Go server from URL |
| NaN → 0.0 | Replaces `"NaN"` strings with `0.0` for numeric fields |
| Keep `timestamp` field | Retains the field in observation results (Go requires all schema fields) |

**Systemd services:**
- `opensky-publisher.service` → SensorHub
- `opensky-publisher-go.service` → Go server

**Confirmed:** ~170 published, 0 errors per cycle on both servers.

### 4.4  ISS Publisher

**Files created:** `publishers/iss/bootstrap_iss.py` (new)
**Files changed:** `publishers/iss/iss_publisher.py`

| Change | Detail |
|---|---|
| Bootstrap script | Created `bootstrap_iss.py` using `bootstrap_helpers.py` — 2 systems (position + track), 2 datastreams, 2 procedures, 1 deployment |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var |
| `_is_go_server` flag | Detects Go server from URL |
| Timestamp in result | Re-adds `timestamp` from `phenomenonTime` when missing |

### 4.5  NWS Surface Observations Publisher

**Files changed:** `bootstrap_nws.py`, `nws_publisher.py`

| Change | Detail |
|---|---|
| Per-station datastream UID | `urn:os4csapi:datastream:nws:{station_id}:nwsSurfaceObs:v1` |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var |
| `_is_go_server` flag | NaN→0.0, timestamp re-added from phenomenonTime |

### 4.6  NDBC Buoy Publisher

**Files changed:** `bootstrap_ndbc.py`, `ndbc_publisher.py`, `ndbc_buoycam_publisher.py`

| Change | Detail |
|---|---|
| Per-station datastream UIDs | `urn:os4csapi:datastream:ndbc:{station_id}:ndbcBuoyObs:v1` and `urn:os4csapi:datastream:ndbc:{station_id}:ndbcBuoycam:v1` |
| `OSH_BASE_URL` override | Both publishers read `OSH_BASE_URL` env var |
| `_is_go_server` flag | NaN→0.0, timestamp re-added from phenomenonTime |
| `BUOYCAM_CACHE_BASE_URL` fix | Added `Environment=BUOYCAM_CACHE_BASE_URL=https://129-80-248-53.sslip.io/buoycam` to both `ndbc-buoycam-publisher.service` and `ndbc-buoycam-publisher-go.service`. Without this, `image_cache.py` produced relative paths (e.g., `/41009/2026/04/17/...jpg`) instead of absolute URLs. State file cleared and services restarted to force re-publish all 5 stations with correct URLs. |

### 4.7  CO-OPS Coastal Observations Publisher

**Files changed:** `bootstrap_coops.py`, `coops_publisher.py`

| Change | Detail |
|---|---|
| Per-station datastream UID | `urn:os4csapi:datastream:coops:{station_id}:coopsCoastalObs:v1` |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var |
| `_is_go_server` flag | NaN→0.0, timestamp re-added from phenomenonTime |

### 4.8  AviationWeather METAR Publisher

**Files changed:** `bootstrap_aviation_wx.py`, `aviation_wx_publisher.py`

| Change | Detail |
|---|---|
| Per-station datastream UID | `urn:os4csapi:datastream:awx:{icao_id}:metarObs:v1` |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var |
| `_is_go_server` flag | NaN→0.0, timestamp re-added from phenomenonTime |

### 4.9  USGS Water Publisher

**Files changed:** `bootstrap_usgs_water.py`, `usgs_water_publisher.py`

| Change | Detail |
|---|---|
| Per-station datastream UIDs | `urn:os4csapi:datastream:usgs-water:{nwis_id}:usgsDischarge:v1` and `urn:os4csapi:datastream:usgs-water:{nwis_id}:usgsGageHeight:v1` |
| Station key fix | Fixed `st["id"]` → `nwis_id` (station dict uses `nwisId` key) |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var |
| `_is_go_server` flag | Timestamp re-added from phenomenonTime |

### 4.10  USGS NIMS Imagery Publisher

**Files changed:** `bootstrap_usgs_nims.py`, `usgs_nims_publisher.py`

| Change | Detail |
|---|---|
| Per-camera datastream UID | `urn:os4csapi:datastream:usgs-nims:{cam_id}:usgsNimsImage:v1` |
| `OSH_BASE_URL` override | Publisher reads `OSH_BASE_URL` env var |
| `_is_go_server` flag | Timestamp re-added from phenomenonTime |
| Companion pattern | NIMS creates datastreams on USGS Water systems (depends on Water bootstrap) |

---

## 5  Go Server Resource Inventory

Final resource counts after complete fleet migration:

| Resource Type | Count |
|---|---|
| Systems | 37 |
| Datastreams | 58 |
| Procedures | 11 |
| Deployments | 58 |
| Observations | Growing (561+ at first verification) |

### 5.1  Breakdown by Publisher

| Publisher | Systems | Datastreams | Procedures | Deployments |
|---|---|---|---|---|
| NWS | 10 | 10 | 1 | 12 |
| NDBC (obs) | 5 | 5 | 1 | 7 |
| NDBC (buoycam) | — | 5 | 1 | — |
| CO-OPS | 5 | 5 | 1 | 7 |
| AviationWeather | 5 | 5 | 1 | 7 |
| USGS Water | 8 | 16 | 1 | 10 |
| USGS NIMS | — | 8 | 1 | 10 |
| USGS Earthquake | 1 | 1 | 1 | 2 |
| OpenSky ADS-B | 1 | 1 | 1 | 2 |
| ISS | 2 | 2 | 2 | 1 |
| **Total** | **37** | **58** | **11** | **58** |

---

## 6  Dual-Publish Pattern

The established pattern for adding Go server support to any publisher:

### 6.1  Bootstrap Script Changes

1. Add explicit `uid` to all `ensure_datastream()` calls:
   ```python
   ensure_datastream(base_url, auth, system_id, {
       "uid": "urn:os4csapi:datastream:<publisher>:<output>:v1",
       "outputName": "<output>",
       ...
   })
   ```

### 6.2  Publisher Code Changes

1. **`OSH_BASE_URL` override** — read from env to target a different server:
   ```python
   self._base_url = os.environ.get(
       "OSH_BASE_URL",
       f"https://{self.osh_address}/{self.osh_root}/api",
   )
   ```

2. **Go server detection** — set a flag for conditional behavior:
   ```python
   self._is_go_server = "csapi-go" in self._base_url
   ```

3. **Time coercion** — convert numeric time fields to strings:
   ```python
   if self._is_go_server:
       for key in TIME_FIELDS:
           if key in result and not isinstance(result[key], str):
               result[key] = str(result[key])
   ```

4. **NaN replacement** — substitute `0.0` for `"NaN"` strings:
   ```python
   if self._is_go_server:
       for key, val in result.items():
           if val == "NaN":
               result[key] = 0.0
   ```

5. **Include all schema fields** — ensure every declared field is present in every observation.

### 6.3  VM Deployment

1. Run bootstrap against Go server:
   ```bash
   OSH_BASE_URL="https://129-80-248-53.sslip.io/csapi-go" \
   OSH_USER=dummy OSH_PASS=dummy \
   python -m publishers.<name>.bootstrap_<name>
   ```

2. Create systemd service (copy existing, change env):
   ```ini
   [Service]
   Environment="OSH_ADDRESS=129-80-248-53.sslip.io"
   Environment="OSH_BASE_URL=https://129-80-248-53.sslip.io/csapi-go"
   Environment="OSH_USER=dummy"
   Environment="OSH_PASS=dummy"
   ExecStart=/usr/bin/python3 -m publishers.<name>.<name>_publisher
   ```

3. Enable and start: `sudo systemctl enable --now <name>-publisher-go.service`

---

## 7  Publisher Fleet Status

All 10 publishers are dual-publishing on both SensorHub and the Go server.

| # | Publisher | SH Service | Go Service | Interval | Notes |
|---|-----------|------------|------------|----------|-------|
| 1 | USGS Earthquake | `usgs-eq-publisher` | `usgs-eq-publisher-go` | 60s | 300 obs/cycle |
| 2 | OpenSky ADS-B | `opensky-publisher` | `opensky-publisher-go` | ~300s | ~170 obs/cycle, NaN→0.0 |
| 3 | ISS | `iss-publisher` | `iss-publisher-go` | 30s | CelesTrak TLE fetch may timeout (transient) |
| 4 | NWS | `nws-publisher` | `nws-publisher-go` | 3600s | 10 stations |
| 5 | NDBC | `ndbc-publisher` | `ndbc-publisher-go` | 3600s | 5 buoys |
| 6 | NDBC BuoyCAM | `ndbc-buoycam-publisher` | `ndbc-buoycam-publisher-go` | 900s | 5 cameras, `BUOYCAM_CACHE_BASE_URL` fix applied |
| 7 | CO-OPS | `coops-publisher` | `coops-publisher-go` | 360s | 5 tide stations |
| 8 | AviationWeather | `aviation-wx-publisher` | `aviation-wx-publisher-go` | 600s | 5 METAR stations |
| 9 | USGS Water | `usgs-water-publisher` | `usgs-water-publisher-go` | 900s | 8 gages (discharge + gage height) |
| 10 | USGS NIMS | `usgs-nims-publisher` | `usgs-nims-publisher-go` | 900s | 8 cameras, companion datastream pattern |

**Excluded from dual-publish:**
- **UAS Simulator** — FastAPI service, not a publisher in the same sense; separate integration path.
- **Localizer** — Depends on UAS simulator data; separate integration path.

### 7.1  VM Deployment Layout

Each Go publisher has its own directory under `/home/ubuntu/`:

```
/home/ubuntu/nws-publisher-go/
/home/ubuntu/ndbc-publisher-go/          # Also serves ndbc-buoycam-publisher-go
/home/ubuntu/coops-publisher-go/
/home/ubuntu/aviation-wx-publisher-go/
/home/ubuntu/usgs-water-publisher-go/
/home/ubuntu/usgs-nims-publisher-go/
/home/ubuntu/iss-publisher-go/
/home/ubuntu/usgs-eq-publisher/           # Shared dir (no -go suffix)
/home/ubuntu/OSHConnect-Python/          # OpenSky uses main repo clone
```

Each directory contains a copy of the relevant `publishers/` subtree plus `bootstrap_helpers.py`. Staging repo clone at `/tmp/OSHConnect-Python` for updates.

### 7.2  BuoyCAM Image Cache

BuoyCAM images are cached on disk at `/var/www/buoycam/` and served by Caddy:

```
# Caddy config
handle_path /buoycam/* {
    root * /var/www/buoycam
    header Access-Control-Allow-Origin *
    file_server browse
}
```

The `image_cache.py` module builds image URLs using:
```python
CACHE_BASE_URL = os.environ.get("BUOYCAM_CACHE_BASE_URL", "")
# → f"{CACHE_BASE_URL}/{station_id}/{ymd}/{ts}.jpg"
```

Without `BUOYCAM_CACHE_BASE_URL` set, the publisher produced relative paths like `/41009/2026/04/17/20260417T150121Z.jpg` — which broke in the Explorer since images need absolute URLs. Fixed by adding `Environment=BUOYCAM_CACHE_BASE_URL=https://129-80-248-53.sslip.io/buoycam` to both BuoyCAM systemd services. State files cleared and services restarted to force re-publish all 5 stations with correct absolute URLs.

**Verified:** `GET /datastreams/{id}/observations?limit=1&resultTime=latest` returns `imageUrl: "https://129-80-248-53.sslip.io/buoycam/41009/2026/04/17/20260417T160348Z.jpg"` — loads correctly.

---

## 8  GitHub Issues Filed

All filed on [OS4CSAPI/connected-systems-go](https://github.com/OS4CSAPI/connected-systems-go/issues):

| # | Label | Title |
|---|-------|-------|
| [#1](https://github.com/OS4CSAPI/connected-systems-go/issues/1) | bug | Datastream creation without explicit `uid` stores empty string, violates unique constraint |
| [#2](https://github.com/OS4CSAPI/connected-systems-go/issues/2) | bug | DELETE on parent resources fails with raw PostgreSQL FK constraint error |
| [#3](https://github.com/OS4CSAPI/connected-systems-go/issues/3) | enhancement | Research: Time field encoding — strict ISO 8601 vs. numeric timestamps |
| [#4](https://github.com/OS4CSAPI/connected-systems-go/issues/4) | enhancement | Research: NaN handling for numeric observation fields |
| [#5](https://github.com/OS4CSAPI/connected-systems-go/issues/5) | enhancement | Research: Strict schema validation — requiring ALL declared fields |
| [#6](https://github.com/OS4CSAPI/connected-systems-go/issues/6) | enhancement | Research: Cross-resource references — `@link` objects only vs. flat `@id` strings |
| [#7](https://github.com/OS4CSAPI/connected-systems-go/issues/7) | bug | `?uid=` query parameter silently ignored — returns all resources unfiltered |
| [#8](https://github.com/OS4CSAPI/connected-systems-go/issues/8) | bug | Subdeployments hidden from top-level `/deployments` listing |
| [#9](https://github.com/OS4CSAPI/connected-systems-go/issues/9) | bug | Default pagination limit of 10 too low — most resources hidden |
| [#10](https://github.com/OS4CSAPI/connected-systems-go/issues/10) | bug | SensorML `documents` array silently dropped — system thumbnails/media links lost |

Related library issues:
- [ogc-client-CSAPI_2#166](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/issues/166) — Library parsers need `@link.href` fallback.
- [ogc-client-CSAPI_2#167](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/issues/167) — `buildQueryString()` should not apply a default `limit` parameter.

---

## 9  Git History

### OSHConnect-Python (this repo)

All commits pushed to `main`:

| Commit | Description |
|--------|-------------|
| `e022ef2` | Go CSAPI compat: uid on datastreams, str Time fields, GeoJSON features lookup, OSH_BASE_URL override |
| `cfa4395` | Fix display URL to use actual base_url |
| `1cda1d5` | Dual-publish compat: coerce Time fields to strings only for Go server |
| `63c5201` | OpenSky: add OSH_BASE_URL override, uid on datastream, fix display URL |
| `d331433` | OpenSky: keep timestamp field for Go server (schema validation requires it) |
| `eed2e4d` | OpenSky: replace NaN strings with 0.0 for Go server (strict JSON validation) |
| `b7e551f` | feat: dual-publish support for all 8 remaining publishers |
| `906ae33` | feat: ISS bootstrap + bootstrap_helpers OSH_BASE_URL fix |
| `e7f792a` | fix: per-station unique datastream UIDs for Go server bootstraps |
| `92f584b` | fix: add limit=1000 to find_by_uid for Go server pagination |
| `3a02268` | fix: search subdeployments under parent, fix USGS Water station key |
| `62b78a3` | fix: ensure result.timestamp present for Go server schema validation |

### ogc-csapi-explorer

Commit `2f0869a` (Go server `@link.href` compat) already pushed.

---

## 10  Lessons Learned

### 10.1  Go Server Requires Explicit Everything

SensorHub is lenient — auto-generating UIDs, accepting partial results, filling timestamps from envelope fields. The Go server enforces strict PostgreSQL constraints and JSON schema validation. Every field must be explicit.

### 10.2  Bootstrap Idempotency Requires Reliable `find_by_uid`

The `find_by_uid()` pattern (check if exists, skip or create) breaks when the server ignores the `uid` query parameter and pagination hides existing resources. The `&limit=1000` workaround is fragile for large deployments.

### 10.3  Multi-Station Publishers Need Per-Station UIDs

SensorHub treats datastream UIDs as optional and per-system scoped. The Go server's global `UNIQUE` constraint on `unique_identifier` means every datastream across the entire database must have a distinct UID.

### 10.4  Subdeployment Hierarchy Is Not Transparent

The Go server's `/deployments` endpoint only returns top-level deployments. Bootstraps that create child deployments must search under the parent explicitly.

### 10.5  VM Deployment Workflow

The current file-copy deployment (staging repo → per-publisher directories) is error-prone. Multiple bootstrap failures were caused by stale code in publisher directories. A git-pull-based or symlink-based approach would be more reliable.

### 10.6  Environment Variables Must Be Explicitly Set in Systemd

The BuoyCAM image URL issue was caused by a missing `BUOYCAM_CACHE_BASE_URL` environment variable in both publisher systemd services. The `image_cache.py` module defaults to `""` for the base URL, producing relative paths that work in development but break when the images are served from a different origin. All publisher-specific env vars must be audited when deploying new services.

---

## 11  Future Work

- ~~**File GitHub issues** for the 4 newly discovered Go server behaviors (§3.3)~~ — Done: #7, #8, #9 filed; #10 filed for new `documents` issue
- **Go server SensorML `documents` support** — Issue #10 tracks this. System thumbnails and media links will remain broken until the Go server preserves the `documents` array on ingest/output. No client-side workaround available.
- **Explorer smoke test** against Go server to verify map visualization
- **Consolidate VM deployment** — replace per-directory file copies with symlinks or a deploy script
- **UAS Simulator + Localizer** — evaluate Go server integration path
- **Monitoring** — add health-check dashboard for Go publisher services
- **CelesTrak resilience** — add retry/fallback for ISS TLE fetch timeouts
- **Audit publisher env vars** — ensure all required environment variables (e.g., `BUOYCAM_CACHE_BASE_URL`) are set in every systemd service file

---

## Appendix A — VM Service Inventory

Services running on `129.80.248.53` as of 2026-04-17:

```
# SensorHub publishers (10)
iss-publisher.service
nws-publisher.service
ndbc-publisher.service
ndbc-buoycam-publisher.service
coops-publisher.service
aviation-wx-publisher.service
opensky-publisher.service
usgs-eq-publisher.service
usgs-water-publisher.service
usgs-nims-publisher.service

# Go server publishers (10)
iss-publisher-go.service
nws-publisher-go.service
ndbc-publisher-go.service
ndbc-buoycam-publisher-go.service
coops-publisher-go.service
aviation-wx-publisher-go.service
opensky-publisher-go.service
usgs-eq-publisher-go.service
usgs-water-publisher-go.service
usgs-nims-publisher-go.service

# Other
simulator.service
```

### Appendix A.1 — BuoyCAM Service Environment Variables

Both BuoyCAM publisher services now include the image cache base URL:

```ini
# /etc/systemd/system/ndbc-buoycam-publisher-go.service (excerpt)
[Service]
Environment="OSH_BASE_URL=https://129-80-248-53.sslip.io/csapi-go"
Environment="BUOYCAM_CACHE_BASE_URL=https://129-80-248-53.sslip.io/buoycam"

# /etc/systemd/system/ndbc-buoycam-publisher.service (excerpt)
[Service]
Environment="BUOYCAM_CACHE_BASE_URL=https://129-80-248-53.sslip.io/buoycam"
```
