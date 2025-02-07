import numpy as np

# Example arrays
A_nans = np.full(15, np.nan)  # array of 15 NaNs
B_nums = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])  # array of 11 integers
num_B, = B_nums.shape
# Create a mask to identify NaN values in A
mask_15 = np.isnan(A_nans)

# Overwrite NaN values in A with corresponding elements from B
# A[mask_15] = B_nums[:mask_15.sum()]
A_nans[:num_B] = B_nums[:num_B]

# Concatenate A and B to get C
# C = np.concatenate((A, B[mask.sum():]))

print(A_nans)
