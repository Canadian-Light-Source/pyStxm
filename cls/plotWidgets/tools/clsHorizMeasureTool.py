"""
Created on Oct 6, 2016

@author: bergr
"""
import os

from PyQt5 import QtGui, QtWidgets

from plotpy.tools import *

# from guiqwt.config import _

from cls.plotWidgets.config import _
from . import clsHLineSegmentTool

from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname

_dir = os.path.dirname(os.path.abspath(__file__))


class clsHorizMeasureTool(clsHLineSegmentTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Measure distance between two points")
    ICON = os.path.join(_dir, "horizmeasure.png")
    SHAPE_STYLE_KEY = "shape/segment"

    def setup_shape(self, shape):
        """
        setup_shape(): description

        :param shape: shape description
        :type shape: shape type

        :returns: None
        """
        plot = self.manager.get_plot()
        plot.unselect_all()
        plot.set_active_item(shape)
        shape._parent_tool = self
        shape.annotationparam.format = "%.05f"
        if self.setup_shape_cb is not None:
            self.setup_shape_cb(shape)

    def set_shape_style(self, shape):
        """Override so that plotpy reads style settings from cls/plotWidgets/config.py
        (which defines the 'russ/segment' entries) rather than from plotpy's own
        built-in CONF, which doesn't know about that key."""
        from cls.plotWidgets.config import CONF as LOCAL_CONF
        shape.shape.shapeparam.read_config(
            LOCAL_CONF, self.SHAPE_STYLE_SECT, self.SHAPE_STYLE_KEY
        )
        shape.shape.shapeparam.update_item(shape.shape)

    def set_enabled(self, en):
        self.action.setEnabled(en)

    def set_format(self, frmt):
        """
        default is '%.1f'
        """
        plot = self.manager.get_plot()
        shape = plot.get_active_item()
        shape.annotationparam.format = frmt
