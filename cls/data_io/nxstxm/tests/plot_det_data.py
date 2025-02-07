import copy
import numpy as np
import matplotlib.pyplot as plt

def get_data(fname):
    f = open(fname, "r")
    arr = np.loadtxt(f, delimiter=",")
    f.close()
    return arr



def do_plot(arr):
    plt.imshow(arr, cmap='gray')
    plt.show()

base_1D_data = get_data("base_1D_data.out")

base_1D_data[0] = 0
base_1D_data[9] = 9
base_1D_data[10] = 10
base_1D_data[19] = 19
base_1D_data[20] = 20
base_1D_data[29] = 29
base_1D_data[30] = 30
base_1D_data[39] = 39
base_1D_data[40] = 40
base_1D_data[49] = 49

oneDarr = copy.copy(base_1D_data)
do_plot(np.transpose(np.reshape(oneDarr, (5, 10))))

# #np.reshape(det_data, (xnpoints, num_ev_points))
#
# #dat = get_data("ev_xpnts_reshaped_det_data.out")
# transpdet = np.transpose(dat)
# do_plot(transpdet)
# # do_plot("det_data.out")
# # do_plot("det_data.out")
# # do_plot("det_data.out")
# # do_plot("det_data.out")