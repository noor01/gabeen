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
import sys
import shutil
import time
import threading
import cv2
from skimage.exposure import equalize_hist
from multiprocessing import Process
from datetime import datetime
from tracemalloc import start
import numpy as np
import pandas as pd
from Library.dialog_options import dialog
import json
import copy
import tkinter
from tqdm.auto import tqdm
from tkinter import filedialog
import ipywidgets as widgets
from ipywidgets import interact, interact_manual
import matplotlib.pyplot as plt
from math import floor
from scipy import ndimage
import random
from scipy.interpolate import griddata
from sklearn import linear_model
from .slack_notify import msg as slack

sys.path.append('C:\\Program Files\\OxfordNanoimaging_1.18.3\\.venv\\Lib\\site-packages')
sys.path.append('C:\\Program Files\\OxfordNanoimaging_1.18.3\\nim_python_core\\')
from NimSetup import *
nim_setup('C:\\Users\\ONI\\Dropbox\\Yeo lab\\Noor\\Code\\Army-of-the-Damned\\Library','C:\\Program Files\\OxfordNanoimaging_1.18.3')

from NimPyHelpers import *

# ----------------------------------------------------------------------------------------
# ONI Nanoimager ghost class definition
# ----------------------------------------------------------------------------------------
class oni_ghost(Process):
    # ----------------------------------------------------------------------------------------
    # Initialize and read callibration and configuration files
    # ----------------------------------------------------------------------------------------
    def __init__(self,microscope,mode,preset=None):
        Process.__init__(self)
        self.log_info = {}
        self.mode = mode
        self.preset = preset
        self.dialog = dialog()
        self.focus_style = 'ONI' # change to 'ONI' to use ONI's built in autofocus...currently buggy
        self.initialize_nimOS()
        self.initialize_ONI()
        self.first_aq = True
        self.ND_length = 2
        self.snapshot_num = 0
        if 'xy_start' in self.preset.keys():
            self.xy_start = self.preset['xy_start']
        else:
            self.xy_start = 0
        self.save_dir = self.preset['save_dir']
        
    def initialize_ONI(self):
        
        if self.mode =="CLI":
            self.grab_parameters()
            print("DISCONNECT nimOS from ONI.")
            x = input("Press ENTER to continue when ready >> ")
        elif self.mode == "Jupyter":
            self.jupyter_setup()
            pass
        while True:
            connection_status = self.connect_system()
            if connection_status == False:
                print("Please shutdown nimOS before continuing")
                x = input("Press any key to try again >> ")
            else:
                break
        self.light.FocusLaser.Enabled = True
        self.turn_lights_off()
        self.light.GlobalOnState = True
        self.acquisition.SaveTiffFiles = True
        self.acquisition.RealTimeLocalization= False
        self.init_light_program()
        self.init_xy_pos()
        self.init_z_stacks()
        if self.mode == "CLI":
            self.initialize_focus()
        else:
            pass
        self.camera.SetBinning(self.camera.Binning().b1x1)
        # set ROI here in future
        
    def reinitialize_ONI(self,new_params):
        self.preset = new_params
        if 'xy_start' in self.preset.keys():
            self.xy_start = self.preset['xy_start']
        else:
            self.xy_start = 0
        self.logs_dir = os.path.dirname(self.preset['oni_json'])
        self.main_dataset_tag = self.preset['dataset_tag']
        self.default_dir = 'C:/Data/DEFAULT_USER/' + self.main_dataset_tag + '/'
        self.log_file_name = self.default_dir + 'positional_log.csv'
        if os.path.exists(self.log_file_name):
            pass
        else:
            with open(self.log_file_name,'w+') as log_file:
                log_file.write('filename, pos, x, y, z\n')
        self.start_z = self.preset['start_z']
        self.offset_z = self.preset['offset_z']
        self.offset_z_diff = self.start_z - self.offset_z
        self.first_start_z = self.start_z
        self.light.FocusLaser.Enabled = True
        self.turn_lights_off()
        self.light.GlobalOnState = True
        self.acquisition.SaveTiffFiles = True
        self.acquisition.RealTimeLocalization= False
        self.init_light_program()
        self.init_xy_pos()
        self.init_z_stacks()
        
    def safe_focus_range(self,desired):
        upper_thresh = 2000
        lower_thresh = -450
        if desired[0] < lower_thresh:
            desired[0] = lower_thresh
        elif desired[0] > upper_thresh:
            desired[0] = upper_thresh
        else:
            pass
        if desired[1] > upper_thresh:
            desired[1] = upper_thresh
        elif desired[1] < lower_thresh:
            desired[1] = lower_thresh
        else:
            pass
        return desired
    
    def initialize_focus(self):
        self.global_on_lights_off()
        self.light.FocusLaser.Enabled = True
        if self.mode == "CLI":
            if self.focus_style == 'ONI':
                self._oni_set_autofocus(self.start_z)
            else:
                self._set_autofocus(self.start_z + 50, self.start_z - 50, display_img=True)
            self._move_xy(self.starting_pos['x'],self.starting_pos['y'])
            print("Microscope successfully initialized! :) ")
        elif self.mode == "Jupyter":
            #add function here for manual set up
            self._move_z(self.first_start_z)
            self._move_xy(self.starting_pos['x'],self.starting_pos['y'])
            #self.jupyter_manual_z(preadjust=False,manual_z=self.first_start_z)
            #self.jupyter_get_corner_zs()
            

    def jupyter_setup(self):
        if 'instrument_name' in self.preset.keys():
            self.instrument_name = self.preset['instrument_name']
        else:
            self.instrument_name = '0'
        multi_acq_config = self.preset['oni_json']
        with open(multi_acq_config) as json_file:
            self.oni_params = json.load(json_file)
        # save logs in the same folder that the acquisition json file was saved in
        self.logs_dir = os.path.dirname(multi_acq_config)
        self.main_dataset_tag = self.preset['dataset_tag']
        self.default_dir = 'C:/Data/DEFAULT_USER/' + self.main_dataset_tag + '/'
        self.log_file_name = self.default_dir + 'positional_log.csv'
        if os.path.isdir(self.default_dir):
            pass
        else:
            os.mkdir(self.default_dir)
        if os.path.exists(self.log_file_name):
            pass
        else:
            with open(self.log_file_name,'w+') as log_file:
                log_file.write('filename, pos, x, y, z\n')
        self.start_z = self.preset['start_z']
        self.offset_z = self.preset['offset_z']
        self.offset_z_diff = self.start_z - self.offset_z
        self.first_start_z = self.start_z
        
    def position_logger(self,pos, filename):
        x = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        y = self.stage.GetPositionInMicrons(self.stage.Axis.Y)
        z = self.stage.GetPositionInMicrons(self.stage.Axis.Z)
        with open(self.log_file_name,mode='a') as log_file:
            log_file.write(filename + ',' + str(pos) + ',' + str(x) + ',' + str(y) + ',' + str(z) + '\n')
            
    def jupyter_manual_z(self,preadjust=True,force_z = 0,dapi_ch=0,dapi_power=15):
        self.global_on_lights_off()
        self.light.FocusLaser.Enabled = True
        if preadjust == True and force_z == 0:
            print("Doing coarse autofocus...before manual check")
            self._set_autofocus(zmin=self.start_z+150,zmax=self.start_z-150,callibrate=False)
        elif force_z != 0:
            self.best_z = force_z
            self._move_z(force_z)
        else:
            self.best_z = self.start_z
        self.light[dapi_ch].PercentPower = dapi_power
        for n in [0,1,2,3]:
            if n != dapi_ch:
                self.light[n].Enabled = False
        manual_max = self.best_z+100
        manual_min = self.best_z-100
        @interact(z=(manual_min,manual_max,0.2))
        def _manual_z_adjust(z):
            self._move_z(z)
            foc_im = self._focus_cam_snapshot()
            self.light[0].Enabled = True
            self.lightGlobalOnState = False
            n_Frames = 1
            image_source = self.camera.CreateImageSource(n_Frames)
            self.lightGlobalOnState = True
            self.focus_dapi_im = self.quick_crop((image_source.GetNextImage().ImageData()),split=1024,side=0)
            self.lightGlobalOnState = False
            self.focus_dapi_im = equalize_hist(cv2.convertScaleAbs(self.focus_dapi_im))
            fig, axs = plt.subplots(nrows=2,figsize=(10,15))
            axs[0].imshow(foc_im)
            axs[1].imshow(self.focus_dapi_im,cmap='magma')
            self.best_z = z
            self.first_start_z = z
            del(image_source)
        _manual_z_adjust(self.best_z)
        
    def force_best_z(self,new_z):
        self.first_start_z = new_z
    
    def initialize_nimOS(self):
        self.instrument = get_nim_control()
        self.data_manager = get_nim_data_manager()
        self.profiles = get_user_profile_manager()
        self.user_settings = get_user_settings()
        self.acquisition = create_nim_acq_manager(self.instrument, self.data_manager, self.profiles)
        self.calibration = get_calibration_control()
        self.stage = self.instrument.StageControl
        self.light = self.instrument.LightControl
        self.camera = self.instrument.CameraControl
        self.illum_angle = self.instrument.IlluminationAngleControl
        self.focus_cam = self.instrument.FocusCameraControl
        self.autofocus = self.instrument.AutoFocusControl
        self.temperature = self.instrument.TemperatureControl
        self.stageX = self.stage.Axis.X
        self.stageY = self.stage.Axis.Y
        self.stageZ = self.stage.Axis.Z

        
    def select_instrument(self):
        instruments = self.instrument.GetAvailableInstruments()
        for instr in instruments:
            print(instr)
        # Select the first instrument
        if self.instrument_name in instruments:
            print("Connecting to %s..." % self.instrument_name)
            self.instrument.SelectInstrument(self.instrument_name)
            return True
        elif len(instruments)>0:
            print("Connecting to %s..." % instruments[0])
            self.instrument.SelectInstrument(instruments[0])
            return True
        else:
            print('No instrument available')
            return False
        
    def callibrate_autofocus(self,start_z=0):
        self.global_on_lights_off()
        self._move_z(start_z)
        print('autofocusing')
        self.autofocus.StartReferenceCalibration()
        while self.autofocus.CurrentStatus == self.autofocus.Status.CALIBRATING:
            time.sleep(0.1)
        if self.autofocus.LastCalibrationCode is not self.autofocus.CalibrationCompleteCode.SUCCESS:
            raise Exception('Focus not able to calibrate')
        else:
            print('autofocus complete')
        
    def connect_system(self):
        if not self.instrument.IsConnected:
            if not self.select_instrument():
                print("Could not select instrument")
                return False
            print("Instrument connecting....")
            self.instrument.Connect()
            if not self.instrument.IsConnected:
                print("Failed to coßnnect to microscope")
                return False
            else:
                print("Connected Successfully!")
                return True
    
    def grab_parameters(self):
        #print("1. Please use nimOS to focus system, and callibrate autofocus")
        print("Please setup the multiacquisition and save the acquisition file.")
        x = input("Press ENTER here to select your .json file >> ")
        # open a tkinter window to select the file
        tkinter.Tk().withdraw()
        file_path = filedialog.askopenfilename()
        with open(file_path) as json_file:
            self.oni_params = json.load(json_file)
        # save logs in the same folder that the acquisition json file was saved in
        self.logs_dir = os.path.dirname(file_path)
        # Get a list of directories to save to
        """
        num_drives = self.dialog.get_user_numeric_value('How many directories to target for saving?',max_threshold=10)
        self.save_directories = {}
        for i in range(0,num_drives):
            tkinter.Tk().withdraw()
            file_path_tmp = filedialog.askopenfilename() # put an empty text file first in each folder to detect
            file_path = ''.join(file_path_tmp.split('/')[:-1]) + '/'
            print(file_path)
            # get free space in drive
            free_space = shutil.disk_usage(file_path)[2]
            self.save_directories[file_path] = free_space
        """
        # get main dataset tag for saving on system
        print("What main dataset tag to use?")
        self.main_dataset_tag = input(">> ")
        self.default_dir = 'C:/Data/DEFAULT_USER/' + self.main_dataset_tag + '/'
        self.start_z = self.dialog.get_user_numeric_value("What z to start at?")
        self.first_start_z = self.start_z
        
    def _get_dir_size(self,path='.'):
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.get_dir_size(entry.path)
        return total
    
    # switch drives to save to if next acquisition won't fit on current drive
    def _get_save_dir(self,buffer_dir):
        # get accounting of current drive space
        for save_dir in self.save_directories.keys():
            free_space = shutil.disk_usage(save_dir)[2]
            self.save_directories[save_dir] = free_space
        acq_size = self._get_dir_size(buffer_dir)
        n = 0
        save_dirs = list(self.save_directories.keys())
        while True:
            if acq_size > self.save_directories[save_dirs[n]]:
                n += 1
                continue
            else:
                final_save_dir = save_dirs[n]
                break
        return final_save_dir
        
    def make_and_get_json(self,filename):
        # create a new json file for this round with designated round IDs and shit
        round_params = copy.deepcopy(self.oni_params)
        now = datetime.now()
        time_stamp = now.strftime("%m-%d-%Y_%H-%M-%S")
        round_params['savingOptions']['dataSetTag'] = filename
        round_params['timestamp'] = time_stamp
        file = self.logs_dir + '/' + filename + '.json'
        print(round_params)
        with open(file,'w') as json_dump:
            json.dump(round_params,json_dump)
        # load it up
        loaded = self.multi_acquisition.LoadConfigurationFromFile(file)
        if not loaded:
            raise Exception("Couldn't load multiacquisition config from file")

    def _get_stage_pos(self):
        x = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        y = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        z = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        return (x,y,z)
    
    def _move_pos(self,x,y,z):
        self.stage.RequestMoveAbsolute(self.stageX,x)
        self.stage.RequestMoveAbsolute(self.stageY,y)
        self.stage.RequestMoveAbsolute(self.stageZ,z)
        while self.stage.IsMoving(self.stageX) or self.stage.IsMoving(self.stageY) or self.stage.IsMoving(self.stageZ):
            time.sleep(0.1)
        
    def _move_xy(self,x,y):
        self.stage.RequestMoveAbsolute(self.stageX,x)
        self.stage.RequestMoveAbsolute(self.stageY,y)
        while self.stage.IsMoving(self.stageX) or self.stage.IsMoving(self.stageY):
            time.sleep(0.1)

    def _move_z(self,z):
        if z > 1800:
            z = 1800
            print("WARNING: Z is too high, setting to 1800")
        else:
            pass
        self.stage.RequestMoveAbsolute(self.stageZ,z)
        while self.stage.IsMoving(self.stageZ):
            time.sleep(0.1)
        
    def _get_z(self):
        return self.stage.GetPositionInMicrons(self.stage.Axis.Z)
    
    def _get_curr_position(self):
        x = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        y = self.stage.GetPositionInMicrons(self.stage.Axis.Y)
        z = self.stage.GetPositionInMicrons(self.stage.Axis.Z)
        return (x,y,z)
        
    def _get_sharpness(self,foc_im):
        dx = np.diff(foc_im)[1:,:] # remove the first row
        dy = np.diff(foc_im, axis=0)[:,1:] # remove the first column
        dnorm = np.sqrt(dx**2 + dy**2)
        shrp = np.average(dnorm)
        return shrp
    
    def _focus_centerofmass(self,img):
        norm = np.divide(img,np.max(img))
        bin_img = np.where(norm > 0.7,1,0)
        cm = ndimage.measurements.center_of_mass(bin_img)
        return cm
    
    def _focus_cam_snapshot(self):
        return nim_image_to_array(self.focus_cam.GetLatestImage())
    
    def _oni_set_autofocus(self,z):
        self.best_z = z
        self.callibrate_autofocus(start_z=z)
    
    def _reset_z_focus(self):
        self.autofocus.Stop()
        self._move_z(self.first_start_z)
        self._move_xy(self.starting_pos['x'],self.starting_pos['y'])
        self._oni_quick_focus()
        #self._set_autofocus(self.first_start_z+75,self.first_start_z-75,callibrate=True)
        
    
    def _set_autofocus(self,zmin,zmax,callibrate=True):
        safe_range = self.safe_focus_range([zmin,zmax])
        zmin = safe_range[0]
        zmax = safe_range[1]
        #self.light.GlobalOnState = True
        # coarse focus
        coarse_sharpness = []
        coarse_zs = list(np.arange(zmin,zmax,-2))
        print("Doing Coarse Focus")
        for z in tqdm(coarse_zs):
            self._move_z(z)
            foc_im = self._focus_cam_snapshot()
            shrp = self._get_sharpness(foc_im)
            coarse_sharpness.append(shrp)
        best_z = coarse_zs[coarse_sharpness.index(max(coarse_sharpness))]
        print("Best Z from coarse focus: " + str(best_z))
        fine_range = list(np.arange(best_z-10,best_z+10,0.5))
        scores = []
        print("Doing fine focus adjustments")
        for z in tqdm(fine_range):
            self._move_z(z)
            time.sleep(0.1)
            foc_im = self._focus_cam_snapshot()
            scores.append(np.std(foc_im))
        best_z = fine_range[scores.index(max(scores))]
        self._move_z(z)
        foc_im = self._focus_cam_snapshot()
        cm = self._focus_centerofmass(foc_im)
        self.best_z = best_z
        self.reference_cm = cm
        if callibrate == True and self.focus_style == 'ONI':
            print("Calibrating autofocus")
            self.callibrate_autofocus(self.best_z)
        else:
            return
    
    def _oni_quick_focus(self,timeout=5000):
        self.autofocus.Stop()
        self.autofocus.StartSingleShotAutoFocus(timeout)
    
    def _quick_focus(self,acceptable=75):
        self.light.FocusLaser.Enabled = True
        self._oni_quick_focus()
        foc_im = self._focus_cam_snapshot()
        cm = self._focus_centerofmass(foc_im)
        if np.std(foc_im) < 7:
            print("autofocus failed")
            # autofocus failed
            self._set_autofocus(zmin=self.first_start_z+75,zmax=self.first_start_z-75)
        else:
            pass
    
    def _move_pos_autofocus(self,x,y):
        #self.autofocus.StartContinuousAutoFocus()
        self._move_xy(x,y)
        #self.autofocus.Stop()
        self._move_z(self.best_z)
        self._quick_focus()
    
    def _get_n_points(self,lst, N):
        if N <= 0:
            return []
        elif N >= len(lst):
            return lst
        
        indices = [int(i * (len(lst) - 1) / (N - 1)) for i in range(N)]
        return [lst[i] for i in indices]

    
    def jupyter_get_corner_zs(self,force_z=0,num_points = 5,range_max=10):
        self.global_on_lights_off()
        self.light.FocusLaser.Enabled = True
        # corners = self.find_extreme_points(self.positions)
        #corners = random.sample(self.positions,num_points)
        corners = self._get_n_points(self.positions,num_points)
        if force_z != 0:
            self.start_z = force_z
        manual_max = self.start_z+range_max
        manual_min = self.start_z-range_max
        self.corner_vals = {}
        for n in range(len(corners)):
            self.corner_vals[n] = [corners[n],0]
        @interact(z=(manual_min,manual_max,0.2),
                  xy=list(self.corner_vals.keys()))
        def _manual_z_adjust(z,xy):
            #print(self.corner_vals)
            self._move_z(z)
            pos = self.corner_vals[xy][0]
            self._move_xy(pos[0],pos[1])
            foc_im = self._focus_cam_snapshot()
            self.light[0].Enabled = True
            self.lightGlobalOnState = False
            n_Frames = 1
            image_source = self.camera.CreateImageSource(n_Frames)
            self.lightGlobalOnState = True
            self.focus_dapi_im = self.quick_crop((image_source.GetNextImage().ImageData()),split=1024,side=0)
            self.lightGlobalOnState = False
            self.focus_dapi_im = equalize_hist(cv2.convertScaleAbs(self.focus_dapi_im))
            fig, ax = plt.subplots(nrows=3,figsize=(5,10))
            ax[0].scatter([x[0][0] for x in self.corner_vals.values()],[y[0][1] for y in self.corner_vals.values()],color='r')
            ax[0].scatter([pos[0]],[pos[1]],color='b',marker='x')
            ax[0].set_aspect('equal', adjustable='box')
            ax[1].imshow(foc_im)
            ax[2].imshow(cv2.convertScaleAbs(self.focus_dapi_im))
            self.corner_vals[xy][1] = z
        _manual_z_adjust(self.start_z,0)
    
    def train_z_model(self):
        X = np.asarray([i[0] for i in self.corner_vals.values()])
        Y = np.asarray([i[1] for i in self.corner_vals.values()])
        self.z_model = linear_model.LinearRegression()
        self.z_model.fit(X,Y)
        #also callibrate autofocus at the current position
        curr_z = self._get_z()
        self.callibrate_autofocus(curr_z)
        
            
    def move_pos_modeled_focus(self,x,y,move=True,oni_auto=True):
        #z = float(self.z_function(x,y))
        z = self.z_model.predict(np.asarray((x,y)).reshape(1,-1))[0]
        if move == True:
            self._move_xy(x,y)
            self._move_z(z)
            if oni_auto == True:
                self._oni_quick_focus()
            else:
                pass
        else:
            pass
        return z
        
        
    def init_light_program(self):
        self.light.GloablOnState = False
        json_light_program = self.oni_params['steps']
        exposure = json_light_program[0]['exposure_ms'] # just use whatever exposure is on the first light program
        self.camera.SetTargetExposureMilliseconds(exposure)
        self.light_program = []
        self.exposure_program = []
        for step in json_light_program:
            _lasers = []
            self.exposure_program.append(step['exposure_ms'])
            for item in step['lightStates']:
                if item['on'] == False:
                    _lasers.append(0.0)
                else:
                    _lasers.append(item['value'])
            self.light_program.append(_lasers)
        self.summed_light_program = list(np.asarray(self.light_program).sum(axis=0))
        # prime the lasers to be ready to go
        for n,power in enumerate(self.summed_light_program):
            self.light[n].PercentPower = power
            self.light[n].Enabled = False
        
    def _grab_starting_pos(self):
        pos = self.oni_params['movementOptions']['customXYPositions_mm'][0]['position']
        pos['x'] = pos['x'] * 1000
        pos['y'] = pos['y'] * 1000
        pos['z'] = pos['z'] * 1000
        return pos
           
    def _grab_custom_fovs(self):
        positions = []
        for n in self.oni_params['movementOptions']['customXYPositions_mm']:
            positions.append(n['position'])
        return positions
    
    def _make_tiles(self,starting_pos,n_x,n_y,x_inc_um,y_inc_um):
        x_start = starting_pos['x']
        y_start = starting_pos['y']
        positions = []
        xs = list(range(0,n_x))
        ys = list(range(0,n_y))
        if (len(ys) % 2) == 0:
            all_xs = (xs + list(reversed(xs)))*floor(len(ys)/2)
        else:
            all_xs = (xs + list(reversed(xs)))*floor(len(ys)/2)
            all_xs += xs
        all_ys = []
        for y in ys:
            all_ys += [y]*len(xs)
        tmp_positions = list(zip(all_xs,all_ys))
        positions = []
        for pos in tmp_positions:
            positions.append([x_start + (pos[0] * x_inc_um), y_start + (pos[1] * y_inc_um)])
        return positions
    
    def init_xy_pos(self):
        if 'fov_positions' in self.preset.keys():
            self.starting_pos = {'x' : self.preset['fov_positions'][0][0],
                                 'y' : self.preset['fov_positions'][0][1]}
            self.positions = self.preset['fov_positions']
        elif len(self.oni_params['movementOptions']['customXYPositions_mm']) == 1:
            self.acq_mode = 'tilescan'
            self.starting_pos = self._grab_starting_pos()
            #self.start_z = self.starting_pos['z']*1000
            print("Starting position [um]: ")
            print(self.starting_pos)
            n_x = self.oni_params['movementOptions']['numberOfStepsInXY']['x']
            n_y = self.oni_params['movementOptions']['numberOfStepsInXY']['y']
            x_inc_um = self.oni_params['movementOptions']['fovIncrement_mm']['x']*1000
            y_inc_um = self.oni_params['movementOptions']['fovIncrement_mm']['y']*1000
            self.positions = self._make_tiles(self.starting_pos,n_x,n_y,x_inc_um,y_inc_um)
        elif len(self.oni_params['movementOptions']['customXYPositions_mm']) > 1:
            self.acq_mode = 'custom'
            positions_raw = self._grab_custom_fovs()
            self.positions = []
            for n in positions_raw:
                self.positions.append([n['x'],n['y']])
                
    def init_z_stacks(self):
        top = self.oni_params['movementOptions']['zStackStartPosition_um']
        num_slices = self.oni_params['movementOptions']['numberOfZSlices']
        dz = self.oni_params['movementOptions']['spacingBetweenZSlices_um']
        zs = []
        for n in range(num_slices):
            zs.append(top-(n*dz))
        self.relative_zs = np.asarray(zs)
        
    def _generate_real_zs(self,z_start):
        return list(self.relative_zs + np.array(z_start))
    
    def turn_lights_off(self):
        for light in range(4):
            self.light[light].Enabled = False
            
    def global_on_lights_off(self):
        self.turn_lights_off()
        self.light.GlobalOnState = True
    
    def activate_light_program(self,lighting):
        bool_647 = False
        self.lightGlobalOnState = False
        for n,power in enumerate(lighting):
            if n == 3 and power >0:
                bool_647 = True
            self.light[n].PercentPower = power
            if power > 0:
                self.light[n].Enabled = True
            else:
                self.light[n].Enabled = False
        #self.light.GlobalOnState = True
        return bool_647
        # just remember to turn it off after
            
    def _clean_folder(self,dir_):
        all_files = os.listdir(dir_)
        for f in all_files:
            if '.tif' in f:
                continue
            else:
                os.remove(dir_+f)
    
    def data_transfer(self,filename):
        def _move_files(start_dir,target_dir,filename):
            files = os.listdir(start_dir)
            for f in files:
                if filename in f:
                    try:
                        shutil.move(start_dir + f, target_dir + f)
                    except:
                        continue
                else:
                    continue
        start_folder = self.default_dir
        print(start_folder)
        self._clean_folder(start_folder)
        save_dir = self._get_save_dir(start_folder)
        #self.th = threading.Thread(target=_move_files, args=(start_folder,save_dir,filename))
        #self.th.start() # we'll wait for this thread to be complete by the time we get to our next imaging sesh
        
    def full_acquisition(self,filename):
        #self.autofocus.Stop()
        #self.light.GlobalOnStateStartac = False
        total_frames = len(self.positions) * len(self.light_program) * len(self.relative_zs)
        pbar = tqdm(total=total_frames)
        if not os.path.isdir(f'{self.save_dir}/{filename}'):
            os.makedirs(f'{self.save_dir}/{filename}')
        for pos_n, pos in enumerate(self.positions):
            self.acquire_single_position(pos_n,pos,self.save_dir,filename,pbar=pbar)
        self.light.GlobalOnState = False
        pbar.close()
            
    
    
    
    def full_acquisition_old(self,filename):
        self.autofocus.Stop()
        self.light.GlobalOnStateStartac = False
        #self._reset_z_focus()
        total_num_frames = len(self.positions)*len(self.relative_zs)*len(self.light_program)
        self.light.GlobalOnState = True
        pbar = tqdm(total=total_num_frames)
        for pos_n, pos in enumerate(self.positions):
            x = pos[0]
            y = pos[1]
            #self._move_pos_autofocus(x,y)
            #curr_z = self._get_z()
            curr_z = self.move_pos_modeled_focus(x,y,oni_auto=True)
            # log position
            self.position_logger(self.xy_start + pos_n, filename)
            offset_z = curr_z - self.offset_z_diff
            zs = self._generate_real_zs(offset_z)
            self._move_z(zs[0])
            time.sleep(0.1)
            cam_temp = self.camera.GetSensorTemperatureCelsius()
            self.log_info = {'fov': self.xy_start + pos_n, 'x' : x, 'y' : y, 'best_z' : offset_z, 'cam_temp' : cam_temp}
            for z_idx, z in enumerate(zs):
                self._move_z(z)
                n_frames = 1
                for c, program in enumerate(self.light_program):
                    self.activate_light_program(program)
                    save = filename + '_XY%s_Z%s_C%s' % (self.xy_start + pos_n,z_idx,c)
                    self.safe_image(save)
                    while self.acquisition.IsActiveOrCompleting:
                        time.sleep(0.1)
                    pbar.update(1)
                    #self.GlobalOnState = False
                    #time.sleep(0.3)
            self.light.GlobalOnState = False
            self._move_z(offset_z)
        while self.data_manager.IsBusy:
            time.sleep(0.1)
        pbar.close()
        
    def camera_snapshot(self,image_source,light_step):
        #self.lightGlobalOnState = False
        #self.camera.SetTargetExposureMilliseconds(exposure)
        bool647 = self.activate_light_program(light_step)
        if bool647 == True:
            side = 1
        else:
            side = 0
        #image_source = self.camera.CreateImageSource(1)
        #self.lightGlobalOnState = True
        im = image_source.GetNextImage().ImageData()
        im = self.quick_crop(im,split=1024,side=side)
        return im
    
    def acquire_single_position(self,pos_n,pos,dirname,filename,pbar=None,z_overide=0):
        self.global_on_lights_off()
        self.camera.BeginView()
        x = pos[0]
        y = pos[1]
        curr_z = self.move_pos_modeled_focus(x,y,oni_auto=True)
        # log position
        self.position_logger(self.xy_start + pos_n, filename)
        offset_z = curr_z - self.offset_z_diff
        zs = self._generate_real_zs(offset_z)
        #image_stack = [] # should organize to TZCYX axes
        image_stack = []
        #image_source = self.camera.CreateImageSource(n_Frames)
        cam_temp = self.camera.GetSensorTemperatureCelsius()
        self.log_info = {'fov': self.xy_start + pos_n, 'x' : x, 'y' : y, 'best_z' : offset_z, 'cam_temp' : cam_temp}
        nframes = len(self.light_program) * len(zs)
        source = self.camera.CreateImageSource(nframes)
        for c, program in enumerate (self.light_program):
            self.lightGlobalOnState = False
            self.camera.SetTargetExposureMilliseconds(self.exposure_program[c])
            channel_stack = []
            self._move_z(zs[0])
            self.lightGlobalOnState = True
            for z in zs:
                self._move_z(z)
                im = self.camera_snapshot(source,program)
                channel_stack.append(im)
                if pbar is not None:
                    pbar.update(1)
            self.lightGlobalOnState = False
            image_stack.append(channel_stack)
        self.light.GlobalOnState = False
        self._move_z(offset_z)
        save_name_prefix = f'{dirname}/{filename}'
        if not os.path.isdir(save_name_prefix):
            os.makedirs(save_name_prefix)
        np.save(f'{save_name_prefix}/{pos_n}.npy',np.asarray(image_stack),allow_pickle=False)
            
            
    
    def quick_crop(self,image,side,split=1024):
        if split==0:
            side = image.shape[1]/2
        else:
            pass
        if side == 0:
            return image[:,:split]
        else:
            return image[:,split:]
    
    
    def acquire_single_position_old(self,pos,dirname,filename,z_overide=0):
        x = pos[0]
        y = pos[1]
        self._move_pos_autofocus(x,y)
        if z_overide == 0:
            curr_z = self._get_z()
            offset_z = curr_z - self.offset_z_diff
        else:
            offset_z = z_overide
        zs = self._generate_real_zs(offset_z)
        for z_idx, z in enumerate(zs):
            self._move_z(z)
            n_frames = 1
            for c, program in enumerate(self.light_program):
                self.activate_light_program(program)
                save = filename + '_Z%s_C%s' % (z_idx,c)
                self.acquisition.Start(dirname,save,1)
                while self.acquisition.IsActiveOrCompleting:
                    time.sleep(0.1)
                #self.GlobalOnState = False
                #time.sleep(0.3)
    
    
    
    # safe from storage problems
    def safe_image(self,save_name):
        try:
            self.acquisition.Start(self.main_dataset_tag,save_name,1)
        except Exception as e:
            print(e)
            slack(f"<!here> Imaging failed. Error {e}")
            slack(str(self.log_info))
            time.sleep(60)
            self.safe_image()
    
    #compatability function
    def run_ND(self,filename):
        self.full_acquisition(filename)
        
    def shutdown(self):
        self.instrument.Disconnect()
        # if data transfer is in progress wait for it to complete before shutting down code
        """
        if self.th.is_alive() == True:
            self.th.join()
        else:
            pass
        """
        