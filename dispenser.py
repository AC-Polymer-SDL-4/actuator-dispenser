from cnc_machine import CNC_Machine
from actuator_controller import ActuatorRemote
import os
import time
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import math  # Used for volume calculations
import cv2  # Used for the camera capture in __init__
import re

# Represents the whole system, which combines the CNC machine, actuator, and optionally a camera
# Has the actions that you generally want to take

class Liquid_Dispenser:
    def __init__(self, cnc_comport, actuator_comport, camera_index=0, output_dir="well_plate_photos"):
        # Initialize CNC machine and actuator
        self.cnc_machine = CNC_Machine(com=cnc_comport)
        self.actuator = ActuatorRemote(port=actuator_comport)

        # Camera setup (optional, used in capture_and_save)
        self.output_dir = output_dir
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Warm-up camera
        time.sleep(1.5)
        for _ in range(10):
            self.cap.read()
            time.sleep(0.1)

    def dispense_between(self, source_location, source_index, dest_location, dest_index, vol_pipet, air_time=0.7, buffer_time=1, speed=32768, mix=False):
        max_vol = 0.5 # hardcoded max volume in mL
        slope = 0.4295  # seconds per mL, based on calibration
        num_dispenses = math.ceil (vol_pipet / max_vol) #eg 1.7 / 0.5 = 3.4 rounded up is 4.0 dispenses
        dispense_vol = vol_pipet / num_dispenses #eg 1.7 / 4 = 0.425
        retract_time = dispense_vol / slope
        if mix == True:
            for i in range (num_dispenses):
                self.cnc_machine.move_to_location(source_location, source_index, safe=False)
                self.actuator.retract(air_time, speed=speed)
                self.cnc_machine.move_to_point(z=-70)
                self.actuator.retract(retract_time, speed=speed)
                self.cnc_machine.move_to_point(z=0)
                self.cnc_machine.move_to_location(dest_location, dest_index, safe=False)
                self.actuator.extend(air_time + retract_time + buffer_time, speed=speed)
                self.cnc_machine.move_to_point(z=-62)  # Move down to mix
                for i in range(3):  # Mix 3 times
                    self.actuator.retract(1, speed=speed)  # Retract to mix
                    self.actuator.extend(1, speed=speed)  # Extend to mix
                self.cnc_machine.move_to_point(z=0)  # Move back up
        else:
            for i in range (num_dispenses):
                self.cnc_machine.move_to_location(source_location, source_index, safe=False)
                self.actuator.retract(air_time, speed=speed)
                self.cnc_machine.move_to_point(z=-70)
                self.actuator.retract(retract_time, speed=speed)
                self.cnc_machine.move_to_point(z=0)
                self.cnc_machine.move_to_location(dest_location, dest_index, safe=False)
                self.actuator.extend(air_time + retract_time + buffer_time, speed=speed)

    def dispense_condition(self, source_location, source_index, dest_location="vial_rack", dest_index=6, vol_pipet=0.5, air_time=0.7, buffer_time=1, speed=32768):
        max_vol = 0.5 # hardcoded max volume in mL
        slope = 0.4295  # seconds per mL, based on calibration
        num_dispenses = math.ceil (vol_pipet / max_vol) #eg 1.7 / 0.5 = 3.4 rounded up is 4.0 dispenses
        dispense_vol = vol_pipet / num_dispenses #eg 1.7 / 4 = 0.425
        retract_time = dispense_vol / slope
        for i in range (3):
            self.cnc_machine.move_to_location(source_location, source_index, safe=False)
            self.actuator.retract(air_time, speed=speed)
            self.cnc_machine.move_to_point(z=-70)
            self.actuator.retract(retract_time, speed=speed)
            self.cnc_machine.move_to_point(z=0)
            self.cnc_machine.move_to_location(dest_location, dest_index, safe=False)
            self.actuator.extend(air_time + retract_time + buffer_time, speed=speed)
    
    def move_to_origin(self):
        self.cnc_machine.move_to_point(x=0, y=140, z=0)
        print("Moved CNC to safe position")

    def cleanup(self):
        self.cap.release()

    def capture_and_save(self, dest_index):
        for _ in range(3):
            self.cap.read()
            time.sleep(0.1)
        ret, frame = self.cap.read()
        if ret and frame is not None:
            filename = f"well_plate{dest_index}.jpg"
            path = os.path.join(self.output_dir, filename)
            cv2.imwrite(path, frame)
            print(f"Photo saved: {filename}")
        else:
            print(f"Failed to capture image for well_plate {dest_index}")

    def average_rgb_in_center(self, image_path, square_size=100, show_crop=True, save_crop=True, crop_folder="center_crops"):
        # Open the image using PIL and ensure it's in RGB mode
        image = Image.open(image_path).convert('RGB')
        width, height = image.size

        # Define the center crop box
        half_size = square_size // 2
        center_x, center_y = width // 2, height // 2
        left = max(center_x - half_size, 0)
        top = max(center_y - half_size, 0)
        right = min(center_x + half_size, width)
        bottom = min(center_y + half_size, height)

        # Crop the image and convert to numpy array
        cropped = image.crop((left, top, right, bottom))
        arr = np.array(cropped)

        # Compute average RGB over the cropped area
        avg_rgb = tuple(np.mean(arr, axis=(0, 1)))

        # Save the cropped image automatically
        if save_crop:
            # Create crop folder if it doesn't exist
            crop_dir = os.path.join(self.output_dir, crop_folder)
            os.makedirs(crop_dir, exist_ok=True)
            
            # Extract well number from the original image path
            filename = os.path.basename(image_path)
            # Use regex to extract well number from filename like "well_plate12.jpg"
            match = re.search(r'well_plate(\d+)', filename)
            if match:
                well_number = match.group(1)
                crop_filename = f"center_crop{well_number}.jpg"
            else:
                # Fallback naming if pattern doesn't match
                base_name = os.path.splitext(filename)[0]
                crop_filename = f"center_crop_{base_name}.jpg"
            
            crop_path = os.path.join(crop_dir, crop_filename)
            cropped.save(crop_path)
            print(f"Center crop saved: {crop_filename}")

        if show_crop:
            plt.imshow(cropped)
            plt.title("Center Crop")
            plt.axis("off")
            plt.show()

        print("Average RGB:", avg_rgb)
        return avg_rgb
    

    def gif_maker(self, folder_path="well_plate_photos", output_gif_path="well_plate_timelapse.gif"):
        # Function to extract number from filename (e.g., "12.jpg" -> 12)
        def extract_number(filename):
            match = re.search(r'\d+', filename)
            return int(match.group()) if match else float('inf')

        # Get image file paths and sort them by number
        image_files = sorted([
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))
        ], key=lambda f: extract_number(os.path.basename(f)))

        # Check for images
        if not image_files:
            raise ValueError("No image files found in the folder.")

        # Open all images and convert to RGB
        images = [Image.open(img_path).convert('RGB') for img_path in image_files]

        # Save as animated GIF
        images[0].save(
            output_gif_path,
            save_all=True,
            append_images=images[1:],
            duration=300,  # Adjust frame speed
            loop=0         # Loop forever
        )

        print(f"GIF saved as {output_gif_path}")
