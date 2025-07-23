from cnc_machine import CNC_Machine

cnc = CNC_Machine(com = "COM4")

#Location-based controls... Does the calculation for you
cnc.move_to_location('vial_rack', 0) #where? What position?
