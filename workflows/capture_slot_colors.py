import argparse
import os
import time
from pathlib import Path
import logging
import numpy as np
import matplotlib.pyplot as plt

# Reuse existing dispenser + camera flow
from base_workflow import Liquid_Dispenser


def make_swatch_png(rgb: dict, title: str, out_path: Path):
    # rgb dict: {"R": float, "G": float, "B": float}
    r = float(rgb.get("R", 0.0)) / 255.0
    g = float(rgb.get("G", 0.0)) / 255.0
    b = float(rgb.get("B", 0.0)) / 255.0

    fig = plt.figure(figsize=(2.0, 2.0), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.imshow(np.ones((100, 100, 3)) * np.array([r, g, b])[None, None, :])
    ax.set_title(title, fontsize=8, color=(0.1, 0.1, 0.1))

    fig.savefig(out_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)


def capture_slots(slots, virtual=False, camera_index=0, square_size=1):
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path("output/slot_capture") / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    disp = Liquid_Dispenser(
        cnc_comport="COM5",
        actuator_comport="COM3",
        virtual=virtual,
        camera_index=camera_index,
        log_level=logging.INFO,
        output_dir=str(out_dir),
    )
    disp.cnc_machine.Z_LOW_BOUND = -70
    disp.cnc_machine.home()

    summary_rows = []
    measurement_rows = []  # measurement_summary-style rows

    for slot in slots:
        suffix = f"slot_{slot:02d}"
        # Capture colors like uncertainty workflow: RGB, LAB, HSV from center crop
        rgb = disp.get_image_color("well_plate_camera", slot, suffix, square_size=square_size, color_space="RGB", show_crop=False)
        lab = disp.get_image_color("well_plate_camera", slot, suffix, square_size=square_size, color_space="LAB", show_crop=False)
        hsv = disp.get_image_color("well_plate_camera", slot, suffix, square_size=square_size, color_space="HSV", show_crop=False)
        if rgb is None:
            print(f"Slot {slot}: capture failed")
            continue

        r = float(rgb.get("R", 0.0)) ; g = float(rgb.get("G", 0.0)) ; b = float(rgb.get("B", 0.0)) 
        swatch_path = out_dir / f"{suffix}_swatch.png"
        make_swatch_png(rgb, f"slot {slot}: RGB({r:.1f}, {g:.1f}, {b:.1f})", swatch_path)
        summary_rows.append({"slot": slot, "R": r, "G": g, "B": b, "swatch": str(swatch_path)})

        # Build measurement_summary-like row (single replicate → std=0)
        group_id = int(slot // 6) + 1
        measurement_rows.append({
            "well_index": slot,
            "group_id": group_id,
            "num_replicates": 1,
            "RGB_R_mean": r,
            "RGB_R_std": 0.0,
            "RGB_G_mean": g,
            "RGB_G_std": 0.0,
            "RGB_B_mean": b,
            "RGB_B_std": 0.0,
            "LAB_L_mean": float(lab.get("L", 0.0)) if isinstance(lab, dict) else 0.0,
            "LAB_L_std": 0.0,
            "LAB_A_mean": float(lab.get("A", 0.0)) if isinstance(lab, dict) else 0.0,
            "LAB_A_std": 0.0,
            "LAB_B_mean": float(lab.get("B", 0.0)) if isinstance(lab, dict) else 0.0,
            "LAB_B_std": 0.0,
            "HSV_H_mean": float(hsv.get("H", 0.0)) if isinstance(hsv, dict) else 0.0,
            "HSV_H_std": 0.0,
            "HSV_S_mean": float(hsv.get("S", 0.0)) if isinstance(hsv, dict) else 0.0,
            "HSV_S_std": 0.0,
            "HSV_V_mean": float(hsv.get("V", 0.0)) if isinstance(hsv, dict) else 0.0,
            "HSV_V_std": 0.0,
        })

    # Write a small CSV summary
    if summary_rows:
        import pandas as pd
        # Original simple summary
        df = pd.DataFrame(summary_rows)
        df.to_csv(out_dir / "slot_colors_summary.csv", index=False)

        # Measurement-style summary similar to uncertainty workflow
        if measurement_rows:
            df_measure = pd.DataFrame(measurement_rows)
            df_measure.to_csv(out_dir / "measurement_summary.csv", index=False)

        # Display all swatches at the end in a single figure
        # Build a simple grid layout based on the number of slots
        n = len(summary_rows)
        cols = min(4, n)
        rows = int(np.ceil(n / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(2.2*cols, 2.2*rows), dpi=160)
        if n == 1:
            axes = np.array([[axes]])
        elif rows == 1:
            axes = np.array([axes])
        # Flatten iterator over axes
        ax_list = axes.flatten()
        for i, row in enumerate(summary_rows):
            ax = ax_list[i]
            color = np.array([row["R"], row["G"], row["B"]], dtype=float) / 255.0
            ax.imshow(np.ones((50, 50, 3)) * color[None, None, :])
            ax.set_title(f"slot {row['slot']}: RGB({row['R']:.0f},{row['G']:.0f},{row['B']:.0f})", fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        # Hide any leftover axes
        for j in range(len(summary_rows), len(ax_list)):
            ax_list[j].axis('off')
        plt.tight_layout()
        plt.show()

    # Move back to a safe position
    try:
        disp.cnc_machine.move_to_point(z=0)
        disp.move_to_origin()
    except Exception:
        pass

    print(f"Saved outputs to: {out_dir}")


def main():
    ap = argparse.ArgumentParser(description="Capture color swatches at specified well_plate_camera slots")
    ap.add_argument("--slots", type=str, default="3,7,11,23", help="Comma-separated well indices to capture")
    ap.add_argument("--virtual", action="store_true", help="Run in virtual mode (no hardware)")
    ap.add_argument("--square", type=int, default=1, help="Square size for center crop (pixels); 1 = single pixel")
    ap.add_argument("--camera-index", type=int, default=0, help="Camera device index")
    args = ap.parse_args()

    slots = [int(s.strip()) for s in args.slots.split(",") if s.strip()]
    capture_slots(slots, virtual=args.virtual, camera_index=args.camera_index, square_size=args.square)


if __name__ == "__main__":
    main()
