import subprocess

class ActuatorRemote:
    """
    Remote controller class to operate a Pico-based actuator
    by sending commands using mpremote subprocess calls.
    """

    def __init__(self, port="COM6"):
        self.port = port

    def _call(self, command_body):
        """
        Internal method to send an mpremote command string to the Pico.
        """
        try:
            subprocess.run(
                ["mpremote", "connect", self.port, "exec", command_body],
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f"mpremote command failed: {e}")

    def extend(self, seconds):
        """
        Remotely extend the actuator for a given number of seconds.
        """
        self._call(f"import actuator; a=actuator.Actuator(); a.extend({seconds}); a.stop_actuator()")

    def retract(self, seconds):
        """
        Remotely retract the actuator for a given number of seconds.
        """
        self._call(f"import actuator; a=actuator.Actuator(); a.retract({seconds}); a.stop_actuator()")

    def stop(self):
        """
        Remotely stop the actuator immediately.
        """
        self._call("import actuator; a=actuator.Actuator(); a.stop_actuator()")
