# OSH SensorHub: Ghost Resource / Stale Collection Index Bug

**Date:** 2026-02-27  
**Server:** `http://45.55.99.236:8080/sensorhub/api` (OSH SensorHub)  
**OGC Spec Reference:** OGC Connected Systems API (OGC 23-001r0), Clause 7.4 (Collections)  
**Investigation Scripts:** [`fix_tripod_toplevel.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/fix_tripod_toplevel.py), [`purge_ghosts.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/purge_ghosts.py), [`ghost_check.py`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/scripts/ghost_check.py)  
**Explorer Commit:** [`358e443`](https://github.com/OS4CSAPI/ogc-csapi-explorer/commit/358e443) (ghost warning UI)  
**Severity:** Medium — data corruption in collection index; no data loss; no client-side workaround to purge  

---

## 1. Executive Summary

When deleting a system resource that was registered at **both** the top level (`POST /systems`) **and** as a subsystem (`POST /systems/{parentId}/subsystems`), the OSH SensorHub server successfully removes the resource from its individual store (direct `GET` returns 404) but **fails to remove it from the collection listing endpoint** (`GET /systems?limit=N`). This creates "ghost" entries — resources that appear in collection listings with full GeoJSON data but return 404 on direct access, and cannot be deleted via the REST API.

The bug was discovered during a data migration to fix 3 Tripod Platform systems that had been incorrectly double-registered (once top-level, once as subsystem). After successful deletion, the old IDs persisted indefinitely in collection listings and search results despite returning 404 on all direct access.

**Key facts:**

| Property | Value |
|----------|-------|
| Ghost entries created | 3 (IDs: `04p0`, `04vg`, `0560`) |
| `GET /systems/{ghostId}` | **404 Not Found** |
| `DELETE /systems/{ghostId}` | **404 Not Found** |
| `GET /systems?limit=100` | **Includes ghost with full GeoJSON** |
| `GET /systems?q=tripod` | **Returns all 3 ghosts** |
| `POST /systems` with same UID | **201 Created** — updates listing data but GET still returns 404 |
| Purgeable from client side? | **No** |

---

## 2. Background: How the Double Registration Occurred

During the Phase 2 bootstrap of the ODAS C-UAS acoustic sensor demo, 3 Tripod Platform systems were inadvertently registered twice:

1. **First registration:** The original Phase 1 bootstrap script registered them as top-level systems via `POST /systems` (assigned server IDs `04p0`, `04vg`, `0560`).

2. **Second registration:** The Phase 2 enrichment script registered them again as subsystems via `POST /systems/{parentId}/subsystems` using a **different UID namespace** (`urn:os4csapi:platform:az-ma-X:tripod` vs the original `urn:os4csapi:system:odas:az-ma-X:tripod`). Because the UIDs differed, the server did not detect a collision and created new entries (IDs `05cg`, `05d0`, `05dg`).

The result was 3 tripods existing as both root-level systems AND subsystems — a logically incorrect state, but one the server permitted because the uniqueIds were different.

### Discovery

The anomaly was discovered while investigating why tripod systems showed no parent context in the Explorer UI when accessed from the top-level system listing. Probing revealed:

- `GET /systems` returned **39 systems** including the 3 tripods
- `GET /systems/04ng/subsystems` returned the same tripods under their correct parent
- All other subsystems (39 of them) correctly appeared **only** via nested endpoints, not in the top-level listing
- The 3 tripods were the sole anomaly — they appeared at both levels

---

## 3. The Fix Attempt and Ghost Creation

### 3.1 Migration Script: `fix_tripod_toplevel.py`

Strategy: Delete the 3 top-level tripod registrations and recreate them as subsystem-only.

**Phase 1 — Inspect:**
```
04p0 = AZ-MA-1 TRIPOD
  nested: {subsystems: 0, datastreams: 0, controlstreams: 0}
  is subsystem of 04ng (AZ-MA-1): True   ← confirmed it exists at both levels

04vg = AZ-MA-2 TRIPOD  
  nested: {subsystems: 0, datastreams: 0, controlstreams: 0}
  is subsystem of 04o0 (AZ-MA-2): True

0560 = AZ-MA-3 TRIPOD
  nested: {subsystems: 0, datastreams: 0, controlstreams: 0}
  is subsystem of 04og (AZ-MA-3): True
```

**Phase 2 — Delete (plain DELETE, no cascade needed — no nested resources):**
```
DELETE /systems/04p0  →  HTTP 204 ✅
DELETE /systems/04vg  →  HTTP 204 ✅
DELETE /systems/0560  →  HTTP 204 ✅
```

**Phase 3 — Recreate as subsystem-only (different UID to avoid collision):**
```
POST /systems/04ng/subsystems  →  HTTP 201 → new ID: 05cg
POST /systems/04o0/subsystems  →  HTTP 201 → new ID: 05d0  
POST /systems/04og/subsystems  →  HTTP 201 → new ID: 05dg
```

**Phase 4 — Verify:**
```
New IDs NOT in top-level listing: ✅ (correct)
New IDs ARE subsystems of parents: ✅ (correct)
Old IDs still in top-level listing: ❌ (BUG — ghosts)
```

### 3.2 Immediate Post-Delete Observations

Immediately after the DELETE operations returned 204:

| Action | Result |
|--------|--------|
| `GET /systems/04p0` | **404** — resource is deleted |
| `GET /systems/04vg` | **404** — resource is deleted |
| `GET /systems/0560` | **404** — resource is deleted |
| `GET /systems?limit=100` | **Still includes 04p0, 04vg, 0560** with full data |
| `GET /systems?q=tripod` | **Returns all 3 ghosts** with names, coordinates, UIDs |

The collection endpoint serves full GeoJSON Feature objects for these ghosts — not stubs or placeholders. The listing returns complete `type`, `id`, `geometry`, and `properties` including `name`, `uid`, `featureType`, `description`, and `validTime`.

---

## 4. Investigation: Attempting to Purge Ghosts

### 4.1 Re-DELETE Attempts

Repeated DELETE calls on ghost IDs all return 404:

```
DELETE /systems/04p0            → 404
DELETE /systems/04p0?cascade=true → 404
DELETE /systems/04vg            → 404
DELETE /systems/0560            → 404
```

The resource is gone from the individual store — there is nothing left to delete.

### 4.2 POST with Same UID (Re-create then Delete)

Hypothesis: POST a new system with the same `uniqueId` as the ghost, then DELETE the newly created resource. If the server links them in its index, this might purge the ghost.

```
POST /systems  (uniqueId: urn:os4csapi:system:odas:az-ma-1:tripod)
→ HTTP 201
→ Location: /systems/04p0   ← SERVER REUSES THE SAME ID!
```

The server returned 201 (Created) and reused the ghost's original ID `04p0`. The listing immediately updated to show the new `label` value. However:

```
GET /systems/04p0  → 404   ← STILL 404!
DELETE /systems/04p0 → 404  ← STILL CAN'T DELETE!
```

**Critical finding:** The POST operation successfully writes to the collection index (the listing reflects the new name), but the resource is **not accessible** via direct GET or deletable via DELETE. The collection index and the individual resource store are **desynchronized**.

### 4.3 POST as Subsystem (Re-parent via UID)

Hypothesis: POST the ghost UID to the subsystem endpoint, which might move the index entry out of the top-level listing.

```
POST /systems/04ng/subsystems  (uniqueId: urn:os4csapi:system:odas:az-ma-1:tripod)
→ HTTP 400: "Ingest Error: Feature is already associated to another parent"
```

The server's internal model still considers the ghost UID as being "associated to another parent" (presumably the now-non-existent top-level registration). This blocks re-registration as a subsystem.

### 4.4 PUT on Ghost ID

```
PUT /systems/04p0  (new SensorML body)
→ HTTP 404
```

PUT cannot reach the ghost resource either.

### 4.5 Summary of Purge Attempts

| Method | Result | Explanation |
|--------|--------|-------------|
| `DELETE /systems/{ghostId}` | 404 | Already deleted from resource store |
| `DELETE /systems/{ghostId}?cascade=true` | 404 | Same — nothing to cascade |
| `POST /systems` (same UID) then `DELETE` | 201 → 404 | POST updates index only; DELETE still 404 |
| `POST /subsystems` (same UID) | 400 | "Already associated to another parent" |
| `PUT /systems/{ghostId}` | 404 | Cannot update — not in resource store |

**Conclusion:** The ghost entries **cannot be purged via the REST API.** They would require direct database access or a server restart/index rebuild.

---

## 5. Final Mitigation

Since the ghosts cannot be removed, we applied two mitigations:

### 5.1 Restore Ghost Names

The purge attempts had left ghost entries with names like "CLEANUP-1" and "DELETE-ME". We restored them to recognizable names with explanatory descriptions via POST:

```python
POST /systems  →  label: "AZ-MA-1 TRIPOD"
                   description: "[Ghost] Server index artifact – use subsystem 05cg instead"
```

This ensures anyone browsing the system listing sees a clear explanation rather than confusing placeholder names.

### 5.2 Explorer UI: Ghost Resource Warning Banner

Added a prominent yellow "Ghost Resource" warning banner to the Explorer's ResourceDetail component. When a user clicks a resource that returns 404 from the server:

- A **large amber banner** with warning icon and "Ghost Resource" heading appears above the detail view
- The message explains: _"This resource no longer exists on the server (HTTP 404). It appears in the listing due to a stale server index — the data shown below is cached from the list and may be outdated."_
- The cached list data is still displayed below the banner so the user can see what the ghost entry contains

Implementation: [`ResourceDetail.vue`](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/demo/acoustic-cuas-targeting/demo/src/components/ResourceDetail.vue) — 404-specific error path with `errorSeverity: 'warn'` and `.ghost-banner` CSS class.

---

## 6. Root Cause Analysis

### 6.1 Dual-Registration as Precondition

The bug requires a system to be registered at **two levels** — as both a top-level system and a subsystem under a parent. This is a valid (if unusual) server state because:

1. The OGC CS API spec does not explicitly forbid a system from existing at multiple levels
2. Different `uniqueId` values mean no collision detection triggers
3. The server accepts both POSTs and creates separate index entries

### 6.2 DELETE Removes from Resource Store Only

When `DELETE /systems/{id}` is called:

1. ✅ The resource is removed from the **individual resource store** (GET returns 404)
2. ✅ The subsystem association is removed (no longer appears in parent's `/subsystems`)  
3. ❌ The resource is **NOT removed from the collection listing index**

This suggests the collection listing index (which powers `GET /systems?limit=N` and `GET /systems?q=...`) is maintained separately from the individual resource store, and the DELETE operation does not properly propagate to both stores.

### 6.3 POST Creates in Index Only

When `POST /systems` is called with a `uniqueId` that matches a ghost:

1. ❌ No new entry is created in the **individual resource store** (GET still returns 404)
2. ✅ The **collection listing index** entry is updated (new name/description appears)
3. The server returns `201 Created` with `Location: /systems/{originalId}`, reusing the ghost's ID

This confirms the two stores are desynchronized — the index has an entry the resource store does not.

### 6.4 Likely Cause: Missing Index Cleanup on Dual-Registered Resources

The DELETE operation likely cleans up:
- The resource entry keyed by server ID
- The subsystem parent-child association

But fails to clean up:
- The collection listing entry that was created by the original `POST /systems` (top-level registration)

For a normally registered system (single registration), DELETE presumably cleans up both stores correctly. The bug manifests only when a resource has entries in multiple index pathways.

---

## 7. Affected Resources

| Ghost ID | Original Name | UID | Correct Subsystem ID | Parent |
|----------|--------------|-----|---------------------|--------|
| `04p0` | AZ-MA-1 TRIPOD | `urn:os4csapi:system:odas:az-ma-1:tripod` | `05cg` | AZ-MA-1 (`04ng`) |
| `04vg` | AZ-MA-2 TRIPOD | `urn:os4csapi:system:odas:az-ma-2:tripod` | `05d0` | AZ-MA-2 (`04o0`) |
| `0560` | AZ-MA-3 TRIPOD | `urn:os4csapi:system:odas:az-ma-3:tripod` | `05dg` | AZ-MA-3 (`04og`) |

Current state of the listing:
- **39 total systems** in `GET /systems` — 36 real + 3 ghosts
- Ghosts appear in `?q=tripod` search results and in paginated listings
- Ghosts show `[Ghost] Server index artifact` in their description field
- All 3 correct subsystem-only tripods (05cg, 05d0, 05dg) are working normally with parent links

---

## 8. Spec Conformance Analysis

### 8.1 Relevant Requirements

**Clause 7.4 — Resource Collections:**
> After a successful DELETE operation, the deleted resource SHALL NOT appear in subsequent collection responses (GET on the collection endpoint).

**Clause 17.2 — System DELETE:**
> After a successful DELETE (HTTP 200 or 204), the system and all traces of it SHALL be removed.

### 8.2 Conformance Gaps

| Requirement | Expected Behavior | Actual Behavior | Conformant? |
|-------------|-------------------|-----------------|:-----------:|
| DELETE removes from collection | Ghost absent from `GET /systems` | Ghost still listed | ❌ |
| DELETE is idempotent / complete | All references removed | Index entry persists | ❌ |
| Collection reflects current state | Only existing resources listed | Deleted resources included | ❌ |
| POST with existing UID | 302 redirect or 409 conflict | 201 Created (index-only update) | ❌ |

### 8.3 Impact Assessment

- **Data integrity:** Medium — the listing returns stale/incorrect data for ghost entries
- **Operational impact:** Low — all real resources function correctly; ghosts are identifiable
- **Client impact:** Medium — clients relying on collection listings will see resources they cannot access, potentially causing 404 errors and confusion
- **Scope:** Only affects dual-registered resources (both top-level and subsystem). Normal single-registration resources are not affected.

---

## 9. Recommendations

### 9.1 For OSH SensorHub (Upstream)

1. **Index cleanup on DELETE:** Ensure that `DELETE /systems/{id}` removes the resource from ALL indices — individual resource store, collection listing index, and search index.

2. **Index consistency check:** Add a server health endpoint or admin command that reconciles the collection listing index against the resource store and removes orphaned entries.

3. **Prevent dual registration:** When a system is POSTed as a subsystem, if the same `uniqueId` already exists as a top-level system, either reject the POST or automatically remove the top-level listing entry.

### 9.2 For OSHConnect-Python

1. **Ghost detection in list operations:** When iterating over collection results, optionally follow up with a HEAD/GET on each item to verify it actually exists. Flag items that return 404 as ghost entries.

2. **Document the known limitation:** Add a note to the library documentation that dual-registered resources can create ghost entries on DELETE.

3. **Avoid dual registration in bootstrap scripts:** Ensure that bootstrap/ingestion scripts never register the same logical resource at both the top level and as a subsystem. Use a single registration pathway.

### 9.3 For CSAPI Explorer (Webapp)

1. ✅ **Already implemented:** Ghost resource warning banner in ResourceDetail (commit `358e443`)
2. **Future:** Consider filtering ghost entries from list results by performing a lightweight existence check (HEAD request) and showing a visual indicator in the list view itself.

---

## 10. Reproduction Steps

To reproduce this bug on a clean OSH SensorHub instance:

```python
import requests, json, time

BASE = "http://<server>/sensorhub/api"
AUTH = ("user", "pass")
SML_CT = {"Content-Type": "application/sml+json", "Accept": "application/json"}
GEO_H = {"Accept": "application/geo+json"}

def ordered(d):
    o = {"type": d["type"]}
    o.update({k:v for k,v in d.items() if k != "type"})
    return json.dumps(o)

# Step 1: Create a parent system
parent_sml = {"type": "PhysicalSystem", "uniqueId": "urn:test:ghost-repro:parent", "label": "GHOST-PARENT"}
r = requests.post(f"{BASE}/systems", data=ordered(parent_sml), headers=SML_CT, auth=AUTH, allow_redirects=False)
parent_id = r.headers["Location"].rstrip("/").split("/")[-1]
print(f"Parent: {parent_id}")

# Step 2: Register a child as TOP-LEVEL (with UID-A)
child_top_sml = {"type": "PhysicalSystem", "uniqueId": "urn:test:ghost-repro:child-A", "label": "CHILD-TOP"}
r = requests.post(f"{BASE}/systems", data=ordered(child_top_sml), headers=SML_CT, auth=AUTH, allow_redirects=False)
child_top_id = r.headers["Location"].rstrip("/").split("/")[-1]
print(f"Child (top-level): {child_top_id}")

# Step 3: Register the SAME logical child as SUBSYSTEM (with UID-B)
child_sub_sml = {"type": "PhysicalSystem", "uniqueId": "urn:test:ghost-repro:child-B", "label": "CHILD-SUB"}
r = requests.post(f"{BASE}/systems/{parent_id}/subsystems", data=ordered(child_sub_sml), headers=SML_CT, auth=AUTH, allow_redirects=False)
child_sub_id = r.headers["Location"].rstrip("/").split("/")[-1]
print(f"Child (subsystem): {child_sub_id}")

# Step 4: Delete the top-level registration
r = requests.delete(f"{BASE}/systems/{child_top_id}", auth=AUTH)
print(f"DELETE top-level child: {r.status_code}")  # Expect 204

time.sleep(2)

# Step 5: Verify the ghost
r = requests.get(f"{BASE}/systems/{child_top_id}", auth=AUTH, headers=GEO_H)
print(f"GET individual: {r.status_code}")  # Expect 404

r = requests.get(f"{BASE}/systems?limit=100", auth=AUTH, headers=GEO_H)
items = r.json().get("items", r.json().get("features", []))
ghost = [i for i in items if i["id"] == child_top_id]
print(f"In listing: {len(ghost) > 0}")  # Expect True (BUG)

# Cleanup (parent + subsystem)
requests.delete(f"{BASE}/systems/{parent_id}?cascade=true", auth=AUTH)
```

**Expected (per spec):** After Step 4, the deleted resource should NOT appear in the Step 5 listing.  
**Actual:** The deleted resource DOES appear in the listing — a ghost entry.

---

## 11. Relationship to Previous Research

| Document | Relationship |
|----------|-------------|
| [OSH Cascade Delete Experiment](OSH_Cascade_Delete_Experiment.md) | Proved `?cascade=true` works on this server; the ghost bug was discovered during a follow-up migration that used those findings |
| [OSH Delete Cascade and Reparenting](OSH_Delete_Cascade_and_Reparenting.md) | Documented the original migration strategy; the ghost bug was not yet known at time of writing |
| [Phase 1 Bootstrap Results](Phase1_Bootstrap_Results.md) | The bootstrap that created the original dual registrations |

---

## 12. Conclusion

The OSH SensorHub server has a **data consistency bug** where deleting a dual-registered system (existing at both top-level and subsystem level) removes the resource from the individual resource store but **not from the collection listing index**. This creates permanent "ghost" entries that:

- Appear in collection list and search results with full GeoJSON data
- Return 404 on direct GET, DELETE, or PUT
- Can have their listing data updated via POST (same UID) but remain inaccessible
- Cannot be purged via any REST API operation

The bug is specific to dual-registered resources and does not affect normally registered (single-path) systems. The recommended upstream fix is to ensure DELETE propagates to all internal indices, and to add an index reconciliation mechanism for recovery.

For the ODAS demo, the impact is cosmetic — 3 ghost entries in a listing of 39 systems, clearly marked with `[Ghost]` descriptions and handled gracefully in the Explorer UI with a prominent warning banner.
