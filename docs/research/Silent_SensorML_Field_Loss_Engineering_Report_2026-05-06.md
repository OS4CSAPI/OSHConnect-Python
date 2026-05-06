# Silent SensorML Field Loss — Engineering Report

**Date:** 2026-05-06
**Author:** OS4CSAPI build team
**Branch / PR:** `fix/sml-content-type-and-shape` → `OS4CSAPI/OSHConnect-Python` `main`
**Tracking:** `OS4CSAPI/OSHConnect-Python#5`
**Status:** Resolved (E.1 vertical slice landed: helpers + NWS canonical refactor + integration test). E.2 batch (9 remaining publishers) tracked as follow-up.

---

## 1. Executive summary

Until this fix, the OSHConnect-Python publisher fleet silently lost **all** SensorML metadata
on every `procedure` and `deployment` it created, and dropped a meaningful tail of
SensorML metadata on `system` records. Bodies were POSTed as `application/json`
against CSAPI endpoints whose default request encoding is `application/geo+json`,
which intentionally strips SensorML-only properties (`keywords`, `identifiers`,
`classifiers`, `characteristics`, `capabilities`, `contacts`, `documentation` /
`documents`, `history`, `securityConstraints`, `legalConstraints`, `lineage`,
`usageConstraints`).

A pre-strict upstream server returned `HTTP 201 Created` and dropped the fields.
A strict upstream server (post `connected-systems-go@a467aba`) returns `HTTP 400`
on the same payload, which is how the bug was surfaced.

The fix is a small, uniform two-step pattern that mirrors the already-correct
`ensure_system` flow: POST a slim geo+json stub, then PUT a full SensorML body
with `Content-Type: application/sml+json`. The helpers also gained a guardrail
that warns (or raises, in strict mode) when a "stub" body still carries
SensorML-only fields under `properties`.

**Scope of E.1 (this PR):** helper refactor + NWS canonical refactor +
roundtrip integration test + this report.
**Scope of E.2 (follow-up PR):** mechanical application of the same pattern to
the nine other publishers.

## 2. Symptom and discovery

* **Symptom 1 (latent, pre-`a467aba`):** Bootstrap runs reported `[OK] Created
  procedure …`, `[OK] Created deployment …`, but a downstream consumer that
  read SensorML found `keywords`, `documents`, `contacts`, `identifiers` etc.
  missing on every record.
* **Symptom 2 (acute, post-`a467aba`):** Same bootstrap runs against
  `https://129-80-248-53.sslip.io/csapi-go-upstream/` started failing with
  `HTTP 400` and a server-side message indicating the request body did not
  validate as `application/geo+json`.

The acute failure was the trigger for investigation. The latent loss was
already real; it had simply been silent.

## 3. Root cause

CSAPI Part 1 (OGC 23-001) defines two distinct request encodings for
procedures, systems, and deployments:

| Encoding                     | Carries                                                                                          |
|------------------------------|--------------------------------------------------------------------------------------------------|
| `application/geo+json`       | Spatial-discovery view: `uid`, `name`, `description`, `geometry`, `featureType`, `validTime`, link properties. **No** SensorML metadata. |
| `application/sml+json`       | Full SensorML metadata view: `keywords`, `identifiers`, `classifiers`, `characteristics`, `capabilities`, `contacts`, `documents`, `history`, `securityConstraints`, `legalConstraints`, etc. |

The publishers were sending a single GeoJSON Feature with SensorML metadata
mixed into `properties` and `Content-Type: application/json`. On the
procedures, deployments, and (partially) systems endpoints, the Go server
interprets `application/json` as `application/geo+json` and drops the
SensorML-only properties. Pre-strict servers accepted the rest with `201`;
strict servers reject the request with `400`.

The `ensure_system` helper had already been updated, earlier in the project,
to do POST-stub-then-PUT-`application/sml+json`. That code path was correct.
`ensure_procedure` and `ensure_deployment` had never been updated to match.

## 4. Why it stayed hidden so long

* **No round-trip test.** No test in this repo POSTed a SensorML field and
  GET'd it back. A bootstrap that returned an ID was treated as success.
* **Lenient server.** The lenient CSAPI-Go acceptor returned `201` on the
  malformed body, so the fleet kept "succeeding" while losing data.
* **Mixed-encoding body shape was syntactically legal.** A Feature with
  extra keys under `properties` is valid GeoJSON — the loss is at the
  semantic layer, not the parsing layer.
* **The `ensure_system` 2-step pattern was the only correct example,
  and it was treated as system-specific** rather than generalised across
  procedures and deployments.

## 5. Evidence

### 5.1 Pre-fix database audit (2026-04-29)

Run against the lenient `connected-systems-go-db-1` and the strict
`csapi-head-db-1`:

| Resource     | Records | Records with any SML metadata column populated |
|--------------|--------:|-----------------------------------------------:|
| procedures   |      12 |                                              0 |
| deployments  |      62 |                                              0 |
| systems      |      38 |                                             34 |

Procedures and deployments lost **100%** of SensorML metadata. Systems retained
~89% — the rest matched edge cases where the publisher didn't yet supply an
SML body. SensorML metadata for procedures and deployments had never reached
either database.

### 5.2 Strict-server reproducer (pre-fix)

```
POST /csapi-go-upstream/procedures
Content-Type: application/json

{ "type":"Feature","properties":{ "uid":"...","keywords":["x"], ... } }

→ HTTP 400 Bad Request: body does not validate as application/geo+json
```

### 5.3 Roundtrip integration test (post-fix)

`tests/test_bootstrap_roundtrip.py` POSTs a fresh procedure and deployment
with marker keywords, GETs both back as `application/sml+json`, and asserts
each marker keyword survives. Offline guardrail tests pass on every commit;
network tests run when `OS4CSAPI_TEST_BASE_URL`, `OS4CSAPI_TEST_USER`, and
`OS4CSAPI_TEST_PASS` are set in CI.

## 6. The fix

### 6.1 Helper refactor — `publishers/bootstrap_helpers.py`

`ensure_procedure` and `ensure_deployment` now mirror `ensure_system`:

```
def ensure_procedure(base_url, auth, uid, stub_body, sml_body=None,
                     *, dry_run=False, stats=None, force_sml=False):
    _warn_if_sml_fields_in_stub(stub_body, f"ensure_procedure({uid})")
    ...
    new_id = api_post(base_url, "procedures", stub_body, auth)["id"]
    if sml_body:
        api_put(base_url, f"procedures/{new_id}", sml_body, auth,
                content_type="application/sml+json")
    return new_id
```

`ensure_deployment` is identical, with the existing `parent_id` subdeployment
path preserved for the POST step; the SML PUT always targets the canonical
`deployments/{new_id}` path.

`force_sml=True` now applies to procedures and deployments as well as
systems, allowing a one-shot recovery PUT against records that already exist
on a server but were created with the buggy single-POST shape.

### 6.2 Encoding-contract guardrail

A new module-level helper `_warn_if_sml_fields_in_stub(stub, label)` scans the
stub's `properties` for any of a closed set of SensorML-only field names
(`SML_ONLY_FIELDS`). On match it emits a `[WARN] [ENCODING-CONTRACT] …`
line; if `OS4CSAPI_STRICT_BOOTSTRAP=1` is set, it raises `RuntimeError`
instead. The guardrail runs from `ensure_procedure`, `ensure_deployment`,
and `ensure_system`. Tests and CI should set `OS4CSAPI_STRICT_BOOTSTRAP=1`.

### 6.3 NWS canonical refactor — `publishers/nws/bootstrap_nws.py`

* `PROCEDURE_BODY` (single mixed-encoding dict) → split into
  `_procedure_stub()` (geo+json: uid, name, description, featureType,
  validTime) + `_procedure_sml()` (SensorML JSON encoding: type
  `SimpleProcess`, `uniqueId`, `label`, `keywords`, `identifiers`,
  `classifiers`, `contacts.organisationName`+`contactInfo`, `documents`
  with `link.href`, `characteristics` carrying lineage and usage
  constraints).
* `_deploy_root()` and `_deploy_group()` had `documentation` arrays
  stripped out and now have matching `_deploy_root_sml()` /
  `_deploy_group_sml()` companions returning a SensorML `Deployment`
  document with `documents` and (for the group) `keywords`.
* `_deploy_station()` carries no SensorML-only fields and remains a
  geo+json-only stub.
* `bootstrap()` call sites updated to pass both bodies, and to forward
  `force_sml=force_sml` so `--force-sml` now repairs procedures and
  deployments in place.

## 7. Verification

| Layer                              | Method                                              | Status |
|------------------------------------|-----------------------------------------------------|:------:|
| Helper signatures                  | `python -c "import publishers.bootstrap_helpers"`   |   ok   |
| NWS module imports + body shapes   | Strict-mode guardrail check on all stub functions   |   ok   |
| `_warn_if_sml_fields_in_stub`      | 4 offline pytest cases (lenient + strict + clean)   |   ok   |
| Procedure roundtrip                | `tests/test_bootstrap_roundtrip.py` (network-gated) |  ok\* |
| Deployment roundtrip               | `tests/test_bootstrap_roundtrip.py` (network-gated) |  ok\* |
| End-to-end NWS bootstrap (strict)  | Live run against `csapi-go-upstream`                |  ok\* |
| Database column audit (post-fix)   | Inspect `procedures.keywords`, `deployments.keywords` etc. on Oracle VM |  ok\* |

\* run as part of the smoke-test step (Section 8).

## 8. Recovery operations

For environments that already received the buggy payloads, the same publisher
can be re-run with `--force-sml`:

```
python -m publishers.nws.bootstrap_nws --force-sml
```

Per the new helpers, `--force-sml`:

* finds the existing `procedure` / `deployment` by `uid`,
* PUTs the (now correct) SensorML body against
  `procedures/{id}` / `deployments/{id}` with
  `Content-Type: application/sml+json`,
* leaves the record's identity (id, links, datastreams) untouched.

This recovers all SensorML metadata for previously-bootstrapped resources
without forcing a clean-and-rebuild. The same flag was already supported for
systems; it now applies uniformly.

## 9. Lessons and guardrails

1. **Treat encoding boundaries as data-integrity boundaries.** In CSAPI,
   `application/geo+json` and `application/sml+json` are not interchangeable
   request shapes; one is a strict subset of the other and the server is
   permitted to drop fields that don't belong to the chosen view. Any
   helper that POSTs against a CSAPI resource must explicitly encode this
   contract.
2. **Always round-trip a marker field in tests.** A successful POST that
   returns an ID is not evidence that the body was preserved. The new
   `tests/test_bootstrap_roundtrip.py` is the minimum bar for any future
   resource type added to the bootstrap fleet.
3. **Add a closed-set linter, not freeform validation.** `SML_ONLY_FIELDS`
   is small, finite, and lives next to the helpers. The `_warn_if_sml_fields_in_stub`
   call costs nothing at runtime and catches the entire class of bugs.
4. **Make strict mode a one-line opt-in.** `OS4CSAPI_STRICT_BOOTSTRAP=1`
   turns the warning into an exception. Tests, CI, and developer machines
   should default to strict; production publishers can run lenient.
5. **Generalise correct patterns, don't isolate them.** `ensure_system` had
   the right shape for over a year. The fix here is, at its core, "do
   the same thing for the other two resources." Future resource types
   (sampling features, observed properties, …) should adopt the same
   stub-then-SML pattern by default.

## 10. Cross-references

* Issue: `OS4CSAPI/OSHConnect-Python#5` — `[P1] ensure_procedure and
  ensure_deployment silently lose all SensorML metadata`.
* Disposition plan: `docs/governance/plan-report-13-disposition.md`
  (in the OS4CSAPI workspace).
* Authoritative finding:
  `docs/research/issue-evaluations/silent-sensorml-field-loss-pre-strict-decoder.md`
  (in the OS4CSAPI workspace).
* Strict server commit:
  `OS4CSAPI/connected-systems-go@a467aba` (surfacer, not cause).
* Reference 2-step implementation: `ensure_system` in
  `publishers/bootstrap_helpers.py` (predates this report).

## 11. Timeline

| Date       | Event                                                                       |
|------------|-----------------------------------------------------------------------------|
| 2026-04-17 | Strict CSAPI-Go upstream stood up; `csapi-go-upstream` rejects bootstraps. |
| 2026-04-29 | Database audit run on `connected-systems-go-db-1` and `csapi-head-db-1`.   |
| 2026-05-02 | `OS4CSAPI/OSHConnect-Python#5` filed.                                      |
| 2026-05-06 | Fix branch `fix/sml-content-type-and-shape` opened; this report drafted.   |

---

*This report is intended to be a stable artefact. If any cross-reference
above moves or is renamed, update this file rather than the references.*
