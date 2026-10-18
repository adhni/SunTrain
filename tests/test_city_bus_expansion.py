import gzip
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from dashboard import replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_city_buses import selected_route, source_for

ROOT = Path(__file__).resolve().parents[1]


def test_bus_scope_excludes_regional_operators_rail_and_ferries():
    agencies = {"metro": {"agency_name": "Transperth"}, "regional": {"agency_name": "Transwa"},
                "town": {"agency_name": "TransBunbury"}, "cta": {"agency_name": "Chicago Transit Authority"}}
    for kind in ("0", "1", "2", "4"):
        assert not selected_route("perth", {"agency_id": "metro", "route_type": kind}, agencies)
    assert selected_route("perth", {"agency_id": "metro", "route_type": "3"}, agencies)
    for agency in ("regional", "town", "cta"):
        assert not selected_route("perth", {"agency_id": agency, "route_type": "3"}, agencies)
    assert selected_route("chicago", {"route_type": "3"}, {"cta": agencies["cta"]})
    assert not selected_route("chicago", {"route_type": "1"}, {"cta": agencies["cta"]})


@pytest.mark.parametrize("city", ["chicago", "perth"])
def test_all_optional_bus_days_preserve_scope_colours_geometry_and_start_assignment(city):
    source = source_for(city)
    first, last = date.fromisoformat(source["first"]), date.fromisoformat(source["last"])
    directory = ROOT / "data/reference" / city / "bus"
    expected = {str(first + timedelta(days=i)) for i in range((last-first).days + 1)}
    assert {p.name.removesuffix(".json.gz") for p in directory.glob("*.json.gz")} == expected
    colors, labels, trip_occurrences = set(), set(), set()
    for day in sorted(expected):
        with gzip.open(directory / (day + ".json.gz"), "rt") as stream:
            bundle = json.load(stream)
        assert set(bundle["days"]) == {day}
        assert bundle["metadata"]["timezone"] == source["timezone"]
        assert not bundle["metadata"]["omitted_trips"]
        for pattern in bundle["patterns"].values():
            assert pattern["mode"] == "bus" and pattern["operator"] == ("CTA" if city == "chicago" else "Transperth")
            colors.add(pattern["color"])
            labels.add(pattern["line"])
            topology = bundle["stop_patterns"][pattern["stop_pattern"]]
            assert all(bundle["stations"][s]["mode"] == "bus" for s in topology["stations"])
            for i, leg in enumerate(topology["legs"]):
                path = bundle["paths"][leg]
                if path["quality"] == "approximate":
                    assert path["coordinates"] == path["distances"] == []
                    continue
                for index, point in ((i, path["coordinates"][0]), (i+1, path["coordinates"][-1])):
                    stop = bundle["stations"][topology["stations"][index]]
                    assert replay.cumulative_distances([[stop["lon"], stop["lat"]], point])[-1] <= 151
        for pattern, trip, offset in bundle["days"][day]:
            assert 10800 <= offset < 97200
            occurrence = (trip, date.fromisoformat(day).toordinal() * 86400 + offset)
            assert occurrence not in trip_occurrences
            trip_occurrences.add(occurrence)
        hashes = {s["sha256"] for s in bundle["metadata"]["sources"]}
        assert hashes == ({s["sha256"] for s in source["archives"]} if city == "chicago" else {source["sha256"]})
    assert "#FF8200" not in colors
    if city == "perth":
        assert colors >= {"#009645", "#002F6C", "#9D2235", "#F1B434", "#509E2F", "#65428A"}
        assert any("Blue CAT" in line for line in labels)
        assert any("Purple CAT" in line for line in labels)
    else:
        assert colors == {"#99999C", "#414145", "#b71234", "#0065bd"}


@pytest.mark.parametrize("city,day", [("chicago", "2025-11-24"), ("perth", "2026-10-05")])
def test_buses_are_optional_and_merge_without_mutating_rail(city, day, monkeypatch, tmp_path):
    replay.clear_replay_cache()
    monkeypatch.setenv(f"SUNTRAIN_{city.upper()}_BUS_REFERENCE", str(tmp_path / "missing"))
    assert descriptor(day, city)["modes"] == city_settings(city)["default_modes"]
    rail = replay.get_replay_day(day, city)
    before = (len(rail["services"]), len(rail["transit_stop_patterns"]))
    assert not any(s["mode"] == "bus" for s in rail["services"])
    monkeypatch.delenv(f"SUNTRAIN_{city.upper()}_BUS_REFERENCE")
    info = descriptor(day, city, ["bus"])
    assert info["bus_data_loaded"]
    combined = replay.get_replay_day(day, city, include_buses=True)
    assert combined["bus_data_loaded"] and any(s["mode"] == "bus" for s in combined["services"])
    assert (len(rail["services"]), len(rail["transit_stop_patterns"])) == before
    for service in combined["services"]:
        assert "stops" not in service
        pattern = combined["transit_patterns"][service["pattern"]]
        topology = combined["transit_stop_patterns"][pattern["stop_pattern"]]
        assert all(0 <= s < len(combined["stations"]) for s in topology["stations"])
        assert all(leg in combined["paths"] for leg in topology["legs"])
