import argparse
import os
import datetime
from camera import Camera

def parse_args():
    ap = argparse.ArgumentParser(description="Capture images using the camera only (no CNC)")
    ap.add_argument("--camera-index", type=int, default=0, help="Camera device index")
    ap.add_argument("--suffixes", nargs="*", default=["slot0","slot1","slot2"], help="Suffixes for images to capture")
    ap.add_argument("--output-subdir", default="cnc_camera_test", help="Output subfolder under output/")
    return ap.parse_args()


def main():
    args = parse_args()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("output", args.output_subdir, ts)
    os.makedirs(out_dir, exist_ok=True)

    cam = Camera(camera_index=args.camera_index, output_dir=out_dir, virtual=False)
    try:
        for suf in args.suffixes:
            fname = cam.capture_and_save(suf)
            print(f"Captured: {fname}")
    finally:
        cam.cleanup()

if __name__ == "__main__":
    main()
