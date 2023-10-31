#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for serial interface with the New Era 1000 series Peristaltic pump (singular)
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 01/24/2022
# noorsher2@gmail.com
#
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------------------------
import serial
import time
import os
from .pump import Pump
# ----------------------------------------------------------------------------------------
# New Era Class Definition
# ----------------------------------------------------------------------------------------
class new_era_peristaltic(Pump):
    def __init__(self,serial_port):
        #serial port is the serial port that the pump is connected to
        self.initialize(serial_port)
        
    def initialize(self,serial_port):
        self.ser = serial.Serial(port = serial_port,
                                 baudrate = 19200,
                                 timeout = 0.1)
    
    #quick function for sending serial commands
    def serial_cmd(self,cmd):
        self.ser.write(cmd.encode('ascii'))
        output = self.ser.readline()
        return str(output)

    # quick handshake function to aid in autodetection of new era pump
    # WARNING: this assumes a default of 1/16 inch diameter is set for the ID of the tubing in the pump
    def handshake(self):
        self.find_pump()
        output = self.get_diameter()
        print(output)
        if "1/16" in str(output):
            return True
        else:
            return False

    def find_pump(self):
        tot_range = 10
        pumps = []
        for i in range(tot_range):
            output = self.serial_cmd('%iADR\x0D'%i)
            if output != "b''":
                pumps.append(i)
        #for use of singular pump, default address is 0, so just use that
        self.pump = 0
        return pumps

    def pause_pump(self):
        cmd = '%iSTP\x0D'%self.pump
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from stop_pump not understood')

    def stop(self):
        self.pause_pump()
        self.pause_pump()

    def set_rate(self,direction,rate):
        #set direction of flow; direction = dispense or withdraw
        cmd = '%iDIR%s\x0D'%(self.pump,direction)
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_rate not understood')
        #set rate; units are mL/min (MM)
        cmd = str(self.pump) + 'RAT' + str(round(rate,2)) + 'MM\x0D'
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_rate not understood')

    def set_volume(self,volume):
        #set volume units to ml
        cmd = '%iVOLML\x0D'
        output = self.serial_cmd(cmd)
        #set volume
        cmd = str(self.pump) + 'VOL' + str(round(volume,2)) + '\x0D'
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_volume not understood')

    def set_diameter(self,diameter):
        #diameter is a string such as '1/16' which is 1/16 inch which is default diameter on the New Era pump
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
        self.set_diameter('1/16')
        self.set_volume(1)
        self.set_rate('INF',5)
        self.start()

    def close(self):
        self.ser.close()