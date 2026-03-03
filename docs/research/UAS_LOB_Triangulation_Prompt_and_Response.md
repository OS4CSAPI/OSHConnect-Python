# UAS LOB Triangulation — Prompt + Response

## User prompt
well I just perfected the data simulator to have a UAS simulated passing through the detection ranges of our three deployed microphone acoustic array sensors. It is working beautifully. What happens is that the simulated UAS flies a path through the detection ranges of each sensor and they generate a line of bearing (LOB) observation through their LOB datastream. That LOB observation generates a line from the sensor to the end of its detection range in the direction of the detected UAS. I have them set up so their detection ranges overlap. So when the UAS flies in a location that is covered by two or more of the microphone array sensors, they each will produce their own line of bearing observation that starts from the sensor to the direction they detected it. Here is what I am curious about and think I would like to do, but I must be honest: I really don't know what I am talking about: I think I would like to set up a SensorML Procedure (maybe?) at the sensor string deployment level (remember, we modeled the concept of sensor string from the USMC's remote sensor operations doctrine manual to be a deployment and it has 3 subdeployments, one for each deployed microphone array node system), and the process of this procedure would be to receive the input of the LOB datastreams from all 3 of the MA Node systems and when 2 or more of the individual MA node system's LOB observations intersect with the same classification field at the same time, the output is the generation of some object. Now I don't know what this object should be, maybe it's a new observation? maybe it's a feature of interest? maybe a feature? The operational context is that when these conditions are met (2 or more of these LOB observations with same classification at the same time from different MA node systems intersect), the location of that intersection is considered the estimated location of that UAS. please think very deeply about this and do tons of research and make all of the recommendations that you possibly can.

## Assistant response
What you're describing is **bearing-only (LOB) geolocation / triangulation**: multiple sensors each produce an azimuth/bearing observation, and when ≥2 bearings plausibly refer to the same target at the same time, you compute an **estimated target location**.

### The key modeling insight
In CSAPI/SOSA terms, that "string-level fusion" is **not just a Procedure**. It's best modeled as:

- a **System** (software agent) that *consumes prior observations* and produces new observations, and
- a **Procedure** that describes the triangulation method.

That matches SOSA's definition of a Sensor/System: a sensor can be **software** and can respond to *input data composed from results of prior observations* and generate a result. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

---

## 1) What should the "string-level thing" be: Procedure vs System?
### Recommended
Create a **String Localizer System** (or "LOB Triangulator") deployed at the **STRING deployment** level (or under it as a subdeployment slot), and have it implement a Procedure like:

- `urn:...:procedure:lob-triangulation:v1`

Then:
- your MA Nodes keep producing **LOB Observations** in their own LOB DataStreams
- the String Localizer produces **Location Estimate Observations** in its own DataStream

CSAPI already supports linking a DataStream to the Procedure used to generate it (`sosa:usedProcedure`), and linking individual Observations to the Procedure as well. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html)) ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

So the *deployment-level* concept you're after is really: **a System (the "fusion processor") that is part of the STRING deployment context** and uses a well-defined Procedure.

---

## 2) What should the "object" be when bearings intersect?
You have three viable objects; you can use more than one.

### Option A (best default): a new **Observation** in a "Location Estimate" DataStream
When ≥2 LOBs correlate, generate an Observation whose **result is a point location estimate** (plus uncertainty).

This is very "CSAPI-native" because Observations are exactly how you publish estimated values of properties at times. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

**Result schema:** use SWE Common's `Vector` or a `Record` containing a `Vector`.

Part 2 literally provides an example Vector schema for location (lat/lon/h with CRS). ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

Add uncertainty as extra fields (e.g., `cep50_m`, `covariance`, `bearingIntersectionResidual`), still within a SWE `Record`.

### Option B: a **SamplingFeature** for the track/hypothesis + Observations reference it
This is how you turn "a single intersection" into a persistent *thing* (your track identity).

Part 2 defines **Sample / Sampling Feature** as the "subject of observation," and Observations can reference a `samplingFeature`. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html)) ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

Practical approach:
- When the first correlated intersection occurs, create a SamplingFeature like `UAS-Track-0007`.
- All subsequent LOB observations (once associated) and all Location Estimate observations reference that same SamplingFeature.

This matches the pattern you already like: a track/hypothesis "born on first detection" and persisted with firstSeen/lastSeen.

### Option C: an **Event** (detection event / localization event)
If you want a discrete "this happened" object ("UAS localized"), model that as an Event resource family (CSAPI Part 2 includes system events; many implementations use events for alerts). This is useful for alerting, but you'll still usually want Option A for the continuous location updates.

**My recommendation:** do **A + B** (Location Estimate Observation + Track SamplingFeature). Add C later if you want alert workflows.

---

## 3) How to express "same classification at same time" robustly
Your current rule ("same classification field at the same time") is a good simulator starting point, but in real ops it'll create false matches.

A better correlation gate (still simple) is:

1) **time window**: |t₁ − t₂| ≤ Δt (e.g., 0.5–2.0 s)
2) **class match**: same `classification` (UAS vs other)
3) **geometry plausibility**:
   - intersection lies within both sensors' detection ranges
   - intersection residual small (bearings nearly intersect vs almost parallel)
4) **optional**: use bearing uncertainty weights

You can encode the correlation evidence into the *output* observation's `parameters` (or result fields), because CSAPI allows observation parameters and requires that result/parameters conform to the DataStream's schema. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html)) ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

---

## 4) What the two key DataStreams look like (schemas)
### A) MA Node "LOB" DataStream (per node)
**Produced by:** the MA node System (required association). ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))  
**Procedure:** SRP-PHAT/DOA procedure (optional association at DS level). ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))  
**Result schema suggestion (Record):**
- `bearing_deg` (Quantity)
- `bearing_unc_deg` (Quantity)
- `range_max_m` (Quantity) (or infer from detectionRange)
- `classification` (Text/Category)
- optional `lob_id` (Text) / `detection_id` (Text)

You do **not** have to store the line geometry; your map can render the line from:
- sensor position (deployment slot geometry)
- bearing
- range_max

### B) String Localizer "Location Estimate" DataStream (string-level)
**Produced by:** the String Localizer System. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))  
**Procedure:** `lob-triangulation:v1` (optional DS procedure). ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))  
**Result schema suggestion (Record):**
- `location` (Vector lat/lon/(h), like the Part 2 example) ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))
- `uncertainty_m` (Quantity) or `cep50_m`
- `classification` (Text/Category)
- `source_lob_obs_ids` (Text array) **or** `source_lob_refs` as a record list
- optional `method` / `residual` fields

**Observation associations:** include `samplingFeature` = "UAS-Track-0007" when known. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

---

## 5) Where should this live in your doctrine/deployment model?
Given your doctrine mapping (STRING deployment with 3 MA node subdeployments), I'd do:

- STRING deployment (doctrinal container)
  - Node-1 slot → MA-1 system
  - Node-2 slot → MA-2 system
  - Node-3 slot → MA-3 system
  - **(new)** "String Fusion Slot" → String Localizer system

So you're not pretending the *deployment itself* runs the algorithm. You're saying: "this operation has an asset (software agent) that performs fusion."

---

## 6) Important reality check for your current OSH server
Based on your own probes, OSH currently **does not** persist `deployedSystems` and also **does not** persist DataStream `deployment` associations or implement `/deployments/{id}/datastreams`. That means the clean "deployment-first" query path won't work server-side right now.

But none of that blocks this fusion model, because:
- the Localizer is just another **System**
- it owns its own DataStreams/Observations (`/systems/{localizer}/datastreams/...`)
- your UI can still present it "at the string level" via the deployment tree + platform links

---

## 7) Extra recommendations (optional but high value)
### Use a "track identity strategy"
- **Before association is confident:** each node can emit LOBs with a `candidate_id` local to that node.
- **When fusion happens:** create a `global_track_id` (SamplingFeature) and start assigning future LOBs + location estimates to it.

### Use weighted least squares instead of raw 2-line intersection
Even with only two bearings, you'll get better behavior if you treat bearings with uncertainty and compute the best-fit point, not a brittle intersection. (This is standard in bearing-only localization literature; it becomes critical with noise.)

### Consider an OGC API – Processes wrapper later
If you ever want "compute location on demand over a time window," a Processes endpoint can run triangulation as a job. But for your simulator and live op picture, publishing derived Observations is the right first step.

---

### Bottom line recommendation
1) **Create a String Localizer System** (software agent) at STRING level.  
2) Attach a **Triangulation Procedure** to it / its DataStream. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))  
3) Output **Location Estimate Observations** in a dedicated DataStream using a SWE `Vector` (lat/lon/h) + uncertainty. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))  
4) Create/maintain a **SamplingFeature** as the "track/hypothesis identity," and reference it from both LOB and location estimate observations when correlated. ([docs.ogc.org](https://docs.ogc.org/is/23-002/23-002.html))

If you paste one example of your current LOB Observation JSON (and the LOB datastream schema), I'll propose the exact SWE Common `resultSchema` for both streams (LOB + location estimate) with fields/units that match your simulator outputs, so you can implement it without guessing.
