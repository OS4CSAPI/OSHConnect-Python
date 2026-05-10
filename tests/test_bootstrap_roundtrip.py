"""
test_bootstrap_roundtrip.py — integration test for the encoding-correct
two-step bootstrap pattern.

Verifies that ``ensure_procedure`` and ``ensure_deployment`` preserve
SensorML metadata end-to-end:

    POST geo+json stub → PUT application/sml+json body → GET application/sml+json
    → asserts ``keywords`` (and other SensorML-only fields) round-trip.

Also exercises the ``_warn_if_sml_fields_in_stub`` guardrail unconditionally
(no network).

Configuration (set in env to enable the network portion):

    OS4CSAPI_TEST_BASE_URL  — e.g. https://129-80-248-53.sslip.io/csapi-go-upstream
    OS4CSAPI_TEST_USER      — basic-auth username
    OS4CSAPI_TEST_PASS      — basic-auth password
    OS4CSAPI_STRICT_BOOTSTRAP=1  — recommended; turns guardrail warnings into errors

When the network env is missing, the network-dependent tests are skipped
but the offline guardrail tests still run.
"""
from __future__ import annotations

import os
import time
import uuid

import pytest

from publishers.bootstrap_helpers import (
    SML_ONLY_FIELDS,
    _auth_header,
    _warn_if_sml_fields_in_stub,
    api_delete,
    api_get,
    ensure_deployment,
    ensure_procedure,
)


# ─────────────────────────────────────────────────────────────────────
#  Offline tests — no network required
# ─────────────────────────────────────────────────────────────────────

def test_sml_only_fields_includes_expected_set():
    for field in ("keywords", "identifiers", "classifiers", "contacts",
                  "documentation", "documents", "history",
                  "characteristics", "capabilities",
                  "securityConstraints", "legalConstraints"):
        assert field in SML_ONLY_FIELDS, field


def test_warn_if_sml_fields_passes_clean_stub():
    clean_stub = {
        "type": "Feature",
        "geometry": None,
        "properties": {
            "uid": "urn:test:clean",
            "featureType": "sosa:ObservingProcedure",
            "name": "Clean stub",
            "description": "Only geo+json fields under properties.",
            "validTime": ["2024-01-01T00:00:00Z", ".."],
        },
    }
    # No exception, no warning expected.
    _warn_if_sml_fields_in_stub(clean_stub, "test")


def test_warn_if_sml_fields_strict_mode_raises_on_leak(monkeypatch):
    """In strict mode, SensorML fields under properties MUST raise."""
    monkeypatch.setenv("OS4CSAPI_STRICT_BOOTSTRAP", "1")

    # Re-import to pick up the env at module load? The helper reads env
    # at import. Patch the module-level flag for this test.
    import publishers.bootstrap_helpers as bh
    monkeypatch.setattr(bh, "_STRICT_BOOTSTRAP", True)

    leaky_stub = {
        "type": "Feature",
        "properties": {
            "uid": "urn:test:leaky",
            "name": "Leaky stub",
            "keywords": ["this", "leaks"],
        },
    }
    with pytest.raises(RuntimeError, match="ENCODING-CONTRACT"):
        bh._warn_if_sml_fields_in_stub(leaky_stub, "test-leaky")


def test_warn_if_sml_fields_lenient_mode_warns_on_leak(monkeypatch, capsys):
    """In lenient (default) mode, leaks emit a [WARN] line."""
    import publishers.bootstrap_helpers as bh
    monkeypatch.setattr(bh, "_STRICT_BOOTSTRAP", False)
    bh._warn_if_sml_fields_in_stub(
        {"properties": {"uid": "x", "contacts": [{}]}}, "leak-test")
    out = capsys.readouterr().out
    assert "[WARN]" in out
    assert "ENCODING-CONTRACT" in out
    assert "contacts" in out


# ─────────────────────────────────────────────────────────────────────
#  Network tests — require live CSAPI server
# ─────────────────────────────────────────────────────────────────────

_BASE_URL = os.environ.get("OS4CSAPI_TEST_BASE_URL", "").rstrip("/")
_USER = os.environ.get("OS4CSAPI_TEST_USER", "")
_PASS = os.environ.get("OS4CSAPI_TEST_PASS", "")

_HAS_NETWORK_CONFIG = bool(_BASE_URL and _USER and _PASS)
_skip_no_net = pytest.mark.skipif(
    not _HAS_NETWORK_CONFIG,
    reason=("Set OS4CSAPI_TEST_BASE_URL / OS4CSAPI_TEST_USER / OS4CSAPI_TEST_PASS "
            "to enable bootstrap roundtrip integration tests."),
)


def _unique_uid(kind: str) -> str:
    return f"urn:os4csapi:test:{kind}:{uuid.uuid4().hex[:12]}"


def _expected_keywords() -> list[str]:
    return ["alpha", "bravo", "roundtrip", f"ts-{int(time.time())}"]


@_skip_no_net
def test_procedure_roundtrip_preserves_sensorml():
    """Create a procedure with SensorML metadata; GET it back; assert keywords survive."""
    auth = _auth_header(_USER, _PASS)
    uid = _unique_uid("procedure")
    keywords = _expected_keywords()

    stub = {
        "type": "Feature",
        "geometry": None,
        "properties": {
            "uid": uid,
            "featureType": "sosa:ObservingProcedure",
            "name": "Roundtrip Test Procedure",
            "description": "Created by tests/test_bootstrap_roundtrip.py.",
        },
    }
    sml = {
        "type": "SimpleProcess",
        "id": uid,
        "uniqueId": uid,
        "label": "Roundtrip Test Procedure",
        "description": "SensorML body for roundtrip integration test.",
        "keywords": keywords,
        "identifiers": [{
            "definition": "http://sensorml.com/ont/swe/property/ShortName",
            "label": "Short Name",
            "value": "Roundtrip Test",
        }],
    }

    new_id = None
    try:
        new_id = ensure_procedure(_BASE_URL, auth, uid, stub, sml)
        assert new_id, "ensure_procedure returned no id"

        # GET as SensorML
        from urllib.request import Request, urlopen
        import json
        req = Request(f"{_BASE_URL}/procedures/{new_id}", headers={
            "Authorization": auth,
            "Accept": "application/sml+json",
        })
        with urlopen(req, timeout=15) as resp:
            doc = json.loads(resp.read().decode())

        got_keywords = doc.get("keywords") or []
        for kw in keywords:
            assert kw in got_keywords, (
                f"keyword {kw!r} did not round-trip; got {got_keywords!r} "
                f"(SensorML fields probably stripped — encoding-contract bug regressed)"
            )

        assert any(i.get("value") == "Roundtrip Test"
                   for i in (doc.get("identifiers") or [])), \
            f"identifiers did not round-trip; got {doc.get('identifiers')!r}"

    finally:
        if new_id:
            try:
                api_delete(_BASE_URL, f"procedures/{new_id}", auth, cascade=True)
            except Exception:
                pass


@_skip_no_net
def test_deployment_roundtrip_preserves_sensorml():
    """Same contract for deployments."""
    auth = _auth_header(_USER, _PASS)
    uid = _unique_uid("deployment")
    keywords = _expected_keywords()

    stub = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-95.0, 37.0]},
        "properties": {
            "uid": uid,
            "featureType": "sosa:Deployment",
            "name": "Roundtrip Test Deployment",
            "description": "Created by tests/test_bootstrap_roundtrip.py.",
        },
    }
    sml = {
        "type": "Deployment",
        "id": uid,
        "uniqueId": uid,
        "label": "Roundtrip Test Deployment",
        "description": "SensorML body for roundtrip integration test.",
        "keywords": keywords,
    }

    new_id = None
    try:
        new_id = ensure_deployment(_BASE_URL, auth, uid, stub, sml)
        assert new_id

        from urllib.request import Request, urlopen
        import json
        req = Request(f"{_BASE_URL}/deployments/{new_id}", headers={
            "Authorization": auth,
            "Accept": "application/sml+json",
        })
        with urlopen(req, timeout=15) as resp:
            doc = json.loads(resp.read().decode())

        got_keywords = doc.get("keywords") or []
        for kw in keywords:
            assert kw in got_keywords, (
                f"keyword {kw!r} did not round-trip; got {got_keywords!r}"
            )
    finally:
        if new_id:
            try:
                api_delete(_BASE_URL, f"deployments/{new_id}", auth, cascade=True)
            except Exception:
                pass
