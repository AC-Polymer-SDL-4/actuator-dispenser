from base_workflow import Liquid_Dispenser, start_workflow_logging
# from actuator_controller import ActuatorRemote
# from cnc_machine import CNC_Machine
# from dispenser import Liquid_Dispenser
import time
import os
import pandas as pd
import logging

# Initialize dispenser
dispenser = Liquid_Dispenser(cnc_comport="COM4", camera_index=1, actuator_comport="COM6", virtual=False, log_level=logging.INFO)
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
COLOR_SPACE = 'RGBA'  # 'RGB' or 'HSV' or 'LAB' or 'RGBA
# print(RESERVOIRS['waste'])

speed = 32768
dispenser.dispense_between(source_location="reservoir_12", source_index=11, dest_location="reservoir_12", dest_index=10, transfer_vol=0.5, buffer_time=0.35, speed=speed)


#dispenser.condition_needle(source_location=res, source_index=RESERVOIRS['water'], dest_location=res, dest_index=RESERVOIRS["waste"], num_conditions = 3)
#dispenser.rinse_needle(wash_location=res, wash_index=RESERVOIRS['wash'], num_mixes=3, vol_pipet=0.5)
#dispenser.dispense_between(source_location="reservoir_12", source_index=11, dest_location="well_plate", dest_index=0, transfer_vol=0.5, blowout_vol=0.3, buffer_time=1.25)

# c = dispenser.get_image_color(location="well_plate_camera", location_index=0, image_suffix="test", square_size=60, color_space=COLOR_SPACE)
# print("The well was:", c)
# dispenser.cnc_machine.move_to_point(z=0)