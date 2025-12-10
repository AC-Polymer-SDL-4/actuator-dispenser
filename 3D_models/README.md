# Hardware Assembly Guide
## Summary of steps
_Total assembly time: ~4 hours_

1.	Order the required parts in the BoM.
2.	3D-print the files in the `3D_models` folder including the tool head and optionally the deckware holder, backlight clamps and electronics casing
3.	Assemble the CNC machine following the manufacturer's instructions (_2 hours_)
4.	Connect the actuator to the microcontroller and power supply (_20 mins_)
5.	Connect the device to your computer and code setup (_25+ minutes, depending on your operating system_)
6.	Assemble the tool head (_50 mins_)
7.	Mount the backlight and deck ware holder (_optional, 5 mins_)
   
Please also read through the [**important notes**](#%EF%B8%8Fimportant-notes-things-to-watch-out-for-when-starting-workflows).

---
## Step 1: Order Required Parts
All materials required to build this dispenser are listed below:

### Bill of Materials (BoM)
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

### Generic Materials and Tools needed
|Item|Manufacturer|Product Number|Qty|Cost ($USD)|Notes|
|--|--|--|--|--|--|
|22 AWG Wires|Adafruit|[1311](https://www.adafruit.com/product/1311)|40 cm|15.95||
|M3 **x 16mm** Screw|Adafruit|[1311](https://www.adafruit.com/product/1311)|1|15.95|Locking mechanism between syringe plunger and actuator|
|M3 Nut|Adafruit|[1311](https://www.adafruit.com/product/1311)|1|15.95|Locking mechanism between syringe plunger and actuator|
|M6 **x 10mm** Screw|Adafruit|[1311](https://www.adafruit.com/product/1311)|4|15.95|Holds deckware on CNC deck|

- Pliers
- Allen keys
- Super glue
- access to 3D printer, with PLA, PETG and 95A TPU filament


## Step 2: 3D-print Required Parts
Please print the following .STL files in the filament and with the supports specified in the Notes section. The editable Fusion 360 files for all these parts are provided in the `fusion files` folder, so this tool can be adapted to other types of labware, syringes, actuators or gantry systems.

|File|Filament|Print instructions|
|--|--|--|
|Plunger_TPU_Cap.stl|95A TPU|print with 5mm outer brim, 0.1mm spacing|
|Actuator_Holder.stl|PLA|Orient to the side, print with tree supports and extra painted supports in the hanging circular ridges|
|Plunger_Holder.stl|PETG|Print with tree support in the given orientation|
|Backlight_clamp.stl|PLA|Print with supports|
|Backlight_clamp_left.stl|PLA|Print with supports|
|Deckware_Holder.stl|PLA|Print with supports|
|Reservoir_Spacer.stl|PLA|Print upside down (in the orientation provided), with normal supports|
|Electronics box|PLA|Optional|


## Step 3: Assemble the CNC machine 
The Genmitsu 3014 CNC machine comes with all the parts needed to build the CNC Machine and a manual with step-by-step instructions. We find that the Grblcontrol (Candle) app is a user-friendly way to control the CNC machine, when starting off, capturing the locations of the labware and for troubleshooting.

## Step 4: Connect Actuator to microcontroller and power supply
_Parts and materials required:_
-	Wires (red and black) + solder/jumper wires
-	Small screw for tightening connector terminals
-	Connector terminal with barrel opening
-	metal rod with 2mm diameter

1. If using the optional electronics box, place the UNO R3 microcontroller at the bottom of the box, with the USB port aligned with the rectangular slot at the side of the box
2. Mount the motor shield above the microcontroller and ensure they are attached securely
3. To connect the power supply, insert a red wire into the positive (+) terminal and a black wire into the negative (-) terminal of the barrel connector. Tighten the screws and gently tug to confirm the wires are secured. Then, connect the red wire to the VIN pin and the black wire to the GND pins on the motor shield. <br>
**[INSERT WIRING DIAGRAM]**
   
4. Wire the actuator: connect the red (positive) wire to the A+ pin and the black (negative) wire to A- on the motor shield. Use wire connectors or solder extensions if needed to provide enough slack for movement of the actuator in the CNC gantry.
5. Plug the 12V power supply into the barrel connector.
6. Connect the microcontroller to your computer using the USB-C / USB-A cable. There should be a green light in the microcontroller when connected.


## Step 5: Connect dispenser with computer and code set-up
1.	Install [Python version 3.10.11](https://www.python.org/downloads/release/python-31011/) and a code editor (e.g., [Visual Studio Code](https://code.visualstudio.com/Download)), if they aren’t already installed.
2.	Download the `code` folder, which includes all the code used to control the dispenser. More details on the code structure and customization can be found in the folder’s `README.md`.
3.	Plug in the USB cables for the CNC machine, microcontroller (actuator) and USB camera. On Windows, use the device manager app to find the COM PORT number of the CNC machine and microcontroller and determine the camera index (usually 0 or 1) of the USB camera. More details and debugging tips can be found in `code/README.md`.
4.	Install the packages listed in `code/requirements.txt`.
5.	Edit the COM PORT numbers in the code when initializing the dispenser or individual components to run tests and workflows.
	  -  For example: `dispenser = Liquid_Dispenser(cnc_comport="COM4", camera_index=0, acutuator_comport=”COM3”)` or `cnc = CNC_Machine(com = "COM4") `
7.	Run `tests/act_ext.py` to check that the actuator is connected and working. This should retract and extend the plunger by ~0.5cm. If troubleshooting is needed, refer to `code/README.md`.

Additional details on the code design and functionality can be found in `code/README.md`.

## Step 6: Assemble Dispenser Tool Head
Tools and Materials needed:
-	Hex allen key
-	Pliers
-	1 Syringe + Needle
-	3D-Printed pieces: TPU padding, tool head and actuator_syringe_connector
-	Super-glue

1.	Place the actuator into the top of the tool head, with the actuator shaft aligned with the square hole in the holder. After it is inserted, check if the holes in the shaft are aligned with larger holes at the side of the holder. If not, use `act_ext.py` to move the actuator up or down using the retract() and extend() methods respectively.
   <img width="200" alt="2" src="https://github.com/user-attachments/assets/45d75311-2296-47b7-8b75-9df62e44e4a6" />

2.	Glue the TPU padding to the bottom of the syringe plunger. After it dries, insert the plunger into the syringe.
<img width="150" alt="3" src="https://github.com/user-attachments/assets/ffe0deb3-437f-4ebb-83b3-0956bda05e91" />

3.	Attach the actuator syringe connector (shown in orange) to the top of the syringe plunger.
<img width="150" alt="5" src="https://github.com/user-attachments/assets/d5d2c002-d74b-4678-87c7-10935f2a6e2c" />
<img width="300" alt="7" src="https://github.com/user-attachments/assets/5deb88d0-9c7c-41b5-81f2-d99f5ccbc72b" />

4.	Place the syringe inside the tool holder (shown in blue).
<img width="200" alt="8" src="https://github.com/user-attachments/assets/a39cc3ee-fd90-4d6f-8f80-d4c03b8e7e88" />
 
5.	Align the square at the top of the orange connector piece with the actuator shaft, then slowly push the plunger upwards until the holes in the connector are line up with holes in the actuator shaft.
<img width="350" alt="9" src="https://github.com/user-attachments/assets/9f59a5c9-05da-4742-b3d4-ba3f349f55b8" />

6.	Insert the screw through the aligned holes and tighten the nut to secure the actuator to the plunger. 
<img width="250" alt="10" src="https://github.com/user-attachments/assets/dd6c8f58-3463-474a-87d8-da53b8a07171" />
<img width="250" alt="11" src="https://github.com/user-attachments/assets/6eb70b54-99e4-45b1-a7ef-ffb16b5f46f3" /> <br>
The following is how it should look when this step is complete: <br>
<img width="300" height="768" alt="12" src="https://github.com/user-attachments/assets/4711ccec-19c9-44b6-b15e-8b50517a3bb9" />

7.	Add the holder cap and insert the holder into the CNC tool holder. The circular part of the tool head should sit slightly below the top of CNC tool holder.
<img width="200" alt="13" src="https://github.com/user-attachments/assets/f665dd76-7e55-4774-9b43-5f2e1d568981" />

8.	Extend the plunger using `act_ext.py` until the plunger is at the very bottom of the syringe. It is recommended to use intervals of 0.3 second extensions.
9.	Twist off the syringe cap and attach a new syringe needle by twisting it on.
10.	Thread the metal rod through the holes at the top of the holder and the actuator

## Step 7: Deck set-up and mount labware 
1.	Place the backlight on the CNC deck.
2.	Using an Allen key, use 2 M6 screws to attach the left and right backlight clamps to the CNC deck. Position them near the recommended locations, as placing screws close to the edges of the X and Y axes may risk damaging the system when the gantry moves.
3.	If you are using the given labware set-up, place the well plate in the slot that is higher, and place a liquid reservoir inside the 3D printed reservoir spacer and into the other slot. If using other labware, feel free to adapt the deck ware holder and location coordinates in `code/location_status.yaml`.

_🎉Congratulations you have finished setting up the hardware for the ultra-budget liquid dispenser!_

## ⚠️IMPORTANT NOTES: Things to watch out for when starting workflows
1. Ensure the metal rod at the top of the holder is in place; it keeps the actuator secured when moving
   <img width="300" alt="15" src="https://github.com/user-attachments/assets/c6f6f787-888d-412f-9ce0-08c39c77cc94" />

2. Ensure the camera is securely placed in the front of the tool head
   - Test its positionings using `cnc_camera_test.py` to make sure you don’t pick up the edges of the wells
   - Edit location_status.yaml, decrease the crop size or adjust the camera if needed
     
3.	Ensure the actuator is fully extended & plunger is at the bottom of the syringe. Since the position of the syringe is not tracked, pulling it too far up can break the dispenser.
     - If not, use `code\test\act_ext.py` to move the plunger

4.	It is recommended to **re-calibrate** the dispenser every 3 full 24-wellplates of experiments (**~1200** liquid transfers) and switch to a **new syringe** every 6 well plates of experiments (**~2000** liquid transfers).
     - For calibrations, run `volume_calibration.py` to calibrate the system for accurate liquid transfer

## Replacing the syringe
_Tools and Materials needed:_
-	Hex allen key
-	Pliers
-	New syringe
-	New syringe needle (optional)

1.	Remove tool head from the CNC holder and remove the cap.
2.	Move the syringe up so the screw and nut are aligned with the holes at the side of the holder using `act.retract()` or `act.extend()` in `act_ext.py`. It is recommended to use time intervals of 0.3 seconds. 
3.	Hold the screw in place using an Allen key and use pliers to unfasten the nut. Then, remove the screw.
    <img width="300" alt="17" src="https://github.com/user-attachments/assets/398d2f14-bc01-421c-9f2b-4adf513e4096" />

4.	Remove the orange connector pieces to release the old syringe from the actuator.
5.	To install the new syringe, follow the same steps in [step 6](#step-6-assemble-dispenser-tool-head) of this assembly guide.



