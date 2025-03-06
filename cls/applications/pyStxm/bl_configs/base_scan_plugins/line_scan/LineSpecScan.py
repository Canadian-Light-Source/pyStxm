"""
Created on Sep 26, 2016

@author: bergr
"""

import numpy as np
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *

from cls.applications.pyStxm import abs_path_to_ini_file
from cls.scanning.BaseScan import BaseScan, get_sequence_nums, get_rows
from cls.utils.roi_dict_defs import *

from cls.types.stxmTypes import scan_types, sample_positioning_modes

from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.utils.json_utils import dict_to_json
from bcm.devices.ophyd.qt.data_emitters import ImageDataEmitter, SIS3820ImageDataEmitter

_logger = get_module_logger(__name__)
appConfig = ConfigClass(abs_path_to_ini_file)


class BaseLineSpecScanClass(BaseScan):
    """
    This class
    """

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)

    def verify_scan_velocity(self):
        """
        This is meant to take a motor and check that the scan velocity is not greater than the max velocity of the motor
        To be implemented by the inheriting class

        calc_scan_velo(self, mtr, rng, npoints, dwell)
        return True for scan velo checks out and False for it is invalid
        """
        #mtr_gx = self.main_obj.device("DNM_GONI_X")
        #mtr_x = self.main_obj.device("DNM_SAMPLE_X")
        crs_x = self.main_obj.device("DNM_COARSE_X")
        piezo_mtr_x = self.main_obj.get_sample_fine_positioner("X")
        if self.is_pxp:
            return(True)

        if self.is_fine_scan:
            self.scan_velo = self.calc_scan_velo(piezo_mtr_x, self.x_roi[RANGE], self.x_roi[NPOINTS], self.dwell)
        else:
            #coarse scan
            self.scan_velo = self.calc_scan_velo(crs_x, self.x_roi[RANGE], self.x_roi[NPOINTS], self.dwell)
        if self.scan_velo > 0:
            return(True)
        else:
            return(False)

    def init_subscriptions(self, ew, func, dets=[]):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :return:
        """

        if self.is_pxp:
            # self._emitter_cb = ImageDataEmitter(DNM_DEFAULT_COUNTER, y=DNM_ZONEPLATE_Z, x=DNM_SAMPLE_X,
            #                                          scan_type=self.scan_type, bi_dir=self._bi_dir)
            counter_nm = dets[0].name
            det = self.main_obj.device(counter_nm)
            if counter_nm.find("SIS3820") > -1:
                self._emitter_cb = SIS3820ImageDataEmitter(
                    det.det_id,
                    counter_nm,
                    det_dev=det,
                    is_pxp=self.is_pxp,
                    y="DNM_ZONEPLATE_Z",
                    x="DNM_SAMPLE_X",
                    scan_type=self.scan_type,
                    bi_dir=self._bi_dir,
                )
            else:
                self._emitter_cb = ImageDataEmitter(
                    "DNM_DEFAULT_COUNTER",
                    y="DNM_ZONEPLATE_Z",
                    x="DNM_SAMPLE_X",
                    scan_type=self.scan_type,
                    bi_dir=self._bi_dir,
                )
            # self._emitter_cb = ImageDataEmitter(DNM_DEFAULT_COUNTER, y='mtr_y', x='mtr_x',
            #                                    scan_type=self.scan_type, bi_dir=self._bi_dir)
            self._emitter_cb.set_row_col(
                rows=self.numE, cols=self.x_roi[NPOINTS], seq_dct=self.seq_map_dct
            )
            self._emitter_sub = ew.subscribe_cb(self._emitter_cb)
            self._emitter_cb.new_plot_data.connect(func)

        else:
            counter_nm = dets[0].name
            det = self.main_obj.device(counter_nm)
            if counter_nm.find("SIS3820") > -1:
                self._emitter_cb = SIS3820ImageDataEmitter(
                    det.det_id,
                    counter_nm,
                    det_dev=det,
                    is_pxp=self.is_pxp,
                    y="DNM_ZONEPLATE_Z",
                    x="DNM_SAMPLE_X",
                    scan_type=self.scan_type,
                    bi_dir=self._bi_dir,
                )
            else:
                self._emitter_cb = ImageDataEmitter(
                    "DNM_DEFAULT_COUNTER",
                    y="DNM_ZONEPLATE_Z",
                    x="DNM_SAMPLE_X",
                    scan_type=self.scan_type,
                    bi_dir=self._bi_dir,
                )
            self._emitter_cb.set_row_col(
                rows=self.zz_roi[NPOINTS],
                cols=self.x_roi[NPOINTS],
                seq_dct=self.seq_map_dct,
            )
            self._emitter_sub = ew.subscribe_cb(self._emitter_cb)
            self._emitter_cb.new_plot_data.connect(func)

    def get_num_progress_events(self):
        """
        each scan needs to indicate how many event documents the RE will produce for the scan
        as each iteration (based on seq id of event document) makes up the total number of events for this scan,
        will change if it is point by point, line by line, or executed by the waveform generator where there are
        no event documents

        To be over ridden by inheriting class
        """
        if self.is_pxp:
            return self.numY * self.numE
        else:
            return self.numE

    def on_scan_done(self, call_base_class_only=False):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
        if call_base_class_only:
            return

        if self.is_fine_scan:
            super().fine_scan_on_scan_done()
        else:
            mtr_dct = self.determine_samplexy_posner_pvs()
            mtr_x = self.main_obj.device(mtr_dct["sx_name"])
            mtr_y = self.main_obj.device(mtr_dct["sy_name"])
            mtr_x.move_fine_to_coarse_fbk_pos()
            mtr_y.move_fine_to_coarse_fbk_pos()

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        call a specific scan start for fine scans
        """
        # this is now checked earlier by the scan pluggin because the multi region widget needs to update its UI colors
        # accordingly, so we can just assume if it made it this far its good to go
        return True
        # mtr_dct = self.determine_samplexy_posner_pvs()
        # # mtr_x = self.main_obj.device(mtr_dct["sx_name"])
        # # mtr_y = self.main_obj.device(mtr_dct["sy_name"])
        # mtr_x = self.main_obj.get_sample_positioner("X")
        # mtr_y = self.main_obj.get_sample_positioner("Y")
        #
        # # #determine if the scan will violate soft limits
        # accel_dist_prcnt_pv, deccel_dist_prcnt_pv = self.get_accel_deccel_pvs()
        #
        # ACCEL_DISTANCE = self.x_roi[RANGE] * accel_dist_prcnt_pv.get()
        # DECCEL_DISTANCE = self.x_roi[RANGE] * deccel_dist_prcnt_pv.get()
        # xstart = self.x_roi[START] - ACCEL_DISTANCE
        # xstop = self.x_roi[STOP] + DECCEL_DISTANCE
        # ystart, ystop = self.y_roi[START] , self.y_roi[STOP]
        #
        # #check if beyond soft limits
        # # if the soft limits would be violated then return False else continue and return True
        # if not mtr_x.check_scan_limits(xstart, xstop):
        #     _logger.error("Scan would violate soft limits of X motor")
        #     return(False)
        # if not mtr_y.check_scan_limits(ystart, ystop):
        #     _logger.error("Scan would violate soft limits of Y motor")
        #     return(False)
        #
        # if self.is_fine_scan:
        #     super().fine_scan_go_to_scan_start()
        # else:
        #
        #     # before starting scan check the interferometers, note BOTH piezo's must be off first
        #     mtr_x.set_piezo_power_off()
        #     mtr_y.set_piezo_power_off()
        #
        #     if not mtr_x.do_voltage_check():
        #         self.mtr_recenter_msg.show()
        #         mtr_x.do_autozero()
        #     if not mtr_y.do_voltage_check():
        #         self.mtr_recenter_msg.show()
        #         mtr_y.do_autozero()
        #
        #     mtr_x.do_interferometer_check()
        #     mtr_y.do_interferometer_check()
        #
        #     self.mtr_recenter_msg.hide()
        #
        #     mtr_x.move_coarse_to_scan_start(start=xstart, stop=self.x_roi[STOP], npts=self.x_roi[NPOINTS], dwell=self.dwell)
        #     mtr_y.move_coarse_to_position(ystart, False)
        #
        #     #coarse focus scan
        #     mtr_x.set_piezo_power_off()
        #     mtr_y.set_piezo_power_off()
        #
        # return(True)

    # def configure_devs(self, dets):
    #     """
    #     configure_devs(): description
    #
    #     :param dets: dets description
    #     :type dets: dets type
    #
    #     :returns: None
    #     """
    #     super().configure_devs(dets)
    #
    #     for d in dets:
    #         if hasattr(d, "set_dwell"):
    #             d.set_dwell(self.dwell)
    #         if hasattr(d, "set_config"):
    #             if self.is_horiz_line:
    #                 is_pxp_scan = False
    #             else:
    #                 is_pxp_scan = True
    #             d.set_config(self.y_roi[NPOINTS], self.x_roi[NPOINTS], is_pxp_scan=is_pxp_scan)
    #         if self.is_pxp:
    #             if hasattr(d, "setup_for_software_triggered"):
    #                 d.setup_for_software_triggered()
    #         else:
    #             if hasattr(d, "setup_for_hdw_triggered"):
    #                 d.setup_for_hdw_triggered()
    def configure_devs(self, dets):
        """
        configure_devs(): description

        :param dets: dets description
        :type dets: dets type

        :returns: None
        """
        # super().configure_devs(dets)

        for d in dets:
            if hasattr(d, "set_dwell"):
                d.set_dwell(self.dwell)
            if hasattr(d, "set_config"):
                if self.is_horiz_line:
                    is_pxp_scan = False
                else:
                    is_pxp_scan = True
                d.set_config(self.y_roi[NPOINTS], self.x_roi[NPOINTS], is_pxp_scan=is_pxp_scan)
            if self.is_pxp:
                if hasattr(d, "setup_for_software_triggered"):
                    d.setup_for_software_triggered()
                if hasattr(d, "set_row_change_index_points"):
                    # use defaults of all args = False
                    d.set_row_change_index_points()
                # if hasattr(d, "enable_data_read_for_spectra"):
                #     d.enable_data_read_for_spectra(True)
                # if hasattr(d, "set_spec_ids"):
                #     d.set_spec_ids(self.e_ids)
            else:
                if hasattr(d, "setup_for_hdw_triggered"):
                    d.setup_for_hdw_triggered()
                if hasattr(d, "set_row_change_index_points"):
                    d.set_row_change_index_points(remove_first_point=True)
                # if hasattr(d, "enable_data_read_for_spectra"):
                #     d.enable_data_read_for_spectra(True)
                # if hasattr(d, "set_spec_ids"):
                #     d.set_spec_ids(self.e_ids)

        # need to call this AFTER the settings are made above as the channel names for SIS3820 need spatial ids
        super().configure_devs(dets)

    def make_scan_plan(self, dets, md=None, bi_dir=False):
        """
        override the default make_scan_plan to set the scan_type
        :param dets:
        :param gate:
        :param md:
        :param bi_dir:
        :return:
        """
        self.configure_devs(dets)

        if self.is_pxp:
            return self.make_pxp_scan_plan(dets, md=md, bi_dir=bi_dir)
        else:
            # return (self.make_single_image_e712_plan(dets, gate, md=md, bi_dir=bi_dir))
            return self.make_lxl_scan_plan(dets, md=md, bi_dir=bi_dir)



    def make_pxp_scan_plan(self, dets, md=None, bi_dir=False):
        """
            gate and counter need to be staged for pxp
        :param dets:
        :param gate:
        :param bi_dir:
        :return:
        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        self._bi_dir = bi_dir
        mtr_dct = self.determine_samplexy_posner_pvs()

        @bpp.baseline_decorator(dev_list)
        @bpp.stage_decorator(dets)
        # @bpp.run_decorator(md=md)
        def do_scan():

            if self.is_fine_scan:
                mtr_x = self.main_obj.device(mtr_dct["fx_name"])
                mtr_y = self.main_obj.device(mtr_dct["fy_name"])
            else:
                mtr_x = self.main_obj.device(mtr_dct["cx_name"])
                mtr_y = self.main_obj.device(mtr_dct["cy_name"])

            ev_mtr = self.main_obj.device("DNM_ENERGY")
            pol_mtr = self.main_obj.device("DNM_EPU_POLARIZATION")
            shutter = self.main_obj.device("DNM_SHUTTER")


            # this starts the wavgen and waits for it to finish without blocking the Qt event loop
            # the detector will be staged automatically by the grid_scan plan
            shutter.open()
            idx = 0

            pol_setpoints = self.e_rois[0][EPU_POL_PNTS]
            for pol in pol_setpoints:
                md = {
                    "metadata": dict_to_json(
                        self.make_standard_metadata(
                            entry_name="entry%d" % idx,
                            scan_type=self.scan_type,
                            dets=dets,
                        )
                    )
                }
                yield from bpp.open_run(md)
                # switch to new polarization
                yield from bps.mv(pol_mtr, pol)
                for ev_roi in self.e_rois:
                    # switch to new energy
                    for ev_sp in ev_roi[SETPOINTS]:
                        yield from bps.mv(ev_mtr, ev_sp)
                        self.dwell = ev_roi[DWELL]

                        # go to start of line
                        # yield from bps.mv(mtr_x, self.x_roi[START], mtr_y, self.y_roi[START])

                        # now do point by point
                        for i in range(int(self.x_roi[NPOINTS])):
                            x = self.x_roi[SETPOINTS][i]
                            y = self.y_roi[SETPOINTS][i]
                            yield from bps.mv(mtr_y, y)
                            yield from bps.mv(mtr_x, x)
                            #yield from bps.trigger_and_read(dets + [mtr_y, mtr_x])
                            yield from bps.trigger_and_read(dets)

                yield from bpp.close_run()
                idx += 1
            shutter.close()
            # yield from bps.wait(group='e712_wavgen')

            # print("LineSpecClass PxP: make_scan_plan Leaving")

        return (yield from do_scan())

    def make_lxl_scan_plan(self, dets, md=None, bi_dir=False):
        """

        this needs to be adapted to be a fly scan, setup SampleX to trigger at correct location, set scan velo and acc range
        and then call scan, gate an d counter need to be staged for lxl
        :param dets:
        :param gate:
        :param bi_dir:
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

        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():

            print('entering BaseLineSpecScanClass: do_scan')
            psmtr_x = self.main_obj.device("DNM_SAMPLE_X")
            psmtr_y = self.main_obj.device("DNM_SAMPLE_Y")
            mtr_ev = self.main_obj.device("DNM_ENERGY")
            crs_x = self.main_obj.device("DNM_COARSE_X")
            crs_y = self.main_obj.device("DNM_COARSE_Y")
            shutter = self.main_obj.device("DNM_SHUTTER")
            piezo_mtr_x = self.main_obj.get_sample_fine_positioner("X")
            piezo_mtr_y = self.main_obj.get_sample_fine_positioner("Y")
            accel_dist_prcnt_pv, deccel_dist_prcnt_pv = self.get_accel_deccel_pvs()

            ev_setpoints = []
            for ev_roi in self.e_rois:
                # switch to new energy
                for ev_sp in ev_roi[SETPOINTS]:
                    ev_setpoints.append(ev_sp)

            if self.is_fine_scan:
                psmtr_x.set_piezo_power_on()
                psmtr_y.set_piezo_power_on()
                mtr_x = piezo_mtr_x
                mtr_y = piezo_mtr_y

            else:
                psmtr_x.set_piezo_power_off()
                psmtr_y.set_piezo_power_off()
                mtr_x = crs_x
                mtr_y = crs_y

            shutter.open()
            # det = dets[0]
            sisdev = dets[0]
            ACCEL_DISTANCE = self.x_roi[RANGE] * accel_dist_prcnt_pv.get()
            DECCEL_DISTANCE = self.x_roi[RANGE] * deccel_dist_prcnt_pv.get()
            piezo_mtr_x.scan_start.put(self.x_roi[START] - ACCEL_DISTANCE)
            piezo_mtr_x.scan_stop.put(self.x_roi[STOP] + DECCEL_DISTANCE)
            #print(f"BaseLineSpecScanClass: ACCEL_DISTANCE = {ACCEL_DISTANCE}, DECCEL_DISTANCE={DECCEL_DISTANCE}")
            piezo_mtr_x.marker_start.put(self.x_roi[START])
            piezo_mtr_x.marker_stop.put(self.x_roi[STOP])
            piezo_mtr_x.set_marker.put(self.x_roi[START])
            piezo_mtr_x.set_marker_position(self.x_roi[START])

            yield from bps.mv(mtr_x, self.x_roi[START] - ACCEL_DISTANCE, group='BB')
            yield from bps.mv(mtr_y, self.y_roi[CENTER], group='BB')
            yield from bps.wait('BB')

            for ev_sp in ev_setpoints:

                yield from bps.mv(mtr_ev, ev_sp, group='EV')
                yield from bps.wait('EV')

                ACCEL_DISTANCE = self.x_roi[RANGE] * accel_dist_prcnt_pv.get()
                DECCEL_DISTANCE = self.x_roi[RANGE] * deccel_dist_prcnt_pv.get()
                mtr_x.velocity.put(self.scan_velo)
                piezo_mtr_x.enable_marker_position(True)
                yield from bps.mv(sisdev.run, 1, group='SIS3820')
                yield from bps.wait('SIS3820')

                yield from bps.mv(mtr_x, self.x_roi[STOP] + DECCEL_DISTANCE, group='BB')
                yield from bps.wait('BB')
                yield from bps.trigger_and_read(dets)
                piezo_mtr_x.enable_marker_position(False)

                mtr_x.velocity.put(3500)
                yield from bps.mv(mtr_x, self.x_roi[START] - ACCEL_DISTANCE, group='CC')
                yield from bps.wait('CC')

                # print("bottom of loop")
            shutter.close()

            # print("BaseLineSpecScanClass LxL: make_scan_plan Leaving")

        return (yield from do_scan())



    def configure(
        self,
        wdg_com,
        sp_id=0,
        ev_idx=0,
        line=True,
        spectra=False,
        block_disconnect_emit=False,
    ):
        """
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
        ret = super().configure(wdg_com, sp_id=sp_id, line=line)
        if not ret:
            return(ret)

        _logger.info("configure: LineScan %d" % sp_id)

        if ev_idx == 0:
            self.reset_evidx()
            self.reset_imgidx()
            self.final_data_dir = None
            self.line_column_cntr = 0

        e_roi = self.e_rois[ev_idx]
        dct_put(
            self.sp_db,
            SPDB_RECT,
            (e_roi[START], self.x_roi[START], self.e_rois[-1][STOP], self.x_roi[STOP]),
        )

        self.configure_sample_motors_for_scan()

        self.setpointsDwell = dct_get(e_roi, DWELL)
        self.setpointsPol = dct_get(e_roi, EPU_POL_PNTS)
        self.setpointsOff = dct_get(e_roi, EPU_OFF_PNTS)
        self.setpointsAngle = dct_get(e_roi, EPU_ANG_PNTS)

        self.dwell = e_roi[DWELL]

        self.numEPU = len(self.setpointsPol)
        self.numE = int(self.sp_db[SPDB_EV_NPOINTS])
        self.numSPIDS = len(self.sp_rois)
        self.numImages = 1

        self.numZX = self.zx_roi[NPOINTS]
        self.numZY = self.zy_roi[NPOINTS]

        # NOTE! currently only arbitrary line is supported when equal number of x and e points so use E points
        # self.numY = self.e_roi[NPOINTS]
        self.numX = int(self.numE)
        self.numY = int(self.x_roi[NPOINTS])

        if self.scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
            self.is_line_spec = True
        else:
            _logger.error(
                "LineSpecSSCAN: unable to determine scan type [%d]" % self.scan_type
            )
            return
        dct = self.determine_samplexy_posner_pvs()

        accRange = 0
        if self.numImages > 1:
            self.stack = True
        else:
            self.stack = False

        if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            self.config_for_goniometer_scan(dct)

        else:
            self.config_for_sample_holder_scan(dct)

        self.config_hdr_datarecorder(self.stack)

        # #testing
        self.seq_map_dct = self.generate_linespec_seq_image_map(
                           self.e_rois, self.x_roi, self.y_roi)
        # if self.is_pxp:
        #     self.seq_map_dct = self.generate_pxp_ev_roi_seq_image_map(
        #                    self.e_rois, self.x_roi, self.y_roi)
        # else:
        #     self.seq_map_dct = self.generate_ev_roi_seq_image_map(
        #         self.e_rois, self.x_roi[NPOINTS]
        #     )

        # THIS must be the last call
        self.finish_setup()
        self.new_spatial_start.emit(ev_idx)
        return(ret)

    def generate_linespec_seq_image_map(self, erois, x_roi, y_roi):
        """
            used primarily by Linespec scans that can have multiple images per scan where each image represents a
            different energy range and resolution
        :param erois:
        :param nxpnts:
        :return:
        """

        def get_columns(num_cols, npnts):
            lst = list(range(0, num_cols))
            return np.repeat(lst, npnts)

        dct = {}
        ev_idx = 0
        seq_num = 0
        nxpnts = int(x_roi[NPOINTS])
        ttl_ev_npnts = 0
        for eroi in erois:
            #this needs to include polarization points as well
            ttl_ev_npnts += int(eroi[NPOINTS])

        row_lst = list(range(0, nxpnts))
        if self.is_pxp:
            seq = get_sequence_nums(seq_num, ttl_ev_npnts * nxpnts)
            rows = get_rows(row_lst, ttl_ev_npnts)
            cols = get_columns(ttl_ev_npnts, nxpnts)

            ttl = zip(seq, rows, cols)
            for s, r, c in ttl:
                dct[s] = {"img_num": 0, "row": r, "col": c}
        else:
            # each line is an event in the sequence
            for seq in range(seq_num, seq_num + ttl_ev_npnts):
                dct[seq] = {"img_num": 0, "row": 0, "col": seq}

        return dct

    def generate_pxp_ev_roi_seq_image_map(self, erois, x_roi, y_roi):
        """
            used primarily by Linespec scans that can have multiple images per scan where each image represents a
            different energy range and resolution
        :param erois:
        :param nxpnts:
        :return:
        """

        def get_columns(num_cols, npnts):
            lst = list(range(0, num_cols))
            return np.repeat(lst, npnts)

        dct = {}
        ev_idx = 0
        seq_num = 0
        nxpnts = int(x_roi[NPOINTS])
        ttl_ev_npnts = 0
        for eroi in erois:
            ttl_ev_npnts += int(eroi[NPOINTS])

        row_lst = list(range(0, nxpnts))
        seq = get_sequence_nums(seq_num, ttl_ev_npnts * nxpnts)
        rows = get_rows(row_lst, ttl_ev_npnts)
        cols = get_columns(ttl_ev_npnts, nxpnts)

        ttl = zip(seq, rows, cols)
        for s, r, c in ttl:
            dct[s] = {"img_num": 0, "row": r, "col": c}

        return dct