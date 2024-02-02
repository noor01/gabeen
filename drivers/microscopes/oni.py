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

sys.path.append('C:\\Program Files\\OxfordNanoimaging_1.18.3\\.venv\\Lib\\site-packages')
sys.path.append('C:\\Program Files\\OxfordNanoimaging_1.18.3\\nim_python_core\\')
from NimSetup import *
nim_setup(os.getcwd(),'C:\\Program Files\\OxfordNanoimaging_1.18.3')

from NimPyHelpers import *

import time
import cv2
import numpy as np
import json
from tqdm.auto import tqdm
from math import floor
from sklearn import linear_model
from .microscope import Microscope
sys.path.append('../data_processing')
from data_processing import local_storage_manager as lsm
sys.path.append('../telemetry')
from telemetry import slack_notify
from scipy.signal import find_peaks
from utils import *



# ----------------------------------------------------------------------------------------
# ONI Nanoimager ghost class definition
# ----------------------------------------------------------------------------------------
class ONI(Microscope):
    # ----------------------------------------------------------------------------------------
    # Initialize and read callibration and configuration files
    # ----------------------------------------------------------------------------------------
    def __init__(self,dataset_tag,oni_config=None,system_name=None):
        self.log_info = {}
        self.initialize(oni_config,system_name,dataset_tag)
        #self.positions = self.oni_config['xy_positions_mm']
        self.xy_start = 0
        
    def initialize(self,oni_config,system_name,dataset_tag):
        self.oni_config = oni_config
        self.system_name = system_name
        self.initialize_nimOS()
        self.initialize_ONI(dataset_tag)
    
    def initialize_ONI(self,dataset_tag):
        self.input_params_setup(dataset_tag)
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
        self.init_z_pos()
        self.initialize_crop()
        self.camera.SetBinning(self.camera.Binning().b1x1)
        
    def reset_parameters(self,oni_config,dataset_tag):
        self.oni_config = oni_config
        self.xy_start = 0
        self.logs_dir = f'../runs/{self.system_name}/{dataset_tag}'
        self.main_dataset_tag = dataset_tag
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        self.log_file_name = os.path.join(self.logs_dir, 'positional_log.csv')
        if os.path.exists(self.log_file_name):
            pass
        else:
            with open(self.log_file_name,'w+') as log_file:
                log_file.write('filename, pos, x, y, z\n')
        self.start_z = self.oni_config['start_z']
        self.first_start_z = self.start_z
        self.light.FocusLaser.Enabled = True
        self.turn_lights_off()
        self.light.GlobalOnState = True
        self.acquisition.SaveTiffFiles = True
        self.acquisition.RealTimeLocalization= False
        self.init_light_program()
        self.init_xy_pos()
        self.init_z_pos()
    
    def initialize_crop(self):
        self.crop_params = self.oni_config['cropping']
    
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
            

    def input_params_setup(self,dataset_tag):
        self.instrument_name = self.oni_config['microscope_name']
        # save logs in the same folder that the acquisition json file was saved in
        self.logs_dir = f'../runs/{self.system_name}/{dataset_tag}'
        self.main_dataset_tag = dataset_tag
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
        self.log_file_name = os.path.join(self.logs_dir, 'positional_log.csv')
        if os.path.exists(self.log_file_name):
            pass
        else:
            with open(self.log_file_name,'w+') as log_file:
                log_file.write('filename, pos, x, y, z\n')        
        self.start_z = self.oni_config['start_z']
        self.first_start_z = self.start_z
        
    def position_logger(self,pos, filename):
        x = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        y = self.stage.GetPositionInMicrons(self.stage.Axis.Y)
        z = self.stage.GetPositionInMicrons(self.stage.Axis.Z)
        with open(self.log_file_name,mode='a') as log_file:
            log_file.write(filename + ',' + str(pos) + ',' + str(x) + ',' + str(y) + ',' + str(z) + '\n')
    
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
        
    def cal_ONI_AF(self,start_z=0):
        self.global_on_lights_off()
        self.move_z(start_z)
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
                print("Failed to connect to microscope")
                return False
            else:
                print("Connected Successfully!")
                return True

    def get_stage_pos(self):
        x = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        y = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        z = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        return (x,y,z)
        
    def move_xy(self,x,y):
        self.stage.RequestMoveAbsolute(self.stageX,x)
        self.stage.RequestMoveAbsolute(self.stageY,y)
        while self.stage.IsMoving(self.stageX) or self.stage.IsMoving(self.stageY):
            time.sleep(0.1)

    def move_z(self,z):
        if z > 1800:
            z = 1800
            print("WARNING: Z is too high, setting to 1800")
        else:
            pass
        self.stage.RequestMoveAbsolute(self.stageZ,z)
        while self.stage.IsMoving(self.stageZ):
            time.sleep(0.1)
        
    def get_z(self):
        return self.stage.GetPositionInMicrons(self.stage.Axis.Z)
    
    def get_stage_pos(self):
        x = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        y = self.stage.GetPositionInMicrons(self.stage.Axis.Y)
        z = self.stage.GetPositionInMicrons(self.stage.Axis.Z)
        return (x,y,z)
        
    def get_sharpness(self,foc_im):
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
    
    def _oni_quick_focus(self,timeout=5000):
        self.autofocus.Stop()
        self.autofocus.StartSingleShotAutoFocus(timeout)
    
    def _get_n_points(self,lst, N):
        if N <= 0:
            return []
        elif N >= len(lst):
            return lst
        
        indices = [int(i * (len(lst) - 1) / (N - 1)) for i in range(N)]
        return [lst[i] for i in indices]
    
    def callibrate_autofocus(self,force_z=0,num_points_fraction = 0.025,range_max=10,resolution=0.1, search_window=10):
        self.global_on_lights_off()
        self.light.FocusLaser.Enabled = True
        # corners = self.find_extreme_points(self.positions)
        #corners = random.sample(self.positions,num_points)
        #num_points = int(len(self.positions)*num_points_fraction)
        num_points = 25
        corners = self._get_n_points(self.positions,num_points)
        if force_z != 0:
            self.start_z = force_z
        zmax = self.start_z+range_max
        zmin = self.start_z-range_max
        self.corner_vals = {}
        print("Gathering best focus z-positions")
        #self.callib_images = {}
        self.af_images = {}
        for n in tqdm(range(len(corners))):
            self.move_xy(corners[n][0],corners[n][1])
            z = self.get_best_focus_af((zmin,zmax),resolution,search_window=search_window)
            self.corner_vals[n] = [corners[n],z]
        print(self.corner_vals)
        print("Training z-model")
        self.train_z_model()
        print(f'Model score: {self.z_model.score(np.asarray([i[0] for i in self.corner_vals.values()]),np.asarray([i[1] for i in self.corner_vals.values()]))}')
    
    def callibrate_autofocus_debug_version(self,force_z=0,num_points_fraction = 0.025,range_max=10,resolution=0.5, search_window=10):
        self.global_on_lights_off()
        self.light.FocusLaser.Enabled = True
        # corners = self.find_extreme_points(self.positions)
        #corners = random.sample(self.positions,num_points)
        #num_points = int(len(self.positions)*num_points_fraction)
        num_points = 5
        corners = self._get_n_points(self.positions,num_points)
        if force_z != 0:
            self.start_z = force_z
        zmax = self.start_z+range_max
        zmin = self.start_z-range_max
        self.corner_vals = {}
        print("Gathering best focus z-positions")
        self.callib_images = {}
        self.af_images = {}
        for n in tqdm(range(len(corners))):
            self.move_xy(corners[n][0],corners[n][1])
            z,ims,afimgs = self.get_best_focus_dapi((zmin,zmax),resolution,search_window=search_window)
            self.corner_vals[n] = [corners[n],z]
            self.callib_images[n] = ims
            self.af_images[n] = afimgs
        print(self.corner_vals)
        print("Training z-model")
        self.train_z_model()
        print(f'Model score: {self.z_model.score(np.asarray([i[0] for i in self.corner_vals.values()]),np.asarray([i[1] for i in self.corner_vals.values()]))}')
    
    def get_best_focus_af(self,z_range,resolution, search_window=10):
        self.lightGlobalOnState = False
        z1 = min(z_range)
        z2 = max(z_range)
        zs = list(np.arange(z1,z2,resolution))
        af_intensities = []
        af_aux_vals = []
        for z in zs:
            self.move_z(z)
            self.lightGlobalOnState = True
            af_im = self._focus_cam_snapshot()
            af_intensities.append(np.std(af_im))
            af_aux_vals.append(np.max(af_im))
        self.lightGlobalOnState = False
        af_intensities = normalize(np.asarray(af_intensities))
        best_focus_z = self.get_best_focus(zs,af_aux_vals,search_window=search_window)
        return best_focus_z
    
    def get_best_focus_dapi(self,z_range,resolution, search_window=10):
        self.lightGlobalOnState = False
        self.light[0].Enabled = True
        self.camera.SetTargetExposureMilliseconds(self.exposure_program[0])
        z1 = min(z_range)
        z2 = max(z_range)
        zs = list(np.arange(z1,z2,resolution))
        image_stack = []
        af_stack = []
        im_intensities = []
        af_intensities = []
        af_aux_vals = []
        n_Frames = len(zs)
        image_source = self.camera.CreateImageSource(n_Frames)
        for z in zs:
            self.move_z(z)
            self.lightGlobalOnState = True
            focus_dapi_im = self.quick_crop((image_source.GetNextImage().ImageData()),side=0)
            af_im = self._focus_cam_snapshot()
            im_intensities.append(np.max(focus_dapi_im)/np.std(focus_dapi_im))
            af_intensities.append(np.std(af_im))
            af_aux_vals.append(np.max(af_im))
            
            image_stack.append(focus_dapi_im)
            af_stack.append(self._focus_cam_snapshot())
        self.lightGlobalOnState = False
        """
        # determine which image is most in focus
        scores = []
        for im in image_stack:
            #scores.append(self.variance_of_laplacian(im))
            scores.append(self.LAPM(im))
        best_focus_z = zs[scores.index(max(scores))]
        """
        #best_focus_z = self.peak_finding_focus(zs,image_stack)
        im_intensities = normalize(np.asarray(im_intensities))
        af_intensities = normalize(np.asarray(af_intensities))
        best_focus_z = self.get_best_focus(zs,im_intensities,af_intensities,af_aux_vals,search_window=search_window)
        return best_focus_z, image_stack, af_stack
    
    def get_best_focus(self,zs,af_aux_vals, search_window=10):
        best_af_zidx = np.argmax(af_aux_vals)
        best_z = zs[best_af_zidx]
        """
        z1 = np.argmin(np.abs(zs-(best_af_z-search_window)))
        z2 = np.argmin(np.abs(zs-(best_af_z+search_window)))
        search_zs = zs[best_af_zidx:z2]
        masked_is = im_is[best_af_zidx:z2]
        i_z_idx = np.argmax(masked_is)
        best_z = search_zs[i_z_idx]
        print(best_z)
        """
        return best_z
    
    def peak_finding_focus(self,zs,image_stack):
        intensities = []
        for i in range(len(image_stack)):
            intensities.append(np.max(image_stack[i])/np.std(image_stack[i]))
        peaks, _ = find_peaks(intensities, height=np.mean(intensities))
        peak_z_vals = [zs[i] for i in peaks]
        if len(peak_z_vals) > 1:
            return np.mean(peak_z_vals) # best focus is between two layers of cells
        else:
            return peak_z_vals[0]
    
    def variance_of_laplacian(self,image):
        """Compute the Laplacian of the image and then return the focus
        measure, which is simply the variance of the Laplacian."""
        return cv2.Laplacian(image, cv2.CV_64F).var()
    
    def LAPM(self,img):
        """Implements the Modified Laplacian (LAP2) focus measure
        operator. Measures the amount of edges present in the image."""
        # borrowed from: https://github.com/antonio490/Autofocus
        kernel = np.array([-1, 2, -1])
        laplacianX = np.abs(cv2.filter2D(img, -1, kernel))
        laplacianY = np.abs(cv2.filter2D(img, -1, kernel.T))
        return np.mean(laplacianX + laplacianY)
    
    def train_z_model(self):
        X = np.asarray([i[0] for i in self.corner_vals.values()])
        Y = np.asarray([i[1] for i in self.corner_vals.values()])
        self.z_model = linear_model.LinearRegression()
        self.z_model.fit(X,Y)
        #also callibrate autofocus at the current position
        curr_pos = self.get_stage_pos()
        callib_z = self.z_model.predict(np.asarray((curr_pos[0],curr_pos[1])).reshape(1,-1))[0]
        self.cal_ONI_AF(callib_z)
             
    def move_xy_autofocus(self,x,y,move=True,oni_auto=False):
        #z = float(self.z_function(x,y))
        z = self.z_model.predict(np.asarray((x,y)).reshape(1,-1))[0]
        if move == True:
            self.move_xy(x,y)
            self.move_z(z)
            if oni_auto == True:
                self._oni_quick_focus()
            else:
                pass
        else:
            pass
        return z
        
    def init_light_program(self):
        self.light.GloablOnState = False
        json_light_program = self.oni_config['light_program']
        exposure = json_light_program[0]['exposure_ms'] # just use whatever exposure is on the first light program
        self.camera.SetTargetExposureMilliseconds(exposure)
        self.light_program = []
        self.exposure_program = []
        for step in json_light_program:
            _lasers = []
            self.exposure_program.append(step['exposure_ms'])
            for item in step['laser_power']:
                _lasers.append(item)
            self.light_program.append(_lasers)
        self.summed_light_program = list(np.asarray(self.light_program).sum(axis=0))
        # prime the lasers to be ready to go
        for n,power in enumerate(self.summed_light_program):
            self.light[n].PercentPower = power
            self.light[n].Enabled = False
        
    def _grab_starting_pos(self):
        pos = self.oni_config['xy_positions_mm'][0]
        return pos
           
    def _grab_custom_fovs(self):
        positions = self.oni_config['xy_positions_mm']
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
        self.starting_pos = {'x' : self.oni_config['xy_positions_mm'][0][0],
                                 'y' : self.oni_config['xy_positions_mm'][0][1]}
        self.positions = self.oni_config['xy_positions_mm']
        """elif len(self.oni_config['config']['movementOptions']['customXYPositions_mm']) == 1:
            self.acq_mode = 'tilescan'
            self.starting_pos = self._grab_starting_pos()
            #self.start_z = self.starting_pos['z']*1000
            print("Starting position [um]: ")
            print(self.starting_pos)
            n_x = self.oni_config['config']['movementOptions']['numberOfStepsInXY']['x']
            n_y = self.oni_config['config']['movementOptions']['numberOfStepsInXY']['y']
            x_inc_um = self.oni_config['config']['movementOptions']['fovIncrement_mm']['x']*1000
            y_inc_um = self.oni_config['config']['movementOptions']['fovIncrement_mm']['y']*1000
            self.positions = self._make_tiles(self.starting_pos,n_x,n_y,x_inc_um,y_inc_um)
        elif len(self.oni_config['config']['movementOptions']['customXYPositions_mm']) > 1:
            self.acq_mode = 'custom'
            positions_raw = self._grab_custom_fovs()
            self.positions = []
            for n in positions_raw:
                self.positions.append([n['x'],n['y']])"""
                
    def init_z_pos(self):
        self.relative_zs = np.asarray(self.oni_config['z_relative_positions_um'])
        
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

    def full_acquisition(self,filename,skip_to=0):
        #self.autofocus.Stop()
        #self.light.GlobalOnStateStartac = False
        try:
            del(self.callib_images) # free up some RAM
            del(self.af_images)
        except:
            pass
        total_frames = len(self.positions) * len(self.light_program) * len(self.relative_zs)
        pbar = tqdm(total=total_frames)
        
        im_dim = (self.oni_config['num_z_slices'],self.crop_params['height'],self.crop_params['width'])
        filename = os.path.join(self.main_dataset_tag,filename)
        # in case this is the first acquisition
        lsm.create_folder_in_all_drives(filename)
        #self.save_dir = lsm.get_save_path(filename,len(self.positions),im_dim)
        # NOTE: this is a hardcoded hack to temporarily get SQ-001 going
        self.save_dir = 'D:\\SQ-001\\' + filename
        if skip_to > 0:
            positions = self.positions[skip_to:]
            add_to_pos = skip_to
        else:
            positions = self.positions
            add_to_pos = 0
        
        for pos_n, pos in enumerate(positions):
            pos_n += add_to_pos
            self.acquire_single_position(pos_n,pos,self.save_dir,filename,pbar=pbar)
        self.light.GlobalOnState = False
        pbar.close()
        try:
            slack_notify(f'Finished {filename}')
        except:
            pass

    def camera_snapshot(self,image_source=None,light_step_num=0,control_shutter=False):
        if image_source is None:
            image_source = self.camera.CreateImageSource(1)
        light_step = self.light_program[light_step_num]
        return self._camera_snapshot(image_source,light_step,control_shutter=control_shutter)
    
    def _camera_snapshot(self,image_source,light_step,control_shutter=False):
        #self.lightGlobalOnState = False
        #self.camera.SetTargetExposureMilliseconds(exposure)
        bool647 = self.activate_light_program(light_step)
        if bool647 == True:
            side = 1
        else:
            side = 0
        #image_source = self.camera.CreateImageSource(1)
        #self.lightGlobalOnState = True
        if control_shutter == True:
            self.lightGlobalOnState = True
        im = image_source.GetNextImage().ImageData()
        if control_shutter == True:
            self.lightGlobalOnState = False
        im = self.quick_crop(im,side=side)
        return im
    
    def acquire_single_position(self,pos_n,pos,dirname,filename,pbar=None):
        self.global_on_lights_off()
        self.camera.BeginView()
        x = pos[0]
        y = pos[1]
        curr_z = self.move_xy_autofocus(x,y,oni_auto=True)
        # log position
        self.position_logger(self.xy_start + pos_n, filename)
        #offset_z = curr_z - self.offset_z_diff
        zs = self._generate_real_zs(curr_z)
        #image_stack = [] # should organize to TZCYX axes
        image_stack = []
        #image_source = self.camera.CreateImageSource(n_Frames)
        cam_temp = self.camera.GetSensorTemperatureCelsius()
        self.log_info = {'fov': self.xy_start + pos_n, 'x' : x, 'y' : y, 'best_z' : curr_z, 'cam_temp' : cam_temp}
        nframes = len(self.light_program) * len(zs)
        source = self.camera.CreateImageSource(nframes)
        """
        for c, program in enumerate (self.light_program):
            self.lightGlobalOnState = False
            self.camera.SetTargetExposureMilliseconds(self.exposure_program[c])
            channel_stack = []
            self.move_z(zs[0])
            self.lightGlobalOnState = True
            for z in zs:
                self.move_z(z)
                im = self._camera_snapshot(source,program)
                channel_stack.append(im)
                if pbar is not None:
                    pbar.update(1)
            self.lightGlobalOnState = False
            image_stack.append(channel_stack)
        self.light.GlobalOnState = False
        self.move_z(curr_z)
        """
        # nest channels inside of z
        self.move_z(zs[0])
        for z in zs:
            self.move_z(z)
            channel_stack = []
            for c, program in enumerate (self.light_program):
                self.lightGlobalOnState = False
                self.camera.SetTargetExposureMilliseconds(self.exposure_program[c])
                self.lightGlobalOnState = True
                im = self._camera_snapshot(source,program)
                self.lightGlobalOnState = False
                channel_stack.append(im)
                if pbar is not None:
                    pbar.update(1)
            image_stack.append(channel_stack)
        lsm.save_image_stack(image_stack,self.save_dir,pos_n)
            
    def quick_crop(self,image,side):
        if side == 0:
            corner = self.crop_params['top-left']
        else:
            corner = self.crop_params['top-right']
        im = image[corner[0]*2:(corner[0] + self.crop_params['height'])*2,corner[1]*2:(corner[1] + self.crop_params['width'])*2]
        return im
        
    def shutdown(self):
        self.instrument.Disconnect()
        