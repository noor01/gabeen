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
    def __init__(self):
        super().__init__()

    def multiple_choice(self,choices,optional_dialog=None,optional_args=None):
        print("Please enter the number of the desired option:")
        if optional_dialog != None:
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
            if optional_args != None:
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
                if optional_args == None:
                    return response_dict[int(resp)]
                else:
                    return response_dict[int(resp)], optional_resp
            else:
                print("Invalid response. Try Again")

    def multiple_select(self,choices):
        print("Please enter the NUMBER for each desired option, seperated by commas")
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

    def simple_question(self,dialog,valid_responses):
        for line in dialog:
            print(line)
        while True:
            resp = input(">> ")
            if resp in valid_responses:
                return resp
            else:
                pass

    def simple_yes_no(self,dialog):
        r = self.simple_question([dialog],['Y','Yes','YES','yes','y','N','No','NO','no','n'])
        if r in ['Y','Yes','YES','yes']:
            return True
        elif r in ['N','No','NO','no','n']:
            return False

    def wait_loading_bar(self,total_time):
        total_time = int(total_time)
        try:
            for i in tqdm(range(0,total_time)):
                time.sleep(1)
        except:
            print("Incubating for " + str(round(total_time/60,2)) + " minutes")
            time.sleep(total_time)

    def get_user_numeric_value(self,dialog,dtype='int',min_threshold=0,max_threshold=0):
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
