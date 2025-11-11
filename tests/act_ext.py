from base_workflow import ActuatorRemote
import time, logging

act = ActuatorRemote(port="COM6", virtual=False, log_level=logging.DEBUG, timeout=1.0)

#SINGLE TESTS
# print("RET:", act.retract(0.3, speed=65000))
# time.sleep(1)
print("EXT:", act.extend(0.1, speed=65000))

time.sleep(1)
print("STOP:", act.stop())

#SPEED AND TIME CALIBRATION TEST
#SPEEDS = [32768/2, 32768/3] 
SPEEDS = [32678]
TIMES = [0.25, 0.5, 1, 1.25]
REPLICATES = 4
BUFFER = 0.1
# for s in SPEEDS:
#     for t in TIMES:
#         for r in range(REPLICATES):
#             print(f"RET at speed {s}, time {t}: ", act.retract(t, speed=s))
#             time.sleep(1)
#             input(f"***Retracted at speed {s}, time {t}, rep {r}. Press Enter to continue***")
#             print(f"EXT at speed {s}, time {t}: ", act.extend(t+BUFFER, speed=s))
#             input(f"***Completed speed {s}, time {t}, rep {r}. Press Enter to continue***")

# print("STOP:", act.stop())