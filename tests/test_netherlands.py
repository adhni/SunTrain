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
    DISPLAY_COLORS, INTERNATIONAL_ROUTES, OPERATORS, SOURCE, describe_route, selected_route,
)
from schedule_helpers import expanded_pattern


def test_domestic_scope_excludes_replacements_metros_and_international_routes():
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


def test_route_identity_and_display_palette_preserve_source_colours_when_present():
    route = {"route_id": "17562", "agency_id": "IFF:NS", "route_short_name": "Intercity",
             "route_long_name": "Rotterdam Centraal <-> Utrecht Centraal IC2800", "route_color": ""}
    described = describe_route(route, {})
    assert described["route_id"] == "17562" and described["mode"] == "train"
    assert "Rotterdam Centraal ↔ Utrecht Centraal IC2800" in described["line"]
    assert described["color"] == DISPLAY_COLORS["IFF:NS"]
    assert describe_route({**route, "route_color": "ABCDEF"}, {})["color"] == "ABCDEF"


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
    assert not metadata["omitted_trips"]
    assert metadata["native_anchor_patterns"] > 100
    patterns = reference["patterns"]
    assert {p["operator"] for p in patterns.values()} == set(OPERATORS.values())
    assert {p["color"] for p in patterns.values()} == {"#" + color for color in DISPLAY_COLORS.values()}
    assert all(p["mode"] == "train" and "stops" not in p for p in patterns.values())
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
    for day, rows in reference["days"].items():
        assert 3000 < len(rows) < 8000
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
    assert city_settings("netherlands")["start_date"] == SOURCE["first"]
    with pytest.raises(ValueError, match="covers"):
        replay.get_replay_day("2026-06-08", "netherlands")
    with pytest.raises(ValueError, match="Unsupported transport mode"):
        descriptor(SOURCE["first"], "netherlands", ["bus"])
