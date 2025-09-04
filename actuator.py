from machine import Pin, PWM
import time

class Actuator:
    """
    Class to control a linear actuator using an H-bridge and PWM.
    Designed for Raspberry Pi Pico (uses duty_u16 scale: 0–65535).
    """

    def __init__(self):
        # Setup GPIO pins for direction control
        self.IN1 = Pin(26, Pin.OUT)
        self.IN2 = Pin(25, Pin.OUT)

        # Setup PWM pin for speed control
        self.ENA = PWM(Pin(27))
        self.ENA.freq(1000)
        self.ENA.duty_u16(0)  # 50% duty cycle (range: 0–65535)

    def extend(self, time_seconds):
        """
        Extend the actuator for the specified duration.
        """
        self.IN1.on()
        self.IN2.off()
        self.ENA.duty_u16(10000)
        print("Extending...")
        time.sleep(time_seconds)

    def retract(self, time_seconds):
        """
        Retract the actuator for the specified duration.
        """
        self.IN1.off()
        self.IN2.on()
        self.ENA.duty_u16(10000)
        print("Retracting...")
        time.sleep(time_seconds)

    def stop_actuator(self):
        """
        Stop the actuator by disabling motor power.
        """
        self.IN1.off()
        self.IN2.off()
        self.ENA.duty_u16(0)
        print("Stopped.")
