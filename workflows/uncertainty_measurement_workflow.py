"""
Uncertainty Measurement Workflow

This workflow systematically measures color values from all 24 wells with replicate measurements
to quantify two types of uncertainty:
- MEASUREMENT uncertainty: from m=6 replicate photos of each well
- PROCESS uncertainty: from n=6 identical wells (groups of 6 wells with same composition)

Well plate layout:
- Wells 0-5: Group 1 (identical composition)
- Wells 6-11: Group 2 (identical composition) 
- Wells 12-17: Group 3 (identical composition)
- Wells 18-23: Group 4 (identical composition)

For each well:
- Takes m=6 replicate photos
- Analyzes each photo in RGB, LAB, and HSV color spaces
- Stores individual measurements for uncertainty analysis

Data output structure:
- 24 wells × 6 measurements × 3 color spaces = 432 total color measurements
- Each measurement includes: well_id, group_id, replicate_id, RGB, LAB, HSV values
- Statistical analysis of measurement vs process uncertainty

Modes:
- MANUAL_MODE = True: Only imaging, no pipetting (for manually prepared wells)
- MANUAL_MODE = False: Full pipetting + imaging workflow (to be implemented)
"""
#test
from base_workflow import Liquid_Dispenser, start_workflow_logging
import pandas as pd
import numpy as np
import time
import logging
import os
import datetime
import cv2
from typing import Dict, List, Tuple, Any

RANDOM_VARIABLE = None

# Workflow configuration
NUM_WELLS = 24  # Total wells to measure
WELLS_PER_GROUP = 6  # Number of identical wells per group
NUM_REPLICATES = 6  # Number of replicate photos per well (m)
COLOR_SPACES = ['RGB', 'LAB', 'HSV']  # Color spaces to analyze

# Operation mode
MANUAL_MODE = False  # True: Only imaging, False: Pipetting + imaging
VIRTUAL = False  # Set False to run on real hardware
SAVE_DATA = True  # Save data even in virtual mode

# Reservoir mapping (for future pipetting mode)
RESERVOIRS = {
    'R': 0,      # Red colorant
    'Y': 1,      # Yellow colorant  
    'B': 2,      # Blue colorant
    
    'Water': 3,  # Water/diluent # this one needs water
    'wash': 4,   # Wash solution # this one needs water
    'condition_water_1': 5,   # Condition water # this one needs water
    'condition_waste_1': 6,   # Condition waste
    'condition_water_2': 7,   # Second condition water (if needed) # this one needs water
    'condition_waste_2': 8,   # Second condition waste (if needed)
    'waste': 9   # Waste container
}

# Imaging parameters
SQUARE_SIZE = 60  # Size of crop area for color analysis
DELAY_BETWEEN_MEASUREMENTS = 0.5  # Delay between replicate photos (seconds)

# Get workflow name and create output directory
workflow_name = os.path.splitext(os.path.basename(__file__))[0]
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
virtual_tag = "_virtual" if VIRTUAL else ""
mode_tag = "_manual" if MANUAL_MODE else "_automated"
output_dir = os.path.join("output", workflow_name, f"{timestamp}{virtual_tag}{mode_tag}")

def get_well_group(well_index: int) -> int:
    """
    Get the group ID for a given well index.
    Groups: 0-5=Group1, 6-11=Group2, 12-17=Group3, 18-23=Group4
    """
    return (well_index // WELLS_PER_GROUP) + 1

def convert_color_to_all_spaces(dispenser, location: str, well_index: int, 
                                measurement_id: str, square_size: int = SQUARE_SIZE) -> Dict[str, Dict[str, float]]:
    """
    Capture one image and convert to all color spaces (RGB, LAB, HSV).
    Returns dictionary with all color space values.
    """
    # Get RGB first (this captures the image)
    rgb_color = dispenser.get_image_color(location, well_index, measurement_id, 
                                        square_size=square_size, color_space='RGB', show_crop=False)
    
    # Convert same image to other color spaces
    lab_color = dispenser.get_image_color(location, well_index, measurement_id, 
                                        square_size=square_size, color_space='LAB', show_crop=False)
    
    hsv_color = dispenser.get_image_color(location, well_index, measurement_id, 
                                        square_size=square_size, color_space='HSV', show_crop=False)
    
    return {
        'RGB': rgb_color,
        'LAB': lab_color, 
        'HSV': hsv_color
    }

def measure_well_replicates(dispenser, well_index: int, logger) -> List[Dict[str, Any]]:
    """
    Measure a single well with multiple replicates.
    Returns list of measurements, one per replicate.
    """
    logger.info(f"Measuring well {well_index} with {NUM_REPLICATES} replicates...")
    
    measurements = []
    group_id = get_well_group(well_index)
    
    for replicate in range(NUM_REPLICATES):
        measurement_id = f"well_{well_index:02d}_rep_{replicate+1:02d}"
        logger.debug(f"Taking replicate {replicate+1}/{NUM_REPLICATES} for well {well_index}")
        
        # Capture all color spaces for this replicate
        colors = convert_color_to_all_spaces(dispenser, "well_plate_camera", well_index, measurement_id)
        
        # Create measurement record
        measurement = {
            'well_index': well_index,
            'group_id': group_id,
            'replicate_id': replicate + 1,
            'measurement_id': measurement_id,
            'timestamp': datetime.datetime.now().isoformat(),
        }
        
        # Add color values for each color space
        for color_space, color_values in colors.items():
            for channel, value in color_values.items():
                measurement[f"{color_space}_{channel}"] = round(float(value), 3)
        
        measurements.append(measurement)
        logger.debug(f"Well {well_index}, Rep {replicate+1}: " + 
                    ", ".join([f"{cs}=({', '.join(f'{k}={v:.1f}' for k,v in colors[cs].items())})" 
                              for cs in COLOR_SPACES]))
        
        # Small delay between replicates to ensure independent measurements
        if not VIRTUAL and replicate < NUM_REPLICATES - 1:
            time.sleep(DELAY_BETWEEN_MEASUREMENTS)
    
    return measurements

def create_test_mixtures(dispenser, logger):
    """
    Create test mixtures in wells for uncertainty measurement.
    Creates 4 different compositions, with 6 identical wells each.
    """
    logger.info("Creating test mixtures for uncertainty measurement...")
    
    # Define 4 test compositions (volumes in mL) - MODIFY THESE VALUES AS NEEDED
    #TODO how the concentrations are chosen
    test_compositions = {
        1: {'R': 0.3, 'Y': 0.3, 'B': 0.3, 'Water': 0.1},  # Group 1: wells 0-5
        2: {'R': 0.7, 'Y': 0.1, 'B': 0.1, 'Water': 0.1},  # Group 2: wells 6-11  
        3: {'R': 0.1, 'Y': 0.7, 'B': 0.1, 'Water': 0.1},  # Group 3: wells 12-17
        4: {'R': 0.1, 'Y': 0.1, 'B': 0.7, 'Water': 0.1},  # Group 4: wells 18-23
    }
    
    logger.info("Test compositions defined:")
    for group_id, composition in test_compositions.items():
        wells_range = f"{(group_id-1)*6}-{group_id*6-1}"
        logger.info(f"  Group {group_id} (wells {wells_range}): "
                   f"R={composition['R']:.1f}mL, Y={composition['Y']:.1f}mL, "
                   f"B={composition['B']:.1f}mL, Water={composition['Water']:.1f}mL")
    
    # Create mixtures for each group
    for group_id in range(1, 5):
        composition = test_compositions[group_id]
        start_well = (group_id - 1) * WELLS_PER_GROUP
        end_well = start_well + WELLS_PER_GROUP
        
        logger.info(f"Creating Group {group_id} mixtures in wells {start_well}-{end_well-1}")
        
        # Create identical mixtures in all 6 wells for this group
        for well_index in range(start_well, end_well):
            logger.info(f"Creating mixture at well {well_index} (Group {group_id})")
            create_mixture_at_well(dispenser, well_index, composition, logger)
    
    logger.info("All test mixtures created successfully")

def create_mixture_at_well(dispenser, well_index, volumes_ml, logger):
    """
    Create a color mixture at the specified well by dispensing from reservoirs.
    
    Args:
        dispenser: Liquid_Dispenser instance
        well_index: Target well index (0-23)
        volumes_ml: Dictionary of volumes in milliliters for each component
        logger: Logger instance
    """
    logger.info(f"Creating mixture at well {well_index} with volumes: {volumes_ml}")
    
    # Find the last component with volume > 0 -> will mix after dispense
    last_component = None
    for component in reversed(list(volumes_ml.keys())):
        if volumes_ml[component] > 0 and component in RESERVOIRS:
            last_component = component
            break

    # Dispense each component
    for component, volume_ml in volumes_ml.items():
        if volume_ml > 0 and component in RESERVOIRS:
            reservoir_index = RESERVOIRS[component]
            logger.info(f"Dispensing {volume_ml:.3f}mL of {component} from reservoir {reservoir_index}")

            if component == last_component:
                dispense_mix_volume = 0.4
            else:
                dispense_mix_volume = 0

            dispenser.dispense_between(
                source_location="reservoir_12",
                source_index=reservoir_index,
                dest_location="well_plate", 
                dest_index=well_index,
                transfer_vol=volume_ml,
                mixing_vol=dispense_mix_volume,
                num_mixes=5 if component == last_component else 0,
                speed=41000,  # Default speed
            )

            # Condition needle between components
            vol_pipet = min(volume_ml + 0.1, 0.45)  # Maximum pipet volume 0.45mL
            condition_index = 2 if well_index > NUM_WELLS/2 else 1
            
            dispenser.condition_needle(
                source_location="reservoir_12", 
                source_index=RESERVOIRS[f'condition_water_{condition_index}'],
                dest_location="reservoir_12",
                dest_index=RESERVOIRS[f'condition_waste_{condition_index}'],
                vol_pipet=vol_pipet,
                speed=41000,
                num_conditions=1
            )

            # Rinse needle after each component
            dispenser.rinse_needle(
                wash_location="reservoir_12", 
                wash_index=RESERVOIRS['wash'], 
                num_mixes=3,
                speed=41000
            )
            
            # Small delay between dispenses
            if not VIRTUAL:
                time.sleep(0.5)

def calculate_uncertainties(measurements_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate measurement and process uncertainties from the collected data.
    
    Returns summary statistics with uncertainties for each group and color channel.
    """
    results = []
    
    # Group by well group and color channel
    for group_id in range(1, 5):  # Groups 1-4
        group_data = measurements_df[measurements_df['group_id'] == group_id]
        
        for color_space in COLOR_SPACES:
            # Get all channels for this color space
            color_columns = [col for col in measurements_df.columns if col.startswith(f"{color_space}_")]
            
            for channel_col in color_columns:
                channel_name = channel_col.replace(f"{color_space}_", "")
                
                # Calculate well means (average of replicates for each well)
                well_means = group_data.groupby('well_index')[channel_col].mean()
                
                # Measurement uncertainty: average within-well standard deviation
                well_stds = group_data.groupby('well_index')[channel_col].std()
                measurement_uncertainty = well_stds.mean()
                
                # Process uncertainty: standard deviation of well means
                process_uncertainty = well_means.std()
                
                # Overall statistics
                group_mean = group_data[channel_col].mean()
                group_std = group_data[channel_col].std()
                
                results.append({
                    'group_id': group_id,
                    'color_space': color_space,
                    'channel': channel_name,
                    'group_mean': round(group_mean, 3),
                    'group_std': round(group_std, 3),
                    'measurement_uncertainty': round(measurement_uncertainty, 3),
                    'process_uncertainty': round(process_uncertainty, 3),
                    'uncertainty_ratio': round(process_uncertainty / measurement_uncertainty, 3) if measurement_uncertainty > 0 else np.inf,
                    'num_wells': len(well_means),
                    'num_measurements': len(group_data)
                })
    
    return pd.DataFrame(results)

def save_results(all_measurements: List[Dict], logger):
    """Save measurement data and uncertainty analysis to CSV files."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Save raw measurements
    measurements_df = pd.DataFrame(all_measurements)
    measurements_file = os.path.join(output_dir, "uncertainty_measurements_raw.csv")
    measurements_df.to_csv(measurements_file, index=False)
    logger.info(f"Raw measurements saved to {measurements_file}")
    
    # Calculate and save uncertainties
    uncertainties_df = calculate_uncertainties(measurements_df)
    uncertainties_file = os.path.join(output_dir, "uncertainty_analysis.csv")
    uncertainties_df.to_csv(uncertainties_file, index=False)
    logger.info(f"Uncertainty analysis saved to {uncertainties_file}")
    
    # Save summary statistics
    summary_stats = generate_summary_statistics(measurements_df)
    summary_file = os.path.join(output_dir, "measurement_summary.csv")
    summary_stats.to_csv(summary_file, index=False)
    logger.info(f"Summary statistics saved to {summary_file}")
    
    return measurements_df, uncertainties_df, summary_stats

def generate_summary_statistics(measurements_df: pd.DataFrame) -> pd.DataFrame:
    """Generate summary statistics for each well."""
    
    summary_data = []
    
    for well_index in range(NUM_WELLS):
        well_data = measurements_df[measurements_df['well_index'] == well_index]
        group_id = get_well_group(well_index)
        
        if len(well_data) == 0:
            continue
            
        summary_row = {
            'well_index': well_index,
            'group_id': group_id,
            'num_replicates': len(well_data)
        }
        
        # Add mean and std for each color channel
        for color_space in COLOR_SPACES:
            color_columns = [col for col in measurements_df.columns if col.startswith(f"{color_space}_")]
            
            for channel_col in color_columns:
                channel_name = channel_col.replace(f"{color_space}_", "")
                
                mean_val = well_data[channel_col].mean()
                std_val = well_data[channel_col].std()
                
                summary_row[f"{color_space}_{channel_name}_mean"] = round(mean_val, 3)
                summary_row[f"{color_space}_{channel_name}_std"] = round(std_val, 3)
        
        summary_data.append(summary_row)
    
    return pd.DataFrame(summary_data)

def main():
    """Main uncertainty measurement workflow."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"uncertainty_measurement{virtual_tag}{mode_tag}_{timestamp}.log"
    
    # Create a single logger first to avoid rotating file conflicts
    logger = start_workflow_logging("uncertainty_measurement", log_filename=log_filename, virtual=VIRTUAL)
    
    logger.info("=" * 60)
    logger.info("Starting Uncertainty Measurement Workflow")
    logger.info("=" * 60)
    logger.info(f"Mode: {'Manual (imaging only)' if MANUAL_MODE else 'Automated (pipetting + imaging)'}")
    logger.info(f"Wells to measure: {NUM_WELLS}")
    logger.info(f"Wells per group: {WELLS_PER_GROUP}")
    logger.info(f"Replicates per well: {NUM_REPLICATES}")
    logger.info(f"Color spaces: {', '.join(COLOR_SPACES)}")
    logger.info(f"Total measurements: {NUM_WELLS * NUM_REPLICATES * len(COLOR_SPACES)} color measurements")
    
    # Initialize hardware with console logging only to avoid file conflicts
    logger.info("Initializing hardware...")
    dispenser = Liquid_Dispenser(
        cnc_comport="COM5",
        actuator_comport="COM3",
        virtual=VIRTUAL,
        camera_index=0,
        log_level=logging.WARNING,  # Minimize dispenser logging to console only
        output_dir=output_dir,
        log_filename=None,  # Force console logging only for dispenser
    )
    dispenser.cnc_machine.Z_LOW_BOUND = -70
    dispenser.cnc_machine.home()

    # Preflight camera check: ensure we can capture a test frame before workflow
    try:
        logger.info("Running camera preflight check...")
        # Move to camera imaging position for a valid scene
        try:
            dispenser.cnc_machine.move_to_location("well_plate_camera", 0, safe=True)
        except Exception:
            pass
        preflight_ok = False
        for attempt in range(1, 3):
            img = dispenser.camera.capture_and_save(f"preflight_{attempt}")
            if img:
                logger.info(f"Camera preflight succeeded on attempt {attempt}: {img}")
                preflight_ok = True
                break
            else:
                logger.warning(f"Camera preflight attempt {attempt} failed; retrying...")
                time.sleep(0.5)
        if not preflight_ok:
            raise RuntimeError("Camera preflight failed — aborting workflow.")
    except Exception as e:
        logger.error(f"Camera preflight error: {e}")
        raise

    # --- Custom priming: 5x dispense_between (res 7→7), then blowout ---
    logger.info("Priming: 5x dispense_between from reservoir 7 to 7...")
    for i in range(5):
        dispenser.dispense_between(
            source_location="reservoir_12",
            source_index=7,
            dest_location="reservoir_12",
            dest_index=7,
            transfer_vol=0.45,
            mixing_vol=0,
            num_mixes=0,
            speed=41000
        )
        logger.info(f"Priming repetition {i+1}/5 complete.")
    logger.info("Performing blowout after priming using condition_needle...")
    dispenser.condition_needle(
        source_location="reservoir_12",
        source_index=7,
        dest_location="reservoir_12",
        dest_index=7,
        num_conditions=1,
        vol_pipet=0.45,
        speed=41000
    )
    logger.info("Blowout complete.")
    
    # Send Slack notification if using real hardware
    if not dispenser.virtual:
        try:
            import slack_agent
            secrets = slack_agent.load_secrets()
            SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
            SLACK_WEBHOOK_URL = secrets["SLACK_WEBHOOK_URL"]
            SLACK_CHANNEL = "C09J10VQ02C"
            slack_agent.send_slack_message("Uncertainty Measurement Workflow started on real hardware.", SLACK_CHANNEL)
        except:
            logger.warning("Could not send Slack notification")
    
    try:
        # Step 1: Create mixtures if in automated mode
        if not MANUAL_MODE:
            logger.info("Step 1: Creating test mixtures...")
            create_test_mixtures(dispenser, logger)
        else:
            logger.info("Step 1: Skipping mixture creation (manual mode - assuming wells are pre-prepared)")
        
        # Step 2: Systematic measurement of all wells
        logger.info("Step 2: Starting systematic measurement of all wells...")
        
        all_measurements = []
        
        # Measure each well with replicates
        for well_index in range(NUM_WELLS):
            group_id = get_well_group(well_index)
            logger.info(f"Processing well {well_index} (Group {group_id})")
            
            # Get replicate measurements for this well
            well_measurements = measure_well_replicates(dispenser, well_index, logger)
            all_measurements.extend(well_measurements)
            
            # Save progress periodically
            if (well_index + 1) % 6 == 0:  # Every 6 wells (each group)
                logger.info(f"Completed group {group_id} (wells {well_index-5} to {well_index})")
                if SAVE_DATA:
                    # Save intermediate results
                    temp_df = pd.DataFrame(all_measurements)
                    os.makedirs(output_dir, exist_ok=True)
                    temp_file = os.path.join(output_dir, f"measurements_progress_group_{group_id}.csv")
                    temp_df.to_csv(temp_file, index=False)
                    logger.info(f"Progress saved to {temp_file}")
        
        # Step 3: Save final results and calculate uncertainties
        logger.info("Step 3: Analyzing results and calculating uncertainties...")
        
        if SAVE_DATA or not VIRTUAL:
            measurements_df, uncertainties_df, summary_stats = save_results(all_measurements, logger)
            
            # Log key findings
            logger.info("=" * 60)
            logger.info("UNCERTAINTY ANALYSIS RESULTS")
            logger.info("=" * 60)
            
            # Show uncertainty summary for each group
            for group_id in range(1, 5):
                group_uncertainties = uncertainties_df[uncertainties_df['group_id'] == group_id]
                logger.info(f"\nGroup {group_id} uncertainty summary:")
                
                for color_space in COLOR_SPACES:
                    cs_data = group_uncertainties[group_uncertainties['color_space'] == color_space]
                    if len(cs_data) > 0:
                        avg_measurement_unc = cs_data['measurement_uncertainty'].mean()
                        avg_process_unc = cs_data['process_uncertainty'].mean()
                        avg_ratio = cs_data['uncertainty_ratio'].mean()
                        logger.info(f"  {color_space}: Measurement={avg_measurement_unc:.3f}, "
                                  f"Process={avg_process_unc:.3f}, Ratio={avg_ratio:.2f}")
            
            # Overall statistics
            total_measurements = len(all_measurements)
            avg_measurement_unc = uncertainties_df['measurement_uncertainty'].mean()
            avg_process_unc = uncertainties_df['process_uncertainty'].mean()
            
            logger.info(f"\nOverall Summary:")
            logger.info(f"Total measurements collected: {total_measurements}")
            logger.info(f"Average measurement uncertainty: {avg_measurement_unc:.3f}")
            logger.info(f"Average process uncertainty: {avg_process_unc:.3f}")
            logger.info(f"Average uncertainty ratio (Process/Measurement): {avg_process_unc/avg_measurement_unc:.2f}")
        
        logger.info("=" * 60)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {str(e)}")
        logger.error(f"Error details: {repr(e)}")
        raise
        
    finally:
        logger.info("Moving to origin position...")
        dispenser.cnc_machine.move_to_point(z=0)
        dispenser.move_to_origin()
    
    # Send completion notification
    if not dispenser.virtual:
        try:
            slack_agent.send_slack_message("Uncertainty Measurement Workflow completed on real hardware.", SLACK_CHANNEL)
        except:
            pass

if __name__ == "__main__":
    main()