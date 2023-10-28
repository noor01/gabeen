import pandas as pd
import json
import os
from .fluid_control import fluid_control
from .hardware_loader import hardware_control

class experiment_manager():
    def __init__(self,system_name, protocol,imaging_params=None) -> None:
        self.system_name = system_name
        self.protocol = protocol
        self.imaging_params = imaging_params
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
        
    def run_experimental_step(self,step):
        step_type = self.experiment[step]["step_type"]
        if step_type == "image":
            
            
            self.hardware.hardware["microscope"].acqufire_image()
        elif step_type == "fluid":
            self.fluid_control.run_fluid_step(step)
        elif step_type == "wait":
            self.hardware.hardware["ONI"].wait(self.experiment[step]["wait_time"])
        else:
            raise ValueError(f"Step type {step_type} not recognized"