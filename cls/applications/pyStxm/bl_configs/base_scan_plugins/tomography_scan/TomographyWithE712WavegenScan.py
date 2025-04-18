# coding=utf-8
"""
Created on Dec 8, 2017

@author: bergr
"""

import bluesky.plan_stubs as bps

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *

from cls.applications.pyStxm import abs_path_to_ini_file
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.scanning.BaseScan import BaseScan
from cls.types.stxmTypes import (
    scan_types,
    sample_positioning_modes,
    sample_fine_positioning_modes,
)
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.utils.dict_utils import dct_get
from cls.utils.json_utils import dict_to_json

_logger = get_module_logger(__name__)

appConfig = ConfigClass(abs_path_to_ini_file)


class BaseTomographyWithE712WavegenScanClass(BaseScan):
    """
    This class is based on SampleImageWithEnergySSCAN and modified to support the E712 waveform generator
    for executing the low level scan and triggering, the main scan is still controlled by SSCAN records but instead of using sscan records and motor
    positioners to move the motors it uses the E712 waveform generator which must be configured first here.

    The standard BaseScan api will be followed and hte E712 wave generator will only be used if it is :
        - a fine scan
        - the E712 is available
    if the scan is a coarse scan it will not be used, this should work for both zoneplate and standard sample fine scans.

    Note: the configuration is the only thing that changes in order to execute pxp or lxl scans, the data from a pxp scans when using the
    waveform generator are received as a complete line just like lxl scans
    """

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=MAIN_OBJ)
        self.x_use_reinit_ddl = False
        # self.x_use_ddl = False
        # self.x_use_reinit_ddl = False
        # self.x_start_end_pos = False
        # self.x_force_reinit = False
        self.x_auto_ddl = True
        # self.spid_data = None
        self.img_idx_map = {}
        self.spid_data = {}
        self.start_gate_and_cntr = False
        self.e712_enabled = True
        self.e712_wg = MAIN_OBJ.device("DNM_E712_WIDGET")
        # NOTE THIS IS NOT THE CORRECT DETECTOR
        # self.default_detector_nm = "DNM_DEFAULT_COUNTER"

    def init_subscriptions(self, ew, func):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :return:
        """

        if self.is_pxp:
            pass
        else:
            pass

    def stop(self):
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        e712_wdg.stop_wave_generator()

        # call the parents stop
        super().stop()

    def on_scan_done(self):
        """
        when scan is done
        :return:
        """
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        e712_wdg.on_wavegen_scan_done()

    def make_scan_plan(self, dets, gate, md=None, bi_dir=False):
        """
        override the default make_scan_plan to set the scan_type
        :param dets:
        :param gate:
        :param md:
        :param bi_dir:
        :return:
        """
        if self.numImages is 1:
            self.scan_type = scan_types.SAMPLE_IMAGE
            return self.make_single_image_e712_plan(dets, gate, md=md, bi_dir=bi_dir)
        else:
            self.scan_type = scan_types.TOMOGRAPHY
            return self.make_tomo_plan(dets, gate, md=md, bi_dir=bi_dir)

    def get_ev_starting_setpoint(self, e_rois):
        ev_roi = e_rois[0]
        ev_sp = ev_roi[SETPOINTS][0]
        return ev_sp

    def make_tomo_plan(self, dets, gate, md=None, bi_dir=False):
        print("entering: make_tomo_plan")
        stagers = []
        for d in dets:
            stagers.append(d)

        def do_scan():
            # yield from bps.open_run(md)
            ev_mtr = self.main_obj.device("DNM_ENERGY")
            pol_mtr = self.main_obj.device("DNM_EPU_POLARIZATION")
            off_mtr = self.main_obj.device("DNM_EPU_OFFSET")
            ang_mtr = self.main_obj.device("DNM_EPU_ANGLE")
            gx_mtr = self.main_obj.device("DNM_GONI_X")
            gy_mtr = self.main_obj.device("DNM_GONI_Y")
            gz_mtr = self.main_obj.device("DNM_GONI_Z")
            gt_mtr = self.main_obj.device("DNM_GONI_THETA")
            zpz_adjust_posner = self.main_obj.device("DNM_ZONEPLATE_Z_ADJUST")
            print("starting: make_tomo_plan: do_scan()")
            entrys_lst = []

            self.sp_id = 0
            # this updates member vars x_roi, y_roi, etc... with current spatial id specifics
            self.update_roi_member_vars(self.sp_rois[self.sp_id])
            zpz_adjust_vals = dct_get(self.sp_rois[self.sp_id], SPDB_G_ZPZ_ADJUST)

            self._current_img_idx = 0
            entry_idx = 0
            zpz_adjust_idx = 0
            # move goni_t and ev to start (these are the slowest)
            yield from bps.mv(
                gt_mtr,
                self.gt_roi[SETPOINTS][0],
                ev_mtr,
                self.get_ev_starting_setpoint(self.e_rois),
            )

            for gt_idx in range(len(self.gt_roi[SETPOINTS])):

                if zpz_adjust_vals[ENABLED]:
                    # adjust the zonplate Z position for focus based on the user entered data
                    yield from bps.mv(
                        zpz_adjust_posner, zpz_adjust_vals[SETPOINTS][zpz_adjust_idx]
                    )
                    zpz_adjust_idx += 1

                # move goni X,Y,Z,T to there setpoints
                # yield from bps.mv(gt_mtr, self.gt_roi[SETPOINTS][gt_idx], gx_mtr, self.gx_roi[SETPOINTS][gt_idx], \
                #                  gy_mtr, self.gy_roi[SETPOINTS][gt_idx], gz_mtr, self.gz_roi[SETPOINTS][gt_idx])
                yield from bps.mv(gt_mtr, self.gt_roi[SETPOINTS][gt_idx])

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
                        yield from bps.mv(ev_mtr, ev_sp)
                        # self.dwell = ev_roi[DWELL]
                        self.dwell = self.setpointsDwell
                            # take a single image that will be saved with its own run scan id
                            img_dct = self.img_idx_map["%d" % self._current_img_idx]
                            md = {
                                "metadata": dict_to_json(
                                    self.make_standard_metadata(
                                        entry_name=img_dct["entry"],
                                        scan_type=self.scan_type,
                                        dets=dets,
                                    )
                                )
                            }

                            if img_dct["entry"] not in entrys_lst:
                                entrys_lst.append(img_dct["entry"])
                                # only take the baseline once
                                if self.use_hdw_accel:
                                    print(
                                        "Creating new baseline measurement for [%s]"
                                        % img_dct["entry"]
                                    )
                                    yield from self.make_single_image_e712_plan(
                                        dets, gate, md=md, do_baseline=True
                                    )
                                else:
                                    yield from self.make_single_image_plan(
                                        dets, gate, md=md, do_baseline=True
                                    )

                            else:
                                # this data will be used to add to previously created entries
                                if self.use_hdw_accel:
                                    yield from self.make_single_image_e712_plan(
                                        dets, gate, md=md, do_baseline=False
                                    )
                                else:
                                    yield from self.make_single_image_plan(
                                        dets, gate, md=md, do_baseline=False
                                    )

                            self._current_img_idx += 1

                entry_idx += 1

            # print("make_tomo_plan Leaving")

        return (yield from do_scan())

    def on_this_scan_done(self):
        # self.shutter.close()
        # self.gate.stop()
        # self.counter.stop()
        # self.save_hdr()
        # self.on_save_sample_image()
        pass

    def on_scan_done_discon_sigs(self):
        """
        on_scan_done(): fires when the top level scan is done, calls on_child_scan_done() if one has been
        configured by parent scan plugin

        :returns: None
        """

        if self.signals_connected:
            # _logger.debug('BaseScan: on_scan_done_discon_sigs: emitted all_done sig')
            self.all_done.emit()
        else:
            _logger.debug(
                "BaseScan: on_scan_done_discon_sigs: ELSE: sigs were not connected"
            )
        # if(done):
        self.disconnect_signals()

    def configure(
        self, wdg_com, sp_id=0, ev_idx=0, line=True, block_disconnect_emit=False
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
        ret = super().configure(wdg_com, sp_id=sp_id, line=line, z_enabled=False)
        if not ret:
            return(ret)

        _logger.info(
            "\n\nTomographyWithE712WavegenScanClass: configuring sp_id [%d]" % sp_id
        )
        self.new_spatial_start_sent = False
        # initial setup and retrieval of common scan information
        self.set_spatial_id(sp_id)
        # self.wdg_com = wdg_com
        # self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        # self.sp_ids = list(self.sp_rois.keys())
        # self.sp_id = sp_id
        # self.sp_db = self.sp_rois[sp_id]
        # self.scan_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_TYPE)
        # self.scan_sub_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)
        # self.sample_positioning_mode = MAIN_OBJ.get_sample_positioning_mode()
        # self.sample_fine_positioning_mode = MAIN_OBJ.get_fine_sample_positioning_mode()
        #
        # self.update_roi_member_vars(self.sp_db)
        #
        # #the wavegenerator does both axis in one sscan record by calling the wavegenerator to execute,
        # # this is done in sscan2
        # # self.xyScan = self._scan2
        #
        # self.determine_scan_res()

        # dct_put(self.sp_db, SPDB_RECT, (self.x_roi[START], self.y_roi[START], self.x_roi[STOP], self.y_roi[STOP]))
        # the sample motors have different modes, make a call to handle that they are setup correctly for this scan
        #        self.configure_sample_motors_for_scan()

        if ev_idx == 0:
            self.reset_evidx()
            self.reset_imgidx()
            self.reset_pnt_spec_spid_idx()
            self.final_data_dir = None
            self.update_dev_data = []

        if len(self.sp_ids) > 1:
            self.is_multi_spatial = True
            # if multi spatial then just save everything without prompting
            self.set_save_all_data(True)
        else:
            self.is_multi_spatial = False
            self.set_save_all_data(False)

        # get the energy and EOU related setpoints
        e_roi = self.e_rois[ev_idx]
        self.setpointsDwell = dct_get(e_roi, DWELL)
        # self.setpointsPol = self.convert_polarity_points(dct_get(e_roi, 'EPU_POL_PNTS'))
        self.setpointsPol = dct_get(e_roi, EPU_POL_PNTS)
        self.setpointsOff = dct_get(e_roi, EPU_OFF_PNTS)
        self.setpointsAngle = dct_get(e_roi, EPU_ANG_PNTS)
        self.ev_pol_order = dct_get(e_roi, EV_POL_ORDER)

        # sps = dct_get(self.wdg_com, SPDB_SINGLE_LST_SP_ROIS)
        # evs = dct_get(self.wdg_com, SPDB_SINGLE_LST_EV_ROIS)
        # pols = dct_get(self.wdg_com, SPDB_SINGLE_LST_POL_ROIS)
        # dwells = dct_get(self.wdg_com, SPDB_SINGLE_LST_DWELLS)
        # sub_type = dct_get(self.wdg_com, SPDB_SCAN_PLUGIN_SUBTYPE)

        # self.is_lxl = False
        # self.is_pxp = False
        # self.is_point_spec = False
        # self.file_saved = False
        # self.sim_point = 0
        #
        # if(sub_type is scan_sub_types.POINT_BY_POINT):
        #     self.is_pxp = True
        #     self.is_lxl = False
        # else:
        #     self.is_pxp = False
        #     self.is_lxl = True
        #
        # self.use_hdw_accel = dct_get(self.sp_db, SPDB_HDW_ACCEL_USE)
        # if (self.use_hdw_accel is None):
        #     self.use_hdw_accel = True
        #     if (dct_get(self.sp_db, SPDB_HDW_ACCEL_AUTO_DDL)):
        #         self.x_auto_ddl = True
        #         self.x_use_reinit_ddl = False
        #     else:
        #         # Reinit DDL for the current scan
        #         self.x_auto_ddl = False
        #         self.x_use_reinit_ddl = True
        #
        # self.is_fine_scan = True
        #
        # # setup some convienience member variables
        # self.dwell = e_roi[DWELL]
        # self.numX = int(self.x_roi[NPOINTS])
        # self.numY = int(self.y_roi[NPOINTS])
        # self.numZX = int(self.zx_roi[NPOINTS])
        # self.numZY = int(self.zy_roi[NPOINTS])
        # self.numEPU = len(self.setpointsPol)
        # self.numE = int(self.sp_db[SPDB_EV_NPOINTS])
        #
        # self.numSPIDS = len(self.sp_rois)

        if self.scan_type != scan_types.SAMPLE_POINT_SPECTRUM:
            self.numImages = int(
                self.sp_db[SPDB_EV_NPOINTS] * self.numEPU * self.numSPIDS
            )
        else:
            # is a sample point spectrum
            self.numImages = 1

        # set some flags that are used elsewhere
        if self.numImages > 1:
            self.stack = True
            self.save_all_data = True
        else:
            self.stack = False

        # if (self.sample_positioning_mode == sample_positioning_modes.GONIOMETER):
        if self.fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE:
            self.is_zp_scan = True
        else:
            self.is_zp_scan = False
            # determine and setup for line or point by point

        self.ttl_pnts = 0

        # depending on the scan size the positioners used in the scan will be different, use a singe
        # function to find out which we are to use and return those names in a dct
        dct = self.determine_samplexy_posner_pvs(force_fine_scan=True)

        # depending on the current samplpositioning_mode perform a different configuration
        if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            self.seq_map_dct = self.generate_2d_seq_image_map(
                self.numE, self.numEPU, self.zy_roi[NPOINTS], self.zx_roi[NPOINTS], lxl=self.is_lxl
            )
            if self.use_hdw_accel:
                self.config_for_goniometer_scan_hdw_accel(dct)
            else:
                self.config_for_goniometer_scan(dct)

        else:
            if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
                self.seq_map_dct = self.generate_2d_seq_image_map(
                    self.numE,
                    self.numEPU,
                    self.zy_roi[NPOINTS],
                    self.zx_roi[NPOINTS],
                    lxl=self.is_lxl,
                )
                # goniometer_zoneplate mode
                self.configure_for_zxzy_fine_scan_hdw_accel(dct)
            elif (self.sample_positioning_mode == sample_positioning_modes.COARSE) and (
                self.fine_sample_positioning_mode
                == sample_fine_positioning_modes.ZONEPLATE
            ):
                self.seq_map_dct = self.generate_2d_seq_image_map(
                    self.numE,  self.numEPU, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=self.is_lxl
                )
                self.configure_for_coarse_zoneplate_fine_scan_hdw_accel(dct)
            else:
                # coarse_samplefine mode
                self.seq_map_dct = self.generate_2d_seq_image_map(
                    self.numE,  self.numEPU, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=self.is_lxl
                )
                self.configure_for_samplefxfy_fine_scan_hdw_accel(dct)

        self.final_data_dir = self.config_hdr_datarecorder(
            self.stack, self.final_data_dir
        )
        # self.stack_scan = stack

        # redo the img_idx_map for tomography, this is the sequential image to data dimension map
        # recall that teh data is organized:
        # data[Counter_name][Spatial_id][Polarization][energy_idx][y][x]
        #
        # this img_idx_map is used in teh on_counter_changed handler to put the data in the correct array
        self.img_idx_map = {}
        indiv_img_idx = 0
        spid = list(self.sp_rois.keys())[0]
        offset = 0
        for gt_sp in self.gt_roi[SETPOINTS]:
            for i in range(self.numE):
                for pol in range(self.numEPU):
                    self.img_idx_map["%d" % indiv_img_idx] = {
                        "e_idx": i,
                        "pol_idx": pol,
                        "sp_idx": 0,
                        "sp_id": spid,
                        "entry": "entry%d" % (pol + offset),
                        "rotation_angle": gt_sp,
                    }
                    indiv_img_idx += 1
            if self.numEPU is 1:
                offset += 1
            else:
                offset += 2

        # make sure OSA XY is in its center
        self.move_osaxy_to_its_center()

        self.seq_map_dct = self.generate_2d_seq_image_map(
            self.numE, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=self.is_lxl
        )
        # THIS must be the last call
        self.finish_setup()

        self.new_spatial_start.emit(sp_id)
        return(ret)

    def configure_for_coarse_scan(self, dct):
        """
        if this is executed the assumption is that the zoneplate will be stationary and the Fx Fy stages will be off
        because the scan will be accomplished by moving the sample with the coarse motors only
        :return:
        """
        self.xScan = self._scan1
        self.yScan = self._scan2
        self.xyScan = None
        self.config_for_sample_holder_scan(dct)

    def configure_for_zxzy_fine_scan_hdw_accel(self, dct, is_focus=False):
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

        self.set_config_devices_func(self.on_this_dev_cfg)

        self.sample_mtrx = self.sample_finex = self.main_obj.device("DNM_ZONEPLATE_X")
        self.sample_mtry = self.sample_finey = self.main_obj.device("DNM_ZONEPLATE_Y")

        # move Gx and Gy to center of scan, is it within a um?
        if self.zx_roi[CENTER] != 0.0:
            # zx is moving to scan center
            pass
        else:
            # Gx is moving to scan center nd zx is centered around 0, so move Gx to scan center
            self.main_obj.device(dct["cx_name"]).put(
                "user_setpoint", self.gx_roi[CENTER]
            )

        # if(self.is_within_dband( gy_mtr.get_position(), self.gy_roi[CENTER], 15.0)):
        if self.zy_roi[CENTER] != 0.0:
            # zy is moving to scan center
            pass
        else:
            # Gy is moving to scan center nd zy is centered around 0, so move Gy to scan center
            self.main_obj.device(dct["cy_name"]).put(
                "user_setpoint", self.gy_roi[CENTER]
            )

        # config the sscan that makes sure to move goni xy and osa xy to the correct position for scan
        # the setupScan will be executed as the top level but not monitored
        self.num_points = self.numY

        self.sample_mtrx.put("Mode", 0)

        # setup the E712 wavtable's and other relevant params
        self.modify_config_for_hdw_accel()

    def configure_for_samplefxfy_fine_scan_hdw_accel(self, dct):
        """
        if this is executed the assumption is that the the scan will be a sampleFx Fy fine scan, it should make sure the
        SampleX and SampleY stages are in their start positions the wavegen tables and set the starting offset (which
        will be the big difference)
        :return:
        """
        """
                For a fine scan this will always be a scan of max range 100x100um (actually less)
                and the sequence to configure a scan is to position the goniometer at teh center of the scan everytime
                and set the +/- scan range to be about Fine XY center (0,0)

                Need to take into account that this could be a LxL scan (uses xScan, yScan, zScan) or a PxP (uses xyScan, zScan)

                Because this scan uses the waveform generator on the E712 there are no positioners set for X and Y scan only the
                triggering of the waveform generator.

                """
        ### VERY IMPORTANT the current PID tune for ZX is based on a velo (SLew Rate) of 1,000,000
        # must be FxFy
        self.main_obj.get_sample_fine_positioner("X").set_power(1)
        self.main_obj.get_sample_fine_positioner("Y").set_power(1)

        self.main_obj.get_sample_fine_positioner("X").set_velo(100000.0)
        self.main_obj.get_sample_fine_positioner("Y").set_velo(100000.0)

        # this scan is used with and without the goniometer so setupScan maybe None
        # if(self.setupScan):
        #     self.setupScan.set_positioner(1, self.main_obj.device('DNM_SAMPLE_X))
        #     self.setupScan.set_positioner(2, self.main_obj.device('DNM_SAMPLE_Y))

        # these are the SampleX SampleY motors
        cx_mtr = self.main_obj.device(dct["cx_name"])
        cy_mtr = self.main_obj.device(dct["cy_name"])

        cx_mtr.put("Mode", 0)  # MODE_NORMAL
        cy_mtr.put("Mode", 0)  # MODE_NORMAL

        self.set_config_devices_func(self.on_this_dev_cfg)
        self.sample_mtrx = self.sample_finex = self.main_obj.get_sample_fine_positioner("X")
        self.sample_mtry = self.sample_finey = self.main_obj.get_sample_fine_positioner("Y")

        # move Gx and Gy to center of scan, is it within a um?
        # Sx is moving to scan center nd fx is centered around 0, so move Sx to scan center
        cx_mtr.move(self.x_roi[CENTER])
        self.sample_finex.put("user_setpoint", self.x_roi[CENTER])
        # self.main_obj.device(dct['cx_name']).put('user_setpoint', self.x_roi[CENTER])

        # if(self.is_within_dband( gy_mtr.get_position(), self.gy_roi[CENTER], 15.0)):
        # Sy is moving to scan center nd fy is centered around 0, so move Sy to scan center
        # self.main_obj.device(dct['cy_name']).put('user_setpoint', self.gy_roi[CENTER])
        cy_mtr.move(self.y_roi[CENTER])

        # config the sscan that makes sure to move goni xy and osa xy to the correct position for scan
        # the setupScan will be executed as the top level but not monitored
        self.num_points = self.numY

        # setup the E712 wavtable's and other relevant params
        self.modify_config_for_hdw_accel()

    def configure_for_coarse_zoneplate_fine_scan_hdw_accel(self, dct):
        """
        if this is executed the assumption is that the the scan will be a sampleFx Fy fine scan, it should make sure the
        SampleX and SampleY stages are in their start positions the wavegen tables and set the starting offset (which
        will be the big difference)
        :return:
        """
        """
                For a fine scan this will always be a scan of max range 100x100um (actually less)
                and the sequence to configure a scan is to position the goniometer at teh center of the scan everytime
                and set the +/- scan range to be about Fine XY center (0,0)

                Need to take into account that this could be a LxL scan (uses xScan, yScan, zScan) or a PxP (uses xyScan, zScan)

                Because this scan uses the waveform generator on the E712 there are no positioners set for X and Y scan only the
                triggering of the waveform generator.

                """
        ### VERY IMPORTANT the current PID tune for ZX is based on a velo (SLew Rate) of 1,000,000
        # must be FxFy
        self.main_obj.device("DNM_ZONEPLATE_X").set_power(1)
        self.main_obj.device("DNM_ZONEPLATE_Y").set_power(1)

        self.main_obj.device("DNM_ZONEPLATE_X").set_velo(1000000.0)
        self.main_obj.device("DNM_ZONEPLATE_Y").set_velo(1000000.0)

        # this scan is used with and without the goniometer so setupScan maybe None
        # if(self.setupScan):
        #     self.setupScan.set_positioner(1, self.main_obj.device('DNM_SAMPLE_X))
        #     self.setupScan.set_positioner(2, self.main_obj.device('DNM_SAMPLE_Y))

        # these are the SampleX SampleY motors
        # cx_mtr = self.main_obj.device(dct['cx_name'])
        # cy_mtr = self.main_obj.device(dct['cy_name'])

        # cx_mtr.put('Mode', 0)  # MODE_NORMAL
        # cy_mtr.put('Mode', 0)  # MODE_NORMAL

        self.set_config_devices_func(self.on_this_dev_cfg)
        self.sample_mtrx = self.sample_finex = self.main_obj.device("DNM_SAMPLE_X")
        self.sample_mtry = self.sample_finey = self.main_obj.device("DNM_SAMPLE_Y")

        self.sample_mtrx.put("Mode", 0)  # MODE_NORMAL
        self.sample_mtry.put("Mode", 0)  # MODE_NORMAL

        # Sx is moving to scan center nd fx is centered around 0, so move Sx to scan center
        # cx_mtr.move(self.x_roi[CENTER])
        # self.sample_finex.put('user_setpoint', self.x_roi[CENTER])
        # self.sample_mtrx.put('user_setpoint', self.x_roi[CENTER])
        self.sample_mtrx.put("user_setpoint", self.x_roi[START])

        # cy_mtr.move(self.y_roi[CENTER])
        # self.sample_mtry.put('user_setpoint', self.y_roi[CENTER])
        self.sample_mtry.put("user_setpoint", self.y_roi[START])

        # config the sscan that makes sure to move goni xy and osa xy to the correct position for scan
        # the setupScan will be executed as the top level but not monitored
        self.num_points = self.numY

        # setup the E712 wavtable's and other relevant params
        self.modify_config_for_hdw_accel()

    # def config_for_goniometer_scan_hdw_accel(self, dct, is_focus=False):
    #     """
    #     For a goniometer scan this will always be a fine scan of max range 100x100um (actually less)
    #     and the sequence to configure a scan is to position the goniometer at teh center of the scan everytime
    #     and set the +/- scan range to be about Zoneplate XY center (0,0)
    #
    #     Need to take into account that this could be a LxL scan (uses xScan, yScan, zScan) or a PxP (uses xyScan, zScan)
    #
    #     Because this scan uses the waveform generator on the E712 there are no positioners set for X and Y scan only the
    #     triggering of the waveform generator, will still need to do something so that save_hdr has something to get data
    #     from, not sure how to handle this yet.
    #
    #     """
    #     ### VERY IMPORTANT the current PID tune for ZX is based on a velo (SLew Rate) of 1,000,000
    #     self.main_obj.device('DNM_ZONEPLATE_X).set_velo(1000000.0)
    #     self.main_obj.device('DNM_ZONEPLATE_Y).set_velo(1000000.0)
    #     #
    #     # gx_mtr = self.main_obj.device(dct['cx_name'])
    #     # gy_mtr = self.main_obj.device(dct['cy_name'])
    #     #
    #     # self.set_config_devices_func(self.on_this_dev_cfg)
    #     #
    #     self.sample_mtrx = self.sample_finex = self.main_obj.device('DNM_ZONEPLATE_X)
    #     self.sample_mtry = self.sample_finey = self.main_obj.device('DNM_ZONEPLATE_Y)
    #     #
    #     # move Gx and Gy to center of scan, is it within a um?
    #     if (self.zx_roi[CENTER] != 0.0):
    #         # zx is moving to scan center
    #         pass
    #     else:
    #         # Gx is moving to scan center nd zx is centered around 0, so move Gx to scan center
    #         self.main_obj.device(dct['cx_name']).put('user_setpoint', self.gx_roi[CENTER])
    #
    #     # if(self.is_within_dband( gy_mtr.get_position(), self.gy_roi[CENTER], 15.0)):
    #     if (self.zy_roi[CENTER] != 0.0):
    #         # zy is moving to scan center
    #         pass
    #     else:
    #         # Gy is moving to scan center nd zy is centered around 0, so move Gy to scan center
    #         self.main_obj.device(dct['cy_name']).put('user_setpoint', self.gy_roi[CENTER])
    #     #
    #     self.num_points = self.numY
    #
    #     self.sample_mtrx.put('Mode', 0)
    #
    #     #setup the E712 wavtable's and other relevant params, because tomo is always only a single spatial but many
    #     # theta angles only send the one spatial to the hdw config
    #     sp_id = list(self.sp_rois.keys())[0]
    #     self.modify_config_for_hdw_accel(sp_rois={sp_id: self.sp_rois[sp_id]} )


#     def on_sample_scan_counter_changed_hdw_accel(self, row, data, counter_name='counter0'):
#         """
#         on_sample_scan_counter_changed_hdw_accel(): Used by SampleImageWithEnergySSCAN
#
#         :param row: row description
#         :type row: row type
#
#         :param data: data description
#         :type data: data type
#
#         :returns: None
#         """
#         """
#         The on counter_changed slot will take data cquired by line and point scans but it must treat each differently.
#         The point scan still arrives as a one demensiotnal array but there are only 3 elements, data[row, point, value].
#         The point scan has been programmed to acquire num_x_points + 1 so that the counter can increment the row value, thus this
#         slot during a point scan will receive a point+1 and in that case it should be ignored.
#
#         LIne scan data arrives in the form data[row, < number of x points of values >]
#
#         This slot has to handle
#
#         """
#
#         if(row < 0):
#             row = 0
#
#         sp_id =  int(MAIN_OBJ.device('DNM_E712_CURRENT_SP_ID').get_position())
#         self.set_spatial_id(sp_id)
#
#         if ((self.scan_type == scan_types.OSA_FOCUS) or (self.scan_type == scan_types.SAMPLE_FOCUS)):
#             nptsy = self.numZ
#         else:
#             nptsy = self.numY
#
#         _evidx = self.get_evidx()
#         _imgidx = MAIN_OBJ.device('DNM_E712_IMAGE_IDX').get_position()
#         #print 'on_sample_scan_counter_changed_hdw_accel: _imgidx=%d row=%d' % (_imgidx, row)
#
#         if (self.is_pxp and (not self.use_hdw_accel)):
#             # Image point by point
#             point = int(data[0])
#             val = data[1]
#
#             # print 'SampleImageWithEnergySSCAN: on_counter_changed: _imgidx=%d row=%d point=%d, data = %d' % (_imgidx, row, point, val)
#             self.data[_imgidx, row, point] = val
#         elif (self.is_pxp and self.use_hdw_accel):
#             point = 0
#             (wd,) = data.shape
#             #print data
#             val = data[0:wd]
#         else:
#             # print 'SampleImageWithEnergySSCAN: LXL on_counter_changed: _imgidx, row and data[0:10]=', (_imgidx, row, data[0:10])
#             point = 0
#             (wd,) = data.shape
#             val = data[0:(wd - 1)]
#
#         dct = self.init_counter_to_plotter_com_dct(make_counter_to_plotter_com_dct())
#         dct[CNTR2PLOT_ROW] = int(row)
#         dct[CNTR2PLOT_COL] = int(point)
#         dct[CNTR2PLOT_VAL] = val
#         #because we could be multi spatial override the default
#         dct[CNTR2PLOT_SP_ID] = sp_id
#
#         _dct = self.get_img_idx_map(_imgidx)
#         _sp_id = _dct['sp_id']
#         pol_idx = _dct['pol_idx']
#         e_idx = _dct['e_idx']
#
#         #print 'on_sample_scan_counter_changed_hdw_accel: counter_name=[%s] _imgidx=%d, sp_id=%d' % (counter_name, _imgidx, _sp_id)
#         #print 'self.img_data[0].shape',self.img_data[_sp_id].shape
#         #print 'val.shape', val.shape
#         img_ht, img_wd = self.img_data[_sp_id].shape
#         row_wd, = val.shape
#
#         if(img_wd == row_wd):
#             self.img_data[_sp_id][int(row), :] = val
#             self.spid_data[counter_name][sp_id][pol_idx][e_idx, int(row), :] = val
#             self.sigs.changed.emit(dct)
#
#         #now emit progress information
#         prog = float(float(row + 0.75) / float(img_ht)) * 100.0
#         if (self.stack):
#             prog_dct = make_progress_dict(sp_id=sp_id, percent=prog, cur_img_idx=_imgidx)
#         else:
#             prog_dct = make_progress_dict(sp_id=sp_id, percent=prog, cur_img_idx=_imgidx)
#
#         self.low_level_progress.emit(prog_dct)
#
#
#     def on_coarse_sample_scan_counter_changed(self, row, data, counter_name='counter0'):
#         """
#         on_sample_scan_counter_changed_hdw_accel(): Used by SampleImageWithEnergySSCAN
#
#         :param row: row description
#         :type row: row type
#
#         :param data: data description
#         :type data: data type
#
#         :returns: None
#         """
#         """
#         The on counter_changed slot will take data acquired by line and point scans but it must treat each differently.
#         The point scan still arrives as a one demensiotnal array but there are only 3 elements, data[row, point, value].
#         The point scan has been programmed to acquire num_x_points + 1 so that the counter can increment the row value, thus this
#         slot during a point scan will receive a point+1 and in that case it should be ignored.
#
#         LIne scan data arrives in the form data[row, < number of x points of values >]
#
#         This slot has to handle
#
#         """
#
#         if(row < 0):
#             print()
#             row = 0
#
#         sp_id =  int(MAIN_OBJ.device('DNM_E712_CURRENT_SP_ID').get_position())
#         self.set_spatial_id(sp_id)
#
#         if ((self.scan_type == scan_types.OSA_FOCUS) or (self.scan_type == scan_types.SAMPLE_FOCUS)):
#             nptsy = self.numZ
#         else:
#             nptsy = self.numY
#
#         _evidx = self.get_evidx()
#         #_imgidx = MAIN_OBJ.device('DNM_E712_IMAGE_IDX').get_position()
#         _imgidx = self.base_zero(self.get_imgidx())
#         _dct = self.get_img_idx_map(_imgidx)
#         _sp_id = _dct['sp_id']
#         pol_idx = _dct['pol_idx']
#         e_idx = _dct['e_idx']
#
#         #set the spatial id so that save_hdr can use it
#         self.set_spatial_id(_sp_id)
#         #print 'on_sample_scan_counter_changed_hdw_accel: _imgidx=%d row=%d' % (_imgidx, row)
#
#         if (self.is_pxp and (not self.use_hdw_accel)):
#             # Image point by point
#             point = int(data[0])
#             val = data[1]
#
#             # print 'SampleImageWithEnergySSCAN: on_counter_changed: _imgidx=%d row=%d point=%d, data = %d' % (_imgidx, row, point, val)
#             self.data[_imgidx, row, point] = val
#
#         else:
#             # print 'SampleImageWithEnergySSCAN: LXL on_counter_changed: _imgidx, row and data[0:10]=', (_imgidx, row, data[0:10])
#             point = 0
#             (wd,) = data.shape
#             val = data[0:(wd - 1)]
#
#         dct = self.init_counter_to_plotter_com_dct(make_counter_to_plotter_com_dct())
#         dct[CNTR2PLOT_ROW] = int(row)
#         dct[CNTR2PLOT_COL] = int(point)
#         dct[CNTR2PLOT_VAL] = val
#         #because we could be multi spatial override the default
#         dct[CNTR2PLOT_SP_ID] = _sp_id
#
#         self.img_data[_sp_id][int(row), :] = val
#
#         #print 'self.spid_data[%s][%d][%d][%d, %d, :]' % (counter_name,_sp_id,pol_idx,e_idx, int(row))
#         self.spid_data[counter_name][_sp_id][pol_idx][e_idx, int(row), :] = val
#         self.sigs.changed.emit(dct)
#
#         #now emit progress information
#         prog = float(float(row + 0.75) / float(nptsy)) * 100.0
#         if (self.stack):
#             prog_dct = make_progress_dict(sp_id=_sp_id, percent=prog)
#         else:
#             prog_dct = make_progress_dict(sp_id=_sp_id, percent=prog)
#
#         self.low_level_progress.emit(prog_dct)
#
#     def hdw_accel_save_hdr(self, update=False, do_check=True):
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
#         GUI wait until it is finished, that seems reasonable for the user to wait a couple secondsù
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
#         if (update):
#             _logger.info('Skipping save_hdr() update = True')
#             return
#         upside_dwn_scans = [scan_types.SAMPLE_LINE_SPECTRUM, scan_types.SAMPLE_IMAGE]
#         # _logger.info('save_hdr: starting')
#         if (self.is_point_spec):
#             self.save_point_spec_hdr(update)
#             return
#
#
#
#         # self.gate.stop()
#         # self.counter.stop()
#         self.data_obj.set_scan_end_time()
#
#         # self.main_obj.update_zmq_posner_snapshot()
#         # self.main_obj.update_zmq_detector_snapshot()
#         # self.main_obj.update_zmq_pv_snapshot()
#         upd_list = []
#         for s in self.scanlist:
#             upd_list.append(s.get_name())
#         # self.main_obj.update_zmq_sscan_snapshot(upd_list)
#
#         _ev_idx = self.get_evidx()
#         _img_idx = self.get_imgidx() - 1
#         _spatial_roi_idx = self.get_spatial_id()
#         sp_db = self.sp_rois[_spatial_roi_idx]
#         sample_pos = 1
#
#         # data_name_dct = master_get_seq_names(datadir, prefix_char=data_file_prfx, thumb_ext=thumb_file_sffx, dat_ext='hdf5', stack_dir=self.stack)
#         # hack
#         if (_img_idx < 0):
#             _img_idx = 0
#         self.data_dct = self.data_obj.get_data_dct()
#
#         ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
#         #        data_file_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
#         #        thumb_file_ext = dct_get(ado_obj, ADO_CFG_THUMB_EXT)
#         datadir = dct_get(ado_obj, ADO_CFG_DATA_DIR)
#         datafile_name = dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME)
#         datafile_prfx = dct_get(ado_obj, ADO_CFG_PREFIX)
#         #        thumb_name = dct_get(ado_obj, ADO_CFG_DATA_THUMB_NAME)
#         stack_dir = dct_get(ado_obj, ADO_CFG_STACK_DIR)
#
# #        if (not update):
# #            if (not self.check_if_save_all_data(datafile_name)):
# #                return
#         if(self.use_hdw_accel):
#             if (self.e712_wg.save_this_ddl()):
#                 self.e712_wg.get_ddl_table(X_WAVE_TABLE_ID, cb=self.e712_wg.save_ddl_data)
#
#         self.saving_data.emit('Saving...')
#
#         if (self.stack):
#             datadir = stack_dir
#
#         # alldata = self.main_obj.get_zmq_sscan_snapshot(upd_list)
#         for scan in self.scanlist:
#             sname = scan.get_name()
#             #    #ask each scan to get its data and store it in scan.scan_data
#             if (scan.section_name == SPDB_XY):
#                 # this is a sscan where P1 is X and P2 is Y, separate them such that they look like two separate scans
#                 # alldata = self.take_sscan_snapshot(scan.name)
#
#                 if(self.use_hdw_accel):
#                     alldata = {}
#                     alldata['P1RA'] = self.x_roi[SETPOINTS]
#                     alldata['P2RA'] = self.y_roi[SETPOINTS]
#                     alldata['NPTS'] = self.x_roi[NPOINTS]
#                     alldata['CPT'] = self.x_roi[NPOINTS]
#                     p1data = alldata['P1RA']
#                     npts = alldata['NPTS']
#                     cpt = alldata['CPT']
#                     p2data = alldata['P2RA']
#                 else:
#                     alldata = scan.get_all_data()
#                     p1data = alldata['P1RA']
#                     npts = alldata['NPTS']
#                     cpt = alldata['CPT']
#                     p2data = alldata['P2RA']
#                     dct_put(self.data_dct, 'DATA.SSCANS.XY', alldata)
#
#                 dct_put(self.data_dct, 'DATA.SSCANS.XY', alldata)
#                 dct_put(self.data_dct, 'DATA.SSCANS.X', {'P1RA': p1data, 'NPTS': npts, 'CPT': cpt})
#                 dct_put(self.data_dct, 'DATA.SSCANS.Y', {'P1RA': p2data, 'NPTS': npts, 'CPT': cpt})
#             else:
#                 all_data = scan.get_all_data()
#                 if (self.use_hdw_accel and (scan.section_name == (SPDB_X or SPDB_Y))):
#                     # there will not be any P1RA key in all_data because there are no positioners specified so
#                     # the data must be generated for X and Y in
#                     p1data = np.linspace(self.x_roi[START], self.x_roi[STOP], self.x_roi[NPOINTS])
#                     p2data = np.linspace(self.y_roi[START], self.y_roi[STOP], self.y_roi[NPOINTS])
#                     all_data['P1RA'] = p1data
#                     all_data['P2RA'] = p2data
#                     xnpts = self.x_roi[NPOINTS]
#                     ynpts = self.y_roi[NPOINTS]
#                     xcpt = xnpts
#                     ycpt = ynpts
#                     all_data['NPTS'] = self.x_roi[NPOINTS]
#                     all_data['CPT'] = self.x_roi[NPOINTS]
#                     dct_put(self.data_dct, 'DATA.SSCANS.XY', all_data)
#                     dct_put(self.data_dct, 'DATA.SSCANS.X', {'P1RA': p1data, 'NPTS': xnpts, 'CPT': xcpt})
#                     dct_put(self.data_dct, 'DATA.SSCANS.Y', {'P1RA': p2data, 'NPTS': ynpts, 'CPT': ycpt})
#                 else:
#                     dct_put(self.data_dct, 'DATA.SSCANS.' + scan.section_name, scan.get_all_data())
#                     # dct_put(self.data_dct,'DATA.SSCANS.' + scan.section_name, alldata[sname])
#
#         # if (self.scan_type in upside_dwn_scans and not update):
#         #     # the data for these scans needs to be flipped upside down, but because this function is called multiple times
#         #     #depending on where the scan is at we need to make sure we are only flipping the data 1 time, so here
#         #     #we are doing it at the end (the last time it is called) when update is False
#         #     _data = self.flip_data_upsdown(self.data[_img_idx - 1])
#         #     self.data[_img_idx - 1] = np.copy(_data)
#         #
#         # elif(self.scan_type is scan_types.SAMPLE_IMAGE_STACK and not update):
#         #     #stack scan save individual images during an update, so flip during an update for a stack scan
#         #     #but then the issue is the very last image because it will get flipped multiple times
#         #     _data = self.flip_data_upsdown(self.data[_img_idx - 1])
#         #     self.data[_img_idx - 1] = np.copy(_data)
#         #
#         # elif (self.scan_type is scan_types.SAMPLE_IMAGE_STACK and update):
#         #     # stack scan save individual images during an update, so flip during an update for a stack scan
#         #     # but then the issue is the very last image because it will get flipped multiple times
#         #     _data = self.flip_data_upsdown(self.data[_img_idx - 1])
#         #     self.data[_img_idx - 1] = np.copy(_data)
#
#         # _logger.info('grabbing devices snapshot')
#         devices = self.main_obj.get_devices()
#
#         # get the current spatial roi and put it in the dct as a dict with its sp_id as the key
#         _wdgcom = {}
#         dct_put(_wdgcom, WDGCOM_CMND, self.wdg_com[CMND])
#         _sprois = {}
#         _sprois[_spatial_roi_idx] = self.wdg_com['SPATIAL_ROIS'][_spatial_roi_idx]
#         dct_put(_wdgcom, SPDB_SPATIAL_ROIS, _sprois)
#         dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
#
#         testing_polarity_entries = False
#         if (testing_polarity_entries):
#             t_dct = {}
#
#             dct_put(t_dct, 'POSITIONERS', self.take_positioner_snapshot(devices['POSITIONERS']))
#             dct_put(t_dct, 'DETECTORS', self.take_detectors_snapshot(devices['DETECTORS']))
#             dct_put(t_dct, 'TEMPERATURES', self.take_temps_snapshot(devices['TEMPERATURES']))
#             dct_put(t_dct, 'PRESSURES', self.take_pressures_snapshot(devices['PRESSURES']))
#             dct_put(t_dct, 'PVS', self.take_pvs_snapshot(devices['PVS']))
#             # _logger.info('DONE grabbing devices snapshot')
#             # dct_put(t_dct, ADO_CFG_WDG_COM, self.wdg_com)
#             dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
#
#             dct_put(t_dct, ADO_CFG_SCAN_TYPE, self.scan_type)
#             dct_put(t_dct, ADO_CFG_CUR_EV_IDX, _ev_idx)
#             dct_put(t_dct, ADO_CFG_CUR_SPATIAL_ROI_IDX, _spatial_roi_idx)
#             dct_put(t_dct, ADO_CFG_CUR_SAMPLE_POS, sample_pos)
#             dct_put(t_dct, ADO_CFG_CUR_SEQ_NUM, 0)
#             dct_put(t_dct, ADO_CFG_DATA_DIR, datadir)
#             dct_put(t_dct, ADO_CFG_DATA_FILE_NAME, datafile_prfx)
#             dct_put(t_dct, ADO_CFG_UNIQUEID, datafile_prfx)
#             dct_put(t_dct, ADO_CFG_X, self.x_roi)
#             dct_put(t_dct, ADO_CFG_Y, self.y_roi)
#             dct_put(t_dct, ADO_CFG_Z, self.z_roi)
#             dct_put(t_dct, ADO_CFG_EV_ROIS, self.e_rois)
#             dct_put(t_dct, ADO_DATA_POINTS, self.data)
#             #dct_put(t_dct, ADO_CFG_IMG_IDX_MAP, self.img_idx_map)
#
#             images_data = np.zeros((self.numEPU, self.numE, self.numY, self.numX))
#             image_idxs = []
#             for i in range(self.numEPU):
#                 image_idxs.append(np.arange(i, self.numImages, self.numEPU))
#
#             # for idxs in image_idxs:
#             for i in range(self.numEPU):
#                 idxs = image_idxs[i]
#                 y = 0
#                 for j in idxs:
#                     images_data[i][y] = self.data[j]
#                     y += 1
#
#             new_e_rois = self.turn_e_rois_into_polarity_centric_e_rois(self.e_rois)
#             pol_rois = []
#             for e_roi in self.e_rois:
#                 for pol in range(self.numEPU):
#                     pol_rois.append(e_roi['POL_ROIS'][pol])
#
#             for pol in range(self.numEPU):
#                 self.data_dct['entry_%d' % pol] = copy.deepcopy(t_dct)
#                 dct_put(self.data_dct['entry_%d' % pol], ADO_DATA_POINTS, copy.deepcopy(images_data[pol]))
#                 dct_put(self.data_dct['entry_%d' % pol], ADO_DATA_SSCANS,
#                         copy.deepcopy(self.data_dct['DATA']['SSCANS']))
#                 dct_put(self.data_dct['entry_%d' % pol], ADO_CFG_EV_ROIS, [new_e_rois[pol]])
#         else:
#
#             if ((self.data_dct['TIME'] != None) and update):
#                 # we already have already set these and its not the end of the scan sp skip
#                 pass
#             else:
#                 dct_put(self.data_dct, 'TIME', make_timestamp_now())
#                 dct_put(self.data_dct, 'POSITIONERS', self.take_positioner_snapshot(devices['POSITIONERS']))
#                 dct_put(self.data_dct, 'DETECTORS', self.take_detectors_snapshot(devices['DETECTORS']))
#                 dct_put(self.data_dct, 'TEMPERATURES', self.take_temps_snapshot(devices['TEMPERATURES']))
#                 dct_put(self.data_dct, 'PRESSURES', self.take_pressures_snapshot(devices['PRESSURES']))
#                 dct_put(self.data_dct, 'PVS', self.take_pvs_snapshot(devices['PVS']))
#
#             # _logger.info('DONE grabbing devices snapshot')
#             # dct_put(self.data_dct, ADO_CFG_WDG_COM, self.wdg_com)
#             dct_put(self.data_dct, ADO_CFG_WDG_COM, _wdgcom)
#
#             if (update):
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
#             #dct_put(self.data_dct, ADO_DATA_POINTS, self.data)
#             #dct_put(self.data_dct, ADO_CFG_IMG_IDX_MAP, self.img_idx_map)
#
#             cur_idx = self.get_consecutive_scan_idx()
#             _dct = self.get_img_idx_map(cur_idx)
#
#             # sp_idx = _dct['sp_idx']
#             sp_id = _dct['sp_id']
#             pol_idx = _dct['pol_idx']
#
#             #for now just use the first counter
#             #counter = self.counter_dct.keys()[0]
#             counter = DNM_DEFAULT_COUNTER
#             if(sp_id not in list(self.spid_data[counter].keys())):
#                 _logger.error('hdw_accel_save_hdr: sp_id[%d] does not exist in self.spid_data[counter].keys()' % sp_id)
#                 return
#             #self._data = self.spid_data[counter][sp_idx][pol_idx]
#             self._data = self.spid_data[counter][sp_id][pol_idx]
#             dct_put(self.data_dct, ADO_DATA_POINTS, self._data)
#
#             dct_put(self.data_dct, ADO_STACK_DATA_POINTS, self.spid_data)
#             dct_put(self.data_dct, ADO_STACK_DATA_UPDATE_DEV_POINTS, self.update_dev_data)
#
#             dct_put(self.data_dct, ADO_SP_ROIS, self.sp_rois)
#
#
#         if (update):
#             self.hdr.save(self.data_dct, use_tmpfile=True)
#         else:
#             pass
#             #Sept 8
#             # if(self.stack or (len(self.sp_rois) > 1)):
#             #     self.hdr.save(self.data_dct, allow_tmp_rename=True)
#             #     self.clean_up_data()
#             # else:
#             #     self.hdr.save(self.data_dct)
#             #end Sept 8
#
#             #update stop time in tmp file
#             self.main_obj.zmq_stoptime_to_tmp_file()
#
#             #now send the Active Data Object (ADO) to the tmp file under the section 'ADO'
#             dct = {}
#             dct['cmd'] = CMD_SAVE_DICT_TO_TMPFILE
#             wdct = {'WDG_COM':dict_to_json(_wdgcom), 'SCAN_TYPE': self.scan_type}
#
#             #try deleting datapoints
#             del self.data_dct['DATA']['POINTS']
#             self.data_dct['DATA']['POINTS'] = []
#             del self.data_dct['STACK_DATA']['POINTS']
#             self.data_dct['STACK_DATA']['POINTS'] = {}
#
#             data_dct_str = dict_to_json(self.data_dct)
#             dct['dct'] = {'SP_ROIS': dict_to_json(self.sp_rois), 'CFG': wdct, 'numEpu': self.numEPU, 'numSpids':self.numSPIDS, 'numE':self.numE, \
#                           'DATA_DCT':data_dct_str}
#
#             #debugging
#             print('hdw_accel_save_hdr: SIZES: _wdgcom=%d wdct=%d' % (get_size(_wdgcom), get_size(wdct)))
#             print('hdw_accel_save_hdr: SIZES: self.data_dct=%d data_dct_str=%d' % (get_size(self.data_dct), get_size(data_dct_str)))
#             print('hdw_accel_save_hdr: SIZES: dct=%d ' % (get_size(dct)))
#
#             self.main_obj.zmq_save_dict_to_tmp_file(dct)
#
#             dct = {}
#             dct['cmd'] = CMD_EXPORT_TMP_TO_NXSTXMFILE
#             self.main_obj.zmq_save_dict_to_tmp_file(dct)
#
#         self.on_save_sample_image(_data=self.img_data[_spatial_roi_idx])
#
#         # _logger.info('save_hdr: done')
#         if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#             self.main_obj.device('CX_auto_disable_power').put(1)  # enabled
#             self.main_obj.device('CY_auto_disable_power').put(1)  # enabled

# def hdw_accel_chk_for_more_evregions(self):
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
#     _logger.info('hdw_accel_chk_for_more_evregions: checking')
#
#     if (self._abort):
#         _logger.info('hdw_accel_chk_for_more_evregions: scan aborting')
#         # make sure to save current scan
#         if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#             self.gate.stop()
#             self.counter.stop()
#         # self.on_save_sample_image()
#         self.on_data_level_done()
#         self.save_hdr()
#         self.hdr.remove_tmp_file()
#
#         return (True)
#
#     # increment the index into ev regions
#     self.incr_evidx()
#
#     # if(self._current_ev_idx < len(self.e_rois)):
#     if (self.get_evidx() < len(self.e_rois)):
#         _logger.info('hdw_accel_chk_for_more_evregions: yes there is, loading and starting')
#         if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#             if(not self.is_point_spec):
#                 self.gate.stop()
#                 self.counter.stop()
#
#         if (self.scan_type not in multi_ev_single_image_scans):
#             # signal plotter to start a new image
#             # sp_id = self.get_next_spatial_id()
#             # self.new_spatial_start.emit(sp_id)
#             self.new_spatial_start.emit(self.sp_db[SPDB_ID_VAL])
#
#         e_roi = self.e_rois[self._current_ev_idx]
#         # configure next ev sscan record with next ev region start/stop
#         self._config_start_stop(self.evScan, 1, e_roi[START], e_roi[STOP], e_roi[NPOINTS])
#
#         # prev_dwell = self.dwell
#         self.dwell = e_roi[DWELL]
#
#         if (self.use_hdw_accel):
#         #     # need to check to see if dwell changed, if it did we need to re-configure the wavetables
#         #     # if(prev_dwell != self.dwell):
#         #     # _logger.debug('dwell changed [%.2f] so reconfiguring the hardware accel' % self.dwell)
#              self.modify_config()
#              # wait for gate and counter to start
#         #     time.sleep(2.0)
#         #    pass
#
#
#         # need to determine the scan velocity if there is a change in Dwell for this next ev region
#         elif (not self.is_point_spec):
#             # the dwell ime for the new ev region could have changed so determine the scan velo and accRange
#             # need to determine the scan velocity if there is a change in Dwell for this next ev region
#             if (self.is_line_spec and self.is_pxp):
#                 scan_velo = self.get_mtr_max_velo(self.xyScan.P1)
#                 # vmax = self.get_mtr_max_velo(self.xyScan.P1)
#             else:
#                 vmax = self.get_mtr_max_velo(self.xScan.P1)
#                 (scan_velo, npts, dwell) = ensure_valid_values(self.x_roi[START], self.x_roi[STOP], self.dwell,
#                                                                self.numX, vmax, do_points=True)
#                 # need the range of scan to be passed to calc_accRange()
#                 rng = self.x_roi[STOP] - self.x_roi[START]
#                 accRange = calc_accRange('SampleX', 'Fine', rng, scan_velo, dwell, accTime=0.04)
#                 # reassign dwell because it ay have changed on return from ensure_valid_values()
#                 self.dwell = dwell
#                 _logger.debug('set_sample_scan_velocity Image scan: scan_velo=%.2f um/s accRange=%.2f um' % (
#                 scan_velo, accRange))
#
#             self.set_x_scan_velo(scan_velo)
#             # ok now finish configuration and start it
#             self.on_this_dev_cfg()
#             if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#                 self.gate.start()
#                 self.counter.start()
#
#
#         elif (self.is_point_spec):
#             # ok now finish configuration and start it
#             self.on_this_dev_cfg()
#             if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#                 self.gate.start()
#                 self.counter.start()
#
#         self.start()
#         # let caller know were not done
#         return (False)
#     else:
#         _logger.info('chk_for_more_evregions: Nope no more')
#         if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#             self.gate.stop()
#             self.counter.stop()
#
#         # ok scan is all done now, so save final header file
#         if (not self.file_saved):
#             _logger.debug('chk_for_more_evregions: calling on_save_sample_image()')
#             self.on_save_sample_image()
#         self.save_hdr()
#
#         # ok there are no more ev regions to execute
#         return (True)

# def coarse_chk_for_more_evregions(self):
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
#     # Sept 6 if(TEST_SAVE_INITIAL_FILE):
#     # Sept 6     self.save_hdr(update=True)
#     _logger.info('chk_for_more_evregions: checking')
#
#     if (self._abort):
#         _logger.info('chk_for_more_evregions: scan aborting')
#         # make sure to save current scan
#         if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#             self.gate.stop()
#             self.counter.stop()
#         # self.on_save_sample_image()
#         # self.on_data_level_done()
#         self.save_hdr()
#         self.hdr.remove_tmp_file()
#
#         return (True)
#
#     # increment the index into ev regions
#     self.incr_evidx()
#
#     # if(self._current_ev_idx < len(self.e_rois)):
#     if (self.get_evidx() < len(self.e_rois)):
#         _logger.info('chk_for_more_evregions: yes there is, loading and starting')
#         if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#             if (not self.is_point_spec):
#                 self.gate.stop()
#                 self.counter.stop()
#
#                 # sept 11
#                 self.counter.wait_till_stopped()
#
#         if (self.scan_type not in multi_ev_single_image_scans):
#             # signal plotter to start a new image
#             # sp_id = self.get_next_spatial_id()
#             # self.new_spatial_start.emit(sp_id)
#             self.new_spatial_start.emit(self.sp_db[SPDB_ID_VAL])
#
#         e_roi = self.e_rois[self._current_ev_idx]
#         # configure next ev sscan record with next ev region start/stop
#         self._config_start_stop(self.evScan, 1, e_roi[START], e_roi[STOP], e_roi[NPOINTS])
#
#         # prev_dwell = self.dwell
#         self.dwell = e_roi[DWELL]
#
#         if (self.use_hdw_accel):
#             # need to check to see if dwell changed, if it did we need to re-configure the wavetables
#             # if(prev_dwell != self.dwell):
#             # _logger.debug('dwell changed [%.2f] so reconfiguring the hardware accel' % self.dwell)
#             self.modify_config()
#             # wait for gate and counter to start
#             time.sleep(2.0)
#
#         # need to determine the scan velocity if there is a change in Dwell for this next ev region
#         elif (not self.is_point_spec):
#             # the dwell ime for the new ev region could have changed so determine the scan velo and accRange
#             # need to determine the scan velocity if there is a change in Dwell for this next ev region
#             if (self.is_line_spec and self.is_pxp):
#                 scan_velo = self.get_mtr_max_velo(self.xyScan.P1)
#                 # vmax = self.get_mtr_max_velo(self.xyScan.P1)
#             else:
#                 vmax = self.get_mtr_max_velo(self.xScan.P1)
#                 (scan_velo, npts, dwell) = ensure_valid_values(self.x_roi[START], self.x_roi[STOP], self.dwell,
#                                                                self.numX, vmax, do_points=True)
#                 # need the range of scan to be passed to calc_accRange()
#                 rng = self.x_roi[STOP] - self.x_roi[START]
#                 accRange = calc_accRange('SampleX', 'Fine', rng, scan_velo, dwell, accTime=0.04)
#                 # reassign dwell because it ay have changed on return from ensure_valid_values()
#                 self.dwell = dwell
#                 _logger.debug('set_sample_scan_velocity Image scan: scan_velo=%.2f um/s accRange=%.2f um' % (
#                 scan_velo, accRange))
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
#         elif (self.is_point_spec):
#             # ok now finish configuration and start it
#             self.on_this_dev_cfg()
#             if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#                 if (not self.is_point_spec):
#                     self.gate.start()
#                     self.counter.start()
#                     # sept 11
#                     self.counter.wait_till_running()
#
#         self.start()
#         # let caller know were not done
#         return (False)
#     else:
#         _logger.info('chk_for_more_evregions: Nope no more')
#         if ((not self.is_point_spec) and self.coarse_chk_for_more_spatial_regions()):
#             # were not done
#             return (False)
#         else:
#             if (self.main_obj.get_beamline_id() is BEAMLINE_IDS.STXM):
#                 self.gate.stop()
#                 self.counter.stop()
#
#             # ok scan is all done now, so save final header file
#             if (not self.file_saved):
#                 _logger.debug('chk_for_more_evregions: calling on_save_sample_image()')
#                 self.on_save_sample_image()
#             self.save_hdr()
#
#             # ok there are no more spatial regions to execute
#             return (True)
#
# def coarse_chk_for_more_spatial_regions(self):
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
#     if (self._abort):
#         _logger.info('chk_for_more_spatial_regions: scan aborting')
#         self.save_hdr()
#         self.hdr.remove_tmp_file()
#         return (True)
#
#     # get the next spatial ID in the list of spatial regions we are to scan
#     sp_id = self.get_next_spatial_id()
#     if (sp_id is not None):
#         # save the current one and then go again
#         self.save_hdr()
#
#         _logger.info('chk_for_more_spatial_regions: found sp_id=%d, loading and starting' % sp_id)
#
#         # because we will be starting a new scan that will have new self.data created we need to reinit the index to the data
#         # because imgidx is what is used as the first dimension of the data
#         _logger.info('chk_for_more_spatial_regions: resetting the data image index')
#         self.reset_imgidx()
#
#         if (self.is_lxl):
#             self.configure(self.wdg_com, sp_id, ev_idx=0, line=True, block_disconnect_emit=True)
#         else:
#             if (self.is_point_spec):
#                 self.configure(self.wdg_com, sp_id, ev_idx=0, line=False, block_disconnect_emit=True)
#             else:
#                 self.configure(self.wdg_com, sp_id, ev_idx=0, line=False, block_disconnect_emit=True)
#         self.start()
#         return (True)
#     else:
#         _logger.info('chk_for_more_spatial_regions: nope all done')
#         return (False)
