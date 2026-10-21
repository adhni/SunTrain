import gzip
import json

import pytest

from dashboard.replay import JAPAN_LIMITED_PATH
from scripts.prepare_japan_kyushu_replay import DAY, parse_tables, printed_clocks, station_label


def test_pdf_labels_and_midnight_are_read_without_generating_departures():
    assert station_label("Futsukaich（i 二日市）") == ("二日市", "Futsukaichi")
    assert station_label("MiyazakiAirpor（t 宮崎空港）") == ("宮崎空港", "MiyazakiAirport")
    assert station_label("TrainName（列車名）") == ("列車名", "TrainName")
    assert printed_clocks("(cid:2)") is None
    assert printed_clocks("||") is None
    assert printed_clocks("0:00", 23 * 3600 + 59 * 60) == (86400, 86400)
    assert printed_clocks("0:09", 86400) == (86940, 86940)
    for stamp, previous in [("TBC", None), ("12:60", None), ("7:00", 8 * 3600)]:
        with pytest.raises(ValueError):
            printed_clocks(stamp, previous)


def test_source_columns_exclude_unverified_calendar_and_all_parts_of_footnoted_trips():
    def table(star=False):
        return [["Traintype（列車種類）", "EP", "DS"],
                ["TrainName（列車名）", "SONIC\n1", "MORI YUFUINNO\n1"],
                ["Seattype（座席設備）", "R/N", "R"],
                ["Hakata（博多）", "★6:21" if star else "6:21", "9:17"],
                ["Kokura（小倉）", "7:09", "9:51"]]
    trips, _, omitted, exclusions = parse_tables([(7, [table()])])
    assert list(trips) == ["Sonic:1"]
    assert len(trips["Sonic:1"]["calls"]) == 2
    assert omitted["Sightseeing train column; operating calendar unverified"] == 1
    trips, _, _, exclusions = parse_tables([(7, [table()]), (8, [table(True)])])
    assert not trips and exclusions == ["Sonic:1"]


def test_bundled_kyushu_snapshot_retains_printed_calls_and_shared_patterns():
    with gzip.open(JAPAN_LIMITED_PATH, "rt") as stream:
        reference = json.load(stream)
    rows = reference["days"][DAY]
    assert len(rows) == 225 and len({trip for _, trip, _ in rows}) == 225
    assert {p["operator"] for p in reference["patterns"].values()} == {"JR Kyushu"}
    families = {p["line"] for p in reference["patterns"].values()}
    assert {"Sonic", "Midori", "Relay Kamome", "Yufu", "Kirishima", "Nichirin", "Hyuga", "Huis Ten Bosch"} <= families
    assert not {"Kamome", "Yufuin No Mori", "Aso Boy!"} & families
    assert len(reference["metadata"]["excluded_footnote_services"]) == 10
    by_number = {reference["train_numbers"][trip]: (key, offset) for key, trip, offset in rows}
    for number, first, last in [("Sonic 1", "06:21", "08:44"), ("Midori 69", "22:35", "24:09")]:
        key, offset = by_number[number]
        pattern = reference["patterns"][key]
        expected = lambda text: int(text[:2]) * 3600 + int(text[3:]) * 60
        assert offset + pattern["times"][1] == expected(first)
        assert offset + pattern["times"][-2] == expected(last)
    for key, _, offset in rows:
        pattern = reference["patterns"][key]
        assert "stops" not in pattern and "stop_pattern" in pattern
        assert all(a <= b for a, b in zip(pattern["times"], pattern["times"][1:]))
        assert 10800 <= offset + pattern["times"][1] < 97200
    for path in reference["paths"].values():
        if path["quality"] == "approximate":
            assert path["coordinates"] == path["distances"] == []
    assert reference["metadata"]["geometry_legs"] == {"mapped": 2161}
    assert JAPAN_LIMITED_PATH.stat().st_size < 500_000
