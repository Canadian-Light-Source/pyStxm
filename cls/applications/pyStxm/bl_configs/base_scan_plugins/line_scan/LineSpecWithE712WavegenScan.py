"""
Created on june 18, 2019

@author: bergr
"""
from cycler import cycler

from bluesky.plans import scan_nd
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types

from cls.applications.pyStxm import abs_path_to_ini_file
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.scanning.BaseScan import BaseScan
from cls.utils.roi_dict_defs import *
from cls.utils.json_utils import dict_to_json

from cls.types.stxmTypes import (
    scan_types,
    sample_positioning_modes,
    sample_fine_positioning_modes,
)

from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass

_logger = get_module_logger(__name__)
appConfig = ConfigClass(abs_path_to_ini_file)


class BaseLineSpecWithE712WavegenScanClass(BaseScan):
    """
    This class
    """

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=MAIN_OBJ)
        self.e712_wg = MAIN_OBJ.device("DNM_E712_WIDGET")
        self.use_hdw_accel = True
        self.x_auto_ddl = True
        self.x_use_reinit_ddl = False
        # self.default_detector_nm = "DNM_DEFAULT_COUNTER"
        

    def init_subscriptions(self, ew, func, dets):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :return:
        """
        pass

    def configure_devs(self, dets, gate):
        if self.is_pxp:
            for d in dets:
                if hasattr(d, "set_mode"):
                    d.set_mode(0)
            gate.set_mode(bs_dev_modes.NORMAL_PXP)
            gate.set_num_points(1)
            gate.set_trig_src(trig_src_types.NORMAL_PXP)

        else:
            for d in dets:
                if hasattr(d, "set_mode"):
                    d.set_mode(bs_dev_modes)
            gate.set_mode(bs_dev_modes.E712)
            gate.set_num_points(self.x_roi[NPOINTS])
            gate.set_trig_src(trig_src_types.E712)

        gate.set_dwell(self.dwell)
        gate.configure()

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
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
        mtr_dct = self.determine_samplexy_posner_pvs()
        mtr_x = self.main_obj.device(mtr_dct["sx_name"])
        mtr_y = self.main_obj.device(mtr_dct["sy_name"])

        x_roi = self.sp_db["X"]
        y_roi = self.sp_db["Y"]
        zz_roi = self.sp_db["ZP"]["Z"]

        #determine if the scan will violate soft limits
        if self.is_fine_scan:
            accel_dis_prcnt_nm = "DNM_FINE_ACCEL_DIST_PRCNT"
            deccel_dis_prcnt_nm = "DNM_FINE_DECCEL_DIST_PRCNT"
        else:
            accel_dis_prcnt_nm = "DNM_COARSE_ACCEL_DIST_PRCNT"
            deccel_dis_prcnt_nm = "DNM_COARSE_DECCEL_DIST_PRCNT"

        accel_dist_prcnt_pv = self.main_obj.device(accel_dis_prcnt_nm)
        deccel_dist_prcnt_pv = self.main_obj.device(deccel_dis_prcnt_nm)
        ACCEL_DISTANCE = self.x_roi["RANGE"] * accel_dist_prcnt_pv.get()
        DECCEL_DISTANCE = self.x_roi["RANGE"] * deccel_dist_prcnt_pv.get()
        xstart = self.x_roi['START'] - ACCEL_DISTANCE
        xstop = self.x_roi['STOP'] + DECCEL_DISTANCE
        ystart, ystop = self.y_roi['START'] , self.y_roi['STOP']

        #check if beyond soft limits
        # if the soft limits would be violated then return False else continue and return True
        if not mtr_x.check_scan_limits(xstart, xstop):
            _logger.error("Scan would violate soft limits of X motor")
            return(False)
        if not mtr_y.check_scan_limits(ystart, ystop):
            _logger.error("Scan would violate soft limits of Y motor")
            return(False)

        if self.is_fine_scan:
            super().fine_scan_go_to_scan_start()
        else:

            # mtr_x.move_to_scan_start(start=x_roi[START], stop=x_roi[STOP], npts=x_roi[NPOINTS], dwell=self.dwell, start_in_center=True)
            # mtr_y.move_to_position(y_roi[CENTER], False)

            # before starting scan check the interferometers, note BOTH piezo's must be off first
            mtr_x.set_piezo_power_off()
            mtr_y.set_piezo_power_off()

            if not mtr_x.do_voltage_check():
                self.mtr_recenter_msg.show()
                mtr_x.do_autozero()
            if not mtr_y.do_voltage_check():
                self.mtr_recenter_msg.show()
                mtr_y.do_autozero()

            mtr_x.do_interferometer_check()
            mtr_y.do_interferometer_check()

            self.mtr_recenter_msg.hide()

            mtr_x.move_coarse_to_scan_start(start=xstart, stop=x_roi[STOP], npts=x_roi[NPOINTS], dwell=self.dwell)
            mtr_y.move_coarse_to_position(ystart, False)

            #coarse focus scan
            mtr_x.set_piezo_power_off()
            mtr_y.set_piezo_power_off()

        return(True)

    def make_pxp_scan_plan(self, dets, gate, md=None, bi_dir=False):
        """
            gate and counter need to be staged for pxp
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
                        entry_name="entry0", scan_type=self.scan_type
                    )
                )
            }
        mtr_dct = self.determine_samplexy_posner_pvs()

        @bpp.baseline_decorator(dev_list)
        @bpp.stage_decorator(dets)
        def do_scan():

            mtr_x = self.main_obj.device(mtr_dct["cx_name"])
            mtr_y = self.main_obj.device(mtr_dct["cy_name"])
            mtr_ev = self.main_obj.device("DNM_ENERGY")
            shutter = self.main_obj.device("DNM_SHUTTER")

            ev_setpoints = []
            for ev_roi in self.e_rois:
                # switch to new energy
                for ev_sp in ev_roi[SETPOINTS]:
                    ev_setpoints.append(ev_sp)

            x_traj = cycler(mtr_x, self.x_roi[SETPOINTS])
            y_traj = cycler(mtr_y, self.y_roi[SETPOINTS])
            energy_traj = cycler(mtr_ev, ev_setpoints)

            yield from bps.stage(gate)
            # this starts the wavgen and waits for it to finish without blocking the Qt event loop
            # the detector will be staged automatically by the grid_scan plan
            shutter.open()
            yield from scan_nd(dets, energy_traj * (y_traj + x_traj), md=md)

            shutter.close()
            # yield from bps.wait(group='e712_wavgen')
            yield from bps.unstage(gate)

            # print("LineSpecScanWithE712WavegenClass PxP: make_scan_plan Leaving")

        return (yield from do_scan())

    # def make_lxl_scan_plan(self, dets, gate, md=None, bi_dir=False):
    #     '''
    #
    #
    #     :param dets:
    #     :param gate:
    #     :param bi_dir:
    #     :return:
    #     '''
    #     #config detector and gate for num points etc
    #     flyer_det = dets[0]
    #     gate.set_num_points(self.x_roi[NPOINTS])
    #     gate.set_mode(1) #line
    #     flyer_det.configure(self.x_roi[NPOINTS], self.scan_type)
    #     e712_dev = self.main_obj.device('DNM_E712_OPHYD_DEV)
    #     dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
    #     self._bi_dir = bi_dir
    #     # make sure the line detector knows that we are the line spec scan
    #     dets[0].set_scan_type(self.scan_type)
    #
    #     if (md is None):
    #         md = {'metadata': dict_to_json(
    #             self.make_standard_metadata(entry_name='entry0', scan_type=self.scan_type))}
    #     @bpp.baseline_decorator(dev_list)
    #     @bpp.stage_decorator(dets)
    #     #@bpp.run_decorator(md=md)
    #     def do_scan():
    #
    #         mtr_ev = self.main_obj.device('DNM_ENERGY)
    #         shutter = self.main_obj.device('DNM_SHUTTER)
    #
    #         yield from bps.open_run(md)
    #         yield from bps.kickoff(flyer_det)
    #         yield from bps.stage(gate)
    #
    #         yield from bps.sleep(0.5)
    #
    #         shutter.open()
    #         for ev_roi in self.e_rois:
    #             # switch to new energy
    #             for ev_sp in ev_roi[SETPOINTS]:
    #                 yield from bps.mv(mtr_ev, ev_sp)
    #                 yield from bps.mv(e712_dev.run, 1)
    #         shutter.close()
    #         yield from bps.unstage(gate)
    #
    #         yield from bps.complete(flyer_det)  # stop minting events everytime the line_det publishes new data!
    #         # the collect method on e712_flyer may just return as empty list as a formality, but future proofing!
    #         yield from bps.collect(flyer_det)
    #
    #         yield from bps.close_run()
    #
    #         print('FocusE712ScanClass: LXL make_scan_plan Leaving')
    #
    #     return (yield from do_scan())

    # def make_single_image_e712_plan(self, dets, gate, md=None, bi_dir=False, do_baseline=True):
    #     '''
    #     a scan plan fior taking a single 2d image with the hdw acceleration provided by the PI E712 piezo controller
    #     This plan is called by the fine_image_scan and tomography scans
    #     :param dets:
    #     :param gate:
    #     :param md:
    #     :param bi_dir:
    #     :param do_baseline:
    #     :return:
    #     '''
    #     print('entering: make_LINESPEC_single_image_e712_plan, baseline is:', do_baseline)
    #     #zp_def = self.get_zoneplate_info_dct()
    #     dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()
    #     e712_dev = self.main_obj.device('DNM_E712_OPHYD_DEV)
    #     e712_wdg = self.main_obj.device('DNM_E712_WIDGET)
    #     shutter = self.main_obj.device('DNM_SHUTTER)
    #     ev_mtr = self.main_obj.device('DNM_ENERGY)
    #     pol_mtr = self.main_obj.device('DNM_EPU_POLARIZATION)
    #     DNM_E712_X_USE_TBL_NUM = self.main_obj.device('DNM_E712_X_USE_TBL_NUM')
    #     DNM_E712_Y_USE_TBL_NUM = self.main_obj.device('DNM_E712_Y_USE_TBL_NUM')
    #     DNM_E712_X_START_POS = self.main_obj.device('DNM_E712_X_START_POS')
    #     DNM_E712_Y_START_POS = self.main_obj.device('DNM_E712_Y_START_POS')
    #     stagers = []
    #     for d in dets:
    #         stagers.append(d)
    #     det = dets[0]
    #     if(self.is_lxl):
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
    #     #det.set_num_points(self.x_roi[NPOINTS])
    #     det.configure(self.x_roi[NPOINTS], self.scan_type)
    #     if(md is None):
    #         md = {'metadata': dict_to_json(self.make_standard_metadata(entry_name='entry0', scan_type=self.scan_type))}
    #     # if(not skip_baseline):
    #     #     @bpp.baseline_decorator(dev_list)
    #
    #     @conditional_decorator(bpp.baseline_decorator(dev_list), do_baseline)
    #     @bpp.stage_decorator(stagers)
    #     @bpp.run_decorator(md=md)
    #     def do_scan():
    #         print('starting: make_single_image_e712_plan:  do_scan()')
    #         # load the sp_id for wavegen
    #         x_tbl_id, y_tbl_id = e712_wdg.get_wg_table_ids(self.sp_id)
    #         print('make_single_image_e712_plan: putting x_tbl_id=%d, y_tbl_id=%d' % (x_tbl_id, y_tbl_id))
    #         DNM_E712_X_USE_TBL_NUM.put(x_tbl_id)
    #         DNM_E712_Y_USE_TBL_NUM.put(y_tbl_id)
    #         # get the X motor reset position * /
    #         if(self.fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE):
    #             DNM_E712_X_START_POS.put(self.zx_roi[START])
    #             DNM_E712_Y_START_POS.put(self.zy_roi[START])
    #             e712_wdg.set_num_cycles(self.zy_roi[NPOINTS])
    #         else:
    #             DNM_E712_X_START_POS.put(self.x_roi[START])
    #             DNM_E712_Y_START_POS.put(self.y_roi[START])
    #             e712_wdg.set_num_cycles(self.y_roi[NPOINTS])
    #
    #         #yield from bps.stage(gate)
    #         yield from bps.kickoff(det)
    #         # , starts=starts, stops=stops, npts=npts, group='e712_wavgen', wait=True)
    #         # this starts the wavgen and waits for it to finish without blocking the Qt event loop
    #         shutter.open()
    #         yield from bps.mv(e712_dev.run, 1)
    #         shutter.close()
    #         # yield from bps.wait(group='e712_wavgen')
    #         yield from bps.unstage(gate)
    #         yield from bps.complete(det)  # stop minting events everytime the line_det publishes new data!
    #         # yield from bps.unmonitor(det)
    #         # the collect method on e712_flyer may just return as empty list as a formality, but future proofing!
    #         yield from bps.collect(det)
    #         print('make_single_image_e712_plan Leaving')
    #
    #     return (yield from do_scan())

    def make_lxl_scan_plan(self, dets, gate, md=None, bi_dir=False):
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
        e712_dev = self.main_obj.device("DNM_E712_OPHYD_DEV")
        e712_wdg = self.main_obj.device("DNM_E712_WIDGET")
        shutter = self.main_obj.device("DNM_SHUTTER")
        dnm_e712_x_use_tbl_num = self.main_obj.device("DNM_E712_X_USE_TBL_NUM")
        dnm_e712_y_use_tbl_num = self.main_obj.device("DNM_E712_Y_USE_TBL_NUM")
        mtr_ev = self.main_obj.device("DNM_ENERGY")
        shutter = self.main_obj.device("DNM_SHUTTER")
        stagers = []

        for d in dets:
            stagers.append(d)
        stagers.append(gate)
        det = dets[0]

        if self.fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE:
            det.configure(self.zx_roi[NPOINTS], self.scan_type)
        else:
            det.configure(self.x_roi[NPOINTS], self.scan_type)
        if md is None:
            md = {
                "metadata": dict_to_json(
                    self.make_standard_metadata(
                        entry_name="entry0", scan_type=self.scan_type
                    )
                )
            }

        @bpp.baseline_decorator(dev_list)
        # @bpp.stage_decorator(dets)
        # @bpp.stage_decorator(dets)
        @bpp.run_decorator(md=md)
        def do_scan():

            x_tbl_id, y_tbl_id = e712_wdg.get_wg_table_ids(self.sp_id)
            print(
                "make_single_image_e712_plan: putting x_tbl_id=%d, y_tbl_id=%d"
                % (x_tbl_id, y_tbl_id)
            )
            dnm_e712_x_use_tbl_num.put(x_tbl_id)
            dnm_e712_y_use_tbl_num.put(y_tbl_id)

            if self.use_hdw_accel:
                # this get rid of crappy first 2 lines of scan?
                for i in range(2):
                    yield from bps.mv(e712_dev.run, 1)
                yield from bps.sleep(0.5)

            yield from bps.kickoff(dets[0])
            yield from bps.stage(gate)
            shutter.open()
            # bps.open_run(md=md)

            # now do a horizontal line for every new zoneplate Z setpoint
            img_dct = self.img_idx_map["0"]
            print("Creating new baseline measurement for [%s]" % img_dct["entry"])
            for ev_roi in self.e_rois:
                # switch to new energy
                for ev_sp in ev_roi[SETPOINTS]:
                    yield from bps.mv(mtr_ev, ev_sp)

                    if self.use_hdw_accel:
                        # yield from self.make_single_image_e712_plan(dets, gate, md=md, do_baseline=True)
                        yield from bps.mv(e712_dev.run, 1)
                    else:
                        # this is just stubbed in, has not been immplemented in correct way for this scan
                        yield from self.make_single_image_plan(
                            dets, gate, md=md, do_baseline=True
                        )

            shutter.close()
            # yield from bps.wait(group='e712_wavgen')
            # bps.close_run()
            yield from bps.unstage(gate)
            yield from bps.complete(
                dets[0]
            )  # stop minting events everytime the line_det publishes new data!
            # yield from bps.unmonitor(det)
            # the collect method on e712_flyer may just return as empty list as a formality, but future proofing!
            yield from bps.collect(dets[0])
            # print("LineSpecScanWithE712WavegenClass LxL: make_scan_plan Leaving")

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
        # call the base class configure so that all member vars can be initialized
        ret = super().configure(wdg_com, sp_id=sp_id, line=line)
        if not ret:
            return(ret)

        _logger.info("configure: LineSpecSScanWithE712Wavegen %d" % sp_id)
        # self.set_spatial_id(sp_id)
        # self.wdg_com = wdg_com
        # self.sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        # self.sp_db = self.sp_rois[sp_id]
        # self.sp_ids = list(self.sp_rois.keys())
        # self.sp_id = self.sp_ids[0]
        # self.scan_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_TYPE)
        # self.scan_sub_type = dct_get(self.sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)
        #
        # self.is_lxl = False
        # self.is_pxp = False
        # self.is_point_spec = False
        # self.is_line_spec = False
        # self.file_saved = False
        #
        # if(self.scan_sub_type == scan_sub_types.LINE_UNIDIR):
        #     self.is_lxl = True
        # else:
        #     self.is_pxp = True
        #
        # if (self.fine_sample_positioning_mode == sample_fine_positioning_modes.ZONEPLATE):
        #     self.is_zp_scan = True
        # else:
        #     self.is_zp_scan = False
        #
        # if(ev_idx == 0):
        #     self.reset_evidx()
        #     self.reset_imgidx()
        #     self.final_data_dir = None
        #     self.line_column_cntr = 0
        #
        # self.update_roi_member_vars(self.sp_db)
        self.stack = False
        e_roi = self.e_rois[ev_idx]
        dct_put(
            self.sp_db,
            SPDB_RECT,
            (e_roi[START], self.x_roi[START], self.e_rois[-1][STOP], self.x_roi[STOP]),
        )

        self.configure_sample_motors_for_scan()

        self.setpointsDwell = dct_get(e_roi, DWELL)
        # convert the Polarization QComboBox index values to the STXM Wrapper equivelants
        # self.setpointsPol = self.convert_polarity_points(dct_get(e_roi, 'EPU_POL_PNTS'))
        self.setpointsPol = dct_get(e_roi, EPU_POL_PNTS)
        self.setpointsOff = dct_get(e_roi, EPU_OFF_PNTS)
        self.setpointsAngle = dct_get(e_roi, EPU_ANG_PNTS)

        # sps = dct_get(self.wdg_com, SPDB_SINGLE_LST_SP_ROIS)
        # evs = dct_get(self.wdg_com, SPDB_SINGLE_LST_EV_ROIS)
        # pols = dct_get(self.wdg_com, SPDB_SINGLE_LST_POL_ROIS)
        # dwells = dct_get(self.wdg_com, SPDB_SINGLE_LST_DWELLS)

        # self.dwell = e_roi[DWELL]
        #
        # #data shape for LineSPec scan = (  numEpu, numEv, numX)
        # #                                  #images, #rows, #cols
        # self.numEPU = len(self.setpointsPol)
        # self.numE = int(self.sp_db[SPDB_EV_NPOINTS])
        # self.numSPIDS = len(self.sp_rois)
        # self.numImages = 1
        #
        # self.numZX = self.zx_roi[NPOINTS]
        # self.numZY = self.zy_roi[NPOINTS]

        # NOTE! currently only arbitrary line is supported when equal number of x and e points so use E points
        # self.numY = self.e_roi[NPOINTS]
        self.numX = self.numE
        self.numY = self.x_roi[NPOINTS]

        if self.scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
            self.is_line_spec = True
        else:
            _logger.error(
                "LineSpecSSCAN: unable to determine scan type [%d]" % self.scan_type
            )
            return

        dct = self.determine_samplexy_posner_pvs()

        # depending on the current samplpositioning_mode perform a different configuration
        if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            if self.use_hdw_accel:
                self.config_for_goniometer_scan_hdw_accel(dct)
            else:
                self.config_for_goniometer_scan(dct)
        else:
            if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
                # goniometer_zoneplate mode
                self.configure_for_zxzy_fine_scan_hdw_accel(dct)
            elif (self.sample_positioning_mode == sample_positioning_modes.COARSE) and (
                self.fine_sample_positioning_mode
                == sample_fine_positioning_modes.ZONEPLATE
            ):
                self.configure_for_coarse_zoneplate_fine_scan_hdw_accel(dct)
            else:
                # coarse_samplefine mode
                self.configure_for_samplefxfy_fine_scan_hdw_accel(dct)

        self.config_hdr_datarecorder(self.stack)

        self.seq_map_dct = self.generate_ev_roi_seq_image_map(
            self.e_rois, self.x_roi[NPOINTS]
        )

        # THIS must be the last call
        self.finish_setup()
        self.new_spatial_start.emit(ev_idx)
        return(ret)

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
        self.set_config_devices_func(self.on_this_dev_cfg)
        self.sample_mtrx = self.sample_finex = self.main_obj.device("DNM_SAMPLE_X")
        self.sample_mtry = self.sample_finey = self.main_obj.device("DNM_SAMPLE_Y")

        self.sample_mtrx.put("Mode", 0)  # MODE_NORMAL
        self.sample_mtry.put("Mode", 0)  # MODE_NORMAL

        # Sx is moving to scan center nd fx is centered around 0, so move Sx to scan center
        # cx_mtr.move(self.x_roi[CENTER])
        # self.sample_finex.put('user_setpoint', self.x_roi[CENTER])
        self.sample_mtrx.put("user_setpoint", self.x_roi[CENTER])

        # cy_mtr.move(self.y_roi[CENTER])
        self.sample_mtry.put("user_setpoint", self.y_roi[CENTER])

        # config the sscan that makes sure to move goni xy and osa xy to the correct position for scan
        # the setupScan will be executed as the top level but not monitored
        self.num_points = self.numY

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

        # create usetable map
        wavtable_map = self.e712_wg.create_wavgen_usetable_map(self.sp_ids)
        # clear previous wavetables
        self.e712_wg.clear_wavetables()

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

        y_startatend_flags = []

        y_start_mode = []

        sp_roi_ids = []

        for sp_id in sp_rois:
            sp_db = sp_rois[sp_id]
            e_rois = dct_get(sp_db, SPDB_EV_ROIS)
            ev_idx = self.get_evidx()
            dwell = e_rois[ev_idx][DWELL]

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
            x_reset_posns.append(x_reset_pos)
            y_reset_posns.append(y_reset_pos)

            x_start_mode.append(IMMEDIATELY)
            y_start_mode.append(IMMEDIATELY)

            ddl_data = None
            y_startatend_flags.append(0)

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
                    y_is_pxp=True,
                )
                x_useddl_flags.append(0)
                x_reinitddl_flags.append(0)
                x_startatend_flags.append(0)
            else:
                mode = 1
                # program waveforms into tables
                # modify y_roi to reflect that the number of y points is only 1, this number is written into the num of cycles to execute per wavegen execution
                y_roi[NPOINTS] = 1
                ddl_data = self.e712_wg.send_wave(
                    sp_id,
                    x_roi,
                    y_roi,
                    dwell,
                    mode,
                    x_auto_ddl=self.x_auto_ddl,
                    x_force_reinit=self.x_use_reinit_ddl,
                    y_is_pxp=False,
                )

                # ddl_data = self.e712_wg.get_stored_ddl_table()
                ddl_tbl_pv = MAIN_OBJ.device("e712_ddl_tbls")
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

            # keep running total
            ttl_wavtables += 1

        # map_lst, self.spid_data = self.make_stack_data_map(numEv=self.numE, numPol=self.numEPU, numSp=self.numSPIDS, x_npnts_lst=x_npnts_lst, y_npnts_lst=y_npnts_lst)

        # write the x motor reset positions to the waveform pv
        MAIN_OBJ.device("DNM_E712_XRESETPOSNS").put(x_reset_posns)
        MAIN_OBJ.device("DNM_E712_YRESETPOSNS").put(y_reset_posns)
        # write the wavtable ids to the waveform pv
        MAIN_OBJ.device("DNM_E712_X_WAVTBL_IDS").put(x_wavtbl_id_lst)
        MAIN_OBJ.device("DNM_E712_Y_WAVTBL_IDS").put(y_wavtbl_id_lst)

        MAIN_OBJ.device("DNM_E712_X_NPTS").put(x_npnts_lst)

        # VERY IMPORTANT: make sure that the WG only executes 1 time for each X line
        # remember the spec line is only 1 time per wavegen execution, this pv is read by the gate_cntr_cfg EPICS application(SNL)
        # to set the number of cycles to execute
        MAIN_OBJ.device("DNM_E712_Y_NPTS").put([1])

        MAIN_OBJ.device("DNM_E712_X_USEDDL").put(x_useddl_flags)
        MAIN_OBJ.device("DNM_E712_X_USEREINIT").put(x_reinitddl_flags)
        MAIN_OBJ.device("DNM_E712_X_STRT_AT_END").put(x_startatend_flags)

        # 0 = OFF, 1=ON
        self.main_obj.device("DNM_E712_Y_STRT_AT_END").put(y_startatend_flags)

        MAIN_OBJ.device("DNM_E712_X_START_MODE").put(x_start_mode)
        MAIN_OBJ.device("DNM_E712_Y_START_MODE").put(y_start_mode)

        MAIN_OBJ.device("DNM_E712_SP_IDS").put(sp_roi_ids)

        # make sure that the num of cycles is always 1
        self.e712_wg.set_num_cycles(1)

        _logger.info(
            "Estimated time to complete scan is: %s"
            % self.e712_wg.get_new_time_estemate()
        )

    def on_this_dev_cfg(self):
        """
        on_this_dev_cfg(): description

        :returns: None
        this is an API method to configure the gate, shutter and counter devices for this scan
        """
        # if((self.is_pxp) or (self.is_point_spec)):
        # if (self.is_pxp):
        #     if (self.use_hdw_accel):
        #         #numY == the number of X points but numX is the energies
        #         set_devices_for_e712_wavegen_point_scan(self.scan_type, self.dwell, self.numY, self.counter,numE=self.numE)
        #         # set_devices_for_e712_wavegen_point_scan(scan_type, dwell, numX, counter, numE=0)
        #     else:
        #         # set_devices_for_point_scan(self.roi, self.gate, self.counter, self.shutter)
        #         set_devices_for_point_scan(self.scan_type, self.dwell, self.numE, self.numX, self.gate, self.counter,
        #                                    self.shutter)
        # else:
        #     if(self.use_hdw_accel):
        #         set_devices_for_e712_wavegen_line_scan(self.dwell, self.numX, self.gate, self.counter)
        #     else:
        #         set_devices_for_line_scan(self.dwell, self.numX, self.gate, self.counter, self.shutter)
        #
        # #make sure they are started
        # self.gate.start()
        # self.counter.start()
        pass


#     def linespec_pxp_counter_changed(self, col, xxx_todo_changeme):
#         """
#         linespec_counter_changed(): description
#
#         :param row: row description
#         :type row: row type
#
#         :param (x: (x description
#         :type (x: (x type
#
#         :param y): y) description
#         :type y): y) type
#
#         :returns: None
#         """
#         (row, val) = xxx_todo_changeme
#         """
#         Used to override the sampleImageScanWithEnergy.on_changed handler.
#         This is a slot that is connected to the counters changed signal
#         """
#         if((self.ttl_pnts % self.numY) == 0):
#             if(self.ttl_pnts is not 0):
#                 self.line_column_cntr += 1
#         #print 'linespec_pxp_counter_changed: line_column_cntr=%d row=%d val=%d' % (self.line_column_cntr, row, val)
#         #print 'linespec_pxp_counter_changed: ttl_pnts=%d' % (self.ttl_pnts)
#         self.ttl_pnts += 1
#
#         dct = self.init_counter_to_plotter_com_dct(make_counter_to_plotter_com_dct())
# #         _imgidx = self.get_imgidx()
#         #1, 10, 40
#         _imgidx = self.get_imgidx()
#         self.data[_imgidx, row, self.line_column_cntr] = val
#
#         dct[CNTR2PLOT_ROW] = int(row)
#         dct[CNTR2PLOT_COL] = int(self.line_column_cntr)
#         dct[CNTR2PLOT_VAL] = int(val)
#         self.sigs.changed.emit(dct)
#
#     def linespec_counter_changed(self, col, data, counter_name=DNM_DEFAULT_COUNTER):
#         """
#         linespec_counter_changed(): description
#         :param row: row description
#         :type row: row type
#         :param (x: (x description
#         :type (x: (x type
#
#         :param y): y) description
#         :type y): y) type
#         :returns: None
#             Used to override the sampleImageScanWithEnergy.on_changed handler.
#             This is a slot that is connected to the counters changed signal
#
#             The line scan data is opposit to all the other scans in that the axis' are
#                 |                    |
#             X/Y |            NOT  eV |
#                 |                    |
#                 |__________          |__________
#                     eV                    X/Y
#         """
#         sp_id = int(self.main_obj.device('DNM_E712_CURRENT_SP_ID').get_position())
#         self.set_spatial_id(sp_id)
#
#         dct = self.init_counter_to_plotter_com_dct(make_counter_to_plotter_com_dct())
#         # print 'linespec_pxp_counter_changed: line_column_cntr=%d row=%d val=%d' % (self.line_column_cntr, row, val)
#         # print 'linespec_pxp_counter_changed: ttl_pnts=%d' % (self.ttl_pnts)
#         self.ttl_pnts += 1
#
#         _imgidx = self.get_imgidx()
#         _imgidx = 0
#
#         _dct = self.get_img_idx_map(_imgidx)
#         pol_idx = _dct['pol_idx']
#         e_idx = _dct['e_idx']
#
#         if (sp_id not in list(self.spid_data[counter_name].keys())):
#             _logger.error('sp_id[%d] does not exist in self.spid_data keys' % sp_id)
#             print('sp_id[%d] does not exist in self.spid_data keys' % sp_id)
#             print('self.spid_data.keys=', list(self.spid_data[counter_name].keys()))
#             return
#
#         # self.spid_data[counter_name][sp_id][pol_idx][_imgidx, :, self.line_column_cntr] = np.flipud( data[0:int(self.numY)])
#         #self.spid_data[counter_name][sp_id][pol_idx][_imgidx, :, self.line_column_cntr] = data[0:self.numY]
#
#         #print self.spid_data[counter_name][sp_id][pol_idx].shape
#         #print data.shape
#         #print data[0:self.numY]
#         self.spid_data[counter_name][sp_id][pol_idx][_imgidx, :, self.line_column_cntr] = data[0:self.numY]
#
#
#         dct[CNTR2PLOT_ROW] = None
#         dct[CNTR2PLOT_COL] = int(self.line_column_cntr)
#         dct[CNTR2PLOT_VAL] = data[0:self.numY]
#         dct[CNTR2PLOT_IS_LINE] = True
#         dct[CNTR2PLOT_IS_POINT] = False
#
#         self.line_column_cntr += 1
#         self.sigs.changed.emit(dct)
#
#         prog = float(float(self.line_column_cntr + 0.75) / float(self.numE)) * 100.0
#         prog_dct = make_progress_dict(sp_id=dct[CNTR2PLOT_SP_ID], percent=prog)
#         self.low_level_progress.emit(prog_dct)
