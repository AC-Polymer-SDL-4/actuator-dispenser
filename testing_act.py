from actuator_controller import ActuatorRemote
from cnc_machine import CNC_Machine
from dispenser import Liquid_Dispenser
import time

dispenser = Liquid_Dispenser(cnc_comport='COM4', actuator_comport='COM3')

# Ask user for starting mass
start_mass = float(input("Enter starting mass (before retraction): "))

retract_time = float(input("Enter fluid retraction time in seconds (e.g., 0.4): "))

# Set actuator power to a constant value
actuator_power = 65520

dispenser.dispense_between("vial_rack", 1, "vial_rack", 0, retract_time, speed=actuator_power)

dispenser.move_to_origin()

# Ask for new mass and compute volume dispensed
new_mass = float(input("Enter new mass (after dispensing): "))
volume = new_mass - start_mass
volume = round(volume, 2)  # Round to two decimal places
print(f"Calculated volume: {volume} g")

# Log the result
with open("mass_log.txt", "a") as f:
    f.write(f"Retraction time: {retract_time}s, Volume dispensed: {volume}g, Actuator power: {actuator_power}\n")
print("Volume logged.")