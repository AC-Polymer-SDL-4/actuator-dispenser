from base_workflow import ActuatorRemote

act = ActuatorRemote(port='COM3')

act.extend(.2)
act.retract(.2)
