
import sys
import numpy as np

from plotpy.tools import RectangleTool, MultiLineTool
from plotpy.styles import style_generator, update_style_attr

from plotpy.items import (
    RectangleShape,
)

# from guiqwt.baseplot import canvas_to_axes, axes_to_canvas
from plotpy.config import _

STYLE = style_generator()
np.set_printoptions(threshold=sys.maxsize)

def customize_shape(shape):
    global STYLE
    param = shape.shapeparam
    style = next(STYLE)
    update_style_attr(style, param)
    param.update_shape(shape)
    shape.plot().replot()


class DefaultToolbarID:
    pass


class clsRegionTool(RectangleTool):
    TITLE = _("RegionTool")
    shp = None
    SWITCH_TO_DEFAULT_TOOL = True

    def reset_points(self):
        self.shp.set_points(np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]))

    def get_plot_points(self):
        if self.shp:
            return self.shp.get_points()
        return None

    def create_shape(self):
        shape = RectangleShape(0, 0, 1, 1)
        self.set_shape_style(shape)
        self.shp = shape
        return shape, 0, 2

    def add_shape_to_plot(self, plot, p0, p1):
        """
        Method called when shape's rectangular area
        has just been drawn on screen.
        Adding the final shape to plot and returning it.
        """
        shape = self.get_final_shape(plot, p0, p1)
        self.handle_final_shape(shape)
        plot.replot()

    def setup_shape(self, shape):
        """To be reimplemented"""
        shape.setTitle(self.TITLE)
        if self.setup_shape_cb is not None:
            self.setup_shape_cb(shape)

    def handle_final_shape(self, shape):
        """To be reimplemented"""
        if self.handle_final_shape_cb is not None:
            self.handle_final_shape_cb(shape)

    def mouse_release(self, filter, event):
        """Releasing the mouse button validate the last point position"""
        # self.shape = self.shapes[self.shape_id]
        #
        # if self.current_handle is None:
        #     return
        # if self.init_pos is not None and self.init_pos == event.pos():
        #     self.shape.del_point(-1)
        # else:
        #     self.shape.move_local_point_to(self.current_handle, event.pos())
        # self.init_pos = None
        # self.current_handle = None
        # filter.plot.replot()
        print(filter)