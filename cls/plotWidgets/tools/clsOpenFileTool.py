"""
Created on Aug 9, 2016

@author: bergr
"""
import os
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal
from plotpy.tools import CommandTool, DefaultToolbarID
from guidata.qthelpers import get_std_icon

from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname
from plotpy.widgets.imagefile import exec_image_open_dialog
from cls.appWidgets.dialogs import getOpenFileName, getOpenFileNames

from cls.plotWidgets.config import _


class clsOpenFileTool(CommandTool):

    openfile = pyqtSignal(object)

    def __init__(self, manager, formats="*.*", toolbar_id=DefaultToolbarID):
        """
        __init__(): description

        :param manager: manager description
        :type manager: manager type

        :param formats='*.*': formats='*.*' description
        :type formats='*.*': formats='*.*' type

        :param toolbar_id=DefaultToolbarID: toolbar_id=DefaultToolbarID description
        :type toolbar_id=DefaultToolbarID: toolbar_id=DefaultToolbarID type

        :returns: None
        """
        CommandTool.__init__(
            self,
            manager,
            _("Open..."),
            get_std_icon("DialogOpenButton", 16),
            toolbar_id=toolbar_id,
        )
        self.formats = formats
        self.directory = ""

    def set_enabled(self, en):
        self.action.setEnabled(en)

    def set_directory(self, dirname):
        """
        set_directory(): description

        :param dirname: dirname description
        :type dirname: dirname type

        :returns: None
        """
        self.directory = dirname

    def get_filename(self, plot):
        """
        get_filename(): description

        :param plot: plot description
        :type plot: plot type

        :returns: None
        """

        filenames = getOpenFileNames("Open", filter_str="Images (%s)" % self.formats, search_path=self.directory
        )
        return filenames

    def activate_command(self, plot, checked):
        """
        activate_command(): description

        :param plot: plot description
        :type plot: plot type

        :param checked: checked description
        :type checked: checked type

        :returns: None
        """
        """Activate tool"""
        filename = self.get_filename(plot)
        if filename:
            self.openfile.emit(filename)
