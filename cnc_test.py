from cnc_machine import CNC_Machine

cnc = CNC_Machine(com = "COM3")

#option 1: Hard controls
cnc.move_to_point(x=5, y=10, z=-25)
cnc.move_to_point(0,0,5)
cnc.move_to_point(z=0) #Use for this

#Location-based controls... Does the calculation for you
cnc.move_to_location('vial_rack', 0) #where? What position?

for i in range (0, 24):
    cnc.move_to_location('well_plate', i) #move to each well plate spot
