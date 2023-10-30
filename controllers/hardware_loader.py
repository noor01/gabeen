import json
import os
from ..drivers import *

class hardware_control():
    def __init__(self, system_name, protocol,imaging_params=None) -> None:
        self.system_name = system_name
        self.protocol = protocol
        self.imaging_params = imaging_params
        self.initialize_hardware()

    def initialize_hardware(self):
        # Define file paths
        experiment_file = f"protocols/{self.system_name}/{self.protocol}/experiment.json"
        com_file = f"system-files/{self.system_name}/comports.json"

        # Check if files exist
        if not os.path.exists(experiment_file):
            raise FileNotFoundError(f"{experiment_file} not found")
        if not os.path.exists(com_file):
            raise FileNotFoundError(f"{com_file} not found")

        # Read files
        self.experiment = json.load(open(experiment_file))
        self.comports = json.load(open(com_file))
        
        # Check if microscope is needed for this protocol.
        use_microscope = False
        for step, step_info in self.experiment.items():
            if step_info["step_type"] == 'image':
                use_microscope = True
                break
        
        # Initialize hardware
        self.hardware = {}
        for hardware_name, hardware_info in self.comports.items():
            if hardware_info['hardware_type'] == "microscope" and not use_microscope:
                continue
            hardware_type = hardware_info["hardware_type"]
            if hardware_type == "valve":
                if hardware_info["hardware_manuracturer"] == "precigenome":
                    self.hardware[hardware_name] = precigenome(hardware_info["COM"])
                elif hardware_info["hardware_manuracturer"] == "hamilton":
                    self.hardware[hardware_name] = hamilton(hardware_info["COM"])
                else:
                    raise ValueError(f"Hardware manufacturer {hardware_info['hardware_manuracturer']} not recognized")

            elif hardware_type == "pump":
                if hardware_info["hardware_manuracturer"] == "new_era_peristaltic":
                    self.hardware[hardware_name] = new_era_peristaltic(hardware_info["COM"])
                elif hardware_info["hardware_manuracturer"] == "new_era_syringe":
                    self.hardware[hardware_name] = new_era_syringe(hardware_info["COM"])
                else:
                    raise ValueError(f"Hardware manufacturer {hardware_info['hardware_manuracturer']} not recognized")

            elif hardware_type == "microscope" and use_microscope:
                if hardware_info["hardware_manuracturer"] == "ONI":
                    self.hardware['microscope'] = ONI(self.imaging_params,self.system_name)
                
            elif hardware_type == "liquid_handler":
                raise NotImplementedError("Liquid handler not implemented yet")
                
            else:
                raise ValueError(f"Hardware type {hardware_type} not recognized")
        