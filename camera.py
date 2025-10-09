import cv2  # Used for the camera capture
import os
import time
import logging
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import re


class Camera:
    """
    Camera controller class for capturing and processing images.
    
    Features:
      - Virtual mode for testing without camera hardware
      - Structured logging (DEBUG/INFO/WARNING/ERROR)
      - Compatible with CNC_Machine logging system
    """
    
    def __init__(self, camera_index=0, output_dir="captured_images", virtual=False, log_level=logging.INFO):
        """
        Initialize the camera controller.
        
        Args:
            camera_index (int): Camera device index (usually 0 for default camera)
            output_dir (str): Directory to save captured images
            virtual (bool): If True, simulates camera operations without hardware
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        # Setup logging to match CNC_Machine format
        self.logger = logging.getLogger(__name__ + ".Camera")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.setLevel(log_level)
        
        self.output_dir = output_dir
        self.virtual = virtual
        self.camera_index = camera_index
        self.cap = None
        
        self.logger.info(
            "Camera initialized: index=%d, output_dir=%s, virtual=%s", 
            camera_index, output_dir, virtual
        )
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.debug("Output directory created/verified: %s", self.output_dir)
        
        if not self.virtual:
            try:
                # Initialize actual camera hardware
                self.logger.info("Initializing camera hardware on index %d", camera_index)
                self.cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) #minimize buffering
                
                # Warm-up camera
                self.logger.debug("Warming up camera...")
                time.sleep(1.5)
                for i in range(10):
                    ret, _ = self.cap.read()
                    if not ret:
                        self.logger.warning("Camera warm-up frame %d failed", i+1)
                    time.sleep(0.1)
                self.logger.info("Camera warm-up completed")
                
            except Exception as e:
                self.logger.error("Failed to initialize camera: %s", e)
                raise
        else:
            self.logger.info("[VIRTUAL] Camera hardware initialization skipped")
    def capture_and_save(self, dest_index):
        """
        Capture an image and save it to the output directory.
        
        Args:
            dest_index: Index/identifier for the image filename
            
        Returns:
            str: Filename of saved image, or None if capture failed
        """
        if self.virtual:
            # In virtual mode, just log what would happen
            filename = f"well_plate{dest_index}.jpg"
            self.logger.info("[VIRTUAL] Would capture and save image: %s", filename)
            return filename
            
        self.logger.debug("Capturing image for dest_index: %s", dest_index)
        
        try:
            # Take a few frames to stabilize
            for i in range(3):
                ret, _ = self.cap.read()
                if not ret:
                    self.logger.warning("Stabilization frame %d failed", i+1)
                time.sleep(0.2)
            
            # Capture the actual frame
            ret, frame = self.cap.read()
            if ret and frame is not None:
                filename = f"well_plate{dest_index}.jpg"
                path = os.path.join(self.output_dir, filename)
                cv2.imwrite(path, frame)
                self.logger.info("Photo saved: %s", filename)
                return path
            else:
                self.logger.error("Failed to capture frame for dest_index: %s", dest_index)
                return None
                
        except Exception as e:
            self.logger.error("Exception during image capture: %s", e)
            return None

    def cleanup(self):
        """
        Release camera resources.
        """
        if self.virtual:
            self.logger.info("[VIRTUAL] Camera cleanup - no hardware to release")
            return
            
        if self.cap is not None:
            self.logger.info("Releasing camera resources")
            self.cap.release()
            self.logger.debug("Camera released successfully")
        else:
            self.logger.warning("No camera to release")

    def average_rgb_in_center(self, image_path, square_size=100, show_crop=True, save_crop=True, crop_folder="center_crops", rgba = False):
        """
        Calculate the average RGB values in the center square of an image.
        
        Args:
            image_path (str): Path to the image file
            square_size (int): Size of the center square in pixels
            show_crop (bool): Whether to display the cropped image
            save_crop (bool): Whether to save the cropped image
            crop_folder (str): Folder name for saving cropped images
            
        Returns:
            tuple: Average RGB values (R, G, B)
        """
        self.logger.debug("Processing image: %s (square_size=%d)", image_path, square_size)
        
        try:
            # Open the image using PIL and ensure it's in RGB mode
            image = Image.open(image_path).convert('RGB')
            width, height = image.size
            self.logger.debug("Image dimensions: %dx%d", width, height)

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
            if rgba == False: 
                avg_rgb = tuple(np.mean(arr, axis=(0, 1)[:3])) #slice to only get the rgb values
                self.logger.info("Average RGB calculated: (%.1f, %.1f, %.1f)", *avg_rgb)
            else: 
                avg_rgb = tuple(np.mean(arr, axis=(0, 1))) #already gets alpha value too
                self.logger.info("Average RGBA calculated: (%.1f, %.1f, %.1f, %.1f)", *avg_rgb)

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
                self.logger.debug("Center crop saved: %s", crop_filename)

            if show_crop:
                self.logger.debug("Displaying cropped image")
                plt.imshow(cropped)
                plt.title("Center Crop")
                plt.axis("off")
                plt.show()

            return avg_rgb
            
        except Exception as e:
            self.logger.error("Failed to process image %s: %s", image_path, e)
            raise 

    def gif_maker(self, folder_path="well_plate_photos", output_gif_path="well_plate_timelapse.gif"):
        """
        Create an animated GIF from a folder of images.
        
        Args:
            folder_path (str): Path to folder containing images
            output_gif_path (str): Output path for the GIF file
        """
        self.logger.info("Creating GIF from folder: %s", folder_path)
        
        try:
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
                self.logger.error("No image files found in folder: %s", folder_path)
                raise ValueError("No image files found in the folder.")
                
            self.logger.debug("Found %d images to process", len(image_files))

            # Open all images and convert to RGB
            images = [Image.open(img_path).convert('RGB') for img_path in image_files]
            self.logger.debug("Loaded %d images successfully", len(images))

            # Save as animated GIF
            images[0].save(
                output_gif_path,
                save_all=True,
                append_images=images[1:],
                duration=300,  # Adjust frame speed (milliseconds per frame)
                loop=0         # Loop forever
            )

            self.logger.info("GIF saved successfully: %s", output_gif_path)
            
        except Exception as e:
            self.logger.error("Failed to create GIF: %s", e)
            raise