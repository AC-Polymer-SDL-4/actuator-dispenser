slope = 0.4003 #0.4295
volume = float(input("what is ur desired volume in mL? "))  # Example volume in milliliters
time = round(volume / slope, 2)

print(" Time to dispense volume:", time, "seconds")

