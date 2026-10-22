"""Prepare Bangkok rail from the pinned official OTP / Namtang snapshot.

National SRT records and incomplete/ambiguous urban templates are deliberately
excluded. Departures illustrate source frequencies, not observed train services.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
import gzip
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash, path_legs, records
from scripts.prepare_boston_replay import fetch
from scripts.prepare_jakarta_busway import frequency_departures
from scripts.prepare_rail_replay import prepare as prepare_rail
from scripts.prepare_transit_replay import active_services, seconds

URL = "https://namtang-api.otp.go.th/download/namtang-gtfs.zip"
SHA256 = "a451d1081c6008fb2c94a0c8c0be7172c2dd320adacb3a3db1b1390a1bf50ce7"
FIRST, LAST = date(2026, 10, 12), date(2026, 10, 18)
OUTPUT = ROOT / "data/reference/bangkok/2026-10-12.json.gz"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
ROUTES = {
    "1": ("BTSC", "0", "subway", "BTS", "BTS Sukhumvit"),
    "2": ("BTSC", "0", "subway", "BTS", "BTS Silom"),
    "3": ("BEM", "1", "subway", "MRT Blue / Purple", "MRT Blue"),
    "4": ("BEM", "1", "subway", "MRT Blue / Purple", "MRT Purple"),
    "2025": ("BTSC", "0", "light_rail", "BTS", "Gold Line"),
    "2026": ("SRTET", "0", "commuter_rail", "SRT Red Lines", "Dark Red Line"),
    "2027": ("SRTET", "0", "commuter_rail", "SRT Red Lines", "Light Red Line"),
    "2224": ("MRTA", "1", "light_rail", "MRT Yellow", "MRT Yellow"),
}
NOTE = ("Bangkok rail only: BTS Sukhumvit/Silom, MRT Blue/Purple, Gold, Yellow and both Red Lines. "
        "Movements illustrate OTP / Namtang frequency templates and journey sections, not exact train departures or live positions. "
        "21 October 2026 snapshot applied to 12–18 October calendars, including the 13 October holiday exception. "
        "National SRT, Pink Line, Airport Rail Link, buses and passenger loads are excluded pending reliable timings.")


def english(value):
    return value.split(";")[-1].strip()


def selected_route(route, agencies):
    config = ROUTES.get(route.get("route_id"))
    return bool(config and (route.get("agency_id"), route.get("route_type")) == config[:2])


def select_templates(routes, trips, calls, frequencies, stops):
    """Reject impossible running times and conflicting duplicate definitions."""
    groups, omitted = defaultdict(list), {}
    for tid, trip in trips.items():
        sequence = calls[tid]
        times = [(seconds(s["arrival_time"]), seconds(s["departure_time"])) for s in sequence]
        flat = [v for pair in times for v in pair]
        if len(sequence) < 2 or any(b < a for a, b in zip(flat, flat[1:])):
            omitted[tid] = "Missing or backwards station times"
            continue
        invalid = False
        for a, b, (_, departure), (arrival, _) in zip(sequence, sequence[1:], times, times[1:]):
            points = [[float(stops[s["stop_id"]]["stop_lon"]), float(stops[s["stop_id"]]["stop_lat"])] for s in [a, b]]
            distance = cumulative_distances(points)[-1]; elapsed = arrival - departure
            if distance > 50 and (elapsed <= 0 or distance / elapsed > 50):  # conservative 180 km/h upper bound
                invalid = True
                break
        if invalid:
            omitted[tid] = "Zero-time or implausibly fast movement between distinct stations"
            continue
        frequency_departures(frequencies[tid])  # Reject overlapping/invalid windows before conversion.
        key = (trip["route_id"], trip["service_id"], trip.get("direction_id"), tuple(s["stop_id"] for s in sequence))
        groups[key].append((tid, tuple(v - flat[0] for v in flat)))
    selected = set()
    for group in groups.values():
        if len({times for _, times in group}) > 1:
            omitted.update({tid: "Conflicting timings for the same route, calendar and station sequence" for tid, _ in group})
            continue
        # Identical timing templates occur with both coarse all-day windows and
        # detailed peak/off-peak windows. Keep the detailed version once.
        chosen = min((tid for tid, _ in group), key=lambda tid: (-len(frequencies[tid]), int(tid)))
        selected.add(chosen)
        omitted.update({tid: "Duplicate timing template; detailed peak/off-peak definition retained as " + chosen
                        for tid, _ in group if tid != chosen})
    return selected, omitted


def prepare(cache, output):
    cache.mkdir(parents=True, exist_ok=True)
    original = fetch(URL, cache / "namtang-gtfs.zip")
    if file_hash(original) != SHA256:
        raise ValueError("OTP snapshot changed; validate its dates, rail scope and templates before updating the pin")
    with ZipFile(original) as archive:
        info = list(records(archive, "feed_info.txt"))
        if info[0]["feed_version"] != "20261021":
            raise ValueError("Unexpected OTP feed edition")
        routes = {r["route_id"]: r for r in records(archive, "routes.txt") if selected_route(r, {})}
        trips = {r["trip_id"]: r for r in records(archive, "trips.txt") if r["route_id"] in routes}
        stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
        calls, frequencies = defaultdict(list), defaultdict(list)
        for row in records(archive, "stop_times.txt"):
            if row["trip_id"] in trips:
                calls[row["trip_id"]].append(row)
        for sequence in calls.values():
            sequence.sort(key=lambda r: int(r["stop_sequence"]))
        for row in records(archive, "frequencies.txt"):
            if row["trip_id"] in trips:
                frequencies[row["trip_id"]].append(row)
        selected, omitted = select_templates(routes, trips, calls, frequencies, stops)
        if {trips[t]["route_id"] for t in selected} != set(ROUTES):
            raise ValueError("A selected Bangkok rail line has no usable timing templates")
        station_ids = {s["stop_id"] for t in selected for s in calls[t]}
        shape_ids = {trips[t]["shape_id"] for t in selected}
        calendars = list(records(archive, "calendar.txt")); exceptions = list(records(archive, "calendar_dates.txt"))
        templates = cache / "rail-templates.zip"
        with ZipFile(templates, "w") as target:
            def write(name, rows):
                rows = iter(rows); first = next(rows)
                text = io.StringIO(newline=""); writer = csv.DictWriter(text, fieldnames=list(first))
                writer.writeheader(); writer.writerow(first); writer.writerows(rows)
                entry = ZipInfo(name, (2026, 10, 22, 0, 0, 0)); entry.compress_type = ZIP_DEFLATED
                target.writestr(entry, text.getvalue().encode())
            write("agency.txt", records(archive, "agency.txt"))
            write("calendar.txt", calendars); write("calendar_dates.txt", exceptions)
            write("routes.txt", ({**r, "route_long_name": ROUTES[r["route_id"]][4]} for r in routes.values()))
            write("trips.txt", ({**trips[t], "trip_headsign": english(trips[t]["trip_headsign"])} for t in sorted(selected, key=int)))
            write("stops.txt", ({**stops[s], "stop_name": english(stops[s]["stop_name"])} for s in sorted(station_ids, key=int)))
            write("stop_times.txt", (s for t in sorted(selected, key=int) for s in calls[t]))
            write("shapes.txt", (r for r in records(archive, "shapes.txt") if r["shape_id"] in shape_ids))
    source = {"first": str(FIRST), "last": str(LAST), "timezone": "Asia/Bangkok", "captured": "2026-10-22",
        "published": "2026-10-21", "url": templates.resolve().as_uri(), "sha256": file_hash(templates),
        "calendar_validity": True, "assign_by_start": ["subway", "light_rail", "commuter_rail"],
        "source": "Office of Transport and Traffic Policy and Planning, Thailand · Namtang GTFS 20261021",
        "source_url": "https://namtang-api.otp.go.th/opendata", "license": "CC BY 4.0", "license_url": LICENSE,
        "attribution": "Office of Transport and Traffic Policy and Planning, Thailand (OTP / สนข.), CC BY 4.0. "
            "Namtang feed 20261021, retrieved 22 October 2026. SunTrain changes: rail selection, English display names, "
            "invalid/duplicate template exclusions, shared schedule/path conversion and illustrative headway departures.",
        "geometry_source": "OTP / Namtang supplied rail shapes", "geometry_source_url": URL,
        "geometry_license": "CC BY 4.0", "geometry_license_url": LICENSE,
        "geometry_method": "ordered_projection", "note": NOTE}
    def describe(route, trip):
        _, _, mode, operator, line = ROUTES[route["route_id"]]
        return {"mode": mode, "operator": operator, "line": line, "route_id": route["route_id"], "frequency_based": True}
    unresolved = []
    def geometry_factory(routes, trips, shapes):
        def resolve(route, trip, sequence, coordinates):
            if route["route_id"] not in {"2026", "2027"}:
                return NotImplemented
            # Red Line station/shape mismatches must not erase the entire line.
            # Recover only pairs matching their own directional source shape.
            raw = shapes[trip["shape_id"]]; curves = []
            for i, (a, b) in enumerate(zip(coordinates, coordinates[1:])):
                try:
                    curve = path_legs(raw, None, [a, b])[0]
                    if cumulative_distances(curve)[-1] > max(1500, 3 * cumulative_distances([a, b])[-1]):
                        curve = None
                except ValueError:
                    curve = None
                if curve is None:
                    pair = [route["route_id"], sequence[i]["stop_id"], sequence[i + 1]["stop_id"]]
                    if pair not in unresolved:
                        unresolved.append(pair)
                curves.append(curve)
            return curves
        return resolve
    prepared = cache / "rail-templates.json.gz"
    prepare_rail("bangkok", source, cache / "build", prepared, selected_route, describe,
                 geometry_resolver_factory=geometry_factory)
    with gzip.open(prepared, "rt") as stream:
        result = json.load(stream)
    patterns = {trip: key for rows in result["days"].values() for key, trip, _ in rows}
    if set(patterns) != selected:
        raise ValueError("Some Bangkok frequency templates were omitted by the rail converter")
    result["days"] = {str(FIRST + timedelta(days=i)): [] for i in range(7)}
    for i in range(-1, 8):
        service_day = FIRST + timedelta(days=i); active = active_services(calendars, exceptions, service_day)
        for tid in sorted(selected, key=int):
            if trips[tid]["service_id"] not in active:
                continue
            first = calls[tid][0]
            dwell = seconds(first["departure_time"]) - seconds(first["arrival_time"])
            for departure in frequency_departures(frequencies[tid]):
                owner = service_day + timedelta(days=(departure - 10800) // 86400)
                if str(owner) in result["days"]:
                    offset = (service_day - owner).days * 86400 + departure - dwell
                    result["days"][str(owner)].append([patterns[tid], tid + ":estimate-" + str(departure), offset])
    for rows in result["days"].values():
        rows.sort(key=lambda r: (r[2], r[1]))
        if len(rows) != len({(t, o) for _, t, o in rows}):
            raise ValueError("Duplicate estimated departure")
    result["metadata"].update(sources=[{"source_url": URL, "source_date": "2026-10-21", "retrieved": "2026-10-22", "sha256": SHA256}],
        frequency_based=True, feed_version="20261021", selected_templates=sorted(selected, key=int), excluded_templates=omitted,
        unresolved_stop_pairs=unresolved,
        license_statement_url="https://namtang-api.otp.go.th/opendata", excluded_networks=["National SRT", "Airport Rail Link", "MRT Pink", "Buses", "Ferries"],
        calendar_basis="Published calendars and exceptions applied to 12–18 October 2026; current snapshot, not a historical revision archive",
        daily_services={d: dict(Counter(result["patterns"][p]["line"] for p, _, _ in rows)) for d, rows in result["days"].items()})
    save_reference(result, output)
    print("Bangkok departures", {d: len(v) for d, v in result["days"].items()}, "bytes", output.stat().st_size,
          "excluded templates", omitted, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/thailand")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(); prepare(args.cache.resolve(), args.output)
