
from ophyd.sim import det1, det2
from bcm.devices.ophyd.qt.daqmx_counter_input import LineDetectorFlyerDevice, SimLineDetectorFlyerDevice
from bluesky.plans import count
from bluesky import RunEngine
from databroker import Broker

line_det_dct = {
    "name": "DNM_LINE_DET",
    "class": "LineDetectorDevice",
    "dcs_nm": "TB_ASTXM:Ci:counter:",
    "name": "DNM_LINE_DET",
    "con_chk_nm": "Run",
}

RE = RunEngine({})

db = Broker.named('mongo_databroker')

# Insert all metadata/data captured into db.
RE.subscribe(db.insert)

dflyer = LineDetectorFlyerDevice(line_det_dct["dcs_nm"], name=line_det_dct["name"])

sim_lfly_dev1 = SimLineDetectorFlyerDevice(
        "TB_ASTXM:Ci:counter11:",
        name='SIM_FLYERDET_1',
        stream_names={"stream_names" :"primary"}
    )
sim_lfly_dev1.set_num_points(10)
sim_lfly_dev1.set_num_rows(10)
sim_lfly_dev1.read()

sim_lfly_dev2 = SimLineDetectorFlyerDevice(
        "TB_ASTXM:Ci:counter12:",
        name='SIM_FLYERDET_2',
        stream_names={"stream_names" :"primary"}
    )
sim_lfly_dev2.set_num_points(20)
sim_lfly_dev2.set_num_rows(30)


dets = [det1, sim_lfly_dev1, sim_lfly_dev2]   # a list of any number of detectors

RE(count(dets))

