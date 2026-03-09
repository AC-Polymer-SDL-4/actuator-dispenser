import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

datasets = {
    'Low Yellow (more)': 'output/uncertainty_measurement_workflow/20260217_144032_automated_darkest_more_yellow_7_1_1',
    'High Yellow (most)': 'output/uncertainty_measurement_workflow/20260223_145629_automated_darkets_most_yellow_7_1_1_20_missing'
}

channels = ['LAB_B', 'RGB_G', 'LAB_A', 'B_prime', 'G_prime', 'A_prime']
display_names = ['LAB_B', 'RGB_G', 'LAB_A', "B'", "G'", "A'"]

print('R² for v_Y (Yellow Volume) - How well each channel differentiates yellow changes')
print('='*75)

results = {}
for ch, disp in zip(channels, display_names):
    results[disp] = []
    for ds_name, ds_path in datasets.items():
        try:
            df = pd.read_csv(f'{ds_path}/measurement_summary.csv')
            X = df[['v_Y']].values
            y = df[ch].values
            model = LinearRegression().fit(X, y)
            r2 = model.score(X, y)
            results[disp].append(r2)
        except Exception as e:
            results[disp].append(np.nan)
            print(f"Error loading {ds_path}: {e}")

print(f"{'Channel':<12} {'Low Yellow':<14} {'High Yellow':<14} {'Change':<10} {'Ratio'}")
print('-'*65)
for disp in display_names:
    low, high = results[disp]
    change = high - low
    ratio = high / low if low > 0.001 else float('inf')
    print(f'{disp:<12} {low:<14.3f} {high:<14.3f} {change:+.3f}      {ratio:.1f}x')
