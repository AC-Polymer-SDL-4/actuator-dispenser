from base_workflow import Liquid_Dispenser, start_workflow_logging
import time
import os
import pandas as pd
import datetime

# Get workflow name (file name without extension)
workflow_name = os.path.splitext(os.path.basename(__file__))[0]
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join("output", workflow_name, timestamp)

# Initialize dispenser in virtual mode
virtual = False
dispenser = Liquid_Dispenser(cnc_comport="COM5", 
                             actuator_comport="COM3", 
                             camera_index=0, 
                             virtual=virtual,
                             output_dir=output_dir)
dispenser.cnc_machine.Z_LOW_BOUND = -70 #Just in this case

dispenser.cnc_machine.home()

#df = pd.DataFrame()

# for i in range(6):
#     try:
#         r, g, b = dispenser.get_image_color("well_plate_camera", i, f"_{i}", square_size=60)
#         # Add RGB values to the existing DataFrame
#         df.loc[i, 'Red'] = r
#         df.loc[i, 'Green'] = g
#         df.loc[i, 'Blue'] = b

#     except Exception as e:
#         if not virtual:
#             print(f"Cannot capture image for well {i}: {e}")
#         continue

# Save DataFrame to CSV
# if not virtual:
#     print (df)
#     output_csv = "well_plate_data.csv"
#     df.to_csv(os.path.join(output_dir,output_csv), index=False) 
#     # Save DataFrame to CSV
#     print(f"Data saved to {output_csv}")


for i in range(24):
    color = dispenser.get_image_color("well_plate_camera",i, f"_{i}", square_size=60, show_crop=True)
    print(f"Color measurement well {i}: {color}")


#closing
dispenser.cnc_machine.close()
dispenser.camera.cleanup()