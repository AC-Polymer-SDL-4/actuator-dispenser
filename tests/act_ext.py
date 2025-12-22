from base_workflow import ActuatorRemote
import time, logging

act = ActuatorRemote(port="COM3", virtual=False, log_level=logging.DEBUG, timeout=1.0)

#SINGLE TESTS
print("RET:", act.retract(0.3, speed=65000)) #moves the plunger up by ~2mm
time.sleep(1)
print("EXT:", act.extend(0.55, speed=65000)) #extra buffer time to ensure plunger is at the bottom
time.sleep(1)
print("STOP:", act.stop())
