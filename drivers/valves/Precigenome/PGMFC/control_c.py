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
        lib_name = "pgmfc_64.dll"
    else:
        lib_name = "pgmfc_32.dll"
elif sys.platform.startswith("linux"):
    sharedObjectVersion = "2.0.0"
    libclass = ctypes.CDLL
    # lib_name = "pgmfc_x86_64.so"
    if is_64_bits:
        lib_name = "libpgmfc_64.so"
    else:
        lib_name = "libpgmfc_32.so"
    if platform.machine().lower().startswith('arm'):
        lib_relative_path = ('shared', 'pi')
    else:
        lib_relative_path = ('shared', 'linux')
else:
    raise NotImplementedError("SDK not available on " + sys.platform)
#"""

# import Lib.mfc_controls as lib
resource_package = __name__
resource_path = '/'.join(lib_relative_path)
# resource_path = r"F:\bitbucket\FlowSDK\pgmfc\x64\Release"
libpath = pkg_resources.resource_filename(resource_package, resource_path)
# print libpath, lib_name
lib = libclass(os.path.join(libpath, lib_name))

# print lib

lib.mfcs_detect.argtypes = [POINTER(c_uint16)]
lib.mfcs_initialization.argtypes = [c_uint16]
lib.mfcs_initialization.restype = c_uint64
lib.mfcstz_detect.argtypes = [POINTER(c_uint16)]
lib.mfcstz_initialization.argtypes = [c_uint16]
lib.mfcstz_initialization.restype = c_uint64

lib.mfcs_close.argtypes = [c_uint64]
lib.mfcs_getchannelscount.argtypes = [c_uint64, POINTER(c_uint16)]
lib.mfcs_frimwareversion.argtypes = [c_uint64, c_char_p]

lib.mfcs_monitor_start.argtypes = [c_uint64, c_uint16]
lib.mfcs_monitor_stop.argtypes = [c_uint64]

lib.mfcs_stopEmergency.argtypes = [c_uint64]

lib.mfcs_getmoduleid.argtypes = [c_uint64, POINTER(c_uint16), c_uint16]
lib.mfcs_setmoduleid.argtypes = [c_uint64, c_uint16, c_uint16]

lib.mfcs_set_params.argtypes = [c_uint64, c_uint16, c_uint16, c_float, c_float, c_float, c_float, c_float, c_bool]
lib.mfcs_set_params_flowrate.argtypes = [c_uint64, c_uint16, c_uint16, c_float, c_float, c_float, c_float, c_float, c_bool]

lib.mfcs_purge_on.argtypes = [c_uint64, c_uint16, c_bool]
lib.mfcs_purge_off.argtypes = [c_uint64, c_uint16, c_bool]

lib.mfcs_getCurPressure.argtypes = [c_uint64, c_uint16, POINTER(c_float), POINTER(c_uint16)]
lib.mfcs_getCurFlowrate.argtypes = [c_uint64, c_uint16, POINTER(c_float), POINTER(c_uint16)]
lib.mfcs_getCurFlowrate_Liquid.argtypes = [c_uint64, c_uint16, POINTER(c_float), POINTER(c_uint16)]
lib.mfcs_getCurFlowtotalizer.argtypes = [c_uint64, c_uint16, POINTER(c_float), POINTER(c_uint16)]

lib.mfcs_controlValves.argtypes = [c_uint64, c_uint16, c_uint16, c_bool]

lib.mfcs_operateDigitalOutputs.argtypes = [c_uint64, c_uint16, c_uint16, c_uint16, c_uint16, c_uint16]
lib.mfcs_queryDigitalIOStates.argtypes = [c_uint64, POINTER(c_uint16)]

lib.mfcs_checkFlowmeter.argtypes = [c_uint64, c_uint16]
lib.mfcs_queryFlowmeterInfo.argtypes = [c_uint64, c_uint16, POINTER(c_bool), c_char_p]

lib.mfcs_queryRotaryAddress.argtypes = [c_uint64, c_uint16, c_uint16, POINTER(c_bool)]
lib.mfcs_rotaryReset.argtypes = [c_uint64, c_uint16, c_uint16]
lib.mfcs_getOneCircleCount.argtypes = [c_uint64, c_uint16, c_uint16, POINTER(c_uint16)]
lib.mfcs_queryRotaryCurPos.argtypes = [c_uint64, c_uint16, c_uint16, POINTER(c_uint16)]
lib.mfcs_rotarySwitchTo.argtypes = [c_uint64, c_uint16, c_uint16, c_uint16]

lib.mfcs_queryChannelStatus1.argtypes = [c_uint64]
lib.mfcs_queryChannelStatus2.argtypes = [c_uint64]
lib.mfcs_getCurChannelInfo.argtypes = [c_uint64, POINTER(c_uint16), POINTER(c_uint16), POINTER(c_uint16), POINTER(c_float), POINTER(c_float)]

def mfcs_detect():
    serial_number_list = (ctypes.c_uint16 * 20)(*([0] * 20))
    c_error = c_uint8(lib.mfcs_detect(serial_number_list))
    serial_number_list = list(filter(None, serial_number_list))
    return (c_error.value, serial_number_list)

def mfcstz_detect():
    serial_number_list = (ctypes.c_uint16 * 20)(*([0] * 20))
    c_error = c_uint8(lib.mfcstz_detect(serial_number_list))
    serial_number_list = list(filter(None, serial_number_list))
    return (c_error.value, serial_number_list)


def mfcs_get_handler(serial_number):
    return c_uint64(lib.mfcs_get_handler(c_uint16(serial_number)))

def mfcs_initialization(serial_number):
    value = lib.mfcs_initialization(serial_number)
    return c_uint64(value)

def mfcstz_initialization(serial_number):
    value = lib.mfcstz_initialization(serial_number)
    return c_uint64(value)

def mfcs_close(handle):
    c_error = c_uint8(lib.mfcs_close(handle))
    return c_error.value

def mfcs_getchannelscount(handle):
    channels = c_uint16(0)
    c_error = c_uint8(lib.mfcs_getchannelscount(handle, byref(channels)))
    return (c_error.value, channels.value)

def mfcs_firmwareversion(handle):
    version = create_string_buffer(20)  # c_char_p('')
    c_error = c_uint8(lib.mfcs_frimwareversion(handle, version))
    return (c_error.value, version.value)

def mfcs_monitor_start(handle, span=100):
    c_error = c_uint8(lib.mfcs_monitor_start(handle, c_uint16(span)))
    return c_error.value

def mfcs_monitor_stop(handle):
    c_error = c_uint8(lib.mfcs_monitor_stop(handle))
    return c_error.value

def mfcs_stopEmergency(handle):
    c_error = c_uint8(lib.mfcs_stopEmergency(handle))
    return c_error.value

def mfcs_getmoduleid(handle, channel):
    mid = c_uint16(0)
    c_error = c_uint8(lib.mfcs_getmoduleid(handle, byref(mid), c_uint16(channel)))
    return (c_error.value, mid.value)

def mfcs_setmoduleid(handle, mid, channel):
    c_error = c_uint8(lib.mfcs_setmoduleid(handle, mid, channel))
    return (c_error.value)

def mfcs_purge_on(handle, channel, external=True):
    c_error = c_uint8(lib.mfcs_purge_on(handle, c_uint16(channel), c_bool(external)))
    return c_error.value

def mfcs_purge_off(handle, channel, external=True):
    c_error = c_uint8(lib.mfcs_purge_off(handle, c_uint16(channel), c_bool(external)))
    return c_error.value

def mfcs_set_params(handle, channel, type=1, peak=2.0, trough=2.0, period=10, duty=0.25,
                    runtime=50, bNormalOpen=False):
    c_error = c_uint8(lib.mfcs_set_params(handle, c_uint16(channel),
                                        c_uint16(type), c_float(peak),
                                        c_float(trough), c_float(period), c_float(duty),
                                        c_float(runtime), c_bool(bNormalOpen)))
    return c_error.value

def mfcs_set_params_flowrate(handle, channel, type=1, peak=100, trough=50, period=10, duty=0.25,
                    runtime=50, bNormalOpen=False):
    c_error = c_uint8(lib.mfcs_set_params_flowrate(handle, c_uint16(channel),
                                        c_uint16(type), c_float(peak),
                                        c_float(trough), c_float(period), c_float(duty),
                                        c_float(runtime), c_bool(bNormalOpen)))
    return c_error.value

def mfcs_controlValves(handle, channel, idvalve, bOpen):
    c_error = c_uint8(lib.mfcs_controlValves(handle, c_uint16(channel), c_uint16(idvalve), c_bool(bOpen)))
    return c_error.value

def mfcs_operateDigitalOutputs(handle, idPort, itype, polarity, peroid, pulse):
    c_error = c_uint8(lib.mfcs_operateDigitalOutputs(handle, c_uint16(idPort), c_uint16(itype),
                                                   c_uint16(polarity),
                                                   c_uint16(peroid), c_uint16(pulse)))
    return c_error.value

def mfcs_queryDigitalIOStates(handle):
    states_list = (ctypes.c_uint16 * 8)(*([0] * 8))
    c_error = c_uint8(lib.mfcs_queryDigitalIOStates(handle, states_list))
    states_list = list(states_list)
    # states_list = list(filter(None, states_list))
    return (c_error.value, states_list)

def mfcs_checkFlowmeterInfo(handle, channel):
    c_error = c_uint8(lib.mfcs_checkFlowmeterInfo(handle, c_uint16(channel)))
    return c_error.value

def mfcs_queryFlowmeterInfo(handle, channel):
    connected = c_bool(False)
    model = create_string_buffer(20)  # c_char_p('')

    c_error = c_uint8(lib.mfcs_queryFlowmeterInfo(handle, c_uint16(channel), byref(connected), model))
    return (c_error.value, connected.value, model.value)

# region rotary valves
def mfcs_queryRotaryAddress(handle, switchType, mountID):
    connected = c_bool(False)
    c_error =  c_uint8(lib.mfcs_queryRotaryAddress(handle, switchType, mountID, byref(connected)))
    return (c_error.value, connected.value)

def mfcs_rotaryReset(handle, switchType, mountID):
    c_error = c_uint8(lib.mfcs_rotaryReset(handle, switchType, mountID))
    return c_error.value

def mfcs_getRotaryOneCircleCount(handle, switchType, mountID):
    count = c_uint16(0)
    c_error = c_uint8(lib.mfcs_getOneCircleCount(handle, switchType, mountID, byref(count)))
    return (c_error.value, count.value)

def mfcs_queryRotaryCurPos(handle, switchType, mountID):
    curpos = c_uint16(0)
    c_error = c_uint8(lib.mfcs_queryRotaryCurPos(handle, switchType, mountID, byref(curpos)))
    return (c_error.value, curpos.value)

def mfcs_rotarySwitchTo(handle, switchType, mountID, portID):
    c_error =  c_uint8(lib.mfcs_rotarySwitchTo(handle, switchType, mountID, portID))
    return c_error.value
# endregion

# region read current sensor data.  timestamp, value
def mfcs_cur_pressure(handle, channel):
    pressure = c_float(0)
    timestamp = c_uint16(0)
    c_error = c_uint8(lib.mfcs_getCurPressure(handle, c_uint16(channel), byref(pressure), byref(timestamp)))
    return (c_error.value, pressure.value, timestamp.value)

def mfcs_cur_airflowrate(handle, channel):
    flowrate = c_float(0)
    timestamp = c_uint16(0)
    c_error = c_uint8(lib.mfcs_getCurFlowrate(handle, c_uint16(channel), byref(flowrate), byref(timestamp)))
    return (c_error.value, flowrate.value, timestamp.value)

def mfcs_cur_liquidflowrate(handle, channel):
    flowrate = c_float(0)
    timestamp = c_uint16(0)
    c_error = c_uint8(lib.mfcs_getCurFlowrate_Liquid(handle, c_uint16(channel), byref(flowrate), byref(timestamp)))
    return (c_error.value, flowrate.value, timestamp.value)

def mfcs_cur_liquidflowtotalizer(handle, channel):
    flowtotalizer = c_float(0)
    timestamp = c_uint16(0)
    c_error = c_uint8(lib.mfcs_getCurFlowtotalizer(handle, c_uint16(channel), byref(flowtotalizer), byref(timestamp)))
    return (c_error.value, flowtotalizer.value, timestamp.value)

def mfcs_queryChannelStatus1(handle):
    c_error = c_uint8(lib.mfcs_queryChannelStatus1(handle))
    return c_error.value

def mfcs_queryChannelStatus2(handle):
    c_error = c_uint8(lib.mfcs_queryChannelStatus2(handle))
    return c_error.value

def mfcs_getCurChannelInfo(handle):
    pumpStatus = c_uint16(0)
    runTime = c_uint16(0)
    waveForm = c_uint16(0)
    maxValue = c_float(0)
    minValue = c_float(0)
    c_error = c_uint8(lib.mfcs_getCurChannelInfo(
        handle, byref(pumpStatus),byref(runTime), byref(waveForm), byref(maxValue), byref(minValue)))
    return (c_error.value, pumpStatus.value, runTime.value, waveForm.value, maxValue.value, minValue.value)
# endregion


