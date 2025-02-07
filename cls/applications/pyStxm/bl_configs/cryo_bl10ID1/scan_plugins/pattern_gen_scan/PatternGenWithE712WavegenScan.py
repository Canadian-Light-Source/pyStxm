"""
Created on 04/11/2022

@author: bergr
"""
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.base_scan_plugins.pattern_gen_scan.PatternGenWithE712WavegenScan import (
    BasePatternGenWithE712WavegenScanClass,
)

_logger = get_module_logger(__name__)


class PatterGenWithE712WavegenScanClass(BasePatternGenWithE712WavegenScanClass):
    """a scan for executing a PatterGenWithE712Wavegen scan

    This class is stubbed in here in case you would like to orverride the base implementation, if you want to use
    as is there is no need to do anything else just leave as is

    """

    def __init__(self, main_obj=None):
        """
        __init__():

        :returns: None
        """
        super().__init__(main_obj=main_obj)
