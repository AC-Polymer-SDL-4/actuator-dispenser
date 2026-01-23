import os
import sys
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def find_latest_csv(base_dir=os.path.join("output", "calibration")):
    paths = sorted(glob.glob(os.path.join(base_dir, "time_volume_*", "calibration_measurements.csv")))
    return paths[-1] if paths else None


def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    # Filter to time-based rows with measured volumes
    df_time = df[(df["calibration_type"] == "time") & df["target_time_s"].notna() & df["measured_volume_ml"].notna()].copy()
    df_time["target_time_s"] = df_time["target_time_s"].astype(float)
    df_time["measured_volume_ml"] = df_time["measured_volume_ml"].astype(float)
    return df_time


def fit_linear(df_time: pd.DataFrame):
    t = df_time["target_time_s"].values
    v = df_time["measured_volume_ml"].values
    k, b = np.polyfit(t, v, 1)
    v_pred = k * t + b
    ss_res = ((v - v_pred) ** 2).sum()
    ss_tot = ((v - v.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    slope_seconds_per_ml = 1.0 / k if k != 0 else np.nan
    return k, b, r2, v_pred, slope_seconds_per_ml


def plot_time_vs_volume(df_time, k, b, out_dir):
    plt.figure(figsize=(7, 5))
    plt.scatter(df_time["target_time_s"], df_time["measured_volume_ml"], alpha=0.8, label="Measured")
    t_line = np.linspace(df_time["target_time_s"].min(), df_time["target_time_s"].max(), 100)
    plt.plot(t_line, k * t_line + b, color="orange", label="Fit")
    plt.xlabel("Time (s)")
    plt.ylabel("Volume (mL)")
    plt.title("Time → Volume Calibration")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "time_vs_volume_fit.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_residuals(df_time, k, b, out_dir):
    residuals = df_time["measured_volume_ml"] - (k * df_time["target_time_s"] + b)
    plt.figure(figsize=(7, 4))
    plt.scatter(df_time["target_time_s"], residuals, alpha=0.8)
    plt.axhline(0, color="black", linewidth=1)
    plt.xlabel("Time (s)")
    plt.ylabel("Residual (mL)")
    plt.title("Residuals vs Time")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "residuals_vs_time.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def plot_box_per_time(df_time, out_dir):
    # Round/format time to bucket by unique targets
    grouped = df_time.copy()
    grouped["time_label"] = grouped["target_time_s"].round(3).astype(str)
    # Order by numeric time
    order = sorted(grouped["time_label"].unique(), key=lambda s: float(s))
    data = [grouped[grouped["time_label"] == t]["measured_volume_ml"].values for t in order]
    plt.figure(figsize=(max(7, len(order) * 0.6), 4))
    plt.boxplot(data, labels=order, showmeans=True)
    plt.xlabel("Time (s)")
    plt.ylabel("Volume (mL)")
    plt.title("Per-time Dispense Variability")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "per_time_variability_boxplot.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def main():
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = find_latest_csv()
    if not csv_path or not os.path.exists(csv_path):
        print("No calibration CSV found. Provide path explicitly or run tests/calibration/volume_calibration.py first.")
        sys.exit(1)

    out_dir = os.path.dirname(csv_path)
    df_time = load_data(csv_path)
    if df_time.empty:
        print("No time-based calibration rows with measured volumes found.")
        sys.exit(1)

    k, b, r2, v_pred, slope_seconds_per_ml = fit_linear(df_time)

    summary_path = os.path.join(out_dir, "calibration_fit_summary.txt")
    with open(summary_path, "w") as f:
        f.write(f"Fit: volume = k * time + b\n")
        f.write(f"k (mL/s) = {k:.4f}\n")
        f.write(f"b (mL)   = {b:.4f}\n")
        f.write(f"R^2       = {r2:.4f}\n")
        f.write(f"Estimated SLOPE (seconds/mL) = {slope_seconds_per_ml:.4f}\n")
        f.write(f"N = {len(df_time)} rows\n")
    print(f"Saved fit summary → {summary_path}")

    p1 = plot_time_vs_volume(df_time, k, b, out_dir)
    p2 = plot_residuals(df_time, k, b, out_dir)
    p3 = plot_box_per_time(df_time, out_dir)
    print("Saved plots:")
    print(" -", p1)
    print(" -", p2)
    print(" -", p3)


if __name__ == "__main__":
    main()
