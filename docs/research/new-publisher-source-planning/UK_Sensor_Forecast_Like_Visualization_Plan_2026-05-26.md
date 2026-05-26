# UK Sensor Forecast-Like Visualization Plan - 2026-05-26

## Summary

It does make sense to add forecast-like visualizations for the new UK sources, but the product language should be precise.

The publishers currently deployed for Environment Agency Hydrology, UK-AIR, BGS SensorThings, and Met Office Land Observations mostly expose observed telemetry. They can support rich map cards, recent-history trend panels, freshness/status badges, threshold bands, and short-horizon context. They should not be labeled as forecasts unless the underlying source is a forecast product.

The recommended plan is therefore two-track:

1. Build a reusable observation trend visualization pattern for the deployed UK station sources.
2. Add separate true forecast publishers for sources that actually expose forecast products, especially Met Office Global Spot / Site-Specific Forecast, UK-AIR pollution forecasts, and Environment Agency / Flood Forecasting Centre flood-risk forecasts.

This gives the Explorer a polished, forecast-style user experience quickly while preserving technical honesty about observed data versus predicted data.

Just as important: this plan should preserve the value already added by richer source-specific media. The buoy sensors, water-monitoring stations, and similar sources with working images, video clips, representative thumbnails, or other context should not be simplified into generic trend/forecast cards. Trend and forecast features should be additive: keep the media and source-specific context that make a station feel real, and improve those affordances whenever a source is touched.

## Current Live UK Source Inventory

| Source | Current publisher type | Current parameters | Persistent service | Forecast status |
| --- | --- | --- | --- | --- |
| Met Office Land Observations | Observed weather stations | Air temperature, humidity, MSLP, visibility, weather code, wind direction, wind speed, wind gust, pressure tendency | `met-office-datahub-publisher.service` | Observation only; true forecast should come from Global Spot / Site-Specific Forecast |
| Environment Agency Hydrology | Observed hydrology stations | River level, river flow, rainfall, groundwater level | `environment-agency-hydrology-publisher.service` | Observation time series; separate flood warnings and five-day flood-risk products exist |
| UK-AIR | Observed air-quality stations | NO2, O3, PM10, PM2.5 | `uk-air-publisher.service` | Observation time series; separate five-day pollution forecast exists |
| BGS SensorThings / UKGEOS | Observed borehole telemetry | Water temperature, conductivity, water level maOD | `bgs-sensorthings-publisher.service` | Trend/baseline visualization only; no forecast product identified |

## Research Findings

### Met Office

Current deployed source:

- Land Observations API: `https://datahub.metoffice.gov.uk/docs/g/category/observations/type/land-observations/api-documentation`
- The Observation Location service is explicitly observational.
- Documented flow is `GET /observation-land/1/nearest`, then `GET /observation-land/1/{geohash}`.
- The docs recommend caching nearest-location lookups.
- Our existing free-plan notes record a 360 calls/day limit for Land Observations.

Forecast-relevant follow-on source:

- Existing session research captured Met Office Weather DataHub Site-Specific Forecast / Global Spot under `/sitespecific/v0`.
- The known product family exposes Global hourly, three-hourly, and daily spot forecast APIs.
- This is the strongest candidate for a true forecast publisher because it is point/location JSON/GeoJSON forecast data rather than gridded GRIB2.
- Atmospheric Models remain a larger separate track because they are gridded model files, likely GRIB2, and need different storage/parsing choices.

Implication:

- Use Land Observations for current conditions and recent trends.
- Use Global Spot / Site-Specific Forecast for actual forecast language, forecast lead times, and forecast panels.

### Environment Agency Hydrology

Current deployed source:

- Hydrology API: `https://environment.data.gov.uk/hydrology/doc/reference`
- The revised Hydrology API provides historic and recent hydrological data from nearly 8,000 monitoring stations.
- It includes sub-daily, typically 15-minute, time series and daily time series.
- Covered parameters include flow, level, rainfall, groundwater level, dissolved oxygen, conductivity, temperature, nitrate, pH, turbidity, and related water-quality values.
- The API includes recent/historic readings endpoints, quality/completeness flags, and fair-use cautions for large data volumes.

Forecast-relevant companion source:

- Flood Monitoring API: `https://environment.data.gov.uk/flood-monitoring/doc/reference`
- It provides near-real-time flood warnings, flood areas, water levels, flows, stations, measures, readings, and historic readings.
- It also documents a five-day flood-risk forecast produced by the Flood Forecasting Centre, issued daily and more frequently during serious flood risk.
- The flood-risk forecast covers the day of issue and the following four days, by county, across river, sea, surface-water, and groundwater flooding for England and Wales.
- The flood-monitoring reference points to forecast API documentation at `https://api.foursources.metoffice.gov.uk/docs/flood-guidance-statement-api-public`.

Implication:

- Immediate Explorer work should show hydrographs, rising/falling trend, station-scale bands, and quality flags from observed hydrology readings.
- True flood forecast work should be a separate publisher because its geometry and semantics are area/county risk, not station telemetry.

### UK-AIR

Current deployed source:

- SOS / 52 North REST API root: `https://uk-air.defra.gov.uk/sos-ukair/api/v1/`
- The API exposes services, stations, timeseries, categories, offerings, features, procedures, and phenomena.
- Current publisher uses station timeseries for observed pollutant concentrations.
- UK-AIR data pages describe over 1,500 monitoring sites, automatic and non-automatic networks, monitoring data, descriptive statistics, exceedance statistics, and licensing under Open Government Licence terms unless otherwise stated.

Forecast-relevant companion source:

- Pollution forecast page: `https://uk-air.defra.gov.uk/forecasting/`
- It provides a more detailed interactive view of the UK Air Pollution Forecast for up to five days ahead.
- The page includes Today, Tomorrow, and Outlook text, a forecast map, postcode/location search, and 1-10 air-pollution bands from Low through Very High.
- The page states the forecast is provided by the Met Office.
- UK-AIR also points users to the Daily Air Quality Index / health-advice material and newer replacement services such as Check air quality and Get air pollution data.

Implication:

- Immediate Explorer work should compute DAQI-like bands only if the pollutant, averaging period, and threshold mapping are correct and documented.
- A true UK-AIR forecast publisher needs a separate source discovery pass to identify machine-readable forecast endpoints behind the public forecast map or replacement service APIs.

### BGS SensorThings / UKGEOS

Current deployed source:

- BGS Sensor API: `https://sensors.bgs.ac.uk/api.html`
- SensorThings API root: `https://sensors.bgs.ac.uk/FROST-Server/v1.1`
- Interactive docs: `https://sensors-docs.bgs.ac.uk/`
- The API uses OGC SensorThings API v1.1 through FROST Server.
- It exposes Things, Locations, Datastreams, Observations, ObservedProperties, Sensors, and FeaturesOfInterest.
- BGS documentation explicitly highlights API usage for querying and plotting data.

UKGEOS context:

- Glasgow Observatory page: `https://www.ukgeos.ac.uk/glasgow-observatory`
- The observatory exists to study shallow mine-water heat energy, heat storage, environmental impacts, and baseline conditions.
- Boreholes and data loggers continuously measure temperature, pressure, conductivity, and related environmental changes.

Implication:

- BGS should not be presented as a forecast without a model.
- The best visualization is a borehole baseline/status panel: stale/current badge, water temperature, water level maOD, conductivity, recent history, and maybe a slow-change anomaly indicator.
- If BGS forecast-like work is desired later, it should be framed as modeled mine-water heat potential or groundwater response, not as a direct source forecast.

## Product Concept

Add a new Explorer card section named something like `Trends` or `Recent Pattern`, not `Forecast`, for observation-backed sources.

The section should appear below `Latest readings` on deployed-system cards and in a compact form in map popups. It should behave like the existing US weather-style popup in visual density: small, useful, glanceable, and grounded in the selected station.

This section should be composed around the existing card value rather than replacing it. If a card already has strong imagery, video clips, source links, station photos, platform thumbnails, or curated attribution, those elements remain first-class. The new time-series or forecast panel should sit beside or below them, not crowd them out.

### Source Value Preservation Rule

Every source update should start with a quick value inventory before changing the card or map behavior.

Check whether the source already has:

- representative thumbnails or station imagery
- camera images, video clips, or externally linked media
- platform-specific diagrams, such as buoy, borehole, aircraft, vessel, or station illustrations
- source attribution, license notes, and public landing-page links
- rich latest-reading labels, role labels, symbols, and source filters
- special map behavior, such as tracks, areas, clustered stations, or deployment geometry
- source-specific freshness handling, stale-data warnings, or quality flags

The default rule is to preserve those features and make them better if the new work touches the source. A trend card should never cause a buoy video, water-monitoring image, station thumbnail, or curated source link to disappear. If layout pressure forces a choice, preserve the source-specific media/context and make the new trend panel collapsible or secondary.

Recommended labels:

| Data type | UI label | Avoid |
| --- | --- | --- |
| Current observed value | `Current conditions` or `Latest readings` | `Forecast` |
| Recent observed series | `Recent trend`, `Last 24h`, `Last 72h` | `Prediction` |
| Derived near-term direction from observations | `Rising`, `Falling`, `Steady`, `Improving`, `Worsening` | `Will rise`, `Will fall` |
| True forecast feed | `Forecast`, `Valid time`, `Lead time`, `Issued` | Treating forecast points as deployed sensors |
| Warning/risk product | `Risk outlook`, `Warning area`, `Severity` | Station-style observation wording |

## Immediate Visualization Plan

### Shared Station Trend Card

Create a reusable Explorer component for recent time-series summaries.

Inputs:

- deployed system / station id
- datastream ids already discovered for the card
- source family key, such as `ea-hydrology`, `uk-air`, `met-office`, or `bgs`
- latest observations already fetched for the card
- optional recent observation fetch window, initially 24h or 72h

Outputs:

- compact mini chart or sparkline per selected parameter
- latest value and unit
- relative age and freshness state
- trend direction from first/last or small linear slope
- parameter-specific badge or threshold band where safe
- source links and attribution already present in the card

Implementation notes:

- Start with SVG sparklines or lightweight CSS/canvas; avoid a heavy charting dependency unless we need axes/interaction.
- Fetch recent observations only when the detail card is open, not during full map load.
- Cap the per-card request count. For example, fetch up to three datastreams, `_limit=48` or similar, and stop if the server returns no data.
- Reuse the card's existing latest-reading labels and freshness logic so visual language stays consistent.
- Cache per datastream for a short browser TTL, roughly 5 minutes, to avoid repeated fetches while clicking stacked features.
- Preserve existing media slots, thumbnails, video links, source attribution, and specialized card sections. The new trend component should be a card section, not a card takeover.

### Source-Specific Behavior

#### Met Office Land Observations

Best visual treatment:

- Weather-station current conditions card.
- Priority fields: air temperature, wind speed/gust/direction, mean sea-level pressure, relative humidity, visibility, weather code.
- Add a small pressure tendency indicator using the existing `-1/0/1` pressure tendency code.
- If recent observations are available per scalar datastream, show a 24h temperature sparkline and wind/pressure summaries.

Demo value:

- Closest to the screenshot-style weather popup.
- Good for London Heathrow, Stornoway, and Cairngorm contrasts.

Constraint:

- Land Observations are observations. Do not call them forecasts.

#### Environment Agency Hydrology

Best visual treatment:

- Hydrograph card with water level / flow / rainfall trend.
- Priority fields: river level, river flow, rainfall, groundwater level.
- Show rising/falling/steady state from recent readings.
- For level stations, research station scale metadata from the hydrology/flood-monitoring station descriptions and show typical range if available.
- Show quality and completeness flags visibly when present.

Demo value:

- Very strong operational feel: recent water movement, rainfall pulses, and groundwater level.
- Good bridge to future flood-risk overlays.

Constraint:

- Do not infer flood forecast from a single gauge trend. The forecast product is separate.

#### UK-AIR

Best visual treatment:

- Air-quality station trend card.
- Priority fields: NO2, O3, PM10, PM2.5.
- Show latest pollutant concentration and recent trend.
- Add a threshold/band badge only after implementing pollutant-specific DAQI threshold logic correctly.
- Consider a small `Improving / Worsening / Stable` badge based on recent slope.

Demo value:

- Strong public-facing interpretability if paired with DAQI language.
- Camden roadside NO2 and rural/background ozone make a good contrast.

Constraint:

- Current SOS values are hourly observations, not the UK-AIR 5-day pollution forecast.

#### BGS SensorThings / UKGEOS

Best visual treatment:

- Borehole status / baseline card.
- Priority fields: water temperature, conductivity, water level maOD.
- Use a longer time horizon if data density permits: 30d or 90d would make more sense than 24h for slow groundwater changes.
- Show stale-source state clearly when upstream latest data is old.

Demo value:

- Shows the difference between rapid operational weather/air/water networks and slow environmental baseline instrumentation.
- The UKGEOS borehole thumbnail and station role already work well.

Constraint:

- No forecast claim. This is a monitoring and baseline-trend visualization.

## True Forecast Publisher Plan

### Phase F1: Met Office Global Spot / Site-Specific Forecast

Priority: highest.

Why:

- We already have session notes that a free-plan key exists for `/sitespecific/v0`.
- It is point forecast data and therefore a natural complement to Met Office Land Observations.
- It can power true forecast language: valid time, lead time, issued time, forecast parameter, and forecast location.

Recommended CSAPI model:

- Procedure: Met Office site-specific forecast retrieval.
- Systems: logical forecast points, not physical stations.
- Deployments: curated forecast locations, possibly co-located with the three Land Observations demo areas.
- Datastreams: either one structured multi-parameter forecast datastream per location/resolution or one datastream per parameter per location, depending on response shape.
- Observations: preserve issue time, valid time, lead time, forecast step, parameter, unit, source location, and source API metadata.

Explorer behavior:

- Card role should be `Forecast Point`, `Weather Forecast Location`, or similar, not `Weather Observation Site`.
- Map symbol should be visually related but distinguishable from physical weather stations.
- Popup can use actual `Forecast` label.

Open research tasks:

- Verify exact endpoint paths for hourly, three-hourly, and daily Global Spot products.
- Verify auth header and query parameters for `/sitespecific/v0`.
- Probe response shape without printing secrets.
- Confirm call limits and caching requirements.

### Phase F2: UK-AIR Five-Day Pollution Forecast

Priority: medium.

Why:

- UK-AIR public pages expose a 5-day pollution forecast with Low / Moderate / High / Very High language and 1-10 index bands.
- The forecast is highly demo-friendly and easy for users to understand.

Recommended research approach:

- Inspect network calls behind `https://uk-air.defra.gov.uk/forecasting/` and the newer `https://check-air-quality.service.gov.uk/` service.
- Identify whether there is a reusable public JSON endpoint, WMS layer, tile source, Atom feed, or static data file.
- Prefer official machine-readable endpoints over scraping rendered page text.

Recommended CSAPI model:

- Procedure: UK air-pollution forecast retrieval.
- Systems: forecast regions/points or a forecast-grid adapter, depending on source shape.
- Deployments: forecast regions or demo locations.
- Observations: forecast issue time, valid day, DAQI band/index, pollutant driver if available, region/location, forecast text.

Explorer behavior:

- Show `Air Quality Forecast`, 1-10 band, Low/Moderate/High/Very High, and forecast day tabs.
- Optionally overlay region polygons or forecast point markers if licensing and source geometry allow.

### Phase F3: Environment Agency / Flood Forecasting Centre Flood-Risk Forecast

Priority: medium-high if flood demo value is desired.

Why:

- Flood-risk outlook is operationally meaningful and officially forecast-oriented.
- It complements the station hydrographs without pretending gauge trends are forecasts.

Recommended research approach:

- Review the Flood Guidance Statement API docs referenced by the Environment Agency flood-monitoring API.
- Check authentication, license, geography, and whether the forecast is public enough for our demo use.
- Identify whether the output is county risk, region risk, images, polygons, or text summaries.

Recommended CSAPI model:

- Procedure: Flood risk forecast retrieval.
- Systems: forecast product adapter or forecast regions.
- Deployments: affected regions/counties.
- Observations: issue time, valid day, risk level, affected area, impact/advice text, source product URL.

Explorer behavior:

- Add a `Flood Risk Outlook` overlay, separate from station observations.
- Use severity/risk bands and area geometry where available.
- Link related EA gauge stations as context, not as the forecast source.

### Phase F4: BGS Modeled Context, Not Forecast

Priority: low unless a specific model source appears.

Why:

- BGS SensorThings telemetry supports trend/baseline monitoring.
- UKGEOS is research infrastructure for mine-water heat and environmental response, but no operational forecast feed was identified.

Potential later work:

- Add anomaly detection against a rolling baseline.
- Add thermal-resource context, such as stable mine-water temperature and long-term water-level movement.
- Only use forecast language if an explicit model or forecast product is published.

## Recommended Build Order

1. Source value inventory and preservation pass
   - Identify existing image, video, thumbnail, attribution, symbol, source-filter, and rich-card behavior for every source being updated.
   - Treat buoy sensors and water-monitoring stations with working media as regression sentinels.
   - Capture before/after screenshots or browser notes for at least one rich-media source whenever the card layout changes.

2. Explorer-only Station Trend Card
   - No new backend publisher required.
   - Fetch recent observations for currently selected station cards.
   - Add source-specific labels and trend rules.
   - Highest visual payoff for the least operational risk.

3. Met Office Global Spot Forecast Publisher
   - True forecast data.
   - Best match to the screenshot-style weather UI.
   - Use existing secret-file pattern and Oracle service deployment practices.

4. EA Hydrology Station Scale / Hydrograph Enrichment
   - Add recent series, quality flags, and station range bands.
   - Consider station-scale metadata enrichment in bootstrap or card fetch.

5. UK-AIR DAQI / Pollution Forecast Discovery
   - Add observed pollutant trend cards first.
   - Only add DAQI or 5-day forecast if threshold/source semantics are correct.

6. Flood-Risk Forecast Overlay
   - Separate forecast-area product.
   - More complex but potentially excellent for demos.

7. BGS Long-Horizon Baseline Panel
   - Make BGS visually useful without forcing a forecast metaphor.

## Acceptance Criteria

For the immediate trend-card phase:

- Production Explorer cards for Met Office, EA Hydrology, UK-AIR, and BGS can show recent series without blocking map load.
- Card fetches are lazy and bounded.
- Each source uses correct labels and units.
- Existing source-specific value-adds, including images, video clips, thumbnails, attribution, rich role labels, source filters, and specialized map behavior, are preserved or improved.
- Buoy sensors and water-monitoring stations with working images/video are included as regression checks when shared card layout changes are made.
- Observation-backed UI uses `Recent trend` or equivalent, not `Forecast`.
- True forecast cards, when added, include issue time and valid time.
- Browser console remains clean after the recent `controlstreams` fix.
- Production smoke test covers at least one card from each source family.

For true forecast publishers:

- Forecast source is official and machine-readable.
- Credential handling follows `/etc/os4csapi/publisher-secrets.env` or service-specific key-file patterns.
- Forecast resources are modeled distinctly from physical deployed sensors.
- Cards clearly distinguish `observed`, `forecast`, `issued`, and `valid` times.
- Docs include source terms, call limits, data model, validation commands, and Explorer verification screenshots or text evidence.

## Risks And Guardrails

- Do not call observation data a forecast.
- Do not infer flood risk from a single hydrology gauge.
- Do not compute DAQI bands without pollutant-specific averaging and thresholds.
- Do not request bulk hydrology history during map load; the Hydrology API has large volumes and fair-use cautions.
- Do not use UKGEOS photographs unless their license is explicitly reusable; continue using the official non-photo borehole illustration unless better terms are found.
- Do not make forecast points look like physical deployed stations.
- Do not flatten rich source cards into a lowest-common-denominator telemetry panel. Preserve buoy media, water-monitoring imagery, video clips, curated thumbnails, attribution, and source-specific map/card behavior.
- Do not let the trend/forecast component become the whole card. It is an additional time-context layer.
- Keep all access-gated Met Office credentials out of git, logs, issue bodies, and screenshots.

## Bottom Line

The clever path is not to bolt a generic forecast card onto everything. It is to make the Explorer fluent in three distinct time semantics:

- `Observed now`: latest station readings.
- `Recent pattern`: bounded recent history and trend from observed telemetry.
- `Forecast outlook`: explicit source forecast products with issue and valid times.
- `Source context`: the imagery, video, attribution, diagrams, station identity, and specialized behavior that make each data source worth exploring.

That model lets the new UK sources feel as rich as the US weather-style cards while keeping the data story accurate and defensible.