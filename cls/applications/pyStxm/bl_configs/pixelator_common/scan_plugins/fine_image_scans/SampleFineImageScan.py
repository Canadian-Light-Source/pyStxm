"""
Created on Sept 9, 2024

@author: bergr
"""
import copy


from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

from cls.applications.pyStxm.bl_configs.base_scan_plugins.fine_image_scans.SampleFineImageScan import (
    BaseFineSampleImageScanClass,
)
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger
from cls.utils.dict_utils import dct_put, dct_get
from cls.utils.json_utils import dict_to_json

_logger = get_module_logger(__name__)

# get the accel distance for now from the app configuration
ACCEL_DISTANCE = MAIN_OBJ.get_preset_as_float("fine_accel_distance")


class FineSampleImageScanClass(BaseFineSampleImageScanClass):
    """
    This class is used to implement Coarse scans for conventional mode scanning
    """

    def __init__(self, main_obj=None):
        """
        __init__(): description

        :returns: None
        """
        super().__init__(main_obj=main_obj)
        self.x_use_reinit_ddl = False
        self.x_auto_ddl = True
        # self.spid_data = None
        self.img_idx_map = {}
        self.spid_data = {}
        self.is_pxp = True
        self.is_lxl = False
        # in working with integration with SLS Pixelator I realized that there should be a separation
        # between how the scan is executed (lxl or pxp) and how the data arrives to be plotted (lxl or pxp)
        # the scan type does not determine the plot type, so added this var so that a ScanClass can dictate which
        # plotting function type is needed for the data
        self.data_plot_type = 'line'  # or point

    def init_subscriptions(self, ew, func, det_lst):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :param det_lst is a list of detector ophyd objects
        :return:
        """
        if len(det_lst) > 0 and hasattr(det_lst[0], 'name'):
            for d in det_lst:
                if hasattr(d, 'reset'):
                    d.reset()
                d.new_plot_data.connect(func)
                self._det_subscriptions.append(d)

    def go_to_scan_start(self):
        return True

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
