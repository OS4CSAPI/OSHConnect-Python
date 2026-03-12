# Live Source Verification

**Verified date:** 2026-03-12

This package was not built from local assumptions alone. The following official
USGS earthquake resources were queried live on 2026-03-12 and used to shape the package.

## Verified live endpoints and pages

- `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson`
- `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson`
- `https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/nc75326262.geojson`
- `https://earthquake.usgs.gov/fdsnws/event/1/query.geojson?format=geojson&eventid=nc75326262`
- `https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php`
- `https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson_detail.php`
- `https://earthquake.usgs.gov/earthquakes/feed/policy.php`
- `https://earthquake.usgs.gov/data/comcat/index.php`
- `https://earthquake.usgs.gov/data/comcat/data-eventterms.php`

## Most important observations

### 1. The current `all_day` summary feed is live and healthy

Verified response metadata:

- title: `USGS All Earthquakes, Past Day`
- status: `200`
- api version: `2.3.0`
- count at verification time: `287`

This confirms the current publisher's default feed choice is still valid.

### 2. `significant_month` is also live and useful as a lower-volume alternative

Verified response metadata:

- title: `USGS Significant Earthquakes, Past Month`
- status: `200`
- api version: `2.3.0`
- count at verification time: `11`

This is the strongest low-volume alternative if the project ever wants a more
curated event stream without changing the Pattern C model.

### 3. Summary features already expose more fields than the current result contract

Verified example `nc75326262` includes:

- `url`
- `detail`
- `sig`
- `alert`
- `tsunami`
- `net`
- `code`
- `ids`
- `sources`
- `types`
- `nst`
- `dmin`
- `rms`
- `gap`

The current publisher only maps a subset of these, which is acceptable for the
baseline runtime but should be documented explicitly.

### 4. The detail feed is the main enrichment surface

Verified example `detail/nc75326262.geojson` adds a `products` object with:

- `nearby-cities`
- `origin`
- `phase-data`
- `scitech-link`

Those product entries expose:

- contributor source
- product update time
- contributor-specific properties
- contents URLs such as QuakeML and JSON files

This is the most important official source for future selective enrichment.

### 5. The FDSN `query.geojson` event service aligns with detail-feed semantics

For `eventid=nc75326262`, the `query.geojson` response matched the detail feed
in the areas that matter to this package:

- same event id
- same geometry
- same summary-style properties
- same `products` block shape for this event

That means the FDSN service is a valid companion source for targeted fetches and
future backfill, but the current summary-feed runtime does not need to be replaced.

### 6. Official lifecycle guidance is favorable for a feed-based publisher

The feed lifecycle policy states:

- any production feed will be available for at least six months in production or deprecated form
- at least 30 days notice is given before a feed is deprecated and before removal

This materially lowers the risk of documenting official feed URLs in the bootstrap.

### 7. Official field semantics support richer future contracts

The event terms documentation confirms that:

- `alert` carries PAGER-based impact severity
- `net` is the contributor code
- `sig` is a significance score
- `status` is a review state
- `tsunami` is a binary tsunami-association flag
- `types` describes available product families
- `updated` is the event update time in epoch milliseconds

These are the best candidates for optional future result-body expansion if the
Explorer or downstream APIs need more than the current lean summary contract.
