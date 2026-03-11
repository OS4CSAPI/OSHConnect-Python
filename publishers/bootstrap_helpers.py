#!/usr/bin/env python3
"""
bootstrap_helpers.py — Shared idempotent CSAPI resource-creation helpers.

Extracted from the proven bootstrap_iss.py pattern. All functions use stdlib-only
HTTP (urllib) with no external dependencies.

Functions:
  find_by_uid()       — Lookup resource by UID in a collection
  find_datastream()   — Lookup datastream by outputName under a system
  ensure_procedure()  — Create procedure if not exists
  ensure_system()     — Create system (geo+json stub POST → SensorML PUT)
  ensure_datastream() — Create datastream with SWE DataRecord schema
  ensure_deployment() — Create deployment node (with optional parent)
  clean_resource()    — Delete resource by UID if it exists
  api_get/post/put/delete() — Low-level HTTP helpers with retry
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
    """Return server config dict from environment variables."""
    return {
        "base_url": os.environ.get(
            "BOOTSTRAP_URL",
            "https://os4csapi-osh.duckdns.org/sensorhub/api"),
        "user": os.environ.get("OSH_USER", "os4csapi"),
        "password": os.environ.get("OSH_PASS", "ogc134mm"),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  SSL + DNS workarounds (same as bootstrap_iss.py)
# ═══════════════════════════════════════════════════════════════════════════

ORACLE_IP = "129.80.248.53"

_ssl_ctx = _ssl.create_default_context()
_ssl_ctx.check_hostname = True
_ssl_ctx.verify_mode = _ssl.CERT_REQUIRED

_original_getaddrinfo = socket.getaddrinfo

def _patched_getaddrinfo(host, port, *args, **kwargs):
    """Force DNS resolution for DuckDNS to the known Oracle IP."""
    if isinstance(host, str) and "os4csapi-osh.duckdns.org" in host:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ORACLE_IP, port or 443))]
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

    result = api_get(base_url, f"{collection}?uid={uid}", auth)
    if result and "items" in result:
        for item in result["items"]:
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
#  Idempotent resource creation
# ═══════════════════════════════════════════════════════════════════════════

def ensure_procedure(base_url: str, auth: str, uid: str, body: dict,
                     *, dry_run: bool = False, stats: dict = None) -> str | None:
    """Create a procedure if it doesn't already exist. Returns server ID."""
    existing = find_by_uid(base_url, auth, "procedures", uid)
    if existing:
        print(f"  [SKIP] Procedure {uid} already exists (id={existing})")
        if stats:
            stats.setdefault("skipped", 0)
            stats["skipped"] += 1
        return existing

    if dry_run:
        print(f"  [DRY] Would create procedure: {uid}")
        return None

    result = api_post(base_url, "procedures", body, auth)
    new_id = result.get("id") if result else None
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


def ensure_deployment(base_url: str, auth: str, uid: str, body: dict,
                      parent_id: str | None = None,
                      *, dry_run: bool = False, stats: dict = None) -> str | None:
    """Create a deployment node if it doesn't exist. Returns server ID."""
    existing = find_by_uid(base_url, auth, "deployments", uid)
    if existing:
        print(f"  [SKIP] Deployment {uid} already exists (id={existing})")
        if stats:
            stats.setdefault("skipped", 0)
            stats["skipped"] += 1
        return existing

    if dry_run:
        print(f"  [DRY] Would create deployment: {uid}")
        return None

    path = "deployments"
    if parent_id:
        path = f"deployments/{parent_id}/subdeployments"

    result = api_post(base_url, path, body, auth)
    new_id = result.get("id") if result else None
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
