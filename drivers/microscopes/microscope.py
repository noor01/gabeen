from abc import ABC, abstractmethod

class Microscope(ABC):
    @abstractmethod
    def initialize(self,params,system_name):
        pass
    
    @abstractmethod
    def callibrate_autofocus(self):
        pass
    
    @abstractmethod
    def get_stage_pos(self):
        pass
    
    @abstractmethod
    def move_xy(self,x,y):
        pass
    
    @abstractmethod
    def move_z(self,z):
        pass
    
    @abstractmethod
    def move_xy_autofocus(self,x,y):
        pass
    
    @abstractmethod
    def init_xy_pos(self):
        pass
    
    @abstractmethod
    def init_z_pos(self):
        pass
    
    @abstractmethod
    def reset_parameters(self,new_params):
        pass
    
    @abstractmethod
    def full_acquisition(self,nested_dir_names):
        pass
    
    @abstractmethod
    def camera_snapshot(self):
        pass
    
    @abstractmethod
    def shutdown(self): 
        pass