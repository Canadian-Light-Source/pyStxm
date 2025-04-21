"""
Created on 04/11/2022

@author: bergr
"""

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.base_scan_plugins.det_scan.det_scan import (
    BaseDetectorScanParam,
)

from cls.applications.pyStxm.bl_configs.pixelator_common.plugin_utils import init_scan_req_member_vars

_logger = get_module_logger(__name__)


class DetectorScanParam(BaseDetectorScanParam):

    data = {}

    def __init__(self, parent=None):
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS)
        self.scan_class = self.instanciate_scan_class(
            __file__, "DetectorScan", "DetectorScanClass"
        )
        self.osa_out_limit = "low"

        init_scan_req_member_vars(self)

