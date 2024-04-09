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
from ..serial_com import SerialCom
# ----------------------------------------------------------------------------------------
# New Era Class Definition
# ----------------------------------------------------------------------------------------
class new_era_peristaltic(Pump):
    """
    A class representing a New Era peristaltic pump.

    Attributes:
        ser (SerialCom): The serial communication object for the pump.

    Methods:
        __init__(self, serial_port): Initializes the pump object.
        initialize(self, serial_port): Initializes the serial communication with the pump.
        serial_cmd(self, cmd): Sends a serial command to the pump and returns the output.
        handshake(self): Performs a quick handshake to aid in autodetection of the pump.
        find_pump(self): Finds the available pumps connected to the serial port.
        pause_pump(self): Pauses the pump.
        stop(self): Stops the pump.
        set_rate(self, direction, rate): Sets the direction and rate of flow for the pump.
        set_volume(self, volume): Sets the volume for the pump.
        set_diameter(self, diameter): Sets the diameter of the tubing in the pump.
        get_diameter(self): Retrieves the diameter of the tubing in the pump.
        start(self): Starts the pump.
        prime_pump(self): Primes the pump with default settings.
        close(self): Closes the serial communication with the pump.
    """
    def __init__(self, serial_port):
        """
        Initializes the new_era_peristaltic object.

        Args:
            serial_port (str): The serial port that the pump is connected to.
        """
        self.initialize(serial_port)
        
    def initialize(self, serial_port):
        """
        Initializes the serial communication with the pump.

        Args:
            serial_port (str): The serial port that the pump is connected to.
        """
        self.ser = SerialCom(port=serial_port, baudrate=19200, timeout=0.1)
    
    def serial_cmd(self, cmd):
        """
        Sends a serial command to the pump and returns the output.

        Args:
            cmd (str): The serial command to send to the pump.

        Returns:
            str: The output received from the pump.
        """
        output = self.ser.write(cmd)
        return str(output)

    def handshake(self):
        """
        Performs a quick handshake to aid in autodetection of the pump.

        Returns:
            bool: True if the pump is detected, False otherwise.
        """
        self.find_pump()
        output = self.get_diameter()
        print(output)
        if "1/16" in str(output):
            return True
        else:
            return False

    def find_pump(self):
        """
        Finds the available pumps connected to the serial port.

        Returns:
            list: A list of pump addresses found.
        """
        tot_range = 10
        pumps = []
        for i in range(tot_range):
            output = self.serial_cmd('%iADR\x0D'%i)
            if output != "b''":
                pumps.append(i)
        #for use of singular pump, default address is 0, so just use that
        return pumps

    def pause_pump(self):
        """
        Pauses the pump.
        """
        cmd = '%iSTP\x0D'%0
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from stop_pump not understood')

    def stop(self):
        """
        Stops the pump.
        """
        self.pause_pump()
        self.pause_pump()

    def set_rate(self, direction, rate):
        """
        Sets the direction and rate of flow for the pump.

        Args:
            direction (str): The direction of flow (dispense or withdraw).
            rate (float): The rate of flow in mL/min.
        """
        cmd = '%iDIR%s\x0D'%(0,direction)
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_rate not understood')
        cmd = str(0) + 'RAT' + str(round(rate,2)) + 'MM\x0D'
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_rate not understood')

    def set_volume(self, volume):
        """
        Sets the volume for the pump.

        Args:
            volume (float): The volume in mL.
        """
        cmd = '%iVOLML\x0D'
        output = self.serial_cmd(cmd)
        cmd = str(0) + 'VOL' + str(round(volume,2)) + '\x0D'
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_volume not understood')

    def set_diameter(self, diameter):
        """
        Sets the diameter of the tubing in the pump.

        Args:
            diameter (str): The diameter of the tubing, e.g., '1/16'.
        """
        cmd = '%iDIA%s\x0D'%(0,diameter)
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from set_diameter not understood')

    def get_diameter(self):
        """
        Retrieves the diameter of the tubing in the pump.

        Returns:
            str: The diameter of the tubing.
        """
        cmd = '%iDIA\x0D'%(0)
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from get_diameter not understood')
        return output

    def start(self):
        """
        Starts the pump.
        """
        cmd = '%iRUN\x0D'%0
        output = self.serial_cmd(cmd)
        if '?' in output:
            print(cmd.strip()+' from start_pump not understood')

    def prime_pump(self):
        """
        Primes the pump with default settings.
        """
        self.set_diameter('1/16')
        self.set_volume(1)
        self.set_rate('INF',5)
        self.start()

    def close(self):
        """
        Closes the serial communication with the pump.
        """
        self.ser.close()