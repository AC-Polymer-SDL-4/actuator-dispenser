from base_workflow import Liquid_Dispenser, start_workflow_logging
# from actuator_controller import ActuatorRemote
# from cnc_machine import CNC_Machine
# from dispenser import Liquid_Dispenser
import time
import os
import pandas as pd

# Initialize dispenser
dispenser = Liquid_Dispenser(cnc_comport="COM4", actuator_comport="COM3", virtual=False)
dispenser.cnc_machine.Z_LOW_BOUND=-70
dispenser.cnc_machine.home()




RESERVOIRS = {
    'R': 0,      # Red colorant
    'B': 1,      # Yellow colorant  
    'Y': 2,      # Blue colorant
    'water': 3,  # Water/diluent
    'wash': 4,   # Wash solution
    'waste': 5,   # Waste container
}

res="reservoir_12"
# print(RESERVOIRS['waste'])

#dispenser.dispense_between(source_location="reservoir_12", source_index=4, dest_location="reservoir_12", dest_index=5, transfer_vol=0.5, air_time=0.7, buffer_time=1, speed=65520)


#dispenser.condition_needle(source_location=res, source_index=RESERVOIRS['water'], dest_location=res, dest_index=RESERVOIRS["waste"], num_conditions = 3)
#dispenser.rinse_needle(wash_location=res, wash_index=RESERVOIRS['wash'], num_mixes=4)
dispenser.dispense_between(source_location="reservoir_12", source_index=3, dest_location="well_plate", dest_index=23, transfer_vol=1.0, air_time=0.7, buffer_time=1, speed=65520, mixing_vol=0.4)

logger = start_workflow_logging("dispenser_test")

def create_mixture_at_well(dispenser, well_index, volumes_ml, logger):

    """
    Create a color mixture at the specified well by dispensing from reservoirs.
    
    Args:
        dispenser: Liquid_Dispenser instance
        well_index: Target well index (1-23, since 0 is target sample)
        volumes_ml: Dictionary of volumes in milliliters for each component
        logger: Logger instance
    """
    
    logger.info(f"Creating mixture at well {well_index} with volumes: {volumes_ml}")
    
    # Dispense each component
    component = 'water'
    volume_ml = 0.3
    reservoir_index = RESERVOIRS[component]
    logger.info(f"Dispensing {volume_ml:.3f}mL of {component} from reservoir {reservoir_index}")

    dispenser.condition_needle(
        source_location="reservoir_12", 
        source_index=reservoir_index,
        dest_location="reservoir_12",
        dest_index=RESERVOIRS["waste"],
        num_conditions = 1)
    

    dispenser.dispense_between(
        source_location="reservoir_12",
        source_index=reservoir_index,
        dest_location="well_plate", 
        dest_index=well_index,
        transfer_vol=volume_ml  # Now in mL as expected
    )

    dispenser.rinse_needle(
        wash_location="reservoir_12", 
        wash_index=RESERVOIRS['wash'], 
        num_mixes=3
    )
    
    # Small delay between dispenses
    time.sleep(0.5)

# create_mixture_at_well(dispenser, 0, 0 , logger)
# r,g,b = dispenser.get_image_rgb(location="well_plate_camera", location_index=0, square_size=75, image_suffix = "test_target_sample")
# print(f"R: {r}, G: {g}, B: {b}")
#dispenser.cnc_machine.home()
# volumes=[0.1,0.1,0.1,0.1, 0.2, 0.2, 0.2, 0.2, 0.3, 0.3, 0.3, 0.3, 0.4, 0.4, 0.4, 0.4, 0.5, 0.5, 0.5, 0.5]
# for i in range(len(volumes)):
#     #dispenser.condition_needle(source_location="reservoir_12", source_index=RESERVOIRS['water'], dest_location="reservoir_12", dest_index=RESERVOIRS['waste'])
#     vol = volumes[i]
#     dispenser.dispense_between(source_location="reservoir_12", source_index=RESERVOIRS['water'],transfer_vol=vol, dest_location="well_plate", dest_index=i)
#     dispenser.cnc_machine.move_to_point(z=0)
#     input("Press enter when ready for next dispense")

dispenser.cnc_machine.move_to_point(z=0)