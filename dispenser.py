from cnc_machine import CNC_Machine
from actuator_controller import ActuatorRemote
#from camera_controller import Camera 

#Represents the whole system, which combines the cnc_machine, light, and actuator

class Liquid_Dispenser:
    def __init__(self, cnc_comport, actuator_comport): #Initialize connection to the CNC machine and actuator
        self.cnc_machine = CNC_Machine(com = cnc_comport)
        self.actuator = ActuatorRemote(port = actuator_comport)
    def aspirate_at_location(self, location, location_index, time): #Move to location then withdraw
        self.cnc_machine.move_to_location(location, location_index, safe=True)
        self.actuator.retract(time)
        self.cnc_machine.move_to_point(z=0)
    def dispense_at_Location(self, location, location_index, time): #Move to location then dispense
        self.cnc_machine.move_to_location(location, location_index, safe=True)
        self.actuator.extend(time)
        self.cnc_machine.move_to_point(z=0)

