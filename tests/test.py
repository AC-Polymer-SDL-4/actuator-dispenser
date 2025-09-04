from actuator_controller import ActuatorRemote
from cnc_machine import CNC_Machine
from dispenser import Liquid_Dispenser
import time
import os
import pandas as pd

# Initialize dispenser
dispenser = Liquid_Dispenser(cnc_comport="COM4", actuator_comport="COM3")

dispenser.dispense_condition(source_location="vial_rack", source_index=0, dest_location="vial_rack", dest_index=6, vol_pipet=1, air_time=0.7, buffer_time=1, speed=65520)
    