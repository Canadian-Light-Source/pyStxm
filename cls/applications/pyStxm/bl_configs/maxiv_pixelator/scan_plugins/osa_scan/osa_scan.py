"""
Created on 04/11/2022

@author: bergr
"""

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger

from cls.applications.pyStxm.bl_configs.base_scan_plugins.osa_scan.osa_scan import (
    BaseOsaScanParam,
)
from cls.applications.pyStxm.bl_configs.sls_pixelator.plugin_utils import init_scan_req_member_vars

_logger = get_module_logger(__name__)


class OsaScanParam(BaseOsaScanParam):

    data = {}

    def __init__(self, parent=None):
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS)
        self.scan_class = self.instanciate_scan_class(
            __file__, "OsaScan", "OsaScanClass"
        )
        init_scan_req_member_vars(self)
