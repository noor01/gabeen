import json
import pandas as pd
import os
from .fluid_control import fluid_control
from .hardware_loader import hardware_control
from .microscope_control import microscope_control
from telemetry import slack_notify
from utils import protocol_system_compiler,loading_bar
from tqdm.auto import tqdm

class experiment_manager():
    def __init__(self, system_name, protocol, experiment_name, delay_microscope_init=False, microscope_fov_start=0) -> None:
        """
        Initializes an ExperimentManager object.

        Args:
            system_name (str): Name of the system.
            protocol (str): Protocol to be used.
            imaging_params (dict, optional): Imaging parameters. Defaults to None.
            delay_microscope_init (bool, optional): Whether to delay microscope initialization. Defaults to False.
            microscope_fov_start (int, optional): Starting fov to skip to just for the first round that is run. Useful for resuming from a crashed experiment. Defaults to 0.
        """
        self.initialize(system_name, protocol, experiment_name, delay_microscope_init, microscope_fov_start, hardware_init=True)

    def initialize(self, system_name, protocol, experiment_name, delay_microscope_init=False, microscope_fov_start=0, hardware_init=False):
        self.system_name = system_name
        self.protocol = protocol
        self.experiment_name = experiment_name
        self.delay_microscope_init = delay_microscope_init
        self.microscope_fov_start = microscope_fov_start
        protocol_system_compiler.compile_protocol(system_name, protocol) # first make sure system is properly configured
        if hardware_init == True:
            self.hardware_loader = hardware_control(self.system_name, self.protocol)
            self.fluid_control = fluid_control(self.hardware_loader.hardware,
                                               self.hardware_loader.pump_types,
                                               self.system_name,
                                               self.protocol)
            if self.hardware_loader.use_microscope:
                self.initialize_microscope()
        self.runs_folder = f"../runs/{self.system_name}"
        self.experiment_folder = f"{self.runs_folder}/{self.experiment_name}"
        self.create_experiment_folder()
        self.read_protocol()
        self.first_round = True
    
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
        self.microscope_control = microscope_control(self.system_name,self.experiment_name,self.delay_microscope_init)
        self.microscope_initialized = self.microscope_control.microscope_initialized
        
    def run_experimental_step(self,step):
        step_type = self.experiment[step]["step_type"]
        print(str(self.experiment[step]))
        if step_type == "image":
            if self.microscope_initialized == False:
                raise ValueError("Microscope not initialized")
            else:
                pass
            filename = self.experiment[step]['step_metadata']["filename"]
            if self.first_round and self.microscope_fov_start > 0:
                self.first_round = False
                self.microscope_control.microscope.full_acquisition(filename,skip_to=self.microscope_fov_start)
            else:
                self.microscope_control.microscope.full_acquisition(filename)
        elif step_type == "fluid":
            self.fluid_control.run_protocol_step(self.experiment[step])
        elif step_type == "wait":
            loading_bar.loading_bar_wait(int(self.experiment[step]['step_metadata']["wait_time"]))
        elif step_type == "user_action":
            raise NotImplementedError("User action not implemented")
        elif step_type == "compute":
            raise NotImplementedError("Compute step not implemented")
        else:
            raise ValueError(f"Step type {step_type} not recognized")
        
        if self.experiment[step]["slack_notify"] == True:
            try:
                slack_notify.msg(f'Completed step #{step}')
            except:
                pass
        print(f"Completed step #{step}")
            
    def execute_all(self,skip_to_step=None):
        print(f'Total estimated runtime: {self.estimate_total_time()}')
        if skip_to_step is not None:
            self.steps = self.steps[self.steps.index(skip_to_step):]
        for step in tqdm(self.steps):
            self.run_experimental_step(step)
        print("Experiment complete!")
        
    def display_experiment(self):
        print(pd.DataFrame(self.experiment).T)
        
    def display_fluids(self):
        print(self.fluid_control.fluids)


    def estimate_fluidics_time(self):
        time = 0 # in seconds
        for step in self.steps:
            if self.experiment[step]["step_type"] == "fluid":
                volume = float(self.experiment[step]['step_metadata']["volume"])
                speed = float(self.experiment[step]['step_metadata']["speed"])
                if self.fluid_control.path_mode == 'linear':
                    time += 60*volume/speed
                elif self.fluid_control.path_mode == 'bifurcated':
                    time += (60*volume/speed)*2
            elif self.experiment[step]["step_type"] == 'wait':
                time += int(self.experiment[step]['step_metadata']["wait_time"])
        return time / 60 # in minutes
    
    def estimate_imaging_time(self):
        time = 0
        for step in self.steps:
            if self.experiment[step]["step_type"] == "image":
                time += self.microscope_control.estimate_acquisition_time()
        return time / 60 # in minutes
    
    def estimate_total_time(self):
        time = 0
        if self.hardware_loader.use_microscope:
            time += self.estimate_imaging_time()
        time += self.estimate_fluidics_time()
        units = 'minutes'
        if time > 60:
            time = time / 60 # convert to hours
            units = 'hours'
        if time > 24:
            time = time / 24 # convert to days
            units = 'days'
        return f'{time} {units}'