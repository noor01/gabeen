import serial

class SerialCom:
    """
    A class representing a serial communication interface.

    Args:
        serial_port (str): The serial port to connect to. Defaults to None.
        baudrate (int): The baud rate for the serial communication. Defaults to 9600.
        bytesize (int): The number of data bits. Defaults to serial.EIGHTBITS.
        parity (str): The parity setting. Defaults to serial.PARITY_NONE.
        stopbits (float): The number of stop bits. Defaults to serial.STOPBITS_ONE.
        timeout (float): The timeout value in seconds. Defaults to None.

    Attributes:
        serial_port (str): The serial port to connect to.
        baudrate (int): The baud rate for the serial communication.
        bytesize (int): The number of data bits.
        parity (str): The parity setting.
        stopbits (float): The number of stop bits.
        timeout (float): The timeout value in seconds.
    """

    def __init__(self, serial_port=None, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        
    def open(self):
        """
        Opens the serial communication.

        This method initializes the serial communication with the specified settings.
        """
        self.serial = serial.Serial(port=self.serial_port,
                                    baudrate=self.baudrate,
                                    bytesize=self.bytesize,
                                    parity=self.parity,
                                    stopbits=self.stopbits,
                                    timeout=self.timeout)
        
    def close(self):
        """
        Closes the serial communication.

        This method closes the serial communication.
        """
        self.serial.close()
        
    def write(self, cmd):
        """
        Writes a command to the serial port and returns the output.

        Args:
            cmd (str): The command to write to the serial port.

        Returns:
            str: The output received from the serial port.
        """
        self.open()
        self.serial.write(cmd.encode('ascii'))
        output = self.serial.readline()
        self.close()
        return output
class SerialCom:
    def __init__(self,serial_port=None, baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout
        
    def open(self):
        self.serial = serial.Serial(port = self.serial_port,
                                    baudrate = self.baudrate,
                                    bytesize = self.bytesize,
                                    parity = self.parity,
                                    stopbits = self.stopbits,
                                    timeout = self.timeout)
    def close(self):
        self.serial.close()
        
    def write(self,cmd):
        self.open()
        self.serial.write(cmd.encode('ascii'))
        output = self.serial.readline()
        self.close()
        return output
