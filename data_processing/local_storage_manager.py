import os
import psutil
import numpy as np
import sys
sys.path.append('../telemetry')
from telemetry import slack_notify
import time
import tifffile

def map_dir_memory():
    """
    Maps the memory usage of each directory in the system.

    Returns:
        dict: A dictionary containing the memory usage information for each directory.
              The keys are the mount points of the directories, and the values are
              dictionaries with the following keys:
              - "total": the total memory available for the directory
              - "used": the amount of memory used by the directory
              - "free": the amount of free memory in the directory
    """
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
    """
    Get the available memory in bytes for the directory specified by the given path.

    Args:
        path (str): The path of the directory.

    Returns:
        int or None: The available memory in bytes for the directory, or None if the path is invalid.
    """
    memory_dict = map_dir_memory()
    for drive, memory_info in memory_dict.items():
        if path.startswith(drive):
            return memory_info['free']
    return None

def save_image_stack(image_stack, target_dir, file_prefix):
    """
    Save an image stack as an OME-TIFF file.

    Args:
        image_stack (ndarray): The image stack to be saved.
        target_dir (str): The directory where the file will be saved.
        file_prefix (str): The prefix for the file name.

    Returns:
        None
    """
    # check if target_dir exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    # save image stack
    #image_stack_3d = np.stack(image_stack, axis=0)
    file_str = f'{os.path.join(target_dir, str(file_prefix))}.ome.tiff'
    with tifffile.TiffWriter(file_str, append=False) as tif:
        tif.save(image_stack,
                 photometric='minisblack',
                 metadata={'axes':'ZCYX',
                           "SizeX":image_stack.shape[3],
                           "SizeY": image_stack.shape[2],
                            "SizeC": image_stack.shape[1],
                            "SizeZ": image_stack.shape[0],
                            })

def save_image_stack_npy(image_stack, target_dir, file_prefix):
    """
    Save a stack of images as a NumPy array in .npy format.

    Args:
        image_stack (list): A list of images to be saved.
        target_dir (str): The directory where the .npy file will be saved.
        file_prefix (str): The prefix to be added to the filename.

    Returns:
        None
    """
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
            
def create_folder_in_drive(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

def get_save_path(folder_name, num_stacks, stack_dims, dtype=np.uint16, slack=True):
    """
    Get the save path for storing data.

    Args:
        folder_name (str): The name of the folder to be created.
        num_stacks (int): The number of stacks.
        stack_dims (tuple): The dimensions of the stack.
        dtype (numpy.dtype, optional): The data type of the stack. Defaults to np.uint16.
        slack (bool, optional): Whether to send a Slack notification. Defaults to True.

    Returns:
        str: The path of the created folder.
    """
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
    

