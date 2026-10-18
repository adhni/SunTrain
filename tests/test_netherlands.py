from collections import Counter
from datetime import date, datetime, time, timedelta
import gzip
import json
from zoneinfo import ZoneInfo

import pytest

from dashboard import data, replay
from dashboard.cities import city_settings
from dashboard.replay_http import descriptor
from scripts.prepare_netherlands_replay import (
    DISPLAY_COLORS, GEOMETRY, GEOMETRY_SHA256, INTERNATIONAL_ROUTES, METRO_LINES, METRO_OPERATORS,
    OPERATORS, SOURCE, describe_route, metro_geometry_resolver, selected_route,
)
from scripts.prepare_netherlands_geometry import selected_relation
from scripts.prepare_australian_replay import file_hash
from schedule_helpers import expanded_pattern


def test_domestic_train_scope_excludes_replacements_and_international_routes():
    agencies = {key: {"agency_name": name} for key, name in OPERATORS.items()}
    domestic = {"route_id": "17562", "agency_id": "IFF:NS", "route_type": "2"}
    assert selected_route(domestic, agencies)
    for agency in OPERATORS:
        assert selected_route({**domestic, "agency_id": agency}, agencies)
    for mode in ("0", "1", "3", "4"):
        assert not selected_route({**domestic, "route_type": mode}, agencies)
    for agency in ("IFF:NS_INT", "IFF:DB", "IFF:EUROBAHN", "IFF:VIAS", "IFF:NMBS", "IFF:GV", "GVB", "RET"):
        assert not selected_route({**domestic, "agency_id": agency}, agencies)
    for route in INTERNATIONAL_ROUTES:
        assert not selected_route({**domestic, "agency_id": "IFF:ARRIVA", "route_id": route}, agencies)
    assert not selected_route(domestic, {"IFF:NS": {"agency_name": "Unexpected operator"}})


def test_metro_scope_includes_only_the_two_audited_agencies_and_their_ten_lines():
    agencies = {key: {"agency_name": name} for key, name in {**OPERATORS, **METRO_OPERATORS}.items()}
    metro = {"route_id": "91927", "agency_id": "GVB", "route_type": "1", "route_short_name": "50"}
    for agency, lines in METRO_LINES.items():
        for line in lines:
            assert selected_route({**metro, "agency_id": agency, "route_short_name": line}, agencies)
        assert not selected_route({**metro, "agency_id": agency, "route_short_name": "99"}, agencies)
        for mode in ("0", "2", "3", "4"):
            assert not selected_route({**metro, "agency_id": agency, "route_type": mode}, agencies)
    for agency in OPERATORS:
        assert not selected_route({**metro, "agency_id": agency}, agencies)
    assert not selected_route(metro, {"GVB": {"agency_name": "Unrelated operator"}})


def test_route_identity_and_display_palette_preserve_source_colours_when_present():
    route = {"route_id": "17562", "agency_id": "IFF:NS", "route_short_name": "Intercity",
             "route_long_name": "Rotterdam Centraal <-> Utrecht Centraal IC2800", "route_color": ""}
    described = describe_route(route, {})
    assert described["route_id"] == "17562" and described["mode"] == "train"
    assert "Rotterdam Centraal ↔ Utrecht Centraal IC2800" in described["line"]
    assert described["color"] == DISPLAY_COLORS["IFF:NS"]
    assert describe_route({**route, "route_color": "ABCDEF"}, {})["color"] == "ABCDEF"
    for agency, code, color, city in [("GVB", "50", "187a36", "Amsterdam"), ("RET", "A", "00b43f", "Rotterdam")]:
        metro = describe_route({**route, "agency_id": agency, "route_short_name": code, "route_color": color}, {})
        assert metro["mode"] == "subway" and metro["route_id"] == route["route_id"]
        assert metro["line"] == f"{city} Metro {code}" and metro["color"] == color


def test_ret_geometry_is_pinned_and_only_overrides_the_audited_operator():
    assert file_hash(GEOMETRY) == GEOMETRY_SHA256
    with gzip.open(GEOMETRY, "rt") as stream:
        geographic = json.load(stream)
    assert geographic["metadata"]["license"] == "ODbL 1.0"
    assert set(geographic["lines"]) == METRO_LINES["RET"]
    assert all(len(v["coordinates"]) == len(v["node_ids"]) >= 2
               for variants in geographic["lines"].values() for v in variants)
    relation = {"type": "route", "route": "subway", "operator": "RET", "ref": "E"}
    assert selected_relation(relation)
    assert not selected_relation({**relation, "operator": "GVB"})
    assert not selected_relation({**relation, "route": "bus"})
    resolve = metro_geometry_resolver(geographic)
    for agency in [*OPERATORS, "GVB"]:
        assert resolve({"agency_id": agency}, {}, [], []) is NotImplemented


def test_pinned_week_preserves_shared_schedules_native_geometry_and_unique_occurrences():
    with gzip.open(replay.NETHERLANDS_PATH, "rt") as stream:
        reference = json.load(stream)
    metadata = reference["metadata"]
    assert metadata["schedule_encoding"] == "shared-stops-flat-times-v1"
    assert metadata["sources"][0]["sha256"] == SOURCE["sha256"]
    assert metadata["sources"][0]["feed_version"] == "9375"
    assert metadata["sources"][0]["valid_from"] == "20260529"
    assert metadata["sources"][0]["valid_through"] == "20261212"
    assert metadata["geometry_method"] == "native_or_ordered_per_leg"
    assert metadata["geometry_sha256"] == GEOMETRY_SHA256
    assert metadata["geometry_license"] == "ODbL 1.0"
    assert not metadata["omitted_trips"]
    assert metadata["native_anchor_patterns"] > 100
    patterns = reference["patterns"]
    assert {p["operator"] for p in patterns.values()} == set(OPERATORS.values()) | set(METRO_OPERATORS.values())
    trains = [p for p in patterns.values() if p["mode"] == "train"]
    metros = [p for p in patterns.values() if p["mode"] == "subway"]
    assert {p["color"] for p in trains} == {"#" + color for color in DISPLAY_COLORS.values()}
    metro_colors = {"GVB": dict(zip(["50", "51", "52", "53", "54"],
                                  ["#187a36", "#FF6600", "#00adef", "#d81118", "#fff200"])),
                    "RET": dict(zip(["A", "B", "C", "D", "E"],
                                  ["#00b43f", "#ffdd00", "#e32119", "#34b4e4", "#003a8c"]))}
    assert {p["operator"] for p in metros} == {"GVB", "RET"}
    assert all(p["color"] == metro_colors[p["operator"]][p["route_short_name"]] for p in metros)
    assert all(p["mode"] in {"train", "subway"} and "stops" not in p for p in patterns.values())
    for pattern in patterns.values():
        expanded = expanded_pattern(reference, pattern)
        assert len(expanded["stops"]) == len(expanded["legs"]) + 1
        times = [value for stop in expanded["stops"] for value in stop[1:]]
        assert all(b >= a for a, b in zip(times, times[1:]))
        for index, leg in enumerate(expanded["legs"]):
            path = reference["paths"][leg]
            if path["quality"] == "approximate":
                assert path["coordinates"] == path["distances"] == []
                continue
            assert path["quality"] == "shape" and len(path["coordinates"]) >= 2
            assert len(path["coordinates"]) == len(path["distances"])
            assert path["distances"][0] == 0
            assert all(b >= a for a, b in zip(path["distances"], path["distances"][1:]))
            for station_index, point in ((index, path["coordinates"][0]), (index + 1, path["coordinates"][-1])):
                stop = reference["stations"][expanded["stops"][station_index][0]]
                assert replay.cumulative_distances([[stop["lon"], stop["lat"]], point])[-1] <= 151
    zone = ZoneInfo(SOURCE["timezone"])
    first = date.fromisoformat(SOURCE["first"])
    assert set(reference["days"]) == {str(first + timedelta(days=i)) for i in range(7)}
    occurrences = set()
    train_counts = [5960, 5977, 5985, 5973, 5737, 5249, 4652]
    for index, (day, rows) in enumerate(sorted(reference["days"].items())):
        assert 3000 < len(rows) < 15000
        assert sum(patterns[p]["mode"] == "train" for p, _, _ in rows) == train_counts[index]
        for agency, lines in METRO_LINES.items():
            assert {patterns[p]["route_short_name"] for p, _, _ in rows if patterns[p]["operator"] == agency} == lines
        for line in {p["line"] for p in metros}:
            legs = Counter(reference["paths"][leg]["quality"]
                           for key, _, _ in rows if patterns[key]["line"] == line
                           for leg in reference["stop_patterns"][patterns[key]["stop_pattern"]]["legs"])
            assert legs["shape"] / sum(legs.values()) > .95, (day, line, legs)
        local = date.fromisoformat(day)
        midnight = int(datetime.combine(local, time(0), zone).timestamp())
        start = midnight + 3 * 3600
        for pattern, trip, offset in rows:
            occurrence = (trip, midnight + offset)
            assert occurrence not in occurrences
            occurrences.add(occurrence)
            assert start <= occurrence[1] < start + 86400
        assert Counter(patterns[p]["route_id"] for p, _, _ in rows) == metadata["daily_services"][day]
    names = {s["name"] for s in reference["stations"]}
    assert {"Amsterdam Centraal", "Utrecht Centraal", "Rotterdam Centraal", "Den Haag Centraal",
            "Groningen", "Maastricht", "Vlissingen", "Enschede", "Leeuwarden"} <= names
    assert replay.NETHERLANDS_PATH.stat().st_size < 5_000_000


def test_every_day_loads_without_passenger_warehouse_and_uses_amsterdam_local_time(monkeypatch):
    monkeypatch.setattr(data, "_connect", lambda: pytest.fail("Netherlands replay queried Melbourne data"))
    for i in range(7):
        day = str(date.fromisoformat(SOURCE["first"]) + timedelta(days=i))
        payload = replay.get_replay_day(day, "netherlands")
        clock = datetime.fromtimestamp(payload["initial"], ZoneInfo(payload["timezone"]))
        assert clock.hour == 8 and str(clock.date()) == day
        assert clock.utcoffset().total_seconds() == 7200
        assert payload["passenger_data"] is False
        assert payload["services"] and all("stops" not in s for s in payload["services"])
        assert payload["schedule"]["license_url"] == "https://gtfs.ovapi.nl/README"
        metro = replay.get_replay_day(day, "netherlands", modes=["subway"])
        rail = replay.get_replay_day(day, "netherlands", modes=["train"])
        assert len(metro["services"]) + len(rail["services"]) == len(payload["services"])
        assert all(s["mode"] == "subway" for s in metro["services"])
        assert all(p["mode"] == "subway" for p in metro["transit_patterns"].values())
        assert {p["operator"] for p in metro["transit_patterns"].values()} == {"GVB", "RET"}
    assert city_settings("netherlands")["start_date"] == SOURCE["first"]
    with pytest.raises(ValueError, match="covers"):
        replay.get_replay_day("2026-06-08", "netherlands")
    with pytest.raises(ValueError, match="Unsupported transport mode"):
        descriptor(SOURCE["first"], "netherlands", ["bus"])
