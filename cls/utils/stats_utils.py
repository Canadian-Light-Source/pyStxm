

import math
import numpy as np

def calc_rmse(expected_arr, actual_arr):
    mse = np.square(np.subtract(actual_arr,expected_arr)).mean()
    rmse = math.sqrt(mse)
    return(rmse)

if __name__ == '__main__':
    actual_arr = np.array([1, 2, 3, 4, 5])
    expected_arr = np.array([1.6, 2.5, 2.9, 3, 4.1])
    rmse = calc_rmse(expected_arr , actual_arr)
    print("Root Mean Square Error: = %.3f\n" % rmse)

