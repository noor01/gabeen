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
from .valve import Valve
from ..serial_com import SerialCom
# ----------------------------------------------------------------------------------------
# HamiltonMVP Class Definition
# ----------------------------------------------------------------------------------------
class hamilton(Valve):
    def __init__(self,serial_port):
        
        self.valve = SerialCom(port = serial_port,
                                baudrate = 9600,
                                bytesize = serial.SEVENBITS,
                                parity = serial.PARITY_ODD,
                                stopbits = serial.STOPBITS_ONE,
                                timeout = 0.1)
        #useful shortcuts for serial characters
        self.ack = ("\x06").encode('ascii')
        self.carriage_return = ('\x13').encode('ascii')
        self.negative_ack = ("\x21").encode('ascii')
        self.assign_addresses()
        self.initialize()

    #quick function for writing comands
    def serial_cmd(self,cmd):
        output = self.valve.write(cmd)
        return output
    # ------------------------------------------------------------------------------------
    # Define Device Addresses: Must be First Command Issued
    # ------------------------------------------------------------------------------------
    def assign_addresses(self):
        output = self.serial_cmd('1a\r')
    # ------------------------------------------------------------------------------------
    # Quick handshake function to aid in valve autodetection for AOTD.
    # Only use for single serial port!!!
    # ------------------------------------------------------------------------------------
    def handshake(self):
        output = self.serial_cmd('1a\r')
        if "1a" in str(output):
            return True
        else:
            return False
    # ------------------------------------------------------------------------------------
    # Waits until valve is finished moving before allowing program to continue
    # ------------------------------------------------------------------------------------
    def move_finished(self):
        address = 'a'
        dictionary = {"*": False,
                      "N": False,
                      "F": False,
                      "Y": True}
        output = self.serial_cmd('%sF\r' %(address))
        output = output.decode('ascii')[-2]
        done = dictionary[output]
        while done == False:
            time.sleep(0.5)
            output = self.serial_cmd('%sF\r' %(address))
            output = output.decode('ascii')[-2]
            done = dictionary[output]
    # ------------------------------------------------------------------------------------
    # Quick function for initializing an individual valve
    # ------------------------------------------------------------------------------------
    def initialize(self):
        address = 'a'
        output = self.serial_cmd('%sLXR\r' %(address))
        if '06' not in str(output):
            print("Unable to communicate to valve")
            print("Check that the serial cable is connected to the INPUT port")
            valve_status = False
        else:
            self.move_finished()
        if self.ack in output:
            # print("Valve initialized")
            valve_status = True
        elif self.negative_ack in output:
            print("Error in initializing valve ")
            valve_status = False
        else:
            print("Unknown internal error has occured")
            valve_status = False
        #return valve_status
    # ------------------------------------------------------------------------------------
    # Quick function for changing valve position: automatically determines shortest
    # path turn. Will spit out an error if MVP not properly setup
    # ------------------------------------------------------------------------------------
    def valve_switch(self,valve):
        address = 'a'
        #Poll if valve is busy. wait until it's not
        #self.move_finished(ser)
        #Ask what type of valve it is
        output = self.serial_cmd('%sLQT\r' %(address))
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
        output = self.serial_cmd('%sLQP\r' %(address))
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
        output = self.serial_cmd(address+dir_var+str(valve)+"R\r")
        if self.ack in output:
            turn_stat = True
        elif self.negative_ack in output:
            print("Error in valve change")
            turn_stat = False
        else:
            print("Unknown internal error has occured")
            turn_stat = False
        time.sleep(2)
        return turn_stat

    def close(self):
        for ser in self.ser:
            ser.close()