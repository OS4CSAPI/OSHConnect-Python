# Storebaelt Source Retirement Disposition

**Date:** 2026-06-04  
**Decision:** Retire Storebaelt webcams as an active public OS4CSAPI/OSH publisher source.

## Permission Request Outcome

Sam Bolling requested permission and usage guidance from Storebaelt/Sund & Baelt for limited, non-commercial OGC API - Connected Systems standards-evaluation use of the publicly visible Storebaelt webcam data.

Lene Gebauer Thomsen, Head of Corporate Communication at Sund & Baelt Holding A/S, replied that she administers the service and that Storebaelt is in the process of shutting it down. Her response stated that it will not be possible to use the service as a case for the project.

The response is not an approval with conditions. Treat it as a provider refusal for this demonstration use case, plus an operational warning that the source is going away.

## Actions Taken

- Stopped and disabled `storebaelt-webcams-publisher.service` on the Oracle host.
- Removed the Storebaelt camera deployments, grouping deployments, systems, and procedure from the public OSH/CSAPI instance using the package cleanup path.
- Verified the service is inactive and disabled.
- Verified cleanup dry-run finds no remaining Storebaelt resources.
- Archived the Storebaelt publisher entry points behind `STOREBAELT_WEBCAMS_ALLOW_ARCHIVED=1` so they cannot be accidentally restarted as an active public source.

## Retained Value

The implementation remains useful as historical engineering evidence for:

- camera/media source modeling in CSAPI;
- poster-image freshness heartbeat semantics;
- separating source-check time from image-content change time;
- strict SWE result field ordering;
- datastream schema immutability after observations;
- Explorer UX patterns for distinguishing a still poster from a live provider player;
- permission-review workflow for public media sources.

## Replacement Source Criteria

Do not select a replacement webcam/media source for public demonstration unless at least one of these is true:

- the provider gives explicit permission;
- the source has an open data/media license allowing the intended use;
- the source has documented API or reuse terms allowing media integration;
- the source is a government/public-domain source with clear reuse permissions.

For future media publishers, prefer CSAPI-native metadata, freshness, and health observations first. Add live playback, snapshots, or stream relay only when the provider terms clearly allow the chosen media use.