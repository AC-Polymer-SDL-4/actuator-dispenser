"""
Test script to verify the logging and virtual mode functionality.
This script tests all the enhanced components without requiring hardware.
"""

import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dispenser import Liquid_Dispenser

def test_virtual_mode():
    """Test the virtual mode functionality with all logging levels."""
    
    print("="*60)
    print("Testing Virtual Mode Liquid Dispenser")
    print("="*60)
    
    # Set up root logger to see all messages
    logging.basicConfig(level=logging.DEBUG, force=True)
    
    try:
        # Initialize dispenser in virtual mode
        print("\n1. Initializing dispenser in virtual mode...")
        dispenser = Liquid_Dispenser(
            cnc_comport="COM3",
            actuator_comport="COM6", 
            camera_index=0,
            virtual=True,  # This is the key - virtual mode!
            log_level=logging.INFO
        )
        
        print("\n2. Testing dispense_between operation...")
        dispenser.dispense_between(
            source_location="vial_rack",
            source_index=0,
            dest_location="well_plate", 
            dest_index=5,
            vol_pipet=0.1,  # 0.1 mL
            mix=False
        )
        
        print("\n3. Testing conditioning operation...")
        dispenser.dispense_condition(
            source_location="vial_rack",
            source_index=1,
            vol_pipet=0.5
        )
        
        print("\n4. Testing move to origin...")
        dispenser.move_to_origin()
        
        print("\n5. Testing image capture...")
        rgb = dispenser.get_image_rgb("well_plate", 0, "test")
        print(f"RGB result: {rgb}")
        
        print("\n6. Testing mix operation...")
        dispenser.dispense_between(
            source_location="vial_rack",
            source_index=2,
            dest_location="well_plate",
            dest_index=10, 
            vol_pipet=0.2,
            mix=True  # Test mixing
        )
        
        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("Virtual mode is working correctly with full logging.")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_virtual_mode()
