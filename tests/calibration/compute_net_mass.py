import os
import sys
import argparse
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

"""
Compute per-dispense net mass (and volume) from cumulative mass entries.
Supports time-mode calibration with plate resets after N groups of times.

Usage:
  python tests/calibration/compute_net_mass.py --input <calibration_measurements.csv> \
      --groups-per-plate 6 --tare 43.706 --out <optional_output_csv>

Notes:
- If --tare is omitted, the baseline per plate defaults to the first measured_mass_g in that plate.
- If the CSV includes 'plate_index' (added by the runner), resets use it directly.
- Otherwise, plate_index is inferred from time_index and --groups-per-plate.
- Negative first entries (due to tare mismatch) are clamped to positive magnitude for that first row only.
"""

def parse_args():
    ap = argparse.ArgumentParser(description="Compute net dispensed mass from cumulative measurements")
    ap.add_argument("--input", required=True, help="Path to calibration_measurements.csv or renamed CSV")
    ap.add_argument("--out", default=None, help="Output CSV path (default: alongside input with _net suffix)")
    ap.add_argument("--groups-per-plate", type=int, default=6, help="Number of time groups per plate (24 wells / 4 reps = 6)")
    ap.add_argument("--tare", type=float, default=None, help="Rack/plate tare mass in grams (applied per plate if provided)")
    return ap.parse_args()


def quant4(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def main():
    args = parse_args()
    in_csv = args.input
    out_csv = args.out or os.path.splitext(in_csv)[0] + "_net.csv"

    df = pd.read_csv(in_csv)
    # Only process time-mode rows with cumulative measured_mass_g present
    mask = (df.get("calibration_type") == "time") & df.get("measured_mass_g").notna()
    df_time = df[mask].copy()
    if df_time.empty:
        print("No time-mode rows with measured_mass_g found.")
        return 1

    # Ensure required columns exist
    for col in ["time_index", "well_index", "timestamp"]:
        if col not in df_time.columns:
            df_time[col] = None

    # Determine plate_index: prefer explicit column; else infer from time_index
    if "plate_index" not in df_time.columns or df_time["plate_index"].isna().all():
        if "time_index" in df_time.columns and df_time["time_index"].notna().any():
            df_time["plate_index"] = (df_time["time_index"].fillna(0).astype(int) // args.groups_per_plate).astype(int)
        else:
            # Fallback: single plate
            df_time["plate_index"] = 0

    # Build per-plate tare map from any meta rows (if present)
    tare_map = {}
    if "calibration_type" in df.columns and (df["calibration_type"] == "meta").any():
        metas = df[df["calibration_type"] == "meta"].copy()
        if "plate_index" in metas.columns and "measured_mass_g" in metas.columns:
            for _, r in metas.iterrows():
                try:
                    pidx = int(r.get("plate_index")) if pd.notna(r.get("plate_index")) else None
                except Exception:
                    pidx = None
                if pidx is not None and pd.notna(r.get("measured_mass_g")):
                    tare_map[pidx] = float(r.get("measured_mass_g"))

    # Sort deterministically within each plate
    df_time = df_time.sort_values(["plate_index", "well_index", "timestamp"], ascending=[True, True, True])

    # Compute per-plate net differences
    dispensed = []
    for plate_idx, g in df_time.groupby("plate_index", sort=True):
        plate_tare = tare_map.get(plate_idx, args.tare)
        prev_mass = plate_tare if plate_tare is not None else float(g["measured_mass_g"].iloc[0])
        for j, m in enumerate(g["measured_mass_g"].tolist()):
            diff = m - prev_mass
            if j == 0 and diff < 0:
                # Clamp first row to positive magnitude if tare slightly exceeds first reading
                diff = abs(diff)
            dispensed.append(quant4(diff))
            prev_mass = m

    df_time["dispensed_mass_g"] = dispensed
    df_time["dispensed_volume_ml"] = df_time["dispensed_mass_g"]  # water assumption

    # Reorder/keep useful columns
    cols = [
        "calibration_type","plate_index","time_index","replicate","well_index","target_time_s","target_volume_ml",
        "dispensed_mass_g","dispensed_volume_ml","measured_mass_g","air_time_s","buffer_time_s","speed","timestamp"
    ]
    for c in cols:
        if c not in df_time.columns:
            df_time[c] = None
    df_time = df_time[cols]

    df_time.to_csv(out_csv, index=False)
    print("Wrote:", out_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
