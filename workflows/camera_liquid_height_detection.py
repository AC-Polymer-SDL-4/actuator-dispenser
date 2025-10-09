from base_workflow import Liquid_Dispenser, start_workflow_logging
import time
import os
import pandas as pd
import datetime

# Get workflow name (file name without extension)
workflow_name = os.path.splitext(os.path.basename(__file__))[0]
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join("output", workflow_name, timestamp)

MAX_WELLS = 24

# Initialize dispenser in virtual mode
virtual = False
dispenser = Liquid_Dispenser(cnc_comport="COM4", 
                             actuator_comport="COM3", 
                             camera_index=1, 
                             virtual=virtual,
                             output_dir=output_dir)
dispenser.cnc_machine.Z_LOW_BOUND = -70 #Just in this case

dispenser.cnc_machine.home()

conversion_well_heights = {0:0,1:2.65, 2:7.95, 3:5.3}


for i in range(MAX_WELLS):
    dispenser.cnc_machine.move_to_location(location_name="well_plate_camera", location_index = i, safe=True)
    time.sleep(1)
    mod = i % 4
    height = conversion_well_heights[mod]
    dispenser.camera.capture_and_save(f"_LLD_well{i}_{height}mm")


#closing
dispenser.cnc_machine.home()
dispenser.cnc_machine.close()
dispenser.camera.cleanup()