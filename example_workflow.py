from dispenser import Liquid_Dispenser

cnc_dispenser = Liquid_Dispenser(cnc_comport = "COM3", actuator_comport= "COM7") 

#Titration
#Aspirate from vial 0 to wellplate spot 2
cnc_dispenser.aspirate_at_location('vial_rack', 0, 0.02)
cnc_dispenser.dispense_at_location('well_plate', 2, 0.02)

