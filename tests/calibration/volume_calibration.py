import sys
import os
import time
import argparse
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import logging

# Ensure parent tests directory is on sys.path to import base_workflow
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from base_workflow import Liquid_Dispenser, start_workflow_logging
from constants import (
    CALIBRATION_TIMES_S,
    CALIBRATION_REPLICATES,
    AIR_TIME_S,
    BUFFER_TIME_S,
    ACTUATOR_SPEED,
    MAX_TIME_S,
    SLOPE_SECONDS_PER_ML,
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
OUTPUT_DIR = os.path.join("output", "calibration", f"time_volume_{session_ts}")
os.makedirs(OUTPUT_DIR, exist_ok=True)
CSV_PATH = os.path.join(OUTPUT_DIR, "calibration_measurements.csv")

def _append_measurement(row: dict):
    df = pd.DataFrame([row])
    header = not os.path.exists(CSV_PATH)
    df.to_csv(CSV_PATH, mode="a", header=header, index=False)

def dispense_by_time(dispenser, source_location, source_index, retract_time, dest_location, dest_index, air_time=0.7, buffer_time=0.35, speed=32768):
    # Enforce retract time bounds
    if retract_time < RETRACT_MIN_TIME_S or retract_time > RETRACT_MAX_TIME_S:
        raise ValueError(f"Retract time {retract_time:.3f}s out of bounds [{RETRACT_MIN_TIME_S:.3f}, {RETRACT_MAX_TIME_S:.3f}]s")
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
    p = argparse.ArgumentParser(description="Time→Volume calibration runner")
    p.add_argument("--type", choices=["time", "volume"], default="time")
    p.add_argument("--times", type=str, default=",".join(str(t) for t in CALIBRATION_TIMES_S),
                   help="Comma-separated retract times in seconds (only for --type=time)")
    p.add_argument("--volumes", type=str, default="0.025,0.050,0.100,0.250,0.450",
                   help="Comma-separated volumes in mL (only for --type=volume)")
    p.add_argument("--reps", type=int, default=CALIBRATION_REPLICATES, help="Replicates per time/volume")
    p.add_argument("--air", type=float, default=AIR_TIME_S, help="Air buffer time (s)")
    p.add_argument("--buffer", type=float, default=BUFFER_TIME_S, help="Buffer time (s)")
    p.add_argument("--speed", type=int, default=ACTUATOR_SPEED, help="Actuator speed [0-65535]")
    return p.parse_args([] if hasattr(sys, 'ps1') else None)

def _parse_float_list(s):
    return [float(x) for x in s.split(',') if x.strip()]

# Defaults and parsed overrides
args = _parse_args()
CALIBRATION_TYPE = args.type  # 'time' or 'volume'
TIMES = _parse_float_list(args.times)
VOLUMES = _parse_float_list(args.volumes)

BUFFER = args.buffer  # extra time to push out in seconds (used in both time and volume-based calibration)
BLOWOUT_VOL = 0.28  # default (only used in volume-based calibration)
AIR_TIME = args.air  # default air buffer time (only used in time-based calibration)
SPEED = args.speed  # 32768 default, 65000 maximum speed

NUM_REPLICATES = args.reps  # number of replicate dispenses per time or volume
well_counter = 0  # starting well index
MAX_WELLS = 24  # max number of wells to use for calibration (24 for 24-well plate)

if CALIBRATION_TYPE == 'time':
    # Dispensing by time calibration using grouped wells per time
    total_required_wells = len(TIMES) * NUM_REPLICATES
    if total_required_wells <= MAX_WELLS:
        for time_idx, t in enumerate(TIMES):
            base_well = time_idx * NUM_REPLICATES
            for rep in range(NUM_REPLICATES):
                dest_well = base_well + rep
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
                # Prompt for measured mass increase (grams) to compute volume (mL)
                measured_mass = input(
                    f"t={t:.3f}s → well {dest_well} (rep {rep + 1}/{NUM_REPLICATES}). Enter measured mass in grams (4 dp): "
                ).strip()
                measured_volume_ml = None
                if measured_mass:
                    try:
                        mass_g = float(Decimal(measured_mass).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
                        measured_volume_ml = float(Decimal(mass_g).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
                    except ValueError:
                        print("Invalid mass input; skipping volume logging.")
                _append_measurement({
                    "calibration_type": "time",
                    "time_index": time_idx,
                    "replicate": rep + 1,
                    "well_index": dest_well,
                    "target_time_s": t,
                    "target_volume_ml": None,
                    "measured_volume_ml": measured_volume_ml,
                    "measured_mass_g": measured_volume_ml if measured_volume_ml is not None else None,
                    "air_time_s": meta["air_time_s"],
                    "buffer_time_s": meta["buffer_time_s"],
                    "speed": meta["speed"],
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
    else:
        print(f"Not enough wells: need {total_required_wells}, have {MAX_WELLS}")

elif CALIBRATION_TYPE == 'volume':
    # Dispense by volume calibration
    if (len(VOLUMES) * NUM_REPLICATES - well_counter) <= MAX_WELLS:
        for v in VOLUMES:
            for i in range(NUM_REPLICATES):
                # Pre-check: estimated retract time must be within bounds
                retract_est = v * SLOPE_SECONDS_PER_ML
                if retract_est < RETRACT_MIN_TIME_S or retract_est > RETRACT_MAX_TIME_S:
                    print(f"Target volume {v} mL implies retract {retract_est:.3f}s outside [{RETRACT_MIN_TIME_S:.3f}, {RETRACT_MAX_TIME_S:.3f}]s; skipping.")
                    continue
                dispenser.dispense_between(
                    source_location="reservoir_12",
                    source_index=11,
                    dest_location="well_plate",
                    dest_index=well_counter,
                    transfer_vol=v,
                    speed=SPEED,
                    buffer_time=BUFFER,
                    blowout_vol=BLOWOUT_VOL,
                )
                # Prompt for measured mass increase (grams) to compute delivered volume (mL)
                measured_mass = input(
                    f"***Dispensed {v} mL, rep {i + 1}.*** Enter measured mass increase in grams (or leave blank to skip): "
                ).strip()
                measured_volume_ml = None
                if measured_mass:
                    try:
                        mass_g = float(Decimal(measured_mass).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
                        measured_volume_ml = float(Decimal(mass_g).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
                    except ValueError:
                        print("Invalid mass input; skipping volume logging.")
                _append_measurement({
                    "calibration_type": "volume",
                    "replicate": i + 1,
                    "well_index": well_counter,
                    "target_time_s": None,
                    "target_volume_ml": v,
                    "measured_volume_ml": measured_volume_ml,
                    "measured_mass_g": measured_volume_ml if measured_volume_ml is not None else None,
                    "air_time_s": AIR_TIME,
                    "buffer_time_s": BUFFER,
                    "speed": SPEED,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                well_counter += 1
                input("Press Enter to continue to next dispense")
    else:
        print(f"Not enough wells to dispense each of the volumes into a {MAX_WELLS} wellplate")
