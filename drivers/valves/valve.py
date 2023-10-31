from abc import ABC, abstractmethod

class Valve(ABC):
    @abstractmethod
    def close(self):
        pass
    
    @abstractmethod
    def handshake(self):
        pass
    
    @abstractmethod
    def initialize(self):
        pass
    
    @abstractmethod
    def valve_switch(self,valve):
        pass