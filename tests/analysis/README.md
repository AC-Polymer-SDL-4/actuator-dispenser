# Analysis Scripts

This folder contains the streamlined analysis tools for uncertainty workflow outputs.

- `uncertainty_plot_and_stats.py`: Primary analysis and plotting script. Generates trends, normalized channels (`R'`, `G'`, `B'`, LAB, HSV), dotted expected overlays (water-scaled `R*0.9`, `Y*0.9`, `B*0.9`), group stats, and ANOVA.
- `validate_normalized.py`: Sanity checks for `normalized_channels.csv` (ranges, sum-to-one where applicable).
- `concentration_calibration.py`: Fits a simple mixing model from normalized RGB to dye fractions; predicts fractions per well and outputs calibration plots.

Notes:
- Expected compositions are centralized in `uncertainty_plot_and_stats.get_expected_compositions()`.
- RGB normalization uses sRGB gamma decode to linear-light before computing fractions.

Deprecated helpers were removed or stubbed to reduce redundancy. Use the main script and validators above for routine analysis.

Deprecated:
- `camera_srgb_check.py` (stub): Use inline OpenCV snippets for occasional camera diagnostics.
- `compare_linear_vs_raw_normalization.py` (stub): RGB normalization and error metrics are available in the main script.
- `check_normalized_summary.py` (stub): Use `validate_normalized.py` and the main script outputs.
