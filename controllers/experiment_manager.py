import pandas as pd
import time
import json
import os
from .fluid_control import fluid_control
from .hardware_loader import hardware_control
from utils import protocol_system_compiler
from tqdm.auto import tqdm

class experiment_manager():
    def __init__(self, system_name, protocol, experiment_name, imaging_params=None, delay_microscope_init=False, microscope_fov_start=0) -> None:
        """
        Initializes an ExperimentManager object.

        Args:
            system_name (str): Name of the system.
            protocol (str): Protocol to be used.
            imaging_params (dict, optional): Imaging parameters. Defaults to None.
            delay_microscope_init (bool, optional): Whether to delay microscope initialization. Defaults to False.
            microscope_fov_start (int, optional): Starting fov to skip to just for the first round that is run. Useful for resuming from a crashed experiment. Defaults to 0.
        """
        self.system_name = system_name
        self.protocol = protocol
        self.imaging_params = imaging_params
        protocol_system_compiler.compile_protocol(system_name, protocol) # first make sure system is properly configured
        self.hardware = hardware_control(self.system_name, self.protocol, self.imaging_params, delay_microscope_init)
        self.fluid_control = fluid_control(self.hardware.hardware, self.system_name, self.protocol)
        self.experiment_name = experiment_name
        self.delay_microscope_init = delay_microscope_init
        self.microscope_fov_start = microscope_fov_start
        self.runs_folder = f"../runs/{self.system_name}"
        self.experiment_folder = f"{self.runs_folder}/{self.experiment_name}"
        self.create_experiment_folder()
        self.read_protocol()
        self.first_round = True
        self.microscope_initialized = self.hardware.microscope_initialized

    def create_experiment_folder(self):
        if not os.path.exists(self.runs_folder):
            os.mkdir(self.runs_folder)
        if not os.path.exists(self.experiment_folder):
            os.mkdir(self.experiment_folder)
            if self.delay_microscope_init:
                print(f"Please add config.json, overview.tiff and optional fov_positions.json to {self.experiment_folder}")
                
    def read_protocol(self):
        # Define file paths
        experiment_file = f"../protocols/{self.system_name}/{self.protocol}/experiment.json"
        # Check if files exist
        if not os.path.exists(experiment_file):
            raise FileNotFoundError(f"{experiment_file} not found")
        self.experiment = json.load(open(experiment_file))
        self.experiment = {int(k):v for k,v in self.experiment.items()}
        self.steps = list(self.experiment.keys())
        
        # add some kind of massive double checking that all hardware and protocol configs are setup properly
        
    def initialize_microscope(self):
        self.hardware.initialize_microscope()
        self.microscope_initialized = True
        
    def run_experimental_step(self,step):
        step_type = self.experiment[step]["step_type"]
        if step_type == "image":
            if self.microscope_initialized == False:
                raise ValueError("Microscope not initialized")
            else:
                pass
            filename = self.experiment[step]["filename"]
            if self.first_round and self.microscope_fov_start > 0:
                self.first_round = False
                self.hardware.hardware["microscope"].full_acquisition(filename,skip_to=self.microscope_fov_start)
            else:
                self.hardware.hardware["microscope"].full_acquisition(filename)
        elif step_type == "fluid":
            self.fluid_control.run_protocol_step(step)
        elif step_type == "wait":
            time.sleep(int(self.experiment[step]["wait_time"]))
        elif step_type == "user_action":
            raise NotImplementedError("User action not implemented")
        elif step_type == "compute":
            raise NotImplementedError("Compute step not implemented")
        else:
            raise ValueError(f"Step type {step_type} not recognized")
        
        if self.experiment[step]["slack_notify"] == True:
            self.slack_notify(f'Completed step #{step}')
        print(f"Completed step #{step}")
            
    def execute_all(self,skip_to_step=None):
        if skip_to_step is not None:
            self.steps = self.steps[self.steps.index(skip_to_step):]
        for step in tqdm(self.steps):
            self.run_experimental_step(step)
        print("Experiment complete!")

