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

mtrDetailDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")

class PositionerDetail(QtWidgets.QDialog):
    """
    The positioner detail form for each motor
    """

    changed = QtCore.pyqtSignal(float)
    do_move = QtCore.pyqtSignal(object, float)

    def __init__(self, positioner, dev_ui, mtr):
        super(PositionerDetail, self).__init__()
        uic.loadUi(os.path.join(mtrDetailDir, "spfbk_detail.ui"), self)
        self.mtr = mtr
        self.positioner = positioner
        self.dev_ui = dev_ui

        self.units = ""
        # load the Motor.cfg file

        # connect btn handlers
        self.stopBtn.clicked.connect(self.on_stop_btn)
        self.calBtn.clicked.connect(self.calibrate)
        self.goHomeBtn.clicked.connect(self.on_home_btn)
        self.forceCalibratedBtn.clicked.connect(self.on_force_calibrated)
        self.zeroMtrBtn.clicked.connect(self.on_zero_motor)
        self.onOffBtn.clicked.connect(self.on)
        self.mtrGrpBox.clicked.connect(self.on_enable)
        self.domovesBtn.clicked.connect(self.do_moves)

        self.relSetpointFld.returnPressed.connect(self.on_move_rel_position)
        self.setpointFld.returnPressed.connect(self.on_move_to_position)
        self.setPosFld.returnPressed.connect(self.on_set_position)
        self.velFld.returnPressed.connect(self.on_set_velo)

        self.changed.connect(self.update_fbk)
        self.loadMotorConfig(self.positioner)

    def loadMotorConfig(self, positioner="AbsSampleX"):
        posner_nm = str(positioner)

        if self.mtr is not None:
            self.mtr.add_callback("user_readback", self.on_change)

        self.mtrNameFld.setText(posner_nm)
        self.unitsLbl.setText(self.units)
        # self.mtr = self.positioner
        self.loadParamsToGui(self.mtr)
        self.mtr.add_callback("ctrlr_status", self.on_status_bits)

    def loadParamsToGui(self, mtr):
        self.posFbkLbl.setText("%.3f" % (self.mtr.position))
        # self.zeroOffsetLbl.setText('%.6f' % (self.mtr.unit_offset))
        # self.absPosLbl.setText(str('%.3f' % (self.mtr.abs_position)))
        # self.encSlopeLbl.setText(str('%.6f' % (self.mtr.enc_slope)))
        # self.negWindowLbl.setText(str('%.3f' % (self.mtr.negWindow)))
        # self.posWindowLbl.setText(str('%.3f' % (self.mtr.posWindow)))

        self.velFbkLbl.setText(str("%.3f" % (self.mtr.velocity.get())))
        self.accFbkLbl.setText(str("%.3f" % (self.mtr.acceleration.get())))

    def on_change(self, **kwargs):
        # print(kwargs)
        val = kwargs["value"]
        self.changed.emit(val)

    def update_fbk(self, val):
        # print(f'on_change: {positioner}: {val: .3f}')
        self.posFbkLbl.setText("%.3f" % (val))
        # self.zeroOffsetLbl.setText('%.6f' % (self.mtr.unit_offset))
        # self.absPosLbl.setText(str('%.3f' % (self.mtr.abs_position)))
        # self.encSlopeLbl.setText(str('%.6f' % (self.mtr.enc_slope)))
        # self.negWindowLbl.setText(str('%.3f' % (self.mtr.negWindow)))
        # self.posWindowLbl.setText(str('%.3f' % (self.mtr.posWindow)))

        # self.velFbkLbl.setText(str('%.3f' % (self.mtr.velocity.get())))
        # self.accFbkLbl.setText(str('%.3f' % (self.mtr.acceleration.get())))
        # self.check_calibd()

    def on_log_msg(self, msg):
        self.logStringLbl.setText(str(msg))

    def clear_error(self):
        self.logStringLbl.setText("")

    def on_enable(self, is_checked):
        self.mtr.set_enable(is_checked)

    def on_status(self, status: str, color=None):
        if self.mtr is not None:
            self.statusLbl.setText(str(status))
            self.statusLbl.setStyleSheet("background-color:%s;" % (color or "black"))

    def on_status_bits(self, value=None, old_value=None, **kwargs):
        if value is None or value == old_value:
            return

        flags = int(value)
        at_high_limit = flags | (2 ** 2) == flags
        slip_stall = flags | (2 ** 6) == flags
        hardware_err = flags | (2 ** 9) == flags
        controller_err = flags | (2 ** 12) == flags
        at_low_limit = flags | (2 ** 13) == flags

        if hardware_err:
            self.on_status("HARDWARE ERROR", _fbk_hardstopped)
        elif controller_err:
            self.on_status("CONTROLLER ERROR", _fbk_hardstopped)
        elif slip_stall:
            self.on_status("SLIP/STALL", _fbk_hardstopped)
        elif at_high_limit:
            self.on_status("AT HIGH LIMIT", _fbk_moving)
        elif at_low_limit:
            self.on_status("AT LOW LIMIT", _fbk_moving)
        else:
            self.on_status("OK", _fbk_not_moving)

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

    def check_calibd(self, cal):
        if cal:
            clr = QtGui.QColor(0, 255, 0)  # (r,g,b)
        else:
            clr = QtGui.QColor(255, 0, 0)  # (r,g,b)
        self.calibratedWgt.setStyleSheet(
            "QWidget { background-color: %s }" % clr.name()
        )

    def on_zero_motor(self):
        if self.mtr is not None:
            self.mtr.set_current_position(0.0)

    def on_force_calibrated(self):
        if self.mtr is not None:
            self.mtr.calib_done.put(1, wait=True)

    def on_set_velo(self):
        if self.mtr is not None:
            val = float(str(self.velFld.text()))
            self.mtr.velocity.put(val, wait=True)

    def on_set_scan_start(self):
        if self.mtr is not None:
            strtval = float(str(self.scanStartFld.text()))
            rngval = float(str(self.rangeFld.text()))

            centerx = strtval + (0.5 * rngval)
            if rngval > 80:
                self.mtr.set_for_coarse_scan(True, centerx)
            else:
                self.mtr.set_for_coarse_scan(False, centerx)

            self.mtr.move_to_finescan_start(centerx, rngval)
            self.mtr.set_marker(strtval)

    def on_move_to_position(self):
        if self.mtr is not None:
            val = float(str(self.setpointFld.text()))
            self.mtr.move(val, wait=False)

    def on_move_rel_position(self):
        if self.mtr is not None:
            val = float(str(self.relSetpointFld.text()))
            self.mtr.move_by.put(val, wait=False)

    def on_set_position(self):
        if self.mtr is not None:
            val = float(str(self.setPosFld.text()))
            self.mtr.set_current_position(val)

    def on_stop_btn(self):
        if self.mtr is not None:
            # self.mtr.set_for_coarse_scan(True, -46.7)
            self.mtr.stop()

    def on_home_btn(self):
        if self.mtr is not None:
            self.mtr.go_home()
            # self.mtr.set_for_coarse_scan(False, -46.7)

    def stop(self):
        if self.mtr is not None:
            self.mtr._stop_motor()

    def calibrate(self):
        if self.mtr is not None:
            self.mtr.calibrate()

    def goHome(self):
        if self.mtr is not None:
            self.mtr.go_home(wait=False)

    def on_scan_done(self):
        print("on_scan_done: called")
        self.q.quit()

    def on(self, ischecked):
        if self.mtr is not None:
            if ischecked:
                self.mtr.motor_on()
            else:
                self.mtr.motor_off()

    def do_moves(self):
        self.moveThread.start()

        self.q.exec_()
        print("after self.q.exec_()")
        # self.moveThread.done.disconnect()
        self.moveThread.wait(50)
        self.moveThread.terminate()
        print("done")
        # objgraph.show_growth()

    def move_terminated(self):
        print("self.moveThread: finally this sucker died")

    def on_exit(self):
        pass
        # self.moveThread.wait(50)
        # self.moveThread.quit()
        # self.moveThread.terminate()
        # if(self.mtr is not None):
        # 	self.mtr.close_mtr()