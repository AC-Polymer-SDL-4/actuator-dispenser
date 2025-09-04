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

# You can now use these in your workflow files:
# ActuatorRemote, CNC_Machine, Liquid_Dispenser
