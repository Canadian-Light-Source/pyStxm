"""
Created on Aug 25, 2023

@author: bergr
"""
import os

from PyQt5 import QtCore, QtWidgets
from plotpy.tools import *
from plotpy.items.shape.marker import Marker

from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname
from cls.plotWidgets.config import _

_dir = os.path.dirname(os.path.abspath(__file__))

class clsHorizSelectPositionTool(HCursorTool):
    changed = QtCore.pyqtSignal(object)
    TITLE = _("Select Position")
    ICON = "hcursor.png"
    CHECKABLE = True

    def __init__(
        self,
        manager,
        icon=os.path.join(_dir, "selectPosition.png"),
        toolbar_id=DefaultToolbarID,
    ):
        super(clsHorizSelectPositionTool, self).__init__(
            manager,
            tip=_("Select Position"),
            icon=icon,
            toolbar_id=toolbar_id,
            switch_to_default_tool=True,
        )

        # assert icon in ("reuse", "create")
        self.action.setCheckable(True)
        self.action.setChecked(False)
        self._my_checked_state = False

    def create_shape(self):
        marker = Marker()
        marker.set_markerstyle("-")
        return marker

    def set_enabled(self, en):
        self.action.setEnabled(en)

    def activate_command(self, plot, checked):
        """Activate tool"""
        # self.changed.emit(checked)
        pass

    def activate(self):
        """Activate tool"""

        if self._my_checked_state:
            self.deactivate()
            return

        for baseplot, start_state in list(self.start_state.items()):
            baseplot.filter.set_state(start_state, None)

        self.action.blockSignals(True)
        self.action.setChecked(True)
        self.manager.set_active_tool(self)
        if self.shape is not None:
            self.shape.setVisible(True)
        self._my_checked_state = True
        self.action.blockSignals(False)

    def deactivate(self):
        """Deactivate tool"""
        self.action.setChecked(False)
        # self.show_title.emit(False, self)
        if self.shape is not None:
            self.shape.setVisible(False)
        self._my_checked_state = False

    def move(self, filter, event):
        plot = filter.plot
        if not self.shape:
            self.shape = self.create_shape()
            self.shape.attach(plot)
            self.shape.setZ(plot.get_max_z() + 1)
            self.shape.move_local_point_to(0, event.pos())
            self.shape.setVisible(True)
        self.shape.move_local_point_to(1, event.pos())
        plot.replot()
        self.last_pos = self.shape.xValue(), self.shape.yValue()
        self.changed.emit(self.last_pos)

    def end_move(self, filter, event):
        # if self.shape is not None:
        #     assert self.shape.plot() == filter.plot
        #     filter.plot.add_item_with_z_offset(self.shape, SHAPE_Z_OFFSET)
        #     #self.shape = None
        #     #self.SIG_TOOL_JOB_FINISHED.emit()
        pass
