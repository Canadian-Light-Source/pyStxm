"""
Created on Apr 26, 2017

@author: bergr
"""
import copy

from bluesky.plans import count, scan, grid_scan
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import FailedStatus

from ophyd.utils import (ReadOnlyError, LimitError, DestroyedError)
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types

from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

from cls.scanning.BaseScan import BaseScan, SIM_SPEC_DATA, SIMULATE_SPEC_DATA
from cls.types.stxmTypes import (
    scan_types,
    scan_sub_types,
    energy_scan_order_types,
    sample_positioning_modes,
    sample_fine_positioning_modes,
)
from cls.scanning.scan_cfg_utils import ensure_valid_values, calc_accRange
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.utils.dict_utils import dct_put, dct_get
from cls.utils.json_utils import dict_to_json
from cls.plotWidgets.utils import *

_logger = get_module_logger(__name__)

appConfig = ConfigClass(abs_path_to_ini_file)

# get the accel distance for now from the app configuration
ACCEL_DISTANCE_PERCENT_OF_RANGE = MAIN_OBJ.get_preset_as_float("coarse_accel_dist_percent_of_range")


class BaseCoarseImageScanClass(BaseScan):
    """
    This class is used to implement Coarse scans for conventional mode scanning
    """

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)
        # self.x_use_reinit_ddl = False
        # self.x_auto_ddl = True
        # self.spid_data = None
        self.img_idx_map = {}
        self.spid_data = {}
        # set a default detctor name if the user has not selected any detector from the detector selection window
        # self.default_detector_nm = "C"

    def config_devs_for_line(self, dets):
        '''
        config devs for line scan
        '''
        for d in dets:
            if hasattr(d, "set_dwell"):
                d.set_dwell(self.dwell)
            if hasattr(d, "set_config"):
                d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=self.is_pxp)
            if hasattr(d, "setup_for_hdw_triggered"):
                d.setup_for_hdw_triggered()
            if hasattr(d, "set_row_change_index_points"):
                d.set_row_change_index_points(remove_first_point=True)

    def config_devs_for_point(self, dets):
        '''
        config devs for point scan
        '''
        pass

    def configure_devs(self, dets):
        """

        """
        super().configure_devs(dets)

        if self.is_lxl:
            self.config_devs_for_line(dets)
        else:
            self.config_devs_for_point(dets)

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        move the coarse X and Y motors to the start of the scan and make sure the
        piezo motors are off
        mtr_dct =
        {'xstart': -3000.0,
         'ystart': -3238.07,
         'xpv': 'PSMTR1610-3-I12-00',
         'ypv': 'PSMTR1610-3-I12-01',
         'sx_name': 'DNM_SAMPLE_X',
         'sy_name': 'DNM_SAMPLE_Y',
         'cx_name': 'DNM_SAMPLE_X',
         'cy_name': 'DNM_SAMPLE_Y',
         'fx_name': 'DNM_SAMPLE_FINE_X',
         'fy_name': 'DNM_SAMPLE_FINE_Y',
         'fine_pv_nm': {'X': 'PZAC1610-3-I12-40', 'Y': 'PZAC1610-3-I12-41'},
         'coarse_pv_nm': {'X': 'PSMTR1610-3-I12-00', 'Y': 'PSMTR1610-3-I12-01'},
         'sample_pv_nm': {'X': 'PSMTR1610-3-I12-00', 'Y': 'PSMTR1610-3-I12-01'}}
        """

        mtr_dct = self.determine_samplexy_posner_pvs()
        mtr_x = self.main_obj.device(mtr_dct["sx_name"])
        mtr_y = self.main_obj.device(mtr_dct["sy_name"])

        accel_dist_prcnt_pv, deccel_dist_prcnt_pv = self.get_accel_deccel_pvs()

        ACCEL_DISTANCE = self.x_roi[RANGE] * accel_dist_prcnt_pv.get()
        DECCEL_DISTANCE = self.x_roi[RANGE] * deccel_dist_prcnt_pv.get()
        xstart = self.x_roi[START] - ACCEL_DISTANCE
        xstop = self.x_roi[STOP] + DECCEL_DISTANCE
        ystart, ystop = self.y_roi[START], self.y_roi[STOP]

        # check if beyond soft limits
        # if the soft limits would be violated then return False else continue and return True
        if not mtr_x.check_scan_limits(xstart, xstop, coarse_only=True):
            _logger.error("Scan would violate soft limits of X motor")
            return (False)
        if not mtr_y.check_scan_limits(ystart, ystop, coarse_only=True):
            _logger.error("Scan would violate soft limits of Y motor")
            return (False)

        #before starting scan check the interferometers, note BOTH piezo's must be off first
        mtr_x.set_piezo_power_off()
        mtr_y.set_piezo_power_off()

        mtr_x.do_interferometer_check()
        mtr_y.do_interferometer_check()

        mtr_x.move_coarse_to_scan_start(start=xstart, stop= self.x_roi[STOP], npts=self.x_roi[NPOINTS], dwell=self.dwell)
        mtr_y.move_coarse_to_position(ystart, False)

        return(True)

    def verify_scan_velocity(self):
        """
        This is meant to take a motor and check that the scan velocity is not greater than the max velocity of the motor
        To be implemented by the inheriting class

        calc_scan_velo(self, mtr, rng, npoints, dwell)
        return True for scan velo checks out and False for it is invalid
        """
        crs_x = self.main_obj.device("DNM_COARSE_X")
        #coarse scan
        self.scan_velo = self.calc_scan_velo(crs_x, self.x_roi[RANGE], self.x_roi[NPOINTS], self.dwell)
        if self.scan_velo > 0:
            return(True)
        else:
            return(False)

    def get_num_progress_events(self):
        """
        over ride base class def
        """
        if self.is_lxl:
            return self.y_roi[NPOINTS]
        else:
            #point scan
            return self.x_roi[NPOINTS] * self.y_roi[NPOINTS]

    def make_pxp_scan_plan(self, dets, bi_dir=False, md={}):
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()  # skip_lst)

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
            psmtr_x = self.main_obj.device("DNM_SAMPLE_X")
            psmtr_y = self.main_obj.device("DNM_SAMPLE_Y")
            psmtr_x.set_piezo_power_off()
            psmtr_y.set_piezo_power_off()
            mtr_x = self.main_obj.device("DNM_COARSE_X")
            mtr_y = self.main_obj.device("DNM_COARSE_Y")
            shutter = self.main_obj.device("DNM_SHUTTER")

            shutter.open()
            yield from bps.mv(mtr_x, self.x_roi['START'], group='B')
            yield from bps.mv(mtr_y, self.y_roi['START'], group='B')
            yield from bps.wait('B')
            # a scan with N events
            for y_sp in self.y_roi['SETPOINTS']:
                yield from bps.mv(mtr_y, y_sp)
                for x_sp in self.x_roi['SETPOINTS']:
                    yield from bps.mv(mtr_x, x_sp, group='BB')
                    # yield from bps.wait('BB')
                    yield from bps.trigger_and_read(dets)

            shutter.close()
            # print("CoarseSampleImageScanClass: make_pxp_scan_plan Leaving")

        return (yield from do_scan())

    def make_lxl_scan_plan(self, dets, md=None, bi_dir=False):
        """
        This produces a line by line scan that uses base level plans to do the scan
        due to the sis3820 requiring it to be running before the X motor moves across the scan line

        :param dets:
        :param gate:
        :param bi_dir:
        :return:
        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list()#skip_lst)

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
            try:
                print('entering BaseCoarseImageScanClass: line_by_line do_scan')

                psmtr_x = self.main_obj.device("DNM_SAMPLE_X")
                psmtr_y = self.main_obj.device("DNM_SAMPLE_Y")
                crs_x = self.main_obj.device("DNM_COARSE_X")
                crs_y = self.main_obj.device("DNM_COARSE_Y")
                shutter = self.main_obj.device("DNM_SHUTTER")
                piezo_mtr = self.main_obj.get_sample_fine_positioner("X")
                self.is_fine_scan = False
                accel_dist_prcnt_pv, deccel_dist_prcnt_pv = self.get_accel_deccel_pvs()
                return_velo = 3500.0
                psmtr_x.set_piezo_power_off()
                psmtr_y.set_piezo_power_off()

                shutter.open()
                ACCEL_DISTANCE = self.x_roi["RANGE"] * accel_dist_prcnt_pv.get()
                DECCEL_DISTANCE = self.x_roi["RANGE"] * deccel_dist_prcnt_pv.get()

                #scan_velo = self.x_roi["RANGE"] / ((self.x_roi["NPOINTS"] * self.dwell) * 0.001)
                piezo_mtr.scan_start.put(self.x_roi['START'] - ACCEL_DISTANCE)
                #piezo_mtr.scan_stop.put(self.x_roi['STOP'] + ACCEL_DISTANCE)
                piezo_mtr.scan_stop.put(self.x_roi['STOP'] + DECCEL_DISTANCE)

                piezo_mtr.marker_start.put(self.x_roi['START'])
                piezo_mtr.marker_stop.put(self.x_roi['STOP'])
                piezo_mtr.set_marker.put(self.x_roi['START'])
                piezo_mtr.set_marker_position(self.x_roi['START'])

                # move to scan start
                yield from bps.mv(crs_x, self.x_roi['START'] - ACCEL_DISTANCE, group='BB')
                yield from bps.mv(crs_y, self.y_roi['START'], group='BB')
                yield from bps.wait('BB')

                for y_sp in self.y_roi['SETPOINTS']:
                    ACCEL_DISTANCE = self.x_roi["RANGE"] * accel_dist_prcnt_pv.get()
                    DECCEL_DISTANCE = self.x_roi["RANGE"] * deccel_dist_prcnt_pv.get()
                    # print(f"CoarseImageScan: ACCEL_DISTANCE = {ACCEL_DISTANCE}, DECCEL_DISTANCE={DECCEL_DISTANCE}")
                    crs_x.velocity.put(self.scan_velo)
                    piezo_mtr.enable_marker_position(True)
                    for d in dets:
                        if hasattr(d, 'run'):
                            yield from bps.mv(d.run, 1, group='SIS3820')
                    # yield from bps.mv(crs_y, y_sp)
                    yield from bps.mv(crs_x, self.x_roi['STOP'] + DECCEL_DISTANCE, group='BB')
                    yield from bps.wait('BB')
                    yield from bps.trigger_and_read(dets)
                    piezo_mtr.enable_marker_position(False)
                    crs_x.velocity.put(return_velo)
                    yield from bps.mv(crs_x, self.x_roi['START'] - ACCEL_DISTANCE, crs_y, y_sp, group='CC')
                    yield from bps.wait('CC')

                shutter.close()

            except LimitError as le:
                _logger.error(f"There was a problem involving a motor setpoint being larger than valid range: [{le}]")

            except FailedStatus as fe:
                _logger.error(f"Most likely a motor is sitting on a limit: [{fe}]")

        return (yield from do_scan())



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
        _logger.info("\n\nCoarseSampleImageScanClass: configuring sp_id [%d]" % sp_id)
        self.new_spatial_start_sent = False
        # initial setup and retrieval of common scan information
        self.set_spatial_id(sp_id)
        self.determine_scan_res()
        # if self.is_fine_scan:
        #     _logger.error("Scan is a fine scan, use Image Scan for this")
        #     return None

        # dct_put(self.sp_db, SPDB_RECT, (self.x_roi[START], self.y_roi[START], self.x_roi[STOP], self.y_roi[STOP]))
        # the sample motors have different modes, make a call to handle that they are setup correctly for this scan
        self.configure_sample_motors_for_scan()

        if ev_idx == 0:
            self.reset_evidx()
            self.reset_imgidx()
            # self.reset_pnt_spec_spid_idx()
            self.final_data_dir = None
            self.update_dev_data = []

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

        self.use_hdw_accel = False
        self.x_auto_ddl = False
        self.x_use_reinit_ddl = False

        # setup some convienience member variables
        self.dwell = e_roi[DWELL]
        self.numX = int(self.x_roi[NPOINTS])
        self.numY = int(self.y_roi[NPOINTS])
        self.numZX = int(self.zx_roi[NPOINTS])
        self.numZY = int(self.zy_roi[NPOINTS])
        self.numEPU = len(self.setpointsPol)
        # self.numE = self.sp_db[SPDB_EV_NPOINTS] * len(self.setpointsPol)
        self.numE = int(self.sp_db[SPDB_EV_NPOINTS])
        self.numSPIDS = len(self.sp_rois)
        self.numImages = 1

        # set some flags that are used elsewhere
        self.stack = False
        self.is_lxl = False
        self.is_pxp = False
        self.is_point_spec = False
        self.file_saved = False
        self.sim_point = 0

        # users can request that the the ev and polarity portions of the scan can be executed in different orders
        # based on the order that requires a certain what for the sscan clases to be assigned in terms of their "level" so handle that in
        # another function
        # self.set_ev_pol_order(self.ev_pol_order)
        if self.scan_sub_type == scan_sub_types.LINE_UNIDIR:
            # LINE_UNIDIR
            self.is_lxl = True

        else:
            # POINT_BY_POINT
            self.is_pxp = True

        # # depending on the scan size the positioners used in the scan will be different, use a singe
        # # function to find out which we are to use and return those names in a dct
        dct = self.determine_samplexy_posner_pvs()

        #SKIP THIS AND SEE Oct 24 2022 self.config_for_sample_holder_scan(dct)

        self.final_data_dir = self.config_hdr_datarecorder(
            self.stack, self.final_data_dir
        )
        # self.stack_scan = stack

        # make sure OSA XY is in its center
        self.move_osaxy_to_its_center()

        self.seq_map_dct = self.generate_2d_seq_image_map(
            num_evs=1, num_pols=1, nypnts=self.y_roi[NPOINTS], nxpnts=self.x_roi[NPOINTS], lxl=self.is_lxl
        )

        # THIS must be the last call
        self.finish_setup()
        # self.new_spatial_start.emit(sp_id)
        return(ret)

    def config_for_sample_holder_scan(self, dct):
        """
        this function accomplishes the following:
            - set the positoners for X and Y
            - set the sample X and Y positioners to self.sample_mtrx etc
            - determine and set the fine positioners to sample_finex etc
            - move the sample_mtrx/y to start by setting scan Mode too ScanStart then moving and waiting until stopped
            - determine if coarse or fine scan and PxP or LxL and:
                - get max velo of the x positioner
                - Determine if scan is Line Spectra
                    - if LineSpectra the number of points is Y not X
                    - calc ScanVelo, Npts and Dwell, adjusting Npts to match velo and dwell
                - Depending on coarse or fine scans calc accel/deccel range or get straight from blConfig
                - Set the MarkerStart,ScanStart/Stop etc by calling config_samplex_start_stop
                - set the X positioner velocity to the scan velo
                - set the driver Mode to LINE_UNIDIR or COARSE or whatever it needs
                - if Fine scan make sure the servo power is on
        """
        self.sample_mtrx = self.main_obj.get_sample_positioner("X")
        self.sample_mtry = self.main_obj.get_sample_positioner("Y")
        self.sample_finex = self.main_obj.get_sample_fine_positioner("X")
        self.sample_finey = self.main_obj.get_sample_fine_positioner("Y")
        self.coarse_x = self.main_obj.device("DNM_COARSE_X")
        self.coarse_y = self.main_obj.device("DNM_COARSE_Y")

        # setup X positioner
        self.sample_mtrx.set_mode(self.sample_mtrx.MODE_SCAN_START)
        self.sample_mtrx.move(dct["xstart"])
        _logger.info("Waiting for SampleX to move to start")
        self.confirm_stopped([self.sample_mtrx])
        # self.sample_finex.set_power(0)
        # self.coarse_x.move(dct["xstart"])
        # _logger.info("Waiting for SampleX to move to start")
        # self.confirm_stopped([self.coarse_x])

        # setup Y positioner
        self.sample_mtry.set_mode(self.sample_mtrx.MODE_SCAN_START)
        self.sample_mtry.move(dct["ystart"])
        _logger.info("Waiting for SampleY to move to start")
        self.confirm_stopped([self.sample_mtry])
        # self.sample_finex.set_power(0)
        # self.coarse_y.move(dct["ystart"])
        # _logger.info("Waiting for SampleY to move to start")
        # self.confirm_stopped([self.coarse_y])

        # setup X
        if self.is_pxp or self.is_point_spec:
            if self.x_roi[SCAN_RES] == COARSE:
                # scan_velo = self.get_mtr_max_velo(self.xScan.P1)
                scan_velo = self.sample_mtrx.get_max_velo()
            else:
                # scan_velo = self.get_mtr_max_velo(self.main_obj.device('DNM_SAMPLE_FINE_X))
                scan_velo = self.sample_finex.get_max_velo()

            # x needs one extra to switch the row
            npts = self.numX
            dwell = self.dwell
            accRange = 0
            deccRange = 0
            line = False
        else:
            _ev_idx = self.get_evidx()
            e_roi = self.e_rois[_ev_idx]
            vmax = self.sample_mtrx.get_max_velo()
            # its not a point scan so determine the scan velo and accRange
            if self.scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
                # for line spec scans the number of points is saved in self.numY
                (scan_velo, npts, dwell) = ensure_valid_values(
                    self.x_roi[START],
                    self.x_roi[STOP],
                    self.dwell,
                    self.numY,
                    vmax,
                    do_points=True,
                )
            else:
                (scan_velo, npts, dwell) = ensure_valid_values(
                    self.x_roi[START],
                    self.x_roi[STOP],
                    self.dwell,
                    self.numX,
                    vmax,
                    do_points=True,
                )

            if self.x_roi[SCAN_RES] == COARSE:
                accRange = calc_accRange(
                    dct["sx_name"],
                    self.x_roi[SCAN_RES],
                    self.x_roi[RANGE],
                    scan_velo,
                    dwell,
                    accTime=0.04,
                )
                deccRange = accRange
            else:
                # pick up any changes from disk from the app config file
                # appConfig.update()
                section = "SAMPLE_IMAGE_PXP"
                if self.is_lxl:
                    section = "SAMPLE_IMAGE_LXL"

                # accRange = float(appConfig.get_value(section, 'f_acc_rng'))
                # deccRange = float(appConfig.get_value(section, 'f_decc_rng'))
                accRange = self.main_obj.get_preset(section, "f_acc_rng")
                deccRange = self.main_obj.get_preset(section, "f_decc_rng")

            # the number of points may have changed in order to satisfy the dwell the user wants
            # so update the number of X points and dwell
            # self.numX = npts
            # self.x_roi[NPOINTS] = npts

            line = True
            e_roi[DWELL] = dwell
            self.dwell = dwell

        print("accRange=%.2f um" % (accRange))
        print("deccRange=%.2f um" % (deccRange))

        # move X to start
        # self.sample_mtrx.put('Mode', MODE_SCAN_START)
        # self.sample_mtrx.put('Mode', MODE_NORMAL)
        if self.is_lxl:
            # self.config_samplex_start_stop(dct['xpv'], self.x_roi[START], self.x_roi[STOP], self.numX, accRange=accRange, line=line)
            if self.x_roi[SCAN_RES] == COARSE:
                self.sample_mtrx.config_start_stop(
                    self.x_roi[START],
                    self.x_roi[STOP],
                    self.numX,
                    accRange=accRange,
                    deccRange=deccRange,
                    line=line,
                )
                self.sample_mtrx.set_velo(scan_velo)
                # self.config_samplex_start_stop(dct['sample_pv_nm']['X'], self.x_roi[START], self.x_roi[STOP], self.numX,
                # accRange=accRange, deccRange=deccRange, line=line)
            else:
                # if it is a fine scan then dont use the abstract motor for the actual scanning
                # because the status fbk timing is currently not stable
                self.sample_finex.config_start_stop(
                    self.x_roi[START],
                    self.x_roi[STOP],
                    self.numX,
                    accRange=accRange,
                    deccRange=deccRange,
                    line=line,
                )
                self.sample_finex.set_velo(scan_velo)
                # self.config_samplex_start_stop(dct['fine_pv_nm']['X'], self.x_roi[START], self.x_roi[STOP],
                #                                self.numX, accRange=accRange, deccRange=deccRange, line=line)

        # self.set_x_scan_velo(scan_velo)
        # self.confirm_stopped([self.sample_mtrx, self.sample_mtry])

        self.num_points = self.numY

        # self.confirm_stopped(self.mtr_list)
        # set teh velocity in teh sscan rec for X
        if self.is_pxp or self.is_point_spec:
            # force it to toggle, not sure why this doesnt just work
            if self.x_roi[SCAN_RES] == COARSE:
                # self.sample_mtrx.put('Mode', MODE_COARSE)
                self.sample_mtrx.set_mode(self.sample_mtrx.MODE_COARSE)

            else:
                # self.sample_mtrx.put('Mode', MODE_POINT)
                # self.sample_finex.set_power( 1)
                self.sample_mtrx.set_mode(self.sample_mtrx.MODE_POINT)
                self.sample_finex.set_power(self.sample_mtrx.POWER_ON)

            if self.y_roi[SCAN_RES] == COARSE:
                # self.sample_mtry.put('Mode', MODE_COARSE)
                self.sample_mtry.set_mode(self.sample_mtry.MODE_COARSE)
            else:
                # self.sample_mtry.put('Mode', MODE_LINE_UNIDIR)
                # self.sample_finey.set_power( 1)
                self.sample_mtry.set_mode(self.sample_mtry.MODE_LINE_UNIDIR)
                self.sample_finey.set_power(self.sample_mtry.POWER_ON)

        else:
            # force it to toggle, not sure why this doesnt just work
            if self.x_roi[SCAN_RES] == COARSE:
                # self.sample_mtrx.put('Mode', MODE_COARSE)
                self.sample_mtrx.set_mode(self.sample_mtrx.MODE_COARSE)
                # self.xScan.put('P1PV', dct['coarse_pv_nm']['X'] + '.VAL')
                # self.xScan.put('R1PV', dct['coarse_pv_nm']['X'] + '.RBV')
            #                self.xScan.put('BSPV', dct['sample_pv_nm']['X'] + '.VELO')
            # self.main_obj.device( DNM_CX_AUTO_DISABLE_POWER ).put(0) #disabled
            # self.set_sample_posner_mode(self.sample_mtrx, self.sample_finex, MODE_COARSE)
            else:
                # self.sample_mtrx.put('Mode', MODE_LINE_UNIDIR)
                self.sample_mtrx.set_mode(self.sample_mtrx.MODE_LINE_UNIDIR)

                # self.xScan.put('P1PV', dct['fine_pv_nm']['X'] + '.VAL')
                # self.xScan.put('R1PV', dct['fine_pv_nm']['X'] + '.RBV')
                # self.sample_finex.set_power( 1)
                self.sample_finex.set_power(self.sample_mtrx.POWER_ON)

            # self.main_obj.device( DNM_CX_AUTO_DISABLE_POWER ).put(1) #enabled
            # self.set_sample_posner_mode(self.sample_mtrx, self.sample_finex, MODE_LINE_UNIDIR)

            # set Y's scan mode
            if self.y_roi[SCAN_RES] == COARSE:
                # self.set_sample_posner_mode(self.sample_mtrx, self.sample_finex, MODE_COARSE)
                # self.sample_mtry.put('Mode', MODE_COARSE)
                self.sample_mtry.set_mode(self.sample_mtrx.MODE_COARSE)

                # self.yScan.put('P1PV', dct['coarse_pv_nm']['Y'] + '.VAL')
                # self.yScan.put('R1PV', dct['coarse_pv_nm']['Y'] + '.RBV')

            else:

                # self.set_sample_posner_mode(self.sample_mtrx, self.sample_finex, MODE_LINE_UNIDIR)
                # self.sample_mtry.put('Mode', MODE_NORMAL)
                # self.sample_mtry.put('Mode', MODE_LINE_UNIDIR)
                self.sample_mtry.set_mode(self.sample_mtrx.MODE_LINE_UNIDIR)
                # self.yScan.put('P1PV', dct['fine_pv_nm']['Y'] + '.VAL')
                # self.yScan.put('R1PV', dct['fine_pv_nm']['Y'] + '.RBV')
                # self.sample_finey.set_power( 1)
                self.sample_finey.set_power(self.sample_mtry.POWER_ON)

            # self.main_obj.device( DNM_CY_AUTO_DISABLE_POWER ).put(1) #enabled

    def on_scan_done(self):
        """
        called when scan is done
        turn the fine motor power back on so that it is ready for next scan type
        """
        # call base class method first
        super().on_scan_done()

        mtr_dct = self.determine_samplexy_posner_pvs()
        mtr_x = self.main_obj.device(mtr_dct["sx_name"])
        mtr_y = self.main_obj.device(mtr_dct["sy_name"])
        #mtr_x.set_piezo_power_on()
        #mtr_y.set_piezo_power_on()

