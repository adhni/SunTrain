import gzip
import json
import os

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
    assert {leg for p in silver["transit_patterns"].values() for leg in p["legs"]} == silver["paths"].keys()
