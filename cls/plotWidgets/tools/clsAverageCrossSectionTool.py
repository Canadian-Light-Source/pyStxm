"""
Created on Aug 9, 2016

@author: bergr
"""
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal

from plotpy.tools import *

# from guiqwt.config import _
from plotpy.interfaces import IShapeItemType
from cls.plotWidgets.config import _
from plotpy.items import AnnotatedRectangle
from cls.plotWidgets.tools.utils import get_parent_who_has_attr, get_widget_with_objectname

from cls.utils.roi_utils import get_unique_roi_id, add_to_unique_roi_id_list
from cls.types.stxmTypes import spatial_type_prefix


class clsAverageCrossSectionTool(AverageCrossSectionTool):
    shapeNum = 0
    SWITCH_TO_DEFAULT_TOOL = True
    TITLE = _("Select 2D ROI for scan")
    ICON = "csection_a.png"
    SHAPE_STYLE_KEY = "shape/average_cross_section"
    shapeNum = 0  # used in the TITLE that is displayed to the user
    unique_id = 0  # used as the key to a dict of shapeItems, not for display
    # SHAPE_TITLE = 'ROI %d' % shapeNum
    SHAPE_TITLE = "ROI %d" % unique_id
    enable_multi_shape = False
    spatial_type = spatial_type_prefix.ROI

    def set_enabled(self, en):
        self.action.setEnabled(en)

    # def get_num_instances(self):
    #    num_this_shape = self.manager.

    def re_init_unique_id(self):
        """
        re_init_unique_id(): description

        :returns: None
        """
        # print 're_init_unique_id: IN: %d' % self.unique_id
        self.unique_id = get_unique_roi_id()
        # print 're_init_unique_id: OUT: %d' % self.unique_id

    def activate(self):
        """Activate tool"""
        current_shape_items = self.manager.get_main().get_plot().get_items(item_type=IShapeItemType)
        if self.manager.get_main().parent().multi_region_enabled:
            self.do_activate()
        elif len(current_shape_items) > 0:
            self.deactivate()
        elif len(current_shape_items) == 0:
            self.do_activate()

    def do_activate(self):
        """
        activate(): description

        :returns: None
        """
        """Activate tool"""
        # This function gets called numerous times by different objects, only
        # increment the item counter if it is called by QAction (which is only called once per
        # click of the tool
        # print 'clsAverageCrossSectionTool: START: self.unique_id=%d' % self.unique_id
        if isinstance(self.sender(), QtWidgets.QAction):
            if self.shapeNum > 0:
                # feb 21 2018: tomo
                add_to_unique_roi_id_list(self.unique_id)
                #
                if self.manager.get_main().parent().multi_region_enabled:
                    pass
                else:

                    self.action.setChecked(False)
                    self.manager.activate_default_tool()
                    return

            self.shapeNum += 1

            # get a new unique ID that will be assigned to the shape
            self.re_init_unique_id()
            # tell the main plot what teh current unique_id is so that it can ignore signals with unique_id's that
            # are not current
            self.manager._cur_shape_uid = self.unique_id

        for baseplot, start_state in list(self.start_state.items()):
            baseplot.filter.set_state(start_state, None)

        self.action.setChecked(True)
        self.manager.set_active_tool(self)
        # print 'clsAverageCrossSectionTool: END: self.unique_id=%d' % self.unique_id
        # print 'clsAverageCrossSectionTool: addr(self.unique_id)=%d' % id(self.unique_id)

    def setup_shape(self, shape):
        """
        setup_shape(): description

        :param shape: shape description
        :type shape: shape type

        :returns: None
        """
        shape.setTitle("ROI %d" % self.unique_id)
        # create a new property of the shape
        shape.unique_id = self.unique_id
        shape.shapeNum = self.shapeNum
        shape._parent_tool = self
        self.setup_shape_appearance(shape)
        super(CrossSectionTool, self).setup_shape(shape)
        self.register_shape(shape, final=False)

    def interactive_triggered(self, action):
        if action is self.action:
            self.activate()
        else:
            self.deactivate()

    def deactivate(self):
        """Deactivate tool"""
        self.action.setChecked(False)

    def update_status(self, plot):
        """
        Override the base class update_status that would set the
        tool enabled if there is an image item in the plotter, I want to control
        the enabled/disabled state of the tool at a higher level so
        do not do anything automatic
        """
        pass