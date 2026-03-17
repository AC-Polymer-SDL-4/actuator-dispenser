from base_workflow import Liquid_Dispenser, start_workflow_logging

# --- Config ---
VIRTUAL = False
WELL = 0
HCL_VIAL   = 0  # vial_rack_12 index
NAOH_VIAL  = 1  # vial_rack_12 index
WATER_VIAL = 2  # vial_rack_12 index (tip conditioning)
NUM_REPEATS = 10

logger = start_workflow_logging("titration", virtual=VIRTUAL)
dispenser = Liquid_Dispenser(cnc_comport="COM4", actuator_comport="COM3", virtual=VIRTUAL)
dispenser.cnc_machine.home()

# --- Initial HCl dispense (800 uL) ---
dispenser.dispense_between("vial_rack_12", HCL_VIAL, "well_plate", WELL, transfer_vol=0.8)
color = dispenser.get_image_color("well_plate_camera", WELL, "step_0")
logger.info(f"Step 0 (HCl baseline): {color}")
dispenser.rinse_needle("vial_rack_12", WATER_VIAL)

# --- Titration loop ---
for i in range(1, NUM_REPEATS + 1):
    dispenser.dispense_between("vial_rack_12", NAOH_VIAL, "well_plate", WELL, transfer_vol=0.1, mixing_vol=0.4)
    color = dispenser.get_image_color("well_plate_camera", WELL, f"step_{i}")
    logger.info(f"Step {i} (after {i * 100} uL NaOH): {color}")
    dispenser.rinse_needle("vial_rack_12", WATER_VIAL)

    
