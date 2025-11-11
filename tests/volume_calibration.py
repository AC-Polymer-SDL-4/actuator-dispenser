from base_workflow import Liquid_Dispenser, start_workflow_logging
import time
import os
import pandas as pd

# Initialize dispenser
dispenser = Liquid_Dispenser(cnc_comport="COM4", actuator_comport="COM6", virtual=False, camera_index=1)
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

#TIMES = [0.05, 0.25, 0.5, 0.75, 1, 1.25] #times to try in seconds
#TIMES = [1]
VOLUMES = [0.025, 0.05, 0.1, 0.25, 0.5]
NUM_REPLICATES =  4
 #number of replicate dispenses per volume or time
well_counter = 0
MAX_WELLS = 24
SPEED = 32768 #32768

#buffer and blowout_vol aren't used! (have set to defaults)
BUFFER = 0.35  #extra time to push out in seconds
BLOWOUT_VOL = 0.28 #0.28 is default

#Dispensing by time calibration
# if (len(TIMES)*NUM_REPLICATES-well_counter) <= MAX_WELLS:
#     for t in TIMES:
#         for i in range(NUM_REPLICATES):
#             dispense_by_time(dispenser, source_location="reservoir_12", source_index=11,retract_time=t, dest_location="well_plate", dest_index=well_counter, speed=SPEED)
#             well_counter += 1
#             input(f"***Dispensed for {t} seconds, rep {i + 1}.*** Press Enter to continue to next dispense")
# else:
#     print(f"Not enough wells to dispense each of the volumes into a {MAX_WELLS} wellplate")

#Dispense by volume calibration
if (len(VOLUMES)*NUM_REPLICATES-well_counter) <= MAX_WELLS:
    for v in VOLUMES:
        for i in range(NUM_REPLICATES):
            dispenser.dispense_between(source_location="reservoir_12", source_index=11, dest_location="well_plate", dest_index=well_counter, transfer_vol=v, speed=SPEED, buffer_time=BUFFER, blowout_vol=BLOWOUT_VOL)
            well_counter += 1
            input(f"***Dispensed {v} mL: *** Press Enter to continue to next dispense")
else:
    print(f"Not enough wells to dispense each of the volumes into a {MAX_WELLS} wellplate")

