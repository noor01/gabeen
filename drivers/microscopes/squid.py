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
sys.path.append('../drivers')
from drivers.microscopes.octopi_research.software.control import gabeen_control as squid
import xml.etree.ElementTree as ET

# ----------------------------------------------------------------------------------------
# ONI Nanoimager ghost class definition
# ----------------------------------------------------------------------------------------
class Squid(Microscope):
    """
    The Squid class represents a microscope called Squid.

    Attributes:
        dataset_tag (str): The tag for the dataset.
        config (Optional): The configuration object.
        system_name (Optional): The name of the system.
        is_simulation (bool): Indicates whether the microscope is in simulation mode.
        log_info (dict): A dictionary to store log information.
        xy_start (int): The starting position for the xy coordinates.
        pp (pprint.PrettyPrinter): A pretty printer object.

    Methods:
        __init__(self, dataset_tag, config=None, system_name=None, is_simulation=False, *args, **kwargs):
            Initializes the Squid microscope object.
        initialize(self, is_simulation):
            Initializes the Squid microscope.
        shutdown(self):
            Shuts down the Squid microscope.
        reboot(self, move_to=None):
            Reboots the Squid microscope.
        get_stage_pos(self):
            Gets the current stage position.
        get_z(self):
            Gets the current z position.
        wait_till_stage_op_complete(self, timeout=None):
            Waits until the stage operation is complete.
        move_xy(self, x, y):
            Moves the stage to the specified xy coordinates.
        move_z(self, z):
            Moves the stage to the specified z position.
        move_xy_autofocus(self, x, y):
            Moves the stage to the specified xy coordinates for autofocus.
        activate_light_program(self, lighting, turn_on=True):
            Activates the light program with the specified lighting intensity.
        turn_lights_off(self):
            Turns off the lights.
        turn_lights_on(self):
            Turns on the lights.
        set_camera_exposure(self, exposure):
            Sets the camera exposure time.
        set_camera_gain(self, gain):
            Sets the camera analog gain.
        stop_camera(self):
            Stops the camera streaming.
        camera_snapshot(self):
            Takes a snapshot using the camera.
        focus_cam_snapshot(self):
            Takes a snapshot using the focus camera.
        stop_focus_camera(self):
            Stops the focus camera streaming.
        AF_laser_on(self):
            Turns on the autofocus laser.
        AF_laser_off(self):
            Turns off the autofocus laser.
        callibrate_autofocus(self):
            Calibrates the autofocus.
        callibrate_dapi(self):
            Calibrates the DAPI focus.
        quick_focus(self):
            Performs quick focus.
        train_focus_model(self):
            Trains the focus model.
        coarse_z(self, step_size_um, reset_z=True):
            Performs coarse z scanning.
        scan_z_to_next_maxima(self, step_size_um):
            Scans z to the next maxima.
        scan_z_to_next_minima(self, step_size_um):
            Scans z to the next minima.
        _focus_centerofmass(self, img):
            Calculates the center of mass for focusing.
        full_acquisition(self, filename, skip_to=0):
            Performs a full acquisition.
        acquire_single_position(self, pos_n, pos, filename, pbar=None):
            Acquires a single position during the acquisition process.
    """
    def __init__(self, dataset_tag, config=None, system_name=None, is_simulation=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_info = {}
        self.dataset_tag = dataset_tag
        self.initialize(is_simulation)
        #self.positions = self.squid_config['xy_positions_mm']
        self.xy_start = 0
        self.pp = pprint.PrettyPrinter(indent=4)
        
    def initialize(self, is_simulation):
        """
        Initializes the Squid microscope.

        Args:
            is_simulation (bool): Indicates whether the microscope is in simulation mode.
        """
        self.squid = squid.OctopiGUI(is_simulation=is_simulation)
        #self.squid.camera.set_pixel_format('MONO16')
        self.AnalogGain=10
        self.set_camera_gain(self.AnalogGain)
        self.crop_width = self.squid.multipointController.crop_width
        self.crop_height = self.squid.multipointController.crop_height
        self.AF_crop_width = self.squid.autofocusController.crop_width
        self.AF_crop_height = self.squid.autofocusController.crop_height
        # prevent joystick actions
        self.squid.navigationController.enable_joystick_button_action = False
        self.focus_callib_state = False
        self.read_channel_config()
            
    def shutdown(self):
        """
        Shuts down the Squid microscope.
        """
        self.squid.closeEvent()
        
    def reboot(self, move_to=None):
        """
        Reboots the Squid microscope.

        Args:
            move_to (Optional): The position to move to after rebooting.
        """
        raise NotImplementedError
        
    ######################################################
    # Stage Control
    ######################################################
        
    def get_stage_pos(self):
        """
        Gets the current stage position.

        Returns:
            Tuple: The current stage position in the format (x, y, z).
        """
        return self.squid.navigationController.get_updated_pos(self.squid.microcontroller)
    
    def get_z(self):
        """
        Gets the current z position.

        Returns:
            float: The current z position.
        """
        _, _, z = self.get_stage_pos()
        return z 
    
    def wait_till_stage_op_complete(self, timeout=None):
        """
        Waits until the stage operation is complete.

        Args:
            timeout (Optional): The timeout value in seconds.
        """
        t0 = time.time()
        while self.squid.navigationController.microcontroller.is_busy():
            time.sleep(0.1)
            t1 = time.time()
            if timeout is not None and t1 - t0 > timeout:
                break
            
    def move_xy(self, x, y):
        """
        Moves the stage to the specified xy coordinates.

        Args:
            x (float): The x coordinate.
            y (float): The y coordinate.
        """
        self.squid.navigationController.move_to(x, y)
        self.wait_till_stage_op_complete()
        self.squid.navigationController.update_pos(self.squid.navigationController.microcontroller)
        
    def move_z(self, z):
        """
        Moves the stage to the specified z position.

        Args:
            z (float): The z position.
        """
        self.squid.navigationController.move_z_to(z)
        self.wait_till_stage_op_complete()
        self.squid.navigationController.update_pos(self.squid.navigationController.microcontroller)
    
    # NOTE: not implemented
    def move_xy_autofocus(self, x, y):
        """
        Moves the stage to the specified xy coordinates for autofocus.

        Args:
            x (float): The x coordinate.
            y (float): The y coordinate.
        """
        raise NotImplementedError
        
    ######################################################
    # Laser Control
    ######################################################
    def activate_light_program(self, lighting, turn_on=True):
        """
        Activates the light program with the specified lighting intensity.

        Args:
            lighting (list): A list of lighting intensities for each laser.
            turn_on (bool): Indicates whether to turn on the lights.
        """
        for i, intensity in enumerate(lighting):
            self.squid.liveController.set_illumination(self.laser_idx_map[i], intensity)
        if turn_on:
            self.turn_lights_on()
    
    def turn_lights_off(self):
        """
        Turns off the lights.
        """
        self.squid.liveController.turn_off_illumination()
        
    def turn_lights_on(self):
        """
        Turns on the lights.
        """
        self.squid.liveController.turn_on_illumination()
    
    ######################################################
    # Camera Control
    ######################################################
    def set_camera_exposure(self, exposure):
        """
        Sets the camera exposure time.

        Args:
            exposure (float): The exposure time in milliseconds.
        """
        self.squid.camera.set_exposure_time(exposure)
        
    def set_camera_gain(self, gain):
        """
        Sets the camera analog gain.

        Args:
            gain (int): The analog gain value.
        """
        self.squid.camera.set_analog_gain(gain)
    
    def stop_camera(self):
        """
        Stops the camera streaming.
        """
        self.squid.camera.stop_streaming()
    
    def camera_snapshot(self):
        """
        Takes a snapshot using the camera.

        Returns:
            ndarray: The captured image.
        """
        if not self.squid.camera.is_streaming:
            self.squid.camera.start_streaming()
        self.squid.camera.send_trigger()
        image = self.squid.camera.read_frame()
        image = self.crop_image(image, self.crop_width, self.crop_height)
        image = self.rotate_and_flip_image(image,
                                           rotate_image_angle=self.squid.camera.rotate_image_angle,
                                           flip_image=self.squid.camera.flip_image)
        return image
    
    ######################################################
    # Autofocus Control
    ######################################################
    
    def focus_cam_snapshot(self):
        """
        Takes a snapshot using the focus camera.

        Returns:
            ndarray: The captured image.
        """
        if not self.squid.camera_focus.is_streaming:
            self.squid.camera_focus.start_streaming()
        self.AF_laser_on()
        self.squid.camera_focus.send_trigger()
        image = self.squid.camera_focus.read_frame()
        self.AF_laser_off()
        image = self.AF_crop_image(image)
        image = self.rotate_and_flip_image(image,
                                           rotate_image_angle=self.squid.camera_focus.rotate_image_angle,
                                           flip_image=self.squid.camera_focus.flip_image)
        return image
    
    def stop_focus_camera(self):
        """
        Stops the focus camera streaming.
        """
        self.squid.camera_focus.stop_streaming()
    
    def AF_laser_on(self):
        """
        Turns on the autofocus laser.
        """
        self.squid.microcontroller.turn_on_AF_laser()
        
    def AF_laser_off(self):
        """
        Turns off the autofocus laser.
        """
        self.squid.microcontroller.turn_off_AF_laser()
    
    def callibrate_autofocus(self):
        """
        Calibrates the autofocus.
        """
        raise NotImplementedError
    
    def callibrate_dapi(self):
        """
        Calibrates the DAPI focus.
        """
        raise NotImplementedError
    
    def quick_focus(self):
        """
        Performs quick focus.
        """
        raise NotImplementedError
    
    def train_focus_model(self):
        """
        Trains the focus model.
        """
        raise NotImplementedError
    
    def coarse_z(self, step_size_um, reset_z=True):
        """
        Performs coarse z scanning.

        Args:
            step_size_um (float): The step size in micrometers.
            reset_z (bool): Indicates whether to reset the z position.
        """
        # start from bottom
        self.move_z(0)
        # move past first spot
        self.scan_z_to_next_maxima(step_size_um)
        self.scan_z_to_next_minima(step_size_um)
        # move past second spot
        self.scan_z_to_next_maxima(step_size_um)
        self.scan_z_to_next_minima(step_size_um)
        # Stay at third spot
        self.scan_z_to_next_maxima(step_size_um)
        
        
    def scan_z_to_next_maxima(self, step_size_um):
        """
        Scans z to the next maxima.

        Args:
            step_size_um (float): The step size in micrometers.
        """
        im = self.focus_cam_snapshot()
        b_i = np.sum(im)
        while True:
            self.move_z(self.get_z() + (step_size_um/1000))
            i = np.sum(self.focus_cam_snapshot())
            if i > b_i:
                pass
            else:
                break # last step was the maxima
    
    def scan_z_to_next_minima(self, step_size_um):
        """
        Scans z to the next minima.

        Args:
            step_size_um (float): The step size in micrometers.
        """
        im = self.focus_cam_snapshot()
        b_i = np.sum(im)
        while True:
            self.move_z(self.get_z() + (step_size_um/1000))
            i = np.sum(self.focus_cam_snapshot())
            if i < b_i:
                pass
            else:
                break # last step was the minima
            
    
    def _focus_centerofmass(self, img):
        """
        Calculates the center of mass for focusing.

        Args:
            img (ndarray): The image.

        Returns:
            Tuple: The center of mass coordinates in the format (x, y).
        """
        norm = np.divide(img, np.max(img))
        bin_img = np.where(norm > 0.7, 1, 0)
        cm = center_of_mass(bin_img)
        return cm
    
    ######################################################
    # Acquisition Control
    ######################################################
    def full_acquisition(self, filename, skip_to=0):
        """
        Performs a full acquisition.

        Args:
            filename (str): The filename for saving the acquired images.
            skip_to (int): The index to skip to during the acquisition process.
        """
        self.turn_lights_off()
        try:
            del(self.callib_images) # free up some RAM
            del(self.af_images)
        except:
            pass
        total_frames = len(self.positions) * len(self.light_program) * len(self.relative_zs)
        pbar = tqdm(total=total_frames)
        parent_dir = os.path.join(self.squid_config['save_destination'], self.main_dataset_tag)
        folder = os.path.join(parent_dir, filename)
        # in case this is the first acquisition
        lsm.create_folder_in_drive(folder)
        self.save_dir = folder

        im_shape = (len(self.light_program),
                    len(self.relative_zs),
                    self.crop_height,
                    self.crop_width
                    )
                    
        self.image_stack = np.zeros(im_shape, dtype=np.uint16)
        if skip_to > 0:
            positions = self.positions[skip_to:]
            add_to_pos = skip_to
        else:
            positions = self.positions
            add_to_pos = 0
            
        # Calibrate ONI autofocus at first position
        self.move_xy(positions[0][0], positions[0][1])
        
        if self.focus_callib_state == False:
            print("Calibrating autofocus laser")
            self.calibrate_autofocus()
            print("Aligning AF laser with best DAPI focus")
            self.calibrate_dapi()
            self.focus_callib_state = True
        else:
            self.quick_focus()
            self.quick_focus() # do twice just in case
            
        for pos_n, pos in enumerate(positions):
            pos_n += add_to_pos
            self.acquire_single_position(pos_n, pos, filename, pbar=pbar)
        self.turn_lights_off()
        pbar.close()
        try:
            slack_notify(f'Finished {filename}')
        except:
            pass
    
    def acquire_single_position(self, pos_n, pos, filename, pbar=None):
        """
        Acquires a single position during the acquisition process.

        Args:
            pos_n (int): The position index.
            pos (Tuple): The xy coordinates of the position.
            filename (str): The filename for saving the acquired images.
            pbar (Optional): The progress bar object.
        """
        x = pos[0]
        y = pos[1]
        curr_z = self.move_xy_autofocus(x, y)
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
    
    def reset_parameters(self):
        raise NotImplementedError
    
    ######################################################
    # Utilities
    ######################################################
    
    def xml_to_dict(self,file_path):
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
        config_file = '../drivers/microscopes/octopi_research/software/channel_configurations.xml'
        channel_config = self.xml_to_dict(config_file)
        self.laser_idx_map = {}
        for mode in channel_config:
            if 'BF' in mode['Name']:
                pass
            else:
                if '405' in mode['Name']:
                    self.laser_idx_map[0] = int(mode['IlluminationSource'])
                elif '488' in mode['Name']:
                    self.laser_idx_map[1] = int(mode['IlluminationSource'])
                elif '561' in mode['Name']:
                    self.laser_idx_map[2] = int(mode['IlluminationSource'])
                elif '638' in mode['Name']:
                    self.laser_idx_map[3] = int(mode['IlluminationSource'])
                elif '730' in mode['Name']:
                    self.laser_idx_map[4] = int(mode['IlluminationSource'])
                    
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