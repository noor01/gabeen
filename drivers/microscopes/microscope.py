from abc import ABC, abstractmethod

class Microscope(ABC):
    @abstractmethod
    def initialize(self):
        pass
    
    @abstractmethod
    def valve_switch(self,valve):
        pass