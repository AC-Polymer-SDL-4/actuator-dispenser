from base_workflow import Liquid_Dispenser, start_workflow_logging
import time
import os
import pandas as pd
import logging

SIMULATE = False

# Initialize dispenser
dispenser = Liquid_Dispenser(cnc_comport="COM5", actuator_comport="COM3", virtual=SIMULATE, camera_index=0, log_level=logging.INFO)
dispenser.cnc_machine.Z_LOW_BOUND=-70
dispenser.cnc_machine.home()

def dispense_by_time(dispenser, source_location, source_index, retract_time, dest_location, dest_index, air_time=0.7,buffer_time=0.35, speed=32768):
    dispenser.cnc_machine.move_to_location(source_location, source_index, safe=True)
                        
    dispenser.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
    dispenser.actuator.retract(air_time, speed=speed)

    dispenser.logger.debug("Moving down to aspirate liquid")
    #dispenser.cnc_machine.move_to_point(z=-64) #for reservoir_12
    dispenser.cnc_machine.move_to_aspirate_height(source_location)

    dispenser.logger.debug("Aspirating liquid: %.2f seconds", retract_time)
    dispenser.actuator.retract(retract_time, speed=speed)

    dispenser.logger.debug("Moving up from source")
    dispenser.cnc_machine.move_to_point(z=0)

    # Move to destination and dispense
    dispenser.logger.debug("Moving to destination: %s[%d]", dest_location, dest_index)
    dispenser.cnc_machine.move_to_location(dest_location, dest_index, safe=True)
    dispenser.cnc_machine.move_to_dispense_height(dest_location)

    total_dispense_time = air_time + retract_time + buffer_time #extra time to push out
    dispenser.logger.debug("Dispensing liquid: %.2f seconds total", total_dispense_time)
    dispenser.actuator.extend(total_dispense_time, speed=speed)

    dispenser.cnc_machine.move_to_point(z=0)

# CALIBRATION PARAMETERS
CALIBRATION_TYPE = 'volume' #'time' or 'volume'
TIMES = [0.05, 0.25, 0.5, 0.75, 1, 1.25] #times to try in seconds (for time-based calibration)
VOLUMES = [0.025, 0.05, 0.1, 0.25, 0.45] #volumes to try in mL (for volume-based calibration)

BUFFER = 0.25  #extra time to push out in seconds (used in both time and volume-based calibration)
BLOWOUT_VOL = 0.28 #0.28 is default (only used in volume-based calibration)
AIR_TIME = 0.7 #default air buffer time (only used in time-based calibration)
SPEED = 41000 #32768 is default, 65000 is maximum speed

NUM_REPLICATES =  4 #number of replicate dispenses per volume or time
well_counter = 0 #starting well index
MAX_WELLS = 24 #max number of wells to use for calibration (24 for 24-well plate)

if CALIBRATION_TYPE == 'time':
    # Dispensing by time calibration
    if (len(TIMES)*NUM_REPLICATES-well_counter) <= MAX_WELLS:
        for t in TIMES:
            for i in range(NUM_REPLICATES):
                dispense_by_time(dispenser, source_location="reservoir_12", source_index=11,retract_time=t, dest_location="well_plate", dest_index=well_counter, speed=SPEED, buffer_time=BUFFER, air_time=AIR_TIME)
                well_counter += 1
                input(f"***Dispensed for {t} seconds, rep {i + 1}.*** Press Enter to continue to next dispense")
    else:
        print(f"Not enough wells to dispense each of the volumes into a {MAX_WELLS} wellplate") 

elif CALIBRATION_TYPE == 'volume':
    # Dispense by volume calibration
    if (len(VOLUMES)*NUM_REPLICATES-well_counter) <= MAX_WELLS:
        for v in VOLUMES:
            for i in range(NUM_REPLICATES):
                dispenser.dispense_between(source_location="reservoir_12", source_index=11, dest_location="well_plate", dest_index=well_counter, transfer_vol=v, speed=SPEED, buffer_time=BUFFER, blowout_vol=BLOWOUT_VOL)
                well_counter += 1
                input(f"***Dispensed {v} mL, rep {i + 1}: *** Press Enter to continue to next dispense")
    else:
        print(f"Not enough wells to dispense each of the volumes into a {MAX_WELLS} wellplate")