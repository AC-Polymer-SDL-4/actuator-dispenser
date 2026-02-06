import sys
import os
import time
import argparse
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import logging

# Ensure parent tests directory and workspace root are on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from workflows.base_workflow import Liquid_Dispenser
from constants import (
    CALIBRATION_REPLICATES,
    AIR_TIME_S,
    BUFFER_TIME_S,
    ACTUATOR_SPEED,
    MAX_TIME_S,
    RETRACT_MIN_TIME_S,
    RETRACT_MAX_TIME_S,
)

SIMULATE = False

# Initialize dispenser

dispenser = Liquid_Dispenser(cnc_comport="COM5", actuator_comport="COM3", virtual=SIMULATE, camera_index=0, log_level=logging.INFO)
dispenser.cnc_machine.Z_LOW_BOUND = -70
dispenser.cnc_machine.home()

# Set up output logging for calibration runs
session_ts = time.strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = os.path.join("output", "calibration", f"time_volume_retest_{session_ts}")
os.makedirs(OUTPUT_DIR, exist_ok=True)
CSV_PATH = os.path.join(OUTPUT_DIR, "calibration_measurements.csv")


def _append_measurement(row: dict):
    df = pd.DataFrame([row])
    header = not os.path.exists(CSV_PATH)
    df.to_csv(CSV_PATH, mode="a", header=header, index=False)


def dispense_by_time(dispenser, source_location, source_index, retract_time, dest_location, dest_index, air_time=0.7, buffer_time=0.25, speed=32768):
    # Enforce retract time bounds with small tolerance to avoid FP edge issues
    EPS = 1e-3  # 1 ms tolerance
    if retract_time < (RETRACT_MIN_TIME_S - EPS):
        raise ValueError(f"Retract time {retract_time:.3f}s below minimum {RETRACT_MIN_TIME_S:.3f}s")
    if retract_time > (RETRACT_MAX_TIME_S + EPS):
        raise ValueError(f"Retract time {retract_time:.3f}s above maximum {RETRACT_MAX_TIME_S:.3f}s")
    if retract_time > RETRACT_MAX_TIME_S:
        dispenser.logger.info("Clamping retract_time from %.3fs to max %.3fs due to tolerance", retract_time, RETRACT_MAX_TIME_S)
        retract_time = RETRACT_MAX_TIME_S
    dispenser.cnc_machine.move_to_location(source_location, source_index, safe=True)

    dispenser.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
    dispenser.actuator.retract(air_time, speed=speed)

    dispenser.logger.debug("Moving down to aspirate liquid")
    dispenser.cnc_machine.move_to_aspirate_height(source_location)

    dispenser.logger.debug("Aspirating liquid: %.2f seconds", retract_time)
    dispenser.actuator.retract(retract_time, speed=speed)

    dispenser.logger.debug("Moving up from source")
    dispenser.cnc_machine.move_to_point(z=0)

    # Move to destination and dispense
    dispenser.logger.debug("Moving to destination: %s[%d]", dest_location, dest_index)
    dispenser.cnc_machine.move_to_location(dest_location, dest_index, safe=True)
    dispenser.cnc_machine.move_to_dispense_height(dest_location)

    total_dispense_time = air_time + retract_time + buffer_time  # extra time to push out
    # Ensure total extend time does not exceed MAX_TIME
    if total_dispense_time > MAX_TIME_S:
        # Reduce buffer_time to fit within MAX_TIME, but not below zero
        buffer_time = max(0.0, MAX_TIME_S - air_time - retract_time)
        total_dispense_time = air_time + retract_time + buffer_time
        dispenser.logger.info("Adjusted buffer_time to %.3fs to respect MAX_TIME=%.3fs", buffer_time, MAX_TIME_S)
    dispenser.logger.debug("Dispensing liquid: %.2f seconds total", total_dispense_time)
    dispenser.actuator.extend(total_dispense_time, speed=speed)

    dispenser.cnc_machine.move_to_point(z=0)
    return {
        "target_time_s": retract_time,
        "air_time_s": air_time,
        "buffer_time_s": buffer_time,
        "speed": speed,
    }


def _parse_args():
    p = argparse.ArgumentParser(description="Focused time→volume retest runner (0.50, 1.00 s)")
    p.add_argument("--reps", type=int, default=3, help="Replicates per time (default: 3)")
    p.add_argument("--air", type=float, default=AIR_TIME_S, help="Air buffer time (s)")
    p.add_argument("--buffer", type=float, default=BUFFER_TIME_S, help="Buffer time (s)")
    p.add_argument("--speed", type=int, default=ACTUATOR_SPEED, help="Actuator speed [0-65535]")
    return p.parse_args([] if hasattr(sys, 'ps1') else None)


# Defaults and parsed overrides
args = _parse_args()
TIMES = [0.50, 1.00]

BUFFER = args.buffer  # extra time to push out in seconds
AIR_TIME = args.air   # air buffer time
SPEED = args.speed    # actuator speed

NUM_REPLICATES = args.reps  # number of replicate dispenses per time
MAX_WELLS = 24

# Dispensing by time calibration using grouped wells per time
# Map times to wells in blocks of NUM_REPLICATES; reset every 24 wells (modulo mapping)
groups_per_plate = MAX_WELLS // NUM_REPLICATES  # e.g., 24-well plate with 4 reps -> 6 groups

for time_idx, t in enumerate(TIMES):
    base_well = (time_idx % groups_per_plate) * NUM_REPLICATES
    plate_index = time_idx // groups_per_plate
    for rep in range(NUM_REPLICATES):
        dest_well = base_well + rep
        # Prompt for baseline mass BEFORE dispensing (3 dp)
        baseline_in = input(
            f"t={t:.3f}s → well {dest_well} (rep {rep + 1}/{NUM_REPLICATES}). Enter baseline mass BEFORE dispense (3 dp): "
        ).strip()

        # Perform dispensing
        meta = dispense_by_time(
            dispenser,
            source_location="reservoir_12",
            source_index=11,
            retract_time=t,
            dest_location="well_plate",
            dest_index=dest_well,
            speed=SPEED,
            buffer_time=BUFFER,
            air_time=AIR_TIME,
        )

        # Apply tip conditioning and rinse between replicates (reuse approach from uncertainty workflow)
        try:
            # Choose conditioning set based on well region (first half uses set 1, second half set 2)
            condition_index = 2 if dest_well > (MAX_WELLS // 2) else 1
            # Reservoir indices as used in uncertainty workflow mapping
            CONDITION_WATER = 5 if condition_index == 1 else 7
            CONDITION_WASTE = 6 if condition_index == 1 else 8
            WASH_INDEX = 4
            # Pipet a reasonable conditioning volume
            vol_pipet = 0.30  # mL; bounded by device capability
            dispenser.condition_needle(
                source_location="reservoir_12",
                source_index=CONDITION_WATER,
                dest_location="reservoir_12",
                dest_index=CONDITION_WASTE,
                vol_pipet=vol_pipet,
                speed=SPEED,
                num_conditions=1,
            )
            dispenser.rinse_needle(
                wash_location="reservoir_12",
                wash_index=WASH_INDEX,
                num_mixes=3,
                speed=SPEED,
            )
            if not SIMULATE:
                time.sleep(0.5)
        except Exception as e:
            dispenser.logger.warning(f"Tip conditioning step failed or unsupported: {e}")

        # Prompt for mass AFTER dispensing (3 dp)
        after_in = input(
            f"t={t:.3f}s → well {dest_well} (rep {rep + 1}/{NUM_REPLICATES}). Enter mass AFTER dispense (3 dp): "
        ).strip()

        measured_volume_ml = None
        baseline_mass_g = None
        after_mass_g = None
        dispensed_mass_g = None
        dispensed_volume_ml = None
        if baseline_in and after_in:
            try:
                baseline_mass_g = float(Decimal(baseline_in).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
                after_mass_g = float(Decimal(after_in).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
                dispensed_mass_g = float(Decimal(after_mass_g - baseline_mass_g).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
                dispensed_volume_ml = dispensed_mass_g  # water assumption: 1 g == 1 mL
                measured_volume_ml = dispensed_volume_ml
                if dispensed_mass_g < 0:
                    print("Warning: net dispensed mass is negative; check inputs.")
            except ValueError:
                print("Invalid mass inputs; skipping volume logging.")

        _append_measurement({
            "calibration_type": "time",
            "time_index": time_idx,
            "plate_index": plate_index,
            "replicate": rep + 1,
            "well_index": dest_well,
            "target_time_s": t,
            "target_volume_ml": None,
            "measured_volume_ml": measured_volume_ml,
            "measured_mass_g": after_mass_g if after_mass_g is not None else None,
            "baseline_mass_g": baseline_mass_g if baseline_mass_g is not None else None,
            "after_mass_g": after_mass_g if after_mass_g is not None else None,
            "dispensed_mass_g": dispensed_mass_g if dispensed_mass_g is not None else None,
            "dispensed_volume_ml": dispensed_volume_ml if dispensed_volume_ml is not None else None,
            "air_time_s": meta["air_time_s"],
            "buffer_time_s": meta["buffer_time_s"],
            "speed": meta["speed"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })