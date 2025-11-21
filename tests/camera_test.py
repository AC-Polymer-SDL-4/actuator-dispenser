import cv2
import os
import time
from base_workflow import Camera

# --- Setup: Create output folder ---
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

camera = Camera (0, output_dir)
camera.capture_and_save("_test")
camera.cleanup()
