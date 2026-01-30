import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    # Filter rows with numeric values
    df_clean = df.dropna(subset=["target_volume_ml", "dispensed_mass_g"]).copy()
    df_clean["target_volume_ml"] = df_clean["target_volume_ml"].astype(float)
    df_clean["dispensed_mass_g"] = df_clean["dispensed_mass_g"].astype(float)
    # Group by target volume
    grouped = df_clean.groupby("target_volume_ml")["dispensed_mass_g"]
    stats = pd.DataFrame({
        "n": grouped.count(),
        "mean_mass_g": grouped.mean(),
        "std_mass_g": grouped.std(ddof=1),
    })
    stats["cv_percent"] = (stats["std_mass_g"] / stats["mean_mass_g"]) * 100.0
    stats["mean_error_percent"] = ((stats["mean_mass_g"] - stats.index) / stats.index) * 100.0
    return stats.reset_index()


def make_plot(df: pd.DataFrame, out_png: Path):
    df_clean = df.dropna(subset=["target_volume_ml", "dispensed_mass_g"]).copy()
    df_clean["target_volume_ml"] = df_clean["target_volume_ml"].astype(float)
    df_clean["dispensed_mass_g"] = df_clean["dispensed_mass_g"].astype(float)

    plt.figure(figsize=(6, 5))
    # Scatter of replicates
    plt.scatter(df_clean["target_volume_ml"], df_clean["dispensed_mass_g"], c="#1f77b4", label="replicates")
    # y=x reference
    vmin = max(0.0, float(df_clean["target_volume_ml"].min()) * 0.8)
    vmax = float(df_clean["target_volume_ml"].max()) * 1.2
    plt.plot([vmin, vmax], [vmin, vmax], "--", color="#888888", label="target = delivered")

    plt.xlabel("Target volume (mL)")
    plt.ylabel("Delivered (g ≈ mL)")
    plt.title("Measured vs Target Volume")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()


def main():
    ap = argparse.ArgumentParser(description="Plot calibration CSV and compute stats")
    ap.add_argument("csv", help="Path to calibration_measurements_net.csv")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    df = pd.read_csv(csv_path)

    stats = compute_stats(df)
    stats_out = csv_path.parent / "volume_validation_stats.csv"
    stats.to_csv(stats_out, index=False)

    png_out = csv_path.parent / "measured_vs_target_volume.png"
    make_plot(df, png_out)

    print(f"Wrote stats: {stats_out}")
    print(f"Wrote plot:  {png_out}")


if __name__ == "__main__":
    main()
