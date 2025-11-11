slope = 0.461 #0.4295 (David's version), 0.4003 (MN version 1)
volume = float(input("what is ur desired volume in mL? "))  # Example volume in milliliters
time = round(volume / slope, 2)

print(" Time to dispense volume:", time, "seconds")

