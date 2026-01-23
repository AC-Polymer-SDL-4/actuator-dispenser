# diag_serial.py
import time, serial, serial.tools.list_ports

# 1) Show ports with details so we’re 100% on the right one
ports = list(serial.tools.list_ports.comports())
print("Available ports:")
for p in ports:
    print(f"  {p.device}  vid={p.vid} pid={p.pid}  desc='{p.description}'  hwid='{p.hwid}'")

PORT = "COM3"   # <-- set to your UNO’s port
BAUD = 115200

print(f"\nOpening {PORT} @ {BAUD} …")
ser = serial.Serial(PORT, BAUD, timeout=3)

# Don’t hold reset lines; some boards need this off
try:
    ser.setDTR(False)
    ser.setRTS(False)
except Exception:
    pass

# Give the UNO time to (re)start after open
time.sleep(2.5)

# Drain any startup text then read for 3s to catch READY lines
print("Reading any READY lines for 3s…")
t0 = time.time()
while time.time() - t0 < 3.0:
    if ser.in_waiting:
        line = ser.readline().decode("ascii", "ignore").strip()
        print("<<", line)

def send(cmd, wait=3.0):
    print(">>", cmd)
    ser.write((cmd + "\n").encode("ascii"))
    ser.flush()
    t1 = time.time()
    got = False
    while time.time() - t1 < wait:
        if ser.in_waiting:
            line = ser.readline().decode("ascii", "ignore").strip()
            print("<<", line)
            got = True
            # keep printing any additional lines that arrive briefly
            t2 = time.time()
            while time.time() - t2 < 0.2 and ser.in_waiting:
                print("<<", ser.readline().decode("ascii", "ignore").strip())
            break
        time.sleep(0.01)
    if not got:
        print("<< (no response)")

# Now that we should be seeing READY in the loop, try commands.
print("\nSend commands (make sure 12 V is plugged in):\n")
send("EXT 1.0 60000")
time.sleep(1.3)
send("STOP")
time.sleep(0.3)
send("RET 1.0 60000")
time.sleep(1.3)
send("STOP")

ser.close()
