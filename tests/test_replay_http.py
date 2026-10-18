from schedule_helpers import expanded_pattern
import gzip
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from flask import Flask

from dashboard import replay, replay_http as http
from dashboard.cities import CITIES


@pytest.fixture
def replay_client(monkeypatch, sample_parquet, tmp_path):
    monkeypatch.setenv("SUNTRAIN_PARQUET_GLOB", str(sample_parquet))
    monkeypatch.setenv("SUNTRAIN_RAIL_GEOMETRY", str(tmp_path / "missing.json"))
    monkeypatch.setenv("SUNTRAIN_REPLAY_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(http.data, "get_metadata", lambda: {"min_date": "2023-07-10", "max_date": "2023-07-11"})
    app = Flask(__name__)
    http.register_replay_routes(app)
    return app.test_client()


def test_every_city_has_small_descriptors_without_building_schedules(replay_client, monkeypatch):
    monkeypatch.setattr(replay, "get_replay_day", lambda *a, **k: pytest.fail("descriptor built a schedule"))
    for city, settings in CITIES.items():
        day = settings.get("start_date", "2023-07-10")
        info = http.descriptor(day, city)
        assert len(json.dumps(info)) < 600 and "services" not in info
        assert info["modes"] == list(http.selected_modes(city))
        assert info["url"].startswith("/api/replay/" + city + "/")


def test_compressed_cache_etags_and_plain_json(replay_client, monkeypatch):
    info = http.descriptor("2023-07-10", "melbourne")
    response = replay_client.get(info["url"], headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["Content-Encoding"] == "gzip"
    assert response.headers["Vary"] == "Accept-Encoding"
    assert "immutable" in response.headers["Cache-Control"]
    day = json.loads(gzip.decompress(response.data))
    assert day["revision"] == info["revision"] and day["loaded_modes"] == ["train"]
    assert day["services"][0]["number"] == "1001"
    assert not day.get("transit_patterns")
    for cached in (replay._get_day, replay._get_prepared_day, replay._get_with_buses, http.transit.read_reference):
        assert cached.cache_info().currsize == 0
    monkeypatch.setattr(replay, "get_replay_day", lambda *a, **k: pytest.fail("cached response rebuilt"))
    cached = replay_client.get(info["url"], headers={"Accept-Encoding": "gzip", "If-None-Match": response.headers["ETag"]})
    assert cached.status_code == 304 and not cached.data
    plain = replay_client.get(info["url"])
    assert plain.get_json() == day and "Content-Encoding" not in plain.headers
    # Cache eviction must not break a response already streaming to a browser.
    with http.compressed_day(info) as stream:
        monkeypatch.setattr(http, "CACHE_LIMIT", 0)
        http.trim_cache(http.cache_directory(), http.cache_directory() / "other.json.gz")
        assert json.loads(gzip.decompress(stream.read())) == day


def test_revision_changes_with_modes_and_source_and_rejects_invalid_requests(replay_client, monkeypatch, sample_parquet):
    first = http.descriptor("2023-07-10", "melbourne")
    assert first != http.descriptor("2023-07-11", "melbourne")
    assert first["revision"] != http.descriptor("2023-07-10", "melbourne", ["bus"])["revision"]
    original = sample_parquet.stat().st_mtime_ns
    os.utime(sample_parquet, ns=(original + 100000, original + 100000))
    assert first["revision"] != http.descriptor("2023-07-10", "melbourne")["revision"]
    assert replay_client.get(first["url"]).status_code == 409
    for url in [first["url"].replace("melbourne", "unknown"), first["url"].replace("2023-07-10", "bad"),
                first["url"].replace("modes=train", "modes=flight"), first["url"].replace("2023-07-10", "2030-01-01")]:
        assert replay_client.get(url).status_code == 404


def test_disk_cache_evicts_oldest_and_keeps_current(tmp_path, monkeypatch):
    monkeypatch.setattr(http, "CACHE_LIMIT", 12)
    for index in range(3):
        path = tmp_path / f"{index}.json.gz"
        path.write_bytes(b"123456")
        os.utime(path, (index + 1, index + 1))
    http.trim_cache(tmp_path, tmp_path / "2.json.gz")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["1.json.gz", "2.json.gz"]


def test_melbourne_rail_never_opens_transit_bundles(replay_client, monkeypatch):
    monkeypatch.setattr(http.transit, "fingerprint", lambda *a: pytest.fail("rail visit opened transit"))
    day = replay.get_replay_day("2023-07-11", modes=["train"])
    assert len(day["services"]) == 1 and "transit_patterns" not in day


def test_bus_only_request_never_queries_passenger_warehouse(replay_client, monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_TRANSIT_REFERENCE", str(tmp_path / "unavailable.json"))
    monkeypatch.setattr(http.data, "_connect", lambda: pytest.fail("bus visit queried passenger warehouse"))
    assert replay.get_replay_day("2023-07-11", modes=["bus"])["services"] == []


def test_mode_selection_does_not_mutate_cached_boston_or_expand_shared_stops():
    full = replay.get_replay_day("2024-06-24", "boston")
    full_count = len(full["services"])
    silver = replay.get_replay_day("2024-06-24", "boston", modes=["silver_line"])
    assert len(full["services"]) == full_count
    assert 0 < len(silver["services"]) < full_count
    assert all(s["mode"] == "silver_line" and "stops" not in s for s in silver["services"])
    assert all(p["mode"] == "silver_line" for p in silver["transit_patterns"].values())
    assert {leg for p in silver["transit_patterns"].values() for leg in expanded_pattern(silver, p)["legs"]} == silver["paths"].keys()


def test_uncached_builds_share_a_memory_budget_but_cached_downloads_do_not_wait(tmp_path, monkeypatch):
    monkeypatch.setenv("SUNTRAIN_REPLAY_CACHE", str(tmp_path))
    first_entered, release_first, second_attempted, second_entered = (threading.Event() for _ in range(4))
    calls = []

    def write(info, stream):
        calls.append(info["revision"])
        if info["revision"] == "first":
            first_entered.set()
            assert release_first.wait(5)
        else:
            second_entered.set()
        stream.write(b'{"services":[]}')

    def download(revision):
        if revision == "second":
            second_attempted.set()
        with http.compressed_day({"revision": revision}) as stream:
            return gzip.decompress(stream.read())

    monkeypatch.setattr(http, "write_day", write)
    (tmp_path / "cached.json.gz").write_bytes(gzip.compress(b'{"cached":true}'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        first = pool.submit(download, "first")
        assert first_entered.wait(5)
        second = pool.submit(download, "second")
        duplicate = pool.submit(download, "first")
        try:
            assert second_attempted.wait(5)
            assert pool.submit(download, "cached").result(timeout=2) == b'{"cached":true}'
            assert not second_entered.wait(0.05)
        finally:
            release_first.set()
        assert first.result(timeout=5) == second.result(timeout=5) == duplicate.result(timeout=5)
    assert calls == ["first", "second"]


def test_failed_generation_releases_schedules_and_can_retry(tmp_path, monkeypatch):
    monkeypatch.setenv("SUNTRAIN_REPLAY_CACHE", str(tmp_path))
    releases = []
    monkeypatch.setattr(replay, "clear_replay_cache", lambda: releases.append(True))
    def failure(info, stream):
        stream.write(b'{"unfinished":')
        raise ValueError("bad schedule")
    monkeypatch.setattr(http, "write_day", failure)
    with pytest.raises(ValueError, match="bad schedule"):
        http.compressed_day({"revision": "failed"})
    assert len(releases) == 2 and not list(tmp_path.iterdir())
    monkeypatch.setattr(http, "write_day", lambda info, stream: stream.write(b'{}'))
    with http.compressed_day({"revision": "failed"}) as stream:
        assert gzip.decompress(stream.read()) == b'{}'


@pytest.mark.parametrize("city,day", [("boston", "2024-06-24"), ("london", "2026-10-05")])
def test_bus_only_download_does_not_open_unselected_rail_reference(city, day, monkeypatch):
    replay.clear_replay_cache()
    original_open = gzip.open
    def bus_open(path, *args, **kwargs):
        assert str(path) != str(replay.prepared_path(city)), "Bus-only request opened rail"
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(gzip, "open", bus_open)
    payload = replay.get_replay_day(day, city, modes=["bus"])
    assert payload["services"] and all(s["mode"] == "bus" for s in payload["services"])
    assert payload["schedule"]["license_url"] and payload["schedule"]["source_url"]
    assert payload["bus_schedule"]["available"]


def test_chunked_json_preserves_nested_data_and_unicode():
    value = {"text": 'Glen Waverley → City "Loop"', "null": None, "number": 1.25,
             "stations": [{"lon": -71.1234567890123, "name": "King’s Cross"}, {}],
             "patterns": {"a": {"times": [0, 10, 20, 30], "legs": []}}, "empty": [], "empty_map": {}}
    assert json.loads(b''.join(http.json_fragments(value))) == value
