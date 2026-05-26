# CSAPI-Go Server Integration Report

**Date:** 2026-04-17 (last updated 2026-04-18)
**Status:** Complete — Updated with ISS Orbit Track & Deployment-Hierarchy Findings
**Scope:** Dual-publish the entire OS4CSAPI publisher fleet to the
connected-systems-go server

---

## 1  Executive Summary

OS4CSAPI has deployed a second
Connected Systems API server —
[connected-systems-go](https://github.com/OS4CSAPI/connected-systems-go) — alongside the existing OSH SensorHub. This report
documents the integration effort: server architecture, behavioral differences
discovered during live testing, workarounds applied, publishers migrated to date, and the
plan to complete the remaining fleet.

**Final state:** 10 of 10 publishers
dual-publishing on the Go server. 37 systems, 58 datastreams, 11 procedures, 58
deployments bootstrapped. All services running as systemd units with observations
flowing. 6 GitHub issues filed against the Go server, plus 4 additional
behavioral differences discovered during fleet-wide migration.

**Update — ISS Investigation:** After the initial integration, the ISS was
reported as not visible on the Go server map. A multi-phase investigation revealed:
(a) CelesTrak blocks Oracle Cloud IP addresses, causing both ISS publishers to
crash-loop; (b) the Go server's handling of `resultTime=latest` query parameter
was inconsistent; (c) the ISS was actually rendering correctly on the map, but
at its real-time orbital position (e.g., Indian Ocean), off-screen from the
default US-centered view. All issues have been resolved — CelesTrak fallback
applied to both publishers, `resultTime=latest` fallback applied to 7 call sites
in the Explorer, and ISS position confirmed visible with click-to-inspect
working.

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

The
[ogc-csapi-explorer](https://github.com/OS4CSAPI/ogc-csapi-explorer) demo app includes:

- **CF Pages proxy:** `demo/functions/api/csapi-go/[[path]].ts` → forwards to Go server
- **Vite dev proxy:** `demo/vite.config.ts` → local dev routing
- **Server selector:** "CSAPI-Go" option on the connection page (no auth required)

---

## 3  Behavioral Differences Discovered

During live integration testing, we identified 6 differences
between connected-systems-go and OSH SensorHub. These have been filed as GitHub issues
on [OS4CSAPI/connected-systems-go](https://github.com/OS4CSAPI/connected-systems-go/issues).

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

These were discovered during the full fleet migration and are not yet filed as issues.

#### Unique constraint on datastream `unique_identifier` (global scope)

- **Severity:** P2-Major
- **Problem:** PostgreSQL `idx_datastreams_unique_identifier` enforces global uniqueness across ALL datastreams, not just within a system. Multi-station publishers initially shared one UID template (e.g., `urn:os4csapi:datastream:nws:nwsSurfaceObs:v1`) for all stations — the second station's datastream creation failed.
- **Workaround:** All multi-station publishers now generate per-station UIDs: `urn:os4csapi:datastream:nws:{station_id}:nwsSurfaceObs:v1`.
- **Files changed:** `bootstrap_nws.py`, `bootstrap_ndbc.py`, `bootstrap_coops.py`, `bootstrap_aviation_wx.py`, `bootstrap_usgs_water.py`, `bootstrap_usgs_nims.py`.

#### `?uid=` query parameter ignored

- **Severity:** P2-Major
- **Problem:** `GET /systems?uid=urn:os4csapi:...` returns ALL systems (unfiltered) instead of the matching one. Combined with the default pagination limit of 10, `find_by_uid()` missed resources beyond the first page.
- **Workaround:** `find_by_uid()` now appends `&limit=1000` to all queries and matches client-side.
- **File changed:** `bootstrap_helpers.py`.

#### `/deployments` only returns top-level deployments

- **Severity:** P3-Minor
- **Problem:** `GET /deployments` does not include sub-deployments in results. Sub-deployments are only accessible via `GET /deployments/{parent_id}/subdeployments`.
- **Workaround:** `ensure_deployment()` now searches `deployments/{parent_id}/subdeployments` when `parent_id` is provided.
- **File changed:** `bootstrap_helpers.py`.

#### Strict result schema validation (timestamp required)

- **Severity:** P3-Minor (extends Issue #5)
- **Problem:** Go server validates that observation results contain ALL fields defined in the datastream schema, including `timestamp`. Publishers were popping `timestamp` from results (SensorHub auto-fills it from `phenomenonTime`), causing `result.timestamp is required by datastream schema` errors.
- **Workaround:** All publishers now re-add `timestamp` from `phenomenonTime` when targeting Go server.
- **Files changed:** All 8 publisher files.

### 3.4  ISS-Specific Behavioral Differences (Discovered During Map Investigation)

These were discovered during the ISS map investigation (§12).

#### `resultTime=latest` query parameter handling

- **Severity:** P3-Minor
- **Problem:** The Explorer's `buildSystemLocationCache()` and live-refresh cycles use `resultTime=latest` to fetch the most recent observation. The Go server's handling of this parameter was observed to be inconsistent — sometimes returning empty result sets, sometimes succeeding. SensorHub handles this reliably.
- **Impact:** Systems without native geometry (like ISS) rely on observation-derived locations. If the latest observation fetch fails, the system has no map position.
- **Workaround (Explorer):** Applied a `resultTime=latest` → plain `limit=1` fallback at all 7 call sites in `MapViewPage.vue`. The Go server returns newest-first by default, so `limit=1` without `resultTime` returns the most recent observation.
- **Note:** Subsequent curl testing confirmed that `resultTime=latest` + `limit=1` combined _does_ return valid data from the Go server. The inconsistency may be timing-dependent or related to the Go server's query parser behavior when other parameters are present.

#### SensorML `documents` array dropped

- **Severity:** P3-Minor
- **Problem:** When POSTing system or procedure resources with a SensorML `documents` array, the Go server accepts the POST but drops the `documents` field on subsequent GETs.
- **Impact:** Rich procedure metadata (specification documents, datasheets) is lost.
- **Workaround:** None. Metadata must be stored externally or in the `description` field.

### 3.5  Full Behavioral Comparison

| Behavior | SensorHub | connected-systems-go |
|---|---|---|
| Collection key for geo-resources | `items` | `features` (GeoJSON) |
| Collection key for datastreams | `items` | `items` |
| ID format | Short numeric | UUID |
| Auth requirement | Required (HTTP Basic) | None (headers tolerated) |
| Datastream UID on create | Optional (auto-generated) | Effectively required (see #1) |
| Datastream UID scope | Per-system | Global unique constraint |
| `?uid=` filter parameter | Supported | Ignored (returns all) |
| Default pagination limit | 100 | 10 |
| `/deployments` listing | All (flat) | Top-level only |
| `result.timestamp` field | Auto-filled from phenomenonTime | Required in result body |
| `resultTime=latest` query | Supported | Inconsistent (see §3.4) |
| SensorML `documents` array | Preserved | Dropped on GET |

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
| **CelesTrak TLE fallback** | Added fallback to `tle.ivanstanojevic.me` when CelesTrak is unreachable (see §12.2) |

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
   OSH_USER=dummy OSH_PASS=<osh-admin-password> \
   python -m publishers.<name>.bootstrap_<name>
   ```

2. Create systemd service (copy existing, change env):
   ```ini
   [Service]
   Environment="OSH_ADDRESS=129-80-248-53.sslip.io"
   Environment="OSH_BASE_URL=https://129-80-248-53.sslip.io/csapi-go"
   Environment="OSH_USER=dummy"
   Environment="OSH_PASS=<osh-admin-password>"
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
| 3 | ISS | `iss-publisher` | `iss-publisher-go` | 30s | CelesTrak fallback to ivanstanojevic.me TLE API (see §12.2) |
| 4 | NWS | `nws-publisher` | `nws-publisher-go` | 3600s | 10 stations |
| 5 | NDBC | `ndbc-publisher` | `ndbc-publisher-go` | 3600s | 5 buoys |
| 6 | NDBC BuoyCAM | `ndbc-buoycam-publisher` | `ndbc-buoycam-publisher-go` | 900s | 5 cameras, image observations |
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

Related library issues:
- [ogc-client-CSAPI_2#166](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/issues/166) — Library parsers need `@link.href` fallback.
- [ogc-client-CSAPI_2#167](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/issues/167) — `buildQueryString()` should not inject a default limit.

**Not yet filed** (from §3.3 and §3.4):
- Unique constraint on datastream `unique_identifier` (global scope)
- `?uid=` query parameter ignored
- `/deployments` only returns top-level deployments
- Strict result schema validation (`timestamp` required)
- `resultTime=latest` inconsistent handling
- SensorML `documents` array dropped on GET

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

Additional Explorer changes (pushed to `main`):
- `resultTime=latest` → `limit=1` fallback at 7 call sites in `MapViewPage.vue`
- `extractLatLonFromResult()` handles Go server observation formats (`lat_deg`/`lon_deg`)
- `isLocationRelatedDatastream()` broadened to catch ISS patterns
- `enrichSystems()` correctly resolves ISS from observation-derived location cache

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

### 10.6  CelesTrak IP Blocking Breaks Orbital Publishers

CelesTrak blocks requests from Oracle Cloud IP ranges. This caused both ISS publishers (SensorHub and Go) to crash-loop silently. The fix required a TLE fallback to an alternative API (`tle.ivanstanojevic.me`). Any future orbital/satellite publisher must account for this.

### 10.7  "Missing" Features May Be Off-Screen

When a system has no native geometry (like ISS, whose geometry comes from observations), its map position depends on the enrichment pipeline working correctly. A system appearing to be "missing" may actually be rendered at its real-time position far from the default map view. The Data Sources panel in the Explorer sidebar provides a quick count (e.g., "🛰️ ISS / Satellite 1") to confirm presence without manual map navigation.

---

## 11  Future Work

- **File GitHub issues** for the 6 newly discovered Go server behaviors (§3.3 and §3.4)
- **Consolidate VM deployment** — replace per-directory file copies with symlinks or a deploy script
- **UAS Simulator + Localizer** — evaluate Go server integration path
- **Monitoring** — add health-check dashboard for Go publisher services
- **ISS Orbit Track publisher for Go server** — the orbit track system (`f13579a5-...`) exists on Go but has 0 observations; a dedicated orbit track publisher is needed (see §12.5)
- **Suppress periodic 404 errors** — the Explorer's live-refresh cycle generates 404s for Go server endpoints that don't support `sortBy`/`sortOrder` query parameters, and the SENREP overlay fetches a hardcoded SensorHub datastream ID that doesn't exist on Go
- **`resultTime=latest` issue** — file as connected-systems-go issue for tracking

---

## 12  ISS Map Investigation (Added 2026-04-17)

### 12.1  Problem Statement

After the initial integration was reported complete, the ISS system was not visible on the Go server map in the Explorer. SensorHub's map showed the ISS correctly. The investigation aimed to determine whether the issue was in the publisher pipeline, the Go server data, or the Explorer rendering.

### 12.2  Root Cause 1 — CelesTrak Blocks Oracle Cloud IPs

**Discovery:** Both ISS publishers (`iss-publisher.service` for SensorHub, `iss-publisher-go.service` for Go) were crash-looping. The CelesTrak API (`celestrak.org`) blocks requests from Oracle Cloud IP address ranges, causing the TLE fetch to fail on every cycle.

**Fix:** Patched both publishers with a fallback TLE source:
- **Primary:** CelesTrak OMM JSON API (`celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON`)
- **Fallback:** Ivan Stanojevic TLE API (`tle.ivanstanojevic.me/api/tle/25544`) with `User-Agent: OSHConnect-Python/1.0` header
- **Propagation:** Fallback uses `Satrec.twoline2rv()` with raw TLE lines instead of OMM JSON fields

**Files patched on VM:**
- `/home/ubuntu/iss-publisher-go/publishers/iss/iss_publisher.py` (Go publisher)
- `/home/ubuntu/iss_publisher_v3.py` (SensorHub dual-product publisher)

After the patch, both publishers resumed publishing ISS position observations to their respective servers.

### 12.3  Root Cause 2 — `resultTime=latest` in Explorer

**Discovery:** The Explorer's `buildSystemLocationCache()` Phase C uses `resultTime=latest` to fetch the most recent observation for systems without native geometry. The Go server's handling of this parameter was inconsistent for some endpoints.

**Fix:** Applied a fallback pattern at all 7 call sites in `MapViewPage.vue`:
```typescript
// First attempt with resultTime=latest
let obsRes = await apiFetch(obsUrl, { headers: { 'Accept': 'application/om+json' } })

// Fallback: Go server may not handle resultTime=latest consistently.
// Retry with plain limit=1 (Go returns newest-first by default).
if (obsRes.ok && obsRes.data && !(obsRes.data.items?.[0] || obsRes.data[0])) {
  const fallbackUrl = getNestedListUrl('datastreams', ds.id, 'observations', { limit: 1 })
  obsRes = await apiFetch(fallbackUrl, { headers: { 'Accept': 'application/om+json' } })
}
```

### 12.4  Resolution — ISS Confirmed on Map

A comprehensive diagnostic pass (315 console log entries) confirmed the ISS pipeline works end-to-end on the Go server:

| Stage | Result |
|-------|--------|
| Global `/datastreams` fetch | 58 DS returned, 2 ISS-related |
| `isLocationRelatedDatastream()` filter | ISS Position (SGP4) matched on `"position"` keyword |
| `bySystem` dedup | ISS Position Publisher → `d4987f4f-2660-4ff4-b239-b7488ede663b` |
| Observation fetch | `GET /datastreams/db6756eb-.../observations?resultTime=latest&limit=1` → 200 OK, 1 item |
| `extractLatLonFromResult()` | `lat_deg=-44.4, lon_deg=77.8, alt_km=430.9` → `{ lat, lon, alt }` |
| `systemLocationCache` | Cached at `d4987f4f-...` with `lat=-44.4, lon=77.8` |
| `enrichSystems()` | ISS found without native geometry, cache hit, enriched feature created |
| Map render | Feature added to `systems` vector layer, 662 total features |
| Click interaction | Popup shows observation details: coordinates, altitude, timestamp |

**The ISS was on the map the entire time** — located at its real-time orbital position
(Indian Ocean, ~lat -23°, lon 106° at time of verification), which is outside the
default US-centered map view. Zooming to the ISS coordinates confirmed the marker
and popup work correctly.

**Go server ISS resources:**

| Resource | ID |
|----------|----|
| ISS Position Publisher (system) | `d4987f4f-2660-4ff4-b239-b7488ede663b` |
| ISS Position (SGP4) (datastream) | `db6756eb-e4ed-47e9-94c2-02eff5edf8d4` |
| ISS Orbit Track Publisher (system) | `f13579a5-67c2-41ce-bc58-7851ac31c1e3` |
| ISS Orbit Track (datastream) | `2d311345-2fd8-4759-94fb-43a94fc24e8c` |

### 12.5  Remaining Gap — ISS Orbit Track

The ISS Orbit Track system and datastream exist on the Go server, but the datastream has **0 observations**. The current Go ISS publisher only publishes position (point) observations, not orbit track (polyline) observations. The SensorHub ISS publisher (`iss_publisher_v3.py`) is a dual-product publisher that produces both position and orbit track, but the Go publisher (`iss_publisher.py`) only produces position.

**To enable orbit tracks on Go server:**
- Either extend the Go ISS publisher to produce orbit track observations (array of lat/lon points along the predicted orbital path), or
- Create a dedicated `iss_orbit_track_publisher_go.py` that computes and publishes the full orbit polyline.

---

## 13  ISS Orbit Track & Deployment-Hierarchy Investigation (Added 2026-04-18)

After §12 closed out the position-marker visibility question, a follow-up
investigation was opened when the ISS **orbit track polyline** and the ISS
**deployed-system marker** were both absent from the Go server map in the
deployed Explorer, while rendering correctly on OSH SensorHub. This section
documents four additional Go-server behaviors, one Explorer bug (now fixed),
and one bootstrap gap (now fixed).

### 13.1  Root Cause 3 — Observations returned in DESCENDING order by default

- **Severity:** P2-Major
- **Comparison:** SensorHub returns observations in **ascending** time order
  by default. The Go server returns them in **descending** (newest-first) order.
- **Impact:** The Explorer's `loadObservationLayers()` burst-dedup loop assumed
  ascending order when collapsing repeated point-observations into a single
  polyline. Running it on descending data caused every item after the first to
  be classified as a duplicate and dropped, leaving `trackCoords.length === 1`
  and no polyline ever being added to the map.
- **Fix (Explorer):** Added an explicit ascending `allItems.sort()` by
  `phenomenonTime` immediately before the dedup loop. Committed to
  `ogc-csapi-explorer` as `604d7c1` and deployed to Cloudflare Pages.
- **Result:** The full 500-point ISS orbit track now renders correctly on the
  Go-server map, matching OSH behavior.

### 13.2  Go server silently ignores `sortBy` / `sortOrder` parameters

- **Severity:** P3-Minor
- **Problem:** Passing `sortBy=phenomenonTime&sortOrder=asc` to
  `/datastreams/{id}/observations` has no effect — the server returns the same
  descending order regardless of parameter values. No error, no warning.
- **Workaround:** Client-side sort (see §13.1). Ordering cannot be requested
  from the server; it must be imposed by the consumer.

### 13.3  Go server silently ignores time-range filters

- **Severity:** P3-Minor
- **Problem:** `resultTime=<start>/<end>`, `phenomenonTime=<start>/<end>`, and
  `datetime=<start>/<end>` range filters are all silently accepted and then
  ignored on `/datastreams/{id}/observations`. The full unfiltered result set
  is returned (subject to `limit`).
- **Impact:** Clients that rely on server-side time-windowing (e.g., "last
  N minutes") must paginate and filter client-side. This compounds the
  ordering issue from §13.1 because the newest-first default means an
  unbounded query trims the *oldest* data.
- **Workaround:** Request large `limit` values and filter by timestamp
  client-side. Not yet filed as an issue.

### 13.4  Cloudflare Pages production deployment stuck on stale build

- **Severity:** P2-Major (deployment / CI issue, not Go-server)
- **Problem:** Production bundle at `ogc-csapi-explorer.pages.dev` remained on
  the Apr 17 build (`index-B_aWg6nq.js`) for multiple days after new commits
  were pushed to `main`. The GitHub → Cloudflare auto-deploy hook appears to
  have skipped several commits. This masked the §13.1 fix and sent the
  investigation down several incorrect paths.
- **Workaround:** Manual Cloudflare redeploy after confirming the stuck state
  by inspecting the bundle hash in the live page. Future fixes need a
  deployment-smoke step that asserts a known marker string from the latest
  commit is present in the served bundle before declaring a fix verified.

### 13.5  Go server missing ISS deployment subtree (bootstrap gap)

- **Severity:** P2-Major (data completeness; Go server has partial parity)
- **Problem:** On OSH, the ISS tracking context is a **four-level** deployment
  hierarchy:
  ```
  Orbital Tracking Demo        (root, geometry: null)
    └─ LEO Objects             (geometry: null)
       └─ ISS Tracking Role    (geometry: null)
          ├─ ISS Position Feed        → platform@link → ISS Position Publisher
          └─ ISS Orbit Track Feed     → platform@link → ISS Orbit Track Publisher
  ```
  The **leaf** deployments carry the `platform@link` that ties a deployment
  to a system. The Explorer's snap-to-track-tip logic in `MapViewPage.vue`
  matches deployments to systems by
  `rd.properties['platform@link'].href.split('/').pop() === dsInfo.systemId`.
- **Go-server state:** Bootstrap created only the root `Orbital Tracking Demo`
  deployment. The three descendants — LEO Objects, ISS Tracking Role, and the
  two leaves carrying `platform@link` — were never created. As a result no
  Go-server deployment had a `platform@link` to the ISS systems, and the
  deployed-system marker could not be positioned on the map.
- **Fix:** Added `scripts/bootstrap_iss_deployments_go.py` to the
  `ogc-csapi-explorer` repo. It is idempotent, searches by UID under each
  parent, POSTs to `/deployments/{parent_id}/subdeployments` with
  `application/geo+json`, and tolerates the Go server's `201 Created` +
  empty-body response by re-fetching the new resource by UID. After running
  it, the Go server now has the complete four-level hierarchy with
  `platform@link` on both leaves pointing at the ISS Position Publisher and
  ISS Orbit Track Publisher.
- **Follow-up for `bootstrap_iss.py`:** The main ISS bootstrap script in this
  repo already encodes the full `DEPLOYMENT_TREE`, but it was not executed
  end-to-end against the Go server during the original fleet migration
  (only the root was persisted). The deployment helper's recursive
  `create_deployment_node()` should be re-validated against the Go server as
  a regression guard.

### 13.6  Go server missing `/deployments/{id}/systems` endpoint

- **Severity:** P3-Minor
- **Problem:** `GET /deployments/{id}/systems` returns **404 Not Found** on
  the Go server. OSH supports this endpoint and uses it to list the systems
  associated with a deployment (independently of `platform@link` traversal).
- **Impact:** Clients that discover systems via deployment → systems
  navigation instead of the reverse (`platform@link`) path are broken
  against Go. The Explorer does not currently rely on this endpoint, so
  no behavior change was required, but third-party clients may.
- **Workaround:** Use `/deployments/{id}/subdeployments` to walk to leaves,
  then follow each leaf's `platform@link.href` to the system.

### 13.7  Updated Behavioral Comparison Additions

| Behavior | SensorHub | connected-systems-go |
|---|---|---|
| Observation default sort order | Ascending by `phenomenonTime` | **Descending** (newest-first) |
| `sortBy` / `sortOrder` query params | Honored | **Silently ignored** |
| `resultTime` / `phenomenonTime` / `datetime` range filters | Honored | **Silently ignored** |
| `/deployments/{id}/systems` endpoint | Supported | **404 Not Found** |
| Deployment `201 Created` response body | Full resource JSON | Empty; `Location` header only |

### 13.8  New Explorer commits (ogc-csapi-explorer `main`)

| Commit | Description |
|--------|-------------|
| `604d7c1` | fix(map): sort observations ascending before burst-dedup to handle Go server's descending default order; restores ISS orbit-track polyline on Go |
| (script) | `scripts/bootstrap_iss_deployments_go.py` — idempotent creator for the missing ISS deployment subtree on Go, with `platform@link` on both leaves |

### 13.9  Outstanding items to file as Go-server issues

- Default descending observation order (documentation / configurability)
- `sortBy` / `sortOrder` silently ignored
- Time-range filters (`resultTime`, `phenomenonTime`, `datetime`) silently ignored
- `/deployments/{id}/systems` endpoint missing (404)
- `201 Created` with empty body on POST (should return created resource or at
  least `Location` consistently; clients must refetch by UID)

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
