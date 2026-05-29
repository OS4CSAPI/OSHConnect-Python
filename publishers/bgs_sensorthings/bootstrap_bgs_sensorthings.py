#!/usr/bin/env python3
"""
bootstrap_bgs_sensorthings.py -- Register curated BGS SensorThings telemetry
resources on the OS4CSAPI server.

Creates station-centric CSAPI resources:
  Procedure:
    urn:os4csapi:procedure:bgs-sensorthings:v1

  Systems:
    urn:os4csapi:system:bgs-sensorthings:{siteId}:v1

  Datastreams:
    one datastream per selected BGS SensorThings Datastream under each Thing

Station and datastream selection is read from stations.json in this directory.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from publishers.bootstrap_helpers import (
    get_config, _auth_header,
    api_put, find_by_uid, ensure_procedure, ensure_system, ensure_datastream, ensure_deployment,
    clean_resource, add_bootstrap_args, print_summary,
)


VALID_TIME_START = "2026-01-01T00:00:00Z"

PROC_UID = "urn:os4csapi:procedure:bgs-sensorthings:v1"
DEPLOY_ROOT_UID = "urn:os4csapi:deployment:bgs-sensorthings-demo:v1"
DEPLOY_GROUP_UID = "urn:os4csapi:deployment:bgs-sensorthings-ukgeos-glasgow:v1"

BGS_HOME = "https://sensors.bgs.ac.uk/"
BGS_API_DOCS = "https://sensors.bgs.ac.uk/api.html"
BGS_INTERACTIVE_DOCS = "https://sensors-docs.bgs.ac.uk/"
BGS_API_ROOT = "https://sensors.bgs.ac.uk/FROST-Server/v1.1"
OGL3 = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
UKGEOS_LEGAL = "https://www.ukgeos.ac.uk/legal-and-compliance"
PUBLISH_INTERVAL_SECONDS = 900


def _image_docs(station: dict) -> list[dict]:
    image = station.get("image") or {}
    if not image.get("url"):
        return []
    return [
        {
            "role": "http://dbpedia.org/resource/Illustration",
            "name": image.get("name") or "Representative UKGEOS illustration",
            "description": (
                f"{image.get('description', 'Representative UKGEOS visual.')} "
                f"Acknowledgement: {image.get('acknowledgement', 'Contains NERC materials (c) NERC 2026')}."
            ),
            "link": {"href": image["url"], "type": "image/svg+xml"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Representative image source",
            "description": "UKGEOS Glasgow Observatory page containing the representative borehole infrastructure illustration.",
            "link": {"href": image.get("pageUrl") or "https://www.ukgeos.ac.uk/glasgow-observatory", "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "UKGEOS legal and attribution notes",
            "description": image.get("license", "UKGEOS legal text documents OGL availability and image exclusions."),
            "link": {"href": UKGEOS_LEGAL, "type": "text/html"},
        },
    ]


def _load_stations() -> list[dict]:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "stations.json"), encoding="utf-8") as f:
        return json.load(f)["stations"]


def _uid_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-").lower()


def _system_uid(site_id: str) -> str:
    return f"urn:os4csapi:system:bgs-sensorthings:{_uid_token(site_id)}:v1"


def _deploy_uid(site_id: str) -> str:
    return f"urn:os4csapi:deployment:bgs-sensorthings-{_uid_token(site_id)}:v1"


def _datastream_uid(station: dict, datastream: dict) -> str:
    return (
        "urn:os4csapi:datastream:bgs-sensorthings:"
        f"{_uid_token(station['siteId'])}:{datastream['outputName']}:v1"
    )


def _latest_observation_url(datastream: dict) -> str:
    ds_id = datastream["datastreamId"]
    return f"{BGS_API_ROOT}/Datastreams({ds_id})/Observations?$top=1&$orderby=phenomenonTime%20desc"


PROCEDURE_STUB = {
    "type": "Feature",
    "geometry": None,
    "properties": {
        "uid": PROC_UID,
        "featureType": "sosa:ObservingProcedure",
        "name": "BGS SensorThings Telemetry Observation v1",
        "description": (
            "Publishes a curated set of BGS SensorThings groundwater and geothermal "
            "telemetry readings from the UKGEOS Glasgow observatory."
        ),
        "validTime": [VALID_TIME_START, ".."],
    },
}

PROCEDURE_SML = {
    "type": "SimpleProcess",
    "id": PROC_UID,
    "uniqueId": PROC_UID,
    "definition": "sosa:ObservingProcedure",
    "label": "BGS SensorThings Telemetry Observation v1",
    "description": (
        "Fetches selected latest observations from the British Geological Survey "
        "Sensor Data Service OGC SensorThings API and publishes one CSAPI "
        "observation per selected Thing/Datastream. The initial curated set covers "
        "UKGEOS Glasgow downhole hydro loggers with water temperature, conductivity, "
        "and pressure-derived water level telemetry."
    ),
    "keywords": [
        "BGS",
        "British Geological Survey",
        "SensorThings",
        "FROST Server",
        "UKGEOS",
        "Glasgow",
        "groundwater",
        "geothermal",
        "OGL",
    ],
    "documents": [
        {"role": "http://dbpedia.org/resource/Web_page", "name": "BGS Sensor Data Service", "link": {"href": BGS_HOME, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "BGS SensorThings API Docs", "link": {"href": BGS_API_DOCS, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "BGS SensorThings Interactive Docs", "link": {"href": BGS_INTERACTIVE_DOCS, "type": "text/html"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "BGS SensorThings API Root", "link": {"href": BGS_API_ROOT, "type": "application/json"}},
        {"role": "http://dbpedia.org/resource/Web_page", "name": "Open Government Licence v3.0", "link": {"href": OGL3, "type": "text/html"}},
    ],
    "contacts": [
        {
            "role": "operator",
            "organisationName": "British Geological Survey",
            "contactInfo": {"onlineResource": {"linkage": "https://www.bgs.ac.uk/"}},
        },
        {
            "role": "publisher",
            "organisationName": "OS4CSAPI",
            "contactInfo": {"onlineResource": {"linkage": "https://github.com/OS4CSAPI/OSHConnect-Python"}},
        },
    ],
}


def _system_stub(station: dict) -> dict:
    site_id = station["siteId"]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _system_uid(site_id),
            "featureType": "sosa:Sensor",
            "name": f"BGS {station['shortName']} Downhole Hydro Logger",
            "description": station["description"],
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _system_sml(station: dict) -> dict:
    site_id = station["siteId"]
    parameter_labels = ", ".join(d["label"] for d in station.get("datastreams", []))
    docs = _image_docs(station) + [
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "BGS SensorThings Thing",
            "description": f"SensorThings Thing resource for {station['name']}.",
            "link": {"href": station["thingUrl"], "type": "application/json"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "BGS SensorThings API Docs",
            "link": {"href": BGS_API_DOCS, "type": "text/html"},
        },
        {
            "role": "http://dbpedia.org/resource/Web_page",
            "name": "Open Government Licence v3.0",
            "description": station.get("dataUsage", "Available under the Open Government Licence with UKRI acknowledgement."),
            "link": {"href": OGL3, "type": "text/html"},
        },
    ]
    for datastream in station.get("datastreams", []):
        docs.append({
            "role": "http://dbpedia.org/resource/Web_page",
            "name": datastream["label"],
            "description": "Latest-observation query for this curated BGS SensorThings datastream.",
            "link": {"href": _latest_observation_url(datastream), "type": "application/json"},
        })

    characteristics = [
        {"type": "Text", "name": "source_thing_id", "label": "SensorThings Thing ID", "value": station["thingId"]},
        {"type": "Text", "name": "borehole_reference", "label": "Borehole Reference", "value": station.get("boreholeReference", "Not available")},
        {"type": "Text", "name": "category", "label": "Category", "value": station.get("category", "Not available")},
        {"type": "Text", "name": "arrays", "label": "Source Arrays", "value": ", ".join(station.get("arrays", []))},
        {"type": "Text", "name": "curated_parameters", "label": "Curated Parameters", "value": parameter_labels},
        {"type": "Text", "name": "selection_reason", "label": "Selection Reason", "value": station.get("selectionReason", "Curated demo station")},
        {"type": "Text", "name": "data_usage", "label": "Data Usage", "value": station.get("dataUsage", "Open Government Licence with UKRI acknowledgement")},
    ]

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(site_id),
        "uniqueId": _system_uid(site_id),
        "definition": "sosa:System",
        "label": f"BGS {station['shortName']} Downhole Hydro Logger",
        "description": station["description"],
        "keywords": [
            "BGS",
            "British Geological Survey",
            "SensorThings",
            "UKGEOS",
            "Glasgow",
            "groundwater",
            "geothermal",
            station["shortName"],
            station["thingId"],
        ],
        "identifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"BGS {station['shortName']}"},
            {"definition": "http://sensorml.com/ont/swe/property/StationID", "label": "SensorThings Thing ID", "value": station["thingId"]},
            {"definition": "http://sensorml.com/ont/swe/property/UniqueID", "label": "OS4CSAPI UID", "value": _system_uid(site_id)},
        ],
        "classifiers": [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Source Type", "value": "BGS SensorThings downhole hydro logger"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Groundwater and geothermal observatory telemetry"},
        ],
        "contacts": [
            {"role": "operator", "organisationName": "British Geological Survey", "contactInfo": {"onlineResource": {"linkage": "https://www.bgs.ac.uk/"}}},
        ],
        "documents": docs,
        "characteristics": [{"label": "Station Properties", "characteristics": characteristics}],
        "capabilities": [{
            "definition": "http://www.w3.org/ns/ssn/systems/SystemCapability",
            "label": "Publisher Capabilities",
            "capabilities": [
                {
                    "type": "Quantity",
                    "name": "publish_interval",
                    "definition": "http://qudt.org/vocab/quantitykind/Period",
                    "label": "Publish Interval",
                    "uom": {"code": "s"},
                    "value": PUBLISH_INTERVAL_SECONDS,
                },
                {
                    "type": "Text",
                    "name": "source_query_mode",
                    "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
                    "label": "Source Query Mode",
                    "value": "Latest BGS SensorThings observations polled by phenomenon time descending",
                },
            ],
        }],
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326",
        },
    }


def _go_compatible_system_sml(sml: dict, base_url: str) -> dict:
    if "csapi-go" not in base_url:
        return sml
    compat = dict(sml)
    compat.pop("characteristics", None)
    return compat


def _datastream_schema(station: dict, datastream: dict) -> dict:
    result_field = datastream.get("resultField", "value")
    return {
        "uid": _datastream_uid(station, datastream),
        "outputName": datastream["outputName"],
        "name": datastream["label"],
        "description": (
            f"{datastream['label']} from BGS SensorThings datastream "
            f"{datastream['datastreamId']} on {station['name']}."
        ),
        "documentation": [
            {"title": "BGS SensorThings Datastream", "href": datastream["datastreamUrl"], "rel": "describedby"},
            {"title": "Latest Observation", "href": _latest_observation_url(datastream), "rel": "service"},
            {"title": "BGS SensorThings API Docs", "href": BGS_API_DOCS, "rel": "documentation"},
            {"title": "Open Government Licence v3.0", "href": OGL3, "rel": "license"},
        ],
        "schema": {
            "obsFormat": "application/om+json",
            "resultSchema": {
                "type": "DataRecord",
                "label": f"BGS {datastream['label']} Observation",
                "description": "Latest BGS SensorThings observation with source identifiers and provenance.",
                "fields": [
                    {"type": "Time", "name": "timestamp", "label": "Observation Time", "definition": "http://www.opengis.net/def/property/OGC/0/SamplingTime", "referenceTime": "1970-01-01T00:00:00Z", "uom": {"code": "s"}},
                    {"type": "Text", "name": "thingId", "label": "Curated Thing ID", "definition": "http://sensorml.com/ont/swe/property/StationID"},
                    {"type": "Text", "name": "sourceThingId", "label": "SensorThings Thing ID", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "sourceDatastreamId", "label": "SensorThings Datastream ID", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "observedProperty", "label": "Observed Property", "definition": "http://sensorml.com/ont/swe/property/ObservableProperty"},
                    {"type": "Quantity", "name": result_field, "label": datastream["label"], "definition": "http://sensorml.com/ont/swe/property/Value", "uom": {"code": datastream.get("uom", datastream["unit"])}},
                    {"type": "Text", "name": "unit", "label": "Unit", "definition": "http://sensorml.com/ont/swe/property/Unit"},
                    {"type": "Text", "name": "sourceObservationId", "label": "SensorThings Observation ID", "definition": "http://sensorml.com/ont/swe/property/Identifier"},
                    {"type": "Text", "name": "publishFlag", "label": "Source Publish Flag", "definition": "http://sensorml.com/ont/swe/property/Status"},
                    {"type": "Text", "name": "sourceUrl", "label": "Source URL", "definition": "http://sensorml.com/ont/swe/property/ReferenceURL"},
                ],
            },
        },
    }


def _deploy_root() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-4.2003, 55.8385]},
        "properties": {
            "uid": DEPLOY_ROOT_UID,
            "featureType": "sosa:Deployment",
            "name": "BGS SensorThings Demo",
            "description": "Top-level grouping for curated BGS SensorThings telemetry resources.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_group() -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-4.2003, 55.8385]},
        "properties": {
            "uid": DEPLOY_GROUP_UID,
            "featureType": "sosa:Deployment",
            "name": "BGS UKGEOS Glasgow Hydro Loggers",
            "description": "Grouping deployment for curated BGS UKGEOS Glasgow downhole hydro logger telemetry.",
            "validTime": [VALID_TIME_START, ".."],
        },
    }


def _deploy_station(station: dict, system_server_id: str, base_url: str) -> dict:
    site_id = station["siteId"]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [station["lon"], station["lat"]]},
        "properties": {
            "uid": _deploy_uid(site_id),
            "featureType": "sosa:Deployment",
            "name": f"BGS {station['shortName']} UKGEOS Deployment",
            "description": f"Deployment node linking BGS SensorThings Thing {station['thingId']} to its CSAPI hydro logger system.",
            "validTime": [VALID_TIME_START, ".."],
            "platform@link": {
                "href": f"{base_url.rstrip('/')}/systems/{system_server_id}",
                "uid": _system_uid(site_id),
                "title": f"BGS {station['shortName']} Downhole Hydro Logger",
            },
        },
    }


def clean_all(base_url: str, auth: str, *, dry_run: bool = False, stats: dict):
    stations = _load_stations()
    for station in stations:
        clean_resource(base_url, auth, "deployments", _deploy_uid(station["siteId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_GROUP_UID, dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "deployments", DEPLOY_ROOT_UID, dry_run=dry_run, stats=stats, cascade=True)
    for station in stations:
        clean_resource(base_url, auth, "systems", _system_uid(station["siteId"]), dry_run=dry_run, stats=stats, cascade=True)
    clean_resource(base_url, auth, "procedures", PROC_UID, dry_run=dry_run, stats=stats)


def _ensure_system_resilient(base_url: str, auth: str, station: dict,
                             *, dry_run: bool, stats: dict, force_sml: bool) -> str | None:
    uid = _system_uid(station["siteId"])
    try:
        return ensure_system(
            base_url, auth, uid, _system_stub(station),
            _go_compatible_system_sml(_system_sml(station), base_url),
            dry_run=dry_run, stats=stats, force_sml=force_sml,
        )
    except RuntimeError as exc:
        if "HTTP 500 POST" not in str(exc) or "/systems" not in str(exc):
            raise
        recovered = find_by_uid(base_url, auth, "systems", uid, no_cache=True)
        if not recovered:
            raise
        print(f"  [WARN] Server returned HTTP 500 after creating system {uid}; recovered id={recovered}")
        if not dry_run:
            try:
                api_put(base_url, f"systems/{recovered}",
                        _go_compatible_system_sml(_system_sml(station), base_url),
                        auth, content_type="application/sml+json")
                print(f"  [SML] PUT SensorML for recovered system {uid} (id={recovered})")
            except Exception as sml_exc:
                print(f"  [WARN] SML PUT skipped for recovered system {uid} (id={recovered}): {sml_exc}")
        if stats:
            stats.setdefault("recovered", 0)
            stats["recovered"] += 1
        return recovered


def bootstrap(*, clean: bool = False, clean_only: bool = False,
              dry_run: bool = False, force_sml: bool = False):
    server_config = get_config()
    base_url = server_config["base_url"]
    auth = _auth_header(server_config["user"], server_config["password"])
    stations = _load_stations()
    stats: dict[str, int] = {}

    print()
    print("=" * 70)
    print("  BGS SensorThings -- Bootstrap")
    print("=" * 70)
    print(f"  Server:    {base_url}")
    print(f"  Stations:  {len(stations)}")
    print(f"  Clean:     {clean}  Clean-only: {clean_only}  Dry-run: {dry_run}  Force-SML: {force_sml}")
    print()

    if clean or clean_only:
        print("  -- Cleaning existing resources --")
        clean_all(base_url, auth, dry_run=dry_run, stats=stats)
        if clean_only:
            print_summary(stats, dry_run)
            return

    print("  -- Procedure --")
    ensure_procedure(base_url, auth, PROC_UID, PROCEDURE_STUB, PROCEDURE_SML,
                     dry_run=dry_run, stats=stats, force_sml=force_sml)

    print("  -- Systems + Datastreams --")
    system_ids: dict[str, str] = {}
    for station in stations:
        site_id = station["siteId"]
        sys_id = _ensure_system_resilient(
            base_url, auth, station, dry_run=dry_run, stats=stats, force_sml=force_sml)
        if sys_id:
            system_ids[site_id] = sys_id
        for datastream in station.get("datastreams", []):
            if dry_run and not sys_id:
                print(f"  [DRY] Would create datastream '{datastream['outputName']}' on system {site_id}")
                continue
            ensure_datastream(base_url, auth, sys_id or "pending", datastream["outputName"],
                              _datastream_schema(station, datastream),
                              dry_run=dry_run, stats=stats)

    print("  -- Deployments --")
    root_id = ensure_deployment(base_url, auth, DEPLOY_ROOT_UID, _deploy_root(),
                                dry_run=dry_run, stats=stats)
    group_id = ensure_deployment(base_url, auth, DEPLOY_GROUP_UID, _deploy_group(),
                                 parent_id=root_id, dry_run=dry_run, stats=stats)
    for station in stations:
        site_id = station["siteId"]
        sys_id = system_ids.get(site_id) or "pending"
        ensure_deployment(base_url, auth, _deploy_uid(site_id),
                          _deploy_station(station, sys_id, base_url),
                          parent_id=group_id, dry_run=dry_run, stats=stats)

    print_summary(stats, dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap BGS SensorThings resources on the CSAPI server.")
    add_bootstrap_args(parser)
    args = parser.parse_args()
    bootstrap(clean=args.clean, clean_only=args.clean_only,
              dry_run=args.dry_run, force_sml=args.force_sml)


if __name__ == "__main__":
    main()
