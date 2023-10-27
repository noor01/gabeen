"""This module contains the exceptions raised by the MFCS SDK, to enable 
application control via try/except blocks"""

from __future__ import print_function
import sys
import inspect

class VALVES_InvalidType(Exception):
    """Raised if the specified Valve is not connected to the computer"""

class VALVES_AckError(Exception):
    """Raised if the Motor returns a error"""

class VALVES_Unknown(ValueError):
    """Raised if received an unknown error"""
    
def doc():
    for c in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        print("{} \n    {}\n".format(c[0], c[1].__doc__))