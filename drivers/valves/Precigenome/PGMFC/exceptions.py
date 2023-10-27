"""This module contains the exceptions raised by the MFCS SDK, to enable 
application control via try/except blocks"""

from __future__ import print_function
import sys
import inspect

class MFCS_NoMFCS(Exception):
    """Raised if the specified MFCS is not connected to the computer"""

class MFCS_NoChannel(Exception):
    """Raised if the specified channel does not exist on the instrument"""

class MFCS_OutOfRange(ValueError):
    """Raised if a command (pressure, valve voltage or alpha) is out of range 
    for the specified channel"""
    
def doc():
    for c in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        print("{} \n    {}\n".format(c[0], c[1].__doc__))