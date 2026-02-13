import sys
import time
import cv2
from pathlib import Path

def decode_fourcc(fourcc: int) -> str:
    return "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

def main(index: int = 0, out_dir: str | None = None):
    cap = cv2.VideoCapture(index, cv2.CAP_ANY)
    if not cap.isOpened():
        print(f"Failed to open camera index {index}")
        return
    # Warm up a bit
    for _ in range(5):
        cap.read()
        time.sleep(0.05)
    ok, frame = cap.read()
    if not ok or frame is None:
        print("Failed to capture a frame")
        cap.release()
        return
    h, w = frame.shape[:2]
    dtype = frame.dtype
    mn = int(frame.min())
    mx = int(frame.max())
    fmt = int(cap.get(cv2.CAP_PROP_FORMAT))
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print("Camera check:")
    print(f" - index: {index}")
    print(f" - frame shape: {h}x{w}x{frame.shape[2] if frame.ndim==3 else 1}")
    print(f" - dtype: {dtype}")
    print(f" - value range: [{mn}, {mx}]")
    print(f" - CAP_PROP_FORMAT: {fmt}")
    print(f" - FOURCC: {decode_fourcc(fourcc)} ({fourcc})")
    print(f" - FPS (reported): {fps}")
    print("Interpretation:")
    if dtype == 'uint8':
        print(" - Frame is 8-bit per channel (uint8).")
    else:
        print(" - Frame is not uint8; pipeline may not be 8-bit.")
    print(" - OpenCV typically decodes MJPG/YUY2 streams to BGR8 code values (display-encoded, sRGB-like).")
    if out_dir:
        p = Path(out_dir)
        p.mkdir(parents=True, exist_ok=True)
        out_path = p / "camera_check_frame.png"
        cv2.imwrite(str(out_path), frame)
        print(f"Saved test frame to: {out_path}")
    cap.release()

if __name__ == '__main__':
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    main(idx, out_dir)
