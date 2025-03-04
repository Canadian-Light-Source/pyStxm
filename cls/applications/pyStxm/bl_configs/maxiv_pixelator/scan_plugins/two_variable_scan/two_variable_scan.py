"""
Created on 04/11/2022

@author: bergr
"""
from PyQt5 import QtCore
import os
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.log import get_module_logger

from cls.applications.pyStxm.bl_configs.base_scan_plugins.two_variable_scan.two_variable_scan import (
    BaseTwoVariableScanParam,
)
from cls.applications.pyStxm.bl_configs.maxiv_pixelator.plugin_utils import init_scan_req_member_vars

_logger = get_module_logger(__name__)

PREC=3

class TwoVariableScanParam(BaseTwoVariableScanParam):

    data = {}

    def __init__(self, parent=None):
        super().__init__(main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__))
        self.scan_class = self.instanciate_scan_class(
            __file__, "TwoVariableScan", "TwoVariableScanClass"
        )
        init_scan_req_member_vars(self)

        self.name = "Motor2D Scan"


    def populate_variable_cbox(self, category='POSITIONERS', primary_selected_motor=''):
        """
        populate the primary and secondary motor combo box's
        this function can be called with the name of the selected primary motor, this will be used to skip adding that
        motor to the secondary list thereby guard railing the user into not selecting ht esame motor for both primary and
        secondary
        """
        devices = self.main_obj.get_devices_in_category("POSITIONERS")
        self.primVarComboBox.clear()
        self.secVarComboBox.clear()
        self.var_dct = {}
        idx = 0
        keys = list(devices.keys())
        keys.sort()
        # load both Primary and Secondary with positioner names
        for var in keys:
            dev_display_name = self.generate_display_name(var)
            self.primVarComboBox.addItem(dev_display_name)
            self.var_dct[idx] = {'name': var, 'dev': devices[var]}
            idx += 1
            if primary_selected_motor != dev_display_name:
                self.secVarComboBox.addItem(dev_display_name)
            else:
                # add this dev name then disable it because it is already selected as the primary
                # add it but disabled
                self.secVarComboBox.addItem(dev_display_name)
                index = self.secVarComboBox.findText(dev_display_name)
                model = self.secVarComboBox.model()
                item = model.item(index)  # Access the second item (index 1)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)  # Disable the item

        #set default selections of first and second motors for primary and secondary
        self.primVarComboBox.setCurrentIndex(0)
        self.prim_variable_changed(0)
        self.secVarComboBox.setCurrentIndex(1)
        self.sec_variable_changed(1)
        x_dev, x_mtr_name, x_units = self.get_selected_dev_name_and_units('primary')
        y_dev, y_mtr_name, y_units = self.get_selected_dev_name_and_units('secondary')
        self.axis_strings = [f"{y_dev.name} {y_units}", f"{x_dev.name} {x_units}", "", ""]
        self.update_plot_strs.emit(self.axis_strings)




