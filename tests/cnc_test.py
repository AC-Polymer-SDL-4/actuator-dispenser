import time
from base_workflow import CNC_Machine

cnc = CNC_Machine(com = "COM5", z_low_bound=-70)

#option 1: Hard controls
# cnc.move_to_point(x=5, y=10, z=-25)
# cnc.move_to_point(0,0,5)
# cnc.move_to_point(z=0) #Use for this

#option 2: Location-based controls... Does the calculation for you (from location_status.yaml)
#cnc.move_to_location(location_name='vial_rack', location_index=0) #where? What position?

# for i in range (0, 24): #to test all 24 well plate positions
#     cnc.move_to_location(location_name='well_plate', i, safe = False) #move to each well plate spot, safe = False to skip safe height

#option 3: Home CNC machine
cnc.home()
cnc.close()
