import os
import json
import serial.tools.list_ports

# Step 1: Map existing hardware attached via COM ports using the pyserial library.
ports = serial.tools.list_ports.comports()
existing_hardware = {}
for port, desc, hwid in sorted(ports):
    existing_hardware[hwid] = port

# Step 2: Query the user for a name for the system. Create a folder in ../system-files with the system name if said folder doesn't exist already.
system_name = input("Enter a name for the system: ")
system_folder_path = f"../system-files/{system_name}"
if not os.path.exists(system_folder_path):
    os.makedirs(system_folder_path)

# Step 3-5: Perpetually query the user to enter a name for a new piece of hardware. User plugs in the new hardware, the script automatically detects the the COM port that was plugged in. Add the hardware name (hardware ID) as key and COM port value as the value to a nested dictionary in the json file in ../system-files/{system_name}/comports.json. Create the json file if it doesn't already exist. If user enters 0, exit.
comports_file_path = f"{system_folder_path}/comports.json"
if os.path.exists(comports_file_path):
    with open(comports_file_path, "r") as f:
        comports = json.load(f)
else:
    comports = {}

while True:
    hardware_name = input("Enter a name for the new piece of hardware (enter 0 to exit): ")
    if hardware_name == "0":
        break
    print("Please plug in the new hardware...")
    while True:
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            if hwid not in existing_hardware:
                existing_hardware[hwid] = port
                comports[hardware_name] = {'COM':port}
                with open(comports_file_path, "w") as f:
                    json.dump(comports, f, indent=4)
                print(f"{hardware_name} has been added with COM port {port}")
                break
        else:
            continue
        break
