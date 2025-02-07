
import os
from cls.utils.scan_estimation.estimator import EstimateScanTimeClass, run_estimations
import matplotlib.pyplot as plt
import numpy as np

# # Example data (list of tuples)
def do_plot(actual, predictions):
    plt.style.use('_mpl-gallery')
    act_arr = np.array(actual)
    est_arr = np.array(predictions)
    x = np.linspace(0, 10, len(actual))
    x2 = np.linspace(0, 10, len(est_arr))

    # plot
    fig, ax = plt.subplots()

    ax.plot(x, act_arr, 'x', markeredgewidth=2)
    ax.plot(x2, est_arr, linewidth=2.0)
    # ax.plot(x2, y2 - 2.5, 'o-', linewidth=2)

    # ax.set(xlim=(0, 8), xticks=np.arange(1, 8),
    #        ylim=(0, 8), yticks=np.arange(1, 8))
    #
    plt.show()

def create_tuples(constant_values, values):
    # Create tuples by pairing each element in the values list with the constant values
    tuples_list = [(value,) + constant_values for value in values]
    return tuples_list

#stack image data
data1 = [[164.0, 150, 150, 1.0, 4, 1], [160.0, 150, 150, 1.0, 4, 1], [164.0, 150, 150, 1.0, 4, 1], [160.0, 150, 150, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [36.0, 50, 50, 1.0, 4, 1], [40.0, 150, 150, 1.0, 1, 1], [41.0, 150, 150, 1.0, 1, 1], [40.0, 150, 150, 1.0, 1, 1], [41.0, 150, 150, 1.0, 1, 1]]
data2 = [[82.22092390060425, 150, 150, 1.0, 2, 1], [115.28390741348267, 100, 100, 1.0, 5, 1], [207.27106189727783, 150, 150, 1.0, 5, 1], [30.998793601989746, 150, 150, 1.0, 3, 1], [18.01468586921692, 50, 50, 1.0, 2, 1], [125.13001370429993, 300, 300, 1.0, 1, 1], [255.1, 300, 300, 1.0, 2, 1], [625.1, 300, 300, 1.0, 5, 1]]
#model_fpath = "c:/test_data/stxm/det_scan_model.pkl"
#model = load_model(model_fpath)


single_image_data = [[8.029, 50, 50, 1.0, 1, 1], [41.097, 150, 150, 1.0, 1, 1], [125.130, 300, 300, 1.0, 1, 1], [470.319, 150, 150, 20.0, 1, 1]  ]

stack_data = {}
num_evs = [2, 5, 10, 20, 50, 75, 100]
num_evs_to_predict = [4, 7, 15, 35, 65, 90, 130]
for ev in num_evs:
    stack_data[ev] = []
    for d in single_image_data:
        stack_data[ev].append([d[0]*ev, d[1], d[2], d[3], d[4], d[5]])

#now the stack data is organized into num_ev

# for ev, data in stack_data.items():
#     estc = EstimateScanTimeClass(degree=2, alpha=0.1, bl_scantime_dir=os.getcwd())
#     estc.init_model_for_scan_type(f'sample_image_stack', data)
#     actual, predictions = run_estimations(estc, 'sample_image_stack', single_image_data)
#     do_plot(actual, predictions)
idx = 0
predict_ev = num_evs_to_predict[idx]
ev = num_evs[idx]
data = stack_data[ev]
estc = EstimateScanTimeClass(degree=2, alpha=0.1, bl_scantime_dir=os.getcwd())
estc.init_model_for_scan_type(f'sample_image_stack', data)
predict_data = []
for d in single_image_data:
    predict_data.append([d[0] * predict_ev, d[1], d[2], d[3], d[4], d[5]])
actual, predictions = run_estimations(estc, 'sample_image_stack', predict_data)
do_plot(actual, predictions)

