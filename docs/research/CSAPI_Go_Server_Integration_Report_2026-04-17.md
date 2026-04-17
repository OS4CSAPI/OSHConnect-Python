# CSAPI-Go Server Integration Report

**Date:** 2026-04-17
**Status:** In Progress
**Scope:** Dual-publish the entire OS4CSAPI publisher fleet to the connected-systems-go server

---

## 1  Executive Summary

OS4CSAPI has deployed a second Connected Systems API server — [connected-systems-go](https://github.com/OS4CSAPI/connected-systems-go) — alongside the existing OSH SensorHub. This report documents the integration effort: server architecture, behavioral differences discovered during live testing, workarounds applied, publishers migrated to date, and the plan to complete the remaining fleet.

**Current state:** 2 of 10 publishers dual-publishing. 6 GitHub issues filed against the Go server.

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

During live integration testing, we identified 6 differences between connected-systems-go and OSH SensorHub. These have been filed as GitHub issues on [OS4CSAPI/connected-systems-go](https://github.com/OS4CSAPI/connected-systems-go/issues).

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

### 3.3  Other Go Server Characteristics

| Behavior | SensorHub | connected-systems-go |
|---|---|---|
| Collection key for geo-resources | `items` | `features` (GeoJSON) |
| Collection key for datastreams | `items` | `items` |
| ID format | Short numeric | UUID |
| Auth requirement | Required (HTTP Basic) | None (headers tolerated) |
| Datastream UID on create | Optional (auto-generated) | Effectively required (see #1) |

---

## 4  Code Changes Applied

### 4.1  Shared Infrastructure — `bootstrap_helpers.py`

**`find_by_uid()`** — Updated to check both `items` and `features` keys in collection responses, since the Go server wraps geo-resources in GeoJSON `features` arrays:

```python
# Support both GeoJSON (features) and flat JSON (items) collections
items = result.get("items", []) or result.get("features", [])
```

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

---

## 5  Go Server Resource Inventory

After bootstrapping USGS EQ and OpenSky on the Go server:

| Resource Type | Count | Examples |
|---|---|---|
| Systems | 2 | USGS Earthquake Feed, OpenSky ADS-B Feed |
| Datastreams | 2 | earthquakeEvent, adsbState |
| Deployments | 2 | USGS EQ deployment, OpenSky deployment |
| Procedures | 2 | USGS EQ procedure, OpenSky procedure |
| Observations | Growing | ~300 EQ events/cycle, ~170 aircraft states/cycle |

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

| # | Publisher | SensorHub | Go Server | Notes |
|---|-----------|:---------:|:---------:|-------|
| 1 | USGS Earthquake | ✅ Running | ✅ Running | First dual-publish. 300 obs/cycle. |
| 2 | OpenSky ADS-B | ✅ Running | ✅ Running | ~170 obs/cycle. NaN→0.0 workaround. |
| 3 | ISS | ✅ Running | ❌ Not started | 1 system, 2 DS. Low complexity. |
| 4 | NWS | ✅ Running | ❌ Not started | 10 stations. Medium complexity. |
| 5 | NDBC | ✅ Running | ❌ Not started | 5 buoys. Medium complexity. |
| 6 | NDBC BuoyCAM | ✅ Running | ❌ Not started | 5 cameras. Image observations — may need special handling. |
| 7 | CO-OPS | ✅ Running | ❌ Not started | 5 tide stations. Medium complexity. |
| 8 | AviationWeather | ✅ Running | ❌ Not started | 5 METAR stations. Medium complexity. |
| 9 | USGS Water | ✅ Running | ❌ Not started | 8 stations. Medium complexity. |
| 10 | USGS NIMS | ✅ Running | ❌ Not started | 8 cameras. Image observations. |

**Excluded from dual-publish:**
- **UAS Simulator** — FastAPI service, not a publisher in the same sense; separate integration path.
- **Localizer** — Depends on UAS simulator data; separate integration path.

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

Related library issue: [ogc-client-CSAPI_2#166](https://github.com/OS4CSAPI/ogc-client-CSAPI_2/issues/166) — Library parsers need `@link.href` fallback.

---

## 9  Git Status

### OSHConnect-Python (this repo)

6 unpushed commits (`e022ef2`..`eed2e4d`) on `main`:

| Commit | Description |
|--------|-------------|
| `e022ef2` | Go CSAPI compat: uid on datastreams, str Time fields, GeoJSON features lookup, OSH_BASE_URL override |
| `cfa4395` | Fix display URL to use actual base_url |
| `1cda1d5` | Dual-publish compat: coerce Time fields to strings only for Go server |
| `63c5201` | OpenSky: add OSH_BASE_URL override, uid on datastream, fix display URL |
| `d331433` | OpenSky: keep timestamp field for Go server (schema validation requires it) |
| `eed2e4d` | OpenSky: replace NaN strings with 0.0 for Go server (strict JSON validation) |

**Action needed:** Push to origin before continuing.

### ogc-csapi-explorer

Commit `2f0869a` (Go server `@link.href` compat) already pushed.

---

## 10  Next Steps — Remaining Publisher Migration

### Phase 1: Push existing work
1. Push 6 unpushed OSHConnect-Python commits to GitHub

### Phase 2: Migrate remaining publishers (8)
For each publisher, apply the dual-publish pattern (§6):

| Priority | Publisher | Rationale |
|----------|-----------|-----------|
| 1 | ISS | Simplest (1 system, 2 DS). Quick win to validate pattern. |
| 2 | NWS | 10 stations, well-tested bootstrap. Good stress test. |
| 3 | NDBC | 5 buoys, similar structure to NWS. |
| 4 | CO-OPS | 5 tide stations, similar structure. |
| 5 | AviationWeather | 5 METAR stations, similar structure. |
| 6 | USGS Water | 8 stations, similar structure. |
| 7 | NDBC BuoyCAM | Image observations — may require Go server testing for binary/URL payloads. |
| 8 | USGS NIMS | Image observations — same considerations as BuoyCAM. |

### Phase 3: Verification
- Confirm all Go server services running with 0 errors
- Run Explorer smoke test against Go server
- Update health-check dashboard to monitor Go server publishers

### Phase 4: Documentation
- Update this report with final status
- Update `Publisher_Fleet_Portability_Plan.md` to reference dual-publish capability
- Update `README.md` with Go server instructions

---

## Appendix A — VM Service Inventory

Services running on `129.80.248.53` as of 2026-04-17:

```
# SensorHub publishers (12)
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

# Go server publishers (2)
usgs-eq-publisher-go.service
opensky-publisher-go.service

# Other
simulator.service
```
