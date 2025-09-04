import subprocess
import logging
from log_config import setup_logger, log_method_entry, log_method_exit, log_virtual_action

class ActuatorRemote:
    """
    Remote controller class to operate a Pico-based actuator
    by sending commands using mpremote subprocess calls.
    
    Features:
      - Virtual mode for testing without hardware
      - Structured logging with file output in logs/ folder
      - Compatible with CNC_Machine logging system
    """

    def __init__(self, port="COM6", virtual=False, log_level=logging.INFO):
        """
        Initialize the actuator controller.
        
        Args:
            port (str): Serial port for the Pico (e.g., "COM6")
            virtual (bool): If True, simulates operations without hardware communication
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.port = port
        self.virtual = virtual
        
        # Setup centralized logging with virtual mode tagging
        self.logger = setup_logger("actuator_controller", virtual=virtual, log_level=log_level)
        
        log_method_entry(self.logger, "__init__", port=port, virtual=virtual)
        
        if virtual:
            self.logger.warning("ActuatorRemote running in VIRTUAL mode - no hardware communication")
        else:
            self.logger.info(f"ActuatorRemote initialized for port {port}")
            
        log_method_exit(self.logger, "__init__")

    def _call(self, command_body):
        """
        Internal method to send an mpremote command string to the Pico.
        
        Args:
            command_body (str): Python code to execute on the Pico
        """
        log_method_entry(self.logger, "_call", command_body=command_body)
        
        if self.virtual:
            # In virtual mode, just log what would be executed
            log_virtual_action(self.logger, f"Would execute mpremote command: {command_body}")
            log_method_exit(self.logger, "_call", "Virtual execution completed")
            return
            
        self.logger.debug("Executing mpremote command on %s", self.port)
        try:
            subprocess.run(
                ["mpremote", "connect", self.port, "exec", command_body],
                check=True
            )
            self.logger.debug("Command executed successfully")
            log_method_exit(self.logger, "_call", "Success")
        except subprocess.CalledProcessError as e:
            self.logger.error("mpremote command failed: %s", e)
            log_method_exit(self.logger, "_call", f"Failed: {e}")
            raise

    def extend(self, seconds, speed=32768):
        """
        Remotely extend the actuator for a given number of seconds.
        
        Args:
            seconds (float): Duration to extend in seconds
            speed (int): Speed setting for the actuator (0-65535)
        """
        log_method_entry(self.logger, "extend", seconds=seconds, speed=speed)
        
        self.logger.info("Extending actuator: %.2f seconds at speed %d", seconds, speed)
        command = f"import actuator; a=actuator.Actuator({speed}); a.extend({seconds}); a.stop_actuator()"
        
        self._call(command)
        log_method_exit(self.logger, "extend")

    def retract(self, seconds, speed=32768):
        """
        Remotely retract the actuator for a given number of seconds.
        
        Args:
            seconds (float): Duration to retract in seconds
            speed (int): Speed setting for the actuator (0-65535)
        """
        log_method_entry(self.logger, "retract", seconds=seconds, speed=speed)
        
        self.logger.info("Retracting actuator: %.2f seconds at speed %d", seconds, speed)
        command = f"import actuator; a=actuator.Actuator({speed}); a.retract({seconds}); a.stop_actuator()"
        
        self._call(command)
        log_method_exit(self.logger, "retract")

    def stop(self):
        """
        Remotely stop the actuator immediately.
        """
        log_method_entry(self.logger, "stop")
        
        self.logger.info("Stopping actuator immediately")
        command = "import actuator; a=actuator.Actuator(); a.stop_actuator()"
        
        self._call(command)
        log_method_exit(self.logger, "stop")
