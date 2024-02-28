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
sys.path.append('../utils')
from utils.squid_utils import *
from scipy.signal import find_peaks
from scipy.ndimage.measurements import center_of_mass
from utils import *
import pprint
from sklearn.linear_model import LinearRegression
# Below are imports for Squid
import control.widgets as widgets
import control.camera as camera
import control.core as core
import control.microcontroller as microcontroller
from control._def import *
from squid_control import *


# ----------------------------------------------------------------------------------------
# ONI Nanoimager ghost class definition
# ----------------------------------------------------------------------------------------
class Squid(Microscope):
    # ----------------------------------------------------------------------------------------
    # Initialize and read callibration and configuration files
    # ----------------------------------------------------------------------------------------
    def __init__(self,dataset_tag,config=None,system_name=None, is_simulation = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_info = {}
        self.dataset_tag = dataset_tag
        self.initialize(is_simulation)
        #self.positions = self.oni_config['xy_positions_mm']
        self.xy_start = 0
        self.pp = pprint.PrettyPrinter(indent=4)
        self.control = squid_control()
        
    def initialize(self,is_simulation):
        # load objects
        if is_simulation:
            self.camera = camera.Camera_Simulation(rotate_image_angle=ROTATE_IMAGE_ANGLE,flip_image=FLIP_IMAGE)
            self.microcontroller = microcontroller.Microcontroller_Simulation()
        else:
            try:
                self.camera = camera.Camera(rotate_image_angle=ROTATE_IMAGE_ANGLE,flip_image=FLIP_IMAGE)
                self.camera.open()
            except:
                self.camera = camera.Camera_Simulation(rotate_image_angle=ROTATE_IMAGE_ANGLE,flip_image=FLIP_IMAGE)
                self.camera.open()
                print('! camera not detected, using simulated camera !')
            try:
                self.microcontroller = microcontroller.Microcontroller(version=CONTROLLER_VERSION)
            except:
                print('! Microcontroller not detected, using simulated microcontroller !')
                self.microcontroller = microcontroller.Microcontroller_Simulation()

        # reset the MCU
        self.microcontroller.reset()

        # configure the actuators
        self.microcontroller.configure_actuators()

        self.objectiveStore = ObjectiveStore()
        self.configurationManager = ConfigurationManager('./channel_configurations.xml')
        #self.streamHandler = StreamHandler(display_resolution_scaling=DEFAULT_DISPLAY_CROP/100)
        self.liveController = LiveController(self.camera,self.microcontroller,self.configurationManager)
        self.navigationController = NavigationController(self.microcontroller)
        self.autofocusController = AutoFocusController(self.camera,self.navigationController,self.liveController)

        # set up the camera		
        # self.camera.set_reverse_x(CAMERA_REVERSE_X) # these are not implemented for the cameras in use
        # self.camera.set_reverse_y(CAMERA_REVERSE_Y) # these are not implemented for the cameras in use
        self.camera.set_software_triggered_acquisition() #self.camera.set_continuous_acquisition()
        self.camera.set_callback(self.streamHandler.on_new_frame)
        self.camera.enable_callback()
        if ENABLE_STROBE_OUTPUT:
            self.camera.set_line3_to_exposure_active()
            

        
    def shutdown(self):
        self.navigationController.home()
        self.liveController.stop_live()
        self.camera.close()
        self.microcontroller.close()
    
######################################################
# Below is from oni.py for templating. Not modified
######################################################
    
    
    
    def initialize_crop(self):
        self.crop_params = self.oni_config['cropping']
        self.im_dim = (self.crop_params['height']*2,self.crop_params['width']*2)

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
        #self.current_z = self.get_z()
        
    def get_z(self):
        return self.stage.GetPositionInMicrons(self.stage.Axis.Z)
    
    def get_stage_pos(self):
        x = self.stage.GetPositionInMicrons(self.stage.Axis.X)
        y = self.stage.GetPositionInMicrons(self.stage.Axis.Y)
        z = self.stage.GetPositionInMicrons(self.stage.Axis.Z)
        return (x,y,z)
    
    def _focus_centerofmass(self,img):
        norm = np.divide(img,np.max(img))
        bin_img = np.where(norm > 0.7,1,0)
        cm = center_of_mass(bin_img)
        return cm
    
    def _focus_cam_snapshot(self):
        return nim_image_to_array(self.focus_cam.GetLatestImage())
    
    def coarse_z(self,fast_res,reset_z=True):
        print("Coarse Z focus")
        self.lightGlobalOnState = False
        zs = list(np.arange(self.z_lower_thresh,self.z_upper_thresh,fast_res))
        af_ints = []
        for z in tqdm(zs):
            self.move_z(z)
            af_ints.append(np.max(self._focus_cam_snapshot()))
        best_z = zs[af_ints.index(max(af_ints))]
        best_int = max(af_ints)
        # double check once more
        if best_int < self.oni_config['safe_focus']['af_intensity_thresh']:
            return 0
        if reset_z == True:
            self.move_z(best_z)
        return best_z
        
    def train_focus_model(self):
        # assume you are approx close to perfect z
        # scan +/- 30 microns at 0.25 micron res
        curr_z = self.get_z()
        z_top = curr_z + 30
        z_bottom = curr_z - 30
        # move to bottom. scan up
        z_range = list(np.linspace(z_bottom,z_top,120))
        cms = []
        ints = []
        for z in z_range:
            self.move_z(z)
            im = self._focus_cam_snapshot()
            a = np.max(im)
            c = self._focus_centerofmass(im)
            cms.append(c)
            ints.append(a)
        # get perfect z from intensity
        pfs_z = z_range[ints.index(max(ints))]
        norm_z = [i-pfs_z for i in z_range] # normalize z values in relation to perfect z
        X = np.asarray(cms)
        self.z_model = LinearRegression()
        self.z_model.fit(X,np.asarray(norm_z))
        
    def quick_focus(self):
        im = self._focus_cam_snapshot()
        cm = self._focus_centerofmass(im)
        if np.max(im) < 200:
            # we're way off course. Just do coarse adjustment again
            #self.coarse_z(5.0,0.1)
            self.coarse_z(1.0)
            relative_z = self.z_model.predict(np.asarray([cm]))
            # for some reason when adjusting from coarse again, it requires doing this twice
            current_z = self.get_z()
            pfs_z = current_z - relative_z
            self.move_z(pfs_z)
        relative_z = self.z_model.predict(np.asarray([cm]))[0]
        current_z = self.get_z()
        pfs_z = current_z - relative_z
        self.move_z(pfs_z)
        return pfs_z
    
    def callibrate_autofocus(self):
        #z, _, _ = self.coarse_z(5.0,0.1)
        z = self.coarse_z(1.0)
        self.move_z(z)
        self.train_focus_model()
        
    def callibrate_dapi(self):
        curr_z = self.quick_focus()
        dapi_program = [self.light_program[0]]
        z_top = curr_z + 20
        z_bottom = curr_z - 20
        zs = list(np.arange(z_bottom,z_top,0.5))
        dapi_stack_shape = [1,len(zs),self.im_dim[0],self.im_dim[1]]
        dapi_stack = np.zeros(dapi_stack_shape,dtype=np.uint16)
        for c, program in enumerate (dapi_program):
            self.lightGlobalOnState = False
            exposure = self.exposure_program[c]
            self.camera.SetTargetExposureMilliseconds(exposure)
            bool647 = self.activate_light_program(program)
            if bool647 == True:
                side = 1
            else:
                side = 0
            self.move_z(zs[0])
            time.sleep(0.5)
            for zn, z in tqdm(enumerate(zs),total=len(zs)):
                self.move_z(z)
                if zn == 0:
                    _ = self.camera_snapshot(side,exposure)  # clear buffer
                dapi_stack[c,zn,:,:] = self.camera_snapshot(side,exposure)
            self.lightGlobalOnState = False
        self.move_z(curr_z)
        stdevs = [np.std(dapi_stack[0,i,:,:]) for i in range(len(zs))]
        best_dapi_z = zs[stdevs.index(max(stdevs))]
        self.offset_z = curr_z - best_dapi_z
        print(f'Offset z: {self.offset_z}')
             
    def move_xy_autofocus(self,x,y):
        self.move_xy(x,y)
        z = self.quick_focus()
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
    
    def lasers_off(self):
        for i in range(4):
            self.light[i].Enabled = False
        
    def lasers_on(self):
        for i in range(4):
            self.light[i].Enabled = True
            
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
        self.light.GlobalOnState = True
        return bool_647
        # just remember to turn it off after

    def full_acquisition(self,filename,skip_to=0):
        self.global_on_lights_off()
        try:
            del(self.callib_images) # free up some RAM
            del(self.af_images)
        except:
            pass
        total_frames = len(self.positions) * len(self.light_program) * len(self.relative_zs)
        pbar = tqdm(total=total_frames)
        parent_dir = os.path.join(self.oni_config['save_destination'],self.main_dataset_tag)
        folder = os.path.join(parent_dir,filename)
        # in case this is the first acquisition
        lsm.create_folder_in_drive(folder)
        self.save_dir = folder

        im_shape = (len(self.light_program),
                    len(self.relative_zs),
                    self.im_dim[0],
                    self.im_dim[1]
                    )
                    
        self.image_stack = np.zeros(im_shape,dtype=np.uint16)
        self.light.GlobalOnState = False
        if skip_to > 0:
            positions = self.positions[skip_to:]
            add_to_pos = skip_to
        else:
            positions = self.positions
            add_to_pos = 0
            
        # Callibrate ONI autofocus at first position
        self.move_xy(positions[0][0],positions[0][1])
        
        if self.focus_callib_state == False:
            print("Callibrating autofocus laser")
            self.callibrate_autofocus()
            print("Aligning AF laser with best DAPI focus")
            self.callibrate_dapi()
            self.focus_callib_state = True
        else:
            self.quick_focus()
            self.quick_focus() # do twice just in case
            
        for pos_n, pos in enumerate(positions):
            pos_n += add_to_pos
            self.acquire_single_position(pos_n,pos,filename,pbar=pbar)
        self.light.GlobalOnState = False
        self.lasers_off()
        pbar.close()
        try:
            slack_notify(f'Finished {filename}')
        except:
            pass
    
    def camera_snapshot(self,side,exposure):
        tik = time.time() * 1000 # milliseconds
        im = np.array(self.camera.GetLatestImage().Pixels,dtype=np.uint16).reshape(2048,2048)
        im = self.quick_crop(im,side=side)
        tok = time.time() * 1000
        time_diff = tok-tik
        if time_diff < exposure:
            time.sleep((exposure-time_diff)/1000) # wait approx. till exposure is done.
        return im
    
    def acquire_single_position(self,pos_n,pos,filename,pbar=None):        
        x = pos[0]
        y = pos[1]
        curr_z = self.move_xy_autofocus(x,y)
        # log position
        self.position_logger(self.xy_start + pos_n, filename)
        #offset_z = curr_z - self.offset_z_diff
        best_bio_z = curr_z - self.offset_z
        zs = self._generate_real_zs(best_bio_z)
        cam_temp = self.camera.GetSensorTemperatureCelsius()
        self.log_info = {'fov': self.xy_start + pos_n, 'x' : x, 'y' : y, 'best_z' : curr_z, 'cam_temp' : cam_temp}
        
        for c, program in enumerate (self.light_program):
            self.lightGlobalOnState = False
            exposure = self.exposure_program[c]
            self.camera.SetTargetExposureMilliseconds(exposure)
            bool647 = self.activate_light_program(program)
            if bool647 == True:
                side = 1
            else:
                side = 0
            self.move_z(zs[0])
            time.sleep(0.5)
            for zn, z in enumerate(zs):
                self.move_z(z)
                if zn == 0:
                    _ = self.camera_snapshot(side,exposure)  # clear buffer
                self.image_stack[c,zn,:,:] = self.camera_snapshot(side,exposure)
                if pbar is not None:
                    pbar.update(1)
            self.lightGlobalOnState = False
        self.move_z(curr_z)
        lsm.save_image_stack(self.image_stack,
                             self.save_dir,
                             str(pos_n))
         
    def quick_crop(self,image,side):
        if side == 0:
            corner = self.crop_params['top-left']
        else:
            corner = self.crop_params['top-right']
        im = image[corner[0]*2:(corner[0] + self.crop_params['height'])*2,corner[1]*2:(corner[1] + self.crop_params['width'])*2]
        return im
        
    def shutdown(self):
        self.instrument.Disconnect()
        
    def reboot(self,move_to=None):
        self.shutdown()
        self.initialize_ONI()
        if move_to is not None:
            self.move_xy_autofocus(move_to[0],move_to[1])
            
