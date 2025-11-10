"""
Created on 04/11/2022

@author: bergr
"""
import os

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger

from cls.applications.pyStxm.bl_configs.base_scan_plugins.fine_image_scans.fine_image_scans import (
    BaseFineImageScansParam,
    USE_E712_HDW_ACCEL,
)

_logger = get_module_logger(__name__)


class SampleFineImageScanParam(BaseFineImageScansParam):

    data = {}

    def __init__(self, parent=None):

        if USE_E712_HDW_ACCEL:
            #super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__))
            super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS,
                             ui_path="fine_image_scans-soft-and-hdw-accel.ui")
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
                             ui_path="fine_image_scans-soft-and-hdw-accel.ui")
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
        if self.hdwAccelGrpBox.isChecked():
            return self.scan_class_hdw
        else:
            return self.scan_class_soft
