# Local source-cache cleanup — 25 October 2026

The seven raw OSM downloads listed below were removed at the user's request to recover local disk space. Prepared app data under `data/`, the other caches, and Google Flights captures were retained. These downloads are geometry-preparation inputs, not files the normal replay needs.

This cleanup supersedes earlier expansion-note statements that these seven raw files remain cached. After deletion, all seven paths were absent and SHA-256 checks confirmed that all 372 retained files under `data/` and the selected prepared geometry caches were unchanged. Local free space measured approximately 4.0 GiB.

## Restore a deleted source

Run from the repository root. Each record below gives the original path, exact byte length, SHA-256 measured immediately before deletion, original source URL, and the preparation script that consumes it.

Download to a temporary filename, verify its SHA-256 against this record, then move it to the original path. For example:

```bash
mkdir -p .cache/java
curl --fail --location 'https://download.geofabrik.de/asia/indonesia/java-261018.osm.pbf' --output .cache/java/java-261018.osm.pbf.download
shasum -a 256 .cache/java/java-261018.osm.pbf.download
# Compare with the Java SHA-256 below; only after it matches:
mv .cache/java/java-261018.osm.pbf.download .cache/java/java-261018.osm.pbf
```

The URLs are recorded provenance, not a promise that the original bytes remain available; they were not redownloaded during cleanup. URLs containing `latest`, and the BBBike London URL, roll forward. A future download may differ. For an identical geometry rebuild, obtain the original snapshot matching the recorded checksum from the provider's archive or an existing backup. If unavailable, use the retained prepared geometry; deliberately updating source pins and revalidating geometry is a separate change. Do not bypass hash checks merely to accept a current download.

Java's URL names 18 October 2026; Kyushu's names 20 October 2026. London is pinned to 11 October 2026 in its preparation script. Other provenance dates remain in the retained prepared geometry metadata and expansion notes. See `JAVA_EXPANSION_NOTES.md`, `LONDON_EXPANSION_NOTES.md`, `THAILAND_EXPANSION_NOTES.md`, `TAIWAN_EXPANSION_NOTES.md`, `JAPAN_EXPANSION_NOTES.md`, `SOUTH_KOREA_EXPANSION_NOTES.md` and `MALAYSIA_EXPANSION_NOTES.md` for rebuilding and preparation-only dependencies.

## Deleted-file manifest

```json
[
  {
    "path": ".cache/java/java-261018.osm.pbf",
    "bytes": 898265371,
    "allocated_bytes": 898269184,
    "sha256": "31fb514159bf252515a95de0b4e47d92f00c1b34d1940477cf5c1de3dcf0d93a",
    "source_url": "https://download.geofabrik.de/asia/indonesia/java-261018.osm.pbf",
    "geometry_builder": "scripts/prepare_java_geometry.py"
  },
  {
    "path": ".cache/london-audit/London.osm.gz",
    "bytes": 406645358,
    "allocated_bytes": 406646784,
    "sha256": "51a9f096bcd6da2c6435cc2dc8ec663f142ea5649498fb6bf1ac65fd858a7b9e",
    "source_url": "https://download.bbbike.org/osm/bbbike/London/London.osm.gz",
    "geometry_builder": "scripts/prepare_london_geometry.py"
  },
  {
    "path": ".cache/thailand/srt/thailand-latest.osm.pbf",
    "bytes": 329048640,
    "allocated_bytes": 329052160,
    "sha256": "68a665cc5f618f63c6afe5cde011d783c3838ea27b1ebaceb857946626ded939",
    "source_url": "https://download.geofabrik.de/asia/thailand-latest.osm.pbf",
    "geometry_builder": "scripts/prepare_thailand_srt.py"
  },
  {
    "path": ".cache/taiwan/taiwan.osm.pbf",
    "bytes": 327725027,
    "allocated_bytes": 327725056,
    "sha256": "c2a077d7e9379ebea58062c6361a073017cc2add206104ed3458e646ed31becc",
    "source_url": "https://download.geofabrik.de/asia/taiwan-latest.osm.pbf",
    "geometry_builder": "scripts/prepare_taiwan_geometry.py"
  },
  {
    "path": ".cache/japan/kyushu-261020.osm.pbf",
    "bytes": 316366928,
    "allocated_bytes": 316370944,
    "sha256": "c56764fbe77b66c6dddadc62ebe8f8ea9bb9a0cff8a00f63507c3e731ed88423",
    "source_url": "https://download.geofabrik.de/asia/japan/kyushu-261020.osm.pbf",
    "geometry_builder": "scripts/prepare_japan_kyushu_geometry.py"
  },
  {
    "path": ".cache/seoul/south-korea.osm.pbf",
    "bytes": 289756580,
    "allocated_bytes": 289759232,
    "sha256": "e683fcb5abf964144d3ff34d1255bb5350aa632f03388d5f07ea122a462f4d10",
    "source_url": "https://download.geofabrik.de/asia/south-korea-latest.osm.pbf",
    "geometry_builder": "scripts/prepare_seoul_geometry.py; scripts/prepare_korea_geometry.py"
  },
  {
    "path": ".cache/kuala-lumpur/malaysia.osm.pbf",
    "bytes": 261558883,
    "allocated_bytes": 261562368,
    "sha256": "1abfb77758d28dea24ffa4d8ce38527ab7bcdaa0ebacfe074b387cac49bde03a",
    "source_url": "https://download.openstreetmap.fr/extracts/asia/malaysia-latest.osm.pbf",
    "geometry_builder": "scripts/prepare_kuala_lumpur_replay.py (compile_geometry); scripts/prepare_malaysia_airport.py"
  }
]
```

Total removed: 2829366787 bytes (2.635 GiB logical file size).

## Disposable cache cleanup — 25 October 2026

Removed the additional file groups selected by the user. Files were checked for open handles before removal, and files changing since inventory were excluded.

| Group | Files removed | Allocated size before removal |
|---|---:|---:|
| `.cache/replay-http` | 124 | 150.24 MiB |
| `.cache/indonesia-http` | 29 | 30.70 MiB |
| `.cache/flights-http` | 7 | 8.24 MiB |
| `.cache/pycache` | 1253 | 20.86 MiB |
| `.pytest_cache` | 6 | 0.10 MiB |
| `.cache/replay-weekday-memory.json` | 1 | 34.22 MiB |
| `.cache/london-audit/bods-london.zip.part` | 1 | 149.72 MiB |
| `.cache/**/*.png` | 237 | 140.90 MiB |
| `.cache/**/*.log` | 463 | 2.80 MiB |

Total: **2121 files, 537.79 MiB** of allocated file storage. Skipped: 0 files. Free disk space after cleanup: approximately 4.53 GiB. SHA-256 verification confirmed all 369 retained app-data and prepared-geometry files unchanged, excluding macOS Finder `.DS_Store` metadata.

Replay HTTP responses regenerate on demand. Python and pytest caches regenerate when their tools run. Screenshots, logs and the benchmark JSON are discarded development artifacts; rerun the corresponding checks to produce new ones. The unfinished London download was discarded; see `LONDON_EXPANSION_NOTES.md` for the retained source and preparation workflow. No original completed source archives, Google Flights captures or tool environments were removed in this second cleanup.
