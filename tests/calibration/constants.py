"""Minimal set of actuator/calibration constants used across tests."""

# Hardware timing/limits
MAX_TIME_S = 1.95            # Maximum actuator time for a single dispense (s)
SLOPE_SECONDS_PER_ML = 0.4061 # Time per mL (s/mL)

# Actuator settings (kept constant during calibration)
ACTUATOR_SPEED = 32768       # 0–65535
BLOWOUT_VOL_ML = 0.28        # Air buffer volume (mL)
BUFFER_TIME_S = 0.15         # Extra push-out time (s)

# Derived values
AIR_TIME_S = BLOWOUT_VOL_ML / SLOPE_SECONDS_PER_ML
SYRINGE_MAX_VOL_ML = MAX_TIME_S * SLOPE_SECONDS_PER_ML
TRANSFER_MAX_VOL_ML = SYRINGE_MAX_VOL_ML - BLOWOUT_VOL_ML
MIN_VOLUME_ML = 0.025        # Minimum reliable volume per dispense

# Time bounds derived from MAX_TIME and air buffer
RETRACT_MIN_TIME_S = 0.0
RETRACT_MAX_TIME_S = MAX_TIME_S - AIR_TIME_S  # Max liquid retract time so air+liquid stays within MAX_TIME

# Recommended calibration set (retract times, seconds)
CALIBRATION_TIMES_S = [0.05, 0.10, 0.12, 0.15, 0.18, 0.20]
CALIBRATION_REPLICATES = 4

# Derived expectations for the recommended times
CALIBRATION_EXPECTED_VOLUMES_ML = [
	round(t / SLOPE_SECONDS_PER_ML, 3) for t in CALIBRATION_TIMES_S
]
CALIBRATION_EXPECTED_EXTEND_S = [
	round(AIR_TIME_S + t + BUFFER_TIME_S, 3) for t in CALIBRATION_TIMES_S
]

# Optional finer resolution set
CALIBRATION_TIMES_FINE_S = [0.06, 0.08, 0.12, 0.16, 0.20]
