import control.widgets as widgets
import control.camera as camera
import control.core as core
import control.microcontroller as microcontroller
from control._def import *
import os
from queue import Queue
from threading import Thread, Lock
import threading
import time
import numpy as np
import pyqtgraph as pg
import scipy
import scipy.signal
import cv2
from datetime import datetime

from lxml import etree as ET
from pathlib import Path
import control.utils_config as utils_config

import math
import json
import pandas as pd

import imageio as iio
import pprint
import subprocess
import sys
sys.path.append('../utils')
from squid_utils import *

class squid_control:
    def __init__(self,dataset_tag,config=None,system_name=None, is_simulation = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_info = {}
        self.dataset_tag = dataset_tag
        self.initialize(is_simulation)
        #self.positions = self.oni_config['xy_positions_mm']
        self.xy_start = 0
        self.pp = pprint.PrettyPrinter(indent=4)
        
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

        self.objectiveStore = core.ObjectiveStore()
        self.configurationManager = core.ConfigurationManager('./channel_configurations.xml')
        self.streamHandler = core.StreamHandler(display_resolution_scaling=DEFAULT_DISPLAY_CROP/100)
        self.liveController = core.LiveController(self.camera,self.microcontroller,self.configurationManager)
        self.navigationController = core.NavigationController(self.microcontroller)
        self.autofocusController = core.AutoFocusController(self.camera,self.navigationController,self.liveController)
        self.multipointController = core.MultiPointController(self.camera,self.navigationController,self.liveController,self.autofocusController,self.configurationManager)
        if ENABLE_TRACKING:
            self.trackingController = core.TrackingController(self.camera,self.microcontroller,self.navigationController,self.configurationManager,self.liveController,self.autofocusController,self.imageDisplayWindow)
        self.camera.set_software_triggered_acquisition() #self.camera.set_continuous_acquisition()
        self.camera.set_callback(self.streamHandler.on_new_frame)
        self.camera.enable_callback()
        if ENABLE_STROBE_OUTPUT:
            self.camera.set_line3_to_exposure_active()
        
        self.illumination_on = False
        self.xPos = 0.0
        self.yPos = 0.0
        self.zPos = 0.0
        self.update_pos(self.microcontroller)
    
class LiveController:

    def __init__(self, camera, microcontroller, configurationManager, control_illumination=True, use_internal_timer_for_hardware_trigger=True, for_displacement_measurement=False):
        self.camera = camera
        self.microcontroller = microcontroller
        self.configurationManager = configurationManager
        self.currentConfiguration = None
        self.trigger_mode = None  # Set to None as default
        self.is_live = False
        self.control_illumination = control_illumination
        self.illumination_on = False
        self.use_internal_timer_for_hardware_trigger = use_internal_timer_for_hardware_trigger
        self.for_displacement_measurement = for_displacement_measurement

        self.fps_trigger = 1
        self.timer_trigger_interval = 1.0 / self.fps_trigger

        self.trigger_thread = None
        self.running = False

        self.trigger_ID = -1

        self.fps_real = 0
        self.counter = 0
        self.timestamp_last = 0

        self.display_resolution_scaling = DEFAULT_DISPLAY_CROP / 100

    def turn_on_illumination(self):
        self.microcontroller.turn_on_illumination()
        self.illumination_on = True

    def turn_off_illumination(self):
        self.microcontroller.turn_off_illumination()
        self.illumination_on = False

    def set_illumination(self, illumination_source, intensity):
        if illumination_source < 10:  # LED matrix
            self.microcontroller.set_illumination_led_matrix(illumination_source, r=(intensity / 100) * LED_MATRIX_R_FACTOR, g=(intensity / 100) * LED_MATRIX_G_FACTOR, b=(intensity / 100) * LED_MATRIX_B_FACTOR)
        else:
            self.microcontroller.set_illumination(illumination_source, intensity)

    def start_live(self):
        self.is_live = True
        self.camera.is_live = True
        self.camera.start_streaming()
        if self.trigger_mode == "SOFTWARE" or (self.trigger_mode == "HARDWARE" and self.use_internal_timer_for_hardware_trigger):
            self._start_triggered_acquisition()
        if self.for_displacement_measurement:
            self.microcontroller.set_pin_level(MCU_PINS.AF_LASER, 1)

    def stop_live(self):
        self.is_live = False
        self.camera.is_live = False
        if hasattr(self.camera, 'stop_exposure'):
            self.camera.stop_exposure()
        if self.trigger_mode in ["SOFTWARE", "HARDWARE"] and self.use_internal_timer_for_hardware_trigger:
            self._stop_triggered_acquisition()
        if self.trigger_mode == "CONTINUOUS":
            self.camera.stop_streaming()
        if self.control_illumination:
            self.turn_off_illumination()
        if self.for_displacement_measurement:
            self.microcontroller.set_pin_level(MCU_PINS.AF_LASER, 0)

    def trigger_acquisition(self):
        # This method gets called repeatedly by the timer thread
        while self.running:
            start_time = time.time()
            if self.trigger_mode == "SOFTWARE":
                if self.control_illumination and not self.illumination_on:
                    self.turn_on_illumination()
                self.trigger_ID += 1
                self.camera.send_trigger()
            elif self.trigger_mode == "HARDWARE":
                self.trigger_ID += 1
                self.microcontroller.send_hardware_trigger(control_illumination=True, illumination_on_time_us=self.camera.exposure_time * 1000)
            time_to_wait = self.timer_trigger_interval - (time.time() - start_time)
            if time_to_wait > 0:
                time.sleep(time_to_wait)

    def _start_triggered_acquisition(self):
        self.running = True
        self.trigger_thread = threading.Thread(target=self.trigger_acquisition)
        self.trigger_thread.start()

    def _stop_triggered_acquisition(self):
        self.running = False
        if self.trigger_thread is not None:
            self.trigger_thread.join()

    def set_trigger_mode(self, mode):
        """
        Set the camera trigger mode.
        :param mode: One of 'SOFTWARE', 'HARDWARE', or 'CONTINUOUS'
        """
        # Stop any ongoing acquisition if the mode is changing
        if self.trigger_mode != mode and self.is_live:
            self._stop_triggered_acquisition()

        self.trigger_mode = mode

        # Configure the camera and microcontroller based on the new mode
        if mode == "SOFTWARE":
            self.camera.set_software_triggered_acquisition()
        elif mode == "HARDWARE":
            self.camera.set_hardware_triggered_acquisition()
            self.microcontroller.set_strobe_delay_us(self.camera.strobe_delay_us)
        elif mode == "CONTINUOUS":
            self.camera.set_continuous_acquisition()

        # Restart acquisition if live view was previously active
        if self.is_live:
            self.start_live()

    def set_trigger_fps(self, fps):
        """
        Set the frames per second for trigger.
        :param fps: The desired FPS for acquisition triggering.
        """
        self.fps_trigger = fps
        self.timer_trigger_interval = 1.0 / self.fps_trigger

        # Restart the triggered acquisition with the new interval if necessary
        if self.is_live and (self.trigger_mode == "SOFTWARE" or (self.trigger_mode == "HARDWARE" and self.use_internal_timer_for_hardware_trigger)):
            self._restart_triggered_acquisition()

    def _restart_triggered_acquisition(self):
        """
        Helper method to restart triggered acquisition with new parameters.
        """
        self._stop_triggered_acquisition()
        self._start_triggered_acquisition()

    def set_microscope_mode(self, configuration):
        """
        Set the microscope configuration.
        :param configuration: A configuration object with attributes like exposure_time, analog_gain, etc.
        """
        self.currentConfiguration = configuration

        # Temporarily stop live view to change settings
        was_live = self.is_live
        if was_live:
            self.stop_live()

        # Apply configuration settings to camera and illumination
        self.camera.set_exposure_time(configuration.exposure_time)
        self.camera.set_analog_gain(configuration.analog_gain)

        if self.control_illumination:
            self.set_illumination(configuration.illumination_source, configuration.illumination_intensity)

        # Restart live view if it was previously active
        if was_live:
            if self.control_illumination:
                self.turn_on_illumination()
            self.timer_trigger.start()
    
    def on_new_frame(self):
        if self.fps_trigger <= 5:
            if self.control_illumination and self.illumination_on == True:
                self.turn_off_illumination()

    def set_display_resolution_scaling(self, display_resolution_scaling):
        self.display_resolution_scaling = display_resolution_scaling/100
    

class NavigationController:
    def __init__(self, microcontroller):
        self.microcontroller = microcontroller
        self.x_pos_mm = 0
        self.y_pos_mm = 0
        self.z_pos_mm = 0
        self.theta_pos_rad = 0
        self.enable_joystick_button_action = True
        self.x_microstepping = MICROSTEPPING_DEFAULT_X
        self.y_microstepping = MICROSTEPPING_DEFAULT_Y
        self.z_microstepping = MICROSTEPPING_DEFAULT_Z
        self.click_to_move = False
        self.theta_microstepping = MICROSTEPPING_DEFAULT_THETA

        # Assuming set_callback is a method to register a callback for position updates
        # You might need to adjust or implement this functionality in your microcontroller class
        self.microcontroller.set_callback(self.update_pos)

    def update_pos(self):
        # This method should be called by the microcontroller whenever there's an update
        x_pos, y_pos, z_pos, theta_pos = self.microcontroller.get_pos()
        # Update the position attributes (conversion from steps to mm or radians may vary)
        self.z_pos = z_pos
        # calculate position in mm or rad
        if USE_ENCODER_X:
            self.x_pos_mm = x_pos*ENCODER_POS_SIGN_X*ENCODER_STEP_SIZE_X_MM
        else:
            self.x_pos_mm = x_pos*STAGE_POS_SIGN_X*(SCREW_PITCH_X_MM/(self.x_microstepping*FULLSTEPS_PER_REV_X))
        if USE_ENCODER_Y:
            self.y_pos_mm = y_pos*ENCODER_POS_SIGN_Y*ENCODER_STEP_SIZE_Y_MM
        else:
            self.y_pos_mm = y_pos*STAGE_POS_SIGN_Y*(SCREW_PITCH_Y_MM/(self.y_microstepping*FULLSTEPS_PER_REV_Y))
        if USE_ENCODER_Z:
            self.z_pos_mm = z_pos*ENCODER_POS_SIGN_Z*ENCODER_STEP_SIZE_Z_MM
        else:
            self.z_pos_mm = z_pos*STAGE_POS_SIGN_Z*(SCREW_PITCH_Z_MM/(self.z_microstepping*FULLSTEPS_PER_REV_Z))
        if USE_ENCODER_THETA:
            self.theta_pos_rad = theta_pos*ENCODER_POS_SIGN_THETA*ENCODER_STEP_SIZE_THETA
        else:
            self.theta_pos_rad = theta_pos*STAGE_POS_SIGN_THETA*(2*math.pi/(self.theta_microstepping*FULLSTEPS_PER_REV_THETA))

    def move_x(self,delta):
        self.microcontroller.move_x_usteps(int(delta/(SCREW_PITCH_X_MM/(self.x_microstepping*FULLSTEPS_PER_REV_X))))

    def move_y(self,delta):
        self.microcontroller.move_y_usteps(int(delta/(SCREW_PITCH_Y_MM/(self.y_microstepping*FULLSTEPS_PER_REV_Y))))

    def move_z(self,delta):
        self.microcontroller.move_z_usteps(int(delta/(SCREW_PITCH_Z_MM/(self.z_microstepping*FULLSTEPS_PER_REV_Z))))

    def move_x_to(self,delta):
        self.microcontroller.move_x_to_usteps(STAGE_MOVEMENT_SIGN_X*int(delta/(SCREW_PITCH_X_MM/(self.x_microstepping*FULLSTEPS_PER_REV_X))))

    def move_y_to(self,delta):
        self.microcontroller.move_y_to_usteps(STAGE_MOVEMENT_SIGN_Y*int(delta/(SCREW_PITCH_Y_MM/(self.y_microstepping*FULLSTEPS_PER_REV_Y))))

    def move_z_to(self,delta):
        self.microcontroller.move_z_to_usteps(STAGE_MOVEMENT_SIGN_Z*int(delta/(SCREW_PITCH_Z_MM/(self.z_microstepping*FULLSTEPS_PER_REV_Z))))

    def move_x_usteps(self,usteps):
        self.microcontroller.move_x_usteps(usteps)

    def move_y_usteps(self,usteps):
        self.microcontroller.move_y_usteps(usteps)

    def move_z_usteps(self,usteps):
        self.microcontroller.move_z_usteps(usteps)
    
    def home_x(self):
        self.microcontroller.home_x()

    def home_y(self):
        self.microcontroller.home_y()

    def home_z(self):
        self.microcontroller.home_z()

    def home_theta(self):
        self.microcontroller.home_theta()

    def home_xy(self):
        self.microcontroller.home_xy()

    def zero_x(self):
        self.microcontroller.zero_x()

    def zero_y(self):
        self.microcontroller.zero_y()

    def zero_z(self):
        self.microcontroller.zero_z()

    def zero_theta(self):
        self.microcontroller.zero_tehta()

    def home(self):
        pass

    def set_x_limit_pos_mm(self,value_mm):
        if STAGE_MOVEMENT_SIGN_X > 0:
            self.microcontroller.set_lim(LIMIT_CODE.X_POSITIVE,int(value_mm/(SCREW_PITCH_X_MM/(self.x_microstepping*FULLSTEPS_PER_REV_X))))
        else:
            self.microcontroller.set_lim(LIMIT_CODE.X_NEGATIVE,STAGE_MOVEMENT_SIGN_X*int(value_mm/(SCREW_PITCH_X_MM/(self.x_microstepping*FULLSTEPS_PER_REV_X))))

    def set_x_limit_neg_mm(self,value_mm):
        if STAGE_MOVEMENT_SIGN_X > 0:
            self.microcontroller.set_lim(LIMIT_CODE.X_NEGATIVE,int(value_mm/(SCREW_PITCH_X_MM/(self.x_microstepping*FULLSTEPS_PER_REV_X))))
        else:
            self.microcontroller.set_lim(LIMIT_CODE.X_POSITIVE,STAGE_MOVEMENT_SIGN_X*int(value_mm/(SCREW_PITCH_X_MM/(self.x_microstepping*FULLSTEPS_PER_REV_X))))

    def set_y_limit_pos_mm(self,value_mm):
        if STAGE_MOVEMENT_SIGN_Y > 0:
            self.microcontroller.set_lim(LIMIT_CODE.Y_POSITIVE,int(value_mm/(SCREW_PITCH_Y_MM/(self.y_microstepping*FULLSTEPS_PER_REV_Y))))
        else:
            self.microcontroller.set_lim(LIMIT_CODE.Y_NEGATIVE,STAGE_MOVEMENT_SIGN_Y*int(value_mm/(SCREW_PITCH_Y_MM/(self.y_microstepping*FULLSTEPS_PER_REV_Y))))

    def set_y_limit_neg_mm(self,value_mm):
        if STAGE_MOVEMENT_SIGN_Y > 0:
            self.microcontroller.set_lim(LIMIT_CODE.Y_NEGATIVE,int(value_mm/(SCREW_PITCH_Y_MM/(self.y_microstepping*FULLSTEPS_PER_REV_Y))))
        else:
            self.microcontroller.set_lim(LIMIT_CODE.Y_POSITIVE,STAGE_MOVEMENT_SIGN_Y*int(value_mm/(SCREW_PITCH_Y_MM/(self.y_microstepping*FULLSTEPS_PER_REV_Y))))

    def set_z_limit_pos_mm(self,value_mm):
        if STAGE_MOVEMENT_SIGN_Z > 0:
            self.microcontroller.set_lim(LIMIT_CODE.Z_POSITIVE,int(value_mm/(SCREW_PITCH_Z_MM/(self.z_microstepping*FULLSTEPS_PER_REV_Z))))
        else:
            self.microcontroller.set_lim(LIMIT_CODE.Z_NEGATIVE,STAGE_MOVEMENT_SIGN_Z*int(value_mm/(SCREW_PITCH_Z_MM/(self.z_microstepping*FULLSTEPS_PER_REV_Z))))

    def set_z_limit_neg_mm(self,value_mm):
        if STAGE_MOVEMENT_SIGN_Z > 0:
            self.microcontroller.set_lim(LIMIT_CODE.Z_NEGATIVE,int(value_mm/(SCREW_PITCH_Z_MM/(self.z_microstepping*FULLSTEPS_PER_REV_Z))))
        else:
            self.microcontroller.set_lim(LIMIT_CODE.Z_POSITIVE,STAGE_MOVEMENT_SIGN_Z*int(value_mm/(SCREW_PITCH_Z_MM/(self.z_microstepping*FULLSTEPS_PER_REV_Z))))
    
    def move_to(self,x_mm,y_mm):
        self.move_x_to(x_mm)
        self.move_y_to(y_mm)
            
            
class SlidePositionControlWorker:
    def __init__(self, slidePositionController, home_x_and_y_separately=False):
        self.slidePositionController = slidePositionController
        self.navigationController = slidePositionController.navigationController
        self.microcontroller = self.navigationController.microcontroller
        self.liveController = self.slidePositionController.liveController
        self.home_x_and_y_separately = home_x_and_y_separately

    def wait_till_operation_is_completed(self, timestamp_start, timeout_limit_s, sleep_time_s=0.1):
        while self.microcontroller.is_busy():
            time.sleep(sleep_time_s)
            if time.time() - timestamp_start > timeout_limit_s:
                print('Error - slide position switching timeout, the program will exit')
                exit()

    def move_to_slide_loading_position(self):
        def task():
            was_live = self.liveController.is_live
            if was_live:
                self.liveController.stop_live()

            # retract z
            timestamp_start = time.time()
            self.slidePositionController.z_pos = self.navigationController.z_pos # zpos at the beginning of the scan
            self.navigationController.move_z_to(OBJECTIVE_RETRACTED_POS_MM)
            self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
            print('z retracted')
            self.slidePositionController.objective_retracted = True
            
            # move to position
            # for well plate
            if self.slidePositionController.is_for_wellplate:
                # reset limits
                self.navigationController.set_x_limit_pos_mm(100)
                self.navigationController.set_x_limit_neg_mm(-100)
                self.navigationController.set_y_limit_pos_mm(100)
                self.navigationController.set_y_limit_neg_mm(-100)
                # home for the first time
                if self.slidePositionController.homing_done == False:
                    print('running homing first')
                    timestamp_start = time.time()
                    # x needs to be at > + 20 mm when homing y
                    self.navigationController.move_x(20)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    # home y
                    self.navigationController.home_y()
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.zero_y()
                    # home x
                    self.navigationController.home_x()
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.zero_x()
                    self.slidePositionController.homing_done = True
                # homing done previously
                else:
                    timestamp_start = time.time()
                    self.navigationController.move_x_to(20)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.move_y_to(SLIDE_POSITION.LOADING_Y_MM)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.move_x_to(SLIDE_POSITION.LOADING_X_MM)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                # set limits again
                self.navigationController.set_x_limit_pos_mm(SOFTWARE_POS_LIMIT.X_POSITIVE)
                self.navigationController.set_x_limit_neg_mm(SOFTWARE_POS_LIMIT.X_NEGATIVE)
                self.navigationController.set_y_limit_pos_mm(SOFTWARE_POS_LIMIT.Y_POSITIVE)
                self.navigationController.set_y_limit_neg_mm(SOFTWARE_POS_LIMIT.Y_NEGATIVE)
            else:

                # for glass slide
                if self.slidePositionController.homing_done == False or SLIDE_POTISION_SWITCHING_HOME_EVERYTIME:
                    if self.home_x_and_y_separately:
                        timestamp_start = time.time()
                        self.navigationController.home_x()
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.zero_x()
                        self.navigationController.move_x(SLIDE_POSITION.LOADING_X_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.home_y()
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.zero_y()
                        self.navigationController.move_y(SLIDE_POSITION.LOADING_Y_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    else:
                        timestamp_start = time.time()
                        self.navigationController.home_xy()
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.zero_x()
                        self.navigationController.zero_y()
                        self.navigationController.move_x(SLIDE_POSITION.LOADING_X_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.move_y(SLIDE_POSITION.LOADING_Y_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.slidePositionController.homing_done = True
                else:
                    timestamp_start = time.time()
                    self.navigationController.move_y(SLIDE_POSITION.LOADING_Y_MM-self.navigationController.y_pos_mm)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.move_x(SLIDE_POSITION.LOADING_X_MM-self.navigationController.x_pos_mm)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)

            if was_live:
                self.liveController.start_live()

            # Notify that the operation is finished. This could be a direct method call
            # or triggering a callback.
            print("Moved to slide loading position.")

        threading.Thread(target=task).start()

    def move_to_slide_scanning_position(self):
        def task():
            was_live = self.liveController.is_live
            if was_live:
                self.liveController.stop_live()

            # move to position
            # for well plate
            if self.slidePositionController.is_for_wellplate:
                # home for the first time
                if self.slidePositionController.homing_done == False:
                    timestamp_start = time.time()

                    # x needs to be at > + 20 mm when homing y
                    self.navigationController.move_x(20)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    # home y
                    self.navigationController.home_y()
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.zero_y()
                    # home x
                    self.navigationController.home_x()
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.zero_x()
                    self.slidePositionController.homing_done = True
                    # move to scanning position
                    self.navigationController.move_x_to(SLIDE_POSITION.SCANNING_X_MM)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)

                    self.navigationController.move_y_to(SLIDE_POSITION.SCANNING_Y_MM)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    
                else:
                    timestamp_start = time.time()
                    self.navigationController.move_x_to(SLIDE_POSITION.SCANNING_X_MM)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.move_y_to(SLIDE_POSITION.SCANNING_Y_MM)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
            else:
                if self.slidePositionController.homing_done == False or SLIDE_POTISION_SWITCHING_HOME_EVERYTIME:
                    if self.home_x_and_y_separately:
                        timestamp_start = time.time()
                        self.navigationController.home_y()
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.zero_y()
                        self.navigationController.move_y(SLIDE_POSITION.SCANNING_Y_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.home_x()
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.zero_x()
                        self.navigationController.move_x(SLIDE_POSITION.SCANNING_X_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    else:
                        timestamp_start = time.time()
                        self.navigationController.home_xy()
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.zero_x()
                        self.navigationController.zero_y()
                        self.navigationController.move_y(SLIDE_POSITION.SCANNING_Y_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                        self.navigationController.move_x(SLIDE_POSITION.SCANNING_X_MM)
                        self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.slidePositionController.homing_done = True
                else:
                    timestamp_start = time.time()
                    self.navigationController.move_y(SLIDE_POSITION.SCANNING_Y_MM-self.navigationController.y_pos_mm)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                    self.navigationController.move_x(SLIDE_POSITION.SCANNING_X_MM-self.navigationController.x_pos_mm)
                    self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)

            # restore z
            if self.slidePositionController.objective_retracted:
                _usteps_to_clear_backlash = max(160,20*self.navigationController.z_microstepping)
                self.navigationController.microcontroller.move_z_to_usteps(self.slidePositionController.z_pos - STAGE_MOVEMENT_SIGN_Z*_usteps_to_clear_backlash)
                self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                self.navigationController.move_z_usteps(_usteps_to_clear_backlash)
                self.wait_till_operation_is_completed(timestamp_start, SLIDE_POTISION_SWITCHING_TIMEOUT_LIMIT_S)
                self.slidePositionController.objective_retracted = False
                print('z position restored')

            if was_live:
                self.liveController.start_live()

            # Notify that the operation is finished. This could be a direct method call
            # or triggering a callback.
            print("Moved to slide scanning position.")
        self.slidePositionController.slide_scanning_position_reached = True
        threading.Thread(target=task).start()
            
            
class SlidePositionController:
    def __init__(self, navigationController, liveController, is_for_wellplate=False):
        self.navigationController = navigationController
        self.liveController = liveController
        self.is_for_wellplate = is_for_wellplate
        self.retract_objective_before_moving = RETRACT_OBJECTIVE_BEFORE_MOVING_TO_LOADING_POSITION
        self.slide_loading_position_reached = False
        self.slide_scanning_position_reached = False
        self.homing_done = False
        self.objective_retracted = False

    def move_to_slide_loading_position(self):
        self.thread = Thread(target=self._move_to_slide_loading_position_worker)
        self.thread.start()

    def _move_to_slide_loading_position_worker(self):
        # Simulating the movement to slide loading position
        if self.retract_objective_before_moving and not self.objective_retracted:
            self.navigationController.retract_objective()
            self.objective_retracted = True
        self.navigationController.move_to_loading_position()
        self.slide_loading_position_reached = True
        self.slot_stop_live()
        self.slot_resume_live()

    def move_to_slide_scanning_position(self):
        self.thread = Thread(target=self._move_to_slide_scanning_position_worker)
        self.thread.start()
        self.clear_slide()

    def _move_to_slide_scanning_position_worker(self):
        # Simulating the movement to slide scanning position
        if self.objective_retracted:
            self.navigationController.deploy_objective()
            self.objective_retracted = False
        self.navigationController.move_to_scanning_position()
        self.slide_scanning_position_reached = True
        self.slot_stop_live()
        self.slot_resume_live()

    def slot_stop_live(self):
        # Directly call the method on liveController to stop live view
        self.liveController.stop_live()

    def slot_resume_live(self):
        # Directly call the method on liveController to resume live view
        self.liveController.start_live()

    def clear_slide(self):
        # Simulating clearing the slide
        self.navigationController.clear_slide_area()
        print("Slide cleared.")
            
class Configuration:
    def __init__(self,mode_id=None,name=None,camera_sn=None,exposure_time=None,analog_gain=None,illumination_source=None,illumination_intensity=None, z_offset=None, pixel_format=None, _pixel_format_options=None):
        self.id = mode_id
        self.name = name
        self.exposure_time = exposure_time
        self.analog_gain = analog_gain
        self.illumination_source = illumination_source
        self.illumination_intensity = illumination_intensity
        self.camera_sn = camera_sn
        self.z_offset = z_offset
        self.pixel_format = pixel_format
        if self.pixel_format is None:
            self.pixel_format = "default"
        self._pixel_format_options = _pixel_format_options
        if _pixel_format_options is None:
            self._pixel_format_options = self.pixel_format
    
class AutofocusWorker:
    # signal_current_configuration = Signal(Configuration)

    def __init__(self,autofocusController):
        self.autofocusController = autofocusController

        self.camera = self.autofocusController.camera
        self.microcontroller = self.autofocusController.navigationController.microcontroller
        self.navigationController = self.autofocusController.navigationController
        self.liveController = self.autofocusController.liveController

        self.N = self.autofocusController.N
        self.deltaZ = self.autofocusController.deltaZ
        self.deltaZ_usteps = self.autofocusController.deltaZ_usteps
        
        self.crop_width = self.autofocusController.crop_width
        self.crop_height = self.autofocusController.crop_height

    def run(self):
        self.run_autofocus()
        self.finished.emit()

    def wait_till_operation_is_completed(self):
        while self.microcontroller.is_busy():
            time.sleep(SLEEP_TIME_S)

    def run_autofocus(self):
        # @@@ to add: increase gain, decrease exposure time
        # @@@ can move the execution into a thread - done 08/21/2021
        focus_measure_vs_z = [0]*self.N
        focus_measure_max = 0

        z_af_offset_usteps = self.deltaZ_usteps*round(self.N/2)
        # self.navigationController.move_z_usteps(-z_af_offset_usteps) # combine with the back and forth maneuver below
        # self.wait_till_operation_is_completed()

        # maneuver for achiving uniform step size and repeatability when using open-loop control
        # can be moved to the firmware
        _usteps_to_clear_backlash = max(160,20*self.navigationController.z_microstepping)
        self.navigationController.move_z_usteps(-_usteps_to_clear_backlash-z_af_offset_usteps)
        self.wait_till_operation_is_completed()
        self.navigationController.move_z_usteps(_usteps_to_clear_backlash)
        self.wait_till_operation_is_completed()

        steps_moved = 0
        for i in range(self.N):
            self.navigationController.move_z_usteps(self.deltaZ_usteps)
            self.wait_till_operation_is_completed()
            steps_moved = steps_moved + 1
            # trigger acquisition (including turning on the illumination)
            if self.liveController.trigger_mode == TriggerMode.SOFTWARE:
                self.liveController.turn_on_illumination()
                self.wait_till_operation_is_completed()
                self.camera.send_trigger()
            elif self.liveController.trigger_mode == TriggerMode.HARDWARE:
                self.microcontroller.send_hardware_trigger(control_illumination=True,illumination_on_time_us=self.camera.exposure_time*1000)
            # read camera frame
            image = self.camera.read_frame()
            if image is None:
                continue
            # tunr of the illumination if using software trigger
            if self.liveController.trigger_mode == TriggerMode.SOFTWARE:
                self.liveController.turn_off_illumination()
            image = utils.crop_image(image,self.crop_width,self.crop_height)
            image = utils.rotate_and_flip_image(image,rotate_image_angle=self.camera.rotate_image_angle,flip_image=self.camera.flip_image)

            timestamp_0 = time.time()
            focus_measure = utils.calculate_focus_measure(image,FOCUS_MEASURE_OPERATOR)
            timestamp_1 = time.time()
            print('             calculating focus measure took ' + str(timestamp_1-timestamp_0) + ' second')
            focus_measure_vs_z[i] = focus_measure
            print(i,focus_measure)
            focus_measure_max = max(focus_measure, focus_measure_max)
            if focus_measure < focus_measure_max*AF.STOP_THRESHOLD:
                break

        # move to the starting location
        # self.navigationController.move_z_usteps(-steps_moved*self.deltaZ_usteps) # combine with the back and forth maneuver below
        # self.wait_till_operation_is_completed()

        # maneuver for achiving uniform step size and repeatability when using open-loop control
        self.navigationController.move_z_usteps(-_usteps_to_clear_backlash-steps_moved*self.deltaZ_usteps)
        # determine the in-focus position
        idx_in_focus = focus_measure_vs_z.index(max(focus_measure_vs_z))
        self.wait_till_operation_is_completed()
        self.navigationController.move_z_usteps(_usteps_to_clear_backlash+(idx_in_focus+1)*self.deltaZ_usteps)
        self.wait_till_operation_is_completed()

        # move to the calculated in-focus position
        # self.navigationController.move_z_usteps(idx_in_focus*self.deltaZ_usteps)
        # self.wait_till_operation_is_completed() # combine with the movement above
        if idx_in_focus == 0:
            print('moved to the bottom end of the AF range')
        if idx_in_focus == self.N-1:
            print('moved to the top end of the AF range')
    
class ObjectiveStore:
    def __init__(self, objectives_dict = OBJECTIVES, default_objective = DEFAULT_OBJECTIVE):
        self.objectives_dict = objectives_dict
        self.default_objective = default_objective
        self.current_objective = default_objective
    
class ConfigurationManager:
    def __init__(self,filename="channel_configurations.xml"):
        self.config_filename = filename
        self.configurations = []
        self.read_configurations()
        
    def save_configurations(self):
        self.write_configuration(self.config_filename)

    def write_configuration(self,filename):
        self.config_xml_tree.write(filename, encoding="utf-8", xml_declaration=True, pretty_print=True)

    def read_configurations(self):
        if(os.path.isfile(self.config_filename)==False):
            utils_config.generate_default_configuration(self.config_filename)
        self.config_xml_tree = ET.parse(self.config_filename)
        self.config_xml_tree_root = self.config_xml_tree.getroot()
        self.num_configurations = 0
        for mode in self.config_xml_tree_root.iter('mode'):
            self.num_configurations = self.num_configurations + 1
            self.configurations.append(
                Configuration(
                    mode_id = mode.get('ID'),
                    name = mode.get('Name'),
                    exposure_time = float(mode.get('ExposureTime')),
                    analog_gain = float(mode.get('AnalogGain')),
                    illumination_source = int(mode.get('IlluminationSource')),
                    illumination_intensity = float(mode.get('IlluminationIntensity')),
                    camera_sn = mode.get('CameraSN'),
                    z_offset = float(mode.get('ZOffset')),
                    pixel_format = mode.get('PixelFormat'),
                    _pixel_format_options = mode.get('_PixelFormat_options')
                )
            )

    def update_configuration(self,configuration_id,attribute_name,new_value):
        conf_list = self.config_xml_tree_root.xpath("//mode[contains(@ID," + "'" + str(configuration_id) + "')]")
        mode_to_update = conf_list[0]
        mode_to_update.set(attribute_name,str(new_value))
        self.save_configurations()

    def update_configuration_without_writing(self, configuration_id, attribute_name, new_value):
        conf_list = self.config_xml_tree_root.xpath("//mode[contains(@ID," + "'" + str(configuration_id) + "')]")
        mode_to_update = conf_list[0]
        mode_to_update.set(attribute_name,str(new_value))

    def write_configuration_selected(self,selected_configurations,filename): # to be only used with a throwaway instance
                                                                             # of this class
        for conf in self.configurations:
            self.update_configuration_without_writing(conf.id, "Selected", 0)
        for conf in selected_configurations:
            self.update_configuration_without_writing(conf.id, "Selected", 1)
        self.write_configuration(filename)
        for conf in selected_configurations:
            self.update_configuration_without_writing(conf.id, "Selected", 0)
            
class AutoFocusController:

    def __init__(self, camera, navigationController, liveController):
        self.camera = camera
        self.navigationController = navigationController
        self.liveController = liveController
        self.N = None
        self.deltaZ = None
        self.deltaZ_usteps = None
        self.crop_width = AF.CROP_WIDTH
        self.crop_height = AF.CROP_HEIGHT
        self.autofocus_in_progress = False
        self.focus_map_coords = []
        self.use_focus_map = False
        self.callback_was_enabled_before_autofocus = False
        self.was_live_before_autofocus = False

    def set_N(self, N):
        self.N = N

    def set_deltaZ(self, deltaZ_um):
        mm_per_ustep_Z = SCREW_PITCH_Z_MM / (self.navigationController.z_microstepping * FULLSTEPS_PER_REV_Z)
        self.deltaZ = deltaZ_um / 1000
        self.deltaZ_usteps = round((deltaZ_um / 1000) / mm_per_ustep_Z)

    def set_crop(self, crop_width, crop_height):
        self.crop_width = crop_width
        self.crop_height = crop_height

    def autofocus(self, focus_map_override=False):
        # If autofocus should run in a separate thread to avoid blocking
        autofocus_thread = threading.Thread(target=self._autofocus_thread, args=(focus_map_override,))
        autofocus_thread.start()

    def _autofocus_thread(self, focus_map_override):
        if self.use_focus_map and (not focus_map_override):
            self.autofocus_in_progress = True
            self.navigationController.microcontroller.wait_till_operation_is_completed()
            x = self.navigationController.x_pos_mm
            y = self.navigationController.y_pos_mm
            
            # z here is in mm because that's how the navigation controller stores it
            target_z = utils.interpolate_plane(*self.focus_map_coords[:3], (x,y))
            print(f"Interpolated target z as {target_z} mm from focus map, moving there.")
            self.navigationController.move_z_to(target_z)
            self.navigationController.microcontroller.wait_till_operation_is_completed()
            self.autofocus_in_progress = False
            self.autofocusFinished.emit()
            return
        # stop live
        if self.liveController.is_live:
            self.was_live_before_autofocus = True
            self.liveController.stop_live()
        else:
            self.was_live_before_autofocus = False

        # temporarily disable call back -> image does not go through streamHandler
        if self.camera.callback_is_enabled:
            self.callback_was_enabled_before_autofocus = True
            self.camera.disable_callback()
        else:
            self.callback_was_enabled_before_autofocus = False

        self.autofocus_in_progress = True
        
        
        self._on_autofocus_completed()

    def _on_autofocus_completed(self):
        # Logic to execute when autofocus is completed
        # For example, resume live view if it was on before autofocus started
        if self.was_live_before_autofocus:
            self.liveController.start_live()

        # If callback was enabled before autofocus, re-enable it
        if self.callback_was_enabled_before_autofocus:
            self.camera.enable_callback()

        # Notify (e.g., via a callback or direct method call) that autofocus is complete
        print("Autofocus completed.")

    # Example of directly displaying an image from autofocus without using signals
    def wait_till_autofocus_has_completed(self):
        while self.autofocus_in_progress == True:
            QApplication.processEvents()
            time.sleep(0.005)
        print('autofocus wait has completed, exit wait')

    def set_focus_map_use(self, enable):
        if not enable:
            print("Disabling focus map.")
            self.use_focus_map = False
            return
        if len(self.focus_map_coords) < 3:
            print("Not enough coordinates (less than 3) for focus map generation, disabling focus map.")
            self.use_focus_map = False
            return
        x1,y1,_ = self.focus_map_coords[0]
        x2,y2,_ = self.focus_map_coords[1]
        x3,y3,_ = self.focus_map_coords[2]

        detT = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if detT == 0:
            print("Your 3 x-y coordinates are linear, cannot use to interpolate, disabling focus map.")
            self.use_focus_map = False
            return

        if enable:
            print("Enabling focus map.")
            self.use_focus_map = True

    def clear_focus_map(self):
        self.focus_map_coords = []
        self.set_focus_map_use(False)

    def gen_focus_map(self, coord1,coord2,coord3):
        """
        Navigate to 3 coordinates and get your focus-map coordinates
        by autofocusing there and saving the z-values.
        :param coord1-3: Tuples of (x,y) values, coordinates in mm.
        :raise: ValueError if coordinates are all on the same line
        """
        x1,y1 = coord1
        x2,y2 = coord2
        x3,y3 = coord3
        detT = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if detT == 0:
            raise ValueError("Your 3 x-y coordinates are linear")
        
        self.focus_map_coords = []

        for coord in [coord1,coord2,coord3]:
            print(f"Navigating to coordinates ({coord[0]},{coord[1]}) to sample for focus map")
            self.navigationController.move_to(coord[0],coord[1])
            self.navigationController.microcontroller.wait_till_operation_is_completed()
            print("Autofocusing")
            self.autofocus(True)
            self.wait_till_autofocus_has_completed()
            #self.navigationController.microcontroller.wait_till_operation_is_completed()
            x = self.navigationController.x_pos_mm
            y = self.navigationController.y_pos_mm
            z = self.navigationController.z_pos_mm
            print(f"Adding coordinates ({x},{y},{z}) to focus map")
            self.focus_map_coords.append((x,y,z))

        print("Generated focus map.")

    def add_current_coords_to_focus_map(self):
        if len(self.focus_map_coords) >= 3:
            print("Replacing last coordinate on focus map.")
        self.navigationController.microcontroller.wait_till_operation_is_completed()
        print("Autofocusing")
        self.autofocus(True)
        self.wait_till_autofocus_has_completed()
        #self.navigationController.microcontroller.wait_till_operation_is_completed()
        x = self.navigationController.x_pos_mm
        y = self.navigationController.y_pos_mm
        z = self.navigationController.z_pos_mm
        if len(self.focus_map_coords) >= 2:
            x1,y1,_ = self.focus_map_coords[0]
            x2,y2,_ = self.focus_map_coords[1]
            x3 = x
            y3 = y

            detT = (y2-y3) * (x1-x3) + (x3-x2) * (y1-y3)
            if detT == 0:
                raise ValueError("Your 3 x-y coordinates are linear. Navigate to a different coordinate or clear and try again.")
        if len(self.focus_map_coords) >= 3:
            self.focus_map_coords.pop()
        self.focus_map_coords.append((x,y,z))
        print(f"Added triple ({x},{y},{z}) to focus map")
