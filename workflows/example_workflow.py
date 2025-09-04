from base_workflow import Liquid_Dispenser, start_workflow_logging

# Initialize workflow logging
workflow_logger = start_workflow_logging("example_workflow", virtual=True)
workflow_logger.info("Starting example workflow - Basic titration demo")

# Initialize dispenser in virtual mode
cnc_dispenser = Liquid_Dispenser(cnc_comport="COM3", actuator_comport="COM7", virtual=True,z_low_bound=-70) 

# Titration workflow
workflow_logger.info("Beginning titration: aspirate from vial 0 to wellplate spot 2")

# Aspirate from vial 0 to wellplate spot 2
cnc_dispenser.dispense_between(
    source_location="vial_rack",
    source_index=0,
    dest_location="well_plate",
    dest_index=2,
    vol_pipet=0.02
)

workflow_logger.info("Example workflow completed successfully")
