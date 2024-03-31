import serial

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
