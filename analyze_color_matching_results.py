import argparse
import csv
import math
import statistics
from pathlib import Path


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_csv_path(path_text):
    path = Path(path_text)
    if path.is_file():
        return path
    if path.is_dir():
        candidate = path / "color_matching_results.csv"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not find CSV at '{path_text}'. Provide a CSV file or a run folder containing color_matching_results.csv")


def _find_latest_results_csv(search_root=None):
    root = Path(search_root) if search_root else Path("output")
    if not root.exists():
        return None

    candidates = list(root.rglob("color_matching_results.csv"))
    if not candidates:
        return None

    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0]


def _load_experiment_rows(csv_path):
    rows = []
    target_row = None

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            well_raw = str(raw.get("well", "")).strip()
            if not well_raw:
                continue

            if well_raw.lower() == "target":
                target_row = raw
                continue

            well = _to_float(well_raw)
            output = _to_float(raw.get("output"))
            r = _to_float(raw.get("R_volume_ml"))
            y = _to_float(raw.get("Y_volume_ml"))
            b = _to_float(raw.get("B_volume_ml"))

            if well is None or output is None or r is None or y is None or b is None:
                continue

            rows.append(
                {
                    "well": int(well),
                    "output": output,
                    "R": r,
                    "Y": y,
                    "B": b,
                }
            )

    if not rows:
        raise ValueError(f"No valid experiment rows found in {csv_path}")

    rows.sort(key=lambda row: row["well"])
    return rows, target_row


def _longest_consecutive_streak(wells):
    if not wells:
        return 0
    longest = 1
    current = 1
    for prev, curr in zip(wells, wells[1:]):
        if curr == prev + 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _summarize_consistency(close_rows, all_rows):
    total = len(all_rows)
    close_count = len(close_rows)
    close_wells = [row["well"] for row in close_rows]
    streak = _longest_consecutive_streak(close_wells)

    halfway = total / 2.0
    close_first_half = sum(1 for row in close_rows if row["well"] <= halfway)
    close_second_half = close_count - close_first_half

    ratio = close_count / total if total else 0.0

    if close_count == 0:
        label = "No close samples"
    elif close_count <= 2 and streak == 1:
        label = "Only a couple close samples"
    elif streak >= 3 or ratio >= 0.30:
        label = "Consistently close"
    else:
        label = "Mixed consistency"

    return {
        "label": label,
        "close_count": close_count,
        "total_count": total,
        "close_ratio": ratio,
        "close_wells": close_wells,
        "longest_streak": streak,
        "close_first_half": close_first_half,
        "close_second_half": close_second_half,
    }


def _compute_input_distances(rows, target_r, target_y, target_b):
    for row in rows:
        dr = row["R"] - target_r
        dy = row["Y"] - target_y
        db = row["B"] - target_b
        row["input_l1"] = abs(dr) + abs(dy) + abs(db)
        row["input_l2"] = math.sqrt(dr * dr + dy * dy + db * db)
        row["delta_R"] = dr
        row["delta_Y"] = dy
        row["delta_B"] = db


def _print_row(label, row):
    print(
        f"{label}: well={row['well']}, output={row['output']:.6f}, "
        f"recipe(R,Y,B)=({row['R']:.3f}, {row['Y']:.3f}, {row['B']:.3f}), "
        f"input_l1={row['input_l1']:.3f}, input_l2={row['input_l2']:.3f}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Analyze how close a color-matching run got in input and output space."
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=str,
        default=None,
        help="Path to color_matching_results.csv or its run folder (optional). If omitted, uses latest output/*/color_matching_results.csv",
    )
    parser.add_argument("--target-r", type=float, default=0.40, help="Target R fraction (default: 0.40)")
    parser.add_argument("--target-y", type=float, default=0.55, help="Target Y fraction (default: 0.55)")
    parser.add_argument("--target-b", type=float, default=0.05, help="Target B fraction (default: 0.05)")
    parser.add_argument(
        "--close-output-threshold",
        type=float,
        default=None,
        help="Absolute output threshold to define 'close' samples. If omitted, uses min + margin*(max-min).",
    )
    parser.add_argument(
        "--close-output-margin",
        type=float,
        default=0.10,
        help="When absolute threshold is omitted, 'close' = output <= min + margin*(max-min). Default: 0.10",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Number of top output wells to print (default: 5)")

    args = parser.parse_args()

    if args.path:
        csv_path = _resolve_csv_path(args.path)
    else:
        csv_path = _find_latest_results_csv("output")
        if csv_path is None:
            raise FileNotFoundError(
                "No color_matching_results.csv found under 'output'. "
                "Pass a path explicitly, for example: "
                "python analyze_color_matching_results.py output/color_matching_workflow/20260320_081432_LAB"
            )
    rows, _target_row = _load_experiment_rows(csv_path)
    _compute_input_distances(rows, args.target_r, args.target_y, args.target_b)

    outputs = [row["output"] for row in rows]
    best_output_row = min(rows, key=lambda row: row["output"])
    closest_input_row = min(rows, key=lambda row: row["input_l2"])

    out_min = min(outputs)
    out_max = max(outputs)
    out_mean = statistics.mean(outputs)
    out_median = statistics.median(outputs)
    out_std = statistics.pstdev(outputs) if len(outputs) > 1 else 0.0

    if args.close_output_threshold is None:
        close_threshold = out_min + args.close_output_margin * (out_max - out_min)
        threshold_source = f"auto (min + {args.close_output_margin:.3f}*(max-min))"
    else:
        close_threshold = args.close_output_threshold
        threshold_source = "manual"

    close_rows = [row for row in rows if row["output"] <= close_threshold]
    consistency = _summarize_consistency(close_rows, rows)

    print(f"CSV: {csv_path}")
    print(f"Target recipe (R,Y,B): ({args.target_r:.3f}, {args.target_y:.3f}, {args.target_b:.3f})")
    print()

    print("=== Output-space closeness (to 0) ===")
    print(f"best_output: {out_min:.6f}")
    print(f"max_output: {out_max:.6f}")
    print(f"mean_output: {out_mean:.6f}")
    print(f"median_output: {out_median:.6f}")
    print(f"std_output: {out_std:.6f}")
    print()

    print("=== Input-space closeness (to target recipe) ===")
    _print_row("Best output well", best_output_row)
    _print_row("Closest recipe well", closest_input_row)
    print(
        "Best output deltas from target: "
        f"dR={best_output_row['delta_R']:+.3f}, dY={best_output_row['delta_Y']:+.3f}, dB={best_output_row['delta_B']:+.3f}"
    )
    print()

    print("=== Close-sample consistency ===")
    print(f"close_threshold: {close_threshold:.6f} ({threshold_source})")
    print(f"close_samples: {consistency['close_count']}/{consistency['total_count']} ({100.0 * consistency['close_ratio']:.1f}%)")
    print(f"close_wells: {consistency['close_wells']}")
    print(f"longest_consecutive_close_streak: {consistency['longest_streak']}")
    print(
        "close_distribution: "
        f"first_half={consistency['close_first_half']}, second_half={consistency['close_second_half']}"
    )
    print(f"consistency_assessment: {consistency['label']}")
    print()

    print("=== Top output wells ===")
    top_k = max(1, args.top_k)
    for index, row in enumerate(sorted(rows, key=lambda r: r["output"])[:top_k], start=1):
        print(
            f"{index:>2}. well={row['well']:>2}, output={row['output']:.6f}, "
            f"recipe=({row['R']:.3f}, {row['Y']:.3f}, {row['B']:.3f}), input_l2={row['input_l2']:.3f}"
        )


if __name__ == "__main__":
    main()
