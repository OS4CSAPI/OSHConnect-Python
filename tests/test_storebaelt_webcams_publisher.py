from datetime import datetime, timezone

import publishers.storebaelt_webcams.storebaelt_webcams_publisher as storebaelt
from publishers.storebaelt_webcams.storebaelt_webcams_publisher import StorebaeltWebcamsPublisher


def test_camera_registry_contains_two_known_webcams():
    cameras = storebaelt._load_cameras()

    assert {camera["id"] for camera in cameras} == {"storebaelt-tower", "sprogo"}
    for camera in cameras:
        assert camera["pageUrl"] == "https://storebaelt.dk/trafik-vejr/webcams/"
        assert camera["playerUrl"].startswith("https://player.sob.m-dn.net/")
        assert camera["posterUrl"].startswith("https://stream.sob.m-dn.net/res/")


def test_fetch_latest_image_maps_http_metadata(monkeypatch):
    camera = {
        "id": "sprogo",
        "title": "Sprogo Webcam",
        "locationName": "Sprogo",
        "pageUrl": "https://storebaelt.dk/trafik-vejr/webcams/",
        "playerUrl": "https://player.sob.m-dn.net/sb2-live.html",
        "posterUrl": "//stream.sob.m-dn.net/res/sb2-live.jpg",
    }

    def fake_probe(url):
        assert url == "https://stream.sob.m-dn.net/res/sb2-live.jpg"
        return {
            "status": 200,
            "headers": {
                "Content-Type": "image/jpeg",
                "Last-Modified": "Wed, 03 Jun 2026 12:00:00 GMT",
                "ETag": '"abc123"',
                "Content-Length": "12345",
            },
            "sha256": "f" * 64,
            "byteLength": 12345,
        }

    monkeypatch.setattr(storebaelt, "_probe_image_url", fake_probe)

    latest = storebaelt.fetch_latest_image(camera)

    assert latest["phenomenonTime"].endswith("Z")
    assert latest["dedupeKey"] == f"sprogo|{'f' * 64}"
    assert latest["result"]["posterUrl"] == "https://stream.sob.m-dn.net/res/sb2-live.jpg"
    assert latest["result"]["playerUrl"] == "https://player.sob.m-dn.net/sb2-live.html"
    assert latest["result"]["mediaType"] == "image/jpeg"
    assert latest["result"]["lastModified"] == "Wed, 03 Jun 2026 12:00:00 GMT"
    assert latest["result"]["sourceLastModifiedTime"] == "2026-06-03T12:00:00Z"
    assert latest["result"]["contentLength"] == "12345"
    assert latest["result"]["imageSha256"] == "f" * 64


def test_publish_cycle_dry_run_publishes_unchanged_heartbeat(monkeypatch):
    publisher = StorebaeltWebcamsPublisher.__new__(StorebaeltWebcamsPublisher)
    publisher.cameras = [{"id": "sprogo", "title": "Sprogo Webcam"}]
    publisher._ds_ids = {}
    publisher._image_state = {}
    publisher._request_delay = 0
    publisher._stale_seconds = 900
    publisher.stats = {"published": 0, "errors": 0, "reconnects": 0, "skipped": 0}

    def fake_fetch(camera):
        return {
            "phenomenonTime": "2026-06-03T12:00:00Z",
            "dedupeKey": "sprogo|abc",
            "result": {
                "cameraId": camera["id"],
                "imageUrl": "https://stream.sob.m-dn.net/res/sb2-live.jpg",
                "imageSha256": "abc",
            },
        }

    monkeypatch.setattr(storebaelt, "fetch_latest_image", fake_fetch)

    assert publisher.publish_cycle(dry_run=True) == 0
    assert publisher.publish_cycle(dry_run=True) == 0
    assert publisher._image_state["sprogo"]["imageSha256"] == "abc"
    assert publisher._image_state["sprogo"]["unchangedPollCount"] == 1
    assert publisher.stats["skipped"] == 0


def test_freshness_status_tracks_changed_and_unchanged_images():
    publisher = StorebaeltWebcamsPublisher.__new__(StorebaeltWebcamsPublisher)
    publisher._image_state = {}
    publisher._stale_seconds = 900
    poll_time = datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc)
    latest = {
        "phenomenonTime": "2026-06-03T12:00:00Z",
        "dedupeKey": "sprogo|abc",
        "result": {"cameraId": "sprogo", "imageSha256": "abc"},
    }

    first = publisher._apply_freshness_status("sprogo", latest, poll_time)

    assert first["result"]["imageChanged"] is True
    assert first["result"]["stalenessStatus"] == "fresh"
    assert first["result"]["unchangedPollCount"] == 0
    assert first["result"]["firstSeenTime"] == "2026-06-03T12:00:00Z"
    assert first["result"]["lastChangedTime"] == "2026-06-03T12:00:00Z"

    second_latest = {
        "phenomenonTime": "2026-06-03T12:05:00Z",
        "dedupeKey": "sprogo|abc",
        "result": {"cameraId": "sprogo", "imageSha256": "abc"},
    }
    second = publisher._apply_freshness_status("sprogo", second_latest, datetime(2026, 6, 3, 12, 5, tzinfo=timezone.utc))

    assert second["result"]["imageChanged"] is False
    assert second["result"]["stalenessStatus"] == "unchanged"
    assert second["result"]["sourceAgeSeconds"] == 300
    assert second["result"]["unchangedPollCount"] == 1
    assert second["result"]["firstSeenTime"] == "2026-06-03T12:00:00Z"
    assert second["result"]["lastChangedTime"] == "2026-06-03T12:00:00Z"


def test_freshness_fields_are_emitted_before_source_url_for_strict_swe_order():
    publisher = StorebaeltWebcamsPublisher.__new__(StorebaeltWebcamsPublisher)
    publisher._image_state = {}
    publisher._stale_seconds = 900
    latest = {
        "phenomenonTime": "2026-06-03T12:00:00Z",
        "dedupeKey": "sprogo|abc",
        "result": {"cameraId": "sprogo", "imageSha256": "abc", "sourceUrl": "https://example.test/image.jpg"},
    }

    updated = publisher._apply_freshness_status("sprogo", latest, datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc))
    keys = list(updated["result"].keys())

    assert keys.index("imageChanged") < keys.index("sourceUrl")
    assert keys.index("sourceAgeSeconds") < keys.index("sourceUrl")
    assert updated["result"]["sourceUrl"] == "https://example.test/image.jpg"


def test_freshness_status_marks_stale_after_threshold():
    publisher = StorebaeltWebcamsPublisher.__new__(StorebaeltWebcamsPublisher)
    publisher._image_state = {
        "sprogo": {
            "imageSha256": "abc",
            "firstSeenTime": "2026-06-03T12:00:00Z",
            "lastChangedTime": "2026-06-03T12:00:00Z",
            "lastSeenTime": "2026-06-03T12:10:00Z",
            "unchangedPollCount": 2,
        }
    }
    publisher._stale_seconds = 900
    latest = {
        "phenomenonTime": "2026-06-03T12:16:00Z",
        "dedupeKey": "sprogo|abc",
        "result": {"cameraId": "sprogo", "imageSha256": "abc"},
    }

    updated = publisher._apply_freshness_status("sprogo", latest, datetime(2026, 6, 3, 12, 16, tzinfo=timezone.utc))

    assert updated["result"]["imageChanged"] is False
    assert updated["result"]["stalenessStatus"] == "stale"
    assert updated["result"]["sourceAgeSeconds"] == 960
    assert updated["result"]["unchangedPollCount"] == 3


def test_http_date_parser_normalizes_to_utc():
    parsed = storebaelt._parse_http_date("Wed, 03 Jun 2026 14:00:00 +0200")

    assert parsed == "2026-06-03T12:00:00Z"
    assert storebaelt._parse_http_date(None) is None
    assert datetime.fromisoformat(parsed.replace("Z", "+00:00")).tzinfo == timezone.utc
