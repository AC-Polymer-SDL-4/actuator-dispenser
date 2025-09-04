import cv2
import os
import time
from cnc_machine import CNC_Machine

# --- Setup: Create output folder ---
output_dir = "well_plate_photos"
os.makedirs(output_dir, exist_ok=True)

# --- Initialize camera with DirectShow backend (more stable on Windows) ---
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Let camera auto‑adjust and flush initial frames
time.sleep(1.5)
for _ in range(10):
    cap.read()
    time.sleep(0.1)

# --- Initialize CNC machine ---
cnc = CNC_Machine(com="COM4")

# --- Loop through all 24 well positions ---
for i in range(24):
    print(f"\n🔄 Moving to well_plate {i} (working position)...")
    cnc.move_to_location('well_plate', i)
    time.sleep(1.5)              # let X/Y settle

    print(f"🎯 Moving to camera‑aligned position for well_plate {i}...")
    cnc.move_to_location('well_plate_camera', i)
    time.sleep(1.5)              # let X/Y settle

    print(f"⬇️ Lowering Z to –30 for photo...")
    cnc.move_to_point(z=-30)
    time.sleep(1.5)              # let Z settle

    # Flush a couple more frames so we definitely grab a fresh one
    for _ in range(3):
        cap.read()
        time.sleep(0.1)

    # Capture and save
    ret, frame = cap.read()
    if ret and frame is not None:
        filename = f"well_plate{i}.jpg"
        path = os.path.join(output_dir, filename)
        cv2.imwrite(path, frame)
        print(f"✅ Captured and saved: {filename}")
    else:
        print(f"❌ Failed to capture well_plate{i}.jpg")

# --- Cleanup ---
cap.release()
print("\n✅ All 24 well_plate images saved in “well_plate_photos/”.")
