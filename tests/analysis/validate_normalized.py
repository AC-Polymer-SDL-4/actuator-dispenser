import sys
from pathlib import Path
import pandas as pd
import numpy as np

TOL = 1e-3  # tolerance for sum-to-one checks

SETS = {
    'RGB_scaled': ["R'","G'","B'"],
    'LAB_scaled': ["L'","C'","h'"],
    'LAB_sum': ["L'_sum","A'_sum","B'_sum"],
    'HSV_scaled': ["H'","S'","V'"],
    'HSV_sum': ["H'_sum","S'_sum","V'_sum"],
}


def check_set(df: pd.DataFrame, label: str, channels: list[str]) -> dict:
    issues = {
        'missing_channels': [],
        'out_of_range': 0,
        'sum_dev_count': 0,
        'sum_dev_max': 0.0,
        'nan_count': 0,
        'rows_checked': 0,
    }
    # Filter rows with those channels
    sub = df[df['channel'].isin(channels)].copy()
    if sub.empty or set(sub['channel'].unique()) != set(channels):
        issues['missing_channels'] = [c for c in channels if c not in set(sub['channel'].unique())]
        return issues
    # Pivot to rows per (group_id, well_index)
    pivot = sub.pivot_table(index=['group_id','well_index'], columns='channel', values='value')
    pivot = pivot.dropna(how='any')
    issues['nan_count'] = int(sub['value'].isna().sum())
    issues['rows_checked'] = int(pivot.shape[0])
    # Range checks
    vals = pivot[channels].to_numpy().ravel()
    issues['out_of_range'] = int(np.sum((vals < -1e-9) | (vals > 1 + 1e-9)))
    # Sum-to-one checks for sets that should sum to 1
    if label.endswith('scaled') and label.startswith('LAB'):
        # LAB_scaled does not need sum-to-one
        pass
    elif label.endswith('scaled') and label.startswith('HSV'):
        # HSV_scaled does not need sum-to-one
        pass
    else:
        sums = pivot[channels].sum(axis=1)
        dev = np.abs(sums - 1.0)
        issues['sum_dev_count'] = int(np.sum(dev > TOL))
        issues['sum_dev_max'] = float(dev.max()) if len(dev) else 0.0
    return issues


def main(folder: str):
    f = Path(folder)
    path = f / 'normalized_channels.csv'
    if not path.exists():
        print('normalized_channels.csv not found at', path)
        return
    df = pd.read_csv(path)
    # Basic schema checks
    assert set(['group_id','well_index','color_space','channel','value']).issubset(df.columns), 'Unexpected CSV schema'
    results = {}
    for label, chans in SETS.items():
        # Select color space rows
        if label.startswith('RGB'):
            cs_df = df[df['color_space']=='RGB']
        elif label.startswith('LAB'):
            cs_df = df[df['color_space']=='LAB']
        else:
            cs_df = df[df['color_space']=='HSV']
        results[label] = check_set(cs_df, label, chans)
    # Print summary
    for label, info in results.items():
        print(f"[{label}] rows_checked={info['rows_checked']} nan={info['nan_count']} out_of_range={info['out_of_range']} sum_dev_count={info['sum_dev_count']} sum_dev_max={info['sum_dev_max']:.6f} missing={info['missing_channels']}")

if __name__ == '__main__':
    main(sys.argv[1])
