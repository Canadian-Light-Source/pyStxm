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

# # Example usage
# data = [
#     860.0, 861.6363636363636, 863.2727272727273, 864.9090909090909, 866.5454545454545,
#     868.1818181818181, 869.8181818181819, 871.4545454545455, 873.0909090909091, 874.7272727272727,
#     876.3636363636364, 878.0, 878.01, 878.608, 879.206, 879.804, 880.402, 881.0, 881.01,
#     881.2688888888889, 881.5277777777777, 881.7866666666666, 882.0455555555556, 882.3044444444445,
#     882.5633333333333, 882.8222222222222, 883.0811111111111, 883.34, 883.5988888888888, 883.8577777777778,
#     884.1166666666667, 884.3755555555556, 884.6344444444444, 884.8933333333333, 885.1522222222222, 885.4111111111112,
#     885.67, 885.9288888888889, 886.1877777777778, 886.4466666666667, 886.7055555555555, 886.9644444444444,
#     887.2233333333334, 887.4822222222223, 887.7411111111111, 888.0, 888.01, 888.5925, 889.175, 889.7574999999999,
#     890.34, 890.9225, 891.505, 892.0875, 892.67, 893.2525, 893.835, 894.4175, 895.0, 895.01, 895.2661538461539,
#     895.5223076923077, 895.7784615384616, 896.0346153846153, 896.2907692307692, 896.5469230769231, 896.8030769230769,
#     897.0592307692308, 897.3153846153846, 897.5715384615385, 897.8276923076922, 898.0838461538461, 898.34,
#     898.5961538461538, 898.8523076923077, 899.1084615384615, 899.3646153846154, 899.6207692307693, 899.876923076923,
#     900.1330769230769, 900.3892307692307, 900.6453846153846, 900.9015384615385, 901.1576923076923, 901.4138461538462,
#     901.67, 901.9261538461539, 902.1823076923077, 902.4384615384615, 902.6946153846154, 902.9507692307692,
#     903.2069230769231, 903.4630769230769, 903.7192307692308, 903.9753846153847, 904.2315384615384, 904.4876923076923,
#     904.7438461538461, 905.0, 905.01, 906.25875, 907.5074999999999, 908.75625, 910.005, 911.25375, 912.5025, 913.75125, 915.0
# ]
#
# split_data = split_by_difference(data)
# for i, subarray in enumerate(split_data):
#     print(f"Subarray {i + 1}: {subarray}")
