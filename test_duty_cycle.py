from machine import Pin, PWM
import time

IN1 = Pin(26, Pin.OUT)
IN2 = Pin(25, Pin.OUT)
ENA = PWM(Pin(27), freq=1000)
ENA.duty(512)  # 50% duty cycle (range 0-1023 for ESP32)

IN1.on()
IN2.off()
ENA.duty(512)
print("Extending...")
time.sleep(0)

IN1.off()
IN2.on()
ENA.duty(512)
print("Retracting...")
time.sleep(10)

IN1.off()
IN2.off()
ENA.duty(0)
print("Stopped.")
