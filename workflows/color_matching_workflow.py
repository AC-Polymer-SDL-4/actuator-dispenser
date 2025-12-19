"""
Color Matching Bayesian Optimization Workflow

This workflow uses Bayesian optimization to find optimal color mixing ratios
to match a target color sample. It iteratively creates color mixtures, analyzes
their RGB values, and optimizes the next batch of experiments.

Hardware setup:
- Reservoir positions:
  0: Red colorant
  1: Yellow colorant  
  2: Blue colorant
  3: Water (diluent)
  4: Wash solution
  5: Waste container
- Well plate positions 0-23 for experiments
- Target sample is manually placed at well_plate position 0

Workflow:
1. Read RGB values from target sample at well_plate position 0
2. Generate initial batch of n=5 wells using Bayesian optimization
3. Create mixtures by dispensing from reservoirs to well plate
4. Condition system between wash and waste
5. Analyze RGB of created wells
6. Feed results back to optimizer
7. Repeat with n=3 wells per batch until well plate is full
"""

from base_workflow import Liquid_Dispenser, start_workflow_logging

# Optimizer Selection - Change this to switch optimization methods
# 'baybe' - Bayesian optimization (default, good exploration)
# 'gradient' - Gradient descent (fast convergence, may find local minima)
# 'convex' - Convex optimization (global optimum if problem is convex)
OPTIMIZER_TYPE = 'gradient'  # Options: 'baybe', 'gradient', 'convex'

# Import the selected optimizer
if OPTIMIZER_TYPE == 'baybe':
    from color_matching_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
elif OPTIMIZER_TYPE == 'gradient':
    from color_matching_gradient_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
elif OPTIMIZER_TYPE == 'convex':
    from color_matching_convex_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
else:
    raise ValueError(f"Unknown optimizer type: {OPTIMIZER_TYPE}. Choose 'baybe', 'gradient', or 'convex'")

import pandas as pd
import numpy as np          
import time
import logging
import os
import datetime
import cv2


# Workflow configuration
INITIAL_BATCH_SIZE = 5 # First batch of wells to create (5)
SUBSEQUENT_BATCH_SIZE = 3  # Size of subsequent batches (3)
MAX_WELLS = 24  # Maximum number of wells on plate (24)
TARGET_WELL = 0  # Index of well containing the target sample
RANDOM_SEED = 31

VIRTUAL = True #saves data by default when NOT virtual
SAVE_DATA = True #option to save data when virtual
WITHOUT_WATER = True

# Choose optimization method at the top of this file by setting OPTIMIZER_TYPE
# 'baybe' - Bayesian optimization (default, good exploration)
# 'gradient' - Gradient descent (fast convergence, may find local minima)
# 'convex' - Convex optimization (global optimum if problem is convex)
OPTIMIZER_TYPE = 'baybe'

# Choose initialization method for ALL optimizers
# 'corner' - Deterministic corner points (pure colors, mixes, equal blend)
# 'sobol' - Space-filling Sobol sequence (pseudo-random with good coverage)
INITIALIZATION_METHOD = 'sobol'

# Choose color space for matching: 'RGB', 'RGBA', 'HSV', or 'LAB'
COLOR_SPACE = 'LAB'
COLOR_SPACE = COLOR_SPACE.upper() #just to make sure it's in uppercase

# Reservoir mapping
RESERVOIRS = {
    'R': 0,      # Red colorant
    'B': 1,      # Yellow colorant  
    'Y': 2,      # Blue colorant
    'Water': 3,  # Water/diluent
    'wash': 4,   # Wash solution
    'condition_water_1': 5,   # Condition water
    'condition_waste_1': 6,   # Condition waste
    'condition_water_2': 7,   # Second condition water (if needed)
    'condition_waste_2': 8,   # Second condition waste (if needed)
    'waste': 9   # Waste container
}

SPEED = 41000  #default speed for dispensing (32768/2 with old syringe)
RINSE_SPEED = 41000   #speed for rinsing needle
CONDITION_BEFORE_RINSE = True  #Whether to do a condition step before rinsing (used for concentrated solutions to contaminate the wash a bit less)

# Get workflow name (file name without extension)
workflow_name = os.path.splitext(os.path.basename(__file__))[0]
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

virtual_tag = "_virtual" if VIRTUAL else ""
output_dir = os.path.join("output", workflow_name, f"{timestamp}{virtual_tag}_{COLOR_SPACE}")


def rgb_distance(rgb1, rgb2):
    """Calculate Euclidean distance between two RGB colors."""
    return np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(rgb1, rgb2)))

def hue_distance_deg(h1, h2):
    d = abs(h1 - h2) % 360
    if d > 180:
        d = 360 - d
    return d

def hsv_distance(hsv1, hsv2, weights=(0.6, 0.2, 0.2)):
    if hsv1 is None or hsv2 is None:
        return float('inf')
    h1, s1, v1 = hsv1
    h2, s2, v2 = hsv2
    dh = hue_distance_deg(h1, h2) / 180.0
    ds = abs(s1 - s2)
    dv = abs(v1 - v2)
    w_h, w_s, w_v = weights
    return np.sqrt((w_h * dh) ** 2 + (w_s * ds) ** 2 + (w_v * dv) ** 2)

def lab_distance(lab1, lab2):
    if lab1 is None or lab2 is None:
        return float('inf')
    return np.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(lab1, lab2)))

def get_color_distance(target_col, sample_col, color_space=COLOR_SPACE):
    target_col = tuple(target_col.values())
    sample_col = tuple(sample_col.values())

    if color_space == 'RGB' or color_space == 'RGBA':
        return rgb_distance(target_col, sample_col)
    elif color_space == 'HSV':
        return hsv_distance(target_col, sample_col)
    elif color_space == 'LAB':
        return lab_distance(target_col, sample_col)
    else:
        return None

def get_color_str(color_dict): #outputs a string representation of color dict (universal for all color spaces)
    return ", ".join(f"{k}={float(v):.3f}" for k, v in color_dict.items())


def volumes_to_milliliters(volumes_dict, total_volume_ml=1.0):
    """
    Convert optimizer volume units to milliliters.
    
    Args:
        volumes_dict: Dictionary with volume ratios from optimizer
        total_volume_ml: Total volume to dispense in milliliters (default = 1.0 mL)
        
    Returns:
        Dictionary with volumes in milliliters
    """
    # Normalize volumes to ensure they sum to total_volume_ml
    total_parts = sum(volumes_dict.values())
    if total_parts == 0:
        return {k: 0 for k in volumes_dict}
    
    factor = total_volume_ml / total_parts
    return {k: v * factor for k, v in volumes_dict.items()}

def create_mixture_at_well(dispenser, well_index, volumes_ml, logger):
    """
    Create a color mixture at the specified well by dispensing from reservoirs.
    
    Args:
        dispenser: Liquid_Dispenser instance
        well_index: Target well index (1-23, since 0 is target sample)
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
                dispense_mix_volume=0.4
            else:
                dispense_mix_volume=0

            dispenser.dispense_between(
                source_location="reservoir_12",
                source_index=reservoir_index,
                dest_location="well_plate", 
                dest_index=well_index,
                transfer_vol=volume_ml,  # Now in mL as expected
                mixing_vol=dispense_mix_volume,
                num_mixes = 5 if component == last_component else 0,
                speed = SPEED,
            )

            if CONDITION_BEFORE_RINSE:
                vol_pipet = min(volume_ml+0.1, 0.45) #maximum pipet volume 0.45mL
                if well_index > MAX_WELLS/2:
                    i = 2
                else:
                    i = 1
                dispenser.condition_needle(
                    source_location="reservoir_12", 
                    source_index=RESERVOIRS[f'condition_water_{i}'],
                    dest_location="reservoir_12",
                    dest_index=RESERVOIRS[f'condition_waste_{i}'],
                    vol_pipet = vol_pipet,
                    speed = SPEED,
                    num_conditions = 1
                )

            dispenser.rinse_needle(
                wash_location="reservoir_12", 
                wash_index=RESERVOIRS['wash'], 
                num_mixes=3,
                speed=RINSE_SPEED
            )
            
            # Small delay between dispenses
            if not VIRTUAL:
                time.sleep(0.5)

def condition_system(dispenser, logger):
    """
    Condition the dispensing system by moving between wash and waste.
    """
    logger.info("Conditioning system between wash and waste")
    
    dispenser.dispense_condition(
        source_location="reservoir_12",
        source_index=RESERVOIRS['wash'],
        dest_location="reservoir_12",
        dest_index=RESERVOIRS['waste']
    )



def main():
    """Main color matching workflow."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"color_matching_workflow{virtual_tag}_{timestamp}.log"

    # Initialize logging
    logger = start_workflow_logging("color_matching_workflow", log_filename=log_filename, virtual=VIRTUAL)
    logger.info("=" * 60)
    logger.info("Starting Color Matching Bayesian Optimization Workflow")
    logger.info("=" * 60)
    
    # Initialize hardware (virtual mode for testing)
    logger.info("Initializing hardware...")
    dispenser = Liquid_Dispenser(
        cnc_comport="COM5", 
        actuator_comport="COM3", #non-gaming computer
        virtual=VIRTUAL,  # Set to False for real hardware
        camera_index=0, #for non-gaming computer
        log_level=logging.INFO,
        output_dir=output_dir,
        log_filename = log_filename,
    )
    dispenser.cnc_machine.Z_LOW_BOUND = -70  # Adjust as needed
    dispenser.cnc_machine.home() #Home machine

    if not dispenser.virtual:
        import slack_agent
        secrets = slack_agent.load_secrets()

        SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
        SLACK_WEBHOOK_URL = secrets["SLACK_WEBHOOK_URL"]
        SLACK_CHANNEL = "C09J10VQ02C"
        slack_agent.send_slack_message("Color Matching Workflow started on real hardware.", SLACK_CHANNEL)

    try:
        # Step 1: Read target color from well 0
        logger.info("Step 1: Reading target color values from sample at well 0")
        target_color = dispenser.get_image_color("well_plate_camera", TARGET_WELL, "target_sample", square_size=60, color_space=COLOR_SPACE, show_crop=True)

        # Handle virtual mode where camera may return None
        if target_color is None:
            logger.warning("Camera returned None (likely virtual mode), using default target color")
            if COLOR_SPACE == 'RGB':
                target_color = {'R': 180, 'G': 120, 'B': 80}  # Brownish target
            elif COLOR_SPACE == 'HSV':
                target_color = {'H': 25, 'S': 0.6, 'V': 0.7}  # Brownish in HSV
            elif COLOR_SPACE == 'LAB':
                target_color = {'L': 50, 'A': 20, 'B': 30}    # Brownish in LAB
            else:
                target_color = {'R': 180, 'G': 120, 'B': 80}  # Default to RGB

        logger.info(f"Target {COLOR_SPACE} values: {get_color_str(target_color)}") #log the target color values

        # Calculate upper bound for optimization (max possible distance) - keep RGB max for optimizer scaling
        max_distance = rgb_distance([0, 0, 0], [255, 255, 255])  # Max possible RGB distance

        # Initialize optimization campaign
        logger.info(f"Initializing {OPTIMIZER_TYPE} optimization campaign...")
        
        # Convert clear parameter to optimizer's expected format
        use_sobol_initialization = (INITIALIZATION_METHOD.lower() == 'sobol')
        
        campaign, searchspace = initialize_campaign(
            upper_bound=50,
            random_seed=RANDOM_SEED,
            random_recs=use_sobol_initialization
        )
        
        # Set target color for convex optimizer (if applicable)
        if OPTIMIZER_TYPE == 'convex' and hasattr(campaign, 'set_target_color'):
            # Convert target color to RGB for convex optimizer
            if COLOR_SPACE == 'RGB':
                target_rgb = [target_color['R'], target_color['G'], target_color['B']]
            else:
                # Convert from other color spaces to RGB
                # For now, use a simple approximation - you might want more sophisticated conversion
                target_rgb = [128, 128, 128]  # Default neutral gray
            campaign.set_target_color(target_rgb)
        logger.info(f"{OPTIMIZER_TYPE.title()} optimization campaign initialized successfully")
        
        # Step 2: Generate and create initial batch
        logger.info(f"Step 2: Generating initial batch of {INITIAL_BATCH_SIZE} recommendations")
        campaign, initial_suggestions = get_initial_recommendations(campaign, INITIAL_BATCH_SIZE)
        logger.debug(f"Initial suggestions generated:\n{initial_suggestions}")
        
        # Display initial conditions for review
        logger.info("="*50)
        logger.info("INITIAL CONDITIONS GENERATED:")
        logger.info("="*50)
        logger.info(f"Optimizer: {OPTIMIZER_TYPE}")
        logger.info(f"Random seed: {RANDOM_SEED}")
        logger.info(f"Target color ({COLOR_SPACE}): {get_color_str(target_color)}")
        logger.info(f"Initial batch size: {INITIAL_BATCH_SIZE}")
        logger.info("\nInitial mixing recommendations:")
        for idx, (_, suggestion) in enumerate(initial_suggestions.iterrows()):
            volumes_dict = {
                'R': suggestion['R'],
                'Y': suggestion['Y'], 
                'B': suggestion['B'],
                'Water': suggestion['Water'] if not WITHOUT_WATER else 0
            }
            volumes_ml = volumes_to_milliliters(volumes_dict)
            logger.info(f"  Well {idx+1}: R={volumes_ml['R']:.3f}mL, Y={volumes_ml['Y']:.3f}mL, B={volumes_ml['B']:.3f}mL, Water={volumes_ml['Water']:.3f}mL")
        
        logger.info("="*50)
        
        # Pause for user review
        if VIRTUAL:
            response = input("\nPress Enter to continue with these initial conditions, or 'q' to quit: ")
            if response.lower().strip() == 'q':
                logger.info("Workflow terminated by user")
                return
        
        # Create initial mixtures
        results_data = []
        current_well = 1  # Start at well 1 (well 0 is target sample)
        
        logger.info("Creating initial mixture batch...")
        for idx, (_, suggestion) in enumerate(initial_suggestions.iterrows()):
            if current_well >= MAX_WELLS:
                logger.warning("Reached maximum number of wells, stopping...")
                break
                
            # Convert optimizer units to milliliters
            volumes_dict = {
                'R': suggestion['R'],
                'Y': suggestion['Y'], 
                'B': suggestion['B'],
                'Water': suggestion['Water'] if not WITHOUT_WATER else 0 #adds 0 for no water
            }

            volumes_ml = volumes_to_milliliters(volumes_dict)
            
            # Create mixture
            create_mixture_at_well(dispenser, current_well, volumes_ml, logger)
            
            # Store experiment details
            results_data.append({
                'well': current_well,
                'R_volume_ml': round(volumes_ml['R'], 2),
                'Y_volume_ml': round(volumes_ml['Y'], 2),
                'B_volume_ml': round(volumes_ml['B'], 2),
                'Water_volume_ml': round(volumes_ml['Water'], 2) if not WITHOUT_WATER else 0, #adds 0 for no water
                # 'R': suggestion['R'],  # Original optimizer values
                # 'Y': suggestion['Y'],
                # 'B': suggestion['B'],
                # 'Water': suggestion['Water']
            })
            
            current_well += 1
        
        # Step 3: Analyze RGB of initial wells
        logger.info("Step 3: Analyzing RGB values of initial wells...")
        
        results_list = []
        for i, result in enumerate(results_data):
            well_idx = result['well']
            logger.debug(f"Analyzing RGB for well {well_idx}")
            
            well_color = dispenser.get_image_color("well_plate_camera", well_idx, f"experiment_{well_idx}", square_size=60, color_space=COLOR_SPACE)
            
            for key, value in well_color.items(): #store the resulting color values
                result[f'measured_{key}'] = round(value, 2)

            distance = get_color_distance(target_color, well_color, color_space=COLOR_SPACE)

            results_list.append(distance)  # Store for adding to suggestions DataFrame
            result['output'] = distance  # Store in our tracking data
            
            logger.info(f"Well {well_idx}: {COLOR_SPACE}={get_color_str(well_color)}, Distance={distance:.1f}") #Outputting the RGB values for logging
            
            if (not dispenser.virtual) or SAVE_DATA:
                results_df = pd.DataFrame(results_data)

                # Append target color as a reference row
                target_row = {}
                for col in results_df.columns:
                    if col == 'well':
                        target_row[col] = "Target"
                    elif col.startswith("measured_"):
                        channel = col.replace("measured_", "")
                        target_row[col] = target_color.get(channel, np.nan)
                    else:
                        target_row[col] = np.nan
                results_df = pd.concat([results_df, pd.DataFrame([target_row])], ignore_index=True)

                os.makedirs(output_dir, exist_ok=True)
                results_file = os.path.join(output_dir, "color_matching_results.csv")
                results_df.to_csv(results_file, index=False)
                logger.info(f"Progress (including target) saved to {results_file}")

        # Add results to the suggestions dataframe (this is what the optimizer expects)
        initial_suggestions['output'] = results_list
        campaign_data = initial_suggestions.copy()  # Track all experiments
        
        # Step 4: Iterative optimization loop
        batch_number = 1
        
        while current_well < MAX_WELLS:
            logger.info(f"Step 4.{batch_number}: Starting optimization iteration {batch_number}")
            
            # Get new recommendations based on all previous results
            remaining_wells = min(SUBSEQUENT_BATCH_SIZE, MAX_WELLS - current_well)
            logger.info(f"Getting {remaining_wells} new recommendations...")
            
            campaign, new_suggestions = get_new_recs_from_results(
                campaign, campaign_data, remaining_wells
            )
            
            logger.debug(f"Generated {len(new_suggestions)} new suggestions:")
            logger.debug(f"\n{new_suggestions}")
            
            # Create new mixtures
            batch_results = []
            results_list = []
            
            for idx, (_, suggestion) in enumerate(new_suggestions.iterrows()):
                if current_well >= MAX_WELLS:
                    break
                    
                # Convert to milliliters
                volumes_dict = {
                    'R': suggestion['R'],
                    'Y': suggestion['Y'],
                    'B': suggestion['B'], 
                    'Water': suggestion['Water'] if not WITHOUT_WATER else 0
                }
                volumes_ml = volumes_to_milliliters(volumes_dict)
                
                # Create mixture
                create_mixture_at_well(dispenser, current_well, volumes_ml, logger)
                
                # Store results
                batch_result = {
                    'well': current_well,
                    'R_volume_ml': round(volumes_ml['R'], 2),
                    'Y_volume_ml': round(volumes_ml['Y'], 2),
                    'B_volume_ml': round(volumes_ml['B'], 2),
                    'Water_volume_ml': round(volumes_ml['Water'], 2) if not WITHOUT_WATER else 0, #adds 0 for no water
                    # 'R': suggestion['R'],
                    # 'Y': suggestion['Y'],
                    # 'B': suggestion['B'],
                    # 'Water': suggestion['Water']
                }
                batch_results.append(batch_result)
                current_well += 1
            
            # Analyze new wells
            logger.info(f"Analyzing RGB values for batch {batch_number}...")
            if not VIRTUAL:
                time.sleep(2)
            
            for i, result in enumerate(batch_results):
                well_idx = result['well'] 
                well_color = dispenser.get_image_color("well_plate_camera", well_idx, f"experiment_{well_idx}", square_size=60, color_space=COLOR_SPACE)
                
                for key, value in well_color.items(): #store the resulting color values
                    result[f'measured_{key}'] = round(value, 2)

                distance = get_color_distance(target_color, well_color, color_space=COLOR_SPACE)

                results_list.append(distance)  # Store for adding to suggestions DataFrame
                result['output'] = distance  # Store in our tracking data

                logger.info(f"Well {well_idx}: {COLOR_SPACE}={get_color_str(well_color)}, Distance={distance:.1f}")

            # Add results to the new suggestions and combine with campaign data
            new_suggestions['output'] = results_list
            campaign_data = pd.concat([campaign_data, new_suggestions], ignore_index=True)
            
            # Add batch results to overall results tracking
            results_data.extend(batch_results)
            batch_number += 1

            # Save partial CSV after each batch (overwrite same file)
            if (not dispenser.virtual) or SAVE_DATA:
                results_df = pd.DataFrame(results_data)

                # Append target color as a reference row
                target_row = {}
                for col in results_df.columns:
                    if col == 'well':
                        target_row[col] = "Target"
                    elif col.startswith("measured_"):
                        channel = col.replace("measured_", "")
                        target_row[col] = target_color.get(channel, np.nan)
                    else:
                        target_row[col] = np.nan
                results_df = pd.concat([results_df, pd.DataFrame([target_row])], ignore_index=True)

                os.makedirs(output_dir, exist_ok=True)
                results_file = os.path.join(output_dir, "color_matching_results.csv")
                results_df.to_csv(results_file, index=False)
                logger.info(f"Progress (including target) saved to {results_file}")
        
        # Final analysis
        logger.info("=" * 60)
        logger.info("WORKFLOW COMPLETE - FINAL ANALYSIS")
        logger.info("=" * 60)
        
        # Find best result
        best_result = min(results_data, key=lambda x: x['output'])
        logger.info(f"Best color match found at well {best_result['well']}")
        logger.info(f"Distance to target: {best_result['output']:.2f}")
        #logger.info(f"RGB: ({best_result['measured_R']}, {best_result['measured_G']}, {best_result['measured_B']})")
        logger.info(f"{COLOR_SPACE}: {get_color_str({k.replace('measured_',''):v for k,v in best_result.items() if k.startswith('measured_')})}")        
        logger.info(f"Recipe: R={best_result['R_volume_ml']:.3f}mL, Y={best_result['Y_volume_ml']:.3f}mL, B={best_result['B_volume_ml']:.3f}mL, Water={best_result['Water_volume_ml']:.3f}mL" if not WITHOUT_WATER else f"Recipe: R={best_result['R_volume_ml']:.3f}mL, Y={best_result['Y_volume_ml']:.3f}mL, B={best_result['B_volume_ml']:.3f}mL, Water=0mL")
        
        if (not dispenser.virtual) or SAVE_DATA:
            # Save results to CSV inside the workflow output directory
            results_df = pd.DataFrame(results_data)

            # Append the target RGB as an extra row at the end of the CSV.
            # This does not modify any data structures used by the optimizer;
            # it's only for record-keeping in the saved CSV.
            try:
                target_row = {}
                for col in results_df.columns:
                    if col == 'well':
                        target_row[col] = "Target"
                    elif col.startswith("measured_"):
                        # Extract the color channel from column name
                        channel = col.replace("measured_", "")
                        # Fill with target value if present, else NaN
                        target_row[col] = target_color.get(channel, np.nan)
                    else:
                        # Other columns stay NaN
                        target_row[col] = np.nan

                # concat the single-row DataFrame to the results
                results_df = pd.concat([results_df, pd.DataFrame([target_row])], ignore_index=True)
            except Exception:
                logger.exception("Failed to append target RGB row; saving without it.")

            # Ensure the output directory exists
            os.makedirs(output_dir, exist_ok=True)
            results_file = os.path.join(output_dir, f"color_matching_results.csv")
            results_df.to_csv(results_file, index=False)
            logger.info(f"Results saved to {results_file}")


        # Summary statistics
        distances = [r['output'] for r in results_data]
        logger.info(f"Summary statistics:")
        logger.info(f"  Min distance: {min(distances):.2f}")
        logger.info(f"  Max distance: {max(distances):.2f}")
        logger.info(f"  Mean distance: {np.mean(distances):.2f}")
        logger.info(f"  Std distance: {np.std(distances):.2f}")
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {str(e)}")
        logger.error(f"Error details: {repr(e)}")
        raise
        
    finally:
        logger.info("Workflow completed. Moving to origin position.")
        dispenser.cnc_machine.move_to_point(z=0)
        dispenser.move_to_origin()

    if not dispenser.virtual:
        slack_agent.send_slack_message("Color Matching Workflow finished on real hardware.", SLACK_CHANNEL)

if __name__ == "__main__":
    main()