# Analysis Scripts

This folder contains the streamlined analysis tools for uncertainty workflow outputs.

- `uncertainty_plot_and_stats.py`: Primary analysis and plotting script. Generates trends, normalized channels (`R'`, `G'`, `B'`, LAB, HSV), dotted expected overlays (water-scaled `R*0.9`, `Y*0.9`, `B*0.9`), group stats, and ANOVA.
- `validate_normalized.py`: Sanity checks for `normalized_channels.csv` (ranges, sum-to-one where applicable).
- `concentration_calibration.py`: Fits a simple mixing model from normalized RGB to dye fractions; predicts fractions per well and outputs calibration plots.

Notes:
- Expected compositions are centralized in `uncertainty_plot_and_stats.get_expected_compositions()`.
- RGB normalization uses sRGB gamma decode to linear-light before computing fractions.

## Camera sRGB Check
Use `camera_srgb_check.py` to verify the camera delivers 8‑bit, 3‑channel frames and to estimate whether frames are sRGB‑like gamma coded.

Example:

```bash
python tests/analysis/camera_srgb_check.py --device 0 --backend dshow --width 1280 --height 720
```

What it does:
- Captures a frame, checks `uint8` dtype and 3‑channel shape.
- Records capture properties (width/height/fps/FourCC/convert_rgb).
- Saves a sample PNG and a text report under `output/cnc_camera_test/<timestamp>/camera_srgb_check/`.
- Compares luminance under linear vs sRGB decode vs pure gamma=2.2; a ratio (MSE_gamma22/MSE_linear) < 0.6 suggests sRGB‑like gamma behavior.

Notes:
- On Windows, `--backend dshow` typically yields stable capture of BGR8 frames.
- If you want to also save the raw numpy array, add `--save-npy`.

Deprecated helpers were removed to reduce redundancy. Use the main script and validators above for routine analysis.
