from bcm.devices import MotorQt
from bluesky import RunEngine
from bluesky.plans import scan, count, list_scan
from ophyd.sim import det1, det2, motor1, motor2

# Make plots update live while scans run.
from bluesky.utils import install_kicker

RE = RunEngine({})
from bluesky.callbacks.best_effort import BestEffortCallback

bec = BestEffortCallback()

# Send all metadata/data captured to the BestEffortCallback.
RE.subscribe(bec)
from databroker import Broker

db = Broker.named("pystxm_amb_bl10ID1")

# Insert all metadata/data captured into db.
RE.subscribe(db.insert)


# now instanciate your devices
# zpz = Motor_Qt('SIM_IOC:m704', name='SIM_IOC:m704')
# energy = Motor_Qt('SIM_VBL1610-I10:AMB:ENERGY', name='SIM_VBL1610-I10:AMB:ENERGY')
#
# zp1 = Zoneplate('MYZONER','zp1', zpz, -4.839514, 100, 45, 60)
# zp2 = Zoneplate('MYZONER','zp2', zpz, -6.791682, 240, 90, 35)
# zp3 = Zoneplate('MYZONER','zp3', zpz, -7.76662, 240, 90, 40)
# zp4 = Zoneplate('MYZONER','zp4', zpz, -4.524239, 140, 60, 40)
# zp5 = Zoneplate('MYZONER','zp5', zpz, -4.85874, 240, 95, 25)
# zp6 = Zoneplate('MYZONER','zp6', zpz, -4.85874, 240, 95, 25)
# zp7 = Zoneplate('MYZONER','zp7', zpz, -5.0665680, 250, 100, 25)
# zp8 = Zoneplate('MYZONER','zp8', zpz, 0, 240, 100, 63.79)

# zp1.set_energy(465)
dets = [det1, det2]  # just one in this case, but it could be more than one
#RE(count(dets))
# RE(scan(dets, zp2, 260, 360, 10))

points = [1, 1, 2, 3, 5, 8, 13]
RE(list_scan(dets, motor1, points))

# RE(scan(dets,
#         motor1, -1.5, 1.5,  # scan motor1 from -1.5 to 1.5
#         motor2, -0.1, 0.1,  # ...while scanning motor2 from -0.1 to 0.1
#         11))  # ...both in 11 steps
