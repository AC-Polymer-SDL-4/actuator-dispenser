from base_workflow import ActuatorRemote
import time, logging

act = ActuatorRemote(port="COM3", virtual=False, log_level=logging.DEBUG, timeout=5.0)

print("EXT:", act.extend(0.8, speed=65000))
print("RET:", act.retract(5, speed=65000))
print("STOP:", act.stop())