# Live Source Verification

**Verified date:** 2026-03-11

This package was not built from local assumptions alone. The following upstream
USGS NIMS resources were queried live on 2026-03-11 and used to shape the package.

## Verified live endpoints

- `https://api.waterdata.usgs.gov/nims/v0/cameras?camId=AZ_Colorado_River_at_Lees_Ferry_Upstream`
- `https://api.waterdata.usgs.gov/nims/v0/listFiles?camId=AZ_Colorado_River_at_Lees_Ferry_Upstream&limit=3&recent=true`
- `https://api.waterdata.usgs.gov/nims/v0/listFiles?camId=AZ_Colorado_River_at_Lees_Ferry_Upstream&limit=2&recent=true&rawItem=true`
- `https://api.waterdata.usgs.gov/nims/v0/cameras?siteId=09380000`
- `https://api.waterdata.usgs.gov/nims/v0/cameras?limit=5`
- `https://api.waterdata.usgs.gov/nims/v0/cameras?limit=2000`

Representative resolution URLs were also verified live for camera
`AZ_Colorado_River_at_Lees_Ferry_Upstream`.

## Most important observations

### 1. `cameras?camId=...` returns a single object

Verified response fields include:

- `camId`
- `nwisId`
- `camName`
- `camDesc`
- `lat`, `lng`
- `stateAbrv`
- `tz`
- `createdDate`, `modifiedDate`
- `newestImageDT`
- `TL_enabled`
- `TL_lastGeneratedDT`
- `TL_lastImageUsedDT`
- `overlayDir`, `thumbDir`, `smallDir`, `tlDir`
- `ingest.period`, `ingest.intr`
- `locus`

This is the best live source for camera identity and resolution-path metadata.

### 2. `listFiles` supports two useful response modes

Plain mode:

- returns a JSON array of filename strings

Rich mode:

- `rawItem=true` returns objects with:
  - `camId`
  - `filename`
  - `timestamp`
  - `fs`

This matters because the current publisher uses plain mode, but richer future
contracts could use rawItem metadata without scraping the filename alone.

### 3. `siteId` camera discovery can return multiple cameras per site

Verified example:

- `siteId=09380000` returned two cameras

This is a core modeling fact because the current curated publisher chooses one
camera per station system.

### 4. Some curated sites currently have multiple live cameras

Verified live snapshot for the curated set:

- `09380000` -> 2 cameras
- `09019850` -> 4 cameras
- the other six curated sites currently resolved to 1 camera each

This is the main evidence behind the package's one-camera-per-station caveat.

### 5. Resolution-specific image and video URLs resolve successfully

Verified HTTP 200 for:

- overlay image URL
- thumbnail image URL
- 720px image URL
- timelapse video URL

This confirms that the observation model is correctly centered on URL references
rather than on binary media ingest.

### 6. Current live inventory snapshot

As measured on 2026-03-11 from `cameras?limit=2000`:

- total cameras: 1137
- hidden: 148
- active: 989
- with NWIS id: 1121
- active with NWIS id: 978
- states represented: 47

The active service surface is therefore large enough that the curated-camera
selection policy is an important part of the design, not just a convenience.
