from actuator_controller import ActuatorRemote

act = ActuatorRemote(port='COM3')


act.retract(1)