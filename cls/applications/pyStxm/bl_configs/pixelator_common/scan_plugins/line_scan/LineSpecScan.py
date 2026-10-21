"""
Created on 04/11/2022

@author: bergr
"""
from cls.utils.log import get_module_logger
from cls.applications.pyStxm.bl_configs.base_scan_plugins.line_scan.LineSpecScan import (
    BaseLineSpecScanClass,
)
from cls.utils.roi_dict_defs import *
from cls.scanning.baseScanClass import get_sequence_nums, get_rows

_logger = get_module_logger(__name__)


class LineSpecScanClass(BaseLineSpecScanClass):
    """a scan for executing a LineSpec scan

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
        seq_map = self.gen_spid_seq_map(self._master_sp_id_list, self.ev_setpoints)
        if len(det_lst) > 0 and hasattr(det_lst[0], 'name'):
            for d in det_lst:
                if hasattr(d, 'reset'):
                    d.reset()
                if hasattr(d, 'set_line_spec_scan'):
                    d.set_line_spec_scan()
                if hasattr(d, 'set_seq_map'):
                    d.set_seq_map(seq_map)
                if hasattr(d, 'set_return_all_spec_at_once'):
                    d.set_return_all_spec_at_once(False)
                d.new_plot_data.connect(func)
                self._det_subscriptions.append(d)


    def go_to_scan_start(self):
        return True

    def on_scan_done(self):
        """
        calls base class on_scan_done() then does some specific stuff
        call a specific on_scan_done for fine scans
        """
        super().on_scan_done(call_base_class_only=True)

    # def generate_linespec_seq_image_map(self, erois, x_roi, y_roi):
    #     """
    #         used primarily by Linespec scans that can have multiple images per scan where each image represents a
    #         different energy range and resolution
    #     :param erois:
    #     :param nxpnts:
    #     :return:
    #     """
    #
    #     def get_columns(num_cols, npnts):
    #         lst = list(range(0, num_cols))
    #         return np.repeat(lst, npnts)
    #
    #     dct = {}
    #     ev_idx = 0
    #     seq_num = 0
    #     nypnts = int(y_roi[NPOINTS])
    #     ttl_ev_npnts = 0
    #     for eroi in erois:
    #         #this needs to include polarization points as well
    #         ttl_ev_npnts += int(eroi[NPOINTS])
    #
    #     row_lst = list(range(0, nypnts))
    #     if not self.is_horiz_line:
    #         seq = get_sequence_nums(seq_num, ttl_ev_npnts * nypnts)
    #         rows = get_rows(row_lst, ttl_ev_npnts)
    #         cols = get_columns(ttl_ev_npnts, nypnts)
    #
    #         ttl = zip(seq, rows, cols)
    #         for s, r, c in ttl:
    #             dct[s] = {"img_num": 0, "row": r, "col": c}
    #     else:
    #         # each line is an event in the sequence
    #         for seq in range(seq_num, seq_num + ttl_ev_npnts):
    #             dct[seq] = {"img_num": 0, "row": 0, "col": seq}
    #
    #     return dct
