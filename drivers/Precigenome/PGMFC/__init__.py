# -*- coding: utf-8 -*-
"""Module for communicating with Fluigent MFCS, MFCS-EZ and PX devices"""
# from . import control_c as controller
from Precigenome.PGMFC import control_c as controller

# from . import utils
from Precigenome.PGMFC import utils
# from .exceptions import MFCS_NoMFCS, MFCS_NoChannel, MFCS_OutOfRange
from Precigenome.PGMFC.exceptions import MFCS_NoMFCS, MFCS_NoChannel, MFCS_OutOfRange

class PGMFC(object):
    """Represents an MFCS or MFCS-EZ instrument, allowing the user to send
    commands and read values from the device"""

    @staticmethod
    def detect():
        """Returns a list containing the serial numbers of all available PG-MFC-Light devices"""
        print('detect start...')
        c_error, list_mfcs = controller.mfcs_detect()
        c_error, list_mfcstz = controller.mfcstz_detect()
        return list_mfcs + list_mfcstz

    def __init__(self, serial_number=0):
        """Creates an object that respresents the PG-MFC-Light device"""
        # Check if there are devices connected, and raise an exception if not
        # print 'PGMFC __init__'
        available_devices = PGMFC.detect()
        if not available_devices:
            utils.parse_error(1)
        if serial_number != 0 and serial_number not in available_devices:
            utils.parse_error(1)

        if serial_number == 0:
            serial_number = available_devices[0]
        # print 'Open USB connection  COM', serial_number
        # Open USB connection
        # self.__handle = controller.mfcs_initialization(serial_number)
        if (serial_number < 100):  # port id < 10 mfcs
            self.__handle = controller.mfcs_initialization(serial_number)
        else:  # mfcstz
            self.__handle = controller.mfcstz_initialization(serial_number)

        if not self.__handle:
            self.__handle = controller.mfcstz_initialization(serial_number)
            if not self.__handle:
                utils.parse_error(2)
        try:
            self.__create_channels()
        except:
            controller.mfcs_close(self.__handle)
            self.__handle = 0
            raise

    def __create_channels(self):
        """Creates a list of the PG-MFC-Light channels. A channel is represented by the
        Channel nested class."""
        self.__channels = []
        for index in range(self.sources):
            self.__channels.append(self.Channel(self, index + 1))

    def __iter__(self):
        """Allows iterating over the PG-MFC-Light channels in a for loop"""
        for c in self.__channels:
            yield c
            
    @property
    def sources(self):
        c_error, channels = controller.mfcs_getchannelscount(self.__handle)
        utils.parse_error(c_error)
        return channels

    @property
    def n_channels(self):
        """Number of pressure channels on the instrument"""
        return len(self.__channels)

    def close(self):
        """terminates threads and deallocates memory used by the MFCS session"""
        if self.__handle != 0:
            controller.mfcs_close(self.__handle)
            self.__handle = 0

        return
    
    def firmware_version(self):
        """read firmware version"""
        if self.__handle != 0:
            c_error, version = controller.mfcs_firmwareversion(self.__handle)
            utils.parse_error(c_error)
            return version
        else:
            utils.parse_error(1)
        return None

    def monitor_start(self, span=100):
        """start reading sensor data.
        span is the interval between two queries. ms"""
        return controller.mfcs_monitor_start(self.__handle, span=span)

    def monitor_stop(self):
        """stop reading sensor data"""
        return controller.mfcs_monitor_stop(self.__handle)

    def stopEmergency(self):
        """terminates the MFCS from running"""
        return controller.mfcs_stopEmergency(self.__handle)

    def getmoduleid(self, channel):
        """read module id"""
        c_error, mid = controller.mfcs_getmoduleid(self.__handle, channel)
        utils.parse_error(c_error)
        return mid

    def setmoduleid(self, mid, channel):
        """set module id, channel(1 2) channel(3 4) same id"""
        c_error = controller.mfcs_setmoduleid(self.__handle, mid, channel)
        utils.parse_error(c_error)

    def purge_on(self, channel_number, external=True):
        """start pump"""
        c_error = controller.mfcs_purge_on(self.__handle, channel_number, external)
        utils.parse_error(c_error)

    def purge_off(self, channel_number, external=True):
        """stop pump"""
        c_error = controller.mfcs_purge_off(self.__handle, channel_number, external)
        utils.parse_error(c_error)

    def set_params(self, channel, type=1, peak=2.0, trough=2.0, period=10, duty=0.25, runtime=50,
                    bNormalOpen=False):
        """Changes the setpoint for the channel's pressure output"""
        if type > 1 and runtime >= 65000:
            raise MFCS_OutOfRange("runtime is 1 - 65000 s for type{}. {} is \
                             out of range".format(type, peak))
        if type > 1 and (duty >= 99.9 or duty < 0.01):
            raise MFCS_OutOfRange("duty is 0.01 - 99.9 for this type. {} is \
                             out of range".format(duty))
        c_error = controller.mfcs_set_params(self.__handle, channel,
                                             type, peak, trough, period, duty, runtime, bNormalOpen)
        utils.parse_error(c_error)

    def set_params_flowrate(self, channel, type=1, peak=100, trough=50, period=10, duty=50.0, runtime=50,
                    bNormalOpen=False):
        """Changes the setpoint for the channel's liquid fowrate. works if a flowmeter is connected to PFMFC."""
        if type > 1 and runtime >= 65000:
            raise MFCS_OutOfRange("runtime is 1 - 65000 s for type{}. {} is \
                             out of range".format(type, peak))
        if type > 1 and (duty >= 99.9 or duty < 0.01):
            raise MFCS_OutOfRange("duty is 0.01 - 99.9 for this type. {} is \
                             out of range".format(duty))
        c_error = controller.mfcs_set_params_flowrate(self.__handle, channel,
                                             type, peak, trough, period, duty, runtime, bNormalOpen)
        utils.parse_error(c_error)

    def get_pressure(self, channel_number):
        """Reads the current pressure measurement on the channel"""
        c_error, pressure, timestamp = \
            controller.mfcs_cur_pressure(self.__handle, channel_number)
        utils.parse_error(c_error)
        return pressure, timestamp

    def get_airflowrate(self, channel_number):
        """Reads the current pressure measurement on the channel"""
        c_error, flowrate, timestamp = \
            controller.mfcs_cur_airflowrate(self.__handle, channel_number)
        utils.parse_error(c_error)
        return flowrate, timestamp

    def get_liquidflowrate(self, channel_number):
        """Reads the current liquid flowrate measurement on the channel"""
        c_error, flowrate, timestamp = \
            controller.mfcs_cur_liquidflowrate(self.__handle, channel_number)
        utils.parse_error(c_error)
        return flowrate, timestamp

    def get_liquidflowtotalizer(self, channel_number):
        """Reads the current liquid flow totalizer on the channel"""
        c_error, flowtotalizer, timestamp = \
            controller.mfcs_cur_liquidflowtotalizer(self.__handle, channel_number)
        utils.parse_error(c_error)
        return flowtotalizer, timestamp

    def controlValves(self, channel, idValve, bOpen):
        """control valves"""
        c_error = controller.mfcs_controlValves(self.__handle, channel, idValve, bOpen)
        utils.parse_error(c_error)
        return

    def operateDigitalOutputs(self, idPort, itype, polarity, peroid=100, pulse=10):
        """operate digital outputs"""
        return controller.mfcs_operateDigitalOutputs(self.__handle, idPort, itype, polarity, peroid, pulse)

    def queryDigitalIOStates(self):
        """query current digital outputs states"""
        c_error, list_states = controller.mfcs_queryDigitalIOStates(self.__handle)
        utils.parse_error(c_error)
        return list_states

    def checkFlowmeterInfo(self, channel):
        """tell controller to check if the flowmeter is connected"""
        return controller.mfcs_checkFlowmeterInfo(self.__handle, channel)

    def queryFlowmeterInfo(self, channel):
        """tell controller to check if the flowmeter is connected, and wait for the check result."""
        c_error, connected, model = controller.mfcs_queryFlowmeterInfo(self.__handle, channel)
        utils.parse_error(c_error)
        return (connected, model)

    def queryRotaryAddress(self, switchType, mountID):
        """check is rotary valve exists"""
        c_error, connected = controller.mfcs_queryRotaryAddress(self.__handle, switchType, mountID)
        utils.parse_rotary_error(c_error)
        return connected

    def getRotaryOneCircleCount(self, switchType, mountID):
        c_error, onecirclecount = controller.mfcs_getRotaryOneCircleCount(self.__handle, switchType, mountID)
        utils.parse_rotary_error(c_error)
        return onecirclecount

    def rotaryReset(self, switchType, mountID):
        """reset"""
        c_error = controller.mfcs_rotaryReset(self.__handle, switchType, mountID)
        utils.parse_rotary_error(c_error)
        return

    def queryRotaryCurPos(self, switchType, mountID):
        """query current pos"""
        c_error, curpos = controller.mfcs_queryRotaryCurPos(self.__handle, switchType, mountID)
        utils.parse_rotary_error(c_error)
        return curpos

    def rotarySwitchTo(self, switchType, mountID, portID):
        """switch to X"""
        c_error =  controller.mfcs_rotarySwitchTo(self.__handle, switchType, mountID, portID)
        utils.parse_rotary_error(c_error)
        return
    
    def queryChannelStatus1(self):
        """start reading sensor data.
        span is the interval between two queries. ms"""
        return controller.mfcs_queryChannelStatus1(self.__handle)
    
    def queryChannelStatus2(self):
        """start reading sensor data.
        span is the interval between two queries. ms"""
        return controller.mfcs_queryChannelStatus2(self.__handle)
    
    def getCurChannelInfo(self):
        c_error, pumpStatus, runTime, waveForm, maxValue, minValue = controller.mfcs_getCurChannelInfo(self.__handle)
        # utils.parse_error(c_error)
        return pumpStatus, runTime, waveForm, maxValue, minValue

    def __repr__(self):
        return "PGMFCS With {} channels".format(len(self.__channels))

    def __getitem__(self, index):
        """Allow channel indexing from the class instance, as if it were
        a list or a dictionary"""
        try:
            i = int(index)
            if i < 1 or i > len(self.__channels):
                raise IndexError()
            return self.__channels[i - 1]
        except ValueError:
            raise MFCS_NoChannel("Channel index must be an integer {}"
                                 .format(len(self.__channels)))
        except IndexError:
            raise MFCS_NoChannel("Channel index is an integer from 1 to {}"
                                 .format(len(self.__channels)))

    def __del__(self):
        """Close the handle so that the shared library stops communicating
        with the instrument"""
        # If __init__ fails, __del__ will fail because the object will
        # not have the __handle attribute. But __init__ closes
        # the handle on error, so that is not a problem
        try:
            if self.__handle != 0:
                # print('mfcs_close')
                controller.mfcs_close(self.__handle)
            # print('PGMFC __del__')
        except:
            pass

    class Channel(object):
        """Represents an individual pressure outlet of the PGMFCS device.
        This class should not be instantiated directly.
        To obtain a Channel instance, initialize the corresponding instrument and then index it
        (e.g., channel = instrument[1])."""
        def __init__(self, instrument, channel_number):
            self.__instrument = instrument
            self.__channel_number = channel_number
            return

        def getmoduleid(self):
            """read module id"""
            return self.__instrument.getmoduleid(self.__channel_number)

        def setmoduleid(self, mid):
            """set module id, channel(1 2) channel(3 4) same id"""
            return self.__instrument.setmoduleid(mid, self.__channel_number)

        def purge_on(self, external):
            """start pump"""
            return self.__instrument.purge_on(self.__channel_number, external)

        def purge_off(self, external=True):
            """stop pump"""
            return self.__instrument.purge_off(self.__channel_number, external)

        def set_params(self, type=1, peak=2.0, trough=2.0, period=10, duty=0.25, runtime=50, bNormalOpen=False):
            return self.__instrument.set_params(self.__channel_number, type, peak, trough, period, duty, runtime,
                                                bNormalOpen)

        def controlValves(self, idValve, bOpen):
            """control valves"""
            return self.__instrument.controlValves(self.__channel_number, idValve, bOpen)

        def get_pressure(self):
            return self.__instrument.get_pressure(self.__channel_number)

        def get_airflowrate(self):
            return self.__instrument.get_airflowrate(self.__channel_number)

        def get_liquidflowrate(self):
            return self.__instrument.get_liquidflowrate(self.__channel_number)

        def get_liquidflowtotalizer(self):
            return self.__instrument.get_liquidflowtotalizer(self.__channel_number)

        @property
        def pressure(self):
            """Read the attribute to get the current pressure measured by the channel in psi"""
            return self.get_pressure()

        @property
        def airflowrate(self):
            """Read the attribute to get the current air flowrate measured by the channel in sccm"""
            return self.get_airflowrate()

        @property
        def liquidflowrate(self):
            """Read the attribute to get the current liquid flowrate measured by the connected flowmeter"""
            return self.get_liquidflowrate()

        @property
        def liquidflowtotalizer(self):
            """Read the attribute to get the current liquid flow totalizer measured by the connected flowmeter"""
            return self.get_liquidflowtotalizer()

        def checkFlowmeterInfo(self):
            """tell controller to check if the flowmeter is connected"""
            return self.__instrument.checkFlowmeterInfo(self.__channel_number)

        def queryFlowmeterInfo(self):
            """tell controller to check if the flowmeter is connected, and wait for the check result."""
            return self.__instrument.queryFlowmeterInfo(self.__channel_number)








