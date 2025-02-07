"""
Created on 2014-10-06

@author: bergr
"""
import os, sys
from PyQt5 import QtCore, QtGui

import simplejson as json
from cls.utils.dict_utils import dct_get, dct_put, dct_key_exist
from cls.utils.dirlist import dirlist
from cls.utils.log import get_module_logger
from cls.utils.json_threadsave import ThreadJsonSave
from cls.stylesheets import master_colors
from cls.applications.pyStxm import abs_path_of_defaults_file as defaultsDir

_logger = get_module_logger(__name__)

# default zoneplate values
zp1 = {"zp_id": 1, "a1": -4.840, "D": 100.0, "CsD": 45.0, "OZone": 60.0}
zp2 = {"zp_id": 2, "a1": -6.792, "D": 240.0, "CsD": 90.0, "OZone": 35.0}
zp3 = {"zp_id": 3, "a1": -7.767, "D": 240.0, "CsD": 90.0, "OZone": 40.0}
zp4 = {"zp_id": 4, "a1": -4.524, "D": 140.0, "CsD": 60.0, "OZone": 40.0}
zp5 = {"zp_id": 5, "a1": -4.859, "D": 240.0, "CsD": 95.0, "OZone": 25.0}
zps = [zp1, zp2, zp3, zp4, zp5]

# default osa definitions
osa1 = {"osa_id": 1, "D": 30.0}
osa2 = {"osa_id": 2, "D": 50.0}
osa3 = {"osa_id": 3, "D": 40.0}
osas = [osa1, osa2, osa3]


class Defaults(QtCore.QObject):
    """
    This class represents the main object for the application defaults
    """

    changed = QtCore.pyqtSignal()

    def __init__(self, fname, new=False):
        super(Defaults, self).__init__()
        self.defdct = {}
        self.fpath = os.path.join(defaultsDir, fname)
        if os.path.exists(self.fpath):
            new = False
        else:
            new = True

        self.init_defaults(new)

    def init_defaults(self, new=False):
        if new:
            self.defdct = self.init_from_template()
            self.save_json_obj(self.defdct)
        else:
            # read from disk
            self.defdct = self.loadJson(self.fpath)

    def add_section(self, section, value):
        dct_put(self.defdct, section, value)
        self.update()

    def init_from_template(self):
        dct = {}
        dct_put(dct, "APP.UI.COLORS", master_colors)

        dct_put(dct, "PRESETS.OSA.OUT", (-4000, None))
        dct_put(dct, "PRESETS.OSA.ABS_OUT", (-4000, None))
        dct_put(dct, "PRESETS.OSA.CENTER", (-2416, 882.96))
        dct_put(dct, "PRESETS.OSA.ABS_CENTER", (-2416, 882.96))
        dct_put(dct, "PRESETS.DETECTOR.CENTER", (586, 259))
        dct_put(dct, "PRESETS.DETECTOR.ABS_CENTER", (586, 259))

        dct_put(dct, "PRESETS.ZP_PARAMS", zps)

        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.ZP_IDX", 0)
        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.ZP_A1", -6.792)
        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.ZP_D", 240.0)
        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.OSA_IDX", 1)
        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.OSA_D", 50.0)
        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.OSA_A0", 534)
        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.OSA_A0MAX", 554)
        dct_put(dct, "PRESETS.ZP_FOCUS_PARAMS.OSA_IDEAL_A0", 534)

        dct_put(dct, "PRESETS.OSA_PARAMS", osas)

        dct_put(dct, "SCAN.DETECTOR", self.get_default_dct(580, 250, 0, 0))
        dct_put(dct, "SCAN.OSA", self.get_default_dct(580, 250, 0, 0))
        dct_put(dct, "SCAN.OSA_FOCUS", self.get_default_dct(580, 250, 0, 0))
        dct_put(dct, "SCAN.FOCUS", self.get_default_dct(580, 250, 0, 0))
        dct_put(dct, "SCAN.POINT", self.get_default_dct(580, 250, 0, 0))
        dct_put(dct, "SCAN.SAMPLE_PXP", self.get_default_dct(580, 250, 0, 0))
        dct_put(dct, "SCAN.SAMPLE_LXL", self.get_default_dct(580, 250, 0, 0))
        dct_put(dct, "SCAN.LINE", self.get_default_dct(580, 250, 0, 0))

        return dct

    def get_default_dct(self, cx=0, cy=0, cz=0, ct=0):
        rng = 20
        npoints = 20
        step = rng / npoints
        hlf_rng = rng * 0.5
        dct = {}
        dct_put(dct, "CENTER", (cx, cy, cz, ct))
        dct_put(dct, "RANGE", (rng, rng, 0, 0))
        dct_put(dct, "NPOINTS", (npoints, npoints, npoints, npoints))
        dct_put(dct, "START", (cx - hlf_rng, cy - hlf_rng, cz - hlf_rng, ct - hlf_rng))
        dct_put(dct, "STOP", (cx + hlf_rng, cy + hlf_rng, cz + hlf_rng, ct + hlf_rng))
        dct_put(dct, "STEP", (step, step, step, step))
        dct_put(dct, "DWELL", 1.0)
        return dct

    def update(self):
        # _logger.debug('defaults.update()')
        self.save_json_obj(self.defdct)

    def save_json_obj(self, dct):
        saveThread = ThreadJsonSave(dct, fpath=self.fpath)
        saveThread.setDaemon(True)
        saveThread.start()

    def loadJson(self, filename):
        """internal load json data from disk"""
        if os.path.exists(filename):
            file = open(filename)
            js = json.loads(file.read())
            file.close()
        else:
            print("json file doesn't exist: died")
            js = {}
        return js

    def get_scan_def(self, section):
        _roi = self.get(section)

        # roi = {}
        # roi['center'] = (_roi[CENTER][0], _roi[CENTER][1])
        # roi['size'] = (_roi[RANGE][0], _roi[RANGE][1])
        # roi['npts'] = (_roi[NPOINTS][0], _roi[NPOINTS][1])
        # roi['all'] = _roi

        return _roi

    def get_focusscan_def(self, section):
        _roi = self.get(section)

        # roi = {}
        # roi['center'] = (_roi[CENTER][0], _roi[CENTER][1])
        # roi['size'] = (_roi[RANGE][0], _roi[RANGE][1])
        # roi['npts'] = (_roi[NPOINTS][0], _roi[NPOINTS][1])
        # roi['all'] = _roi

        return _roi

    def section_exists(self, section):
        if dct_key_exist(self.defdct, section):
            return True
        else:
            return False

    def get(self, name, create=True):
        """get the object section by name"""
        dct = dct_get(self.defdct, name)
        if (dct is None) and create:
            dct = self.get_default_dct()
            self.add_section(name, dct)

        return dct

    def set(self, name, obj):
        """get the object section by name"""
        dct_put(self.defdct, name, obj)
        self.update()

    def get_main_obj(self):
        """return the entire main object dict"""
        return self.defdct


__all__ = ["Defaults"]
