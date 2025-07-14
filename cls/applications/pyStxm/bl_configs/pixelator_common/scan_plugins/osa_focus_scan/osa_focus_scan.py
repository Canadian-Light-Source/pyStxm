"""
Created on 04/11/2022

@author: bergr
"""
import math

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger

from cls.applications.pyStxm.bl_configs.base_scan_plugins.osa_focus_scan.osa_focus_scan import (
    BaseOsaFocusScanParam,
)
from cls.applications.pyStxm.bl_configs.pixelator_common.plugin_utils import init_scan_req_member_vars

_logger = get_module_logger(__name__)


class OsaFocusScanParam(BaseOsaFocusScanParam):

    data = {}

    def __init__(self, parent=None):
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS)
        self.scan_class = self.instanciate_scan_class(
            __file__, "OsaFocusScan", "OsaFocusScanClass"
        )
        init_scan_req_member_vars(self)


    def on_set_focus_btn(self):
        """
        set focus
        """
        if self._new_zpz_pos == None:
            _logger.info("You must first select a position before you can set focus")
            notify(
                "Unable to set focus",
                "You must first select a position before you can set focus",
                accept_str="OK",
            )
            return
        self.reset_focus_btns()
        mtrz = self.main_obj.device("DNM_ZONEPLATE_Z")
        mtrx = self.main_obj.device("DNM_OSA_X")
        mtry = self.main_obj.device("DNM_OSA_Y")
        # mult by -1.0 so that it is always negative as zpz pos needs
        fl = -1.0 * math.fabs(self.main_obj.device("DNM_FOCAL_LENGTH").get_position())
        a0 = self.main_obj.device("DNM_A0").get_position()
        zp_cent = float(self._new_zpz_pos)

        # support for DCS server motors that use offsets
        if hasattr(mtrz, 'apply_delta_to_offset'):
            delta = zp_cent - float(str(self.centerZPFld.text()))
            mtrz.apply_delta_to_offset(delta)

        mtrx.move(0.0)
        mtry.move(0.0)

        #now move to Sample Focus position which is == FL - A0
        #zpz_final_pos = -1.0 * (math.fabs(fl) - math.fabs(a0))
        # for now just move to the focal length position
        zpz_final_pos = -1.0 * (math.fabs(fl))
        mtrz.move(zpz_final_pos)

        #have the plotter delete the focus image
        self._parent.reset_image_plot()