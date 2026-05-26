# Met Office Weather DataHub API Notes

Date: 2026-05-26

## Purpose

Capture Met Office Weather DataHub access information and API documentation links for follow-up publisher planning.

This is a staging document. More source details are expected before implementation begins.

## Credential Status

An API key for the Met Office Weather DataHub Atmospheric Models free plan was provided during the working session.

An API key for the Met Office Weather DataHub Global Spot / Site-Specific Forecast free plan was also provided during the working session.

A Met Office Weather DataHub Land Observations free-plan subscription key was provided during the working session.

The raw key is intentionally not recorded in this repository. Store it only in a local secret location such as `.env`, shell profile, or deployment secret storage.

For this workspace, the preferred local file is `publishers/.env`. The repository `.gitignore` excludes `.env`, so `publishers/.env` is ignored by git.

Recommended local environment variable names:

```text
MET_OFFICE_ATMOSPHERIC_API_KEY
MET_OFFICE_GLOBAL_SPOT_API_KEY
MET_OFFICE_LAND_OBSERVATIONS_API_KEY
```

Do not commit the key to git, documentation, test fixtures, screenshots, logs, or issue bodies.

Known Atmospheric Models key context from the provided credential:

- Product family: Met Office Weather DataHub Atmospheric Models
- Subscribed API context: `/atmospheric-models/1.0.0`
- Plan/tier: free atmospheric models plan
- Token type: API key

Known Global Spot / Site-Specific Forecast key context from the provided credential:

- Product family: Met Office Weather DataHub Site-Specific Forecast / Global Spot
- Subscribed API context: `/sitespecific/v0`
- Subscribed API name: `SiteSpecificForecast`
- Plan/tier: free site-specific plan
- Stated call allowance: 360 calls per day
- Token type: API key

Known Land Observations key context:

- Product family: Met Office Weather DataHub Observations / Land Observations
- API family: Observation Location service
- Subscribed API context: `/observation-land/1`
- Subscribed API name: `CDP_Observation_Land`
- Plan/tier: free Land Observations plan
- Stated call allowance: 360 calls per day
- Token type: API key

## Documentation Links

- Atmospheric overview: https://datahub.metoffice.gov.uk/docs/f/category/atmospheric/overview
- Weather DataHub docs root: https://datahub.metoffice.gov.uk/docs
- Weather DataHub glossary: https://datahub.metoffice.gov.uk/docs/glossary
- Land Observations overview: https://datahub.metoffice.gov.uk/docs/g/category/observations/overview
- Land Observations API documentation: https://datahub.metoffice.gov.uk/docs/g/category/observations/type/land-observations/api-documentation
- Land Observations pricing: https://datahub.metoffice.gov.uk/pricing/observations
- Weather DataHub landing page: https://datahub.metoffice.gov.uk/
- Met Office support: https://datahub.metoffice.gov.uk/support/faqs
- Met Office legal: https://www.metoffice.gov.uk/about-us/legal

## Initial Source Understanding

There are now three distinct Met Office Weather DataHub products under consideration.

### Atmospheric Models

Atmospheric Models are not the same product as Land Observations.

Atmospheric Models provide gridded model data in GRIB2 format. GRIB2 is a WMO-sponsored binary format used in meteorology for historical and forecast weather data.

Available model families listed in the public overview include:

- Global deterministic 10 km
- UK deterministic 2 km standard projection
- UK deterministic 2 km latitude-longitude projection
- Met Office Global and Regional Ensemble Prediction System, Global 20 km
- Met Office Global and Regional Ensemble Prediction System, UK 2 km

The Weather DataHub documentation describes an order-based workflow. An order defines the requested model, region of interest, parameters, time steps, model runs, and file delivery preferences. The system then provides retrieval URLs for generated files.

### Global Spot / Site-Specific Forecast

Global Spot is part of the Site-Specific Forecast product family. The Weather DataHub landing page describes Global Spot as a deterministic site-specific forecast product for a single specified location defined by latitude and longitude.

Public product text lists three GeoJSON APIs:

- Global hourly spot data 1.0.2
- Global three-hourly spot data 1.0.2
- Global daily spot data 1.0.2

This product looks more immediately compatible with a CSAPI scalar-observation publisher than Atmospheric Models, because it is point/location forecast data rather than gridded GRIB2 files.

### Land Observations

Land Observations is the closest fit to the original Met Office publisher plan.

The public documentation describes recent observational data from ground-based instruments across roughly 150 UK station locations. The API provides hourly JSON observations for the past 48 hours and currently advertises 9 parameters. Stations report 24 observations daily at 0000 through 2300 UTC.

The documented API flow is:

1. Call `GET /observation-land/1/nearest` with latitude/longitude or geohash.
2. Cache the nearest land observation location returned by that call.
3. Call `GET /observation-land/1/{geohash}` to retrieve observations for that land location.

The public docs explicitly recommend caching `nearest` endpoint results to reduce unnecessary lookups.

## Publisher Implications

Atmospheric Models are a gridded forecast/model file workflow, not a station-network observation workflow.

Likely CSAPI modeling options need more research:

1. Model-run feed pattern
   - One procedure for Met Office Atmospheric model retrieval.
   - One system representing the model/order adapter.
   - One datastream per configured model/order/parameter bundle.
   - One observation per retrieved model file, carrying file URL, model run time, forecast steps, region, parameters, and metadata.

2. Derived point extraction pattern
   - Retrieve GRIB2 files.
   - Extract selected variables at curated demo points or regions.
   - Publish scalar point observations into CSAPI.
   - Requires a GRIB2 parser and clearer licensing/storage review.

3. Raster/file product pattern
   - Treat model files as media/data artifacts rather than scalar observations.
   - Publish metadata and links to retrieved GRIB2 files.
   - Potentially closer to an imagery/media publisher than to `usgs_water`.

Global Spot likely fits a curated point-forecast pattern:

- One procedure for Met Office Global Spot forecast retrieval.
- One system per curated forecast point or named demo location.
- One datastream per selected forecast parameter/time resolution, or one structured forecast datastream per point if the API returns compact multi-parameter GeoJSON.
- Observations should preserve forecast generation time, valid time, lead time, latitude/longitude, parameter names, units, and source response metadata.

Because Global Spot is forecast data, not observed telemetry, SensorML and card labels should avoid implying a physical deployed sensor at the forecast point.

Land Observations fits the existing station-network publisher model:

- One procedure for Met Office Land Observations ingestion.
- One system per curated Met Office land observation station/location.
- One datastream per selected observed parameter per station, or one structured multi-parameter datastream per station if the live response shape favors compact records.
- One deployment group for the curated Met Office demo set.
- Observations should preserve observation time, source geohash/location identifier, parameter names, units, values, and source response metadata allowed by the terms.

This is the best match for `publishers/usgs_water` and the existing EA/UK-AIR/BGS station-network pattern.

## Open Questions For Next Input

- Which Atmospheric model product/order has been selected in Weather DataHub?
- What order name or retrieval URL should be used?
- Which parameters, region, time steps, and model runs are included in the free-plan order?
- Does the API key authorize order discovery, file listing, direct file retrieval, or all three?
- Are we allowed to persist retrieved GRIB2 files or only metadata/links?
- Should the publisher expose model files as CSAPI observations, extract point values, or both?
- Which Python GRIB2 stack should be used if point extraction is required?
- Which Global Spot endpoint shape should be used: hourly, three-hourly, daily, or a combination?
- What are the exact required query parameters and authentication header for `/sitespecific/v0`?
- Are Global Spot responses GeoJSON FeatureCollections, single Features, or another JSON structure?
- Which curated demo locations should be used for Global Spot forecasts?
- What exact auth header or query parameter does the Land Observations subscription require?
- What exact JSON structure does `GET /observation-land/1/{geohash}` return for live data?
- Which 3-4 curated UK locations best complement the existing demo map while staying well below 360 calls/day?

## Current Recommendation

Stand by for the additional Met Office details before implementing code.

Do not reuse the Land Observations station-network plan for Atmospheric Models without revision. Atmospheric Models need a model-file/order-based design, likely closer to an event/feed or media artifact publisher than a fixed physical station network.

Updated assessment: Land Observations is now the best immediate Met Office publisher candidate because it is real observed telemetry from maintained physical stations, has a station-network model that matches our CSAPI pattern, uses JSON, and has a known free-plan call limit of 360 calls per day.

Global Spot should remain the second Met Office target. It is useful and likely easier than Atmospheric Models, but it is forecast data rather than observed telemetry, so it needs different labeling and modeling.

Atmospheric Models should remain deferred until we explicitly want a GRIB2/model-file publisher.