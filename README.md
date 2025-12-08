# Ultra-budget liquid dispenser
[ADD IMAGE]
## Overview
This repository contains an assembly guide, code, 3D-design files and data collected from using our ultra-budget liquid dispenser. With a small footprint, low cost (~$500 USD), short assembly time (4 hrs), full python integration and visual characterization, this system provides an accessible tool for developing self-driving (automated and AI-guided) workflows.

### Highlights of this system:
- Low cost (approx. $500 USD, see the [bill of materials](#bill-of-materials) below)
- High customizability (3D-printed files can be adapted for different syringes / actuators / labware)
- Full python integration, with modular code design
- Short assembly Time (4 hours)

### Folders included in this repo: 
1. `3D_models`: contains .f3d and .stl files for the 3D-printed labware holder, tool head and electronics casing
2. `code`: contains the python files for the workflows, tests and code used to control the system and a user guide
3. `data`: contains the experimental data collected from color matching workflows (and PVA complexation workflows), referenced in the paper

### Authors:
Monique Ngan, David Okhimame, Harrison Mills, Owen Melville, Nipun Kumar Gupta <br>
[Acceleration Consortium](https://acceleration.utoronto.ca/) <br>
Last updated: Dec 8, 2025

## Assembly Guide
### Bill of Materials 
|Item|Manufacturer|Product Number|Qty|Cost ($USD)|Notes|
|--|--|--|--|--|--|
|CNC Machine|Genmitsu|[3018-PROVer V2](https://www.amazon.com/Genmitsu-3018-PROVer-Beginner-Emergency-Stop-Spoilboard/dp/B0CMTJ6CZC/ref=sr_1_1_sspa?crid=114QL76VIJQT2&dib=eyJ2IjoiMSJ9.si54z4Io1GeuV5q_lf4cUYZaZCHezjGgIqHPUU6P0igZW3XxzJmYpZL9AtNIYYhJccTElgCcUhtUQdVV5ba8m4LS1GSoMPPCwf3UhyZvH4ZiUVoozKL17vWyOP9NJd20GuYpfVtuVC89muO9eLsUb9GWtYLfNeeW22jnDYMXf6Wj7DleAou0EVavEHKg_6sW3kLy3ayNA2Ds_glnvx3UoRy4-qHn3XDycz0rp29txVuko8hxuk06H_KGxhoJuUdYbvN3ssnQmkJF5SzANHrhnlooRnQT6lFYgSyDRnvIUy8.md_gFbjykxNHiYnS4wvrPfHJinOVtTMHGsAoOf21tVY&dib_tag=se&keywords=genmitsu+3018+pro&qid=1765214407&sprefix=%2Caps%2C61&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1)|1|270|Gantry system|
|Backlight||[](https://www.amazon.com/Genmitsu-3018-PROVer-Beginner-Emergency-Stop-Spoilboard/dp/B0CMTJ6CZC/ref=sr_1_1_sspa?crid=114QL76VIJQT2&dib=eyJ2IjoiMSJ9.si54z4Io1GeuV5q_lf4cUYZaZCHezjGgIqHPUU6P0igZW3XxzJmYpZL9AtNIYYhJccTElgCcUhtUQdVV5ba8m4LS1GSoMPPCwf3UhyZvH4ZiUVoozKL17vWyOP9NJd20GuYpfVtuVC89muO9eLsUb9GWtYLfNeeW22jnDYMXf6Wj7DleAou0EVavEHKg_6sW3kLy3ayNA2Ds_glnvx3UoRy4-qHn3XDycz0rp29txVuko8hxuk06H_KGxhoJuUdYbvN3ssnQmkJF5SzANHrhnlooRnQT6lFYgSyDRnvIUy8.md_gFbjykxNHiYnS4wvrPfHJinOVtTMHGsAoOf21tVY&dib_tag=se&keywords=genmitsu+3018+pro&qid=1765214407&sprefix=%2Caps%2C61&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1)|1|270|Gantry system|
|Endoscope Camera||[](https://www.amazon.com/Genmitsu-3018-PROVer-Beginner-Emergency-Stop-Spoilboard/dp/B0CMTJ6CZC/ref=sr_1_1_sspa?crid=114QL76VIJQT2&dib=eyJ2IjoiMSJ9.si54z4Io1GeuV5q_lf4cUYZaZCHezjGgIqHPUU6P0igZW3XxzJmYpZL9AtNIYYhJccTElgCcUhtUQdVV5ba8m4LS1GSoMPPCwf3UhyZvH4ZiUVoozKL17vWyOP9NJd20GuYpfVtuVC89muO9eLsUb9GWtYLfNeeW22jnDYMXf6Wj7DleAou0EVavEHKg_6sW3kLy3ayNA2Ds_glnvx3UoRy4-qHn3XDycz0rp29txVuko8hxuk06H_KGxhoJuUdYbvN3ssnQmkJF5SzANHrhnlooRnQT6lFYgSyDRnvIUy8.md_gFbjykxNHiYnS4wvrPfHJinOVtTMHGsAoOf21tVY&dib_tag=se&keywords=genmitsu+3018+pro&qid=1765214407&sprefix=%2Caps%2C61&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1)|1|270|Gantry system|
|Actuator|Actuonix|[P8-25-165-12-P](https://www.robotshop.com/products/actuonix-p8-p-micro-linear-actuator-25mm-1651-12-volts)|1|101|Movement of syringe plunger|
|1 mL Glass Syringe|Bitomic|[1ML Borosilicate Glass Syringe with Silver Metal Plunger](https://www.amazon.com/Bitomic-Borosilicate-Anti-Leak-Accurate-Measuring/dp/B0B12N5FX1/ref=sr_1_4?crid=27Z7T6R5TKLKY&dib=eyJ2IjoiMSJ9.Yw4kuoOLBHtQtgRgCWrg_UyrphPhIigHygfRI9gIOsOOxc5vZB-vT6Ud9MmBn5jASPJFDirAoTOCDC5BUK4XhJrzwQ0H2fK1CxhK8O50jTiz1UXBEKUiPXQHhhY0z7NGUJ_H0zS58w3F-HV7qmqQ1KvSXZVnOcc-H95d0KyJQKOkdQ1ql96qCZtY4TWm8Ug5pwZGvPdHG9RO7FutGuSDnvlcll1teu8786hucaDxSbc.PAqqr5PJKCy80cdOngdv4AXuUCcV1T5XpCM-I6ynCME&dib_tag=se&keywords=1ml%2Bsyringe%2Bwith%2Bmetal%2Bplunger&qid=1761926550&sprefix=1ml%2Bsyringe%2Bwith%2Bmetal%2Bplunge%2Cspecialty-aps%2C86&sr=8-4-catcorr&srs=58792496011&th=1)|1|23.04|Comes in pakc of 10 syringes|
|Microcontroller|Arduino|[UNO R3](https://www.robotshop.com/products/arduino-uno-r3-usb-microcontroller)|1|30.08||
|Motor Board|Arduino|[A000079](https://www.digikey.ca/en/products/detail/arduino/A000079/2784007)|1|28.4||
|12V Barrel Power Supply|Digikey||1||Microcontroller power supply
|3D-printed tool head and deck ware|n/a|n/a|1|5|Printed in PLA and PETG|
|3D-printed electronics box|n/a|n/a|1|2.18|optional|
## Known issues
1. Gradual decrease in volume dispensed over time: It is recommended to **re-calibrate** the dispenser every 3 full 24-wellplates of experiments (~1200 liquid transfers) and switch to a new syringe every 6 well plates of experiments (~2000 liquid transfers).
2. The glass syringe may break over time due to repeated stress from the extension of the metal plunger: It is highly recommended to 3D-print the **TPU padding** (see the `3D_models` folder) and glue it to the bottom of the syringe.
