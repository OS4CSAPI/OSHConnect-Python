# Upstream Sync Merge Report

**Date:** 2026-05-09
**Branch:** `integrate/upstream-merge-2026-05-09`
**Upstream:** `Botts-Innovative-Research/OSHConnect-Python` @ `main`
**Fork:** `OS4CSAPI/OSHConnect-Python` @ `main` (commit `d8c4058`)

---

## 0. TL;DR

We merged **21 commits / 51 files / +5 048 / −506** of upstream work into our fork without losing any of our 132 ahead-commits. One textual conflict (`README.md`) was resolved by keeping our fork-focused content and appending upstream's MkDocs section. A single real regression — an `AttributeError` on `Node._mqtt_client` triggered by upstream's MQTT/event-bus refactor interacting with `@dataclass`'s auto-generated `__eq__` — was fixed in-place. Test suite: **144 passed, 2 skipped, 4 deselected** (the 4 are pre-existing network-dependent tests requiring a local OSH at `:8282`; they fail identically on `main` without the merge). All 9 publisher modules import cleanly. Branch ready to fast-forward into `main`.

---

## 1. Why we synced

Three drivers:

1. **Silent SensorML field loss bug** — Documented in `Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md`. Upstream commit [`7e6ac05`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/7e6ac05c5d024a634a79e38d5865726fbd9095b8) (*"Prefer `AnyComponent` type over `SerializeAsAny` to prevent loss of data"*) is a direct fix in upstream code for the same root cause we observed locally.
2. **Strict-parsing migration on `/csapi-go-v2`** — While debugging publisher rejections on the new Go server (see `Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md`), it became clear we were patching client-side issues that upstream had already fixed three weeks earlier in their data-model layer.
3. **Drift cost** — We were 21 commits behind / 132 ahead. Each week of further drift makes the merge surface-area larger and the conflict resolution risk higher.

---

## 2. What we pulled in

### Library / data-model fixes (high relevance)

| Commit | Subject |
|---|---|
| [`ea73e22`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/ea73e228615f01b130b185af712a9fcfff0cef66) | Fix longstanding time comparison issue + a deserialization problem |
| [`5541ccd`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/5541ccd492718f752a74422ea62b74446ce97080) | Fix incorrect serialization alias on `VectorSchema` |
| [`7e6ac05`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/7e6ac05c5d024a634a79e38d5865726fbd9095b8) | **Prefer `AnyComponent` over `SerializeAsAny` to prevent data loss** |
| [`5a4a970`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/5a4a97092aea512eb655fe9cce66d100a8eaf92c) | SWE components use `Literal[type_name]` for `type` field |
| [`97cd5e2`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/97cd5e255e98e1a3e3c5a000cc3bdb7e785af00c) | Enforce SWE Common 3 SoftNamedProperty rule |
| [`0d6ef64`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/0d6ef64c140010722735adbba8de8c57b6f1974f) | Bring data models in line with SWECommon 3.0 + validation |
| [`04bee27`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/04bee27fd582cf698c01a2489dd6558e575c4bb2) | Discovery: more reliably attach subresources to parents |

### Feature additions (large, opinionated — accepted with the merge)

| Commit | Subject |
|---|---|
| [`98e63c3`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/98e63c32427a8f5ea34469f072ca61200b910451) | Event-bus framework (initial) |
| [`95bdb6b`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/95bdb6ba932640eecb103153c616bf8efc70b025) | CSAPI Part 3 pub/sub topics, expanded public API |
| [`d7e077e`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/d7e077e55c3a22c9de6c05cd83ee7abeb7547816) | Updates for Part 3 + datastores |
| [`406bd26`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/406bd26e2bb454bebe1b6e44af6a0853b89c4de9) | Refactor event bus into `events/` sub-package, wire lifecycle/streaming |
| [`2e15c29`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/2e15c2973c55fd3d7261133f9ea4470040ec0f08) | SQLite-backed `DataStore` |

### DevX / docs / CI

| Commit | Subject |
|---|---|
| [`de14a46`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/de14a46549c2b1aace8cb3c8583fc52ea5662db5) | Docker + local publish DevX |
| [`853a028`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/853a028883700f6f1289b2cffd2be990bc57dd6c) | Version bump, docs, remove deprecated `to_lower_camel` |
| `1070198`, `02ca719`, `981e5a4`, `3f4b595`, `fe8ae1d`, `5bd72d7`, `c194e2b` | MkDocs migration, GH-Pages workflow, test cleanup |

---

## 3. Conflict resolution

**Single conflict:** `README.md`.

- Our `HEAD` had a fork-focused README (publisher fleet quick-start, fleet summary table, 9 publisher cadence breakdown).
- `upstream/main` had added a "Generating the Docs" MkDocs section.

**Resolution:** Kept our entire fork-focused content verbatim. Appended upstream's MkDocs section after our `## License` heading because that section documents real new files arriving with the merge (`mkdocs.yml`, `docs/markdown/*.md`, `.github/workflows/docs_pages.yaml` updates) and removing it would leave those files undocumented.

No other files conflicted. The 50 other modified/added files merged cleanly because our 132 ahead-commits are concentrated in `publishers/`, `docs/research/`, `scripts/`, `scenarios/` while upstream's 21 are concentrated in `src/oshconnect/` plus new top-level `docs/markdown/`, `mkdocs.yml`, and new tests.

---

## 4. The one real regression: `Node._mqtt_client` AttributeError

### Symptom

```
tests/test_oshconnect.py::TestOSHConnect::test_oshconnect_add_node FAILED
AttributeError: 'Node' object has no attribute '_mqtt_client'.
Did you mean: 'get_mqtt_client'?
```

Triggered by the dataclass-generated `__eq__` on the assertion `assert app._nodes[0] == node`.

### Root cause

`Node` in [`src/oshconnect/streamableresource.py`](../../src/oshconnect/streamableresource.py) is a `@dataclass(kw_only=True)` with a custom `__init__`. The class declares three private fields without defaults:

```python
_basic_auth: bytes
_client_session: OSHClientSession
_mqtt_client: MQTTCommClient
```

Each is assigned conditionally inside `__init__`:

| Field | Assigned only when |
|---|---|
| `_basic_auth` | `username` and `password` are both supplied (via `add_basicauth`) |
| `_client_session` | `session_manager` is passed and `register_with_session_manager` resolves |
| `_mqtt_client` | `kwargs.get('enable_mqtt')` is truthy |

Before upstream's MQTT refactor, the auto-generated `__eq__` happened not to be exercised on uninitialised attributes because the test surface didn't compare `Node` instances. Upstream's event-bus / MQTT refactor wired new code paths (and the new `tests/test_mqtt_topics.py`) that *do* construct and compare `Node`-like objects; combined with our existing `test_oshconnect_add_node` exercising `__eq__`, the latent bug surfaces. The dataclass `__eq__` does `getattr(self, field) == getattr(other, field)` for every declared field; missing attributes raise `AttributeError`.

This is a **pre-existing latent bug in upstream that was unmasked by the merge**, not a bug we introduced. It would have hit upstream's own CI as soon as anyone exercised `Node.__eq__` after [`406bd26`](https://github.com/Botts-Innovative-Research/OSHConnect-Python/commit/406bd26e2bb454bebe1b6e44af6a0853b89c4de9).

### Fix applied

Minimal: add `= None` defaults on the three conditionally-set private fields. Preserves the existing lazy-init pattern (the rest of the codebase already uses `getattr(self, '_mqtt_client', None)` defensively, so `None` is the documented sentinel).

```python
# src/oshconnect/streamableresource.py
_basic_auth: bytes = None
_client_session: OSHClientSession = None
_mqtt_client: MQTTCommClient = None
```

This makes the dataclass-generated `__eq__` see real attribute values (including `None`) on every instance, eliminating the `AttributeError`.

### Why we're not filing upstream

User decision (2026-05-09): documented here instead. Rationale: upstream is on a Part-3 / event-bus push and our patch is one-line; carrying it locally has near-zero maintenance cost. If we re-sync and they've fixed it differently, the merge driver will resolve cleanly. If they haven't, our patch survives. Recorded here for traceability.

---

## 5. Test results after merge + fix

```
============================= test session starts =============================
collected 150 items

tests\test_api_helper.py                                    1 passed
tests\test_bootstrap_roundtrip.py                           4 passed, 2 skipped
tests\test_datastore.py                                    21 passed
tests\test_imports.py                                      14 passed
tests\test_mqtt_topics.py                                  27 passed
tests\test_oshconnect.py                                    3 passed, 4 deselected*
tests\test_resource_datamodels.py                           1 passed
tests\test_schema_equivalence.py                            2 passed
tests\test_serialization.py                                 1 passed
tests\test_streamable_resources.py                          0 passed, 1 deselected*
tests\test_swe_name_validation.py                          35 passed
tests\test_swe_schema_validation.py                        35 passed

================ 144 passed, 2 skipped, 4 deselected in 9.31s =================
```

\* The 4 deselected tests (`test_find_systems`, `test_oshconnect_find_datastreams`, `test_obs_ws_stream`, `test_streamble_observations`) require a live OSH server at `localhost:8282`. They are not merge regressions — they fail identically on pre-merge `main`. They are integration tests masquerading as unit tests.

### Publisher-fleet smoke tests

All 9 publisher bootstrap modules import successfully:

```
oshconnect OK
publishers.nws.bootstrap_nws OK
publishers.iss.bootstrap_iss OK
publishers.ndbc.bootstrap_ndbc OK
publishers.coops.bootstrap_coops OK
publishers.aviation_wx.bootstrap_aviation_wx OK
publishers.opensky.bootstrap_opensky OK
publishers.usgs_water.bootstrap_usgs_water OK
publishers.usgs_nims.bootstrap_usgs_nims OK
publishers.usgs_eq.bootstrap_usgs_eq OK
```

This validates that nothing in upstream's data-model refactor broke our publisher serialisation paths at the import / class-definition level.

---

## 6. What this merge does NOT validate

- **Live publishing against `/csapi-go-v2`.** The strict-parsing rejections documented in `Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md` are server-side; this merge does not address them. We still need to either (a) implement dual-content publication (POST GeoJSON, PUT SensorML) per OGC 23-001, or (b) wait for the Go server to fix its own conformance gaps.
- **Event-bus / Part 3 functionality.** None of our publishers exercise the new `events/` package or Part 3 pub/sub. We accept the new code surface but make no claim it works end-to-end against a real CSAPI Part 3 server.
- **SQLite DataStore.** New, untested in our environment, but isolated behind `datastores/sqlite_store.py` and not pulled into the publisher hot path.

---

## 7. Recommended merge sequence

1. ✅ Branch `integrate/upstream-merge-2026-05-09` pushed
2. ✅ README conflict resolved
3. ✅ `Node._mqtt_client` regression fixed
4. ✅ Test suite green (144 passed)
5. ✅ All 9 publisher imports verified
6. ⏳ Fast-forward `main` to `integrate/upstream-merge-2026-05-09`
7. ⏳ Run one publisher with `--dry-run` against `/csapi-go-v2` to confirm no payload regressions
8. ⏳ Resume strict-parsing remediation work on the now-current main

---

## 8. Cross-references

- [`Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md`](Silent_SensorML_Field_Loss_Engineering_Report_2026-05-06.md) — original observation that motivated this sync
- [`Strict_Parsing_Migration_Findings_Publisher_Fleet_2026-05-09.md`](Strict_Parsing_Migration_Findings_Publisher_Fleet_2026-05-09.md) — initial publisher rejection inventory
- [`Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md`](Strict_Parsing_Migration_Spec_Grounded_Reanalysis_2026-05-09.md) — corrected remediation plan (server-side, not addressed by this merge)
- Upstream commit range: [`d8c4058...upstream/main`](https://github.com/OS4CSAPI/OSHConnect-Python/compare/main...Botts-Innovative-Research:OSHConnect-Python:main)
