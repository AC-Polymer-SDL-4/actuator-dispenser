import os
import sys
import glob
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def find_latest_csv(base_dir=os.path.join("output", "calibration"), mode="volume_validation_dispenser"):
    pattern = os.path.join(base_dir, f"{mode}_*", "calibration_measurements_net.csv")
    paths = sorted(glob.glob(pattern))
    return paths[-1] if paths else None


def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    df = df[df["dispensed_volume_ml"].notna()].copy()
    df["target_volume_ml"] = df["target_volume_ml"].astype(float)
    df["dispensed_volume_ml"] = df["dispensed_volume_ml"].astype(float)
    return df


def summarize_stats(df: pd.DataFrame):
    grp = df.groupby("target_volume_ml")["dispensed_volume_ml"]
    stats = grp.agg(mean_vol_ml="mean", std_vol_ml="std", n="count").reset_index()
    stats["cv_percent"] = (stats["std_vol_ml"] / stats["mean_vol_ml"]) * 100.0
    return stats


def fit_measured_vs_target(df: pd.DataFrame):
    x = df["target_volume_ml"].values
    y = df["dispensed_volume_ml"].values
    k, b = np.polyfit(x, y, 1)
    y_pred = k * x + b
    ss_res = ((y - y_pred) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return k, b, r2


def plot_measured_vs_target(df: pd.DataFrame, stats: pd.DataFrame, out_dir: str, label: str | None = None):
    plt.figure(figsize=(7, 5))
    # Scatter all replicates
    plt.scatter(df["target_volume_ml"], df["dispensed_volume_ml"], alpha=0.7, label="Replicates")
    # Plot 1:1 line
    x_min, x_max = df["target_volume_ml"].min(), df["target_volume_ml"].max()
    x_line = np.linspace(x_min, x_max, 100)
    plt.plot(x_line, x_line, color="black", linestyle="--", label="Ideal (y=x)")
    # Error bars per target (mean ± std)
    plt.errorbar(stats["target_volume_ml"], stats["mean_vol_ml"], yerr=stats["std_vol_ml"], fmt="o", color="orange", label="Mean ± SD")
    plt.xlabel("Target Volume (mL)")
    plt.ylabel("Measured Volume (mL)")
    title = "Measured vs Target Volume"
    if label:
        title += f" — {label}"
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "measured_vs_target_volume.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def main():
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        label = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        csv_path = find_latest_csv()
        label = None
    if not csv_path or not os.path.exists(csv_path):
        print("No volume validation CSV found. Provide path explicitly or run tests/calibration/volume_validation.py first.")
        sys.exit(1)

    out_dir = os.path.dirname(csv_path)
    df = load_data(csv_path)
    if df.empty:
        print("No rows with dispensed_volume_ml found.")
        sys.exit(1)

    stats = summarize_stats(df)
    stats_path = os.path.join(out_dir, "volume_validation_stats.csv")
    stats.to_csv(stats_path, index=False)

    k, b, r2 = fit_measured_vs_target(df)
    summary_path = os.path.join(out_dir, "volume_validation_fit_summary.txt")
    with open(summary_path, "w") as f:
        f.write("Fit: measured = k * target + b\n")
        f.write(f"k (unitless gain) = {k:.4f}\n")
        f.write(f"b (mL)            = {b:.4f}\n")
        f.write(f"R^2               = {r2:.4f}\n")
        f.write(f"N rows            = {len(df)}\n")

    plot_path = plot_measured_vs_target(df, stats, out_dir, label)
    print("Saved:")
    print(" -", plot_path)
    print(" -", stats_path)
    print(" -", summary_path)


if __name__ == "__main__":
    main()
