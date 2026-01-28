import os
import sys
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def find_latest_net_csv(base_dir=os.path.join("output", "calibration")):
    # Look for any calibration_measurements_*_net.csv under time_volume_* folders
    pattern = os.path.join(base_dir, "time_volume_*", "calibration_measurements*_net.csv")
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


def plot_time_vs_net_mass(df_time, k, b, r2, out_dir):
    plt.figure(figsize=(7, 5))
    # Raw replicates
    plt.scatter(df_time["target_time_s"], df_time["dispensed_mass_g"], alpha=0.5, label="Replicates")

    # Per-time uncertainty (±1 SD across replicates)
    g = df_time.copy()
    g["time_label"] = g["target_time_s"].round(3)
    grouped = g.groupby("time_label")
    t_centers = grouped["target_time_s"].mean().values
    means = grouped["dispensed_mass_g"].mean().values
    stds = grouped["dispensed_mass_g"].std(ddof=1).fillna(0).values
    if len(t_centers) > 0:
        plt.errorbar(t_centers, means, yerr=stds, fmt="o", color="tab:blue", ecolor="tab:blue",
                     elinewidth=1, capsize=3, label="Mean ± 1 SD")
    t_line = np.linspace(df_time["target_time_s"].min(), df_time["target_time_s"].max(), 100)
    plt.plot(t_line, k * t_line + b, color="orange", label="Linear fit")
    plt.xlabel("Time (s)")
    plt.ylabel("Net mass (g)")
    plt.title("Time → Net Mass Calibration")
    plt.legend()
    plt.grid(True, alpha=0.3)
    # Annotate fit equation and R^2 on the plot
    ax = plt.gca()
    text = f"y = {k:.4f}x + {b:.4f}\nR^2 = {r2:.4f}"
    ax.text(0.05, 0.95, text, transform=ax.transAxes, va="top", ha="left",
            bbox=dict(facecolor="white", edgecolor="gray", alpha=0.8, boxstyle="round,pad=0.3"), fontsize=9)
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

    # Compute per-time stats (mean, std, N) and write CSV
    df_stats = (
        df_time.assign(time_label=df_time["target_time_s"].round(3))
        .groupby("time_label")
        .agg(
            target_time_s=("target_time_s", "mean"),
            mean_mass_g=("dispensed_mass_g", "mean"),
            std_mass_g=("dispensed_mass_g", lambda x: x.std(ddof=1)),
            n=("dispensed_mass_g", "size"),
        )
        .reset_index(drop=True)
    )
    stats_csv = os.path.join(out_dir, "time_net_mass_stats.csv")
    df_stats.to_csv(stats_csv, index=False)

    summary_path = os.path.join(out_dir, "time_net_mass_fit_summary.txt")
    with open(summary_path, "w") as f:
        f.write("Fit: mass = k * time + b\n")
        f.write(f"k (g/s) = {k:.4f}\n")
        f.write(f"b (g)   = {b:.4f}\n")
        f.write(f"R^2      = {r2:.4f}\n")
        f.write(f"Seconds per gram (s/g) = {seconds_per_gram:.4f}\n")
        f.write(f"N = {len(df_time)} rows\n")
        f.write("\nPer-time stats (mean ± std, n):\n")
        for _, r in df_stats.iterrows():
            f.write(f"t={r['target_time_s']:.3f}s: mean={r['mean_mass_g']:.4f} g, std={0.0 if pd.isna(r['std_mass_g']) else r['std_mass_g']:.4f} g, n={int(r['n'])}\n")
    print(f"Saved fit summary -> {summary_path}")

    p1 = plot_time_vs_net_mass(df_time, k, b, r2, out_dir)
    print("Saved plot:")
    print(" -", p1)
    print("Saved per-time stats:")
    print(" -", stats_csv)


if __name__ == "__main__":
    main()
