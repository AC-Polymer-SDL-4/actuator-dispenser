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

from datetime import datetime

# Workflow configuration
INITIAL_BATCH_SIZE = 5  # First batch of wells to create
SUBSEQUENT_BATCH_SIZE = 3  # Size of subsequent batches
MAX_WELLS = 24  # Maximum number of wells on plate
TARGET_WELL = 0  # Well containing the target sample
RANDOM_SEED = 42

# Reservoir mapping
RESERVOIRS = {
    'R': 0,      # Red colorant
    'Y': 1,      # Yellow colorant  
    'B': 2,      # Blue colorant
    'Water': 3,  # Water/diluent
    'wash': 4,   # Wash solution
    'waste': 5   # Waste container
}

def rgb_distance(rgb1, rgb2):
    """Calculate Euclidean distance between two RGB colors."""
    return np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(rgb1, rgb2)))

def volumes_to_milliliters(volumes_dict, total_volume_ml=0.240):
    """
    Convert optimizer volume units to milliliters.
    
    Args:
        volumes_dict: Dictionary with volume ratios from optimizer
        total_volume_ml: Total volume to dispense in milliliters (default 240μL = 0.240mL)
        
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
    
    # Dispense each component
    for component, volume_ml in volumes_ml.items():
        if volume_ml > 0 and component in RESERVOIRS:
            reservoir_index = RESERVOIRS[component]
            logger.info(f"Dispensing {volume_ml:.3f}mL of {component} from reservoir {reservoir_index}")
            
            dispenser.dispense_between(
                source_location="reservoir",
                source_index=reservoir_index,
                dest_location="well_plate", 
                dest_index=well_index,
                vol_pipet=volume_ml  # Now in mL as expected
            )
            
            # Small delay between dispenses
            time.sleep(0.5)

def condition_system(dispenser, logger):
    """
    Condition the dispensing system by moving between wash and waste.
    """
    logger.info("Conditioning system between wash and waste")
    
    dispenser.dispense_condition(
        source_location="reservoir",
        source_index=RESERVOIRS['wash'],
        dest_location="reservoir",
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
        cnc_comport="COM3", 
        actuator_comport="COM7",
        virtual=True  # Set to False for real hardware
    )
    dispenser.cnc_machine.Z_LOW_BOUND = -70  # Adjust as needed
    dispenser.cnc_machine.home() #Home machine
    
    if not dispenser.virtual:
        import slack_agent
        slack_agent.send_message("Color Matching Workflow started on real hardware.")

    try:
        # Step 1: Read target RGB from well 0
        logger.info("Step 1: Reading target RGB values from sample at well 0")
        target_rgb = dispenser.get_image_rgb("well_plate", TARGET_WELL, "target_sample")
        logger.info(f"Target RGB values: R={target_rgb[0]}, G={target_rgb[1]}, B={target_rgb[2]}")
        
        # Calculate upper bound for optimization (max possible distance)
        max_distance = rgb_distance([0, 0, 0], [255, 255, 255])  # Max possible RGB distance
        
        # Initialize Bayesian optimization campaign
        logger.info("Initializing Bayesian optimization campaign...")
        campaign, searchspace = initialize_campaign(
            upper_bound=max_distance,
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
            
            # Condition system after each mixture
            condition_system(dispenser, logger)
            
            # Store experiment details
            results_data.append({
                'well': current_well,
                'R_volume_ml': volumes_ml['R'],
                'Y_volume_ml': volumes_ml['Y'],
                'B_volume_ml': volumes_ml['B'], 
                'Water_volume_ml': volumes_ml['Water'],
                'R': suggestion['R'],  # Original optimizer values
                'Y': suggestion['Y'],
                'B': suggestion['B'],
                'Water': suggestion['Water']
            })
            
            current_well += 1
        
        # Step 3: Analyze RGB of initial wells
        logger.info("Step 3: Analyzing RGB values of initial wells...")
        time.sleep(2)  # Allow time for mixing
        
        results_list = []
        for i, result in enumerate(results_data):
            well_idx = result['well']
            logger.debug(f"Analyzing RGB for well {well_idx}")
            
            well_rgb = dispenser.get_image_rgb("well_plate", well_idx, f"experiment_{well_idx}")
            result['measured_R'] = well_rgb[0]
            result['measured_G'] = well_rgb[1] 
            result['measured_B'] = well_rgb[2]
            
            # Calculate distance to target (this is what we want to minimize)
            distance = rgb_distance(target_rgb, well_rgb)
            results_list.append(distance)  # Store for adding to suggestions DataFrame
            result['output'] = distance  # Store in our tracking data
            
            logger.info(f"Well {well_idx}: RGB=({well_rgb[0]:.0f}, {well_rgb[1]:.0f}, {well_rgb[2]:.0f}), Distance={distance:.1f}")
        
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
                condition_system(dispenser, logger)
                
                # Store results
                batch_result = {
                    'well': current_well,
                    'R_volume_ml': volumes_ml['R'],
                    'Y_volume_ml': volumes_ml['Y'],
                    'B_volume_ml': volumes_ml['B'],
                    'Water_volume_ml': volumes_ml['Water'], 
                    'R': suggestion['R'],
                    'Y': suggestion['Y'],
                    'B': suggestion['B'],
                    'Water': suggestion['Water']
                }
                batch_results.append(batch_result)
                current_well += 1
            
            # Analyze new wells
            logger.info(f"Analyzing RGB values for batch {batch_number}...")
            time.sleep(2)
            
            for i, result in enumerate(batch_results):
                well_idx = result['well'] 
                well_rgb = dispenser.get_image_rgb("well_plate", well_idx, f"experiment_{well_idx}")
                
                result['measured_R'] = well_rgb[0]
                result['measured_G'] = well_rgb[1]
                result['measured_B'] = well_rgb[2]
                
                distance = rgb_distance(target_rgb, well_rgb)
                result['output'] = distance
                results_list.append(distance)
                
                logger.info(f"Well {well_idx}: RGB=({well_rgb[0]:.0f}, {well_rgb[1]:.0f}, {well_rgb[2]:.0f}), Distance={distance:.1f}")
            
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
        logger.info(f"RGB: ({best_result['measured_R']}, {best_result['measured_G']}, {best_result['measured_B']})")
        logger.info(f"Recipe: R={best_result['R_volume_ml']:.3f}mL, Y={best_result['Y_volume_ml']:.3f}mL, B={best_result['B_volume_ml']:.3f}mL, Water={best_result['Water_volume_ml']:.3f}mL")
        
        # Save results to CSV
        results_df = pd.DataFrame(results_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"color_matching_results_{timestamp}.csv"
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
        dispenser.move_to_origin()

    if not dispenser.virtual:
        slack_agent.send_message("Color Matching Workflow finished on real hardware.")

if __name__ == "__main__":
    main()