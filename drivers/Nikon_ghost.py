#!/usr/bin/python
# ----------------------------------------------------------------------------------------
# A class for automating tasks related to Nikon's NIS Elements software
# ----------------------------------------------------------------------------------------
# Noorsher Ahmed
# 01/10/2020
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
from Library.dialog_options import dialog
# ----------------------------------------------------------------------------------------
# Nikon ghost class definition
# ----------------------------------------------------------------------------------------
class nikon_ghost(Process):
    # ----------------------------------------------------------------------------------------
    # Initialize Squidward and read callibration and configuration files
    # ----------------------------------------------------------------------------------------
    def __init__(self,microscope):
        Process.__init__(self)
        self.dialog = dialog()
        self.locations_file = "AOTD/Configurations/Microscopes/" + microscope + "/button_locations.csv"
        self.get_ND_path()
        self.ask_ND_time()
        self.defineND_series()
        self.load_locations()
        #self.set_ND_path()

    def defineND_series(self):
        ND_options = {1:'Z',
                    2:'lambda',
                    3: 'XY',
                    4: 'timeseries',
                    5: 'tilescan'}
        print("What ND elements will you be using today?")
        for key, value in ND_options.items():
            print(str(key) + ' -- ' + value)
        print("Type number of each element, sperated by commas:")
        series = input(">> ")
        if ',' in series:
            series = [int(s) for s in series.split(',')]
        else:
            series = [int(series)]
        self.ND_series = []
        for i in series:
            self.ND_series.append(ND_options[i])
        print("CONFIRM: Make sure only the desired ND tabs are selected")
        print("Press ENTER to confirm and continue")
        x = input(">> ")

    def ask_ND_time(self):
        print("How long does each ND acquisition take in minutes?")
        self.ND_length = int(input(">>"))*60

    def get_ND_path(self):
        """
        print("What folder would you like to save all images to?")
        self.ND_save_path = input("Drag and drop here >> ")[1:-1]
        """
        print("Please set the SAVE folder destination for ND series")
        print("Hint: it's on the right side of the bottom panel")
        print("Hit ENTER when reay")
        x = input(">> ")

    def set_ND_path(self):
        ND_path_box = self.get_location('ND_save_to_file_path_rightbound')
        self.change_txtbox_value(ND_path_box,self.ND_save_path,bckspace=100)

    def set_ND_filename(self,filename):
        # GUI changes based on ND tabs that are selected
        num_tabs = len(self.ND_series)
        filename_box = self.get_location('ND_save_to_file_filename_rightbound_' + str(num_tabs))
        self.change_txtbox_value(filename_box,filename,bckspace=50)

    def load_locations(self):
        self.locations = pd.read_csv(self.locations_file)
        self.checkbox_values = {}
        """
        checkbox_names = ['z_tab_checkbox','XY_checkbox','lambda_checkbox','timeseries_checkbox','tilescan_checkbox']
        for i in checkbox_names:
            self.checkbox_values[i] = 0
        self.get_checkbox_status()
        """

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
    # Not currently used
    def adjust_exposure(self,exp_value):
        # Adjust image exposure
        adjust_X, adjust_Y = self.get_location('Exposure_dialog')
        pyautogui.click(x=adjust_X,y=adjust_Y,button='left')
        pyautogui.typewrite(exp_value, interval=0.25)
        pyautogui.press('enter')
    # Not currently used
    def adjust_laser_power(self,laser,laser_value):
        # Adjust laser power
        laser_X, laser_Y = self.get_location('laser_' + laser + '_value')
        self.change_txtbox_value((laser_X, laser_Y),laser_value)
        pyautogui.press('enter')
    # Not currently used 
    def quick_snapshot(self,opt_config):
        # Take a quick snapshot in select channel
        # add channel changing click
        self.change_opt_config(opt_config)
        snap_X, snap_Y = self.get_location('Snapshot')
        pyautogui.click(x=snap_X,y=snap_Y,button='left')  
    # Not currently used
    def snapshot_save(self,save_path):
        # Save a snapshot image
        # Hit file button
        file_x, file_y = self.get_location('menu_File')
        pyautogui.click(x=file_x,y=file_y,button='left')

        # Click Save As
        saveAs_x, saveAs_y = self.get_location('menu_SaveAs')
        pyautogui.click(x=saveAs_x,y=saveAs_y, button='left')

        # Enter file name
        fileName_x, fileName_y = self.get_location('SaveDialog_FileName')
        pyautogui.click(x=fileName_x,y=fileName_y,button='left')
        pyautogui.hotkey('ctrl','a')
        pyautogui.hotkey('backspace')
        pyautogui.typewrite(save_path)

        # Press Save
        save_x, save_y = self.get_location('SaveDialog_Save')
        pyautogui.click(x=save_x,y=save_y, button='left')
    # Not currently used
    def change_opt_config(self,opt_config):
        opt_X, opt_Y = self.get_location(opt_config + '_select')
        pyautogui.click(x=opt_X,y=opt_Y,button='left')
    # Not currently used
    def save_opt_config(self,opt_config):
        # Save an optical configuration after adjusting exposure or laser power
        optSave_x, optSave_y = self.get_location(opt_config + '_save')
        pyautogui.click(x=optSave_x,y=optSave_y,button='left')
    # Not currently used
    def read_z_values(self):
        # Move to specific z-plane to take a snapshot
        # Go to the z tab
        self.z_values = {}
        z_tab_x, z_tab_y = self.get_location('z_tab')
        pyautogui.click(x=z_tab_x,y=z_tab_y,button='left')
        time.sleep(0.25)

        # Get z values
        # Get num of steps
        z_num_x,z_num_y = self.get_location('z_num_steps')
        self.z_values['num_steps'] = float(self.txtbox_get_value(z_num_x,z_num_y))

        # Get step size
        z_step_x, z_step_y = self.get_location('z_step_size')
        self.z_values['step_size'] = float(self.txtbox_get_value(z_step_x,z_step_y))

        # Get Top value
        z_top_x, z_top_y = self.get_location('z_top')
        self.z_values['upper_value'] = float(self.txtbox_get_value( z_top_x, z_top_y))

        # Get Bottom size
        z_bottom_x, z_bottom_y = self.get_location('z_bottom')
        self.z_values['lower_value'] = float(self.txtbox_get_value(z_bottom_x, z_bottom_y))
        print(self.z_values)
    # Not currently used
    def move_to_z(self,z_value):
        # Find Z[um] dialog
        z_x, z_y = self.get_location('z_specific')
        self.change_txtbox_value((z_x,z_y),z_value)
        pyautogui.hotkey('enter')
    # Not currently used
    def move_to_middle_z(self):
        self.read_z_values()
        middle = int((self.z_values['upper_value'] + self.z_values['lower_value'])/2)
        self.move_to_z(middle)
    # Not currently used
    # TODO
    def move_to_XY(self,point_name):
        # Move to specific point in ND acquisition's XY option
        print('Function not supported yet')

    def run_ND(self,file_prefix='ND',series='all'):
        # create a timestamp for this run
        now = datetime.now()
        timestamp = now.strftime("%m%d%Y%H%M")
        # set the file name
        filename = str(file_prefix) + str(timestamp)
        self.set_ND_filename(filename)
        # run the ND acquisition
        run_x, run_y = self.get_location('ND_run')
        pyautogui.click(x=run_x,y=run_y,button='left')
        # hold program till acquisition is finished
        self.dialog.wait_loading_bar(self.ND_length)

    # Not currently used
    def change_tab_status(self,ND,status):
        ND_checkbox_dict = {'Z':'z_tab_checkbox',
                            'lambda':'lambda_checkbox',
                            'XY': 'XY_checkbox',
                            'timeseries':'timeseries_checkbox',
                            'tilescan':'tilescan_checkbox'}
        checkbox = ND_checkbox_dict[ND]
        if self.checkbox_values[checkbox] != status:
            if self.tab_chkbox_dict[checkbox] != 0:
                    tab_x, tab_y = self.get_location(self.tab_chkbox_dict[checkbox])
                    pyautogui.click(x=tab_x,y=tab_y)
                    time.sleep(0.5)
            else:
                pass
            box_x, box_y = self.get_location(checkbox)
            pyautogui.click(x=box_x,y=box_y,button='left')
            self.checkbox_values[checkbox] = status
        else:
            print("tab-status is already: " + str(status))
    # Not currently used
    # TODO
    def change_z_status(self,status):
        # change this to use global checkbox status dict
        if self.checkbox_values['z_tab_checkbox'] != status:
            z_box_x, z_box_y = self.get_location('z_tab_checkbox')
            pyautogui.click(x=z_box_x,y=z_box_y,button='left')
            self.checkbox_values['z_tab_checkbox'] = status
        else:
            print("z-status is already: " + str(status))
    # Not currently used
    def get_exposure(self):
        #locate auto exposure button
        exposure_x, exposure_y = self.get_location('Exposure_dialog')
        exposure = self.txtbox_get_value(exposure_x, exposure_y)
        return exposure
    # Not currently used
    def get_laser_power(self,laser):
        laser_x, laser_y = self.get_location('laser_' + str(laser) + '_value')
        power = self.txtbox_get_value(laser_x, laser_y)
        return power
    # Not currently used
    def adjust_OC(self,opt_config,reset={'laser power':0,'exposure':0}):
        # reset option to set specific laser power and exposure values
        # good for after hybridizing a new sequencing primer and PRICKLi performance is better
        self.change_opt_config(opt_config)
        if reset['laser power'] == 0:
            self.adjust_exposure(reset['exposure'])
            self.adjust_laser_power(self.lasermap[opt_config]['laser'],reset['laser power'])
            self.lasermap[opt_config]['power'] = reset['laser power']
            self.lasermap[opt_config]['exposure'] = reset['exposure']
            return 'reset'
        else:
            pass
        current_exposure = self.lasermap[opt_config]['exposure']
        idx = self.exposure_values.index(current_exposure)
        if self.exposure_values[idx] == self.exposure_values[-1]:
            # reached max we can increase exposure. increase laser power
            current_laser_power = self.lasermap[opt_config]['power']
            if current_laser_power > 95:
                # nothing we can do
                return 'maxed'
            else:
                new_power = current_laser_power + 5
                self.adjust_laser_power(self.lasermap[opt_config]['laser'],new_power)
                self.lasermap[opt_config]['power'] = new_power
        else:
            new_exposure = self.exposure_values[idx + 1]
            self.adjust_exposure(new_exposure)
            self.lasermap[opt_config]['exposure'] = new_exposure
        self.save_opt_config(opt_config)
    def change_txtbox_value(self,coordinate,new_value,bckspace=20):
        # Get current value in textbox given textbox coordinate (X,Y); returns value
        pyautogui.click(x=coordinate[0],y=coordinate[1],button='left')
        for i in range(0,8):
            pyautogui.press('right')
        for i in range(0,bckspace):
            pyautogui.press('backspace')
        pyautogui.typewrite(str(new_value))