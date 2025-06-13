import sys
import os
import time

from PyQt5 import QtCore, QtGui, uic, QtWidgets

import queue
import atexit

# from cls.applications.pyStxm.bl10ID01 import MAIN_OBJ, POS_TYPE_BL, POS_TYPE_ES
from cls.appWidgets.main_object import POS_TYPE_BL, POS_TYPE_ES
from cls.stylesheets import master_colors, get_style, font_sizes
from cls.utils.log import get_module_logger
from cls.utils.sig_utils import disconnect_signal, reconnect_signal
from cls.scanning.paramLineEdit import dblLineEditParamObj
#from cls.applications.pyStxm.widgets.spfbk_small import Ui_Form as spfbk_small
from cls.applications.pyStxm.widgets.sp_small import Ui_Form as sp_small
from cls.applications.pyStxm.widgets.button_small_wbtn import (
    Ui_Form as btn_small_pass_a_btn,
)
from cls.applications.pyStxm.widgets.combo_small import (
    Ui_Form as combo_small_ui
)


# from cls.caWidgets.caPushBtn import caPushBtn, caPushBtnWithFbk
from cls.devWidgets.ophydPushBtn import ophydPushBtn, ophydPushBtnWithFbk
from cls.devWidgets.ophydLabelWidget import assign_aiLabelWidget
from cls.scanning.paramLineEdit import intLineEditParamObj, dblLineEditParamObj

iconsDir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "icons", "small"
)

class PositionerDetail(QtWidgets.QDialog):
    """
    The positioner detail form for each motor
    """

    changed = QtCore.pyqtSignal(float)
    do_move = QtCore.pyqtSignal(object, float)

    def __init__(self, positioner, dev_ui, mtr):
        super(PositionerDetail, self).__init__()
        uic.loadUi(os.path.join(os.path.dirname(os.path.abspath(__file__)), "positioner_detail.ui"), self)
        self.mtr = mtr
        self.positioner = positioner
        self.posner_display_name = positioner.replace("DNM_", "").replace("_", " ").title()
        self.dev_ui = dev_ui

        self.units = self.mtr.get_units()
        # load the Motor.cfg file

        # connect btn handlers
        self.setpointFld.returnPressed.connect(self.on_move_to_position)
        self.posOffsetFld.returnPressed.connect(self.on_pos_offset)
        self.upperSoftLimFld.returnPressed.connect(self.on_set_upper_lim)
        self.lowerSoftLimFld.returnPressed.connect(self.on_set_lower_lim)
        self.autoOnOffComboBox.currentTextChanged.connect(self.on_auto_on_off_combobox)

        self.changed.connect(self.update_fbk)
        self.load_motor_config()

    def load_motor_config(self):
        """
        positioner_dct = {
         'atPositionCheckInterval': 0.002,
         'atPositionCheckTimeout': 10.0,
         'autoOffMode': 'Never',
         'axisName': 'BeamShutter',
         'beamlineControlPosition': 0,
         'coarsePositioner': '',
         'description': '',
         'distributionMode': 'n',
         'finePositioner': '',
         'hardwareUnitFactor': 1.0,
         'lowerSoftLimit': 0.0,
         'maxVelocity': 0.0,
         'name': 'BeamShutter',
         'positionOffset': 0.0,
         'unit': '()',
         'upperSoftLimit': 1.0,
         'velocityUnit': '(/ms)'}

        """
        status_str = "OFF"
        if self.mtr is not None:
            self.mtr.add_callback("user_readback", self.on_change)
            # Motorname
            self.posnerNameLbl.setText(self.posner_display_name)
            #status
            status = self.mtr.get_on_off_status()
            if status:
                status_str = "ON"
            self.statusLbl.setText(status_str)
            #position fbk
            self.posFbkLbl.setText(f"{self.mtr.position:.3f}")
            #dist mode
            distribution_mode = self.mtr.get_positioner_dct_value('distributionMode')
            self.distModeLbl.setText(str(distribution_mode))
            # auto on off
            auto_off_mode = self.mtr.get_positioner_dct_value('autoOffMode')
            self.autoOnOffComboBox.setCurrentText(str(auto_off_mode))
            # positioner offset
            pos_offset = self.mtr.get_positioner_dct_value('positionOffset')
            self.posOffsetFld.setText(f"{pos_offset:.2f}")
            # upper limit
            upper_soft_lim = self.mtr.get_positioner_dct_value('upperSoftLimit')
            self.upperSoftLimFld.setText(f"{upper_soft_lim:.2f}")
            # lower limit
            lower_soft_lim = self.mtr.get_positioner_dct_value('lowerSoftLimit')
            self.lowerSoftLimFld.setText(f"{lower_soft_lim:.2f}")
            # max velocity
            max_velo = self.mtr.get_positioner_dct_value('maxVelocity')
            self.maxVeloLbl.setText(f"{max_velo:.2f}")

            # units
            self.posnerUnitsLbl.setText(self.units)
            self.posnerUnitsLbl_2.setText(self.units)
            self.posnerUnitsLbl_3.setText(self.units)
            self.posnerUnitsLbl_4.setText(self.units)
            self.posnerUnitsLbl_5.setText(self.units)
            velo_units_str = self.units.replace("(", "").replace(")", "")
            self.posnerUnitsLbl_6.setText(f"({velo_units_str}/ms)")

    def on_change(self, kwargs):
        """
        on_change: kwargs={'old_value': -456.0, 'value': 7894.0, 'timestamp': 1743786060.091927,
            'status': 0, 'severity': 0, 'precision': 5, 'lower_ctrl_limit': -11000.0, 'upper_ctrl_limit': 11000.0,
            'units': '', 'sub_type': 'value',
            'obj': <bcm.devices.zmq.motor.ZMQMotor object at 0x7f6e53fa5e10>,
            'pvname': 'CoarseX'}
        """
        # print(f"on_change: kwargs={kwargs}")
        val = kwargs["value"]
        self.changed.emit(val)

    def update_fbk(self, val):
        # print(f'on_change: {self.positioner}: {val: .3f}')
        self.posFbkLbl.setText(f"{val:.3f}")

    def on_enable(self, is_checked):
        self.mtr.set_enable(is_checked)

    def on_status(self, status: str, color=None):
        if self.mtr is not None:
            self.statusLbl.setText(str(status))
            self.statusLbl.setStyleSheet("background-color:%s;" % (color or "black"))

    def on_moving(self, is_moving):
        if is_moving:
            clr = QtGui.QColor(255, 0, 0)  # (r,g,b)
        else:
            clr = QtGui.QColor(130, 130, 130)  # (r,g,b)
            self.clear_error()
            # if(self.isdiff != is_moving):
            # 	objgraph.show_growth()
        self.isdiff = is_moving
        self.movingWgt.setStyleSheet("QWidget { background-color: %s }" % clr.name())

    # def check_calibd(self, cal):
    #     if cal:
    #         clr = QtGui.QColor(0, 255, 0)  # (r,g,b)
    #     else:
    #         clr = QtGui.QColor(255, 0, 0)  # (r,g,b)
    #     self.calibratedWgt.setStyleSheet(
    #         "QWidget { background-color: %s }" % clr.name()
    #     )

    def on_move_to_position(self):
        if self.mtr is not None:
            val = float(str(self.setpointFld.text()))
            self.mtr.move(val, wait=False)

    def on_pos_offset(self):
        if self.mtr is not None:
            val = float(str(self.posOffsetFld.text()))
            self.mtr.set_position_offset(val)

    def on_set_upper_lim(self):
        if self.mtr is not None:
            val = float(str(self.upperSoftLimFld.text()))
            self.mtr.set_high_limit(val)

    def on_set_lower_lim(self):
        if self.mtr is not None:
            val = float(str(self.lowerSoftLimFld.text()))
            self.mtr.set_low_limit(val)

    # def on(self, ischecked):
    #     if self.mtr is not None:
    #         if ischecked:
    #             self.mtr.motor_on()
    #         else:
    #             self.mtr.motor_off()

    def on_auto_on_off_combobox(self, txt_str):
        """"
        handler for when the auto on off combo box selection is changed
        """
        # print(f"on_auto_on_off_combobox: text={txt_str}")
        if self.mtr is not None:
            self.mtr.set_auto_on_off(txt_str)


