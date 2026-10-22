from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_malaysia_replay import POSITIONS, ROUTES, selected_route


@pytest.fixture(scope="module")
def reference():
    with gzip.open(replay.MALAYSIA_PATH, "rt") as stream:
        return json.load(stream)


def test_national_scope_keeps_seven_source_products_and_excludes_kl_duplicates():
    for route in ROUTES:
        kind = "2" if route in {"ETS", "ERT", "SH", "ST"} else "0"
        assert selected_route({"agency_id": "ktmb", "route_id": route, "route_type": kind}, {})
        assert not selected_route({"agency_id": "ktmb", "route_id": route, "route_type": "3"}, {})
    for route in ["KC05_KB18", "KA15_KD19", "KGL", "PYL"]:
        assert not selected_route({"agency_id": "ktmb", "route_id": route, "route_type": "0"}, {})


def test_exact_services_remain_compact_and_belong_once_to_their_departure_day(reference):
    assert len(reference["days"]) == 7 and all(len(rows) == 210 for rows in reference["days"].values())
    assert not reference["metadata"]["omitted_trips"]
    assert {p["source_route_id"] for p in reference["patterns"].values()} == set(ROUTES)
    for rows in reference["days"].values():
        assert len({(trip, offset) for _, trip, offset in rows}) == len(rows)
        for key, _, offset in rows:
            pattern = reference["patterns"][key]
            assert "stops" not in pattern and not pattern.get("frequency_based")
            assert 10800 <= offset + pattern["times"][1] < 97200
            assert all(a <= b for a, b in zip(pattern["times"], pattern["times"][1:]))
    assert replay.MALAYSIA_PATH.stat().st_size < 300_000


def test_verified_positions_retain_original_evidence_and_unresolved_paths_stay_empty(reference):
    positions = json.loads(POSITIONS.read_text())
    assert len(positions["stations"]) == 13
    assert reference["metadata"]["station_position_corrections"] == positions["stations"]
    stations = {s["name"]: [s["lon"], s["lat"]] for s in reference["stations"]}
    for item in positions["stations"].values():
        assert stations[item["name"]] == item["coordinates"]
        assert item["original"] != item["coordinates"] and item["osm_node_id"]
    for path in reference["paths"].values():
        if path["quality"] == "approximate":
            assert path["coordinates"] == path["distances"] == []
        else:
            assert path["quality"] == "track" and len(path["coordinates"]) >= 2
    day = replay.get_replay_day("2026-10-12", "malaysia", modes=["train"])
    assert 1 - day["approximate_legs"] / day["total_legs"] > .98


def test_national_view_reuses_kl_files_and_keeps_the_original_kl_view_unchanged():
    digest = hashlib.sha256(replay.KUALA_LUMPUR_PATH.read_bytes()).hexdigest()
    original = replay.get_replay_day("2026-10-12", "kuala_lumpur")
    original_ids = {s["id"] for s in original["services"]}
    default = replay.get_replay_day("2026-10-12", "malaysia")
    assert Counter(s["mode"] for s in default["services"]) == {"train": 210, "commuter_rail": 90}
    full = replay.get_replay_day("2026-10-12", "malaysia", modes=[])
    assert len(full["services"]) == 2695 and len({s["id"] for s in full["services"]}) == 2695
    assert sum(bool(full["transit_patterns"][s["pattern"]].get("frequency_based")) for s in full["services"]) == 2395
    files = replay.rail_reference_files("malaysia", "2026-10-12", ["subway", "light_rail", "commuter_rail"])
    assert {Path(path) for _, path, _ in files} == {replay.prepared_path("kuala_lumpur")}
    again = replay.get_replay_day("2026-10-12", "kuala_lumpur")
    assert {s["id"] for s in again["services"]} == original_ids
    assert hashlib.sha256(replay.KUALA_LUMPUR_PATH.read_bytes()).hexdigest() == digest


def test_overnight_times_and_extended_timeline_survive_train_only_selection(reference):
    key, _, offset = next(row for row in reference["days"]["2026-10-12"] if row[1] == "27")
    pattern = reference["patterns"][key]
    assert offset + pattern["times"][1] == 20 * 3600 + 55 * 60
    assert offset + pattern["times"][-1] == 36 * 3600 + 40 * 60
    for modes in [None, ["train"]]:
        day = replay.get_replay_day("2026-10-12", "malaysia", modes=modes)
        assert datetime.fromtimestamp(day["end"], ZoneInfo(day["timezone"])).strftime("%Y-%m-%d %H:%M") == "2026-10-13 12:40"
    assert descriptor("2026-10-12", "malaysia")["modes"] == ["commuter_rail", "train"]
    with pytest.raises(ValueError, match="Date outside"):
        descriptor("2024-06-24", "malaysia")


def test_optional_kl_selection_does_not_read_the_national_file(monkeypatch, tmp_path):
    monkeypatch.setenv("SUNTRAIN_MALAYSIA_REFERENCE", str(tmp_path / "not-downloaded.json.gz"))
    replay.clear_replay_cache()
    info = descriptor("2026-10-12", "malaysia", modes=["subway"])
    assert info["modes"] == ["subway"]
    day = replay.get_replay_day("2026-10-12", "malaysia", modes=["subway"])
    assert len(day["services"]) == 567
