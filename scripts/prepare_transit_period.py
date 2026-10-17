"""Download the pinned PTV snapshots and prepare the five-week transit replay."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dashboard.transit import PERIOD_START, PERIOD_END, REFERENCE
from scripts.prepare_transit_replay import prepare

ARCHIVES = [
    "https://files.mobilitydatabase.org/mdb-657/mdb-657-202405270004/mdb-657-202405270004.zip",
    "https://files.mobilitydatabase.org/mdb-657/mdb-657-202406030013/mdb-657-202406030013.zip",
    "https://files.mobilitydatabase.org/mdb-657/mdb-657-202406071511/mdb-657-202406071511.zip",
    "https://files.mobilitydatabase.org/mdb-657/mdb-657-202406170018/mdb-657-202406170018.zip",
    "https://files.mobilitydatabase.org/mdb-657/mdb-657-202406240001/mdb-657-202406240001.zip",
]


def snapshot_date(url):
    stamp = re.search(r"mdb-657-(\d{12})", url).group(1)
    return datetime.strptime(stamp, "%Y%m%d%H%M").replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Australia/Melbourne")).date()


def period_chunks(urls, first, last):
    sources = sorted((snapshot_date(url), url) for url in urls)
    chunks = []
    for i, (captured, url) in enumerate(sources):
        start = max(first, captured)
        end = min(last, sources[i + 1][0] - timedelta(days=1) if i + 1 < len(sources) else last)
        if start <= end:
            chunks.append({"start_date": start.isoformat(), "end_date": end.isoformat(),
                           "source_date": captured.isoformat(), "source_url": url, "file": f"{captured.isoformat()}.json.gz"})
    if not chunks or chunks[0]["start_date"] != first.isoformat() or chunks[-1]["end_date"] != last.isoformat():
        raise ValueError("Snapshots do not cover the requested period")
    return chunks


def download_archive(url, cache):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / url.rsplit("/", 1)[-1]
    if path.exists():
        with ZipFile(path) as archive:
            if {"3/google_transit.zip", "4/google_transit.zip"}.issubset(archive.namelist()):
                return path
    raw, slim = path.with_suffix(".download"), path.with_suffix(".tmp")
    print(f"Downloading {path.name}", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=90) as response, raw.open("wb") as stream:
            while block := response.read(1024 * 1024):
                stream.write(block)
        # Keep only the two compressed branches needed for replay in the local cache.
        with ZipFile(raw) as source, ZipFile(slim, "w") as target:
            for branch in ("3", "4"):
                name = f"{branch}/google_transit.zip"
                target.writestr(name, source.read(name))
        slim.replace(path)
    finally:
        raw.unlink(missing_ok=True)
        slim.unlink(missing_ok=True)
    print(f"Cached {path.name} ({path.stat().st_size / 1e6:.0f} MB)", flush=True)
    return path


def build(output=REFERENCE, cache=ROOT / ".cache/transit-archives"):
    first, last = date.fromisoformat(PERIOD_START), date.fromisoformat(PERIOD_END)
    chunks = period_chunks(ARCHIVES, first, last)
    geometry_cache, path_cache = {}, {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        downloads = {c["source_url"]: pool.submit(download_archive, c["source_url"], cache) for c in chunks}
        for chunk in chunks:
            archive = downloads[chunk["source_url"]].result()
            destination = output.parent / chunk["file"]
            print(f"Preparing {chunk['start_date']} through {chunk['end_date']}", flush=True)
            prepare(archive, destination, start_date=chunk["start_date"], end_date=chunk["end_date"],
                    source_date=chunk["source_date"], source_url=chunk["source_url"],
                    geometry_cache=geometry_cache, path_cache=path_cache)
    metadata = {"start_date": PERIOD_START, "end_date": PERIOD_END, "source": "PTV GTFS Schedule",
                "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/"}
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps({"metadata": metadata, "chunks": chunks}, indent=2) + "\n")
    temporary.replace(output)
    print(f"Prepared {(last - first).days + 1} days across {len(chunks)} snapshot bundles: {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REFERENCE)
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache/transit-archives")
    args = parser.parse_args()
    build(args.output, args.cache)
