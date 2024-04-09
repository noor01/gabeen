#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for user interface on command line. Eliminates redundancy
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 01/10/2020
# noorsher2@gmail.com
#
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------------------------
from os import read
from tqdm.auto import tqdm
import time

class dialog:
    """
    A class that provides various dialog options for user interaction.

    Methods:
    - multiple_choice(choices, optional_dialog=None, optional_args=None): Displays a list of choices and prompts the user to select one.
    - multiple_select(choices): Displays a list of choices and prompts the user to select multiple options.
    - simple_question(dialog, valid_responses): Displays a simple question and prompts the user for a valid response.
    - simple_yes_no(dialog): Displays a yes/no question and prompts the user for a valid response.
    - wait_loading_bar(total_time): Displays a loading bar for the specified duration.
    - get_user_numeric_value(dialog, dtype='int', min_threshold=0, max_threshold=0): Prompts the user to enter a numeric value within specified thresholds.

    """

    def __init__(self):
        super().__init__()

    def multiple_choice(self, choices, optional_dialog=None, optional_args=None):
        """
        Displays a list of choices and prompts the user to select one.

        Parameters:
        - choices (list): A list of options for the user to choose from.
        - optional_dialog (str, optional): An optional additional dialog to display before the choices.
        - optional_args (list, optional): An optional list of additional arguments to check for in the user's response.

        Returns:
        - If optional_args is None: The selected choice as a string.
        - If optional_args is not None: A tuple containing the selected choice as a string and the optional argument as a string or False.

        """

        print("Please enter the number of the desired option:")
        if optional_dialog is not None:
            print(optional_dialog)
        else:
            pass
        response_dict = dict()
        n = 1
        for option in choices:
            response_dict[n] = option
            print(str(n) + " - " + str(option))
            n += 1
        while True:
            resp = input(">> ")
            if optional_args is not None:
                for i in optional_args:
                    if i in resp:
                        optional_resp = i
                        resp = resp.split(' ' + i)[0]
                        break
                    else:
                        optional_resp = False
            else:
                optional_resp = None
            if resp.isdigit():
                pass
            else:
                print("Invalid response. Try Again")
                continue
            if int(resp) in response_dict.keys():
                if optional_args is None:
                    return response_dict[int(resp)]
                else:
                    return response_dict[int(resp)], optional_resp
            else:
                print("Invalid response. Try Again")

    def multiple_select(self, choices):
        """
        Displays a list of choices and prompts the user to select multiple options.

        Parameters:
        - choices (list): A list of options for the user to choose from.

        Returns:
        - A list of selected choices.

        """

        print("Please enter the NUMBER for each desired option, separated by commas")
        response_dict = dict()
        n = 1
        for option in choices:
            response_dict[n] = option
            print(str(n) + " - " + str(option))
            n += 1
        series = input(">> ")
        if series == '':
            print("You forgot to put something...try again")
            self.multiple_select(choices)
        else:
            pass
        if ',' in series:
            series = [int(s) for s in series.split(',')]
        else:
            series = [int(series)]
        response_values = []
        for i in series:
            response_values.append(response_dict[i])
        return response_values

    def simple_question(self, dialog, valid_responses):
        """
        Displays a simple question and prompts the user for a valid response.

        Parameters:
        - dialog (list): A list of strings representing the question or dialog to display.
        - valid_responses (list): A list of valid responses.

        Returns:
        - The user's response as a string.

        """

        for line in dialog:
            print(line)
        while True:
            resp = input(">> ")
            if resp in valid_responses:
                return resp
            else:
                pass

    def simple_yes_no(self, dialog):
        """
        Displays a yes/no question and prompts the user for a valid response.

        Parameters:
        - dialog (str): The question or dialog to display.

        Returns:
        - True if the user's response is 'Y', 'Yes', 'YES', 'yes', 'y'.
        - False if the user's response is 'N', 'No', 'NO', 'no', 'n'.

        """

        r = self.simple_question([dialog], ['Y', 'Yes', 'YES', 'yes', 'y', 'N', 'No', 'NO', 'no', 'n'])
        if r in ['Y', 'Yes', 'YES', 'yes']:
            return True
        elif r in ['N', 'No', 'NO', 'no', 'n']:
            return False

    def wait_loading_bar(self, total_time):
        """
        Displays a loading bar for the specified duration.

        Parameters:
        - total_time (int): The duration of the loading bar in seconds.

        """

        total_time = int(total_time)
        try:
            for i in tqdm(range(0, total_time)):
                time.sleep(1)
        except:
            print("Incubating for " + str(round(total_time / 60, 2)) + " minutes")
            time.sleep(total_time)

    def get_user_numeric_value(self, dialog, dtype='int', min_threshold=0, max_threshold=0):
        """
        Prompts the user to enter a numeric value within specified thresholds.

        Parameters:
        - dialog (str): The question or dialog to display before prompting for the numeric value.
        - dtype (str, optional): The data type of the expected numeric value. Default is 'int'.
        - min_threshold (int or float, optional): The minimum allowed value. Default is 0.
        - max_threshold (int or float, optional): The maximum allowed value. Default is 0.

        Returns:
        - The user's numeric value as an int or float, depending on the specified dtype.

        """

        print(dialog)
        print("Enter a number:")
        while True:
            r = input(">> ")
            if '-' in r:
                sign = '-'
                r = r.strip('-')
            else:
                sign = '+'
            if r.isnumeric() == True:
                if sign == '-':
                    r = -float(r)
                else:
                    pass
                if max_threshold != 0 and float(r) < max_threshold and float(r) > min_threshold:
                    break
                elif max_threshold != 0 and float(r) > max_threshold:
                    print("Invalid value. Please enter a value less than " + str(max_threshold))
                elif max_threshold != 0 and float(r) < min_threshold:
                    print("Invalid value. Please enter a value greater than or equal to " + str(min_threshold))
                elif max_threshold == 0:
                    break
                else:
                    break
            else:
                print("Invalid response. Please enter a valid number:")
        if dtype == 'int':
            r = int(r)
        elif dtype == 'float':
            r = float(r)
        return r
