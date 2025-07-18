from cnc_machine import CNC_Machine

cnc = CNC_Machine(com = "COM3")

cnc.move_to_point(x=5, y=10, z=-25)
cnc.move_to_point(0,0,5)
cnc.move_to_point(z=0) #Use for this

cnc.move_to_location('vial_rack', 0)
