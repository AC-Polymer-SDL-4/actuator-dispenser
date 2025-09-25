import logging
import math  # Used for volume calculations
from cnc_machine import CNC_Machine
from actuator_controller import ActuatorRemote
from camera import Camera
from log_config import setup_logger, log_method_entry, log_method_exit, log_virtual_action

class Liquid_Dispenser:
    """
    Main liquid dispensing system that combines CNC machine, actuator, and camera.
    
    This class orchestrates the entire liquid handling workflow including:
    - Moving to source and destination locations
    - Aspirating and dispensing precise volumes
    - Image capture for monitoring
    - Mixing operations
    
    Features:
      - Virtual mode for testing without hardware
      - Structured logging with file output in logs/ folder
      - Compatible with all component logging systems
    """
    
    def __init__(self, cnc_comport, actuator_comport, camera_index=0, output_dir="well_plate_photos", 
                 virtual=False, log_level=logging.INFO):
        """
        Initialize the complete liquid dispensing system.
        
        Args:
            cnc_comport (str): Serial port for CNC machine (e.g., "COM3")
            actuator_comport (str): Serial port for actuator (e.g., "COM6") 
            camera_index (int): Camera device index (usually 0)
            output_dir (str): Directory for saving captured images
            virtual (bool): If True, simulates operations without hardware communication
            log_level: Logging level for this class (DEBUG, INFO, WARNING, ERROR)
        """
        self.virtual = virtual
        
        # Setup centralized logging with virtual mode tagging
        self.logger = setup_logger("dispenser", virtual=virtual, log_level=log_level)
        
        log_method_entry(self.logger, "__init__", 
                        cnc_comport=cnc_comport, 
                        actuator_comport=actuator_comport,
                        camera_index=camera_index,
                        output_dir=output_dir,
                        virtual=virtual)
        
        if virtual:
            self.logger.warning("Liquid_Dispenser running in VIRTUAL mode - no hardware communication")
        
        self.logger.info("Initializing Liquid_Dispenser: cnc_port=%s, actuator_port=%s, virtual=%s", 
                        cnc_comport, actuator_comport, virtual)
        
        try:
            # Initialize CNC machine with virtual mode and logging
            self.cnc_machine = CNC_Machine(com=cnc_comport, virtual=virtual, log_level=log_level)
            
            # Initialize actuator with virtual mode and logging
            self.actuator = ActuatorRemote(port=actuator_comport, virtual=virtual, log_level=log_level)
            
            # Initialize camera with virtual mode and logging  
            self.camera = Camera(camera_index=camera_index, output_dir=output_dir, 
                               virtual=virtual, log_level=log_level)
            
            self.logger.info("All components initialized successfully")
            log_method_exit(self.logger, "__init__", "Success")
            
        except Exception as e:
            self.logger.error("Failed to initialize components: %s", e)
            log_method_exit(self.logger, "__init__", f"Failed: {e}")
            raise

    def dispense_between(self, source_location, source_index, dest_location, dest_index, 
                        vol_pipet, air_time=0.7, buffer_time=1, speed=32768, mix=False):
        """
        Transfer liquid from a source location to a destination location.
        
        This method handles the complete liquid transfer workflow:
        1. Calculates number of dispenses needed based on max volume per dispense
        2. Moves to source location and aspirates liquid
        3. Moves to destination and dispenses liquid
        4. Optionally performs mixing at destination
        
        Args:
            source_location (str): Source location name (e.g., "vial_rack")
            source_index (int): Index within source location
            dest_location (str): Destination location name (e.g., "well_plate") 
            dest_index (int): Index within destination location
            vol_pipet (float): Total volume to transfer in mL
            air_time (float): Time to aspirate air buffer in seconds
            buffer_time (float): Extra time for complete dispensing in seconds
            speed (int): Actuator speed (0-65535)
            mix (bool): Whether to perform mixing at destination
        """
        # Volume calculation constants
        max_vol = 0.5  # Maximum volume per dispense in mL (hardware limitation)
        slope = 0.4295  # Time per mL conversion factor (seconds/mL, from calibration)
        
        self.logger.info(
            "Starting dispense_between: %s[%d] -> %s[%d], volume=%.3f mL, mix=%s", 
            source_location, source_index, dest_location, dest_index, vol_pipet, mix
        )
        
        # Calculate how many dispense cycles we need
        num_dispenses = math.ceil(vol_pipet / max_vol)
        dispense_vol = vol_pipet / num_dispenses  # Volume per individual dispense
        retract_time = dispense_vol * slope  # Time needed to aspirate this volume
        
        self.logger.debug(
            "Dispense calculations: total_vol=%.3f, max_vol=%.3f, num_dispenses=%d, vol_per_dispense=%.3f, retract_time=%.2f",
            vol_pipet, max_vol, num_dispenses, dispense_vol, retract_time
        )
        
        if vol_pipet <= 0:
            self.logger.warning("Invalid volume requested: %.3f mL", vol_pipet)
            return
            
        if vol_pipet > max_vol * 10:  # Reasonable upper limit
            self.logger.warning("Large volume requested (%.3f mL) will require %d dispenses", vol_pipet, num_dispenses)
        
        try:
            if mix:
                self.logger.debug("Performing dispense with mixing")
                # Dispense with mixing at destination
                for cycle in range(num_dispenses):
                    self.logger.debug("Starting dispense cycle %d/%d", cycle + 1, num_dispenses)
                    
                    # Move to source and aspirate
                    self.logger.debug("Moving to source: %s[%d]", source_location, source_index)
                    self.cnc_machine.move_to_location(source_location, source_index, safe=False)
                    
                    self.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
                    self.actuator.retract(air_time, speed=speed)
                    
                    self.logger.debug("Moving down to aspirate liquid")
                    self.cnc_machine.move_to_point(z=-70)
                    
                    self.logger.debug("Aspirating liquid: %.2f seconds (%.3f mL)", retract_time, dispense_vol)
                    self.actuator.retract(retract_time, speed=speed)
                    
                    self.logger.debug("Moving up from source")
                    self.cnc_machine.move_to_point(z=0)
                    
                    # Move to destination and dispense
                    self.logger.debug("Moving to destination: %s[%d]", dest_location, dest_index)
                    self.cnc_machine.move_to_location(dest_location, dest_index, safe=False)
                    
                    total_dispense_time = air_time + retract_time + buffer_time
                    self.logger.debug("Dispensing liquid: %.2f seconds total", total_dispense_time)
                    self.actuator.extend(total_dispense_time, speed=speed)
                    
                    # Perform mixing
                    self.logger.debug("Moving down for mixing")
                    self.cnc_machine.move_to_point(z=-62)  # Move down to mix
                    
                    for mix_cycle in range(3):  # Mix 3 times
                        self.logger.debug("Mix cycle %d/3", mix_cycle + 1)
                        self.actuator.retract(1, speed=speed)  # Retract to mix
                        self.actuator.extend(1, speed=speed)   # Extend to mix
                        
                    self.logger.debug("Moving up after mixing")
                    self.cnc_machine.move_to_point(z=0)  # Move back up
                    
            else:
                self.logger.debug("Performing standard dispense (no mixing)")
                # Standard dispense without mixing
                for cycle in range(num_dispenses):
                    self.logger.debug("Starting dispense cycle %d/%d", cycle + 1, num_dispenses)
                    
                    # Move to source and aspirate
                    self.logger.debug("Moving to source: %s[%d]", source_location, source_index)
                    self.cnc_machine.move_to_location(source_location, source_index, safe=False)
                    
                    self.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
                    self.actuator.retract(air_time, speed=speed)
                    
                    self.logger.debug("Moving down to aspirate liquid")
                    self.cnc_machine.move_to_point(z=-70)
                    
                    self.logger.debug("Aspirating liquid: %.2f seconds (%.3f mL)", retract_time, dispense_vol)
                    self.actuator.retract(retract_time, speed=speed)
                    
                    self.logger.debug("Moving up from source")
                    self.cnc_machine.move_to_point(z=0)
                    
                    # Move to destination and dispense
                    self.logger.debug("Moving to destination: %s[%d]", dest_location, dest_index)
                    self.cnc_machine.move_to_location(dest_location, dest_index, safe=False)
                    
                    total_dispense_time = air_time + retract_time + buffer_time
                    self.logger.debug("Dispensing liquid: %.2f seconds total", total_dispense_time)
                    self.actuator.extend(total_dispense_time, speed=speed)
                    
            self.logger.info("Dispense operation completed successfully")
            
        except Exception as e:
            self.logger.error("Dispense operation failed: %s", e)
            # Try to stop actuator for safety
            try:
                self.actuator.stop()
                self.logger.info("Actuator stopped for safety")
            except:
                self.logger.error("Failed to stop actuator after error")
            raise

    def dispense_condition(self, source_location, source_index, dest_location="vial_rack", 
                          dest_index=6, vol_pipet=0.5, air_time=0.7, buffer_time=1, speed=32768):
        """
        Condition the pipette by aspirating and dispensing to waste.
        
        This method prepares the pipette for accurate dispensing by:
        1. Aspirating liquid from source to prime the tip
        2. Dispensing to waste location (typically for conditioning)
        3. Repeating the process multiple times to ensure accuracy
        
        Args:
            source_location (str): Source location for conditioning liquid
            source_index (int): Index within source location  
            dest_location (str): Waste/destination location (default: "vial_rack")
            dest_index (int): Index for waste location (default: 6)
            vol_pipet (float): Volume for conditioning in mL
            air_time (float): Time to aspirate air buffer in seconds
            buffer_time (float): Extra time for complete dispensing in seconds
            speed (int): Actuator speed (0-65535)
        """
        # Volume calculation constants
        max_vol = 0.5  # Maximum volume per dispense in mL
        slope = 0.4295  # Time per mL conversion factor (seconds/mL)
        
        self.logger.info(
            "Starting conditioning: %s[%d] -> %s[%d], volume=%.3f mL", 
            source_location, source_index, dest_location, dest_index, vol_pipet
        )
        
        # Calculate dispense parameters
        num_dispenses = math.ceil(vol_pipet / max_vol)
        dispense_vol = vol_pipet / num_dispenses
        retract_time = dispense_vol * slope
        
        self.logger.debug(
            "Conditioning calculations: num_dispenses=%d, vol_per_dispense=%.3f, retract_time=%.2f",
            num_dispenses, dispense_vol, retract_time
        )
        
        try:
            # Perform conditioning cycles (typically 3 cycles for good priming)
            for cycle in range(3):
                self.logger.debug("Conditioning cycle %d/3", cycle + 1)
                
                self.logger.debug("Moving to source: %s[%d]", source_location, source_index)
                self.cnc_machine.move_to_location(source_location, source_index, safe=False)
                
                self.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
                self.actuator.retract(air_time, speed=speed)
                
                self.logger.debug("Moving down to aspirate conditioning liquid")
                self.cnc_machine.move_to_point(z=-70)
                
                self.logger.debug("Aspirating conditioning liquid: %.2f seconds", retract_time)
                self.actuator.retract(retract_time, speed=speed)
                
                self.logger.debug("Moving up from source")
                self.cnc_machine.move_to_point(z=0)
                
                self.logger.debug("Moving to waste: %s[%d]", dest_location, dest_index)
                self.cnc_machine.move_to_location(dest_location, dest_index, safe=False)
                
                total_dispense_time = air_time + retract_time + buffer_time
                self.logger.debug("Dispensing to waste: %.2f seconds total", total_dispense_time)
                self.actuator.extend(total_dispense_time, speed=speed)
                
            self.logger.debug("Conditioning completed successfully")
            
        except Exception as e:
            self.logger.error("Conditioning failed: %s", e)
            try:
                self.actuator.stop()
                self.logger.info("Actuator stopped for safety")
            except:
                self.logger.error("Failed to stop actuator after conditioning error")
            raise
    
    def move_to_origin(self):
        """
        Move the CNC machine to a safe origin/home position.
        
        This position is typically used:
        - At the start of operations
        - At the end of operations  
        - When switching between different workflows
        - For safety during manual interventions
        """
        self.logger.info("Moving CNC to safe origin position")
        try:
            # Move to safe position: x=0, y=140, z=0
            self.cnc_machine.move_to_point(x=0, y=140, z=0)
            self.logger.info("CNC moved to origin successfully")
        except Exception as e:
            self.logger.error("Failed to move to origin: %s", e)
            raise

    def get_image_rgb(self, location, location_index, image_suffix, square_size=100):
        """
        Capture an image at a specific location and analyze its RGB values.
        
        In virtual mode, returns simulated RGB values for testing.
        In real mode:
        1. Moves the CNC to the specified location
        2. Captures an image using the camera
        3. Analyzes the center region for average RGB values
        
        Args:
            location (str): Location name to move to (e.g., "well_plate")
            location_index (int): Index within the location
            image_suffix: Suffix for the image filename
            square_size (int): Size of center square for RGB analysis
            
        Returns:
            tuple: Average RGB values (R, G, B) or None if capture failed
        """
        self.logger.info(
            "Capturing image at %s[%d] with suffix '%s'", 
            location, location_index, image_suffix
        )
        
        # Handle virtual mode with dummy RGB values
        if self.virtual:
            import random
            
            # Provide realistic dummy values for different scenarios
            if location_index == 0 and location == "well_plate":
                # Target sample - use a consistent "target" color (purple-ish)
                dummy_rgb = (128, 64, 192)
                self.logger.info("[VIRTUAL] Using target sample RGB: (%.1f, %.1f, %.1f)", *dummy_rgb)
            else:
                # Experimental wells - generate varied colors with some randomness
                # but keep them in realistic ranges for color mixing
                base_r = random.randint(80, 180)
                base_g = random.randint(60, 160) 
                base_b = random.randint(70, 170)
                dummy_rgb = (base_r, base_g, base_b)
                self.logger.info("[VIRTUAL] Using simulated RGB: (%.1f, %.1f, %.1f)", *dummy_rgb)
            
            return dummy_rgb
        
        # Real hardware mode
        try:
            # Move to the specified location for imaging
            self.logger.debug("Moving to imaging position")
            self.cnc_machine.move_to_location(location, location_index)
            
            # Capture and save the image
            self.logger.debug("Capturing image")
            image_path = self.camera.capture_and_save(image_suffix)
            
            if image_path is not None:
                # Analyze the captured image for RGB values
                self.logger.debug("Analyzing image for RGB values")
                rgb = self.camera.average_rgb_in_center(image_path, square_size, 
                                                       show_crop=False, save_crop=False)
                self.logger.info("RGB analysis completed: (%.1f, %.1f, %.1f)", *rgb)
                return rgb
            else:
                self.logger.error("Image capture failed")
                return None
                
        except Exception as e:
            self.logger.error("Image capture and analysis failed: %s", e)
            return None