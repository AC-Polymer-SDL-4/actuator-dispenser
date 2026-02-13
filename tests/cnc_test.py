import time
from base_workflow import CNC_Machine
import time

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
# try:
# 	cnc.home()

# 	# Safe, small motion test near origin
# 	# 1) Ensure we're at safe Z
# 	cnc.move_to_point(z=0)

# 	# 2) Move a small distance in XY at safe Z
# 	cnc.move_to_point_safe(x=10, y=10, z=0, speed=1500)

# 	# 3) Dip slightly down in Z within bounds (e.g., -2 mm), then back up
# 	cnc.move_to_point(z=-2, speed=800)
# 	cnc.move_to_point(z=0, speed=800)

# 	# 4) Return to origin
# 	cnc.move_to_point_safe(x=0, y=0, z=0, speed=1500)
# finally:
# 	cnc.close()

# Added: Home and visit all 24 well plate positions safely, then return to origin
try:
	cnc.home()

	for i in range(12):
		print(f"Visiting well {i}")
		cnc.move_to_location(location_name='reservoir_12', location_index=i, safe=True, speed=1500)
		time.sleep(0.3)

	cnc.move_to_point_safe(x=0, y=0, z=0, speed=1500)
finally:
	cnc.close()
