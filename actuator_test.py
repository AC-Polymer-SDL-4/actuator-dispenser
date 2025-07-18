from actuator_controller import ActuatorRemote

act = ActuatorRemote(port='COM7')

act.extend(3)
act.retract(3)