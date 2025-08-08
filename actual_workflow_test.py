from dispenser import Liquid_Dispenser
import time
import os

dispenser = Liquid_Dispenser(cnc_comport="COM4", actuator_comport="COM3")

source_location = "vial_rack" # Location of the source 
source_index = 3  # Starting from vial 3
retract_time = 1.6  # seconds for retraction

for dest_index in range(4):  # Iterate through well plate spots 0 to 3
    dispenser.dispense_between(
        source_location=source_location,
        source_index=source_index, 
        dest_location="well_plate", # Location of the destination
        dest_index=dest_index,
        retract_time=retract_time,
        air_time=1, # seconds for air gap
        buffer_time=1, # seconds for buffer
        speed=32768
    )
    dispenser.cnc_machine.move_to_location("well_plate_camera", dest_index)
    time.sleep(1)
    dispenser.cnc_machine.move_to_point(z=-30)
    time.sleep(1)
    dispenser.capture_and_save(dest_index)

    # Once the image is saved, compute its average RGB in the center and show the crop
    image_path = os.path.join(dispenser.output_dir, f"well_plate{dest_index}.jpg")
    dispenser.average_rgb_in_center(image_path, 100, True)

dispenser.cleanup()
