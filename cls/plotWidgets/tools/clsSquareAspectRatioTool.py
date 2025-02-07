"""
Created on Aug 9, 2016

@author: bergr
"""
import os

from guidata.configtools import get_icon
from plotpy.interfaces import ICSImageItemType
from plotpy.plot.base import BasePlot
from plotpy.tools import ToggleTool
from plotpy.tools.image import update_image_tool_status
from PyQt5 import QtCore

from cls.plotWidgets.config import _
from cls.plotWidgets.tools.utils import get_parent_who_has_attr


_dir = os.path.dirname(os.path.abspath(__file__))


class clsSquareAspectRatioTool(ToggleTool):
    changed = QtCore.pyqtSignal(bool)

    def __init__(
        self,
        manager,
        plot: BasePlot,
        icon=os.path.join(_dir, "aspect.png"),
        tip="Force aspect Ratio to be square",
    ):
        """
        __init__(): description

        :param manager: manager description
        :type manager: manager type

        :param plot: plot description
        :type plot: plot type

        :param icon="aspect.png": icon="aspect.png" description
        :type icon="aspect.png": icon="aspect.png" type

        :param tip="ForceaspectRatiotobesquare": tip="ForceaspectRatiotobesquare" description
        :type tip="ForceaspectRatiotobesquare": tip="ForceaspectRatiotobesquare" type

        :returns: None
        """
        super().__init__(manager, _("Force aspect ratio to a square"), icon)
        self.plot = plot
        self.ischecked = False
        self.manager = plot.manager
        self.action = self.manager.create_action(
            _("SquareAspectRatioTool"),
            toggled=self.toggle_ischecked,
            icon=get_icon(icon),
            tip=tip,
        )
        self.toolbar = plot.manager.get_default_toolbar()
        self.toolbar.addAction(self.action)
        self.action.setEnabled(False)
        self.action.setIconText("")
        # self.default_icon = build_icon_from_cmap(get_cmap("gist_gray"), width=16, height=16)
        self.default_icon = get_icon(icon)
        self.action.setIcon(self.default_icon)

    def set_enabled(self, en):
        self.action.setEnabled(en)

    def toggle_ischecked(self, checked):
        """
        toggle_ischecked(): description

        :param checked: checked description
        :type checked: checked type

        :returns: None
        """
        if self.ischecked != checked:
            self.ischecked = checked
            p = get_parent_who_has_attr(self.manager, "on_set_aspect_ratio")
            #self.changed.emit(checked)
            p.on_set_aspect_ratio(checked)

    def activate_command(self, plot, checked):
        """
        activate_command(): description

        :param plot: plot description
        :type plot: plot type

        :param checked: checked description
        :type checked: checked type

        :returns: None
        """
        self.ischecked = checked

    def update_status(self, plot):
        """
        update_status(): description

        :param plot: plot description
        :type plot: plot type

        :returns: None
        """
        if update_image_tool_status(self, plot):
            items = plot.get_items(item_type=ICSImageItemType)
            self.action.setEnabled(items is not None)
            self.action.setChecked(items is not None and self.ischecked)

