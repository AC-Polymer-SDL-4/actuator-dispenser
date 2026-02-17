import argparse
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# --- Normalization helpers ---
# NOTE (2026-02-17): Empirical verification using tests/analysis/camera_srgb_check.py
# on the capture pipeline (Windows, DirectShow, FourCC=YUY2, convert_rgb=1)
# indicates frames are sRGB gamma-encoded (ratio_gamma22_to_linear ≈ 0.000).
# Therefore, RGB values stored in workflow CSVs are sRGB channel means.
# Decode to linear-light before any proportional mixing or normalization.

def srgb_to_linear_channel(v: np.ndarray) -> np.ndarray:
    """Convert sRGB channel values to linear-light.

    Accepts arrays in 0..1 or 0..255; auto-scales if needed.
    """
    v = np.array(v, dtype=float)
    if np.nanmax(v) > 1.5:
        v = v / 255.0
    out = np.empty_like(v, dtype=float)
    mask = v <= 0.04045
    out[mask] = v[mask] / 12.92
    out[~mask] = ((v[~mask] + 0.055) / 1.055) ** 2.4
    return out

def compute_normalized_rgb(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize RGB using linearized sRGB fractions R', G', B'.

    Assumes input RGB columns are sRGB-coded channel means (uint8 range),
    so we first decode to linear-light via srgb_to_linear_channel.
    """
    cols = ['RGB_R', 'RGB_G', 'RGB_B']
    if not all(c in df.columns for c in cols):
        return pd.DataFrame()
    rows = []
    for group_id in sorted(df['group_id'].unique()):
        g = df[df['group_id'] == group_id]
        wm = g.groupby('well_index')[cols].mean().sort_index()
        # Linearize sRGB channels to linear-light
        r_lin = srgb_to_linear_channel(wm['RGB_R'].to_numpy())
        g_lin = srgb_to_linear_channel(wm['RGB_G'].to_numpy())
        b_lin = srgb_to_linear_channel(wm['RGB_B'].to_numpy())
        denom = r_lin + g_lin + b_lin
        denom = np.where(denom == 0, np.nan, denom)
        r_norm = r_lin / denom
        g_norm = g_lin / denom
        b_norm = b_lin / denom
        for i, well_idx in enumerate(wm.index):
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'RGB', 'channel': "R'", 'value': float(r_norm[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'RGB', 'channel': "G'", 'value': float(g_norm[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'RGB', 'channel': "B'", 'value': float(b_norm[i])})
    return pd.DataFrame(rows)

def compute_normalized_lab(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize LAB using lightness/chroma/hue features.

    - L' = L*/100 (0..1)
    - C' = C*/P95(C*) clipped to [0,1], where C* = sqrt(a*^2 + b*^2)
    - h' = hue angle (atan2(b*, a*)) mapped to [0,1] via degrees/360

    This avoids sum-normalizing LAB components, which is not meaningful.
    """
    cols = ['LAB_L', 'LAB_A', 'LAB_B']
    if not all(c in df.columns for c in cols):
        return pd.DataFrame()

    # Compute a robust chroma scale across the dataset using well means
    try:
        wm_all = df.groupby(['group_id', 'well_index'])[cols].mean().reset_index()
        C_all = np.sqrt(wm_all['LAB_A'].to_numpy()**2 + wm_all['LAB_B'].to_numpy()**2)
        C_ref = np.nanpercentile(C_all, 95) if C_all.size else 1.0
        if not C_ref or np.isnan(C_ref) or C_ref <= 0:
            C_ref = 1.0
    except Exception:
        C_ref = 1.0

    rows = []
    for group_id in sorted(df['group_id'].unique()):
        g = df[df['group_id'] == group_id]
        wm = g.groupby('well_index')[cols].mean().sort_index()
        Lp = wm['LAB_L'].to_numpy() / 100.0
        a = wm['LAB_A'].to_numpy()
        b = wm['LAB_B'].to_numpy()
        C = np.sqrt(a**2 + b**2)
        Cp = np.clip(C / C_ref, 0.0, 1.0)
        h_rad = np.arctan2(b, a)  # (-pi, pi]
        h_deg = (np.degrees(h_rad) + 360.0) % 360.0
        hp = h_deg / 360.0
        for i, well_idx in enumerate(wm.index):
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'LAB', 'channel': "L'", 'value': float(Lp[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'LAB', 'channel': "C'", 'value': float(Cp[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'LAB', 'channel': "h'", 'value': float(hp[i])})
    return pd.DataFrame(rows)

def compute_normalized_hsv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize HSV via direct scaling (no sum-normalization).

    - H' = H/360 (mapped to [0,1])
    - S' = S/100
    - V' = V/100
    """
    cols = ['HSV_H', 'HSV_S', 'HSV_V']
    if not all(c in df.columns for c in cols):
        return pd.DataFrame()
    rows = []
    for group_id in sorted(df['group_id'].unique()):
        g = df[df['group_id'] == group_id]
        wm = g.groupby('well_index')[cols].mean().sort_index()
        Hp = wm['HSV_H'].to_numpy() / 360.0
        Sp = wm['HSV_S'].to_numpy() / 100.0
        Vp = wm['HSV_V'].to_numpy() / 100.0
        for i, well_idx in enumerate(wm.index):
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'HSV', 'channel': "H'", 'value': float(Hp[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'HSV', 'channel': "S'", 'value': float(Sp[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'HSV', 'channel': "V'", 'value': float(Vp[i])})
    return pd.DataFrame(rows)

def compute_sum_normalized_lab(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy LAB sum-normalization retained as a comparative variant.

    Channels: L'_sum, A'_sum, B'_sum where each is the fraction of
    scaled components (L/100, (A+128)/255, (B+128)/255) divided by their sum.
    """
    cols = ['LAB_L', 'LAB_A', 'LAB_B']
    if not all(c in df.columns for c in cols):
        return pd.DataFrame()
    rows = []
    for group_id in sorted(df['group_id'].unique()):
        g = df[df['group_id'] == group_id]
        wm = g.groupby('well_index')[cols].mean().sort_index()
        L_scaled = wm['LAB_L'].to_numpy() / 100.0
        A_scaled = (wm['LAB_A'].to_numpy() + 128.0) / 255.0
        B_scaled = (wm['LAB_B'].to_numpy() + 128.0) / 255.0
        denom = L_scaled + A_scaled + B_scaled
        denom = np.where(denom == 0, np.nan, denom)
        l_sum = L_scaled / denom
        a_sum = A_scaled / denom
        b_sum = B_scaled / denom
        for i, well_idx in enumerate(wm.index):
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'LAB', 'channel': "L'_sum", 'value': float(l_sum[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'LAB', 'channel': "A'_sum", 'value': float(a_sum[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'LAB', 'channel': "B'_sum", 'value': float(b_sum[i])})
    return pd.DataFrame(rows)

def compute_sum_normalized_hsv(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy HSV sum-normalization retained as a comparative variant.

    Channels: H'_sum, S'_sum, V'_sum where each is the fraction of
    scaled components (H/360, S/100, V/100) divided by their sum.
    """
    cols = ['HSV_H', 'HSV_S', 'HSV_V']
    if not all(c in df.columns for c in cols):
        return pd.DataFrame()
    rows = []
    for group_id in sorted(df['group_id'].unique()):
        g = df[df['group_id'] == group_id]
        wm = g.groupby('well_index')[cols].mean().sort_index()
        H_scaled = wm['HSV_H'].to_numpy() / 360.0
        S_scaled = wm['HSV_S'].to_numpy() / 100.0
        V_scaled = wm['HSV_V'].to_numpy() / 100.0
        denom = H_scaled + S_scaled + V_scaled
        denom = np.where(denom == 0, np.nan, denom)
        h_sum = H_scaled / denom
        s_sum = S_scaled / denom
        v_sum = V_scaled / denom
        for i, well_idx in enumerate(wm.index):
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'HSV', 'channel': "H'_sum", 'value': float(h_sum[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'HSV', 'channel': "S'_sum", 'value': float(s_sum[i])})
            rows.append({'group_id': int(group_id), 'well_index': int(well_idx), 'color_space': 'HSV', 'channel': "V'_sum", 'value': float(v_sum[i])})
    return pd.DataFrame(rows)

def write_normalized_outputs(df: pd.DataFrame, out_dir: Path):
    rgb_n = compute_normalized_rgb(df)
    lab_scaled = compute_normalized_lab(df)
    hsv_scaled = compute_normalized_hsv(df)
    # Removed legacy sum-normalized variants as they are incorrect for LAB/HSV
    variants = [rgb_n, lab_scaled, hsv_scaled]
    all_n = pd.concat([x for x in variants if not x.empty], ignore_index=True) if any((not x.empty) for x in variants) else pd.DataFrame()
    if all_n.empty:
        return None
    out_csv = out_dir / "normalized_channels.csv"
    all_n.to_csv(out_csv, index=False)
    # Per-group plots
    for cs in ['RGB', 'LAB', 'HSV']:
        cs_df = all_n[all_n['color_space'] == cs]
        if cs_df.empty:
            continue
        for group_id in sorted(cs_df['group_id'].unique()):
            g = cs_df[cs_df['group_id'] == group_id]
            pivot = g.pivot(index='well_index', columns='channel', values='value').sort_index()
            import matplotlib.pyplot as plt
            # Determine channel sets (scaled only)
            if cs == 'LAB':
                cols = [c for c in pivot.columns if c in {"L'", "C'", "h'"}]
            elif cs == 'HSV':
                cols = [c for c in pivot.columns if c in {"H'", "S'", "V'"}]
            else:  # RGB
                cols = [c for c in pivot.columns if c in {"R'", "G'", "B'"}]
            # Plot scaled variant
            if cols:
                plt.figure(figsize=(9, 5))
                for ch in cols:
                    plt.plot(pivot.index, pivot[ch].values, marker='o', linestyle='-', label=ch)
                plt.title(f"Group {group_id} — {cs} normalized")
                plt.xlabel("Well index")
                plt.ylabel("Normalized channel value")
                plt.ylim(0, 1)
                plt.grid(True, alpha=0.3)
                # Overlay expected dotted lines (water-scaled) for all color spaces — scaled variant
                expected = get_expected_compositions('dominant')
                comp = expected.get(int(group_id), {'R': 0.33, 'Y': 0.33, 'B': 0.33, 'Water': 0.0})
                scale = 1.0 - comp.get('Water', 0.0)
                r0 = comp['R'] * scale
                y0 = comp['Y'] * scale
                b0 = comp['B'] * scale
                xmin = pivot.index.min() if len(pivot.index) else None
                xmax = pivot.index.max() if len(pivot.index) else None
                if xmin is not None and xmax is not None:
                    plt.hlines([r0], xmin=xmin, xmax=xmax, colors='r', linestyles='dotted', label='R0')
                    plt.hlines([y0], xmin=xmin, xmax=xmax, colors='g', linestyles='dotted', label='Y0')
                    plt.hlines([b0], xmin=xmin, xmax=xmax, colors='b', linestyles='dotted', label='B0')
                plt.legend(fontsize=9)
                plt.tight_layout()
                out_png = out_dir / f"trend_group_{group_id}_{cs}_normalized.png"
                plt.savefig(out_png, dpi=150)
                plt.close()
    return out_csv

def plot_normalized_all_wells(out_dir: Path):
    """Create combined normalized plots across all wells.

    Produces per color space:
    - trend_{CS}_normalized.png (e.g., LAB: L', C', h')
    """
    norm_path = out_dir / "normalized_channels.csv"
    if not norm_path.exists():
        return None
    df_n = pd.read_csv(norm_path)
    made = []
    for cs in ['RGB', 'LAB', 'HSV']:
        cs_df = df_n[df_n['color_space'] == cs]
        if cs_df.empty:
            continue
        import matplotlib.pyplot as plt
        # Only plot scaled variants (sum-normalized removed as incorrect)
        def _plot_scaled(sub_df, cs):
            if sub_df.empty:
                return
            groups = sorted(sub_df['group_id'].unique()) if 'group_id' in sub_df.columns else []
            legend_added = set()
            plt.figure(figsize=(10, 6))
            for group_id in groups:
                g = sub_df[sub_df['group_id'] == group_id]
                pivot = g.pivot(index='well_index', columns='channel', values='value').sort_index()
                # Scaled channels
                if cs == 'LAB':
                    cols = [c for c in pivot.columns if c in {"L'", "C'", "h'"}]
                elif cs == 'HSV':
                    cols = [c for c in pivot.columns if c in {"H'", "S'", "V'"}]
                else:  # RGB
                    cols = [c for c in pivot.columns if c in {"R'", "G'", "B'"}]
                for ch in cols:
                    label = ch if ch not in legend_added else None
                    plt.plot(pivot.index, pivot[ch].values, marker='o', linestyle='-', label=label)
                    if label:
                        legend_added.add(ch)
                # Overlay expected lines (water-scaled)
                expected = get_expected_compositions('dominant')
                comp = expected.get(int(group_id), {'R': 0.33, 'Y': 0.33, 'B': 0.33, 'Water': 0.0})
                scale = 1.0 - comp.get('Water', 0.0)
                r0 = comp['R'] * scale
                y0 = comp['Y'] * scale
                b0 = comp['B'] * scale
                xmin = pivot.index.min() if len(pivot.index) else None
                xmax = pivot.index.max() if len(pivot.index) else None
                if xmin is not None and xmax is not None:
                    plt.hlines([r0], xmin=xmin, xmax=xmax, colors='r', linestyles='dotted', label='R0' if 'R0' not in legend_added else None)
                    plt.hlines([y0], xmin=xmin, xmax=xmax, colors='g', linestyles='dotted', label='Y0' if 'Y0' not in legend_added else None)
                    plt.hlines([b0], xmin=xmin, xmax=xmax, colors='b', linestyles='dotted', label='B0' if 'B0' not in legend_added else None)
                    legend_added.update(['R0', 'Y0', 'B0'])
            plt.title(f"{cs} Normalized Across All Wells")
            plt.xlabel("Well index")
            plt.ylabel("Normalized value")
            plt.ylim(0, 1)
            plt.grid(True, alpha=0.3)
            plt.legend(fontsize=9)
            plt.tight_layout()
            out_png = out_dir / f"trend_{cs}_normalized.png"
            plt.savefig(out_png, dpi=150)
            plt.close()
            made.append(out_png)
        
        _plot_scaled(cs_df, cs)
    return made


def load_measurements(folder: Path) -> pd.DataFrame:
    raw = folder / "uncertainty_measurements_raw.csv"
    if raw.exists():
        df = pd.read_csv(raw)
        return df
    # Fallback: try measurement_summary
    summary = folder / "measurement_summary.csv"
    if summary.exists():
        return pd.read_csv(summary)
    # As last resort, concatenate progress files
    parts: List[pd.DataFrame] = []
    for i in range(1, 5):
        p = folder / f"measurements_progress_group_{i}.csv"
        if p.exists():
            parts.append(pd.read_csv(p))
    if parts:
        return pd.concat(parts, ignore_index=True)
    raise FileNotFoundError(f"No measurements found in {folder}")


def compute_group_stats(df: pd.DataFrame, color_spaces: List[str]) -> pd.DataFrame:
    results = []
    # Expect columns like RGB_R, RGB_G, RGB_B etc.
    for group_id in sorted(df['group_id'].unique()):
        g = df[df['group_id'] == group_id]
        for cs in color_spaces:
            cols = [c for c in df.columns if c.startswith(f"{cs}_")]
            for col in cols:
                # Well means (average of replicates per well)
                well_means = g.groupby('well_index')[col].mean()
                # Measurement uncertainty: average within-well SD
                well_stds = g.groupby('well_index')[col].std()
                measurement_unc = float(well_stds.mean()) if len(well_stds) else np.nan
                # Process uncertainty: SD of well means
                process_unc = float(well_means.std()) if len(well_means) else np.nan
                # Coefficients of variation
                # Measurement CV: average of per-well (std/mean), ignoring zero/NaN means
                per_well_means = g.groupby('well_index')[col].mean()
                per_well_stds = well_stds
                valid = per_well_means.replace(0, np.nan)
                per_well_cv = (per_well_stds / valid) * 100.0
                measurement_cv = float(per_well_cv.dropna().mean()) if len(per_well_cv.dropna()) else np.nan
                # Process CV: std of well means divided by mean of well means
                process_mean = float(well_means.mean()) if len(well_means) else np.nan
                process_cv = float((process_unc / process_mean) * 100.0) if process_mean and process_mean != 0 else np.nan
                # Overall stats
                group_mean = float(g[col].mean())
                group_std = float(g[col].std())
                results.append({
                    'group_id': int(group_id),
                    'color_space': cs,
                    'channel': col.replace(f"{cs}_", ""),
                    'group_mean': round(group_mean, 3),
                    'group_std': round(group_std, 3),
                    'measurement_uncertainty': round(measurement_unc, 3),
                    'process_uncertainty': round(process_unc, 3),
                    'uncertainty_ratio': round(process_unc / measurement_unc, 3) if measurement_unc and measurement_unc > 0 else np.inf,
                    'measurement_cv_percent': round(measurement_cv, 2) if not np.isnan(measurement_cv) else np.nan,
                    'process_cv_percent': round(process_cv, 2) if not np.isnan(process_cv) else np.nan,
                    'num_wells': int(well_means.shape[0]),
                    'num_measurements': int(g.shape[0])
                })
    return pd.DataFrame(results)


def plot_trends(df: pd.DataFrame, out_dir: Path, color_spaces: List[str]):
    # Plot well means per channel across wells, colored by group
    for cs in color_spaces:
        cols = [c for c in df.columns if c.startswith(f"{cs}_")]
        if not cols:
            continue
        plt.figure(figsize=(10, 6))
        for col in cols:
            # Compute well means across all groups
            # To show group trends, we plot each group separately
            for group_id in sorted(df['group_id'].unique()):
                g = df[df['group_id'] == group_id]
                well_means = g.groupby('well_index')[col].mean().sort_index()
                plt.plot(well_means.index, well_means.values, marker='o', linestyle='-', alpha=0.7, label=f"Group {group_id} — {col}")
        plt.title(f"Well Means Trend — {cs}")
        plt.xlabel("Well index")
        plt.ylabel(f"{cs} channel value")
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=8, ncol=2)
        plt.tight_layout()
        out_png = out_dir / f"trend_{cs}.png"
        plt.savefig(out_png, dpi=150)
        plt.close()


def get_expected_compositions(expected_set: str) -> Dict[int, Dict[str, float]]:
    # Two presets: 'original' from earlier workflow, and 'dominant' per latest proposal
    if expected_set == 'original':
        return {
            1: {'R': 0.3, 'Y': 0.3, 'B': 0.3, 'Water': 0.1},
            2: {'R': 0.5, 'Y': 0.2, 'B': 0.2, 'Water': 0.1},
            3: {'R': 0.2, 'Y': 0.5, 'B': 0.2, 'Water': 0.1},
            4: {'R': 0.2, 'Y': 0.2, 'B': 0.5, 'Water': 0.1},
        }
    # 'dominant': user-proposed mapping with stronger single primary
    return {
        1: {'R': 0.3, 'Y': 0.3, 'B': 0.3, 'Water': 0.1},
        2: {'R': 0.7, 'Y': 0.1, 'B': 0.1, 'Water': 0.1},
        3: {'R': 0.1, 'Y': 0.7, 'B': 0.1, 'Water': 0.1},
        4: {'R': 0.1, 'Y': 0.1, 'B': 0.7, 'Water': 0.1},
    }


def compute_normalized_rgb_error(df: pd.DataFrame, out_dir: Path, expected_set: str):
    # Map groups to expected compositions; assume Y maps to G channel for expected RGB fractions (simplification)
    expected = get_expected_compositions(expected_set)
    rows = []
    groups = sorted(df['group_id'].unique()) if 'group_id' in df.columns else []
    for group_id in groups:
        g = df[df['group_id'] == group_id]
        # Well means for RGB channels
        cols = ['RGB_R', 'RGB_G', 'RGB_B']
        if not all(c in df.columns for c in cols):
            continue
        wm = g.groupby('well_index')[cols].mean().sort_index()
        # Normalize measured RGB per well
        sums = wm.sum(axis=1)
        r_norm = wm['RGB_R'] / sums
        g_norm = wm['RGB_G'] / sums
        b_norm = wm['RGB_B'] / sums
        # Expected fractions
        comp = expected.get(int(group_id), {'R': 0.33, 'Y': 0.33, 'B': 0.33, 'Water': 0.0})
        # For error metrics, use dye-only normalized expectations (exclude water)
        total_dye = comp['R'] + comp['Y'] + comp['B']
        r0_err = comp['R'] / total_dye if total_dye else np.nan
        g0_err = comp['Y'] / total_dye if total_dye else np.nan
        b0_err = comp['B'] / total_dye if total_dye else np.nan
        # For plotting overlays, use water-scaled absolute dye fractions
        scale = 1.0 - comp.get('Water', 0.0)
        r0_line = comp['R'] * scale
        g0_line = comp['Y'] * scale
        b0_line = comp['B'] * scale
        # Euclidean error per well between normalized measured and normalized expected (dye-only)
        err = np.sqrt((r_norm - r0_err)**2 + (g_norm - g0_err)**2 + (b_norm - b0_err)**2)
        # Collect rows
        for well_idx in wm.index:
            rows.append({
                'group_id': int(group_id),
                'well_index': int(well_idx),
                'r_norm': float(r_norm.loc[well_idx]),
                'g_norm': float(g_norm.loc[well_idx]),
                'b_norm': float(b_norm.loc[well_idx]),
                'r0': float(r0_err),
                'g0': float(g0_err),
                'b0': float(b0_err),
                'rgb_error': float(err.loc[well_idx])
            })
        # Plot normalized RGB with expected lines per group
        plt.figure(figsize=(9, 5))
        plt.plot(wm.index, r_norm.values, marker='o', linestyle='-', label=f"R' (mean)")
        plt.plot(wm.index, g_norm.values, marker='o', linestyle='-', label=f"G' (mean)")
        plt.plot(wm.index, b_norm.values, marker='o', linestyle='-', label=f"B' (mean)")
        # Expected horizontal lines (water-scaled)
        plt.hlines([r0_line], xmin=wm.index.min(), xmax=wm.index.max(), colors='r', linestyles='dotted', label=f"R0={r0_line:.2f}")
        plt.hlines([g0_line], xmin=wm.index.min(), xmax=wm.index.max(), colors='g', linestyles='dotted', label=f"Y0={g0_line:.2f}")
        plt.hlines([b0_line], xmin=wm.index.min(), xmax=wm.index.max(), colors='b', linestyles='dotted', label=f"B0={b0_line:.2f}")
        avg_err = float(err.mean()) if len(err) else np.nan
        plt.title(f"Group {group_id} — RGB normalized (avg error {avg_err:.3f})")
        plt.xlabel("Well index")
        plt.ylabel("Normalized channel value")
        plt.ylim(0, 1)
        plt.grid(True, alpha=0.3)
        plt.legend(fontsize=9, ncol=2)
        plt.tight_layout()
        out_png = out_dir / f"trend_group_{group_id}_RGB_normalized.png"
        plt.savefig(out_png, dpi=150)
        plt.close()

    # Save error CSV
    err_df = pd.DataFrame(rows)
    err_path = out_dir / "expected_rgb_error.csv"
    err_df.to_csv(err_path, index=False)
    return err_path

def plot_per_group_channel(df: pd.DataFrame, out_dir: Path, color_spaces: List[str]):
    # One figure per group and per channel (e.g., RGB_R group 1)
    groups = sorted(df['group_id'].unique()) if 'group_id' in df.columns else []
    for group_id in groups:
        g = df[df['group_id'] == group_id]
        for cs in color_spaces:
            cols = [c for c in df.columns if c.startswith(f"{cs}_")]
            for col in cols:
                ch = col.replace(f"{cs}_", "")
                well_means = g.groupby('well_index')[col].mean().sort_index()
                plt.figure(figsize=(7, 4))
                plt.plot(well_means.index, well_means.values, marker='o', linestyle='-', color='#1f77b4')
                plt.title(f"Group {group_id} — {cs}-{ch} (well means)")
                plt.xlabel("Well index")
                plt.ylabel(f"{cs} {ch}")
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                out_png = out_dir / f"trend_{cs}_{ch}_group_{group_id}.png"
                plt.savefig(out_png, dpi=150)
                plt.close()


def plot_per_group_color_space(df: pd.DataFrame, out_dir: Path, color_spaces: List[str]):
    # One figure per group, plotting all channels of a color space together
    groups = sorted(df['group_id'].unique()) if 'group_id' in df.columns else []
    for group_id in groups:
        g = df[df['group_id'] == group_id]
        for cs in color_spaces:
            cols = [c for c in df.columns if c.startswith(f"{cs}_")]
            if not cols:
                continue
            # Well means per channel
            well_means_df = g.groupby('well_index')[cols].mean().sort_index()
            plt.figure(figsize=(9, 5))
            legend_entries = []
            for col in cols:
                ch = col.replace(f"{cs}_", "")
                # Compute CVs
                per_well_means = g.groupby('well_index')[col].mean()
                per_well_stds = g.groupby('well_index')[col].std()
                valid_means = per_well_means.replace(0, np.nan)
                meas_cv = ((per_well_stds / valid_means) * 100.0).dropna().mean()
                proc_cv = (per_well_means.std() / per_well_means.mean() * 100.0) if per_well_means.mean() and per_well_means.mean() != 0 else np.nan
                plt.plot(well_means_df.index, well_means_df[col].values, marker='o', linestyle='-')
                label = f"{ch} (measCV {meas_cv:.1f}%, procCV {proc_cv:.1f}%)" if not np.isnan(meas_cv) and not np.isnan(proc_cv) else f"{ch}"
                legend_entries.append(label)
            plt.title(f"Group {group_id} — {cs} (well means)")
            plt.xlabel("Well index")
            plt.ylabel(f"{cs} channel value")
            plt.grid(True, alpha=0.3)
            plt.legend(legend_entries, title=f"{cs} channels", fontsize=9)
            plt.tight_layout()
            out_png = out_dir / f"trend_group_{group_id}_{cs}.png"
            plt.savefig(out_png, dpi=150)
            plt.close()

def anova_per_channel(df: pd.DataFrame, color_spaces: List[str]) -> pd.DataFrame:
    rows = []
    for cs in color_spaces:
        cols = [c for c in df.columns if c.startswith(f"{cs}_")]
        for col in cols:
            # Use well means to represent process-level variation between groups
            group_samples: Dict[int, np.ndarray] = {}
            for group_id in sorted(df['group_id'].unique()):
                g = df[df['group_id'] == group_id]
                well_means = g.groupby('well_index')[col].mean().dropna()
                group_samples[group_id] = well_means.values
            if len(group_samples) >= 2:
                try:
                    f_stat, p_val = stats.f_oneway(*group_samples.values())
                except Exception:
                    f_stat, p_val = np.nan, np.nan
            else:
                f_stat, p_val = np.nan, np.nan
            rows.append({
                'color_space': cs,
                'channel': col.replace(f"{cs}_", ""),
                'f_stat': f_stat,
                'p_value': p_val,
            })
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description="Plot uncertainty workflow data and compute statistics")
    ap.add_argument("folder", help="Path to uncertainty_measurement_workflow output folder")
    ap.add_argument("--expected-set", choices=["original", "dominant"], default="dominant",
                    help="Expected composition set to use for normalized RGB error (original or dominant)")
    args = ap.parse_args()

    folder = Path(args.folder)
    out_dir = folder
    df = load_measurements(folder)

    # Determine available color spaces from columns
    color_spaces = []
    for cs in ['RGB', 'LAB', 'HSV']:
        if any(c.startswith(f"{cs}_") for c in df.columns):
            color_spaces.append(cs)

    # Plot trends
    plot_trends(df, out_dir, color_spaces)
    # Replace granular per-channel plots with combined color-space plots per group
    plot_per_group_color_space(df, out_dir, color_spaces)

    # Normalized RGB error vs expected compositions
    err_csv = compute_normalized_rgb_error(df, out_dir, args.expected_set)

    # Write normalized channels for RGB (linearized), LAB, HSV and plots
    norm_csv = write_normalized_outputs(df, out_dir)
    made_norm = plot_normalized_all_wells(out_dir)

    # Compute group stats
    stats_df = compute_group_stats(df, color_spaces)
    stats_path = out_dir / "uncertainty_group_stats.csv"
    stats_df.to_csv(stats_path, index=False)

    # ANOVA per channel
    anova_df = anova_per_channel(df, color_spaces)
    anova_path = out_dir / "uncertainty_anova.csv"
    anova_df.to_csv(anova_path, index=False)

    print(f"Wrote trends: {[str(out_dir / f'trend_{cs}.png') for cs in color_spaces]}")
    print(f"Wrote group stats: {stats_path}")
    print(f"Wrote ANOVA: {anova_path}")
    print(f"Wrote normalized RGB error CSV: {err_csv}")
    if norm_csv:
        print(f"Wrote normalized channels CSV: {norm_csv}")
    if made_norm:
        print(f"Wrote combined normalized plots: {[str(p) for p in made_norm]} ")


if __name__ == "__main__":
    main()
