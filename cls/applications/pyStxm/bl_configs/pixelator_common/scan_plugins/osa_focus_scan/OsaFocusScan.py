"""
Created on 04/11/2022

@author: bergr
"""
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.base_scan_plugins.osa_focus_scan.OsaFocusScan import (
    BaseOsaFocusScanClass,
)

_logger = get_module_logger(__name__)


class OsaFocusScanClass(BaseOsaFocusScanClass):
    """a scan for executing a OsaFocus scan

    This class is stubbed in here in case you would like to orverride the base implementation, if you want to use
    as is there is no need to do anything else just leave as is

    """

    def __init__(self, main_obj=None):
        """
        __init__():

        :returns: None
        """
        super().__init__(main_obj=main_obj)

        self.is_pxp = False
        self.is_lxl = True
        # in working with integration with SLS Pixelator I realized that there should be a separation
        # between how the scan is executed (lxl or pxp) and how the data arrives to be plotted (lxl or pxp)
        # the scan type does not determine the plot type, so added this var so that a ScanClass can dictate which
        # plotting function type is needed for the data
        self.data_plot_type = 'line'  # or point


    def init_subscriptions(self, ew, func, det_lst):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :param det_lst is a list of detector ophyd objects
        :return:
        """
        if len(det_lst) > 0 and hasattr(det_lst[0], 'name'):
            for d in det_lst:
                if hasattr(d, 'reset'):
                    d.reset()
                d.new_plot_data.connect(func)
                self._det_subscriptions.append(d)