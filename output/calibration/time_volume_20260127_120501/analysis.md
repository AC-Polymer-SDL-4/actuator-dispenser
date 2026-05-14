# Time → Net Mass Calibration Analysis

**Dataset:** output/calibration/time_volume_20260127_120501/calibration_measurements_net.csv

## Fit Summary
- k (g/s): 0.3811
- b (g): 0.0041
- R^2: 0.9877
- RMSE (g): 0.0161
- Seconds per gram (s/g): 2.6238
- N (rows): 48

## Per-Time Statistics (replicate variability)
Columns: time_s, N, mean_g, sd_g, cv_%, se_g, ci95_g

| time_s | N | mean_g | sd_g | cv_% | se_g | ci95_g |
| --- | --- | --- | --- | --- | --- | --- |
| 0.05 | 4.0 | 0.024 | 0.0012 | 4.81 | 0.0006 | 0.0011 |
| 0.16 | 4.0 | 0.0658 | 0.0067 | 10.12 | 0.0033 | 0.0065 |
| 0.27 | 4.0 | 0.1085 | 0.0029 | 2.66 | 0.0014 | 0.0028 |
| 0.38 | 4.0 | 0.148 | 0.0032 | 2.14 | 0.0016 | 0.0031 |
| 0.49 | 4.0 | 0.1868 | 0.0334 | 17.9 | 0.0167 | 0.0328 |
| 0.6 | 4.0 | 0.2258 | 0.0115 | 5.11 | 0.0058 | 0.0113 |
| 0.71 | 4.0 | 0.2802 | 0.0153 | 5.45 | 0.0076 | 0.015 |
| 0.82 | 4.0 | 0.317 | 0.015 | 4.73 | 0.0075 | 0.0147 |
| 0.93 | 4.0 | 0.3622 | 0.0247 | 6.82 | 0.0124 | 0.0242 |
| 1.04 | 4.0 | 0.4028 | 0.0211 | 5.24 | 0.0106 | 0.0207 |
| 1.15 | 4.0 | 0.4468 | 0.0157 | 3.52 | 0.0079 | 0.0154 |
| 1.25 | 4.0 | 0.4732 | 0.0286 | 6.04 | 0.0143 | 0.028 |

## Observations
- Strong linearity with high R^2; small intercept.
- Typical single-dispense SD ~0.015 g (median) and CV ~5%.
- Absolute SD increases with time (heteroscedasticity); relative CV generally mid-single digits.
- Some timings show elevated variability (e.g., spikes visible in table).

## Artifacts
- Plot: output/calibration/time_volume_20260127_120501/time_to_net_mass_fit.png
- Fit summary: output/calibration/time_volume_20260127_120501/time_net_mass_fit_summary.txt
- Per-time stats CSV: output/calibration/time_volume_20260127_120501/per_time_stats.csv