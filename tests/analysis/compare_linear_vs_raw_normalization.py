import sys
from pathlib import Path
import numpy as np
import pandas as pd

def srgb_to_linear(v_uint8: np.ndarray) -> np.ndarray:
    s = np.clip(v_uint8.astype(np.float64) / 255.0, 0.0, 1.0)
    out = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return out

def expected_map(set_name: str):
    if set_name == 'original':
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

def main(folder: str, expected_set: str = 'dominant'):
    folder = Path(folder)
    raw_path = folder / 'uncertainty_measurements_raw.csv'
    if not raw_path.exists():
        print('No raw measurements found at', raw_path)
        return
    df = pd.read_csv(raw_path)
    cols = ['RGB_R','RGB_G','RGB_B']
    if not all(c in df.columns for c in cols):
        print('Missing RGB columns in measurements')
        return
    per_well = df.groupby(['well_index','group_id'])[cols].mean().reset_index().sort_values('well_index')
    # Raw 8-bit normalized
    s_raw = per_well[cols].sum(axis=1)
    raw_norm = pd.DataFrame({
        "R'": per_well['RGB_R'] / s_raw,
        "G'": per_well['RGB_G'] / s_raw,
        "B'": per_well['RGB_B'] / s_raw,
    })
    # Linear-light normalized
    R_lin = srgb_to_linear(per_well['RGB_R'].to_numpy())
    G_lin = srgb_to_linear(per_well['RGB_G'].to_numpy())
    B_lin = srgb_to_linear(per_well['RGB_B'].to_numpy())
    s_lin = R_lin + G_lin + B_lin
    lin_norm = pd.DataFrame({
        "R'": R_lin / s_lin,
        "G'": G_lin / s_lin,
        "B'": B_lin / s_lin,
    })
    # Expected normalized fractions per group (R, Y->G, B)
    comps = expected_map(expected_set)
    exp = per_well[['group_id']].copy()
    exp['R0'] = exp['group_id'].map(lambda g: comps[int(g)]['R'])
    exp['G0'] = exp['group_id'].map(lambda g: comps[int(g)]['Y'])
    exp['B0'] = exp['group_id'].map(lambda g: comps[int(g)]['B'])
    tot = (exp['R0'] + exp['G0'] + exp['B0']).replace(0, np.nan)
    exp[['R0','G0','B0']] = exp[['R0','G0','B0']].div(tot, axis=0)
    # Errors per well
    err_raw = np.sqrt((raw_norm["R'"]-exp['R0'])**2 + (raw_norm["G'"]-exp['G0'])**2 + (raw_norm["B'"]-exp['B0'])**2)
    err_lin = np.sqrt((lin_norm["R'"]-exp['R0'])**2 + (lin_norm["G'"]-exp['G0'])**2 + (lin_norm["B'"]-exp['B0'])**2)
    per_well['err_raw'] = err_raw
    per_well['err_lin'] = err_lin
    # Group-wise summary
    summary = per_well.groupby('group_id')[['err_raw','err_lin']].mean().round(4)
    print('Average normalized RGB error vs expected (per group):')
    print(summary)
    overall = per_well[['err_raw','err_lin']].mean().round(4)
    print('\nOverall average error:')
    print(overall)
    better = 'linearized (sRGB inverse)' if overall['err_lin'] < overall['err_raw'] else 'raw 8-bit normalization'
    print(f"\nMethod with lower overall error: {better}")

if __name__ == '__main__':
    folder = sys.argv[1]
    expected = sys.argv[2] if len(sys.argv) > 2 else 'dominant'
    main(folder, expected)
