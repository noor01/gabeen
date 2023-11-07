import pandas as pd
import json
import os
from utils import loading_bar_wait
from drivers.microscopes import *

class microscope_control():
    def __init__(self, system_name, experiment_name, delay_microscope_init=True) -> None:
        self.system_name = system_name
        self.dataset_tag = experiment_name
        self.microscope_initialized = False
        self.delay_microscope_init = delay_microscope_init
        self.initialize_microscope()
        
    def initialize_microscope(self,overwrite_delay=False):
        if overwrite_delay:
            self.delay_microscope_init=False
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
            
        
        
    def initialize_oni(self,callib_af=True):
        config_json = f"../runs/{self.system_name}/{self.dataset_tag}/config.json"
        if self.delay_microscope_init:
            print(f"Please add config.json, overview.tiff and optional files [fov_positions.json, auxiliary_oni_config.json] to {config_json}")
            return
        else:
            self._initialize_oni(config_json,callib_af)
        
    def _initialize_oni(self,config_json,callib_af=True):
        self.imaging_params = {}
        # check and load config.json
        if not os.path.exists(config_json):
            raise FileNotFoundError(f"{config_json} not found")
        config = json.load(open(config_json))
        self.imaging_params['config'] = config
        # load auxiliary config if it exists
        aux_config_json = f"../runs/{self.system_name}/{self.dataset_tag}/auxiliary_oni_config.json"
        if os.path.exists(aux_config_json):
            aux_config = json.load(open(aux_config_json))
            self.imaging_params.update(aux_config)
        # load custom fov positions if they exist
        fov_path = f"../runs/{self.system_name}/{self.dataset_tag}/fov_positions.json"
        if not os.path.exists(fov_path):
            picked_fovs = False
        else:
            picked_fovs = True
        self.imaging_params['picked_fovs'] = picked_fovs
        if picked_fovs:
            self.imaging_params['fov_positions'] = json.load(open(fov_path))
        # load oni json
        oni_json = f'../system-files/{self.system_name}/oni_params.json'
        if not os.path.exists(oni_json):
            raise FileNotFoundError(f"{oni_json} not found")
        oni_json_params = json.load(open(oni_json))
        self.imaging_params['oni_json'] = oni_json_params
        
        self.microscope = ONI(self.dataset_tag,self.imaging_params,self.system_name)
        self.microscope_initialized = True
        if callib_af == True:
            self.microscope.callibrate_autofocus()
        
    def estimate_acquisition_time(self,buffer=50):
        zs = len(self.microscope.relative_zs)
        positions = len(self.microscope.positions)
        raw_nFrames = zs*positions
        im_steps = len(self.microscope.light_program)
        exposures = self.microscope.exposure_program
        time = 0
        for i in range(im_steps):
            time+= (exposures[i] + buffer) * raw_nFrames # in milliseconds
        time = time / 1000 # in seconds
        return time