"""Minimal set of actuator/calibration constants used across tests."""

# Hardware timing/limits
MAX_TIME_S = 2.20            # Maximum actuator time for a single dispense (s)
SLOPE_SECONDS_PER_ML = 0.4061 # Time per mL (s/mL)

# Actuator settings (kept constant during calibration)
ACTUATOR_SPEED = 32768       # 0–65535
# Set blowout so air time ≈ 0.70 s with current slope
BLOWOUT_VOL_ML = 0.2843      # Air buffer volume (mL) → AIR_TIME_S ≈ 0.7000 s
BUFFER_TIME_S = 0.25         # Extra push-out time (s)

# Derived values
AIR_TIME_S = BLOWOUT_VOL_ML / SLOPE_SECONDS_PER_ML
SYRINGE_MAX_VOL_ML = MAX_TIME_S * SLOPE_SECONDS_PER_ML
TRANSFER_MAX_VOL_ML = SYRINGE_MAX_VOL_ML - BLOWOUT_VOL_ML
MIN_VOLUME_ML = 0.025        # Minimum reliable volume per dispense

# Time bounds derived from MAX_TIME and air buffer
RETRACT_MIN_TIME_S = 0.0
RETRACT_MAX_TIME_S = MAX_TIME_S - AIR_TIME_S  # Max liquid retract time so air+liquid stays within MAX_TIME

# Recommended calibration set (retract times, seconds)
# Updated to 12 time stamps as requested
CALIBRATION_TIMES_S = [
	0.05, 0.16, 0.27, 0.38, 0.49, 0.60,
	0.71, 0.82, 0.93, 1.04, 1.15, 1.25,
]
CALIBRATION_REPLICATES = 4

# Derived expectations for the recommended times
CALIBRATION_EXPECTED_VOLUMES_ML = [
	round(t / SLOPE_SECONDS_PER_ML, 3) for t in CALIBRATION_TIMES_S
]
CALIBRATION_EXPECTED_EXTEND_S = [
	round(AIR_TIME_S + t + BUFFER_TIME_S, 3) for t in CALIBRATION_TIMES_S
]

