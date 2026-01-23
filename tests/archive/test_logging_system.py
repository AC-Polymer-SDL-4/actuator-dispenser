"""
Test script to verify the new centralized logging system with virtual mode tagging.
This script tests both virtual=True and virtual=False modes to ensure logs are
properly saved in the logs/ folder with appropriate tagging.
"""

import logging
from actuator_controller import ActuatorRemote
from dispenser import Liquid_Dispenser

def test_virtual_logging():
    """Test the logging system with virtual mode enabled."""
    print("=== Testing Virtual Mode Logging ===")
    
    # Test actuator in virtual mode
    print("Testing ActuatorRemote in virtual mode...")
    actuator_virtual = ActuatorRemote(port="COM6", virtual=True, log_level=logging.DEBUG)
    actuator_virtual.extend(2.0, speed=50000)
    actuator_virtual.retract(1.5, speed=40000)
    actuator_virtual.stop()
    
    print("Testing Liquid_Dispenser in virtual mode...")
    # Test dispenser in virtual mode
    dispenser_virtual = Liquid_Dispenser(
        cnc_comport="COM3", 
        actuator_comport="COM6", 
        virtual=True, 
        log_level=logging.DEBUG
    )
    
    print("Virtual mode test completed!")

def test_real_logging():
    """Test the logging system with virtual mode disabled (but still no hardware)."""
    print("\n=== Testing Real Mode Logging (no actual hardware) ===")
    
    # Note: This will try to connect to hardware but will fail gracefully
    # The important thing is to verify the logging works correctly
    try:
        print("Testing ActuatorRemote in real mode...")
        actuator_real = ActuatorRemote(port="COM6", virtual=False, log_level=logging.DEBUG)
        print("ActuatorRemote created successfully (but will fail on commands without hardware)")
    except Exception as e:
        print(f"Expected error (no hardware): {e}")
    
    print("Real mode test completed!")

def main():
    """Main test function."""
    print("Testing the new centralized logging system...")
    print("Check the logs/ folder for generated log files:")
    print("- actuator_controller_virtual_YYYYMMDD.log")
    print("- actuator_controller_YYYYMMDD.log") 
    print("- dispenser_virtual_YYYYMMDD.log")
    print("- dispenser_YYYYMMDD.log")
    print()
    
    test_virtual_logging()
    test_real_logging()
    
    print("\n=== Test Complete ===")
    print("Check the logs/ folder to verify log files were created with proper naming!")

if __name__ == "__main__":
    main()
