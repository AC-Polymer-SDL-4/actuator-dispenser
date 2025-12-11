# Code set-up & User Guide

## Basic installation instructions:
1. Install [Python version 3.10.11](https://www.python.org/downloads/release/python-31011/) and a code editor (e.g., [Visual Studio Code](https://code.visualstudio.com/Download)), if they aren’t already installed.
2.	Download the `code` folder, which includes all the code used to control the dispenser. More details on the code structure and customization can be found in the folder’s `README.md`.
3.	Plug in the USB cables for the CNC machine, microcontroller (actuator) and USB camera. On Windows, use the device manager app to find the COM PORT number of the CNC machine and microcontroller and determine the camera index (usually 0 or 1) of the USB camera. More details and debugging tips can be found in `code/README.md`.
4.	Install the packages listed in `code/requirements.txt`.
5.	Edit the COM PORT numbers in the code when initializing the dispenser or individual components to run tests and workflows.
	  -  For example: `dispenser = Liquid_Dispenser(cnc_comport="COM4", camera_index=0, acutuator_comport=”COM3”)` or `cnc = CNC_Machine(com = "COM4")`

## Code Structure
The code is set up in a modular way, where there are separate classes controlling each of the components (e.g., the camera, actuator and CNC machine) a high-level dispenser class that orchestrates all these components. This structure makes it easy to add or switch the components in the dispenser (e.g., adding a pH probe to the tool head) and to reuse the code written for the existing components (like the CNC machine class for another CNC-based tool).
Here are highlighted functions within each of the classes:
|Component|Class Name|Key Functions|
|--|--|--|
|Camera|Camera|<ul><li>`capture_and_save()`: captures images using the camera and returns the file path</li><li>	`average_color_in_center()`: analyze images to determine color space coordinates</li></ul>|
|Actuator|ActuatorRemote| <ul><li>`retract()`: retract actuator to withdraw liquid</li><li>`extend()`: extend actuator to dispense liquid </li> </ul>|
|CNC Machine|CNC_Machine|<ul><li>`move_to_location()`: move tool head to a location saved in `locations_status.yaml`</li></ul>|
|Dispenser|Liquid_Dispenser|<ul><li>`dispense_between()`: transfer liquid from a source location to a destination location, with different liquid transfer parameters like syringe speed, buffer volume <ul> <li>Incorportates CNC movements to the locations and the actuator for liquid manipulation </li></ul></li> <li>`get_image_color()`: moves camera to the designated well to capture and analyze the images for color coordinates <ul><li>Incorportates CNC movements to the locations and the camera for image capture and analysis </li></ul> </li> </ul>|
 
 
## Example workflows
Some example workflows included are: 
1.	`Color_matching_workflow.py`: A self-driving workflow using Bayesian Optimization (BO) to match an unknown target color from red, blue and yellow solutions using visual feedback.
    - This workflow contains all the code for the physical actions and calls from `color_matching_optimizer.py` for BO tasks like initializing the BayBE campaign and getting new suggestions.
    - The data and images collected are in `data\color_matching`
    - Deck set-up: a reservoir with color solutions and water for rinsing the syringe and a 24-wellplate with 1mL of the unknown target color (a combination of the color solutions) in the top-left well in the wellplate.
      
**[Add IMAGE]**

## Troubleshooting connection issues
Connection issues – workflow isn’t running!:
1.	Make sure all components are plugged in (microcontroller, CNC machine (with the power switch on), optionally the backlight) and connected to the computer via USB (microcontroller, camera, CNC machine)
2.	Isolate which component isn’t working by running the test files:
  a. Edit the `com_port` value for the CNC machine and run ‘cnc_machine_test.py’, this should home the cnc machine. 
    - If there are permission_denied errors: make sure Candle is NOT open, and double check the comport number in device manager
  b.  Edit the `camera_index` value (usually 0 or 1) and run `Camera_test.py`, this should capture an image and save it to the output folder.
    - If there are initialization errors: change the camera_index, and check that you can access the camera using a camera app on your computer
  c.	Edit the `com_port` value in `act_ext.py` and run, this should retract and extend the actuator by ~0.5cm. There is also a sound when the actuator is moving.
    - If the actuator doesn’t move: 
      - check the microcontroller to see if it is connected (green light) 
      - run the test again and check if there is an orange light at A+ and A- when sending each of the commands – this means the motor shield is powered but power is not reaching the actuator
      - check the wiring to the actuator and make sure everything is connected
      - If there are no orange lights – this means the motor shield is not powered
      - Check the power supply to the actuator
      - Use a multimeter, in voltage mode to confirm whether power (12V) is supplied throughout the system…
