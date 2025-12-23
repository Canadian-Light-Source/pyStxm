# coding=utf-8
"""
Created on Dec 8, 2017

@author: bergr
"""
import warnings
#this will be removed in the future when an upgrade to the latest BlueSky/ophyd
warnings.filterwarnings("ignore", message="The document type 'bulk_events' has been deprecated")


import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from bcm.devices.ophyd.e712_wavegen.e712_defines import *

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
from cls.scan_engine.decorators import conditional_decorator

_logger = get_module_logger(__name__)

appConfig = ConfigClass(abs_path_to_ini_file)

MAX_PIEZO_VELO = 2.0e21

class BaseSampleFineImageWithE712WavegenScanClass(BaseScan):
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
        super().__init__(main_obj=main_obj)
        self.x_use_reinit_ddl = False
        self.x_auto_ddl = True
        self.img_idx_map = {}
        self.spid_data = {}
        self.e712_enabled = True
        self.e712_wg = MAIN_OBJ.device("DNM_E712_WIDGET")
        self.e712_wg.set_main_obj(MAIN_OBJ)
        self._det_subscription = None
        self._det_prog_subscription = None
        self._saved_one = False
        self.is_fine_scan = True

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
        returns a list of detector ophyd objects
        """
        _dets = []
        for d in dets:
            if det_type == detector_types.LINE_FLYER:
                #check if the flyer interface is supported
                if hasattr(d, "kickoff"):
                    _dets.append(d)
            # if det_type == detector_types.LINE:
            #     #check if the flyer interface is supported
            #     if hasattr(d, "kickoff"):
            #         _dets.append(d)
            # else:
            #     # Point
            #     #if hasattr(d, "kickoff"):
            #     _dets.append(d)


        return(_dets)


    def init_subscriptions(self, ew, func, det_lst):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :param det_lst is a list of detector ophyd objects
        :return:
        """
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!! for now connect only the first detector, in the future though this needs to setup an emitter for each selected detector
        #so that the detectors data can be stored and plottable items can be created and built as the scan progresses
        if len(det_lst) > 0 and hasattr(det_lst[0], 'name'):
            d = det_lst[0]
            d.new_plot_data.connect(func)
            self._det_subscription = d


    # def init_progress_subscription(self, ew, func, det_lst):
    #     """
    #     connect the SIS3820 and ask it to send us progress dictionarys
    #     """
    #     if len(det_lst) > 0 and hasattr(det_lst[0], 'name'):
    #         d = det_lst[0]
    #         if hasattr(d, "set_sequence_map"):
    #             d.set_sequence_map(self.seq_map_dct)
    #         d.new_progress_data.connect(func)
    #         self._det_prog_subscription = d

    def configure_devs(self, dets):
        """

        """
        super().configure_devs(dets)

        if self.is_lxl:
            self.config_devs_for_line(dets)
        else:
            self.config_devs_for_point(dets)

    def config_devs_for_line(self, dets):
        '''
        config devs for line scan
        '''
        for d in dets:
            if hasattr(d, "set_dwell"):
                d.set_dwell(self.dwell)
            if hasattr(d, "set_config"):
                d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=self.is_pxp, is_e712_wg_scan=True)
            if hasattr(d, "setup_for_ntrigs_per_line"):
                d.setup_for_ntrigs_per_line()
            if hasattr(d, "set_row_change_index_points"):
                d.set_row_change_index_points(remove_last_point=True)
            if hasattr(d, "set_sequence_map"):
                d.set_sequence_map(self.seq_map_dct)

        # set it so that the plotter updates every 3rd row
        self.set_plot_update_divisor(3)


    def config_devs_for_point(self, dets):
        '''
        config devs for point scan
        '''
        for d in dets:
            if hasattr(d, "set_dwell"):
                d.set_dwell(self.dwell)
            if hasattr(d, "set_config"):
                d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=self.is_pxp, is_e712_wg_scan=True)
            if hasattr(d, "set_sequence_map"):
                d.set_sequence_map(self.seq_map_dct)
            if hasattr(d, "setup_for_ntrigs_per_line"):
                d.setup_for_ntrigs_per_line()
            if hasattr(d, "set_row_change_index_points"):
                if self.dwell < PXP_SHORT_DWELL_REQ_MULT_TRIGS_MS:
                    d.set_row_change_index_points(ignore_even_data_points=True)
                else:
                    d.set_row_change_index_points(remove_last_point=True)

        # set it so that the plotter updates every row
        self.set_plot_update_divisor(1)

    def stop(self):
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        e712_wdg.stop_wave_generator()

        # call the parents stop
        super().stop()

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
        super().fine_scan_on_scan_done()

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        call a specific scan start for fine scans
        """
        super().fine_scan_go_to_scan_start()
        return(True)


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
        self.dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        if self.is_point_spec:
            self.scan_type = scan_types.SAMPLE_POINT_SPECTRUM
            return self.make_stack_image_plan(dets, md=md, bi_dir=bi_dir)
        elif self.numImages == 1:
            self.scan_type = scan_types.SAMPLE_IMAGE
            # return (self.make_single_image_e712_plan(dets, gate, md=md, bi_dir=bi_dir))
            return self.make_stack_image_plan(dets, md=md, bi_dir=bi_dir)
        else:
            self.scan_type = scan_types.SAMPLE_IMAGE_STACK
            return self.make_stack_image_plan(dets, md=md, bi_dir=bi_dir)

    def make_single_point_spec_plan(
        self, dets, md=None, bi_dir=False, do_baseline=True
    ):

        print("entering: make_single_point_spec_plan")
        # zp_def = self.get_zoneplate_info_dct()
        #dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        e712_dev = self.main_obj.device("DNM_E712_OPHYD_DEV")
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        shutter = self.main_obj.device("DNM_SHUTTER")
        ev_mtr = self.main_obj.device("DNM_ENERGY")
        pol_mtr = self.main_obj.device("DNM_EPU_POLARIZATION")
        dnm_e712_x_use_tbl_num = self.main_obj.device("DNM_E712_X_USE_TBL_NUM")
        dnm_e712_y_use_tbl_num = self.main_obj.device("DNM_E712_Y_USE_TBL_NUM")
        dnm_e712_x_start_pos = self.main_obj.device("DNM_E712_X_START_POS")
        dnm_e712_y_start_pos = self.main_obj.device("DNM_E712_Y_START_POS")
        stagers = []

        det = dets[0]

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

        @conditional_decorator(bpp.baseline_decorator(self.dev_list), do_baseline)
        @bpp.stage_decorator(stagers)
        @bpp.run_decorator(md=md)
        def do_scan():

            print("starting: make_single_point_spec_plan:  do_scan()")
            # load the sp_id for wavegen
            x_tbl_id, y_tbl_id = e712_wdg.get_wg_table_ids(self.sp_id)
            print(
                "make_single_point_spec_plan: putting x_tbl_id=%d, y_tbl_id=%d"
                % (x_tbl_id, y_tbl_id)
            )
            dnm_e712_x_use_tbl_num.put(x_tbl_id)
            dnm_e712_y_use_tbl_num.put(y_tbl_id)
            # get the X motor reset position * /
            if self.is_zp_scan:
                dnm_e712_x_start_pos.put(self.zx_roi[START])
                dnm_e712_y_start_pos.put(self.zy_roi[START])
            else:
                dnm_e712_x_start_pos.put(self.x_roi[START])
                dnm_e712_y_start_pos.put(self.y_roi[START])

            e712_wdg.set_num_cycles(self.y_roi[NPOINTS])


            yield from bps.stage(dets)
            # , starts=starts, stops=stops, npts=npts, group='e712_wavgen', wait=True)
            # this starts the wavgen and waits for it to finish without blocking the Qt event loop
            shutter.open()
            yield from bps.mv(e712_dev.run, 1)
            yield from bps.read(dets)
            shutter.close()
            # yield from bps.wait(group='e712_wavgen')

            yield from bps.unstage(dets)  # stop minting events everytime the line_det publishes new data!
            # yield from bps.unmonitor(det)
            # the collect method on e712_flyer may just return as empty list as a formality, but future proofing!
            # yield from bps.collect(det)
            #print("make_single_point_spec_plan Leaving")

        return (yield from do_scan())



    def make_single_image_e712_plan(self, dets, md=None, bi_dir=False, do_baseline=True):
        #print("entering: make_single_image_e712_plan")

        # zp_def = self.get_zoneplate_info_dct()
        # dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
        e712_dev = self.main_obj.device("DNM_E712_OPHYD_DEV")
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        shutter = self.main_obj.device("DNM_SHUTTER")
        ev_mtr = self.main_obj.device("DNM_ENERGY")
        pol_mtr = self.main_obj.device("DNM_EPU_POLARIZATION")
        DNM_E712_X_USE_TBL_NUM = self.main_obj.device("DNM_E712_X_USE_TBL_NUM")
        DNM_E712_Y_USE_TBL_NUM = self.main_obj.device("DNM_E712_Y_USE_TBL_NUM")
        DNM_E712_X_START_POS = self.main_obj.device("DNM_E712_X_START_POS")
        DNM_E712_Y_START_POS = self.main_obj.device("DNM_E712_Y_START_POS")
        #line_counter = self.main_obj.device("DNM_LINE_DET_FLYER")
        #     md = self.make_standard_metadata(entry_name="entry0", scan_type=self.scan_type, dets=dets)
        if md is None:
            md = {
                "metadata": dict_to_json(
                    self.make_standard_metadata(
                        entry_name="entry0", scan_type=self.scan_type, dets=dets
                    )
                )
            }

        # NOTE: baseline_decorator() MUST come before run_decorator()
        @conditional_decorator(bpp.baseline_decorator(self.dev_list), do_baseline)
        @bpp.run_decorator(md=md)
        def do_scan():

            #print("starting: make_single_image_e712_plan:  do_scan()")
            # load the sp_id for wavegen
            x_tbl_id, y_tbl_id = e712_wdg.get_wg_table_ids(self.sp_id)
            # print(
            #     "make_single_image_e712_plan: putting x_tbl_id=%d, y_tbl_id=%d"
            #     % (x_tbl_id, y_tbl_id)
            # )
            #_do_scan_started = True
            DNM_E712_X_USE_TBL_NUM.put(x_tbl_id)
            DNM_E712_Y_USE_TBL_NUM.put(y_tbl_id)
            # get the X motor reset position * /
            if self.is_zp_scan:
                DNM_E712_X_START_POS.put(self.zx_roi[START])
                DNM_E712_Y_START_POS.put(self.zy_roi[START])
            else:
                DNM_E712_X_START_POS.put(self.x_roi[START])
                DNM_E712_Y_START_POS.put(self.y_roi[START])

            e712_wdg.set_num_cycles(self.y_roi[NPOINTS])

            for d in dets:
                if hasattr(d, "configure_for_scan"):
                    d.configure_for_scan( self.x_roi[NPOINTS], scan_types.SAMPLE_IMAGE)

            for d in dets:
                #print(f"detector [{d.name}]")
                yield from bps.stage(d)
                if hasattr(d, "kickoff"):
                    _logger.debug(f"Calling KICKOFF for device [{d.name}]")
                    yield from bps.kickoff(d, group="KICKED_DETECTORS")
                    _logger.debug(f"DONE Calling KICKOFF for device [{d.name}]")
                if hasattr(d, "init_indexs"):
                    # new image so reset row/col indexes for data it emits to plotter
                    d.init_indexs()

            yield from bps.wait("KICKED_DETECTORS")

            # this starts the wavgen and waits for it to finish without blocking the Qt event loop
            shutter.open()
            _logger.debug(f"Calling bps.trigger(e712_dev)")
            yield from bps.trigger(e712_dev)
            _logger.debug(f"DONE Calling trigger(e712_dev)")

            shutter.close()

            # create an event_page doc in the primary data stream
            if self.get_is_scan_aborted() and not self._saved_one:
                # aborted before first image was saved (cannot save partials)
                pass
            else:
                # aborted or not and its already saved one
                yield from bps.create("primary")

                for d in dets:
                    #yield from bps.read(d)
                    yield from bps.unstage(d)
                    if hasattr(d, "complete"):
                        _logger.debug(f"Calling COMPLETE for device [{d.name}]")
                        yield from bps.complete(d, group="COMPLETED_DETECTORS")  # stop minting events everytime the line_det publishes new data!
                        _logger.debug(f"DONE Calling COMPLETE for device [{d.name}]")

                bps.wait("COMPLETED_DETECTORS")

                for d in dets:
                    # the collect method on e712_flyer may just return as empty list as a formality, but future proofing!
                    if hasattr(d, "collect"):
                        _logger.debug(f"Calling COLLECT for device [{d.name}]")

                        # for collect:
                        # stream: boolean, optional
                        #     If False (default), emit Event documents in one bulk dump. If True, emit events one at time.
                        #
                        # return_payload: boolean, optional
                        #     If True (default), return the collected Events. If False, return None. Using stream=True
                        #     and return_payload=False together avoids accumulating the documents in memory: they are
                        #     emmitted as they are collected, and they are not accumulated.
                        yield from bps.collect(d, stream=True, return_payload=False)

                        _logger.debug(f"DONE Calling COLLECT for device [{d.name}]")

                # bundle and emit doc
                yield from bps.save()

        return (yield from do_scan())

    def make_stack_image_plan(self, dets, md=None, bi_dir=False):
        #print("entering: make_stack_image_plan")
        self._saved_one = False
        stagers = []
        for d in dets:
            stagers.append(d)

        def do_scan():
            # ev_mtr = self.main_obj.device("DNM_ENERGY")
            energy_dev = self.main_obj.device("DNM_ENERGY_DEVICE")
            pol_mtr = self.main_obj.device("DNM_EPU_POLARIZATION")
            off_mtr = self.main_obj.device("DNM_EPU_OFFSET")
            ang_mtr = self.main_obj.device("DNM_EPU_ANGLE")

            # print('starting: make_stack_image_plan: do_scan()')
            entrys_lst = []
            entry_num = 0
            # idx = 0
            self._current_img_idx = 0
            point_spec_devs_configd = False
            prev_entry_nm = ""
            # , starts=starts, stops=stops, npts=npts, group='e712_wavgen', wait=True)
            # this starts the wavgen and waits for it to finish without blocking the Qt event loop
            epu_sps = zip(self.setpointsPol, self.setpointsOff,self.setpointsAngle)

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
                    #yield from bps.mv(ev_mtr, ev_sp)
                    yield from bps.mv(energy_dev, ev_sp)
                    # self.dwell = ev_roi[DWELL]
                    self.dwell = self.setpointsDwell

                    # now load and execute each spatial region
                    for sp_id in self.sp_ids:
                        self.sp_id = sp_id
                        # this updates member vars x_roi, y_roi, etc... with current spatial id specifics
                        self.update_roi_member_vars(self.sp_rois[self.sp_id])
                        if self.is_point_spec and (not point_spec_devs_configd):
                            # config the det and gate
                            for d in dets:
                                if hasattr(d, "set_mode"):
                                    d.set_mode(bs_dev_modes.NORMAL_PXP)
                                if hasattr(d, "configure"):
                                    d.configure()

                            point_spec_devs_configd = True

                        samplemtrx = self.main_obj.get_sample_positioner("X")
                        samplemtry = self.main_obj.get_sample_positioner("Y")
                        finemtrx = self.main_obj.get_sample_fine_positioner("X")
                        finemtry = self.main_obj.get_sample_fine_positioner("Y")
                        # make sure servo power is on
                        finemtrx.servo_power.put(1)
                        finemtry.servo_power.put(1)

                        if self.is_zp_scan:
                            # moving them to the start gets rid of a goofy first line of the scan
                            yield from bps.mv(finemtrx, self.zx_roi[START])
                            yield from bps.mv(finemtry, self.zy_roi[START])
                            yield from bps.mv(
                                samplemtrx,
                                self.gx_roi[CENTER],
                                samplemtry,
                                self.gy_roi[CENTER],
                            )
                            # samplemtrx.move(self.gx_roi[CENTER], wait=True)
                            # samplemtry.move(self.gy_roi[CENTER], wait=True)

                        else:
                            # !!! THIS NEEDS TESTING
                            # moving them to the start gets rid of a goofy first line of the scan
                            yield from bps.mv(finemtrx, self.x_roi[START])
                            yield from bps.mv(finemtry, self.y_roi[START])
                            ############################
                        # take a single image that will be saved with its own run scan id
                        # img_dct = self.img_idx_map['%d' % idx]
                        img_dct = self.img_idx_map["%d" % self._current_img_idx]

                        md = {
                            "metadata": dict_to_json(
                                self.make_standard_metadata(
                                    entry_name=img_dct["entry"],
                                    dets=dets,
                                    scan_type=self.scan_type,
                                )
                            )
                        }
                        # if(entry_num is 0):
                        # if(img_dct['entry'] is not prev_entry_nm):
                        if img_dct["entry"] not in entrys_lst:
                            # only create the entry once
                            if self.is_point_spec:
                                yield from self.make_single_point_spec_plan(
                                    dets, md=md, do_baseline=True
                                )
                            else:
                                yield from self.make_single_image_e712_plan(
                                    dets, md=md, do_baseline=True
                                )

                        else:
                            # this data will be used to add to previously created entries
                            if self.is_point_spec:
                                yield from self.make_single_point_spec_plan(
                                    dets, md=md, do_baseline=False
                                )
                            else:
                                yield from self.make_single_image_e712_plan(
                                    dets, md=md, do_baseline=False
                                )

                        # entry_num += 1
                        # idx += 1
                        self._current_img_idx += 1
                        # prev_entry_nm = img_dct['entry']
                        entrys_lst.append(img_dct["entry"])

                self._saved_one = True

            #print("make_stack_image_plan Leaving")

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
            return(ret)
        _logger.info(
            "\n\nSampleFineImageWithE712WavegenScanClass: configuring sp_id [%d]"
            % sp_id
        )
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
        self.setpointsPol = dct_get(e_roi, EPU_POL_PNTS)
        self.setpointsOff = dct_get(e_roi, EPU_OFF_PNTS)
        self.setpointsAngle = dct_get(e_roi, EPU_ANG_PNTS)
        self.ev_pol_order = dct_get(e_roi, EV_POL_ORDER)

        # sps = dct_get(self.wdg_com, SPDB_SINGLE_LST_SP_ROIS)
        # evs = dct_get(self.wdg_com, SPDB_SINGLE_LST_EV_ROIS)
        # self.setpointsPol = dct_get(self.wdg_com, SPDB_SINGLE_LST_POL_ROIS)
        # self.setpointsDwell = dct_get(self.wdg_com, SPDB_SINGLE_LST_DWELLS)

        # sub_type = dct_get(self.wdg_com, SPDB_SCAN_PLUGIN_SUBTYPE)

        # if sub_type is scan_sub_types.POINT_BY_POINT:
        #     self.is_pxp = True
        #     self.is_lxl = False
        #     #self.default_detector_nm = self._default_detector_nm_pxp
        # else:
        #     self.is_pxp = False
        #     self.is_lxl = True
        #     #self.default_detector_nm = self._default_detector_nm_lxl

        self.use_hdw_accel = dct_get(self.sp_db, SPDB_HDW_ACCEL_USE)
        if self.use_hdw_accel is None:
            self.use_hdw_accel = True

        self.is_fine_scan = True
        # override
        if not self.is_fine_scan:
            # coarse scan so turn hdw accel flag off
            self.use_hdw_accel = False

        if self.use_hdw_accel:
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

        # depending on the current samplpositioning_mode perform a different configuration
        if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            self.seq_map_dct = self.generate_2d_seq_image_map(
                self.numE , self.numEPU, self.zy_roi[NPOINTS], self.zx_roi[NPOINTS], lxl=self.is_lxl,
            )
            if self.use_hdw_accel:
                self.config_for_goniometer_scan_hdw_accel(dct)
            else:
                self.config_for_goniometer_scan(dct)

        else:
            if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
                self.seq_map_dct = self.generate_2d_seq_image_map(
                    self.numE , self.numEPU,
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
                    self.numE , self.numEPU,
                    self.zy_roi[NPOINTS],
                    self.zx_roi[NPOINTS],
                    lxl=self.is_lxl,

                )
                self.configure_for_coarse_zoneplate_fine_scan_hdw_accel(dct)
            else:
                # coarse_samplefine mode
                self.seq_map_dct = self.generate_2d_seq_image_map(
                    self.numE, self.numEPU, self.y_roi[NPOINTS], self.x_roi[NPOINTS], lxl=self.is_lxl,
                )
                self.configure_for_samplefxfy_fine_scan_hdw_accel(dct)

        self.final_data_dir = self.config_hdr_datarecorder(
            self.stack, self.final_data_dir
        )
        # self.stack_scan = stack

        # make sure OSA XY is in its center
        self.move_osaxy_to_its_center()

        # THIS must be the last call
        self.finish_setup()

        self.new_spatial_start.emit(sp_id)
        return(ret)


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
        # self.main_obj.device("DNM_ZONEPLATE_X").set_velo(1000000.0)
        # self.main_obj.device("DNM_ZONEPLATE_Y").set_velo(1000000.0)
        self.main_obj.device("DNM_ZONEPLATE_X").set_velo(MAX_PIEZO_VELO)
        self.main_obj.device("DNM_ZONEPLATE_Y").set_velo(MAX_PIEZO_VELO)

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
        # ### VERY IMPORTANT the current PID tune for ZX is based on a velo (SLew Rate) of 1,000,000
        # # must be FxFy
        # self.main_obj.get_sample_fine_positioner("X").set_power(1)
        # self.main_obj.get_sample_fine_positioner("Y").set_power(1)
        #
        self.main_obj.get_sample_fine_positioner("X").set_velo(MAX_PIEZO_VELO)
        self.main_obj.get_sample_fine_positioner("Y").set_velo(MAX_PIEZO_VELO)
        #
        # # this scan is used with and without the goniometer so setupScan maybe None
        # # if(self.setupScan):
        # #     self.setupScan.set_positioner(1, self.main_obj.device('DNM_SAMPLE_X))
        # #     self.setupScan.set_positioner(2, self.main_obj.device('DNM_SAMPLE_Y))
        #
        # # these are the SampleX SampleY motors
        # cx_mtr = self.main_obj.device(dct["cx_name"])
        # cy_mtr = self.main_obj.device(dct["cy_name"])
        #
        # cx_mtr.put("mode", 0)  # MODE_NORMAL
        # cy_mtr.put("mode", 0)  # MODE_NORMAL
        #
        # # RUSS APR 21 2022 I think this can be skipped because the devices are setup earlier self.set_config_devices_func(self.on_this_dev_cfg)
        # self.sample_mtrx = self.sample_finex = self.main_obj.get_sample_fine_positioner("X")
        # self.sample_mtry = self.sample_finey = self.main_obj.get_sample_fine_positioner("Y")
        #
        # # move Cx and Cy to center of scan, is it within a um?
        # # Sx is moving to scan center nd fx is centered around 0, so move Sx to scan center
        # cx_mtr.move(self.x_roi[CENTER])
        # self.sample_finex.put("user_setpoint", self.x_roi[CENTER])
        # # self.main_obj.device(dct['cx_name']).put('user_setpoint', self.x_roi[CENTER])
        #
        # # if(self.is_within_dband( gy_mtr.get_position(), self.gy_roi[CENTER], 15.0)):
        # # Sy is moving to scan center nd fy is centered around 0, so move Sy to scan center
        # # self.main_obj.device(dct['cy_name']).put('user_setpoint', self.gy_roi[CENTER])
        # cy_mtr.move(self.y_roi[CENTER])

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

        # self.main_obj.device("DNM_ZONEPLATE_X").set_velo(1000000.0)
        # self.main_obj.device("DNM_ZONEPLATE_Y").set_velo(1000000.0)
        self.main_obj.device("DNM_ZONEPLATE_X").set_velo(MAX_PIEZO_VELO)
        self.main_obj.device("DNM_ZONEPLATE_Y").set_velo(MAX_PIEZO_VELO)

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


