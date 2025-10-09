from base_workflow import ActuatorRemote
import logging
import time

act = ActuatorRemote(port='COM3', log_level=logging.DEBUG)

act.extend(0.1)
# time.sleep(1)
#act.retract(.2)
