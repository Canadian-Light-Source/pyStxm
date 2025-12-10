"""
Created on 08/12/2025

@author: bergr
"""
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.base_scan_plugins.fine_image_scans.SampleFineImageScan import (
    BaseSampleFineImageScanClass,
)

_logger = get_module_logger(__name__)


class SampleFineImageScanClass(BaseSampleFineImageScanClass):
    """a scan for executing a Sample Fine Scan scan

    This class is stubbed in here in case you would like to override the base implementation, if you want to use
    as is there is no need to do anything else just leave as is

    """

    def __init__(self, main_obj=None):
        """
        __init__():

        :returns: None
        """
        super().__init__(main_obj=main_obj)