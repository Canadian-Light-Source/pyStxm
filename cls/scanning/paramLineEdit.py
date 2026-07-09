"""
Created on Jun 3, 2016

@author: bergr
"""

import sys
import math
from PyQt5 import QtCore, QtGui, QtWidgets

from cls.stylesheets import master_colors


def get_valid_result_ss():
    # white for normal/accepted
    return "QLineEdit{background: rgb(255, 255, 255);}"

def get_value_modified_ss():
    # a light blue for the background to show the value is being changed
    return "QLineEdit{background: rgb(157, 213, 255);}"

def get_value_not_nominal_ss():
    # a light blue for the background to show the value is being changed
    return f"{master_colors['app_yellow']['rgb_str']};background-color: {master_colors['app_red']['rgb_str']};"



class IntParamValidator(QtGui.QIntValidator):
    # state_changed = pyqtSignal(object)
    def __init__(self, _min, _max, prec, qobj=None, lineFld=None):
        QtGui.QIntValidator.__init__(self)
        self.setRange(_min, _max)
        self.changes_locked = False

    def is_done(self):
        return self.changes_locked

    def lock_changes(self, lock):
        self.changes_locked = lock


class DblParamValidator(QtGui.QDoubleValidator):
    # state_changed = pyqtSignal(object)
    def __init__(self, _min, _max, prec, qobj=None, lineFld=None):
        QtGui.QDoubleValidator.__init__(self)
        if (_min is None) or (_max is None):
            print("dblParamValidator: _min or _max or both are None")
        else:
            self.setRange(_min, _max, prec)
        self.changes_locked = False

    def is_done(self):
        return self.changes_locked

    def lock_changes(self, lock):
        self.changes_locked = lock


class CharParamValidator(QtGui.QRegExpValidator):
    # state_changed = pyqtSignal(object)
    def __init__(self, qobj=None, lineFld=None):
        QtGui.QRegExpValidator.__init__(self)
        self.changes_locked = False
        validator = QtGui.QRegExpValidator(
            QtCore.QRegExp("[0 - 9A - Za - z_ + -.,!@  # $%^&*();\\:/|<>']"), None
        )

    def is_done(self):
        return self.changes_locked

    def lock_changes(self, lock):
        self.changes_locked = lock


class BaseLineEditParamObj(QtCore.QObject):
    valid_returnPressed = QtCore.pyqtSignal()

    def __init__(self, id, parent=None):
        QtCore.QObject.__init__(self)
        self.parent = parent
        self.id = id
        if not hasattr(self, "cur_val"):
            self.cur_val = None
        if not hasattr(self, "fmt"):
            self.fmt = "%s"
        self._style_before_edit = ""
        self._edit_session_dirty = False

        self.parent.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.parent.customContextMenuRequested.connect(self.contextMenuEvent)
        self.parent.focusInEvent = self.focusInEvent
        self.parent.focusOutEvent = self.focusOutEvent
        self.parent.returnPressed.connect(self.on_parent_rtrn_pressed)
        self.parent.textEdited.connect(self.on_parent_changed)
        self.parent.setValidator(self.build_validator())

    def build_validator(self):
        raise NotImplementedError("Subclasses must implement build_validator")

    def get_context_message(self):
        return ""

    def parse_text(self):
        return str(self.parent.text())

    def format_value(self):
        return self.fmt % self.cur_val

    def on_return_pressed(self):
        """Hook for subtype-specific returnPressed behavior."""

    def on_focus_out(self):
        """Hook for subtype-specific focusOut behavior."""

    def _apply_valid_style_if_not_custom(self):
        """Only normalize to valid style when no custom status style is active."""
        cur_ss = (self.parent.styleSheet() or "").strip()
        if cur_ss in ("", get_valid_result_ss(), get_value_modified_ss()):
            self.parent.setStyleSheet(get_valid_result_ss())

    def contextMenuEvent(self, event):
        fld = self.sender()
        if fld:
            ma_str = self.get_context_message()
            self.menu = QtWidgets.QMenu(self.parent)
            renameAction = QtWidgets.QAction(ma_str, self.parent)
            renameAction.triggered.connect(self.renameSlot)
            self.menu.addAction(renameAction)
            # add other required actions
            self.menu.popup(QtGui.QCursor.pos())

    def renameSlot(self):
        print("renaming slot called")
        # get the selected cell and perform renaming

    def focusInEvent(self, event):
        """when focus goes into field copy current value"""
        self._style_before_edit = self.parent.styleSheet()
        self._edit_session_dirty = False
        self.cur_val = self.parse_text()
        QtWidgets.QLineEdit.focusInEvent(self.parent, event)

    def focusOutEvent(self, event):
        """if user has not hit enter on the value in the field when
        focus is lost on this field then return the value to its previous value
        and set the background color"""
        v = self.parent.validator()
        if self._edit_session_dirty and (not v.is_done()):
            # User edited but did not commit with Return: restore prior value/style.
            self.parent.setText(self.format_value())
            self.parent.setStyleSheet(self._style_before_edit)
            v.lock_changes(True)
        elif v.is_done():
            self.cur_val = self.parse_text()
        else:
            self.parent.setText(self.format_value())

        self.on_focus_out()
        self._apply_valid_style_if_not_custom()
        QtWidgets.QLineEdit.focusOutEvent(self.parent, event)

    def on_parent_rtrn_pressed(self):
        self.cur_val = self.parse_text()
        self._edit_session_dirty = False
        self.on_return_pressed()
        v = self.parent.validator()
        v.lock_changes(True)
        self.parent.setStyleSheet(get_valid_result_ss())
        self.valid_returnPressed.emit()

    def on_parent_changed(self):
        v = self.parent.validator()
        v.lock_changes(False)
        if not self._edit_session_dirty:
            self._style_before_edit = self.parent.styleSheet()
        self._edit_session_dirty = True
        self.parent.setStyleSheet(get_value_modified_ss())


class IntLineEditParamObj(BaseLineEditParamObj):
    def __init__(self, id, _min, _max, prec=0, parent=None):
        self.prec = prec
        self._min = _min
        self._max = _max
        self.cur_val = (_min + _max) / 2.0
        self.fmt = "%d"
        super(IntLineEditParamObj, self).__init__(id, parent=parent)

    def build_validator(self):
        return IntParamValidator(self._min, self._max, None)

    def get_context_message(self):
        if (self._min is not None) and (self._max is not None):
            return "valid range is between %d and %d" % (self._min, self._max)
        return "Motor not connected"

    def parse_text(self):
        return int(str(self.parent.text()))

    # Backward-compatible slots.
    def on_int_parent_rtrn_pressed(self):
        self.on_parent_rtrn_pressed()

    def on_int_parent_changed(self):
        self.on_parent_changed()


class DblLineEditParamObj(BaseLineEditParamObj):
    def __init__(self, id, _min, _max, prec, is_range=False, parent=None):
        self.is_range = is_range
        self.prec = prec
        self._min = _min
        self._max = _max
        if (_min is not None) and (_max is not None):
            self.cur_val = (_min + _max) / 2.0
        else:
            self.cur_val = 0.0
        if self.prec > 0:
            self.fmt = "%." + "%df" % (self.prec)
        else:
            self.fmt = "%d"
        super(DblLineEditParamObj, self).__init__(id, parent=parent)

    def build_validator(self):
        return DblParamValidator(self._min, self._max, self.prec, None)

    def get_context_message(self):
        if (self._min is not None) and (self._max is not None):
            if self.is_range:
                return "valid range is between %.2f and %.2f" % (
                    0.0,
                    math.fabs(self._max - self._min),
                )
            return "valid range is between %.2f and %.2f" % (self._min, self._max)
        return "Motor not connected"

    def parse_text(self):
        return float(str(self.parent.text()))

    def on_return_pressed(self):
        # Preserve precision formatting on accepted values.
        self.parent.setText(self.format_value())

    def on_focus_out(self):
        self.parent.update()

    # Backward-compatible slots.
    def on_dbl_parent_rtrn_pressed(self):
        self.on_parent_rtrn_pressed()

    def on_dbl_parent_changed(self):
        self.on_parent_changed()


class CharLineEditParamObj(BaseLineEditParamObj):
    def __init__(self, id, valid_values=None, parent=None):
        self.valid_values = self._normalize_valid_values(valid_values)
        self.fmt = "%s"
        super(CharLineEditParamObj, self).__init__(id, parent=parent)

    def _normalize_valid_values(self, valid_values):
        if type(valid_values) is dict:
            s = ""
            for k in list(valid_values.keys()):
                s += "%s = %s, " % (k, valid_values[k])
            return s
        if type(valid_values) is list:
            s = ""
            for l in valid_values:
                s += "%s, " % (l)
            return s
        return valid_values

    def build_validator(self):
        return CharParamValidator()

    def get_context_message(self):
        if self.valid_values is not None:
            return "valid set of values are: %s" % (self.valid_values)
        return "No retrictions on what you can put here"

    # Backward-compatible slots.
    def on_char_parent_rtrn_pressed(self):
        self.on_parent_rtrn_pressed()

    def on_char_parent_changed(self):
        self.on_parent_changed()


class testWindow(QtWidgets.QWidget):
    """
    classdocs
    """

    def __init__(self):
        super(testWindow, self).__init__()

        scanning_modes_dct = {
            "0": "COARSE_SAMPLEFINE",
            "1": "GONI_ZONEPLATE",
            "2": "COARSE_ZONEPLATE",
        }

        scanning_modes_lst = ["COARSE_SAMPLEFINE", "GONI_ZONEPLATE", "COARSE_ZONEPLATE"]

        self.e1 = QtWidgets.QLineEdit("0.0")
        self.e2 = QtWidgets.QLineEdit("0.0")
        self.e3 = QtWidgets.QLineEdit("0.0")
        self.e4 = QtWidgets.QLineEdit(r"S:\STXM-data\Cryo-STXM\2017")
        self.e5 = QtWidgets.QLineEdit(r"scanning_mode.COARSE_SAMPLEFINE")

        self.e1.dpo = DblLineEditParamObj("e1", -3500.0, 123.5, 3, parent=self.e1)
        self.e2.dpo = DblLineEditParamObj("e2", 0.0, 4123.5, 3, parent=self.e2)
        self.e3.dpo = DblLineEditParamObj("e3", 0.0, 63.5, 3, parent=self.e3)
        self.e4.dpo = CharLineEditParamObj(
            "e4", valid_values="Any valid directory", parent=self.e4
        )
        # self.e5.dpo = charLineEditParamObj('e5', valid_values=scanning_modes_dct, parent=self.e5)
        self.e5.dpo = CharLineEditParamObj(
            "e5", valid_values=scanning_modes_lst, parent=self.e5
        )

        self.e1.dpo.valid_returnPressed.connect(self.recalc_roi)
        self.e2.dpo.valid_returnPressed.connect(self.recalc_roi)
        self.e3.dpo.valid_returnPressed.connect(self.recalc_roi)
        self.e4.dpo.valid_returnPressed.connect(self.recalc_str)
        self.e5.dpo.valid_returnPressed.connect(self.recalc_str)

        flo = QtWidgets.QFormLayout()
        flo.addRow("Double validator 1", self.e1)
        flo.addRow("Double validator 2", self.e2)
        flo.addRow("Double validator 3", self.e3)
        flo.addRow("Char validator 4", self.e4)
        flo.addRow("Char validator 5", self.e5)
        self.setLayout(flo)

    def recalc_roi(self):
        fld = self.sender()
        print(
            "recalcing roi for [%s] range %.2f to %.2f" % (fld.id, fld._min, fld._max)
        )

    def recalc_str(self):
        fld = self.sender()
        print("recalcing str for [%s]" % (fld.id))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = testWindow()

    win.show()
    win.setWindowTitle("PyQt")
    sys.exit(app.exec_())
