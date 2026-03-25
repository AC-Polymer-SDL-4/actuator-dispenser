"""
Simple hardware test flow for CNC + actuator.

Usage:
	python "workflows/testing flow.py"
"""

from base_workflow import Liquid_Dispenser, start_workflow_logging


# Hardware config
VIRTUAL = False
CNC_COMPORT = "COM5"
ACTUATOR_COMPORT = "COM3"
SOURCE_WELL = 2
DEST_WELL = 8
TRANSFER_VOL_ML = 0.05


def main():
	logger = start_workflow_logging("testing_flow", virtual=VIRTUAL)
	dispenser = None

	try:
		logger.info("Initializing dispenser (CNC + actuator)...")
		dispenser = Liquid_Dispenser(cnc_comport=CNC_COMPORT, actuator_comport=ACTUATOR_COMPORT, virtual=VIRTUAL)

		logger.info("Homing CNC...")
		dispenser.cnc_machine.home()

		logger.info(
			"Transferring %.3f mL from vial_rack_12[%d] to vial_rack_12[%d]...",
			TRANSFER_VOL_ML, SOURCE_WELL, DEST_WELL
		)
		dispenser.dispense_between(
			source_location="vial_rack_12",
			source_index=SOURCE_WELL,
			dest_location="vial_rack_12",
			dest_index=DEST_WELL,
			transfer_vol=TRANSFER_VOL_ML,
		)

		logger.info("Returning Z to safe height...")
		dispenser.cnc_machine.move_to_point(z=0)

		logger.info("Testing flow complete.")

	finally:
		if dispenser is not None:
			try:
				dispenser.actuator.close()
			except Exception:
				pass
			try:
				dispenser.cnc_machine.close()
			except Exception:
				pass


if __name__ == "__main__":
	main()

