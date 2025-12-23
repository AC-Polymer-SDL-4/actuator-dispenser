import logging
import math  # Used for volume calculations
from cnc_machine import CNC_Machine
from actuator_controller import ActuatorRemote
from camera import Camera
from log_config import setup_logger, log_method_entry, log_method_exit, log_virtual_action
import time
import os
from datetime import datetime

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
                 virtual=False, log_level=logging.INFO, log_filename=None):
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
        logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(logs_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        workflow_name = "general"
        virtual_tag = "_virtual" if virtual else ""
        log_filename = log_filename if log_filename is not None else f"{workflow_name}{virtual_tag}_{timestamp}.log"

        
        self.logger = setup_logger("dispenser", virtual=virtual, log_level=log_level, log_filename=log_filename)
        
        
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
            self.cnc_machine = CNC_Machine(com=cnc_comport, virtual=virtual, log_level=log_level, log_filename=log_filename)
            
            # Initialize actuator with virtual mode and logging
            self.actuator = ActuatorRemote(port=actuator_comport, virtual=virtual, log_level=log_level, log_filename=log_filename)
            
            # Initialize camera with virtual mode and logging  
            self.camera = Camera(camera_index=camera_index, output_dir=output_dir, 
                               virtual=virtual, log_level=log_level, log_filename=log_filename)
            
            self.logger.info("All components initialized successfully")
            log_method_exit(self.logger, "__init__", "Success")
            
        except Exception as e:
            self.logger.error("Failed to initialize components: %s", e)
            log_method_exit(self.logger, "__init__", f"Failed: {e}")
            raise

    def dispense_between(self, source_location, source_index, dest_location, dest_index, 
                        transfer_vol, blowout_vol = 0.28, buffer_time=0.25, speed=32768, mixing_vol = 0, num_mixes=3, mixing_speed = 32768):
        """
        Transfer liquid from a source location to a destination location,
        with optional mixing. Also supports mixing-only without transfer by setting transfer_vol = 0.
        
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
            transfer_vol (float): Total volume to transfer in mL (0 for mixing-only)
            air_time (float): Time to aspirate air buffer in seconds
            blowout_vol (float): Volume of air (mL) to aspirate/dispense for a blowout effect
            buffer_time (float): Extra time for complete dispensing in seconds
            speed (int): Actuator speed (0-65535)
            mixing_vol (int): (float): Volume to use during mixing (mL) (0 if no mixing)
            num_mixes (int): Number of mixing cycles to perform
        """
        # Volume calculation constants
        MAX_TIME = 1.95 #The maximum time for a single dispense in seconds (for liquid transfer AND blowout time!) -- edit based on calibration
        SLOPE = 0.4061  # Time per mL conversion factor (seconds/mL, from calibration), before: 0.4295, 0.4679, 0.4052, 0.3865 (new metal syringe)

        SYRINGE_MAX_VOL = MAX_TIME*SLOPE #0.76  
        transfer_max_vol = SYRINGE_MAX_VOL-blowout_vol  # Maximum volume per dispense in mL (hardware limitation)
        
        min_vol = 0.025
        air_time = blowout_vol/SLOPE #air_time for blow out
        MIN_BUFFER_TIME = 0 #0.6 #seconds
        

        self.logger.info(
            "Starting dispense_between: %s[%d] -> %s[%d], transfer volume=%.3f mL, mixing volume=%.3f, buffer_time=%.2f s, blowout_vol=%.3f mL", 
            source_location, source_index, dest_location, dest_index, transfer_vol, mixing_vol, buffer_time, blowout_vol
        )
        
        if  transfer_vol < min_vol and transfer_vol != 0: #min volume
            self.logger.warning("Invalid transfer volume requested: %.3f mL", transfer_vol)
            return 
        if  mixing_vol <= min_vol and mixing_vol != 0: #min volume
            self.logger.warning("Invalid mixing volume requested: %.3f mL", mixing_vol)
            return
        if transfer_vol == 0 and mixing_vol == 0:
            self.logger.warning("Nothing to do: both transfer and mixing volumes are zero.")
            return
        
        if buffer_time < MIN_BUFFER_TIME:
            self.logger.warning("Invalid BUFFER time requested: %.3f seconds, setting to minimum of %.2f seconds", buffer_time, MIN_BUFFER_TIME)
            buffer_time = MIN_BUFFER_TIME

        if transfer_vol > 0:
        # Calculate how many dispense cycles we need
            num_dispenses = math.ceil(transfer_vol / transfer_max_vol)
            dispense_vol = transfer_vol / num_dispenses  # Volume per individual dispense
            retract_time = dispense_vol/SLOPE # Time needed to aspirate this volume
            
            
            if transfer_vol > (transfer_max_vol * 10):  # Reasonable upper limit
                self.logger.warning("Large volume requested (%.3f mL) will require %d dispenses", transfer_vol, num_dispenses)
                return 
            
        else:
            num_dispenses = 0
            dispense_vol = 0
            retract_time = 0
        
        self.logger.debug(
            "Dispense calculations: total_vol=%.3f, transfer_max_vol=%.3f, num_dispenses=%d, vol_per_dispense=%.3f, retract_time=%.2f",
            transfer_vol, transfer_max_vol, num_dispenses, dispense_vol, retract_time
        )
        
        #start dispense
        try:
            if transfer_vol > 0:
                self.logger.debug("Performing dispense")
                # Dispense with mixing at destination, transfering liquid before mixing
                
                for cycle in range(num_dispenses):
                    self.logger.debug("Starting dispense cycle %d/%d", cycle + 1, num_dispenses)
                    
                    # Move to source and aspirate
                    self.logger.debug("Moving to source: %s[%d]", source_location, source_index)
                    self.cnc_machine.move_to_location(source_location, source_index, safe=True)
                    
                    self.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
                    self.actuator.retract(air_time, speed=speed)
                    
                    self.logger.debug("Moving down to aspirate liquid")
                    self.cnc_machine.move_to_aspirate_height(source_location)
                    
                    self.logger.debug("Aspirating liquid: %.2f seconds (%.3f mL)", retract_time, dispense_vol)
                    self.actuator.retract(retract_time, speed=speed)

                    if not self.virtual:
                        time.sleep(0.5) #wait 1 second before moving up
                    
                    self.logger.debug("Moving up from source")
                    self.cnc_machine.move_to_point(z=0)
                    
                    # Move to destination and dispense
                    self.logger.debug("Moving to destination: %s[%d]", dest_location, dest_index)
                    self.cnc_machine.move_to_location(dest_location, dest_index, safe=True)
                    self.cnc_machine.move_to_dispense_height(dest_location)
                    
                    total_dispense_time = air_time + retract_time + buffer_time
                    self.logger.debug("Dispensing liquid: %.2f seconds total", total_dispense_time)
                    self.actuator.extend(total_dispense_time, speed=speed)

            if mixing_vol > 0 and num_mixes > 0 and mixing_vol <= transfer_max_vol: #mixing
                retract_time_mixing = mixing_vol / SLOPE  # Time needed to aspirate this volume (no air gap though)
                total_dispense_time = air_time + retract_time_mixing + buffer_time

                 # Move to source and aspirate
                self.logger.debug("Moving to destination location for mixing: %s[%d]", dest_location, dest_index)
                self.cnc_machine.move_to_location(dest_location, dest_index, safe=True)
                
                self.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
                self.actuator.retract(air_time, speed=mixing_speed)

                self.logger.debug("Moving down to aspirate liquid")
                self.cnc_machine.move_to_mixing_height(dest_location)

                for mix_cycle in range(num_mixes):  
                    self.logger.debug("Mix cycle %d/3", mix_cycle + 1)
                    self.actuator.retract(seconds=retract_time_mixing, speed=mixing_speed)  # Retract to mix
                    if not self.virtual:
                        time.sleep(0.5)
                    
                    if mix_cycle == num_mixes -1: #last dispense in mixing, dispense all liquid including air buffer
                        self.logger.debug("Moving up to dispense all liquid and air buffer")
                        self.cnc_machine.move_to_dispense_height(dest_location)

                        self.logger.debug("Dispensing ALL liquid: %.2f seconds total", total_dispense_time)
                        self.actuator.extend(seconds=total_dispense_time, speed=mixing_speed)  # dispense everything

                    else:
                        self.logger.debug("Dispensing liquid: %.2f seconds total", retract_time)
                        self.actuator.extend(seconds=retract_time_mixing, speed=mixing_speed)  # mixing only (keeping air buffer)

                    if not self.virtual:
                        time.sleep(0.5)
                    
                self.logger.info("Mixing complete")
                
            if mixing_vol > transfer_max_vol:
                self.logger.warning("Mixing volume (%.3f mL) exceeds maximum per dispense (%.3f mL); skipping mixing", mixing_vol, transfer_max_vol)
            
            self.logger.debug("Moving up after liquid transfer")
            self.cnc_machine.move_to_point(z=0)  # Move back up
                          
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

    def condition_needle(self, source_location, source_index, dest_location, dest_index, num_conditions = 1, vol_pipet=0.45, buffer_time=0.25, speed=32768):
        """
        Condition the syringe by aspirating from the source location and dispensing into waste
        Args:
        condition_repeats: the number of time to condition
        """
        for i in range(num_conditions):
            self.dispense_between(source_location = source_location, source_index=source_index, dest_location=dest_location, dest_index=dest_index, transfer_vol=vol_pipet, buffer_time=buffer_time, speed=speed, blowout_vol=0.28)

    def rinse_needle(self, wash_location, wash_index,vol_pipet=0.45, buffer_time=0.25, speed=32768, num_mixes = 3):
        """
        Rinsing the syringe in the wash station. Note that it is expected to aspirate and dispense from the same well.
        num_mixes: the number of times to mix inside of well
        """
        self.dispense_between(source_location=wash_location, source_index=wash_index, transfer_vol=0, dest_location=wash_location, dest_index=wash_index, mixing_vol=vol_pipet, buffer_time=buffer_time, mixing_speed=speed,num_mixes=num_mixes)


    # def dispense_condition(self, source_location, source_index, dest_location="vial_rack", 
    #                       dest_index=6, vol_pipet=0.5, buffer_time=1, speed=32768):
    #     """
    #     Condition the pipette by aspirating and dispensing to waste.
        
    #     This method prepares the pipette for accurate dispensing by:
    #     1. Aspirating liquid from source to prime the tip
    #     2. Dispensing to waste location (typically for conditioning)
    #     3. Repeating the process multiple times to ensure accuracy
        
    #     Args:
    #         source_location (str): Source location for conditioning liquid
    #         source_index (int): Index within source location  
    #         dest_location (str): Waste/destination location (default: "vial_rack")
    #         dest_index (int): Index for waste location (default: 6)
    #         vol_pipet (float): Volume for conditioning in mL
    #         air_time (float): Time to aspirate air buffer in seconds
    #         buffer_time (float): Extra time for complete dispensing in seconds
    #         speed (int): Actuator speed (0-65535)
    #     """
    #     # Volume calculation constants
    #     max_vol = 0.5  # Maximum volume per dispense in mL
    #     slope = 0.4003  # Time per mL conversion factor (seconds/mL) before: 0.4295
        
    #     self.logger.info(
    #         "Starting conditioning: %s[%d] -> %s[%d], volume=%.3f mL", 
    #         source_location, source_index, dest_location, dest_index, vol_pipet
    #     )
        
    #     # Calculate dispense parameters
    #     num_dispenses = math.ceil(vol_pipet / max_vol)
    #     dispense_vol = vol_pipet / num_dispenses
    #     retract_time = dispense_vol * slope
        
    #     self.logger.debug(
    #         "Conditioning calculations: num_dispenses=%d, vol_per_dispense=%.3f, retract_time=%.2f",
    #         num_dispenses, dispense_vol, retract_time
    #     )
        
    #     try:
    #         # Perform conditioning cycles (typically 3 cycles for good priming)
    #         for cycle in range(3):
    #             self.logger.debug("Conditioning cycle %d/3", cycle + 1)
                
    #             self.logger.debug("Moving to source: %s[%d]", source_location, source_index)
    #             self.cnc_machine.move_to_location(source_location, source_index, safe=True)
                
    #             # self.logger.debug("Aspirating air buffer: %.2f seconds", air_time)
    #             # self.actuator.retract(air_time, speed=speed)
                
    #             self.logger.debug("Moving down to aspirate conditioning liquid")
    #             #self.cnc_machine.move_to_point(z=-64) #z=-70 before
    #             self.cnc_machine.move_to_aspirate_height(source_location)
                
    #             self.logger.debug("Aspirating conditioning liquid: %.2f seconds", retract_time)
    #             self.actuator.retract(retract_time, speed=speed)
                
    #             self.logger.debug("Moving up from source")
    #             self.cnc_machine.move_to_point(z=0)
                
    #             self.logger.debug("Moving to waste: %s[%d]", dest_location, dest_index)
    #             self.cnc_machine.move_to_location(dest_location, dest_index, safe=True)
                
    #             total_dispense_time =  retract_time + buffer_time #+ air_time
    #             self.logger.debug("Dispensing to waste: %.2f seconds total", total_dispense_time)
    #             self.actuator.extend(total_dispense_time, speed=speed)
                
    #         self.logger.debug("Conditioning completed successfully")
            
    #     except Exception as e:
    #         self.logger.error("Conditioning failed: %s", e)
    #         try:
    #             self.actuator.stop()
    #             self.logger.info("Actuator stopped for safety")
    #         except:
    #             self.logger.error("Failed to stop actuator after conditioning error")
    #         raise
    
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

    def get_image_color(self, location, location_index, image_suffix, square_size=100, color_space="RGB", show_crop=False):
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
        
        # Real hardware mode
        try:
            # Move to the specified location for imaging
            self.logger.debug("Moving to imaging position")
            self.cnc_machine.move_to_location(location, location_index)
            
            # Capture and save the image (full frame)
            self.logger.debug("Capturing image")
            image_path = self.camera.capture_and_save(image_suffix)

            if image_path is not None:
                # Analyze the captured image for color values and save the center crop
                try:
                    self.logger.debug("Analyzing image for %s values", color_space)
                    color = self.camera.average_color_in_center(image_path, square_size,
                                                           show_crop=show_crop, save_crop=True, color_space=color_space)
                    if color_space == "RGB":
                        self.logger.info("RGB analysis completed: (%.1f, %.1f, %.1f)", color["R"], color["G"], color["B"])
                    elif color_space == "RGBA":
                        self.logger.info("RGBA analysis completed: (%.1f, %.1f, %.1f, %.1f)", color["R"], color["G"], color["B"], color["A"])
                    elif color_space == "LAB":
                        self.logger.info("LAB analysis completed: (%.1f, %.1f, %.1f)", color["L"], color["A"], color["B"])
                    elif color_space == "HSV":
                        self.logger.info("HSV analysis completed: (%.1f, %.1f, %.1f)", color["H"], color["S"], color["V"])

                    # Remove the full-frame file; keep only the saved crop. Only attempt
                    # to remove if camera is not virtual and the file exists.
                    try:
                        if not getattr(self.camera, 'virtual', False) and os.path.exists(image_path):
                            os.remove(image_path)
                            self.logger.debug("Removed full image file: %s", image_path)
                    except Exception:
                        self.logger.warning("Failed to remove full image file: %s", image_path)

                    return color

                except Exception:
                    # If processing failed, leave the original image for inspection
                    self.logger.exception("Failed to process captured image")
                    raise
            else:
                self.logger.error("Image capture failed")
                return None
                
        except Exception as e:
            self.logger.error("Image capture and analysis failed: %s", e)
            return None