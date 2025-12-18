"""
Created on Sep 26, 2016

@author: bergr
"""
import copy
from bluesky.plans import scan
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *
from cls.scanning.BaseScan import BaseScan
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger
from cls.utils.dict_utils import dct_put
from cls.types.stxmTypes import spectra_type_scans
from bcm.devices.ophyd.qt.data_emitters import SpecDataEmitter, SIS3820SpecDataEmitter
from cls.utils.json_utils import dict_to_json
from cls.plotWidgets.utils import gen_complete_spec_chan_name
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types

_logger = get_module_logger(__name__)

USE_E712_HDW_ACCEL = MAIN_OBJ.get_preset_as_bool("USE_E712_HDW_ACCEL", "BL_CFG_MAIN")

class BasePositionerScanClass(BaseScan):
    """a scan for executing a positioner line pxp scan in X,"""

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)
        # self.default_detector_nm = "DNM_DEFAULT_COUNTER"
        self._prev_position = None

    def configure_devs(self, dets):
        """
        configure_devs(): description

        :param dets: dets description
        :type dets: dets type

        :returns: None
        """

        for d in dets:
            if hasattr(d, "set_dwell"):
                d.set_dwell(self.dwell)
            if hasattr(d, "set_config"):
                d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=True)
            if hasattr(d, "setup_for_software_triggered"):
                d.setup_for_software_triggered()
            if hasattr(d, "set_row_change_index_points"):
                # use defaults of all args = False
                d.set_row_change_index_points()
            if hasattr(d, "enable_data_read_for_spectra"):
                d.enable_data_read_for_spectra(True)
            if hasattr(d, "set_spatial_ids"):
                d.set_spatial_ids(self._master_sp_id_list)

        # need to call this AFTER the settings are made above as the channel names for SIS3820 need spatial ids
        super().configure_devs(dets)

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        mainly for this scan we check the range of the scan against the soft limits
        return True if succesful False if not
        """
        #self.sample_mtrx = self.main_obj.get_sample_positioner("X")
        #self.sample_mtry = self.main_obj.get_sample_positioner("Y")
        mtr_x = self.main_obj.device(self.x_roi[POSITIONER])

        xstart, xstop = self.x_roi[START], self.x_roi[STOP]

        # check if beyond soft limits
        # if the soft limits would be violated then return False else continue and return True
        if not mtr_x.check_scan_limits(xstart, xstop):
            _logger.error("Scan would violate soft limits of X motor")
            return (False)

        if self.x_roi[POSITIONER].find("DNM_COARSE_") > -1:
            # disable the piezo's
            sample_finex = self.main_obj.get_sample_fine_positioner("X")
            sample_finey = self.main_obj.get_sample_fine_positioner("Y")
            sample_finex.set_power(0)
            sample_finey.set_power(0)

        mtr_x.move(xstart)

        return (True)

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
        #super().fine_scan_on_scan_done()
        sample_finex = self.main_obj.get_sample_fine_positioner("X")
        sample_finey = self.main_obj.get_sample_fine_positioner("Y")
        sample_finex.set_power(1)
        sample_finey.set_power(1)


    def make_pxp_scan_plan(self, dets, md=None, bi_dir=False):
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        self._bi_dir = bi_dir
        if md is None:
            _md = self.make_standard_metadata(
                        entry_name="entry0", scan_type=self.scan_type, dets=dets
                    )
            # # override the default detector so that it contains the first spatial id
            # _md["default_det"] = gen_complete_spec_chan_name(self.default_detector_nm, self._master_sp_id_list[0])
            # _md["default_entry_detectors"] = {self._master_sp_id_list[0]: _md["default_det"]}
            self._master_sp_id_list.sort()
            for d in dets:
                if d.name.find("SIS3820") > -1:
                    en_chan_lst = d.enabled_channels_lst
                    new_en_chan_lst = []
                    entry_dflt_dets = {}
                    for chan_dct in en_chan_lst:
                        for spid in self._master_sp_id_list:
                            # {'chan_nm': 'DNM_SIS3820_CHAN_00', 'chan_num': 0}
                            chan_nm = gen_complete_spec_chan_name(chan_dct["chan_nm"], spid)
                            if spid not in entry_dflt_dets.keys():
                                entry_dflt_dets[spid] = chan_nm
                            new_en_chan_lst.append({'chan_nm': chan_nm, 'chan_num': chan_dct["chan_num"]})
                    _md["sis3820_data_map"] = dict_to_json(copy.copy(new_en_chan_lst))
            _md["default_det"] = new_en_chan_lst[0]["chan_nm"]
            _md["default_entry_detectors"] = entry_dflt_dets
            md = {
                "metadata": dict_to_json( _md )
            }


        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():

            mtr_x = self.main_obj.device(self.x_roi[POSITIONER])
            shutter = self.main_obj.device("DNM_SHUTTER")
            shutter.open()
            for d in dets:
                # set spatial id in detector so channel name will indicate which channel and spatial id
                if hasattr(d, "set_spid"):
                    d.set_spid(self._master_sp_id_list[0])

            # yield from scan(
            #     dets,
            #     mtr_x,
            #     self.x_roi[START],
            #     self.x_roi[STOP],
            #     self.x_roi[NPOINTS],
            #     md=md,
            # )
            # a scan with N events
            for x_sp in self.x_roi['SETPOINTS']:
                yield from bps.mv(mtr_x, x_sp, group='BB')
                # yield from bps.wait('BB')
                #yield from bps.trigger_and_read(dets)
                yield from bps.trigger_and_read(dets + [mtr_x])


            shutter.close()
            for d in dets:
                #turn spec flag back off
                if hasattr(d, "enable_data_read_for_spectra"):
                    d.enable_data_read_for_spectra(False)
                if hasattr(d, "set_spatial_ids"):
                    d.set_spatial_ids([])

            # print("PositionerScanClass: make_scan_plan Leaving")

        return (yield from do_scan())

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
                self._master_sp_id_list, self.x_roi[SETPOINTS]
            )
            mtr_x = self.main_obj.device(self.x_roi[POSITIONER])
            # we also need to pass the sp_id because it needs to send it on to the plotter as data comes in
            # spid_seq_map
            self._emitter_cb = SIS3820SpecDataEmitter(det.det_id,
                                       counter_nm,
                                       det_dev=det,
                                       spid_seq_map=spid_seq_map)
            self._emitter_sub = ew.subscribe_cb(self._emitter_cb)
            self._emitter_cb.new_plot_data.connect(func)
        else:
            _logger.error("Wrong scan type, needs to be a spectra scan type")



    def configure(self, wdg_com, sp_id=0, line=False):
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
        if not ret:
            return(ret)

        # use base configure x y motor scan
        self.stack = False
        self.is_point_spec = True
        self.is_pxp = True
        self.is_lxl = False
        self.sp_id = sp_id

        dct_put(
            self.sp_db,
            SPDB_RECT,
            (self.x_roi[START], self.y_roi[START], self.x_roi[STOP], self.y_roi[STOP]),
        )

        if USE_E712_HDW_ACCEL:
            self.main_obj.device("DNM_E712_CURRENT_SP_ID").put(sp_id)

        self.configure_x_scan_LINEAR(wdg_com, sp_id=sp_id, line=False)

        self.move_zpxy_to_its_center()

        self.seq_map_dct = self.generate_2d_seq_image_map(
            1, 1, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=False
        )
        self.finish_setup()

        return(ret)



