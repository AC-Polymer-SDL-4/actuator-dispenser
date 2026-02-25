"""
Multi-Well Percentage-Based Dispenser Workflow

This workflow takes in multiple percentage sets (water, red, blue, yellow)
and systematically dispenses each color into separate vials with conditioning
between each color to prevent cross-contamination.

Key features:
- Takes N percentage sets as input (e.g., 4 different color recipes)
- Dispenses one color at a time into each vial
- Conditions the needle between each color to prevent contamination
- Total volume per vial = 2 mL
- Uses reservoirs as liquid source

Hardware setup:
- Reservoir positions:
  0: Water
  1: Red colorant
  2: Blue colorant
  3: Yellow colorant
  4: Wash solution
  5: Waste container
- Vial rack: 6 or 12 positions for final mixtures

Dispensing strategy (per vial):
1. Dispense water (calculated from percentage)
2. Condition needle (wash & waste)
3. Dispense red (calculated from percentage)
4. Condition needle (wash & waste)
5. Dispense blue (calculated from percentage)
6. Condition needle (wash & waste)
7. Dispense yellow (calculated from percentage)
8. Condition needle (wash & waste)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_workflow import Liquid_Dispenser, start_workflow_logging
import time



# ============================================================================
# CONFIGURATION - Edit these values to define your dispensing recipe
# ============================================================================

# Percentage sets to dispense
# Format: List of dictionaries with percentage values for each color
# Each set must sum to 100%
PERCENTAGE_SETS = [
    {'water': 50, 'red': 25, 'blue': 15, 'yellow': 10},
    {'water': 40, 'red': 30, 'blue': 20, 'yellow': 10},
    {'water': 60, 'red': 20, 'blue': 10, 'yellow': 10},
    {'water': 45, 'red': 25, 'blue': 25, 'yellow': 5},
]

# Workflow configuration
TOTAL_VOLUME_ML = 2.0  # Total volume per vial in mL
VIRTUAL = True  # Set False to run on real hardware

# Reservoir mapping
RESERVOIRS = {
    'Water': 0,
    'Red': 1,
    'Blue': 2,
    'Yellow': 3,
    'wash': 4,
    'waste': 5
}

# Vial rack location
VIAL_RACK_LOCATION = "vial_rack"

# Color dispense order
COLOR_ORDER = ['Water', 'Red', 'Blue', 'Yellow']


def validate_percentages(percentage_sets):
    """
    Validate that percentage sets are properly formatted and sum to 100%.
    
    Args:
        percentage_sets: List of dictionaries with color percentages
        
    Returns:
        bool: True if valid, raises ValueError otherwise
    """
    required_keys = {'water', 'red', 'blue', 'yellow'}
    
    for i, pct_set in enumerate(percentage_sets):
        if not isinstance(pct_set, dict):
            raise ValueError(f"Set {i}: Expected dictionary, got {type(pct_set)}")
        
        set_keys = set(pct_set.keys())
        if set_keys != required_keys:
            raise ValueError(f"Set {i}: Expected keys {required_keys}, got {set_keys}")
        
        total = sum(pct_set.values())
        if not (99.9 <= total <= 100.1):  # Allow small rounding errors
            raise ValueError(f"Set {i}: Percentages sum to {total}%, must equal 100%")
        
        for color, pct in pct_set.items():
            if pct < 0 or pct > 100:
                raise ValueError(f"Set {i}, {color}: {pct}% is outside valid range [0, 100]")
    
    return True


def percentages_to_volumes(percentages, total_volume_ml=TOTAL_VOLUME_ML):
    """
    Convert percentage set to volumes in mL.
    
    Args:
        percentages: Dictionary with color percentages (lowercase keys)
        total_volume_ml: Total volume to dispense in mL
        
    Returns:
        Dictionary mapping color names to volumes in mL
    """
    # Map lowercase percentage keys to capitalized color names for consistency
    volumes = {}
    color_map = {'water': 'Water', 'red': 'Red', 'blue': 'Blue', 'yellow': 'Yellow'}
    
    for lowercase_color, percentage in percentages.items():
        capitalized_color = color_map[lowercase_color.lower()]
        volumes[capitalized_color] = (percentage / 100.0) * total_volume_ml
    
    return volumes


def condition_needle(dispenser, logger):
    """
    Condition the needle by dispensing between wash and waste.
    
    Args:
        dispenser: Liquid_Dispenser instance
        logger: Logger instance
    """
    logger.debug("Conditioning needle: wash -> waste")
    
    dispenser.dispense_between(
        source_location="reservoir_12",
        source_index=RESERVOIRS['wash'],
        dest_location="reservoir_12",
        dest_index=RESERVOIRS['waste'],
        transfer_vol=0.5  # 500 μL for conditioning
    )
    
    time.sleep(0.2)  # Brief pause after conditioning


def dispense_colors_to_vials(dispenser, percentage_sets, logger, vial_start_index=0):
    """
    Dispense all color combinations to vials with conditioning between each color.
    
    Strategy: For each color, dispense to ALL vials, then condition once.
    This minimizes needle conditioning operations.
    
    Dispense order:
    1. Water to vials 0-N, condition
    2. Red to vials 0-N, condition
    3. Blue to vials 0-N, condition
    4. Yellow to vials 0-N, condition
    
    Args:
        dispenser: Liquid_Dispenser instance
        percentage_sets: List of percentage dictionaries, one per vial
        logger: Logger instance
        vial_start_index: Starting index in vial rack (default 0)
    """
    num_vials = len(percentage_sets)
    logger.info(f"Preparing to fill {num_vials} vials with {len(COLOR_ORDER)} colors each")
    logger.info(f"Dispensing strategy: One color at a time across all vials")
    logger.info(f"Total dispense operations: {num_vials * len(COLOR_ORDER)} (plus {len(COLOR_ORDER)} conditioning steps)")
    
    # Dispense one color at a time to all vials
    for color in COLOR_ORDER:
        logger.info(f"\n{'='*70}")
        logger.info(f"Dispensing {color} to all vials")
        logger.info(f"{'='*70}")
        
        for vial_idx, percentages in enumerate(percentage_sets):
            vial_location_index = vial_start_index + vial_idx
            volumes = percentages_to_volumes(percentages)
            volume_ml = volumes.get(color, 0)
            
            if volume_ml > 0.025:  # Only dispense if volume is > 25 μL (minimum)
                logger.info(f"Vial {vial_idx} (position {vial_location_index}): Dispensing {volume_ml:.3f} mL of {color}")
                
                try:
                    dispenser.dispense_between(
                        source_location="reservoir_12",
                        source_index=RESERVOIRS[color],
                        dest_location="vial_rack",
                        dest_index=vial_location_index,
                        transfer_vol=volume_ml
                    )
                    logger.debug(f"  ✓ {color} dispensed successfully to vial {vial_idx}")
                except Exception as e:
                    logger.error(f"  ✗ Failed to dispense {color} to vial {vial_idx}: {e}")
                    raise
            else:
                logger.debug(f"Vial {vial_idx}: Skipping {color} (volume {volume_ml:.3f} mL < 25 μL minimum)")
            
            time.sleep(0.1)  # Brief pause between vials
        
        # Condition needle after all vials of this color are done
        logger.info(f"Conditioning needle after {color} dispense...")
        try:
            condition_needle(dispenser, logger)
            logger.debug(f"✓ Needle conditioned after {color}")
        except Exception as e:
            logger.error(f"✗ Failed to condition needle: {e}")
            raise
    
    logger.info(f"\n✓ Successfully filled all {num_vials} vials")


def print_dispensing_plan(percentage_sets):
    """
    Print a summary of the dispensing plan for user verification.
    
    Args:
        percentage_sets: List of percentage dictionaries
    """
    print("\n" + "="*70)
    print("DISPENSING PLAN SUMMARY")
    print("="*70)
    print(f"Total vials to fill: {len(percentage_sets)}")
    print(f"Total volume per vial: {TOTAL_VOLUME_ML * 1000:.0f} μL")
    print(f"\n{'Vial #':<8}{'Water %':<12}{'Red %':<12}{'Blue %':<12}{'Yellow %':<12}")
    print("-"*70)
    
    for i, percentages in enumerate(percentage_sets):
        print(f"{i:<8}{percentages['water']:<12.1f}{percentages['red']:<12.1f}{percentages['blue']:<12.1f}{percentages['yellow']:<12.1f}")
    
    print("="*70 + "\n")





def main():
    """Main workflow for multi-well percentage-based dispensing."""
    
    # Initialize logging
    workflow_name = "multi_well_percentage_dispenser"
    logger = start_workflow_logging(workflow_name, virtual=VIRTUAL)
    
    logger.info("="*70)
    logger.info("Starting Multi-Well Percentage Dispenser Workflow")
    logger.info("="*70)
    
    try:
        # Get percentage sets from configuration
        percentage_sets = PERCENTAGE_SETS
        
        # Validate
        validate_percentages(percentage_sets)
        logger.info(f"Validated {len(percentage_sets)} percentage sets")
        
        # Show plan
        print_dispensing_plan(percentage_sets)
        
        # Initialize hardware
        logger.info("Initializing hardware...")
        dispenser = Liquid_Dispenser(
            cnc_comport="COM3",
            actuator_comport="COM7",
            virtual=VIRTUAL
        )
        
        if not VIRTUAL:
            dispenser.cnc_machine.home()  # Home machine on real hardware
            logger.info("Machine homed successfully")
            
            try:
                import slack_agent
                secrets = slack_agent.load_secrets()
                SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
                SLACK_WEBHOOK_URL = secrets["SLACK_WEBHOOK_URL"]
                SLACK_CHANNEL = "C09J10VQ02C"
                slack_agent.send_slack_message(
                    f"Multi-Well Percentage Dispenser started. Filling {len(percentage_sets)} vials.",
                    SLACK_CHANNEL
                )
            except Exception as e:
                logger.warning(f"Could not send Slack notification: {e}")
        
        # Execute dispensing
        logger.info("Starting dispensing sequence...")
        print("\nStarting dispensing sequence...")
        
        starttime = time.time()
        
        dispense_colors_to_vials(dispenser, percentage_sets, logger, vial_start_index=0)
        
        elapsed_time = time.time() - starttime
        logger.info(f"Dispensing completed in {elapsed_time:.1f} seconds")
        
        # Summary
        total_ops = len(percentage_sets) * len(COLOR_ORDER)
        logger.info("="*70)
        logger.info(f"✓ WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info(f"  Vials filled: {len(percentage_sets)}")
        logger.info(f"  Dispense operations: {total_ops}")
        logger.info(f"  Conditioning steps: {total_ops}")
        logger.info(f"  Total time: {elapsed_time:.1f} seconds")
        logger.info("="*70)
        
        print("\n✓ Workflow completed successfully!")
        print(f"  Filled {len(percentage_sets)} vials in {elapsed_time:.1f} seconds")
        
        if not VIRTUAL:
            try:
                slack_agent.send_slack_message(
                    f"Multi-Well Percentage Dispenser completed! Filled {len(percentage_sets)} vials in {elapsed_time:.1f}s",
                    SLACK_CHANNEL
                )
            except Exception as e:
                logger.warning(f"Could not send completion Slack notification: {e}")
    
    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        print("\nWorkflow interrupted by user.")
    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        print(f"\n✗ Workflow failed: {e}")
        raise


if __name__ == "__main__":
    main()
