from base_workflow import Liquid_Dispenser
import time
import os
import pandas as pd

# Initialize dispenser
dispenser = Liquid_Dispenser(cnc_comport="COM4", actuator_comport="COM3")

# Constants
actuator_power = 65520
slope = 0.4295  # Time per mL (or mL per sec reciprocal)

# Setup DataFrame
data = {
    'well': list(range(24)),
    'yellow_vol': [0, 0, 0, 0, 0.1, 0.1, 0.1, 0.1, 0.2, 0.2, 0.2, 0.2, 0.3, 0.3, 0.3, 0.3, 0.4, 0.4, 0.4, 0.4, 0.5, 0.5, 0.5, 0.5],
    'blue_vol':   [0, 0.17, 0.33, 0.5, 0, 0.17, 0.33, 0.5, 0, 0.17, 0.33, 0.5, 0, 0.17, 0.33, 0.5, 0, 0.17, 0.33, 0.5, 0, 0.17, 0.33, 0.5],
}
df = pd.DataFrame(data)
df['water_vol'] = 1 - (df['yellow_vol'] + df['blue_vol'])

#yellow step
for i in range(24):
    if df.loc[i, 'yellow_vol'] > 0:
        dispenser.dispense_between(
            source_location="vial_rack",
            source_index=0,
            dest_location="well_plate",
            dest_index=i,
            vol_pipet=df.loc[i, 'yellow_vol'],
            air_time=0.5,
            buffer_time=1,
            speed=actuator_power
        )
        print(f"Dispensed yellow to well {i}")

dispenser.dispense_condition(
    source_location="vial_rack",
    source_index=4,  # Assuming index 1 is for water
    dest_location="vial_rack",  # Waste location
    dest_index=6,  # waste index
    vol_pipet=1,  # water volume
    air_time=0.7,
    buffer_time=1,
    speed=actuator_power
)

# BLUE step
for i in range(24):
    if df.loc[i, 'blue_vol'] > 0:
        dispenser.dispense_between(
            source_location="vial_rack",
            source_index=1,
            dest_location="well_plate",
            dest_index=i,
            vol_pipet=df.loc[i, 'blue_vol'],
            air_time=0.5,
            buffer_time=1,
            speed=actuator_power
        )
        print(f"Dispensed blue to well {i}")

dispenser.dispense_condition(
    source_location="vial_rack",
    source_index=4,  # Assuming index 1 is for water
    dest_location="vial_rack",  # Waste location
    dest_index=6,  # waste index
    vol_pipet=1,  # water volume
    air_time=0.7,
    buffer_time=1,
    speed=actuator_power
)

# WATER step 
for i in range(24):
    if df.loc[i, 'water_vol'] > 0:
        dispenser.dispense_between(
            source_location="vial_rack",
            source_index=2,
            dest_location="well_plate",
            dest_index=i,
            vol_pipet=df.loc[i, 'water_vol'],
            air_time=0.5,
            buffer_time=1,
            speed=actuator_power
        )
        print(f"Dispensed water to well {i}")
    else:
        print(f"No water needed for well {i}")

# Capture images and compute average RGB values
for i in range(24):
    dispenser.cnc_machine.move_to_location("well_plate_camera", i)
    time.sleep(1)
    dispenser.cnc_machine.move_to_point(z=-30)
    time.sleep(1)
    dispenser.capture_and_save(i)

    # Once the image is saved, compute its average RGB in the center and automatically save the crop
    image_path = os.path.join(dispenser.output_dir, f"well_plate{i}.jpg")
    r, g, b = dispenser.average_rgb_in_center(image_path, 100, show_crop=True, save_crop=True)

    # Add RGB values to the existing DataFrame
    df.loc[i, 'Red'] = r
    df.loc[i, 'Green'] = g
    df.loc[i, 'Blue'] = b
    
dispenser.gif_maker()

dispenser.cleanup()

print (df)

# Save DataFrame to CSV
output_csv = "well_plate_data.csv"
df.to_csv(output_csv, index=False) 
# Save DataFrame to CSV
print(f"Data saved to {output_csv}")