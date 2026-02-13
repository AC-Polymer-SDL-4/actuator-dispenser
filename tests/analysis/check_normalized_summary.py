import sys
from pathlib import Path
import pandas as pd

def main(folder: str):
    f = Path(folder)
    norm_path = f / 'normalized_channels.csv'
    err_path = f / 'expected_rgb_error.csv'
    if not norm_path.exists():
        print('normalized_channels.csv not found at', norm_path)
        return
    df = pd.read_csv(norm_path)
    rgb = df[(df['color_space']=='RGB') & (df['channel'].isin(["R'","G'","B'"]))]
    summary = rgb.groupby(['group_id','channel'])['value'].mean().reset_index()
    pivot = summary.pivot(index='group_id', columns='channel', values='value')
    print('Measured normalized RGB (group means):')
    print(pivot.round(3))
    expected = {
        1: {'R':0.3,'Y':0.3,'B':0.3},
        2: {'R':0.7,'Y':0.1,'B':0.1},
        3: {'R':0.1,'Y':0.7,'B':0.1},
        4: {'R':0.1,'Y':0.1,'B':0.7},
    }
    rows = []
    for gid, comp in expected.items():
        tot = comp['R']+comp['Y']+comp['B']
        rows.append({
            'group_id': gid,
            "R'": comp['R']/tot,
            "G'": comp['Y']/tot,
            "B'": comp['B']/tot,
        })
    exp_df = pd.DataFrame(rows).set_index('group_id')
    print('\nExpected normalized fractions (R,Y->G,B):')
    print(exp_df.round(3))
    # Differences
    diff = (pivot - exp_df).round(3)
    print('\nDifference (measured - expected):')
    print(diff)
    if err_path.exists():
        edf = pd.read_csv(err_path)
        avg_err = edf.groupby('group_id')['rgb_error'].mean().round(4)
        print('\nAverage RGB normalized error per group:')
        print(avg_err)

if __name__ == '__main__':
    folder = sys.argv[1]
    main(folder)
