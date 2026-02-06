import os
import sys

# Ensure project root on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from camera import Camera

# --- Setup: Create output folder ---
output_dir = "output/camera_test"
os.makedirs(output_dir, exist_ok=True)

def main():
	# Try default index 0; change if needed
	cam = Camera(camera_index=0, output_dir=output_dir, virtual=False)
	path = cam.capture_and_save("_test")
	print(f"Captured: {path}")
	cam.cleanup()

if __name__ == "__main__":
	main()
