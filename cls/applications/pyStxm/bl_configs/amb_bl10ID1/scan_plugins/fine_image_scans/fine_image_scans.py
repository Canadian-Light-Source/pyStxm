"""
Created on 04/11/2022

@author: bergr
"""

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
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS)
        if USE_E712_HDW_ACCEL:
            self.scan_class = self.instanciate_scan_class(
                __file__,
                "SampleFineImageWithE712WavegenScan",
                "SampleFineImageWithE712WavegenScanClass",
            )
        else:
            self.scan_class = self.instanciate_scan_class(
                __file__, "SampleFineImageScan", "SampleFineImageScanClass"
            )
