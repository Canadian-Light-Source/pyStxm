"""
Created on 04/11/2022

@author: bergr
"""

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger

from cls.applications.pyStxm.bl_configs.base_scan_plugins.focus_scan.focus_scan import (
    BaseFocusScanParam,
)
from cls.applications.pyStxm.bl_configs.pixelator_common.plugin_utils import init_scan_req_member_vars

_logger = get_module_logger(__name__)


class FocusScanParam(BaseFocusScanParam):

    data = {}

    def __init__(self, parent=None):
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS)
        self.scan_class_coarse = self.instanciate_scan_class(
            __file__, "FocusScan", "FocusScanClass"
        )
        # set the e712 class to the coarse scan class in case there is no e712 support
        self.scan_class_e712 = self.scan_class_coarse
        self.scan_class = self.scan_class_coarse
        # #override the E712 hardware support for now
        # USE_E712_HDW_ACCEL = False
        #
        # if USE_E712_HDW_ACCEL:
        #     self.scan_class_e712 = self.instanciate_scan_class(
        #         __file__, "FocusE712Scan", "FocusE712ScanClass"
        #     )
        #     self.scan_class = self.scan_class_e712
        init_scan_req_member_vars(self)


