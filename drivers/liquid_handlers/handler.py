from abc import ABC, abstractmethod

class Handler(ABC):
    @abstractmethod
    def run_protocol_step(self):
        pass