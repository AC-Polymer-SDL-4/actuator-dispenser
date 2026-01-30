import sys
import os
import time
import argparse
import logging
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

# Ensure parent tests directory and workspace root are on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from workflows.base_workflow import Liquid_Dispenser
from constants import (
    ACTUATOR_SPEED,
    MAX_TIME_S,
)


def _append_row(csv_path: str, row: dict):
    df = pd.DataFrame([row])
    header = not os.path.exists(csv_path)
    df.to_csv(csv_path, mode="a", header=header, index=False)


def dispense_volume_dispenser(dispenser: Liquid_Dispenser,
                              source_location: str,
                              source_index: int,
                              dest_location: str,
                              dest_index: int,
                              transfer_vol_ml: float,
                              blowout_vol_ml: float,
                              buffer_time_s: float,
                              speed: int):
    dispenser.dispense_between(
        source_location=source_location,
        source_index=source_index,
        dest_location=dest_location,
        dest_index=dest_index,
        transfer_vol=transfer_vol_ml,
        blowout_vol=blowout_vol_ml,
        buffer_time=buffer_time_s,
        speed=speed,
        mixing_vol=0,
        num_mixes=0,
    )
    # We rely on weighing to measure delivered volume; timings are internal.
    return {
        "mode": "dispenser",
        "speed": speed,
        "buffer_time_s": buffer_time_s,
        "blowout_vol_ml": blowout_vol_ml,
        "air_time_s": None,
        "retract_time_s": None,
        "extend_time_s": None,
    }


"""
Single-path validation helper

This script validates the embedded timing in dispenser.py by calling
`Liquid_Dispenser.dispense_between()` directly and measuring delivered mass.
Any previous 'direct' timing mode is removed to ensure we test production code.
"""


def parse_args():
    p = argparse.ArgumentParser(description="Volume validation: test dispenser.py timing by calling dispense_between() and weighing results.")
    p.add_argument("--volumes", type=str, default="0.10,0.15,0.20,0.25", help="Comma-separated target volumes (mL).")
    p.add_argument("--reps", type=int, default=4, help="Replicates per target volume.")
    p.add_argument("--speed", type=int, default=ACTUATOR_SPEED, help="Actuator speed [0-65535].")
    p.add_argument("--blowout", type=float, default=0.2843, help="Air buffer volume (mL).")
    p.add_argument("--buffer", type=float, default=0.25, help="Extra push-out time (s).")
    p.add_argument("--simulate", action="store_true", help="Run in virtual mode (no hardware).")
    p.add_argument("--src_loc", type=str, default="reservoir_12", help="Source location name.")
    p.add_argument("--src_idx", type=int, default=11, help="Source index.")
    p.add_argument("--dst_loc", type=str, default="well_plate", help="Destination location name.")
    p.add_argument("--dst_plate_wells", type=int, default=24, help="Total wells per plate for indexing.")
    return p.parse_args([] if hasattr(sys, 'ps1') else None)


def main():
    args = parse_args()
    volumes = [float(s) for s in args.volumes.split(",")]
    # Initialize dispenser
    dispenser = Liquid_Dispenser(cnc_comport="COM5", actuator_comport="COM3", virtual=args.simulate, camera_index=0, log_level=logging.INFO)
    dispenser.cnc_machine.Z_LOW_BOUND = -70
    dispenser.cnc_machine.home()

    # Output directory
    session_ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = Path("output/calibration") / f"volume_validation_dispenser_{session_ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "calibration_measurements_net.csv"

    # Iterate volumes and replicates, allocate wells sequentially by volume
    well_counter = 0
    for vol_idx, vol_ml in enumerate(volumes):
        for rep in range(args.reps):
            dest_well = well_counter % args.dst_plate_wells
            plate_index = well_counter // args.dst_plate_wells
            well_counter += 1

            # Baseline mass BEFORE
            baseline_in = input(
                f"V={vol_ml:.3f} mL → well {dest_well} (rep {rep + 1}/{args.reps}). Enter baseline mass BEFORE dispense (3 dp): "
            ).strip()

            # Perform dispensing via dispenser.py production path
            meta = dispense_volume_dispenser(
                dispenser,
                source_location=args.src_loc,
                source_index=args.src_idx,
                dest_location=args.dst_loc,
                dest_index=dest_well,
                transfer_vol_ml=vol_ml,
                blowout_vol_ml=args.blowout,
                buffer_time_s=args.buffer,
                speed=args.speed,
            )

            # Mass AFTER
            after_in = input(
                f"V={vol_ml:.3f} mL → well {dest_well} (rep {rep + 1}/{args.reps}). Enter mass AFTER dispense (3 dp): "
            ).strip()

            baseline_mass_g = None
            after_mass_g = None
            dispensed_mass_g = None
            dispensed_volume_ml = None
            try:
                baseline_mass_g = float(Decimal(baseline_in).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
                after_mass_g = float(Decimal(after_in).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
                dispensed_mass_g = float(Decimal(after_mass_g - baseline_mass_g).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
                dispensed_volume_ml = dispensed_mass_g  # assume 1 g/mL
                if dispensed_mass_g < 0:
                    print("Warning: net dispensed mass is negative; check inputs.")
            except Exception:
                print("Invalid mass inputs; row will record only metadata.")

            _append_row(str(csv_path), {
                        "calibration_type": "volume_dispenser",
                "volume_index": vol_idx,
                "plate_index": plate_index,
                "replicate": rep + 1,
                "well_index": dest_well,
                "target_volume_ml": vol_ml,
                "dispensed_mass_g": dispensed_mass_g if dispensed_mass_g is not None else None,
                "dispensed_volume_ml": dispensed_volume_ml if dispensed_volume_ml is not None else None,
                "measured_mass_g": after_mass_g if after_mass_g is not None else None,
                "baseline_mass_g": baseline_mass_g if baseline_mass_g is not None else None,
                "air_time_s": meta.get("air_time_s"),
                "retract_time_s": meta.get("retract_time_s"),
                "extend_time_s": meta.get("extend_time_s"),
                "buffer_time_s": meta.get("buffer_time_s"),
                "blowout_vol_ml": meta.get("blowout_vol_ml"),
                "speed": meta.get("speed"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            })

    print(f"Wrote: {csv_path}")
    print("Next: analyze delivered vs requested volumes and CV%.")


if __name__ == "__main__":
    main()
