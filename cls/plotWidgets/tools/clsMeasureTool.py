"""
Created on Aug 9, 2016

@author: bergr
"""
import os
from PyQt5 import QtGui, QtWidgets

from plotpy.tools import *

from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname
from cls.plotWidgets.config import _

_dir = os.path.dirname(os.path.abspath(__file__))


class clsMeasureTool(AnnotatedSegmentTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Distance between end points")
    ICON = os.path.join(_dir, "measure.png")
    SHAPE_STYLE_KEY = "shape/segment"
    _shape = None
    _units = "um"

    def set_units(self, units="um"):
        """
        allow the caller to say what the measurement units are
        ex: um, pixels
        """
        self._units = units

    def set_shape_style(self, shape):
        """Override so that plotpy reads style settings from cls/plotWidgets/config.py
        (which defines the 'russ/segment' entries) rather than from plotpy's own
        built-in CONF, which doesn't know about that key."""
        from cls.plotWidgets.config import CONF as LOCAL_CONF
        shape.shape.shapeparam.read_config(
            LOCAL_CONF, self.SHAPE_STYLE_SECT, self.SHAPE_STYLE_KEY
        )
        shape.shape.shapeparam.update_item(shape.shape)

    def setup_shape(self, shape):
        """
        setup_shape(): description

        :param shape: shape description
        :type shape: shape type

        :returns: None
        """
        self._shape = shape
        shape.get_infos = self.get_infos
        plot = self.manager.get_plot()
        plot.unselect_all()
        plot.set_active_item(shape)
        # self.manager._select_this_item(self)
        super(clsMeasureTool, self).setup_shape(shape)

    def set_enabled(self, en):
        self.action.setEnabled(en)

    def get_infos(self) -> str:
        """Get informations on current shape

        Returns:
            str: Formatted string with informations on current shape
        """
        return "<br>".join(
            [
                _("Center:") + " " + self._shape.get_tr_center_str().replace("um", self._units),
                _("Distance:") + " " + self._shape.x_to_str(self._shape.get_tr_length()).replace("um", self._units),
            ]
        )
