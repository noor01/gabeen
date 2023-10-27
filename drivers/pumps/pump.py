from abc import ABC, abstractmethod

class Pump(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
    
    @abstractmethod
    def handshake(self):
        pass
    
    @abstractmethod
    def initialize(self):
        pass
    
    @abstractmethod
    def set_rate(self,direction,rate):
        pass
    
    @abstractmethod
    def set_volume(self,volume):
        pass
    
    @abstractmethod
    def close(self,pump):
        pass