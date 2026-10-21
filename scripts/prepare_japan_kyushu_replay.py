"""Convert the pinned JR Kyushu operator PDF into shared replay patterns.

Preparation only: install pdfplumber separately; the website never imports it.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash
from scripts.prepare_boston_replay import fetch
from scripts.prepare_france_replay import FranceRailGraph

SOURCE_URL = "https://www.jrkyushu.co.jp/english/pdf/timetable_20260314_20270228.pdf"
ARCHIVE_URL = "https://web.archive.org/web/20260307062937id_/" + SOURCE_URL
PDF_SHA256 = "208a0a10946b7c2b4ddbe9b3eeb19cb1dd8a1425e64d89f91ece743b67405faa"
DAY = "2026-03-17"  # First Tuesday in the publication's stated validity period.
GEOMETRY = ROOT / "data/reference/japan/kyushu-tracks-2026-10-22.json.gz"
GEOMETRY_SHA256 = "7df12600ade65e64720abab646992ac494cf3373dd5eda9174e4927b31317dd4"
FAMILIES = {
    "SONIC": "Sonic", "NICHIRIN": "Nichirin", "SEAGAIA NICHIRIN": "Nichirin Seagaia",
    "HYUGA": "Hyuga", "KIRAMEKI": "Kirameki", "KASASAGI": "Kasasagi",
    "KAMOME Relay": "Relay Kamome", "BOSCH HUISTEN": "Huis Ten Bosch",
    "YUFU": "Yufu", "TOKKYU ODAN KYUSHU": "Kyushu Odan Tokkyu",
    "KAIO": "Kaio", "KIRISHIMA": "Kirishima",
}
MARKERS = re.compile(r"[★◆▲○◇△☆●]")


def station_label(value):
    match = re.fullmatch(r"(.*?)（([A-Za-z\s]*)([^）]+)）", value or "")
    if not match:
        return None
    english = match[1].strip() + match[2].strip()
    return match[3].strip().replace("ヶ", "ケ"), english


def printed_clocks(value, previous=None):
    """Arrows are pass-throughs, not calls; roll an explicit midnight clock forward."""
    clocks = re.findall(r"(\d{1,2}):(\d{2})", value or "")
    if not clocks:
        if re.fullmatch(r"\s*(?:\(cid:2\)|\|\||[↓↑レ－―])*\s*", value or ""):
            return None
        raise ValueError("Unreviewed Kyushu time cell: " + repr(value))
    if len(clocks) > 2 or any(int(h) > 23 or int(m) > 59 for h, m in clocks):
        raise ValueError("Invalid Kyushu printed clock")
    times = [int(h) * 3600 + int(m) * 60 for h, m in clocks]
    if previous is not None:
        times = [t + (previous // 86400) * 86400 for t in times]
    if previous is not None and times[0] < previous:
        if previous % 86400 < 20 * 3600 or times[0] % 86400 > 4 * 3600:
            raise ValueError("Backwards daytime clock in Kyushu table")
        times = [t + 86400 for t in times]
    if times[-1] < times[0]:
        times[-1] += 86400
    return times[0], times[-1]


def parse_tables(pages):
    trips, stations, exclusions, omitted = {}, {}, set(), Counter()
    for page_number, tables in pages:
        for table in tables:
            starts = [i for i, row in enumerate(table) if row[0] and "Traintype" in row[0]] + [len(table)]
            for begin, end in zip(starts, starts[1:]):
                rows = table[begin:end]
                if len(rows) < 4 or "TrainName" not in (rows[1][0] or ""):
                    raise ValueError("Kyushu PDF table structure changed")
                for col, kind in enumerate(rows[0][1:], 1):
                    if kind != "EP":
                        if kind == "DS":
                            omitted["Sightseeing train column; operating calendar unverified"] += 1
                        continue
                    label = (rows[1][col] or "").replace("\n", " ").strip()
                    match = re.fullmatch(r"(.+?)\s+(\d+)", label)
                    if not match:
                        raise ValueError("Unreviewed Kyushu service name: " + label)
                    raw, number = match.groups()
                    line = "Midori" if "MIDORI" in raw else FAMILIES[raw]
                    key, calls, marked = line + ":" + number, [], False
                    for row in rows[3:]:
                        station = station_label(row[0])
                        if not station:
                            continue
                        name, english = station
                        value = row[col] or ""
                        marked |= bool(MARKERS.search(value))
                        try:
                            pair = printed_clocks(value, calls[-1][2] if calls else None)
                        except ValueError as error:
                            raise ValueError(f"Page {page_number}, {key}, {name}: {value!r}, previous={calls[-1:]}") from error
                        if pair:
                            stations[name] = english
                            calls.append([name, *pair])
                    if marked:
                        # These notes extend endpoints or add stops; do not silently
                        # discard the note and animate an incomplete through train.
                        exclusions.add(key)
                        omitted["Footnote-marked journey section; needs extended calls"] += 1
                        continue
                    if len(calls) < 2:
                        raise ValueError("Kyushu train has fewer than two clocks")
                    source_pages = [page_number]
                    if key in trips:
                        old = {s: (a, d) for s, a, d in trips[key]["calls"]}
                        for name, arrival, departure in calls:
                            if name in old:
                                if abs(old[name][0] - arrival) > 900:
                                    raise ValueError("Conflicting Kyushu through-train duplicate")
                                old[name] = min(old[name][0], arrival), max(old[name][1], departure)
                            else:
                                old[name] = arrival, departure
                        calls = sorted([[s, *t] for s, t in old.items()], key=lambda r: (r[1], r[2]))
                        source_pages += trips[key]["pages"]
                    trips[key] = {"line": line, "number": number, "calls": calls, "pages": sorted(set(source_pages))}
    for key in exclusions:
        trips.pop(key, None)
    return trips, stations, omitted, sorted(exclusions)


def prepare(cache, output):
    import pdfplumber

    filename = fetch(ARCHIVE_URL, cache / "kyushu-2026.pdf")
    if file_hash(filename) != PDF_SHA256 or file_hash(GEOMETRY) != GEOMETRY_SHA256:
        raise ValueError("Kyushu source differs from the validated pin")
    with pdfplumber.open(filename) as document:
        if len(document.pages) != 14:
            raise ValueError("Unexpected Kyushu timetable page count")
        trips, _, omitted, exclusions = parse_tables(
            [(i + 1, document.pages[i].extract_tables()) for i in range(4, 12)])
    with gzip.open(GEOMETRY, "rt") as stream:
        geometry = json.load(stream)
    graph = FranceRailGraph(geometry["ways"])
    result = {"stations": [], "patterns": {}, "paths": {}, "days": {DAY: []}, "train_numbers": {}}
    station_ids, coverage, unresolved = {}, Counter(), set()
    for trip_id, trip in sorted(trips.items()):
        calls, ids, legs = trip["calls"], [], []
        for name, _, _ in calls:
            if name not in station_ids:
                station = geometry["stations"][name]
                station_ids[name] = len(result["stations"])
                result["stations"].append({"name": name + " " + station["name"],
                    "lon": station["coordinate"][0], "lat": station["coordinate"][1], "mode": "limited_express"})
            ids.append(station_ids[name])
        for a, b in zip(calls, calls[1:]):
            first, last = (geometry["stations"][call[0]]["coordinate"] for call in (a, b))
            curve = graph.leg(first, last)
            if curve and cumulative_distances(curve)[-1] > max(5000, 3 * cumulative_distances([first, last])[-1]):
                curve = None
            coverage["mapped" if curve else "unresolved"] += 1
            if not curve:
                unresolved.add((a[0], b[0]))
            path_id = "jp-kq-" + hashlib.sha256(json.dumps(curve).encode()).hexdigest()[:20]
            result["paths"][path_id] = {"coordinates": curve or [], "distances": cumulative_distances(curve or []),
                "quality": "track" if curve else "approximate"}
            legs.append(path_id)
        origin = calls[0][1]
        pattern = {"mode": "limited_express", "category": "Limited express", "operator": "JR Kyushu",
            "line": trip["line"], "route_id": "jp-kyushu:" + trip["line"], "route_short_name": trip["line"],
            "source_route_id": "jp-kyushu:" + trip["line"], "color": "#E60012",
            "direction": "Direction A" if int(trip["number"]) % 2 else "Direction B",
            "origin": result["stations"][ids[0]]["name"], "destination": result["stations"][ids[-1]]["name"],
            "stops": [[s, a - origin, d - origin] for s, (_, a, d) in zip(ids, calls)], "legs": legs,
            "source_pages": trip["pages"]}
        key = "jp-kq-" + hashlib.sha256(json.dumps(pattern, sort_keys=True).encode()).hexdigest()[:20]
        result["patterns"][key] = pattern
        result["days"][DAY].append([key, trip_id, origin])
        result["train_numbers"][trip_id] = trip["line"] + " " + trip["number"]
    result["days"][DAY].sort(key=lambda r: (r[2], r[1]))
    result["metadata"] = {"start_date": DAY, "end_date": DAY, "timezone": "Asia/Tokyo",
        "source": "JR Kyushu published regular-train timetable, 14 March 2026–28 February 2027",
        "source_url": SOURCE_URL, "license": "JR Kyushu published timetable; source rights retained",
        "license_url": "https://www.jrkyushu.co.jp/english/",
        "attribution": "Timetable: Kyushu Railway Company / JR Kyushu. Converted, selected and mapped by SunTrain. "
                       "Geography © OpenStreetMap contributors, ODbL 1.0.",
        "sources": [{"source_url": SOURCE_URL, "archive_url": ARCHIVE_URL, "sha256": PDF_SHA256,
                     "valid_from": "2026-03-14", "valid_until": "2027-02-28", "source_pages": "5–12"}],
        "geometry_source": geometry["metadata"]["source"],
        "geometry_source_url": "https://www.openstreetmap.org/copyright", "geometry_license": "ODbL 1.0",
        "geometry_license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "geometry_source_date": geometry["metadata"]["source_date"], "geometry_sha256": GEOMETRY_SHA256,
        "geometry_references": geometry["metadata"]["sources"], "geometry_legs": dict(coverage),
        "unresolved_station_sections": sorted(unresolved), "omitted_source_rows": dict(omitted),
        "excluded_footnote_services": exclusions,
        "daily_services": {DAY: dict(Counter(t["line"] for t in trips.values()))},
        "note": "Regular EP columns only. Sightseeing operating calendars and footnote-extended journeys are excluded. "
                "Actual printed clocks, including midnight rollover; no headway-generated departures. "
                "March 17 source is overlaid by weekday in the March 10 national view; not a claim of March 10 operation. "
                "Unmapped legs stay hidden. The operator publication is not asserted to be an open-licensed GTFS feed."}
    save_reference(result, output)
    print(f"Saved {output}: {len(trips)} services, geometry {dict(coverage)}; {output.stat().st_size} bytes", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/japan")
    parser.add_argument("--output", type=Path, default=ROOT / "data/reference/japan/limited-express-2026-03-17.json.gz")
    args = parser.parse_args()
    prepare(args.cache, args.output)
