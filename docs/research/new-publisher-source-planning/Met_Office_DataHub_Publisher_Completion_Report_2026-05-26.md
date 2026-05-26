# Met Office DataHub Publisher Completion Report - 2026-05-26

## Summary

Met Office Weather DataHub Land Observations is now implemented, deployed on the Oracle publisher host, bootstrapped into the live OSH endpoint, and running as a persistent systemd service.

## Live Deployment

- Service: `met-office-datahub-publisher.service`
- Host: Oracle VM `129.80.248.53`
- CSAPI endpoint: `https://129-80-248-53.sslip.io/sensorhub/api`
- Source API: `https://data.hub.api.metoffice.gov.uk/observation-land/1`
- Runtime cadence: 1 hour
- Secret handling: Met Office key stored in a root-owned host-local key file referenced by `/etc/os4csapi/publisher-secrets.env`; no raw key is stored in git.

## CSAPI Resources

- Procedure: `urn:os4csapi:procedure:met-office-datahub-land-observations:v1` -> `04eg`
- Deployment group: `urn:os4csapi:deployment:met-office-datahub-land-observations:v1` -> `05lg`
- Systems:
  - London Heathrow Area -> `05og`
  - Stornoway Coastal Area -> `05p0`
  - Cairngorm Upland Area -> `05pg`

The bootstrap created 27 datastreams: 9 parameter datastreams for each of the 3 curated locations.

## Live API Findings

- Authentication works with the `apikey` header.
- The nearest endpoint requires `lat` and `lon` parameter names with at most two decimal places.
- Observation records use lowercase `datetime` and flat parameter fields such as `temperature`, `humidity`, `mslp`, `wind_speed`, and `wind_gust`.
- Wind direction arrives as compass text and is mapped to degrees.
- Pressure tendency arrives as `F`, `S`, or `R` and is mapped to `-1`, `0`, or `1`.
- Some locations may omit a subset of parameters in the latest record; the publisher posts the available recognized readings.

## Validation

- Authenticated probe resolved London Heathrow nearest geohash `gcpsvg` and found 48 candidate records.
- Dry-run cycle normalized live readings for all available current parameters.
- Bootstrap succeeded on live OSH.
- One-shot live publisher cycle posted 22 observations with 0 errors.
- The persistent service is enabled and active.
- CSAPI read-back confirmed:
  - deployment query returned 1 item for the Met Office Land Observations group;
  - London Heathrow system query returned 1 item;
  - `air_temperature` datastream `05r0` returned at least 1 observation.

## Follow-Up

- Add an Explorer thumbnail/symbol fallback if the card needs visual polish or if OSH metadata update limits prevent rich SensorML imagery from surfacing.
- Consider Met Office Global Spot as a follow-on forecast publisher using the same Oracle secret-injection pattern.