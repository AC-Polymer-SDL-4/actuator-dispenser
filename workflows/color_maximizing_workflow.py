"""
Color Difference Maximization Bayesian Optimization Workflow

This workflow uses Bayesian optimization to find optimal chemical mixtures
that produce the MAXIMUM color difference from a reference solution.

Hardware setup:
- Reservoir positions:
  0: CuSO4 or FeCl3 (metal salt - user choice)
  1: HCl
  2: Citric acid
  3: Ascorbic acid
  4: PVA-1
  5: PVA-2
  6: PVA-3
  7: NaOH
  8: Water
  9: Wash solution
  10: Waste container
- Well plate positions 0-23 for experiments
- Reference sample: 200μL metal salt + 800μL water at well_plate position 0

Workflow:
1. Create reference solution (200μL metal salt + 800μL water) at well 0
2. Read RGB values from reference at well_plate position 0
3. Generate initial batch of experiments using Bayesian optimization
4. Create mixtures: 200μL metal salt + optimized component amounts (total 1000μL)
5. Condition system between wash and waste
6. Analyze RGB of created wells
7. Feed results back to optimizer (maximizing color difference)
8. Repeat until well plate is full
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_workflow import Liquid_Dispenser, start_workflow_logging
from color_maximizing_optimizer import initialize_campaign, get_initial_recommendations, get_new_recs_from_results
import pandas as pd
import numpy as np
import time
import logging
import os
import datetime
import cv2

# Workflow configuration
INITIAL_BATCH_SIZE = 5  # First batch of wells to create
SUBSEQUENT_BATCH_SIZE = 3  # Size of subsequent batches
MAX_WELLS = 8  # Maximum number of wells on plate
REFERENCE_WELL = 0  # Well containing the reference sample
RANDOM_SEED = 42

VIRTUAL = True
WITHOUT_WATER = False  # Can be toggled to exclude water from variable components

# Choose color space for analysis: 'RGB', 'RGBA', 'HSV', or 'LAB'
COLOR_SPACE = 'RGB'

# Fixed volumes
METAL_SALT_VOLUME_UL = 200  # Fixed amount of CuSO4 or FeCl3
TOTAL_WELL_VOLUME_UL = 1000  # Total volume per well
VARIABLE_VOLUME_UL = TOTAL_WELL_VOLUME_UL - METAL_SALT_VOLUME_UL  # 800μL for other components

# Reservoir mapping (using reservoir_12 location)
RESERVOIRS = {
    'metal_salt': 0,     # CuSO4 or FeCl3 (user specifies which)
    'HCl': 1,
    'citric_acid': 2,
    'ascorbic_acid': 3,
    'PVA_1': 4,
    'PVA_2': 5,
    'PVA_3': 6,
    'NaOH': 7,
    'Water': 8,
    'wash': 9,
    'waste': 10
}

# Location name to use for reservoirs
RESERVOIR_LOCATION = "reservoir_12"

def rgb_distance(rgb1, rgb2):
    """Calculate Euclidean distance between two RGB colors."""
    return np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(rgb1, rgb2)))

def hue_distance_deg(h1, h2):
    """Calculate hue distance in degrees (0-180), accounting for circular nature."""
    diff = abs(h1 - h2)
    return min(diff, 360 - diff)

def hsv_distance(hsv1, hsv2, weights=(0.6, 0.2, 0.2)):
    """Calculate weighted distance between HSV colors.
    
    Args:
        weights: (hue_weight, saturation_weight, value_weight)
                Default emphasizes hue over saturation and value
    """
    h_dist = hue_distance_deg(hsv1[0], hsv2[0]) / 180.0  # Normalize to 0-1
    s_dist = abs(hsv1[1] - hsv2[1]) / 255.0
    v_dist = abs(hsv1[2] - hsv2[2]) / 255.0
    
    return np.sqrt(weights[0] * h_dist**2 + weights[1] * s_dist**2 + weights[2] * v_dist**2)

def lab_distance(lab1, lab2):
    """Calculate Delta E CIE76 distance between LAB colors."""
    return np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(lab1, lab2)))

def get_color_distance(target_col, sample_col, color_space=COLOR_SPACE):
    """Calculate color distance based on the specified color space."""
    if color_space == 'RGB':
        return rgb_distance([target_col['R'], target_col['G'], target_col['B']], 
                          [sample_col['R'], sample_col['G'], sample_col['B']])
    elif color_space == 'HSV':
        return hsv_distance([target_col['H'], target_col['S'], target_col['V']], 
                          [sample_col['H'], sample_col['S'], sample_col['V']])
    elif color_space == 'LAB':
        return lab_distance([target_col['L'], target_col['A'], target_col['B']], 
                          [sample_col['L'], sample_col['A'], sample_col['B']])
    else:
        raise ValueError(f"Unsupported color space: {color_space}")

def get_color_str(color_dict):
    """Output a string representation of color dict (universal for all color spaces)."""
    return ', '.join([f"{k}={v:.1f}" for k, v in color_dict.items()])

def volumes_to_milliliters(volumes_dict, total_variable_volume_ml=0.800):
    """
    Convert optimizer volume units to milliliters for variable components.
    
    Args:
        volumes_dict: Dictionary with volume ratios from optimizer
        total_variable_volume_ml: Total variable volume in milliliters (800μL = 0.800mL)
        
    Returns:
        Dictionary with volumes in milliliters
    """
    # Normalize volumes to ensure they sum to total_variable_volume_ml
    total_parts = sum(volumes_dict.values())
    if total_parts == 0:
        return {k: 0 for k in volumes_dict}
    
    factor = total_variable_volume_ml / total_parts
    return {k: v * factor for k, v in volumes_dict.items()}

def create_reference_solution(dispenser, metal_salt_name, logger):
    """
    Create the reference solution at well 0: 200μL metal salt + 800μL water.
    
    Args:
        dispenser: Liquid_Dispenser instance
        metal_salt_name: Name of metal salt being used ("CuSO4" or "FeCl3")
        logger: Logger instance
    """
    logger.info(f"Creating reference solution at well 0: 200μL {metal_salt_name} + 800μL water")
    
    # Add metal salt
    dispenser.dispense_between(
        source_location=RESERVOIR_LOCATION,
        source_index=RESERVOIRS['metal_salt'],
        dest_location="well_plate",
        dest_index=REFERENCE_WELL,
        transfer_vol=0.200  # 200μL in mL
    )
    
    # Add water
    dispenser.dispense_between(
        source_location=RESERVOIR_LOCATION, 
        source_index=RESERVOIRS['Water'],
        dest_location="well_plate",
        dest_index=REFERENCE_WELL,
        transfer_vol=0.800  # 800μL in mL
    )
    
    logger.info("Reference solution created successfully")

def create_experimental_well(dispenser, well_index, volumes_ml, metal_salt_name, logger):
    """
    Create an experimental mixture: 200μL metal salt + optimized component volumes.
    
    Args:
        dispenser: Liquid_Dispenser instance
        well_index: Target well index
        volumes_ml: Dictionary of variable component volumes in milliliters
        metal_salt_name: Name of metal salt being used
        logger: Logger instance
    """
    logger.info(f"Creating experimental well {well_index} with {metal_salt_name}")
    logger.debug(f"Variable component volumes: {volumes_ml}")
    
    # First add the fixed metal salt amount
    dispenser.dispense_between(
        source_location=RESERVOIR_LOCATION,
        source_index=RESERVOIRS['metal_salt'],
        dest_location="well_plate",
        dest_index=well_index,
        transfer_vol=0.200  # 200μL metal salt
    )
    
    # Add variable components
    for component, volume_ml in volumes_ml.items():
        if volume_ml > 0 and component in RESERVOIRS:
            reservoir_index = RESERVOIRS[component]
            logger.debug(f"Adding {volume_ml:.3f}mL of {component}")
            
            dispenser.dispense_between(
                source_location=RESERVOIR_LOCATION,
                source_index=reservoir_index,
                dest_location="well_plate",
                dest_index=well_index,
                transfer_vol=volume_ml
            )
            
            time.sleep(0.3)  # Small delay between components

def condition_system(dispenser, logger):
    """
    Condition the dispensing system by moving between wash and waste.
    """
    logger.debug("Conditioning system between wash and waste")
    
    dispenser.dispense_condition(
        source_location=RESERVOIR_LOCATION,
        source_index=RESERVOIRS['wash'],
        dest_location=RESERVOIR_LOCATION,
        dest_index=RESERVOIRS['waste']
    )

def main():
    """Main color difference maximization workflow."""
    
    # Get user input for metal salt choice
    print("\nColor Difference Maximization Workflow")
    print("=" * 50)
    print("Choose metal salt:")
    print("1. CuSO4 (Copper Sulfate)")
    print("2. FeCl3 (Iron Chloride)")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == "1":
            metal_salt_name = "CuSO4"
            break
        elif choice == "2":
            metal_salt_name = "FeCl3"
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")
    
    # Initialize logging
    workflow_name = f"color_maximizing_{metal_salt_name.lower()}"
    logger = start_workflow_logging(workflow_name)
    
    # Create output directory for this workflow
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"output/{workflow_name}_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    logger.info("=" * 60)
    logger.info(f"Starting Color Difference Maximization Workflow with {metal_salt_name}")
    logger.info("=" * 60)
    
    # Initialize hardware
    logger.info("Initializing hardware...")
    dispenser = Liquid_Dispenser(
        cnc_comport="COM3",
        actuator_comport="COM7", 
        virtual=VIRTUAL
    )
    dispenser.cnc_machine.Z_LOW_BOUND = -70  # Adjust as needed
    dispenser.cnc_machine.home()  # Home machine

    if not dispenser.virtual:
        import slack_agent
        secrets = slack_agent.load_secrets()

        SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
        SLACK_WEBHOOK_URL = secrets["SLACK_WEBHOOK_URL"]
        SLACK_CHANNEL = "C09J10VQ02C"
        slack_agent.send_slack_message(f"Color Maximization Workflow started on real hardware with {metal_salt_name}.", SLACK_CHANNEL)
    
    try:
        # Step 1: Create reference solution
        logger.info("Step 1: Creating reference solution")
        create_reference_solution(dispenser, metal_salt_name, logger)
        time.sleep(2)  # Allow mixing
        
        # Step 2: Read reference color values
        logger.info("Step 2: Reading reference color values")
        reference_color = dispenser.get_image_color("well_plate_camera", REFERENCE_WELL, f"reference_{metal_salt_name}", square_size=60, color_space=COLOR_SPACE, show_crop=True)
        logger.info(f"Reference {COLOR_SPACE} values: {get_color_str(reference_color)}")
        
        # Calculate upper bound for optimization (max possible distance)
        max_distance = rgb_distance([0, 0, 0], [255, 255, 255])
        
        # Initialize Bayesian optimization campaign
        logger.info("Initializing Bayesian optimization campaign for MAXIMUM color difference...")
        campaign, searchspace = initialize_campaign(
            upper_bound=max_distance,
            random_seed=RANDOM_SEED,
            random_recs=False
        )
        logger.info("Campaign initialized - targeting MAXIMUM color difference from reference")
        
        # Step 3: Generate and create initial batch
        logger.info(f"Step 3: Generating initial batch of {INITIAL_BATCH_SIZE} recommendations")
        campaign, initial_suggestions = get_initial_recommendations(campaign, INITIAL_BATCH_SIZE)
        logger.debug(f"Initial suggestions:\n{initial_suggestions}")
        
        # Create initial mixtures
        results_data = []
        current_well = 1  # Start at well 1 (well 0 is reference)
        
        logger.info("Creating initial experimental batch...")
        for idx, (_, suggestion) in enumerate(initial_suggestions.iterrows()):
            if current_well >= MAX_WELLS:
                logger.warning("Reached maximum number of wells, stopping...")
                break
            
            # Convert optimizer units to milliliters for variable components
            volumes_dict = {
                'HCl': suggestion['HCl'],
                'citric_acid': suggestion['citric_acid'],
                'ascorbic_acid': suggestion['ascorbic_acid'],
                'PVA_1': suggestion['PVA_1'],
                'PVA_2': suggestion['PVA_2'], 
                'PVA_3': suggestion['PVA_3'],
                'NaOH': suggestion['NaOH'],
                'Water': suggestion['Water'] if not WITHOUT_WATER else 0
            }
            volumes_ml = volumes_to_milliliters(volumes_dict)
            
            # Create experimental well
            create_experimental_well(dispenser, current_well, volumes_ml, metal_salt_name, logger)
            condition_system(dispenser, logger)
            
            # Store experiment details
            results_data.append({
                'well': current_well,
                'metal_salt': metal_salt_name,
                'metal_salt_volume_ml': 0.200,
                **{f"{k}_volume_ml": v for k, v in volumes_ml.items()},
                **{k: suggestion[k] for k in volumes_dict.keys()}  # Original optimizer values
            })
            
            current_well += 1
        
        # Step 4: Analyze RGB of initial wells
        logger.info("Step 4: Analyzing RGB values of initial wells...")
        time.sleep(3)  # Allow time for color development
        
        results_list = []
        for i, result in enumerate(results_data):
            well_idx = result['well']
            logger.debug(f"Analyzing RGB for experimental well {well_idx}")
            
            well_color = dispenser.get_image_color("well_plate_camera", well_idx, f"experiment_{well_idx}", square_size=60, color_space=COLOR_SPACE)
            
            # Store measured color values
            for channel, value in well_color.items():
                result[f'measured_{channel}'] = value
            
            # Calculate distance from reference (we want to MAXIMIZE this)
            distance = get_color_distance(reference_color, well_color, COLOR_SPACE)
            results_list.append(distance)
            result['output'] = distance  # This is the objective value for the optimizer
            
            logger.info(f"Well {well_idx}: {COLOR_SPACE}={get_color_str(well_color)}, Distance from ref={distance:.1f}")
        
        # Add results to suggestions dataframe
        initial_suggestions['output'] = results_list
        campaign_data = initial_suggestions.copy()
        
        # Step 5: Iterative optimization loop
        batch_number = 1
        
        while current_well < MAX_WELLS:
            logger.info(f"Step 5.{batch_number}: Starting optimization iteration {batch_number}")
            
            # Get new recommendations
            remaining_wells = min(SUBSEQUENT_BATCH_SIZE, MAX_WELLS - current_well)
            logger.info(f"Getting {remaining_wells} new recommendations to MAXIMIZE color difference...")
            
            campaign, new_suggestions = get_new_recs_from_results(
                campaign, campaign_data, remaining_wells
            )
            
            logger.debug(f"Generated {len(new_suggestions)} new suggestions")
            
            # Create new mixtures
            batch_results = []
            results_list = []
            
            for idx, (_, suggestion) in enumerate(new_suggestions.iterrows()):
                if current_well >= MAX_WELLS:
                    break
                
                # Convert to milliliters
                volumes_dict = {
                    'HCl': suggestion['HCl'],
                    'citric_acid': suggestion['citric_acid'],
                    'ascorbic_acid': suggestion['ascorbic_acid'],
                    'PVA_1': suggestion['PVA_1'],
                    'PVA_2': suggestion['PVA_2'],
                    'PVA_3': suggestion['PVA_3'],
                    'NaOH': suggestion['NaOH'],
                    'Water': suggestion['Water'] if not WITHOUT_WATER else 0
                }
                volumes_ml = volumes_to_milliliters(volumes_dict)
                
                # Create experimental well
                create_experimental_well(dispenser, current_well, volumes_ml, metal_salt_name, logger)
                condition_system(dispenser, logger)
                
                # Store results
                batch_result = {
                    'well': current_well,
                    'metal_salt': metal_salt_name,
                    'metal_salt_volume_ml': 0.200,
                    **{f"{k}_volume_ml": v for k, v in volumes_ml.items()},
                    **{k: suggestion[k] for k in volumes_dict.keys()}
                }
                batch_results.append(batch_result)
                current_well += 1
            
            # Analyze new wells
            logger.info(f"Analyzing RGB values for batch {batch_number}...")
            time.sleep(3)
            
            for i, result in enumerate(batch_results):
                well_idx = result['well']
                well_color = dispenser.get_image_color("well_plate_camera", well_idx, f"experiment_{well_idx}", square_size=60, color_space=COLOR_SPACE)
                
                # Store measured color values
                for channel, value in well_color.items():
                    result[f'measured_{channel}'] = value
                
                distance = get_color_distance(reference_color, well_color, COLOR_SPACE)
                result['output'] = distance
                results_list.append(distance)
                
                logger.info(f"Well {well_idx}: {COLOR_SPACE}={get_color_str(well_color)}, Distance from ref={distance:.1f}")
            
            # Add results and combine with campaign data
            new_suggestions['output'] = results_list
            campaign_data = pd.concat([campaign_data, new_suggestions], ignore_index=True)
            
            # Add to overall tracking
            results_data.extend(batch_results)
            batch_number += 1
        
        # Final analysis
        logger.info("=" * 60)
        logger.info("WORKFLOW COMPLETE - FINAL ANALYSIS")
        logger.info("=" * 60)
        
        # Find BEST result (maximum distance)
        best_result = max(results_data, key=lambda x: x['output'])
        logger.info(f"MAXIMUM color difference found at well {best_result['well']}")
        logger.info(f"Distance from reference: {best_result['output']:.1f}")
        logger.info(f"{COLOR_SPACE}: {get_color_str({k.replace('measured_',''):v for k,v in best_result.items() if k.startswith('measured_')})}")
        logger.info(f"Reference {COLOR_SPACE}: {get_color_str(reference_color)}")
        
        # Log optimal recipe
        logger.info("OPTIMAL RECIPE:")
        logger.info(f"  {metal_salt_name}: 200μL (fixed)")
        for component in ['HCl', 'citric_acid', 'ascorbic_acid', 'PVA_1', 'PVA_2', 'PVA_3', 'NaOH', 'Water']:
            volume_ml = best_result[f"{component}_volume_ml"]
            logger.info(f"  {component}: {volume_ml*1000:.0f}μL")
        
        # Save results with reference color appended
        results_df = pd.DataFrame(results_data)
        
        # Append the reference color as an extra row for record-keeping
        try:
            reference_row = {}
            for col in results_df.columns:
                if col == 'well':
                    reference_row[col] = "Reference"
                elif col.startswith("measured_"):
                    channel = col.replace("measured_", "")
                    reference_row[col] = reference_color.get(channel, np.nan)
                else:
                    reference_row[col] = np.nan
            
            results_df = pd.concat([results_df, pd.DataFrame([reference_row])], ignore_index=True)
        except Exception:
            logger.exception("Failed to append reference color row; saving without it.")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        results_file = os.path.join(output_dir, f"color_maximizing_{metal_salt_name.lower()}_results.csv")
        results_df.to_csv(results_file, index=False)
        logger.info(f"Results saved to {results_file}")
        
        # Summary statistics
        distances = [r['output'] for r in results_data]
        logger.info(f"Summary statistics:")
        logger.info(f"  Max distance (best): {max(distances):.1f}")
        logger.info(f"  Min distance: {min(distances):.1f}")
        logger.info(f"  Mean distance: {np.mean(distances):.1f}")
        logger.info(f"  Std distance: {np.std(distances):.1f}")
        
    except Exception as e:
        logger.error(f"Workflow failed with error: {str(e)}")
        logger.error(f"Error details: {repr(e)}")
        raise
        
    finally:
        logger.info("Workflow completed. Moving to origin position.")
        dispenser.cnc_machine.move_to_point(z=0)
        dispenser.move_to_origin()

    if not dispenser.virtual:
        slack_agent.send_slack_message(f"Color Maximization Workflow finished on real hardware with {metal_salt_name}.", SLACK_CHANNEL)

if __name__ == "__main__":
    main()