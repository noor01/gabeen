import numpy as np

def normalize(arr,scale_max=1):
    min_val = np.min(arr)
    max_val = np.max(arr)
    im = (scale_max*(arr-min_val)) / ((max_val - min_val))
    return im

def replace_outliers_with_mean(data):
    # Convert to numpy array for more efficient computation
    data = np.array(data)
    Q1 = np.percentile(data, 20)
    Q3 = np.percentile(data, 80)
    IQR = Q3 - Q1
    lower_bound = Q1 - (1.5 * IQR)
    upper_bound = Q3 + (1.5 * IQR)
    
    # Identify outliers
    outliers = ((data < lower_bound) | (data > upper_bound))
    
    # Calculate the mean without outliers
    mean_without_outliers = np.mean(data[~outliers])
    
    # Replace outliers with the mean_without_outliers
    data[outliers] = mean_without_outliers
    
    return data.tolist()  # Convert back to list if needed