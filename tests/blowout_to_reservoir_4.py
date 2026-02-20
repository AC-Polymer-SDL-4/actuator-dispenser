import os
import sys
import time
import argparse

# Ensure project root on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_workflow import Liquid_Dispenser, start_workflow_logging


def blowout_syringe_to_reservoir_4(dispenser: Liquid_Dispenser, logger, seconds: float = 2.2, speed: int = 32768,
                                    location: str = "reservoir_12", wash_index: int = 4):
    """
    Move to reservoir 4 (wash) and extend the actuator long enough to empty the syringe.

    Parameters:
    - seconds: duration to extend actuator for a full dispense (default ~2.2s for full stroke + buffer)
    - speed: actuator speed (0-65535)
    - location: location name used for wash station (default: reservoir_12)
    - wash_index: index of the wash station within the location (default: 4)
    """
    try:
        logger.info(f"Blowout: moving to {location}[{wash_index}] to empty syringe")
        dispenser.cnc_machine.move_to_location(location, wash_index, safe=True)
        dispenser.cnc_machine.move_to_dispense_height(location)
        logger.info("Blowout: extending actuator for %.2f seconds (speed=%d)", seconds, speed)
        dispenser.actuator.extend(seconds=seconds, speed=speed)
        dispenser.cnc_machine.move_to_point(z=0)
        logger.info("Blowout completed")
    except Exception as e:
        logger.error("Blowout failed: %s", e)
        try:
            dispenser.actuator.stop()
        except Exception:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(description="Empty syringe contents into reservoir 4 (wash)")
    parser.add_argument("--cnc", default="COM5", help="CNC machine COM port (default: COM5)")
    parser.add_argument("--actuator", default="COM3", help="Actuator COM port (default: COM3)")
    parser.add_argument("--camera-index", type=int, default=0, help="Camera device index (default: 0)")
    parser.add_argument("--seconds", type=float, default=2.2, help="Actuator extend duration in seconds (default: 2.2)")
    parser.add_argument("--speed", type=int, default=32768, help="Actuator speed (0-65535; default: 32768)")
    parser.add_argument("--location", default="reservoir_12", help="Location name for wash station (default: reservoir_12)")
    parser.add_argument("--wash-index", type=int, default=4, help="Wash station index in location (default: 4)")
    parser.add_argument("--virtual", action="store_true", help="Run in virtual mode (no hardware communication)")
    args = parser.parse_args()

    logger = start_workflow_logging("blowout_to_reservoir_4", virtual=args.virtual)
    logger.info("=== Blowout to reservoir 4 ===")
    logger.info("Virtual mode: %s", args.virtual)

    dispenser = Liquid_Dispenser(
        cnc_comport=args.cnc,
        actuator_comport=args.actuator,
        camera_index=args.camera_index,
        output_dir=os.path.join("output", "blowout_to_reservoir_4"),
        virtual=args.virtual,
        log_level=logger.level,
        log_filename=None,
    )

    try:
        # Optional safety: home axes before operation
        dispenser.cnc_machine.home()
        blowout_syringe_to_reservoir_4(
            dispenser, logger,
            seconds=args.seconds,
            speed=args.speed,
            location=args.location,
            wash_index=args.wash_index,
        )
    finally:
        try:
            dispenser.cnc_machine.move_to_point(z=0)
            dispenser.move_to_origin()
        except Exception:
            pass


if __name__ == "__main__":
    main()
