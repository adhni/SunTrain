"""Prepare national KTM services; Kuala Lumpur rail is reused at runtime."""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.replay import cumulative_distances
from scripts.prepare_france_replay import FranceRailGraph
from scripts.compact_transit import save_reference
from scripts.prepare_australian_replay import file_hash, records
from scripts.prepare_kuala_lumpur_replay import FIRST, KTMB_URL, PINS, TRACK_PIN, compile_geometry, source
from scripts.prepare_rail_replay import prepare as prepare_rail

GEOMETRY = ROOT / "data/reference/malaysia/ktm-tracks-2026-10-22.json.gz"
POSITIONS = GEOMETRY.parent / "station-positions-2026-10-21.json"
ROUTES = {"ETS": "KTM ETS", "ERT": "KTM Intercity", "SH": "KTM Intercity",
          "ST": "Shuttle Tebrau", "SS": "Shuttle Selatan",
          "100_47300": "KTM Komuter Utara", "100_9000": "KTM Komuter Utara"}
NOTE = ("KTM ETS, Intercity including Ekspres Rakyat Timuran, northern Komuter, Shuttle Selatan and Shuttle Tebrau, "
        "with KL Komuter reused from Kuala Lumpur. Peninsular Malaysia network represented in the official October 2026 feed; "
        "not Sabah rail. Optional KL MRT/LRT/Monorail reuses its existing frequency estimates. "
        "Individual KTM schedules, Asia/Kuala_Lumpur time, overnight journeys retained. "
        "Source retrieved 22 October 2026 and applied to 12–18 October calendars; not a record of disruptions. "
        "Unsupported railway sections remain gaps. No individual passenger loads.")


def selected_route(route, agencies):
    kind = "2" if route.get("route_id") in {"ETS", "ERT", "SH", "ST"} else "0"
    return route.get("agency_id") == "ktmb" and route.get("route_id") in ROUTES and route.get("route_type") == kind


def describe_route(route, trip):
    return {"mode": "train", "operator": ROUTES[route["route_id"]], "route_id": route["route_id"],
            "route_short_name": route["route_short_name"], "line": route["route_long_name"]}


def prepare(cache, output):
    geography = compile_geometry(cache, output=GEOMETRY, bounds=(99.5, 1.2, 104.7, 7.1), region="Peninsular Malaysia")
    graph = FranceRailGraph(geography["ways"])
    positions = json.loads(POSITIONS.read_text())
    if positions["metadata"]["source_sha256"] != TRACK_PIN or file_hash(cache / "ktmb.zip") != PINS["ktmb"]:
        raise ValueError("Station position reference or original GTFS differs from its pin")
    derived = cache / "national-stations.zip"
    with ZipFile(cache / "ktmb.zip") as original, ZipFile(derived, "w") as target:
        for name in original.namelist():
            contents = original.read(name)
            if name == "stops.txt":
                stops = list(records(original, name))
                for stop in stops:
                    replacement = positions["stations"].get(stop["stop_id"])
                    if replacement is None:
                        continue
                    point = [float(stop["stop_lon"]), float(stop["stop_lat"])]
                    if (point != replacement["original"] or stop["stop_name"] != replacement["name"]
                            or not graph.anchors(replacement["coordinates"])):
                        raise ValueError("A verified station position no longer matches the source")
                    stop["stop_lon"], stop["stop_lat"] = map(str, replacement["coordinates"])
                text = io.StringIO(newline="")
                writer = csv.DictWriter(text, fieldnames=list(stops[0]))
                writer.writeheader(); writer.writerows(stops)
                contents = text.getvalue().encode()
            info = ZipInfo(name, date_time=(2026, 10, 22, 0, 0, 0)); info.compress_type = ZIP_DEFLATED
            target.writestr(info, contents)
    gaps = []

    def resolve(route, trip, sequence, coordinates):
        result = []
        for i, (a, b) in enumerate(zip(coordinates, coordinates[1:])):
            curve = graph.leg(a, b)
            if curve and cumulative_distances(curve)[-1] > max(5000, 3 * cumulative_distances([a, b])[-1]):
                curve = None
            if curve is None:
                pair = (route["route_id"], sequence[i]["stop_id"], sequence[i + 1]["stop_id"])
                if pair not in gaps:
                    gaps.append(pair)
            result.append(curve)
        return result

    config = {**source("ktmb", derived.as_uri(), file_hash(derived)), "name": "Malaysia", "note": NOTE,
              "geometry_source": "© OpenStreetMap contributors · Peninsular Malaysia connected metre-gauge railways",
              "attribution": "Keretapi Tanah Melayu Berhad via data.gov.my, CC BY 4.0. Snapshot retrieved 22 October 2026. "
                             "Railway alignments and 13 verified station-position corrections © OpenStreetMap contributors, ODbL 1.0. "
                             "Original station names and timetable clocks retained; conversion by SunTrain."}
    build = cache / "national-build"
    prepare_rail("my-ktm", config, build, output, selected_route, describe_route, resolve)
    with gzip.open(output, "rt") as stream:
        reference = json.load(stream)
    reference["metadata"].update(
        sources=[{"source_url": KTMB_URL, "source_date": "2026-10-22", "sha256": PINS["ktmb"]}],
        station_position_corrections=positions["stations"], unresolved_stop_pairs=gaps,
        station_position_source={**positions["metadata"], "reference_sha256": file_hash(POSITIONS)})
    save_reference(reference, output)
    print("National KTM", {d: len(rows) for d, rows in reference["days"].items()},
          "bytes", output.stat().st_size, "unresolved pairs", gaps, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/kuala-lumpur")
    parser.add_argument("--output", type=Path, default=GEOMETRY.parent / (str(FIRST) + ".json.gz"))
    args = parser.parse_args()
    prepare(args.cache.resolve(), args.output)
