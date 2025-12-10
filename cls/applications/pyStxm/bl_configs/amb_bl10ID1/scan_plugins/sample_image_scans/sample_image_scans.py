"""
Created on 04/11/2022

@author: bergr
"""
import os

from cls.applications.pyStxm import abs_path_to_ini_file
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger
from cls.utils.dict_utils import dct_get
from cls.utils.roi_dict_defs import WDGCOM_SPATIAL_ROIS, SPDB_XRANGE, SPDB_YRANGE
from cls.utils.cfgparser import ConfigClass

from cls.applications.pyStxm.bl_configs.base_scan_plugins.sample_image_scans.sample_image_scans import (
    BaseSampleImageScansParam,
    USE_E712_HDW_ACCEL,
)

appConfig = ConfigClass(abs_path_to_ini_file)

MAX_FINE_RANGE_X = MAIN_OBJ.get_preset_as_float("max_fine_x")
MAX_FINE_RANGE_Y = MAIN_OBJ.get_preset_as_float("max_fine_y")

_logger = get_module_logger(__name__)


class SampleImageScanParam(BaseSampleImageScansParam):

    data = {}

    def __init__(self, parent=None):

        if USE_E712_HDW_ACCEL:
            super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS,
                             ui_path="sample_image_scans-soft-and-hdw-accel.ui")

            self.scan_class_coarse = self.instanciate_scan_class(
                __file__,
                "CoarseImageScan",
                "CoarseImageScanClass",
            )


            self.scan_class_hdw = self.instanciate_scan_class(
                __file__,
                "SampleFineImageWithE712WavegenScan",
                "SampleFineImageWithE712WavegenScanClass",
            )

            self.scan_class_soft = self.instanciate_scan_class(
                __file__, "SampleFineImageScan", "SampleFineImageScanClass"
            )
            self.scan_class = self.scan_class_soft
        else:
            super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS,
                             ui_path="sample_image_scans-soft-and-hdw-accel.ui")
            self.scan_class_hdw = None
            self.scan_class_soft = self.instanciate_scan_class(
                __file__, "SampleFineImageScan", "SampleFineImageScanClass"
            )
            self.scan_class = self.scan_class_soft

    def get_scan_class(self):
        """
        override the base class method to return the appropriate scan class based on whether
        hardware acceleration is enabled or not
        :return:
        """
        wdg_com = self.update_data()
        sp_rois = wdg_com[WDGCOM_SPATIAL_ROIS]
        sp_ids = list(sp_rois.keys())
        sp_id = sp_ids[0]
        sp_db = sp_rois[sp_id]
        rngX = dct_get(sp_db, SPDB_XRANGE)
        rngY = dct_get(sp_db, SPDB_YRANGE)

        is_coarse_scan = False
        if rngX >= MAX_FINE_RANGE_X:
            is_coarse_scan = True
        if rngY >= MAX_FINE_RANGE_Y:
            is_coarse_scan = True

        if is_coarse_scan:
            return self.scan_class_coarse

        elif self.hdwAccelGrpBox.isChecked():
            return self.scan_class_hdw
        else:
            return self.scan_class_soft
