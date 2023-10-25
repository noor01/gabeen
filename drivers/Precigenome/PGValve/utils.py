from .exceptions import VALVES_AckError, VALVES_InvalidType

error_messages = {1: "Frame Error",
                  2: "Parameter Error",
                  3: "Optical coupling Error",
                  4: "Motor is busy",
                  5: "Motor is blocked",
                  6: "Unknown position",
                  0xfe: "Task is suspended",
                  0xff: "Unkown error",
                  100: "Illegal Input",
                  101: "Invalid Valve",
                  102: "Invalid Valve Instance",
                  200: "No response",
                  201: "No data found"
                  }

def parse_error(c_error):
    if c_error in [1, 2, 3, 4, 5, 6, 0xfe]:
        raise VALVES_AckError(error_messages[c_error])
    if c_error == 100:
        raise VALVES_InvalidType(error_messages[c_error])
    if c_error == 101 or c_error == 102:
        print(error_messages[c_error])
    if c_error == 200 or c_error == 201:
        print(error_messages[c_error])
