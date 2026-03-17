"""
Stability and Sensitivity Analysis Plots

Generates:
1. Normalized std (std/range) plots for stability comparison
2. R² sensitivity plots for each channel vs dye volumes
3. Includes raw and normalized versions of RGB, HSV channels
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from pathlib import Path

# Default group compositions (volumes in mL)
DEFAULT_GROUP_COMPOSITIONS = {
    1: {'v_R': 0.3, 'v_Y': 0.3, 'v_B': 0.3},
    2: {'v_R': 0.7, 'v_Y': 0.1, 'v_B': 0.1},
    3: {'v_R': 0.1, 'v_Y': 0.7, 'v_B': 0.1},
    4: {'v_R': 0.1, 'v_Y': 0.1, 'v_B': 0.7},
}

# Channel ranges for normalization (std/range)
CHANNEL_RANGES = {
    # Raw channels
    'RGB_R': 255, 'RGB_G': 255, 'RGB_B': 255,
    'LAB_L': 100, 'LAB_A': 255, 'LAB_B': 255,
    'HSV_H': 360, 'HSV_S': 100, 'HSV_V': 100,
    # Normalized channels (0-1 range)
    "R'": 1.0, "G'": 1.0, "B'": 1.0,
    "L'": 1.0, "C'": 1.0, "h'": 1.0,
    "H'": 1.0, "S'": 1.0, "V'": 1.0,
}

# Raw channels
RAW_CHANNELS = ['RGB_R', 'RGB_G', 'RGB_B', 'LAB_L', 'LAB_A', 'LAB_B', 'HSV_H', 'HSV_S', 'HSV_V']

# Normalized channels
NORM_CHANNELS = ["R'", "G'", "B'", "L'", "C'", "h'", "H'", "S'", "V'"]


def load_group_compositions(dataset_path):
    """Load composition map from dataset output, falling back to defaults."""
    composition_map_path = os.path.join(dataset_path, "composition_map.csv")
    if not os.path.exists(composition_map_path):
        return DEFAULT_GROUP_COMPOSITIONS

    comp_df = pd.read_csv(composition_map_path)
    required_cols = {'group_id', 'v_R', 'v_Y', 'v_B'}
    if not required_cols.issubset(set(comp_df.columns)):
        return DEFAULT_GROUP_COMPOSITIONS

    mapping = {}
    for _, row in comp_df.iterrows():
        mapping[int(row['group_id'])] = {
            'v_R': float(row['v_R']),
            'v_Y': float(row['v_Y']),
            'v_B': float(row['v_B']),
        }
    return mapping


def load_data(dataset_path):
    """Load measurement summary and normalized channels."""
    summary_path = os.path.join(dataset_path, "measurement_summary.csv")
    norm_path = os.path.join(dataset_path, "normalized_channels.csv")
    
    summary_df = pd.read_csv(summary_path)
    
    group_compositions = load_group_compositions(dataset_path)

    # Add volume columns
    summary_df['v_R'] = summary_df['group_id'].map(lambda g: group_compositions[int(g)]['v_R'])
    summary_df['v_Y'] = summary_df['group_id'].map(lambda g: group_compositions[int(g)]['v_Y'])
    summary_df['v_B'] = summary_df['group_id'].map(lambda g: group_compositions[int(g)]['v_B'])
    
    # Load normalized channels if available
    norm_df = None
    if os.path.exists(norm_path):
        norm_df = pd.read_csv(norm_path)
        # Pivot to wide format for easier analysis
        norm_wide = norm_df.pivot_table(
            index=['group_id', 'well_index'], 
            columns='channel', 
            values='value'
        ).reset_index()
        
        # Add volume columns
        norm_wide['v_R'] = norm_wide['group_id'].map(lambda g: group_compositions[int(g)]['v_R'])
        norm_wide['v_Y'] = norm_wide['group_id'].map(lambda g: group_compositions[int(g)]['v_Y'])
        norm_wide['v_B'] = norm_wide['group_id'].map(lambda g: group_compositions[int(g)]['v_B'])
    else:
        norm_wide = None
    
    return summary_df, norm_wide


def compute_stability_metrics(summary_df, norm_df):
    """Compute normalized std (std/range) for all channels."""
    results = []
    
    # Raw channels from summary_df
    for group_id in range(1, 5):
        group_data = summary_df[summary_df['group_id'] == group_id]
        
        for channel in RAW_CHANNELS:
            std_col = f'{channel}_std'
            mean_col = f'{channel}_mean'
            
            if std_col in group_data.columns:
                # Average std across wells in this group
                avg_std = group_data[std_col].mean()
                avg_mean = group_data[mean_col].mean()
                
                # Normalized std
                norm_std = avg_std / CHANNEL_RANGES[channel]
                
                # CV%
                cv = (avg_std / avg_mean * 100) if avg_mean != 0 else np.nan
                
                results.append({
                    'group_id': group_id,
                    'channel': channel,
                    'channel_type': 'raw',
                    'avg_std': avg_std,
                    'avg_mean': avg_mean,
                    'norm_std': norm_std,
                    'cv_percent': cv
                })
    
    # Normalized channels from norm_df
    if norm_df is not None:
        for group_id in range(1, 5):
            group_data = norm_df[norm_df['group_id'] == group_id]
            
            for channel in NORM_CHANNELS:
                if channel in group_data.columns:
                    values = group_data[channel].values
                    std = np.std(values)
                    mean = np.mean(values)
                    
                    norm_std = std / CHANNEL_RANGES[channel]
                    cv = (std / mean * 100) if mean != 0 else np.nan
                    
                    results.append({
                        'group_id': group_id,
                        'channel': channel,
                        'channel_type': 'normalized',
                        'avg_std': std,
                        'avg_mean': mean,
                        'norm_std': norm_std,
                        'cv_percent': cv
                    })
    
    return pd.DataFrame(results)


def compute_sensitivity(summary_df, norm_df):
    """Compute R² for each channel vs dye volumes."""
    results = []
    
    # Raw channels
    for channel in RAW_CHANNELS:
        mean_col = f'{channel}_mean'
        if mean_col not in summary_df.columns:
            continue
            
        y = summary_df[mean_col].values.reshape(-1, 1)
        
        r2_dict = {'channel': channel, 'channel_type': 'raw'}
        
        # Individual R² for each dye
        for vol_col in ['v_R', 'v_Y', 'v_B']:
            x = summary_df[vol_col].values.reshape(-1, 1)
            model = LinearRegression().fit(x, y)
            r2 = r2_score(y, model.predict(x))
            r2_dict[f'R2_{vol_col}'] = r2
        
        # Aggregate R²
        X = summary_df[['v_R', 'v_Y', 'v_B']].values
        model = LinearRegression().fit(X, y)
        r2_agg = r2_score(y, model.predict(X))
        r2_dict['R2_aggregate'] = r2_agg
        
        results.append(r2_dict)
    
    # Normalized channels
    if norm_df is not None:
        for channel in NORM_CHANNELS:
            if channel not in norm_df.columns:
                continue
                
            y = norm_df[channel].values.reshape(-1, 1)
            
            r2_dict = {'channel': channel, 'channel_type': 'normalized'}
            
            for vol_col in ['v_R', 'v_Y', 'v_B']:
                x = norm_df[vol_col].values.reshape(-1, 1)
                model = LinearRegression().fit(x, y)
                r2 = r2_score(y, model.predict(x))
                r2_dict[f'R2_{vol_col}'] = r2
            
            X = norm_df[['v_R', 'v_Y', 'v_B']].values
            model = LinearRegression().fit(X, y)
            r2_agg = r2_score(y, model.predict(X))
            r2_dict['R2_aggregate'] = r2_agg
            
            results.append(r2_dict)
    
    return pd.DataFrame(results)


def compute_standardized_coefficients(summary_df, norm_df):
    """
    Compute standardized coefficients from multivariate regression.
    
    This is the CORRECT sensitivity metric because dye volumes are correlated
    (v_R + v_Y + v_B = constant), so single-variable R² is confounded.
    
    Standardized coefficients show the independent effect of each dye
    on each channel, controlling for the other dyes.
    """
    results = []
    scaler = StandardScaler()
    x_cols = ['v_R', 'v_Y']
    
    # Use K-1 predictors to avoid singular compositional design (v_R + v_Y + v_B = constant)
    X = summary_df[x_cols].values
    X_scaled = scaler.fit_transform(X)
    
    # Raw channels
    for channel in RAW_CHANNELS:
        mean_col = f'{channel}_mean'
        if mean_col not in summary_df.columns:
            continue
        
        y = summary_df[mean_col].values
        y_scaled = (y - y.mean()) / y.std() if y.std() > 0 else y - y.mean()
        
        model = LinearRegression().fit(X_scaled, y_scaled)
        full_r2 = r2_score(y_scaled, model.predict(X_scaled))

        coef_v_R = float(model.coef_[0])
        coef_v_Y = float(model.coef_[1])
        coef_v_B = -(coef_v_R + coef_v_Y)

        # Partial R² via nested models in identifiable space
        reduced_v_Y = LinearRegression().fit(X_scaled[:, [1]], y_scaled)
        r2_without_v_R = r2_score(y_scaled, reduced_v_Y.predict(X_scaled[:, [1]]))
        partial_r2_v_R = (full_r2 - r2_without_v_R) / (1 - r2_without_v_R) if (1 - r2_without_v_R) > 1e-12 else np.nan

        reduced_v_R = LinearRegression().fit(X_scaled[:, [0]], y_scaled)
        r2_without_v_Y = r2_score(y_scaled, reduced_v_R.predict(X_scaled[:, [0]]))
        partial_r2_v_Y = (full_r2 - r2_without_v_Y) / (1 - r2_without_v_Y) if (1 - r2_without_v_Y) > 1e-12 else np.nan

        coef_l2 = float(np.sqrt(coef_v_R**2 + coef_v_Y**2 + coef_v_B**2))
        
        results.append({
            'channel': channel,
            'channel_type': 'raw',
            'coef_v_R': coef_v_R,
            'coef_v_Y': coef_v_Y,
            'coef_v_B': coef_v_B,
            'coef_l2_contrast': coef_l2,
            'partial_r2_v_R': partial_r2_v_R,
            'partial_r2_v_Y': partial_r2_v_Y,
        })
    
    # Normalized channels
    if norm_df is not None:
        X_norm = norm_df[x_cols].values
        X_norm_scaled = scaler.fit_transform(X_norm)
        
        for channel in NORM_CHANNELS:
            if channel not in norm_df.columns:
                continue
            
            y = norm_df[channel].values
            y_scaled = (y - y.mean()) / y.std() if y.std() > 0 else y - y.mean()
            
            model = LinearRegression().fit(X_norm_scaled, y_scaled)
            full_r2 = r2_score(y_scaled, model.predict(X_norm_scaled))

            coef_v_R = float(model.coef_[0])
            coef_v_Y = float(model.coef_[1])
            coef_v_B = -(coef_v_R + coef_v_Y)

            reduced_v_Y = LinearRegression().fit(X_norm_scaled[:, [1]], y_scaled)
            r2_without_v_R = r2_score(y_scaled, reduced_v_Y.predict(X_norm_scaled[:, [1]]))
            partial_r2_v_R = (full_r2 - r2_without_v_R) / (1 - r2_without_v_R) if (1 - r2_without_v_R) > 1e-12 else np.nan

            reduced_v_R = LinearRegression().fit(X_norm_scaled[:, [0]], y_scaled)
            r2_without_v_Y = r2_score(y_scaled, reduced_v_R.predict(X_norm_scaled[:, [0]]))
            partial_r2_v_Y = (full_r2 - r2_without_v_Y) / (1 - r2_without_v_Y) if (1 - r2_without_v_Y) > 1e-12 else np.nan

            coef_l2 = float(np.sqrt(coef_v_R**2 + coef_v_Y**2 + coef_v_B**2))
            
            results.append({
                'channel': channel,
                'channel_type': 'normalized',
                'coef_v_R': coef_v_R,
                'coef_v_Y': coef_v_Y,
                'coef_v_B': coef_v_B,
                'coef_l2_contrast': coef_l2,
                'partial_r2_v_R': partial_r2_v_R,
                'partial_r2_v_Y': partial_r2_v_Y,
            })
    
    return pd.DataFrame(results)


def plot_stability_by_group(stability_df, output_dir, dataset_name):
    """Plot normalized std for each channel, grouped by group_id."""
    
    # Separate raw and normalized
    raw_df = stability_df[stability_df['channel_type'] == 'raw']
    norm_df = stability_df[stability_df['channel_type'] == 'normalized']
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Raw channels
    ax = axes[0]
    channels = RAW_CHANNELS
    x = np.arange(len(channels))
    width = 0.2
    
    for i, group in enumerate([1, 2, 3, 4]):
        group_data = raw_df[raw_df['group_id'] == group]
        values = [group_data[group_data['channel'] == ch]['norm_std'].values[0] 
                  if len(group_data[group_data['channel'] == ch]) > 0 else 0 
                  for ch in channels]
        ax.bar(x + i * width, values, width, label=f'Group {group}')
    
    ax.set_xlabel('Channel')
    ax.set_ylabel('Normalized Std (std / range)')
    ax.set_title('Raw Channels Stability')
    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(channels, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Normalized channels
    ax = axes[1]
    channels = [ch for ch in NORM_CHANNELS if ch in norm_df['channel'].values]
    if channels:
        x = np.arange(len(channels))
        
        for i, group in enumerate([1, 2, 3, 4]):
            group_data = norm_df[norm_df['group_id'] == group]
            values = [group_data[group_data['channel'] == ch]['norm_std'].values[0] 
                      if len(group_data[group_data['channel'] == ch]) > 0 else 0 
                      for ch in channels]
            ax.bar(x + i * width, values, width, label=f'Group {group}')
        
        ax.set_xlabel('Channel')
        ax.set_ylabel('Normalized Std (std / range)')
        ax.set_title('Normalized Channels Stability')
        ax.set_xticks(x + 1.5 * width)
        ax.set_xticklabels(channels, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle(f'Stability Analysis (std/range)\n{dataset_name}', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'stability_by_group.png'), dpi=150)
    plt.close()


def plot_stability_overall(stability_df, output_dir, dataset_name):
    """Plot average normalized std across all groups for each channel."""
    
    # Average across groups
    avg_stability = stability_df.groupby(['channel', 'channel_type'])['norm_std'].mean().reset_index()
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Combine raw and normalized
    all_channels = RAW_CHANNELS + [ch for ch in NORM_CHANNELS if ch in avg_stability['channel'].values]
    x = np.arange(len(all_channels))
    
    values = []
    colors = []
    for ch in all_channels:
        row = avg_stability[avg_stability['channel'] == ch]
        if len(row) > 0:
            values.append(row['norm_std'].values[0])
            colors.append('steelblue' if ch in RAW_CHANNELS else 'coral')
        else:
            values.append(0)
            colors.append('gray')
    
    bars = ax.bar(x, values, color=colors)
    
    ax.set_xlabel('Channel')
    ax.set_ylabel('Avg Normalized Std (std / range)')
    ax.set_title(f'Overall Stability Comparison\n{dataset_name}')
    ax.set_xticks(x)
    ax.set_xticklabels(all_channels, rotation=45, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='steelblue', label='Raw'),
                       Patch(facecolor='coral', label='Normalized')]
    ax.legend(handles=legend_elements)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'stability_overall.png'), dpi=150)
    plt.close()


def plot_sensitivity_heatmap(sensitivity_df, output_dir, dataset_name):
    """Plot R² heatmap for sensitivity analysis."""
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    for idx, (ch_type, ax) in enumerate([('raw', axes[0]), ('normalized', axes[1])]):
        df = sensitivity_df[sensitivity_df['channel_type'] == ch_type]
        
        if len(df) == 0:
            ax.set_title(f'{ch_type.title()} Channels - No Data')
            continue
        
        channels = df['channel'].tolist()
        data = df[['R2_v_R', 'R2_v_Y', 'R2_v_B', 'R2_aggregate']].values
        
        im = ax.imshow(data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
        
        ax.set_xticks(range(4))
        ax.set_xticklabels(['v_R', 'v_Y', 'v_B', 'Aggregate'])
        ax.set_yticks(range(len(channels)))
        ax.set_yticklabels(channels)
        
        # Add text annotations
        for i in range(len(channels)):
            for j in range(4):
                text = ax.text(j, i, f'{data[i, j]:.2f}',
                              ha='center', va='center', color='black', fontsize=9)
        
        ax.set_title(f'{ch_type.title()} Channels')
        ax.set_xlabel('Dye Volume')
        ax.set_ylabel('Channel')
    
    plt.suptitle(f'Sensitivity Analysis (R² - CONFOUNDED)\n{dataset_name}\nNote: Single-variable R² is confounded because dye volumes are correlated', fontsize=11)
    plt.tight_layout(rect=[0, 0, 0.92, 0.95])  # Leave space on right for colorbar
    plt.colorbar(im, ax=axes, label='R²', shrink=0.8)
    plt.savefig(os.path.join(output_dir, 'sensitivity_heatmap_r2_confounded.png'), dpi=150)
    plt.close()


def plot_coefficient_heatmap(coef_df, output_dir, dataset_name):
    """
    Plot standardized coefficient heatmap (CORRECT sensitivity metric).
    
    Coefficients show the independent effect of each dye on each channel,
    properly accounting for the correlation between dye volumes.
    """
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    
    for idx, (ch_type, ax) in enumerate([('raw', axes[0]), ('normalized', axes[1])]):
        df = coef_df[coef_df['channel_type'] == ch_type]
        
        if len(df) == 0:
            ax.set_title(f'{ch_type.title()} Channels - No Data')
            continue
        
        channels = df['channel'].tolist()
        data = df[['coef_v_R', 'coef_v_Y', 'coef_v_B']].values
        
        # Use diverging colormap centered at 0
        im = ax.imshow(data, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)
        
        ax.set_xticks(range(3))
        ax.set_xticklabels(['v_R (Red)', 'v_Y (Yellow)', 'v_B (Blue)'])
        ax.set_yticks(range(len(channels)))
        ax.set_yticklabels(channels)
        
        # Add text annotations
        for i in range(len(channels)):
            for j in range(3):
                val = data[i, j]
                color = 'white' if abs(val) > 0.5 else 'black'
                ax.text(j, i, f'{val:.2f}', ha='center', va='center', 
                       color=color, fontsize=10, fontweight='bold')
        
        ax.set_title(f'{ch_type.title()} Channels', fontsize=12)
        ax.set_xlabel('Dye Volume')
        ax.set_ylabel('Channel')
    
    plt.suptitle(f'Sensitivity Analysis (Standardized Coefficients - CORRECT)\n{dataset_name}\n'
                 f'+1 = dye increases channel by 1 std, -1 = dye decreases channel by 1 std', 
                 fontsize=11)
    
    # Add colorbar
    cbar = fig.colorbar(im, ax=axes, shrink=0.8, pad=0.02)
    cbar.set_label('Standardized Coefficient\n(positive=increases, negative=decreases)')
    
    plt.tight_layout(rect=[0, 0, 0.92, 0.95])
    plt.savefig(os.path.join(output_dir, 'sensitivity_heatmap_coefficients.png'), dpi=150)
    plt.close()


def plot_sensitivity_bars(sensitivity_df, output_dir, dataset_name):
    """Plot R² aggregate as bar chart (CONFOUNDED - kept for reference)."""
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Sort by R² aggregate
    df_sorted = sensitivity_df.sort_values('R2_aggregate', ascending=True)
    
    channels = df_sorted['channel'].tolist()
    r2_values = df_sorted['R2_aggregate'].tolist()
    colors = ['steelblue' if t == 'raw' else 'coral' for t in df_sorted['channel_type']]
    
    y = np.arange(len(channels))
    bars = ax.barh(y, r2_values, color=colors)
    
    ax.set_yticks(y)
    ax.set_yticklabels(channels)
    ax.set_xlabel('R² (Aggregate) - CONFOUNDED')
    ax.set_title(f'Sensitivity Ranking (R² - CONFOUNDED)\n{dataset_name}\nNote: Use coefficient heatmap for correct sensitivity')
    ax.set_xlim(0, 1)
    ax.grid(True, alpha=0.3, axis='x')
    
    # Add value labels
    for bar, val in zip(bars, r2_values):
        ax.text(val + 0.02, bar.get_y() + bar.get_height()/2, f'{val:.2f}',
               va='center', fontsize=9)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='steelblue', label='Raw'),
                       Patch(facecolor='coral', label='Normalized')]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'sensitivity_ranking_r2_confounded.png'), dpi=150)
    plt.close()


def plot_coefficient_bars(coef_df, output_dir, dataset_name):
    """
    Plot differentiation ranking based on coefficient L2 contrast norm.
    """
    
    # Use robust differentiation metric when available
    coef_df = coef_df.copy()
    if 'coef_l2_contrast' in coef_df.columns:
        coef_df['diff_metric'] = coef_df['coef_l2_contrast']
        x_label = 'Differentiation (L2 norm of compositional contrast coefficients)'
        title_metric = 'L2 Contrast Coefficient Norm'
    else:
        coef_df['diff_metric'] = coef_df[['coef_v_R', 'coef_v_Y', 'coef_v_B']].abs().max(axis=1)
        x_label = 'Max |Coefficient| (sensitivity to dye changes)'
        title_metric = 'Max Absolute Coefficient'
    
    # Also identify which dye has the max effect
    def get_max_dye(row):
        abs_coefs = {'v_R': abs(row['coef_v_R']), 'v_Y': abs(row['coef_v_Y']), 'v_B': abs(row['coef_v_B'])}
        return max(abs_coefs, key=abs_coefs.get)
    
    coef_df['dominant_dye'] = coef_df.apply(get_max_dye, axis=1)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Sort by differentiation metric
    df_sorted = coef_df.sort_values('diff_metric', ascending=True)
    
    channels = df_sorted['channel'].tolist()
    values = df_sorted['diff_metric'].tolist()
    
    # Color by dominant dye
    dye_colors = {'v_R': 'red', 'v_Y': 'gold', 'v_B': 'blue'}
    colors = [dye_colors[d] for d in df_sorted['dominant_dye']]
    
    # Edge color by channel type
    edge_colors = ['black' if t == 'raw' else 'gray' for t in df_sorted['channel_type']]
    
    y = np.arange(len(channels))
    bars = ax.barh(y, values, color=colors, edgecolor=edge_colors, linewidth=2)
    
    ax.set_yticks(y)
    ax.set_yticklabels(channels)
    ax.set_xlabel(x_label)
    ax.set_title(f'Sensitivity Ranking ({title_metric})\n{dataset_name}\nColor = dominant dye, Black edge = raw, Gray edge = normalized')
    ax.set_xlim(0, max(values) * 1.15 if len(values) > 0 else 1)
    ax.grid(True, alpha=0.3, axis='x')
    
    # Add value labels with dominant dye
    for bar, val, dye in zip(bars, values, df_sorted['dominant_dye']):
        ax.text(val + 0.02, bar.get_y() + bar.get_height()/2, f'{val:.2f} ({dye})',
               va='center', fontsize=9)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='red', label='v_R dominant'),
        Patch(facecolor='gold', label='v_Y dominant'),
        Patch(facecolor='blue', label='v_B dominant'),
    ]
    ax.legend(handles=legend_elements, loc='lower right')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'sensitivity_ranking_coefficients.png'), dpi=150)
    plt.close()


def plot_channel_vs_volume_scatter(summary_df, norm_df, output_dir, dataset_name):
    """Create scatter plots of channel values vs dye volumes with regression."""
    
    # Raw channels - 3x3 grid for 9 channels
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    axes = axes.flatten()
    
    colors = {'v_R': 'red', 'v_Y': 'gold', 'v_B': 'blue'}
    
    for i, channel in enumerate(RAW_CHANNELS):
        if i >= len(axes):
            break
        ax = axes[i]
        mean_col = f'{channel}_mean'
        
        if mean_col not in summary_df.columns:
            ax.set_visible(False)
            continue
        
        for vol_col, color in colors.items():
            x = summary_df[vol_col]
            y = summary_df[mean_col]
            
            slope, intercept, r_value, _, _ = stats.linregress(x, y)
            
            ax.scatter(x, y, c=color, alpha=0.7, s=50, label=f'{vol_col} (R²={r_value**2:.2f})')
            
            x_line = np.array([x.min(), x.max()])
            ax.plot(x_line, slope * x_line + intercept, c=color, linestyle='--', alpha=0.5)
        
        ax.set_title(channel)
        ax.set_xlabel('Volume (mL)')
        ax.set_ylabel('Mean Value')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.suptitle(f'Raw Channels vs Dye Volume\n{dataset_name}', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'channel_vs_volume_raw.png'), dpi=150)
    plt.close()
    
    # Normalized channels - 3x3 grid
    if norm_df is not None:
        available_norm = [ch for ch in NORM_CHANNELS if ch in norm_df.columns]
        if available_norm:
            fig, axes = plt.subplots(3, 3, figsize=(15, 12))
            axes = axes.flatten()
            
            for i, channel in enumerate(available_norm):
                if i >= len(axes):
                    break
                ax = axes[i]
                
                for vol_col, color in colors.items():
                    x = norm_df[vol_col]
                    y = norm_df[channel]
                    
                    slope, intercept, r_value, _, _ = stats.linregress(x, y)
                    
                    ax.scatter(x, y, c=color, alpha=0.7, s=50, label=f'{vol_col} (R²={r_value**2:.2f})')
                    
                    x_line = np.array([x.min(), x.max()])
                    ax.plot(x_line, slope * x_line + intercept, c=color, linestyle='--', alpha=0.5)
                
                ax.set_title(channel)
                ax.set_xlabel('Volume (mL)')
                ax.set_ylabel('Normalized Value')
                ax.legend(fontsize=8)
                ax.grid(True, alpha=0.3)
            
            # Hide unused axes
            for j in range(len(available_norm), len(axes)):
                axes[j].set_visible(False)
            
            plt.suptitle(f'Normalized Channels vs Dye Volume\n{dataset_name}', fontsize=12)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, 'channel_vs_volume_normalized.png'), dpi=150)
            plt.close()


def plot_stability_vs_sensitivity(stability_df, coef_df, output_dir, dataset_name):
    """
    Plot stability (x-axis, lower=better) vs differentiation (y-axis, higher=better).
    """
    
    # Average stability across groups for each channel
    avg_stability = stability_df.groupby(['channel', 'channel_type'])['norm_std'].mean().reset_index()
    
    # Compute robust differentiation metric
    coef_df = coef_df.copy()
    if 'coef_l2_contrast' in coef_df.columns:
        coef_df['differentiation_metric'] = coef_df['coef_l2_contrast']
        y_axis_label = 'Differentiation (L2 compositional contrast) — More Differentiating →'
    else:
        coef_df['differentiation_metric'] = coef_df[['coef_v_R', 'coef_v_Y', 'coef_v_B']].abs().max(axis=1)
        y_axis_label = 'Sensitivity (max |coefficient|) — More Differentiating →'
    
    # Merge stability with coefficients
    merged = pd.merge(avg_stability, coef_df, on=['channel', 'channel_type'])
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Define colors and markers
    raw_channels = ['RGB_R', 'RGB_G', 'RGB_B', 'LAB_L', 'LAB_A', 'LAB_B', 'HSV_H', 'HSV_S', 'HSV_V']
    norm_channels = ["R'", "G'", "B'", "L'", "C'", "h'", "H'", "S'", "V'"]
    
    # Color map for channel families
    color_map = {
        'RGB_R': 'red', 'RGB_G': 'green', 'RGB_B': 'blue',
        'LAB_L': 'gray', 'LAB_A': 'magenta', 'LAB_B': 'yellow',
        'HSV_H': 'cyan', 'HSV_S': 'orange', 'HSV_V': 'purple',
        "R'": 'red', "G'": 'green', "B'": 'blue',
        "L'": 'gray', "C'": 'magenta', "h'": 'yellow',
        "H'": 'cyan', "S'": 'orange', "V'": 'purple',
    }
    
    # Plot each point
    for _, row in merged.iterrows():
        channel = row['channel']
        x = row['norm_std']
        y = row['differentiation_metric']
        
        color = color_map.get(channel, 'black')
        marker = 'o' if row['channel_type'] == 'raw' else '^'
        
        ax.scatter(x, y, c=color, marker=marker, s=150, edgecolors='black', linewidths=1, zorder=5)
        
        # Add label
        ax.annotate(channel, (x, y), textcoords="offset points", xytext=(8, 5), 
                   fontsize=9, ha='left')
    
    # Add quadrant lines at median values
    median_x = merged['norm_std'].median()
    median_y = merged['differentiation_metric'].median()
    ax.axvline(x=median_x, color='gray', linestyle='--', alpha=0.5)
    ax.axhline(y=median_y, color='gray', linestyle='--', alpha=0.5)
    
    # Labels for quadrants (adjusted for reversed x-axis)
    ax.text(0.98, 0.98, 'IDEAL\n(stable + differentiating)', transform=ax.transAxes, 
            fontsize=10, verticalalignment='top', horizontalalignment='right', color='green', fontweight='bold')
    ax.text(0.02, 0.98, 'Differentiating\nbut unstable', transform=ax.transAxes,
            fontsize=10, verticalalignment='top', horizontalalignment='left', color='orange')
    ax.text(0.98, 0.02, 'Stable but\nnot differentiating', transform=ax.transAxes,
            fontsize=10, verticalalignment='bottom', horizontalalignment='right', color='orange')
    ax.text(0.02, 0.02, 'POOR\n(unstable + not differentiating)', transform=ax.transAxes,
            fontsize=10, verticalalignment='bottom', horizontalalignment='left', color='red')
    
    ax.set_xlabel('Stability (std/range) — More Stable →', fontsize=11)
    ax.set_ylabel(y_axis_label, fontsize=11)
    ax.set_title(f'Channel Quality: Stability vs Sensitivity\n{dataset_name}', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # Reverse x-axis so lower (better) stability is on the right
    ax.invert_xaxis()
    
    # Set axis limits with some padding - zoom in on the data
    ax.set_xlim(merged['norm_std'].max() * 1.2, 0)
    y_min = max(0, merged['differentiation_metric'].min() - 0.05)  # Start just below lowest point
    y_max = merged['differentiation_metric'].max() * 1.1 if len(merged) > 0 else 1
    ax.set_ylim(y_min, max(y_min + 0.1, y_max))
    
    # Add legend for marker types
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=10, 
               markeredgecolor='black', label='Raw channels'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='gray', markersize=10,
               markeredgecolor='black', label='Normalized channels'),
    ]
    ax.legend(handles=legend_elements, loc='lower left')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'stability_vs_sensitivity.png'), dpi=150)
    plt.close()
    
    # Also save the merged data
    merged.to_csv(os.path.join(output_dir, 'stability_sensitivity_combined.csv'), index=False)
    
    return merged


def analyze_dataset(dataset_path):
    """Run full analysis on a dataset."""
    print(f"\nAnalyzing: {dataset_path}")
    
    dataset_name = os.path.basename(dataset_path)
    output_dir = os.path.join(dataset_path, "analysis")
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data
    summary_df, norm_df = load_data(dataset_path)
    print(f"  Loaded {len(summary_df)} wells")
    
    # Compute metrics
    print("  Computing stability metrics...")
    stability_df = compute_stability_metrics(summary_df, norm_df)
    stability_df.to_csv(os.path.join(output_dir, 'stability_metrics.csv'), index=False)
    
    print("  Computing sensitivity (R² - confounded)...")
    sensitivity_df = compute_sensitivity(summary_df, norm_df)
    sensitivity_df.to_csv(os.path.join(output_dir, 'sensitivity_r2_confounded.csv'), index=False)
    
    print("  Computing standardized coefficients (CORRECT sensitivity)...")
    coef_df = compute_standardized_coefficients(summary_df, norm_df)
    coef_df.to_csv(os.path.join(output_dir, 'sensitivity_coefficients.csv'), index=False)
    
    # Generate plots
    print("  Generating stability plots...")
    plot_stability_by_group(stability_df, output_dir, dataset_name)
    plot_stability_overall(stability_df, output_dir, dataset_name)
    
    print("  Generating sensitivity plots...")
    plot_sensitivity_heatmap(sensitivity_df, output_dir, dataset_name)
    plot_coefficient_heatmap(coef_df, output_dir, dataset_name)
    plot_sensitivity_bars(sensitivity_df, output_dir, dataset_name)
    plot_coefficient_bars(coef_df, output_dir, dataset_name)
    
    print("  Generating scatter plots...")
    plot_channel_vs_volume_scatter(summary_df, norm_df, output_dir, dataset_name)
    
    print("  Generating stability vs sensitivity plot...")
    plot_stability_vs_sensitivity(stability_df, coef_df, output_dir, dataset_name)
    
    print(f"  Saved to: {output_dir}")
    
    # Print summary
    print("\n  === STABILITY SUMMARY (lower = more stable) ===")
    avg_stability = stability_df.groupby('channel')['norm_std'].mean().sort_values()
    for ch, val in avg_stability.items():
        print(f"    {ch}: {val:.4f}")
    
    print("\n  === SENSITIVITY SUMMARY (Standardized Coefficients) ===")
    print("  (Positive = dye increases channel, Negative = dye decreases channel)")
    print(f"  {'Channel':<10} {'v_R':<10} {'v_Y':<10} {'v_B':<10}")
    print("  " + "-"*40)
    for _, row in coef_df[coef_df['channel_type'] == 'raw'].iterrows():
        print(f"  {row['channel']:<10} {row['coef_v_R']:+.2f}      {row['coef_v_Y']:+.2f}      {row['coef_v_B']:+.2f}")
    
    return stability_df, sensitivity_df, coef_df


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]
    else:
        dataset_path = "output/uncertainty_measurement_workflow/20260213_073533_automated_darkest_more_yellow_7_1_1"
    
    analyze_dataset(dataset_path)
