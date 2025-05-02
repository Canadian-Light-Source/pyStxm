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
        self.x_use_reinit_ddl = False
        self.x_auto_ddl = True
        # self.spid_data = None
        self.img_idx_map = {}
        self.spid_data = {}
        self.is_pxp = True
        self.is_lxl = False
        # in working with integration with SLS Pixelator I realized that there should be a separation
        # between how the scan is executed (lxl or pxp) and how the data arrives to be plotted (lxl or pxp)
        # the scan type does not determine the plot type, so added this var so that a ScanClass can dictate which
        # plotting function type is needed for the data
        self.data_plot_type = 'point'  # or point

    def init_subscriptions(self, ew, func, det_lst):
        """
        over ride the base init_subscriptions because we need to use the number of rows from the self.zz_roi instead of
        self.y_roi
        :param ew:
        :param func:
        :param det_lst is a list of detector ophyd objects
        :return:
        """
        seq_map = self.gen_spid_seq_map(self._master_sp_id_list, self.ev_setpoints)
        if len(det_lst) > 0 and hasattr(det_lst[0], 'name'):
            for d in det_lst:
                d.new_plot_data.connect(func)
                if hasattr(d, 'reset'):
                    d.reset()
                if hasattr(d, 'set_spec_scan'):
                    d.set_spec_scan()
                if hasattr(d, 'set_seq_map'):
                    d.set_seq_map(seq_map)
                if hasattr(d, 'set_return_all_spec_at_once'):
                    d.set_return_all_spec_at_once(False)

                self._det_subscriptions.append(d)

    def go_to_scan_start(self):
        return True

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done()
