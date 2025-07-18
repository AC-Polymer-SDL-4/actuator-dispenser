from actuator_controller import ActuatorRemote

act = ActuatorRemote(port='COM7')

act.extend(.05)
act.retract(.05)