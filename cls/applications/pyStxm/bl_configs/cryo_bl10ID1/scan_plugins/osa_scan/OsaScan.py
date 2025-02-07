"""
Created on 04/11/2022

@author: bergr
"""
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.base_scan_plugins.osa_scan.OsaScan import (
    BaseOsaScanClass,
)

from bcm.devices.ophyd.qt.daqmx_counter_output import trig_src_types
from cls.scan_engine.bluesky.bluesky_defs import bs_dev_modes

_logger = get_module_logger(__name__)


class OsaScanClass(BaseOsaScanClass):
    """a scan for executing a Osa scan

    This class is stubbed in here in case you would like to override the base implementation, if you want to use
    as is there is no need to do anything else just leave as is

    """

    def __init__(self, main_obj=None):
        """
        __init__():

        :returns: None
        """
        super().__init__(main_obj=main_obj)

    # example of overriding a base class implementation
    # def configure_devs(self, dets, gate):
    #     # load devices from presets
    #     gate.trig_src_pfi = self.main_obj.get_preset_as_int('pxp_trig_src_pfi', 'DAQMX')  # GATE TRIGGER PFI
    #
    #     gate.set_dwell(self.dwell)
    #     gate.set_trig_src(trig_src_types.NORMAL_PXP)
    #     gate.set_mode(bs_dev_modes.NORMAL_PXP)
    #
    #     for d in dets:
    #         if (hasattr(d, 'set_dwell')):
    #             d.set_dwell(self.dwell)
    #         if (hasattr(d, 'trig_src_pfi')):
    #             d.trig_src_pfi = gate.trig_src_pfi
