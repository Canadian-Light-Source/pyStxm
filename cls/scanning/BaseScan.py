"""
Created on Sep 23, 2016

@author: bergr
"""
import os
import copy
import time
from threading import Lock
import itertools
import numpy as np

from PyQt5 import QtCore, QtWidgets

from bluesky.plans import grid_scan
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types
from cls.scan_engine.decorators import conditional_decorator

# from bcm.devices import BaseObject

# from bcm.devices.device_names import *
from cls.appWidgets.dialogs import warn, notify
from cls.stylesheets import get_style
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.plotWidgets.utils import (
    CNTR2PLOT_IS_POINT,
    CNTR2PLOT_IS_LINE,
)
from cls.scanning.BaseScanSignals import BaseScanSignals
from cls.scanning.scan_cfg_utils import make_timestamp_now
from cls.types.beamline import BEAMLINE_IDS
from cls.types.stxmTypes import detector_types
from cls.utils.cfgparser import ConfigClass
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.json_utils import dict_to_json
from cls.utils.log import get_module_logger
from cls.utils.roi_dict_defs import *
from cls.utils.roi_utils import ActiveDataObj
from cls.utils.sig_utils import reconnect_signal, disconnect_signal
from cls.stylesheets import get_style
from cls.appWidgets.dialogs import non_modal_messagebox
from cls.zeromq.epics.epics_api import *
from bcm.devices.ophyd.qt.data_emitters import ImageDataEmitter, SIS3820ImageDataEmitter, SIS3820SpecDataEmitter

from cls.types.stxmTypes import (
    scan_types,
    scan_sub_types,
    sample_positioning_modes,
    sample_fine_positioning_modes,
    image_type_scans,
    data_shape_types,
    data_shapes,
)

# from cls.applications.pyStxm import abs_path_to_ini_file

appConfig = ConfigClass(abs_path_to_ini_file)

# read the ini file and load the default directories
# appConfig = ConfigClass(abs_path_to_ini_file)

NUM_POINTS_LOST_AFTER_EDIFF = 2
DATA_OFFSET = 1

USE_ZMQ = False  # ZMQ is being tested to provide a way of grabbing device position snapshots and other epics data
# instead of getting it drectly in the main GUI event loop
LOAD_ALL = True
MARK_DATA_FOR_TESTING = False
SIMULATE_IMAGE_DATA = False
SIM_DATA = None


TEST_SAVE_INITIAL_FILE = True
SIMULATE_SPEC_DATA = False
SIM_SPEC_DATA = np.linspace(np.pi, np.pi * 2.0, 100)

MODE_NORMAL = 0
MODE_LINE_UNIDIR = 1
MODE_LINE_BIDIR = 2
MODE_POINT = 3
MODE_COARSE = 4
MODE_SCAN_START = 5
MODE_MOVETO_SET_CPOS = 6

scan_cfg_status_codes = Enum("NORMAL", "SCAN_CONFIG_ERROR")

_logger = get_module_logger(__name__)


def get_sequence_nums(first_num, ttl_pnts):
    return list(range(first_num, first_num + ttl_pnts))


def get_rows(row_lst, npnts):
    return np.tile(row_lst, npnts)


def get_columns(col_lst, npnts):
    lst = list(range(0, len(col_lst)))
    return np.repeat(lst, npnts)


def get_ttl_num_pnts(erois):
    ttl = 0
    for eroi in erois:
        ttl += len(eroi)
    return ttl


class BaseScanException(Exception):
    pass


#class BaseScan(BaseObject):
class BaseScan(QtCore.QObject):
    """
    This class is the high level interface for an abstract scan. It is the high level controller for up to 4
     individual sscan's that it contains, so if the scan record prefix is '%sstxm:energy' then there will exist
     individual sscan epics records:

     EX: for main set of sscan records called ambstxm:energy:scan1 -> scan4
         ambstxm:energy:scan4
          ambstxm:energy:scan3
           ambstxm:energy:scan2
            ambstxm:energy:scan1

     the set of linked scans that make up an energy scan can then be easily configured such that:
          ambstxm:energy:scan4 - is the top level (most outer loop) scan of the EV
              ambstxm:energy:scan3 - is the next level scan of the EPU polarity
                   ambstxm:energy:scan2 - is the bottom level scan of the EPU offset
                        ambstxm:energy:scan1 - is currently unused
    """

    data_start = QtCore.pyqtSignal(object)
    data_ready = QtCore.pyqtSignal()
    top_level_progress = QtCore.pyqtSignal(object)  # progress
    low_level_progress = QtCore.pyqtSignal(object)  # progress
    all_done = QtCore.pyqtSignal()
    sigs_disconnected = QtCore.pyqtSignal()
    new_spatial_start = QtCore.pyqtSignal(object)
    saving_data = QtCore.pyqtSignal(object)

    # def __init__(self, scan_prefix="", map_section="", main_obj=None, cmd_file=None):
    def __init__(self, scan_prefix="", map_section="", main_obj=None, cmd_file=None):
        """
        __init__(): description

        :param scan_prefix: scan_prefix description
        :type scan_prefix: scan_prefix type

        :param map_section: a string used to identify this sscan from others when the setpoints and other data are retrieved when the scan is done
                            This map section name is used when the dict of data that is sent to the data_IO module and it is pulled out there when being written to disk
                            examples for current scans are:
                                Detector Scan = 'XY'
                                Focus Scan = 'FOCUS'
                                Line SPectra Scan = 'LINESPEC'
                                OSA Focus Scan = 'XYZ'
                                OSA Scan = 'XY'
                                Positioner (Generic) Scan = 'X'
                                Sample Image Scan = 'SAMPLEXY_EV'
        :type map_section: string

        :param main_obj: This is a MAIN_OBJ from the application, it contains all of the distributed control device connections (currently only EPICS supported)
        :returns: None
        """
        #super(BaseScan, self).__init__(scan_prefix)
        super(BaseScan, self).__init__(None)
        self.sigs = BaseScanSignals()

        if main_obj is None:
            _logger.error(
                "BaseScan needs to be initialized with instance of applications main device object (MAIN_OBJ)"
            )
            exit()
        self.main_obj = main_obj
        # self.script_dir = appConfig.get_value('MAIN', 'sscan_script_dir')

        self.evidx_mutex = Lock()
        self._current_ev_idx = 0
        self.imgidx_mutex = Lock()
        self._current_img_idx = 0
        self.sproi_idx_mutex = Lock()
        self._current_sp_id = 0

        self._consecutive_scan_mutex = Lock()
        self._consecutive_scan_cntr = 0

        # this is used for non Ophyd detectors to have their own subscriptions to plotting functions
        self._det_subscriptions = []

        # set config status code
        self.config_error = scan_cfg_status_codes.NORMAL
        # the following is a member variable that is used to keep track which spatial point the
        # incoming count value belongs to, so if user is taking spectra of 3 different spatial points
        # and each spectra is comprised of 50 energy points, this variable will be incremented in the following way
        #
        # points as they come in from detector
        # spatial position value is for = sp1   sp2   sp3   sp1   sp2   sp3   ...
        # count values as they come in  =  p1    p2    p3    p4    p5    p6    ...    p50
        #           _pnt_spec_spid_cntr  =   0     1     2     0     1     2    ...
        #
        self.pnt_spec_spid_cntr_mutex = Lock()
        self._pnt_spec_spid_cntr = 0

        self.is_lxl = False
        self.is_pxp = False
        self.is_point_spec = False
        self.is_line_spec = False
        self.is_fine_scan = False
        self.save_request_made_already = True
        self.start_gate_and_cntr = True
        self.e712_enabled = False
        self.is_zp_scan = False
        self.plot_update_divisor = 1 # this is so that each scan can have control of how often the plotter updates data for its scan
                                     # which can occupy too much of the Qt event loop if data comes in too fast

        self.scan_prefix = scan_prefix
        self.top_level_scan = None
        self.data_level_scan = None
        self.bottom_level_scan = None

        self.setupScan = None

        # self.cmd_file = cmd_file
        # self.cmd_file_pv = self.add_pv('%s:cmd_file' % self.scan_prefix)
        self.scan_plan = None
        self.scan_velo = None
        self.scan_aborted = False

        self.numX = None
        self.numY = None
        self.numZ = None
        self.numE = None
        self.numImages = None
        self.numSPIDS = None
        self.num_points = 0

        self._dets = []
        self.gate = None # todo: remove all references to gate
        self.counter = None
        self.shutter = None

        self.active_user = None
        self.hdr = None
        self.data = None
        self.data_dct = None
        self.spid_data = None

        self.roi = None
        self.data_shape = None

        self.image_started = False
        self.busy_saving = False
        self.scan_done = True
        self.scan_started = False
        self.signals_connected = False
        self.file_saved = False
        self._abort = False
        self.stack = False
        self.use_hdw_accel = False
        self.is_multi_spatial = False
        self.is_multi_goni_theta = False

        self.cur_scan_data_dir = None

        # setup defaults
        self.selected_gate_nm = "DNM_GATE"
        #self.selected_counter_nm = "DNM_COUNTER_APD"
        self.selected_shutter_nm = "DNM_SHUTTER"
        self.default_detector_nm = None #this must be set by the inheriting class to the first in the list of selected detectors "DNM_DEFAULT_COUNTER"

        # user settable flags from the .ini file
        self.save_all_data = False
        self.save_jpgs = True

        self.child_scan_on_done = None
        self.sample_positioning_mode = self.main_obj.get_sample_positioning_mode()
        self.fine_sample_positioning_mode = (
            self.main_obj.get_fine_sample_positioning_mode()
        )
        self.datafile_prfx = self.main_obj.get_datafile_prefix()

        # self.scans_list = []
        self.scanlist = []
        self.scan_map = {}
        # this is a dict that acts as a sequence map, from seq of point to img_idx, y, x for teh plotter
        self.seq_map_dct = None

        # a list that each scan can populate to record data from
        self.counter_dct = []

        # a dict that a scan can populate with device names found in MAIN_OBJ.device that will be asked for a get_position()
        # on every on_data_level_done so that the value can be recorded and subsequently written to the data file
        self.update_dev_lst = {}
        self.update_dev_data = []
        self.ev_setpoints = []

        self.scan_type = None  # meant to be set in the parent scan of type like IMAGESCANLINEBYLINE or something
        self.sp_id_list = None
        self._master_sp_id_list = None
        # self.pdlys = {}
        self.data_name_dct = {}

        self.section_name = map_section
        # self.add_scan_map_section(map_section)

        self._bi_dir = False

        self._emitter_sub = None
        self._emitter_cb = None

        self._sel_zp_dct = None

        ss = get_style()
        self.mtr_recenter_msg = non_modal_messagebox("Motor Recenter Required", "The new scan requires a change to the position of the coarse and fine motors, \n "
                                                                                "the fine stages must be autozero'd and the interferometer feedback reset\n "
                                                                                "the scan will begin shortly", font_size=20)
        self.mtr_recenter_msg.setStyleSheet(ss)

    def set_scan_as_aborted(self, val):
        """

        """
        self._abort = val

    def get_is_scan_aborted(self):
        """

        """
        return self._abort

    def populate_ev_setpoints(self):
        """
        walk all evrois and place the setpoints into this single list
        """
        evs = []
        for e_roi in self.e_rois:
            evs.append( e_roi[SETPOINTS])

        # Collapse the lists into a single list of arrays
        collapsed_arr = np.concatenate(evs)
        self.ev_setpoints = collapsed_arr

    def get_plot_update_divisor(self):
        """
        return the scans divisor for controlling plotter updates
        to be implemented by scan class if so desired
        """
        return self.plot_update_divisor

    def set_plot_update_divisor(self, val):
        """
        set the plotter update divisor for the scan
        """
        self.plot_update_divisor = val

    def get_accel_deccel_pvs(self):
        """
        depending on if scan is a fine or coarse scan return the pvs used to get
        the percentage of range to use in calculation of scan start and stop distances
        """
        # determine if the scan will violate soft limits
        if self.is_fine_scan:
            accel_dis_prcnt_nm = "DNM_FINE_ACCEL_DIST_PRCNT"
            deccel_dis_prcnt_nm = "DNM_FINE_DECCEL_DIST_PRCNT"
        else:
            accel_dis_prcnt_nm = "DNM_CRS_ACCEL_DIST_PRCNT"
            deccel_dis_prcnt_nm = "DNM_CRS_DECCEL_DIST_PRCNT"

        accel_dist_prcnt_pv = self.main_obj.device(accel_dis_prcnt_nm)
        deccel_dist_prcnt_pv = self.main_obj.device(deccel_dis_prcnt_nm)

        return(accel_dist_prcnt_pv, deccel_dist_prcnt_pv)

    def test_flyer_iface(self, dets):
        """
        a simple test function for flyer detectors
        """
        for d in dets:
            d.stage()
            d.kickoff()
            print(d.describe())
            print(d.read())
            d.complete()
            print(d.describe_collect())
            d.collect()
            d.unstage()

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        to be implemented by inheriting class
        """
        pass

    def pre_flight_chk(self):
        """
        before the scan plan is configured and executed it must first pass a pre flight check,
        to be implemented by inheriting class
        :return:
        """
        return True

    def generate_ev_roi_seq_image_map(self, erois, nxpnts):
        """
            used primarily by Linespec scans that can have multiple images per scan where each image represents a
            different energy range and resolution
        :param erois:
        :param nxpnts:
        :return:
        """
        dct = {}
        ev_idx = 0
        seq_num = 0
        nxpnts = int(nxpnts)
        for eroi in erois:
            # col_lst = [[0,1,2], [3,4,5,6,7,8], [11,22,33,44,55,66,77,88,99]]
            ev_lst = eroi[SETPOINTS]
            row_lst = list(range(0, nxpnts))
            # ttl_ev_npnts = get_ttl_num_pnts(ev_lst)
            ttl_ev_npnts = int(eroi[NPOINTS])

            seq = get_sequence_nums(seq_num, ttl_ev_npnts * nxpnts)
            seq_num = seq[-1] + 1
            # rows = get_rows(row_lst, len(ev_lst[0]))
            rows = get_rows(row_lst, ttl_ev_npnts)
            cols = get_columns(eroi, nxpnts)

            ev_idx_arr = np.ones(len(seq)) * ev_idx
            ttl = zip(seq, ev_idx_arr, rows, cols)
            for s, img_idx, r, c in ttl:
                # print('(%d, %d, %d, %d)' % (s, img_idx, r, c))
                dct[s] = {"img_num": int(img_idx), "row": r, "col": c}

            ev_idx += 1
        return dct

    def generate_2d_seq_image_map(self, num_evs, num_pols, nypnts, nxpnts, lxl=False):
        """
            used primarily by Linespec scans that can have multiple images per scan where each image represents a
            different energy range and resolution
        :param energies: num energies
        :param nypnts: num rows
        :param nxpnts: num columns
        :param lxl: generate map for a line by line scan where each num in sequence is a row,
            if False then Point by Point scan where each num in sequence is a pixel
        :return:
        """
        dct = {}
        seq_num = 0
        nypnts = int(nypnts)
        nxpnts = int(nxpnts)
        energies = int(num_evs)
        img_idx = 0
        for pol_idx in list(range(0, num_pols)):
            for ev_idx in list(range(0, energies)):
                row_lst = list(range(0, nypnts))
                col_lst = list(range(0, nxpnts))

                if not lxl:
                    seq = get_sequence_nums(seq_num, nypnts * nxpnts)
                    seq_num = seq[-1] + 1
                    rows = np.repeat(row_lst, nxpnts)
                    cols = np.tile(col_lst, nypnts)
                    ev_idx_arr = np.ones(len(seq)) * ev_idx
                else:
                    seq = get_sequence_nums(seq_num, nypnts)
                    seq_num = seq[-1] + 1
                    rows = row_lst
                    cols = np.zeros(nypnts)
                    ev_idx_arr = np.ones(len(seq)) * ev_idx

                ttl = zip(seq, ev_idx_arr, rows, cols)
                for sequence_num, __img_idx, row, col in ttl:
                    # print('(%d, %d, %d, %d)' % (s, img_idx, r, c))
                    dct[sequence_num] = {"img_num": int(img_idx), "row": row, "col": col, "ev_idx": ev_idx,
                                         "pol_idx": pol_idx}

                img_idx += 1

        return dct

    def gen_spectrum_scan_seq_map(self, num_ev, sp_id_lst, num_pol=1):
        num_spids = len(sp_id_lst)
        num_ev_pol = num_ev * num_pol
        ev_idx_lst = list(range(0, num_ev))
        pol_idx_lst = list(range(0, num_pol))
        seq = list(range(0, num_ev_pol * num_spids))
        spid_seq = np.tile(sp_id_lst, num_ev_pol)
        es = np.repeat(ev_idx_lst, num_spids)
        ev_seq = np.tile(es, num_pol)
        pol_seq = np.repeat(pol_idx_lst, num_ev * num_spids)
        entry_lst = ["entry%d" % s for s in sp_id_lst]
        entry_seq = np.tile(entry_lst, num_ev_pol)
        i = 0
        dct = {}
        for s in seq:
            dct[s] = {
                "entry": entry_seq[i],
                "e_idx": ev_seq[i],
                "sp_idx": spid_seq[i],
                "sp_id": spid_seq[i],
                "pol_idx": pol_seq[i],
            }
            i += 1
        return dct

    def gen_spid_seq_map(self, sp_id_lst, points_for_spid):
        """
        given a list of sp_ids and the max number of points expected PER spid, create a zipped list of (spid, seq_number)
        :return:
        """

        ttl_spid_lst = list(np.tile(sp_id_lst, len(points_for_spid)))
        ttl_sequence_points = len(sp_id_lst) * len(points_for_spid)
        seq_lst = range(0, ttl_sequence_points)
        ttl_points_for_spid = list(np.repeat(points_for_spid, len(sp_id_lst)))
        l2 = list(zip(ttl_spid_lst, ttl_points_for_spid))

        # ttl_sp_id_lst = sp_id_lst * len(points_for_spid)
        # ttl_points_for_spid = points_for_spid * len(sp_id_lst)
        # zipped_sp_id_map = dict(itertools.zip_longest(seq_lst, ttl_sp_id_lst, ttl_points_for_spid ))
        zipped_sp_id_map = dict(itertools.zip_longest(seq_lst, l2))
        return zipped_sp_id_map

    def get_zoneplate_info_dct(self):
        return self._sel_zp_dct

    def set_zoneplate_info_dct(self, zp_dct):
        self._sel_zp_dct = zp_dct

    def configure_devs(self, dets):
        """
        to be implemnted by inheriting class
        :param dets:

        :return:
        """
        # make the first selected detector in the list the "default"
        if dets is not None and len(dets) > 0:
            #ok this is not very elegant so likely a better solution will be implemented in the future
            #if the first selected detector is the SIS3820 then grab the name of the first enabled channel and use it as the default
            #as this is the name that will be first in the data file
            if dets[0].name.find('SIS3820') > -1:
                #the SIS3820 ophyd dev has a function to retriev ethe enabled channels numbers and names
                ch_nums, ch_names, ch_fbk_attrs = dets[0].get_enabled_chans()
                self.default_detector_nm = ch_names[0]
            else:
                #just use whatever the first detectors name is
                self.default_detector_nm = dets[0].name
        self._dets = dets


    def make_scan_plan(self, dets, md=None, bi_dir=False, show_summarize=False):
        """
        the main call to configure devices and create the scan plan, this is called from stxmMain
        when start is pressed, each scan pluggin scan class can/must override the configure_devs() function
        """

        self.configure_devs(dets)

        if self.is_pxp:
            plan = self.make_pxp_scan_plan(dets, md=md, bi_dir=bi_dir)
        else:
            plan = self.make_lxl_scan_plan(dets, md=md, bi_dir=bi_dir)

        if show_summarize:
            from bluesky.simulators import summarize_plan
            summarize_plan(plan)
        return(plan)

    def dets_names(self, dets):
        """
        this needs to return the detector name as it is going to show up in the primary or baseline data streams
        this means that it will likely be the name of the device plus the attribute that is read which returns the data
        when it is read, so for a line detector whose name is DNM_LINE_DET the attribute that reads the line data
        is waveform_rbv so the name that neesd to be placed in the list here is "DNM_LINE_DET_waveform_rbv"

        The easiest and most accurate way to get this name is to pull if from the describe() call to that detector
        """

        dlst = []
        for d in dets:
            if hasattr(d, 'describe'):
                dnm = list(d.describe().keys())[0]
            # else:
            #     dnm = 'GE_CCD'
            # #dnm = d.name
            if not dnm in dlst:
                dlst.append(dnm)
        return dlst

    # def make_standard_metadata(self, entry_name, scan_type, dets=[self.main_obj.device('DNM_DEFAULT_COUNTER')], override_xy_posner_nms=False):
    def make_standard_metadata(
        self, entry_name, scan_type, dets=[], override_xy_posner_nms=False
    ):
        """
        return a dict that is standard for all scans and that gives teh data suitcase all it needs to be able to save
        the nxstxm datafile
            IMG_EXP_DATA
        :param entry_name:
        :param scan_type:
        :param primary_det:
        :param override_xy_posner_nms:
        :return:

        """
        if len(dets) == 0:
            dets = []#dets = [self.main_obj.device("DNM_DEFAULT_COUNTER")]

        dct = {}
        dct["entry_name"] = entry_name
        dct["scan_type"] = scan_type
        dct["is_pxp"] = 1 if self.is_pxp == True else 0
        dct["sp_id_lst"] = self._master_sp_id_list
        dct["rois"] = self.get_rois_dict(override_xy_posner_nms)
        dct["num_points"] = self.get_num_points_in_scan()
        dct["num_prog_events"] = self.get_num_progress_events()

        # dct['device_reverse_lu_dct'] = self.main_obj.get_device_reverse_lu_dct()
        dct["dwell"] = self.dwell
        dct["primary_det"] = self.dets_names(dets)
        # dct["detector_names"] = self.dets_names(dets)
        dct["default_det"] = self.default_detector_nm
        dct["ring_current_nm"] = "DNM_BASELINE_RING_CURRENT"
        dct["zp_def"] = self.get_zoneplate_info_dct()
        dct["rotation_angle"] = self.main_obj.get_sample_rotation_angle()
        # self._wdg_com['SPATIAL_ROIS']['1']['ACTIVE_DATA_OBJ']['CFG']['DATA_DIR'] and ['DATA_FILE_NAME']
        dct["wdg_com"] = dict_to_json(self.wdg_com)
        ado = dct_get(self.sp_db, SPDB_ACTIVE_DATA_OBJECT)
        dct["data_dir"] = ado["CFG"]["DATA_DIR"]
        dct["data_filename"] = ado["CFG"]["DATA_FILE_NAME"]
        # include the full sequence map so that spectrum scans can organize the data in the suitcase later
        dct["sequence_map"] = dict_to_json(self.img_idx_map)
        dct["img_idx_map"] = dict_to_json(
            self.img_idx_map["%d" % self._current_img_idx]
        )
        dct["rev_lu_dct"] = self.main_obj.get_device_reverse_lu_dct()
        for d in dets:
            if d.name.find("SIS3820") > -1:
                dct["sis3820_data_map"] = dict_to_json(copy.copy(d.enabled_channels_lst))
        return dct

    def get_rois_dict(self, override_xy_posner_nms=False):
        dct = {}
        for sp_id in self._master_sp_id_list:
            dct[sp_id] = {}
            dct_put(dct[sp_id], SPDB_X, dct_get(self.sp_rois[sp_id], SPDB_X))
            dct_put(dct[sp_id], SPDB_Y, dct_get(self.sp_rois[sp_id], SPDB_Y))
            dct_put(dct[sp_id], SPDB_Z, dct_get(self.sp_rois[sp_id], SPDB_Z))
            if override_xy_posner_nms:
                # force the x and y positioner names to be Sample X and Y
                dct_put(dct[sp_id], SPDB_XPOSITIONER, "DNM_SAMPLE_X")
                dct_put(dct[sp_id], SPDB_YPOSITIONER, "DNM_SAMPLE_Y")

            dct_put(dct[sp_id], SPDB_GX, dct_get(self.sp_rois[sp_id], SPDB_GX))
            dct_put(dct[sp_id], SPDB_GY, dct_get(self.sp_rois[sp_id], SPDB_GY))
            dct_put(dct[sp_id], SPDB_GZ, dct_get(self.sp_rois[sp_id], SPDB_GZ))
            dct_put(dct[sp_id], SPDB_GT, dct_get(self.sp_rois[sp_id], SPDB_GT))

            dct_put(
                dct[sp_id], SPDB_EV_ROIS, dct_get(self.sp_rois[sp_id], SPDB_EV_ROIS)
            )

            dct_put(dct[sp_id], SPDB_ZX, dct_get(self.sp_rois[sp_id], SPDB_ZX))
            dct_put(dct[sp_id], SPDB_ZY, dct_get(self.sp_rois[sp_id], SPDB_ZY))
            dct_put(dct[sp_id], SPDB_ZZ, dct_get(self.sp_rois[sp_id], SPDB_ZZ))

            dct_put(dct[sp_id], SPDB_OX, dct_get(self.sp_rois[sp_id], SPDB_OX))
            dct_put(dct[sp_id], SPDB_OY, dct_get(self.sp_rois[sp_id], SPDB_OY))
            dct_put(dct[sp_id], SPDB_OZ, dct_get(self.sp_rois[sp_id], SPDB_OZ))

        return dct

    def filter_detector_list(self, dets, det_type=detector_types.POINT):
        """
        a base level function that will remove selected detectors that do not
        support a particular interface like a flyer interface for scans that are executed
        by the E712 wave generator, that scan is a flyer because the 2D raster scan is performed
        on the E712 wavegenerators that means that the scan plan does not loop each line calling
        trigger_and_read() the detectors, therefore only detectors that support the flyer interface
        will be allowed, this function allows each scan class to tailor its detectors used in the scan.

        To be implimented by inheriting class
        dets: is a list of ophyd detector objects
        det_type: is a string that says the types of detectors to allow in return list, valid strings are: point, line, line_flyer
        returns a list of detector ophyd objects
        """
        _dets = []
        for d in dets:
            # the following if block is basically a check for the detectotrs that are of type DAQmxCounter
            # the DAQmxCounter device contains instances of point, line and line_flyer ohphyd devices thats why we need to
            # set it to the type we want before allowing it into the detector list
            if hasattr(d, "get_device_by_type"):
                _dets.append(d.get_device_by_type(det_type))
            else:
                #we assume it is an ophyd device of the correct type
                _dets.append(d)
        return(_dets)

    def clear_subscriptions(self, ew):
        """
        clear a subscription from the engine widget
        :param ew:
        :return:
        """
        if self._emitter_sub is not None:
            ew.unsubscribe_cb(self._emitter_sub)
        self._emitter_cb = None

        if hasattr(self, "_det_subscriptions"):
            if self._det_subscriptions is not None:
                self.clear_detector_subscriptions()

    def init_subscriptions(self, ew, func, det_lst):
        """
        Base init_subscriptions is used by most scans
        :param ew:
        :param func:
        :param det_lst is a list of detector ophyd objects
        :return:
        """
        #for now connect only the first detector
        counter_nm = det_lst[0].name
        det = self.main_obj.device(counter_nm)
        if self.scan_type in image_type_scans:
            # if not counter_nm:
            #     counter_dev = self.main_obj.device("DNM_DEFAULT_COUNTER")
            #     counter_nm = list(counter_dev.describe().keys())[0]

            # self._emitter_cb = ImageDataEmitter('%s_single_value_rbv' % DNM_DEFAULT_COUNTER, y='mtr_y', x='mtr_x', scan_type=self.scan_type, bi_dir=self._bi_dir)
            if counter_nm.find("SIS3820") > -1:
                self._emitter_cb = SIS3820ImageDataEmitter(
                    det.det_id,
                    counter_nm,
                    det_dev=det,
                    is_pxp=self.is_pxp,
                    y="mtr_y",
                    x="mtr_x",
                    scan_type=self.scan_type,
                    bi_dir=self._bi_dir,
                )
            else:
                self._emitter_cb = ImageDataEmitter(
                    det.det_id,
                    counter_nm,
                    y="mtr_y",
                    x="mtr_x",
                    scan_type=self.scan_type,
                    bi_dir=self._bi_dir,
                )

            self._emitter_cb.set_row_col(
                rows=self.y_roi[NPOINTS],
                cols=self.x_roi[NPOINTS],
                seq_dct=self.seq_map_dct,
            )
            self._emitter_sub = ew.subscribe_cb(self._emitter_cb)
            self._emitter_cb.new_plot_data.connect(func)
        else:
            _logger.error("Need to implement this for Spectra scans")

    def get_mtr_max_velo(self, mtr):
        """
        take a motor object and get it's max velo if the max velo is not set then
        use the current velo
        """
        if hasattr(mtr, "get_max_velo"):
            vmax = mtr.get_max_velo()
        else:
            _logger.warn("mtr does not support the  get_max_velo() method, using current velocity as max velocity")
            vmax = mtr.get("velocity")
        return(vmax)

    def calc_scan_velo(self, mtr, rng, npoints, dwell):
        """
        This base class function calculates and verifies ththe scan velocity, then returns it
        mtr: is the motor involved
        rng: is the range of the line
        npoints: is the number of points
        dwell: is in milliseconds
        """
        scan_velo = rng / ((npoints * dwell) * 0.001)
        ret = self.check_scan_velo(mtr, scan_velo)
        if not ret:
            #set an invalid scan velocity
            scan_velo = 0

        return(scan_velo)

    def check_scan_velo(self, mtr, desired_velo):
        """
        a function that takes a motor and checks its max velocity against
        what the desired scan velocity is, if it is greater then popup a
        warning message that the user needs to alter their scan params
        (num points increase dwell time) to reduce the scan velocity
        """
        ret = True
        if hasattr(mtr, "get_max_velo"):
            vmax = mtr.get_max_velo()
            if desired_velo > vmax:
                notify("Error scan velo is faster than motor's max velocity",
                       f"Calculated scan velocity {desired_velo} is too fast, max is {vmax}, increase number of points or dwell time and try again\n",
                       "Ok")
                ret = False
        else:
            notify("Warning: unable to check scan velocity", "The motor does not have the get_max_velo() method", "Ok")
            ret = False
        return(ret)


    def generate_scan_plan(self, detectors, md=None, bi_dir=False):
        """
        call the individual scans make_scan_plan() and return that Bluesky scan plan
        :return:
        """
        #from bluesky.simulators import check_limits

        self.scan_plan = self.make_scan_plan(detectors, md=md, bi_dir=bi_dir)
        if self.scan_plan is None:
            _logger.error(
                "generate_scan_plan: scan class cannot return a None scan plan"
            )

        #check_limits(self.scan_plan)

        return self.scan_plan

    def set_counter_dct(self, cntr_dct):
        """
        a list of counter names used to record data

            cntr_dct = {
                'counter0' = {
                    'devname': DNM_COUNTER,
                    'dev':  MAIN_OBJ.device('DNM_COUNTER')
                    }
                'ccd0' = {
                    'devname': DNM_CCD,
                    'dev':  MAIN_OBJ.device('DNM_CCD')
                    }
                }



        :param cntr_dct:
        :return:
        """
        self.counter_dct = cntr_dct

    def set_counter_dct(self, cntr_dct):
        """
        a list of counter names used to record data

            cntr_dct = {
                'counter0' = {
                    'devname': DNM_COUNTER,
                    'dev':  MAIN_OBJ.device('DNM_COUNTER')
                    }
                'ccd0' = {
                    'devname': DNM_CCD,
                    'dev':  MAIN_OBJ.device('DNM_CCD')
                    }
                }



        :param cntr_dct:
        :return:
        """
        self.counter_dct = cntr_dct


    def init_devices(self):
        """
        This is called from BaseScan
        init_devices(): inits the devices used to count, I will need to expand this to accept multiple counters

        :returns: None
        todo:: I will need to expand this to accept multiple counters
        """
        self.gate = self.main_obj.device(self.selected_gate_nm)
        #self.counter = self.main_obj.device(self.selected_counter_nm)
        self.counter = self.main_obj.device(self.default_detector_nm)
        self.shutter = self.main_obj.device(self.selected_shutter_nm)

    def init_set_scan_levels(self):
        """
        init_set_scan_levels(): to be implemented by inheriting class

        :returns: None
        """
        pass

    def init_signals(self):
        """
        init_signals(): to be implemented by inheriting class

        :returns: None
        """
        pass


    def set_save_all_data(self, val):
        """
        set_save_all_data(): sets the flag that decides wether or not to prompt the user everytime a scan is done if they want to save the data or not

        :returns: None
        """
        self.save_all_data = val

    def set_save_jpgs(self, val):
        """
        set_save_jpgs(): sets the flag that decides wether or not to save a jog thumbnail everytime an image scan is done

        :returns: None
        """
        self.save_jpgs = val

        # print 'on_top_level_progress_changed [%.2f]' % val
        self.top_level_progress.emit(val)

    def incr_evidx(self):
        """
        incr_evidx(): description

        :returns: None
        """
        self.evidx_mutex.acquire()
        self._current_ev_idx += 1
        self.evidx_mutex.release()

    def reset_evidx(self):
        """
        reset_evidx(): description

        :returns: None
        """
        self.evidx_mutex.acquire()
        self._current_ev_idx = 0
        self.evidx_mutex.release()

    def get_evidx(self):
        """
        get_evidx(): description

        :returns: None
        """
        self.evidx_mutex.acquire()
        val = self._current_ev_idx
        self.evidx_mutex.release()
        return val

    def incr_consecutive_scan_idx(self):
        """
        incr_evidx(): description

        :returns: None
        """
        self._consecutive_scan_mutex.acquire()
        self._consecutive_scan_cntr += 1
        self._consecutive_scan_mutex.release()
        # print 'incr_consecutive_scan_idx=%d' % self.get_consecutive_scan_idx()

    def reset_consecutive_scan_idx(self):
        """
        reset_evidx(): description

        :returns: None
        """
        self._consecutive_scan_mutex.acquire()
        self._consecutive_scan_cntr = 0
        self._consecutive_scan_mutex.release()

    def get_consecutive_scan_idx(self):
        """
        get_evidx(): description

        :returns: None
        """
        self._consecutive_scan_mutex.acquire()
        val = self._consecutive_scan_cntr
        self._consecutive_scan_mutex.release()
        return val

    def set_spatial_id(self, sp_id):
        """
        set_spatial_id(): description

        :param sp_id: sp_id description
        :type sp_id: sp_id type

        :returns: None
        """
        self.sproi_idx_mutex.acquire()
        self._current_sp_id = sp_id
        # print 'set_spatial_id: %d' % sp_id
        self.sproi_idx_mutex.release()

    def reset_spatial_id(self):
        """
        reset_spatial_id(): description

        :returns: None
        """
        self.sproi_idx_mutex.acquire()
        self._current_sp_id = 0
        self.sproi_idx_mutex.release()

    def get_spatial_id(self):
        """
        get_spatial_id(): description

        :returns: None
        """
        self.sproi_idx_mutex.acquire()
        val = self._current_sp_id
        self.sproi_idx_mutex.release()
        return val

    def get_imgidx(self):
        """
        get_imgidx(): description

        :returns: None
        """
        self.imgidx_mutex.acquire()
        val = int(self._current_img_idx)
        self.imgidx_mutex.release()
        return val

    def incr_imgidx(self):
        """
        incr_imgidx(): description

        :returns: None
        """
        self.imgidx_mutex.acquire()
        self._current_img_idx += 1
        self.imgidx_mutex.release()

    def reset_imgidx(self):
        """
        reset_imgidx(): description

        :returns: None
        """
        self.imgidx_mutex.acquire()
        self._current_img_idx = 0
        self.imgidx_mutex.release()

    def set_active_user(self, user_obj):
        """
        set_active_user(): description

        :param user_obj: user_obj description
        :type user_obj: user_obj type

        :returns: None
        """
        self.active_user = user_obj
        if self.hdr is not None:
            self.hdr.set_data_dir(self.active_user.get_data_dir())

    def set_datafile_names_dict(self, dct):
        self.data_name_dct = dct.copy()

    def get_datafile_names_dict(self):
        return self.data_name_dct

    def set_data_dir(self, path):
        """
        set_data_dir(): description

        :param path: path description
        :type path: path type

        :returns: None
        """
        self.data_dir = path

    def get_data_dir(self):
        """
        get_data_dir(): description

        :returns: None
        """
        return self.data_dir

    def connect_signals(self):
        """
        connect_signals(): connects all of the signals that bridge the world from EPICS to this python instance. The main
        connections made here are to the different leveled sscan records to catch the progress of a level as wel as the completion of a level

        :returns: None
        """
        pass


    def disconnect_signals(self):
        """
        disconnect_signals(): disconnects all of the signals were connected in the connect_signals() routine above. This occurs at the end of each completed scan, the signals are torn down
        and will be reconnected when the next scan is configured before it starts.

        :returns: None
        """
        # connect sscan signals
        pass


    def connect_device_signals(self):
        """
        connect_device_signals(): connects the device signals typically for the Counter and Gate

        :returns: None
        """
        """ called from base class """
        # _logger.debug('BaseScan: connected counter')
        # self.counter.changed.connect(self.on_counter_changed)
        reconnect_signal(self.counter, self.counter.changed, self.on_counter_changed)

    def disconnect_device_signals(self):
        """
        disconnect_device_signals(): disconnects the device signals typically for the Counter and Gate

        :returns: None
        """
        """ called from base class """
        # self.counter.changed.disconnect(self.on_counter_changed)
        disconnect_signal(self.counter, self.counter.changed)
        # _logger.debug('BaseScan: disconnected counter')

    # def on_counter_changed(self, row, data, val=None):
    def on_counter_changed(self, _dct):
        """
        on_counter_changed(): I'm not sure this is used

        :returns: None
        This is a slot that is connected to the counters changed signal
        """
        print("on_counter_changed")

    def on_scan_done(self):
        """
        on_scan_done(): fires when the top level scan is done, calls on_child_scan_done() if one has been
        configured by parent scan plugin

        :returns: None
        """

        stop_all = False
        if self.child_scan_on_done != None:
            stop_all = self.child_scan_on_done()

        if stop_all or (stop_all == None):
            # _logger.debug('BaseScan: [%s] on_scan_done' % self.scan_prefix)
            if self.signals_connected:
                # _logger.debug('BaseScan: on_scan_done: emitted all_done sig')
                self.all_done.emit()
            else:
                _logger.debug("BaseScan: on_scan_done: ELSE: sigs were not connected")
            # if(done):
            # self.disconnect_signals()
        if hasattr(self, "_det_subscriptions"):
            if self._det_subscriptions is not None:
                self.clear_detector_subscriptions()

    def clear_detector_subscriptions(self):
        """
        remove all subscriptions from detectors
        """
        try:
            for d in self._det_subscriptions:
                d.new_plot_data.disconnect()
            self._det_subscriptions = []
        except:
            pass

    def fine_scan_go_to_scan_start(self):
        """
        a very specific got_to_start function for scans that involve the fine motor in the scan
        """
        mtr_dct = self.determine_samplexy_posner_pvs()
        mtr_x = self.main_obj.device(mtr_dct["sx_name"])
        mtr_y = self.main_obj.device(mtr_dct["sy_name"])
        mtr_fx = self.main_obj.device(mtr_dct["fx_name"])
        mtr_fy = self.main_obj.device(mtr_dct["fy_name"])
        suspnd_controller_fbk = self.main_obj.device("DNM_E712_SSPND_CTRLR_FBK")
        if suspnd_controller_fbk:
            # make sure E712 controller feedback of scan is enabled as teh autozero function relies on the moving feedback
            suspnd_controller_fbk.put(0)

        #if not mtr_x.is_fine_already_near_center(x_roi[CENTER]) or not mtr_y.is_fine_already_near_center(y_roi[CENTER]):
        if not mtr_x.is_fine_in_range(self.x_roi) or not mtr_y.is_fine_in_range(self.y_roi):
            #inform the user that we first need to move coarse motor and recenter piezo
            self.mtr_recenter_msg.show()

            #before starting scan check the interferometers, note BOTH piezo's must be off first
            mtr_x.set_piezo_power_off()
            mtr_y.set_piezo_power_off()

            mtr_x.do_autozero()
            mtr_y.do_autozero()

            mtr_x.do_interferometer_check()
            mtr_y.do_interferometer_check()

            mtr_x.move_to_scan_start(start=self.x_roi[START], stop=self.x_roi[STOP], npts=self.x_roi[NPOINTS], dwell=self.dwell, start_in_center=True, line_scan=self.is_lxl)
            mtr_y.move_to_scan_start(start=self.y_roi[START], stop=self.y_roi[STOP], npts=self.y_roi[NPOINTS], dwell=self.dwell, start_in_center=True, line_scan=False)
            #mtr_y.move_to_position(y_roi[START], False)
            self.mtr_recenter_msg.hide()
        else:
            mtr_x.set_piezo_power_on()
            mtr_y.set_piezo_power_on()
            mtr_fx.move(self.x_roi[START])
            mtr_fy.move(self.y_roi[START])

        mtr_x.set_piezo_power_on()
        mtr_y.set_piezo_power_on()


    def fine_scan_on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        """
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        if e712_wdg:
            e712_wdg.on_wavegen_scan_done()

        mtr_dct = self.determine_samplexy_posner_pvs()
        x_roi = self.sp_db["X"]
        y_roi = self.sp_db["Y"]
        mtr_x = self.main_obj.device(mtr_dct["sx_name"])
        mtr_y = self.main_obj.device(mtr_dct["sy_name"])
        # move piezo's to center of scan to setup for if there is a repeat of the scan scan
        mtr_x.move_fine_to_coarse_fbk_pos()
        mtr_y.move_fine_to_coarse_fbk_pos()
        mtr_x.set_piezo_power_on()
        mtr_y.set_piezo_power_on()

        if hasattr(self, "_det_subscriptions"):
            if self._det_subscriptions is not None:
                self.clear_detector_subscriptions()

    def start(self):
        """
        start(): description

        :returns: None
        """
        # self.top_level_scan.put('EXSC', 1)
        _logger.debug("User has pressed START")
        self.save_request_made_already = False
        if self.setupScan is not None:
            self.setupScan.start()
        else:
            self.top_level_scan.start()

        self._abort = False

    def stop(self):
        """
        stop(): description

        :returns: None
        """
        try:
            _logger.debug("User has pressed STOP")

            if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
                #self.gate.stop()
                #self.counter.stop()
                if self.main_obj.device("DNM_SHUTTER").is_auto():
                    self.main_obj.device("DNM_SHUTTER").close()

        except:
            pass
            # we dont need to raise an exception for the stop failing
            # raise BaseScanException(f'Stop Failed')

    def pause(self):
        """
        pause(): description

        :returns: None
        """
        _logger.debug("User has pressed PAUSE")
        self.top_level_scan.pause(1)

    def resume(self):
        """
        resume(): description

        :returns: None
        """
        _logger.debug("User has pressed RESUME")
        self.top_level_scan.pause(0)

    def get_all_data(self):
        """
        get_all_data(): description

        :returns: None
        """
        # print '[%s] get_all() called' % self.positioner
        all_data = {}
        try:
            # for scan in self.scans_list:
            for scan in self.scanlist:

                # all_data.append(scan.get_all_data())
                all_data[scan.section_name] = scan.get_all_data()
            return all_data
        except KeyError as e:
            print("no key in scan data for [%s]" % str(e))
            return {}

    def get_all_positioner_points(self):
        """
        get_all_positioner_points(): description

        :returns: None
        """
        # print '[%s] get_all() called' % self.positioner
        all_data = []
        try:
            # for scan in self.scans_list:
            for scan in self.scanlist:
                all_data.append(scan.get_all_positioner_points())
            return all_data
        except KeyError as e:
            print("no key in scan data for [%s]" % str(e))
            return []

    def get_scan_prefix(self):
        """
        get_scan_prefix(): description

        :returns: None
        """
        return self.scan_prefix

    def confirm_stopped(self, mtrlist):
        """
        confirm_stopped(): Takes a list of Motor objects and waits until they are all stopped then returns

        :param mtrlist: mtrlist description
        :type mtrlist: mtrlist type

        :returns: None
        """
        # time.sleep(0.5)
        # _logger.debug('confirm_stopped: starting')
        time.sleep(0.1)
        QtWidgets.QApplication.processEvents()
        num_mtrs = len(mtrlist)
        t = 0
        done = False
        while (not done) and (t < 9000):
            time.sleep(0.002)
            if (t % 10) == 0:
                QtWidgets.QApplication.processEvents()
            t += 1
            md = 0
            for m in mtrlist:
                if m.get("motor_done_move"):
                    md += 1

            if md == num_mtrs:
                done = True
            else:
                # break
                pass
        # _logger.debug('confirm_stopped: leaving')
        if t >= 9000:
            _logger.error("confirm_stopped: timed out")

    def config_devices(self):
        """
        config_devices(): description

        :returns: None
        """
        """
        this is an API method to configure the gate, shutter and counter devices for this scan
        if they exist, to be implemented by inheriting scan
        """
        pass

    def set_spatial_id_list(self, sp_lst, reverse=True):
        """
        set_spatial_id_list(): description

        :param sp_lst: sp_lst description
        :type sp_lst: sp_lst type

        :returns: None
        """
        # reverse list so that the firs tis last and then when
        # I call pop() they will be removed in order
        sp_lst.sort(reverse=reverse)
        self.sp_id_list = sp_lst
        self._master_sp_id_list = copy.copy(sp_lst)

    def get_next_spatial_id(self):
        """
        get_next_spatial_id(): description

        :returns: None
        """
        # reverse list so that the firs tis last and then when
        # I call pop() they will be removed in order
        if self.sp_id_list:
            id = self.sp_id_list.pop()
            # print 'get_next_spatial_id', self.sp_id_list
            return id
        else:
            return None

    def get_spatial_id_list(self):
        """
        get_spatial_id_list(): description

        :returns: None
        """
        return self.sp_id_list

    def set_config_devices_func(self, dev_cfg_func):
        """
        set_config_devices_func(): description

        :param dev_cfg_func: dev_cfg_func description
        :type dev_cfg_func: dev_cfg_func type

        :returns: None
        """
        self.config_devices = dev_cfg_func

    def modify_config(self):
        """
        modify_config(): description

        :returns: None
        """
        """ an API function tp be implemented if necessary but inheriting class"""
        pass

    def config_record_pvs(self):
        """
        config_record_pvs(): description

        :returns: None
        """
        """ an API function tp be implemented if necessary but inheriting class"""
        pass

    def get_data_dim(self, obj, attr):
        """
        get_data_dim(): take an object and an attribute, if the attrinute is actually something
        other than a string just return the attribute, this allows the data_shape to be defined as a attribute string or as an integer

        :param obj: obj is an object that you want to return an sttribute from
        :type obj: obj is usualy self but it can be any object

        :param attr: attr is the name of the attribute you want to get the value of
        :type attr: attr can be a string or a value
        """
        if type(attr) == str:
            val = getattr(self, attr)
        else:
            val = attr
        return val

    def get_data_dir(self):
        data_dir = self.active_user.get_data_dir()
        return data_dir

    def set_current_scan_data_dir(self, dir):
        """
        useful for finding out the stack or ptycho data dir
        """
        self.cur_scan_data_dir = dir

    def get_current_scan_data_dir(self):
        """
        useful for finding out the stack or ptycho data dir
        """
        return self.cur_scan_data_dir

    def get_cur_filename(self):
        ado = dct_get(self.sp_db, SPDB_ACTIVE_DATA_OBJECT)
        fname = dct_get(ado, ADO_CFG_DATA_FILE_NAME)
        return fname

    def config_hdr_datarecorder(self, stack=True, use_this_data_dir=None):
        """
        config_hdr_datarecorder(): Used to configure the self.data numpy array required for scan.

        :param stack=True: stack=True description
        :type stack=True: stack=True type

        :param use_this_data_dir=None: use_this_data_dir=None description
        :type use_this_data_dir=None: use_this_data_dir=None type

        :returns: None
        """
        """
        this is an API method to initlialize the data recorder module for this scan
        """

        _multi_sp_scans = [
            scan_types.SAMPLE_IMAGE,
            scan_types.SAMPLE_IMAGE_STACK,
            scan_types.TOMOGRAPHY,
        ]
        _spectra_scans = [
            scan_types.SAMPLE_POINT_SPECTRUM,
            scan_types.SAMPLE_LINE_SPECTRUM,
        ]

        self.spid_data = {}
        self.determine_data_shape()

        # get the required data shape
        d1 = int(self.get_data_dim(self, self.data_shape[0]))
        d2 = int(self.get_data_dim(self, self.data_shape[1]))
        d3 = int(self.get_data_dim(self, self.data_shape[2]))

        self.init_spid_data(d1, d2, d3)

        find_next_data_dir = True
        if self.active_user is not None:
            if use_this_data_dir is None:
                data_dir = self.active_user.get_data_dir()
            else:
                data_dir = use_this_data_dir
                find_next_data_dir = False

            ado = dct_get(self.sp_db, SPDB_ACTIVE_DATA_OBJECT)
            fname = dct_get(ado, ADO_CFG_DATA_FILE_NAME).replace(".hdf5", "")

            if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
                data_format = "stxm"
            elif self.main_obj.get_beamline_id() is BEAMLINE_IDS.BIOXAS:
                data_format = "bioxas"
            else:
                # default to stxm
                data_format = "stxm"

            self.data_obj = ActiveDataObj()
            self.data_obj.reset_data_dct()

            return data_dir

    def update_roi_member_vars(self, sp_db):
        # self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        # self.sp_db = self.sp_rois[sp_id]
        self.sp_db = sp_db
        self.set_spatial_id(sp_db[SPDB_ID_VAL])

        self.x_roi = dct_get(self.sp_db, SPDB_X)
        self.y_roi = dct_get(self.sp_db, SPDB_Y)
        self.z_roi = dct_get(self.sp_db, SPDB_Z)
        self.e_rois = dct_get(self.sp_db, SPDB_EV_ROIS)

        self.gx_roi = dct_get(self.sp_db, SPDB_GX)
        self.gy_roi = dct_get(self.sp_db, SPDB_GY)
        self.gz_roi = dct_get(self.sp_db, SPDB_GZ)
        self.gt_roi = dct_get(self.sp_db, SPDB_GT)

        self.zx_roi = dct_get(self.sp_db, SPDB_ZX)
        self.zy_roi = dct_get(self.sp_db, SPDB_ZY)
        self.zz_roi = dct_get(self.sp_db, SPDB_ZZ)

        self.ox_roi = dct_get(self.sp_db, SPDB_OX)
        self.oy_roi = dct_get(self.sp_db, SPDB_OY)
        self.oz_roi = dct_get(self.sp_db, SPDB_OZ)

    def configure_x_scan_LINEAR(self, wdg_com, sp_id=0, line=False):
        """
        configure_x_scan_LINEAR(): used by PositionerSSCAN plugin and configure a very basic single dimension scan

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :param line=False: line=False description
        :type line=False: line=False type

        :returns: None
        """
        """
        This is a base configure function for a scan with an single motor/positioner
        """
        self.wdg_com = wdg_com
        self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        self.sp_db = self.sp_rois[sp_id]
        self.set_spatial_id(sp_id)
        self.scan_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_TYPE)
        self.scan_sub_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)
        self.numX = int(dct_get(self.sp_db, SPDB_XNPOINTS))
        self.numY = int(dct_get(self.sp_db, SPDB_YNPOINTS))
        self.numZ = int(dct_get(self.sp_db, SPDB_ZNPOINTS))
        self.numE = int(dct_get(self.sp_db, SPDB_EV_NPOINTS))
        self.numSPIDS = len(self.sp_rois)
        self.e_rois = dct_get(self.sp_db, SPDB_EV_ROIS)
        e_roi = self.e_rois[0]
        self.numEPU = len(dct_get(e_roi, EPU_POL_PNTS))
        if self.numEPU < 1:
            self.numEPU = 1

        # self.x_roi = dct_get(self.sp_db, SPDB_X)
        # self.y_roi = dct_get(self.sp_db,SPDB_Y)
        # self.z_roi = dct_get(self.sp_db,SPDB_Z)

        self.update_roi_member_vars(self.sp_db)

        dct_put(
            self.sp_db,
            SPDB_RECT,
            (self.x_roi[START], self.y_roi[START], self.x_roi[STOP], self.y_roi[STOP]),
        )

        self.dwell = self.e_rois[0][DWELL]

        self.reset_evidx()
        self.reset_imgidx()

        # self._config_start_stop(self.xScan, 1, self.x_roi[START], self.x_roi[STOP], self.numX)
        # self._config_scan_velo(self.xScan, self.xScan.P1.get('max_speed'))
        # self.stack_scan = False
        self.config_hdr_datarecorder(stack=self.stack)
        # THIS must be the last call
        self.finish_setup()

    def config_basic_2d(self, wdg_com, sp_id=0, z_enabled=False):
        """
        init the member vars for a 2d basic scan
        :param wdg_com:
        :param sp_id:
        :param z_enabled:
        :return:
        """
        self.wdg_com = wdg_com
        self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        self.sp_db = self.sp_rois[sp_id]
        self.set_spatial_id(sp_id)

        self.scan_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_TYPE)
        self.scan_sub_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)
        self.numX = int(dct_get(self.sp_db, SPDB_XNPOINTS))
        self.numY = int(dct_get(self.sp_db, SPDB_YNPOINTS))
        self.numZ = int(dct_get(self.sp_db, SPDB_ZNPOINTS))
        self.numE = int(dct_get(self.sp_db, SPDB_EV_NPOINTS))
        self.numSPIDS = len(self.sp_rois)
        self.e_rois = dct_get(self.sp_db, SPDB_EV_ROIS)
        e_roi = self.e_rois[0]
        self.numEPU = len(dct_get(e_roi, EPU_POL_PNTS))
        self.num_points = self.numX * self.numY

        # self.x_roi = dct_get(self.sp_db, SPDB_X)
        # self.y_roi = dct_get(self.sp_db,SPDB_Y)
        # self.z_roi = dct_get(self.sp_db,SPDB_Z)

        self.update_roi_member_vars(self.sp_db)

        self.dwell = self.e_rois[0][DWELL]

        if z_enabled:
            self.numZ = self.z_roi[NPOINTS]

        self.numY = self.y_roi[NPOINTS]

        self.config_hdr_datarecorder(self.stack)

    def configure_x_y_z_arb_linescan(
        self, wdg_com, sp_id=0, line=True, restore=True, z_enabled=False
    ):
        """
        configure_x_y_z_arb_linescan(): Used by OSAFocusSSCAN

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :param line=True: line=True description
        :type line=True: line=True type

        :param restore=True: restore=True description
        :type restore=True: restore=True type

        :param z_enabled=False: z_enabled=False description
        :type z_enabled=False: z_enabled=False type

        :returns: None
        """
        """
        THis function is similar to the base configure_x_y_z function with the exception of
        how the x and y setpoint tables are assigned, because this function is for creating a scan of 
        an arbitrary line we use a single sscan to move both x and y motors, each has the same number of points
        so in effect they are moved as a single motor. To achieve this we only need to:
            - set the x and y motors to P1 and P2 respectively in the scan1 (xScan) sscan record
            - write the x motors table to scan1.P1PA 
            - write the y motors table to scan1.P2PA
            - remove the yscan from the chain by setting the z scan to call the EXSC of the scan1 instead of scan2 (yScan)
             - set scan1.P1SM and .P2SM to 1 (TABLE)

         This function also expects the parent class to contain the following scan attributes:
            xyScan    where P1==xPositioner P2==yPositioner
            zScan    None if z_enabled == False    
        """
        self.wdg_com = wdg_com
        self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        self.sp_db = self.sp_rois[sp_id]
        self.set_spatial_id(sp_id)
        self.scan_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_TYPE)
        self.scan_sub_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)
        self.numX = int(dct_get(self.sp_db, SPDB_XNPOINTS))
        self.numY = int(dct_get(self.sp_db, SPDB_YNPOINTS))
        self.numZ = int(dct_get(self.sp_db, SPDB_ZNPOINTS))
        # self.numZ = int(dct_get(self.sp_db, SPDB_ZZNPOINTS))
        self.numZZ = dct_get(self.sp_db, SPDB_ZZNPOINTS)
        self.numE = int(dct_get(self.sp_db, SPDB_EV_NPOINTS))
        self.numSPIDS = len(self.sp_rois)
        self.e_rois = dct_get(self.sp_db, SPDB_EV_ROIS)
        e_roi = self.e_rois[0]
        self.numEPU = len(dct_get(e_roi, EPU_POL_PNTS))
        self.update_roi_member_vars(self.sp_db)
        dct_put(
            self.sp_db,
            SPDB_RECT,
            (self.x_roi[START], self.y_roi[START], self.x_roi[STOP], self.y_roi[STOP]),
        )
        self.dwell = self.e_rois[0][DWELL]
        self.reset_evidx()
        self.reset_imgidx()
        self.busy_saving = False

        if z_enabled:
            # make the assumption that z is for zoneplate z ZZ
            dct_put(
                self.sp_db,
                SPDB_RECT,
                (
                    self.x_roi[START],
                    self.zz_roi[START],
                    self.x_roi[STOP],
                    self.zz_roi[STOP],
                ),
            )

        self.config_hdr_datarecorder(self.stack)
        self.stack_scan = False

        # THIS must be the last call
        self.finish_setup()

        sp_id = self.get_next_spatial_id()
        self.new_spatial_start.emit(sp_id)

    def optimize_scan(self):
        """
        optimize_scan(): To be implemented by the inheriting class
        This function is meant to retrieve from the ini file the section for its scan and set any PDLY's
        and any other settings required to optimize the scan for speed.
        Typically this is used by the scans that move the fine piezo stages as their status response can greatly
        mprove the performance if it is optimized.

        appConfig.get_value('SAMPLE_IMAGE', 'whatever')


        """
        pass

    def check_if_save_all_data(self, datafile_name):
        """
        a function to throw up a modal dialog box asking if the user wants to save the data or not. This check can be
        turned off in the app.ini file under DEFAULT/autoSaveData, but also the scan plugins themselves can request that
        the data be autosaved (ex: stacks) that is why there is essentially 2 checks, with the app.ini overriding the other
        of set to 'true'

        :param datafile_name:
        :return:
        """

        # check if user has asked for this to be automatic
        appConfig.update()
        do_autosave = appConfig.get_bool_value("MAIN", "autoSaveData")
        if do_autosave:
            return True

        # if the app.ini file says NOT to autosave we still have to check to see if a san config requested that
        # data be autosaved (ex: stack) or not,
        if not self.save_request_made_already:
            self.save_request_made_already = True
            print("check_if_save_all_data: called")
            if not self.save_all_data:
                app = QtWidgets.QApplication.instance()
                windows = app.allWindows()
                # init default QRect
                rect = QtCore.QRect(50, 50, 100, 100)
                # now find our applications window
                for w in windows:
                    w_obj_nm = str(w.objectName())
                    if w_obj_nm.find("pySTXM") > -1:
                        rect = w.geometry()
                        print(rect)

                px = (rect.width() + rect.x()) / 3
                py = (rect.height() + rect.y()) / 3

                ss = get_style()
                # ss = 'QWidget{	color: rgb(255, 255, 255); background-color: rgb(77, 77, 77);}'
                # ss = 'QWidget{	background-color: rgb(140, 140, 140); font-weight: bold;} QPushButton{	background-color: rgb(208, 208, 208); font-weight: bold;}'
                # ss = 'QWidget{	background-color: rgb(140, 140, 140); font-weight: bold;} '
                # ss += 'QPushButton{ background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgb(90, 90, 90), stop:1 rgb(60, 60, 60)); border: 1 px solid black; color:rgb(220, 220, 220); padding: 1 ex 2 ex;'
                # the following displays a modal dialog box that prompts user if they want to save the at or not
                resp = warn(
                    "Save Data",
                    "Do you want to save this data? [%s]" % datafile_name,
                    accept_str="Yes",
                    reject_str="No",
                    ss=ss,
                    posn=(px, py),
                )
                if resp == "No":
                    return False
            return True

    def display_message(self, msg):
        """
        a function to throw up a modal dialog box letting the user know an issue has occured


        :param datafile_name:
        :return:
        """

        app = QtWidgets.QApplication.instance()
        windows = app.allWindows()
        # init default QRect
        rect = QtCore.QRect(50, 50, 100, 100)
        # now find our applications window
        for w in windows:
            w_obj_nm = str(w.objectName())
            if w_obj_nm.find("pySTXM") > -1:
                rect = w.geometry()
                print(rect)

        px = (rect.width() + rect.x()) / 3
        py = (rect.height() + rect.y()) / 3

        ss = get_style()
        resp = notify("Warning", msg, accept_str="Ok", ss=ss, posn=(px, py))

    def flip_data_upsdown(self, data):
        _data = np.flipud(data).copy()
        return _data
        # return(data)

    def on_x_y_scan_data_level_done(self):
        """
        on_x_y_scan_data_level_done(): Used by :
            DetectorSSCAN
            OsaScanClass
            OSAFocusSSCAN
            FocusScanClass

        This fires at the end of a scan and saves a jpg as well as calls save_hdr() to save the data file

        this is an API slot that gets fired when the data level scan_done signal

        The final data dict should have the main keys of:
            all_data['SSCANS']      - all fields of each sscan record, this will be a list of sscans
            all_data['SCAN_CFG']    - all params from the GUI for this scan, center, range etc, also any flags such as XMCD=True that relate to how to execute this scan
            all_data['DATA']        - counter data collected during scan, for images this will be a 2d array, for point scans this will be a 1d array

        The goal of all_data dict is to write the dict out to disk in <data dir>/master.json. Once it has been recorded to disk the data recorder
        module can open it as a json object and export it based on the scan type so that it can pick and choose what to pull out and write to the header file.
        DNM_SHUTTER
        """
        try:
            print("on_x_y_scan_data_level_done: called")
            self.disconnect_signals()
            if self.main_obj.device("DNM_SHUTTER").is_auto():
                self.main_obj.device("DNM_SHUTTER").close()

            # _logger.debug('xyzSSCAN: on_data_level_done:')
            self.data_obj.set_scan_end_time()
            upd_list = []
            for s in self.scanlist:
                upd_list.append(s.get_name())

            counter = "DNM_DEFAULT_COUNTER"
            _sp_id = list(self.spid_data[counter].keys())[0]

            self.busy_saving = True
            _ev_idx = self.get_evidx()
            _img_idx = self.get_imgidx()
            # _spatial_roi_idx = self.get_spatial_id()

            sp_db = self.sp_rois[_sp_id]
            self.data_dct = self.data_obj.get_data_dct()

            ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
            data_file_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
            datadir = dct_get(ado_obj, ADO_CFG_DATA_DIR)
            datafile_name = dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME)
            thumb_name = dct_get(ado_obj, ADO_CFG_DATA_THUMB_NAME)

            if not self.check_if_save_all_data(datafile_name):
                return

            self.saving_data.emit("Saving Data")

            for scan in self.scanlist:
                # print scan.get_det_data()

                sname = scan.get_name()
                #    #ask each scan to get its data and store it in scan.scan_data
                if scan.section_name == SPDB_XY:
                    # this is a sscan where P1 is X and P2 is Y, separate them such that they look like two separate scans
                    alldata = scan.get_all_data()
                    p1data = alldata["P1RA"]
                    npts = alldata["NPTS"]
                    cpt = alldata["CPT"]
                    if "P2RA" in list(alldata.keys()):
                        p2data = alldata["P2RA"]
                        dct_put(
                            self.data_dct,
                            "DATA.SSCANS.Y",
                            {"P1RA": p2data, "NPTS": npts, "CPT": cpt},
                        )

                    dct_put(self.data_dct, "DATA.SSCANS.XY", alldata)

                    dct_put(
                        self.data_dct,
                        "DATA.SSCANS.X",
                        {"P1RA": p1data, "NPTS": npts, "CPT": cpt},
                    )

                else:
                    dct_put(
                        self.data_dct,
                        "DATA.SSCANS." + scan.section_name,
                        scan.get_all_data(),
                    )
                    # dct_put(self.data_dct,'DATA.SSCANS.' + scan.section_name, alldata[sname])
            sample_pos = 1
            unique_id = "m%s" % (data_file_prfx)

            # need to keep a reference to this so that it can be saved in the field
            # that contains the 'scan_request' json string that is used to recreate/reload this scan
            devices = self.main_obj.get_devices()

            posner_dct = self.take_positioner_snapshot(devices["POSITIONERS"])
            det_dct = self.take_detectors_snapshot(devices["DETECTORS"])
            temp_dct = self.take_temps_snapshot(devices["TEMPERATURES"])
            press_dct = self.take_pressures_snapshot(devices["PRESSURES"])
            pvs_dct = self.take_pvs_snapshot(devices["PVS"])

            dct_put(self.data_dct, "TIME", make_timestamp_now())
            dct_put(self.data_dct, "POSITIONERS", posner_dct)
            dct_put(self.data_dct, "DETECTORS", det_dct)
            dct_put(self.data_dct, "TEMPERATURES", temp_dct)
            dct_put(self.data_dct, "PRESSURES", press_dct)
            dct_put(self.data_dct, "PVS", pvs_dct)

            dct_put(self.data_dct, ADO_CFG_DATA_STATUS, DATA_STATUS_FINISHED)
            dct_put(self.data_dct, ADO_CFG_WDG_COM, self.wdg_com)
            dct_put(self.data_dct, ADO_CFG_SCAN_TYPE, self.scan_type)
            dct_put(self.data_dct, ADO_CFG_CUR_EV_IDX, _ev_idx)
            dct_put(self.data_dct, ADO_CFG_CUR_SPATIAL_ROI_IDX, _sp_id)
            dct_put(self.data_dct, ADO_CFG_CUR_SAMPLE_POS, sample_pos)
            dct_put(self.data_dct, ADO_CFG_CUR_SEQ_NUM, 0)
            dct_put(self.data_dct, ADO_CFG_DATA_DIR, datadir)
            dct_put(self.data_dct, ADO_CFG_DATA_FILE_NAME, data_file_prfx)
            dct_put(self.data_dct, ADO_CFG_DATA_THUMB_NAME, thumb_name)
            dct_put(self.data_dct, ADO_CFG_UNIQUEID, unique_id)
            dct_put(self.data_dct, ADO_CFG_X, self.x_roi)
            dct_put(self.data_dct, ADO_CFG_Y, self.y_roi)
            dct_put(self.data_dct, ADO_CFG_Z, self.z_roi)
            dct_put(self.data_dct, ADO_CFG_ZZ, self.zz_roi)
            dct_put(self.data_dct, ADO_CFG_EV_ROIS, self.e_rois)
            # dct_put(self.data_dct, ADO_CFG_IMG_IDX_MAP, self.img_idx_map)
            # dct_put(self.data_dct, ADO_DATA_POINTS, self.data[_ev_idx] )

            if self.save_jpgs:
                self.hdr.save_image_thumbnail(self.data_dct)

            self.busy_saving = False
            self._data = self.spid_data[counter][_sp_id][0]
            dct_put(self.data_dct, ADO_DATA_POINTS, self._data)

            dct_put(self.data_dct, ADO_STACK_DATA_POINTS, self.spid_data)
            dct_put(
                self.data_dct, ADO_STACK_DATA_UPDATE_DEV_POINTS, self.update_dev_data
            )

            # is this a duplication?????
            dct_put(self.data_dct, ADO_SP_ROIS, self.sp_rois)

            _wdgcom = {}
            dct_put(_wdgcom, WDGCOM_CMND, self.wdg_com[CMND])
            _sprois = {}
            _sprois[_sp_id] = self.wdg_com["SPATIAL_ROIS"][_sp_id]
            dct_put(_wdgcom, SPDB_SPATIAL_ROIS, _sprois)
            dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)

            # update stop time in tmp file
            self.main_obj.zmq_stoptime_to_tmp_file()

            # now send the Active Data Object (ADO) to the tmp file under the section 'ADO'
            dct = {}
            dct["cmd"] = CMD_SAVE_DICT_TO_TMPFILE
            wdct = {"WDG_COM": dict_to_json(_wdgcom), "SCAN_TYPE": self.scan_type}
            data_dct_str = dict_to_json(self.data_dct)
            dct["dct"] = {
                "SP_ROIS": dict_to_json(self.sp_rois),
                "CFG": wdct,
                "numEpu": self.numEPU,
                "numSpids": self.numSPIDS,
                "numE": self.numE,
                "DATA_DCT": data_dct_str,
            }

            self.main_obj.zmq_save_dict_to_tmp_file(dct)

            # returns an idx0 with snapshots inside
            _dct = self.get_snapshot_dict(
                0,
                posner_dct=posner_dct,
                temps_dct=temp_dct,
                press_dct=press_dct,
                det_dct=det_dct,
                pv_dct=pvs_dct,
            )
            self.main_obj.zmq_save_dict_to_tmp_file(_dct)
            dct = {}
            dct["cmd"] = CMD_EXPORT_TMP_TO_NXSTXMFILE
            self.main_obj.zmq_save_dict_to_tmp_file(dct)
            ######## AUG 29

        except KeyError:
            self.disconnect_signals()
            _logger.error("on_x_y_scan_data_level_done: _sp_id=%d" % _sp_id)

    def get_snapshot_dict(
        self,
        cntr,
        posner_dct=None,
        temps_dct=None,
        press_dct=None,
        det_dct=None,
        pv_dct=None,
    ):
        """
        This function can be called from a parent and supply a dct that will be written to the temp hdf file
        with the same dict structure
        :param dct:
        :return:
        dct_put(self.data_dct,'POSITIONERS', self.take_positioner_snapshot(devices['POSITIONERS']))
            dct_put(self.data_dct,'DETECTORS', self.take_detectors_snapshot(devices['DETECTORS']))
            dct_put(self.data_dct, 'TEMPERATURES', self.take_temps_snapshot(devices['TEMPERATURES']))
            dct_put(self.data_dct, 'PRESSURES', self.take_pressures_snapshot(devices['PRESSURES']))
            dct_put(self.data_dct,'PVS', self.take_pvs_snapshot(devices['PVS']))


        """
        devices = self.main_obj.get_devices()
        dct = {}
        dct["cmd"] = CMD_SAVE_DICT_TO_TMPFILE
        idx_dct = {}
        idx_str = "idx%d" % cntr
        idx_dct[idx_str] = {}

        # posnerdevlst = self._gen_register_posner_upd_list()
        if posner_dct is None:
            idx_dct[idx_str]["POSITIONERS"] = self.take_positioner_snapshot()
        else:
            idx_dct[idx_str]["POSITIONERS"] = posner_dct

        if temps_dct is None:
            idx_dct[idx_str]["TEMPERATURES"] = self.take_temps_snapshot()
        else:
            idx_dct[idx_str]["TEMPERATURES"] = temps_dct

        if press_dct is None:
            idx_dct[idx_str]["PRESSURES"] = self.take_pressures_snapshot()
        else:
            idx_dct[idx_str]["PRESSURES"] = press_dct

        if det_dct is None:
            idx_dct[idx_str]["DETECTORS"] = self.take_detectors_snapshot()
        else:
            idx_dct[idx_str]["DETECTORS"] = det_dct

        if pv_dct is None:
            idx_dct[idx_str]["PVS"] = self.take_pvs_snapshot()
        else:
            idx_dct[idx_str]["PVS"] = pv_dct

        _dct = self.get_img_idx_map(cntr)
        pol_idx = _dct["pol_idx"]
        e_idx = _dct["e_idx"]
        sp_id = _dct["sp_id"]

        # copy current data from all configured detectors
        for counter_name in list(self.spid_data.keys()):
            data = self.spid_data[counter_name][sp_id][pol_idx][e_idx]
            idx_dct[idx_str]["DETECTORS"][counter_name] = {}
            idx_dct[idx_str]["DETECTORS"][counter_name][RBV] = data

        dct["dct"] = idx_dct
        return dct

    def get_img_idx_map(self, idx):
        """
        a standard function for retrieving the image_index_map

        :param idx:
        :return:
        """
        if idx >= len(self.img_idx_map):
            idx = len(self.img_idx_map) - 1
        idx_str = "%d" % idx
        if idx_str in list(self.img_idx_map.keys()):
            return self.img_idx_map[idx_str]
        else:
            _logger.error("idx [%s] does not exist in the img_idx_map" % idx_str)
            return None

    # def on_save_sample_image(self, _data=None):
    #     """
    #     on_save_sample_image(): Saves a jpg thumbnail image of current scan and also increments the consecutive_scan_idx counter
    #     It is used by:
    #         FocusScanClass
    #         SampleImageWithEnergySSCAN
    #
    #     This is an API slot that gets fired when the data level scan_done signal and it saves a thumbnail image of current data
    #
    #     The final data dict should have the main keys of:
    #         all_data['SSCANS']      - all fields of each sscan record, this will be a list of sscans
    #         all_data['SCAN_CFG']    - all params from the GUI for this scan, center, range etc, also any flags such as XMCD=True that relate to how to execute this scan
    #         all_data['DATA']        - counter data collected during scan, for images this will be a 2d array, for point scans this will be a 1d array
    #
    #     The goal of all_data dict is to write the dict out to disk in <data dir>/master.json. Once it has been recorded to disk the data recorder
    #     module can open it as a json object and export it based on the scan type so that it can pick and choose what to pull out and write to the header file.
    #
    #     :returns: None
    #
    #     """
    #     try:
    #         if(self.file_saved):
    #             #_logger.debug('on_save_sample_image: returning file already saved')
    #             return
    #         #_logger.debug('on_save_sample_image')
    #         #if(not self.busy_saving):
    #
    #         #try:
    #         if(self.scan_type == scan_types.SAMPLE_POINT_SPECTRUM):
    #             return
    #         self.data_obj.set_scan_end_time()
    #         self.busy_saving = True
    #         #first copy evidx and increment main evidx so that the on_counter_changed handler will not overwrite
    #         _ev_idx = self.get_evidx()
    #         if(self.stack):
    #             _img_idx = self.get_imgidx()
    #         else:
    #             _img_idx = 0
    #
    #         _spatial_roi_idx = self.get_spatial_id()
    #         #self.data_dct = self.data_obj.get_data_dct()
    #         sp_db = self.sp_rois[_spatial_roi_idx]
    #
    #         self.data_dct = self.data_obj.get_data_dct()
    #
    #         ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
    #         data_file_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
    # #                thumb_file_ext = dct_get(ado_obj, ADO_CFG_THUMB_EXT)
    #         datadir = dct_get(ado_obj, ADO_CFG_DATA_DIR)
    #         datafile_name = dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME)
    #         hdf_name = dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME)
    #         thumb_name = dct_get(ado_obj, ADO_CFG_DATA_THUMB_NAME)
    #         #_img_idx = dct_get(ado_obj, ADO_CFG_DATA_IMG_IDX)
    #         stack_dir = dct_get(ado_obj, ADO_CFG_STACK_DIR)
    #
    #         if(not self.save_jpgs):
    #             return
    #
    #         if(self.stack):
    #             datadir = stack_dir
    #             thumb_name = data_file_prfx + '_%03d' % self.get_consecutive_scan_idx()
    #
    #         dct = {}
    #         dct_put(dct, ADO_CFG_DATA_DIR, datadir)
    #         dct_put(dct, ADO_CFG_DATA_THUMB_NAME, thumb_name)
    #         dct_put(dct, ADO_CFG_DATA_FILE_NAME, hdf_name)
    #
    #         if(_data is None):
    #             _dct = self.get_img_idx_map(_img_idx)
    #             sp_id = _dct['sp_id']
    #             sp_idx = _dct['sp_idx']
    #             pol_idx = _dct['pol_idx']
    #
    #             # for now just use the first counter
    #             #counter = self.counter_dct.keys()[0]
    #             counter = DNM_DEFAULT_COUNTER
    #             #self._data = self.spid_data[counter][sp_idx][pol_idx]
    #             self._data = np.copy(self.spid_data[counter][sp_id][pol_idx])
    #             #dct_put(dct, ADO_DATA_POINTS, copy.copy(self.spid_data[counter][sp_id][pol_idx]) )
    #             dct_put(dct, ADO_DATA_POINTS, self._data)
    #         else:
    #             #print 'on_save_sample_image: _data.shape = ', _data.shape
    #             dct_put(dct, ADO_DATA_POINTS, _data)
    #
    #         if(self.is_point_spec):
    #             #self.hdr.save_image_nxdf(self.data_dct)
    #             self.hdr.save_image_nxdf(dct)
    #
    #         elif(self.is_lxl or self.is_pxp):
    #             #save a jpg thumbnail
    #             self.hdr.save_image_thumbnail(dct)
    #             self.incr_imgidx()
    #             self.new_spatial_start.emit(_spatial_roi_idx)
    #
    #         self.busy_saving = False
    #
    #        #     #except:
    #        #     #    self.busy_saving = False
    #        # else:
    #        #     _logger.error('on_save_sample_image: DROP THRU : wanted to save but it was busy')
    #
    #     except KeyError:
    #         _logger.error('on_save_sample_image: How did this happen? _spatial_roi_idx=%d'%_spatial_roi_idx)

    #     def save_hdr(self, update=False, do_check=True):
    #         """
    #         save_hdr(): This is the main datafile savinf function, it is called at the end of every completed scan
    #
    #         :param update: update is a flag set to True when save_hdr() is first called during the configure() portion of the scan
    #                     it allows the data file to be created before data collection has started and then updated as the data is collected,
    #                     when the scan has finished this flag is False which indicates that all final processing of the save should take place
    #                     (ie: prompt the user if they want to save this data etc)
    #
    #         :returns: None
    #
    #         If this function takes a long time due to grabbing a snapshot of all
    #         the positioners it should maybe be moved to its own thread and just have the
    #         GUI wait until it is finished, that seems reasonable for the user to wait a couple seconds
    #         for the file to save as long as the GUI is not hung
    #
    #
    #         This function is used by:
    #             - sample Image PXP
    #             - sample Image LXL
    #             - sample Image point Spectra
    #         None stack scans should yield the following per scan:
    #             one header file
    #             one image thumbnail (jpg)
    #
    #         Stack scans should yield:
    #             one header file
    #             numE * numEpu thumbnail images per stack
    #
    #         The image thumbnails are saved in the on_sampleImage_data_done signal handler
    #
    #         The header file is saved on the scan_done signal of the top level scan
    #         """
    #         #print '\tin save_hdr() update, docheck:', (update, do_check)
    #         if(update):
    #             _logger.debug('Skipping save_hdr() update = True')
    #             return
    #         else:
    #             if (self.main_obj.device('DNM_SHUTTER').is_auto()):
    #                 self.main_obj.device('DNM_SHUTTER').close()
    #
    #         upside_dwn_scans = [scan_types.SAMPLE_LINE_SPECTRUM, scan_types.SAMPLE_IMAGE, scan_types.SAMPLE_IMAGE_STACK]
    #
    #         #_logger.info('save_hdr: starting')
    #
    #         if(self.is_point_spec):
    #             self.save_point_spec_hdr(update)
    #             return
    #
    #         if(self.is_line_spec):
    #             if(self.use_hdw_accel):
    #                 self.gate.stop()
    #                 self.counter.stop()
    #
    #         self.data_obj.set_scan_end_time()
    #
    #         upd_list = []
    #         for s in self.scanlist:
    #             upd_list.append(s.get_name())
    #         #self.main_obj.update_zmq_sscan_snapshot(upd_list)
    #
    #         _ev_idx = self.get_evidx()
    #         _img_idx = self.get_imgidx() - 1
    #         _spatial_roi_idx = self.get_spatial_id()
    #         sp_db = self.sp_rois[_spatial_roi_idx]
    #         sample_pos = 1
    #
    #
    #         #data_name_dct = master_get_seq_names(datadir, prefix_char=data_file_prfx, thumb_ext=thumb_file_sffx, dat_ext='hdf5', stack_dir=self.stack)
    #         #hack
    #         if(_img_idx < 0):
    #             _img_idx = 0
    #         self.data_dct = self.data_obj.get_data_dct()
    #
    #         ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
    # #        data_file_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
    # #        thumb_file_ext = dct_get(ado_obj, ADO_CFG_THUMB_EXT)
    #         datadir = dct_get(ado_obj, ADO_CFG_DATA_DIR)
    #         datafile_name = dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME)
    #         datafile_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
    # #        thumb_name = dct_get(ado_obj, ADO_CFG_DATA_THUMB_NAME)
    #         stack_dir = dct_get(ado_obj, ADO_CFG_STACK_DIR)
    #
    #
    #         if(not update):
    #             if(do_check):
    #                 if(not self.check_if_save_all_data(datafile_name)):
    #                     return
    #
    #         self.saving_data.emit('Saving...')
    #
    #         if(self.stack):
    #             datadir = stack_dir
    #
    #         #alldata = self.main_obj.get_zmq_sscan_snapshot(upd_list)
    #         for scan in self.scanlist:
    #             sname = scan.get_name()
    #             #    #ask each scan to get its data and store it in scan.scan_data
    #             if(self.use_hdw_accel):
    #                 #there wont be any setpoints in the sscan config as the setpoints are done in the waveform generator
    #                 #so just create them
    #                 if (scan.section_name == SPDB_X):
    #                     dct_put(self.data_dct, 'DATA.SSCANS.X', {'P1RA': self.x_roi[SETPOINTS], 'NPTS': self.x_roi[NPOINTS]})
    #
    #                 if (scan.section_name == SPDB_Y):
    #                     dct_put(self.data_dct, 'DATA.SSCANS.Y', {'P1RA': self.y_roi[SETPOINTS], 'NPTS': self.y_roi[NPOINTS]})
    #
    #                 if (scan.section_name == SPDB_XY):
    #                     dct_put(self.data_dct, 'DATA.SSCANS.XY',
    #                             {'P1RA': self.x_roi[SETPOINTS], 'NPTS': self.x_roi[NPOINTS]})
    #                     dct_put(self.data_dct, 'DATA.SSCANS.X',
    #                             {'P1RA': self.x_roi[SETPOINTS], 'NPTS': self.x_roi[NPOINTS]})
    #                     dct_put(self.data_dct, 'DATA.SSCANS.Y',
    #                             {'P1RA': self.y_roi[SETPOINTS], 'NPTS': self.y_roi[NPOINTS]})
    #
    #
    #             elif(scan.section_name == SPDB_XY):
    #                 #this is a sscan where P1 is X and P2 is Y, separate them such that they look like two separate scans
    #                 #alldata = self.take_sscan_snapshot(scan.name)
    #                 alldata = scan.get_all_data()
    #
    #                 p1data = alldata['P1RA']
    #                 npts = alldata['NPTS']
    #                 cpt = alldata['CPT']
    #                 p2data = alldata['P2RA']
    #                 dct_put(self.data_dct,'DATA.SSCANS.XY', alldata)
    #
    #                 dct_put(self.data_dct,'DATA.SSCANS.X', {'P1RA':p1data, 'NPTS':npts, 'CPT':cpt})
    #                 dct_put(self.data_dct,'DATA.SSCANS.Y', {'P1RA':p2data, 'NPTS':npts, 'CPT':cpt})
    #             else:
    #                 dct_put(self.data_dct,'DATA.SSCANS.' + scan.section_name, scan.get_all_data())
    #                 #dct_put(self.data_dct,'DATA.SSCANS.' + scan.section_name, alldata[sname])
    #
    #
    #         # if(self.scan_type in upside_dwn_scans):
    #         #     #the data for these scans needs to be flipped upside down
    #         #     _data = self.flip_data_upsdown(self.data[_img_idx-1])
    #         #     self.data[_img_idx-1] = np.copy(_data)
    #         #
    #         #_logger.info('grabbing devices snapshot')
    #         devices = self.main_obj.get_devices()
    #
    #         #get the current spatial roi and put it in the dct as a dict with its sp_id as the key
    #         _wdgcom = {}
    #         dct_put(_wdgcom, WDGCOM_CMND, self.wdg_com[CMND])
    #         _sprois = {}
    #         _sprois[_spatial_roi_idx] = self.wdg_com['SPATIAL_ROIS'][_spatial_roi_idx]
    #         dct_put(_wdgcom, SPDB_SPATIAL_ROIS,  _sprois )
    #         dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
    #
    #         #SEPT 6
    #         cur_idx = self.get_consecutive_scan_idx()
    #         _dct = self.get_img_idx_map(cur_idx)
    #         sp_id = _dct['sp_id']
    #         pol_idx = _dct['pol_idx']
    #
    #         # for now just use the first counter
    #         #counter = self.counter_dct.keys()[0]
    #         counter = DNM_DEFAULT_COUNTER
    #         #self._data = self.spid_data[counter][sp_id][pol_idx]
    #         #self._data = np.copy(self.spid_data[counter][sp_id][pol_idx])
    #         # end SEPT 6
    #
    #         testing_polarity_entries=False
    #         if(testing_polarity_entries):
    #             t_dct = {}
    #
    #             # dct_put(t_dct,'POSITIONERS', self.take_positioner_snapshot(devices['POSITIONERS']))
    #             # dct_put(t_dct,'DETECTORS', self.take_detectors_snapshot(devices['DETECTORS']))
    #             # dct_put(t_dct,'TEMPERATURES', self.take_temps_snapshot(devices['TEMPERATURES']))
    #             # dct_put(t_dct, 'PRESSURES', self.take_pressures_snapshot(devices['PRESSURES']))
    #             # dct_put(t_dct,'PVS', self.take_pvs_snapshot(devices['PVS']))
    #             # #_logger.info('DONE grabbing devices snapshot')
    #             # #dct_put(t_dct, ADO_CFG_WDG_COM, self.wdg_com)
    #             # dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
    #             #
    #             # dct_put(t_dct, ADO_CFG_SCAN_TYPE, self.scan_type)
    #             # dct_put(t_dct, ADO_CFG_CUR_EV_IDX, _ev_idx)
    #             # dct_put(t_dct, ADO_CFG_CUR_SPATIAL_ROI_IDX, _spatial_roi_idx)
    #             # dct_put(t_dct, ADO_CFG_CUR_SAMPLE_POS, sample_pos)
    #             # dct_put(t_dct, ADO_CFG_CUR_SEQ_NUM, 0)
    #             # dct_put(t_dct, ADO_CFG_DATA_DIR, datadir)
    #             # dct_put(t_dct, ADO_CFG_DATA_FILE_NAME, datafile_prfx)
    #             # dct_put(t_dct, ADO_CFG_UNIQUEID, datafile_prfx)
    #             # dct_put(t_dct, ADO_CFG_X, self.x_roi)
    #             # dct_put(t_dct, ADO_CFG_Y, self.y_roi)
    #             # dct_put(t_dct, ADO_CFG_Z, self.z_roi)
    #             # dct_put(t_dct, ADO_CFG_EV_ROIS, self.e_rois)
    #             # dct_put(t_dct, ADO_DATA_POINTS, self.data )
    #             #
    #             # images_data = np.zeros((self.numEPU, self.numE, self.numY, self.numX))
    #             # image_idxs = []
    #             # for i in range(self.numEPU):
    #             #     image_idxs.append(np.arange(i, self.numImages, self.numEPU))
    #             #
    #             # #for idxs in image_idxs:
    #             # for i in range(self.numEPU):
    #             #     idxs = image_idxs[i]
    #             #     y = 0
    #             #     for j in idxs:
    #             #         images_data[i][y] = self.data[j]
    #             #         y += 1
    #             #
    #             #
    #             # new_e_rois = self.turn_e_rois_into_polarity_centric_e_rois(self.e_rois)
    #             # pol_rois = []
    #             # for e_roi in self.e_rois:
    #             #     for pol in range(self.numEPU):
    #             #         pol_rois.append(e_roi['POL_ROIS'][pol])
    #             #
    #             # for pol in range(self.numEPU):
    #             #     self.data_dct['entry_%d' % pol] = copy.deepcopy(t_dct)
    #             #     dct_put(self.data_dct['entry_%d' % pol], ADO_DATA_POINTS, copy.deepcopy(images_data[pol]) )
    #             #     dct_put(self.data_dct['entry_%d' % pol], ADO_DATA_SSCANS, copy.deepcopy(self.data_dct['DATA']['SSCANS']))
    #             #     dct_put(self.data_dct['entry_%d' % pol], ADO_CFG_EV_ROIS, [new_e_rois[pol]])
    #         else:
    #
    #             if((self.data_dct['TIME'] != None) and update):
    #                 #we already have already set these and its not the end of the scan sp skip
    #                 pass
    #             else:
    #                 dct_put(self.data_dct,'TIME', make_timestamp_now())
    #                 dct_put(self.data_dct,'POSITIONERS', self.take_positioner_snapshot(devices['POSITIONERS']))
    #                 dct_put(self.data_dct,'DETECTORS', self.take_detectors_snapshot(devices['DETECTORS']))
    #                 dct_put(self.data_dct, 'TEMPERATURES', self.take_temps_snapshot(devices['TEMPERATURES']))
    #                 dct_put(self.data_dct, 'PRESSURES', self.take_pressures_snapshot(devices['PRESSURES']))
    #                 dct_put(self.data_dct,'PVS', self.take_pvs_snapshot(devices['PVS']))
    #
    #             #_logger.info('DONE grabbing devices snapshot')
    #             #dct_put(self.data_dct, ADO_CFG_WDG_COM, self.wdg_com)
    #             dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
    #
    #             if(update):
    #                 dct_put(self.data_dct, ADO_CFG_DATA_STATUS, DATA_STATUS_NOT_FINISHED)
    #             else:
    #                 dct_put(self.data_dct, ADO_CFG_DATA_STATUS, DATA_STATUS_FINISHED)
    #
    #             dct_put(self.data_dct, ADO_CFG_SCAN_TYPE, self.scan_type)
    #             dct_put(self.data_dct, ADO_CFG_CUR_EV_IDX, _ev_idx)
    #             dct_put(self.data_dct, ADO_CFG_CUR_SPATIAL_ROI_IDX, _spatial_roi_idx)
    #             dct_put(self.data_dct, ADO_CFG_CUR_SAMPLE_POS, sample_pos)
    #             dct_put(self.data_dct, ADO_CFG_CUR_SEQ_NUM, 0)
    #             dct_put(self.data_dct, ADO_CFG_DATA_DIR, datadir)
    #             dct_put(self.data_dct, ADO_CFG_DATA_FILE_NAME, datafile_prfx)
    #             dct_put(self.data_dct, ADO_CFG_UNIQUEID, datafile_prfx)
    #             dct_put(self.data_dct, ADO_CFG_X, self.x_roi)
    #             dct_put(self.data_dct, ADO_CFG_Y, self.y_roi)
    #             dct_put(self.data_dct, ADO_CFG_Z, self.z_roi)
    #             dct_put(self.data_dct, ADO_CFG_ZZ, self.zz_roi)
    #             dct_put(self.data_dct, ADO_CFG_EV_ROIS, self.e_rois)
    #             #dct_put(self.data_dct, ADO_DATA_POINTS, self.data )
    #             #dct_put(self.data_dct, ADO_CFG_IMG_IDX_MAP, self.img_idx_map)
    #
    #             dct_put(self.data_dct, ADO_DATA_POINTS, self._data)
    #
    #             dct_put(self.data_dct, ADO_STACK_DATA_POINTS, self.spid_data)
    #             dct_put(self.data_dct, ADO_STACK_DATA_UPDATE_DEV_POINTS, self.update_dev_data)
    #
    #             dct_put(self.data_dct, ADO_SP_ROIS, self.sp_rois)
    #
    #
    #         if (update):
    #             #self.hdr.save(self.data_dct, use_tmpfile=True)
    #             pass
    #         else:
    #             pass
    #             # Sept 8
    #             # if(self.stack or (len(self.sp_rois) > 1)):
    #             #     self.hdr.save(self.data_dct, allow_tmp_rename=True)
    #             #     self.clean_up_data()
    #             # else:
    #             #     self.hdr.save(self.data_dct)
    #             # end Sept 8
    #
    #             #update stop time in tmp file
    #             #print '\tsave_hdr: calling self.main_obj.zmq_stoptime_to_tmp_file()'
    #             self.main_obj.zmq_stoptime_to_tmp_file()
    #
    #             #now send the Active Data Object (ADO) to the tmp file under the section 'ADO'
    #             dct = {}
    #             dct['cmd'] = CMD_SAVE_DICT_TO_TMPFILE
    #             wdct = {'WDG_COM':dict_to_json(_wdgcom), 'SCAN_TYPE': self.scan_type}
    #             data_dct_str = dict_to_json(self.data_dct)
    #             if(self.is_line_spec):
    #                 dct['dct'] = {'SP_ROIS': dict_to_json(self.sp_rois), 'CFG': wdct, 'numEpu': self.numEPU,
    #                               'numSpids': self.numSPIDS, 'numE': 1, \
    #                               'DATA_DCT': data_dct_str}
    #             else:
    #                 dct['dct'] = {'SP_ROIS': dict_to_json(self.sp_rois), 'CFG': wdct, 'numEpu': self.numEPU, 'numSpids':self.numSPIDS, 'numE':self.numE, \
    #                           'DATA_DCT':data_dct_str}
    #
    #             self.main_obj.zmq_save_dict_to_tmp_file(dct)
    #
    #             cur_idx = self.get_consecutive_scan_idx()
    #             _dct = self.get_snapshot_dict(cur_idx)
    #
    #             #print '\tsave_hdr: saving a snapshot -> idx(%d)' % cur_idx
    #             self.main_obj.zmq_save_dict_to_tmp_file(_dct)
    #
    #             dct = {}
    #             dct['cmd'] = CMD_EXPORT_TMP_TO_NXSTXMFILE
    #             #print '\tsave_hdr: calling for export of tmp to final hdf file'
    #             self.main_obj.zmq_save_dict_to_tmp_file(dct)
    #
    #         #self.on_save_sample_image(_data=self.img_data[_spatial_roi_idx])
    #         #self.on_save_sample_image(_data=self.img_data[sp_id])
    #         self.on_save_sample_image(_data=self._data)
    #
    #         if(not SIMULATE_IMAGE_DATA):
    #             if(self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #                 self.main_obj.device( DNM_CX_AUTO_DISABLE_POWER ).put(1) #enabled
    #                 self.main_obj.device( DNM_CY_AUTO_DISABLE_POWER ).put(1) #enabled

    def update_data(self, stack=False):

        sp_id = self.get_spatial_id()
        sp_db = self.sp_rois[sp_id]

        ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
        datadir = dct_get(ado_obj, ADO_CFG_DATA_DIR)
        datafile_name = dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME)
        datafile_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
        stack_dir = dct_get(ado_obj, ADO_CFG_STACK_DIR)

        if stack:
            fpath = stack_dir + "\\" + datafile_name
        else:
            fpath = datadir + "\\" + datafile_name

        self.hdr.update_data(
            "entry%d" % sp_id, self.data, counter="counter0", use_tmpfile=True
        )

        # update_data_with_openclose(fpath, 'entry_%d' % sp_id, self.data, counter='counter0')

    #     def save_point_spec_hdr(self, update=False):
    #         """
    #         save_point_spec_hdr(): This is the main datafile saving function, it is called at the end of every completed scan
    #
    #         :returns: None
    #
    #         I separated this out for point spectra scans because it is increasingly harder to make a one size fits all
    #         save routine and adding more and more configuration makes the problem worse.
    #
    #         This function is called on the completion of the point spectra scan, it will save in a single data file an nxstxm 'entry' for
    #         each spatial point.
    #
    #         This function is used by:
    #             - sample point Spectra
    #         None stack scans should yield the following per scan:
    #             one header file
    #             one image thumbnail (jpg)
    #
    #         Stack scans should yield:
    #             one header file
    #             numE * numEpu thumbnail images per stack
    #
    #         The image thumbnails are saved in the on_sampleImage_data_done signal handler
    #
    #         The header file is saved on the scan_done signal of the top level scan
    #         """
    #         #_logger.info('save_hdr: starting')
    #         #if(self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #         #    self.gate.stop()
    #         #DEC 13 self.counter.stop()
    #         self.data_obj.set_scan_end_time()
    #
    #         upd_list = []
    #         for s in self.scanlist:
    #             upd_list.append(s.get_name())
    #
    #         _ev_idx = self.get_evidx()
    #         _img_idx = self.get_imgidx() - 1
    #         _spatial_roi_idx = self.get_spatial_id()
    #         sp_db = self.sp_rois[_spatial_roi_idx]
    #         sample_pos = 1
    #
    #         #data_name_dct = master_get_seq_names(datadir, prefix_char=data_file_prfx, thumb_ext=thumb_file_sffx, dat_ext='hdf5', stack_dir=self.stack)
    #         #hack
    #         if(_img_idx < 0):
    #             _img_idx = 0
    #         self.data_dct = self.data_obj.get_data_dct()
    #
    #         ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
    # #        data_file_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
    # #        thumb_file_ext = dct_get(ado_obj, ADO_CFG_THUMB_EXT)
    #         datadir = dct_get(ado_obj, ADO_CFG_DATA_DIR)
    #         datafile_name = dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME)
    #         datafile_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
    # #        thumb_name = dct_get(ado_obj, ADO_CFG_DATA_THUMB_NAME)
    #         stack_dir = dct_get(ado_obj, ADO_CFG_STACK_DIR)
    #
    #         if(not update):
    #             if(not self.check_if_save_all_data(datafile_name)):
    #                 return
    #
    #         self.saving_data.emit('Saving...')
    #
    #         if(self.stack):
    #             datadir = stack_dir
    #
    #         #alldata = self.main_obj.get_zmq_sscan_snapshot(upd_list)
    #         for scan in self.scanlist:
    #             sname = scan.get_name()
    #             #    #ask each scan to get its data and store it in scan.scan_data
    #             if(scan.section_name == SPDB_XY):
    #                 #this is a sscan where P1 is X and P2 is Y, separate them such that they look like two separate scans
    #                 #alldata = self.take_sscan_snapshot(scan.name)
    #                 alldata = scan.get_all_data()
    #
    #                 p1data = alldata['P1RA']
    #                 npts = alldata['NPTS']
    #                 cpt = alldata['CPT']
    #                 p2data = alldata['P2RA']
    #                 dct_put(self.data_dct,'DATA.SSCANS.XY', alldata)
    #
    #                 dct_put(self.data_dct,'DATA.SSCANS.X', {'P1RA':p1data, 'NPTS':npts, 'CPT':cpt})
    #                 dct_put(self.data_dct,'DATA.SSCANS.Y', {'P1RA':p2data, 'NPTS':npts, 'CPT':cpt})
    #             else:
    #                 dct_put(self.data_dct,'DATA.SSCANS.' + scan.section_name, scan.get_all_data())
    #                 #dct_put(self.data_dct,'DATA.SSCANS.' + scan.section_name, alldata[sname])
    # #        unique_id = 'm%s' % (hdf_name)
    #
    #         # if(self.scan_type == scan_types.SAMPLE_LINE_SPECTRUM):
    #         #     #_data = np.flipud(self.data[_img_idx-1]).copy()
    #         #     _data = self.flip_data_upsdown(self.data[_img_idx-1])
    #         #     self.data[_img_idx-1] = _data
    #
    #         #_logger.info('grabbing devices snapshot')
    #         devices = self.main_obj.get_devices()
    #
    #         #get the current spatial roi and put it in the dct as a dict with its sp_id as the key
    #         _wdgcom = {}
    #         dct_put(_wdgcom, WDGCOM_CMND, self.wdg_com[CMND])
    #         _sprois = {}
    #         _sprois[_spatial_roi_idx] = self.wdg_com['SPATIAL_ROIS'][_spatial_roi_idx]
    #         dct_put(_wdgcom, SPDB_SPATIAL_ROIS,  _sprois )
    #         dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
    #
    #         if((self.data_dct['TIME'] != None) and update):
    #             #we already have already set these and its not the end of the scan sp skip
    #             pass
    #         else:
    #             dct_put(self.data_dct,'TIME', make_timestamp_now())
    #             dct_put(self.data_dct,'POSITIONERS', self.take_positioner_snapshot(devices['POSITIONERS']))
    #             dct_put(self.data_dct,'DETECTORS', self.take_detectors_snapshot(devices['DETECTORS']))
    #             dct_put(self.data_dct, 'TEMPERATURES', self.take_temps_snapshot(devices['TEMPERATURES']))
    #             dct_put(self.data_dct, 'PRESSURES', self.take_pressures_snapshot(devices['PRESSURES']))
    #             dct_put(self.data_dct,'PVS', self.take_pvs_snapshot(devices['PVS']))
    #         #_logger.info('DONE grabbing devices snapshot')
    #         #dct_put(self.data_dct, ADO_CFG_WDG_COM, self.wdg_com)
    #         if(update):
    #             dct_put(self.data_dct, ADO_CFG_DATA_STATUS, DATA_STATUS_NOT_FINISHED)
    #         else:
    #             dct_put(self.data_dct, ADO_CFG_DATA_STATUS, DATA_STATUS_FINISHED)
    #
    #         dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
    #
    #         dct_put(self.data_dct, ADO_CFG_SCAN_TYPE, self.scan_type)
    #         dct_put(self.data_dct, ADO_CFG_CUR_EV_IDX, _ev_idx)
    #
    #         dct_put(self.data_dct, ADO_CFG_CUR_SAMPLE_POS, sample_pos)
    #         dct_put(self.data_dct, ADO_CFG_CUR_SEQ_NUM, 0)
    #         dct_put(self.data_dct, ADO_CFG_DATA_DIR, datadir)
    #         dct_put(self.data_dct, ADO_CFG_DATA_FILE_NAME, datafile_prfx)
    #         dct_put(self.data_dct, ADO_CFG_UNIQUEID, datafile_prfx)
    #         dct_put(self.data_dct, ADO_CFG_EV_ROIS, self.e_rois)
    #         #dct_put(self.data_dct, ADO_CFG_IMG_IDX_MAP, self.img_idx_map)
    #
    #         i = 0
    #         for sp_id in list(self.sp_rois.keys()):
    #
    #             #_sprois[_spatial_roi_idx] = self.wdg_com['SPATIAL_ROIS'][_spatial_roi_idx]
    #             #dct_put(_wdgcom, SPDB_SPATIAL_ROIS,  _sprois )
    #             #dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
    #
    #             _wdgcom = {}
    #             dct_put(_wdgcom, WDGCOM_CMND, self.wdg_com[CMND])
    #             _sproi = self.wdg_com['SPATIAL_ROIS'][sp_id]
    #             #SPDB_SPATIAL_ROIS must be a dict with the sp_id as the key
    #             dct_put(_wdgcom, SPDB_SPATIAL_ROIS,  {sp_id: _sproi} )
    #             dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
    #
    #             self.update_roi_member_vars(_sproi)
    #             dct_put(self.data_dct, ADO_CFG_CUR_SPATIAL_ROI_IDX, i)
    #             dct_put(self.data_dct, ADO_CFG_X, self.x_roi)
    #             dct_put(self.data_dct, ADO_CFG_Y, self.y_roi)
    #             dct_put(self.data_dct, ADO_CFG_Z, self.z_roi)
    #             dct_put(self.data_dct, ADO_CFG_ZZ, self.zz_roi)
    #             dct_put(self.data_dct, ADO_DATA_POINTS, self.data[0][i] )
    #
    #             #commented out may 18 2018
    #             #I need to loop through all the point spatial ids creating an entry for each then at the end rename the .tmp file to the final .hdf5 file
    #             #    otherwise thumbnailviewer will try to read a partial file
    #             # if(update):
    #             #     self.hdr.save_entry(sp_id, self.data_dct, use_tmpfile=True)
    #             # else:
    #             #     self.hdr.save_entry(sp_id, self.data_dct)
    #             #write to the temp file
    #             self.hdr.save_entry(sp_id, self.data_dct, use_tmpfile=True)
    #             i += 1
    #
    #         #now rename tmp file to final filename
    #         self.main_obj.zmq_rename_tmp_to_final()
    #
    #         #_logger.info('save_hdr: done')
    #         if(not SIMULATE_IMAGE_DATA):
    #             if(self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #                 self.main_obj.device( DNM_CX_AUTO_DISABLE_POWER ).put(1) #enabled
    #                 self.main_obj.device( DNM_CY_AUTO_DISABLE_POWER ).put(1) #enabled
    #
    #

    # def modify_for_polarities_as_indiv_entries(self):
    #     '''
    #     modifys self.data_dct so that there are "entry_" keys used for creating axis2000 happy nexus files
    #     '''
    #     pass
    #
    #
    # def turn_e_rois_into_polarity_centric_e_rois(self, e_rois):
    #     '''
    #     for every polarity it makes a copy of the e_roi and replaces the POL_ROIS with a single POL_ROI
    #     so instead of
    #         e_rois[0] POL_ROIS[1, 2, 3, 4]
    #
    #         e_rois[0] POL_ROIS[1]
    #         e_rois[1] POL_ROIS[2]
    #         e_rois[3] POL_ROIS[3]
    #         e_rois[4] POL_ROIS[4]
    #
    #     '''
    #     new_e_rois = []
    #     num_pols = 0
    #     for e_roi in e_rois:
    #
    #         pol_rois = []
    #         pols = []
    #         for pol_roi in e_roi['POL_ROIS']:
    #             num_pols += 1
    #             pol_rois.append(pol_roi)
    #             pols.append((pol_roi['POL'], pol_roi['ANGLE'], pol_roi['OFF']))
    #
    #         #make num_pol copies of each e_roi
    #         idx = 0
    #         for pol in pols:
    #             new_e_roi = copy.deepcopy(e_roi)
    #             pol['POL'] = [pol_rois[idx]['POL']]
    #             pol['ANGLE'] = [pol_rois[idx]['ANGLE']]
    #             pol['OFF'] = [pol_rois[idx]['OFF']]
    #             new_e_roi['POL_ROIS'] = [pol]
    #             idx += 1
    #
    #             new_e_rois.append(new_e_roi)
    #
    #     return(new_e_rois)
    #

    def take_sscan_snapshot(self, sscan_name):
        dct = self.main_obj.take_zmq_sscan_snapshot(sscan_name)
        # print 'take_sscan_snapshot: Done'
        return dct

    def take_positioner_snapshot(self, posners_dct=None):
        if posners_dct is None:
            devices = self.main_obj.get_devices()
            posners_dct = devices["POSITIONERS"]
        dct = self.main_obj.take_positioner_snapshot(posners_dct)
        return dct

    def take_detectors_snapshot(self, detectors_dct=None):
        if detectors_dct is None:
            devices = self.main_obj.get_devices()
            detectors_dct = devices["DETECTORS"]
        dct = self.main_obj.take_detectors_snapshot(detectors_dct)
        return dct

    def take_pvs_snapshot(self, pvs_dct=None):
        if pvs_dct is None:
            devices = self.main_obj.get_devices()
            pvs_dct = devices["PVS"]
        dct = self.main_obj.take_pvs_snapshot(pvs_dct)
        return dct

    def take_temps_snapshot(self, temps_dct=None):
        # if (temps_dct is None):
        #    devices = self.main_obj.get_devices()
        #    temps_dct = devices['TEMPERATURES']
        devobj = self.main_obj.get_device_obj()
        temps_dct = devobj.get_all_temperatures()
        dct = self.main_obj.take_temps_snapshot(temps_dct)
        return dct

    def take_pressures_snapshot(self, press_dct=None):
        # if (press_dct is None):
        #    devices = self.main_obj.get_devices()
        #    press_dct = devices['PRESSURES']
        devobj = self.main_obj.get_device_obj()
        press_dct = devobj.get_all_pressures()
        dct = self.main_obj.take_pressures_snapshot(press_dct)
        return dct

    def determine_data_shape(self):
        """
        the types of scans and required shapes of the data of this scan:
        A - Single spatial sample Image
        B - Multi A
        C - Single Image Stack
        D - Multi C
        E - Point spectra (N spatial, multi ev regions)


        shapes for the above:
        A = (1, Y, X)
        B = (N, 1, Y, X)
        C = (nEv, 1, Y, X)
        D = (N, nEv, 1, Y, X)
        #E = (N, Y, X, nEv)
        E = (1, N, nEv)


        if ev region data is to be kept each in there own level for a stack then the data must be concatenated back into a single
        dimension when written out to disk.

        Also the on_counter_changed() handlers will need to keep track of the index's they use, this gets cumbersome because the
        index's likely need to be changed in signals handlers which makes it more difficult to ensure that a sequence occusr in the right order
        may need to rethiunk all this, the counter on_changed returns only with row, col and data

        NOTE: ZZ refers to Zonplate Z

        """
        if self.scan_type in data_shape_types[data_shapes.NUME_NUMY_NUMX]:
            # single spatial
            self.data_shape = ("numE", "numY", "numX")

        elif self.scan_type in data_shape_types[data_shapes.NUME_NUMZZ_NUMX]:
            # single spatial
            self.data_shape = ("numE", "numZZ", "numX")

        elif self.scan_type in data_shape_types[data_shapes.ONE_NUMSPIDS_NUME]:
            # numE should hold the total number of points from all ev_rois for this spatial region
            self.data_shape = (1, "numSPIDS", "numE")

        elif self.scan_type in data_shape_types[data_shapes.NUMIMAGES_NUMY_NUMX]:
            self.data_shape = ("numImages", "numY", "numX")

        elif self.scan_type in data_shape_types[data_shapes.NUMX_ONE_ONE]:
            # single spatial
            self.data_shape = ("numX", 1, 1)

        elif self.scan_type in data_shape_types[data_shapes.NUMIMAGES_NUMY_NUME]:
            self.data_shape = ("numImages", "numY", "numE")

        else:
            _logger.error("unsupported scan type [%d]" % self.scan_type)
            self.data_shape = (None, None, None)

    # def on_x_y_counter_changed(self, row, xxx_todo_changeme):
    #
    #     """
    #     on_x_y_counter_changed():
    #     Used by:
    #         DetectorSSCAN
    #         OsaScanClass,
    #         OsaFocusScanClass,
    #         FocusScanClass,
    #
    #     :param row: row description
    #     :type row: row type
    #
    #     :param (point: (point description
    #     :type (point: (point type
    #
    #     :param val): val) description
    #     :type val): val) type
    #
    #     :returns: None
    #     """
    #     (point, val) = xxx_todo_changeme
    #     """
    #     This is a slot that is connected to the counters changed signal
    #     """
    #     global SIMULATE_IMAGE_DATA, SIM_DATA
    #
    #     if(SIMULATE_IMAGE_DATA):
    #         val = SIM_DATA[row][point]
    #
    #     top_lvl_npts = self.top_level_scan.get('NPTS')
    #     #print 'on_x_y_counter_changed: [%d] row=%d point=%d val=%d' % (top_lvl_npts, row, point, val)
    #     if((self.scan_type ==  scan_types.OSA_FOCUS) or (self.scan_type ==  scan_types.SAMPLE_FOCUS)):
    #         #nptsy = self.numZ
    #         nptsy = self.numZZ
    #     else:
    #         nptsy = self.numY
    #
    #     _evidx = self.get_evidx()
    #     if(point >= self.numX):
    #         #this is the row switch extra point so drop it
    #         #print 'scan_counter_changed: SKIPPED [%d, %d] = %d' % (row, point, val)
    #         return
    #     if(point > -1):
    #         if(row < top_lvl_npts):
    #             # only one counter is expected to have been configured for this type of scan so ...[0]
    #             #counter = self.counter_dct.keys()[0]
    #             #print 'on_x_y_counter_changed: counter was [%s] is now %s' % (self.counter_dct.keys()[0], DNM_DEFAULT_COUNTER)
    #             #counter = DNM_DEFAULT_COUNTER
    #             counter = DNM_DEFAULT_COUNTER
    #             _sp_id = list(self.spid_data[counter].keys())[0]
    #
    #             #pol_idx=0
    #             # now assign the data
    #             self.spid_data[counter][_sp_id][0][_evidx, row, point] = int(val)
    #             #print 'on_x_y_counter_changed: sp_id=', _sp_id
    #             #print self.spid_data[counter][_sp_id][0][_evidx, row]
    #
    #             dct = self.init_counter_to_plotter_com_dct(make_counter_to_plotter_com_dct())
    #             dct[CNTR2PLOT_ROW] = int(row)
    #             dct[CNTR2PLOT_COL] = int(point)
    #             dct[CNTR2PLOT_VAL] = int(val)
    #             #self.sigs.changed.emit(row, (point, val))
    #             self.sigs.changed.emit(dct)
    #
    #             ttl = self.numX * nptsy
    #             cur_ttl = float(((float(row) + 0.5) * float(self.numX))) + point
    #             prog = (float(cur_ttl) / float(ttl)) * 100.0
    #             prog_dct = make_progress_dict(sp_id=self.get_spatial_id(), percent=prog)
    #
    #             self.low_level_progress.emit(prog_dct)
    #
    #
    #         if(row >= nptsy):
    #             self.incr_evidx()

    # def on_sample_scan_counter_changed(self, row, data, counter_name='counter0'):
    #     """
    #     on_sample_scan_counter_changed(): Used by SampleImageWithEnergySSCAN
    #
    #     :param row: row description
    #     :type row: row type
    #
    #     :param data: data description
    #     :type data: data type
    #
    #     :returns: None
    #     """
    #     """
    #     The on counter_changed slot will take data cquired by line and point scans but it must treat each differently.
    #     The point scan still arrives as a one demensiotnal array but there are only 3 elements, data[row, point, value].
    #     The point scan has been programmed to acquire num_x_points + 1 so that the counter can increment the row value, thus this
    #     slot during a point scan will receive a point+1 and in that case it should be ignored.
    #
    #     LIne scan data arrives in the form data[row, < number of x points of values >]
    #
    #     This slot has to handle
    #
    #     """
    #     global SIMULATE_IMAGE_DATA, SIM_DATA
    #     try:
    #
    #         sp_id = int(self.main_obj.device('DNM_E712_CURRENT_SP_ID').get_position())
    #         self.set_spatial_id(sp_id)
    #
    #         if(SIMULATE_IMAGE_DATA):
    #             data = SIM_DATA[row]
    #             point = self.sim_point
    #
    #         if((self.scan_type ==  scan_types.OSA_FOCUS) or (self.scan_type ==  scan_types.SAMPLE_FOCUS)):
    #             nptsy = self.numZ
    #         else:
    #             nptsy = self.numY
    #
    #         if(SIMULATE_IMAGE_DATA and (self.sim_point >= nptsy)):
    #             self.sim_point = 0
    #             point = self.sim_point
    #
    #         _evidx = self.get_evidx()
    #         #make imgidx zero based
    #
    #         _imgidx = self.base_zero(self.get_imgidx())
    #         #_dct = self.img_idx_map['%d' % _imgidx]
    #         _dct = self.get_img_idx_map(_imgidx)
    #         pol_idx = _dct['pol_idx']
    #         e_idx = _dct['e_idx']
    #
    #         if(self.is_pxp and (not self.use_hdw_accel)):
    #             #Image point by point
    #             if(SIMULATE_IMAGE_DATA):
    #                 val = data[self.sim_point]
    #             else:
    #                 point = int(data[0])
    #                 val = data[1]
    #
    #             if(MARK_DATA_FOR_TESTING):
    #                 val = val * point * _imgidx
    #
    #             if(row >= self.numY):
    #                 self.incr_imgidx()
    #                 #make sure a new image is requested
    #                 row = 0
    #
    #             #print 'SampleImageWithEnergySSCAN: on_counter_changed: _imgidx=%d row=%d point=%d, data = %d' % (_imgidx, row, point, val)
    #             #self.data[_imgidx, row, point] = val
    #             # pol_idx=0
    #             # now assign the data
    #             self.spid_data[counter_name][sp_id][pol_idx][e_idx, int(row), point] = int(val)
    #
    #
    #
    #         else:
    #             #print 'SampleImageWithEnergySSCAN: LXL on_counter_changed: _imgidx, row and data[0:10]=', (_imgidx, row, data[0:10])
    #             #print self.data.shape
    #             point = 0
    #             val = data[0:int(self.numX)]
    #
    #             if(MARK_DATA_FOR_TESTING):
    #                 val = data[0:self.numX] * row
    #
    #             if(row < self.numY):
    #                 #_logger.info('on_sample_scan_counter_changed: saving to self.data[%d, %d]' % (_imgidx, row))
    #                 #self.data[_imgidx, row,:] = val
    #                 self.spid_data[counter_name][sp_id][pol_idx][_evidx, row, :] = val
    #                 pass
    #
    #         if(SIMULATE_IMAGE_DATA):
    #             self.sigs.changed.emit(row, (point, val))
    #             self.sim_point = self.sim_point + 1
    #         else:
    #
    #             dct = self.init_counter_to_plotter_com_dct(make_counter_to_plotter_com_dct())
    #             dct[CNTR2PLOT_ROW] = int(row)
    #             dct[CNTR2PLOT_COL] = int(point)
    #             dct[CNTR2PLOT_VAL] = val
    #             #print dct
    #             #self.sigs.changed.emit(row, data)
    #             self.sigs.changed.emit(dct)
    #
    #             prog = float(float(row + 0.75) / float(nptsy)) * 100.0
    #             #print 'progress = %.2f' % prog
    #             #self.low_level_progress.emit(prog)
    #
    #             if(self.stack):
    #                 prog_dct = make_progress_dict(sp_id=dct[CNTR2PLOT_IMG_CNTR], percent=prog)
    #             else:
    #                 prog_dct = make_progress_dict(sp_id=dct[CNTR2PLOT_SP_ID], percent=prog)
    #
    #             self.low_level_progress.emit(prog_dct)
    #
    #             # top_level_progress
    #     except :
    #         _logger.error('on_sample_scan_counter_changed: [counter_name=%s][sp_id=%d][pol_idx=%d][e_idx=%d]' % (counter_name,sp_id,pol_idx,e_idx))

    # def on_sample_scan_counter_changed(self, row, data, counter_name='counter0'):
    #     """
    #     on_sample_scan_counter_changed(): Used by SampleImageWithEnergySSCAN
    #
    #     :param row: row description
    #     :type row: row type
    #
    #     :param data: data description
    #     :type data: data type
    #
    #     :returns: None
    #     """
    #     """
    #     The on counter_changed slot will take data cquired by line and point scans but it must treat each differently.
    #     The point scan still arrives as a one demensiotnal array but there are only 3 elements, data[row, point, value].
    #     The point scan has been programmed to acquire num_x_points + 1 so that the counter can increment the row value, thus this
    #     slot during a point scan will receive a point+1 and in that case it should be ignored.
    #
    #     LIne scan data arrives in the form data[row, < number of x points of values >]
    #
    #     This slot has to handle
    #
    #     """
    #     global SIMULATE_IMAGE_DATA, SIM_DATA
    #
    #     sp_id = int(self.main_obj.device('DNM_E712_CURRENT_SP_ID').get_position())
    #     self.set_spatial_id(sp_id)
    #
    #     if (SIMULATE_IMAGE_DATA):
    #         data = SIM_DATA[row]
    #         point = self.sim_point
    #
    #     if ((self.scan_type == scan_types.OSA_FOCUS) or (self.scan_type == scan_types.SAMPLE_FOCUS)):
    #         nptsy = self.numZZ
    #     else:
    #         nptsy = self.numY
    #
    #     if (SIMULATE_IMAGE_DATA and (self.sim_point >= nptsy)):
    #         self.sim_point = 0
    #         point = self.sim_point
    #
    #     _evidx = self.get_evidx()
    #     # make imgidx zero based
    #
    #     _imgidx = self.base_zero(self.get_imgidx())
    #     # _dct = self.img_idx_map['%d' % _imgidx]
    #     _dct = self.get_img_idx_map(_imgidx)
    #     pol_idx = _dct['pol_idx']
    #     e_idx = _dct['e_idx']
    #
    #     if (self.is_pxp and (not self.use_hdw_accel)):
    #         # Image point by point
    #         if (SIMULATE_IMAGE_DATA):
    #             val = data[self.sim_point]
    #         else:
    #             point = int(data[0])
    #             val = data[1]
    #
    #         if (MARK_DATA_FOR_TESTING):
    #             val = val * point * _imgidx
    #
    #         if (row >= self.numY):
    #             self.incr_imgidx()
    #             # make sure a new image is requested
    #             row = 0
    #
    #         # print 'SampleImageWithEnergySSCAN: on_counter_changed: _imgidx=%d row=%d point=%d, data = %d' % (_imgidx, row, point, val)
    #         # self.data[_imgidx, row, point] = val
    #         # pol_idx=0
    #         # now assign the data
    #         self.spid_data[counter_name][sp_id][pol_idx][e_idx, int(row), point] = int(val)
    #
    #
    #
    #     else:
    #         # print 'SampleImageWithEnergySSCAN: LXL on_counter_changed: _imgidx, row and data[0:10]=', (_imgidx, row, data[0:10])
    #         # print self.data.shape
    #         point = 0
    #         val = data[0:int(self.numX)]
    #
    #         if (MARK_DATA_FOR_TESTING):
    #             val = data[0:self.numX] * row
    #
    #         if (row < self.numY):
    #             # _logger.info('on_sample_scan_counter_changed: saving to self.data[%d, %d]' % (_imgidx, row))
    #             # self.data[_imgidx, row,:] = val
    #             self.spid_data[counter_name][sp_id][pol_idx][_evidx, row, :] = val
    #             pass
    #
    #     if (SIMULATE_IMAGE_DATA):
    #         self.sigs.changed.emit(row, (point, val))
    #         self.sim_point = self.sim_point + 1
    #     else:
    #
    #         dct = self.init_counter_to_plotter_com_dct(make_counter_to_plotter_com_dct())
    #         dct[CNTR2PLOT_ROW] = int(row)
    #         dct[CNTR2PLOT_COL] = int(point)
    #         dct[CNTR2PLOT_VAL] = val
    #         # print dct
    #         # self.sigs.changed.emit(row, data)
    #         self.sigs.changed.emit(dct)
    #
    #         prog = float(float(row + 0.75) / float(nptsy)) * 100.0
    #         # print 'progress = %.2f' % prog
    #         # self.low_level_progress.emit(prog)
    #
    #         if (self.stack):
    #             prog_dct = make_progress_dict(sp_id=dct[CNTR2PLOT_IMG_CNTR], percent=prog)
    #         else:
    #             prog_dct = make_progress_dict(sp_id=dct[CNTR2PLOT_SP_ID], percent=prog)
    #
    #         self.low_level_progress.emit(prog_dct)
    #
    #         # top_level_progress

    def init_counter_to_plotter_com_dct(self, dct):
        dct[CNTR2PLOT_TYPE_ID] = self.scan_type
        dct[CNTR2PLOT_IMG_CNTR] = self.get_imgidx()
        dct[CNTR2PLOT_EV_CNTR] = self.get_evidx()
        dct[CNTR2PLOT_SP_ID] = self.get_spatial_id()
        dct[CNTR2PLOT_IS_POINT] = self.is_pxp
        dct[CNTR2PLOT_IS_LINE] = self.is_lxl
        # print 'init_counter_to_plotter_com_dct: ' , dct
        return dct

    def base_zero(self, val):
        if val <= 0:
            return 0
        else:
            return val - 1

    def init_tmp_file(self):
        """
        The base init_tmp_file will write the start time to the tmp file as well as write the img_idx_map if one exists
        :return:
        """
        self.main_obj.zmq_starttime_to_tmp_file()

        if self.img_idx_map is not None:
            self.main_obj.zmq_save_img_idx_map(self.img_idx_map)

    def clean_up_data(self):
        self.data = None
        self.spid_data = {}

    def finish_setup(self):
        """
        finish_setup(): This should be called by every BaseScan based scan class at the end of the configure() function

        this is an API function that is called at the end of an inheriting scans initialization,
        calling this function ensures that all BaseScan descendants  contain the required configuration functions
        """

        self.config_osa_tracking()

        # we need these time stamps in order for the inital file to be saved
        self.data_obj.set_scan_start_time()

        # if(TEST_SAVE_INITIAL_FILE):
        #     # testing roughing in a datafile before collection
        #     self.save_hdr(update=True)

        # # the spectra scan does not need a tmp file as it create entries for each spatial point when scan is done
        # if(self.scan_type != scan_types.SAMPLE_POINT_SPECTRUM):
        #     self.init_tmp_file()

        self.config_devices()

        self.modify_config()

        self.config_record_pvs()

        self.optimize_scan()

        self.connect_signals()

        # self.dump_scan_levels()

        if self.main_obj.device("DNM_SHUTTER").is_auto():
            self.main_obj.device("DNM_SHUTTER").open()

    # def chk_for_more_evregions(self):
    #     """
    #     chk_for_more_evregions(): description
    #
    #     :returns: None
    #     """
    #     """
    #     this slot handles the end of scan, when the default on_scan_done() is called in the
    #     base scan class it will check for an installed child on_scan_done slot (this one)
    #     once this has been called it returns True or False
    #         return True if there are no more ev regions and you want the default on_scan_done(0) to finish and clean everything up
    #
    #         return False if there are more ev Regions and you dont want everything stopped and cleaned up
    #     """
    #     multi_ev_single_image_scans = [scan_types.SAMPLE_LINE_SPECTRUM, scan_types.SAMPLE_POINT_SPECTRUM]
    #
    #     #Sept 6 if(TEST_SAVE_INITIAL_FILE):
    #     #Sept 6     self.save_hdr(update=True)
    #     _logger.info('chk_for_more_evregions: checking')
    #
    #     if(self._abort):
    #         _logger.info('chk_for_more_evregions: abort has been set, scan aborting')
    #         #make sure to save current scan
    #         if(self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #             self.gate.stop()
    #             self.counter.stop()
    #
    #         self.disconnect_signals()
    #         self.save_hdr()
    #         self.hdr.remove_tmp_file()
    #
    #         return(True)
    #
    #     #increment the index into ev regions
    #     self.incr_evidx()
    #
    #     if(self.get_evidx() < len(self.e_rois)):
    #         _logger.info('chk_for_more_evregions: yes there is, loading and starting')
    #         if(self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #             # if point or line spec, ONLY THE FIRST dwell value is used, to allow different dwell values
    #             # does not make sense, Jian and I talked about this
    #             # so do NOT stop the gate and counter, leave as previously configured for dwell for rest of ev regions
    #             if(not (self.is_point_spec or self.is_line_spec)):
    #                 self.gate.stop()
    #                 self.counter.stop()
    #                 self.counter.wait_till_stopped()
    #
    #         if(self.scan_type not in multi_ev_single_image_scans):
    #             #signal plotter to start a new image
    #             self.new_spatial_start.emit(self.sp_db[SPDB_ID_VAL])
    #
    #         e_roi = self.e_rois[self._current_ev_idx]
    #         #configure next ev sscan record with next ev region start/stop
    #         self._config_start_stop(self.evScan, 1, e_roi[START], e_roi[STOP], e_roi[NPOINTS])
    #         self.dwell = e_roi[DWELL]
    #
    #         if(self.use_hdw_accel):
    #             #need to check to see if dwell changed, if it did we need to re-configure the wavetables
    #             #if(prev_dwell != self.dwell):
    #             #_logger.debug('dwell changed [%.2f] so reconfiguring the hardware accel' % self.dwell)
    #             self.modify_config()
    #             # wait for gate and counter to start
    #             time.sleep(2.0)
    #
    #         #need to determine the scan velocity if there is a change in Dwell for this next ev region
    #         elif(not self.is_point_spec):
    #             #the dwell ime for the new ev region could have changed so determine the scan velo and accRange
    #             #need to determine the scan velocity if there is a change in Dwell for this next ev region
    #             if(self.is_line_spec and self.is_pxp):
    #                 scan_velo = self.get_mtr_max_velo(self.xyScan.P1)
    #                 #vmax = self.get_mtr_max_velo(self.xyScan.P1)
    #             else:
    #                 vmax = self.get_mtr_max_velo(self.xScan.P1)
    #                 (scan_velo , npts, dwell) = ensure_valid_values(self.x_roi[START],  self.x_roi[STOP],  self.dwell,  self.numX, vmax, do_points=True)
    #                 #need the range of scan to be passed to calc_accRange()
    #                 rng = self.x_roi[STOP] - self.x_roi[START]
    #                 accRange = calc_accRange('SampleX', 'Fine', rng, scan_velo , dwell, accTime=0.04)
    #                 #reassign dwell because it ay have changed on return from ensure_valid_values()
    #                 self.dwell = dwell
    #                 _logger.debug('set_sample_scan_velocity Image scan: scan_velo=%.2f um/s accRange=%.2f um' % (scan_velo, accRange))
    #
    #             self.set_x_scan_velo(scan_velo)
    #             # ok now finish configuration and start it
    #             self.on_this_dev_cfg()
    #             if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #                 self.gate.start()
    #                 self.counter.start()
    #                 # sept 11
    #                 self.counter.wait_till_running()
    #
    #
    #         elif(self.is_point_spec):
    #             if(self.counter.isRunning):
    #                 #leave it running
    #                 pass
    #             else:
    #                 #ok now finish configuration and start it
    #                 self.on_this_dev_cfg()
    #                 if(self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #                     if (not self.is_point_spec):
    #                         self.gate.start()
    #                         self.counter.start()
    #                         #sept 11
    #                         self.counter.wait_till_running()
    #
    #         self.start()
    #         #let caller know were not done
    #         return(False)
    #     else:
    #         _logger.info('chk_for_more_evregions: Nope no more')
    #         if((not self.is_point_spec) and self.chk_for_more_spatial_regions()):
    #             #were not done
    #             return(False)
    #         else:
    #             if(self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
    #                 self.gate.stop()
    #                 self.counter.stop()
    #
    #
    #             #ok scan is all done now, so save final header file
    #             if(not self.file_saved):
    #                 _logger.debug('chk_for_more_evregions: calling on_save_sample_image()')
    #                 self.on_save_sample_image()
    #             self.save_hdr()
    #
    #             #ok there are no more spatial regions to execute
    #             self.disconnect_signals()
    #             return(True)
    #

    # def chk_for_more_spatial_regions(self):
    #     """
    #     chk_for_more_spatial_regions(): this slot handles the end of scan, when the default on_scan_done() is called in the
    #         base scan class it will check for an installed child on_scan_done slot (this one)
    #         once this has been called it returns True or False
    #
    #         return True if there are more spatial Regions and you dont want everything stopped and cleaned up
    #
    #         return False if there are no more spatial regions and you want the default on_scan_done(0 to finish and clean everything up
    #
    #     :returns: True if there are more spatial Regions and you dont want everything stopped and cleaned up
    #             return False if there are no more spatial regions and you want the default on_scan_done(0 to finish and clean everything up
    #
    #     """
    #     _logger.info('chk_for_more_spatial_regions: checking')
    #
    #     if(self._abort):
    #         _logger.info('chk_for_more_spatial_regions: scan aborting')
    #         self.save_hdr()
    #         self.hdr.remove_tmp_file()
    #         return(True)
    #
    #     #get the next spatial ID in the list of spatial regions we are to scan
    #     sp_id = self.get_next_spatial_id()
    #     if(sp_id is not None):
    #         #save the current one and then go again
    #         self.save_hdr()
    #
    #         _logger.info('chk_for_more_spatial_regions: found sp_id=%d, loading and starting' % sp_id)
    #
    #         #because we will be starting a new scan that will have new self.data created we need to reinit the index to the data
    #         #because imgidx is what is used as the first dimension of the data
    #         _logger.info('chk_for_more_spatial_regions: resetting the data image index')
    #         self.reset_imgidx()
    #
    #         if(self.is_lxl):
    #             self.configure(self.wdg_com, sp_id, ev_idx=0, line=True, block_disconnect_emit=True)
    #         else:
    #             if(self.is_point_spec):
    #                 self.configure(self.wdg_com, sp_id, ev_idx=0, line=False, block_disconnect_emit=True)
    #             else:
    #                 self.configure(self.wdg_com, sp_id, ev_idx=0, line=False, block_disconnect_emit=True)
    #         self.start()
    #         return(True)
    #     else:
    #         _logger.info('chk_for_more_spatial_regions: nope all done')
    #         return(False)
    #

    def set_sample_posner_mode(self, smplx, finex, mode):
        """
        set_sample_posner_mode(): description

        :param smplx: smplx description
        :type smplx: smplx type

        :param finex: finex description
        :type finex: finex type

        :param mode: mode description
        :type mode: mode type

        :returns: None
        """
        for i in range(2):
            smplx.put("Mode", mode)
            # finex.put('Mode', mode)

    def determine_scan_res(self):

        if self.x_roi[SCAN_RES] == COARSE:
            self.is_fine_scan = False

        else:
            # FINE
            self.is_fine_scan = True

    def determine_samplexy_posner_pvs(self, force_fine_scan=False):
        """
        determine_samplexy_posner_pvs(): description

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :returns: None
        """
        """ this is a bit convoluted but I dont have a better solution yet.
        The issue is that if it is a fine scan then I need to ensure that the scan starts with the coarse motor
        at the scan center and the fine stage is at the center of its physical range which ensures that
        it can scan its full range, so the decision is made here based on if the scan is a coarse one or not
        
        return 
        #need to find out which low level motor to use
        #depends on range of scan
        sx_pv_name = self.main_obj.device( self.x_roi[POSITIONER] ).get_name()
        sy_pv_name = self.main_obj.device( self.y_roi[POSITIONER] ).get_name()
        
        finex_pv_name = self.main_obj.device( DNM_SAMPLE_FINE_X ).get_name()
        finey_pv_name = self.main_obj.device( DNM_SAMPLE_FINE_Y).get_name()
        coarsex_pv_name = self.main_obj.device( DNM_COARSE_X ).get_name()
        coarsey_pv_name = self.main_obj.device( DNM_COARSE_Y).get_name()
        
        """
        sample_positioning_mode = self.main_obj.get_sample_positioning_mode()
        fine_sample_positioning_mode = self.main_obj.get_fine_sample_positioning_mode()

        if sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            cx_name = "DNM_GONI_X"
            cy_name = "DNM_GONI_Y"

        # elif sample_positioning_mode == sample_positioning_modes.COARSE:
        #     cx_name = "DNM_SAMPLE_X"
        #     cy_name = "DNM_SAMPLE_Y"

        elif(sample_positioning_mode == sample_positioning_modes.COARSE):
            cx_name = "DNM_COARSE_X"
            cy_name = "DNM_COARSE_Y"

        if fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE:
            fx_name = "DNM_ZONEPLATE_X"
            fy_name = "DNM_ZONEPLATE_Y"

        else:
            fx_name = "DNM_SAMPLE_FINE_X"
            fy_name = "DNM_SAMPLE_FINE_Y"

        if self.x_roi[SCAN_RES] == COARSE:
            # leave as is
            if force_fine_scan:
                self.is_fine_scan = True
            else:
                self.is_fine_scan = False
            # starting position will need move the AbstractMotor to the START
            xpv = self.main_obj.device(cx_name).get_name()
            xstart = self.x_roi[START]

        else:
            # FINE
            self.is_fine_scan = True
            # this is just a hack for now, figure out some way to provide an alternate name if condition not met
            xpv = self.main_obj.device(fx_name).get_name()
            # starting position will need to move the AbstractMotor to the CENTER
            xstart = self.x_roi[CENTER]

        # if(ypos.find('Sample') > -1):
        if self.y_roi[SCAN_RES] == COARSE:
            # leave as is
            ypv = self.main_obj.device(cy_name).get_name()
            ystart = self.y_roi[START]
        else:
            # FINE
            # this is just a hack for now, figure out some way to provide an alternate name if condition not met
            ypv = self.main_obj.device(fy_name).get_name()
            ystart = self.y_roi[CENTER]

        finex_pv_name = self.main_obj.device(fx_name).get_name()
        finey_pv_name = self.main_obj.device(fy_name).get_name()
        coarsex_pv_name = self.main_obj.device(cx_name).get_name()
        coarsey_pv_name = self.main_obj.device(cy_name).get_name()

        if sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            sx_pv_name = finex_pv_name
            sy_pv_name = finey_pv_name
            sx_name = fx_name
            sy_name = fy_name
        else:
            sx_pv_name = self.main_obj.device(self.x_roi[POSITIONER]).get_name()
            sy_pv_name = self.main_obj.device(self.y_roi[POSITIONER]).get_name()
            sx_name = self.x_roi[POSITIONER]
            sy_name = self.y_roi[POSITIONER]

        # build a dict that represents the positioners involved in scan based on mode and range
        dct = {}
        dct["xstart"] = xstart
        dct["ystart"] = ystart
        dct["xpv"] = xpv
        dct["ypv"] = ypv
        dct["sx_name"] = sx_name
        dct["sy_name"] = sy_name
        dct["cx_name"] = cx_name
        dct["cy_name"] = cy_name
        dct["fx_name"] = fx_name
        dct["fy_name"] = fy_name
        dct["fine_pv_nm"] = {}
        dct["coarse_pv_nm"] = {}
        dct["sample_pv_nm"] = {}
        dct["fine_pv_nm"]["X"] = finex_pv_name
        dct["fine_pv_nm"]["Y"] = finey_pv_name
        dct["coarse_pv_nm"]["X"] = coarsex_pv_name
        dct["coarse_pv_nm"]["Y"] = coarsey_pv_name
        dct["sample_pv_nm"]["X"] = sx_pv_name
        dct["sample_pv_nm"]["Y"] = sy_pv_name

        # return((xpv,xstart),(ypv,ystart))
        return dct

    # Make sure that the accRange is correct
    # xpv, self.x_roi[START], self.x_roi[STOP], self.numX, accRange=accRange, line=line
    def config_samplex_start_stop(
        self, pos_pv, start, stop, npts, accRange=0.0, deccRange=1.0, line=True
    ):
        """
        config_samplex_start_stop(): description

        :param pos_pv: pos_pv description
        :type pos_pv: pos_pv type

        :param center: center description
        :type center: center type

        :param rng: rng description
        :type rng: rng type

        :param npts: npts description
        :type npts: npts type

        :param accRange=0.0: accRange=0.0 description
        :type accRange=0.0: accRange=0.0 type

        :param line=True: line=True description
        :type line=True: line=True type

        :returns: None
        """
        if line:
            lstart = start - accRange
            lstop = stop + deccRange
            # start
            # self._config_start_stop(xscan, x_posnum, lstart, lstop, 2)
            self.sample_mtrx.scan_start.put(lstart)
            self.sample_mtrx.scan_stop.put(lstop)
            self.sample_mtrx.marker_start.put(start)
            self.sample_mtrx.marker_stop.put(stop)
            self.sample_mtrx.set_marker.put(1000000)
        else:
            self.sample_mtrx.scan_start.put(1000000)
            self.sample_mtrx.scan_stop.put(1000000)
            self.sample_mtrx.marker_start.put(1000000)
            self.sample_mtrx.marker_stop.put(1000000)
            self.sample_mtrx.set_marker.put(1000000)

    def toggle_psuedomotor_start_stop(self, mtr):
        """
        Sometimes the softmotors will get stuck in a MOVING state, so before
        a scan toggle the
        """
        mtr.put("stop_go", 0)  # stop
        time.sleep(0.1)
        mtr.put("stop_go", 3)  # go

    # def set_scan_resolution(self):
    #     '''
    #         sample_positioning_modes = Enum('Coarse', 'Goniometer')
    #         sample_fine_positioning_modes = Enum('SampleFine', 'Zoneplate')
    #     :return:
    #     '''
    #
    #     if(self.sample_positioning_mode == sample_positioning_modes.GONIOMETER):
    #         MAX_SCAN_RANGE_FINEX = self.main_obj.get_preset_as_float('max_fine_x')
    #         MAX_SCAN_RANGE_FINEY = self.main_obj.get_preset_as_float('max_fine_y')
    #     else:
    #         MAX_SCAN_RANGE_FINEX = self.main_obj.get_preset_as_float('max_fine_x')
    #         MAX_SCAN_RANGE_FINEY = self.main_obj.get_preset_as_float('max_fine_y')
    #
    #     if(self.sample_fine_positioning_mode == sample_positioning_modes.COARSE):
    #         #force the scan to be a COARSE scan
    #         self.x_roi[SCAN_RES] = COARSE
    #         self.y_roi[SCAN_RES] = COARSE
    #
    #     else:
    #         if(self.x_roi[RANGE] > MAX_SCAN_RANGE_FINEX):
    #             self.x_roi[SCAN_RES] = COARSE
    #         else:
    #             self.x_roi[SCAN_RES] = 'FINE'
    #
    #         if(self.y_roi[RANGE] > MAX_SCAN_RANGE_FINEY):
    #             self.y_roi[SCAN_RES] = COARSE
    #         else:
    #             self.y_roi[SCAN_RES] = 'FINE'

    def set_scan_resolution(self):
        """
            sample_positioning_modes = Enum('Coarse', 'Goniometer')
            sample_fine_positioning_modes = Enum('SampleFine', 'Zoneplate')
        :return:
        """

        MAX_SCAN_RANGE_FINEX = self.main_obj.get_preset_as_float("max_fine_x")
        MAX_SCAN_RANGE_FINEY = self.main_obj.get_preset_as_float("max_fine_y")

        if self.x_roi[RANGE] > MAX_SCAN_RANGE_FINEX:
            self.x_roi[SCAN_RES] = COARSE
        else:
            self.x_roi[SCAN_RES] = FINE

        if self.y_roi[RANGE] > MAX_SCAN_RANGE_FINEY:
            self.y_roi[SCAN_RES] = COARSE
        else:
            self.y_roi[SCAN_RES] = FINE

        if self.x_roi[SCAN_RES] is FINE:
            self.is_fine_scan = True
        else:
            self.is_fine_scan = False

    def ensure_left_to_right(self, roi_def):
        if roi_def[START] > roi_def[STOP]:
            t = roi_def[STOP]
            roi_def[STOP] = roi_def[START]
            roi_def[START] = t

    def configure_sample_motors_for_scan(self):
        """
        This function is dependant on 2 devices that must exist in the device configuration
            self.main_obj.device( DNM_CX_AUTO_DISABLE_POWER ).put(1)
            self.main_obj.device( DNM_CY_AUTO_DISABLE_POWER ).put(1)
        they control the Coarse X and Y power, which will turn off the Coarse motor power at the end of a move
        making it more stable for fine scans as well as it will generate less heat which is the main idea here
        :return:
        """
        # set the resolution fields of teh X and Y regions of interest
        self.set_scan_resolution()

        cx_pwr = self.main_obj.device("DNM_CX_AUTO_DISABLE_POWER", do_warn=False)
        cy_pwr = self.main_obj.device("DNM_CY_AUTO_DISABLE_POWER", do_warn=False)
        if cx_pwr and cy_pwr:

            # disable the coarse motors Auto power off mode
            if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
                # enable auto power off
                cx_pwr.put(1)
                cy_pwr.put(1)
            else:

                if self.x_roi[SCAN_RES] == "FINE":
                    # enable auto power off
                    cx_pwr.put(1)
                else:
                    # disable auto power off
                    cx_pwr.put(0)

                if self.y_roi[SCAN_RES] == "FINE":
                    # enable auto power off
                    cy_pwr.put(1)
                else:
                    # disable auto power off
                    cy_pwr.put(0)

    ##############################################################
    # methods for manipulating the OSA XYZ tracking for Zoneplate Scanning only
    def enable_osa_x_tracking(self, do):
        if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
            val = 0
            if do:
                val = 1
            self.main_obj.device("OX_tracking_enabled").put(val)

    def enable_osa_y_tracking(self, do):
        if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
            val = 0
            if do:
                val = 1
            self.main_obj.device("DNM_OSAY_TRACKING").put(val)

    def goto_osa_xy_lock_positions(self):
        if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
            self.main_obj.device("DNM_OSAXY_GOTO_LOCKPOSITION").put(1)

    def goto_osa_z_lock_positions(self):
        if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
            self.main_obj.device("DNM_OSAZ_GOTO_LOCKPOSITION").put(1)

    def set_osa_xy_lock_positions(self):
        if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
            self.main_obj.device("DNM_SET_XY_LOCKPOSITION").put(1)

    def set_osa_z_lock_positions(self):
        if self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM:
            self.main_obj.device("DNM_SET_Z_LOCKPOSITION").put(1)

    def config_osa_tracking(self):
        """
        This function handles the decision making for OSA tracking, it looks at
        what the current scan is and current modes, it is meant to be a common function
        that can be called regardless of the endstation that the user is using, and will
        only attempt to push values to the osa tracking PV's if the user is configured for
        zoneplate scanning (GONIOMETER sample positioning mode), if sample scanning (conventional ambient stxm) then just skip
        over and return


        self.main_obj.set_sample_positioning_mode(sample_positioning_modes.GONIOMETER)
        self.main_obj.set_fine_sample_positioning_mode(sample_fine_positioning_modes.ZONEPLATE)

        """
        # first find out if tracking is enabled or not and eecute accordingly
        if not self.main_obj.get_preset_as_bool("OSA_TRACKING_ENABLED"):
            return

        self.set_osa_xy_lock_positions()
        return
        if self.main_obj.get_beamline_id() is not BEAMLINE_IDS.STXM:
            return

        do_types = [
            scan_types.SAMPLE_IMAGE,
            scan_types.SAMPLE_LINE_SPECTRUM,
            scan_types.SAMPLE_POINT_SPECTRUM,
            scan_types.SAMPLE_FOCUS,
            scan_types.SAMPLE_IMAGE_STACK,
        ]

        if self.scan_type not in do_types:
            self.enable_osa_x_tracking(False)
            self.enable_osa_y_tracking(False)
            return
        else:
            self.set_osa_xy_lock_positions()

        fine_sample_positioning_mode = self.main_obj.get_fine_sample_positioning_mode()
        if fine_sample_positioning_mode != sample_fine_positioning_modes.ZONEPLATE:
            # if the fine scanning is not Zoneplate scanning then turn OSA Y tracking off
            self.enable_osa_y_tracking(False)
            return

        scan_range = self.x_roi[RANGE]
        # make sure zoneplate XY are moved to 0,0
        self.main_obj.device("DNM_ZONEPLATE_X").move(0.0)
        self.main_obj.device("DNM_ZONEPLATE_Y").move(0.0)

        if self.is_lxl:
            # if lxl then turn off OSA X tracking and turn ON osa Y tracking
            self.enable_osa_x_tracking(False)
            self.enable_osa_y_tracking(True)
        else:
            if scan_range > (
                0.4 * self.main_obj.get_preset_as_float("MAX_SCAN_RANGE_X")
            ):
                # if lxl then turn off OSA X tracking and turn ON osa Y tracking
                self.enable_osa_x_tracking(True)
                self.enable_osa_y_tracking(True)
            else:
                # self.main_obj.device('DNM_OSA_X').move(0.0)
                self.enable_osa_x_tracking(False)
                self.enable_osa_y_tracking(True)
    def set_x_scan_velo(self, velo):
        """
        set_x_scan_velo(): description

        :param velo: velo description
        :type velo: velo type

        :returns: None
        """
        if (self.is_point_spec or self.is_pxp) and (self.xyScan is not None):
            self._config_scan_velo(self.xyScan, velo)
        else:
            self._config_scan_velo(self.xScan, velo)

    def move_osaxy_to_its_center(self):
        pass
        # ox = self.main_obj.device('DNM_OSA_X')
        # oy = self.main_obj.device('DNM_OSA_Y')

        # ox.put('user_setpoint', 0.0)
        # oy.put('user_setpoint', 0.0)

    def move_samplexy_to_position(self, sx, sy, posx, posy):
        modex = sx.get("Mode")
        modey = sy.get("Mode")
        sx.put("Mode", MODE_SCAN_START)
        sy.put("Mode", MODE_SCAN_START)

        sx.put("user_setpoint", posx)
        sy.put("user_setpoint", posy)

        self.confirm_stopped([sx, sy])

        sx.put("Mode", modex)
        sy.put("Mode", modey)

    def move_zpxy_to_its_center(self):
        zxmtr = self.main_obj.device("DNM_ZONEPLATE_X", do_warn=False)
        zymtr = self.main_obj.device("DNM_ZONEPLATE_Y", do_warn=False)
        if zxmtr and zymtr:
            sample_positioning_mode = self.main_obj.get_sample_positioning_mode()
            fine_sample_positioning_mode = (
                self.main_obj.get_fine_sample_positioning_mode()
            )
            if fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE:
                # only set zx zy to 0.0, 0.0 if we are NOT in COARSE_ZONEPLATE scanning mode
                # because the coordinates for zoneplate scanning in COARSE_ZONEPLATE are +-7000 instead of +-50
                if sample_positioning_mode != sample_positioning_modes.COARSE:
                    zxmtr.put("user_setpoint", 0.0)
                    zymtr.put("user_setpoint", 0.0)

    def config_for_goniometer_scan(self, dct, is_focus=False):
        """
        For a goniometer scan this will always be a fine scan of max range 100x100um (actually less)
        and the sequence to configure a scan is to position the goniometer at teh center of the scan everytime
        and set the +/- scan range to be about Zoneplate XY center (0,0)

        Need to take into account that this could be a LxL scan (uses xScan, yScan, zScan) or a PxP (uses xyScan, zScan)

        """

        # gx_mtr = self.main_obj.device( dct['cx_name'] )
        # gy_mtr = self.main_obj.device( dct['cy_name'] )
        gx_mtr = self.main_obj.get_sample_positioner("X")
        gy_mtr = self.main_obj.get_sample_positioner("Y")

        # self.set_config_devices_func(self.on_this_dev_cfg)

        # self.main_obj.device( dct['cx_name'] )
        self.sample_mtrx = self.sample_finex = self.main_obj.device("DNM_ZONEPLATE_X")
        self.sample_mtry = self.sample_finey = self.main_obj.device("DNM_ZONEPLATE_Y")

        # move Gx and Gy to center of scan, is it within a um?
        if self.zx_roi[CENTER] != 0.0:
            # zx is moving to scan center
            pass
        else:
            # Gx is moving to scan center nd zx is centered around 0, so move Gx to scan center
            gx_mtr.move(self.gx_roi[CENTER])

        # if(self.is_within_dband( gy_mtr.get_position(), self.gy_roi[CENTER], 15.0)):
        if self.zy_roi[CENTER] != 0.0:
            # zy is moving to scan center
            pass
        else:
            # Gy is moving to scan center nd zy is centered around 0, so move Gy to scan center
            gy_mtr.move(self.gy_roi[CENTER])
        if self.is_lxl:
            accRange = deccRange = 5.0
            self.config_samplex_start_stop(
                dct["fine_pv_nm"]["X"],
                self.zx_roi[START],
                self.zx_roi[STOP],
                self.numZX,
                accRange=accRange,
                deccRange=deccRange,
                line=True,
            )
        else:
            accRange = deccRange = 0
            self.config_samplex_start_stop(
                dct["fine_pv_nm"]["X"],
                self.zx_roi[START],
                self.zx_roi[STOP],
                self.numZX,
                accRange=accRange,
                deccRange=deccRange,
                line=False,
            )

    def config_for_sample_holder_scan(self, dct):
        pass

    def init_spid_data(self, d1, d2, d3):
        """
        This function needs to :
        - walk all of the sp_roi's and create the appropriate numpy data arrays in the self.stck_data dictionary
        - init the self.img_idx_map which is used in the on_counter_changed to put the data in the correct array

        d1, d2, d3 are used if the scan is a line_spec or focus scan where the dimensions are flipped because z is used
        for y and other things

        :return: self.counter_dct[counter].keys()[0]


        """
        sample_positioning_mode = self.main_obj.get_sample_positioning_mode()
        fine_sample_positioning_mode = self.main_obj.get_fine_sample_positioning_mode()
        non_zp_scans = [
            scan_types.DETECTOR_IMAGE,
            scan_types.OSA_IMAGE,
            scan_types.OSA_FOCUS,
            scan_types.SAMPLE_FOCUS,
            scan_types.GENERIC_SCAN,
            scan_types.COARSE_IMAGE,
            scan_types.COARSE_GONI,
        ]
        focus_scans = [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]

        # x_npnts_lst = []
        # y_npnts_lst = []

        # reinit the stack data
        self.spid_data = {}
        self.img_data = {}

        # this img_idx_map is used in teh on_counter_changed handler to put the data in the correct array
        self.img_idx_map = {}
        indiv_img_idx = 0
        spid_lst = list(self.sp_rois.keys())

        for i in range(self.numE):
            entry_idx = 0
            for k in range(self.numEPU):
                # for j in range(self.numSPIDS):
                for j in range(len(spid_lst)):
                    self.img_idx_map["%d" % indiv_img_idx] = {
                        "e_idx": i,
                        "pol_idx": k,
                        "sp_idx": j,
                        "sp_id": spid_lst[j],
                        "entry": "entry%d" % entry_idx,
                    }
                    # print 'self.img_idx_map[%d]' % (indiv_img_idx)
                    # print 'self.img_idx_map=' , self.img_idx_map['%d' % indiv_img_idx]
                    indiv_img_idx += 1
                    entry_idx += 1

        for counter in self.counter_dct:
            self.spid_data[counter] = {}
            for sp_id in self.sp_rois:
                sp_db = self.sp_rois[sp_id]
                e_rois = dct_get(sp_db, SPDB_EV_ROIS)
                ev_idx = self.get_evidx()
                dwell = e_rois[ev_idx][DWELL]

                # if ((self.scan_type not in non_zp_scans) and fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE):
                if (
                    self.scan_type not in non_zp_scans
                ) and sample_positioning_mode == sample_positioning_modes.GONIOMETER:
                    x_roi = dct_get(sp_db, SPDB_ZX)
                    y_roi = dct_get(sp_db, SPDB_ZY)
                    x_npnts = int(x_roi[NPOINTS])
                    y_npnts = int(y_roi[NPOINTS])

                else:
                    x_roi = dct_get(sp_db, SPDB_X)
                    y_roi = dct_get(sp_db, SPDB_Y)
                    x_npnts = int(x_roi[NPOINTS])
                    y_npnts = int(y_roi[NPOINTS])

                self.spid_data[counter][sp_id] = {}

                # make a set of arrays for final data
                for q in range(self.numEPU):
                    # self.spid_data[sp_id][q] = np.zeros((self.numE, y_npnts, x_npnts), dtype=np.float32)
                    # this needs to be fixed so that I do not need a special case here
                    if self.is_line_spec or (self.scan_type in focus_scans):
                        # self.spid_data[counter][sp_id][q] = np.zeros((d1, d2, d3), dtype=np.int32)
                        # there is a problem with the focus scan in that it delivers several lines of data before the scan has properly started which screws up the data index
                        # in the on_counter_func, so make it larger until I get time to sort it out

                        self.spid_data[counter][sp_id][q] = np.zeros(
                            (d1, d2, d3), dtype=np.int32
                        )
                        # print 'init_spid_data: creating self.spid_data[counter][sp_id][q]=(d1, d2, d3)', (sp_id, d1, d2, d3)
                    else:
                        self.spid_data[counter][sp_id][q] = np.zeros(
                            (self.numE, y_npnts, x_npnts), dtype=np.int32
                        )

                    _logger.debug(
                        "init_spid_data: self.spid_data[%s][%d][%d]"
                        % (counter, sp_id, q)
                    )

                # create new image data
                if self.is_line_spec or (self.scan_type in focus_scans):
                    self.img_data[sp_id] = np.zeros((d2, d3), dtype=np.int32)
                else:
                    self.img_data[sp_id] = np.zeros((y_npnts, x_npnts), dtype=np.int32)

                # self.img_data[sp_id] = np.zeros((d2, d3), dtype=np.int32)
                # print 'init_spid_data: creating self.img_data[sp_id]=(numY,numX)', (sp_id, y_npnts, x_npnts)

                # x_npnts_lst.append(int(x_npnts))
                # y_npnts_lst.append(int(y_npnts))
                # x_npnts_lst.append(int(d2))
                # y_npnts_lst.append(int(d3))

        # need to make sure that the gate and counter are running before leaving here
        _logger.debug("init_spid_data: data created in self.spid_data")
        # _logger.info('init_spid_data: size(self.spid_data)=%d' % sizeof(self.spid_data))

    def do_update_devs(self, main_obj=None, img_idx_map=None):
        """
        this function takes a main_obj as well as a dictionary that provides a map from incrmental image numbers to
        specific id's like energy (e_idx) polarization index (pol_idx) and spatial id (sp_idx), also the nexus entry
        string is constructed and assigned in the map as a convienience for future use
        :param main_obj:
        :param img_idx_map:
        :return:
        """
        if main_obj is None:
            return {}
        if img_idx_map is None:
            return {}

        dct = {}
        for devname in self.update_dev_lst:

            if len(self.update_dev_data) == 0:
                cur_val_lst = []
            else:
                # print self.update_dev_data[-1]
                cur_val_lst = self.update_dev_data[-1][devname]["val"]

            dev = main_obj.device(devname)
            val = dev.get_position()
            cur_val_lst.append(val)
            cur_idx = len(self.update_dev_data)
            # img_idx_map_dct = img_idx_map[cur_idx]
            _dct = self.get_img_idx_map(cur_idx)
            nxattr_path = self.update_dev_lst[devname]["nxattr_path"] % _dct["entry"]
            dct[devname] = {
                "val": cur_val_lst,
                "nxattr_path": nxattr_path,
                "idx": len(self.update_dev_data),
                "e_idx": _dct["e_idx"],
            }
        self.update_dev_data.append(dct)
        # print dct
        return dct

    def modify_config_for_hdw_accel(self, sp_rois=None):
        """
        Here I need to make the calls to send the commands that generate the waveform on the E712 for the current E_roi, by the end
        of this function everything should be ready  (as far as the E712 is concerned) to just call
            IOCE712:ExecWavgen by the sscan record

        This function needs to :
         - program the E712 with all sp_roi's for each dwell time using 1 wavtable per dwell time
        and spatial region.
         - set the number of points in the sscan record that starts the E712 wavegenerator to the number of wavtables used above
         - set the P1(x) and P2(y) PxPA tables in the sscan record that starts the E712 wavegenerator with the wavtable
         numbers that were used above


        :return:
        """
        if sp_rois is None:
            sp_rois = self.sp_rois

        sample_positioning_mode = self.main_obj.get_sample_positioning_mode()
        fine_sample_positioning_mode = self.main_obj.get_fine_sample_positioning_mode()
        # start gate and counters
        if self.is_pxp:
            mode = 0

        else:
            mode = 1

        self.main_obj.device("DNM_E712_SCAN_MODE").put(mode)

        # set the datarecorder filename
        data_dir = self.get_data_dir()
        fname = self.get_cur_filename()
        self.e712_wg.set_data_recorder_fpath(os.path.join(data_dir, fname))

        # create usetable map
        wavtable_map = self.e712_wg.create_wavgen_usetable_map(self.sp_ids)
        # clear previous wavetables
        self.e712_wg.clear_wavetables()
        self.e712_wg.clear_wavgen_use_tbl_ids()
        self.e712_wg.clear_start_modes()

        # for the current ev index
        # for each sp_db in sp_rois call sendwave() to create the wavetable on the E712 and add wavtable ID to list,
        # keep a running total of number of wavtables used starting from 1
        # set the NPTS of the btm sscan to equal the total number of wavtables used above
        # for each P1 and P2 of the bottom level sscan record write the list of each wavtable ID's to the sscan rec

        # self.img_data = {}

        IMMEDIATELY = 1

        ttl_wavtables = 0
        # the following lists are populated and then written to placeholder waveform PV's that will be used
        # by SNL code to load the next set of params for the next spatial region as they are being executed
        x_wavtbl_id_lst = []
        y_wavtbl_id_lst = []

        x_npnts_lst = []
        y_npnts_lst = []

        x_reset_posns = []
        y_reset_posns = []

        x_start_mode = []
        x_useddl_flags = []
        x_reinitddl_flags = []
        x_startatend_flags = []
        y_start_mode = []
        sp_roi_ids = []

        for sp_id in sp_rois:
            sp_db = sp_rois[sp_id]
            e_rois = dct_get(sp_db, SPDB_EV_ROIS)
            ev_idx = self.get_evidx()
            dwell = e_rois[ev_idx][DWELL]

            # if(fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE):
            if sample_positioning_mode == sample_positioning_modes.GONIOMETER:
                x_roi = dct_get(sp_db, SPDB_ZX)
                y_roi = dct_get(sp_db, SPDB_ZY)
                x_npnts = x_roi[NPOINTS]
                y_npnts = y_roi[NPOINTS]

            else:
                x_roi = dct_get(sp_db, SPDB_X)
                y_roi = dct_get(sp_db, SPDB_Y)
                x_npnts = x_roi[NPOINTS]
                y_npnts = y_roi[NPOINTS]

            # new data struct inparrallel with orig self.data, self.numImages = total numEv and num Pol
            # self.img_data[sp_id] = np.zeros((self.numImages, y_npnts, x_npnts), dtype=np.float32)

            # self.spid_data[sp_id] = {}
            # #make a set of arrays for final data
            # for q in range(self.numEPU):
            #     self.spid_data[sp_id][q] = np.zeros((self.numE, y_npnts, x_npnts), dtype=np.float32)

            x_reset_pos = x_roi[START]
            y_reset_pos = y_roi[START]
            x_axis_id = self.base_zero(self.e712_wg.get_x_axis_id())
            y_axis_id = self.base_zero(self.e712_wg.get_y_axis_id())

            sp_roi_ids.append(sp_id)
            # build a list of wavtable IDs used for this scan
            x_wavtbl_id_lst.append(wavtable_map[sp_id][x_axis_id])
            y_wavtbl_id_lst.append(wavtable_map[sp_id][y_axis_id])
            x_npnts_lst.append(int(x_npnts))
            y_npnts_lst.append(int(y_npnts))
            # x_reset_posns.append(x_reset_pos)
            # y_reset_posns.append(y_reset_pos)

            x_start_mode.append(IMMEDIATELY)
            y_start_mode.append(IMMEDIATELY)

            ddl_data = None
            if self.is_pxp:
                mode = 0
                # program waveforms into tables
                self.e712_wg.send_wave(
                    sp_id,
                    x_roi,
                    y_roi,
                    dwell,
                    mode,
                    x_auto_ddl=self.x_auto_ddl,
                    x_force_reinit=self.x_use_reinit_ddl,
                    do_trig_per_point=True
                )
                x_useddl_flags.append(0)
                x_reinitddl_flags.append(0)
                x_startatend_flags.append(0)
            else:
                mode = 1
                # program waveforms into tables, return ddl_data if one exists for the parameters for this scan
                ddl_data = self.e712_wg.send_wave(
                    sp_id,
                    x_roi,
                    y_roi,
                    dwell,
                    mode,
                    x_auto_ddl=self.x_auto_ddl,
                    x_force_reinit=self.x_use_reinit_ddl,
                    do_trig_per_point=True
                )

                # ddl_data = self.e712_wg.get_stored_ddl_table()
                # RUSS APR 21 2022 ddl_tbl_pv = self.main_obj.device('e712_ddl_tbls')
                # ddl_tbl_pv = []
                # # get all DDL table pv's
                # for i in range(10):
                #     ddl_tbl_pv.append(self.main_obj.device(f'DNM_E712_DDL_TBL_{i}'))
                ddl_tbl_pv = self.get_ddl_table_pvlist()

                if ddl_data is not None:
                    print("load this ddl table into the pvs for this spatial region")

                    ddl_tbl_pv[ttl_wavtables].put(ddl_data)
                    x_useddl_flags.append(1)
                    x_reinitddl_flags.append(0)
                    x_startatend_flags.append(0)
                else:
                    print("set the ddl pv waveform to 0s")
                    ddl_tbl_pv[ttl_wavtables].put([0, 0, 0, 0, 0, 0])
                    x_useddl_flags.append(0)
                    x_reinitddl_flags.append(1)
                    x_startatend_flags.append(0)

            # the x reset pos has now been calculated so retrieve it and store in list
            x_reset_posns.append(self.e712_wg.get_x_scan_reset_pos())
            y_reset_posns.append(y_reset_pos)
            # keep running total
            ttl_wavtables += 1

        # map_lst, self.spid_data = self.make_stack_data_map(numEv=self.numE, numPol=self.numEPU, numSp=self.numSPIDS, x_npnts_lst=x_npnts_lst, y_npnts_lst=y_npnts_lst)
        # write the x motor reset positions to the waveform pv
        self.main_obj.device("DNM_E712_XRESETPOSNS").put(x_reset_posns)
        self.main_obj.device("DNM_E712_YRESETPOSNS").put(y_reset_posns)
        # write the wavtable ids to the waveform pv
        self.main_obj.device("DNM_E712_X_WAVTBL_IDS").put(x_wavtbl_id_lst)
        self.main_obj.device("DNM_E712_Y_WAVTBL_IDS").put(y_wavtbl_id_lst)

        self.main_obj.device("DNM_E712_X_NPTS").put(x_npnts_lst)
        self.main_obj.device("DNM_E712_Y_NPTS").put(y_npnts_lst)

        self.main_obj.device("DNM_E712_X_USEDDL").put(x_useddl_flags)
        self.main_obj.device("DNM_E712_X_USEREINIT").put(x_reinitddl_flags)
        self.main_obj.device("DNM_E712_X_STRT_AT_END").put(x_startatend_flags)

        # 0 = OFF, 1=ON
        self.main_obj.device("DNM_E712_Y_STRT_AT_END").put([1])

        self.main_obj.device("DNM_E712_X_START_MODE").put(x_start_mode)
        self.main_obj.device("DNM_E712_Y_START_MODE").put(y_start_mode)

        self.main_obj.device("DNM_E712_SP_IDS").put(sp_roi_ids)

        # self.gateCntrCfgScan.put('NPTS', ttl_wavtables)

        # need to make sure that the gate and counter are running before leaving here
        _logger.info(
            "Estemated time to complete scan is: %s"
            % self.e712_wg.get_new_time_estemate()
        )

    def get_ddl_table_pvlist(self):
        ddl_tbl_pv = []
        # get all DDL table pv's
        for i in range(10):
            ddl_tbl_pv.append(self.main_obj.device(f"DNM_E712_DDL_TBL_{i}"))
        return ddl_tbl_pv

    def make_single_image_plan(
        self, dets, gate, md=None, bi_dir=False, do_baseline=True
    ):
        _logger.error("make_single_image_plan: THIS NEEDS TO BE IMPLEMENTED")

    # def make_single_pxp_image_plan(self, dets, gate, md=None, bi_dir=False, do_baseline=True):
    #     '''
    #
    #     this needs to be adapted to be a fly scan, setup SampleX to trigger at correct location, set scan velo and acc range
    #     and then call scan, gate an d counter need to be staged for lxl
    #     :param dets:
    #     :param gate:
    #     :param bi_dir:
    #     :return:
    #     '''
    #     dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
    #     self._bi_dir = bi_dir
    #     stagers = []
    #     for d in dets:
    #         stagers.append(d)
    #     det = dets[0]
    #     if (self.is_lxl):
    #         stagers.append(gate)
    #         det.set_mode(1)
    #         gate.set_mode(1)
    #         gate.set_num_points(self.x_roi[NPOINTS])
    #         gate.set_trig_src(trig_src_types.E712)
    #     else:
    #         det.set_mode(0)
    #         gate.set_mode(0)
    #         gate.set_num_points(1)
    #         gate.set_trig_src(trig_src_types.E712)
    #
    #     gate.set_dwell(self.dwell)
    #     # det.set_num_points(self.x_roi[NPOINTS])
    #     det.configure(self.x_roi[NPOINTS], self.scan_type)
    #     if (md is None):
    #         md = {'metadata': dict_to_json(
    #             self.make_standard_metadata(entry_name='entry0', scan_type=self.scan_type))}
    #         # if(not skip_baseline):
    #         #     @bpp.baseline_decorator(dev_list)
    #
    #     @conditional_decorator(bpp.baseline_decorator(dev_list), do_baseline)
    #     @bpp.stage_decorator(stagers)
    #     @bpp.run_decorator(md=md)
    #     def do_scan():
    #         mtr_x = self.main_obj.device('DNM_SAMPLE_X')
    #         mtr_y = self.main_obj.device('DNM_SAMPLE_Y')
    #
    #         shutter = self.main_obj.device('DNM_SHUTTER')
    #
    #         yield from bps.stage(gate)
    #         # the detector will be staged automatically by the grid_scan plan
    #         shutter.open()
    #         bps.open_run(md=md)
    #
    #         # go to start of line
    #         yield from bps.mv(mtr_x, self.x_roi[START], mtr_y, self.y_roi[CENTER])
    #
    #         # now do a horizontal line for every new zoneplate Z setpoint
    #         yield from scan_nd(dets, mtr_y, self.y_roi[START], self.y_roi[STOP], self.y_roi[NPOINTS, \
    #                                 mtr_x, self.x_roi[START], self.x_roi[STOP], self.x_roi[NPOINTS])
    #
    #
    #         shutter.close()
    #         # yield from bps.wait(group='e712_wavgen')
    #         yield from bps.unstage(gate)
    #         bps.close_run()
    #         print('CoarseSampleImageScanClass LxL: make_scan_plan Leaving')
    #
    #     return (yield from do_scan())

    def motor_ready_check(self, mtr_lst):
        """
        make sure that every motor in the list is ready to be scanned by calling the motors implementation of is_ready()
        :param mtr_lst:
        :return:
        """
        ret = True
        for mtr in mtr_lst:
            if not mtr.is_ready():
                _logger.error(
                    "The motor [%s] is NOT ready for scanning, check that it is calibrated and has no errors"
                    % mtr.get_name()
                )
                ret = False
        return ret

    def make_single_pxp_image_plan(
        self, dets, gate, md=None, bi_dir=False, do_baseline=True
    ):
        """
        self explanatory
        :param dets:
        :param gate:
        :param md:
        :param bi_dir:
        :param do_baseline:
        :return:
        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        self._bi_dir = bi_dir
        if md is None:
            md = {
                "metadata": dict_to_json(
                    self.make_standard_metadata(
                        entry_name="entry0", scan_type=self.scan_type, dets=dets
                    )
                )
            }

        @conditional_decorator(bpp.baseline_decorator(dev_list), do_baseline)
        # @bpp.baseline_decorator(dev_list)
        @bpp.stage_decorator(dets)
        # @bpp.run_decorator(md={'entry_name': 'entry0', 'scan_type': scan_types.DETECTOR_IMAGE})
        def do_scan():
            # Declare the end of the run.

            # x_roi = self.sp_db['X']
            # y_roi = self.sp_db['Y']
            mtr_x = self.main_obj.get_sample_fine_positioner("X")
            mtr_y = self.main_obj.get_sample_fine_positioner("Y")
            shutter = self.main_obj.device("DNM_SHUTTER")
            # md = self.make_standard_metadata(entry_num=0, scan_type=self.scan_type)
            yield from bps.stage(gate)
            shutter.open()
            yield from grid_scan(
                dets,
                mtr_y,
                self.y_roi[START],
                self.y_roi[STOP],
                self.y_roi[NPOINTS],
                mtr_x,
                self.x_roi[START],
                self.x_roi[STOP],
                self.x_roi[NPOINTS],
                bi_dir,
                md=md,
            )

            shutter.close()
            # yield from bps.wait(group='e712_wavgen')
            yield from bps.unstage(gate)
            # print('BaseScan: make_pxp_scan_plan: Leaving')

        return (yield from do_scan())

    def make_single_image_e712_plan(
        self, dets, gate, md=None, bi_dir=False, do_baseline=True
    ):
        """
        a scan plan fior taking a single 2d image with the hdw acceleration provided by the PI E712 piezo controller
        This plan is called by the fine_image_scan and tomography scans
        :param dets:
        :param gate:
        :param md:
        :param bi_dir:
        :param do_baseline:
        :return:
        """
        # print('entering: make_single_image_e712_plan, baseline is:', do_baseline)
        # zp_def = self.get_zoneplate_info_dct()
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        e712_dev = self.main_obj.device("DNM_E712_OPHYD_DEV")
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        shutter = self.main_obj.device("DNM_SHUTTER")
        ev_mtr = self.main_obj.device("DNM_ENERGY")
        pol_mtr = self.main_obj.device("DNM_EPU_POLARIZATION")
        DNM_E712_X_USE_TBL_NUM = self.main_obj.device("DNM_E712_X_USE_TBL_NUM")
        DNM_E712_Y_USE_TBL_NUM = self.main_obj.device("DNM_E712_Y_USE_TBL_NUM")
        DNM_E712_X_START_POS = self.main_obj.device("DNM_E712_X_START_POS")
        DNM_E712_Y_START_POS = self.main_obj.device("DNM_E712_Y_START_POS")
        stagers = []
        for d in dets:
            stagers.append(d)
        # det = dets[0]
        for d in dets:
            if self.is_lxl:
                stagers.append(gate)
                if hasattr(d, "set_mode"):
                    d.set_mode(1)
                if hasattr(d, "configure"):
                    d.configure(self.x_roi[NPOINTS], self.scan_type)
            else:
                if hasattr(d, "set_mode"):
                    d.set_mode(0)
                if hasattr(d, "configure"):
                    d.configure(self.x_roi[NPOINTS], self.scan_type)

        if self.is_lxl:
            stagers.append(gate)
            gate.set_mode(1)
            gate.set_num_points(self.x_roi[NPOINTS])
            gate.set_trig_src(trig_src_types.E712)
        else:
            gate.set_mode(0)
            gate.set_num_points(1)
            gate.set_trig_src(trig_src_types.E712)

        gate.set_dwell(self.dwell)
        # det.set_num_points(self.x_roi[NPOINTS])
        # det.configure(self.x_roi[NPOINTS], self.scan_type)
        if md is None:
            md = {
                "metadata": dict_to_json(
                    self.make_standard_metadata(
                        entry_name="entry0", scan_type=self.scan_type, dets=dets
                    )
                )
            }
        # if(not skip_baseline):
        #     @bpp.baseline_decorator(dev_list)

        @conditional_decorator(bpp.baseline_decorator(dev_list), do_baseline)
        @bpp.stage_decorator(stagers)
        @bpp.run_decorator(md=md)
        def do_scan():
            if do_baseline:
                print(
                    "starting: make_single_image_e712_plan:  do_scan() TAKING A BASELINE OF DEVICES"
                )
            else:
                print("starting: make_single_image_e712_plan:  do_scan()")

            # load the sp_id for wavegen
            x_tbl_id, y_tbl_id = e712_wdg.get_wg_table_ids(self.sp_id)
            print(
                "make_single_image_e712_plan: putting x_tbl_id=%d, y_tbl_id=%d"
                % (x_tbl_id, y_tbl_id)
            )
            DNM_E712_X_USE_TBL_NUM.put(x_tbl_id)
            DNM_E712_Y_USE_TBL_NUM.put(y_tbl_id)

            # make sure servo power is on
            finemtrx = self.main_obj.get_sample_fine_positioner("X").servo_power.put(1)
            finemtry = self.main_obj.get_sample_fine_positioner("Y").servo_power.put(1)
            # get the X motor reset position * /
            # samplemtrx = self.main_obj.get_sample_positioner('X')
            # samplemtry = self.main_obj.get_sample_positioner('Y')
            # finemtrx = self.main_obj.get_sample_fine_positioner('X')
            # finemtry = self.main_obj.get_sample_fine_positioner('Y')
            if self.is_zp_scan:
                DNM_E712_X_START_POS.put(self.zx_roi[START])
                DNM_E712_Y_START_POS.put(self.zy_roi[START])
            #     #moving them to the start gets rid of a goofy first line of the scan
            #     finemtrx.move(self.zx_roi[START])
            #     finemtry.move(self.zy_roi[START])
            #     samplemtrx.move(self.gx_roi[CENTER])
            #     samplemtry.move(self.gy_roi[CENTER])
            #
            else:
                DNM_E712_X_START_POS.put(self.x_roi[START])
                DNM_E712_Y_START_POS.put(self.y_roi[START])
            #     # !!! THIS NEEDS TESTING
            #     # moving them to the start gets rid of a goofy first line of the scan
            #     #finemtrx.move(self.x_roi[START])
            #     #finemtry.move(self.y_roi[START])
            #     samplemtrx.move(self.x_roi[START])
            #     samplemtry.move(self.y_roi[START])
            #     ############################

            e712_wdg.set_num_cycles(self.y_roi[NPOINTS])

            # yield from bps.stage(gate)
            yield from bps.kickoff(det)
            # , starts=starts, stops=stops, npts=npts, group='e712_wavgen', wait=True)
            # this starts the wavgen and waits for it to finish without blocking the Qt event loop
            shutter.open()
            yield from bps.mv(e712_dev.run, 1)
            shutter.close()
            # yield from bps.wait(group='e712_wavgen')
            yield from bps.unstage(gate)
            yield from bps.complete(
                det
            )  # stop minting events everytime the line_det publishes new data!
            # yield from bps.unmonitor(det)
            # the collect method on e712_flyer may just return as empty list as a formality, but future proofing!
            yield from bps.collect(det)
            print("make_single_image_e712_plan Leaving")

        return (yield from do_scan())

    def config_for_goniometer_scan_hdw_accel(self, dct, is_focus=False):
        """
        For a goniometer scan this will always be a fine scan of max range 100x100um (actually less)
        and the sequence to configure a scan is to position the goniometer at teh center of the scan everytime
        and set the +/- scan range to be about Zoneplate XY center (0,0)

        Need to take into account that this could be a LxL scan (uses xScan, yScan, zScan) or a PxP (uses xyScan, zScan)

        Because this scan uses the waveform generator on the E712 there are no positioners set for X and Y scan only the
        triggering of the waveform generator, will still need to do something so that save_hdr has something to get data
        from, not sure how to handle this yet.

        """
        ### VERY IMPORTANT the current PID tune for ZX is based on a velo (SLew Rate) of 1,000,000
        self.main_obj.device("DNM_ZONEPLATE_X").set_velo(1000000.0)
        self.main_obj.device("DNM_ZONEPLATE_Y").set_velo(1000000.0)
        #
        self.sample_mtrx = self.sample_finex = self.main_obj.device("DNM_ZONEPLATE_X")
        self.sample_mtry = self.sample_finey = self.main_obj.device("DNM_ZONEPLATE_Y")
        #
        # move Gx and Gy to center of scan, is it within a um?
        if self.zx_roi[CENTER] != 0.0:
            # zx is moving to scan center
            pass
        else:
            # Gx is moving to scan center nd zx is centered around 0, so move Gx to scan center
            self.main_obj.device(dct["cx_name"]).put(
                "user_setpoint", self.gx_roi[CENTER], wait=0.0
            )

        # if(self.is_within_dband( gy_mtr.get_position(), self.gy_roi[CENTER], 15.0)):
        if self.zy_roi[CENTER] != 0.0:
            # zy is moving to scan center
            pass
        else:
            # Gy is moving to scan center nd zy is centered around 0, so move Gy to scan center
            self.main_obj.device(dct["cy_name"]).put(
                "user_setpoint", self.gy_roi[CENTER], wait=0.0
            )
        #
        self.num_points = self.numY

        self.sample_mtrx.put("Mode", 0)

        self.modify_config_for_hdw_accel(self.sp_rois)

    def configure(
        self,
        wdg_com,
        sp_id=0,
        ev_idx=0,
        line=True,
        spectra=False,
        block_disconnect_emit=False,
        restore=True,
        z_enabled=False,
    ):
        """
        the base class configure all scan classes must call first to initialize member vars
        configure(): This is the configure routine that is required to be defined by every scan plugin. the main goal of the configure function is to
            - extract into member variables the scan param data from the wdg_com (widget communication) dict
            - configure the sample motors for the correct Mode for the upcoming scan
            - reset any relevant member variable counters
            - decide if it is a line by line, point by point or point spectrum scan
            - set the optimization function for this scan (which is used later to fine tune some key params of the sscan record before scan)
            - decide if this is a goniometer scan and set a flag accordingly
            - set the start/stop/npts etc fields of the relevant sscan records for a line or point scan by calling either:
                set_ImageLineScan_line_sscan_rec() or set_ImageLineScan_point_sscan_rec()
            - determine the positioners that will be used in this scan (they depend on the size of the scan range, coarse or fine etc)
            - call either config_for_goniometer_scan() or config_for_sample_holder_scan() depending on if a goniometer scan or not
            - create the numpy array in self.data by calling config_hdr_datarecorder()
            - then call final_setup() which must be called at the end of every configure() function

        :param wdg_com: wdg_com is a "widget Communication dictionary" and it is used to relay information to/from widgets regarding current regions of interest
        :type wdg_com: wdg_com is a dictionary comprised of 2 keys: WDGCOM_CMND and SPDB_SPATIAL_ROIS, both of which are strings defined in roi_dict_defs.py
                WDGCOM_CMND       : is a command that identifys what should be done with the rois listed in the next field
                SPDB_SPATIAL_ROIS : is a list of spatial roi's or spatial databases (sp_db)

        :param sp_id: sp_id is the "spatial ID" of the sp_db
        :type sp_id: integer

        :param ev_idx: ev_idx is the index into the e_rois[] list of energy regions of interest, this configure() function could be called again repeatedly if there are more than one
                energy regions of interest, this index is the index into that list, when the scan is first configured/called the index is always the first == 0
        :type ev_idx: integer

        :param line: line is a boolean flag indicating if the scan to be configured is a line by line scan or not
        :type line: bool

        :param block_disconnect_emit: because configure() can be called repeatedly by check_more_spatial_regions() I need to be able to control
                how the main GUI will react to a new scan being executed in succession, this flag if False will not blocking the emission of the 'disconnect' signals signal
                and if True it will block teh emission of the 'disconnect' that the main GUI is listening to
        :type block_disconnect_emit: bool

        :returns: None
        """

        self.set_spatial_id(sp_id)
        self.wdg_com = wdg_com
        self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        self.sp_db = self.sp_rois[sp_id]
        self.sp_ids = list(self.sp_rois.keys())
        self.sp_id = self.sp_ids[0]
        self.scan_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_TYPE)
        self.scan_sub_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)
        self.sample_positioning_mode = self.main_obj.get_sample_positioning_mode()
        self.sample_fine_positioning_mode = (
            self.main_obj.get_fine_sample_positioning_mode()
        )

        self.numImages = 1
        self.numX = dct_get(self.sp_db, SPDB_XNPOINTS)
        self.numY = dct_get(self.sp_db, SPDB_YNPOINTS)
        self.numZ = dct_get(self.sp_db, SPDB_ZNPOINTS)
        self.numZZ = dct_get(self.sp_db, SPDB_ZZNPOINTS)
        self.numZX = dct_get(self.sp_db, SPDB_ZXNPOINTS)
        self.numZY = dct_get(self.sp_db, SPDB_ZYNPOINTS)

        self.numE = dct_get(self.sp_db, SPDB_EV_NPOINTS)
        self.numSPIDS = len(self.sp_rois)
        self.e_rois = dct_get(self.sp_db, SPDB_EV_ROIS)
        e_roi = self.e_rois[0]
        self.numEPU = len(dct_get(e_roi, EPU_POL_PNTS))
        self.dwell = self.e_rois[0][DWELL]

        self.is_lxl = False
        self.is_pxp = False
        self.is_point_spec = False
        self.is_line_spec = False
        self.file_saved = False
        self.stack = False
        self.is_horiz_line = (self.sp_db["Y"]["RANGE"] <  0.0001)


        if self.scan_sub_type == scan_sub_types.LINE_UNIDIR:
            # LINE_UNIDIR
            self.is_lxl = True
            self.is_pxp = False
            # self.pdlys = {}
        else:
            # POINT_BY_POINT
            self.is_pxp = True
            self.is_lxl = False
            # self.pdlys = {}

        if self.fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE:
            self.is_zp_scan = True
        else:
            self.is_zp_scan = False

        if ev_idx == 0:
            self.reset_evidx()
            self.reset_imgidx()
            self.final_data_dir = None
            self.line_column_cntr = 0

        self.populate_ev_setpoints()

        self.update_roi_member_vars(self.sp_db)
        ret = self.verify_scan_velocity()
        self.determine_scan_res()
        #return if the scan velo was verified or not so that we can bail out of the scan before getting any deeper
        return(ret)

    def get_num_points_in_scan(self):
        """
        det a default but can be overriddden by inheriting class
        """
        # self.numX = dct_get(self.sp_db, SPDB_XNPOINTS)
        # self.numY = dct_get(self.sp_db, SPDB_YNPOINTS)
        # self.numZ = dct_get(self.sp_db, SPDB_ZNPOINTS)
        # self.numZZ = dct_get(self.sp_db, SPDB_ZZNPOINTS)
        # self.numZX = dct_get(self.sp_db, SPDB_ZXNPOINTS)
        # self.numZY = dct_get(self.sp_db, SPDB_ZYNPOINTS)
        # self.numE = dct_get(self.sp_db, SPDB_EV_NPOINTS)
        return self.numX * self.numY * self.numE

    def get_num_progress_events(self):
        """
        each scan needs to indicate how many event documents the RE will produce for the scan
        as each iteration (based on seq id of event document) makes up the total number of events for this scan,
        will change if it is point by point, line by line, or executed by the waveform generator where there are
        no event documents

        To be over ridden by inheriting class
        """
        return self.numX * self.numY * self.numE

    def verify_scan_velocity(self):
        """
        For Line by Line scans only, point by point always run at max velo.
        This is meant to take a motor and check that the scan velocity is not greater than the max velocity of the motor
        To be implemented by the inheriting class

        calc_scan_velo(self, mtr, rng, npoints, dwell)
        return True for scan velo checks out and False for it is invalid
        """
        return(True)


if __name__ == "__main__":
    pass
