import os
from cls.utils.scan_estimation.estimator import EstimateScanTimeClass, run_estimations
import matplotlib.pyplot as plt
import numpy as np


# # Example data (list of tuples)
def do_plot(actual, predictions=[]):
    """
    plot actual scan times against a list of estimations for those same parameters
    """
    act_arr = np.array(actual)
    plt.style.use('_mpl-gallery')

    x = np.linspace(0, 10, len(actual))
    # plot
    fig, ax = plt.subplots()
    ax.plot(x, act_arr, 'x', markeredgewidth=2)

    if len(predictions) > 0:
        est_arr = np.array(predictions)
        x2 = np.linspace(0, 10, len(est_arr))
        ax.plot(x2, est_arr, linewidth=2.0)

    plt.subplots_adjust(left=0.115, bottom=0.085)  # Increase left and bottom margins
    ax.set_ylabel('Seconds')
    plt.show()


if __name__ == '__main__':
    data = [[41.09736680984497, 150, 150, 1.0], [40.128658056259155, 150, 150, 1.0],
            [470.3191614151001, 150, 150, 20.0], [8.029917001724243, 50, 50, 1.0], [125.13001370429993, 300, 300, 1.0],
            [90.13, 200, 200, 1.0]]

    # data = [[8.029917001724243, 50, 50, 1.0], [40.128658056259155, 150, 150, 1.0],[41.09736680984497, 150, 150, 1.0],  [125.13001370429993, 300, 300, 1.0], [470.3191614151001, 150, 150, 20.0]]
    data = sorted(data, key=lambda x: x[0])
    print(data)

    scan_name = 'sample_image'
    estc = EstimateScanTimeClass(degree=2, alpha=0.1, bl_scantime_dir=os.getcwd())
    estc.init_model_for_scan_type(scan_name, data)
    actual, estimated = run_estimations(estc, scan_name, data)
    do_plot(actual, estimated)
