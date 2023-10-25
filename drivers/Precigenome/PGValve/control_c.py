#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Wrapper for the shared library. Functions that return more than one value will
return a tuple containing all of the outputs in order, starting from the
error code.
"""

#"""
import sys
import platform
import os
import pkg_resources
import ctypes
from ctypes import byref, c_uint8, c_uint16, c_uint64, c_float, POINTER, c_bool, c_char_p, create_string_buffer

is_64_bits = sys.maxsize > 2 ** 32

if sys.platform.startswith("win32"):
    libclass = ctypes.CDLL
    lib_relative_path = ('shared', 'windows')
    if is_64_bits:
        lib_name = "pgvalve_64.dll"
    else:
        lib_name = "pgvalve_32.dll"
elif sys.platform.startswith("linux"):
    sharedObjectVersion = "2.0.0"
    libclass = ctypes.CDLL
    if is_64_bits:
        lib_name = "libpgvalve_64.so"
    else:
        lib_name = "libpgvalve_32.so"
    if platform.machine().lower().startswith('arm'):
        lib_relative_path = ('shared', 'pi')
    else:
        lib_relative_path = ('shared', 'linux')
else:
    #raise NotImplementedError("SDK not available on " + sys.platform)
    lib_relative_path = ('shared', 'linux')
    libclass = ctypes.CDLL
    lib_name = "libpgvalve_64.so"
#"""

resource_package = __name__
resource_path = '/'.join(lib_relative_path)

libpath = pkg_resources.resource_filename(resource_package, resource_path)
# print libpath, lib_name
lib = libclass(os.path.join(libpath, lib_name))
# print lib

lib.valves_detect.argtypes = [POINTER(c_uint16), POINTER(c_uint16), POINTER(c_uint16)]
lib.valves_initialize.argtypes = [c_uint16, c_uint16, c_uint16]
lib.valves_initialize.restype = c_uint64
lib.valves_close.argtypes = [c_uint64]
lib.valves_reset.argtypes = [c_uint64]
lib.valves_querycurpos.argtypes = [c_uint64, POINTER(c_uint16)]
lib.valves_switchto.argtypes = [c_uint64, c_uint16]

lib.valves_getonecirclecount.argtypes = [c_uint64, POINTER(c_uint16)]
lib.valves_getversion.argtypes = [c_uint64, POINTER(c_uint16)]
lib.valves_ispoweronreset.argtypes = [c_uint64, POINTER(c_bool)]
lib.valves_setpoweronreset.argtypes = [c_uint64, c_bool]
lib.valves_getmaxrpm.argtypes = [c_uint64, POINTER(c_uint16)]
lib.valves_setmaxrpm.argtypes = [c_uint64, c_uint16]
lib.valves_getresetspeed.argtypes = [c_uint64, POINTER(c_uint16)]
lib.valves_setresetspeed.argtypes = [c_uint64, c_uint16]
lib.valves_controlcommand.argtypes = [c_uint64, c_uint16, c_uint16, c_uint16, c_bool]
lib.valves_querycommand.argtypes = [c_uint64, c_uint16, POINTER(c_uint16), POINTER(c_uint16)]


def detect():
    serial_number_list = (ctypes.c_uint16 * 20)(*([0] * 20))
    valvetype_list = (ctypes.c_uint16 * 20)(*([0] * 20))
    mountid_list = (ctypes.c_uint16 * 20)(*([0] * 20))
    c_error = c_uint8(lib.valves_detect(serial_number_list, valvetype_list, mountid_list))
    serial_number_list = list(filter(None, serial_number_list))
    valvetype_list = list(filter(None, valvetype_list))
    mountid_list = list(filter(None, mountid_list))
    return (c_error.value, serial_number_list, valvetype_list, mountid_list)

def initialize(serial_number, valvetype, mounid):
    value = lib.valves_initialize(serial_number, valvetype, mounid)
    return c_uint64(value)

def close(handle):
    c_error = c_uint8(lib.valves_close(handle))
    return c_error.value

def queryaddress(handle):
    connected = c_uint16(0)
    c_error = c_uint8(lib.valves_queryaddress(handle, byref(connected)))
    return (c_error.value, connected.value)

def reset(handle):
    c_error = c_uint8(lib.valves_reset(handle))
    return c_error.value

def querycurpos(handle):
    pos = c_uint16(0)
    c_error = c_uint8(lib.valves_querycurpos(handle, byref(pos)))
    return (c_error.value, pos.value)

def switchto(handle, port=1):
    c_error = c_uint8(lib.valves_switchto(handle, c_uint16(port)))
    return c_error.value

def getonecirclecount(handle):
    channel = c_uint16(0)
    c_error = c_uint8(lib.valves_getonecirclecount(handle, byref(channel)))
    return (c_error.value, channel.value)

def getversion(handle):
    version = c_uint16(0)
    version2 = c_uint16(0)
    c_error = c_uint8(lib.valves_getversion(handle, byref(version), byref(version2)))
    return (c_error.value, version.value, version2.value)

def ispoweronreset(handle):
    isautoreset = c_bool(False)
    c_error = c_uint8(lib.valves_ispoweronreset(handle, byref(isautoreset)))
    return (c_error.value, isautoreset.value)

def setpoweronreset(handle, isautoreset):
    c_error = c_uint8(lib.valves_setpoweronreset(handle, c_bool(isautoreset)))
    return c_error.value

def getmaxrpm(handle):
    maxrpm = c_uint16(0)
    c_error = c_uint8(lib.valves_getmaxrpm(handle, byref(maxrpm)))
    return (c_error.value, maxrpm.value)

def setmaxrpm(handle, maxrpm):
    c_error = c_uint8(lib.valves_setmaxrpm(handle, c_uint16(maxrpm)))
    return c_error.value

def getresetspeed(handle):
    speed = c_uint16(0)
    c_error = c_uint8(lib.valves_getresetspeed(handle, byref(speed)))
    return (c_error.value, speed.value)

def setresetspeed(handle, speed):
    c_error = c_uint8(lib.valves_setresetspeed(handle, c_uint16(speed)))
    return c_error.value

def controlcommand(handle, cmd, para1, para2, bfactory):
    c_error = c_uint8(lib.valves_controlcommand(handle, c_uint16(cmd), c_uint16(para1), c_uint16(para2), c_bool(bfactory)))
    return c_error.value

def querycommand(handle, cmd):
    para1 = c_uint16(0)
    para2 = c_uint16(0)
    c_error = c_uint8(lib.valves_querycommand(handle, c_uint16(cmd), byref(para1), byref(para2)))
    return (c_error.value, para1.value, para2.value)
# endregion


