"""
Created on Sep 26, 2016

@author: bergr
"""


from bluesky.plans import grid_scan
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.scanning.BaseScan import BaseScan
from cls.utils.roi_dict_defs import *
from cls.utils.json_utils import dict_to_json
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes
from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types
from cls.utils.log import get_module_logger


_logger = get_module_logger(__name__)


class BaseOsaScanClass(BaseScan):
    """a scan for executing a detector point scan in X and Y, it takes an existing instance of an XYZScan class"""

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)
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

    def go_to_scan_start(self):
        """
        an API function that will be called if it exists for all scans
        mainly for this scan we check the range of the scan against the soft limits
        return True if succesful False if not
        """

        mtr_x = self.main_obj.device("DNM_OSA_X")
        mtr_y = self.main_obj.device("DNM_OSA_Y")

        xstart, xstop = self.x_roi[START], self.x_roi[STOP]
        ystart, ystop = self.y_roi[START], self.y_roi[STOP]

        # check if beyond soft limits
        # if the soft limits would be violated then return False else continue and return True
        if not mtr_x.check_scan_limits(xstart, xstop):
            _logger.error("Scan would violate soft limits of X motor")
            return (False)
        if not mtr_y.check_scan_limits(ystart, ystop):
            _logger.error("Scan would violate soft limits of Y motor")
            return (False)

        mtr_x.move(xstart)
        mtr_y.move(ystart)

        return (True)

    def make_pxp_scan_plan(self, dets, md=None, bi_dir=False):
        """
        make_pxp_scan_plan(): description
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
        # @bpp.run_decorator(md={'entry_name': 'entry0', 'scan_type': scan_types.DETECTOR_IMAGE})
        # @bpp.stage_decorator(dets)
        @bpp.baseline_decorator(dev_list)
        @bpp.run_decorator(md=md)
        def do_scan():

            mtr_x = self.main_obj.device("DNM_OSA_X")
            mtr_y = self.main_obj.device("DNM_OSA_Y")
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
                    #yield from bps.wait('BB')
                    yield from bps.trigger_and_read(dets)

            shutter.close()
            #print("OsaScanClass: make_scan_plan Leaving")

        return (yield from do_scan())


    def configure(self, wdg_com, sp_id=0, line=False, restore=True, z_enabled=False):
        """
        configure(): description

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :param line=False: line=False description
        :type line=False: line=False type

        :param restore=True: restore=True description
        :type restore=True: restore=True type

        :param z_enabled=False: z_enabled=False description
        :type z_enabled=False: z_enabled=False type

        :returns: None
        """
        # call the base class configure so that all member vars can be initialized
        ret = super().configure(wdg_com, sp_id=sp_id, line=line, z_enabled=z_enabled)
        if not ret:
            return(ret)

        # force a point by point
        self.is_pxp = True

        self.config_basic_2d(wdg_com, sp_id=sp_id, z_enabled=False)

        self.seq_map_dct = self.generate_2d_seq_image_map(
            num_evs=1, num_pols=1, nypnts=self.y_roi[NPOINTS], nxpnts=self.x_roi[NPOINTS], lxl=False
        )
        self.move_zpxy_to_its_center()
        self.finish_setup()
        return(ret)

