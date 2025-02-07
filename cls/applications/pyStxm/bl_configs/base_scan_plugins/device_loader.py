"""
Created on April 11 2022

@author: bergr
"""

import os
import pathlib

from ophyd.epics_motor import EpicsMotor
from ophyd.signal import EpicsSignalBase

from bcm.backend import BACKEND
#from bcm.devices import Mbbi
from bcm.devices import Mbbo
from bcm.devices import Bo
from bcm.devices import Transform
from bcm.devices import MotorQt
from bcm.devices import Counter


if BACKEND == 'epics':
    from bcm.devices import sample_abstract_motor, e712_sample_motor
    from bcm.devices import E712WGDevice
    from bcm.devices.ophyd.e712_wavegen.e712 import E712ControlWidget
    from bcm.devices.ophyd.qt.daqmx_counter_input import (
        DAQmxCounter,
        # PointDetectorDevice,
        # LineDetectorFlyerDevice,
        # LineDetectorDevice,
        SimLineDetectorDevice,
        SimLineDetectorFlyerDevice
    )
    from bcm.devices import TucsenDetector
    from bcm.devices.ophyd.sis3820_scalar import SIS3820ScalarDevice
    from bcm.devices.ophyd.qt.daqmx_counter_output import GateDevice
    from bcm.devices.ophyd.camera import camera

else:
    from bcm.devices import MultiSelectable

#from bcm.devices import BaseOphydGate
from bcm.devices import DCSShutter, init_pv_report_file



from cls.appWidgets.main_object import dev_config_base, POS_TYPE_BL, POS_TYPE_ES

# RUSS FEB25 from cls.appWidgets.splashScreen import get_splash
from cls.appWidgets.splashScreen import get_splash
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.types.stxmTypes import (
    sample_positioning_modes,
    sample_fine_positioning_modes,
    endstation_id_types,
)
from cls.utils.cfgparser import ConfigClass
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.utils import make_basedevice

from ophyd.sim import det1, det2, det3, noisy_det


#from bcm.devices.zmq.PUBSUB.asyncio.zmq_device import ZMQMotor, ZMQBo, ZMQMBBo

_logger = get_module_logger(__name__)


class device_config(dev_config_base):
    def __init__(
        self,
        splash=None,
        bl_config_nm=None,
        sample_pos_mode=sample_positioning_modes.COARSE,
        fine_sample_pos_mode=sample_fine_positioning_modes.SAMPLEFINE,
    ):
        super(device_config, self).__init__(splash=splash)

        # self.beamline = 'AMB STXM 10ID1'
        self.beamline = "OOPS"
        # self.bl_config_prfx = get_config_name(__file__)
        self.bl_config_prfx = bl_config_nm
        self.es_id = endstation_id_types.AMB
        self.sample_pos_mode = sample_pos_mode
        self.fine_sample_pos_mode = fine_sample_pos_mode
        self.splash = splash
        self.done = False
        self.sample_rot_angle_dev = None
        self.det_id_counter = 0
        # self.timer = QtCore.QTimer()
        # self.timer.timeout.connect(self.on_timer)

        p = pathlib.Path.joinpath(
            pathlib.Path.cwd(), "bl_configs", bl_config_nm, bl_config_nm + ".py"
        )
        self.init_devices(p.as_posix())

        self.device_reverse_lookup_dct = self.make_device_reverse_lookup_dict()

        # self.perform_device_connection_check(verbose=True)

        if self.sample_pos_mode is sample_positioning_modes.GONIOMETER:
            self.set_exclude_positioners_list(
                [
                    "DNM_SAMPLE_X",
                    "DNM_SAMPLE_Y",
                    "DNM_ZONEPLATE_Z",
                    "DNM_SAMPLE_FINE_X",
                    "DNM_SAMPLE_FINE_Y",
                    "DNM_COARSE_X",
                    "DNM_COARSE_Y",
                    "DNM_SCANCOARSE_X",
                    "DNM_SCANCOARSE_Y",
                    "AUX1",
                    "AUX2",
                    "Cff",
                    "PeemM3Trans",
                ]
            )
        elif self.sample_pos_mode is sample_positioning_modes.COARSE:
            if self.fine_sample_pos_mode is sample_fine_positioning_modes.SAMPLEFINE:
                self.exclude_list = [
                    "DNM_GONI_X",
                    "DNM_GONI_Y",
                    "DNM_GONI_Z",
                    "DNM_GONI_THETA",
                    "DNM_SAMPLE_FINE_X",
                    "DNM_SAMPLE_FINE_Y",
                    "DNM_SAMPLE_ROT_ANGLE",
                    "DNM_SCANCOARSE_X",
                    "DNM_SCANCOARSE_Y",
                    "AUX1",
                    "AUX2",
                    "Cff",
                    "PeemM3Trans",
                ]
            else:
                # zoneplate
                self.exclude_list = [
                    "DNM_GONI_X",
                    "DNM_GONI_Y",
                    "DNM_GONI_Z",
                    "DNM_GONI_THETA",
                    "DNM_ZONEPLATE_X",
                    "DNM_ZONEPLATE_Y",
                    "DNM_ZONEPLATE_Z",
                    "DNM_SAMPLE_ROT_ANGLE",
                    "DNM_SAMPLE_FINE_X",
                    "DNM_SAMPLE_FINE_Y",
                    "DNM_COARSE_X",
                    "DNM_COARSE_Y",
                    "DNM_SCANCOARSE_X",
                    "DNM_SCANCOARSE_Y",
                    "AUX1",
                    "AUX2",
                    "Cff",
                    "PeemM3Trans",
                ]
        # init_posner_snapshot_cbs(self.devices['POSITIONERS'])
        # self.close_splash()

        print("leaving device_config")

    def init_devices(self, cfg_fpath):

        splash = get_splash()
        # set defaults, here change default connection time from 1.0 to 5.0 to see if I can prevent teh get.run.put(1) frm failing to connect when
        # a scan is run
        EpicsSignalBase.set_defaults(connection_timeout=60.0)

        self.dev_dct = self.get_dev_dct(cfg_fpath)

        for k in list(self.dev_dct.keys()):
            # if k.find("DETECTORS") > -1:
            #     print()
            d_lst = self.dev_dct[k]
            for p_dct in d_lst:
                # pad the dict if it doesnt contain a desc field
                if "desc" not in p_dct.keys():
                    p_dct["desc"] = ""

                # if p_dct['name'].find('DNM_BEAM_DEFOCUS') > -1:
                #     print()
                if splash:
                    splash.show_msg(
                        "connecting to: [%s]" % p_dct["name"].replace("DNM_", "")
                    )
                print("connecting to: [%s]" % p_dct["name"].replace("DNM_", ""))

                if k not in self.devices.keys():
                    self.devices[k] = {}
                self.devices[k]["%s" % p_dct["name"]] = self.create_instance(k, p_dct)

        print("finished connecting to devices")
        self.done = True

    def make_device_reverse_lookup_dict(self):
        """
        this function creates a dictionary where the keys ar ethe device names ex: DNM_<whatever> and the values are the DCS signal names
        so one entry would be:
            {'DNM_SAMPLE_FINE_X': 'PZAC1610-3-I12-40'}
        for devices like PRESSURES and TEMPERATURES just return the same name as they have now defined device name
            {'TM1610-3-I12-01': 'TM1610-3-I12-01'}

        ultimately this dict is passed in with teh meta data that gets sent to the nxSTXM suitcase for data storage

        """
        subcat_lst = ["PRESSURES", "TEMPERATURES"]
        skip_lst = [
            "DETECTORS",
            "DETECTORS_NO_RECORD",
            "DIO",
            "SSCANS",
            "PVS_DONT_RECORD",
            "PRESETS",
            "WIDGETS",
            "E712",
            "HEARTBEATS",
        ]
        dct = {}
        for category in self.devices.keys():
            if category in skip_lst:
                continue
            if category in subcat_lst:
                dev_dct = self.devices[category]
                for dev_nm, dev in dev_dct.items():
                    dct[dev_nm] = dev_nm
            else:
                dev_dct = self.devices[category]
                for dev_nm, dev in dev_dct.items():
                    # dct[dev.get_name()] = self.fix_device_nm(dev_nm)
                    if hasattr(dev, "get_name"):
                        dct[dev_nm] = dev.get_name()
                    else:
                        dct[dev_nm] = dev_nm

        return dct

    def fix_device_nm(self, nm_str):
        l = nm_str.lower()
        l = l.replace(".", "_")
        return l

    def create_instance(self, category, dct):
        """
        take a dev dict entry and create the proper instance of it
        """
        # assign a unique id to each detector that will be used to reference it later in code
        if dct['class'].find("E712") > -1:
            from bcm.devices import E712WGDevice
            from bcm.devices.ophyd.e712_wavegen.e712 import E712ControlWidget

        if (dct['class'].find("DAQmx") or dct['class'].find("SimLineDetector"))  > -1:
            from bcm.devices.ophyd.qt.daqmx_counter_input import (
                DAQmxCounter,
                SimLineDetectorDevice,
                SimLineDetectorFlyerDevice
            )

        if dct['class'].find("TucsenDetector") > -1:
            from bcm.devices import TucsenDetector

        if dct['class'].find("SIS3820ScalarDevice") > -1:
            from bcm.devices.ophyd.sis3820_scalar import SIS3820ScalarDevice

        if dct['class'].find("GateDevice") > -1:
            from bcm.devices.ophyd.qt.daqmx_counter_output import GateDevice

        if dct["class"] == "det1":
            d = det1
            d.name = dct["name"]
        elif dct["class"] == "det2":
            d = det2
            d.name = dct["name"]
        elif dct["class"] == "det3":
            d = det3
            d.name = dct["name"]
        elif dct["class"] == "noisy_det":
            d = noisy_det
            d.name = dct["name"]

        elif dct["class"] == "e712_sample_motor":
            d = e712_sample_motor(
                dct["dcs_nm"], name=dct["dcs_nm"]
            )  # , pos_set=dct['pos_type'])

        elif dct["class"] == "TucsenDetector":
            d = TucsenDetector(dct["dcs_nm"], name=dct["dcs_nm"])
            d.name = dct["name"]

        elif dct["class"] == "camera":
            d = camera(dct["dcs_nm"])

        elif dct["class"] == "MotorQt":
            # d = Motor_Qt(dct['dcs_nm'], name=dct['name'], desc=dct['desc'])#, pos_set=dct['pos_type'])
            d = MotorQt(
                dct["dcs_nm"], name=dct["dcs_nm"], desc=dct["desc"]
            )
            if "units" in dct.keys():
                d.set_units(dct["units"])

        elif dct["class"] == "EpicsMotor":
            # d = Motor_Qt(dct['dcs_nm'], name=dct['name'], desc=dct['desc'])#, pos_set=dct['pos_type'])
            d = EpicsMotor(
                dct["dcs_nm"], name=dct["dcs_nm"]
            )

        elif dct["class"] == "sample_abstract_motor":
            fine_mtr = self.devices["POSITIONERS"][dct["fine_mtr_name"]]
            coarse_mtr = self.devices["POSITIONERS"][dct["coarse_mtr_name"]]
            d = sample_abstract_motor(dct["dcs_nm"], name=dct["dcs_nm"])
            d.set_coarse_fine_mtrs(coarse=coarse_mtr, fine=fine_mtr)

        elif dct["class"] == "BaseOphydGate":
            d = BaseOphydGate(dct["dcs_nm"], name=dct["name"])

        elif dct["class"] == "DCSShutter":
            d = DCSShutter(dct["dcs_nm"])
            if 'ctrl_enum_strs' in dct.keys():
                d.set_ctrl_enum_strings(dct["ctrl_enum_strs"])

            if 'fbk_enum_strs' in dct.keys():
                d.set_fbk_enum_strings(dct["fbk_enum_strs"])

        elif dct["class"] == "MultiSelectable":
            d = MultiSelectable(dct["dcs_nm"])
            if 'ctrl_enum_strs' in dct.keys():
                d.set_ctrl_enum_strings(dct["ctrl_enum_strs"])

            if 'fbk_enum_strs' in dct.keys():
                d.set_fbk_enum_strings(dct["fbk_enum_strs"])

            d.desc = dct["desc"]

        elif dct["class"] == "DAQmxCounter":
            d = DAQmxCounter(dct["dcs_nm"], name=dct["name"], scale_val=dct["scale_val"], stream_names=dct["stream_names"],
                pxp_trig_src_pfi=dct["pxp_trig_src_pfi"],  # PFI for triggering point by point
                lxl_trig_src_pfi=dct["lxl_trig_src_pfi"],  # PFI for triggering line by line
                ci_clk_src_gate_pfi=dct["ci_clk_src_gate_pfi"], # PFI for the line gate
                gate_clk_src_gate_pfi=dct["gate_clk_src_gate_pfi"],  # PFI for the gate src clock
                sig_src_term_pfi=dct["sig_src_term_pfi"]   # PFI for pmt signal input
            )
        # elif dct["class"] == "PointDetectorDevice":
        #     d = PointDetectorDevice(
        #         dct["dcs_nm"], name=dct["name"], scale_val=dct["scale_val"]
        #     )
        elif dct["class"] == "GateDevice":
            d = GateDevice(dct["dcs_nm"], name=dct["name"])
        elif dct["class"] == "SimLineDetectorDevice":
            d = SimLineDetectorDevice(dct["dcs_nm"], name=dct["name"])
        elif dct["class"] == "SimLineDetectorFlyerDevice":
            d = SimLineDetectorFlyerDevice(dct["dcs_nm"], name=dct["name"], stream_names=dct["stream_names"])
        # elif dct["class"] == "LineDetectorDevice":
        #     d = LineDetectorDevice(dct["dcs_nm"], name=dct["name"])
        elif dct["class"] == "Bo":
            d = Bo(base_signal_name=dct["dcs_nm"], desc=dct["desc"])

        elif dct["class"] == "Mbbo":
            d = Mbbo(dct["dcs_nm"])

        elif dct["class"] == "Mbbi":
            d = Mbbi(dct["dcs_nm"])
        elif dct["class"] == "Transform":
            d = Transform(dct["dcs_nm"])
        elif dct["class"] == "E712WGDevice":
            d = E712WGDevice(dct["dcs_nm"], name=dct["name"])
        elif dct["class"] == "E712ControlWidget":
            cntr_tpl = dct["counter"].split("/")
            gate_tpl = dct["gate"].split("/")
            cntr = None #self.devices[cntr_tpl[0]][cntr_tpl[1]]
            gate = None #self.devices[gate_tpl[0]][gate_tpl[1]]
            d = E712ControlWidget(dct["dcs_nm"]) #, counter=cntr, gate=gate)
        elif dct["class"] == "SIS3820ScalarDevice":
            d = SIS3820ScalarDevice(dct["dcs_nm"], name=dct["name"])
        elif dct["class"] == "SIS3820ScalarDevice_CHANNEL":
            """
                "name": "DNM_DEFAULT_COUNTER",
                "class": "SIS3820ScalarDevice_CHANNEL",
                "dcs_nm": "MCS1610-310:mcs:",
                "parent_dev": "DNM_SIS3820",
                "chan_name": "DNM_SIS3820_CHAN_00",
                "con_chk_nm": "scanStart",
            """
            pass

        elif dct["class"] == "Counter":
            d = Counter(dct["dcs_nm"])

        elif dct["class"] == "make_basedevice":
            if "units" not in dct.keys():
                dct["units"] = ""
            if "desc" not in dct.keys():
                dct["desc"] = "No description in config"
            if "rd_only" not in dct.keys():
                dct["rd_only"] = False
            # if "backend" not in dct.keys():
            #     dct["backend"] = "epics"
            d = make_basedevice(
                cat=category,
                sig_nm=dct["dcs_nm"],
                name=dct["name"],
                desc=dct["desc"],
                units=dct["units"],
                rd_only=dct["rd_only"],
                backend=BACKEND,
                devcfg=self,
            )
            if dct['name'].find("DNM_RING_CURRENT") > -1:
                # hack, need ring current to appear to be a detector but not in DETECTORS category because
                # the read() will be looking for an attribute called det.id
                category = "DETECTORS"

        else:
            print("Unknown category [%s]" % dct["class"])
            d = None
        if category.find("DETECTORS") > -1:
            # assign a unique id to each detector that will be used later in the code to reference its data
            d.det_id = self.det_id_counter
            self.det_id_counter += 1

        if "enums" in dct.keys():
            # this device has specified string enumuerations for integer values starting at 0 (ex: EPU Polarization)
            # then assign them to the device
            d.enums = dct['enums']
            if 'enum_values' in dct.keys():
                #some enumeration values might not be straight integers (Pixelator)
                d.enum_values = dct['enum_values']
                idx_lst = list(range(len(dct['enum_values'])))
                # Create a dictionary with floats as keys and strings as values
                d.enum_value_to_idx_dct = dict(zip(d.enum_values, idx_lst))


        return d


def ad_warmed_up(detector):
    old_capture = detector.file_plugin.capture.get()
    old_file_write_mode = detector.file_plugin.file_write_mode.get()
    if old_capture == 1:
        return True

    detector.file_plugin.file_write_mode.put(1)
    detector.cam.acquire.put(1)
    detector.file_plugin.capture.put(1)
    verdict = detector.file_plugin.capture.get() == 1
    detector.file_plugin.capture.put(old_capture)
    detector.file_plugin.file_write_mode.put(old_file_write_mode)
    return verdict


def print_keys(d):
    if isinstance(d, list):
        print_keys(d[0])

    for key in d:
        if isinstance(d[key], dict):
            print_keys(d[key])
        else:
            print(key, d[key].is_active())
