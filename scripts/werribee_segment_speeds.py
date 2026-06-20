from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.data import classify_segment_speed_confidence, get_filter_state, get_segment_speed_pairs


OUTPUT_DIR = ROOT / "data/processed/werribee"
OUTPUT_STEM = "werribee_segment_speeds_confidence"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filters = get_filter_state(
        "2023-07-10",
        "2024-06-30",
        [],
        ["Werribee"],
        [],
        ["U", "D"],
        [],
        [],
    )

    segment_pairs = get_segment_speed_pairs(filters)
    labeled = classify_segment_speed_confidence(segment_pairs)

    labeled.to_csv(OUTPUT_DIR / f"{OUTPUT_STEM}_all.csv", index=False)
    for confidence_band in ("high", "medium", "low"):
        subset = labeled[labeled["confidence_band"] == confidence_band].copy()
        subset.to_csv(OUTPUT_DIR / f"{OUTPUT_STEM}_{confidence_band}.csv", index=False)

    counts = labeled["confidence_band"].value_counts().to_dict()
    print(f"Saved segment speed confidence outputs to {OUTPUT_DIR}")
    print(f"Counts by band: {counts}")


if __name__ == "__main__":
    main()
