import numpy as np
import matplotlib.pyplot as plt

def fit_and_plot(data_x, data_y, degree, title, do_plot=False):
    # Fit a polynomial of the specified degree to the data
    coeffs = np.polyfit(data_x, data_y, degree)
    fitted_function = np.poly1d(coeffs)

    # Generate x values for the fit curve
    fit_x = np.linspace(min(data_x), max(data_x), 100)

    # Calculate y values using the fitted function
    fit_y = fitted_function(fit_x)

    if do_plot:
        # Plot the data and the fit

        plt.scatter(data_x, data_y, label='Data')
        plt.plot(fit_x, fit_y, label=f'Fit (Degree {degree})', color='orange')

        # Add labels and legend
        plt.xlabel('X values')
        plt.ylabel('Total Scan Time (sec)')
        plt.title(title)
        plt.legend()

        # Show the plot
        #plt.show()
        fname = title.replace("\t",f"deg{degree}-")
        fname = fname.replace(" ","_")
        fname = fname.replace(":", "_")
        plt.savefig(f'{fname}.png')
        plt.clf()

    return coeffs

def do_fit_func(x_new, coefficients):
    import numpy as np

    # # Example data
    # x = np.array([1, 2, 3, 4, 5])
    # y = np.array([2, 3, 5, 7, 9])
    #
    # # Determine degree of polynomial fit
    # degree = 2
    #
    # # Perform polynomial fitting
    # coefficients = np.polyfit(x, y, degree)

    # Create the fit function
    fit_function = np.poly1d(coefficients)

    # You can now use fit_function to evaluate the polynomial at any point:
   # x_new = 6
    y_fit = fit_function(x_new)

    print("Predicted per point time when X =", x_new, ":", y_fit)
    return y_fit

def determine_coeffs(data_x, data_y, degree_of_fit):
    # Example data (replace with your own data)
    # data_x = np.array([250, 500, 750, 1000, 1500])
    # data_y = np.array([0.184, 0.197, 0.266, 0.322, 0.344])

    # Specify the degree of the polynomial fit
    # degree_of_fit = 4

    # Call the function to fit and plot the data
    coeffs = fit_and_plot(data_x, data_y, degree_of_fit, "scan", do_plot=True)
    return coeffs

def calc_pxp_exec_time(dwell_ms, num_pnts, range, coeffs):
    dwell_sec = (dwell_ms * 0.001)
    pp_sec = do_fit_func(range, coeffs)
    pp_travel_time = pp_sec - dwell_sec

    ttl_time = (2*dwell_sec + pp_travel_time) * num_pnts

    return ttl_time


if __name__ == '__main__':
    #det_coeffs = [ 4.800e-13, -1.936e-09,  2.602e-06, -1.165e-03,  3.410e-01]
    det_coeffs = [-4.01242679e-18, 2.14919073e-14, -4.51125847e-11,  4.66775472e-08, -2.45851658e-05,  6.28703209e-03, - 4.24309396e-01]
    osa_coeffs = []

    dwell_ms = 1
    numX = 25
    numY = 25
    num_pnts = numX * numY
    # # Example data (replace with your own data)
    data_x = np.array([250, 400, 500, 750, 1000, 1250, 1500])
    data_y = np.array([0.184, 0.193, 0.197, 0.266, 0.322, 0.331, 0.344])

    # Specify the degree of the polynomial fit
    degree_of_fit = 6

    # # Call the function to fit and plot the data
    # coeffs = fit_and_plot(data_x, data_y, degree_of_fit, "Det scan", do_plot=True)
    # print(f"With {degree_of_fit} DOF the coeffs are {coeffs}")
    # # do_fit_func(600, coeffs)
    range = 500
    total_sec = calc_pxp_exec_time(dwell_ms, num_pnts, range, det_coeffs)
    print(f"A detector scan with range ({range}x{range})um and {numX}x{numY} pts will take {total_sec:.2f} seconds long")