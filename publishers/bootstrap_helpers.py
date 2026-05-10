#!/usr/bin/env python3
"""
bootstrap_helpers.py — Shared idempotent CSAPI resource-creation helpers.

Extracted from the proven bootstrap_iss.py pattern. All functions use stdlib-only
HTTP (urllib) with no external dependencies.

Functions:
  find_by_uid()       — Lookup resource by UID in a collection
  find_datastream()   — Lookup datastream by outputName under a system
  ensure_procedure()  — Create procedure (geo+json stub POST → optional SensorML PUT)
  ensure_system()     — Create system (geo+json stub POST → optional SensorML PUT)
  ensure_datastream() — Create datastream with SWE DataRecord schema
  ensure_deployment() — Create deployment node (geo+json stub POST → optional SensorML PUT)
  clean_resource()    — Delete resource by UID if it exists
  api_get/post/put/delete() — Low-level HTTP helpers with retry

Content-type contract (CSAPI Part 1, OGC 23-001):
  - application/geo+json  → spatial-discovery view; carries uid/name/description
                            (+ geometry) only. SensorML metadata is INTENTIONALLY
                            stripped server-side.
  - application/sml+json  → full SensorML metadata view; carries keywords,
                            identifiers, classifiers, characteristics, capabilities,
                            contacts, documentation/documents, history,
                            securityConstraints, legalConstraints, etc.

Bootstrap pattern for procedures, systems, and deployments:
  1. POST a small geo+json stub  (Content-Type: application/json — server
     interprets as application/geo+json on these endpoints).
  2. PUT the full SensorML body  (Content-Type: application/sml+json) against
     the just-created /resource/{id} path.

This module enforces the contract via _warn_if_sml_fields_in_stub(): if a
caller passes a "stub" with SensorML-only fields under properties, a loud
warning is emitted. Set OS4CSAPI_STRICT_BOOTSTRAP=1 to elevate the warning
to an exception (recommended for tests and CI).
"""

import argparse
import base64
import json
import os
import socket
import ssl as _ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration (from env vars or caller)
# ═══════════════════════════════════════════════════════════════════════════

def get_config():
    """Return server config dict from environment variables.

    Uses the same OSH_ADDRESS / OSH_PORT / OSH_ROOT env vars as the
    publishers so only one set of credentials needs to be configured.
    BOOTSTRAP_URL can optionally override the derived URL.
    """
    addr = os.environ.get("OSH_ADDRESS", "")
    port = os.environ.get("OSH_PORT", "443")
    root = os.environ.get("OSH_ROOT", "sensorhub")
    user = os.environ.get("OSH_USER", "")
    password = os.environ.get("OSH_PASS", "")

    if not addr or not user or not password:
        sys.exit(
            "ERROR: OSH_ADDRESS, OSH_USER, and OSH_PASS must be set.\n"
            "  Copy publishers/.env.example → .env and set your server details."
        )

    scheme = "http" if port == "80" else "https"
    default_url = f"{scheme}://{addr}/{root}/api"
    base_url = os.environ.get("BOOTSTRAP_URL",
               os.environ.get("OSH_BASE_URL", default_url))

    return {
        "base_url": base_url,
        "user": user,
        "password": password,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  SSL + DNS workarounds
# ═══════════════════════════════════════════════════════════════════════════

_ssl_ctx = _ssl.create_default_context()
_ssl_ctx.check_hostname = True
_ssl_ctx.verify_mode = _ssl.CERT_REQUIRED

_original_getaddrinfo = socket.getaddrinfo

# Optional DNS override — set OSH_FORCE_IP to bypass DNS for the server hostname.
# Useful behind NAT / split-DNS or when DuckDNS is unreachable from the host.
_FORCE_IP = os.environ.get("OSH_FORCE_IP", "")

if _FORCE_IP:
    _FORCE_HOST = os.environ.get("OSH_ADDRESS", "")

    def _patched_getaddrinfo(host, port, *args, **kwargs):
        """Force DNS resolution for the configured server to OSH_FORCE_IP."""
        if isinstance(host, str) and _FORCE_HOST and _FORCE_HOST in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (_FORCE_IP, port or 443))]
        return _original_getaddrinfo(host, port, *args, **kwargs)

    socket.getaddrinfo = _patched_getaddrinfo


# ═══════════════════════════════════════════════════════════════════════════
#  Low-level HTTP helpers with retry
# ═══════════════════════════════════════════════════════════════════════════

def _auth_header(user: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def _with_retry(fn, label="request", max_retries=3, base_delay=2.0):
    """Retry a callable on transient failure."""
    for attempt in range(max_retries):
        try:
            return fn()
        except (URLError, ConnectionError, TimeoutError, OSError) as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            print(f"    [RETRY] {label} attempt {attempt + 1} failed: {e}. "
                  f"Retrying in {delay}s...")
            time.sleep(delay)


def api_get(base_url: str, path: str, auth: str) -> dict | None:
    """GET a JSON resource. Returns parsed dict or None on 404."""
    def fn():
        url = f"{base_url}/{path}"
        req = Request(url, headers={
            "Authorization": auth,
            "Accept": "application/json",
        })
        try:
            with urlopen(req, timeout=15, context=_ssl_ctx) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            if e.code == 404:
                return None
            raise
    return _with_retry(fn, f"GET {path}")


def api_post(base_url: str, path: str, body: dict, auth: str,
             content_type: str = "application/json") -> dict | None:
    """POST a JSON resource. Returns {id, _location} on success."""
    def fn():
        url = f"{base_url}/{path}"
        data = json.dumps(body).encode()
        req = Request(url, data=data, method="POST", headers={
            "Authorization": auth,
            "Content-Type": content_type,
            "Accept": "application/json",
        })
        try:
            with urlopen(req, timeout=30, context=_ssl_ctx) as resp:
                location = resp.headers.get("Location", "")
                raw = resp.read().decode()
                if location:
                    new_id = location.rstrip("/").split("/")[-1]
                    return {"id": new_id, "_location": location}
                if resp.status == 204 or not raw.strip():
                    return None
                return json.loads(raw)
        except HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code} POST {url}: {body_text[:400]}")
    return _with_retry(fn, f"POST {path}")


def api_put(base_url: str, path: str, body: dict, auth: str,
            content_type: str = "application/sml+json") -> bool:
    """PUT (update) a resource. Returns True on success."""
    def fn():
        url = f"{base_url}/{path}"
        data = json.dumps(body).encode()
        req = Request(url, data=data, method="PUT", headers={
            "Authorization": auth,
            "Content-Type": content_type,
            "Accept": "application/json",
        })
        try:
            with urlopen(req, timeout=30, context=_ssl_ctx) as resp:
                return resp.status in (200, 204)
        except HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code} PUT {url}: {body_text[:400]}")
    return _with_retry(fn, f"PUT {path}")


def api_delete(base_url: str, path: str, auth: str, *, cascade: bool = False) -> bool:
    """DELETE a resource. Returns True on success, False on 404."""
    def fn():
        url = f"{base_url}/{path}"
        if cascade:
            url += "?cascade=true" if "?" not in url else "&cascade=true"
        req = Request(url, method="DELETE", headers={"Authorization": auth})
        try:
            with urlopen(req, timeout=15, context=_ssl_ctx) as resp:
                return resp.status in (200, 204)
        except HTTPError as e:
            if e.code == 404:
                return False
            raise
    return _with_retry(fn, f"DELETE {path}")


# ═══════════════════════════════════════════════════════════════════════════
#  Lookup helpers
# ═══════════════════════════════════════════════════════════════════════════

_uid_cache: dict[str, str] = {}


def find_by_uid(base_url: str, auth: str, collection: str, uid: str) -> str | None:
    """Find a resource by UID in a collection. Returns server ID or None."""
    cache_key = f"{collection}:{uid}"
    if cache_key in _uid_cache:
        return _uid_cache[cache_key]

    result = api_get(base_url, f"{collection}?uid={uid}&limit=1000", auth)
    if result:
        # Support both GeoJSON (features) and flat JSON (items) collections
        items = result.get("items", []) or result.get("features", [])
        for item in items:
            props = item.get("properties", item)
            if props.get("uid") == uid:
                item_id = item.get("id") or props.get("id")
                if item_id:
                    _uid_cache[cache_key] = str(item_id)
                    return str(item_id)
    return None


def find_datastream(base_url: str, auth: str, system_id: str,
                    output_name: str) -> dict | None:
    """Find a datastream on a system by outputName."""
    result = api_get(base_url, f"systems/{system_id}/datastreams", auth)
    if result and "items" in result:
        for ds in result["items"]:
            if ds.get("outputName") == output_name:
                return ds
    return None


# ═══════════════════════════════════════════════════════════════════════════
#  Encoding-contract guardrail
# ═══════════════════════════════════════════════════════════════════════════

# SensorML-only fields that the CSAPI server silently strips when it sees
# them under `properties` of a geo+json POST. Any of these fields appearing
# in a "stub" body indicates the caller has not split GeoJSON encoding from
# SensorML encoding properly — the stub will be accepted (HTTP 201) but
# the listed fields will be DROPPED on the server side.
#
# Background: pre-strict CSAPI servers returned 201 + silent drop. Strict
# servers (post-`a467aba` upstream) return HTTP 400. Either way, the bug
# is on the client. See docs/engineering/2026-05-silent-sensorml-field-loss.md
SML_ONLY_FIELDS = frozenset({
    "keywords",
    "identifiers",
    "classifiers",
    "characteristics",
    "capabilities",
    "contacts",
    "documentation",      # OGC links-array form (not the SensorML `documents` form)
    "documents",          # SensorML form
    "history",
    "securityConstraints",
    "legalConstraints",
    "lineage",
    "usageConstraints",
    "typeOf",
    "configuration",
    "modes",
    "parameters",
    "inputs",
    "outputs",
    "components",
    "connections",
    "localReferenceFrames",
    "localTimeFrames",
    "method",
})

_STRICT_BOOTSTRAP = os.environ.get("OS4CSAPI_STRICT_BOOTSTRAP", "").lower() in ("1", "true", "yes")


def _warn_if_sml_fields_in_stub(stub: dict, label: str) -> None:
    """Loud warning (or exception in strict mode) if a caller passes a 'stub'
    body whose `properties` contain SensorML-only fields.

    These fields will be silently dropped server-side on a geo+json POST.
    Callers must split SensorML metadata out into a separate ``sml_body``
    and let the helper PUT it with ``Content-Type: application/sml+json``.

    Set OS4CSAPI_STRICT_BOOTSTRAP=1 to convert the warning to RuntimeError —
    recommended for tests and CI.
    """
    if not isinstance(stub, dict):
        return
    props = stub.get("properties", stub)
    if not isinstance(props, dict):
        return
    leaked = sorted(SML_ONLY_FIELDS & set(props.keys()))
    if not leaked:
        return
    msg = (
        f"[ENCODING-CONTRACT] {label}: stub body carries SensorML-only "
        f"field(s) under `properties`: {leaked}. These will be silently "
        f"dropped (or 400-rejected by strict servers) on the geo+json POST. "
        f"Move them into a separate sml_body argument."
    )
    if _STRICT_BOOTSTRAP:
        raise RuntimeError(msg)
    print(f"  [WARN] {msg}")


# ═══════════════════════════════════════════════════════════════════════════
#  Idempotent resource creation
# ═══════════════════════════════════════════════════════════════════════════

def ensure_procedure(base_url: str, auth: str, uid: str, stub_body: dict,
                     sml_body: dict | None = None,
                     *, dry_run: bool = False, stats: dict = None,
                     force_sml: bool = False) -> str | None:
    """Create a procedure if it doesn't already exist. Returns server ID.

    Two-step encoding-correct pattern (mirrors ``ensure_system``):

      1. POST ``stub_body`` (geo+json Feature: uid/name/description + optional
         geometry) with ``Content-Type: application/json``. The server
         interprets this as ``application/geo+json`` on the procedures
         endpoint.
      2. If ``sml_body`` is provided, PUT it against the new resource path
         with ``Content-Type: application/sml+json`` to populate full
         SensorML metadata (keywords, identifiers, classifiers,
         characteristics, capabilities, contacts, documents, history,
         securityConstraints, legalConstraints, …).

    When ``force_sml`` is True and the procedure already exists, the
    SensorML body is PUT again — useful for correcting previously-broken
    payloads after this fix lands.

    Callers MUST keep SensorML metadata out of the stub. The
    ``_warn_if_sml_fields_in_stub`` guardrail catches accidental leakage.
    """
    _warn_if_sml_fields_in_stub(stub_body, f"ensure_procedure({uid})")

    existing = find_by_uid(base_url, auth, "procedures", uid)
    if existing:
        if force_sml and sml_body:
            if dry_run:
                print(f"  [DRY] Would force-PUT SML for procedure {uid} (id={existing})")
            else:
                api_put(base_url, f"procedures/{existing}", sml_body, auth,
                        content_type="application/sml+json")
                print(f"  [SML] Force-PUT SensorML for procedure {uid} (id={existing})")
            if stats:
                stats.setdefault("sml_updated", 0)
                stats["sml_updated"] += 1
        else:
            print(f"  [SKIP] Procedure {uid} already exists (id={existing})")
            if stats:
                stats.setdefault("skipped", 0)
                stats["skipped"] += 1
        return existing

    if dry_run:
        print(f"  [DRY] Would create procedure: {uid}")
        return None

    # Step 1: POST geo+json stub
    result = api_post(base_url, "procedures", stub_body, auth)
    new_id = result.get("id") if result else None

    # Step 2: PUT SensorML if provided
    if new_id and sml_body:
        api_put(base_url, f"procedures/{new_id}", sml_body, auth,
                content_type="application/sml+json")

    print(f"  [OK] Created procedure {uid} → id={new_id}")
    if stats:
        stats.setdefault("created", 0)
        stats["created"] += 1
    if new_id:
        _uid_cache[f"procedures:{uid}"] = new_id
    return new_id


def ensure_system(base_url: str, auth: str, uid: str, stub_body: dict,
                  sml_body: dict | None = None,
                  *, dry_run: bool = False, stats: dict = None,
                  force_sml: bool = False) -> str | None:
    """Create a system with optional SensorML PUT. Returns server ID.

    When *force_sml* is True and the system already exists, the SML body is
    PUT again (useful for correcting previously-broken SML payloads).
    """
    _warn_if_sml_fields_in_stub(stub_body, f"ensure_system({uid})")

    existing = find_by_uid(base_url, auth, "systems", uid)
    if existing:
        if force_sml and sml_body:
            if dry_run:
                print(f"  [DRY] Would force-PUT SML for system {uid} (id={existing})")
            else:
                api_put(base_url, f"systems/{existing}", sml_body, auth,
                        content_type="application/sml+json")
                print(f"  [SML] Force-PUT SensorML for system {uid} (id={existing})")
            if stats:
                stats.setdefault("sml_updated", 0)
                stats["sml_updated"] += 1
        else:
            print(f"  [SKIP] System {uid} already exists (id={existing})")
            if stats:
                stats.setdefault("skipped", 0)
                stats["skipped"] += 1
        return existing

    if dry_run:
        print(f"  [DRY] Would create system: {uid}")
        return None

    # Step 1: POST geo+json stub
    result = api_post(base_url, "systems", stub_body, auth)
    new_id = result.get("id") if result else None

    # Step 2: PUT SensorML if provided
    if new_id and sml_body:
        api_put(base_url, f"systems/{new_id}", sml_body, auth,
                content_type="application/sml+json")

    print(f"  [OK] Created system {uid} → id={new_id}")
    if stats:
        stats.setdefault("created", 0)
        stats["created"] += 1
    if new_id:
        _uid_cache[f"systems:{uid}"] = new_id
    return new_id


def ensure_datastream(base_url: str, auth: str, system_id: str,
                      output_name: str, schema_body: dict,
                      *, dry_run: bool = False, stats: dict = None) -> str | None:
    """Create a datastream under a system if it doesn't exist. Returns server ID."""
    existing = find_datastream(base_url, auth, system_id, output_name)
    if existing:
        ds_id = existing.get("id")
        print(f"  [SKIP] Datastream '{output_name}' already exists (id={ds_id})")
        if stats:
            stats.setdefault("skipped", 0)
            stats["skipped"] += 1
        return ds_id

    if dry_run:
        print(f"  [DRY] Would create datastream '{output_name}' on system {system_id}")
        return None

    result = api_post(base_url, f"systems/{system_id}/datastreams", schema_body, auth)
    new_id = result.get("id") if result else None
    print(f"  [OK] Created datastream '{output_name}' → id={new_id}")
    if stats:
        stats.setdefault("created", 0)
        stats["created"] += 1
    return new_id


def ensure_deployment(base_url: str, auth: str, uid: str, stub_body: dict,
                      sml_body: dict | None = None,
                      parent_id: str | None = None,
                      *, dry_run: bool = False, stats: dict = None,
                      force_sml: bool = False) -> str | None:
    """Create a deployment node if it doesn't exist. Returns server ID.

    Two-step encoding-correct pattern (mirrors ``ensure_system`` and
    ``ensure_procedure``):

      1. POST ``stub_body`` (geo+json Feature: uid/name/description +
         optional geometry, validTime, deployment-tree links) with
         ``Content-Type: application/json``. Server interprets as
         ``application/geo+json``.
      2. If ``sml_body`` is provided, PUT it against the new resource path
         with ``Content-Type: application/sml+json`` to populate full
         SensorML metadata (keywords, identifiers, classifiers,
         characteristics, capabilities, contacts, documents, history,
         securityConstraints, legalConstraints, …).

    When ``parent_id`` is given, the create path is
    ``deployments/{parent_id}/subdeployments``; the SML PUT still targets
    the canonical ``deployments/{new_id}`` path.

    When ``force_sml`` is True and the deployment already exists, the
    SensorML body is PUT again.

    Callers MUST keep SensorML metadata out of the stub. The
    ``_warn_if_sml_fields_in_stub`` guardrail catches accidental leakage.
    """
    _warn_if_sml_fields_in_stub(stub_body, f"ensure_deployment({uid})")

    # Check top-level deployments first
    existing = find_by_uid(base_url, auth, "deployments", uid)
    if not existing and parent_id:
        # Go server only lists subdeployments under parent endpoint
        existing = find_by_uid(base_url, auth,
                               f"deployments/{parent_id}/subdeployments", uid)
    if existing:
        if force_sml and sml_body:
            if dry_run:
                print(f"  [DRY] Would force-PUT SML for deployment {uid} (id={existing})")
            else:
                api_put(base_url, f"deployments/{existing}", sml_body, auth,
                        content_type="application/sml+json")
                print(f"  [SML] Force-PUT SensorML for deployment {uid} (id={existing})")
            if stats:
                stats.setdefault("sml_updated", 0)
                stats["sml_updated"] += 1
        else:
            print(f"  [SKIP] Deployment {uid} already exists (id={existing})")
            if stats:
                stats.setdefault("skipped", 0)
                stats["skipped"] += 1
        return existing

    if dry_run:
        print(f"  [DRY] Would create deployment: {uid}")
        return None

    # Step 1: POST geo+json stub at the (possibly nested) create path
    path = "deployments"
    if parent_id:
        path = f"deployments/{parent_id}/subdeployments"

    result = api_post(base_url, path, stub_body, auth)
    new_id = result.get("id") if result else None

    # Step 2: PUT SensorML against the canonical /deployments/{id} path
    if new_id and sml_body:
        api_put(base_url, f"deployments/{new_id}", sml_body, auth,
                content_type="application/sml+json")

    print(f"  [OK] Created deployment {uid} → id={new_id}")
    if stats:
        stats.setdefault("created", 0)
        stats["created"] += 1
    if new_id:
        _uid_cache[f"deployments:{uid}"] = new_id
    return new_id


def clean_resource(base_url: str, auth: str, collection: str, uid: str,
                   *, dry_run: bool = False, stats: dict = None,
                   cascade: bool = False):
    """Delete a resource by UID if it exists."""
    existing_id = find_by_uid(base_url, auth, collection, uid)
    if not existing_id:
        return

    if dry_run:
        print(f"  [DRY] Would delete {collection}/{existing_id} ({uid})")
        return

    print(f"  DELETE {collection}/{existing_id} ({uid})")
    api_delete(base_url, f"{collection}/{existing_id}", auth, cascade=cascade)
    if stats:
        stats.setdefault("deleted", 0)
        stats["deleted"] += 1

    # Invalidate cache
    cache_key = f"{collection}:{uid}"
    _uid_cache.pop(cache_key, None)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI helpers
# ═══════════════════════════════════════════════════════════════════════════

def add_bootstrap_args(parser: argparse.ArgumentParser):
    """Add standard bootstrap CLI arguments."""
    parser.add_argument("--clean", action="store_true",
                        help="Delete then recreate all resources")
    parser.add_argument("--clean-only", action="store_true",
                        help="Delete only (teardown)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without making changes")
    parser.add_argument("--force-sml", action="store_true",
                        help="Force re-PUT SensorML on existing systems (update metadata)")


def print_summary(stats: dict, dry_run: bool = False):
    """Print a summary of bootstrap operations."""
    prefix = "[DRY RUN] " if dry_run else ""
    print()
    print(f"  {prefix}Summary:")
    for k, v in sorted(stats.items()):
        print(f"    {k}: {v}")
    print()
