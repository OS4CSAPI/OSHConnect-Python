# OSH SensorHub Server Behavior: DELETE Cascade, Re-parenting, and Resource Lifecycle

**Date:** 2026-02-27  
**Author:** AI Research Assistant (Phase 5–6 migration activity)  
**Server Under Test:** OSH SensorHub v2.x at `http://45.55.99.236:8080/sensorhub/api`  
**Applicable Spec:** OGC API — Connected Systems — Part 1: Feature Resources (OGC 23-001r0, Clause 17)

---

## 1. Executive Summary

During the ODAS C-UAS acoustic sensor demonstration (Phases 5–6), we needed to
re-parent three top-level system nodes (AZ-MA-1, AZ-MA-2, AZ-MA-3) as subsystems
of AZ-MA-NET. This required understanding the OSH SensorHub server's behavior
around DELETE operations, cascade semantics, resource lifecycle, and hierarchy
management. This report documents all findings from empirical testing and
cross-references them against the OGC CS API specification.

**Critical finding for your developer friend:** No, the DELETE requests in our
testing and migration scripts did **not** include `?cascade=true`. All DELETE
calls were plain `DELETE /systems/{id}` or `DELETE /datastreams/{id}` with no
query parameters. This is the central reason the server returned HTTP 400 when
we attempted to delete a parent system that had children — the server was
correctly enforcing the spec's default behavior of rejecting non-cascading
deletes on resources with nested sub-resources.

---

## 2. Background: The Re-parenting Problem

### 2.1 Initial State

After the Phase 1 bootstrap, the system hierarchy was flat:

```
Top-level systems (all peers at /systems):
  ├── AZ-MA-NET     (04n0)  — network coordinator
  ├── AZ-MA-1       (04ng)  — acoustic node 1 (13 subsystems)
  ├── AZ-MA-2       (04o0)  — acoustic node 2 (13 subsystems)
  └── AZ-MA-3       (04og)  — acoustic node 3 (13 subsystems)
```

### 2.2 Desired State

```
AZ-MA-NET (04n0)
  ├── AZ-MA-1 (subsystem)  — 13 subsystems, 7 datastreams, 1 control stream
  ├── AZ-MA-2 (subsystem)  — 13 subsystems, 7 datastreams, 1 control stream
  └── AZ-MA-3 (subsystem)  — 13 subsystems, 7 datastreams, 1 control stream
```

### 2.3 Why Re-parenting Is Hard

The OGC CS API spec (Clause 17.3) explicitly states:

> _"There is no operation to 'move' a subsystem from one parent to another.
> To achieve this, the client must first delete the subsystem at its canonical
> URI and recreate it under another parent system."_

This means there is no `PATCH` or `PUT` operation that can change a system's
parent. The only path is: **delete → recreate under new parent**.

---

## 3. Empirical Testing: Server Behavior

We wrote a dedicated test script (`test_cascade.py`) to probe the OSH server's
behavior before attempting the full migration. Each test created disposable
resources and cleaned up afterward.

### 3.1 Test 1: Create Parent + Child, Then DELETE Parent (No Cascade Param)

**Request:**
```
POST /systems                          → 201 (parent created)
POST /systems/{parentId}/subsystems    → 201 (child created)
DELETE /systems/{parentId}             → 400 ❌
GET /systems/{childId}                 → 200 (child survived)
```

**Finding:** The server **refused to delete a parent that has children**. HTTP
400 was returned. The child resource survived intact.

**Spec comparison:** The OGC CS API Clause 17.2, Requirement
`/req/create-replace-delete/system-delete-cascade` states:

> _"A. By default (cascade parameter is not set), the server SHALL reject a
> DELETE request on a System resource that has nested resources (i.e.,
> subsystems, sampling features, datastreams, control streams) or is associated
> with a deployment."_

The server behavior is **correct in intent** — it refuses the delete. However,
the **status code differs from the spec**: the server returned **400 Bad
Request** whereas the conformance test
(`/conf/create-replace-delete/system-delete-cascade`) expects **409 Conflict**:

> _"Issue an HTTP DELETE request at URL `{api_root}/systems/{sysId}?cascade=false`.
> Verify that the server responds with an error code **409**."_

**Conformance gap:** OSH returns 400, spec expects 409.

### 3.2 Test 2: DELETE Datastream → Observations Cascade

**Request:**
```
DELETE /datastreams/{dsId}    → 204 ✅
GET observations for dsId     → 0 results
```

**Finding:** Deleting a datastream **automatically cascades to delete all its
observations**, even without `?cascade=true`. This is expected behavior — 
observations are owned resources of a datastream and cannot exist independently.

### 3.3 Test 3: DELETE Leaf System (No Children)

**Request:**
```
DELETE /systems/{leafId}    → 204 ✅
```

**Finding:** A system with no subsystems, no datastreams, no control streams,
and no deployment associations can be deleted with a plain DELETE.

### 3.4 Test 4: POST with Existing uniqueId (Collision)

**Request:**
```
POST /systems  (body with uniqueId already registered)  → 302 Redirect
```

**Finding:** The server returns a **302 redirect** to the existing resource
rather than creating a duplicate. This prevents uniqueId collisions but also
means you **cannot re-register a system with the same uniqueId while the
original still exists**.

### 3.5 Test 5: PUT to Change Parent (Re-parent Attempt)

**Request:**
```
PUT /systems/{id}  (modified body pointing at different parent)  → No effect
```

**Finding:** PUT replaces the system description but does **not** change its
parent association. Parent-child relationships are structural — they are
determined by the endpoint used during creation
(`POST /systems/{parentId}/subsystems`), not by any property in the resource
body.

---

## 4. The `cascade` Parameter: What We Did NOT Do

### 4.1 What the Spec Says

The OGC CS API spec (Clause 17.2, Requirement 61) defines a `cascade` query
parameter for DELETE on systems:

> _"B. If the request contains the **cascade parameter**, the server SHALL accept
> the DELETE request and delete the System resource as well as **all its nested
> resources**."_

The conformance test specifies:
```
DELETE /systems/{sysId}?cascade=true    → All sub-resources deleted
DELETE /systems/{sysId}?cascade=false   → 409 (rejected)
```

### 4.2 What We Actually Did

**Neither our test script nor our migration script used `?cascade=true`.**

In `test_cascade.py`:
```python
r4 = requests.delete(f'{BASE}/systems/{parent_id}', auth=AUTH)
# No ?cascade=true — plain DELETE
```

In `reparent_nodes.py`:
```python
def delete(self, path: str, label: str = "") -> bool:
    r = self.session.delete(f"{BASE}/{path}")
    # No query parameters — plain DELETE
```

### 4.3 Why We Chose Manual Bottom-Up Deletion

We opted for **manual bottom-up deletion** (datastreams → leaf subsystems →
intermediate systems → top-level node) for several reasons:

1. **Unknown server support:** We did not know whether the OSH SensorHub
   instance actually implements `?cascade=true`. The spec defines it as a
   requirement for conformant servers, but implementation coverage is unknown.

2. **Safety:** Manual deletion gives precise control — we could export SML
   backups of each resource before deleting it, verify each deletion succeeded,
   and abort if any step failed.

3. **Datastream observation cascade was already verified:** We confirmed that
   `DELETE /datastreams/{id}` automatically cascades to observations. So the
   manual approach only needed to explicitly walk the system hierarchy, not the
   observation graph.

4. **Risk mitigation:** A single `DELETE /systems/{id}?cascade=true` on AZ-MA-1
   would delete 13 subsystems, 7+ datastreams, 1+ control stream, and thousands
   of observations in one atomic operation. If it failed partway through, the
   recovery path would be unclear.

### 4.4 What Would Have Been Different with `?cascade=true`

If the server supports `?cascade=true`, the migration could have been reduced
from the 74 individual DELETE operations we performed to just **3 DELETE calls**:

```
DELETE /systems/04ng?cascade=true    → AZ-MA-1 + all children + all DS + all obs
DELETE /systems/04o0?cascade=true    → AZ-MA-2 + all children
DELETE /systems/04og?cascade=true    → AZ-MA-3 + all children
```

This would have been significantly simpler. **Testing `?cascade=true` on the OSH
server is a recommended follow-up action.**

---

## 5. Migration Strategy Executed

Given the constraints discovered in Section 3, the migration used a
**bottom-up delete → top-down recreate** strategy:

### Phase 1: Delete (Bottom-Up)

For each of AZ-MA-1, AZ-MA-2, AZ-MA-3:

```
1. For each of 13 subsystems:
   a. DELETE all datastreams (→ cascades to observations)
   b. DELETE all control streams
   c. DELETE the subsystem (now a leaf)
2. DELETE own datastreams
3. DELETE own control streams
4. DELETE the node system (now a leaf)
```

### Phase 2: Recreate (Top-Down)

```
1. POST /systems/04n0/subsystems  → AZ-MA-1 (as subsystem of AZ-MA-NET)
2. POST /systems/{newMA1}/subsystems  → 13 subsystems of AZ-MA-1
3. Repeat for AZ-MA-2 and AZ-MA-3
4. Recreate datastreams and control streams for all systems
5. Re-enrich with SensorML metadata
6. Replay observations
```

### Results

| Metric | Count |
|--------|-------|
| Systems deleted | 42 |
| Datastreams deleted | 22 |
| Control streams deleted | 10 |
| **Total DELETE operations** | **74** |
| Systems recreated | 42 |
| Datastreams recreated | 22 |
| Control streams recreated | 13 |
| **Total POST operations** | **77** |
| Failures | **0** |

The server reassigned new internal IDs to all recreated resources, but uniqueIds
were preserved.

---

## 6. Conformance Observations

### 6.1 Status Code for Rejected Delete

| Behavior | OSH SensorHub | Spec (OGC 23-001r0) | Conformant? |
|----------|--------------|---------------------|-------------|
| DELETE parent with children (no cascade) | **400 Bad Request** | **409 Conflict** | ❌ Wrong code |
| DELETE leaf system | 204 No Content | 200 or 204 | ✅ |
| DELETE datastream (→ cascade to obs) | 204 No Content | 200 or 204 | ✅ |
| POST with duplicate uniqueId | 302 Redirect | Not specified explicitly | ⚠️ Undefined |
| PUT to change parent | Silent no-op | No re-parent operation defined | ✅ (by omission) |

### 6.2 Untested: `?cascade=true`

We did not test whether the OSH server accepts `DELETE /systems/{id}?cascade=true`.
This remains an open question. The spec requires conformant servers to support it
(Requirement 61B).

### 6.3 Untested: `?cascade=false` (Explicit)

We did not test whether passing `?cascade=false` explicitly changes the status
code from 400 to 409 or any other behavior. The spec's conformance test uses
`?cascade=false` to explicitly verify the rejection.

---

## 7. Recommendations

### 7.1 For OSHConnect-Python Library

1. **Add a `cascade` parameter** to the DELETE helper for systems. Default to
   `False` but allow `True` for convenience.

2. **Document the bottom-up deletion pattern** as a fallback strategy for servers
   that don't implement `?cascade=true`.

3. **Add a server conformance probe** that tests `?cascade=true` on a disposable
   test resource to determine server capabilities before running migrations.

### 7.2 For Upstream (OSH SensorHub)

1. **Status code fix:** Return 409 Conflict (not 400 Bad Request) when rejecting
   DELETE of a system with nested resources.

2. **Implement `?cascade=true`** if not already supported — this is a spec
   requirement for the Create/Replace/Delete conformance class.

### 7.3 For Future Migrations

1. **Always test `?cascade=true`** on a disposable resource before attempting a
   large migration. If supported, it dramatically simplifies the process.

2. **Export SML backups** before any destructive operation regardless of approach.

3. **Use the manual bottom-up strategy** as a universal fallback — it works on
   any server regardless of `cascade` support.

---

## 8. Appendix: Relevant Spec Excerpts

### Clause 17.2 — Systems (Create/Replace/Delete)

**Requirement `/req/create-replace-delete/system`:**
- CREATE at `{api_root}/systems` via HTTP POST
- REPLACE and DELETE at `{api_root}/systems/{id}` via HTTP PUT and DELETE

**Requirement `/req/create-replace-delete/system-delete-cascade`:**
- A. By default (cascade parameter is not set), the server SHALL reject a DELETE
  request on a System resource that has nested resources (subsystems, sampling
  features, datastreams, control streams) or is associated with a deployment.
- B. If the request contains the cascade parameter, the server SHALL accept the
  DELETE request and delete the System resource as well as all its nested
  resources.
- C. If the System resource is associated with a Deployment, the Deployment SHALL
  be updated, removing the link to the System.

### Clause 17.3 — Subsystems

> _"There is no operation to 'move' a subsystem from one parent to another. To
> achieve this, the client must first delete the subsystem at its canonical URI
> and recreate it under another parent system."_

### Conformance Test A.11 — system-delete-cascade

```
1. DELETE /systems/{sysId}?cascade=false  → Expect 409
2. DELETE /systems/{sysId}?cascade=true   → Expect success; verify all
   sub-resources deleted
3. If system is referenced by a Deployment, verify Deployment updated
   (link removed) but Deployment itself still exists
```

---

## 9. Test Scripts Referenced

| Script | Location | Purpose |
|--------|----------|---------|
| `test_cascade.py` | `csapi-explorer/test_cascade.py` | Probes OSH server DELETE behavior |
| `reparent_nodes.py` | `csapi-explorer/scripts/reparent_nodes.py` | Full migration: bottom-up delete → top-down recreate |
| `bootstrap.py` | `OSHConnect-Python/scenarios/.../bootstrap.py` | Original system ingestion (Phase 1) |

---

## 10. Conclusion

The OSH SensorHub server correctly protects against accidental recursive deletion
by rejecting plain DELETE on systems with children. However, we **did not use or
test the `?cascade=true` parameter** defined by the OGC CS API spec, which should
enable single-request recursive deletion. Our migration instead used manual
bottom-up deletion (74 operations), which is a universally safe approach but
significantly more complex than a cascade delete would be. 

Testing `?cascade=true` support on the OSH server is the most impactful follow-up
action from this research — if supported, future hierarchy restructuring
operations can be reduced from dozens of HTTP calls to just a handful.

The minor conformance gap (400 vs 409 status code) should be reported upstream
to the OSH SensorHub project.
