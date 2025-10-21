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
from color_matching_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
import pandas as pd
import numpy as np
import time
import logging
import os
import datetime
import cv2


# Workflow configuration
INITIAL_BATCH_SIZE = 5  # First batch of wells to create (5)
SUBSEQUENT_BATCH_SIZE = 3  # Size of subsequent batches (3)
MAX_WELLS = 24  # Maximum number of wells on plate (24)
TARGET_WELL = 0  # Well containing the target sample
RANDOM_SEED = 42

VIRTUAL = True

# Choose color space for matching: 'RGB', 'RGBA', 'HSV', or 'LAB'
COLOR_SPACE = 'HSV'
COLOR_SPACE = COLOR_SPACE.upper() #just to make sure it's in uppercase

# Reservoir mapping
RESERVOIRS = {
    'R': 0,      # Red colorant
    'B': 1,      # Yellow colorant  
    'Y': 2,      # Blue colorant
    'Water': 3,  # Water/diluent
    'wash': 4,   # Wash solution
    'waste': 5   # Waste container
}

# Get workflow name (file name without extension)
workflow_name = os.path.splitext(os.path.basename(__file__))[0]
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = os.path.join("output", workflow_name, timestamp)

# check if skimage is available for color conversions
try:
    from skimage import color as skcolor
    SKIMAGE_AVAILABLE = True
except Exception:
    SKIMAGE_AVAILABLE = False

def rgb_distance(rgb1, rgb2):
    """Calculate Euclidean distance between two RGB colors."""
    return np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(rgb1, rgb2)))

def rgb_to_hsv(rgb):
    """Convert an (R,G,B) tuple (0-255) to (H,S,V) where H is degrees [0-360), S and V in [0,1]."""
    if rgb is None:
        return None
    r, g, b = [int(x) for x in rgb[:3]]
    arr = np.uint8([[[r, g, b]]])
    hsv_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)[0, 0]
    h = float(hsv_cv[0]) * 2.0
    s = float(hsv_cv[1]) / 255.0
    v = float(hsv_cv[2]) / 255.0
    return (h, s, v)

def rgb_to_lab(rgb):
    """Convert (R,G,B) tuple (0-255) to Lab (L in 0-100, a/b roughly -128..127).

    Uses skimage if available for standard ranges, otherwise OpenCV with scaling.
    """
    if rgb is None:
        return None
    r, g, b = [int(x) for x in rgb[:3]]
    arr = np.uint8([[[r, g, b]]])
    if SKIMAGE_AVAILABLE:
        # skimage expects floats in [0,1]
        arr_f = arr.astype('float32') / 255.0
        lab = skcolor.rgb2lab(arr_f)[0, 0]
        return tuple(float(x) for x in lab)
    else:
        lab_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)[0, 0].astype(float)
        L = lab_cv[0] * (100.0 / 255.0)
        a = lab_cv[1] - 128.0
        b = lab_cv[2] - 128.0
        return (L, a, b)

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

# def _possible_crop_filenames(image_suffix):
#     """Return a list of possible crop filenames produced by Camera.average_color_in_center.

#     Camera names crops either `center_crop{n}.jpg` when the original filename
#     matched `well_plate(\d+)`, otherwise it uses `center_crop_{base_name}.jpg`.
#     We construct a set of likely candidates and let the caller pick whichever exists.
#     """
#     # Direct numeric style (if image_suffix is numeric or contains digits)
#     candidates = []
#     # e.g., center_crop0.jpg or center_crop12.jpg
#     candidates.append(f"center_crop{image_suffix}.jpg")
#     # fallback base_name style: original base was 'well_plate{image_suffix}'
#     candidates.append(f"center_crop_well_plate{image_suffix}.jpg")
#     # generic fallback (underscore)
#     candidates.append(f"center_crop_{image_suffix}.jpg")
#     # another fallback if someone passed 'well_plate12' as suffix
#     candidates.append(f"center_crop_{'well_plate' + str(image_suffix)}.jpg")
#     return candidates

# def find_crop_path(dispenser, image_suffix):
#     """Find the actual saved crop path for a given image_suffix using camera output_dir.

#     Returns full path or None if not found.
#     """
#     crop_dir = os.path.join(dispenser.camera.output_dir, "center_crops")
#     for fname in _possible_crop_filenames(image_suffix):
#         p = os.path.join(crop_dir, fname)
#         if os.path.exists(p):
#             return p
#     # Try listing folder and match by contains image_suffix
#     if os.path.isdir(crop_dir):
#         for f in os.listdir(crop_dir):
#             if str(image_suffix) in f:
#                 return os.path.join(crop_dir, f)
#     return None

# def mean_lab_from_crop(crop_path):
#     """Load a crop image and return mean Lab in conventional ranges (L:0-100, a,b approx -128..127).

#     Uses scikit-image if available (recommended) otherwise OpenCV with scaling.
#     """
#     if crop_path is None or not os.path.exists(crop_path):
#         return None
#     try:
#         import numpy as _np
#         from PIL import Image as _Image
#         img = _Image.open(crop_path).convert('RGB')
#         arr = _np.array(img)
#         if SKIMAGE_AVAILABLE:
#             # skimage expects floats in [0,1]
#             arr_f = arr.astype('float32') / 255.0
#             lab = skcolor.rgb2lab(arr_f)
#             mean_lab = _np.mean(lab.reshape(-1, 3), axis=0)
#             return tuple(mean_lab.tolist())
#         else:
#             # OpenCV path: convert RGB->BGR then to LAB, scale to conventional Lab
#             import cv2 as _cv2
#             bgr = _cv2.cvtColor(arr, _cv2.COLOR_RGB2BGR)
#             lab_cv = _cv2.cvtColor(bgr, _cv2.COLOR_BGR2LAB).astype(float)
#             mean_lab_cv = _np.mean(lab_cv.reshape(-1, 3), axis=0)
#             # Convert OpenCV LAB (L 0-255) to conventional L 0-100, a/b offset by 128
#             L = mean_lab_cv[0] * (100.0 / 255.0)
#             a = mean_lab_cv[1] - 128.0
#             b = mean_lab_cv[2] - 128.0
#             return (L, a, b)
#     except Exception:
#         return None

# def mean_hsv_from_crop(crop_path):
#     """Load a crop image and return mean HSV (H degrees [0-360), S [0-1], V [0-1])."""
#     if crop_path is None or not os.path.exists(crop_path):
#         return None
#     try:
#         import numpy as _np
#         from PIL import Image as _Image
#         img = _Image.open(crop_path).convert('RGB')
#         arr = _np.array(img)
#         # Convert RGB array [H,W,3] uint8 to HSV via OpenCV
#         import cv2 as _cv2
#         rgb = arr.astype('uint8')
#         hsv_cv = _cv2.cvtColor(rgb, _cv2.COLOR_RGB2HSV).astype(float)
#         # HSV: H [0,179] -> degrees, S,V [0,255] -> normalize
#         h = hsv_cv[:, :, 0] * 2.0
#         s = hsv_cv[:, :, 1] / 255.0
#         v = hsv_cv[:, :, 2] / 255.0
#         mean_h = float(_np.mean(h))
#         mean_s = float(_np.mean(s))
#         mean_v = float(_np.mean(v))
#         return (mean_h, mean_s, mean_v)
#     except Exception:
#         return None


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

            # dispenser.condition_needle(
            #     source_location="reservoir_12", 
            #     source_index=reservoir_index,
            #     dest_location="reservoir_12",
            #     dest_index=RESERVOIRS["waste"],
            #     num_conditions = 1)

            if component == last_component:
                dispense_mix_volume=0.3
            else:
                dispense_mix_volume=0

            dispenser.dispense_between(
                source_location="reservoir_12",
                source_index=reservoir_index,
                dest_location="well_plate", 
                dest_index=well_index,
                transfer_vol=volume_ml,  # Now in mL as expected
                mixing_vol=dispense_mix_volume,
            )

            dispenser.rinse_needle(
                wash_location="reservoir_12", 
                wash_index=RESERVOIRS['wash'], 
                num_mixes=3
            )
            
            # Small delay between dispenses
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
    
    # Initialize logging
    logger = start_workflow_logging("color_matching_workflow")
    logger.info("=" * 60)
    logger.info("Starting Color Matching Bayesian Optimization Workflow")
    logger.info("=" * 60)
    
    # Initialize hardware (virtual mode for testing)
    logger.info("Initializing hardware...")
    dispenser = Liquid_Dispenser(
        cnc_comport="COM4", 
        actuator_comport="COM6",
        virtual=VIRTUAL,  # Set to False for real hardware
        camera_index=1, 
        log_level=logging.DEBUG,
        output_dir=output_dir
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
        target_color = dispenser.get_image_color("well_plate_camera", TARGET_WELL, "target_sample", square_size=60, color_space=COLOR_SPACE)


        logger.info(f"Target {COLOR_SPACE} values: {get_color_str(target_color)}") #log the target color values

        # Calculate upper bound for optimization (max possible distance) - keep RGB max for optimizer scaling
        max_distance = rgb_distance([0, 0, 0], [255, 255, 255])  # Max possible RGB distance

        # Initialize Bayesian optimization campaign
        logger.info("Initializing Bayesian optimization campaign...")
        campaign, searchspace = initialize_campaign(
            upper_bound=50,
            random_seed=RANDOM_SEED,
            random_recs=False
        )
        logger.info("Bayesian optimization campaign initialized successfully")
        
        # Step 2: Generate and create initial batch
        logger.info(f"Step 2: Generating initial batch of {INITIAL_BATCH_SIZE} recommendations")
        campaign, initial_suggestions = get_initial_recommendations(campaign, INITIAL_BATCH_SIZE)
        logger.debug(f"Initial suggestions generated:\n{initial_suggestions}")
        
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
                'Water': suggestion['Water']
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
                'Water_volume_ml': round(volumes_ml['Water'], 2),
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
                    'Water': suggestion['Water']
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
                    'Water_volume_ml': round(volumes_ml['Water'], 2),
                    # 'R': suggestion['R'],
                    # 'Y': suggestion['Y'],
                    # 'B': suggestion['B'],
                    # 'Water': suggestion['Water']
                }
                batch_results.append(batch_result)
                current_well += 1
            
            # Analyze new wells
            logger.info(f"Analyzing RGB values for batch {batch_number}...")
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
        logger.info(f"Recipe: R={best_result['R_volume_ml']:.3f}mL, Y={best_result['Y_volume_ml']:.3f}mL, B={best_result['B_volume_ml']:.3f}mL, Water={best_result['Water_volume_ml']:.3f}mL")
        
        if dispenser.virtual: #TODO: save back to not virtual!
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

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Ensure the output directory exists
            os.makedirs(output_dir, exist_ok=True)
            results_file = os.path.join(output_dir, f"color_matching_results_{timestamp}.csv")
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