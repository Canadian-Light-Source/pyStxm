"""
Created on 04/11/2022

@author: bergr
"""
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.base_scan_plugins.fine_point_scan.PointSpecScan import (
    BasePointSpecScanClass,
)

_logger = get_module_logger(__name__)


class PointSpecScanClass(BasePointSpecScanClass):
    """a scan for executing a PointSpec scan

    This class is stubbed in here in case you would like to orverride the base implementation, if you want to use
    as is there is no need to do anything else just leave as is

    """

    def __init__(self, main_obj=None):
        """
        __init__():

        :returns: None
        """
        super().__init__(main_obj=main_obj)
