from base_workflow import Liquid_Dispenser
import argparse
import os
import datetime


def parse_args():
    ap = argparse.ArgumentParser(description="Capture images at well_plate_camera slots")
    ap.add_argument("slots", nargs="*", type=int, default=[0, 1, 2], help="Slot indices to capture (e.g. 0 1 2)")
    ap.add_argument("--cnc", dest="cnc", default="COM5", help="CNC COM port (e.g. COM5)")
    ap.add_argument("--act", dest="act", default="COM3", help="Actuator COM port (e.g. COM3)")
    ap.add_argument("--camera-index", dest="camera_index", type=int, default=0, help="Camera device index")
    ap.add_argument("--virtual", dest="virtual", action="store_true", help="Run in virtual mode (no hardware)")
    ap.add_argument("--no-home", dest="no_home", action="store_true", help="Skip homing before capture")
    ap.add_argument("--square-size", dest="square_size", type=int, default=60, help="Center crop square size for color analysis")
    ap.add_argument("--show-crop", dest="show_crop", action="store_true", help="Display crop window during analysis")
    return ap.parse_args()


def main():
    args = parse_args()

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", "cnc_camera_test", ts)

    os.makedirs(out_dir, exist_ok=True)

    disp = Liquid_Dispenser(
        cnc_comport=args.cnc,
        actuator_comport=args.act,
        camera_index=args.camera_index,
        output_dir=out_dir,
        virtual=args.virtual,
    )

    try:
        if not args.no_home:
            disp.cnc_machine.home()

        for slot in args.slots:
            color = disp.get_image_color(
                location="well_plate_camera",
                location_index=slot,
                image_suffix=f"_slot{slot}",
                square_size=args.square_size,
                color_space="RGB",
                show_crop=args.show_crop,
            )
            print(f"Slot {slot}: {color}")

    finally:
        try:
            disp.cnc_machine.close()
        except Exception:
            pass
        try:
            disp.camera.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()
