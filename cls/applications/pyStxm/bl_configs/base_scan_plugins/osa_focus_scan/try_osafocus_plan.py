import matplotlib
matplotlib.use('qt5agg')
#matplotlib.use("TkAgg")

from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.utils import install_kicker, install_qt_kicker



RE = RunEngine({})


bec = BestEffortCallback()
bec.enable_table()

# Send all metadata/data captured to the BestEffortCallback.
RE.subscribe(bec)

# Make plots update live while scans run.

#install_qt_kicker()

from databroker import Broker
#db = Broker.named('mongo_databroker')
db = Broker.named('temp')

# Insert all metadata/data captured into db.
RE.subscribe(db.insert)

from bluesky.utils import ProgressBarManager
RE.waiting_hook = ProgressBarManager()
#
# from ophyd.sim import det1, det2, motor1, motor2  # two simulated detectors
# from bluesky.plans import count
# dets = [det1, det2]   # a list of any number of detectors
#
# RE(count(dets))
#
# # five consecutive readings
# RE(count(dets, num=5))
#
# # five sequential readings separated by a 1-second delay
# RE(count(dets, num=5, delay=1))
#
# # a variable delay
# RE(count(dets, num=5, delay=[1, 2, 3, 4]))
#
#
# from bluesky.plans import scan
# dets = [det]   # just one in this case, but it could be more than one
#
# RE(scan(dets, motor, -1, 1, 10))
#
# from bluesky.plans import rel_scan
#
# RE(rel_scan(dets, motor, -1, 1, 10))
# from bluesky.plans import list_scan
#
# points = [1, 1, 2, 3, 5, 8, 13]
#
# RE(list_scan(dets, motor, points))
#
#
# # Scan motor1 and motor2 jointly through a 5-point trajectory.
# RE(list_scan(dets, motor1, [1, 1, 3, 5, 8], motor2, [25, 16, 9, 4, 1]))
#
# from ophyd.sim import det4
#
# dets = [det4]   # just one in this case, but it could be more than one
#
# from bluesky.plans import grid_scan
#
# RE(grid_scan(dets,
#              motor1, -1.5, 1.5, 3,  # scan motor1 from -1.5 to 1.5 in 3 steps
#              motor2, -0.1, 0.1, 5, False))  # scan motor2 from -0.1 to 0.1in 5
#
#
# uid, = RE(count([det4], num=3))
#
# header = db[uid]
# header.start
#
from bluesky.plans import scan_nd
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from cycler import cycler
from bluesky.plans import scan
from ophyd.sim import motor, motor1, motor2, det, noisy_det
from bluesky.callbacks import LiveTable
import numpy as np

# uid = RE(scan([det], motor, 1, 5, 5), LiveTable([motor, det]))
# RE(scan([det], motor, 1, 5, 5), LiveTable([motor, det]))
# RE(scan([det], motor, 1, 5, 5), LiveTable([motor, det]))
# RE(scan([det], motor, 1, 5, 5), LiveTable([motor, det]))
# RE(scan([det], motor, 1, 5, 5), LiveTable([motor, det]))
# print('uid=%s' % uid)
#
# print('Old uid is ["cc76d12e-5ce0-457c-b810-9bb8b8aa12c7"]')
# print('')

def doit():
    def do_scan():

        x_stpts = np.linspace(-25,25,10)
        y_stpts = np.ones(10) * -1.2345
        zz_stpts = np.linspace(-5000, -6000, 10)

        x_traj = cycler(mtr_x, x_stpts)
        y_traj = cycler(mtr_y, y_stpts)
        zz_traj = cycler(mtr_z, zz_stpts)
        dets = [det]
        md = {'owner': 'arse'}
        #yield from bps.stage(gate)
        #shutter.open()
        # the detector will be staged automatically by the grid_scan plan
        yield from scan_nd(dets, zz_traj * (y_traj + x_traj), md=md)

        #shutter.close()
        # yield from bps.wait(group='e712_wavgen')
        #yield from bps.unstage(gate)

        print("OsaFocusScanClass: make_scan_plan Leaving")


    return (yield from do_scan())

mtr_x = motor #self.main_obj.device("DNM_OSA_X")
mtr_y = motor1 #self.main_obj.device("DNM_OSA_Y")
mtr_z = motor2 #self.main_obj.device("DNM_ZONEPLATE_Z")
mtr_x.name = 'mtr_x'
mtr_y.name = 'mtr_y'
mtr_z.name = 'mtr_z'
uid = RE(doit(), LiveTable([mtr_x, mtr_y, mtr_z, det]))