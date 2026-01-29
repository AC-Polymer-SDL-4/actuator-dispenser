import argparse
import os
import time
from pathlib import Path

import pandas as pd


def combine_csvs(input_paths, outdir=None):
    frames = []
    for p in input_paths:
        df = pd.read_csv(p)
        # Basic sanity: required columns
        required = {"target_time_s", "dispensed_mass_g"}
        if not required.issubset(df.columns):
            raise ValueError(f"Missing required columns in {p}: {required - set(df.columns)}")
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    # Sort by time then replicate to keep tidy ordering
    sort_cols = ["target_time_s"] + (["replicate"] if "replicate" in combined.columns else [])
    combined = combined.sort_values(sort_cols).reset_index(drop=True)

    # Determine output directory
    if outdir is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        outdir = Path("output/calibration") / f"combined_six_times_{ts}"
    else:
        outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    out_csv = outdir / "calibration_measurements_net.csv"
    combined.to_csv(out_csv, index=False)
    return str(out_csv)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Combine multiple time-based net calibration CSVs into one.")
    parser.add_argument("inputs", nargs="+", help="Paths to calibration_measurements_net.csv files to combine")
    parser.add_argument("--outdir", default=None, help="Output directory for the combined CSV")
    args = parser.parse_args()

    out_csv = combine_csvs(args.inputs, args.outdir)
    print(f"Wrote combined CSV -> {out_csv}")
