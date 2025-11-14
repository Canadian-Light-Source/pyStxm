"""
Created on Sep 26, 2016

@author: bergr
"""
# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *

from bluesky.plans import scan_nd
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from cycler import cycler


from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.scanning.BaseScan import BaseScan
from cls.utils.roi_dict_defs import *

from cls.types.stxmTypes import scan_sub_types
from cls.utils.log import get_module_logger
from cls.utils.json_utils import dict_to_json
from cls.utils.dict_utils import dct_get
from bcm.devices.ophyd.qt.data_emitters import ImageDataEmitter, SIS3820ImageDataEmitter
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types

_logger = get_module_logger(__name__)


class BaseOsaFocusScanClass(BaseScan):
    """a scan for executing a detector point scan in X and Y, it takes an existing instance of an XYZScan class"""

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :param main_obj=None: main_obj=None description
        :type main_obj=None: main_obj=None type

        :returns: None
        """
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)
        self._prev_zpz_pos = None
        # self.default_detector_nm = "DNM_DEFAULT_COUNTER"

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
                d.set_config(self.y_roi["NPOINTS"], self.x_roi["NPOINTS"], is_pxp_scan=True)
            if hasattr(d, "setup_for_software_triggered"):
                d.setup_for_software_triggered()
            if hasattr(d, "set_row_change_index_points"):
                # use defaults of all args = False
                d.set_row_change_index_points()

    def get_num_points_in_scan(self):
        """
        overriddden by inheriting class
        """
        # self.numX = dct_get(self.sp_db, SPDB_XNPOINTS)
        # self.numY = dct_get(self.sp_db, SPDB_YNPOINTS)
        # self.numZ = dct_get(self.sp_db, SPDB_ZNPOINTS)
        # self.numZZ = dct_get(self.sp_db, SPDB_ZZNPOINTS)
        # self.numZX = dct_get(self.sp_db, SPDB_ZXNPOINTS)
        # self.numZY = dct_get(self.sp_db, SPDB_ZYNPOINTS)
        # self.numE = dct_get(self.sp_db, SPDB_EV_NPOINTS)
        return self.numX * self.numZZ

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        call a specific scan start for fine scans
        """

        mtr_x = self.main_obj.device("DNM_OSA_X")
        mtr_y = self.main_obj.device("DNM_OSA_Y")
        mtr_z = self.main_obj.device("DNM_ZONEPLATE_Z")

        #init the previous zoneplate z position so that when the user clicks
        #set_zp_to_focus this value can be used if needed
        self._prev_zpz_pos = mtr_z.get_position()

        xstart, xstop = self.x_roi[START], self.x_roi[STOP]
        ystart, ystop = self.y_roi[START], self.y_roi[STOP]
        zzstart, zzstop = self.zz_roi[START], self.zz_roi[STOP]

        # check if beyond soft limits
        # if the soft limits would be violated then return False else continue and return True
        if not mtr_x.check_scan_limits(xstart, xstop):
            _logger.error("Scan would violate soft limits of X motor")
            return (False)
        if not mtr_y.check_scan_limits(ystart, ystop):
            _logger.error("Scan would violate soft limits of Y motor")
            return (False)
        if not mtr_z.check_scan_limits(zzstart, zzstop):
            _logger.error("Scan would violate soft limits of ZZ motor")
            return (False)

        mtr_x.move(xstart)
        mtr_y.move(ystart)
        mtr_z.move(zzstart)

        return(True)

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
                x="DNM_OSA_X",
                scan_type=self.scan_type,
                bi_dir=self._bi_dir,
            )
        else:
            self._emitter_cb = ImageDataEmitter(
                self.default_detector_nm,
                y="DNM_ZONEPLATE_Z",
                x="DNM_OSA_X",
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

    def make_pxp_scan_plan(self, dets, md=None, bi_dir=False):
        """
        make_pxp_scan_plan(): description

        :param dets: dets description
        :type dets: dets type

        :param md=None: md=None description
        :type md=None: md=None type

        :param bi_dir=False: bi_dir=False description
        :type bi_dir=False: bi_dir=False type

        :returns: None
        """
        dev_list = self.main_obj.main_obj[DEVICES].devs_as_list(skip_lst=["DNM_RING_CURRENT"])
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
            """
            do_scan(): description

            :param defdo_scan(: defdo_scan( description
            :type defdo_scan(: defdo_scan( type

            :returns: None
            """
            mtr_x = self.main_obj.device("DNM_OSA_X")
            mtr_y = self.main_obj.device("DNM_OSA_Y")
            mtr_z = self.main_obj.device("DNM_ZONEPLATE_Z")
            shutter = self.main_obj.device("DNM_SHUTTER")

            # x_traj = cycler(mtr_x, self.x_roi[SETPOINTS])
            # y_traj = cycler(mtr_y, self.y_roi[SETPOINTS])
            # zz_traj = cycler(mtr_z, self.zz_roi[SETPOINTS])
            #
            # shutter.open()
            # # the detector will be staged automatically by the grid_scan plan
            # yield from scan_nd(dets, zz_traj * (y_traj + x_traj), md=md)

            setpoints = list(zip(self.x_roi['SETPOINTS'], self.y_roi['SETPOINTS']))
            for z_sp in self.zz_roi['SETPOINTS']:
                yield from bps.mv(mtr_z, z_sp, group='ZZ')
                yield from bps.wait('ZZ')
                for spts in setpoints:
                    x_sp, y_sp = spts
                    yield from bps.mv(mtr_x, x_sp, mtr_y, y_sp, group='BB')
                    yield from bps.wait('BB')
                    yield from bps.trigger_and_read(dets)

            shutter.close()
            # print("OsaFocusScanClass: make_scan_plan Leaving")

        return (yield from do_scan())

    def configure(self, wdg_com, sp_id=0, line=False, restore=True, z_enabled=True):
        """
        configure(): description

        :param wdg_com: wdg_com description
        :type wdg_com: wdg_com type

        :param sp_id=0: sp_id=0 description
        :type sp_id=0: sp_id=0 type

        :param line=False: line=False description
        :type line=False: line=False type

        :param restore=True: restore=True description
        :type restore=True: restore=True type

        :param z_enabled=True: z_enabled=True description
        :type z_enabled=True: z_enabled=True type

        :returns: None
        """
        # call the base class configure so that all member vars can be initialized
        ret = super().configure(wdg_com, sp_id=sp_id, line=line, z_enabled=z_enabled)
        if not ret:
            return(ret)

        self.is_pxp = True
        self.sub_type = scan_sub_types.POINT_BY_POINT

        self.configure_x_y_z_arb_linescan(wdg_com, sp_id=sp_id, line=line, z_enabled=z_enabled)
        self.move_zpxy_to_its_center()

        self.seq_map_dct = self.generate_2d_seq_image_map(1, 1, self.zz_roi[NPOINTS], self.x_roi[NPOINTS], lxl=False)
        self.finish_setup()
        return(ret)

    def on_scan_done(self):
        """
        called when scan is done

        """
        pass