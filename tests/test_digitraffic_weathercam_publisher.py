from datetime import datetime, timezone

import publishers.digitraffic_weathercam.digitraffic_weathercam_publisher as digitraffic
from publishers.digitraffic_weathercam.digitraffic_weathercam_publisher import DigitrafficWeathercamPublisher


def test_fetch_latest_image_maps_metadata_and_probe(monkeypatch):
    camera = {
        "roadWeatherStationId": "1014",
        "cameraStationId": "C01507",
        "cameraStationName": "vt25_Hanko",
        "presetId": "C0150701",
    }

    def fake_get_json(url):
        assert url.endswith("/stations/C01507/data")
        return {
            "dataUpdatedTime": "2026-06-04T17:34:00Z",
            "presets": [
                {"id": "C0150701", "measuredTime": "2026-06-04T17:34:11Z"},
            ],
        }

    def fake_probe(url):
        assert url == "https://weathercam.digitraffic.fi/C0150701.jpg"
        return {
            "status": 200,
            "etag": '"abc"',
            "contentLength": "12345",
            "lastModified": "Wed, 04 Jun 2026 17:34:11 GMT",
            "sourceLastModifiedTime": "2026-06-04T17:34:11Z",
        }

    monkeypatch.setattr(digitraffic, "_get_json", fake_get_json)
    monkeypatch.setattr(digitraffic, "_probe_image_url", fake_probe)

    latest = digitraffic.fetch_latest_image(camera)

    assert latest["phenomenonTime"] == "2026-06-04T17:34:11Z"
    assert latest["result"]["camId"] == "C0150701"
    assert latest["result"]["mediaType"] == "image/jpeg"
    assert latest["result"]["httpStatus"] == 200
    assert latest["result"]["etag"] == '"abc"'
    assert latest["result"]["sourceLastModifiedTime"] == "2026-06-04T17:34:11Z"
    assert latest["dedupeKey"].startswith("C0150701|")


def test_publish_cycle_dry_run_emits_heartbeat_for_unchanged(monkeypatch):
    publisher = DigitrafficWeathercamPublisher.__new__(DigitrafficWeathercamPublisher)
    publisher.cameras = [{"presetId": "C0150701", "roadWeatherStationId": "1014"}]
    publisher._ds_ids = {}
    publisher._image_state = {}
    publisher._request_delay = 0
    publisher._stale_seconds = 900
    publisher.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def fake_fetch(_camera):
        return {
            "phenomenonTime": "2026-06-04T17:34:11Z",
            "dedupeKey": "C0150701|2026-06-04T17:34:11Z|\"abc\"|12345",
            "result": {
                "camId": "C0150701",
                "imageUrl": "https://weathercam.digitraffic.fi/C0150701.jpg",
                "sourceUrl": "https://tie.digitraffic.fi/api/weathercam/v1/stations/C01507/data",
            },
        }

    monkeypatch.setattr(digitraffic, "fetch_latest_image", fake_fetch)

    assert publisher.publish_cycle(dry_run=True) == 0
    assert publisher.publish_cycle(dry_run=True) == 0
    assert publisher._image_state["C0150701"]["unchangedPollCount"] == 1
    assert publisher.stats["skipped"] == 0


def test_freshness_status_marks_stale_and_keeps_source_url_last():
    publisher = DigitrafficWeathercamPublisher.__new__(DigitrafficWeathercamPublisher)
    publisher._image_state = {
        "C0150701": {
            "imageToken": "old-token",
            "firstSeenTime": "2026-06-04T17:00:00Z",
            "lastChangedTime": "2026-06-04T17:00:00Z",
            "lastSeenTime": "2026-06-04T17:10:00Z",
            "unchangedPollCount": 2,
        }
    }
    publisher._stale_seconds = 900

    latest = {
        "phenomenonTime": "2026-06-04T17:16:00Z",
        "dedupeKey": "old-token",
        "result": {
            "camId": "C0150701",
            "sourceUrl": "https://tie.digitraffic.fi/api/weathercam/v1/stations/C01507/data",
        },
    }

    updated = publisher._apply_freshness_status("C0150701", latest, datetime(2026, 6, 4, 17, 16, tzinfo=timezone.utc))

    assert updated["result"]["imageChanged"] is False
    assert updated["result"]["stalenessStatus"] == "stale"
    assert updated["result"]["sourceAgeSeconds"] == 960
    keys = list(updated["result"].keys())
    assert keys.index("sourceAgeSeconds") < keys.index("sourceUrl")


def test_parse_http_date_normalizes_to_utc():
    parsed = digitraffic._parse_http_date("Wed, 04 Jun 2026 19:34:11 +0200")

    assert parsed == "2026-06-04T17:34:11Z"
    assert digitraffic._parse_http_date(None) is None
