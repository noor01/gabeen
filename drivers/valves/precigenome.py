#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for serial interface with a series of PreciGenome rotary valves by USB
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 04/24/2023
# noorsher2@gmail.com
#
# This code is part of the Yeo lab's setup for MERFISH and related microscopy
# fluidics. The design of the fluidics system is inspired by Moffit et al. 2016.
# The code takes some inspiration from the Zhuang lab's storm_control software available
# on Github here: https://github.com/ZhuangLab/storm-control
# However, the code has been re-written to be more bare-bones and specific to Yeo Lab usage.
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------------------------
from .Precigenome.PGValve import PGValve
from .valve import Valve
import time

class precigenome(Valve):
    def __init__(self,serial_port):
        #handling serial port the way Precigenome SDK does
        self.ser = int(serial_port.replace('COM',''))
        self.valve = PGValve(serial_number=self.ser) # use automode to find the valve
        self.initialize()
        
    def handshake(self):
        resp = self.valve.getversion()
        if len(resp) > 0:
            return True
        else:
            return False
    
    def initialize(self):
        self.valve.switchto(1)
        time.sleep(2) # for some reason precigenome releases code lock too early
        
    # ------------------------------------------------------------------------------------
    # Quick function for changing valve position: automatically determines shortest
    # path turn. Will spit out an error if MVP not properly setup
    # ------------------------------------------------------------------------------------
    def valve_switch(self,valve):
        self.valve.switchto(valve)
        return

    def close(self):
        self.valve.close()
