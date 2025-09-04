from actuator_controller import ActuatorRemote

act = ActuatorRemote(port='COM7')

act.extend(2)
act.retract(2)