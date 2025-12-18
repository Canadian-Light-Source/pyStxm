"""
Created on Sep 26, 2016

@author: bergr
"""
import copy
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *
from cls.scanning.BaseScan import BaseScan
from cls.utils.roi_dict_defs import *
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.log import get_module_logger
from cls.types.stxmTypes import sample_fine_positioning_modes, spectra_type_scans
#from bcm.devices.ophyd.qt.data_emitters import SpecDataEmitter
from bcm.devices.ophyd.qt.data_emitters import SpecDataEmitter, SIS3820SpecDataEmitter
from cls.utils.json_utils import dict_to_json
from cls.plotWidgets.utils import gen_complete_spec_chan_name
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types

USE_E712_HDW_ACCEL = MAIN_OBJ.get_preset_as_bool("USE_E712_HDW_ACCEL", "BL_CFG_MAIN")

_logger = get_module_logger(__name__)


class BasePointSpecScanClass(BaseScan):
    """a scan for executing a positioner line pxp scan in X,"""

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)
        # self.default_detector_nm = "DNM_DEFAULT_COUNTER"

    def configure_devs(self, dets):
        """
        -
        """
        for d in dets:
            if hasattr(d, "set_dwell"):
                d.set_dwell(self.dwell)
            if hasattr(d, "set_config"):
                d.set_config(self.y_roi[NPOINTS], self.x_roi[NPOINTS], is_pxp_scan=True)
            if hasattr(d, "setup_for_software_triggered"):
                d.setup_for_software_triggered()
            if hasattr(d, "enable_data_read_for_spectra"):
                d.enable_data_read_for_spectra(True)
            if hasattr(d, "set_spatial_ids"):
                d.set_spatial_ids(self._master_sp_id_list)
        #need to call this AFTER the settings are made above as the channel names for SIS3820 need spatial ids
        super().configure_devs(dets)

    def get_num_progress_events(self):
        """
        over ride base class def
        """
        return self.numSPIDS * self.numE * self.numEPU

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        call a specific scan start for fine scans
        """
        super().fine_scan_go_to_scan_start()
        return(True)

    def init_subscriptions(self, ew, func, det_lst):
        """
        Base init_subscriptions is used by most scans
        :param ew:
        :param func:
        :return:
        """
        counter_nm = det_lst[0].name
        det = self.main_obj.device(counter_nm)
        if self.scan_type in spectra_type_scans:
            spid_seq_map = self.gen_spid_seq_map(
                self._master_sp_id_list, self.ev_setpoints
            )
            if self.is_zp_scan:
                mtr_x = self.main_obj.device("DNM_ZONEPLATE_X")
            else:
                mtr_x = self.main_obj.device(self.x_roi[POSITIONER])
            self._emitter_cb = SIS3820SpecDataEmitter(det.det_id,
                                                      counter_nm,
                                                      det_dev=det,
                                                      spid_seq_map=spid_seq_map)
            self._emitter_sub = ew.subscribe_cb(self._emitter_cb)
            self._emitter_cb.new_plot_data.connect(func)
        else:
            _logger.error("Wrong scan type, needs to be a spectra scan type")

    def make_pxp_scan_plan(self, dets, md=None, bi_dir=False):
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        self._bi_dir = bi_dir

        if md is None:
            _md = self.make_standard_metadata(
                        entry_name="entry0",
                        scan_type=self.scan_type,
                        dets=dets,
                        override_xy_posner_nms=True,
                    )
            # override the sis3820_map so that it contains th efully qualified channel names with spid
            #{'chan_nm': 'DNM_SIS3820_CHAN_00', 'chan_num': 0}
            self._master_sp_id_list.sort()
            for d in dets:
                if d.name.find("SIS3820") > -1:
                    en_chan_lst = d.enabled_channels_lst
                    new_en_chan_lst = []
                    entry_dflt_dets = {}
                    for chan_dct in en_chan_lst:
                        for spid in self._master_sp_id_list:
                            #{'chan_nm': 'DNM_SIS3820_CHAN_00', 'chan_num': 0}
                            chan_nm = gen_complete_spec_chan_name(chan_dct["chan_nm"], spid)
                            if spid not in entry_dflt_dets.keys():
                                entry_dflt_dets[spid] = chan_nm
                            new_en_chan_lst.append({'chan_nm':chan_nm, 'chan_num': chan_dct["chan_num"]})
                    _md["sis3820_data_map"] = dict_to_json(copy.copy(new_en_chan_lst))
            _md["default_det"] = new_en_chan_lst[0]["chan_nm"]
            _md["default_entry_detectors"] = entry_dflt_dets
            md = {
                "metadata": dict_to_json(_md)
            }



        # override the POSIIONER so tha nxstxm and can export properly
        # md = self.add_spids_xy_setpoints(md)
        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():

            # need to make sure that all spatial points are within range of the piezo's before executing this

            #assume all points a reachable
            energy_dev = self.main_obj.device("DNM_ENERGY_DEVICE")
            mtr_x = self.main_obj.get_sample_fine_positioner("X")
            mtr_y = self.main_obj.get_sample_fine_positioner("Y")
            pol_mtr = self.main_obj.device("DNM_EPU_POLARIZATION")
            off_mtr = self.main_obj.device("DNM_EPU_OFFSET")
            ang_mtr = self.main_obj.device("DNM_EPU_ANGLE")
            shutter = self.main_obj.device("DNM_SHUTTER")

            shutter.open()

            epu_sps = zip(self.setpointsPol, self.setpointsOff, self.setpointsAngle)
            for pol, off, ang in epu_sps:
                # switch to new polarization, offset and angle
                if pol_mtr.get_position() != pol:
                    yield from bps.mv(pol_mtr, pol)
                if off_mtr.get_position() != off:
                    yield from bps.mv(off_mtr, off)
                if ang_mtr.get_position() != ang:
                    yield from bps.mv(ang_mtr, ang)
                # switch to new energy
                for ev_sp in self.ev_setpoints:
                    yield from bps.mv(energy_dev, ev_sp)
                    self.dwell = self.setpointsDwell

                    for sp_id, sp_db in self.sp_rois.items():
                        for d in dets:
                            # set spatial id in detector so channel name will indicate which channel and spatial id
                            if hasattr(d, "set_spid"):
                                d.set_spid(sp_id)

                        x_pos = dct_get(sp_db, SPDB_XSTART)
                        y_pos = dct_get(sp_db, SPDB_YSTART)
                        yield from bps.mv(mtr_x, x_pos, mtr_y, y_pos)
                        yield from bps.trigger_and_read(dets)

            shutter.close()
            for d in dets:
                #turn spec flag back off
                if hasattr(d, "enable_data_read_for_spectra"):
                    d.enable_data_read_for_spectra(False)
                if hasattr(d, "set_spatial_ids"):
                    d.set_spatial_ids([])

            # print("PositionerScanClass: make_scan_plan Leaving")

        return (yield from do_scan())

    def on_scan_done(self):
        """
        called when scan is done
        turn the fine motor power back on so that it is ready for next scan type
        """
        # call base class method first
        super().on_scan_done()

    def configure(self, wdg_com, sp_id=0, ev_idx=0, line=False, block_disconnect_emit=False):
        """
        configure(): description

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :param sp_id: sp_id description
        :type sp_id: sp_id type

        :param line=False: line=False description
        :type line=False: line=False type

        :returns: None
        """
        ret = super().configure(wdg_com, sp_id=sp_id, line=line, z_enabled=False)
        # use base configure x y motor scan
        self.stack = False
        self.is_point_spec = True
        self.is_pxp = True
        self.is_lxl = False
        self.sp_id = sp_id

        if USE_E712_HDW_ACCEL:
            self.main_obj.device("DNM_E712_CURRENT_SP_ID").put(sp_id)

        self.wdg_com = wdg_com
        self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        self.sp_id_list = list(self.sp_rois.keys())
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
        self.ev_setpoints = dct_get(wdg_com, SPDB_SINGLE_LST_EV_ROIS)
        e_roi = self.e_rois[0]
        self.setpointsDwell = dct_get(e_roi, DWELL)
        self.setpointsPol = dct_get(e_roi, EPU_POL_PNTS)
        self.setpointsOff = dct_get(e_roi, EPU_OFF_PNTS)
        self.setpointsAngle = dct_get(e_roi, EPU_ANG_PNTS)

        # self.setpointsPol = len(dct_get(e_roi, EPU_POL_PNTS))
        # if self.setpointsPol < 1:
        #     self.setpointsPol = 1

        self.update_roi_member_vars(self.sp_db)

        dct_put(
            self.sp_db,
            SPDB_RECT,
            (self.x_roi[START], self.y_roi[START], self.x_roi[STOP], self.y_roi[STOP]),
        )

        if self.fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE:
            self.is_zp_scan = True
        else:
            self.is_zp_scan = False

        self.dwell = self.e_rois[0][DWELL]

        self.reset_evidx()
        self.reset_imgidx()

        # self.stack_scan = False
        self.config_hdr_datarecorder(stack=self.stack)
        self.move_zpxy_to_its_center()

        self.seq_map_dct = self.gen_spectrum_scan_seq_map(
            self.numE, self.sp_id_list, num_pol=self.numEPU
        )

        # THIS must be the last call
        self.finish_setup()
        return(ret)

