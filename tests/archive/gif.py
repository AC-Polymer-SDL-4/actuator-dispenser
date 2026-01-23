from PIL import Image
import os
import re
from dispenser import Liquid_Dispenser

# Initialize dispenser
dispenser = Liquid_Dispenser(cnc_comport="COM4", actuator_comport="COM3")

# Create GIF using all images in the well_plate_photos folder
dispenser.gif_maker()

# Clean up the dispenser
dispenser.cleanup()
