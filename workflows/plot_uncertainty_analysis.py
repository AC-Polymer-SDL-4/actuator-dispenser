"""
Plot Uncertainty Analysis for Multiple Datasets

Generates visualization plots for uncertainty measurement workflow results:
1. Channel values by group (box plots)
2. Channel values vs dye volumes (scatter with regression)
3. Stability comparison (normalized std)
4. Sensitivity analysis (R² values)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# Datasets to analyze
DATASETS = [
    "output/uncertainty_measurement_workflow/20260217_144032_automated_darkest_more_yellow_7_1_1",
    "output/uncertainty_measurement_workflow/20260220_130448_automated_darkest_more_yellow_7_1_1",
    "output/uncertainty_measurement_workflow/20260220_152241_automated_darkest_more_yellow_7_1_1",
]

# Group compositions (volumes in mL)
GROUP_COMPOSITIONS = {
    1: {'v_R': 0.3, 'v_Y': 0.3, 'v_B': 0.3},
    2: {'v_R': 0.7, 'v_Y': 0.1, 'v_B': 0.1},
    3: {'v_R': 0.1, 'v_Y': 0.7, 'v_B': 0.1},
    4: {'v_R': 0.1, 'v_Y': 0.1, 'v_B': 0.7},
}

# Channel ranges for normalization
CHANNEL_RANGES = {
    'RGB_R': 255, 'RGB_G': 255, 'RGB_B': 255,
    'LAB_L': 100, 'LAB_A': 255, 'LAB_B': 255,
    'HSV_H': 360, 'HSV_S': 100, 'HSV_V': 100,
}

# Channels to analyze
CHANNELS = ['RGB_R', 'RGB_G', 'RGB_B', 'LAB_L', 'LAB_A', 'LAB_B', 'HSV_H', 'HSV_S', 'HSV_V']


def load_dataset(dataset_path):
    """Load measurement summary from a dataset."""
    summary_path = os.path.join(dataset_path, "measurement_summary.csv")
    raw_path = os.path.join(dataset_path, "uncertainty_measurements_raw.csv")
    
    summary_df = pd.read_csv(summary_path)
    raw_df = pd.read_csv(raw_path)
    
    # Add volume columns based on group_id
    for df in [summary_df, raw_df]:
        df['v_R'] = df['group_id'].map(lambda g: GROUP_COMPOSITIONS[g]['v_R'])
        df['v_Y'] = df['group_id'].map(lambda g: GROUP_COMPOSITIONS[g]['v_Y'])
        df['v_B'] = df['group_id'].map(lambda g: GROUP_COMPOSITIONS[g]['v_B'])
    
    return summary_df, raw_df


def plot_channel_by_group(raw_df, dataset_name, output_dir):
    """Create box plots of each channel by group."""
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    axes = axes.flatten()
    
    for i, channel in enumerate(CHANNELS):
        ax = axes[i]
        data = [raw_df[raw_df['group_id'] == g][channel].values for g in range(1, 5)]
        ax.boxplot(data, labels=['G1', 'G2', 'G3', 'G4'])
        ax.set_title(channel)
        ax.set_xlabel('Group')
        ax.set_ylabel('Value')
        ax.grid(True, alpha=0.3)
    
    plt.suptitle(f'Channel Values by Group\n{dataset_name}', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{dataset_name}_channel_by_group.png'), dpi=150)
    plt.close()


def plot_channel_vs_volume(summary_df, dataset_name, output_dir):
    """Create scatter plots of channel values vs dye volumes."""
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    axes = axes.flatten()
    
    colors = {'v_R': 'red', 'v_Y': 'gold', 'v_B': 'blue'}
    
    for i, channel in enumerate(CHANNELS):
        ax = axes[i]
        
        for vol_col, color in colors.items():
            x = summary_df[vol_col]
            y = summary_df[f'{channel}_mean']
            
            # Fit linear regression
            slope, intercept, r_value, _, _ = stats.linregress(x, y)
            
            ax.scatter(x, y, c=color, alpha=0.7, label=f'{vol_col} (R²={r_value**2:.2f})')
            
            # Plot regression line
            x_line = np.array([x.min(), x.max()])
            ax.plot(x_line, slope * x_line + intercept, c=color, linestyle='--', alpha=0.5)
        
        ax.set_title(channel)
        ax.set_xlabel('Volume (mL)')
        ax.set_ylabel('Mean Value')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle(f'Channel vs Dye Volume\n{dataset_name}', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{dataset_name}_channel_vs_volume.png'), dpi=150)
    plt.close()


def plot_stability_comparison(summary_df, dataset_name, output_dir):
    """Plot normalized standard deviation for each channel by group."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    groups = [1, 2, 3, 4]
    x = np.arange(len(CHANNELS))
    width = 0.2
    
    for i, group in enumerate(groups):
        group_data = summary_df[summary_df['group_id'] == group]
        norm_stds = []
        
        for channel in CHANNELS:
            std_col = f'{channel}_std'
            mean_std = group_data[std_col].mean()
            norm_std = mean_std / CHANNEL_RANGES[channel]
            norm_stds.append(norm_std)
        
        ax.bar(x + i * width, norm_stds, width, label=f'Group {group}')
    
    ax.set_xlabel('Channel')
    ax.set_ylabel('Normalized Std (std / range)')
    ax.set_title(f'Stability Comparison by Channel\n{dataset_name}')
    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(CHANNELS, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{dataset_name}_stability.png'), dpi=150)
    plt.close()


def calculate_sensitivity(summary_df):
    """Calculate R² for each channel vs each dye volume."""
    results = []
    
    for channel in CHANNELS:
        y = summary_df[f'{channel}_mean'].values.reshape(-1, 1)
        
        # Individual R² for each dye
        r2_dict = {'channel': channel}
        
        for vol_col in ['v_R', 'v_Y', 'v_B']:
            x = summary_df[vol_col].values.reshape(-1, 1)
            model = LinearRegression().fit(x, y)
            r2 = r2_score(y, model.predict(x))
            r2_dict[f'R2_{vol_col}'] = r2
        
        # Aggregate R² (multiple regression)
        X = summary_df[['v_R', 'v_Y', 'v_B']].values
        model = LinearRegression().fit(X, y)
        r2_agg = r2_score(y, model.predict(X))
        r2_dict['R2_aggregate'] = r2_agg
        
        results.append(r2_dict)
    
    return pd.DataFrame(results)


def plot_sensitivity_heatmap(sensitivity_df, dataset_name, output_dir):
    """Plot R² heatmap for sensitivity analysis."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    data = sensitivity_df[['R2_v_R', 'R2_v_Y', 'R2_v_B', 'R2_aggregate']].values
    
    im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    
    ax.set_xticks(range(4))
    ax.set_xticklabels(['v_R', 'v_Y', 'v_B', 'Aggregate'])
    ax.set_yticks(range(len(CHANNELS)))
    ax.set_yticklabels(CHANNELS)
    
    # Add text annotations
    for i in range(len(CHANNELS)):
        for j in range(4):
            text = ax.text(j, i, f'{data[i, j]:.2f}',
                          ha='center', va='center', color='black', fontsize=10)
    
    plt.colorbar(im, ax=ax, label='R²')
    ax.set_title(f'Sensitivity Analysis (R²)\n{dataset_name}')
    ax.set_xlabel('Dye Volume')
    ax.set_ylabel('Channel')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{dataset_name}_sensitivity_heatmap.png'), dpi=150)
    plt.close()
    
    return sensitivity_df


def main():
    """Generate plots for all datasets."""
    
    for dataset_path in DATASETS:
        print(f"\nProcessing: {dataset_path}")
        
        # Get dataset name from path
        dataset_name = os.path.basename(dataset_path)
        
        # Create output directory for plots
        output_dir = os.path.join(dataset_path, "plots")
        os.makedirs(output_dir, exist_ok=True)
        
        # Load data
        summary_df, raw_df = load_dataset(dataset_path)
        print(f"  Loaded {len(summary_df)} wells, {len(raw_df)} measurements")
        
        # Generate plots
        print("  Generating channel by group plots...")
        plot_channel_by_group(raw_df, dataset_name, output_dir)
        
        print("  Generating channel vs volume plots...")
        plot_channel_vs_volume(summary_df, dataset_name, output_dir)
        
        print("  Generating stability comparison...")
        plot_stability_comparison(summary_df, dataset_name, output_dir)
        
        print("  Calculating sensitivity analysis...")
        sensitivity_df = calculate_sensitivity(summary_df)
        plot_sensitivity_heatmap(sensitivity_df, dataset_name, output_dir)
        
        # Save sensitivity results
        sensitivity_df.to_csv(os.path.join(output_dir, f'{dataset_name}_sensitivity.csv'), index=False)
        
        print(f"  Plots saved to: {output_dir}")
        
        # Print sensitivity summary
        print("\n  Sensitivity Summary (R² aggregate):")
        for _, row in sensitivity_df.iterrows():
            print(f"    {row['channel']}: {row['R2_aggregate']:.3f}")


if __name__ == "__main__":
    main()
