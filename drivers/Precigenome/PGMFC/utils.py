from .exceptions import MFCS_NoMFCS, MFCS_NoChannel

error_messages = {1: "PGMFC not connected",
                  2: "Fail Open Session",
                  3: "This channel does not exist on this PGMFC",

                  100: "Illegal Input",
                  101: "Invalid PGMFC",
                  200: "No response",
                  201: "No data found"
                  }

def parse_error(c_error):
    if c_error == 1:
        raise MFCS_NoMFCS(error_messages[c_error])
    if c_error == 3:
        raise MFCS_NoChannel(error_messages[c_error])
    if c_error == 2:
        print("\033[3;31m" + error_messages[c_error] + "\033[0m")
    if c_error == 100 or c_error == 101:
        print("\033[3;31m" + error_messages[c_error] + "\033[0m")
    if c_error == 200 or c_error == 201:
        print("\033[3;31m" + error_messages[c_error] + "\033[0m")

rotary_error_messages = {
    0x01: "Frame error",
    0x02: "Parameter error",
    0x03: "Optical coupling error",
    0x04: "The motor is busy",
    0x05: "Motor is blocked",
    0x06: "Unknown position",
    0xfe: "Task is suspened",
    0xff: "Unkown error",
    200: "No response"
}

def parse_rotary_error(c_error):
    # raise MFCS_NoMFCS(error_messages[c_error])
    if c_error != 0:
        print(error_messages[c_error])
    return

