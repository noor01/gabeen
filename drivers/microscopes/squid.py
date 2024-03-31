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
import octopi_research.software.control.gabeen_control as squid
from configparser import ConfigParser
from octopi_research.software.control._def import CACHED_CONFIG_FILE_PATH
import glob


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
        #self.positions = self.squid_config['xy_positions_mm']
        self.xy_start = 0
        self.pp = pprint.PrettyPrinter(indent=4)
        
    def initialize(self,is_simulation):
        self.squid = squid.OctopiGUI(is_simulation=is_simulation)
        self.squid.camera.set_pixel_format('MONO16')
        self.AnalogGain="10"
        self.set_camera_gain(self.AnalogGain)
        self.crop_width = self.squid.multiPointController.crop_width
        self.crop_height = self.squid.multiPointController.crop_height
        self.AF_crop_width = self.squid.autoFocusController.crop_width
        self.AF_crop_height = self.squid.autoFocusController.crop_height
        # prevent joystick actions
        self.squid.navigationController.enable_joystick_button_action = False
        self.focus_callib_state == False:
            
    def shutdown(self):
        self.squid.closeEvent()
        
    def reboot(self,move_to=None):
        raise NotImplementedError
        
    ######################################################
    # Stage Control
    ######################################################
        
    def get_stage_pos(self):
        return self.squid.navigationController.get_updated_pos(self.navigationController.microcontroller)
    
    def get_z(self):
        _,_,z = self.get_stage_pos()
        return z 
    
    def wait_till_stage_op_complete(self):
        while self.squid.navigationController.microcontroller.is_busy():
            time.sleep(0.1)
            
    def move_xy(self,x,y):
        self.squid.navigationController.move_to(x,y)
        self.wait_till_stage_op_complete()
        self.squid.navigationController.update_pos(self.squid.navigationController.microcontroller)
        
    def move_z(self,z):
        self.squid.navigationController.move_z_to(z)
        self.wait_till_stage_op_complete()
        self.squid.navigationController.update_pos(self.squid.navigationController.microcontroller)
    
    # NOTE: not implemented
    def move_xy_autofocus(self,x,y):
        raise NotImplementedError
        
    ######################################################
    # Laser Control
    ######################################################
    def activate_light_program(self,lighting,turn_on=True):
        # lighting is a list length len(lasers) with each element being the intensity of the laser
        for i, intensity in enumerate(lighting):
            self.squid.liveController.set_illumination(self.laser_idx_map[i],intensity)
        if turn_on:
            self.turn_lights_on()
    
    def turn_lights_off(self):
        self.squid.liveController.turn_off_illumination()
        
    def turn_lights_on(self):
        self.squid.liveController.turn_on_illumination()
    
    ######################################################
    # Camera Control
    ######################################################
    def set_camera_exposure(self,exposure):
        self.squid.camera.set_exposure(exposure) # in milliseconds
        
    def set_camera_gain(self,gain):
        self.squid.camera.set_gain(gain)
        
    def camera_snapshot(self):
        self.squid.camera.send_trigger()
        image = self.squid.camera.read_frame()
        image = self.crop_image(image,self.crop_width,self.crop_height)
        image = self.rotate_and_flip_image(image,
                                           rotate_image_angle=self.squid.camera.rotate_image_angle,
                                           flip_image=self.squid.camera.flip_image)
        return image
    
    ######################################################
    # Autofocus Control
    ######################################################
    
    def focus_cam_snapshot(self):
        self.squid.camera_fc.send_trigger()
        image = self.squid.camera_fc.read_frame()
        image = self.AF_crop_image(image)
        image = self.rotate_and_flip_image(image,
                                           rotate_image_angle=self.squid.camera_fc.rotate_image_angle,
                                           flip_image=self.squid.camera_fc.flip_image)
        return image
    
    def AF_laser_on(self):
        self.squid.liveController.set_illumination(self.AF_LASER,100)
        # //TODO: figure out what the self.AF_LASER is supposed to be
        
    def AF_laser_off(self):
        self.squid.liveController.turn_off_illumination()
        self.squid.liveController.set_illumination(self.AF_LASER,0)
    
    def callibrate_autofocus(self):
        raise NotImplementedError
    
    def callibrate_dapi(self):
        raise NotImplementedError
    
    def quick_focus(self):
        raise NotImplementedError
    
    def train_focus_model(self):
        raise NotImplementedError
    
    def coarse_z(self, fast_res, reset_z=True):
        raise NotImplementedError
    
    def _focus_centerofmass(self,img):
        norm = np.divide(img,np.max(img))
        bin_img = np.where(norm > 0.7,1,0)
        cm = center_of_mass(bin_img)
        return cm
    
    ######################################################
    # Acquisition Control
    ######################################################
    def full_acquisition(self, filename, skip_to=0):
        self.turn_lights_off()
        try:
            del(self.callib_images) # free up some RAM
            del(self.af_images)
        except:
            pass
        total_frames = len(self.positions) * len(self.light_program) * len(self.relative_zs)
        pbar = tqdm(total=total_frames)
        parent_dir = os.path.join(self.squid_config['save_destination'],self.main_dataset_tag)
        folder = os.path.join(parent_dir,filename)
        # in case this is the first acquisition
        lsm.create_folder_in_drive(folder)
        self.save_dir = folder

        im_shape = (len(self.light_program),
                    len(self.relative_zs),
                    self.crop_height,
                    self.crop_width
                    )
                    
        self.image_stack = np.zeros(im_shape,dtype=np.uint16)
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
        self.turn_lights_off()
        pbar.close()
        try:
            slack_notify(f'Finished {filename}')
        except:
            pass
    
    def acquire_single_position(self, pos_n, pos, filename, pbar=None):
        x = pos[0]
        y = pos[1]
        curr_z = self.move_xy_autofocus(x,y)
        best_bio_z = curr_z - self.offset_z
        zs = self._generate_real_zs(best_bio_z)
        cam_temp = self.squid.camera.get_temperature()
        self.log_info = {'fov': self.xy_start + pos_n, 'x' : x, 'y' : y, 'best_z' : curr_z, 'cam_temp' : cam_temp}
        
        for c, program in enumerate (self.light_program):
            self.turn_lights_off()
            exposure = self.exposure_program[c]
            self.set_camera_exposure(exposure)
            self.move_z(zs[0])
            self.wait_till_stage_op_complete()
            self.activate_light_program(program)
            for zn, z in enumerate(zs):
                self.move_z(z)
                self.wait_till_stage_op_complete()
                self.image_stack[c,zn,:,:] = self.camera_snapshot()
                if pbar is not None:
                    pbar.update(1)
            self.turn_lights_off()
        self.move_z(curr_z)
        lsm.save_image_stack(self.image_stack,
                             self.save_dir,
                             str(pos_n))
    
    
    ######################################################
    # Acquisition Configuration
    ######################################################
    def init_xy_pos(self):
        self.starting_pos = {'x' : self.squid_config['xy_positions_mm'][0][0],
                                 'y' : self.squid_config['xy_positions_mm'][0][1]}
        self.positions = self.squid_config['xy_positions_mm']
    
    def init_z_pos(self):
        self.relative_zs = np.asarray(self.squid_config['z_relative_positions_um'])
    
    def init_light_program(self):
        light_program_dict = self.squid_config['light_program']
        self.light_program = []
        self.exposure_program = []
        for step in light_program_dict:
            _lasers = []
            self.exposure_program.append(step['exposure_ms'])
            for item in step['laser_power']:
                _lasers.append(item)
            self.light_program.append(_lasers)
    
    def initialize_params(self):
        raise NotImplementedError
    
    ######################################################
    # Utilities
    ######################################################
    
    def xml_to_dict(file_path):
        # Parse the XML file and get the root element
        tree = ET.parse(file_path)
        root = tree.getroot()

        # List to hold all mode dictionaries
        modes = []

        # Iterate over each 'mode' element in the root
        for mode in root.findall('mode'):
            # Create a dictionary for each 'mode', with attribute names as keys and attribute values as values
            mode_dict = mode.attrib
            # Add the dictionary to the list
            modes.append(mode_dict)

        return modes
    
    def read_channel_config(self):
        config_file = 'octopi_research/software/channel_configurations.xml'
        channel_config = xml_to_dict(config_file)
        self.laser_idx_map = {}
        for mode in channel_config:
            if 'BF' in mode['name']:
                pass
            else:
                if '405' in mode['name']:
                    self.laser_idx_map[0] = mode['IlluminationSource']
                elif '488' in mode['name']:
                    self.laser_idx_map[1] = mode['IlluminationSource']
                elif '561' in mode['name']:
                    self.laser_idx_map[2] = mode['IlluminationSource']
                elif '638' in mode['name']:
                    self.laser_idx_map[3] = mode['IlluminationSource']
                elif '730' in mode['name']:
                    self.laser_idx_map[4] = mode['IlluminationSource']
                    
    def crop_image(self,image,crop_width,crop_height):
        image_height = image.shape[0]
        image_width = image.shape[1]
        roi_left = int(max(image_width/2 - crop_width/2,0))
        roi_right = int(min(image_width/2 + crop_width/2,image_width))
        roi_top = int(max(image_height/2 - crop_height/2,0))
        roi_bottom = int(min(image_height/2 + crop_height/2,image_height))
        image_cropped = image[roi_top:roi_bottom,roi_left:roi_right]
        return image_cropped
    
    def AF_crop_image(self,image):
        return self.crop_image(image,self.AF_crop_width,self.AF_crop_height)
    
    def rotate_and_flip_image(self,image,rotate_image_angle,flip_image):
        ret_image = image.copy()
        if(rotate_image_angle != 0):
            if(rotate_image_angle == 90):
                ret_image = cv2.rotate(ret_image,cv2.ROTATE_90_CLOCKWISE)
            elif(rotate_image_angle == -90):
                ret_image = cv2.rotate(ret_image,cv2.ROTATE_90_COUNTERCLOCKWISE)
            elif(rotate_image_angle == 180):
                ret_image = cv2.rotate(ret_image,cv2.ROTATE_180)
        if(flip_image is not None):
            '''
                flipcode = 0: flip vertically
                flipcode > 0: flip horizontally
                flipcode < 0: flip vertically and horizontally
            '''
            if(flip_image == 'Vertical'):
                ret_image = cv2.flip(ret_image, 0)
            elif(flip_image == 'Horizontal'):
                ret_image = cv2.flip(ret_image, 1)
            elif(flip_image == 'Both'):
                ret_image = cv2.flip(ret_image, -1)

        return ret_image