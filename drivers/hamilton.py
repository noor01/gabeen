#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for serial interface with a series of Hamilton MVP devices connected by USB
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 01/24/2022
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
import time
import os
# ----------------------------------------------------------------------------------------
# HamiltonMVP Class Definition
# ----------------------------------------------------------------------------------------
class hamilton():
    def __init__(self,serial_ports):
        #serial_port is a list of serial ports, in order of pump number
        self.ports = serial_ports
        self.ser = []
        #define attributes
        #initialize serial RS-232 connection with MVP daisy-chain
        for port in self.ports:
            ser = serial.Serial(port = port,
                                baudrate = 9600,
                                bytesize = serial.SEVENBITS,
                                parity = serial.PARITY_ODD,
                                stopbits = serial.STOPBITS_ONE,
                                timeout = 0.1)
            self.ser.append(ser)
        #useful shortcuts for serial characters
        self.ack = ("\x06").encode('ascii')
        self.carriage_return = ('\x13').encode('ascii')
        self.negative_ack = ("\x21").encode('ascii')

    #quick function for writing comands
    def serial_cmd(self,cmd,ser):
        ser.write(cmd.encode('ascii'))
        output = ser.readline()
        return output
    # ------------------------------------------------------------------------------------
    # Define Device Addresses: Must be First Command Issued
    # ------------------------------------------------------------------------------------
    def assign_addresses(self):
        for ser in self.ser:
            output = self.serial_cmd('1a\r',ser)
    # ------------------------------------------------------------------------------------
    # Quick handshake function to aid in valve autodetection for AOTD.
    # Only use for single serial port!!!
    # ------------------------------------------------------------------------------------
    def handshake(self):
        ser = self.ser[0]
        output = self.serial_cmd('1a\r',ser)
        if "1a" in str(output):
            return True
        else:
            return False
    # ------------------------------------------------------------------------------------
    # Waits until valve is finished moving before allowing program to continue
    # ------------------------------------------------------------------------------------
    def move_finished(self,ser):
        address = 'a'
        dictionary = {"*": False,
                      "N": False,
                      "F": False,
                      "Y": True}
        output = self.serial_cmd('%sF\r' %(address),ser)
        output = output.decode('ascii')[-2]
        done = dictionary[output]
        while done == False:
            time.sleep(0.5)
            output = self.serial_cmd('%sF\r' %(address),ser)
            output = output.decode('ascii')[-2]
            done = dictionary[output]
    # ------------------------------------------------------------------------------------
    # Quick function for initializing an individual valve
    # ------------------------------------------------------------------------------------
    def initialize_valve(self, ser):
        address = 'a'
        output = self.serial_cmd('%sLXR\r' %(address), ser)
        if '06' not in str(output):
            print("Unable to communicate to valve")
            print("Check that the serial cable is connected to the INPUT port")
            valve_status = False
        else:
            self.move_finished(ser)
        if self.ack in output:
            # print("Valve initialized")
            valve_status = True
        elif self.negative_ack in output:
            print("Error in initializing valve ")
            valve_status = False
        else:
            print("Unknown internal error has occured")
            valve_status = False
        return valve_status
    # ------------------------------------------------------------------------------------
    # Quick function for changing valve position: automatically determines shortest
    # path turn. Will spit out an error if MVP not properly setup
    # ------------------------------------------------------------------------------------
    def valve_switch(self,valve, ser):
        address = 'a'
        #Poll if valve is busy. wait until it's not
        #self.move_finished(ser)
        #Ask what type of valve it is
        output = self.serial_cmd('%sLQT\r' %(address), ser)
        valve_type = (output.decode('ascii'))[-2]
        #dict of number of ports available for each type
        type_dict = {"2": 8,
                     "3": 6,
                     "4": 3,
                     "5": 2,
                     "6": 2,
                     "7": 4},
        if valve <= type_dict[0][valve_type]:
            pass
        else:
            print("Not a valid port number. This valve only supports "
                  + str(type_dict[0][valve_type]) + " ports")
            turn_stat = False
            return turn_stat
        #Ask valve what the current position is
        output = self.serial_cmd('%sLQP\r' %(address), ser)
        old_val = int((output.decode('ascii'))[-2])
        #Determine fastest direction to turn
        diff = old_val*45 - valve*45
        if diff < 0:
            diff = diff + 360
        if diff > 180:
            dir_var = 'LP0'
        elif diff < 180:
            dir_var = 'LP1'
        else:
            dir_var = 'LP1'
        output = self.serial_cmd(address+dir_var+str(valve)+"R\r", ser)
        if self.ack in output:
            turn_stat = True
        elif self.negative_ack in output:
            print("Error in valve change")
            turn_stat = False
        else:
            print("Unknown internal error has occured")
            turn_stat = False
        return turn_stat

    def initialize_daisychain(self):
        #Assign addresses to all valves in daisy chain
        self.assign_addresses()
        for ser in self.ser:
            self.initialize_valve(ser)

        #Create a dictionary for reagent number : valve ser, valve number, MVP number in chain

        self.valve_codebook = {}
        start = 1
        stop = 8
        MVP_num = 1
        if len(self.ser) > 1:
            second_last_ser = self.ser[-2]
        elif len(self.ser) == 1:
            second_last_ser = self.ser[-1]
            stop = 9
        for ser in self.ser:
            valve = 1
            for reagent in range(start,stop):
                self.valve_codebook.update({reagent: [ser,valve,MVP_num]})
                valve = valve+1
            start = start + 7
            if ser != second_last_ser:
                stop = stop + 7
            elif ser == second_last_ser:
                stop = stop + 8
            MVP_num = MVP_num + 1
        print("Created valve address map")
        print("MVP valve controllers initialized successfully")

    def fluid_switch (self, reagent_num):
        #assume valve #8 is for connecting to next MVP in daisy chain
        ser_actual = self.valve_codebook[reagent_num][0]
        for ser in self.ser:
            if ser == ser_actual:
                continue
            else:
                self.valve_switch(8,ser)
        valve_num = self.valve_codebook[reagent_num][1]
        status = self.valve_switch(valve_num,ser_actual)

    def close(self):
        for ser in self.ser:
            ser.close()


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
