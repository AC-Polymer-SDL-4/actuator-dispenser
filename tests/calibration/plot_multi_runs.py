import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import time


def summarize_runs(csv_paths):
    records = []
    all_points = []
    for p in csv_paths:
        df = pd.read_csv(p)
        df = df.dropna(subset=["target_volume_ml", "dispensed_mass_g"]).copy()
        df["target_volume_ml"] = df["target_volume_ml"].astype(float)
        df["dispensed_mass_g"] = df["dispensed_mass_g"].astype(float)
        # keep raw points for combined stats later
        df["run"] = p.parent.name
        all_points.append(df[["target_volume_ml", "dispensed_mass_g", "run"]])

        # Per-volume stats within this run
        g = df.groupby("target_volume_ml")["dispensed_mass_g"]
        stats = pd.DataFrame({
            "target_volume_ml": g.mean().index,
            "n": g.count().values,
            "median_mass_g": g.median().values,
            "std_mass_g": g.std(ddof=1).values,
        })
        stats["run"] = p.parent.name
        records.append(stats)
    per_run = pd.concat(records, ignore_index=True)
    combined = pd.concat(all_points, ignore_index=True)
    # Combined per-volume stats across all runs
    g_all = combined.groupby("target_volume_ml")["dispensed_mass_g"]
    combined_stats = pd.DataFrame({
        "target_volume_ml": g_all.mean().index,
        "n": g_all.count().values,
        "median_mass_g": g_all.median().values,
        "std_mass_g": g_all.std(ddof=1).values,
    })
    return per_run, combined_stats


def plot_aggregate(per_run_df: pd.DataFrame, combined_stats: pd.DataFrame, out_png: Path):
    plt.figure(figsize=(7, 5))
    # Plot per-run medians with error bars (std), but no legend to avoid clutter
    runs = sorted(per_run_df["run"].unique())
    colors = plt.cm.tab10.colors
    color_map = {run: colors[i % len(colors)] for i, run in enumerate(runs)}

    for run in runs:
        sub = per_run_df[per_run_df["run"] == run]
        x = sub["target_volume_ml"].values
        y = sub["median_mass_g"].values
        yerr = sub["std_mass_g"].values
        plt.errorbar(x, y, yerr=yerr, fmt="o", color=color_map[run], alpha=0.6)

    # y=x reference
    plt.plot([0.0, 0.27], [0.0, 0.27], "--", color="#888888")

    # Draw ±kσ bars (k=1..12) anchored on y=x for each target volume using combined stats
    sigma_levels = list(range(1, 13))
    for _, row in combined_stats.iterrows():
        x = float(row["target_volume_ml"])  # target
        std = float(row["std_mass_g"]) if pd.notna(row["std_mass_g"]) else 0.0
        for k in sigma_levels:
            yerr_k = k * std
            # thinner, lighter lines for higher k to reduce clutter
            alpha = max(0.15, 0.6 - (k - 1) * 0.04)
            plt.errorbar([x], [x], yerr=[yerr_k], fmt="none", ecolor="#222222", elinewidth=1.0, capsize=2, alpha=alpha)

    plt.xlim(0.0, 0.27)
    plt.ylim(0.0, 0.27)
    plt.xlabel("Target volume (mL)")
    plt.ylabel("Delivered (g ≈ mL)")
    plt.title("Median ± Std (per run) with ±1…12σ about y=x")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def main():
    ap = argparse.ArgumentParser(description="Aggregate multiple calibration runs; plot median±std per run and volume")
    ap.add_argument("csvs", nargs="+", help="Paths to calibration_measurements_net.csv files")
    args = ap.parse_args()

    csv_paths = [Path(p) for p in args.csvs]
    per_run_df, combined_stats = summarize_runs(csv_paths)

    # Write combined stats next to first CSV's parent in a new aggregate folder
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = csv_paths[0].parent.parent / f"aggregate_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    stats_out = out_dir / "aggregate_median_std_per_run.csv"
    per_run_df.to_csv(stats_out, index=False)
    stats2_out = out_dir / "aggregate_combined_stats.csv"
    combined_stats.to_csv(stats2_out, index=False)

    png_out = out_dir / "aggregate_median_std.png"
    plot_aggregate(per_run_df, combined_stats, png_out)

    print(f"Wrote per-run stats: {stats_out}")
    print(f"Wrote combined stats: {stats2_out}")
    print(f"Wrote plot:  {png_out}")


if __name__ == "__main__":
    main()
