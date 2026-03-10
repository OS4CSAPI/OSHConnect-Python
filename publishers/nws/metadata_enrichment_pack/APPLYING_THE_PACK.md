# Applying the Pack

## Minimum viable application

If you want a low-risk pass that is very likely to work:

- use the enriched descriptions
- add keywords arrays
- add documentation / externalLinks arrays
- add operator/contact metadata
- add the representative image metadata block
- update the Arizona deployment wording

## If your OSH/CSAPI server is strict

Some deployments may ignore or reject custom metadata keys that are not part of the expected resource schema.
If that happens, keep the content but move it into:
- longer `description` text
- SensorML `documentation`, `contacts`, `identifiers`, and `classifiers`
- a sidecar manifest in the repo for future UI use

## Suggested validation checklist

- bootstrap still posts procedure successfully
- systems still post successfully
- SensorML body still saves successfully
- datastream creation still works
- Explorer still renders resource cards and popups
- extra metadata fields are preserved by the server
