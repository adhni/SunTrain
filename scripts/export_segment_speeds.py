from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.data import (
    classify_segment_speed_confidence,
    get_filter_state,
    get_metadata,
    get_segment_speed_pairs,
)


OUTPUT_ROOT = ROOT / "data/processed/segment_speeds"
BY_LINE_ROOT = OUTPUT_ROOT / "by_line"
OUTPUT_STEM = "segment_speeds_confidence"


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"


def write_band_files(frame: pd.DataFrame, output_dir: Path, stem_prefix: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / f"{stem_prefix}_{OUTPUT_STEM}_all.csv", index=False)
    for confidence_band in ("high", "medium", "low"):
        subset = frame[frame["confidence_band"] == confidence_band].copy()
        subset.to_csv(output_dir / f"{stem_prefix}_{OUTPUT_STEM}_{confidence_band}.csv", index=False)


def export_line(line_name: str, start_date: str, end_date: str) -> pd.DataFrame:
    filters = get_filter_state(
        start_date,
        end_date,
        [],
        [line_name],
        [],
        ["U", "D"],
        [],
        [],
    )
    segment_pairs = get_segment_speed_pairs(filters)
    labeled = classify_segment_speed_confidence(segment_pairs)
    labeled.insert(0, "line_slug", slugify(line_name))
    return labeled


def main() -> None:
    metadata = get_metadata()
    start_date = metadata["min_date"]
    end_date = metadata["max_date"]

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    BY_LINE_ROOT.mkdir(parents=True, exist_ok=True)

    all_lines: list[pd.DataFrame] = []
    for line_name in metadata["lines"]:
        labeled = export_line(line_name, start_date, end_date)
        all_lines.append(labeled)

        line_slug = slugify(line_name)
        write_band_files(labeled, BY_LINE_ROOT / line_slug, line_slug)

    combined = pd.concat(all_lines, ignore_index=True) if all_lines else pd.DataFrame()
    write_band_files(combined, OUTPUT_ROOT, "all_lines")

    counts = combined["confidence_band"].value_counts().to_dict() if not combined.empty else {}
    print(f"Saved all-line segment speed confidence outputs to {OUTPUT_ROOT}")
    print(f"Counts by band: {counts}")


if __name__ == "__main__":
    main()
