# BuoyCAM reference

NDBC documents a direct URL pattern for the most recent BuoyCAM image for a station:

`https://www.ndbc.noaa.gov/buoycam.php?station=xxxxx`

Replace `xxxxx` with the station ID.

Important caveats:
- only some stations have BuoyCAMs
- photos are generally taken during daylight operations
- an older-than-16-hours image condition can result in no image being displayed
- invalid or non-BuoyCAM stations return specific error messages

## Recommended modeling approach

- add `has_buoycam: true/false` to curated station metadata
- expose the direct BuoyCAM URL as a station characteristic or documentation link
- do not require an image for all stations
- fall back to a representative buoy icon/class image when no BuoyCAM exists
