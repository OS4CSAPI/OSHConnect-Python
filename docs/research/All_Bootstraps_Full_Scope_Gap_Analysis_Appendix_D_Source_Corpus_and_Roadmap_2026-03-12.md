# All Bootstraps Full-Scope Gap Analysis

## Appendix D. Source Corpus and Roadmap

**Date:** 2026-03-12
**Method note:** external claims in the master report and dossiers are grounded in primary or official sources only. Repo-local artifacts were treated as the source of truth for current implementation state; official public documentation was treated as the source of truth for upstream semantics and service behavior.

---

## D.1 Standards Corpus

| Standard / Reference | Official URL | Why It Was Used |
|---|---|---|
| OGC API Connected Systems landing page | <https://ogcapi.ogc.org/connectedsystems/> | High-level reference point for the CSAPI resource model the bootstraps are targeting. |
| SensorML JSON Encoding Standard | <https://docs.ogc.org/is/23-000r6/23-000r6.html> | Primary reference for judging SensorML body shape, identifiers, contacts, documents, and rich system metadata. |
| Semantic Sensor Network / SOSA | <https://docs.ogc.org/is/17-002r1/17-002r1.html> | Reference for procedure, system, observation, and deployment intent. |
| SWE Common Data Model 2.0 | <https://docs.ogc.org/is/08-094r1/08-094r1.html> | Reference for result-record structure, field typing, units, and DataRecord-style result schemas. |
| Observations and Measurements 2.0 | <https://docs.ogc.org/is/10-004r3/10-004r3.html> | Conceptual reference for observation/result intent, even where the implementation is CSAPI-first rather than OM-encoded. |

### D.1.1 How the standards corpus affected scoring

- `SensorML quality` scores were most influenced by the SensorML JSON encoding standard and the known NWS/NDBC field-shape incident.
- `Procedure`, `system`, and `deployment` scores were strongly influenced by SOSA/SSN intent.
- `Datastream semantics` and `field semantics` scores were strongly influenced by SWE Common result-structure expectations.
- `Standards conformance` scores were not legal conformance claims; they are design-intent maturity judgments against the standards listed above.

---

## D.2 Official Source Corpus By Publisher

### D.2.1 NWS

| Official source | URL | Report use |
|---|---|---|
| NWS API web services documentation | <https://www.weather.gov/documentation/services-web-api> | Verified the official NWS public API context used by the publisher family. |
| NWS OpenAPI description | <https://api.weather.gov/openapi.json> | Supports bootstrap provenance claims and endpoint traceability. |
| NWS API root | <https://api.weather.gov/> | Confirms public API entry point used by station and point resources. |
| NWS ASOS information | <https://www.weather.gov/asos/> | Used to judge whether the procedure/system language reflects ASOS/AWOS station semantics. |

### D.2.2 NDBC

| Official source | URL | Report use |
|---|---|---|
| NDBC home | <https://www.ndbc.noaa.gov/> | Primary official source for buoy program context. |
| NDBC web data guide | <https://www.ndbc.noaa.gov/docs/ndbc_web_data_guide.pdf> | Supports measurement and field-semantics judgments. |
| NDBC real-time data access FAQ | <https://www.ndbc.noaa.gov/faq/rt_data_access.shtml> | Supports access-path and provenance judgments. |
| NDBC measurement descriptions | <https://www.ndbc.noaa.gov/faq/measdes.shtml> | Supports datastream semantic precision judgments. |
| NDBC BuoyCAM home | <https://www.ndbc.noaa.gov/buoycams.shtml> | Supports the imagery companion-stream analysis. |
| NDBC BuoyCAM FAQ | <https://www.ndbc.noaa.gov/faq/buoycamlinks.shtml> | Supports provenance and imagery-link quality judgments. |

### D.2.3 CO-OPS

| Official source | URL | Report use |
|---|---|---|
| CO-OPS API documentation | <https://api.tidesandcurrents.noaa.gov/api/prod/> | Primary reference for water-level and coastal observation semantics. |
| CO-OPS web services info | <https://www.tidesandcurrents.noaa.gov/web_services_info.html> | Supports broader source-traceability judgments. |
| CO-OPS metadata API | <https://api.tidesandcurrents.noaa.gov/mdapi/prod/> | Supports station metadata expectations. |
| CO-OPS data products API | <https://api.tidesandcurrents.noaa.gov/dpapi/prod/> | Supports product/family separation analysis. |
| Tides and Currents home | <https://tidesandcurrents.noaa.gov/> | Supports agency-level provenance and operational context. |

### D.2.4 Aviation Weather

| Official source | URL | Report use |
|---|---|---|
| AviationWeather API docs | <https://aviationweather.gov/data/api/> | Primary reference for METAR API semantics. |
| AviationWeather home | <https://aviationweather.gov/> | Supports provenance and agency context. |

### D.2.5 OpenSky

| Official source | URL | Report use |
|---|---|---|
| OpenSky Network home | <https://opensky-network.org/> | Supports source provenance and organization context. |
| OpenSky REST API docs | <https://openskynetwork.github.io/opensky-api/rest.html> | Primary reference for feed-adapter semantics and auth/rate-limit considerations. |
| OpenSky state-vectors docs | <https://openskynetwork.github.io/opensky-api/index.html#state-vectors> | Supports state-vector field semantics. |
| OpenSky token endpoint docs context | <https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token> | Supports the auth-aware follow-on recommendation. |

### D.2.6 ISS / CelesTrak

| Official source | URL | Report use |
|---|---|---|
| CelesTrak GP data formats | <https://celestrak.org/NORAD/documentation/gp-data-formats.php> | Primary official source for the ISS bootstrap precedent and current runtime's orbital-source semantics. |
| CelesTrak GP endpoint pattern | <https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON> | Confirms the live upstream pattern used by the current ISS runtime. |

### D.2.7 USGS Water

| Official source | URL | Report use |
|---|---|---|
| USGS OGC API docs | <https://api.waterdata.usgs.gov/docs/ogcapi/> | Primary reference for the current water-data bootstrap. |
| USGS OGC API OpenAPI HTML | <https://api.waterdata.usgs.gov/ogcapi/v0/openapi?f=html> | Supports endpoint inventory and provenance judgments. |
| Latest continuous collection | <https://api.waterdata.usgs.gov/ogcapi/v0/collections/latest-continuous> | Supports the discharge / gage-height result-model analysis. |
| Time-series metadata collection | <https://api.waterdata.usgs.gov/ogcapi/v0/collections/time-series-metadata> | Supports parameter and statistic specificity analysis. |
| Combined metadata collection | <https://api.waterdata.usgs.gov/ogcapi/v0/collections/combined-metadata> | Supports monitoring-location and parameter cross-reference analysis. |
| USGS API registration | <https://api.usgs.gov/> | Supports auth/rate-limit follow-on analysis. |

### D.2.8 USGS NIMS

| Official source | URL | Report use |
|---|---|---|
| USGS NIMS docs | <https://api.waterdata.usgs.gov/docs/nims/> | Primary reference for the imagery publisher and pack analysis. |
| USGS NIMS cameras endpoint | <https://api.waterdata.usgs.gov/nims/v0/cameras> | Supports live camera-model and site-filter reasoning. |
| USGS NIMS listFiles endpoint | <https://api.waterdata.usgs.gov/nims/v0/listFiles> | Supports image-file and result-shape reasoning. |
| USGS Water home | <https://waterdata.usgs.gov/> | Supports broader provenance context. |

### D.2.9 USGS Earthquake

| Official source | URL | Report use |
|---|---|---|
| GeoJSON summary feed docs | <https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php> | Primary reference for summary-feed semantics. |
| GeoJSON detail feed docs | <https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson_detail.php> | Supports summary-vs-detail target-state analysis. |
| Feed lifecycle policy | <https://earthquake.usgs.gov/earthquakes/feed/policy.php> | Supports lifecycle and dedupe reasoning. |
| ComCat overview | <https://earthquake.usgs.gov/data/comcat/index.php> | Supports event authority and provenance analysis. |
| ComCat event terms | <https://earthquake.usgs.gov/data/comcat/data-eventterms.php> | Supports field-term semantics. |
| FDSN event API | <https://earthquake.usgs.gov/fdsnws/event/1/> | Supports cross-reference and follow-on semantic enrichment analysis. |

---

## D.3 Repo-Local Source Corpus

The official web corpus above was paired with a repo-local implementation corpus:

- every active bootstrap file in `publishers/`
- every legacy bootstrap file in `csapi-explorer/scripts/`
- every paired current runtime publisher where runtime alignment mattered
- the current shared helper layer, `publishers/bootstrap_helpers.py`
- the active sidecars: `stations.json`, `cameras.json`, and `config.json`
- the active packs and total packs present on disk
- prior research notes in `docs/research`

This pairing matters because a bootstrap can be semantically well-intended in planning notes while still being materially incomplete in the current repository state.

---

## D.4 Confirmed Current-State Mismatches

These mismatches were treated as evidence, not as noise:

1. `publishers/iss/bootstrap_iss.py` is still missing, even though `publishers/iss/iss_publisher.py` exists and `publishers/README.md` still tells users to run the missing bootstrap.
2. `publishers/usgs_water/total_bootstrap_data_model_enrichment_pack` is absent on disk, even though `docs/research/USGS_Water_Total_Bootstrap_Data_Model_Enrichment_Pack_2026-03-11.md` states that it was created under that path.
3. Current publisher runtimes broadly still disable TLS certificate verification even though the shared bootstrap helper layer now uses `CERT_REQUIRED` and hostname verification.
4. Pack maturity is uneven enough that "has a bootstrap" and "has a complete implementation package" are not equivalent statements.

---

## D.5 Prioritized Remediation Roadmap

### Tier 1. Universal high-priority gaps

| Priority | Recommendation | Type | Why It Is Tier 1 |
|---|---|---|---|
| 1 | Restore proper TLS verification and certificate handling across all active publisher runtimes. | `runtime-follow-on` | This is the clearest fleet-wide operational weakness and currently undercuts otherwise improved bootstrap hygiene. |
| 2 | Define canonical bootstrap families in code, not just in planning prose: station-per-system, Pattern A companion datastream, and Pattern C feed adapter. | `bootstrap-only` | The family structure is now real enough that not naming it in code is creating avoidable duplication and drift. |
| 3 | Publish an artifact-state policy that distinguishes `metadata pack`, `total pack`, `research note`, and `historical source basis`, then reconcile repo/documentation drift against that policy. | `archive/clarify` | The fleet now has enough artifact diversity that unclear package state is becoming a first-class maintainability problem. |
| 4 | Standardize provenance manifests and semantic-contract sidecars for every publisher. | `metadata-only` | The strongest current publishers are the ones where source authority is explicit and reviewable outside the bootstrap file. |
| 5 | Add round-trip conformance probes for SensorML PUT/GET and result schema retrieval. | `runtime-follow-on` | The NWS/NDBC hollow-metadata incident showed that bootstrap success logs are not sufficient evidence of semantic success. |
| 6 | Resolve the ISS canonical-home gap by migrating the bootstrap into `OSHConnect-Python` and correcting `publishers/README.md`. | `migration` | This is the single largest architecture/documentation contradiction in the active fleet. |

### Tier 2. Publisher-family gaps

| Family | Recommendation | Type | Rationale |
|---|---|---|---|
| Station-per-system | Extract a declarative shared builder for station sidecars, procedure/system builders, standard deployment tree creation, and family-wide result-schema conventions. | `bootstrap-only` | Five current publishers still duplicate the same structural skeleton. |
| Station-per-system | Normalize family-wide field semantics for units, nullability, QC flags, and observed-property naming. | `metadata-only` | Current schemas are functional but still drift source by source. |
| Pattern C feed adapter | Define a common feed-adapter contract: source URL manifest, coverage statement, cadence budget, dedupe policy, and state/event provenance fields. | `metadata-only` | OpenSky and USGS EQ are already converging toward a reusable feed-adapter model. |
| Pattern A companion datastream | Formalize dependency semantics between the owning system family and the companion stream family. | `bootstrap-only` | USGS NIMS currently depends on USGS water systems but expresses that dependency only implicitly. |
| Scenario / migration | Move scenario-only bootstraps and phase scripts into a clearly separate scenario or migration namespace. | `archive/clarify` | Current repo boundaries still invite public-data and scenario scripts to be read as peers when they are not. |

### Tier 3. Per-bootstrap target-state work

| Bootstrap | Next target-state move | Type |
|---|---|---|
| NWS | Fold the best of the metadata pack into the live bootstrap, then add a round-trip SensorML conformance probe and explicit QC/null semantics. | `runtime-follow-on` |
| NDBC | Clarify the relationship between buoy observations and BuoyCAM imagery, then harden runtime security and schema semantics accordingly. | `runtime-follow-on` |
| CO-OPS | Create a metadata enrichment pack and consider splitting water-level and met semantics into more explicit datastream families. | `metadata-only` |
| Aviation WX | Create a metadata enrichment pack and expand provenance beyond minimal API references. | `metadata-only` |
| OpenSky | Keep the current Pattern C shape, but add auth-aware budget controls, stronger quality semantics, and runtime hardening. | `runtime-follow-on` |
| ISS | Port `bootstrap_iss.py` into `publishers/iss/`, keep the dual-product model, and make it the canonical current bootstrap. | `migration` |
| USGS Water | Materialize the missing total-pack directory or retract the claim; then lock the statistic-specific semantic contract into the package. | `total-pack` |
| USGS NIMS | Keep the current Pattern A model, but document or redesign the selected-camera-per-station constraint as a conscious policy. | `runtime-follow-on` |
| USGS EQ | Extend the total pack toward explicit summary-detail-FDSN crosswalk semantics and lifecycle/QC guidance. | `runtime-follow-on` |

### Tier 4. Legacy migration or archival cleanup

| Legacy script | Recommended disposition | Type |
|---|---|---|
| `scripts/bootstrap_iss.py` | Migrate into the current publisher repo with security cleanup and environment normalization. | `migration` |
| `scripts/bootstrap_uas.py` | Preserve as an enrichment reference, but document it as scenario-specific and non-canonical for public-data work. | `archive/clarify` |
| `scripts/bootstrap_localizer.py` | Archive as a scenario-only focused bootstrap; keep it as a minimal pattern reference, not a canonical public-data template. | `archive/clarify` |
| `scripts/bootstrap_v25.py` | Retain only as a historical migration bridge and extract any reusable scenario-import techniques into separate tools. | `archive/clarify` |
| `scripts/bootstrap_v3.1.py` | Archive as a historical stage in scenario hierarchy evolution. | `archive/clarify` |
| `scripts/bootstrap_v4.py` | Preserve as the authoritative scenario reference, but move it out of the mental path for public-data publisher contributors. | `archive/clarify` |

---

## D.6 Roadmap Ordering Recommendation

If the project can only fund a few moves, the recommended order is:

1. Close the ISS gap.
2. Fix runtime TLS verification across the active fleet.
3. Reconcile artifact-state drift, starting with the USGS water package-path mismatch.
4. Extract the station-family builder.
5. Bring CO-OPS and Aviation WX up to pack parity.
6. Add automated round-trip conformance probes so the next metadata regression is caught automatically rather than through manual explorer inspection.

This order gives the project the biggest gain in canonical completeness, operational safety, and semantic confidence per unit effort.
