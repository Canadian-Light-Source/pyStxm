# coding=utf-8
"""
Created on July 26, 2019

@author: bergr
"""
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types
from bcm.devices.ophyd.qt.data_emitters import ImageDataEmitter
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.scanning.BaseScan import BaseScan
from cls.types.stxmTypes import (
    scan_types,
    scan_sub_types,
    sample_positioning_modes,
    sample_fine_positioning_modes,
    detector_types
)
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.utils.dict_utils import dct_get
from cls.utils.json_utils import dict_to_json

from ophyd.sim import DetWithCountTime

from .pattern_gen_utils import return_final_scan_points

_logger = get_module_logger(__name__)

appConfig = ConfigClass(abs_path_to_ini_file)
USE_E712_HDW_ACCEL = MAIN_OBJ.get_preset_as_bool("USE_E712_HDW_ACCEL", "BL_CFG_MAIN")

class BasePatternGenScanClass(BaseScan):
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
        # self.spid_data = None
        self.img_idx_map = {}
        self.spid_data = {}
        self.img_details = {}
        self.exp_data = None
        self.final_data = []
        self.segment_cmnd_lst = []
        self.e712_enabled = False
        self.total_time_seconds = 0.0
        self.num_ttl_pnts = 0
        
        if USE_E712_HDW_ACCEL:
            self.e712_enabled = True
            self.e712_wg = MAIN_OBJ.device("DNM_E712_WIDGET")
            self.e712_wg.set_main_obj(MAIN_OBJ)
        
    def init_subscriptions(self, ew, func, det_lst):
        """
        over ride the base init_subscriptions because we dont want any data emitted to plotter
        self.y_roi
        :param ew:
        :param func:
        :param det_lst is a list of detector ophyd objects
        :return:
        """
        pass

    def get_num_progress_events(self):
        """
        each scan needs to indicate how many event documents the RE will produce for the scan
        as each iteration (based on seq id of event document) makes up the total number of events for this scan,
        will change if it is point by point, line by line, or executed by the waveform generator where there are
        no event documents

        To be over ridden by inheriting class
        """
        return self.get_num_points_in_scan()

    def get_num_points_in_scan(self):
        """
        here I need to return the actual number of points which do not include the 0 pixel points
        this was already determined in configure when return_final_scan_points() was called
        """
        return(self.num_ttl_pnts)

    def configure_devs(self, dets):
        """
        configure_devs(): description

        :param dets: dets description
        :type dets: dets type

        :returns: None
        """
        super().configure_devs(dets)

        for d in dets:
            if hasattr(d, "set_dwell"):
                d.set_dwell(0.0)
            if hasattr(d, "set_config"):
                d.set_config(1, 1, is_pxp_scan=True)
            if hasattr(d, "setup_for_software_triggered"):
                d.setup_for_software_triggered()

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        call a specific scan start for fine scans
        """
        super().fine_scan_go_to_scan_start()
        return (True)

    def stop(self):
        # call the parents stop
        super().stop()

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
        super().fine_scan_on_scan_done()
        suspnd_controller_fbk = self.main_obj.device("DNM_E712_SSPND_CTRLR_FBK")
        #renable E712 controller feedback of scan was aborted
        suspnd_controller_fbk.put(0)

        #move motors to somewhere before the start of the scan
        mtr_dct = self.determine_samplexy_posner_pvs()
        mtr_x = self.main_obj.device(mtr_dct["fx_name"])
        mtr_y = self.main_obj.device(mtr_dct["fy_name"])
        mtr_x.move(self.x_roi[SETPOINTS][0] - 5.0)
        mtr_y.move(self.y_roi[SETPOINTS][0] - 5.0)


    def make_pxp_scan_plan(self, dets, md=None, bi_dir=False):
        """
        override the default make_pxp_scan_plan to set the scan_type
        :param dets:
        :param gate:
        :param md:
        :param bi_dir:
        :return:
        """
        if len(self.img_details.keys()):
            if hasattr(self, "e712_wg"):
                if self.e712_wg.useHdwRadioBtn.isChecked():
                    return(self.make_hdw_accelerated_image_pattern_scan_plan(dets, md=md, bi_dir=bi_dir))
                else:
                    return self.make_sw_image_pattern_scan_plan(dets, md=md, bi_dir=bi_dir)
            else:
                return self.make_sw_image_pattern_scan_plan(dets, md=md, bi_dir=bi_dir)
        else:
            #its a pad scan
            return self.make_9pad_pattern_generator_plan(dets, md=md, bi_dir=bi_dir)

    def make_hdw_accelerated_image_pattern_scan_plan(self, dets, md={}, bi_dir=False):
        """

        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        self._bi_dir = bi_dir

        final_data = self.final_data
        shutter = self.main_obj.device("DNM_SHUTTER")
        e712_dev = self.main_obj.device("DNM_E712_OPHYD_DEV")
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        DNM_E712_X_USE_TBL_NUM = self.main_obj.device("DNM_E712_X_USE_TBL_NUM")
        DNM_E712_Y_USE_TBL_NUM = self.main_obj.device("DNM_E712_Y_USE_TBL_NUM")
        DNM_E712_X_START_POS = self.main_obj.device("DNM_E712_X_START_POS")
        DNM_E712_Y_START_POS = self.main_obj.device("DNM_E712_Y_START_POS")
        #start Immediately
        self.main_obj.device("DNM_E712_X_START_MODE").put(1)
        #dont start
        self.main_obj.device("DNM_E712_Y_START_MODE").put(0)

        finemtrx = self.main_obj.get_sample_fine_positioner("X")
        finemtry = self.main_obj.get_sample_fine_positioner("Y")
        if md is None:
            md = {
                "metadata": dict_to_json(
                    self.make_standard_metadata(
                        entry_name="entry0",
                        scan_type=self.scan_type,
                        dets=dets,
                        override_xy_posner_nms=True,
                    )
                )
            }
        # NOTE: baseline_decorator() MUST come before run_decorator()
        @bpp.run_decorator(md=md)
        def do_scan():
            print("starting: make_hdw_accelerated_image_pattern_scan_plan:  do_scan()")
            # load the sp_id for wavegen
            # x_tbl_id, y_tbl_id = self.e712_wdg.get_wg_table_ids(self.sp_id)
            # print(
            #     "make_hdw_accelerated_image_pattern_scan_plan: putting x_tbl_id=%d, y_tbl_id=%d"
            #     % (x_tbl_id, y_tbl_id)
            # )
            # DNM_E712_X_USE_TBL_NUM.put(x_tbl_id)
            # DNM_E712_Y_USE_TBL_NUM.put(y_tbl_id)
            # get the X motor reset position * /
            # if self.is_zp_scan:
            #     DNM_E712_X_START_POS.put(self.zx_roi[START])
            #     DNM_E712_Y_START_POS.put(self.zy_roi[START])
            # else:
            #     DNM_E712_X_START_POS.put(self.x_roi[START])
            #     DNM_E712_Y_START_POS.put(self.y_roi[START])

            e712_wdg.set_num_cycles(1, do_extra=False)

            # for d in dets:
            #     if hasattr(d, "configure_for_scan"):
            #         d.configure_for_scan(self.x_roi[NPOINTS], scan_types.SAMPLE_IMAGE)
            #
            # for d in dets:
            #     yield from bps.stage(d)
            #     if hasattr(d, "kickoff"):
            #         yield from bps.kickoff(d)
            #     if hasattr(d, "init_indexs"):
            #         # new image so reset row/col indexes for data it emits to plotter
            #         d.init_indexs()

            # this starts the wavgen and waits for it to finish without blocking the Qt event loop
            shutter.open()
            self.num_lines_in_wg
            tbl_num = 1
            for dct in final_data:
                if tbl_num < self.num_lines_in_wg:
                    y_pos = dct["y"]
                    x_start = dct["x_line"][0]
                    DNM_E712_X_USE_TBL_NUM.put(tbl_num)
                    yield from bps.mv(finemtrx, x_start)
                    yield from bps.mv(finemtry, y_pos)
                    yield from bps.mv(e712_dev.run, 1)
                    tbl_num += 1
            shutter.close()
            # yield from bps.wait(group='e712_wavgen')

            # for d in dets:
            #     yield from bps.unstage(d)
            #     if hasattr(d, "complete"):
            #         yield from bps.complete(d)  # stop minting events everytime the line_det publishes new data!
            #     # yield from bps.unmonitor(det)
            #
            # for d in dets:
            #     # the collect method on e712_flyer may just return as empty list as a formality, but future proofing!
            #     if hasattr(d, "collect"):
            #         yield from bps.collect(d)

            # yield from bps.trigger_and_read(dets)

        return (yield from do_scan())


    def make_sw_image_pattern_scan_plan(self, dets, md={}, bi_dir=False):
        """

        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        self._bi_dir = bi_dir
        final_data = self.final_data
        det_with_count_time = DetWithCountTime(name='det', labels={'detectors'})

        mtr_dct = self.determine_samplexy_posner_pvs()
        mtr_x = self.main_obj.device(mtr_dct["fx_name"])
        mtr_y = self.main_obj.device(mtr_dct["fy_name"])
        shutter = self.main_obj.device("DNM_SHUTTER")
        suspnd_controller_fbk = self.main_obj.device("DNM_E712_SSPND_CTRLR_FBK")

        #remove the IMG_EXP_DATA from the SCAN_PLUGIN as it may be too large for mongo db in BlueSky md
        self.wdg_com["SPATIAL_ROIS"][self.sp_id]["SCAN_PLUGIN"].pop('IMG_EXP_DATA')

        if md is None:
            md = {
                "metadata": dict_to_json(
                    self.make_standard_metadata(
                        entry_name="entry0",
                        scan_type=self.scan_type,
                        dets=dets,
                        override_xy_posner_nms=True,
                    )
                )
            }

        # override the POSIIONER so tha nxstxm and can export properly
        # md = self.add_spids_xy_setpoints(md)
        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():
            #need a dud dets to generate the event documents needed for the progress report from the RE
            dets = [det_with_count_time]
            shutter.open()
            # this PV will cause the E712 driver to not bog down controller with reading/updating values that we dont care about during scan resulting in better performance
            suspnd_controller_fbk.put(1)

            for dct in final_data:
                y_pos = dct["y"]
                yield from bps.mv(mtr_y, y_pos)
                comb_data = zip(dct["x_line"], dct["dwell_data"])
                for [x_pos, dwell_time] in list(comb_data):
                    #dwell_time is in milliseconds but settle time is in seconds
                    mtr_x.settle_time = dwell_time * 0.001
                    #print("make_sw_image_pattern_scan_plan: moving X to %.3f" % x_pos)
                    yield from bps.mv(mtr_x, x_pos)
                    #here we need to create an event doc so that the progress of the scan will be picked up by the progress signals and handlers
                    yield from bps.create(name="primary")
                    yield from bps.read(det_with_count_time)
                    yield from bps.save()

            shutter.close()
            #re enable controller feedback
            suspnd_controller_fbk.put(0)
            # print("PositionerScanClass: make_scan_plan Leaving")

        return (yield from do_scan())

    def make_pattern_generator_plan(self, dets, md=None, bi_dir=False):
        """
        a plan for making the 9 pad pattern generator plan
        :param dets:
        :param gate:
        :param md:
        :param bi_dir:
        :return:
        """
        print("entering: make_pattern_generator_plan")
        # dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        stagers = []
        for d in dets:
            stagers.append(d)

        def do_scan():
            # print('starting: make_pattern_generator_plan: do_scan()')
            entrys_lst = []
            entry_num = 0
            self._current_img_idx = 0
            mtr_x = self.main_obj.get_sample_fine_positioner("X")
            mtr_y = self.main_obj.get_sample_fine_positioner("Y")
            if not self.motor_ready_check([mtr_x, mtr_y]):
                _logger.error(
                    "The scan cannot execute because one or more motors for the scan are not in a ready state"
                )
                return None

            for sp_id in self.sp_ids:
                self.sp_id = sp_id
                self.dwell = self.sp_rois[sp_id][SPDB_EV_ROIS][0][DWELL]

                print(
                    "make_pattern_generator_plan: scanning pad %d, setting dwell=%.2f"
                    % (sp_id + 1, self.dwell)
                )
                _logger.info(
                    "make_pattern_generator_plan: scanning pad %d, setting dwell=%.2f"
                    % (sp_id + 1, self.dwell)
                )

                # this updates member vars x_roi, y_roi, etc... with current spatial id specifics
                self.update_roi_member_vars(self.sp_rois[self.sp_id])

                for d in dets:
                    if hasattr(d, "set_dwell"):
                        d.set_dwell(self.dwell)
                    if hasattr(d, "set_points_per_row"):
                        d.set_points_per_row(self.x_roi[NPOINTS])

                # take a single image that will be saved with its own run scan id
                img_dct = self.img_idx_map["%d" % self._current_img_idx]

                md = {
                    "metadata": dict_to_json(
                        self.make_standard_metadata(
                            entry_name=img_dct["entry"], scan_type=self.scan_type
                        )
                    )
                }

                # take the bnaseline on the middle (5th) pad so that its params are used for the data
                if self._current_img_idx == 4:
                    do_baseline = True
                else:
                    do_baseline = False

                yield from self.make_single_pxp_image_plan(
                    dets, md=md, do_baseline=do_baseline
                )
                self._current_img_idx += 1
                entrys_lst.append(img_dct["entry"])

            # print("make_pattern_generator_plan Leaving")

        return (yield from do_scan())


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

    # def configure(self, wdg_com, sp_id=0, ev_idx=0, line=True, block_disconnect_emit=False):
    #     """
    #     configure(): This is the configure routine that is required to be defined by every scan plugin. the main goal of the configure function is to
    #         - extract into member variables the scan param data from the wdg_com (widget communication) dict
    #         - configure the sample motors for the correct Mode for the upcoming scan
    #         - reset any relevant member variable counters
    #         - decide if it is a line by line, point by point or point spectrum scan
    #         - set the optimization function for this scan (which is used later to fine tune some key params of the sscan record before scan)
    #         - decide if this is a goniometer scan and set a flag accordingly
    #         - set the start/stop/npts etc fields of the relevant sscan records for a line or point scan by calling either:
    #             set_ImageLineScan_line_sscan_rec() or set_ImageLineScan_point_sscan_rec()
    #         - determine the positioners that will be used in this scan (they depend on the size of the scan range, coarse or fine etc)
    #         - call either config_for_goniometer_scan() or config_for_sample_holder_scan() depending on if a goniometer scan or not
    #         - create the numpy array in self.data by calling config_hdr_datarecorder()
    #         - then call final_setup() which must be called at the end of every configure() function
    #
    #     :param wdg_com: wdg_com is a "widget Communication dictionary" and it is used to relay information to/from widgets regarding current regions of interest
    #     :type wdg_com: wdg_com is a dictionary comprised of 2 keys: WDGCOM_CMND and SPDB_SPATIAL_ROIS, both of which are strings defined in roi_dict_defs.py
    #             WDGCOM_CMND       : is a command that identifys what should be done with the rois listed in the next field
    #             SPDB_SPATIAL_ROIS : is a list of spatial roi's or spatial databases (sp_db)
    #
    #     :param sp_id: sp_id is the "spatial ID" of the sp_db
    #     :type sp_id: integer
    #
    #     :param ev_idx: ev_idx is the index into the e_rois[] list of energy regions of interest, this configure() function could be called again repeatedly if there are more than one
    #             energy regions of interest, this index is the index into that list, when the scan is first configured/called the index is always the first == 0
    #     :type ev_idx: integer
    #
    #     :param line: line is a boolean flag indicating if the scan to be configured is a line by line scan or not
    #     :type line: bool
    #
    #     :param block_disconnect_emit: because configure() can be called repeatedly by check_more_spatial_regions() I need to be able to control
    #             how the main GUI will react to a new scan being executed in succession, this flag if False will not blocking the emission of the 'disconnect' signals signal
    #             and if True it will block teh emission of the 'disconnect' that the main GUI is listening to
    #     :type block_disconnect_emit: bool
    #
    #     :returns: None
    #
    #     """
    #     ret = super().configure(wdg_com, sp_id=sp_id, line=line, z_enabled=False)
    #     if not ret:
    #         return(ret)
    #
    #     _logger.info("\n\nPatternGenScanClass: configuring sp_id [%d]" % sp_id)
    #     self.new_spatial_start_sent = False
    #     img_details = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_IMG_DETAILS)
    #     if len(img_details.keys()):
    #         self.exp_data = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_IMG_EXP_DATA)
    #         self.img_details = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_IMG_DETAILS)
    #     else:
    #         self.exp_data = None
    #         self.img_details = {}
    #
    #     if ev_idx == 0:
    #         self.reset_evidx()
    #         self.reset_imgidx()
    #         # self.reset_pnt_spec_spid_idx()
    #         self.final_data_dir = None
    #         self.update_dev_data = []
    #
    #     if len(self.sp_ids) > 1:
    #         self.is_multi_spatial = True
    #         # if multi spatial then just save everything without prompting
    #         self.set_save_all_data(True)
    #     else:
    #         self.is_multi_spatial = False
    #         self.set_save_all_data(False)
    #
    #     self.use_hdw_accel = dct_get(self.sp_db, SPDB_HDW_ACCEL_USE)
    #     if self.use_hdw_accel is None:
    #         self.use_hdw_accel = False
    #         self.e712_enabled = False
    #         # force the wave table rate to be 10 so that all pattern pads will be calc to use same rate
    #         # self.e712_wg.set_forced_rate(10)
    #
    #     self.is_fine_scan = True
    #     # override
    #     if not self.is_fine_scan:
    #         # coarse scan so turn hdw accel flag off
    #         self.use_hdw_accel = False
    #
    #
    #     if self.scan_type != scan_types.SAMPLE_POINT_SPECTRUM:
    #         self.numImages = int(
    #             self.sp_db[SPDB_EV_NPOINTS] * self.numEPU * self.numSPIDS
    #         )
    #     else:
    #         # is a sample point spectrum
    #         self.numImages = 1
    #
    #     # set some flags that are used elsewhere
    #     if self.numImages > 1:
    #         self.stack = True
    #         self.save_all_data = True
    #     else:
    #         self.stack = False
    #
    #     # self.is_lxl = False
    #     # self.is_pxp = False
    #     # self.is_point_spec = False
    #     # self.file_saved = False
    #     # self.sim_point = 0
    #     #
    #     # if (self.scan_sub_type == scan_sub_types.LINE_UNIDIR):
    #     #     # LINE_UNIDIR
    #     #     self.is_lxl = True
    #     # else:
    #     #     # POINT_BY_POINT
    #     #     self.is_pxp = True
    #     #
    #     # if (self.fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE):
    #     #     self.is_zp_scan = True
    #     # else:
    #     #     self.is_zp_scan = False
    #     #     # determine and setup for line or point by point
    #     # self.ttl_pnts = 0
    #
    #     # depending on the scan size the positioners used in the scan will be different, use a singe
    #     # function to find out which we are to use and return those names in a dct
    #     dct = self.determine_samplexy_posner_pvs(force_fine_scan=True)
    #
    #     # depending on the current samplpositioning_mode perform a different configuration
    #     if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
    #         if self.use_hdw_accel:
    #             self.config_for_goniometer_scan_hdw_accel(dct)
    #         else:
    #             self.config_for_goniometer_scan(dct)
    #
    #     else:
    #         if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
    #             # goniometer_zoneplate mode
    #             if self.use_hdw_accel:
    #                 self.configure_for_zxzy_fine_scan_hdw_accel(dct)
    #             else:
    #                 raise Exception(
    #                     "configure_for_zxzy_fine_scan()  This needs to be implemented!!!"
    #                 )
    #
    #         elif (self.sample_positioning_mode == sample_positioning_modes.COARSE) and (
    #             self.fine_sample_positioning_mode
    #             == sample_fine_positioning_modes.ZONEPLATE
    #         ):
    #             if self.use_hdw_accel:
    #                 self.configure_for_coarse_zoneplate_fine_scan_hdw_accel(dct)
    #             else:
    #                 raise Exception(
    #                     "configure_for_coarse_zoneplate_fine_scan()  This needs to be implemented!!!"
    #                 )
    #
    #         else:
    #             # coarse_samplefine mode
    #             if self.use_hdw_accel:
    #                 self.configure_for_samplefxfy_fine_scan_hdw_accel(dct)
    #             else:
    #                 raise Exception(
    #                     "configure_for_samplefxfy_fine_scan() does not exist, This needs to be implemented!!!"
    #                 )
    #
    #     # move Gx and Gy to center of scan, is it within a um?
    #
    #     self.final_data_dir = self.config_hdr_datarecorder(
    #         self.stack, self.final_data_dir
    #     )
    #     # self.stack_scan = stack
    #
    #     # make sure OSA XY is in its center
    #     self.move_osaxy_to_its_center()
    #
    #     self.seq_map_dct = self.generate_2d_seq_image_map(
    #         1, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=False
    #     )
    #
    #     # THIS must be the last call
    #     self.finish_setup()
    #
    #     self.new_spatial_start.emit(sp_id)
    #     return(ret)

    def configure(self, wdg_com, sp_id=0, ev_idx=0, line=True, block_disconnect_emit=False):
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
            return (ret)
        _logger.info(
            "\n\nPatternGenWithE712WavegenScanClass: configuring sp_id [%d]"
            % sp_id
        )
        self.final_data = {}
        img_details = {}
        img_details = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_IMG_DETAILS)
        if len(img_details.keys()):
            self.exp_data = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_IMG_EXP_DATA)
            self.img_details = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_IMG_DETAILS)
            self.final_data, self.total_time_seconds, self.num_ttl_pnts = return_final_scan_points(dct_get(self.sp_db, SPDB_XSETPOINTS),
                                                  dct_get(self.sp_db, SPDB_YSETPOINTS),
                                                  self.exp_data)
            print("Pattern Generation is expected to take approx %.2f seconds or %.2f minutes" %(self.total_time_seconds, self.total_time_seconds/60.0))
        else:
            self.exp_data = None
            self.img_details = {}
        self.new_spatial_start_sent = False

        if ev_idx == 0:
            self.reset_evidx()
            self.reset_imgidx()
            # self.reset_pnt_spec_spid_idx()
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

        sps = dct_get(self.wdg_com, SPDB_SINGLE_LST_SP_ROIS)
        evs = dct_get(self.wdg_com, SPDB_SINGLE_LST_EV_ROIS)
        pols = dct_get(self.wdg_com, SPDB_SINGLE_LST_POL_ROIS)
        dwells = dct_get(self.wdg_com, SPDB_SINGLE_LST_DWELLS)
        sub_type = dct_get(self.wdg_com, SPDB_SCAN_PLUGIN_SUBTYPE)


        self.is_pxp = True
        self.is_lxl = False

        self.use_hdw_accel = dct_get(self.sp_db, SPDB_HDW_ACCEL_USE)
        if self.use_hdw_accel is None and USE_E712_HDW_ACCEL:
            self.use_hdw_accel = True

        self.is_fine_scan = True
        # override
        if not self.is_fine_scan:
            # coarse scan so turn hdw accel flag off
            self.use_hdw_accel = False

        if self.use_hdw_accel and USE_E712_HDW_ACCEL:
            # self.save_hdr = self.hdw_accel_save_hdr

            # set the DDL flags
            if dct_get(self.sp_db, SPDB_HDW_ACCEL_AUTO_DDL):
                self.x_auto_ddl = True
                self.x_use_reinit_ddl = False
            else:
                # Reinit DDL for the current scan
                self.x_auto_ddl = False
                self.x_use_reinit_ddl = True

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

        self.ttl_pnts = 0

        # depending on the scan size the positioners used in the scan will be different, use a singe
        # function to find out which we are to use and return those names in a dct
        dct = self.determine_samplexy_posner_pvs(force_fine_scan=True)

        if USE_E712_HDW_ACCEL:
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
                        self.numE,
                        self.numEPU,
                        self.zy_roi[NPOINTS],
                        self.zx_roi[NPOINTS],
                        lxl=self.is_lxl,
                    )
                    self.configure_for_coarse_zoneplate_fine_scan_hdw_accel(dct)
                else:
                    # coarse_samplefine mode
                    self.seq_map_dct = self.generate_2d_seq_image_map(
                        self.numE, self.numEPU, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=self.is_lxl
                    )
                    #self.configure_for_samplefxfy_fine_scan_hdw_accel(dct)
                    if hasattr(self, "e712_wg"):
                        if self.e712_wg.useHdwRadioBtn.isChecked():
                            self.modify_config_patterngen_for_hdw_accel(dct)

        self.final_data_dir = self.config_hdr_datarecorder(
            self.stack, self.final_data_dir
        )
        # self.stack_scan = stack

        # make sure OSA XY is in its center
        self.move_osaxy_to_its_center()

        # THIS must be the last call
        self.finish_setup()

        self.new_spatial_start.emit(sp_id)
        return (ret)


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
        self.num_points = self.numY

        # setup the E712 wavtable's and other relevant params
        if len(self.img_details.keys()) > 0:
            self.modify_config_patterngen_for_hdw_accel()

    def modify_config_patterngen_for_hdw_accel(self, sp_rois=None):
        """
        This function must:
        - take all of the exposure data lines and get the wav strings for each line
        back from the E712,
        - then when the scan is executed:
            - load each line in a different wavetable (max 120) until all the
        points are used up and a complete line is loaded
            - execute that each line consecutively until all loaded lines have been executed
            - load another batch of lines until the points are all used up
            - repeat until all lines are done


        :return:
        """
        #override is_pxp
        self.is_pxp = True
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
        #data_dir = self.get_data_dir()
        #fname = self.get_cur_filename()
        #self.e712_wg.set_data_recorder_fpath(os.path.join(data_dir, fname))

        # create usetable map
        wavtable_map = self.e712_wg.create_wavgen_usetable_map(self.sp_ids)
        # clear previous wavetables
        self.e712_wg.clear_wavetables()
        self.e712_wg.clear_wavgen_use_tbl_ids()
        self.e712_wg.clear_start_modes()
        #define_pxp_segments_from_exposure_data(xdata, ydata,data,dwell
        self.segment_cmnd_lst = self.e712_wg.define_pxp_segments_from_exposure_data(self.final_data, wavtbl_rate=10)
        # self.img_data = {}
        self.num_lines_in_wg = 0
        for dct in self.segment_cmnd_lst:
            pnts_left = self.e712_wg.get_total_num_points_left()
            if pnts_left > 10000:
                y = dct["y"]
                print(dct)
                cmd_lst = dct["segments"]
                if self.e712_wg.useHdwRadioBtn.isChecked():
                    self.e712_wg.send_command_string(cmd_lst)
                self.num_lines_in_wg += 1




        IMMEDIATELY = 1
        #
        # ttl_wavtables = 0
        # # the following lists are populated and then written to placeholder waveform PV's that will be used
        # # by SNL code to load the next set of params for the next spatial region as they are being executed
        # x_wavtbl_id_lst = []
        # y_wavtbl_id_lst = []
        #
        # x_npnts_lst = []
        # y_npnts_lst = []
        #
        # x_reset_posns = []
        # y_reset_posns = []
        #
        # x_start_mode = []
        # x_useddl_flags = []
        # x_reinitddl_flags = []
        # x_startatend_flags = []
        # y_start_mode = []
        # sp_roi_ids = []
        #
        # for sp_id in sp_rois:
        #     sp_db = sp_rois[sp_id]
        #     e_rois = dct_get(sp_db, SPDB_EV_ROIS)
        #     ev_idx = self.get_evidx()
        #     dwell = e_rois[ev_idx][DWELL]
        #
        #     # if(fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE):
        #     if sample_positioning_mode == sample_positioning_modes.GONIOMETER:
        #         x_roi = dct_get(sp_db, SPDB_ZX)
        #         y_roi = dct_get(sp_db, SPDB_ZY)
        #         x_npnts = x_roi[NPOINTS]
        #         y_npnts = y_roi[NPOINTS]
        #
        #     else:
        #         x_roi = dct_get(sp_db, SPDB_X)
        #         y_roi = dct_get(sp_db, SPDB_Y)
        #         x_npnts = x_roi[NPOINTS]
        #         y_npnts = y_roi[NPOINTS]
        #
        #     # new data struct inparrallel with orig self.data, self.numImages = total numEv and num Pol
        #     # self.img_data[sp_id] = np.zeros((self.numImages, y_npnts, x_npnts), dtype=np.float32)
        #
        #     # self.spid_data[sp_id] = {}
        #     # #make a set of arrays for final data
        #     # for q in range(self.numEPU):
        #     #     self.spid_data[sp_id][q] = np.zeros((self.numE, y_npnts, x_npnts), dtype=np.float32)
        #
        #     x_reset_pos = x_roi[START]
        #     y_reset_pos = y_roi[START]
        #     x_axis_id = self.base_zero(self.e712_wg.get_x_axis_id())
        #     y_axis_id = self.base_zero(self.e712_wg.get_y_axis_id())
        #
        #     sp_roi_ids.append(sp_id)
        #     # build a list of wavtable IDs used for this scan
        #     x_wavtbl_id_lst.append(wavtable_map[sp_id][x_axis_id])
        #     y_wavtbl_id_lst.append(wavtable_map[sp_id][y_axis_id])
        #     x_npnts_lst.append(int(x_npnts))
        #     y_npnts_lst.append(int(y_npnts))
        #     # x_reset_posns.append(x_reset_pos)
        #     # y_reset_posns.append(y_reset_pos)
        #
        #     x_start_mode.append(IMMEDIATELY)
        #     y_start_mode.append(IMMEDIATELY)
        #
        #     ddl_data = None
        #     if self.is_pxp:
        #         mode = 0
        #         # program waveforms into tables
        #         self.e712_wg.send_wave(
        #             sp_id,
        #             x_roi,
        #             y_roi,
        #             dwell,
        #             mode,
        #             x_auto_ddl=self.x_auto_ddl,
        #             x_force_reinit=self.x_use_reinit_ddl,
        #             trig_per_point=True
        #         )
        #         x_useddl_flags.append(0)
        #         x_reinitddl_flags.append(0)
        #         x_startatend_flags.append(0)
        #     else:
        #         mode = 1
        #         # program waveforms into tables, return ddl_data if one exists for the parameters for this scan
        #         ddl_data = self.e712_wg.send_wave(
        #             sp_id,
        #             x_roi,
        #             y_roi,
        #             dwell,
        #             mode,
        #             x_auto_ddl=self.x_auto_ddl,
        #             x_force_reinit=self.x_use_reinit_ddl,
        #             trig_per_point=True
        #         )
        #
        #         # ddl_data = self.e712_wg.get_stored_ddl_table()
        #         # RUSS APR 21 2022 ddl_tbl_pv = self.main_obj.device('e712_ddl_tbls')
        #         # ddl_tbl_pv = []
        #         # # get all DDL table pv's
        #         # for i in range(10):
        #         #     ddl_tbl_pv.append(self.main_obj.device(f'DNM_E712_DDL_TBL_{i}'))
        #         ddl_tbl_pv = self.get_ddl_table_pvlist()
        #
        #         if ddl_data is not None:
        #             print("load this ddl table into the pvs for this spatial region")
        #
        #             ddl_tbl_pv[ttl_wavtables].put(ddl_data)
        #             x_useddl_flags.append(1)
        #             x_reinitddl_flags.append(0)
        #             x_startatend_flags.append(0)
        #         else:
        #             print("set the ddl pv waveform to 0s")
        #             ddl_tbl_pv[ttl_wavtables].put([0, 0, 0, 0, 0, 0])
        #             x_useddl_flags.append(0)
        #             x_reinitddl_flags.append(1)
        #             x_startatend_flags.append(0)
        #
        #     # the x reset pos has now been calculated so retrieve it and store in list
        #     x_reset_posns.append(self.e712_wg.get_x_scan_reset_pos())
        #     y_reset_posns.append(y_reset_pos)
        #     # keep running total
        #     ttl_wavtables += 1
        #
        # # map_lst, self.spid_data = self.make_stack_data_map(numEv=self.numE, numPol=self.numEPU, numSp=self.numSPIDS, x_npnts_lst=x_npnts_lst, y_npnts_lst=y_npnts_lst)
        # # write the x motor reset positions to the waveform pv
        # self.main_obj.device("DNM_E712_XRESETPOSNS").put(x_reset_posns)
        # self.main_obj.device("DNM_E712_YRESETPOSNS").put(y_reset_posns)
        # # write the wavtable ids to the waveform pv
        # self.main_obj.device("DNM_E712_X_WAVTBL_IDS").put(x_wavtbl_id_lst)
        # self.main_obj.device("DNM_E712_Y_WAVTBL_IDS").put(y_wavtbl_id_lst)
        #
        # self.main_obj.device("DNM_E712_X_NPTS").put(x_npnts_lst)
        # self.main_obj.device("DNM_E712_Y_NPTS").put(y_npnts_lst)
        #
        # self.main_obj.device("DNM_E712_X_USEDDL").put(x_useddl_flags)
        # self.main_obj.device("DNM_E712_X_USEREINIT").put(x_reinitddl_flags)
        # self.main_obj.device("DNM_E712_X_STRT_AT_END").put(x_startatend_flags)
        #
        # # 0 = OFF, 1=ON
        # self.main_obj.device("DNM_E712_Y_STRT_AT_END").put([1])
        #
        # self.main_obj.device("DNM_E712_X_START_MODE").put(x_start_mode)
        # self.main_obj.device("DNM_E712_Y_START_MODE").put(y_start_mode)
        #
        # self.main_obj.device("DNM_E712_SP_IDS").put(sp_roi_ids)
        #
        # # self.gateCntrCfgScan.put('NPTS', ttl_wavtables)
        #
        # # need to make sure that the gate and counter are running before leaving here
        # _logger.info(
        #     "Estemated time to complete scan is: %s"
        #     % self.e712_wg.get_new_time_estemate()
        # )

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
