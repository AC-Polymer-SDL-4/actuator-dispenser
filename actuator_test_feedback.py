from machine import Pin, ADC, PWM
import time

IN1 = Pin(26, Pin.OUT)
IN2 = Pin(25, Pin.OUT)
ENA = PWM(Pin(27))
ENA.freq(1000)

adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

def extend():
    IN1.value(1)
    IN2.value(0)
    ENA.duty(512)

def retract():
    IN1.value(0)
    IN2.value(1)
    ENA.duty(512)

def stop_motor():
    ENA.duty(0)
    IN1.value(0)
    IN2.value(0)

def read_position():
    return adc.read()

print("Extending for 5 seconds...")
extend()
start = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), start) < 5000:
    position = read_position()
    print("Position:", position)
    time.sleep(0.1)
    if position < 300:
        stop_motor()

# stop_motor()

# print("Waiting 1 second before retracting...")
# time.sleep(1)

# print("Retracting for 5 seconds...")
# retract()
# start = time.ticks_ms()
# while time.ticks_diff(time.ticks_ms(), start) < 5000:
#     print("Position:", read_position())
#     time.sleep(0.1)
# stop_motor()

print("Done.")
