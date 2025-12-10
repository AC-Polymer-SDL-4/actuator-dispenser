# Ultra-budget liquid dispenser
[ADD IMAGE]
## Overview
This repository contains an assembly guide, code, 3D-design files and data collected from using our ultra-budget liquid dispenser. With a small footprint, low cost (~$500 USD), short assembly time (4 hrs), full python integration and visual characterization, this system provides an accessible tool for developing self-driving (automated and AI-guided) workflows.

### Highlights of this system:
- Low cost (approx. $500 USD, see the [bill of materials](#bill-of-materials-bom) below)
- High customizability (3D-printed files can be adapted for different syringes / actuators / labware)
- Full python integration, with modular code design
- Short assembly Time (4 hours)

### Folders included in this repo: 
1. `3D_models`: contains .f3d and .stl files for the 3D-printed labware holder, tool head and electronics casing, along with an assembly guide
2. `code`: contains the python files for the workflows, tests and code used to control the system and a user guide for code usage
3. `data`: contains the experimental data collected from color matching workflows (and PVA complexation workflows), referenced in the paper

### Authors:
Monique Ngan, David Okhimame, Harrison Mills, Owen Melville, Nipun Kumar Gupta <br>
[Acceleration Consortium](https://acceleration.utoronto.ca/) <br>
Last updated: Dec 8, 2025

## Summary of Assembly Guide
A complete assembly guide is provided in the `3D_models` folder.

### Bill of Materials (BoM)
All materials required to build this dispenser are listed below.
|Item|Manufacturer|Product Number|Qty|Cost ($USD)|Notes|
|--|--|--|--|--|--|
|CNC Machine|Genmitsu|[3018-PROVer V2](https://www.amazon.com/Genmitsu-3018-PROVer-Beginner-Emergency-Stop-Spoilboard/dp/B0CMTJ6CZC/ref=sr_1_1_sspa?crid=114QL76VIJQT2&dib=eyJ2IjoiMSJ9.si54z4Io1GeuV5q_lf4cUYZaZCHezjGgIqHPUU6P0igZW3XxzJmYpZL9AtNIYYhJccTElgCcUhtUQdVV5ba8m4LS1GSoMPPCwf3UhyZvH4ZiUVoozKL17vWyOP9NJd20GuYpfVtuVC89muO9eLsUb9GWtYLfNeeW22jnDYMXf6Wj7DleAou0EVavEHKg_6sW3kLy3ayNA2Ds_glnvx3UoRy4-qHn3XDycz0rp29txVuko8hxuk06H_KGxhoJuUdYbvN3ssnQmkJF5SzANHrhnlooRnQT6lFYgSyDRnvIUy8.md_gFbjykxNHiYnS4wvrPfHJinOVtTMHGsAoOf21tVY&dib_tag=se&keywords=genmitsu+3018+pro&qid=1765214407&sprefix=%2Caps%2C61&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1)|1|270|Gantry system|
|Backlight|HSK|[A4 Artist tracing Light Box](https://www.amazon.com/A4-Improved-Structure-Storage-Warranty/dp/B0755C2CBF/ref=sr_1_4_sspa?crid=HGMW73TTRQPR&dib=eyJ2IjoiMSJ9.4_N0Ik2-dp33AqZZQUH6lPCSK-indHZUztzxuA_r5m_N6FRgQakr2q2xWczA877ma-Kn3Wg1YssFvzX84_W71JBoGDrN-t-5l_fsytKcybtXcK0HeyLXEXp_SuL3Htm51K4VryE6UoOmJL38-CZoYn_D8gwmrOynzbvfrmPzWD8jF6ix13Yp7R2c_YWNEXzYW7PVZbbpmDKgD99cERhaPxwE0AcsIdEN1bAno8V0K94bn6aerwMUDKuRpkXaxoCaNUVZQ9D3wBQpVmUUeIcgyqLJ7cCkaRW__667lzrvsLQ.3viHBebDTzdf3RWMV6b_BhIbzKl7_wF7b8SZPi4-uwI&dib_tag=se&keywords=a4%2Bled%2Bpanel&qid=1765299952&sprefix=a4%2Bled%2Bpanel%2Caps%2C148&sr=8-4-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1)|1|25.00|Enhances color visibility|
|Endoscope Camera|Tyenaza|[Endoscope Camera, Mobile Phone PC USB Type C](https://www.amazon.com/Endoscope-Camera-Mobile-Android-Automobile/dp/B0C6JR8TG8/ref=sr_1_10?dib=eyJ2IjoiMSJ9.UIx0_MnMRGRcN0FERPB60y0NFmOgdnMQwJY_1EN66x4e0-ot7XKPUeLJWaDTTIR6yV3tI7ThsW7LMkz1T1ZsGDWzj2Li6v4Vzr0u1RFGjRJIh_l7XIKk1Q0l5vpX20Y2uUF0HGad6THztKjjV1ANWd9QVDipdAZR5o26QjN-asDvbAYdY3iFJLmzDEKfAzMXOLw6BiDXPRqVsRnZXsVLfnMkuEQyuJAj5EdrKnWCnd5dk5_VgxRdt2Xlt7z77ri_MPU8DGG1KqCneqq29vXT1oAolqWyowlYc-aIQW_GiM8.EIXRIeel0Ufo-43jwhLEJ31pGBRFZajIRWRv7-a2gD0&dib_tag=se&keywords=endoscope+camera+pc&qid=1765299980&sr=8-10)|1|13.07|Visual Characterization|
|Actuator|Actuonix|[P8-25-165-12-P](https://www.robotshop.com/products/actuonix-p8-p-micro-linear-actuator-25mm-1651-12-volts)|1|101|Movement of syringe plunger|
|1 mL Glass Syringe|Bitomic|[1ML Borosilicate Glass Syringe with Silver Metal Plunger](https://www.amazon.com/Bitomic-Borosilicate-Anti-Leak-Accurate-Measuring/dp/B0B12N5FX1/ref=sr_1_4?crid=27Z7T6R5TKLKY&dib=eyJ2IjoiMSJ9.Yw4kuoOLBHtQtgRgCWrg_UyrphPhIigHygfRI9gIOsOOxc5vZB-vT6Ud9MmBn5jASPJFDirAoTOCDC5BUK4XhJrzwQ0H2fK1CxhK8O50jTiz1UXBEKUiPXQHhhY0z7NGUJ_H0zS58w3F-HV7qmqQ1KvSXZVnOcc-H95d0KyJQKOkdQ1ql96qCZtY4TWm8Ug5pwZGvPdHG9RO7FutGuSDnvlcll1teu8786hucaDxSbc.PAqqr5PJKCy80cdOngdv4AXuUCcV1T5XpCM-I6ynCME&dib_tag=se&keywords=1ml%2Bsyringe%2Bwith%2Bmetal%2Bplunger&qid=1761926550&sprefix=1ml%2Bsyringe%2Bwith%2Bmetal%2Bplunge%2Cspecialty-aps%2C86&sr=8-4-catcorr&srs=58792496011&th=1)|1|23.04|Comes in pack of 10 syringes|
|Microcontroller|Arduino|[UNO R3](https://www.robotshop.com/products/arduino-uno-r3-usb-microcontroller)|1|30.08|Communication between computer and actuator|
|Motor Board|Arduino|[A000079](https://www.digikey.ca/en/products/detail/arduino/A000079/2784007)|1|28.4|Powers actuator|
|12V Barrel Power Supply|Digikey||1||Microcontroller power supply
|3D-printed tool head and deck ware|n/a|n/a|1|5|Printed in PLA and PETG|
|3D-printed electronics box|n/a|n/a|1|2.18|optional|
|Total Cost||||**approximately 500**||

### Other generic materials needed:

|Item|Manufacturer|Product Number|Qty|Cost ($USD)|Notes|
|--|--|--|--|--|--|
|22 AWG Wires|Adafruit|[1311](https://www.adafruit.com/product/1311)|40 cm|15.95||
|M3 **x 16mm** Screw|Adafruit|[1311](https://www.adafruit.com/product/1311)|1|15.95|Locking mechanism between syringe plunger and actuator|
|M3 Nut|Adafruit|[1311](https://www.adafruit.com/product/1311)|1|15.95|Locking mechanism between syringe plunger and actuator|
|M6 **x 10mm** Screw|Adafruit|[1311](https://www.adafruit.com/product/1311)|4|15.95|Holds deckware on CNC deck|

- pliers
- Allen keys
- Super glue
- access to 3D printer, with PLA, PETG and 95A TPU filament

### Summary of steps for assembling this tool
_Total assembly time: approximately 4 hours_

1.	Order the required parts in the BoM.
2.	3D-print the files in the `3D_models` folder including the tool head and optionally the deckware holder, backlight clamps and electronics casing
3.	Assemble the CNC machine following the manufacturer's instructions (_2 hours_)
4.	Connect the actuator to the microcontroller and power supply (_20 mins_)
5.	Connect the device to your computer and code setup (_25 minutes, depending on your operating system_)
6.	Assemble the tool head (_50 mins_)
7.	Mount the backlight and deck ware holder (_optional, 5 mins_)

## Known issues
1. Gradual decrease in volume dispensed over time: It is recommended to **re-calibrate** the dispenser every 3 full 24-wellplates of experiments (~1200 liquid transfers) and **replace the syringe** every 6 well plates of experiments (~2000 liquid transfers).
2. The glass syringe may break over time due to repeated stress from the extension of the metal plunger: It is highly recommended to 3D-print the **TPU padding** (see the `3D_models` folder) and glue it to the bottom of the syringe.
