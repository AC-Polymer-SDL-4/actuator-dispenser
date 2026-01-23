import os
import sys
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def find_latest_net_csv(base_dir=os.path.join("output", "calibration")):
    # Look for any mass_calibration_data_*_net.csv under time_volume_* folders
    pattern = os.path.join(base_dir, "time_volume_*", "mass_calibration_data_*_net.csv")
    paths = sorted(glob.glob(pattern))
    return paths[-1] if paths else None


def load_data(csv_path: str):
    df = pd.read_csv(csv_path)
    # Filter to time-based rows with computed net mass
    df_time = df[(df["calibration_type"] == "time") & df["target_time_s"].notna() & df["dispensed_mass_g"].notna()].copy()
    df_time["target_time_s"] = df_time["target_time_s"].astype(float)
    df_time["dispensed_mass_g"] = df_time["dispensed_mass_g"].astype(float)
    return df_time


def fit_linear(df_time: pd.DataFrame):
    t = df_time["target_time_s"].values
    m = df_time["dispensed_mass_g"].values
    # Fit mass = k * time + b
    k, b = np.polyfit(t, m, 1)
    m_pred = k * t + b
    ss_res = ((m - m_pred) ** 2).sum()
    ss_tot = ((m - m.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    # Helpful conversion: seconds per gram (s/g)
    seconds_per_gram = 1.0 / k if k != 0 else np.nan
    return k, b, r2, m_pred, seconds_per_gram


def plot_time_vs_net_mass(df_time, k, b, out_dir):
    plt.figure(figsize=(7, 5))
    plt.scatter(df_time["target_time_s"], df_time["dispensed_mass_g"], alpha=0.8, label="Net mass per dispense")
    t_line = np.linspace(df_time["target_time_s"].min(), df_time["target_time_s"].max(), 100)
    plt.plot(t_line, k * t_line + b, color="orange", label="Linear fit")
    plt.xlabel("Time (s)")
    plt.ylabel("Net mass (g)")
    plt.title("Time → Net Mass Calibration")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    path = os.path.join(out_dir, "time_to_net_mass_fit.png")
    plt.savefig(path, dpi=150)
    plt.close()
    return path


def main():
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = find_latest_net_csv()
    if not csv_path or not os.path.exists(csv_path):
        print("No net calibration CSV found. Provide path explicitly or run net conversion first.")
        sys.exit(1)

    out_dir = os.path.dirname(csv_path)
    df_time = load_data(csv_path)
    if df_time.empty:
        print("No time-based net mass rows found.")
        sys.exit(1)

    k, b, r2, m_pred, seconds_per_gram = fit_linear(df_time)

    summary_path = os.path.join(out_dir, "time_net_mass_fit_summary.txt")
    with open(summary_path, "w") as f:
        f.write("Fit: mass = k * time + b\n")
        f.write(f"k (g/s) = {k:.4f}\n")
        f.write(f"b (g)   = {b:.4f}\n")
        f.write(f"R^2      = {r2:.4f}\n")
        f.write(f"Seconds per gram (s/g) = {seconds_per_gram:.4f}\n")
        f.write(f"N = {len(df_time)} rows\n")
    print(f"Saved fit summary -> {summary_path}")

    p1 = plot_time_vs_net_mass(df_time, k, b, out_dir)
    print("Saved plot:")
    print(" -", p1)


if __name__ == "__main__":
    main()
