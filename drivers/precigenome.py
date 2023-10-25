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
import serial
from Library.Hardware.Precigenome.PGValve import PGValve
import time
import os
# ----------------------------------------------------------------------------------------
# HamiltonMVP Class Definition
# ----------------------------------------------------------------------------------------
class precigenome():
    def __init__(self,serial_port,mode='SDK'):
        self.mode = mode
        #serial_port is a list of serial ports, in order of pump number
        self.ser = int(serial_port.replace('COM',''))
        self.valve = PGValve(serial_number=self.ser) # use automode to find the valve

    # ------------------------------------------------------------------------------------
    # Quick handshake function to aid in valve autodetection for AOTD.
    # Only use for single serial port!!!
    # ------------------------------------------------------------------------------------
    def handshake(self):
        resp = self.valve.getversion()
        if len(resp) > 0:
            return True
        else:
            return False
    
    def initialize_valve(self):
        self.valve.reset()
        
    # ------------------------------------------------------------------------------------
    # Quick function for changing valve position: automatically determines shortest
    # path turn. Will spit out an error if MVP not properly setup
    # ------------------------------------------------------------------------------------
    def valve_switch(self,valve):
        self.valve.switchto(valve)
        return

    # Not yet supported
    def initialize_daisychain(self):
        print("Not yet supported... in development")
        return
        print('in progress')

        #Create a dictionary for reagent number : valve ser, valve number, MVP number in chain

        self.valve_codebook = {}
        start = 1
        stop = self.max_valves
        MVP_num = 1
        if len(self.ser) > 1:
            second_last_ser = self.ser[-2]
        elif len(self.ser) == 1:
            second_last_ser = self.ser[-1]
            stop = stop + 1
        for ser in self.ser:
            valve = 1
            for reagent in range(start,stop):
                self.valve_codebook.update({reagent: [ser,valve,MVP_num]})
                valve = valve+1
            start = start + (self.max_valves - 1)
            if ser != second_last_ser:
                stop = stop + (self.max_valves - 1)
            elif ser == second_last_ser:
                stop = stop + self.max_valves
            MVP_num = MVP_num + 1
        print("Created valve address map")
        print("MVP valve controllers initialized successfully")

    def fluid_switch (self, reagent_num):
       self.valve_switch(reagent_num)

    def close(self):
        self.valve.close()


#
# The MIT License
#
# Copyright (c) 2018 Yeo Lab, University of California, San Diego
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
