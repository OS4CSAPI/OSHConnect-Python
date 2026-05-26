# Candidate Source Triage and Prioritization

Date: 2026-05-26

## Purpose

This report evaluates four candidate public data sources for possible new OSHConnect-Python publishers. The candidates were supplied as leads, not as confirmed implementation targets. This triage asks:

- Is the source real and machine-readable?
- Is it public/open enough for a demonstration publisher?
- Is the data valuable and relevant to the OS4CSAPI demonstration story?
- Which existing publisher pattern should be used if we implement it?
- In what order should the sources be considered?

Candidate sources:

1. UK-AIR Sensor Observation Service for air pollution: https://uk-air.defra.gov.uk/data/about_sos
2. Environment Agency Hydrological Open Data: https://www.data.gov.uk/dataset/98a4d46e-23e7-4430-883c-9e5f14645e8f/hydrological-open-data
3. BGS Sensor Data Service for seismology and geothermal telemetry: https://sensors.bgs.ac.uk/
4. Met Office Weather DataHub: https://datahub.metoffice.gov.uk/

## Executive Ranking

| Priority | Source | Recommendation | Why |
| --- | --- | --- | --- |
| 1 | Environment Agency Hydrological Open Data | Implement first | Highest feasibility plus high demo value. Public JSON API, OGL 3, live/historic river/groundwater/rainfall/flow data, strong station-network fit. |
| 2 | UK-AIR Sensor Observation Service | Implement second | Strong value and standards alignment. Public 52 North SOS/REST API, OGL 3, live in-situ air pollution timeseries. More modeling complexity than hydrology. |
| 3 | BGS Sensor Data plus BGS Earthquake feeds | Split into two scoped opportunities | BGS SensorThings API is excellent for geothermal/groundwater/environmental telemetry, but the same site says seismic data is outside that API. BGS earthquake GeoRSS/KML feeds are a separate event-feed opportunity. |
| 4 | Met Office Weather DataHub | Defer unless subscription/account overhead is acceptable | Valuable and technically straightforward, but access is gated by registration/subscription. Free plan exists for Land Observations, but this is less open-demo-friendly than the others. |

Bottom line: start with **Environment Agency Hydrology**, then **UK-AIR**, then choose between **BGS SensorThings telemetry** or **BGS earthquake GeoRSS** depending on whether the next demo need is station telemetry or seismic events. Treat **Met Office Weather DataHub** as a later integration unless we explicitly want to manage API keys and subscription terms.

## Scoring Summary

Scores are 1-5, where 5 is strongest.

| Source | Value/relevance | Suitability | Feasibility | Standards fit | Access openness | Overall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Environment Agency Hydrology | 5 | 5 | 5 | 4 | 5 | 24/25 |
| UK-AIR SOS | 5 | 4 | 4 | 5 | 5 | 23/25 |
| BGS Sensor Data / Earthquake feeds | 4 | 4 | 4 | 5 for SensorThings, 3 for GeoRSS | 4 | 21/25 |
| Met Office DataHub | 4 | 4 | 3 | 3 | 2 | 16/25 |

## 1. Environment Agency Hydrological Open Data

### What It Is

The Environment Agency Hydrological Open Data portal provides live and historic hydrometric and water-quality data for England. The data.gov.uk listing says it includes data from roughly 7,000 stations, including river flow, river level, groundwater, and rainfall. It includes high-resolution data, mainly 15-minute, daily data, and real-time telemetry updates.

Official portal and API:

- Dataset page: https://www.data.gov.uk/dataset/98a4d46e-23e7-4430-883c-9e5f14645e8f/hydrological-open-data
- Explorer: https://environment.data.gov.uk/hydrology/
- API reference: https://environment.data.gov.uk/hydrology/doc/reference
- Stations JSON: https://environment.data.gov.uk/hydrology/id/stations.json?_limit=3
- Measures JSON: https://environment.data.gov.uk/hydrology/id/measures.json?_limit=5

### Access and Licensing

- Public access without authentication in tested endpoints.
- JSON, GeoJSON, CSV, RDF, TTL, and HTML formats are advertised by API metadata.
- License metadata in API responses reports OGL 3.
- Data may be provisional and subject to revision after quality-control procedures.

### Probe Results

Verified endpoints:

- `https://environment.data.gov.uk/hydrology/id/stations.json?_limit=3` returned HTTP 200 JSON with station records, latitude/longitude, station labels, notation IDs, and API metadata.
- `https://environment.data.gov.uk/hydrology/id/measures.json?_limit=5` returned HTTP 200 JSON with measure records including parameter, parameterName, period, periodName, valueType, observedProperty, and station-linked series semantics.
- Parameter-filtered measure endpoints for `level` and `rainfall` returned usable JSON.

Important implementation note: the API is format-sensitive. The plain `.../id/stations?limit=3` shape returned a 400 during probing, while `.json?_limit=3` and `?_format=json` shapes worked. Use the documented linked-data conventions rather than inventing query names.

### Data Model Fit

Best existing exemplar: `publishers/usgs_water`.

Recommended CSAPI model:

- One procedure for Environment Agency hydrology observation ingestion.
- One system per station or curated station.
- One datastream per measure/parameter/statistic combination.
- Optional deployment grouping by catchment, region, or curated demo area.
- Observations carry value, timestamp, qualifier/status where available, measure ID, parameter, unit, period, and source reading URL.

### Value

Very high. This adds a rich environmental/hydrological layer to the demo, complementary to existing USGS Water. It is especially useful because it gives a UK/England counterpart to the existing USGS water story and exercises station-network modeling at real scale.

### Risks

- Need curate the station list; the full source is too large for a casual demo publisher.
- Need choose a small set of station/measure pairs and avoid uncontrolled polling.
- Need handle revised/provisional values.
- Need confirm exact reading query patterns for the selected measures during implementation.

### Recommendation

Implement first. It is the strongest combination of value, open access, machine-readable API, and fit to our existing best-of-breed `usgs_water` publisher pattern.

## 2. UK-AIR Sensor Observation Service

### What It Is

Defra UK-AIR provides a Sensor Observation Service for air pollution measurements. The service is a 52 North SOS implementation supporting OGC SOS 1.0.0, SOS 2.0.0, and the European Air Quality e-Reporting data model. It also exposes a REST API through the 52 North Timeseries API.

Official documentation and endpoints:

- Overview: https://uk-air.defra.gov.uk/data/about_sos
- SOS GetCapabilities: https://uk-air.defra.gov.uk/data/sos/service?service=SOS&request=GetCapabilities
- REST API docs: https://uk-air.defra.gov.uk/data/sos/static/doc/api-doc/
- REST API root: https://uk-air.defra.gov.uk/sos-ukair/api/v1/
- Stations: https://uk-air.defra.gov.uk/sos-ukair/api/v1/stations?limit=3
- Timeseries: https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries?limit=3

### Access and Licensing

- Public REST endpoints responded without authentication.
- Site states content is available under Open Government Licence v3.0 except where otherwise stated.
- SOS supports KVP, SOAP, POX, REST, JSON POST, and EXI bindings.
- Transactional extension is not implemented, which is fine because we only need read access.

### Probe Results

Verified endpoints:

- `https://uk-air.defra.gov.uk/sos-ukair/api/v1/` returned HTTP 200 JSON listing resources: services, stations, timeseries, categories, offerings, features, procedures.
- `https://uk-air.defra.gov.uk/sos-ukair/api/v1/stations?limit=3` returned HTTP 200 JSON station GeoJSON-style records.
- `https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries?limit=3` returned HTTP 200 JSON timeseries metadata with station, pollutant vocabulary URI, units, and identifiers.
- `https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/3` returned a Camden Kerbside nitrogen dioxide timeseries with first/last values, station, phenomenon, category, procedure, feature, and unit `ug.m-3`.
- `https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/3/getData?timespan=PT24H/2026-05-26T00:00:00Z` returned HTTP 200 JSON time-value pairs.

### Data Model Fit

Best existing exemplar: `publishers/usgs_water`, with strict compatibility notes from `publishers/aviation_wx`.

Recommended CSAPI model:

- One procedure for UK-AIR pollutant observation ingestion.
- One system per monitoring site, if we can consolidate pollutant-specific station labels cleanly.
- One datastream per pollutant per station.
- Observations carry timestamp, pollutant code/URI, value, unit, station ID, source timeseries ID, and optional quality/status if exposed through extras/raw SOS metadata.

Alternative model:

- If the 52 North station IDs are pollutant-specific rather than physical-site-specific, start with one system per UK-AIR timeseries for implementation simplicity, then later consolidate by site. This is less elegant but may reduce initial ambiguity.

### Value

Very high. Air quality is immediately understandable in a demo and pairs well with public-health, urban, environmental, and weather/hydrology stories. The source is standards-based, which is especially relevant for an OGC/CSAPI demonstration.

### Risks

- The API is beta and built on older SOS/SensorML/O&M conventions.
- Station labels in quick probes appear pollutant-specific, so physical station consolidation needs careful source analysis.
- Need choose a curated set of pollutants and stations to avoid a very large publisher footprint.
- Timeseries timestamps are millisecond epoch values and must be normalized carefully.

### Recommendation

Implement second. It is highly relevant and standards-aligned, but slightly more model-heavy than Environment Agency Hydrology.

## 3. BGS Sensor Data Service and Related Seismology Feeds

### What It Is

The supplied BGS Sensor Data URL points to a BGS SensorThings API powered by FROST Server. It exposes public sensor data in OGC SensorThings API v1.1 format. The site describes groundwater temperature/levels, barometric pressure, motion sensors, weather stations, geothermal/urban observatory data, events, and complex multidatastream data.

Official Sensor Data endpoints:

- Landing page: https://sensors.bgs.ac.uk/
- API docs: https://sensors.bgs.ac.uk/api.html
- SensorThings API root: https://sensors.bgs.ac.uk/FROST-Server/v1.1
- OpenAPI spec: https://sensors.bgs.ac.uk/FROST-Server/v1.1/api
- Interactive API docs: https://sensors-docs.bgs.ac.uk/

Important correction: the BGS Sensor Data page explicitly says seismic data is outside the scope of the Oracle sensor database and the SensorThings API, and points to BGS earthquake/seismology systems for seismic data.

Adjacent BGS earthquake/seismology sources:

- BGS Earthquake Seismology: https://www.earthquakes.bgs.ac.uk/
- Recent UK events: https://www.earthquakes.bgs.ac.uk/earthquakes/recent_uk_events.html
- Online data feeds: https://www.earthquakes.bgs.ac.uk/feeds/feeds.html
- Recent UK earthquake GeoRSS: https://www.earthquakes.bgs.ac.uk/feeds/MhSeismology.xml
- Recent world earthquake GeoRSS: https://www.earthquakes.bgs.ac.uk/feeds/WorldSeismology.xml

### Access and Licensing

SensorThings API:

- Public access without authentication in tested endpoints.
- API records include access and usage properties such as `access_restriction` and `data_usage`.
- Landing page says only publicly available data is released, but records may carry restrictions and usage metadata.

BGS earthquake feeds:

- Public GeoRSS and KML feeds.
- Feed page says data are under Open Government Licence, subject to acknowledgement: `Contains British Geological Survey materials © UKRI [year]`.

### Probe Results

Verified SensorThings endpoints:

- `https://sensors.bgs.ac.uk/FROST-Server/v1.1` returned HTTP 200 JSON listing SensorThings collections including Things, Locations, Datastreams, MultiDatastreams, Observations, ObservedProperties, Sensors, and FeaturesOfInterest.
- `https://sensors.bgs.ac.uk/FROST-Server/v1.1/Things?$top=3` returned Things such as BGS groundwater loggers with rich properties.
- `https://sensors.bgs.ac.uk/FROST-Server/v1.1/Datastreams?$top=3&$expand=Thing,ObservedProperty,Sensor` returned datastream metadata including units, observed area, phenomenonTime, access restriction, and data usage.
- `https://sensors.bgs.ac.uk/FROST-Server/v1.1/Observations?$top=3&$orderby=phenomenonTime desc` returned recent observation/event records.

Verified earthquake feed endpoints:

- `https://www.earthquakes.bgs.ac.uk/earthquakes/recent_uk_events.html` returned a recent-events table updated on 2026-05-26.
- `https://www.earthquakes.bgs.ac.uk/feeds/MhSeismology.xml` returned GeoRSS with recent UK earthquake items, title, description, pubDate, category, lat, long, magnitude, depth, and source detail link.
- `https://www.earthquakes.bgs.ac.uk/feeds/WorldSeismology.xml` returned GeoRSS for recent world seismic events.

### Data Model Fit

There are two distinct opportunities here.

#### 3A. BGS SensorThings telemetry

Best existing exemplar: `publishers/usgs_water`, with some direct SensorThings-specific adapter logic.

Recommended CSAPI model:

- One procedure for BGS SensorThings telemetry ingestion.
- One system per SensorThings Thing.
- One datastream per SensorThings Datastream.
- Observations map from SensorThings Observations, preserving result, resultTime, phenomenonTime, resultQuality, parameters, and FeatureOfInterest references.

This is a strong technical fit because SensorThings is already close to CSAPI/SOSA/SSN concepts.

#### 3B. BGS earthquake GeoRSS

Best existing exemplar: `publishers/usgs_eq`.

Recommended CSAPI model:

- One procedure for BGS earthquake feed ingestion.
- One feed-adapter system.
- One datastream for UK earthquake events, optionally another for world events or induced seismicity.
- Observations represent one feed item per earthquake event.
- Dedupe by source detail URL plus pubDate, or by parsed event timestamp/location/magnitude when needed.

This duplicates some thematic ground already covered by USGS EQ, but it adds UK-specific national-authority relevance.

### Value

Medium-high to high, depending on which branch we choose.

- SensorThings telemetry is valuable because it exercises an OGC SensorThings source and UK geothermal/groundwater observatory data.
- Earthquake GeoRSS is immediately demo-friendly and easy to implement, but overlaps with the existing USGS Earthquake publisher unless the UK-specific angle matters.

### Risks

- The original source lead is slightly conflated: geothermal/environmental telemetry and seismology are not served from the same API.
- SensorThings exposes rich nested data and many datastreams; we need curate a small subset.
- Some SensorThings records may carry access restrictions or usage constraints in properties; publisher must filter to unrestricted/OGL-compatible records.
- Earthquake GeoRSS is less semantically rich than USGS EQ GeoJSON and may require parsing description strings for magnitude/depth.

### Recommendation

Do not treat this as one publisher. Split it into two candidate tasks:

1. **BGS SensorThings telemetry publisher** if we want standards-rich station telemetry and geothermal/groundwater data.
2. **BGS earthquake GeoRSS publisher** if we want a quick UK-specific seismic event feed.

Prioritize after UK-AIR unless the demo specifically needs UK seismology sooner.

## 4. Met Office Weather DataHub

### What It Is

Met Office Weather DataHub provides several weather products, including atmospheric model data, site-specific forecasts, observations, and map images. The most relevant product for a publisher is Land Observations, which provides recent historical weather data from ground-based instruments across UK locations.

Official pages:

- Landing page: https://datahub.metoffice.gov.uk/
- Land Observations API docs: https://datahub.metoffice.gov.uk/docs/g/category/observations/type/land-observations/api-documentation
- Observations overview: https://datahub.metoffice.gov.uk/docs/g/category/observations/overview
- Observations pricing: https://datahub.metoffice.gov.uk/pricing/observations

### Access and Licensing

This is the major constraint.

The DataHub workflow is explicitly:

1. Register for an account.
2. Choose a product.
3. Select data.
4. Subscribe to a plan.
5. Get data via API.

The Land Observations pricing page indicates a free plan up to 360 calls per day, with paid monthly tiers above that. The sample data page says sample data is historic, free of charge, and not for commercial or operational use or redistribution.

### API Shape

The Land Observations API documentation states typical usage is:

1. Call `GET /observation-land/1/nearest` with latitude/longitude or geohash to find the nearest land observation location.
2. Call `GET /observation-land/1/{geohash}` to retrieve observations for that location.
3. Cache nearest lookups to reduce unnecessary calls.

### Data Model Fit

Best existing exemplar: `publishers/aviation_wx` or `publishers/usgs_water`, depending on implementation scope.

Recommended CSAPI model:

- One procedure for Met Office land observation ingestion.
- One system per selected Met Office observation location/geohash.
- One datastream per selected location, or per parameter group if the API result is broad.
- Observations carry temperature, wind, pressure, precipitation, visibility, humidity, and other available land-observation fields.

### Value

High in general weather terms, but lower marginal value for our current publisher fleet because we already have Aviation WX, NWS/NDBC-like weather, and other environmental data. Its main value would be UK official weather observations and forecast-adjacent context.

### Risks

- Requires registration, application/subscription setup, and API key management.
- Free tier may be enough for a small demo, but it still creates operational overhead.
- Terms for sample data are restrictive and not suitable for a public operational demo.
- Product plans and subscription state introduce failure modes not present in the open public APIs above.

### Recommendation

Defer. It is feasible if we intentionally accept account/key/subscription management, but it should not precede the open, public, standards-aligned sources.

## Recommended Implementation Order

### Phase 1: Environment Agency Hydrology

Build a curated station-network publisher based on `usgs_water`.

Initial scope:

- Select 5-10 stations across river level, river flow, rainfall, and groundwater if available.
- Bootstrap one system per station and one datastream per selected measure.
- Poll latest readings for selected measures.
- Preserve source measure IDs, period, parameter, units, qualifier/status, and revision/provisional notes.

Why first:

- Strongest feasibility.
- Strongest open-data posture.
- Excellent fit with existing CSAPI modeling patterns.
- High demo relevance.

### Phase 2: UK-AIR SOS

Build a curated air-quality publisher based on `usgs_water`, with strict bootstrap practices from `aviation_wx`.

Initial scope:

- Select a small set of recognizable stations and pollutants, for example nitrogen dioxide, PM2.5, PM10, ozone.
- Decide whether to consolidate pollutant-specific station labels into physical systems or use one system per timeseries for the first pass.
- Poll recent timeseries values through the 52 North REST API.
- Preserve pollutant vocabulary URI and unit metadata.

Why second:

- Very high environmental/public-health value.
- Strong OGC/SOS standards story.
- Slightly more modeling ambiguity than hydrology.

### Phase 3: BGS, Chosen Branch

Choose one of two branches:

- **3A: BGS SensorThings telemetry** for geothermal/groundwater/environmental telemetry.
- **3B: BGS earthquake GeoRSS** for UK-specific seismic events.

Recommendation: choose 3A if the goal is standards-rich sensor interoperability; choose 3B if the goal is a quick visible event layer.

Why third:

- Valuable, but the supplied lead splits into two different data products.
- Requires one extra scoping decision before implementation.

### Phase 4: Met Office Weather DataHub

Implement only after deciding that subscription/API-key overhead is acceptable.

Initial scope if pursued:

- Use the free Land Observations plan if terms allow the intended demo use.
- Select a small set of geohashes/locations.
- Cache nearest-location lookups.
- Store API key in environment config only.

Why fourth:

- Technically feasible but not as open-demo-friendly as the other three.

## Publisher Pattern Mapping

| Source | Existing pattern to start from | Notes |
| --- | --- | --- |
| Environment Agency Hydrology | `publishers/usgs_water` | Station network with multiple measures/datastreams. |
| UK-AIR SOS | `publishers/usgs_water` + `publishers/aviation_wx` | Station/pollutant datastreams with strict SensorML split and 52 North REST adapter. |
| BGS SensorThings telemetry | `publishers/usgs_water` | SensorThings Things to CSAPI systems; Datastreams to CSAPI datastreams. |
| BGS earthquake GeoRSS | `publishers/usgs_eq` | Pattern C event-feed adapter. |
| Met Office Land Observations | `publishers/aviation_wx` or `publishers/usgs_water` | Weather station/location observations, but account/API-key gated. |

## Open Questions Before Implementation

Environment Agency Hydrology:

- Which geography should the demo emphasize?
- Which parameter mix matters most: river level, flow, rainfall, groundwater, water quality?
- Should we mirror USGS Water exactly or intentionally show a UK counterpart?

UK-AIR:

- Which pollutants should be in the first cut?
- Should one physical site become one system with multiple pollutant datastreams, or should each API timeseries become its own system initially?
- Do extras/raw SOS metadata expose useful license, QA, or station-network fields worth preserving?

BGS:

- Do we want geothermal/groundwater telemetry or seismology first?
- For SensorThings, which Things/Datastreams are unrestricted and demo-relevant?
- For earthquake feeds, do we want UK-only, induced seismicity, world earthquakes, or multiple datastreams?

Met Office:

- Are we willing to register and manage a DataHub subscription/API key?
- Do the free-plan terms permit the intended public demonstration use?
- Does this duplicate too much of the existing weather publisher story?

## Final Recommendation

Proceed in this order:

1. Environment Agency Hydrology.
2. UK-AIR SOS.
3. BGS, after choosing SensorThings telemetry versus earthquake GeoRSS.
4. Met Office DataHub, only if API-key/subscription management is acceptable.

This order maximizes near-term success while still preserving high-value follow-on options. It also lets us reuse the best current OSHConnect-Python patterns cleanly: `usgs_water` for station networks, `usgs_eq` for event feeds, and `aviation_wx` for strict CSAPI/SensorML compatibility.
