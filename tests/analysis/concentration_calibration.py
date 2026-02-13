import argparse
import os
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import nnls

from uncertainty_plot_and_stats import load_measurements


def srgb_to_linear(channel_8bit: np.ndarray) -> np.ndarray:
    # Convert 8-bit sRGB code values (0..255) to linear light (0..1)
    E = np.clip(channel_8bit.astype(np.float64) / 255.0, 0.0, 1.0)
    L = np.where(
        E <= 0.04045,
        E / 12.92,
        np.power((E + 0.055) / 1.055, 2.4)
    )
    return L


def get_expected_compositions(expected_set: str) -> Dict[int, Dict[str, float]]:
    if expected_set == 'original':
        return {
            1: {'R': 0.3, 'Y': 0.3, 'B': 0.3, 'Water': 0.1},
            2: {'R': 0.5, 'Y': 0.2, 'B': 0.2, 'Water': 0.1},
            3: {'R': 0.2, 'Y': 0.5, 'B': 0.2, 'Water': 0.1},
            4: {'R': 0.2, 'Y': 0.2, 'B': 0.5, 'Water': 0.1},
        }
    return {
        1: {'R': 0.3, 'Y': 0.3, 'B': 0.3, 'Water': 0.1},
        2: {'R': 0.7, 'Y': 0.1, 'B': 0.1, 'Water': 0.1},
        3: {'R': 0.1, 'Y': 0.7, 'B': 0.1, 'Water': 0.1},
        4: {'R': 0.1, 'Y': 0.1, 'B': 0.7, 'Water': 0.1},
    }


def build_dataset(df: pd.DataFrame, expected_set: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    comps = get_expected_compositions(expected_set)
    # Per-well mean RGB (8-bit)
    rgb_cols = ['RGB_R', 'RGB_G', 'RGB_B']
    if not all(c in df.columns for c in rgb_cols):
        raise ValueError('RGB columns not found in measurements')
    per_well = df.groupby('well_index')[rgb_cols + ['group_id']].mean().sort_index()
    # Linearize
    R_lin = srgb_to_linear(per_well['RGB_R'].values)
    G_lin = srgb_to_linear(per_well['RGB_G'].values)
    B_lin = srgb_to_linear(per_well['RGB_B'].values)
    X_lin = np.stack([R_lin, G_lin, B_lin], axis=1)  # (N,3)
    # Normalize to proportions r',g',b'
    sums = X_lin.sum(axis=1, keepdims=True)
    sums[sums == 0] = np.nan
    X_norm = X_lin / sums
    X_df = pd.DataFrame(X_norm, columns=['r_norm', 'g_norm', 'b_norm'])
    X_df['group_id'] = per_well['group_id'].astype(int).values
    X_df['well_index'] = per_well.index.astype(int)
    # Build dye composition fractions (ignoring water)
    C = []
    for gid in X_df['group_id']:
        comp = comps[int(gid)]
        total = comp['R'] + comp['Y'] + comp['B']
        if total <= 0:
            C.append([np.nan, np.nan, np.nan])
        else:
            C.append([comp['R']/total, comp['Y']/total, comp['B']/total])
    C_df = pd.DataFrame(C, columns=['R_frac', 'Y_frac', 'B_frac'])
    C_df['group_id'] = X_df['group_id']
    C_df['well_index'] = X_df['well_index']
    return X_df, C_df


def fit_mixing_matrix(X_df: pd.DataFrame, C_df: pd.DataFrame, allow_bias: bool = True) -> Dict[str, np.ndarray]:
    # Fit X ≈ C * M^T + b using least squares (optionally with bias term)
    X = X_df[['r_norm','g_norm','b_norm']].values  # (N,3)
    C = C_df[['R_frac','Y_frac','B_frac']].values  # (N,3)
    mask = ~np.isnan(X).any(axis=1) & ~np.isnan(C).any(axis=1)
    Xm = X[mask]
    Cm = C[mask]
    if allow_bias:
        Cm_aug = np.concatenate([Cm, np.ones((Cm.shape[0],1))], axis=1)  # (N,4)
        # Solve per channel: Xm[:,ch] ≈ Cm_aug @ w_ch
        W = []
        for ch in range(3):
            w, *_ = np.linalg.lstsq(Cm_aug, Xm[:, ch], rcond=None)
            W.append(w)
        W = np.stack(W, axis=1)  # (4,3) last row is bias
        M = W[:3, :]
        b = W[3, :]
    else:
        W, *_ = np.linalg.lstsq(Cm, Xm, rcond=None)  # (3,3)
        M = W
        b = np.zeros(3)
    # Compute fit metrics
    Xm_pred = Cm @ M + b
    resid = Xm - Xm_pred
    rmse = float(np.sqrt(np.nanmean(resid**2)))
    r2 = 1.0 - float(np.nanvar(resid) / np.nanvar(Xm)) if np.nanvar(Xm) > 0 else np.nan
    return {'M': M, 'b': b, 'rmse': rmse, 'r2': r2}


def predict_concentrations(X_df: pd.DataFrame, model: Dict[str, np.ndarray]) -> pd.DataFrame:
    # Estimate dye fractions from measured normalized RGB via NNLS on each sample
    M = model['M']  # (3,3)
    b = model['b']  # (3,)
    preds = []
    for i, row in X_df.iterrows():
        x = row[['r_norm','g_norm','b_norm']].values.astype(float)
        y = x - b
        # Solve C >= 0 to minimize ||M C - y|| using nnls per channel stack
        # Convert to normal equation form: minimize ||A c - y||, A = M
        c, _ = nnls(M, y)
        s = c.sum()
        if s > 0:
            c = c / s
        preds.append({'well_index': int(row['well_index']), 'group_id': int(row['group_id']),
                      'R_frac_pred': float(c[0]), 'Y_frac_pred': float(c[1]), 'B_frac_pred': float(c[2])})
    return pd.DataFrame(preds)


def plot_calibration(X_df: pd.DataFrame, C_df: pd.DataFrame, folder: Path, model: Dict[str, np.ndarray]):
    # Scatter plots of measured normalized channels vs dye fractions; show fitted mapping via M
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for ch, name in enumerate(['R','G','B']):
        ax = axes[ch]
        # Choose expected fraction axis: R_frac for R, Y_frac for G, B_frac for B
        if name == 'R':
            t = C_df['R_frac'].values
        elif name == 'G':
            t = C_df['Y_frac'].values
        else:
            t = C_df['B_frac'].values
        y = X_df[['r_norm','g_norm','b_norm']].values[:, ch]
        ax.scatter(t, y, s=24, alpha=0.7)
        ax.set_xlabel(f"{name} dye fraction")
        ax.set_ylabel(f"Measured {name}' (normalized)")
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    out_png = folder / 'calibration_scatter.png'
    plt.savefig(out_png, dpi=150)
    plt.close(fig)

    # Residual histogram
    X = X_df[['r_norm','g_norm','b_norm']].values
    C = C_df[['R_frac','Y_frac','B_frac']].values
    Xm_pred = C @ model['M'] + model['b']
    resid = (X - Xm_pred).ravel()
    plt.figure(figsize=(6,4))
    plt.hist(resid, bins=30, alpha=0.8)
    plt.title(f"Residuals (rmse {model['rmse']:.3f}, R^2 {model['r2']:.2f})")
    plt.xlabel("Residual")
    plt.ylabel("Count")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    out_png = folder / 'calibration_residuals.png'
    plt.savefig(out_png, dpi=150)
    plt.close()


def main():
    ap = argparse.ArgumentParser(description='Fit dye concentration calibration from uncertainty workflow outputs')
    ap.add_argument('folder', help='Path to uncertainty_measurement_workflow output folder')
    ap.add_argument('--expected-set', choices=['original','dominant'], default='dominant',
                    help='Expected composition set to map wells to dye fractions')
    ap.add_argument('--no-bias', action='store_true', help='Fit without bias term in mixing model')
    args = ap.parse_args()

    folder = Path(args.folder)
    df = load_measurements(folder)
    X_df, C_df = build_dataset(df, args.expected_set)

    model = fit_mixing_matrix(X_df, C_df, allow_bias=(not args.no_bias))

    # Save model parameters
    M = model['M']
    b = model['b']
    np.savetxt(folder / 'mixing_matrix_M.csv', M, delimiter=',', fmt='%.6f')
    np.savetxt(folder / 'mixing_bias_b.csv', b.reshape(1,-1), delimiter=',', fmt='%.6f')
    with open(folder / 'mixing_fit_summary.txt', 'w') as f:
        f.write(f"RMSE: {model['rmse']:.6f}\n")
        f.write(f"R2: {model['r2']:.6f}\n")

    # Predict concentrations (fractions)
    pred_df = predict_concentrations(X_df, model)
    pred_df.to_csv(folder / 'predicted_dye_fractions.csv', index=False)

    # Plot calibration scatter and residuals
    plot_calibration(X_df, C_df, folder, model)

    print(f"Saved mixing matrix: {folder / 'mixing_matrix_M.csv'}")
    print(f"Saved bias vector: {folder / 'mixing_bias_b.csv'}")
    print(f"Saved fit summary: {folder / 'mixing_fit_summary.txt'}")
    print(f"Saved predicted fractions: {folder / 'predicted_dye_fractions.csv'}")
    print(f"Saved calibration scatter: {folder / 'calibration_scatter.png'}")
    print(f"Saved calibration residuals: {folder / 'calibration_residuals.png'}")


if __name__ == '__main__':
    main()
