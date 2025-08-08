from cnc_machine import CNC_Machine

cnc = CNC_Machine(com = "COM4")

for i in range (0, 24):
    cnc.move_to_location('well_plate', i, safe = False) #move to each well plate spot
