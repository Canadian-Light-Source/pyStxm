"""
Created on 04/11/2022

@author: bergr
"""
import os

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger
from cls.stylesheets import get_style

from cls.applications.pyStxm.bl_configs.base_scan_plugins.fine_image_scans.fine_image_scans import (
    BaseFineImageScansParam,
    )
from cls.types.stxmTypes import scan_sub_types

from cls.applications.pyStxm.bl_configs.maxiv_pixelator.plugin_utils import (connect_scan_req_detail_flds_to_validator,
    init_scan_req_member_vars, set_scan_rec_default)

_logger = get_module_logger(__name__)


class SampleFineImageScanParam(BaseFineImageScansParam):

    data = {}

    def __init__(self, parent=None):
        MAIN_OBJ.enable_multi_region = False
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__))
        self.scan_class = self.instanciate_scan_class(
                __file__, "SampleFineImageScan", "FineSampleImageScanClass"
            )
        self.name = "Sample Scan"
        init_scan_req_member_vars(self)
        # the default scan rec settings dict was created above now force tiling to be True for this plugin
        set_scan_rec_default(self, 'tiling', True)

        connect_scan_req_detail_flds_to_validator(self)
        
    def update_data(self):
        self.wdg_com = super().update_data(force_pxp=True)
        # the sub type in the base plugin is checked and set each time the data is updated, it checks to see
        # if the y_roi is a horizontal line or not, we overide this here because the
        # pixelator coarse stages do not support LxL constant velocity mode scanning
        posner_name_x = 'DNM_SAMPLE_FINE_X'
        posner_name_y = 'DNM_SAMPLE_FINE_Y'

        dct = self.get_scan_request()
        if dct['coarse_only']:
            posner_name_x = 'DNM_COARSE_X'
            posner_name_y = 'DNM_COARSE_Y'

        (sp_roi_dct, sp_ids, sp_id, sp_db) = wdg_to_sp(self.wdg_com)
        if len(sp_db) > 0:
            for _id in sp_ids:
                sp_db = get_sp_db_from_wdg_com(self.wdg_com, _id)
                x_roi = dct_get(sp_db, SPDB_X)
                x_roi[POSITIONER] = posner_name_x
                y_roi = dct_get(sp_db, SPDB_Y)
                y_roi[POSITIONER] = posner_name_y

        return self.wdg_com
