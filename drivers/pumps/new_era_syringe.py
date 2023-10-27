#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for serial interface with the New Era syringe pumps
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 01/24/2022
# noorsher2@gmail.com
#
# This code is part of the Yeo lab's setup for MERFISH and related microscopy
# fluidics.
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------------------------
import serial
from tqdm import tqdm
import time
from .pump import Pump
# ----------------------------------------------------------------------------------------
# New Era Class Definition
# ----------------------------------------------------------------------------------------
class new_era_syringe(Pump):
    def __init__(self,serial_port,diameter='8.585',syringe_limit=3):
        #serial port is the serial port that the pump is connected to
        self.ser = serial.Serial(port = serial_port,
                                 baudrate = 19200,
                                 timeout = 0.1)

        self.syringe_diams = {'3 ml BD':'8.585',
                            '10 ml BD':'14.60',
                            '30ml BD':'21.59'}
        self.syringe_limits = {'3 ml BD':3,
                            '10 ml BD':10,
                            '30ml BD':30}
        
        self.diameter = diameter
        self.syringe_limit = syringe_limit

        self.find_pump()
        self.prime_volume = 0.2

    # legacy function
    def get_diameter_from_user(self):
        print("What syringe are you using?")
        syringe = self.dialog.multiple_choice(list(self.syringe_diams.keys()))
        self.diameter = self.syringe_diams[syringe]
        self.syringe = syringe
        self.set_diameter(self.diameter)
    
    def serial_cmd(self,cmd):
        self.ser.write(cmd.encode('ascii'))
        output = self.ser.readline()
        return str(output)

    # quick handshake function to aid in autodetection of new era pump
    # WARNING: this assumes a default of 1/16 inch diameter is set for the ID of the tubing in the pump
    def handshake(self):
        output = self.get_diameter()
        if len(output) > 5 and 'DIA' not in output:
            return True
        else:
            return False

    def find_pump(self):
        tot_range = 10
        n = 0
        while True:
            self.pump = n
            output = self.get_diameter()
            if len(output) > 5 and 'DIA' not in output:
                break
            elif n > tot_range:
                #print("ERROR COULD NOT FIND PUMP")
                break
            else:
                n+=1
        #print("Pump found at " + str(self.pump))

    def pause_pump(self):
        cmd = '*STP\x0D'
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from pause_pump not understood')

    def stop(self):
        self.pause_pump()

    def set_rate(self,direction,rate):
        #set direction of flow; direction = dispense or withdraw
        # if incorrect direction given, will default to dispense direction
        if direction == 'dispense':
            dir_cmd = 'INF'
        elif direction == 'withdraw':
            dir_cmd = 'WDR'
        else:
            dir_cmd = 'INF'
        cmd = '%iDIR%s\x0D'%(self.pump,direction)
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_rate not understood')
        #set rate; input units are mL/min (MM)
        # max rate = 2 mL/min
        cmd = str(self.pump) + 'RAT' + str(round(rate,2)) + 'MM*\x0D'
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_rate not understood')

    def set_volume(self,volume):
        #set volume units to ml
        cmd = str(self.pump) + 'VOLML\x0D'
        output = self.serial_cmd(cmd)
        #set volume
        cmd = str(self.pump) + 'VOL' + str(round(volume,2)) + '\x0D'
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_volume not understood')

    def set_diameter(self,diameter):
        cmd = '%iDIA%s\x0D'%(self.pump,diameter)
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_diameter not understood')

    def get_diameter(self):
        #diameter is a string such as '1/16' which is 1/16 inch which is default diameter on the New Era pump
        cmd = '%iDIA\x0D'%(self.pump)
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from get_diameter not understood')
        return output

    def start(self):
        cmd = '%iRUN\x0D'%self.pump
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from start_pump not understood')

    def prime_pump(self):
        self.set_volume(self.prime_volume)
        # create small barrier of air to reduce risk of pump running with no room left during dispensing
        self.set_rate('WDR',2)
        self.start()
        wait_time = int((self.prime_volume/2)*60)
        print("Priming pump")
        for i in tqdm(range(0,wait_time)):
            time.sleep(1)
    def close(self):
        self.ser.close()