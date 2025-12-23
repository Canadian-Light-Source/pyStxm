"""
Created on 2014-07-15

@author: bergr
"""
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
from cls.utils.importing import dynamic_import
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

mtrDetailDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")

# motor internal status
NONFLOAT, OUTSIDE_LIMITS, UNCONNECTED = -13, -12, -11
TIMEOUT, TIMEOUT_BUTDONE = -8, -7
UNKNOWN_ERROR = -5
DONEW_SOFTLIM, DONEW_HARDLIM = -4, -3
DONE_OK = 0
MOVE_BEGUN, MOVE_BEGUN_CONFIRMED = 0, 1
NOWAIT_SOFTLIM, NOWAIT_HARDLIM = 4, 3
MIN_MTR_FLD_NM_WIDTH = 300
MAX_UNITS_WIDTH = 40
FEEDBACK_DELAY = 100

_sp_not_moving = master_colors["app_ltgray"]["rgb_str"]
_fbk_not_moving = master_colors["app_superltblue"]["rgb_str"]
_fbk_moving = master_colors["fbk_moving_ylw"]["rgb_str"]
_fbk_hardstopped = master_colors["fbk_hard_stopped"]["rgb_str"]
_fbk_at_limit_true = master_colors["fbk_limit_bad"]["rgb_str"]
_fbk_at_limit_false = master_colors["fbk_limit_okay"]["rgb_str"]
_master_font_size = font_sizes["master_font_size"]
_pbtn_font_size = font_sizes["pbtn_font_size"]

_logger = get_module_logger(__name__)

MTR_FEEDBACK_FORMAT = "%6.3f"

class PositionersPanel(QtWidgets.QWidget):
    """
    This is a widget that takes from the arg 'positioner_set' the positioners to filter from the
    master device list in the main object. This allows this Panel to present a panel of Endstation or Beamline
    positioners depending.
    positioner_set='endstation'
    :param positioner_set: a string that is used to decide which positioners to include on the panel. Supported
                    options are:
                            'endstation'
                            'beamline'

    :type string:

    :returns:  None
    """
    combo_fbk_changed = QtCore.pyqtSignal(object)
    # used when the device the combo box is connected to
    # changes value outside of being set here in motorPanel

    # def __init__(self, positioner_set='ES', exclude_list=[], main_obj=None, parent=None):
    def __init__(self, devs_dct, exclude_list=[], main_obj=None, parent=None):
        super().__init__(parent)
        self.exclude_list = exclude_list
        self.enum_list = ["EPUPolarization", "EPUHarmonic", "Branch"]
        self.main_obj = main_obj

        #see if the beamline configuration has over ridden the default motor_detail directory
        if self.main_obj.get_beamline_cfg_preset("motor_detail_module_path"):
            module_name = self.main_obj.get_beamline_cfg_preset("motor_detail_module_path")
            class_name = "PositionerDetail"
        else:
            # else default
            module_name = "cls.applications.pyStxm.widgets.positioner_detail"
            class_name = "PositionerDetail"

        self.PositionerDetailClass = dynamic_import(module_name, class_name)

        self.fbk_enabled = False
        self.mtr = None
        self.mtrlib = None

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(0)

        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setSpacing(2)

        self.styleBtn = QtWidgets.QPushButton("Update Style")
        self.styleBtn.clicked.connect(self.on_update_style)

        # self.vbox.addWidget(self.styleBtn)
        self.updateQueue = queue.Queue()

        self.updateTimer = QtCore.QTimer()
        self.updateTimer.timeout.connect(self.update_widgets)

        self.setLayout(self.vbox)
        self.mtr_dict = {}

        # devs_dct = self.main_obj.get_devices_in_category('POSITIONERS', pos_type=self.positioner_set)
        pos_keys = list(devs_dct.keys())
        pos_keys.sort()
        row = 0
        for dev_nm in pos_keys:
            # print dev
            if dev_nm in self.exclude_list:
                continue
            mtr = devs_dct[dev_nm]
            widg = QtWidgets.QWidget()
            if hasattr(mtr, "enums"):
                # assume it needs teh combobox setter
                dev_ui = uic.loadUi(os.path.join(mtrDetailDir, "combofbk_small.ui"), widg)
                dev_ui.spComboBox.mtr_info = (dev_nm, dev_ui, widg, mtr)
                self.connect_combobox_widgets(dev_nm, dev_ui, widg, mtr, row)
            else:
                dev_ui = uic.loadUi(os.path.join(mtrDetailDir, "spfbk_small.ui"), widg)
                dev_ui.setPosFld.installEventFilter(self)
                dev_ui.setPosFld.mtr_info = (dev_nm, dev_ui, widg, mtr)
                self.update_setpoint_field_range(dev_ui.setPosFld, mtr)
                self.connect_motor_widgets(dev_nm, dev_ui, widg, mtr, row)

            dev_ui.stopBtn.setIcon(QtGui.QIcon(os.path.join(iconsDir, "stop.png")))
            dev_ui.detailsBtn.setIcon(
                QtGui.QIcon(os.path.join(iconsDir, "details.png"))
            )
            row += 1

            self.mtr_dict[mtr.get_name()] = (dev_nm, dev_ui, widg, mtr)

        # _logger.debug('DONE uic.loadUi [%s]' % dev)
        # print 'positioner: [%s] pvname [%s]' % (dev, mtr.get_name())

        self.vbox.addLayout(self.grid_layout)

        self.fbk_enabled = False
        atexit.register(self.on_exit)
        self.enable_feedback()

    def update_setpoint_field_range(self, fld, mtr):
        llm = mtr.get_low_limit()
        hlm = mtr.get_high_limit()

        if (hlm is not None) and (llm is not None):
            if not hasattr(fld, "dpo"):
                fld.dpo = dblLineEditParamObj(fld.objectName(), llm, hlm, 2, parent=fld)
            fld.dpo._min = llm
            fld.dpo._max = hlm
        else:
            # this will need to be handled correctly in the future, for now leave myself a message
            ma_str = "pv wasnt connected yet"

    def eventFilter(self, object, event):
        """
        This event filter was primarily setup to dynamically set the min max range msgs in the ToolTips
        :param object:
        :param event:
        :return:
        """
        if event.type() == (QtCore.QEvent.ToolTip or QtCore.QEvent.FocusIn):
            (dev, dev_ui, widg, mtr) = object.mtr_info
            llm = mtr.get_low_limit()
            hlm = mtr.get_high_limit()
            if (hlm is not None) and (llm is not None):
                ma_str = "move absolute between %.3f and %.3f" % (llm, hlm)
                object.dpo._min = llm
                object.dpo._max = hlm
            else:
                # this will need to be handled correctly in the future, for now leave myself a message
                ma_str = "pv wasnt connected yet"
            object.setToolTip(ma_str)

        return QtWidgets.QWidget.eventFilter(self, object, event)

    def enable_feedback(self):
        self.updateTimer.start(FEEDBACK_DELAY)
        self.fbk_enabled = True

    def on_exit(self):
        # print 'on_exit'
        pass

    def on_update_style(self):
        """handler for interactive button"""
        self.qssheet = get_style()
        self.setStyleSheet(self.qssheet)

    def connect_motor_widgets(self, name, mtr_ui, widg, mtr, row):
        #skip_moving_sts_lst = ['PSMTR']
        _logger.debug("connect_motor_widgets[%s]" % name)
        desc = mtr.get_desc()
        pv_name = mtr.get_name()
        mtr_ui.stopBtn.clicked.connect(self.stop)
        mtr_ui.detailsBtn.clicked.connect(self.on_details)
        mtr_ui.setPosFld.returnPressed.connect(self.on_return_pressed)
        # mtr_ui.mtrNameFld.setText(desc)
        name = name.replace('DNM_', '').replace('_', ' ')
        mtr_ui.mtrNameFld.setText(name)
        mtr_ui.mtrNameFld.setToolTip(desc)
        mtr_ui.mtrNameFld.setStyleSheet(
            "border: 2 px solid %s; background-color: %s;"
            % (_fbk_not_moving, _fbk_not_moving)
        )
        mtr_ui.setPosFld.setStatusTip(pv_name)
        mtr_ui.stopBtn.setStatusTip(pv_name)
        mtr_ui.detailsBtn.setStatusTip(pv_name)

        if self.main_obj.get_device_backend() == 'zmq':
            mtr.add_callback("motor_done_move", self.zmq_update_moving)
            mtr.add_callback("user_readback", self.zmq_update_fbk)
            mtr.add_callback("spmg_enum", self.zmq_update_emerg_stop)
            mtr.add_callback("at_low_limit_val", self.zmq_update_limit_le_ds)
            mtr.add_callback("at_high_limit_val", self.zmq_update_limit_le_ds)
        else:
            mtr.add_callback("motor_done_move", self.update_moving)
            mtr.add_callback("user_readback", self.update_fbk)
            mtr.add_callback("spmg_enum", self.update_emerg_stop)
            mtr.add_callback("at_low_limit_val", self.update_limit_le_ds)
            mtr.add_callback("at_high_limit_val", self.update_limit_le_ds)

        if mtr.connected:
            #mtr_fbk = mtr.get("user_readback")
            mtr_fbk = mtr.get_position()
            if type(mtr_fbk) is float:
                s = MTR_FEEDBACK_FORMAT % mtr_fbk
                mtr_ui.posFbkLbl.setText(s)
        else:
            _logger.warn("%s is not ready to get feedback: %s" % (desc, pv_name))

        # update now whether the motor is disabled from the SPMG state
        clr_str = _fbk_hardstopped if mtr.is_hard_stopped() else _fbk_not_moving
        mtr_ui.mtrNameFld.setStyleSheet("border: 2px solid %s; background-color: %s;" % (clr_str, clr_str))

        # update now whether the motor is at a limit switch
        led_vbox = QtWidgets.QVBoxLayout()
        clr_high_limit = _fbk_at_limit_true if mtr.at_high_limit() else _fbk_at_limit_false
        mtr_ui.highLimitLED.setStyleSheet("background-color: %s;" % clr_high_limit)
        clr_low_limit = _fbk_at_limit_true if mtr.at_low_limit() else _fbk_at_limit_false
        mtr_ui.lowLimitLED.setStyleSheet("background-color: %s;" % clr_low_limit)
        led_vbox.addWidget(mtr_ui.highLimitLED)
        led_vbox.addWidget(mtr_ui.lowLimitLED)

        units = str(mtr.get_units())
        mtr_ui.unitsLbl.setText(units or "")
        mtr_ui.unitsLbl.setMaximumWidth(MAX_UNITS_WIDTH)

        self.grid_layout.addWidget(mtr_ui.mtrNameFld, row, 0)
        self.grid_layout.addWidget(mtr_ui.setPosFld, row, 1)
        self.grid_layout.addWidget(mtr_ui.posFbkLbl, row, 2)
        self.grid_layout.addLayout(led_vbox, row, 3)
        self.grid_layout.addWidget(mtr_ui.unitsLbl, row, 4)
        self.grid_layout.addWidget(mtr_ui.stopBtn, row, 5)
        self.grid_layout.addWidget(mtr_ui.detailsBtn, row, 6)
        # _logger.debug('Done[%s] \n\n' % name)

    def connect_combobox_widgets(self, name, mtr_ui, widg, mtr, row):

        _logger.debug("connect_combobox_widgets[%s]" % name)
        # populate the combo box
        mtr_ui.spComboBox.addItems(mtr.enums)
        desc = mtr.get_desc()
        pv_name = mtr.get_name()
        mtr_ui.stopBtn.clicked.connect(self.stop)
        mtr_ui.detailsBtn.clicked.connect(self.on_details)
        mtr_ui.spComboBox.currentIndexChanged.connect(self.on_combo_selection_changed)
        mtr_ui.mtrNameFld.setText(desc)
        mtr_ui.mtrNameFld.setToolTip(desc)
        mtr_ui.mtrNameFld.setStyleSheet(
            "border: 2 px solid %s; background-color: %s;"
            % (_fbk_not_moving, _fbk_not_moving)
        )
        mtr_ui.spComboBox.setStatusTip(pv_name)
        mtr_ui.stopBtn.setStatusTip(pv_name)
        mtr_ui.detailsBtn.setStatusTip(pv_name)

        # add callbacks to the ophyd EpicsMotor object
        if self.main_obj.get_device_backend() == 'zmq':
            mtr.add_callback("motor_done_move", self.zmq_update_moving)
            mtr.add_callback("user_readback", self.zmq_update_fbk)
            mtr.add_callback("spmg_enum", self.zmq_update_emerg_stop)
        else:
            mtr.add_callback("motor_done_move", self.update_moving)
            mtr.add_callback("user_readback", self.update_fbk)
            mtr.add_callback("spmg_enum", self.update_emerg_stop)

        if mtr.connected:
            mtr_fbk = mtr.get("user_readback")
            if type(mtr_fbk) is float:
                mtr_fbk = int(mtr_fbk)
                s = mtr.enums[int(mtr_fbk)]
                mtr_ui.posFbkLbl.setText(s)
                #now set teh Combo box selection without firing its setter signals
                mtr_ui.spComboBox.blockSignals(True)
                mtr_ui.spComboBox.setCurrentIndex(mtr_fbk)
                mtr_ui.spComboBox.blockSignals(False)

        else:
            _logger.warn("%s is not ready to get feedback: %s" % (desc, pv_name))

        # update now whether the motor is disabled from the SPMG state
        clr_str = _fbk_hardstopped if mtr.is_hard_stopped() else _fbk_not_moving
        mtr_ui.mtrNameFld.setStyleSheet("border: 2px solid %s; background-color: %s;" % (clr_str, clr_str))
        units = str(mtr.get_units())
        mtr_ui.unitsLbl.setText(units or "")
        mtr_ui.unitsLbl.setMaximumWidth(MAX_UNITS_WIDTH)

        # update now whether the motor is at a limit switch
        led_vbox = QtWidgets.QVBoxLayout()
        clr_high_limit = _fbk_at_limit_true if mtr.at_high_limit() else _fbk_at_limit_false
        mtr_ui.highLimitLED.setStyleSheet("background-color: %s;" % clr_high_limit)
        clr_low_limit = _fbk_at_limit_true if mtr.at_low_limit() else _fbk_at_limit_false
        mtr_ui.lowLimitLED.setStyleSheet("background-color: %s;" % clr_low_limit)
        led_vbox.addWidget(mtr_ui.highLimitLED)
        led_vbox.addWidget(mtr_ui.lowLimitLED)

        self.grid_layout.addWidget(mtr_ui.mtrNameFld, row, 0)
        self.grid_layout.addWidget(mtr_ui.spComboBox, row, 1)
        self.grid_layout.addWidget(mtr_ui.posFbkLbl, row, 2)
        self.grid_layout.addLayout(led_vbox, row, 3)
        self.grid_layout.addWidget(mtr_ui.unitsLbl, row, 4)
        self.grid_layout.addWidget(mtr_ui.stopBtn, row, 5)
        self.grid_layout.addWidget(mtr_ui.detailsBtn, row, 6)
        # _logger.debug('Done[%s] \n\n' % name)

    def update_combobox_selection(self, mtr):
        mtr_fbk = mtr.get("user_readback")
        if type(mtr_fbk) is float:
            s = MTR_FEEDBACK_FORMAT % mtr_fbk
            mtr_ui.posFbkLbl.setText(s)
            mtr_ui.spComboBox.blockSignals(True)
            mtr_ui.spComboBox.setCurrentIndex(int(mtr_fbk))
            mtr_ui.spComboBox.blockSignals(False)
    def append_widget_to_positioner_layout(self, widg):
        self.vbox.addWidget(widg)

    def append_setpoint_device(self, name, desc, units, dev, _min, _max, prec=0, cb=None, min_mtrfld_nm_width=MIN_MTR_FLD_NM_WIDTH):
        widg = QtWidgets.QWidget()
        dev_ui = sp_small()
        dev_ui.setupUi(widg)
        dev_ui.mtrNameFld.setMinimumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setMaximumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setText(name)
        dev_ui.unitsLbl.setText(units)
        desc_tt = self.format_tooltip_text(desc)
        dev_ui.mtrNameFld.setToolTip(desc_tt)
        dev_ui.mtrNameFld.setStyleSheet(
            # "border: 2 px solid %s; background-color: %s;" % (_fbk_not_moving, _fbk_not_moving))
            "border: 2 px solid %s; background-color: %s;"
            % (_sp_not_moving, _sp_not_moving)
        )

        dev_ui.setPosFld.setStatusTip(dev.get_name())

        dev_ui.setPosFld.dpo = dblLineEditParamObj(
            dev.get_name(), _min, _max, prec, parent=dev_ui.setPosFld
        )
        # dev_ui.setPosFld.dpo.valid_returnPressed.connect(on_changed_cb)
        # if the user passed a callback call it when return is pressed instead of the default handler
        if cb:
            dev_ui.setPosFld.dpo.valid_returnPressed.connect(cb)
        else:
            dev_ui.setPosFld.dpo.valid_returnPressed.connect(self.on_setpoint_dev_changed)

        self.mtr_dict[dev.get_name()] = {"dev": dev, "dev_ui": dev_ui}

        self.append_widget_to_positioner_layout(widg)

    def append_toggle_btn(self, name, desc, off_val, on_val, off_str, on_str, cb, min_mtrfld_nm_width=MIN_MTR_FLD_NM_WIDTH):
        """

        :param name:
        :param desc:
        :param off_val:
        :param on_val:
        :param off_str:
        :param on_str:
        :param cb: callback to execute when clicked
        :return:
        """
        dev_dct = {}
        dev_dct["on_val"] = on_val
        dev_dct["on_str"] = on_str
        dev_dct["off_val"] = off_val
        dev_dct["off_str"] = off_str

        ss = get_style()
        widg = QtWidgets.QWidget()
        dev_ui = btn_small_pass_a_btn()
        pBtn = QtWidgets.QPushButton()
        pBtn.setStyleSheet(
            "QPushButton{ %s;} QPushButton::indicator::checked{<b>%s</b>}		QPushButton::indicator::unchecked{<b>%s</b>}"
            % (_pbtn_font_size, on_str, off_str)
        )
        pBtn.clicked.connect(cb)
        pBtn.setStyleSheet(ss)
        dev_ui.setupUi(widg, pBtn)
        dev_ui.mtrNameFld.setMinimumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setMaximumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setText(name)
        desc_tt = self.format_tooltip_text(desc)
        dev_ui.mtrNameFld.setToolTip(desc_tt)
        _nm = name.replace(" ", "")
        id = _nm + "_btn"
        dev_ui.pushBtn.setObjectName(id)
        dev_ui.mtrNameFld.setStyleSheet(
            # "border: 2 px solid %s; background-color: %s;" % (_fbk_not_moving, _fbk_not_moving))
            "font: %s; border: 2 px solid %s; background-color: %s;"
            % (_master_font_size, _sp_not_moving, _sp_not_moving)
        )

        self.append_widget_to_positioner_layout(widg)

        # self.mtr_dict[_nm] = {'dev': None, 'dev_ui': dev_ui, dev_dct: dev_dct}

    def append_toggle_btn_device(
        self,
        name,
        desc,
        dev,
        off_val,
        on_val,
        off_str,
        on_str,
        cb=None,
        fbk_dev=None,
        toggle=True,
        min_mtrfld_nm_width=MIN_MTR_FLD_NM_WIDTH
    ):
        # assign callback if provided
        self.cb = cb
        widg = QtWidgets.QWidget()
        dev_ui = btn_small_pass_a_btn()
        if fbk_dev:
            pBtn = ophydPushBtnWithFbk(
                dev,
                sig_change_kw="value",
                off_val=off_val,
                on_val=on_val,
                off_str=off_str,
                on_str=on_str,
                fbk_dev=fbk_dev,
                toggle=toggle,
                cb=self.cb
            )
        else:
            pBtn = ophydPushBtn(
                dev,
                off_val=off_val,
                on_val=on_val,
                off_str=off_str,
                on_str=on_str,
                toggle=toggle,
                cb=self.cb
            )

        dev_ui.setupUi(widg, pBtn)
        dev_ui.mtrNameFld.setMinimumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setMaximumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setText(name)
        desc_tt = self.format_tooltip_text(desc)
        dev_ui.mtrNameFld.setToolTip(desc_tt)
        id = dev.get_name() + "_btn"
        dev_ui.pushBtn.setObjectName(id)

        _fnt_size = int(_pbtn_font_size.replace("px",""))
        font = dev_ui.pushBtn.font()
        font.setPixelSize(_fnt_size)
        dev_ui.pushBtn.setFont(font)

        dev_ui.mtrNameFld.setStyleSheet(
            # "border: 2 px solid %s; background-color: %s;" % (_fbk_not_moving, _fbk_not_moving))
            "font: bold %s; border: 2 px solid %s; background-color: %s;"
            % (_master_font_size, _sp_not_moving, _sp_not_moving)
        )

        self.append_widget_to_positioner_layout(widg)

        return pBtn

    def append_combobox_device(self,
        name,
        desc,
        dev,
        enum_strs,
        enum_vals,
        cb=None,
        min_mtrfld_nm_width=MIN_MTR_FLD_NM_WIDTH
    ):
        ss = get_style()
        self.cb = cb
        widg = QtWidgets.QWidget()
        dev_ui = combo_small_ui()
        dev_ui.setupUi(widg)
        dev_ui.comboBox.addItems(enum_strs)
        dev_ui.comboBox.setStatusTip(dev.get_name())
        dev_ui.comboBox._device = dev
        widg.setStyleSheet(ss)
        dev_ui.comboBox.currentIndexChanged.connect(self.on_non_mtr_combo_selection_changed)
        # dev_ui.setupUi(widg, pBtn)
        dev_ui.mtrNameFld.setMinimumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setMaximumWidth(min_mtrfld_nm_width)
        dev_ui.mtrNameFld.setText(name)
        desc_tt = self.format_tooltip_text(desc)
        dev_ui.mtrNameFld.setToolTip(desc_tt)
        id = dev.get_name() + "_combobox"
        # dev_ui.pushBtn.setObjectName(id)

        _fnt_size = int(_pbtn_font_size.replace("px",""))
        font = dev_ui.comboBox.font()
        font.setPixelSize(_fnt_size)
        dev_ui.comboBox.setFont(font)

        dev_ui.mtrNameFld.setStyleSheet(
            # "border: 2 px solid %s; background-color: %s;" % (_fbk_not_moving, _fbk_not_moving))
            "font: bold %s; border: 2 px solid %s; background-color: %s;"
            % (_master_font_size, _sp_not_moving, _sp_not_moving)
        )

        self.append_widget_to_positioner_layout(widg)

    def on_non_mtr_combo_selection_changed(self, pos):
        """
        the handler for when a new selection is made from a combobox, ex: Polarization
        """
        cmbo = self.sender()
        # if there is a callback provided call it, else set the device value
        if hasattr(cmbo, 'cb') and cmbo.cb:
            cmbo.cb(pos)
        else:
            dev = cmbo._device
            sts = dev.set(pos)

    def format_tooltip_text(
        self,
        msg,
        title_clr="white"
    ):
        """
        take arguments and create an html string used for tooltips
        :param title: The title will be bolded
        :param msg: The message will be simple black text
        :param title_clr: The Title will use this color
        :param newline: A flag to add a newline at the end of the string or not
        :param start_preformat: If this is the first string we need to start the PREformat tag
        :param end_preformat: If this is the last string we need to stop the PREformat tag
        :return:
        """
        s = ""
        s += f"<font size='3' color='{title_clr}'><b>{msg}</b></font>"
        return s

    def on_btn_dev_push(self, chkd):
        btn = self.sender()
        id = btn.objectName()
        dev_dct = self.mtr_dict[id]
        if chkd:
            val = dev_dct["on_val"]
            val_str = dev_dct["on_str"]
        else:
            val = dev_dct["off_val"]
            val_str = dev_dct["off_str"]

        btn.setText(val_str)
        dev_dct["dev"].put(val)

    def on_setpoint_dev_changed(self):
        fld = self.sender()
        dev_dct = self.mtr_dict[fld.id]
        dev_dct["dev"].put(fld.cur_val)

    def on_editing_finished(self):

        print("on_editing_finished")

    def update_widgets(self):

        call_task_done = False
        while not self.updateQueue.empty():
            resp = self.updateQueue.get()
            if isinstance(resp, dict):
                if "setStyleSheet" in list(resp.keys()):
                    for ss in resp["setStyleSheet"]:
                        widget = ss[0]
                        clr_str = ss[1]
                        is_moving = ss[2]
                        # print 'update_widgets: setStyleSheet(%s)' % clr_str
                        widget.setStyleSheet(clr_str)
                        call_task_done = True

                if "setText" in list(resp.keys()):
                    widget = resp["setText"][0]
                    _str = resp["setText"][1]
                    # print 'update_widgets: setText(%s)' % _str
                    widget.setText(_str)
                    call_task_done = True

                if "pvname" in list(resp.keys()):
                    (dev, dev_ui, widg, mtr) = self.mtr_dict[resp["pvname"]]
                    dev_ui.spComboBox.blockSignals(True)
                    dev_ui.spComboBox.setCurrentIndex(resp["val"])
                    dev_ui.spComboBox.blockSignals(False)

        if call_task_done:
            self.updateQueue.task_done()

    def stop(self):
        fld = self.sender()
        pvname = str(fld.statusTip())
        (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]
        mtr.stop()

    def zmq_update_moving(self, dct):
        """
        convert zmq args to kwargs like epics uses
        """
        dct['obj'].parent = QtCore.QObject()
        dct['obj'].parent.name = dct['obj'].get_name()
        dct['obj'].pvname = dct['obj'].get_name()
        self.update_moving(**dct)

    def update_moving(self, **kwargs):
        """
        do not try to set a widget property here as
        it will eventually scew up teh main GUI thread
        Hence the use of a Queue and QTimer
        """
        if not self.fbk_enabled:
            return
        is_moving = False
        if 'obj' not in kwargs.keys():
            return

        if not hasattr(kwargs['obj'], 'pvname'):
            _logger.error(f"No attribute [pvname] in kwargs['obj'] {kwargs['obj']}")
            return
        pvname = kwargs['obj'].pvname.split(".")[0]

        (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]
        val = float(kwargs["value"])
        txt_clr = "color: black;"
        # this is for the DMOV or DONE Moving, I want Moving so invert logic
        if val:
            is_moving = False
            clr_str = _fbk_not_moving
            # txt_clr = "color: black;"
        else:
            is_moving = True
            clr_str = _fbk_moving
            # txt_clr = "color: white;"

        _dct = {}
        _dct["setStyleSheet"] = [
            (
                dev_ui.mtrNameFld,
                "border: 2 px solid %s; background-color: %s;" % (clr_str, clr_str),
                is_moving,
            )
        ]
        self.updateQueue.put_nowait(_dct)

    def zmq_update_emerg_stop(self, dct):
        """
        convert zmq args to kwargs like epics uses
        """
        dct['obj'].parent = QtCore.QObject()
        #dct['obj'].parent.name = dct['obj'].get_name()
        dct["obj"].pvname = dct['obj'].get_name()
        self.update_emerg_stop(**dct)

    def update_emerg_stop(self, **kwargs):
        if not self.fbk_enabled:
            return
        #pvname = kwargs["obj"].parent.name
        pvname = kwargs["obj"].pvname.split('.')[0]
        (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]
        if mtr.is_hard_stopped():
            clr_str = _fbk_hardstopped
        else:
            clr_str = _fbk_not_moving

        _dct = {}
        _dct["setStyleSheet"] = [
            (
                dev_ui.mtrNameFld,
                "border: 2px solid %s; background-color: %s;" % (clr_str, clr_str),
                False,
            )
        ]
        self.updateQueue.put_nowait(_dct)


    def zmq_update_limit_le_ds(self, dct):
        """
        convert zmq args to kwargs like epics uses
        """
        dct['obj'].parent = QtCore.QObject()
        dct['obj'].parent.name = dct['obj'].get_name()
        self.update_limit_le_ds(**dct)

    def update_limit_le_ds(self, **kwargs):
        if not self.fbk_enabled:
            return

        pvname = kwargs["obj"].parent.name
        (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]

        clr_high_limit = _fbk_at_limit_true if mtr.at_high_limit() else _fbk_at_limit_false
        clr_low_limit = _fbk_at_limit_true if mtr.at_low_limit() else _fbk_at_limit_false

        _dct = {}
        _dct["setStyleSheet"] = [
            (
                dev_ui.highLimitLED,
                "background-color: %s;" % clr_high_limit,
                False,
            ),
            (
                dev_ui.lowLimitLED,
                "background-color: %s;" % clr_low_limit,
                False,
            ),
        ]
        self.updateQueue.put_nowait(_dct)


    def zmq_update_fbk(self, dct):
        """
        convert zmq args to kwargs like epics uses
        """
        #print(f"motorPanel: zmq_updateFbk: dct={dct}")
        dct['obj']._read_pv = QtCore.QObject()
        dct['obj']._read_pv.pvname = dct['obj'].get_name()
        dct["pvname"] = dct['obj'].get_name()
        self.update_fbk(**dct)

    def update_fbk(self, **kwargs):
        """
        do not try to set a widget property here as
        it will eventually screw up the main GUI thread
        Hence the use of a Queue and QTimer
        """
        #print(f"motorPanel: updateFbk: [{kwargs}]")
        if 'obj' not in kwargs.keys():
            print(f"motorPanel: updateFbk: NO obj in kwargs.keys()=[{kwargs}]")
            return

        if self.fbk_enabled is True:
            pvname = kwargs["obj"]._read_pv.pvname
            # print(f"motorPanel: updateFbk: {pvname} [{kwargs}]")
            if pvname.find(".") > -1:
                idx = pvname.find(".")
                pvname = pvname[0:idx]
            # (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname[0:idx]]
            (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]
            _dct = {}
            if hasattr(mtr, "enums"):
                val = int(kwargs["value"])
                # its the combop box so use the enumeration strings instead of integer value
                s = mtr.enums[val]
                _dct["pvname"] = pvname
                _dct["val"] = val
            else:
                val = float(kwargs["value"])
                s = MTR_FEEDBACK_FORMAT % val

            _dct["setText"] = (dev_ui.posFbkLbl, s)
            self.updateQueue.put_nowait(_dct)

    def on_combo_selection_changed(self, pos):
        """
        the handler for when a new selection is made from a combobox, ex: Polarization
        """
        cmbo = self.sender()
        pvname = str(cmbo.statusTip())
        (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]
        #pos = in(str(self.sender().text()))
        sts = mtr.move(pos, wait=False)


    def on_return_pressed(self):
        """
        a return pressed handler
        """
        fld = self.sender()
        pvname = str(fld.statusTip())
        (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]
        pos = float(str(self.sender().text()))
        # support for CLS collision tracking
        if hasattr(mtr, "check_tr_A"):
            mtr.check_tr_A.put(pos)
            sts = "success"
        else:
            sts = mtr.move(pos, wait=False)

        if sts == OUTSIDE_LIMITS:
            # outside the limits
            clr_str = "yellow;"
        else:
            clr_str = "white;"

        _dct = {}
        _dct["setStyleSheet"] = [
            (dev_ui.setPosFld, "background-color: " + clr_str, False)
        ]
        self.updateQueue.put_nowait(_dct)

    def check_soft_limits(self, mtr, sp):
        """
        checking the soft limits of the motor
        """
        lvio = mtr.get("soft_limit")
        if lvio == 0:
            return True
        else:
            return False

    def contextMenuEvent(self, event):
        """
        if the user right clicks in a setpoint field, this will show the valid range of allowable values as a tooltip
        """
        fld = self.sender()
        if fld:
            pvname = str(fld.statusTip())
            (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]

            # self._pvs['VAL'].connected
            # if(mtr._pvs['setpoint'].connected):
            if mtr._user_setpoint.connected:
                hlm = mtr.get_high_limit()
                llm = mtr.get_low_limit()

                if (llm is not None) and (hlm is not None):
                    ma_str = "move %s absolute between %.3f and %.3f" % (dev, llm, hlm)
            else:
                ma_str = "Motor %s not connected" % (dev)

            self.menu = QtWidgets.QMenu(self)
            renameAction = QtWidgets.QAction(ma_str, self)
            # renameAction.triggered.connect(self.renameSlot)
            self.menu.addAction(renameAction)
            # add other required actions
            self.menu.popup(QtGui.QCursor.pos())

    def on_details(self):
        """
        when the user clicks to see the details panel
        """
        fld = self.sender()
        pvname = str(fld.statusTip())
        (dev, dev_ui, widg, mtr) = self.mtr_dict[pvname]

        detForm = self.PositionerDetailClass(dev, dev_ui, mtr)
        # ss = get_style()
        # detForm.setStyleSheet(ss)
        detForm.show()
        detForm.exec_()

    def stop_all_motors(self, hard=False):
        """
        stop all motors
        """
        try:
            for pvname, (dev, dev_ui, widg, mtr) in self.mtr_dict.items():
                print("Stopping", pvname)
                if mtr and mtr.connected:
                    if hard and hasattr(mtr, "hard_stop"):
                        mtr.hard_stop()
                    else:
                        mtr.stop()
        except ValueError:
            # mtr object does not exist
            pass

    def resume_hardstopped_motors(self):
        """
        resuming from an all stop
        """
        try:
            for pvname, (dev, dev_ui, widg, mtr) in self.mtr_dict.items():
                print("Resuming", pvname)
                if mtr and mtr.connected:
                    if hasattr(mtr, "hard_stop_resume"):
                        mtr.hard_stop_resume()
        except ValueError:
            # mtr object does not exist
            pass


def go():
    app = QtWidgets.QApplication(sys.argv)
    # window = PositionersPanel('beamline')
    # window.show()
    window2 = PositionersPanel("ES")
    window2.enable_feedback()
    window2.show()

    app.exec_()


def profile_it():

    # determine_profile_bias_val()

    profile.Profile.bias = 9.95500362835e-07

    profile.run("go()", "testprof.dat")

    p = pstats.Stats("testprof.dat")
    p.sort_stats("cumulative").print_stats(100)


if __name__ == "__main__":
    import profile
    import pstats

    # log_to_qt()
    go()
    # profile_it()

    # test()
