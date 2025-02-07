import sys
import numpy as np
import copy
from PIL import Image, ImageDraw

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import pyqtSignal
import os.path as osp


from qtpy.QtCore import Qt
from plotpy.plot import PlotDialog, PlotOptions
from plotpy.items import ImageItem
from plotpy.tools import RectangleTool, MultiLineTool
from plotpy.builder import make
from plotpy.styles import style_generator, update_style_attr
from plotpy.events import (
    setup_standard_tool_filter,
    KeyEventMatch,
    QtDragHandler,
)

from plotpy.items import (
    RectangleShape,
    PolygonShape,
)

from cls.plotWidgets.visual_signals import VisualSignalsClass
from cls.plotWidgets.tools.clsROITool import ROITool
# from guiqwt.baseplot import canvas_to_axes, axes_to_canvas
from plotpy.config import _

# from cls.utils.images import array_to_image


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


MAX_SHAPES = 50
SHAPE_Z_OFFSET = 1000


def convert_plot_poly_to_point_poly(cols, rows, plot_boundaries, poly_positions):
    """
    the multi point polygon values are in units of um and I need them to be in pixel points for
    the masking to work during integration
    """
    # Define the plotting positions of the corners
    x_min = plot_boundaries['xmin']
    x_max = plot_boundaries['xmax']
    y_min = plot_boundaries['ymin']
    y_max = plot_boundaries['ymax']

    # Calculate the x and y ranges
    x_range = x_max - x_min
    y_range = y_max - y_min


    # Initialize a list to store the corresponding array indices
    point_indices = []

    # Map each plotting position to its array indices
    for x_plot, y_plot in poly_positions:
        # Calculate the array indices
        col_index = int((x_plot - x_min) / x_range * (cols - 1))
        row_index = int((y_plot - y_min) / y_range * (rows - 1))

        # Append the indices to the list
        point_indices.append((col_index, row_index))

    #print("Array indices corresponding to the plotting positions:")
    arr_poly_points = []
    for index in point_indices:
        #print(index)
        arr_poly_points.append(index)

    return arr_poly_points

# def convert_um_to_pixels(x_um, y_um, x_min_um, x_max_um, y_min_um, y_max_um, x_pixels, y_pixels):
#     # Calculate the range in micrometers
#     x_range_um = x_max_um - x_min_um
#     y_range_um = y_max_um - y_min_um
#
#     # Calculate the scaling factors
#     x_scale = x_pixels / x_range_um
#     y_scale = y_pixels / y_range_um
#
#     # Convert coordinates from micrometers to pixels
#     x_pixel = int((x_um - x_min_um) * x_scale)
#     y_pixel = int((y_um - y_min_um) * y_scale)
#
#     return x_pixel, y_pixel

def integrate_poly_mask(
    data,
    polygon_lst=[
        882.3713684210528,
        1827.9528421052632,
        337.88631578947377,
        1307.141052631579,
        1107.2673684210529,
        1105.918315789474,
    ],
    plot_boundaries={}
):
    """
    take an array of image data, and one dimensioanl list of x,y points of a multipoint polygon ex: [x1,xy,x2,y2,x3,y3,...]
    and return the sum of the pixels that fall within the polygon

    :param data:
    :param polygon_lst:
    :return:
    """
    if type(polygon_lst) != list:
        print("The polygon parameter must be a single dimension list of points")
        return None
    height, width = data.shape

    if len(plot_boundaries) == 0:
        plot_boundaries['xmin'] = 0
        plot_boundaries['xmax'] = width
        plot_boundaries['ymin'] = 0
        plot_boundaries['ymax'] = height

    #print(f"integrate_poly_mask: data.shape=[{data.shape}]")
    img = Image.new("L", (width, height), 0)

    #print(f"integrate_poly_mask: [{polygon_lst}]")
    #convert the given poly point list which is in pltter coordinates into pixels
    print(f"BEFORE: {polygon_lst}")
    polygon_lst = convert_plot_poly_to_point_poly(width, height, plot_boundaries, polygon_lst)
    print(f"AFTER: {polygon_lst}")
    ImageDraw.Draw(img).polygon(polygon_lst, outline=1, fill=1)
    mask = np.array(img, dtype=bool)
    #img.show()
    num_pixels = np.count_nonzero(mask)
    # sum_val = np.int64(data[mask].sum() / num_pixels)
    if num_pixels > 0:
        sum_val = float(float(data[mask].sum()) / float(num_pixels))
        #print(f"integrate_poly_mask: sum_val = {sum_val}")
        return sum_val
    else:
        return None

#
class ROI_ImageWidget(QWidget):
    def __init__(self):
        super(ROI_ImageWidget, self).__init__()
        gridparam = make.gridparam(
            background="black",
            minor_enabled=(False, False),
            major_enabled=(False, False),
        )
        self.img_plot = PlotDialog(
            edit=False,
            toolbar=True,
            title="All image and plot tools test",
            options=PlotOptions(gridparam=gridparam),
        )

        # color_dct = color_map
        vbox = QtWidgets.QVBoxLayout()
        # btn = QtWidgets.QPushButton('Get all points')
        # btn.clicked.connect(self.get_points_dct)
        # vbox.addWidget(btn)
        btn = QtWidgets.QPushButton("Integrate points")
        btn.clicked.connect(self.on_integrate_points_btn)
        vbox.addWidget(btn)
        vbox.addWidget(self.img_plot)
        self.roi_tool = self.img_plot.manager.add_tool(
            ROITool, handle_final_shape_cb=customize_shape
        )
        self.visual_signals_obj = VisualSignalsClass()
        self.roi_tool.set_visual_sigs_obj(self.visual_signals_obj)
        # self.ff_tool.rois_changed.connect(self.on_rois_changed)
        self.setLayout(vbox)
        self.setMinimumSize(500, 600)

    def on_marker_changed(self, arg):
        print("on_marker_changed")

    def convert_points(self, shp):
        pnts = shp.get_points()
        temp = []
        for pnt in pnts:
            # can_pnt = axes_to_canvas_int(shp, pnt[0], pnt[1])
            temp.append((int(pnt[0]), int(pnt[1])))
        # print('Shape id [%d] has points' % (shp.shape_id), temp)
        return (shp.shape_id, temp)

    def on_sig_item_moved(self, shp):
        self.convert_points(shp)

    def on_sig_item_changed(self, plt):
        print("on_sig_item_changed: ")
        for i in plt.items:
            if type(i) == PolygonShape:
                self.convert_points(i)

    def on_rois_changed(self, dct):
        print("ROIWidgets rois_changed", dct)
        # pass

    # def get_points_dct(self):
    #     dct = {}
    #     items = self.img_plot.get_plot().get_items()
    #     for shp in items:
    #         if type(shp) == PolygonShape:
    #             pnts = shp.get_points()
    #             dct[shp.shape_id] = pnts.flatten().tolist()
    #     return dct
    def get_points_dct(self):
        dcts = {}
        items = self.img_plot.get_plot().get_items()
        # print(f"get_points_dct: items=[{items}]")
        for shp in items:
            if type(shp) == PolygonShape:
                pnts = shp.get_points()
                # dct[shp.shape_id] = pnts.flatten().tolist()
                # dct[shp.shape_id] = {'name': shp.title().text(), 'color': shp.shapeparam.sel_line.color, 'points': pnts.flatten().tolist(), 'checked': True}
                if shp.shape_id not in list(dcts.keys()):
                    dcts[shp.shape_id] = self.visual_signals_obj.gen_sig_dct(
                        shp.shape_id,
                        title=shp.title().text(),
                        color=shp.shapeparam.sel_line.color,
                        points=pnts.flatten().tolist(),
                        checked=True,
                        shape=shp
                    )

        return dcts

    def on_integrate_points_btn(self):
        pnts_dct = self.get_points_dct()
        items = self.img_plot.get_plot().get_items()
        for i in items:
            if type(i) == ImageItem:
                # for shp_id, polygon_lst in pnts_dct.items():
                #     val = integrate_poly_mask(i.data, polygon_lst)
                #     print("integrated value for shape[%d] is %d" % (shp_id, val))
                for shp_id, poly_dct in pnts_dct.items():
                    val = integrate_poly_mask(i.data, poly_dct[shp_id]['points'])
                    #print(f"integrated value for shape[{shp_id}] is [{val}] for polypoints [{poly_dct[shp_id]['points']}]")
                    print(f"integrated value for shape[{shp_id}] is [{val}] ")

def get_points_dct(img_plot, visual_signals_obj):
    dcts = {}
    items = img_plot.get_plot().get_items()
    # print(f"get_points_dct: items=[{items}]")
    for shp in items:
        if type(shp) == PolygonShape:
            pnts = shp.get_points()
            # dct[shp.shape_id] = pnts.flatten().tolist()
            # dct[shp.shape_id] = {'name': shp.title().text(), 'color': shp.shapeparam.sel_line.color, 'points': pnts.flatten().tolist(), 'checked': True}
            if shp.shape_id not in list(dcts.keys()):
                dcts[shp.shape_id] = visual_signals_obj.gen_sig_dct(
                    shp.shape_id,
                    title=shp.title().text(),
                    color=shp.shapeparam.sel_line.color,
                    points=pnts.flatten().tolist(),
                    checked=True,
                    shape=shp
                )

    return dcts

def on_integrate_points_btn(img_plot, visual_signals_obj):
    pnts_dct = get_points_dct(img_plot, visual_signals_obj)
    items = img_plot.get_plot().get_items()
    for i in items:
        if type(i) == ImageItem:
            # for shp_id, polygon_lst in pnts_dct.items():
            #     val = integrate_poly_mask(i.data, polygon_lst)
            #     print("integrated value for shape[%d] is %d" % (shp_id, val))
            for shp_id, poly_dct in pnts_dct.items():
                rect = i.border_rect.get_rect()
                plot_boundaries = {}
                plot_boundaries['xmin'] = rect[0]
                plot_boundaries['xmax'] = rect[2]
                plot_boundaries['ymin'] = rect[1]
                plot_boundaries['ymax'] = rect[3]
                val = integrate_poly_mask(i.data, poly_dct[shp_id]['points'], plot_boundaries=plot_boundaries)

                #print(f"integrated value for shape[{shp_id}] is [{val}] for polypoints [{poly_dct[shp_id]['points']}]")
                print(f"integrated value for shape[{shp_id}] is [{val}] ")

def go():
    """Test"""
    # -- Create QApplication
    import guidata
    #from cls.utils.tracing_utils import trace_calls

    #sys.settrace(trace_calls)
    app = QApplication(sys.argv)
    # --
    color_map = []
    r = 0
    g = 255
    b = 0
    for i in range(12):
        rs = hex(r).replace("0x", "#")
        if rs == "#0":
            rs = "#00"
        gs = hex(g).replace("0x", "")
        if gs == "0":
            gs = "00"
        bs = hex(b).replace("0x", "")
        if bs == "0":
            bs = "00"
        s = f"{rs}{gs}{bs}"
        color_map.append(s)
        r += 25
        g -= 25
        b += 25
        if r > 255:
            r = 30
        if g < 0:
            g = 240
        if b > 255:
            b = 12

    color_map.append("")
    filename = osp.join(osp.dirname(__file__), "test_data", "gray_pattern.jpg")
    # filename = osp.join(osp.dirname(__file__), "checkers.png")
    # filename = osp.join(osp.dirname(__file__), "black_white.png")
    win = ROI_ImageWidget()
    image = make.image(filename=filename, colormap="gist_gray")#, alpha_mask=False)
    # img_dat = np.zeros((10,10), dtype=np.uint8)
    # img_dat[5,5] = 255
    # image = make.image(data=img_dat, colormap="gist_gray", alpha_mask=False)
    plot = win.img_plot.get_plot()
    plot.add_item(image)
    win.show()
    sys.exit(app.exec_())





if __name__ == "__main__":
    go()

