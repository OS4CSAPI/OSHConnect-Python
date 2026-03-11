# Enriched SensorML system body candidate

def _system_sml(station: dict) -> dict:
    nwis_id = station["nwisId"]
    drainage = station.get("drainageArea_sqmi")
    drainage_text = f"{drainage} sq mi" if drainage is not None else "Not available"
    altitude = station.get("altitude_ft")
    altitude_text = f"{altitude} ft" if altitude is not None else "Not available"

    characteristics_fields = [
        {
            "type": "Text",
            "name": "reporting_cadence",
            "definition": "http://sensorml.com/ont/swe/property/ReportingFrequency",
            "label": "Reporting Cadence",
            "value": "Instantaneous values at approximately 15-minute intervals"
        },
        {
            "type": "Text",
            "name": "timezone",
            "definition": "http://sensorml.com/ont/swe/property/TimeZone",
            "label": "Station Timezone",
            "value": station.get("tz", "UTC")
        },
        {
            "type": "Text",
            "name": "uses_daylight_savings",
            "definition": "http://sensorml.com/ont/swe/property/TimeZone",
            "label": "Uses Daylight Savings",
            "value": station.get("usesDaylightSavings", "Unknown")
        },
        {
            "type": "Text",
            "name": "drainage_area",
            "definition": "http://sensorml.com/ont/swe/property/DrainageArea",
            "label": "Drainage Area",
            "value": drainage_text
        },
        {
            "type": "Text",
            "name": "hydrologic_unit_code",
            "definition": "http://sensorml.com/ont/swe/property/HydrologicUnitCode",
            "label": "Hydrologic Unit Code",
            "value": station.get("huc", "")
        },
        {
            "type": "Text",
            "name": "site_type",
            "definition": "http://sensorml.com/ont/swe/property/SensorType",
            "label": "Site Type",
            "value": station.get("siteType", station.get("siteTypeCode", "Unknown"))
        },
        {
            "type": "Text",
            "name": "altitude",
            "definition": "http://sensorml.com/ont/swe/property/Elevation",
            "label": "Station Altitude",
            "value": altitude_text
        },
        {
            "type": "Text",
            "name": "vertical_datum",
            "definition": "http://sensorml.com/ont/swe/property/VerticalDatum",
            "label": "Vertical Datum",
            "value": station.get("verticalDatum", "Not available")
        },
        {
            "type": "Text",
            "name": "horizontal_accuracy",
            "definition": "http://sensorml.com/ont/swe/property/PositionalAccuracy",
            "label": "Horizontal Accuracy",
            "value": station.get("horizontalAccuracyNote", "Not available")
        },
        {
            "type": "Text",
            "name": "coordinate_method",
            "definition": "http://sensorml.com/ont/swe/property/Method",
            "label": "Coordinate Method",
            "value": station.get("horizontalMethodName", "Not available")
        }
    ]

    if station.get("camId"):
        characteristics_fields.append({
            "type": "Text",
            "name": "nims_camera_id",
            "definition": "http://sensorml.com/ont/swe/property/AssociatedFacility",
            "label": "Associated NIMS Camera",
            "value": station["camId"]
        })

    return {
        "type": "PhysicalSystem",
        "id": _system_uid(nwis_id),
        "uniqueId": _system_uid(nwis_id),
        "definition": "sosa:System",
        "label": f"USGS {nwis_id} - {station['name']}",
        "description": (
            f"USGS water monitoring station at {station['name']} (NWIS ID {nwis_id}). "
            f"Located in {station.get('county', '')}, {station['state']}. "
            "This CSAPI system represents the curated monitoring-location resource published by "
            "OSHConnect-Python. It exposes discharge and gage-height datastreams anchored to the "
            "USGS Water Data OGC API instantaneous series semantics."
        ),
        "keywords": [
            "USGS",
            "NWIS",
            "water",
            "hydrology",
            "streamflow",
            "gage height",
            "monitoring location",
            nwis_id,
            station["stateAbbr"]
        ],
        "identifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "Short Name",
                "value": f"USGS {nwis_id}"
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/LongName",
                "label": "Long Name",
                "value": station["fullName"]
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/ModelNumber",
                "label": "NWIS Site Number",
                "value": nwis_id
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "Agency Code",
                "value": station.get("agencyCode", "USGS")
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/ShortName",
                "label": "District Code",
                "value": station.get("districtCode", "")
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/UniqueID",
                "label": "OS4CSAPI UID",
                "value": _system_uid(nwis_id)
            }
        ],
        "classifiers": [
            {
                "definition": "http://sensorml.com/ont/swe/property/SensorType",
                "label": "Site Type",
                "value": station.get("siteType", station.get("siteTypeCode", "Unknown"))
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/IntendedApplication",
                "label": "Network",
                "value": "USGS National Water Information System (NWIS)"
            },
            {
                "definition": "http://sensorml.com/ont/swe/property/SystemRole",
                "label": "Operator",
                "value": station.get("agencyName", "U.S. Geological Survey")
            }
        ],
        "contacts": [
            {
                "role": "http://sensorml.com/ont/swe/property/Operator",
                "organisationName": station.get("agencyName", "U.S. Geological Survey"),
                "contactInfo": {
                    "website": USGS_WATER_HOME
                }
            }
        ],
        "documents": [
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Monitoring Location",
                "description": f"USGS monitoring-location resource for site {nwis_id}.",
                "link": {"href": station.get("monitoringLocationUrl", _monitoring_location_url(nwis_id)), "type": "application/geo+json"}
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Latest Continuous - Discharge",
                "description": f"Latest discharge values for site {nwis_id}.",
                "link": {"href": station.get("latestContinuous00060Url", _latest_continuous_url(nwis_id, '00060')), "type": "application/geo+json"}
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Latest Continuous - Gage Height",
                "description": f"Latest gage-height values for site {nwis_id}.",
                "link": {"href": station.get("latestContinuous00065Url", _latest_continuous_url(nwis_id, '00065')), "type": "application/geo+json"}
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Time Series Metadata - Discharge",
                "description": f"Time-series metadata for discharge at site {nwis_id}.",
                "link": {"href": station.get("timeSeries00060Url", _time_series_metadata_url(nwis_id, '00060')), "type": "application/geo+json"}
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "Time Series Metadata - Gage Height",
                "description": f"Time-series metadata for gage height at site {nwis_id}.",
                "link": {"href": station.get("timeSeries00065Url", _time_series_metadata_url(nwis_id, '00065')), "type": "application/geo+json"}
            },
            {
                "role": "http://dbpedia.org/resource/Web_page",
                "name": "USGS Water Data OGC API",
                "description": "Official USGS Water Data OGC API documentation.",
                "link": {"href": USGS_API_DOCS, "type": "text/html"}
            }
        ],
        "characteristics": [
            {
                "label": "Station Properties",
                "characteristics": characteristics_fields
            }
        ],
        "capabilities": [
            {
                "definition": "http://www.w3.org/ns/ssn/systems/SystemCapability",
                "label": "Published Datastreams",
                "capabilities": [
                    {
                        "type": "Text",
                        "name": "supported_parameter_codes",
                        "definition": "http://sensorml.com/ont/swe/property/DataSource",
                        "label": "Supported Parameter Codes",
                        "value": ",".join(station.get("parameterCodes", []))
                    },
                    {
                        "type": "Text",
                        "name": "statistic_series",
                        "definition": "http://sensorml.com/ont/swe/property/DataSource",
                        "label": "Published Statistic",
                        "value": f"{STATISTIC_INSTANTANEOUS} ({STATISTIC_INSTANTANEOUS_NAME})"
                    },
                    {
                        "type": "Text",
                        "name": "source_collections",
                        "definition": "http://sensorml.com/ont/swe/property/DataSource",
                        "label": "Primary Source Collections",
                        "value": "monitoring-locations, latest-continuous or continuous, time-series-metadata"
                    }
                ]
            }
        ],
        "position": {
            "type": "Point",
            "coordinates": [station["lon"], station["lat"]],
            "srsName": "http://www.opengis.net/def/crs/EPSG/0/4326"
        }
    }
