import os
import psutil
import numpy as np

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
    
import numpy as np

def save_image_stack(image_stack, target_dir, nested_dir_names, file_prefix):
    # check if target_dir exists
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    # check if nested_dir_names exists
    for nested_dir_name in nested_dir_names:
        target_dir = os.path.join(target_dir, nested_dir_name)
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
    # save image stack
    image_stack_3d = np.stack(image_stack, axis=0)
    np.save(f'{os.path.join(target_dir, file_prefix)}.npy', image_stack_3d)

def estimate_mem_footprint(stack_dims, num_stacks, dtype=np.uint16):
    return np.prod(stack_dims) * num_stacks * np.dtype(dtype).itemsize