"""Download and audit official LTA train GTFS without publishing unverified replay.

Use --download with LTA_ACCOUNT_KEY or the ignored local account-key file.
Without --download, inspect the cached ZIP without needing credentials/network.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_transit_replay import active_services, records, seconds

ENDPOINT = "https://datamall2.mytransport.sg/ltaodataservice/GTFSScheduleTrain"
LICENSE_URL = "https://datamall.lta.gov.sg/content/datamall/en/SingaporeOpenDataLicence.html"
CACHE = ROOT / ".cache/singapore-audit"
REQUIRED = {"agency.txt", "routes.txt", "trips.txt", "stops.txt", "stop_times.txt"}


def download(destination, key_file):
    key = os.environ.get("LTA_ACCOUNT_KEY", "").strip()
    if not key and key_file.is_file():
        key = key_file.read_text().strip()
    if not key:
        raise ValueError("Set LTA_ACCOUNT_KEY locally or provide --key-file; never put keys in arguments")
    try:
        request = Request(ENDPOINT, headers={"AccountKey": key, "Accept": "application/json"})
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
        links = [row.get("Link") or row.get("link") for row in payload.get("value", [])]
        links = [link for link in links if link]
        if len(links) != 1:
            raise ValueError("Expected one timetable download link")
        parsed = urlparse(links[0])
        if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".amazonaws.com"):
            raise ValueError("Unexpected timetable download host")
        with urlopen(links[0], timeout=120) as response:
            content = response.read()
        with ZipFile(io.BytesIO(content)) as archive:
            if not REQUIRED <= set(archive.namelist()):
                raise ValueError("Download does not contain a complete GTFS timetable")
    except Exception:
        # urllib errors can contain signed URLs. Do not expose them in tracebacks.
        raise RuntimeError("LTA train download failed; check access, API availability and ZIP contents") from None
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(destination)


def audit(filename, first, last):
    if first > last:
        raise ValueError("Start date must precede end date")
    with ZipFile(filename) as archive:
        names = set(archive.namelist())
        if not REQUIRED <= names or not {"calendar.txt", "calendar_dates.txt"} & names:
            raise ValueError("Missing required GTFS files or service calendar")
        agencies = {r["agency_id"]: r for r in records(archive, "agency.txt")}
        routes = {r["route_id"]: r for r in records(archive, "routes.txt")}
        trips = {r["trip_id"]: r for r in records(archive, "trips.txt")}
        stops = {r["stop_id"]: r for r in records(archive, "stops.txt")}
        calendars = list(records(archive, "calendar.txt")) if "calendar.txt" in names else []
        exceptions = list(records(archive, "calendar_dates.txt")) if "calendar_dates.txt" in names else []
        feed = list(records(archive, "feed_info.txt")) if "feed_info.txt" in names else []
        shapes = {r["shape_id"] for r in records(archive, "shapes.txt")} if "shapes.txt" in names else set()
        frequency_trips = {r["trip_id"] for r in records(archive, "frequencies.txt")} if "frequencies.txt" in names else set()
        calls = defaultdict(list)
        issues = Counter()
        for row in records(archive, "stop_times.txt"):
            if row["trip_id"] not in trips:
                issues["stop_times_without_trip"] += 1
            calls[row["trip_id"]].append(row)
        for trip_id, trip in trips.items():
            if trip["route_id"] not in routes:
                issues["trips_without_route"] += 1
            sequence = sorted(calls[trip_id], key=lambda r: int(r["stop_sequence"]))
            if len(sequence) < 2:
                issues["trips_with_fewer_than_two_stops"] += 1
            if len({r["stop_sequence"] for r in sequence}) != len(sequence):
                issues["duplicate_stop_sequences"] += 1
            try:
                times = [seconds(r[field]) for r in sequence for field in ("arrival_time", "departure_time")]
                if any(b < a for a, b in zip(times, times[1:])):
                    issues["backwards_trip_times"] += 1
            except (ValueError, KeyError):
                issues["invalid_trip_times"] += 1
            if any(r["stop_id"] not in stops for r in sequence):
                issues["trips_without_stop"] += 1
        for stop in stops.values():
            try:
                lon, lat = float(stop["stop_lon"]), float(stop["stop_lat"])
                if not math.isfinite(lon + lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise ValueError("Invalid coordinates")
            except (ValueError, KeyError):
                issues["invalid_stop_coordinates"] += 1
        lines = {}
        for route in routes.values():
            key = route["route_short_name"]
            entry = lines.setdefault(key, {"name": route["route_long_name"], "agency": route["agency_id"],
                "route_type": route["route_type"], "color": "#" + route["route_color"], "route_variants": 0})
            entry["route_variants"] += 1
        daily = {}
        for offset in range((last - first).days + 1):
            day = first + timedelta(days=offset)
            active = active_services(calendars, exceptions, day)
            counts = Counter(routes[t["route_id"]]["route_short_name"] for t in trips.values()
                             if t["service_id"] in active and t["route_id"] in routes)
            daily[str(day)] = dict(sorted(counts.items()))
        missing_shapes = sum(not t.get("shape_id") or t["shape_id"] not in shapes for t in trips.values())
        blockers = []
        if missing_shapes:
            blockers.append(f"{missing_shapes} trips lack supplied railway shapes; no replacement geometry validated")
        else:
            blockers.append("Supplied shapes still require ordered stop projection and branch/loop validation")
        if issues:
            blockers.append("Timetable validation issues need investigation")
        if frequency_trips:
            blockers.append("Frequency-based services need explicit handling")
        if any(not counts for counts in daily.values()):
            blockers.append("Selected period contains dates without active services")
        if any(a["agency_timezone"] != "Asia/Singapore" for a in agencies.values()):
            blockers.append("Unexpected agency timezone")
        return {"source_url": ENDPOINT, "license_url": LICENSE_URL,
            "sha256": hashlib.sha256(filename.read_bytes()).hexdigest(), "feed_info": feed,
            "calendar_ranges": calendars, "date_exceptions": exceptions,
            "agencies": {key: row["agency_name"] for key, row in agencies.items()},
            "counts": {"routes": len(routes), "trips": len(trips), "stops": len(stops),
                       "stop_times": sum(map(len, calls.values())), "shapes": len(shapes),
                       "trips_without_shapes": missing_shapes, "frequency_trips": len(frequency_trips)},
            "lines": lines, "daily_service_date_trip_counts": daily, "validation_issues": dict(issues),
            "timetable_checks_passed": not issues, "ready_for_replay": False, "blockers": blockers,
            "note": "Snapshot calendars, not evidence of every past disruption. Counts are GTFS service-date trips, not 03:00 replay occurrences. No passenger train loads."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--zip", type=Path, default=CACHE / "train-gtfs.zip")
    parser.add_argument("--key-file", type=Path, default=CACHE / "account-key")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 10, 5))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 10, 11))
    parser.add_argument("--output", type=Path, default=CACHE / "audit.json")
    args = parser.parse_args()
    if args.download:
        download(args.zip, args.key_file)
    report = audit(args.zip, args.start, args.end)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("counts", "validation_issues", "ready_for_replay", "blockers")}, indent=2))
