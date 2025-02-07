"""
Created on Aug 9, 2016

@author: bergr
"""

# from guiqwt.config import _
from plotpy.tools import *

from cls.plotWidgets.config import _
from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname
from cls.types.stxmTypes import spatial_type_prefix


class clsRectangleTool(AverageCrossSectionTool):
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("")
    ICON = "rectangle.png"
    SHAPE_STYLE_KEY = "shape/average_cross_section"
    SHAPE_TITLE = TITLE
    spatial_type = spatial_type_prefix.ROI

    def set_enabled(self, en):
        self.action.setEnabled(en)
