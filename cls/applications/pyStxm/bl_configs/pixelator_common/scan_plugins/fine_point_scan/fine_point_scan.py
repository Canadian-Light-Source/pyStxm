"""
Created on 04/11/2022

@author: bergr
"""
import os

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger
from cls.utils.roi_dict_defs import *
from cls.applications.pyStxm.bl_configs.base_scan_plugins.fine_point_scan.fine_point_scan import (
    BasePointSpecScanParam,
)
from cls.applications.pyStxm.bl_configs.pixelator_common.plugin_utils import (connect_scan_req_detail_flds_to_validator,
                                                                              init_scan_req_member_vars, set_scan_rec_default, scan_rec_enable_widget)
from cls.utils.roi_utils import get_sp_db_from_wdg_com, wdg_to_sp
from cls.utils.dict_utils import dct_get

_logger = get_module_logger(__name__)


class PointSpecScanParam(BasePointSpecScanParam):

    data = {}

    def __init__(self, parent=None):
        MAIN_OBJ.enable_multi_region = False
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__))
        self.scan_class = self.instanciate_scan_class(
            __file__, "PointSpecScan", "PointSpecScanClass"
        )

        init_scan_req_member_vars(self)
        # the default scan rec settings dict was created above now force tiling to be True for this plugin
        set_scan_rec_default(self, 'tiling', True)
        # disable widgets not used by this scan
        scan_rec_enable_widget(self, 'meander', False)
        scan_rec_enable_widget(self, 'y_axis_fast', False)
        scan_rec_enable_widget(self, 'auto_defocus', False)
        scan_rec_enable_widget(self, 'defocus_diam_field', False)
        connect_scan_req_detail_flds_to_validator(self)

    def update_data(self):
        self.wdg_com = super().update_data()
        # the sub type in the base plugin is checked and set each time the data is updated, it checks to see
        # if the y_roi is a horizontal line or not, we overide this here because the
        # pixelator coarse stages do not support LxL constant velocity mode scanning
        (sp_roi_dct, sp_ids, sp_id, sp_db) = wdg_to_sp(self.wdg_com)
        if len(sp_db) > 0:
            for _id in sp_ids:
                sp_db = get_sp_db_from_wdg_com(self.wdg_com, _id)
                x_roi = dct_get(sp_db, SPDB_X)
                x_roi[POSITIONER] = 'DNM_SAMPLE_FINE_X'
                y_roi = dct_get(sp_db, SPDB_Y)
                y_roi[POSITIONER] = 'DNM_SAMPLE_FINE_Y'

        return self.wdg_com
