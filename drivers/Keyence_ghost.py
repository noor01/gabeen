#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for automating tasks related to Keyence acquisition software
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 07/15/2021
# noorsher2@gmail.com
#
# ----------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------
# Import
# ----------------------------------------------------------------------------------------
import os
import time
from multiprocessing import Process
from datetime import datetime
import numpy as np
import pandas as pd
import pyautogui
import pyperclip
import pickle
from tkinter import filedialog
from Library.dialog_options import dialog
# ----------------------------------------------------------------------------------------
# Keyence ghost class definition
# ----------------------------------------------------------------------------------------
class keyence_ghost(Process):
    # ----------------------------------------------------------------------------------------
    # Initialize Squidward and read callibration and configuration files
    # ----------------------------------------------------------------------------------------
    def __init__(self,microscope):
        Process.__init__(self)
        self.dialog = dialog()
        self.locations_file = "AOTD/Configurations/Microscopes/" + microscope + "/button_locations.csv"
        self.get_ND_path()
        self.ask_ND_time()
        self.config_channels()
        #self.defineND_series()
        self.load_locations()

    def browseFiles(self):
        print("Please select a folder to save all files to")
        filename = filedialog.askdirectory(initialdir='/')
        return filename

    def ask_ND_time(self):
        print("How long does each ND acquisition take in minutes (approximately)?")
        self.ND_length = int(input(">>"))*60

    def get_ND_path(self):
        self.root_save_path = self.browseFiles()

    def set_root_path(self):
        root_path_box = self.get_location('Root_path')
        self.change_txtbox_value(root_path_box,self.root_save_path,bckspace=100,right=20)

    def config_channels(self):
        chs = ['CH1','CH2','CH3','CH4']
        fluors = ['DAPI','GFP','Cy3','Cy5']
        ch_fluor_dict = {}
        for ch in chs:
            print("What fluorophore is in-- " + ch + " --?")
            ch_fluor_dict[ch] = self.dialog.multiple_choice(fluors)
        with open(self.root_save_path+'/channel_config.txt','w+') as f:
            f.write(str(ch_fluor_dict))
        with open(self.root_save_path+'/channel_config.pkl','wb+') as f:
            pickle.dump(ch_fluor_dict,f,protocol=pickle.HIGHEST_PROTOCOL)

    def load_locations(self):
        self.locations = pd.read_csv(self.locations_file)

    def get_location(self,element):
        row = self.locations[self.locations['Element_name']==element]
        X = row['X']
        Y = row['Y']
        return X,Y
    # Not currently used
    def txtbox_get_value(self,x,y):
        # Get current value in textbox given textbox coordinate (X,Y); returns value
        pyautogui.click(x=x,y=y,button='left')
        time.sleep(0.25)
        pyautogui.click(x=x,y=y,button='left')
        pyautogui.drag(-100, 0, 0.5, button='left')
        pyautogui.hotkey('ctrl','c')
        value = pyperclip.paste()
        return value

    def run_ND(self,file_prefix='ND',series='all'):
        # create a timestamp for this run
        now = datetime.now()
        timestamp = now.strftime("%m%d%Y%H%M")
        # set the file name
        filename = str(file_prefix) + '_' + str(timestamp)
        # start capture
        print("Starting capture")
        self.click_button("Start_capture")
        # set root path
        time.sleep(5)
        print("Changing root path")
        self.set_root_path()
        # set group name
        time.sleep(0.5)
        print("setting group name")
        file_path_box = self.get_location("Group_folder")
        self.change_txtbox_value(file_path_box,filename,bckspace=50)
        # Change prefix to generic "image"
        prefix_box = self.get_location("Prefix")
        self.change_txtbox_value(prefix_box,'image',bckspace=50)
        # hit ok
        self.click_button("Capture_OK")
        time.sleep(2)
        # confirm capture
        self.click_button("Capture_confirm")
        # wait for acquisition to finish
        print("Waiting for completion...")
        self.wait_for_finish(filename)
        # Close capture dialog
        print("Completed")
        time.sleep(0.5)
        self.click_button("Capture_dialog_close")
        time.sleep(0.2)
        self.click_button("Capture_dialog_close2")
        # get back to live image
        time.sleep(0.5)
        self.click_button("Live_image")

    def click_button(self,button_name):
        x,y = self.get_location(button_name)
        pyautogui.click(x=x,y=y,button='left')

    def change_txtbox_value(self,coordinate,new_value,bckspace=20,right=8):
        # Get current value in textbox given textbox coordinate (X,Y); returns value
        pyautogui.click(x=coordinate[0],y=coordinate[1],button='left')
        for i in range(0,right):
            pyautogui.press('right')
        for i in range(0,bckspace):
            pyautogui.press('backspace')
        pyautogui.typewrite(str(new_value))

    def wait_for_finish(self,filename):
        while True:
            snap1 = os.listdir(self.root_save_path + '/' + filename)
            time.sleep(15)
            snap2 = os.listdir(self.root_save_path + '/' + filename)
            if snap1 == snap2:
                print("Acquisition complete")
                break
            else:
                print('.')
                pass
    def get_subfiles(self,directory):
        files = []
        for path, subdirs, files in os.walk(directory):
            for name in files:
                files.append(name)