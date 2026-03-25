import cv2  # Used for the camera capture
import os
import time
import logging
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np
import re
from log_config import setup_logger, log_method_entry, log_method_exit, log_virtual_action
import torch
import gc

class Camera:
    """
    Camera controller class for capturing and processing images.
    
    Features:
      - Virtual mode for testing without camera hardware
      - Structured logging (DEBUG/INFO/WARNING/ERROR)
      - Compatible with CNC_Machine logging system
    """
    
    def __init__(self, camera_index=0, output_dir="captured_images", virtual=False, log_level=logging.INFO, log_filename=None,
                 anti_flicker_hz: int = 60, preferred_fourcc: str = "MJPG", target_fps: int = 30):
        """
        Initialize the camera controller.
        
        Args:
            camera_index (int): Camera device index (usually 0 for default camera)
            output_dir (str): Directory to save captured images
            virtual (bool): If True, simulates camera operations without hardware
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.output_dir = output_dir
        self.virtual = virtual
        self.camera_index = camera_index
        self.cap = None
        self.anti_flicker_hz = anti_flicker_hz
        self.preferred_fourcc = preferred_fourcc
        self.target_fps = target_fps
        
        # Setup centralized logging with virtual mode tagging
        self.logger = setup_logger("camera", virtual=virtual, log_level=log_level, log_filename=log_filename)

        self.logger.info(
            "Camera initialized: index=%d, output_dir=%s, virtual=%s", 
            camera_index, output_dir, virtual
        )
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.debug("Output directory created/verified: %s", self.output_dir)
        
        if not self.virtual:
            try:
                # Initialize actual camera hardware with backend fallbacks
                self.logger.info("Initializing camera hardware on index %d", camera_index)

                def try_open(idx: int):
                    backends = [getattr(cv2, 'CAP_DSHOW', None), getattr(cv2, 'CAP_MSMF', None), getattr(cv2, 'CAP_ANY', 0)]
                    for be in backends:
                        if be is None:
                            continue
                        cap = cv2.VideoCapture(idx, be)
                        if cap is not None and cap.isOpened():
                            self.logger.info("Camera opened with backend=%s on index %d", str(be), idx)
                            return cap
                        # Ensure release if opened partially
                        try:
                            if cap is not None:
                                cap.release()
                        except Exception:
                            pass
                    return None

                # First try requested index
                cap = try_open(self.camera_index)
                # Fallback to index 0 if different and failed
                if cap is None and self.camera_index != 0:
                    self.logger.warning("Failed to open camera at index %d; trying index 0", self.camera_index)
                    cap = try_open(0)

                if cap is None:
                    raise RuntimeError(f"Unable to open camera at indices [{self.camera_index}, 0] with available backends")

                self.cap = cap
                # Apply preferred properties (best-effort)
                try:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimize buffering
                    # Try to enforce preferred pixel format (FOURCC)
                    if isinstance(self.preferred_fourcc, str) and len(self.preferred_fourcc) == 4:
                        fourcc_val = cv2.VideoWriter_fourcc(*self.preferred_fourcc)
                        self.cap.set(cv2.CAP_PROP_FOURCC, fourcc_val)
                        read_back = int(self.cap.get(cv2.CAP_PROP_FOURCC))
                        back_str = ''.join([chr((read_back >> (8 * i)) & 0xFF) for i in range(4)])
                        self.logger.info("Requested FOURCC=%s, camera reports FOURCC=%s", self.preferred_fourcc, back_str)
                    # FPS preference
                    if self.target_fps:
                        self.cap.set(cv2.CAP_PROP_FPS, float(self.target_fps))
                except Exception:
                    self.logger.debug("Setting camera properties failed; continuing with defaults")

                # Try anti-flicker-friendly exposure (best effort)
                try:
                    self._apply_antiflicker_exposure()
                except Exception:
                    self.logger.debug("Exposure tuning not supported by this device/backend; skipping")

                # Warm-up camera with retries
                self.logger.debug("Warming up camera...")
                time.sleep(1.0)
                ok_frames = 0
                for i in range(15):
                    ret, _ = self.cap.read()
                    if ret:
                        ok_frames += 1
                    else:
                        self.logger.warning("Camera warm-up frame %d failed", i + 1)
                    time.sleep(0.08)
                if ok_frames < 3:
                    self.logger.error("Camera warm-up had few successful frames (%d/15)", ok_frames)
                    raise RuntimeError(
                        f"Camera initialization failed during warm-up ({ok_frames}/15 frames ok). "
                        "Aborting startup instead of fallback reopen."
                    )
                else:
                    self.logger.info("Camera warm-up completed (%d/15 frames ok)", ok_frames)

            except Exception as e:
                self.logger.error("Failed to initialize camera: %s", e)
                raise
        else:
            self.logger.info("[VIRTUAL] Camera hardware initialization skipped")

    def _fallback_reopen(self):
        """Attempt to reopen camera with alternate backend and conservative settings."""
        try:
            # Release current handle if any
            try:
                if self.cap is not None:
                    self.cap.release()
            except Exception:
                pass
            self.cap = None

            self.logger.info("Attempting camera fallback reopen...")

            # Try MSMF first, then DSHOW, then ANY
            backends = [getattr(cv2, 'CAP_MSMF', None), getattr(cv2, 'CAP_DSHOW', None), getattr(cv2, 'CAP_ANY', 0)]
            for be in backends:
                if be is None:
                    continue
                cap = cv2.VideoCapture(self.camera_index, be)
                if cap is not None and cap.isOpened():
                    self.logger.info("Fallback opened camera with backend=%s", str(be))
                    # Conservative settings: lower res, auto exposure
                    try:
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        cap.set(cv2.CAP_PROP_FPS, 30.0)
                        # Prefer auto exposure to avoid unsupported manual modes
                        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                    except Exception:
                        pass
                    # Warm-up a few frames
                    ok = 0
                    for i in range(10):
                        ret, _ = cap.read()
                        ok += int(bool(ret))
                        time.sleep(0.08)
                    if ok >= 3:
                        self.logger.info("Fallback warm-up succeeded (%d/10)", ok)
                        self.cap = cap
                        return
                    else:
                        self.logger.warning("Fallback warm-up had few frames (%d/10); trying next backend", ok)
                        try:
                            cap.release()
                        except Exception:
                            pass
                        continue
                # Release unsuccessful open
                try:
                    if cap is not None:
                        cap.release()
                except Exception:
                    pass

            self.logger.error("Camera fallback reopen failed across all backends")
        except Exception as e:
            self.logger.error("Fallback reopen exception: %s", e)
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
            if self.cap is None or not self.cap.isOpened():
                self.logger.warning("Capture handle not opened; attempting to reinitialize camera")
                # Try fallback reopen first
                self._fallback_reopen()
                if self.cap is None or not self.cap.isOpened():
                    # Final attempt with CAP_ANY
                    tmp = cv2.VideoCapture(self.camera_index, getattr(cv2, 'CAP_ANY', 0))
                    if tmp is not None and tmp.isOpened():
                        self.cap = tmp
                    else:
                        self.logger.error("Failed to reopen camera before capture")
                        return None

            for i in range(5):
                ret, _ = self.cap.read()
                if not ret:
                    self.logger.warning("Stabilization frame %d failed", i + 1)
                time.sleep(0.15)
            
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

    def _apply_antiflicker_exposure(self):
        """Best-effort anti-flicker exposure tuning for 50/60Hz lighting.

        On Windows, exposure units vary by backend. We'll try common patterns:
        - Turn off auto exposure when possible.
        - Set exposure near 1/60s (60 Hz) or 1/50s (50 Hz). For DSHOW-like backends
          OpenCV often uses log2 time (e.g., -6 ~ 1/64s). We'll try a small set.
        """
        if self.cap is None or not self.cap.isOpened():
            return

        # Try disabling auto exposure (multiple conventions)
        for val in (0.25, 0.0, 1.0):  # 0.25 (DSHOW manual), 0.0 (manual MSMF), 1.0 (some toggles)
            try:
                ok = self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, float(val))
                if ok:
                    self.logger.info("Set CAP_PROP_AUTO_EXPOSURE=%s", val)
                    break
            except Exception:
                pass

        # Pick target exposure candidates aligned to mains flicker
        # Use log2 seconds for DSHOW-like drivers; try a few around 1/60 and 1/50
        if int(self.anti_flicker_hz) == 50:
            candidates = [-5.6, -5.0, -6.0]  # around 1/50..1/64s
        else:
            candidates = [-6.0, -5.6, -5.0]  # around 1/60..1/32s

        success = False
        for v in candidates:
            try:
                ok = self.cap.set(cv2.CAP_PROP_EXPOSURE, float(v))
                readback = self.cap.get(cv2.CAP_PROP_EXPOSURE)
                self.logger.info("Tried exposure %.2f; camera reports %.2f (ok=%s)", v, readback, str(ok))
                # Consider success if set call returned True or readback moved near v
                if ok or (abs((readback or 0) - v) < 0.6):
                    success = True
                    break
            except Exception:
                continue
        if not success:
            self.logger.debug("Exposure setting attempts did not succeed; leaving device defaults")

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
            cv2.destroyAllWindows()
        else:
            self.logger.warning("No camera to release")

    def average_color_in_center(self, image_path, square_size=100, show_crop=True, save_crop=True, crop_folder="center_crops", color_space="RGB"):
        """
        Calculate the average color values in the center square of an image.
x
        Args:
            image_path (str): Path to the image file
            square_size (int): Size of the center square in pixels
            show_crop (bool): Whether to display the cropped image
            save_crop (bool): Whether to save the cropped image
            crop_folder (str): Folder name for saving cropped images
            color_mode (str): Color mode, either "RGB" or "RGBA" or "LAB" or "HSV"
        Returns:
            dict: Average colour values ex. {"R": val, "G": val, "B": val} for RGB
        """
        self.logger.debug("Processing image: %s (square_size=%d)", image_path, square_size)

        if getattr(self, "virtual", False):
            self.logger.info("Simulation mode enabled — generating random color values.")

            # Decide which colour spaces to compute
            if color_space is None:
                self.logger.warning("color_space is None in virtual mode; defaulting to RGB")
                requested = ["RGB"]
            elif isinstance(color_space, (list, tuple)):
                requested = [s.upper() for s in color_space]
            elif isinstance(color_space, str) and color_space in ("RGB", "RGBA", "HSV", "LAB"):
                requested = [str(color_space).upper()]
            else:
                self.logger.warning("Unrecognized color_space '%s' in virtual mode; defaulting to RGB", color_space)
                requested = ["RGB"]

            results = {}

            for space in requested:
                if space == "RGB":
                    results["RGB"] = {
                        "R": float(np.random.uniform(0, 255)),
                        "G": float(np.random.uniform(0, 255)),
                        "B": float(np.random.uniform(0, 255)),
                    }

                elif space == "RGBA":
                    results["RGBA"] = {
                        "R": float(np.random.uniform(0, 255)),
                        "G": float(np.random.uniform(0, 255)),
                        "B": float(np.random.uniform(0, 255)),
                        "A": 255.0,
                    }

                elif space == "HSV":
                    results["HSV"] = {
                        "H": float(np.random.uniform(0, 360)),
                        "S": float(np.random.uniform(0, 100)),
                        "V": float(np.random.uniform(0, 100)),
                    }

                elif space == "LAB":
                    # Use realistic color mixing if mixture volumes are available
                    if hasattr(self, '_current_mixture_volumes'):
                        results["LAB"] = self._simulate_realistic_color_mixing(self._current_mixture_volumes)
                    else:
                        # Fallback to random values if no mixture info
                        results["LAB"] = {
                            "L": float(np.random.uniform(0, 100)),
                            "A": float(np.random.uniform(-128, 127)),
                            "B": float(np.random.uniform(-128, 127)),
                        }

            # Simulate crop metadata (no real file)
            results["crop_path"] = None
            results["crop_rect"] = (0, 0, square_size, square_size)

            self.logger.info("[Virtual] mode color results: %s", results)

            # Match normal return behavior
            if len(requested) == 1:
                return results[requested[0]] #only returns the value for the color space chosen
            
            return results

        try: # in  real hardware
            # Open the image using PIL and ensure it's in RGB mode
            image = Image.open(image_path).convert('RGB')
            width, height = image.size
            self.logger.debug("Image dimensions: %dx%d", width, height)

            # Define the center crop box (ensure at least 1x1 pixels)
            try:
                sq = int(square_size) if square_size is not None else 1
            except Exception:
                sq = 1
            if sq < 1:
                sq = 1

            center_x, center_y = width // 2, height // 2
            # Compute start so that end = start + sq, clamped within image
            start_x = max(min(center_x - (sq // 2), width - sq), 0)
            start_y = max(min(center_y - (sq // 2), height - sq), 0)
            left = int(start_x)
            top = int(start_y)
            right = int(min(left + sq, width))
            bottom = int(min(top + sq, height))

            # Crop the image and convert to numpy array
            cropped = image.crop((left, top, right, bottom))
            arr = np.array(cropped)

            # Decide which colour spaces to compute. Accepts None (use color_mode), a string, or a list/tuple
            if color_space is None:
                self.logger.warning("color_space is None in virtual mode; defaulting to RGB")
                requested = ["RGB"]    
            elif isinstance(color_space, (list, tuple)):
                requested = [s.upper() for s in color_space and s.upper() in ("RGB", "RGBA", "HSV", "LAB")]
            elif isinstance(color_space, str) and color_space in ("RGB", "RGBA", "HSV", "LAB"):
                requested = [str(color_space).upper()]
            else:
                self.logger.warning("Unrecognized color_space '%s'; defaulting to RGB", color_space)
                requested = ["RGB"]


            # Prepare a result mapping
            results = {}

            # Ensure we have an RGB array to derive other spaces from
            rgb_arr = arr[..., :3].astype(np.uint8)

            # Helper: include crop_path later after saving
            # Compute RGB / RGBA
            if any(r in ("RGB",) for r in requested):
                mean_rgb = tuple(np.mean(rgb_arr, axis=(0, 1)).astype(float))
                results['RGB'] = {"R": mean_rgb[0], "G": mean_rgb[1], "B": mean_rgb[2]}
                self.logger.info("Average RGB calculated: (%.1f, %.1f, %.1f)", *mean_rgb)

            if any(r in ("RGBA",) for r in requested):
                # If alpha channel present, use it; otherwise assume fully opaque (255)
                if arr.shape[-1] == 4:
                    mean_rgba = tuple(np.mean(arr, axis=(0, 1)).astype(float))
                else:
                    mean_rgb = tuple(np.mean(rgb_arr, axis=(0, 1)).astype(float))
                    mean_rgba = (mean_rgb[0], mean_rgb[1], mean_rgb[2], 255.0)
                results['RGBA'] = {"R": mean_rgba[0], "G": mean_rgba[1], "B": mean_rgba[2], "A": mean_rgba[3]}
                self.logger.info("Average RGBA calculated: (%.1f, %.1f, %.1f, %.1f)", *mean_rgba)

            # Compute HSV (normalized: H 0-360, S/V 0-100)
            if any(r in ("HSV",) for r in requested):
                hsv_image = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2HSV)
                h = hsv_image[..., 0].astype(np.float32)
                s = hsv_image[..., 1].astype(np.float32)
                v = hsv_image[..., 2].astype(np.float32)

                # Hue circular mean: convert to radians (degrees = h*2, radians = degrees * pi/180)
                hue_rad = h * 2.0 * np.pi / 180.0
                mean_sin = np.mean(np.sin(hue_rad))
                mean_cos = np.mean(np.cos(hue_rad))
                mean_hue_rad = np.arctan2(mean_sin, mean_cos)
                mean_hue_deg = (mean_hue_rad * 180.0 / np.pi) % 360.0

                mean_s_percent = float(np.mean(s) / 255.0 * 100.0)
                mean_v_percent = float(np.mean(v) / 255.0 * 100.0)

                results['HSV'] = {"H": float(mean_hue_deg), "S": mean_s_percent, "V": mean_v_percent}
                self.logger.info("Average HSV calculated: (H=%.1f°, S=%.1f%%, V=%.1f%%)", mean_hue_deg, mean_s_percent, mean_v_percent)

            # Compute LAB (prefer skimage, fallback to OpenCV conversion)
            if any(r in ("LAB",) for r in requested):
                lab_mean = None
                try:
                    from skimage import color as skcolor
                    # skimage expects floats in 0..1
                    rgb_float = rgb_arr.astype(np.float64) / 255.0
                    lab = skcolor.rgb2lab(rgb_float)
                    lab_mean_vals = np.mean(lab.reshape(-1, 3), axis=0)
                    lab_mean = (float(lab_mean_vals[0]), float(lab_mean_vals[1]), float(lab_mean_vals[2]))
                    self.logger.debug("Used skimage.rgb2lab for LAB conversion")
                except Exception:
                    # Fallback: OpenCV conversion (uint8), then map OpenCV ranges to conventional
                    lab_image = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2LAB)
                    mean_lab_cv = np.mean(lab_image, axis=(0, 1))
                    L = float(mean_lab_cv[0]) * (100.0 / 255.0)
                    a = float(mean_lab_cv[1]) - 128.0
                    b = float(mean_lab_cv[2]) - 128.0
                    lab_mean = (L, a, b)
                    self.logger.debug("Used OpenCV for LAB conversion (fallback)")

                results['LAB'] = {"L": lab_mean[0], "A": lab_mean[1], "B": lab_mean[2]}
                self.logger.info("Average LAB calculated: (%.2f, %.2f, %.2f)", lab_mean[0], lab_mean[1], lab_mean[2])
            # End of colour computations

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

            # Attach crop metadata
            if 'crop_path' not in locals():
                crop_path = None
            # Attach metadata to results
            results['crop_path'] = crop_path
            results['crop_rect'] = (left, top, right, bottom)

            if show_crop:
                self.logger.debug("Displaying cropped image")
                plt.imshow(cropped)
                plt.title("Center Crop")
                plt.axis("off")
                plt.show()

            # Backwards compatibility: if colour_space was None and color_mode was RGB, return legacy dict
            if color_space is None and (color_space is None or str(color_space).upper() == 'RGB'):
                return results.get('RGB', {})

            # If only a single requested space was asked, return that space's dict for convenience
            if len(requested) == 1:
                space = requested[0]
                return results.get(space, {}) #returns only the dict for that colour space

            # Once done, delete tensor and image, then clear memory
            del tensor
            del img
            gc.collect()

            # if torch.cuda.is_available():
            #     torch.cuda.empty_cache()  # safe even if using CPU only

            # Otherwise return full results mapping
            return results

            

            
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
    
    def set_current_mixture(self, volumes):
        """Set the current mixture volumes for realistic simulation"""
        self._current_mixture_volumes = volumes
    
    def _simulate_realistic_color_mixing(self, volumes):
        """Simulate realistic color mixing based on RGB volume ratios"""
        r_vol = volumes.get('R', 0) * 1000  # Convert to microliters
        y_vol = volumes.get('Y', 0) * 1000
        b_vol = volumes.get('B', 0) * 1000
        
        # Normalize volumes to fractions
        total_vol = r_vol + y_vol + b_vol
        if total_vol == 0:
            return {"L": 50.0, "A": 0.0, "B": 0.0}  # Neutral gray
            
        r_frac = r_vol / total_vol
        y_frac = y_vol / total_vol  
        b_frac = b_vol / total_vol
        
        # Define approximate LAB values for pure colors
        red_lab = [53.0, 80.0, 67.0]      # Bright red dye
        yellow_lab = [97.0, -21.0, 94.0]   # Yellow dye  
        blue_lab = [32.0, 79.0, -108.0]    # Blue dye
        
        # Linear mixing (simplified model)
        mixed_l = r_frac * red_lab[0] + y_frac * yellow_lab[0] + b_frac * blue_lab[0]
        mixed_a = r_frac * red_lab[1] + y_frac * yellow_lab[1] + b_frac * blue_lab[1]  
        mixed_b = r_frac * red_lab[2] + y_frac * yellow_lab[2] + b_frac * blue_lab[2]
        
        # Add realistic noise (measurement uncertainty)
        noise_scale = 2.0  # Standard deviation
        mixed_l += np.random.normal(0, noise_scale)
        mixed_a += np.random.normal(0, noise_scale)
        mixed_b += np.random.normal(0, noise_scale)
        
        # Clamp to valid LAB ranges
        mixed_l = np.clip(mixed_l, 0, 100)
        mixed_a = np.clip(mixed_a, -128, 127)
        mixed_b = np.clip(mixed_b, -128, 127)
        
        return {
            "L": float(mixed_l),
            "A": float(mixed_a), 
            "B": float(mixed_b),
        }