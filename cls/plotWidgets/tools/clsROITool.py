
import sys
import numpy as np
import copy
from PyQt5.QtCore import pyqtSignal


from qtpy.QtCore import Qt
from plotpy.tools import MultiLineTool
from plotpy.styles import style_generator, update_style_attr
from plotpy.events import (
    setup_standard_tool_filter,
    KeyEventMatch,
    QtDragHandler,
)

from plotpy.items import (
    PolygonShape,
)
from plotpy.config import _

STYLE = style_generator()
np.set_printoptions(threshold=sys.maxsize)

LINE_WIDTH = 2
UNSEL_FILL_ALPHA = 0.60
SEL_FILL_ALPHA = 0.90
def customize_shape(shape):
    global STYLE
    param = shape.shapeparam
    style = next(STYLE)
    update_style_attr(style, param)
    param.update_shape(shape)
    shape.plot().replot()


SHAPE_Z_OFFSET = 1000

class DefaultToolbarID:
    pass

class ROITool(MultiLineTool):
    TITLE = _("Roi Tool")
    ICON = "freeform.png"
    shapeNum = 0  # used in the TITLE that is displayed to the user
    unique_id = 0  # used as the key to a dict of shapeItems, not for display
    SHAPE_TITLE = "ROI %d" % unique_id
    rois_changed = pyqtSignal(object)
    roi_pnt_changed = pyqtSignal(object)

    def __init__(
        self,
        manager,
        handle_final_shape_cb=None,
        shape_style=None,
        toolbar_id=DefaultToolbarID,
        title=None,
        icon=None,
        tip=None,
        switch_to_default_tool=None,
    ):
        super(ROITool, self).__init__(
            manager,
            toolbar_id,
            title=title,
            icon=icon,
            tip=tip,
            switch_to_default_tool=switch_to_default_tool,
        )
        self.handle_final_shape_cb = handle_final_shape_cb
        self.shape = None
        self.shapes = (
            {}
        )  #  {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None, 9: None}
        self.shapes_pnts = (
            {}
        )  # {0: None, 1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None, 9: None}
        # for i in range(0,MAX_SHAPES):
        #     self.shapes[i] = self.gen_shape_dct(i)
        self.shape_id = 0
        self.current_handle = None
        self.init_pos = None
        self.visual_sigs_obj = None
        self.shape_exists = False
        self.rois_changed.connect(self.save_points)
        # "shape/drag/line/width"
        # "shape/drag/sel_line/width"
        if shape_style is not None:
            self.shape_style_sect = shape_style[0]
            self.shape_style_key = shape_style[1]
        else:
            self.shape_style_sect = "plot"
            self.shape_style_key = "shape/drag"

    def set_visual_sigs_obj(self, vsig_obj=None):
        if vsig_obj == None:
            return
        self.visual_sigs_obj = vsig_obj
        self.visual_sigs_obj.roi_id_updated.connect(self.resync_shape_id)
        # local shapes will exist in vsig_obj so that the main app can be aware of what rois exist
        self.shapes = vsig_obj._roi_shapes
        # for i in range(0,MAX_SHAPES):
        #     self.shapes[i] = self.gen_shape_dct(i)

    # def gen_shape_dct(self, shid, clr_nm):
    #
    #     dct = {}
    #     dct['name'] = 'ROI_%d [%s]' % (shid, clr_nm)
    #     dct['shape'] = None
    #     dct['points'] = []
    #     dct['exists'] = False
    #     return(dct)

    def resync_shape_id(self, roi_id=0):
        # synchronize the shape number
        #self.shape_id = self.visual_sigs_obj.get_current_roi_id()
        self.shape_id = roi_id

    def shape_deleted(self, shid):
        """
        when a shape is deleted
        :param shid:
        :return:
        """
        if shid in self.shapes.keys():
            self.shapes.pop(shid)

    def remove_roi(self, shid, shape_nm):
        self.shape_deleted(shid)
        #looks like the shape in the tool is already deletcd self.visual_sigs_obj.del_signal(shape_nm)

    def reset(self):
        # self.shapes[self.shape_id] = None
        self.shapes[self.shape_id] = self.visual_sigs_obj.gen_sig_dct(self.shape_id)
        self.shape = self.shapes[self.shape_id]["shape"]
        self.shape = None
        self.current_handle = None

    def create_shape(self, filter, pt):
        """

        """
        # print('ROITool: creating shape[%d]' % self.shape_id)
        clr_nm, nxt_color = self.visual_sigs_obj.colors.get_next_color()

        # if self.shape_id > len(self.shapes):
        #     # print("no more shapes availbale")
        #     # return
        #     self.shape_id = len(self.shapes) + 1
        #     if self.shape_id > MAX_SHAPES:
        #         print("no more shapes availbale")
        #         return
        if self.shape_id > self.visual_sigs_obj.get_max_num_signals():
            print("no more shapes availbale")
            return

        self.shape = PolygonShape(closed=False)
        self.shape.shape_id = self.shape_id
        self.shapes[self.shape_id]["shape"] = self.shape
        self.shape.set_style(self.shape_style_sect, self.shape_style_key)
        # self.shapeparam.read_config(CONF, section, option)
        sp = self.shape.shapeparam
        sp.update_shape(self.shape)
        sp.line.width = LINE_WIDTH
        sp.sel_line.width = LINE_WIDTH
        sp.sel_line.color = nxt_color
        sp.line.color = nxt_color
        sp.sel_symbol.facecolor = sp.sel_symbol.edgecolor = nxt_color
        sp.symbol.facecolor = sp.symbol.edgecolor = nxt_color
        sp.fill.alpha = UNSEL_FILL_ALPHA
        sp.sel_fill.alpha = SEL_FILL_ALPHA
        sp.sel_fill.color = nxt_color
        sp.fill.color = nxt_color

        sp.label = "ROI_%d [%s]" % (self.shape_id, clr_nm)
        sp.update_shape(self.shape)
        self.shapes[self.shape_id]["exists"] = True
        self.shapes[self.shape_id]["checked"] = True
        self.shapes[self.shape_id]["name"] = sp.label
        self.shapes[self.shape_id]["color"] = nxt_color
        # the signal indicating this has changed will fire after this call to add_item_with_z_offset
        filter.plot.add_item_with_z_offset(self.shape, SHAPE_Z_OFFSET)
        self.shape.setVisible(True)

        self.shape.add_local_point(pt)
        return self.shape.add_local_point(pt)

    def setup_filter(self, baseplot):
        """

        """
        filter = baseplot.filter
        # Initialisation du filtre
        start_state = filter.new_state()
        # Bouton gauche :
        handler = QtDragHandler(filter, Qt.LeftButton, start_state=start_state)
        filter.add_event(
            start_state,
            KeyEventMatch((Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space)),
            self.validate,
            start_state,
        )
        filter.add_event(
            start_state,
            KeyEventMatch((Qt.Key_Backspace, Qt.Key_Escape,)),
            self.cancel_point,
            start_state,
        )
        handler.SIG_START_TRACKING.connect(self.mouse_press)
        handler.SIG_MOVE.connect(self.move)
        handler.SIG_STOP_NOT_MOVING.connect(self.mouse_release)
        handler.SIG_STOP_MOVING.connect(self.mouse_release)
        return setup_standard_tool_filter(filter, start_state)

    def validate(self, filter, event):
        super(ROITool, self).validate(filter, event)
        self.shape = self.shapes[self.shape_id]["shape"]
        if self.handle_final_shape_cb is not None:
            self.handle_final_shape_cb(self.shape)
        self.reset()

    def cancel_point(self, filter, event):
        """Reimplement base class method"""
        super(ROITool, self).cancel_point(filter, event)
        self.shape = self.shapes[self.shape_id]["shape"]
        self.shap.closed = len(self.shape.points) > 2

    def mouse_press(self, filter, event):
        """Reimplement base class method"""
        if self.shape_id not in self.shapes.keys():
            self.shapes[self.shape_id] = self.visual_sigs_obj.gen_sig_dct(self.shape_id, checked=True)
            self.shapes[self.shape_id]["shape"] = None

        self.shape = self.shapes[self.shape_id]["shape"]
        if self.shape is None:
            self.init_pos = event.pos()
            self.current_handle = self.create_shape(filter, event.pos())
            filter.plot.replot()
        else:
            self.current_handle = self.shape.add_local_point(event.pos())

        if self.shape != None:
            self.shape.closed = len(self.shape.points) > 2
            self.shapes[self.shape_id]["exists"] = True
            # new June 9
            self.shapes[self.shape_id]["shape"] = self.shape
            self.shapes[self.shape_id]["checked"] = True

    def move(self, filter, event):
        """moving while holding the button down lets the user
        position the last created point
        """
        # print('moving shape[%d]' % self.shape_id)
        self.shape = self.shapes[self.shape_id]["shape"]
        if self.shape is None or self.current_handle is None:
            # Error ??
            return
        self.shape.move_local_point_to(self.current_handle, event.pos())
        self.shapes[self.shape_id]["exists"] = True
        filter.plot.replot()

    def mouse_release(self, filter, event):
        """Releasing the mouse button validate the last point position"""
        self.shape = self.shapes[self.shape_id]["shape"]

        if self.current_handle is None:
            return
        if self.init_pos is not None and self.init_pos == event.pos():
            self.shape.del_point(-1)
        else:
            self.shape.move_local_point_to(self.current_handle, event.pos())
        self.init_pos = None
        self.current_handle = None
        self.shapes[self.shape_id]["exists"] = True

        filter.plot.replot()

    def activate(self):
        """Activate tool"""
        for baseplot, start_state in list(self.start_state.items()):
            baseplot.filter.set_state(start_state, None)

        self.sender()
        self.manager.set_active_tool(self)

    def interactive_triggered(self, action):
        if action is self.action:
            self.activate()
        else:
            if self.shape_id in list(self.shapes.keys()):
                if self.shapes[self.shape_id]["exists"] is not None:
                    self.deactivate()

    def deactivate(self):
        """Deactivate tool"""
        self.rois_changed.emit(self.shape_id)

    def save_points(self):
        if hasattr(self, "shapes_pnts"):
            # if self.shapes_pnts[self.shape_id] is None:
            if self.shape_id < self.visual_sigs_obj.get_max_num_signals():
                if self.shape_id in self.shapes.keys():
                    if self.shapes[self.shape_id]["exists"]:
                        # print('assigning .shapes_pnts[%d]' % self.shape_id)
                        self.shapes[self.shape_id]["points"] = copy.copy(
                            self.shape.get_points()
                        )
                        # self.shape_id += 1
                        self.shape_id = self.visual_sigs_obj.get_next_roi_id()