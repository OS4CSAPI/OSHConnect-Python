# Publisher Fleet Portability Plan

**Date:** 2025-07-25  
**Status:** Complete  
**Scope:** Make the entire publisher fleet (9 publishers, 10 bootstraps, Docker Compose) reusable on any CSAPI-compliant server

---

## 1  Problem Statement

The publisher fleet *architecturally* supports portability — env vars, JSON station configs, idempotent bootstraps, and Dockerfiles are all in place. In practice, however, someone cloning this repo and running the publishers without carefully setting every environment variable would **silently authenticate against our production server** and begin writing observations into it.

### Audit Numbers

| Metric | Count |
|---|---|
| Files with hardcoded server/credential defaults | **24** |
| Total hardcoded references (`os4csapi-osh` or `ogc134mm`) | **69** |
| Distinct env var systems (bootstrap vs. publisher) | **2** |
| Setup documentation | **0** |

### What's Already Portable (No Changes Needed)

- **Station / sensor JSON configs** — station lists, buoy lists, METAR stations, etc. are data files a user can swap out  
- **Idempotent bootstraps** — `bootstrap_*.py` scripts create-or-skip, safe to re-run  
- **UIDs** — server-scoped, generated at bootstrap time per-server  
- **Dockerfiles** — all use `python:3.12-slim`, env vars are declared (just need safe defaults)  
- **Docker Compose structure** — YAML anchors, volume mounts, restart policies

---

## 2  Work Items

### 2.1  HIGH — Replace Dangerous Credential Defaults

**Risk:** A friend who forgets to set env vars silently hits our production server.

Every publisher `__init__` has the same five lines:

```python
self.osh_address = os.environ.get("OSH_ADDRESS", "os4csapi-osh.duckdns.org")
self.osh_port    = int(os.environ.get("OSH_PORT", "443"))
self.osh_user    = os.environ.get("OSH_USER", "os4csapi")
self.osh_pass    = os.environ.get("OSH_PASS", "ogc134mm")
self.osh_root    = os.environ.get("OSH_ROOT", "sensorhub")
```

And `bootstrap_helpers.py` `get_config()` at L39-40:

```python
"base_url": os.environ.get(
    "BOOTSTRAP_URL",
    "https://os4csapi-osh.duckdns.org/sensorhub/api"),
```

Plus every Dockerfile bakes in `ENV OSH_ADDRESS=os4csapi-osh.duckdns.org` etc.

**Fix:**

1. Change all Python defaults to obviously-wrong placeholders:
   - `OSH_ADDRESS` → `"your-server.example.com"`
   - `OSH_USER` → `"changeme"`
   - `OSH_PASS` → `"changeme"`
   - `BOOTSTRAP_URL` → `"https://your-server.example.com/sensorhub/api"`
2. Add a fail-fast guard at the top of each publisher `__init__` and in `bootstrap_helpers.get_config()`:
   ```python
   if self.osh_address == "your-server.example.com":
       sys.exit("ERROR: OSH_ADDRESS not configured. "
                "Copy .env.example → .env and fill in your server details.")
   ```
3. Remove hardcoded values from all 10 Dockerfiles; leave just `ENV OSH_ADDRESS=` (empty) so Docker Compose or `.env` must supply them.

**Files affected:** All 8 non-ISS publisher `.py` files, `publishers/base.py`, `bootstrap_helpers.py`, 10 Dockerfiles, `docker-compose.yml` `x-osh-env` anchor.

**Estimated changes:** ~69 line edits across 24 files.

---

### 2.2  HIGH — Remove or Guard the DNS Monkey-Patch

**Risk:** Silently forces all DuckDNS resolution to a hardcoded Oracle IP. Would break anyone on a different server.

In `bootstrap_helpers.py` L50-64:

```python
ORACLE_IP = "129.80.248.53"

def _patched_getaddrinfo(host, port, *args, **kwargs):
    if isinstance(host, str) and "os4csapi-osh.duckdns.org" in host:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ORACLE_IP, port or 443))]
    return _original_getaddrinfo(host, port, *args, **kwargs)

socket.getaddrinfo = _patched_getaddrinfo
```

**Fix:**

1. Move the monkey-patch behind an opt-in env var:
   ```python
   _FORCE_IP = os.environ.get("OSH_FORCE_IP", "")
   if _FORCE_IP:
       # DNS override active — used when DuckDNS is unreachable from the host
       ...
   ```
2. Remove the hardcoded `ORACLE_IP` constant.
3. Patch condition should match the configured address, not a hardcoded hostname.

**Files affected:** `bootstrap_helpers.py` only (single location, imported by all bootstraps).

---

### 2.3  HIGH — Unify Bootstrap and Publisher Config

**Risk:** Two different env var schemes confuse new users and require setting overlapping values.

| Component | Env Var(s) | What It Expects |
|---|---|---|
| Bootstraps | `BOOTSTRAP_URL` | Full URL: `https://host/root/api` |
| Publishers | `OSH_ADDRESS`, `OSH_PORT`, `OSH_ROOT` | Separate parts, assembled at runtime |

**Fix:**

1. Make `bootstrap_helpers.get_config()` derive its `base_url` from the same `OSH_ADDRESS` / `OSH_PORT` / `OSH_ROOT` env vars the publishers use:
   ```python
   def get_config():
       addr = os.environ.get("OSH_ADDRESS", "your-server.example.com")
       port = int(os.environ.get("OSH_PORT", "443"))
       root = os.environ.get("OSH_ROOT", "sensorhub")
       scheme = "http" if port == 80 else "https"
       base_url = os.environ.get(
           "BOOTSTRAP_URL",
           f"{scheme}://{addr}/{root}/api"
       )
       return {
           "base_url": base_url,
           "user": os.environ.get("OSH_USER", "changeme"),
           "password": os.environ.get("OSH_PASS", "changeme"),
       }
   ```
2. Keep `BOOTSTRAP_URL` as an optional override for edge cases, but the default path only requires the standard five vars.
3. Update `docker-compose.yml` `x-osh-env` to document this.

**Files affected:** `bootstrap_helpers.py`, `docker-compose.yml` (comments only).

---

### 2.4  MEDIUM — Create `.env.example` and Operator Guide

**Risk:** No documentation on what env vars to set, what order to run things, or how the fleet fits together.

**Deliverables:**

1. **`publishers/.env.example`**
   ```env
   # ── OSH Server Connection ──
   OSH_ADDRESS=your-server.example.com
   OSH_PORT=443
   OSH_USER=admin
   OSH_PASS=changeme
   OSH_ROOT=sensorhub

   # ── Optional ──
   # OSH_FORCE_IP=10.0.0.5          # Override DNS (useful behind NAT)
   # BOOTSTRAP_URL=                  # Override full bootstrap URL
   # BUOYCAM_CACHE_BASE_URL=         # NDBC BuoyCAM image proxy base URL
   ```

2. **`publishers/README.md`** — Getting-started guide:
   - Prerequisites (Python 3.12, Docker, target CSAPI server)
   - Quick start: copy `.env.example` → `.env`, fill in values, run a bootstrap, start a publisher
   - Architecture diagram (bootstraps → server, publishers → server)
   - Per-publisher notes (data sources, caveats, refresh intervals)
   - Docker Compose usage

**Files affected:** 2 new files.

---

### 2.5  LOW — Document BuoyCAM External Dependency

**Risk:** The NDBC BuoyCAM publisher serves cached images via a URL that must point somewhere accessible. The default refers to our server.

```yaml
BUOYCAM_CACHE_BASE_URL: https://os4csapi-osh.duckdns.org/buoycam
```

**Fix:**

1. Default to placeholder (`https://your-server.example.com/buoycam`).
2. Add a note in `README.md` explaining that the operator must host a static file server (or use the same OSH server with an Nginx location block) to serve the cached BuoyCAM JPEGs.

**Files affected:** `docker-compose.yml`, `ndbc_buoycam_publisher.py`, `README.md`.

---

## 3  Execution Order

| Step | Item | Est. Time |
|---|---|---|
| 1 | 2.4 — Create `.env.example` + `README.md` | 30 min |
| 2 | 2.1 — Replace credential defaults + add fail-fast guards | 60 min |
| 3 | 2.2 — Guard the DNS monkey-patch | 15 min |
| 4 | 2.3 — Unify config (bootstrap derives from publisher vars) | 15 min |
| 5 | 2.5 — BuoyCAM docs | 10 min |
| 6 | Smoke test — bootstrap + publish cycle with only `.env` set | 15 min |
| | **Total** | **~2.5 hrs** |

Step 1 goes first because it establishes the env var contract that steps 2-4 reference.  
Step 6 verifies the whole chain works when only the `.env` file supplies credentials.

---

## 4  What This Plan Does NOT Cover

| Topic | Reason |
|---|---|
| Common base class extraction | Assessed separately; recommendation is to park it (no drift, fleet stable) |
| AISHub publisher | Blocked on AISHub membership approval |
| Commercial API publishers | Out of scope (no keys, different licensing) |
| SWE schema improvements | Orthogonal to portability |
| Explorer (csapi-explorer) portability | Separate repo, no hardcoded server defaults |

---

## 5  Success Criteria

A collaborator can:

1. Clone the repo
2. Copy `.env.example` → `.env` and fill in their CSAPI server details
3. Run any bootstrap script — it creates resources on *their* server
4. Run `docker compose up` — all publishers start and write to *their* server
5. At no point does any traffic reach `os4csapi-osh.duckdns.org` unless they explicitly configure it

If any step fails or silently contacts the wrong server, the portability work is incomplete.
