import cv2
import os
import time
from base_workflow import Camera

# --- Setup: Create output folder ---
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

camera = Camera(camera_index=0, output_dir=output_dir) #change camera index if needed
camera.capture_and_save("_test")
camera.cleanup()
