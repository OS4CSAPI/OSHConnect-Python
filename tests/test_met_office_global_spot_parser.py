from publishers.met_office_global_spot.met_office_global_spot_publisher import (
    _candidate_records,
    _issued_time,
    _lead_time_hours,
    _parse_source_time,
    _value_for_parameter,
)


PARAMETERS = [
    {
        "outputName": "air_temperature_forecast",
        "label": "Forecast Air Temperature",
        "resultField": "air_temperature_c",
        "aliases": ["screenTemperature", "airTemperature"],
    },
    {
        "outputName": "wind_speed_forecast",
        "label": "Forecast Wind Speed",
        "resultField": "wind_speed_ms",
        "aliases": ["windSpeed10m", "windSpeed"],
    },
]


def test_candidate_records_find_nested_forecast_values():
    payload = {
        "issueTime": "2026-05-26T06:00:00Z",
        "features": [
            {
                "properties": {
                    "validTime": "2026-05-26T09:00:00Z",
                    "parameters": {
                        "screenTemperature": 14.5,
                        "windSpeed10m": 7.2,
                    },
                },
            },
            {
                "properties": {
                    "validTime": "2026-05-26T10:00:00Z",
                    "parameters": {"unrelated": 1},
                },
            },
        ],
    }

    records = _candidate_records(payload, PARAMETERS)

    assert len(records) == 1
    assert _value_for_parameter(records[0], PARAMETERS[0]) == 14.5
    assert _value_for_parameter(records[0], PARAMETERS[1]) == 7.2


def test_forecast_time_normalization_and_lead_time():
    timestamp, normalized = _parse_source_time("2026-05-26T09:00:00Z")

    assert timestamp > 0
    assert normalized == "2026-05-26T09:00:00Z"
    assert _issued_time({"modelRunTime": "2026-05-26T06:00:00Z"}) == "2026-05-26T06:00:00Z"
    assert _lead_time_hours("2026-05-26T06:00:00Z", "2026-05-26T09:00:00Z") == 3.0
