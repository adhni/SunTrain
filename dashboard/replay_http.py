"""Small replay descriptors and immutable compressed downloads for every city."""
from __future__ import annotations

import glob
import gzip
import hashlib
import os
import tempfile
import threading
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import orjson
from flask import abort, request, send_file

from dashboard import data, replay, transit
from dashboard.cities import city_settings

FORMAT_VERSION = 2
CACHE_LIMIT = 256 * 1024 * 1024
BUILD_LOCKS = [threading.Lock() for _ in range(16)]
CACHE_LOCK = threading.Lock()


def selected_modes(city, modes=None):
    settings = city_settings(city)
    allowed = {mode for _, mode in settings["modes"]}
    chosen = set(settings.get("default_modes", allowed) if modes is None else modes or allowed)
    if not chosen <= allowed:
        raise ValueError("Unsupported transport mode")
    return tuple(sorted(chosen))


def _stamp(path):
    path = Path(path)
    return str(path), path.stat().st_mtime_ns, path.stat().st_size


def descriptor(business_date, city, modes=None):
    day = date.fromisoformat(business_date)
    if str(day) != business_date:
        raise ValueError("Expected an ISO business date")
    settings = city_settings(city)
    bounds = (settings["start_date"], settings["end_date"]) if city != "melbourne" else (
        data.get_metadata()["min_date"], data.get_metadata()["max_date"])
    if not bounds[0] <= business_date <= bounds[1]:
        raise ValueError("Date outside city coverage")
    modes = selected_modes(city, modes)
    if city == "melbourne":
        source = data._dataset_path()
        stamps = [_stamp(p) for p in sorted(glob.glob(source))]
        stamps.append((source,))
        geometry = replay.geometry_file()
        if geometry.exists():
            stamps.append(_stamp(geometry))
        if set(modes) & {"tram", "bus"}:
            stamps.append(transit.fingerprint(business_date))
    else:
        stamps = [_stamp(replay.prepared_path(city))]
        if city in replay.BUS_REFERENCE_CITIES and "bus" in modes:
            stamps.append(_stamp(replay.bus_reference_file(city, business_date)))
    revision = hashlib.sha256(repr((FORMAT_VERSION, city, business_date, modes, stamps)).encode()).hexdigest()[:24]
    return {"city": city, "business_date": business_date, "modes": list(modes), "revision": revision,
            "bus_data_loaded": city in replay.BUS_REFERENCE_CITIES and "bus" in modes,
            "url": f"/api/replay/{city}/{business_date}/{revision}.json?" + urlencode({"modes": ",".join(modes)})}


def cache_directory():
    return Path(os.getenv("SUNTRAIN_REPLAY_CACHE", str(replay.ROOT / ".cache/replay-http")))


def trim_cache(directory, keep):
    files = []
    for path in directory.glob("*.json.gz"):
        try:
            stat = path.stat()
            files.append((stat.st_mtime_ns, path, stat.st_size))
        except FileNotFoundError:
            pass
    total = sum(size for _, _, size in files)
    for _, path, size in sorted(files):
        if total <= CACHE_LIMIT:
            break
        if path != keep:
            path.unlink(missing_ok=True)
            total -= size


def compressed_day(info):
    directory = cache_directory()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (info["revision"] + ".json.gz")
    with BUILD_LOCKS[int(info["revision"][:2], 16) % len(BUILD_LOCKS)]:
        with CACHE_LOCK:
            try:
                stream = path.open("rb")
            except FileNotFoundError:
                stream = None
            if stream:
                try:
                    os.utime(path, None)
                except FileNotFoundError:
                    pass  # Another process evicted it; the open descriptor stays valid.
                return stream
        if stream is None:
            payload = replay.get_replay_day(info["business_date"], info["city"],
                include_buses=info["bus_data_loaded"], modes=info["modes"])
            payload = {**payload, "revision": info["revision"], "loaded_modes": info["modes"]}
            # Fast serialization runs once per version, outside the Dash callback.
            encoded = gzip.compress(orjson.dumps(payload), compresslevel=3, mtime=0)
            with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(encoded)
            with CACHE_LOCK:
                temporary.replace(path)
                stream = path.open("rb")
                trim_cache(directory, path)
    return stream


def register_replay_routes(server):
    @server.get("/api/replay/<city>/<business_date>/<revision>.json")
    def replay_download(city, business_date, revision):
        try:
            modes = request.args.get("modes")
            info = descriptor(business_date, city, modes.split(",") if modes else None)
        except (ValueError, KeyError, FileNotFoundError):
            abort(404)
        if revision != info["revision"]:
            abort(409, "Replay version changed. Select the date again to reload.")
        stream = compressed_day(info)
        if request.accept_encodings["gzip"]:
            response = send_file(stream, mimetype="application/json", conditional=False, etag=False, max_age=31536000)
            response.content_length = os.fstat(stream.fileno()).st_size
            response.set_etag(revision + "-gzip", weak=True)
            response.headers["Content-Encoding"] = "gzip"
        else:
            with stream:
                response = server.response_class(gzip.decompress(stream.read()), mimetype="application/json")
            response.set_etag(revision + "-identity", weak=True)
            response.cache_control.public = True
            response.cache_control.max_age = 31536000
        response.cache_control.immutable = True
        response.headers["Vary"] = "Accept-Encoding"
        response.make_conditional(request)
        return response
