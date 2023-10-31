import json
import os
from drivers import *

class hardware_control():
    def __init__(self, system_name, protocol, dataset_tag=None, imaging_params=None,delay_microscope_init=False) -> None:
        self.system_name = system_name
        self.protocol = protocol
        self.dataset_tag = dataset_tag
        self.microscope_initialized = False
        if imaging_params is None:
            self.imaging_params = {}
        else:
            self.imaging_params = imaging_params
        self.initialize_hardware(delay_microscope_init)

    def initialize_hardware(self,delay_microscope_init=False):
        # Define file paths
        experiment_file = f"../protocols/{self.system_name}/{self.protocol}/experiment.json"
        com_file = f"../system-files/{self.system_name}/comports.json"

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
                if hardware_info["hardware_manufacturer"] == "precigenome":
                    self.hardware[hardware_name] = precigenome(hardware_info["COM"])
                elif hardware_info["hardware_manufacturer"] == "hamilton":
                    self.hardware[hardware_name] = hamilton(hardware_info["COM"])
                else:
                    raise ValueError(f"Hardware manufacturer {hardware_info['hardware_manufacturer']} not recognized")

            elif hardware_type == "pump":
                if hardware_info["hardware_manufacturer"] == "new_era_peristaltic":
                    self.hardware[hardware_name] = new_era_peristaltic(hardware_info["COM"])
                elif hardware_info["hardware_manufacturer"] == "new_era_syringe":
                    self.hardware[hardware_name] = new_era_syringe(hardware_info["COM"])
                else:
                    raise ValueError(f"Hardware manufacturer {hardware_info['hardware_manufacturer']} not recognized")

            elif hardware_type == "microscope" and use_microscope and not delay_microscope_init:
                if hardware_info["hardware_manufacturer"] == "oni":
                    self.imaging_params['instrument_name'] = hardware_info['metadata']['instrument_name']
                    if self.dataset_tag is None:
                        raise ValueError("dataset_tag must be specified for ONI microscope")
                    self.hardware['microscope'] = ONI(self.dataset_tag,self.imaging_params,self.system_name)
                    self.microscope_initialized = True
                
            elif hardware_type == "liquid_handler":
                raise NotImplementedError("Liquid handler not implemented yet")
                
            else:
                raise ValueError(f"Hardware type {hardware_type} not recognized")
            
    def initialize_microscope(self):
        config_json = f"../runs/{self.system_name}/{self.dataset_tag}/config.json"
        if not os.path.exists(config_json):
            raise FileNotFoundError(f"{config_json} not found")
        config = json.load(open(config_json))
        self.imaging_params['config'] = config
        fov_path = f"../runs/{self.system_name}/{self.dataset_tag}/fov_positions.json"
        if not os.path.exists(fov_path):
            picked_fovs = False
        else:
            picked_fovs = True
        self.imaging_params['picked_fovs'] = picked_fovs
        if picked_fovs:
            self.imaging_params['fov_positions'] = json.load(open(fov_path))
        
        
        self.hardware['microscope'] = ONI(self.dataset_tag,self.imaging_params,self.system_name)
        self.microscope_initialized = True
        
