from actuator_controller import ActuatorRemote

act = ActuatorRemote(port='COM3')

act.extend(2)
act.retract(2)