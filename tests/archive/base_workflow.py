"""
Base workflow module that handles importing from the parent directory.
Import this at the beginning of your workflow files to access the main modules.
"""

import sys
import os

# Add the parent directory to Python path so we can import the main modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the main modules and make them available
from actuator_controller import ActuatorRemote
from cnc_machine import CNC_Machine
from dispenser import Liquid_Dispenser
from camera import Camera
from log_config import initialize_workflow_logging

# You can now use these in your workflow files:
# ActuatorRemote, CNC_Machine, Liquid_Dispenser, initialize_workflow_logging

def start_workflow_logging(workflow_name, virtual=False):
    """
    Convenience function to start workflow logging.
    Call this at the beginning of your workflow with the workflow filename.
    
    Args:
        workflow_name (str): Name of the workflow (e.g., "example_workflow")
        virtual (bool): Whether running in virtual mode
    
    Returns:
        logging.Logger: Workflow logger
    """
    return initialize_workflow_logging(workflow_name, virtual=virtual)
