# actuator_remote_arduino.py
import time
import logging

try:
    import serial
except ImportError as e:
    raise SystemExit("Please install pyserial:  pip install pyserial") from e

# Try to import your logging helpers; fall back to no-ops if unavailable
try:
    from log_config import setup_logger, log_method_entry, log_method_exit, log_virtual_action
except Exception:
    def setup_logger(name, virtual=False, log_level=logging.INFO):
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(log_level)
            ch = logging.StreamHandler()
            ch.setLevel(log_level)
            fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(fmt)
            logger.addHandler(ch)
        return logger
    def log_method_entry(logger, name, **kwargs): logger.debug(f"→ {name} {kwargs}")
    def log_method_exit(logger, name, result=None): logger.debug(f"← {name} {result}")
    def log_virtual_action(logger, msg): logger.info(f"[VIRTUAL] {msg}")

class ActuatorRemote:
    """
    Arduino-based actuator controller over serial.
    Compatible public API with your previous Pico/mpremote version.
    Commands sent to Arduino sketch:
      EXT <seconds> [speed0-65535]
      RET <seconds> [speed0-65535]
      STOP
    """
    def __init__(self, port="COM3", virtual=False, log_level=logging.INFO, baud=115200, timeout=2.0):
        self.port = port
        self.virtual = virtual
        self.baud = baud
        self.timeout = timeout

        # logger (uses yours if available, else the no-op fallback)
        self.logger = setup_logger("actuator_controller", virtual=virtual, log_level=log_level)
        log_method_entry(self.logger, "__init__", port=port, virtual=virtual)

        if self.virtual:
            self.ser = None
            self.logger.warning("ActuatorRemote running in VIRTUAL mode - no hardware communication")
            log_method_exit(self.logger, "__init__")
            return

        # --- open serial and prep UNO R4 CDC ---
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout, write_timeout=self.timeout)
        try:
            # KEY for UNO R4: keep DTR asserted so CDC streams serial
            self.ser.setDTR(True)
            self.ser.setRTS(False)
        except Exception:
            pass

        # allow CDC to settle after opening
        time.sleep(2.0)

        # Read (don't flush) a few startup lines so we see READY beacons
        t0 = time.time()
        while time.time() - t0 < 1.0:
            try:
                line = self.ser.readline().decode("ascii", "ignore").strip()
                if line:
                    self.logger.debug(f"Arduino: {line}")
            except Exception:
                break
            time.sleep(0.01)

        self.logger.info(f"ActuatorRemote connected on {self.port} @ {self.baud}")
        log_method_exit(self.logger, "__init__")



    def _send(self, line):
        log_method_entry(self.logger, "_send", line=line)
        if self.virtual:
            log_virtual_action(self.logger, f"Would send: {line!r}")
            log_method_exit(self.logger, "_send", "virtual")
            return "OK:VIRTUAL"

        msg = (line.strip() + "\n").encode("ascii")
        self.ser.write(msg)
        self.ser.flush()
        # Read one line of response (Arduino prints OK/ERR)
        resp = ""
        t0 = time.time()
        while time.time() - t0 < self.timeout:
            if self.ser.in_waiting:
                resp = self.ser.readline().decode("ascii", errors="ignore").strip()
                break
            time.sleep(0.01)
        if not resp:
            resp = "NO-RESPONSE"
        self.logger.debug(f"Arduino: {resp}")
        log_method_exit(self.logger, "_send", resp)
        return resp

    def _send_and_wait_stop(self, line, expected_secs, extra=0.5):
        # send the command
        resp = self._send(line)
        # now wait until Arduino reports it's done, or timeout
        deadline = time.time() + float(expected_secs) + float(extra)
        last = resp
        while time.time() < deadline:
            try:
                r = self.ser.readline().decode("ascii","ignore").strip()
            except Exception:
                r = ""
            if r:
                self.logger.debug(f"Arduino: {r}")
                last = r
                if "OK:STOPPED" in r:
                    return r  # finished the timed move
            time.sleep(0.01)
        return last or "NO-RESPONSE"


    def extend(self, seconds, speed=32768, wait=True):
        line = f"EXT {float(seconds):.3f} {int(speed)}"
        if wait:
            return self._send_and_wait_stop(line, expected_secs=seconds)
        else:
            return self._send(line)

    def retract(self, seconds, speed=32768, wait=True):
        line = f"RET {float(seconds):.3f} {int(speed)}"
        if wait:
            return self._send_and_wait_stop(line, expected_secs=seconds)
        else:
            return self._send(line)

    def stop(self):
        """Stop immediately."""
        log_method_entry(self.logger, "stop")
        resp = self._send("STOP")
        log_method_exit(self.logger, "stop", resp)
        return resp

    def close(self):
        if self.ser:
            try: self.ser.close()
            except Exception: pass
