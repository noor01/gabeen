import pandas as pd
import time
import json
import os
from .fluid_control import fluid_control
from .hardware_loader import hardware_control
from ..utils import protocol_system_compiler

class experiment_manager():
    def __init__(self,system_name, protocol,imaging_params=None) -> None:
        self.system_name = system_name
        self.protocol = protocol
        self.imaging_params = imaging_params
        protocol_system_compiler(system_name,protocol) # first make sure system is properly configured
        self.hardware = hardware_control(self.system_name, self.protocol,self.imaging_params)
        self.fluid_control = fluid_control(self.hardware.hardware, self.system_name, self.protocol)
        self.read_protocol()
        
    def read_protocol(self):
        # Define file paths
        experiment_file = f"protocols/{self.system_name}/{self.protocol}/experiment.json"
        # Check if files exist
        if not os.path.exists(experiment_file):
            raise FileNotFoundError(f"{experiment_file} not found")
        self.experiment = json.load(open(experiment_file))
        self.steps = list(self.experiment.keys())
        
        # add some kind of massive double checking that all hardware and protocol configs are setup properly
        
    def jupyter_setup_imaging_params(self):
        # setup parameters such as FOV picking
        pass
        
    def run_experimental_step(self,step):
        step_type = self.experiment[step]["step_type"]
        if step_type == "image":
            filename = self.experiment[step]["filename"]
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
            
    def execute_all(self):
        for step in self.steps:
            self.run_experimental_step(step)
        
        print("Experiment complete!")