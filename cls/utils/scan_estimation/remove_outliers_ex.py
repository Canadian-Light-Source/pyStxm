import numpy as np
import math



def remove_outliers(arr, abs_val_limit=15.0):
    """

    """
    differences = np.diff(arr)
    absolute_differences = np.abs(differences)

    #print(absolute_differences)
    filtered_data = []
    i = 0
    avg = []
    for val in absolute_differences:
        if val < abs_val_limit:
            avg.append(arr[i])
            if i == 0:
                i = 1.0
            avg_arr = np.array(avg)
            mean = np.mean(avg_arr)
            if math.fabs(arr[i] - mean) < abs_val_limit:
                filtered_data.append(arr[i])

        i += 1
    #print(filtered_data)
    return filtered_data

if __name__ == '__main__':
    arr = np.array([203.0, 56.0, 110.0, 176.0, 82.0, 76.0, 76.0, 86.0, 57.0, 62.0,
                    84.0, 75.0, 74.0, 82.0, 82.0, 61.0, 6.0, 75.0, 109.0, 5.0, 14.0, 210.0])
    filtered_data = remove_outliers(arr, abs_val_limit=15.0)
    # # Filter out outliers
    # filtered_data = [x for x in data if (x >= lower_bound and x <= upper_bound)]
    #
    print("Original data:", arr)
    print("Filtered data (without outliers):", filtered_data)
