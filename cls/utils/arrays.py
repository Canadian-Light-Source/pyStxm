"""
Created on Jan 27, 2017

@author: bergr
"""
import numpy as np


def flip_data_upsdown(data):
    _data = np.flipud(data).copy()
    return _data


# def resize_1d_array(a, b):
#     bb = np.zeros(len(b))
#     if len(a) < len(bb):
#         c = bb.copy()
#         c[:len(a)] += a
#     else:
#         c = a.copy()
#         c[:len(bb)] += bb
#
#     return(c)


def resize_1d_array(a, b):
    """
    resize a to be length of b
    :param a:
    :param b:
    :return:
    """
    lenb = len(b)
    # resize a to be length of b
    a = np.resize(a, (lenb))
    return a

def split_by_difference(data, tolerance=1e-4):
    """
    Splits an array into subarrays based on changes in the difference between consecutive values.

    Args:
    - data (list[float]): The input array.
    - tolerance (float): The allowable deviation in differences to consider them the same.

    Returns:
    - list[list[float]]: A list of subarrays split by changes in the difference between values.
    """
    if not data.any():
        return []

    result = []
    current_subarray = [data[0]]  # Start with the first value
    new_range_started = False
    for i in range(1, len(data)):
        current_diff = data[i] - data[i - 1]

        # Check if the difference has changed significantly
        if i > 1:
            previous_diff = data[i - 1] - data[i - 2]
            if abs(current_diff - previous_diff) > tolerance and not new_range_started:
                result.append(current_subarray)  # Add the current subarray to results
                current_subarray = []  # Start a new subarray
                new_range_started = True
            else:
                new_range_started = False

        current_subarray.append(data[i])  # Append the current value to the subarray

    # Append the last subarray
    if current_subarray:
        result.append(current_subarray)

    return result


def nulls_to_nans(obj):
    if obj is None:
        return np.nan
    elif isinstance(obj, list):
        return [nulls_to_nans(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: nulls_to_nans(v) for k, v in obj.items()}
    else:
        return obj

def convert_numpy_to_python(obj):
    """Convert numpy types to standard Python types for JSON serialization, replacing NaN with None. Handles tuples."""
    import numpy as np

    if isinstance(obj, np.ndarray):
        arr = obj.tolist()
        return [
            convert_numpy_to_python(x) if not (isinstance(x, float) and np.isnan(x)) else None
            for x in arr
        ]
    elif isinstance(obj, dict):
        return {k: convert_numpy_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [
            convert_numpy_to_python(x) if not (isinstance(x, float) and np.isnan(x)) else None
            for x in obj
        ]
    elif isinstance(obj, tuple):
        # Convert tuple to list and handle NaN
        return [
            convert_numpy_to_python(x) if not (isinstance(x, float) and np.isnan(x)) else None
            for x in obj
        ]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return None if np.isnan(obj) else float(obj)
    elif isinstance(obj, float) and np.isnan(obj):
        return None
    return obj


def clean_nans(obj):
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    elif isinstance(obj, float) and np.isnan(obj):
        return None
    else:
        return obj