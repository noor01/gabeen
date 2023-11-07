import os
import psutil
import numpy as np
import sys
sys.path.append('../telemetry')
from telemetry import slack_notify

def map_dir_memory():
    memory_dict = {}
    for partition in psutil.disk_partitions():
        memory_info = psutil.disk_usage(partition.mountpoint)
        memory_dict[partition.mountpoint] = {
            "total": memory_info.total,
            "used": memory_info.used,
            "free": memory_info.free
        }
    return memory_dict
    
def get_dir_mem_avail(path):
    memory_dict = map_dir_memory()
    for drive, memory_info in memory_dict.items():
        if path.startswith(drive):
            return memory_info['free']
    return None

def save_image_stack(image_stack, target_dir, file_prefix):
    # check if target_dir exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    # save image stack
    image_stack_3d = np.stack(image_stack, axis=0)
    np.save(f'{os.path.join(target_dir, str(file_prefix))}.npy', image_stack_3d)

def estimate_mem_footprint(stack_dims, num_stacks, dtype=np.uint16):
    return np.prod(stack_dims) * num_stacks * np.dtype(dtype).itemsize

def create_folder_in_all_drives(folder_name):
    for partition in psutil.disk_partitions():
        drive = partition.mountpoint
        folder_path = os.path.join(drive, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
import time

def get_save_path(folder_name,num_stacks, stack_dims, dtype=np.uint16,slack=True):
    # Estimate memory footprint of the stack
    mem_needed = estimate_mem_footprint(stack_dims, num_stacks, dtype)
    
    # Map available memory on all drives
    memory_dict = map_dir_memory()
    
    # Check each drive for available memory
    while True:
        for drive, memory_info in memory_dict.items():
            if memory_info['free'] >= mem_needed:
                # Create folder in the selected drive
                folder_path = os.path.join(drive, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                return folder_path
        
        # If no drive has enough memory, wait for 5 minutes and retry
        # This gives the user the opportunity to free up memory...also pauses experiment until memory is freed
        print("No drive has enough memory. Waiting 5 minutes...")
        if slack == True:
            slack_notify.msg("No drive has enough memory. Waiting 5 minutes...")
        time.sleep(300)
        memory_dict = map_dir_memory()
    

