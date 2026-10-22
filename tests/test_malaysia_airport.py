from collections import Counter
import gzip
import json
from pathlib import Path

import pytest

from dashboard import replay
from dashboard.replay_http import descriptor
from scripts.prepare_malaysia_airport import SOURCE, GEOMETRY, parse_table, remove_combined_duplicates


def read(path):
    with gzip.open(path, "rt") as stream:
        return json.load(stream)


def test_combined_night_rows_match_both_calendars_before_being_removed():
    source = read(SOURCE)
    combined = source["metadata"]["combined_ekspres_rows_stored_under_transit"]
    transit = [t for t in source["trips"] if t["kind"] == "transit"]
    assert len(combined) == 10
    assert remove_combined_duplicates(combined, transit) == ([], combined)
    with pytest.raises(ValueError, match="exactly one"):
        remove_combined_duplicates(combined, [t for t in transit if t["calendar"] == "weekday"])
    assert Counter((t["kind"], t["calendar"]) for t in source["trips"]) == {
        ("ekspres", "daily"): 108, ("transit", "weekday"): 104, ("transit", "weekend"): 83}


def test_pdf_columns_preserve_short_workings_and_roll_over_only_at_midnight():
    trips = parse_table([["-", "-", "-", "05:00", "05:07", "05:10", None,
                          "23:55", "00:00", "00:07", "00:16", "00:27", "00:35"]], "transit", "weekday")
    assert trips[0]["calls"] == [["ST", 18000], ["T1", 18420], ["T2", 18600]]
    assert trips[1]["calls"][-1] == ["KL", 88500]
    with pytest.raises(ValueError, match="Backwards"):
        parse_table([["10:00", "09:30", "10:33", None, None, None, None]], "ekspres", "daily")


@pytest.mark.parametrize("day,calendar,count", [("2026-10-12", "weekday", 212), ("2026-10-17", "weekend", 191)])
def test_every_published_call_is_retained_without_frequencies_or_duplicate_trains(day, calendar, count):
    source = read(SOURCE); reference = read(replay.KUALA_LUMPUR_PATH)
    expected = Counter(tuple((code, t) for code, t in trip["calls"]) for trip in source["trips"]
                       if trip["calendar"] in {calendar, "daily"})
    names = {"KL": "KL Sentral", "BTS": "Bandar Tasik Selatan", "PC": "Putrajaya & Cyberjaya",
             "ST": "Salak Tinggi", "T1": "KLIA T1", "T2": "KLIA T2"}
    reverse = {v: k for k, v in names.items()}; actual = Counter()
    for key, trip, offset in reference["days"][day]:
        pattern = reference["patterns"][key]
        if pattern["mode"] != "airport_rail":
            continue
        assert not pattern.get("frequency_based") and "stops" not in pattern
        assert 10800 <= offset + pattern["times"][1] < 97200
        topology = reference["stop_patterns"][pattern["stop_pattern"]]
        calls = tuple((reverse[reference["stations"][s]["name"]], offset + pattern["times"][i * 2])
                      for i, s in enumerate(topology["stations"]))
        actual[calls] += 1
        assert all(reference["paths"][leg]["quality"] == "track" and reference["paths"][leg]["coordinates"]
                   for leg in topology["legs"])
    assert actual == expected and sum(actual.values()) == count and set(actual.values()) == {1}
    # Both airport services run after midnight, but their shared train appears once.
    assert (("T2", 90000), ("T1", 90300), ("ST", 90720), ("PC", 91260), ("BTS", 91920), ("KL", 92400)) in actual


def test_airport_layer_is_shared_across_views_with_optional_national_loading(monkeypatch, tmp_path):
    kl = replay.get_replay_day("2026-10-12", "kuala_lumpur", modes=["airport_rail"])
    assert len(kl["services"]) == 212 and kl["approximate_legs"] == 0
    kl_patterns = [kl["transit_patterns"][s["pattern"]] for s in kl["services"]]
    assert {p["line"] for p in kl_patterns} == {"KLIA Ekspres", "KLIA Transit"}
    assert {p["color"] for p in kl_patterns} == {"#800080", "#139593"}
    assert "operator rights retained" in kl["schedule"]["license"]
    monkeypatch.setenv("SUNTRAIN_MALAYSIA_REFERENCE", str(tmp_path / "not-loaded.gz"))
    replay.clear_replay_cache()
    info = descriptor("2026-10-12", "malaysia", modes=["airport_rail"])
    assert info["modes"] == ["airport_rail"]
    files = replay.rail_reference_files("malaysia", "2026-10-12", ["airport_rail"])
    assert {Path(path) for _, path, _ in files} == {replay.KUALA_LUMPUR_PATH}
    national = replay.get_replay_day("2026-10-12", "malaysia", modes=["airport_rail"])
    assert len(national["services"]) == 212 and national["approximate_legs"] == 0
    assert Counter(national["transit_patterns"][s["pattern"]]["line"] for s in national["services"]) == Counter(p["line"] for p in kl_patterns)
    assert read(GEOMETRY)["metadata"]["license"] == "ODbL 1.0"
