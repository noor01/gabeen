import pandas as pd
import json
import os
from utils import loading_bar_wait
from ..drivers.microscopes import *

class microscope_control():
    def __init__(self, system_name, experiment_name, delay_microscope_init=True) -> None:
        self.system_name = system_name
        self.experiment_name = experiment_name
        self.delay_microscope_init = delay_microscope_init
        self.initialize_microscope()
        
    def initialize_microscope(self):
        # Define file paths
        com_file = f"../system-files/{self.system_name}/comports.json"
        
        # Check if files exist
        if not os.path.exists(com_file):
            raise FileNotFoundError(f"{com_file} not found")
        
        # Read files
        self.comports = json.load(open(com_file))
        if 'microscope' not in self.comports.keys():
            raise ValueError("No microscope found in comports.json")
        if self.comports['microscope']['hardware_manufacturer'] == 'oni':
            self.initialize_oni()
        else:
            raise NotImplementedError(f"Microscope manufacturer {self.comports['microscope']['hardware_manufacturer']} not implemented")
            
        
        
    def initialize_oni(self):
        config_json = f"../runs/{self.system_name}/{self.dataset_tag}/config.json"
        if self.delay_microscope_init:
            print(f"Please add config.json, overview.tiff and optional fov_positions.json to {config_json}")
            return
        else:
            self._initialize_oni(config_json)
        
    def _initialize_oni(self,config_json):
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
        self.microscope = ONI(self.dataset_tag,self.imaging_params,self.system_name)
        self.microscope_initialized = True