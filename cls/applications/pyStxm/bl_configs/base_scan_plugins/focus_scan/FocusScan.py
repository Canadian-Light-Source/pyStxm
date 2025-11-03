"""
Created on Sep 26, 2016

@author: bergr
"""
from bluesky.plans import scan_nd
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.scanning.BaseScan import BaseScan, MODE_SCAN_START
from cls.utils.dict_utils import dct_put
from cls.utils.log import get_module_logger
from cls.utils.roi_dict_defs import *
from cls.utils.json_utils import dict_to_json
from bcm.devices.ophyd.qt.data_emitters import ImageDataEmitter, SIS3820ImageDataEmitter

USE_E712_HDW_ACCEL = MAIN_OBJ.get_preset_as_bool("USE_E712_HDW_ACCEL", "BL_CFG_MAIN")
# get the accel distance for now from the app configuration
ACCEL_DISTANCE = MAIN_OBJ.get_preset_as_float("fine_accel_distance")
ACCEL_DISTANCE_PERCENT_OF_RANGE = MAIN_OBJ.get_preset_as_float("coarse_accel_dist_percent_of_range")

_logger = get_module_logger(__name__)


class BaseFocusScanClass(BaseScan):
    """
    This scan uses the SampleX and SampleY stages which allows the scan to be done as a line by line instead of
    the point by point scan which is required by the stages that cannot trigger on position such as the OSAFocus scan
    that is why this scan is left as an X, Y, Z scan instead of an XY, Z scan
    """

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)
        self._prev_zpz_pos = None

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
        if self.is_fine_scan:
            self.scan_velo = self.calc_scan_velo(piezo_mtr_x, self.x_roi[RANGE], self.x_roi[NPOINTS], self.dwell)
        else:
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
            return self.zz_roi[NPOINTS]
        else:
            #point scan
            return self.x_roi[NPOINTS] * self.zz_roi[NPOINTS]

    def init_subscriptions(self, ew, func, dets=[]):
        """
         override the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of

        self.y_roi

        :param ew: ew description
        :type ew: ew type

        :param func: func description
        :type func: func type

        :param dets: dets is really just a dud here so that the init_subscriptions func has the correct arg signature
        :returns: None
        """
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
                self.default_detector_nm,
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
        mtr_z = self.main_obj.device("DNM_ZONEPLATE_Z")

        accel_dist_prcnt_pv, deccel_dist_prcnt_pv = self.get_accel_deccel_pvs()
        ACCEL_DISTANCE = self.x_roi[RANGE] * accel_dist_prcnt_pv.get()
        DECCEL_DISTANCE = self.x_roi[RANGE] * deccel_dist_prcnt_pv.get()
        xstart = self.x_roi[START] - ACCEL_DISTANCE
        xstop = self.x_roi[STOP] + DECCEL_DISTANCE
        ystart, ystop = self.y_roi[START] , self.y_roi[STOP]
        zzstart, zzstop = self.zz_roi[START], self.zz_roi[STOP]

        #check if beyond soft limits
        # if the soft limits would be violated then return False else continue and return True
        if not self.is_fine_scan:
            coarse_only = True
        else:
            coarse_only = False
            
        if not mtr_x.check_scan_limits(xstart, xstop, coarse_only=coarse_only):
            _logger.error("Scan would violate soft limits of X motor")
            return(False)
        if not mtr_y.check_scan_limits(ystart, ystop, coarse_only=coarse_only):
            _logger.error("Scan would violate soft limits of Y motor")
            return(False)
        if not mtr_z.check_scan_limits(zzstart, zzstop):
            _logger.error("Scan would violate soft limits of ZZ motor")
            return(False)


        if self.is_fine_scan:
            super().fine_scan_go_to_scan_start()
        else:

            mtr_z.move(zzstart)
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

            mtr_x.move_coarse_to_scan_start(start=xstart, stop=self.x_roi[STOP], npts=self.x_roi[NPOINTS], dwell=self.dwell)
            mtr_y.move_coarse_to_position(ystart, False)

            #coarse focus scan
            mtr_x.set_piezo_power_off()
            mtr_y.set_piezo_power_off()

        return(True)

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
                d.set_dwell(self.dwell)
            if hasattr(d, "set_config"):
                if self.is_horiz_line:
                    is_pxp_scan = False
                else:
                    is_pxp_scan = True
                d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=is_pxp_scan)
            if self.is_pxp:
                if hasattr(d, "setup_for_software_triggered"):
                    d.setup_for_software_triggered()
                if hasattr(d, "set_row_change_index_points"):
                    # use defaults of all args = False
                    d.set_row_change_index_points()

            else:
                if hasattr(d, "setup_for_hdw_triggered"):
                    d.setup_for_hdw_triggered()
                if hasattr(d, "set_row_change_index_points"):
                    d.set_row_change_index_points(remove_first_point=True)

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
        if md is None:
            md = {
                "metadata": dict_to_json(
                    self.make_standard_metadata(
                        entry_name="entry0", scan_type=self.scan_type, dets=dets
                    )
                )
            }
        mtr_dct = self.determine_samplexy_posner_pvs()

        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():
            psmtr_x = self.main_obj.device("DNM_SAMPLE_X")
            psmtr_y = self.main_obj.device("DNM_SAMPLE_Y")
            if self.is_fine_scan:
                mtr_x = self.main_obj.device(mtr_dct["fx_name"])
                mtr_y = self.main_obj.device(mtr_dct["fy_name"])
            else:
                psmtr_x.set_piezo_power_off()
                psmtr_y.set_piezo_power_off()
                psmtr_x = self.main_obj.device(mtr_dct["sx_name"])
                psmtr_y = self.main_obj.device(mtr_dct["sy_name"])
                mtr_x = psmtr_x.get_coarse_mtr()
                mtr_y = psmtr_y.get_coarse_mtr()
            mtr_z = self.main_obj.device("DNM_ZONEPLATE_Z")
            shutter = self.main_obj.device("DNM_SHUTTER")

            shutter.open()
            setpoints = list(zip(self.x_roi['SETPOINTS'], self.y_roi['SETPOINTS']))
            for z_sp in self.zz_roi['SETPOINTS']:
                yield from bps.mv(mtr_z, z_sp, group='ZZ')
                yield from bps.wait('ZZ')
                for spts in setpoints:
                    x_sp, y_sp = spts
                    yield from bps.mv(mtr_x, x_sp,mtr_y, y_sp, group='BB')
                    yield from bps.wait('BB')
                    yield from bps.trigger_and_read(dets)

            shutter.close()
            # print("FocusScanClass PxP: make_scan_plan Leaving")

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
                    # self.make_standard_metadata(entry_name='entry0', scan_type=self.scan_type, primary_det=self.dets_names(dets)))}
                    self.make_standard_metadata(
                        entry_name="entry0", scan_type=self.scan_type, dets=dets
                    )
                )
            }

        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)

        def do_scan():
            print('entering BaseFocusScanClass: do_scan')
            psmtr_x = self.main_obj.device("DNM_SAMPLE_X")
            psmtr_y = self.main_obj.device("DNM_SAMPLE_Y")
            crs_x = self.main_obj.device("DNM_COARSE_X")
            crs_y = self.main_obj.device("DNM_COARSE_Y")
            mtr_z = self.main_obj.device("DNM_ZONEPLATE_Z")
            shutter = self.main_obj.device("DNM_SHUTTER")
            piezo_mtr_x = self.main_obj.get_sample_fine_positioner("X")
            piezo_mtr_y = self.main_obj.get_sample_fine_positioner("Y")
            accel_dist_prcnt_pv, deccel_dist_prcnt_pv = self.get_accel_deccel_pvs()

            if self.is_fine_scan:
                psmtr_x.set_piezo_power_on()
                psmtr_y.set_piezo_power_on()
                shutter.open()
                # det = dets[0]
                sisdev = dets[0]
                ACCEL_DISTANCE = self.x_roi["RANGE"] * accel_dist_prcnt_pv.get()
                DECCEL_DISTANCE = self.x_roi["RANGE"] * deccel_dist_prcnt_pv.get()
                piezo_mtr_x.scan_start.put(self.x_roi['START'] - ACCEL_DISTANCE)
                piezo_mtr_x.scan_stop.put(self.x_roi['STOP'] + DECCEL_DISTANCE)
                print(f"SampleFocusScan: ACCEL_DISTANCE = {ACCEL_DISTANCE}, DECCEL_DISTANCE={DECCEL_DISTANCE}")
                piezo_mtr_x.marker_start.put(self.x_roi['START'])
                piezo_mtr_x.marker_stop.put(self.x_roi['STOP'])
                piezo_mtr_x.set_marker.put(self.x_roi['START'])
                piezo_mtr_x.set_marker_position(self.x_roi['START'])


                yield from bps.mv(piezo_mtr_x, self.x_roi['START'] - ACCEL_DISTANCE, group='BB')
                yield from bps.mv(piezo_mtr_y, self.y_roi['CENTER'], group='BB')
                yield from bps.wait('BB')
                #
                for z_sp in self.zz_roi['SETPOINTS']:
                    yield from bps.mv(mtr_z, z_sp, group='ZZ')
                    yield from bps.wait('ZZ')
                    #re calc so that we can adjust during scan testing
                    ACCEL_DISTANCE = self.x_roi["RANGE"] * accel_dist_prcnt_pv.get()
                    DECCEL_DISTANCE = self.x_roi["RANGE"] * deccel_dist_prcnt_pv.get()

                    piezo_mtr_x.velocity.put(self.scan_velo)
                    piezo_mtr_x.enable_marker_position(True)
                    yield from bps.mv(sisdev.run, 1, group='SIS3820')

                    yield from bps.mv(piezo_mtr_x, self.x_roi['STOP'] + DECCEL_DISTANCE, group='BB')
                    yield from bps.wait('BB')
                    yield from bps.trigger_and_read(dets)
                    piezo_mtr_x.enable_marker_position(False)

                    piezo_mtr_x.velocity.put(2000)
                    yield from bps.mv(piezo_mtr_x, self.x_roi['START'] - ACCEL_DISTANCE, group='CC')
                    yield from bps.wait('CC')
                    # print("bottom of loop")
                shutter.close()

            else:
                #coarse focus scan
                psmtr_x.set_piezo_power_off()
                psmtr_y.set_piezo_power_off()
                shutter.open()
                ACCEL_DISTANCE = self.x_roi["RANGE"] * ACCEL_DISTANCE_PERCENT_OF_RANGE
                sisdev = dets[0]
                piezo_mtr_x.scan_start.put(self.x_roi['START'] - ACCEL_DISTANCE)
                piezo_mtr_x.scan_stop.put(self.x_roi['STOP'] + ACCEL_DISTANCE)
                piezo_mtr_x.marker_start.put(self.x_roi['START'])
                piezo_mtr_x.marker_stop.put(self.x_roi['STOP'])
                piezo_mtr_x.set_marker.put(self.x_roi['START'])
                piezo_mtr_x.set_marker_position(self.x_roi['START'])

                yield from bps.mv(crs_x, self.x_roi['START'] - ACCEL_DISTANCE, group='BB')
                yield from bps.mv(crs_y, self.y_roi['CENTER'], group='BB')
                yield from bps.wait('BB')
                # a scan with 10 events
                for z_sp in self.zz_roi['SETPOINTS']:
                    yield from bps.mv(mtr_z, z_sp)

                    ACCEL_DISTANCE = self.x_roi["RANGE"] * accel_dist_prcnt_pv.get()
                    DECCEL_DISTANCE = self.x_roi["RANGE"] * deccel_dist_prcnt_pv.get()

                    crs_x.velocity.put(self.scan_velo)
                    piezo_mtr_x.enable_marker_position(True)
                    yield from bps.mv(sisdev.run, 1, group='SIS3820')

                    yield from bps.mv(crs_x, self.x_roi['STOP'] + DECCEL_DISTANCE, group='BB')
                    yield from bps.wait('BB')
                    yield from bps.trigger_and_read(dets)
                    piezo_mtr_x.enable_marker_position(False)

                    crs_x.velocity.put(2000)
                    yield from bps.mv(crs_x, self.x_roi['START'] - ACCEL_DISTANCE, group='CC')
                    yield from bps.wait('CC')
                shutter.close()

            # yield from bps.unstage(gate)
            # yield from bps.unstage(line_counter)

            # print("BaseFocusScanClass LxL: make_scan_plan Leaving")

        return (yield from do_scan())

    def on_this_scan_done(self):
        """
        on_this_scan_done(): description

        :returns: None
        """
        # stop gate and counter input tasks
        # self.gate.stop()
        # self.counter.stop()
        # self.on_this_data_level_done()
        pass

    def configure(self, wdg_com, sp_id=0, line=False):
        """
        configure(): description

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :param line=False: line=False description
        :type line=False: line=False type

        :returns: None
        """
        """ here if line == True then it is a line scan else config for point by point """
        ret = super().configure(wdg_com, sp_id=sp_id, line=line, z_enabled=True)
        if not ret:
            return(ret)

        if USE_E712_HDW_ACCEL:
            self.main_obj.device("DNM_E712_CURRENT_SP_ID").put(sp_id)

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

        # also sets the scan res for x and y as well as turns off AutoDisable
        self.configure_sample_motors_for_scan()

        self.dwell = self.e_rois[0][DWELL]
        self.numZX = self.zx_roi[NPOINTS]
        self.numZY = self.zy_roi[NPOINTS]

        self.reset_evidx()
        self.reset_imgidx()
        self.stack = False

        # make sure OSA XY is in its center
        self.move_osaxy_to_its_center()

        # self.data_shape = ('numE', 'numZ', 'numX')
        self.config_hdr_datarecorder(self.stack)
        # self.stack_scan = stack

        self.seq_map_dct = self.generate_2d_seq_image_map(
            1, 1, self.zz_roi[NPOINTS], self.x_roi[NPOINTS], lxl=self.is_lxl
        )

        # THIS must be the last call
        self.finish_setup()

        # added this to try and stabalize the start of the scan (sends lines before proper start)
        # self.gate.wait_till_running_polling()
        # self.counter.wait_till_running_polling()
        return(ret)


    