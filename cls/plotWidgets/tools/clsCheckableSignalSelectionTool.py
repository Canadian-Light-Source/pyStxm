from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt

from collections import Counter

import plotpy
from plotpy.tools import CommandTool, DefaultToolbarID
from plotpy.interfaces import (
    IColormapImageItemType,
    ICurveItemType
)
from plotpy.config import _
from plotpy.plot import BasePlot

from cls.utils.sig_utils import disconnect_signal
from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname

class PersistentMenu(QMenu):
    focusLost = pyqtSignal()  # Signal emitted when the menu loses focus

    def __init__(self, parent=None):
        super(PersistentMenu, self).__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)  # Ensure the menu can receive focus

    def focusOutEvent(self, event):
        self.focusLost.emit()  # Emit the focusLost signal
        self.hide()
        super(PersistentMenu, self).focusOutEvent(event)

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.pos())
        if action and action.isCheckable():
            action.trigger()  # Trigger the action without closing the menu
        else:
            super(PersistentMenu, self).mouseReleaseEvent(event)


def update_sigselect_tool_status(tool, plot):
    enabled = (isinstance(plot, BasePlot))
    tool.action.setEnabled(enabled)
    return enabled

########################################################################
class clsCheckableSignalSelectTool(CommandTool):
    changed = pyqtSignal(object)

    def __init__(self, manager, signals_dct, toolbar_id=DefaultToolbarID):
        self.signals_dct = signals_dct
        super(clsCheckableSignalSelectTool, self).__init__(
            manager,
            _("clsCheckableSignalSelectTool"),
            tip=_("Select signals to view"),
            toolbar_id=toolbar_id
        )
        self._selected_signals = []
        self.action.setEnabled(True)
        self.action.setIconText("Signals  ")
        self.parent_obj_nm = "NONE"
        if get_widget_with_objectname(manager, "CurveViewerWidget"):
            self.parent_obj_nm = "CurveViewerWidget"
        elif get_widget_with_objectname(manager, "ImageWidgetPlot"):
            self.parent_obj_nm = "ImageWidgetPlot"
        if not hasattr(self, "menu"):
            self.menu = PersistentMenu()
        self.menu.focusLost.connect(self.on_menu_focus_lost)  # Connect focusLost signal
        self.action.setMenu(self.menu)

    def on_menu_focus_lost(self):
        """Emit the changed signal with the list of checked signals when the menu loses focus."""
        checked_signals = self.get_checked_signals()
        if not self.lists_have_same_contents(checked_signals, self._selected_signals):
            self._selected_signals = checked_signals[:]
            self.changed.emit(checked_signals)

    def set_pulldown_title(self, title):
        self.action.setIconText(f"{title}  ")

    def lists_have_same_contents(self, list1, list2):
        """
        Check if two lists have the same contents, regardless of order.
        """
        return Counter(list1) == Counter(list2)

    def create_action_menu(self, manager):
        """Create and return a checkable menu for the tool's action"""
        dets = self.signals_dct
        if not hasattr(self, "menu"):
            self.menu = PersistentMenu()
        if len(dets) > 0:
            menu = self.menu
            # Clear previous menu
            menu.clear()
            for signal_name, dct in dets.items():
                action = QAction(signal_name, menu)
                action.setCheckable(True)
                if dct['selected']:
                    print(f"clsCheckableSignalSelectTool: signal {signal_name} is selected")
                    action.setChecked(True)
                menu.addAction(action)
            return menu
        return QMenu()

    def update_menu(self, manager):
        self.menu = self.create_action_menu(manager)
        self.action.setMenu(self.menu)

    def get_checked_signals(self):
        """Retrieve the list of checked signals"""
        return [action.text() for action in self.menu.actions() if action.isChecked()]

    def get_all_signals(self):
        """Retrieve the list of checked signals"""
        return [action.text() for action in self.menu.actions()]

    def activate_sigsel_tool(self, action):
        """Handle menu action activation"""
        all_signals = self.get_all_signals()
        checked_signals = self.get_checked_signals()
        print("clsCheckableSignalSelectTool: All signals:", all_signals)
        self.set_pulldown_title(" ALL Signals ")
        # emit list of selected detector names
        self.changed.emit(checked_signals)