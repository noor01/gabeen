import pandas as pd
import json
import os
from utils import loading_bar_wait
from drivers.microscopes import *
import pickle

class microscope_control():
    """
    Class representing a microscope control.

    Args:
        system_name (str): The name of the microscope system.
        experiment_name (str): The tag for the experiment.
        protocol (str): The protocol used for the experiment.
        delay_microscope_init (bool, optional): Whether to delay microscope initialization. Defaults to True.

    Attributes:
        system_name (str): The name of the microscope system.
        dataset_tag (str): The tag for the experiment.
        protocol (str): The protocol used for the experiment.
        microscope_initialized (bool): Whether the microscope is initialized.
        delay_microscope_init (bool): Whether to delay microscope initialization.
        comports (dict): Dictionary containing the comports information.
        imaging_params (dict): Dictionary containing the imaging parameters.
        microscope (ONI): Instance of the microscope.

    Raises:
        FileNotFoundError: If the required files are not found.
        ValueError: If no microscope is found in comports.json.
        NotImplementedError: If the microscope manufacturer is not implemented.
    """

    def __init__(self, system_name, experiment_name, protocol, delay_microscope_init=True) -> None:
        self.system_name = system_name
        self.dataset_tag = experiment_name
        self.protocol = protocol
        self.microscope_initialized = False
        self.delay_microscope_init = delay_microscope_init
        self.initialize_microscope()
        
    def initialize_microscope(self, overwrite_delay=False):
        """
        Initializes the microscope.

        Args:
            overwrite_delay (bool, optional): Whether to overwrite the delay for microscope initialization. Defaults to False.
        """
        if overwrite_delay:
            self.delay_microscope_init = False
        
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
            
    def initialize_oni(self, callib_af=True):
        """
        Initializes the ONI microscope.

        Args:
            callib_af (bool, optional): Whether to calibrate autofocus. Defaults to True.
        """
        oni_config_path = f"../protocols/{self.system_name}/{self.protocol}/oni_params.pkl"
        
        with open(oni_config_path, 'rb') as f:
            oni_config = pickle.load(f)
        
        if self.delay_microscope_init:
            print(f"Please add config.json, overview.tiff and optional files [fov_positions.json, auxiliary_oni_config.json] to {oni_config_path}")
            return
        else:
            self._initialize_oni(oni_config_path, oni_config, callib_af)
        
    def _initialize_oni(self, config_json, config, callib_af=True):
        """
        Initializes the ONI microscope.

        Args:
            config_json (str): Path to the config.json file.
            config (dict): Dictionary containing the imaging parameters.
            callib_af (bool, optional): Whether to calibrate autofocus. Defaults to True.
        """
        self.imaging_params = {}
        
        # Check and load config.json
        if not os.path.exists(config_json):
            raise FileNotFoundError(f"{config_json} not found")
        
        self.imaging_params = config
        self.microscope = ONI(self.dataset_tag, self.imaging_params, self.system_name)
        self.microscope_initialized = True
        
        if callib_af == True:
            pass
            
    def callibrate_autofocus(self):
        """
        Calibrates autofocus for the microscope.
        """
        self.microscope.callibrate_autofocus()
        
    def estimate_acquisition_time(self, buffer=50):
        """
        Estimates the acquisition time for the microscope.

        Args:
            buffer (int, optional): Buffer time in milliseconds. Defaults to 50.

        Returns:
            float: Estimated acquisition time in seconds.
        """
        zs = len(self.microscope.relative_zs)
        positions = len(self.microscope.positions)
        raw_nFrames = zs * positions
        im_steps = len(self.microscope.light_program)
        exposures = self.microscope.exposure_program
        time = 0
        
        for i in range(im_steps):
            time += (exposures[i] + buffer) * raw_nFrames  # in milliseconds
        
        time = time / 1000  # in seconds
        return time