import napari
import numpy as np
import PIL
import matplotlib.pyplot as plt
from .FOVPicker import *
from skimage.io import imread
from skimage.transform import resize
from skimage.filters import threshold_otsu
from collections import defaultdict

def concatonate_image(image1, image2, direction):
    concatonated_image = []
    if direction == 'right':
        concatonated_image = np.hstack((image1, image2))
            
    if direction == 'left':
        concatonated_image = np.hstack((image2, image1))
    
    if direction == 'up':
        concatonated_image = np.vstack((image2, image1))
            
    concatonated_image = np.array(concatonated_image)
    return concatonated_image

def get_sections(labels, og_shape):
    sections = defaultdict(Image)
    unique = np.unique(labels.image_dict['array'])[1:]
    index = 0
    for u in unique:
        array = resize(coordinates_to_array(list(zip(np.where(labels.image_dict['array'] == u)[1], np.where(labels.image_dict['array'] == u)[0])), labels.shape), og_shape)
        coordinates = array_to_coordinates(array)
        sections[index] = Image(array, coordinates, og_shape)
        index += 1
    return sections

def get_image_windows(overview, labels, dimensions, x=428, y=684):
    height, width = overview.shape
    horizontal, vertical = dimensions
    x_pos = np.arange(0, width, x)
    y_pos = np.arange(0, height, y)
    last_x = x_pos[-1] - (x - (width - x_pos[-1]))
    last_y = y_pos[-1] - (y - (height - y_pos[-1]))
    x_pos = np.append(x_pos[:-1], last_x)
    y_pos = np.append(y_pos[:-1], last_y)
    corners = sorted([(y, x) for y in (y_pos) for x in (x_pos)], reverse=True)
    for i in range(vertical):
        if i%2 == 1:
            start = i*horizontal
            end = start+horizontal
            corners[start:end] = corners[start:end][::-1]
    
    border_coordinates = []
    for corner in corners:
        x_border = np.arange(corner[1], corner[1]+x)
        y_border = np.arange(corner[0], corner[0]+y)
        border_coordinates += [(x, y_border[0]) for x in x_border]
        border_coordinates += [(x_border[0], y) for y in y_border]
        border_coordinates += [(x, y_border[-1]) for x in x_border]
        border_coordinates += [(x_border[-1], y) for y in y_border]
    
    labels.set_coordinate_data('border_coordinates', border_coordinates)
    labels.set_coordinate_data('positions', corners)
    
    overlay = np.array(PIL.Image.fromarray(resize(coordinates_to_array(list(zip(np.where(labels.image_dict['array'] > 0)[1], np.where(labels.image_dict['array'] > 0)[0])), labels.shape), overview.shape)))
    for coordinate in overview.coordinate_dict['binary_coordinates']:
        overlay[coordinate[1], coordinate[0]] = 2
    for coordinate in border_coordinates:
        overlay[coordinate[1], coordinate[0]] = 3
        
    labels.set_image_data('label_overlay', overlay)
    
    return labels

def get_fovs(labels, x=428, y=684):
    positions = labels.coordinate_dict['positions']
    fov = []
    for i in range(len(positions)):
        split = labels.image_dict['labels_full_size'][positions[i][0]:positions[i][0]+y, positions[i][1]:positions[i][1]+x]
        if 1 in split:
            fov.append(i)
    return fov

def get_positions(overview, labels, dimensions, start_position, increments, x=428, y=684):
    fov = get_fovs(labels, x, y)
    positions = labels.coordinate_dict['positions']
    horizontal, vertical = dimensions
    x_inc, y_inc = increments
    # rows = []
    pos_index = 0
    switch_directions = 0
    curr_x = start_position[0]
    curr_y = start_position[1]
    pos_coordinates = []
    # fov_image = np.zeros(overview.shape)
    for i in range(vertical):
        if switch_directions%2 == 0:
            image_row = []
            for j in range(horizontal):
                if pos_index in fov:
                    '''split = overview.image_dict['array'][positions[pos_index][0]:positions[pos_index][0]+y, positions[pos_index][1]:positions[pos_index][1]+x]
                    if len(image_row) == 0:
                        image_row = np.array(split)
                    else:
                        image_row = concatonate_image(image_row, split, 'left')'''
                    pos_coordinates.append((curr_x, curr_y))
                    if j != horizontal - 1:
                        curr_x += x_inc
                    '''
                    corners = [(positions[pos_index][1], positions[pos_index][0]), (positions[pos_index][1]+x, positions[pos_index][0]+y)]
                    x_coords = [x for x in range(corners[0][0], corners[1][0])]
                    y_coords = [y for y in range(corners[0][1], corners[1][1])]
                    for coordinate in list(itertools.product(x_coords, y_coords)):
                        fov_image[coordinate[1], coordinate[0]] = 1'''
                    pos_index += 1
                else:
                    '''
                    blank = np.zeros((y, x))
                    if len(image_row) == 0:
                        image_row = np.array(blank)
                    else:
                        image_row = concatonate_image(image_row, blank, 'left')
                    '''
                    if j != horizontal - 1:
                        curr_x += x_inc
                    pos_index += 1
            switch_directions += 1
            curr_y += y_inc
            # rows.append(image_row)
        else:
            # image_row = []
            for j in range(horizontal):
                if pos_index in fov:
                    # split = overview.image_dict['array'][positions[pos_index][0]:positions[pos_index][0]+y, positions[pos_index][1]:positions[pos_index][1]+x]
                    '''if len(image_row) == 0:
                        image_row = np.array(split)
                    else:
                        image_row = concatonate_image(image_row, split, 'right')'''
                    pos_coordinates.append((curr_x, curr_y))
                    
                    if j != horizontal - 1:
                        curr_x -= x_inc
                    '''corners = [(positions[pos_index][1], positions[pos_index][0]), (positions[pos_index][1]+x, positions[pos_index][0]+y)]
                    x_coords = [x for x in range(corners[0][0], corners[1][0])]
                    y_coords = [y for y in range(corners[0][1], corners[1][1])]
                    for coordinate in list(itertools.product(x_coords, y_coords)):
                        fov_image[coordinate[1], coordinate[0]] = 1'''
                    pos_index += 1
                else:
                    '''
                    blank = np.zeros((y, x))
                    if len(image_row) == 0:
                        image_row = np.array(blank)
                    else:
                        image_row = concatonate_image(image_row, blank, 'right')
                    '''
                    if j != horizontal - 1:
                        curr_x -= x_inc
                    pos_index += 1
            switch_directions += 1
            curr_y += y_inc
            # rows.append(image_row)
    '''
    rows = rows[::-1]
    final_image = []
    for row in rows:
        if len(final_image) == 0:
            final_image = row
        else:
            final_image = concatonate_image(row, final_image, 'up')
    final = Image(np.array(final_image))
    final.set_coordinate_data('pos_coordinates', pos_coordinates)
    
    for coordinate in array_to_coordinates(overview.image_dict['binary']):
        fov_image[coordinate[1], coordinate[0]] = 2
    for coordinate in labels.coordinate_dict['border_coordinates']:
        fov_image[coordinate[1], coordinate[0]] = 3
    final.set_image_data('fov_overlay', fov_image)
    final.set_image_data('label_overlay', labels.image_dict['label_overlay'])'''
    return pos_coordinates

def open_napari(overview_file, resize_value=4):
    overview = Image(imread(overview_file, plugin='tifffile'), None, None)
    overview.get_binary(overview.image_dict['array'], threshold_otsu(overview.image_dict['array']))
    resized_overview = Image(resize(overview.image_dict['array'], (overview.shape[0]//resize_value, overview.shape[1]//resize_value)), None, None)
    viewer = napari.view_image(resized_overview.image_dict['array'], name='Overview')
    return overview, viewer

def FOVPicker(overview, viewer, dimensions, start_position, increments):
    labels = Image(viewer.layers['Labels'].data, None, None)
    labels.set_image_data('labels_full_size', resize(labels.image_dict['array'], overview.shape))
    #labels.get_binary(labels.image_dict['labels_full_size'])
    #sections = get_sections(labels, overview.shape)
    labels = get_image_windows(overview, labels, dimensions)
    final = get_positions(overview, labels, dimensions=dimensions, start_position=start_position, increments=increments)
    final.show(final.image_dict['label_overlay'], 'cividis')
    final.show(final.image_dict['fov_overlay'], 'cividis')
    final.show(final.image_dict['array'], 'inferno')
    return labels, final