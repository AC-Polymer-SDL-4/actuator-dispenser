from cnc_machine import CNC_Machine

cnc = CNC_Machine(com = "COM4")

#option 1: Hard controls
for i in range (0, 24):
    cnc.move_to_location('well_plate', i) #move to each well plate spot
