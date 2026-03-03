# LOB Triangulation — Implementation Specification

> Follow-up to [UAS_LOB_Triangulation_Prompt_and_Response.md](UAS_LOB_Triangulation_Prompt_and_Response.md).  
> Fills the gaps identified in review: concrete schemas, algorithm, timing, and OSH constraints.

**Date:** 2026-03-03  
**Updated:** 2026-03-03 — LOB schema corrected to 7 fields (added classification); datastream IDs updated after delete/recreate  
**Status:** Draft specification  
**Scope:** Bearing-only UAS geolocation for the OS4CSAPI AZ-String-Alpha sensor string

---

## 1. Current State on the Live Server

### 1.1 LOB Datastream Schema (actual, from server)

Each MA node has one LOB datastream. Schema is identical across all three. The authoritative source for this schema is [`scripts/bootstrap_v4.py` (line 536)](https://github.com/OS4CSAPI/ogc-csapi-explorer/blob/main/scripts/bootstrap_v4.py#L536) in the csapi-explorer repo.

Example: datastream `04c0` (AZ-MA-1 LOB):

```json
{
  "obsFormat": "application/om+json",
  "resultSchema": {
    "type": "DataRecord",
    "name": "az_ma_1_lob",
    "definition": "https://os4csapi.org/def/odas/track/lobRecordOSH",
    "label": "LOB",
    "fields": [
      { "type": "Time",     "name": "timestamp",       "label": "Epoch seconds",    "uom": { "code": "s" } },
      { "type": "Count",    "name": "trackId",          "label": "Track ID" },
      { "type": "Quantity", "name": "bearingTrue",      "label": "Bearing true",     "uom": { "code": "deg" }, "constraint": { "intervals": [[0.0, 360.0]] } },
      { "type": "Quantity", "name": "bearingStdDev",    "label": "Bearing std dev",  "uom": { "code": "deg" } },
      { "type": "Quantity", "name": "sensorLat",        "label": "Sensor lat",       "uom": { "code": "deg" }, "constraint": { "intervals": [[-90.0, 90.0]] } },
      { "type": "Quantity", "name": "sensorLon",        "label": "Sensor lon",       "uom": { "code": "deg" }, "constraint": { "intervals": [[-180.0, 180.0]] } },
      { "type": "Text",     "name": "classification",   "label": "Classification",   "definition": "https://os4csapi.org/def/odas/classification" }
    ]
  }
}
```

**7 fields.** The `classification` field was added by deleting the original 6-field LOB datastreams and recreating them with the corrected schema. OSH does not support PUT on `/datastreams/{id}/schema` (HTTP 405), but DELETE + POST works when the datastream has no observations.

### 1.2 Server Inventory

| Resource | ID | UID |
|----------|----|-----|
| Deployment (ICO) | `040g` | `urn:os4csapi:deployment:ico:ft-huachuca:001` |
| System AZ-MA-1 | `0420` | `urn:os4csapi:system:odas:az-ma-1` |
| System AZ-MA-2 | `0490` | `urn:os4csapi:system:odas:az-ma-2` |
| System AZ-MA-3 | `049g` | `urn:os4csapi:system:odas:az-ma-3` |
| LOB DS — MA-1 | **`04c0`** | — |
| LOB DS — MA-2 | **`04cg`** | — |
| LOB DS — MA-3 | **`04d0`** | — |

> **Note:** LOB datastream IDs changed from `0420`/`0460`/`049g` to `04c0`/`04cg`/`04d0` after the schema fix. The simulator and webapp discover datastreams dynamically by `outputName`, so no hardcoded references break.

### 1.3 Node Positions (fixed, from bootstrap)

| Node | Latitude | Longitude | Detection Range |
|------|----------|-----------|-----------------|
| AZ-MA-1 | 31.6490196 | -110.2758537 | 3,000 m |
| AZ-MA-2 | 31.6569236 | -110.2659979 | 3,000 m |
| AZ-MA-3 | 31.6637961 | -110.2515496 | 3,000 m |

### 1.4 OSH Constraints

- **Schema is STRICT.** PUT on `/datastreams/{id}/schema` returns HTTP 405. POST with extra fields returns HTTP 400. New datastreams must have their schema set at creation time. **Workaround:** DELETE the datastream (if empty) and POST a new one with the corrected schema.
- **`deployedSystems` not persisted.** OSH does not store deployment-to-system linkages server-side. The webapp maintains this relationship via `platform@link` on deployments.
- **STRING deployment not on server.** The SNET deployment was reparented previously but the server currently has only the top-level ICO deployment (`040g`). Subdeployments exist in the bootstrap script.

---

## 2. String Localizer System — Proposed Server Resources

### 2.1 System Registration

```json
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:system:fusion:az-string-alpha-localizer",
    "name": "AZ-String-Alpha LOB Triangulator",
    "description": "Software agent that fuses LOB observations from 3 MA nodes to produce UAS location estimates via weighted least-squares bearing intersection.",
    "typeOf": "urn:os4csapi:procedure:lob-triangulation:v1",
    "definition": "http://www.w3.org/ns/sosa/Sensor"
  }
}
```

**Rationale:** Per SOSA, a sensor can be software that responds to input data composed from results of prior observations. This system *is* the fusion processor. It implements the triangulation procedure.

### 2.2 Location Estimate DataStream

Owner: the String Localizer system.

#### Schema

```json
{
  "obsFormat": "application/om+json",
  "resultSchema": {
    "type": "DataRecord",
    "name": "location_estimate",
    "definition": "https://os4csapi.org/def/fusion/locationEstimate",
    "label": "UAS Location Estimate",
    "fields": [
      {
        "type": "Time",
        "name": "timestamp",
        "definition": "https://os4csapi.org/def/odas/time/epochSeconds",
        "label": "Epoch seconds",
        "referenceTime": "1970-01-01T00:00:00Z",
        "uom": { "code": "s" }
      },
      {
        "type": "Count",
        "name": "trackId",
        "definition": "https://os4csapi.org/def/odas/trackId",
        "label": "Track ID"
      },
      {
        "type": "Quantity",
        "name": "estimatedLat",
        "definition": "https://os4csapi.org/def/fusion/estimatedLat",
        "label": "Estimated latitude",
        "uom": { "code": "deg" },
        "constraint": { "intervals": [[-90.0, 90.0]] }
      },
      {
        "type": "Quantity",
        "name": "estimatedLon",
        "definition": "https://os4csapi.org/def/fusion/estimatedLon",
        "label": "Estimated longitude",
        "uom": { "code": "deg" },
        "constraint": { "intervals": [[-180.0, 180.0]] }
      },
      {
        "type": "Quantity",
        "name": "cep50_m",
        "definition": "https://os4csapi.org/def/fusion/cep50",
        "label": "CEP50 (m)",
        "description": "Circular error probable — 50% of fixes fall within this radius",
        "uom": { "code": "m" }
      },
      {
        "type": "Text",
        "name": "classification",
        "definition": "https://os4csapi.org/def/odas/classification",
        "label": "Classification"
      },
      {
        "type": "Count",
        "name": "numContributingLobs",
        "definition": "https://os4csapi.org/def/fusion/numContributingLobs",
        "label": "Contributing LOBs"
      },
      {
        "type": "Text",
        "name": "contributingSensors",
        "definition": "https://os4csapi.org/def/fusion/contributingSensors",
        "label": "Contributing sensors",
        "description": "Comma-separated list of sensor names that contributed LOBs"
      },
      {
        "type": "Quantity",
        "name": "residual_m",
        "definition": "https://os4csapi.org/def/fusion/residual",
        "label": "Residual (m)",
        "description": "Mean perpendicular distance from each bearing line to the estimated point",
        "uom": { "code": "m" }
      }
    ]
  }
}
```

#### Example Observation

```json
{
  "phenomenonTime": "2026-03-03T21:30:05.000Z",
  "resultTime": "2026-03-03T21:30:05.000Z",
  "result": {
    "timestamp": 1772684405.000,
    "trackId": 1,
    "estimatedLat": 31.6685,
    "estimatedLon": -110.2521,
    "cep50_m": 42.7,
    "classification": "UAS",
    "numContributingLobs": 3,
    "contributingSensors": "AZ-MA-1,AZ-MA-2,AZ-MA-3",
    "residual_m": 18.3
  }
}
```

**Design decisions:**
- **Self-contained results.** Each observation embeds the contributing sensor names and LOB count rather than referencing observation IDs. This avoids fragile cross-references and makes each estimate independently interpretable.
- **CEP50** is the standard military metric for location accuracy (50% circular error probable). It's computed from the geometry of the bearing intersection.
- **`contributingSensors`** is a comma-separated string rather than an array because OSH's strict schema doesn't support variable-length arrays in SWE Common DataRecord fields.

---

## 3. Triangulation Algorithm

### 3.1 Problem Statement

Given $N \geq 2$ sensors, each at known position $(x_i, y_i)$ with bearing $\theta_i$ (degrees from true north, clockwise) and bearing uncertainty $\sigma_i$ (degrees), find the point $\hat{p} = (\hat{x}, \hat{y})$ that best explains all bearings.

### 3.2 Weighted Least Squares (WLS) Bearing Intersection

Each bearing defines a line from sensor $i$ in direction $\theta_i$. The perpendicular distance from a candidate point $(x, y)$ to bearing line $i$ is:

$$d_i = \sin(\theta_i)(x - x_i) - \cos(\theta_i)(y - y_i)$$

We minimize the weighted sum of squared perpendicular distances:

$$\min_{\hat{x}, \hat{y}} \sum_{i=1}^{N} w_i \cdot d_i^2$$

where $w_i = 1 / \sigma_i^2$ (inverse variance weighting).

This is a linear system $\mathbf{A}^T \mathbf{W} \mathbf{A} \hat{p} = \mathbf{A}^T \mathbf{W} \mathbf{b}$ where:

$$A_i = [\sin(\theta_i), -\cos(\theta_i)]$$
$$b_i = \sin(\theta_i) \cdot x_i - \cos(\theta_i) \cdot y_i$$
$$W = \text{diag}(w_1, w_2, \ldots, w_N)$$

**Solution:** $\hat{p} = (\mathbf{A}^T \mathbf{W} \mathbf{A})^{-1} \mathbf{A}^T \mathbf{W} \mathbf{b}$

### 3.3 Why WLS Instead of Simple 2-Line Intersection

| Scenario | Simple intersection | WLS |
|----------|-------------------|-----|
| 2 LOBs, perpendicular | Identical result | Identical result |
| 2 LOBs, nearly parallel | Wild point thousands of meters away | Still wild, but with high residual → detectable |
| 3 LOBs | Undefined (3 lines → 3 different intersection points) | Single best-fit point incorporating all evidence |
| Unequal bearing uncertainty | No way to express | Higher-confidence bearings weighted more heavily |

With 3 sensors in the triple-detection zone (your climax scenario), WLS produces a single optimal estimate rather than forcing you to pick between 3 pairwise intersections.

### 3.4 CEP50 Estimation

After computing $\hat{p}$, estimate CEP50 from the residuals:

$$\text{residual}_i = |d_i(\hat{p})|$$
$$\text{mean residual (m)} = \frac{1}{N} \sum |d_i|$$
$$\text{CEP50} \approx 0.675 \times \text{DRMS}$$

where DRMS is the distance root mean square from the covariance of the WLS solution. For a simpler approximation in the simulator:

$$\text{CEP50} \approx \text{mean residual} \times 1.2$$

### 3.5 Coordinate Considerations

All math above works in a local Cartesian frame. Convert WGS-84 lat/lon to local meters using:

$$x_{\text{m}} = \text{lon} \times \frac{\pi}{180} \times R \times \cos(\text{lat}_{\text{ref}})$$
$$y_{\text{m}} = \text{lat} \times \frac{\pi}{180} \times R$$

where $R = 6{,}371{,}000$ m and $\text{lat}_{\text{ref}}$ is the centroid of the sensor network (≈31.655°N).

After solving, convert back to WGS-84.

---

## 4. Correlation Gate

Before running triangulation, determine which LOBs to fuse.

### 4.1 Gate Criteria (applied per tick)

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| **Time window** | $\|t_i - t_j\| \leq 2.0$ s | LOBs from the same simulator tick land within ~1s |
| **Classification match** | Same `classification` value | Only fuse same-type detections (field now in LOB schema) |
| **Range plausibility** | Intersection point within `detection_max_m` of all contributing sensors | Rejects phantom intersections outside detection envelopes |
| **Residual cap** | Mean residual $\leq 500$ m | Rejects near-parallel bearing pairs with wildly divergent intersection |
| **Minimum LOBs** | $N \geq 2$ | Need at least 2 bearings for a fix |

### 4.2 Classification Gate Note

With the corrected LOB schema, the `classification` field is now carried **in the observation data itself** (e.g. `"classification": "UAS"`), not hardcoded on the frontend. This means the localizer can read classification directly from the LOB observations it consumes via CSAPI, enabling proper heterogeneous target filtering in the future.

### 4.3 Implementation for the Standalone Localizer

The localizer is a standalone process (see [LOB_Localizer_Architecture_Correction.md](LOB_Localizer_Architecture_Correction.md)):

1. Poll each LOB datastream for latest observation (`resultTime=latest`)
2. Collect all LOBs where `|phenomenonTime - now| ≤ Δt`
3. Group by `classification` value from the observation result
4. For each group with $N \geq 2$: run WLS, apply residual gate, publish

---

## 5. Execution Model

> **⚠️ This section is superseded by [LOB_Localizer_Architecture_Correction.md](LOB_Localizer_Architecture_Correction.md).**
>
> The localizer MUST be a **standalone CSAPI consumer/producer**, NOT embedded in the simulator. See the architecture correction document for the full rationale and corrected design.

### 5.1 Summary of Corrected Model

The localizer runs as an independent process that:
1. **Consumes** LOB observations from the 3 MA datastreams via `GET /datastreams/{id}/observations`
2. **Correlates** by time window and classification
3. **Computes** WLS bearing intersection
4. **Produces** location estimates via `POST /datastreams/{localizer_ds}/observations`

It has zero coupling to the simulator — no shared memory, no import paths, no function calls. All communication flows through the CSAPI server.

### 5.2 Why Not Embedded

Running the localizer inside the simulator:
- Bypasses the CSAPI standard (uses in-memory data instead of API)
- Defeats the demo narrative (one process doing everything ≠ interoperability)
- Cannot generalize to real hardware (depends on simulator internal state)

---

## 6. Python Implementation Outline

### 6.1 Triangulation Function

```python
import math

R_EARTH = 6_371_000  # metres

def wls_bearing_intersection(lobs: list[dict], lat_ref: float = 31.655) -> dict:
    """
    Weighted least-squares bearing intersection.
    
    Each lob: { sensorLat, sensorLon, bearingTrue, bearingStdDev, classification, name }
    Returns: { estimatedLat, estimatedLon, cep50_m, residual_m, n }
    """
    cos_ref = math.cos(math.radians(lat_ref))
    
    # Convert to local cartesian (metres)
    sensors = []
    for lob in lobs:
        x = lob["sensorLon"] * (math.pi / 180) * R_EARTH * cos_ref
        y = lob["sensorLat"] * (math.pi / 180) * R_EARTH
        theta = math.radians(lob["bearingTrue"])
        sigma = max(lob["bearingStdDev"], 0.5)  # floor at 0.5°
        w = 1.0 / (math.radians(sigma) ** 2)
        sensors.append((x, y, theta, w))
    
    # Build WLS system: A^T W A x = A^T W b
    ata = [[0, 0], [0, 0]]
    atb = [0, 0]
    
    for x_i, y_i, theta_i, w_i in sensors:
        a0 = math.sin(theta_i)
        a1 = -math.cos(theta_i)
        b_i = a0 * x_i + a1 * y_i
        
        ata[0][0] += w_i * a0 * a0
        ata[0][1] += w_i * a0 * a1
        ata[1][0] += w_i * a1 * a0
        ata[1][1] += w_i * a1 * a1
        atb[0]    += w_i * a0 * b_i
        atb[1]    += w_i * a1 * b_i
    
    # Solve 2x2 system
    det = ata[0][0] * ata[1][1] - ata[0][1] * ata[1][0]
    if abs(det) < 1e-12:
        return None  # near-parallel bearings, no solution
    
    x_hat = (ata[1][1] * atb[0] - ata[0][1] * atb[1]) / det
    y_hat = (ata[0][0] * atb[1] - ata[1][0] * atb[0]) / det
    
    # Residuals
    residuals = []
    for x_i, y_i, theta_i, w_i in sensors:
        d = abs(math.sin(theta_i) * (x_hat - x_i) - math.cos(theta_i) * (y_hat - y_i))
        residuals.append(d)
    
    mean_residual = sum(residuals) / len(residuals)
    cep50 = mean_residual * 1.2  # simplified estimate
    
    # Convert back to WGS-84
    est_lon = x_hat / (math.pi / 180 * R_EARTH * cos_ref)
    est_lat = y_hat / (math.pi / 180 * R_EARTH)
    
    return {
        "estimatedLat": round(est_lat, 6),
        "estimatedLon": round(est_lon, 6),
        "cep50_m": round(cep50, 1),
        "residual_m": round(mean_residual, 1),
        "n": len(lobs),
    }
```

### 6.2 Observation Builder

```python
def build_location_estimate_observation(
    wls_result: dict,
    contributing_sensors: list[str],
    track_id: int = 1,
    classification: str = "UAS",
) -> dict:
    now = iso_now()
    return {
        "phenomenonTime": now,
        "resultTime": now,
        "result": {
            "timestamp": epoch_seconds(),
            "trackId": track_id,
            "estimatedLat": wls_result["estimatedLat"],
            "estimatedLon": wls_result["estimatedLon"],
            "cep50_m": wls_result["cep50_m"],
            "classification": classification,
            "numContributingLobs": wls_result["n"],
            "contributingSensors": ",".join(contributing_sensors),
            "residual_m": wls_result["residual_m"],
        },
    }
```

### 6.3 Standalone Localizer Loop

```python
# localizer.py — standalone CSAPI consumer/producer (see Architecture Correction)

LOB_DATASTREAMS = {
    "AZ-MA-1": "04c0",
    "AZ-MA-2": "04cg",
    "AZ-MA-3": "04d0",
}
LOCALIZER_DS = "<created at bootstrap>"
POLL_INTERVAL = 5  # seconds
TIME_WINDOW = 10   # seconds
RESIDUAL_CAP = 500 # metres

last_processed_times = {}

while running:
    lobs = []
    for name, ds_id in LOB_DATASTREAMS.items():
        obs = GET(f"datastreams/{ds_id}/observations?resultTime=latest&limit=1")
        if obs and obs not already processed:
            lobs.append({**obs["result"], "name": name})

    # Group by classification
    by_class = group_by(lobs, key=lambda l: l.get("classification", "UAS"))

    for cls, group in by_class.items():
        if len(group) >= 2:
            wls = wls_bearing_intersection(group)
            if wls and wls["residual_m"] <= RESIDUAL_CAP:
                loc_obs = build_location_estimate_observation(
                    wls,
                    contributing_sensors=[l["name"] for l in group],
                    classification=cls,
                )
                POST(f"datastreams/{LOCALIZER_DS}/observations", loc_obs)

    sleep(POLL_INTERVAL)
```

---

## 7. Server Bootstrapping Steps

Before the localizer can publish, these resources must exist on the server:

### Step 1: Create the String Localizer System

```
POST /systems
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:system:fusion:az-string-alpha-localizer",
    "name": "AZ-String-Alpha LOB Triangulator",
    "description": "Software fusion agent — WLS bearing-only geolocation"
  }
}
```

### Step 2: Create the Location Estimate DataStream

```
POST /systems/{localizer_sys_id}/datastreams
{
  "name": "UAS Location Estimate",
  "outputName": "az_string_alpha_location_estimate",
  "resultSchema": { ... }  // see Section 2.2
}
```

### Step 3: Register the Procedure (optional, for provenance)

```
POST /procedures
{
  "type": "Feature",
  "properties": {
    "uid": "urn:os4csapi:procedure:lob-triangulation:v1",
    "name": "LOB Triangulation v1",
    "description": "Weighted least-squares bearing-only intersection using N≥2 LOBs with inverse-variance weighting"
  }
}
```
