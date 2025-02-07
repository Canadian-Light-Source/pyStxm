# Make plots update live while scans run.
import numpy as np
import datetime
import matplotlib.pyplot as plt

from bcm.devices.ophyd.motor import MotorQt
from bluesky.utils import install_kicker
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine
from bluesky import Msg
from ophyd.sim import det1, det2, det3, motor1, motor2, motor3, SynGauss, noisy_det, DetWithCountTime
from bluesky.plans import scan
import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps
from bluesky.plan_stubs import pause, open_run, close_run, sleep, mv, read
from cycler import cycler
from bluesky.plans import list_scan, grid_scan, scan, scan_nd, count
from databroker import Broker
from ophyd import EpicsMotor

from cls.applications.pyStxm.bl_configs.base_scan_plugins.pattern_gen_scan.pattern_gen_utils import *
from cls.utils.stats_utils import calc_rmse

npnts = 6
xdata = np.linspace(-0.15,0.15, npnts)
ydata = np.linspace(-0.15, 0.15, npnts)
dwell_data = np.random.randint(2500, size=npnts*npnts)
totalerr_lst = []
all_actuals = []
all_dwell = []
avg_neg = []
avg_pos = []
long_timeout_occur = []

def pattergen_scan(dets, mtrs, per_pnt_adjustment, final_data, total_pnts, md={"scan_type": "pattern_gen_scan"}
):
    global totalerr_lst, npnts, all_actuals, all_dwell, avg_neg, avg_pos, long_timeout_occur
    totalerr_lst = []
    all_actuals = []
    all_dwell = []
    avg_neg = []
    avg_pos = []
    long_timeout_occur = []
    total_pnts = total_pnts
    @bpp.run_decorator(md=md)
    def do_scan():
        #shutter.open()

        mtr_x = mtrs[0]
        mtr_y = mtrs[1]
        percnt_complete = 0.0
        pnts_done = 0
        rows = 0
        for dct in final_data:
            y_pos = dct["y"]
            yield from bps.mv(mtr_y, y_pos)
            comb_data = zip(dct["x_line"], dct["dwell_data"])
            i = 0
            for x_pos, dwell_time in comb_data:

                # dwell_time is in milliseconds but settle time is in seconds
                mtr_x.settle_time = (dwell_time * 0.001) - per_pnt_adjustment
                # print("make_image_pattern_scan_plan: moving X to %.3f" % x_pos)
                a = datetime.datetime.now()
                # rint("dwell=%.2f" % (dwell_time))
                yield from bps.mv(mtr_x, x_pos)
                #yield from bps.trigger_and_read(dets)
                yield from bps.create(name="primary")
                yield from bps.read(det_with_count_time)
                yield from bps.save()
                pnts_done += 1
                b = datetime.datetime.now()
                delta = b - a
                delt_sec = delta.total_seconds()
                err = delt_sec - (dwell_time * 0.001)
                if delt_sec > 2.0:
                    # remove stupid timeout from stats
                    delt_sec = 0.04
                    long_timeout_occur.append(1)

                all_actuals.append(delt_sec)
                all_dwell.append(dwell_time * 0.001)
                if err < 0.0:
                    avg_neg.append(err)
                else:
                    if err > 2.0:
                        # remove stupid timeout from stats
                        err = 0.4
                    avg_pos.append(err)

                totalerr_lst.append(err)
                percnt_complete = float(pnts_done/total_pnts) * 100.0
                print(f"[{rows},{i}] / {percnt_complete:.2f}% Done: dwell_time={dwell_time * 0.001:.3f} sec delta actual={delt_sec:.3f} sec : ERROR = {err:.3f} ms")
                i += 1
            rows += 1


        print("PositionerScanClass: make_scan_plan Leaving")


    return (yield from do_scan())

def process_image(fname, time_value_of_brightest_pixel_ms=1000.0):

    # fname = 'data/grayscale-trimmed.png'
    # fname = 'data/dock.jpg'
    # # fname='mountain.jpg'
    # # data = imread("data/lines_5250nmx1875nm_15nmpixels.GIF")
    # # imdata = imread("data/screen_shot_20210720_at_11.24.05_am.png")
    #
    # fname = "data/MTF-Reticle-MWO-Graphic-cropped.png"
    # fname = "data/Resolution_test-neg_0_0044-MWO-Graphic.png"
    # fname = "data/elbow_50nmpixels_3x3um.GIF"



    print(f"processing [{fname}] using time_value_of_brightest_pixel_ms={time_value_of_brightest_pixel_ms}")
    data, exp_data, img_details = load_grayscale_image(fname, time_value_of_brightest_pixel_ms=time_value_of_brightest_pixel_ms)
    total_time_sec = calc_total_time_in_sec(exp_data)
    print("Approximate Total time to execute scan is %.2f seconds, %.2f minutes" % (total_time_sec, total_time_sec / 60.0))
    rows, cols = exp_data.shape
    ncols, nrows = img_details["image.size"]
    xcenter = -6284.2
    xrange = 40.882
    ycenter = 998.014
    yrange = 41.114
    xstart = xcenter - (xrange / 2.0)
    xstop = xcenter + (xrange / 2.0)
    ystart = ycenter - (yrange / 2.0)
    ystop = ycenter + (yrange / 2.0)
    xdata = np.linspace(xstart, xstop, ncols)
    ydata = np.linspace(ystart, ystop, nrows)
    xdata_delta = np.diff(xdata)
    final_data, total_time, total_pnts = return_final_scan_points(xdata, ydata, exp_data)
    print("Approximate Total time to execute scan is %.2f seconds, %.2f minutes" % (total_time, total_time / 60.0))
    return(final_data, total_time, xdata, ydata, total_pnts)
    # for l in final_data:
    #    print(l)

    # img_arr = create_new_image_from_processed_data(nrows, ncols, (xstart, ystart), (xstop, ystop), final_data)
    # im = data_to_image(img_arr)
    # im.show()

if __name__ == "__main__":

    from epics import PV
    import os
    import pprint

    def caught_doc_msg(name, doc):
        print("caught_doc_msg: [%s]" % (name))
        print(doc)

    suspnd_controller_fbk = PV("TB_ASTXM:E712:SuspendCtrlrFbk")
    det_with_count_time = DetWithCountTime(name='det', labels={'detectors'})
    dets = [det_with_count_time]
    mtr_x = MotorQt("PZAC1610-3-I12-40", name="SFX")
    mtr_y = MotorQt("PZAC1610-3-I12-41", name="SFY")
    # while not mtr_x.connected:
    #     sleep(0.1)
    # while not mtr_y.connected:
    #     sleep(0.1)
    dir = r'C:\\controls\\sandbox\\pyStxm3\\cls\\applications\\pyStxm\\bl_configs\\base_scan_plugins\\pattern_gen_scan\\data'
    fname = "elbow_50nmpixels_3x3um.GIF"
    fname = "Siemens_star_small.png"
    #fname = "Siemens_star_D6_Crossline_negative.png"
    idx1 = fname.find(".")
    fprefix = fname[:idx1]
    fpath = dir + "\\" + fname


    RE = RunEngine({})
    db = Broker.named("pystxm_amb_bl10ID1")
    # Insert all metadata/data captured into db.
    RE.subscribe(db.insert)
    #RE.subscribe(caught_doc_msg)
    bec = BestEffortCallback()
    # Send all metadata/data captured to the BestEffortCallback.
    #RE.subscribe(bec)
    suspnd_controller_fbk.put(1)
    dir = r'C:\controls\sandbox\pyStxm3\cls\applications\pyStxm\bl_configs\base_scan_plugins\pattern_gen_scan\data\imgs'
    dirList = os.listdir(dir)

    per_pnt_adjustment = 0.00
    time_value_of_brightest_pixel_ms = 1000.0
    try:

        #while time_value_of_brightest_pixel_ms > 0.0:
        for fname in dirList:
            idx1 = fname.find(".")
            fprefix = fname[:idx1]
            final_data, total_time, xdata, ydata, total_pnts = process_image(fpath, time_value_of_brightest_pixel_ms=time_value_of_brightest_pixel_ms)
            start_time = datetime.datetime.now()

            RE(pattergen_scan(dets, [mtr_x, mtr_y],per_pnt_adjustment, final_data, total_pnts))
            stop_time = datetime.datetime.now()
            delta_time = stop_time - start_time
            delt_sec = delta_time.total_seconds()
            total_dwell_time = np.sum(all_dwell)

            neg_arr = np.array(avg_neg)
            pos_arr = np.array(avg_pos)
            npts_neg, = neg_arr.shape
            npts_pos, = pos_arr.shape


            err_arr = np.array(all_actuals)
            dwells_arr = np.array(all_dwell)
            fig, ax = plt.subplots()
            _xdata = list(range(len(all_actuals)))
            totalerr = np.sum(totalerr_lst)
            rmse = calc_rmse(dwells_arr, err_arr)
            #s1 = f"{fprefix}: Using per_pnt_adjustment={per_pnt_adjustment} we end up with the following: rmse = %.3f" % rmse
            s1 = f"{fprefix}: Using time_value_of_brightest_pixel_ms={time_value_of_brightest_pixel_ms} we end up with the following: rmse = %.3f" % rmse
            s2 = "Total error for %d points is %.3f sec, avgerr = %.2f sec" % (npnts * npnts, totalerr, totalerr / (npnts * npnts))
            s3 = "Avg negative[%d] = %.2f sec, Avg positve[%d] = %.2f" % (npts_neg, np.average(neg_arr), npts_pos, np.average(pos_arr))
            print(s1)
            print(s2)
            print(s3)
            # plt.text(xdata[0] + 1, ydata[0] + 2.95, s1, fontsize=7)
            # plt.text(xdata[0] + 1, ydata[0] + 2.75, s2, fontsize=7)
            # plt.text(xdata[0] + 1, ydata[0] + 2.85, s3, fontsize=7)
            plt.plot(_xdata, dwells_arr, label="Dwell")
            plt.plot(_xdata, err_arr, label="Actual")
            # these are matplotlib.patch.Patch properties
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            textstr = '\n'.join((
                r' Using time_value_of_brightest_pixel_ms=%.2f$ we end up with the following: rmse = %.3f sec' % (time_value_of_brightest_pixel_ms, rmse),
                r' Num long timeouts occurred = %d' % len(long_timeout_occur),
                r' expected time=%.2f sec  actual=%.2f sec' % (total_dwell_time, delt_sec)))

            # place a text box in upper left in axes coords
            ax.text(0.05, 1.09, textstr, transform=ax.transAxes, fontsize=7,
                    verticalalignment='top', bbox=props)
            plt.legend()


            #plt.show()
            plt.savefig("tst_output/friday/%s_%.4f.jpg" % (fprefix, time_value_of_brightest_pixel_ms))
            #per_pnt_adjustment += 0.01  # 9
            # if time_value_of_brightest_pixel_ms <= 100.0:
            #     time_value_of_brightest_pixel_ms -= 25.0
            # else:
            #     time_value_of_brightest_pixel_ms -= 250
        suspnd_controller_fbk.put(0)


    except RuntimeError:
        pass
    # header = db[-1]
    # primary_docs = header.documents(fill=True)
    # print(list(primary_docs))
