from machine import ADC, Pin
import time

# Connect the yellow wire to GPIO 34 (or any other ADC pin you used)
feedback_pin = ADC(Pin(34))      # Choose your actual pin
feedback_pin.atten(ADC.ATTN_11DB)  # Set range 0 - 3.3V

while True:
    val = feedback_pin.read()  # 0 to 4095
    voltage = val * 3.3 / 4095
    print("Raw:", val, "Voltage:", voltage)
    time.sleep(0.5)