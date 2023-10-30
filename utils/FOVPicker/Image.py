import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

def plot_image(image_array, cmap='inferno', figsize=(24, 6)):
    plt.style.use('dark_background')
    plt.figure(figsize=figsize)
    plt.imshow(image_array, cmap=cmap)
    plt.axis('off')
    plt.show()
    
def coordinates_to_array(coordinates, shape):
    image = np.zeros(shape)
    for coordinate in coordinates:
        image[coordinate[1], coordinate[0]] = 1
    return image

def array_to_coordinates(image_array):
    return list(zip(np.where(image_array > 0)[1], np.where(image_array > 0)[0]))

class Image:
    image_dict = defaultdict(np.array)
    array = np.array([])
    binary = np.array([])
    coordinate_dict = defaultdict(list)
    shape = (0,0)
    
    def __init__(self, array=np.array([]), coordinates=None, shape=None):
        if coordinates == None:
            self.image_dict = defaultdict(np.array)
            self.image_dict['array'] = array
            self.shape = array.shape
            self.coordinate_dict = defaultdict(list)
        else:
            self.image_dict = defaultdict(np.array)
            self.coordinate_dict = defaultdict(list)
            self.coordinate_dict['image_coordinates'] = coordinates
            if array.size == 0:
                self.image_dict['array'] = coordinates_to_array(coordinates, shape)
                self.shape = shape
            else:
                self.image_dict['array'] = array
                self.shape = array.shape
        
    def get_coordinates(self):
        self.coordinate_dict['image_coordinates'] = array_to_coordinates(self.image_dict['array'])
    
    def get_binary(self, array, thresh=0):
        self.image_dict['binary'] = array > thresh
        self.coordinate_dict['binary_coordinates'] = array_to_coordinates(self.image_dict['binary'])
        
    def set_coordinate_data(self, name, coordinates):
        self.coordinate_dict[name] = coordinates
    
    def set_image_data(self, name, array):
        self.image_dict[name] = array
        
    def show(self, array, cmap='inferno', figsize=(52, 13)):
        plot_image(array, cmap, figsize=figsize)
        