import argparse
import os
import time
from datetime import datetime
from typing import Tuple

import cv2
import numpy as np


def fourcc_to_str(fourcc: int) -> str:
    return "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def srgb_to_linear_channel(v_norm: np.ndarray) -> np.ndarray:
    """Decode sRGB to linear-light per channel.

    v_norm is in [0,1]. Returns linear-light in [0,1].
    """
    a = 0.055
    cutoff = 0.04045
    return np.where(
        v_norm <= cutoff,
        v_norm / 12.92,
        ((v_norm + a) / (1 + a)) ** 2.4,
    )


def estimate_srgb_like_gamma(frame_bgr_u8: np.ndarray) -> Tuple[float, float, float]:
    """Estimate whether the frame behaves like sRGB gamma-coded content.

    Computes luminance using three mappings and compares MSE:
      - linear (gamma=1): direct normalized BGR
      - sRGB decode: piecewise 2.4
      - pure power-law 2.2: v**2.2

    Returns (mse_linear, mse_gamma22, mse_ratio) where mse_ratio = mse_gamma22 / mse_linear.
    A ratio < ~0.6 suggests gamma-coded behavior consistent with sRGB/power-law.
    """
    # Normalize to [0,1]
    b = frame_bgr_u8[..., 0].astype(np.float32) / 255.0
    g = frame_bgr_u8[..., 1].astype(np.float32) / 255.0
    r = frame_bgr_u8[..., 2].astype(np.float32) / 255.0

    # Luminance coefficients (Rec. 709 / sRGB)
    w_r, w_g, w_b = 0.2126, 0.7152, 0.0722

    # Linear mapping (gamma=1)
    y_linear_assumed = w_r * r + w_g * g + w_b * b

    # sRGB decode (piecewise)
    r_lin = srgb_to_linear_channel(r)
    g_lin = srgb_to_linear_channel(g)
    b_lin = srgb_to_linear_channel(b)
    y_srgb_decoded = w_r * r_lin + w_g * g_lin + w_b * b_lin

    # Pure gamma=2.2 decode approximation
    gamma = 2.2
    y_gamma22 = w_r * (r ** gamma) + w_g * (g ** gamma) + w_b * (b ** gamma)

    # Compare to sRGB-decoded luminance (proxy for linear-light)
    def mse(a: np.ndarray, c: np.ndarray) -> float:
        return float(np.mean((a - c) ** 2))

    mse_linear = mse(y_linear_assumed, y_srgb_decoded)
    mse_gamma22 = mse(y_gamma22, y_srgb_decoded)
    ratio = (mse_gamma22 / mse_linear) if mse_linear > 1e-12 else 0.0
    return mse_linear, mse_gamma22, ratio


def capture_frame(device_index: int, backend: int | None, width: int | None, height: int | None) -> Tuple[np.ndarray, dict]:
    # Prefer DirectShow on Windows for stability
    cap = cv2.VideoCapture(device_index, backend if backend is not None else cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera at index {device_index}")

    # Try to ensure RGB conversion on capture
    try:
        cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
    except Exception:
        pass

    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Warmup frames
    for _ in range(5):
        cap.read()

    ok, frame = cap.read()
    if not ok or frame is None:
        cap.release()
        raise RuntimeError("Failed to read a frame from camera")

    props = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "fourcc": fourcc_to_str(int(cap.get(cv2.CAP_PROP_FOURCC))),
        "convert_rgb": int(cap.get(cv2.CAP_PROP_CONVERT_RGB)) if hasattr(cv2, "CAP_PROP_CONVERT_RGB") else None,
    }
    cap.release()
    return frame, props


def write_report(out_dir: str, report: str) -> None:
    ensure_dir(out_dir)
    with open(os.path.join(out_dir, "camera_srgb_check.txt"), "w", encoding="utf-8") as f:
        f.write(report)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify camera produces 8-bit sRGB-like frames")
    parser.add_argument("--device", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--width", type=int, default=None, help="Request frame width")
    parser.add_argument("--height", type=int, default=None, help="Request frame height")
    parser.add_argument("--backend", type=str, default="dshow", choices=["auto", "dshow", "msmf"], help="OpenCV backend")
    parser.add_argument("--out", type=str, default=None, help="Output directory for sample and report")
    parser.add_argument("--save-npy", action="store_true", help="Save raw numpy array alongside PNG")
    args = parser.parse_args()

    backend_map = {
        "auto": None,
        "dshow": cv2.CAP_DSHOW,
        "msmf": cv2.CAP_MSMF,
    }
    backend = backend_map.get(args.backend)

    # Default output path under repository output tree
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "output",
        "cnc_camera_test",
        timestamp,
        "camera_srgb_check",
    )
    ensure_dir(out_dir)

    t0 = time.time()
    frame, props = capture_frame(args.device, backend, args.width, args.height)
    dt = time.time() - t0

    # 8-bit & shape checks
    dtype_ok = frame.dtype == np.uint8
    shape_ok = frame.ndim == 3 and frame.shape[2] == 3
    min_val, max_val = int(frame.min()), int(frame.max())

    # sRGB-like gamma behavior estimate
    mse_linear, mse_gamma22, ratio = estimate_srgb_like_gamma(frame)

    # Save sample image
    sample_path = os.path.join(out_dir, "sample_frame.png")
    cv2.imwrite(sample_path, frame)
    if args.save_npy:
        np.save(os.path.join(out_dir, "sample_frame.npy"), frame)

    report_lines = [
        "Camera sRGB Check Report",
        f"Device Index: {args.device}",
        f"Backend: {args.backend}",
        f"Requested WxH: {args.width}x{args.height}",
        "",
        "Capture Properties:",
        f"  width: {props['width']}",
        f"  height: {props['height']}",
        f"  fps: {props['fps']:.2f}",
        f"  fourcc: {props['fourcc']}",
        f"  convert_rgb: {props['convert_rgb']}",
        f"  capture_time_s: {dt:.3f}",
        "",
        "Frame Checks:",
        f"  dtype_uint8: {dtype_ok}",
        f"  shape_3_channels: {shape_ok} ({frame.shape})",
        f"  value_range: min={min_val}, max={max_val}",
        "",
        "Gamma Behavior (luminance vs sRGB decode):",
        f"  mse_linear: {mse_linear:.6f}",
        f"  mse_gamma22: {mse_gamma22:.6f}",
        f"  ratio_gamma22_to_linear: {ratio:.3f}",
        "  Interpretation: ratio < 0.6 suggests sRGB-like gamma coding",
        "",
        f"Saved sample PNG to: {sample_path}",
        f"Output dir: {out_dir}",
    ]

    report_text = "\n".join(report_lines)
    print(report_text)
    write_report(out_dir, report_text)


if __name__ == "__main__":
    main()
    # No extra cleanup needed here; capture happens inside functions.