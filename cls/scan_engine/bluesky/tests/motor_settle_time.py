# Make plots update live while scans run.
import numpy as np
import datetime
import matplotlib.pyplot as plt

from bcm.devices.ophyd.motor import MotorQt
from bluesky.utils import install_kicker
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky import RunEngine
from bluesky import Msg
from ophyd.sim import det1, det2, det3, motor1, motor2, motor3, SynGauss, noisy_det
from bluesky.plans import scan
import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps
from bluesky.plan_stubs import pause, open_run, close_run, sleep, mv, read
from cycler import cycler
from bluesky.plans import list_scan, grid_scan, scan, scan_nd, count
from databroker import Broker
from ophyd import EpicsMotor

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


def pattergen_scan(mtrs,per_pnt_adjustment = 0.09,
    md={"scan_type": "pattern_gen_scan"}
):
    global totalerr_lst, npnts, xdata, ydata, dwell_data, all_actuals, all_dwell, avg_neg, avg_pos
    @bpp.run_decorator(md=md)
    def do_scan():
        #shutter.open()

        mtr_x = mtrs[0]
        mtr_y = mtrs[1]

        i = 0

        for y_pos in ydata:
            yield from bps.mv(mtr_y, y_pos)
            for x_pos in xdata:
                dwell_time = dwell_data[i]
                # dwell_time is in milliseconds but settle time is in seconds
                mtr_x.settle_time = (dwell_time * 0.001) - per_pnt_adjustment
                # print("make_image_pattern_scan_plan: moving X to %.3f" % x_pos)
                a = datetime.datetime.now()
                # rint("dwell=%.2f" % (dwell_time))
                yield from bps.mv(mtr_x, x_pos)
                b = datetime.datetime.now()
                delta = b - a
                delt_sec = delta.total_seconds()
                err = delt_sec - (dwell_time * 0.001)
                all_actuals.append(delt_sec)
                all_dwell.append(dwell_time * 0.001)
                if err < 0.0:
                    avg_neg.append(err)
                else:
                    avg_pos.append(err)
                totalerr_lst.append(err)
                print(f"[{i}] Done: dwell_time={dwell_time * 0.001} sec delta actual={delt_sec} : ERROR = {err}")
                i += 1


        print("PositionerScanClass: make_scan_plan Leaving")


    return (yield from do_scan())

if __name__ == "__main__":
    from ophyd.device import (Component as Cpt, )
    from ophyd import (SimDetector, SingleTrigger, Component, Device,
                       DynamicDeviceComponent, Kind, wait)
    from ophyd.areadetector.plugins import (ImagePlugin, StatsPlugin,
                                            ColorConvPlugin, ProcessPlugin,
                                            OverlayPlugin, ROIPlugin,
                                            TransformPlugin, NetCDFPlugin,
                                            TIFFPlugin, JPEGPlugin, HDF5Plugin,
        # FilePlugin
                                            )


    class MyDetector(SingleTrigger, SimDetector):
        tiff1 = Cpt(TIFFPlugin, 'TIFF1:')


    det = MyDetector("SIMCCD1610-I10-02:", name='test')
    print(det.tiff1.plugin_type)


    det.wait_for_connection()
    det.cam.acquire_time.put(0.5)
    det.cam.acquire_period.put(0.5)
    det.cam.num_images.put(1)
    det.cam.image_mode.put(det.cam.ImageMode.SINGLE)
    det.cam.shutter_mode.put(1) #0==None, 1==Epics PV, 2=Detectopr Output
    det.stage()
    st = det.trigger()
    det.unstage()

    def caught_doc_msg(name, doc):
        print("caught_doc_msg: [%s]" % (name))
        print(doc)


    mtr_x = MotorQt("PZAC1610-3-I12-40", name="SFX")
    mtr_y = MotorQt("PZAC1610-3-I12-41", name="SFY")

    # while not mtr_x.connected:
    #     sleep(0.1)
    # while not mtr_y.connected:
    #     sleep(0.1)

    RE = RunEngine({})
    db = Broker.named("pystxm_amb_bl10ID1")
    # Insert all metadata/data captured into db.
    RE.subscribe(db.insert)
    RE.subscribe(caught_doc_msg)
    bec = BestEffortCallback()
    # Send all metadata/data captured to the BestEffortCallback.
    RE.subscribe(bec)
    per_pnt_adjustment = 0.0
    try:
        for x in list(range(15)):
            start_time = datetime.datetime.now()
            totalerr_lst = []
            all_actuals = []
            all_dwell = []
            avg_neg = []
            avg_pos = []
            RE(pattergen_scan([mtr_x, mtr_y],per_pnt_adjustment))
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
            s1 = f"Using per_pnt_adjustment={per_pnt_adjustment} we end up with the following: rmse = %.3f" % rmse
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
                r' expected time=%.2f sec  actual=%.2f sec' % (total_dwell_time, delt_sec),
                r'$\ rmse=%.2f$ sec' % (rmse,),
                r'$\ per pnt adjustment=%.2f$ sec' % (per_pnt_adjustment,)))

            # place a text box in upper left in axes coords
            ax.text(0.05, 1.09, textstr, transform=ax.transAxes, fontsize=7,
                    verticalalignment='top', bbox=props)
            plt.legend()


            #plt.show()
            plt.savefig("tst_output/tuesday/per_pnt_adjustment_%.2f.jpg" % per_pnt_adjustment)
            per_pnt_adjustment += 0.01  # 9
    except RuntimeError:
        pass
    # header = db[-1]
    # primary_docs = header.documents(fill=True)
    # print(list(primary_docs))
