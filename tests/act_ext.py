from base_workflow import ActuatorRemote
import time, logging

act = ActuatorRemote(port="COM6", virtual=False, log_level=logging.DEBUG, timeout=1.0)

#print("RET:", act.retract(0.5, speed=65000))
time.sleep(1)
print("EXT:", act.extend(0.8, speed=65000))

print("STOP:", act.stop())