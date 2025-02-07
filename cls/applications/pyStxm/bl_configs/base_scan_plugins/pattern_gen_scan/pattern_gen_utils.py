from PIL import Image
import numpy as np
from numpy import asarray

from cls.utils.images import get_image_details_dict

def load_image(fname):
    # load the image
    image = Image.open(fname)
    img_details = get_image_details_dict()
    if hasattr(image, "bits"):
        img_details["image.bits"] = image.bits
    img_details["image.filename"] = image.filename
    img_details["image.format"] = image.format
    img_details["image.size"] = image.size
    if hasattr(image, "info"):
        #this image has a bunch of stuff that is difficult to seruialize for json so dont include it, only use dpi
        if "dpi" in image.info.keys():
            img_details["image.dpi"] = image.info["dpi"]
        else:
            img_details["image.dpi"] = image.size

    img_details["image.mode"] = image.mode

    # convert image to numpy array
    data = asarray(image)
    nrgba = 0
    if data.ndim == 2:
        nrows, ncols = data.shape
    elif data.ndim == 3:
        nrows, ncols, nrgba = data.shape
    return(nrows,ncols,nrgba, data, img_details)


def data_to_image(data):
    # create Pillow image
    image2 = Image.fromarray(data)
    print(type(image2))

    # summarize image details
    print(image2.mode)
    print(image2.size)
    return (image2)

def rgba_to_mono_array(data):
    if data.ndim == 3:
        mono_arr = data[:,:,0]
    else:
        mono_arr = data
    return(mono_arr)

def get_min_max_of_array(data):
    max = np.amax(data)
    min = np.amin(data)
    return(min, max)

def get_exposure_time_of_pixel(pixel, time_value_of_brightest_pixel_ms=1000):
    """
    1 ms is shortest exposure time, and 500ms is the max,
    so do a linear interpolation from 0 to 255
    because its linear y=mx+b and when x=0 so is y so the y intercepot is 0 (b)
    so m = max / 255
    then use y = m(x)
    :param pixel:
    :return:
    """
    m = float(time_value_of_brightest_pixel_ms / 255.0)
    y = m * pixel
    return(y)

def convert_pixels_to_exposures(data, time_value_of_brightest_pixel_ms=1000.0):
    """

    """
    import numpy as np
    if hasattr(data, "max"):
        max_arr_val = data.max()
        scaler = float(time_value_of_brightest_pixel_ms/max_arr_val)
        liner = lambda t: int(t * scaler)
        vfunc = np.vectorize(liner)
        arr = vfunc(data)
    else:
        arr = np.array([],dtype=np.uint8)
    return arr

def calc_total_time_in_sec(exp_data):
    """
    return the sum total of all exposure data which is in ms
    """
    #scale exact pixel dwells by a measured amount (50ms)
    ttl_ms = np.sum(exp_data) #* 1.05
    #return total in seconds
    return(ttl_ms / 1000.0)

def do_scan(xdata, ydata, exp_data):
    """
    for each line of exposure data determine the indices of exposures that are non zero as those are the only ones we care about
    then use the indices of non zero exposures as indexs into the X,Y position data, then run the line point by point
    repeat for next line
    :param xdata: 1D array of x motor positions
    :param ydata: 1D array of x motor positions
    :param exp_data: 2D array of pixel exposure values
    :return:
    """
    rows = 0
    rows, cols = exp_data.shape
    row_indices = list(range(rows))
    for row in row_indices:
        line_data = exp_data[row]
        y = ydata[row]
        no_zero_ele = np.nonzero(line_data)
        if no_zero_ele[0].size > 0:
            x_line  = xdata[tuple(no_zero_ele)]
            dwell_data = line_data[tuple(no_zero_ele)]
            final_line_data = zip(x_line, dwell_data)
            for [x,dwell] in list(final_line_data):
                print(f"motor Y [{y}] motor X[{x}] dwell = [{dwell}]ms")

def return_final_scan_points(xdata, ydata, exp_data):
    """
    return a zipped final data consisting of (yposition, xposition, exposure time)
    :param xdata: 1D array of x motor positions
    :param ydata: 1D array of x motor positions
    :param exp_data: 2D array of pixel exposure values
    :return:
    """
    final_data = []
    exp_data = np.flipud(exp_data)
    rows, cols = exp_data.shape

    row_indices = list(range(rows))
    num_rows = 0
    num_ttl_pnts = 0
    for row in row_indices:
        line_data = exp_data[row]
        y = ydata[row]
        no_zero_ele = np.nonzero(line_data)
        if no_zero_ele[0].size > 0:
            x_line  = xdata[tuple(no_zero_ele)]
            dwell_data = line_data[tuple(no_zero_ele)]
            xdelta_line =  np.diff(x_line)
            xdelta_line = np.insert(xdelta_line, 0, 0.0)
            line_time = np.sum(dwell_data)
            npts, = x_line.shape
            num_ttl_pnts += npts
            num_rows += 1
            final_data.append({"y":y,
                               "row": row,
                               "x_indices": no_zero_ele,
                               "x_line": x_line,
                               "xdelta_line": xdelta_line,
                               "dwell_data": dwell_data,
                               "line_time": line_time})
                               # "xshape": x_line.shape,
                               # "dwellshape": dwell_data.shape})
    #give total_time in seconds
    total_time = np.sum(exp_data)
    total_time = (total_time / 1000.0)
    return(final_data, total_time, num_ttl_pnts)


def load_grayscale_image(fname, time_value_of_brightest_pixel_ms=1000.0):
    nrows, ncols, nrgba, data, img_details = load_image(fname)
    data = rgba_to_mono_array(data)
    exp_data = convert_pixels_to_exposures(data, time_value_of_brightest_pixel_ms)
    return(data, exp_data, img_details)

def create_new_image_from_processed_data(nrows, ncols, pos_mins, pos_maxs, final_data):
    """
    Take the processed data and create an image
    nrows, ncols are the original number of pixels of data
    pos_mins, pos_maxs are the min values and max positional values
    :return:
    """
    img_data = np.zeros((nrows, ncols), dtype=np.uint8)
    for dct in final_data:
        row = dct["row"]
        x_indices = dct["x_indices"]
        i = 0
        for x in x_indices[0]:
            img_data[row][x] = dct["dwell_data"][i]
            i += 1
    img_data = np.flipud(img_data)
    return(img_data)


if __name__ == '__main__':

    fname='data/grayscale-trimmed.png'
    fname='data/dock.jpg'
    #fname='mountain.jpg'
    #data = imread("data/lines_5250nmx1875nm_15nmpixels.GIF")
    #imdata = imread("data/screen_shot_20210720_at_11.24.05_am.png")

    fname = "data/MTF-Reticle-MWO-Graphic-cropped.png"
    fname = "data/Resolution_test-neg_0_0044-MWO-Graphic.png"
    fname = "data/elbow_50nmpixels_3x3um.GIF"
    #fname = "data/XY-resolution.GIF"
    fname = "data/Siemens_star_D6_Crossline_negative.png"
    #fname = "data/Polar_coordinate_FK300-MWO-Graphic.png"
    # nrows, ncols, nrgba, data, img_details = load_image(fname)
    # data = rgba_to_mono_array(data)
    # min, max = get_min_max_of_array(data)
    # exp_data = convert_pixels_to_exposures(data, max)
    # xdata = np.linspace(-50,50,ncols)
    # ydata = np.linspace(-50,50,nrows)
    # do_scan(xdata, ydata, exp_data)
    # im = data_to_image(data)
    # im.show()
    # im = data_to_image(exp_data)
    # im.show()

    time_value_of_brightest_pixel_ms = 1000.0
    print(f"processing [{fname}] using time_value_of_brightest_pixel_ms={time_value_of_brightest_pixel_ms}")
    data, exp_data, img_details = load_grayscale_image(fname, time_value_of_brightest_pixel_ms=time_value_of_brightest_pixel_ms)
    total_time_sec = calc_total_time_in_sec(exp_data)
    #print("Approximate Total time to execute scan is %.2f seconds, %.2f minutes" % (total_time_sec, total_time_sec / 60.0))
    rows, cols = exp_data.shape
    # sum = 0.0
    # ttl_pnts = 0
    # for i in list(range(rows)):
    #     line = exp_data[i]
    #     val = np.sum(line) * 0.001
    #     sum += val
    #     pnts = val/0.00003
    #     ttl_pnts += pnts
    #     if ttl_pnts >= 262144:
    #         print("Line [%d] sum = [%.2f] seconds == [%d] points, ttl_points this far [%d] ***" % (i, val, pnts, ttl_pnts))
    #     else:
    #         print("Line [%d] sum = [%.2f] seconds == [%d] points, ttl_points this far [%d]" % (i, val, pnts, ttl_pnts))
    #
    #     #print(np.sum(line))
    # print(f"Total for image is [{sum}] seconds == [{sum/0.00003}] points")
    ncols, nrows = img_details["image.size"]
    xcenter = -6284.2
    xrange = 40.882
    ycenter = 998.014
    yrange = 41.114
    xstart = xcenter - (xrange/2.0)
    xstop = xcenter + (xrange / 2.0)
    ystart = ycenter - (yrange / 2.0)
    ystop = ycenter + (yrange / 2.0)
    xdata = np.linspace(xstart,xstop,ncols)
    ydata = np.linspace(ystart,ystop,nrows)
    xdata_delta = np.diff(xdata)
    final_data, total_time, num_ttl_pnts = return_final_scan_points(xdata, ydata, exp_data)
    print("Total dwell only time of the scan is %.2f seconds, %.2f minutes" % (total_time, total_time/60.0))
    print("ttl number of exposure points is %d" % num_ttl_pnts)
    #for l in final_data:
    #    print(l)

    # img_arr = create_new_image_from_processed_data(nrows, ncols, (xstart,ystart), (xstop, ystop), final_data)
    # im = data_to_image(img_arr)
    # im.show()



