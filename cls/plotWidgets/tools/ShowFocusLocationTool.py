"""
Created on May 15, 2019

@author: bergr
"""
import os

from PyQt5 import QtCore, QtWidgets
from plotpy.tools import *

from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname
from cls.plotWidgets.config import _

_dir = os.path.dirname(os.path.abspath(__file__))


class ShowFocusLocationTool(ToggleTool):
    changed = QtCore.pyqtSignal(object)

    def __init__(
        self,
        manager,
        icon=os.path.join(_dir, "magnifier.png"),
        toolbar_id=DefaultToolbarID,
    ):
        super(ShowFocusLocationTool, self).__init__(
            manager, _("Show Focus Location"), icon=icon, toolbar_id=toolbar_id
        )
        self.action.setCheckable(True)
        self.action.setChecked(False)

    def set_enabled(self, en):
        self.action.setEnabled(en)

    def activate_command(self, plot, checked):
        """Activate tool"""
        self.changed.emit(checked)

    def deactivate(self):
        """Deactivate tool"""
        self.action.setChecked(False)
