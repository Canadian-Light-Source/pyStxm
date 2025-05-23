# -*- coding:utf-8 -*-
"""
Created on 2011-03-03

@author: bergr
"""
from functools import partial
import sys
import os
import timeit
from typing import Dict, Optional, Tuple, Union
from PyQt5 import QtGui, QtWidgets
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject, QTimer, QPointF, QRectF, Qt
from PyQt5 import uic

import copy
import qwt as Qwt

import numpy as np

from cls.types.stxmTypes import SPEC_ROI_PREFIX
from plotpy.plot import PlotOptions
from plotpy.mathutils.colormap import get_cmap, register_extra_colormap
from plotpy.plot import  PlotDialog
from plotpy.tools import *
from plotpy.styles import (
    AnnotationParam,
    ImageParam,
    ImageAxesParam,
    GridParam,
    CurveParam,
)

from cls.plotWidgets.config import _, DEFAULTS

from plotpy.items import shape
from plotpy.items import ImageItem, TrImageItem, LabelItem, HistogramItem

from guidata.qthelpers import add_actions
from guidata.configtools import get_icon
from guidata.config import CONF


def _nanmin(data):
    if isinstance(data, np.ma.MaskedArray):
        data = data.data
    if data.dtype.name in ("float32", "float64", "float128"):
        return np.nanmin(data)
    else:
        return data.min()


def _nanmax(data):
    if isinstance(data, np.ma.MaskedArray):
        data = data.data
    if data.dtype.name in ("float32", "float64", "float128"):
        return np.nanmax(data)
    else:
        return data.max()


from plotpy.interfaces import (
    ICSImageItemType,
    IPanel,
    IBasePlotItem,
    ICurveItemType,
    IShapeItemType,
    IDecoratorItemType,
)
from plotpy.items import AnnotatedRectangle, AnnotatedSegment, AnnotatedPoint, AnnotatedCircle, AnnotatedEllipse

# from cls.plotWidgets.guiqwt_qt5_sigs import (
#     SIG_MARKER_CHANGED,
#     SIG_PLOT_LABELS_CHANGED,
#     SIG_AXES_CHANGED,
#     SIG_ANNOTATION_CHANGED,
#     SIG_AXIS_DIRECTION_CHANGED,
#     SIG_VOI_CHANGED,
#     SIG_ITEMS_CHANGED,
#     SIG_ACTIVE_ITEM_CHANGED,
#     SIG_ITEM_MOVED,
#     SIG_LUT_CHANGED,
#     SIG_ITEM_SELECTION_CHANGED,
#     SIG_STOP_MOVING,
#     SIG_PLOT_AXIS_CHANGED)

from plotpy.builder import make

from guidata.dataset import DataSet
from guidata.dataset.dataitems import StringItem
from guidata.dataset.qtwidgets import DataSetShowGroupBox
from guidata.dataset import update_dataset

from cls.plotWidgets.tools.annotatedHorizontalSegment import AnnotatedHorizontalSegment

from cls.plotWidgets.stxm_osa_dflt_settings import (
    make_dflt_stxm_osa_smplholder_settings_dct,
)
from cls.plotWidgets.tools import ROITool, clsSquareAspectRatioTool
from cls.utils.excepthook import exception
from cls.utils.nextFactor import nextFactor
from cls.utils.angles import calcRectPoints
from cls.utils.fileUtils import get_file_path_as_parts
from cls.utils.log import get_module_logger
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.json_utils import file_to_json
from cls.utils.cfgparser import ConfigClass
from cls.utils.time_utils import datetime_string_to_seconds

from cls.stylesheets import master_colors
from cls.appWidgets.dialogs import excepthook, errorMessage
from cls.plotWidgets import tools
from cls.plotWidgets.shape_restrictions import ROILimitObj, ROILimitDef, ROI_STATE_ALARM
from cls.utils.roi_utils import (
    get_first_sp_db_from_wdg_com,
    make_spatial_db_dict,
    widget_com_cmnd_types,
    get_unique_roi_id,
    is_unique_roi_id_in_list,
    get_current_unique_id,
    set_current_unique_id,
    delete_unique_id,
)
from cls.utils.roi_dict_defs import *
from cls.plotWidgets.color_def import (
    get_normal_clr,
    get_alarm_clr,
    get_warn_clr,
    get_normal_fill_pattern,
    get_warn_fill_pattern,
    get_alarm_fill_pattern,
)
from cls.plotWidgets.shapes.pattern_gen import add_pattern_to_plot

import cls.types.stxmTypes as types

from cls.utils.save_settings import SaveSettings
from cls.utils.json_threadsave import mime_to_dct

from cls.data_io.stxm_data_io import STXMDataIo
from cls.scanning.dataRecorder import DataIo
#from cls.plotWidgets.CLSPlotItemBuilder import clsPlotItemBuilder

from cls.utils.threaded_image_loader import ThreadpoolImageLoader

from cls.plotWidgets.shapes.utils import (
    create_rect_centerd_at,
    create_rectangle,
    create_simple_circle,
)


# plotDir = os.path.dirname(os.path.abspath(__file__)) + '/'
plotDir = os.path.dirname(os.path.abspath(__file__))
# define a list of VALID tools for a particular plotting type, used to
# only allow access to certain tools for cerrtain scans
PNT_tools = ["AnnotatedPointTool", "clsPointTool"]
SEG_tools = [
    "SegmentTool",
    "clsHLineSegmentTool",
    "AnnotatedSegmentTool",
    "clsSegmentTool",
]
ROI_tools = ["RectangleTool", "AnnotatedRectangleTool", "clsAverageCrossSectionTool"]
CIR_tools = ["CircleTool", "EllipseTool", "AnnotatedCircleTool", "AnnotatedEllipseTool"]


MAIN_TOOLS_STR = [
    "SelectPointTool",
    "SelectTool",
    "RectZoomTool",
    "BasePlotMenuTool",
    "ExportItemDataTool",
    "EditItemDataTool",
    "ItemCenterTool",
    "DeleteItemTool",
    "DummySeparatorTool",
    "BasePlotMenuTool",
    "DisplayCoordsTool",
    "ItemListPanelTool",
    "DummySeparatorTool",
    "ColormapTool",
    "ReverseYAxisTool",
    "AspectRatioTool",
    "ContrastPanelTool",
    "SnapshotTool",
    "ImageStatsTool",
    "XCSPanelTool",
    "YCSPanelTool",
    "CrossSectionTool",
    "AverageCrossSectionTool",
    "SaveAsTool",
    "CopyToClipboardTool",
    "PrintTool",
    "HelpTool",
    "AboutTool",
]


OSA_CRYO = "OSA_CRYO"
OSA_AMBIENT = "OSA_AMBIENT"
SAMPLE_GONI = "SAMPLE_GONI"
SAMPLE_STANDARD = "SAMPLE_STANDARD"
FILTER_STRING = "*.hdf5;*.png;*.jpg"

MAX_IMAGE_Z = 1000
# setup module logger with a default do-nothing handler
_logger = get_module_logger(__name__)




DEFAULT_IMG_INIT_VAL = -1.0


class ImageParam(DataSet):
    title = StringItem(_("Title"))
    scan_time = StringItem("Scan Time")
    scan_type = StringItem("Scan Type")
    npoints = StringItem("Number of Points")

    # npoints = IntItem(_("NPoints"), default=0., unit="points", help=_("Number of Points (pts)"))
    # height = IntItem(_("Height"), default=0., unit="points", help=_("Image height (pts)"))
    # center = FloatItem(_("Center"), default=0., unit="um", help=_("Image center (um)"))
    # range = FloatItem(_("Range"), default=00., unit="um", help=_("Image range (um)"))

    energy = StringItem("Energy")
    center = StringItem("Center")
    rng = StringItem("Range")
    dwell = StringItem("Dwell")
    # current = FloatItem("Current", default=10., min=1, max=30, unit="mA",
    #               help="Threshold current")
    # floatarray = FloatArrayItem("Float array", default=np.ones( (50,5), float),
    #                            format=" %.2e ").set_pos(col=1)


def dumpObj(obj):
    """
    dumpObj(): description
    :param dumpObj(obj: dumpObj(obj description
    :type dumpObj(obj: dumpObj(obj type
    :returns: None
    """
    print("dumpObj: ")
    print(obj)
    for i in list(obj.__dict__.keys()):
        print("%s : %s" % (i, obj.__dict__[i]))


def dump_key_pressed(dct):
    for k in list(dct.keys()):
        if k == Qt.Key_C:
            print("Key Qt.Key_C == ", dct[k])
        if k == Qt.Key_X:
            print("Key Qt.Key_X == ", dct[k])
        if k == Qt.Key_Y:
            print("Key Qt.Key_Y == ", dct[k])
        if k == Qt.Key_M:
            print("Key Qt.Key_M == ", dct[k])
        if k == Qt.Key_Alt:
            print("Key Qt.Key_Alt == ", dct[k])


class InputState(object):
    def __init__(self):
        """
        __init__(): description

        :returns: None
        """

        self.keyisPressed = {}
        self.keyisPressed[Qt.Key_X] = False
        self.keyisPressed[Qt.Key_Y] = False
        # 'S'cribble, for controlling motors
        self.keyisPressed[Qt.Key_M] = False
        # self.keyisPressed[Qt.Key_Space] = False
        self.keyisPressed[Qt.Key_Alt] = False
        # self.keyisPressed[Qt.Key_F1] = False  # for emitting a new_roi_center
        self.keyisPressed[Qt.Key_C] = False  # for emitting a new_roi_center
        self.keyisPressed[Qt.Key_Control] = False

        self.btnisPressed = {}
        self.btnisPressed[QtCore.Qt.MouseButton.LeftButton] = False
        self.btnisPressed[QtCore.Qt.MouseButton.MiddleButton] = False
        self.btnisPressed[QtCore.Qt.MouseButton.RightButton] = False

        # represents the delta values
        self.center = (0.0, 0.0)
        self.range = (0.0, 0.0)
        self.npts = (0, 0)
        self.rect = (0, 0, 0, 0)
        self.shape_outof_range = False
        self.force_out_of_range = False

        # the id of the currently selected plotItem
        self.plotitem_id = None  # a unique ID number
        self.plotitem_title = None  # the title ex: SEG 2
        self.plotitem_shape = None  # the current shape item
        # the type of the plot item, one of the types.spatial_type_prefix types (PNT,
        # SEG, ROI)
        self.plotitem_type = None

    def reset(self):
        self.keyisPressed = {}
        self.keyisPressed[Qt.Key_X] = False
        self.keyisPressed[Qt.Key_Y] = False
        self.keyisPressed[Qt.Key_M] = False  # for controlling motors
        # self.keyisPressed[Qt.Key_Space] = False
        self.keyisPressed[Qt.Key_Alt] = False
        self.keyisPressed[Qt.Key_C] = False
        self.keyisPressed[Qt.Key_Control] = False

        self.btnisPressed = {}
        self.btnisPressed[QtCore.Qt.MouseButton.LeftButton] = False
        self.btnisPressed[QtCore.Qt.MouseButton.MiddleButton] = False
        self.btnisPressed[QtCore.Qt.MouseButton.RightButton] = False

        # represents the delta values
        self.center = (0.0, 0.0)
        self.range = (0.0, 0.0)
        self.npts = (0, 0)
        self.rect = (0, 0, 0, 0)

        # the id of the currently selected plotItem
        self.plotitem_id = None  # a unique ID number
        self.plotitem_title = None  # the title ex: SEG 2
        self.plotitem_shape = None  # the current shape item
        # the type of the plot item, one of the types.spatial_type_prefix types (PNT,
        # SEG, ROI)
        self.plotitem_type = None


class ImageWidgetPlot(PlotDialog):

    new_region = pyqtSignal(object)
    region_changed = pyqtSignal(object)
    region_deleted = pyqtSignal(object)
    region_selected = pyqtSignal(object)
    new_ellipse = pyqtSignal(object)
    target_moved = pyqtSignal(object)
    shape_moved = pyqtSignal(object)
    new_roi_center = pyqtSignal(object)
    scan_loaded = pyqtSignal(object)
    dropped = QtCore.pyqtSignal(QtCore.QMimeData)
    new_beam_position = QtCore.pyqtSignal(float, float)
    new_selected_position = QtCore.pyqtSignal(float, float)

    def __init__(
        self,
        parent,
        filtStr=FILTER_STRING,
        tsting=False,
        type="basic",
        sample_pos_mode=None,
        options=None,
        settings_fname="settings.json",
    ):
        """
        __init__(): description

        :param parent: parent description
        :type parent: parent type

        :param filtStr="*.hdf5": filtStr="*.hdf5" description
        :type filtStr="*.hdf5": filtStr="*.hdf5" type

        :param tsting=False: tsting=False description
        :type tsting=False: tsting=False type

        :param type='basic': type='basic' description
        :type type='basic': type='basic' type

        :param options=None: options=None description
        :type options=None: options=None type

        :returns: None
        background="#555555"
        background="#3e3e3e"
        """
        self.gridparam = make.gridparam(
            background = master_colors["plot_bckgrnd"]["rgb_str"],
            minor_enabled = (False, False),
            major_enabled = (False, False),
        )
        # these variables are needed because they are used in function calls made by the  PlotDialog constructor

        self.fileFilterStr = filtStr
        self.type = type
        self._data_dir = ""
        self.data_io = None
        self._auto_contrast = True
        self.data: Dict[str, np.ndarray] = {}
        self.items = {}
        self.image_type = (
            None  # used to identify what type of image == currently being displayed
        )
        self.dataHeight = 0
        self.dataWidth = 0
        self.wPtr = 0
        self.hPtr = 0
        self.xstep = 1.0
        self.ystep = 1.0
        # scalars for non-square data
        self.htSc = 1
        self.widthSc = 1
        self.dataAtMax = False
        self.image_is_new = True
        self.checkRegionEnabled = True
        self.multi_region_enabled = True
        self.show_image_params = False
        self.drop_enabled = True
        self.fill_plot_window = False
        self.bmspot_fbk_obj = None
        self.progbar = None
        self.selected_detectors = []

        self._cur_shape_uid = -1

        # a dict to keep track of the priority of images that are added and their relationship to which images are closure
        # to the surface and which are lower
        self.add_images_z_depth_dct = {}
        self.roiNum = 0
        self.segNum = 0
        self.shapeNum = 0
        self.pntNum = 0

        self.max_shape_size = (None, None)
        self._trimage_max_sizes = {}

        # transform factors for pixel to unit conversion
        self.xTransform = 0.0
        self.yTransform = 0.0
        self.zTransform = 0.0
        self.unitTransform = "um"

        self.show_beam_spot = False
        self.prev_beam_pos = (0.0, 0.0)
        #
        if options == None:
            options = PlotOptions(
                show_xsection=True,
                show_ysection=True,
                xsection_pos="top",
                ysection_pos="right",
                xlabel=("um", ""),
                ylabel=("um", ""),
                zlabel=None,
                show_contrast=True,
                lock_aspect_ratio=True,
                gridparam=self.gridparam,
                yreverse=False
            )
        else:
            #make sure this is turned off otherwise it will flip the axis for images
            options.yreverse = False

        self.sel_item_id = None

        if self.type == "analyze":
            self.register_tools = self.register_analyze_tools
        elif self.type == "select":
            self.register_tools = self.register_select_tools
        elif self.type == "calib_camera":
            self.register_tools = self.register_camera_tools
        elif self.type == "ptycho_camera":
            self.register_tools = self.register_ptycho_camera_tools
        else:
            self.register_tools = self.register_basic_tools

        super(ImageWidgetPlot, self).__init__(
            title="", toolbar=True, edit=False, options=options
        )
        self.setObjectName("ImageWidgetPlot")
        self.settings_fname = os.path.join(plotDir, settings_fname)
        if not os.path.exists(self.settings_fname):
            osa_smplhldr_dct = make_dflt_stxm_osa_smplholder_settings_dct(
                self.settings_fname
            )

        else:
            osa_smplhldr_dct = file_to_json(self.settings_fname)

        self.ss = SaveSettings(self.settings_fname, dct_template=osa_smplhldr_dct)

        contrast_pnl = self.get_contrast_panel()
        gpplot = contrast_pnl.get_plot()
        gpplot.get_items()[0].gridparam.background = master_colors["plot_bckgrnd"]["rgb_hex"]
        gpplot.get_items()[0].gridparam.update_grid(gpplot.get_items()[0])

        self.osa_type = OSA_AMBIENT
        self.sample_hldr_type = SAMPLE_GONI

        # init this first because the constructor for  PlotDialog will call our
        # over ridden 'register_tools' function which needs this param

        self.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().setSpacing(2)

        # self.setMinimumSize(400, 300)
        self.checkRegionEnabled = True
        #
        # # setup some default values
        self.max_roi = 100000
        self.max_seg_len = 1000
        self.max_shape_size = (5000, 5000)
        #
        self.roi_limit_def = None
        self.seg_limit_def = None
        self.pnt_limit_def = None
        #
        self.zoom_scale = 1.0
        self.zoom_rngx = 1.0
        self.zoom_rngy = 1.00


        #
        #
        # create an instance of InputState so that I can
        # connect key presses with mouse events
        self.inputState = InputState()
        #
        self.filtVal = 0
        self.plot = self.get_plot()
        pcan = self.plot.canvas()
        pcan.setObjectName("imagePlotBgrnd")
        pcan.setStyleSheet("background-color: %s;" % master_colors["plot_bckgrnd"]["rgb_str"])
        #
        xcs = self.get_xcs_panel()
        xcs.set_options(autoscale=True)
        xcs.cs_plot.toggle_perimage_mode(True)
        xcan = xcs.cs_plot.canvas()
        xcan.setObjectName("xCrossSection")
        xcan.setStyleSheet("background-color: %s;" % master_colors["plot_bckgrnd"]["rgb_str"])

        ycs = self.get_ycs_panel()
        ycs.set_options(autoscale=True)
        ycs.cs_plot.toggle_perimage_mode(True)
        ycan = ycs.cs_plot.canvas()
        ycan.setObjectName("yCrossSection")
        ycan.setStyleSheet("background-color: %s;" % master_colors["plot_bckgrnd"]["rgb_str"])

        # force the cross section colors to be the color we want
        xcs.cs_plot.param.line.color = master_colors['app_plot_blue']["rgb_hex"]  # "#0e64cc"
        ycs.cs_plot.param.line.color = master_colors['app_plot_blue']["rgb_hex"]  # "#0e64cc"
        # SHADE == the alpha channel
        xcs.cs_plot.SHADE = 0.95
        ycs.cs_plot.SHADE = 0.95

        self.plot.plotLayout().setCanvasMargin(0)
        self.plot.plotLayout().setAlignCanvasToScales(True)
        #
        # set legend
        self.legend = Qwt.QwtLegend()
        self.legend.setDefaultItemMode(Qwt.QwtLegendData.Checkable)
        # self.plot.insertLegend(self.legend, Qwt.QwtPlot.RightLegend)
        self.plot.insertLegend(self.legend, Qwt.QwtPlot.BottomLegend)

        self.plot.SIG_ITEM_SELECTION_CHANGED.connect(self.selected_item_changed)
        self.plot.SIG_ITEMS_CHANGED.connect(self.items_changed)
        self.plot.SIG_ITEM_MOVED.connect(self.active_item_moved)
        self.plot.SIG_ANNOTATION_CHANGED.connect(self.annotation_item_changed)
        self.plot.SIG_MARKER_CHANGED.connect(self.marker_changed)
        self.plot.SIG_ITEM_HANDLE_MOVED.connect(self.item_handle_moved)
        # self.plot.SIG_TOOL_JOB_FINISHED.connect(self.shape_end_rect)
        self.plot.SIG_ACTIVE_ITEM_CHANGED.connect(self.on_active_item_changed)
        self.plot.SIG_PLOT_AXIS_CHANGED.connect(self.on_sig_plot_axis_changed)
        self.plot.SIG_AXES_CHANGED.connect(self.on_sig_axes_changed)

        self.dropped.connect(self.on_drop)
        # force the plot axis to make vertical 0 at the bottom instead of the
        # default of top
        self.plot.set_axis_direction("left", False)
        #
        # force the plot to snap to fit the current plot in
        self.set_autoscale()
        self.plot.unselect_all()
        #
        if tsting:
            self.tstTimer = QTimer()
            self.tstTimer.timeout.connect(self.tstDataPoint)
            self.tstTimer.start(10)
        else:
            self.tstTimer = None

        self.set_grid_colors()

        self.set_center_at_0(2000, 2000)
        #
        self.param_gbox = None
        #
        self.setAcceptDrops(True)
        #
        self.init_param_cross_marker()
        self.add_all_red_colormap()

        self._shape_registry = {}

        # now force the contrast colors to be what we want
        _cpnl = self.get_contrast_panel()
        _cpnl.local_manager.get_plot().canvas().setStyleSheet("background-color: rgb(20,20,20);")
        _cpnl.local_manager.get_plot().param.line.color = master_colors['app_histo_blue']["rgb_hex"]
        if hasattr(_cpnl, "histogram"):
            _cpnl.histogram.range_mono_color = "yellow"
            _cpnl.histogram.range_multi_color = "yellow"
            _cpnl.histogram.range.shapeparam.line.color = "#ffff7f"
            _cpnl.histogram.range.shapeparam.sel_line.color = "yellow"
            _cpnl.histogram.range.shapeparam.symbol.facecolor = "yellow"
            _cpnl.histogram.range.shapeparam.sel_symbol.color = "yellow"
            _cpnl.histogram.range.shapeparam.sel_symbol.facecolor = "yellow"
            _cpnl.histogram.range.shapeparam.fill = "yellow"
            _cpnl.histogram.range.shapeparam.shade = 0.15


    def get_xcs_panel(self):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        xcs = plot.manager.get_xcs_panel()
        return xcs

    def get_ycs_panel(self):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        ycs = plot.manager.get_ycs_panel()
        return ycs

    def add_all_red_colormap(self):
        """
        used to indicate errors
        """
        red_cmap = get_cmap("hsv")
        qclr = QtGui.QColor()
        qclr.setRgb(255, 0, 0)
        red_cmap.setColorInterval(qclr, qclr)
        register_extra_colormap("allred", red_cmap)


    def get_selected_detectors(self):
        '''
        return the current list of detectors that have been selected by the parent widget
        '''
        return(self.selected_detectors)

    def set_selected_detectors(self, det_nm_lst=[]):
        '''
        set a list of detector names that will be used to populate the SignalSlectionTool pull down list
        '''
        self.selected_detectors = det_nm_lst
        sigsel_tool = self.plot.manager.get_tool(tools.clsSignalSelectTool)
        action = QtWidgets.QAction()
        action.setText(self.selected_detectors[0])
        sigsel_tool.activate_sigsel_tool(action)
        sigsel_tool.update_menu(self.manager)


    def set_image_type(self, image_type):
        """
        sometimes it when switching between different scans it == required that the wdg_com dict that gets emitted
        by the tools knows what type of image it should be using  as focus scans use Z coordinates for Y plot coordinates.
        :param image_type:
        :return:
        """
        self.image_type = image_type

    def set_fill_plot_window(self, val):
        """
        when the user clicks auto scale, it will check this flag to see if they want the plot to be filled or not
        :param val:
        :return:
        """
        self.fill_plot_window = val

    def replot(self):
        plot = self.get_plot()
        plot.replot()

    # def register_shape_info(self, shape_info_dct={'shape_title': None, 'on_selected': None}):
    def register_shape_info(self, shape_info_dct={}):
        self._shape_registry[shape_info_dct["shape_title"]] = shape_info_dct

    def get_shape_titles_from_registry(self):
        return self._shape_registry.keys()

    def get_shape_from_registry(self, shape_title):
        if shape_title in self._shape_registry.keys():
            return self._shape_registry[shape_title]

    def set_grid_colors(self):
        
        fg_clr = master_colors["plot_forgrnd"]["rgb_str"]
        bg_clr = master_colors["plot_bckgrnd"]["rgb_str"]
        min_clr = master_colors["plot_gridmaj"]["rgb_str"]
        maj_clr = master_colors["plot_gridmin"]["rgb_str"]

        # self.set_grid_parameters("#323232", "#343442", "#545454")
        # self.set_grid_parameters("#7d7d7d", "#343442", "#545454")
        self.set_grid_parameters(bg_clr, min_clr, maj_clr)
        self.set_cs_grid_parameters(fg_clr, bg_clr, min_clr, maj_clr)

    def update_style(self):
        print("Updating style")
        ss = get_style()
        self.setStyleSheet(ss)
        self.set_grid_colors()

    def set_dataIO(self, data_io_cls):
        self.data_io = data_io_cls

    def init_param_cross_marker(self):
        """create a marker used for adjusting the center of a scan based on pressing
         Ctrl-C and moving the mouse around on the screen over an image, this will
        cause the image plot to emit the center_changed signal
        """
        self.param_cross_marker = shape.Marker()
        section = "plot"
        self.param_cross_marker.set_style(section, "marker/parmcross")
        self.param_cross_marker.setVisible(False)
        self.param_cross_marker.attach(self.plot)

    def update_contrast(self, img_idx=None):
        if len(self.items) > 0:
            if img_idx is None:
                # use most recent item
                keys = list(self.items.keys())
                img_idx = keys[-1]

            if self.items[img_idx] is not None:
                self._select_this_item(self.items[img_idx], False)

    def set_enable_drop_events(self, en):
        self.drop_enabled = en

    def dragEnterEvent(self, event):
        if self.drop_enabled:
            event.acceptProposedAction()
            self.dropped.emit(event.mimeData())

    def dragMoveEvent(self, event):
        if self.drop_enabled:
            event.acceptProposedAction()

    # @exception
    def dropEvent(self, event):
        if self.drop_enabled:
            # import simplejson as json
            mimeData = event.mimeData()
            if mimeData.hasImage():
                # self.setPixmap(QtGui.QPixmap(mimeData.imageData()))
                # print 'dropEvent: mime data has an IMAGE'
                pass
            elif mimeData.hasHtml():
                # self.setText(mimeData.html())
                # self.setTextFormat(QtCore.Qt.RichText)
                # print 'dropEvent: mime data has HTML'
                pass
            elif mimeData.hasText():
                # self.setText(mimeData.text())
                # self.setTextFormat(QtCore.Qt.PlainText)
                # print 'dropEvent: mime data has an TEXT = \n[%s]' %
                # mimeData.text()
                dct = mime_to_dct(mimeData)
                # print 'dropped file == : %s' % dct['file']
                self.blockSignals(True)
                self.openfile(
                    [dct["file"]],
                    scan_type=dct["scan_type_num"],
                    addimages=True,
                    dropped=True,
                    stack_index=dct.get("stack_index"),
                )
                self.blockSignals(False)
            elif mimeData.hasUrls():
                # print 'dropEvent: mime data has URLs'
                pass
            else:
                # self.setText("Cannot display data")
                # print 'dropEvent: mime data Cannot display data'
                pass

            # self.setBackgroundRole(QtGui.QPalette.Dark)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        if self.drop_enabled:
            event.accept()

    @exception
    def on_drop(self, mimeData=None):
        # self.formatsTable.setRowCount(0)

        if self.drop_enabled:
            if mimeData == None:
                return

            for format in mimeData.formats():
                formatItem = QtWidgets.QTableWidgetItem(format)
                formatItem.setFlags(QtCore.Qt.ItemIsEnabled)
                formatItem.setTextAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

                if format == "text/plain":
                    text = mimeData.text()  # .strip()
                elif format == "text/html":
                    text = mimeData.html()  # .strip()
                elif format == "text/uri-list":
                    text = " ".join([url.toString() for url in mimeData.urls()])
                elif format == 'application/x-stxmscan':
                    text = mimeData.text()
                else:
                    # text = " ".join(["%02X" % ord(datum)
                    #                 for datum in mimeData.data(format)])
                    # text = " ".join(["%02X" % ord(datum) for datum in str(mimeData.data(format))])
                    if str(mimeData.data(format)).find("8f") > -1:
                        text = " ".join(
                            [
                                "%02X" % ord(datum)
                                for datum in str(mimeData.data(format))
                            ]
                        )
                    else:
                        text = " ".join(
                            [
                                "%02X" % ord(datum)
                                for datum in str(
                                    mimeData.data(format), encoding="cp1252"
                                )
                            ])

                    # print(" ".join(["%02X" % ord(datum) for datum in str(mimeData.data(format), encoding='cp1252')]))
                    # text = " ".join(["%02X" % ord(datum) for datum in str(mimeData.data(format), encoding='cp1252')])

    def on_sig_axes_changed(self, obj):
        """
        on_sig_axes_changed(): description
        :param obj: obj description
        :type obj: obj type

        :returns: None
        """
        # print 'on_sig_axes_changed'
        # print obj
        pass

    def enable_image_param_display(self, val):
        self.show_image_params = val
        if self.show_image_params:
            self.param_gbox = DataSetShowGroupBox(_("Image parameters"), ImageParam)
            self.plot_layout.addWidget(self.param_gbox)
        # else:
        #    self.plot_layout.addWidget(self.param_gbox)

        ############## INTERFACE ROUTINES ####################
        # def load_file_data(self, data):
        """
        load_file_data(): description

        :param data: data description
        :type data: data type

        :returns: None
        """
        #    """ set the plotting data to data """
        #    pass

        # def add_data(self, data):
        """
        add_data(): description

        :param data: data description
        :type data: data type

        :returns: None
        """

    #    """ append data to the current plotting data """
    #    pass

    def update(self):
        """
        update(): description

        :returns: None
        """
        """ force and update to the plot """
        pass

    def get_selected_data(self, rangeX, rangeY):
        """
        get_selected_data(): description

        :param rangeX: rangeX description
        :type rangeX: rangeX type

        :param rangeY: rangeY description
        :type rangeY: rangeY type

        :returns: None
        """
        """ return the selected data as a numpy array """
        pass

    def get_data(self, item_name, flip=False):
        """
        get_data(): description

        :returns: None
        """
        """ return all of the plotting data as a numpy array"""
        if flip:
            return np.flipud(self.data[item_name])
        else:
            item = self.get_image_item(item_name)
            if item:
                item.data.shape
                return np.copy(item.data)
            else:
                return None
            # if img_idx in self.data.keys():
            #     return self.data[img_idx]
            # else:
            #     return None

    ############## End of INTERFACE ROUTINES ####################
    def register_tools(self):
        """
        register_tools(): description

        :returns: None
        """
        self.register_basic_tools()

    def on_select_tool_changed(self, filter, event):
        """
        on_select_tool_changed(): This handler fires when the user has held Ctrl-C down and
        moved the mouse overtop the plot window, the purpose of this == to emit the center_changed signal
        which can then be used by listeners to automatically modify the center of a scan parameter.

        The signal that this slot services == emitted by the tools.clsSelectTool

        :param filter: filter description
        :type filter: filter type

        :param event: event description
        :type event: event type

        :returns: None
        """

        if event == None:
            self.param_cross_marker.setVisible(False)
            self.plot.replot()

        elif event.modifiers() & Qt.ControlModifier or self.plot.canvas_pointer:
            pass
            # pos = event.pos()
            # self.plot.set_marker_axes()
            # self.param_cross_marker.setZ(self.plot.get_max_z() + 1)
            # self.param_cross_marker.setVisible(True)
            # self.param_cross_marker.move_local_point_to(0, pos)
            # self.plot.replot()
            #
            # c = QPointF(pos.x(), pos.y())
            # # x, y = self.plot.cross_marker.canvas_to_axes(c)
            # x, y = self.plot.canvas2plotitem(self.param_cross_marker, pos.x(), pos.y())
            # # print 'canvas_to_axes: x=%.1f y=%.1f' % (x, y)
            #
            # self.inputState.center = (x, y)
            # self.inputState.range = (0, 0)
            # self.inputState.npts = (None, None)
            # self.inputState.rect = (x, y, 0, 0)
            # self.inputState.plotitem_type = None
            # # sept 18 2017
            # self.inputState.plotitem_id = get_current_unique_id()
            # self.inputState.plotitem_shape = self.param_cross_marker
            # # print 'on_select_tool_changed: emitting_new_roi'
            # self._emit_new_roi(self.image_type)
            #
            # # print 'x=%.1f y=%.1f' % (pos.x(), pos.y())
            # # x, y = self.plot.cross_marker.axes_to_canvas(pos.x(), pos.y())
            #
            # # self.marker_changed(self.param_cross_marker)

        else:
            vis_parmcross = self.param_cross_marker.isVisible()
            self.param_cross_marker.setVisible(False)

            if vis_parmcross:
                self.plot.replot()

    def add_tool(self, toolklass, *args, **kwargs):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        # print(plot.manager.toolbars)
        tool = plot.manager.add_tool(toolklass, *args, **kwargs)
        return tool

    def add_separator_tool(self, toolbar_id=None):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        plot.manager.add_separator_tool(toolbar_id)


    def register_select_tools(self):
        """
        register_select_tools(): description

        :returns: None
        """
        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=self.fileFilterStr)
        self.opentool.set_directory(self._data_dir)
        self.opentool.openfile.connect(self.openfile)

        # self.selectTool = self.add_tool(SelectTool)
        self.selectTool = self.add_tool(tools.clsSelectTool)
        self.selectTool.changed.connect(self.on_select_tool_changed)

        self.add_tool(BasePlotMenuTool, "item")
        self.add_tool(ColormapTool)
        self.add_separator_tool()
        self.add_tool(PrintTool)
        self.add_tool(DisplayCoordsTool)

        self.plot = self.get_plot()
        clr_ac = self.get_clear_images_action()

        # clr_ac.setChecked(self._auto_contrast)
        add_actions(self.plot.manager.toolbars['default'], [clr_ac])

        self.add_separator_tool()
        self.addTool("tools.clsSquareAspectRatioTool")
        self.add_separator_tool()

        self.add_tool(ReverseYAxisTool)

        # rt = StxmRectangleTool
        # rt.TITLE = _("2D Region")
        # rt.create_shape = self._create_rect_shape
        # at = self.add_tool(
        #     rt,
        #     setup_shape_cb=self._setup_rect_shape,
        #     handle_final_shape_cb=self._handle_final_rect_shape)

        #        ast = tools.clsMeasureTool
        #        #ast.create_shape = self._create_seg_shape
        #        aa = self.add_tool(
        #            ast,
        #            setup_shape_cb=self._setupsegment,
        #            handle_final_shape_cb=self._handle_final_segment_shape)
        #        aa.TITLE = _("%s %d" % (types.spatial_type_prefix.SEG, self.segNum))

        # apt = AnnotatedPointTool
        apt = tools.clsPointTool
        apt.create_shape = self._create_point_shape
        ap = self.add_tool(
            apt,
            setup_shape_cb=self.setuppoint,
            handle_final_shape_cb=self._handle_final_point_shape,
        )
        # ap.TITLE = _("selecting")

        self.set_default_tool(self.selectTool)
        self.get_default_tool().activate()

    def register_camera_tools(self):
        """
        register_camera_tools(): description

        :returns: None
        """
        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=FILTER_STRING)
        self.opentool.set_directory(self._data_dir)
        self.opentool.openfile.connect(self.openfile)
        self.selectTool = self.add_tool(tools.clsSelectTool)
        self.selectTool.changed.connect(self.on_select_tool_changed)
        self.add_tool(BasePlotMenuTool, "item")
        self.add_tool(ColormapTool)
        self.add_tool(SnapshotTool)

        self.add_separator_tool()

        self.add_tool(PrintTool)

        self.addTool("tools.clsHorizMeasureTool")
        self.add_separator_tool()
        self.plot = self.get_plot()
        clr_ac = self.get_clear_images_action()

        # clr_ac.setChecked(self._auto_contrast)
        add_actions(self.plot.manager.toolbars['default'], [clr_ac])

        self.set_default_tool(self.selectTool)
        self.get_default_tool().activate()

    def register_ptycho_camera_tools(self):
        """
        register_camera_tools(): description

        :returns: None
        """
        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=FILTER_STRING)
        self.opentool.set_directory(self._data_dir)
        self.opentool.openfile.connect(self.openfile)
        self.selectTool = self.add_tool(tools.clsSelectTool)
        self.selectTool.changed.connect(self.on_select_tool_changed)
        self.add_tool(BasePlotMenuTool, "item")
        self.add_tool(ColormapTool)
        self.add_tool(SnapshotTool)
        self.add_tool(PrintTool)
        self.add_tool(HelpTool)

        self.add_separator_tool()
        self.addTool("tools.clsMeasureTool",units="pixels")

        self.plot = self.get_plot()
        clr_ac = self.get_clear_images_action()

        # clr_ac.setChecked(self._auto_contrast)
        add_actions(self.plot.manager.toolbars['default'], [clr_ac])

        self.set_default_tool(self.selectTool)
        self.get_default_tool().activate()

    def register_analyze_tools(self):
        """
        register_analyze_tools(): description

        :returns: None
        """
        # opentool = self.add_tool(OpenFileTool, "*.json;*.hdr;*.tif;*.jpg")
        # opentool = self.add_tool(OpenFileTool, self.fileFilterStr)
        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=self.fileFilterStr)
        self.opentool.set_directory(self._data_dir)
        self.opentool.openfile.connect(self.openfile)
        self.add_tool(ReverseYAxisTool)
        self.add_tool(SaveAsTool)

        self.add_separator_tool()

        self.addTool("tools.clsSquareAspectRatioTool")

        self.add_separator_tool()

        # self.selectTool = self.add_tool(SelectTool)
        self.selectTool = self.add_tool(tools.clsSelectTool)
        self.selectTool.changed.connect(self.on_select_tool_changed)
        self.add_tool(BasePlotMenuTool, "item")
        self.add_tool(ColormapTool)
        # self.add_tool(XCSPanelTool)
        self.add_tool(YCSPanelTool)
        self.add_tool(SnapshotTool)
        self.add_tool(RectZoomTool)

        self.add_separator_tool()

        self.add_tool(PrintTool)
        self.add_tool(DisplayCoordsTool)

        self.plot = self.get_plot()
        clr_ac = self.get_clear_images_action()
        # clr_ac.setChecked(self._auto_contrast)
        add_actions(self.plot.manager.toolbars['default'], [clr_ac])
        self.add_separator_tool()

        art = tools.clsAverageCrossSectionTool
        # art.TITLE = _("Select ROI")
        art.create_shape = self._create_rect_shape
        at = self.add_tool(
            art,
            setup_shape_cb=self._setup_rect_shape,
            handle_final_shape_cb=self._handle_final_rect_shape,
        )
        at.action.setVisible(False)

        self.addTool("tools.clsSegmentTool", is_visible=False)
        self.addTool("tools.clsHLineSegmentTool", is_visible=False)

        apt = tools.clsPointTool
        # apt.create_shape = self._create_point_shape
        ap = self.add_tool(
            apt,
            setup_shape_cb=self.setuppoint,
            handle_final_shape_cb=self._handle_final_point_shape
        )
        ap.action.setVisible(False)
        self.add_separator_tool()

        meas = self.add_tool(tools.clsMeasureTool)
        # add an auto contrast tool button, remove the default toolbuttons, all
        # except set to full range based on data
        cpnl = self.get_contrast_panel()
        cpnl_actions = cpnl.toolbar.actions()
        cpnl.toolbar.removeAction(cpnl_actions[1])
        cpnl.toolbar.removeAction(cpnl_actions[2])
        cpnl.toolbar.removeAction(cpnl_actions[3])
        con_ac = cpnl.manager.create_action(
            "Auto Contrast",
            toggled=self.set_auto_contrast,
            icon=get_icon("csapplylut.png"),
            tip=_("Enable Auto Contrast "),
        )
        con_ac.setChecked(self._auto_contrast)
        add_actions(cpnl.toolbar, [con_ac])

        self.set_default_tool(self.selectTool)
        self.get_default_tool().activate()

    def activate_sel_horizontal_pos_tool(self, chkd):
        if chkd:
            self.activate_tool("clsHorizSelectPositionTool")
        else:
            self.deactivate_tool("clsHorizSelectPositionTool")

    def activate_sel_center_pos_tool(self, chkd):
        if chkd:
            self.activate_tool("clsCrossHairSelectPositionTool")
        else:
            self.deactivate_tool("clsCrossHairSelectPositionTool")
            #make sure it goes back to default tool
            self.selectTool.activate()

    def activate_horiz_line_sel_tool(self, chkd):
        if chkd:
            self.activate_tool("clsHLineSegmentTool")
        else:
            self.deactivate_tool("clsHLineSegmentTool")

    def activate_arbitrary_line_sel_tool(self, chkd):
        if chkd:
            self.activate_tool("clsSegmentTool")
        else:
            self.deactivate_tool("clsSegmentTool")

    def activate_point_sel_tool(self, chkd):
        if chkd:
            self.activate_tool("clsPointTool")
        else:
            self.deactivate_tool("clsPointTool")

    def deactivate_tool(self, toolstr):
        """
        deactivate a tool by name
        """
        dct = self.toolclasses_to_dct()
        if toolstr in list(dct.keys()):
            tool = dct[toolstr]
            if hasattr(tool, "deactivate"):
                tool.deactivate()
        self.plot.replot()

    def activate_tool(self, toolstr):
        """
        activate the given too specified by the toolstring if it exists on the current plot
        """
        # tb = self.plot.manager.get_toolbar()
        # actions = tb.actions()
        # for ac in actions:
        #     # print 'enable_menu_action: checking [%s]' % ac.text()
        #     if ac.text().find(toolstr) > -1:
        #         ac.setEnabled(1)
        #         break
        dct = self.toolclasses_to_dct()
        if toolstr in list(dct.keys()):
            tool = dct[toolstr]
            if hasattr(tool, "activate"):
                tool.activate()


    def register_osa_and_samplehldr_tool(
        self, sample_pos_mode=types.sample_positioning_modes.COARSE
    ):
        """
        register_osa_and_samplehldr_tool(): register the osa and sample holder tools

        :returns: None
        """
        sht = self.add_tool(tools.StxmShowSampleHolderTool)
        osat = self.add_tool(tools.StxmShowOSATool)

        if sample_pos_mode == types.sample_positioning_modes.GONIOMETER:
            osat.changed.connect(self.create_uhv_osa)
            self.osa_type = OSA_CRYO
            sht.changed.connect(self.create_goni_sample_holder)
            self.sample_hldr_type = SAMPLE_GONI

        else:
            self.osa_type = OSA_AMBIENT
            osat.changed.connect(self.create_osa)
            sht.changed.connect(self.create_stdrd_sample_holder)
            self.sample_hldr_type = SAMPLE_STANDARD

    def register_samplehldr_tool(
        self, sample_pos_mode=types.sample_positioning_modes.COARSE
    ):
        """
        register_osa_and_samplehldr_tool(): register the osa and sample holder tools

        :returns: None
        """
        sht = self.add_tool(tools.StxmShowSampleHolderTool)

        if sample_pos_mode == types.sample_positioning_modes.GONIOMETER:
            sht.changed.connect(self.create_goni_sample_holder)
            self.sample_hldr_type = SAMPLE_GONI

        else:
            sht.changed.connect(self.create_stdrd_sample_holder)
            self.sample_hldr_type = SAMPLE_STANDARD

    def register_osa_tool(self, sample_pos_mode=types.sample_positioning_modes.COARSE):
        """
        register_osa_and_samplehldr_tool(): register the osa and sample holder tools

        :returns: None
        """
        osat = self.add_tool(tools.StxmShowOSATool)

        if sample_pos_mode == types.sample_positioning_modes.GONIOMETER:
            osat.changed.connect(self.create_uhv_osa)
            self.osa_type = OSA_CRYO

        else:
            self.osa_type = OSA_AMBIENT
            osat.changed.connect(self.create_osa)

    def get_contrast_panel(self, plot=None):
        '''
        a result of the port to plotpy, redirect to new location
        '''
        if plot == None:
            plot = self.get_plot()
        return plot.manager.get_contrast_panel()

    def register_basic_tools(self):
        """
        register_basic_tools(): description

        :returns: None
        """
        # self.plot = self.get_plot()
        # self.plot.manager.toolbar.hide()
        # toolbar = QtWidgets.QToolBar(_("Tools"))
        # self.plot.manager.add_toolbar("Basic", toolbar)
        # toolbar.show()

        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=self.fileFilterStr)
        self.opentool.set_directory(self._data_dir)
        self.opentool.openfile.connect(self.openfile)

        # self.selectTool = self.add_tool(SelectTool)
        self.selectTool = self.add_tool(tools.clsSelectTool)
        self.selectTool.changed.connect(self.on_select_tool_changed)
        self.add_tool(BasePlotMenuTool, "item")
        self.add_tool(ColormapTool)
        self.add_tool(SnapshotTool)
        self.add_separator_tool()

        self.add_tool(PrintTool)
        self.addTool("tools.clsSquareAspectRatioTool")

        # add an auto contrast tool button, remove the default toolbuttons, all
        # except set to full range based on data
        cpnl = self.get_contrast_panel()
        cpnl_actions = cpnl.toolbar.actions()
        for i in range(1, len(cpnl_actions)):
            cpnl.toolbar.removeAction(cpnl_actions[i])
        # cpnl.toolbar.removeAction(cpnl_actions[2])
        # cpnl.toolbar.removeAction(cpnl_actions[3])
        con_ac = cpnl.manager.create_action(
            "Auto Contrast",
            toggled=self.set_auto_contrast,
            icon=get_icon("csapplylut.png"),
            tip=_("Enable Auto Contrast "),
        )
        con_ac.setChecked(self._auto_contrast)
        add_actions(cpnl.toolbar, [con_ac])

        self.add_separator_tool()
        self.plot = self.get_plot()
        clr_ac = self.get_clear_images_action()
        # clr_ac.setChecked(self._auto_contrast)
        add_actions(self.plot.manager.toolbars['default'], [clr_ac])


        self.add_separator_tool()
        bs_tool = self.add_tool(tools.BeamSpotTool, self.get_plot())
        bs_tool.changed.connect(self.enable_beam_spot)
        self.add_separator_tool()

        self.set_default_tool(self.selectTool)
        self.get_default_tool().activate()

    def activate_create_roi_tool(self, chkd):
        if chkd:
            self.activate_tool("clsROITool")
        else:
            self.deactivate_tool("clsROITool")
            self.get_default_tool().activate()

    def set_default_tool(self, toolklass):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        plot.manager.set_default_tool(toolklass)

    def get_default_tool(self):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        return plot.manager.get_default_tool()

    def enable_menu_action(self, ac_name, val):
        assert type(ac_name) == str, (
            "enable_menu_action: ac_name != a string: %r" % ac_name
        )
        assert type(val) == bool, "enable_menu_action: val != a boolean:"
        tb = self.plot.manager.get_toolbar()
        actions = tb.actions()
        for ac in actions:
            # print 'enable_menu_action: checking [%s]' % ac.text()
            if ac.text().find(ac_name) > -1:
                ac.setEnabled(val)
                break

    def get_clear_images_action(self):
        clr_ac = self.plot.manager.create_action(
            "Clear Plot",
            toggled=partial(self.delImagePlotItems, clear_cached_data=True),
            icon=get_icon("trash.png"),
            tip=_("Clear Images from plot "),
        )
        clr_ac.setCheckable(False)
        # connect it to the triggered signal otherwise it wont fire with checkable set to False which fires 'toggled'
        clr_ac.triggered.connect(partial(self.delImagePlotItems, clear_cached_data=True))

        return clr_ac

    def enable_beam_spot(self, chkd):
        if chkd:
            self.show_beam_spot = True
            # it may not be initialized yet
            if self.bmspot_fbk_obj:
                self.bmspot_fbk_obj.enable_fbk_timer()
        else:
            self.show_beam_spot = False

            # it may not be initialized yet
            if self.bmspot_fbk_obj:
                self.bmspot_fbk_obj.disable_fbk_timer()

            self.blockSignals(True)
            shapes = self.plot.get_items(item_type=IShapeItemType)
            for shape in shapes:
                if hasattr(shape, "shapeparam"):
                    s = shape.shapeparam
                    title = s._title
                    if title.find("beam_spot") > -1:
                        self.delPlotItem(shape)
            self.blockSignals(False)
            self.plot.replot()

    def get_sample_positioning_mode(self):
        return self.sample_pos_mode

    def set_sample_positioning_mode(self, mode):
        self.sample_pos_mode = mode

    def set_auto_contrast(self, auto):
        """
        set_auto_contrast(): description

        :param auto: auto description
        :type auto: auto type

        :returns: None
        """
        self._auto_contrast = auto

    #         if(auto):
    #             self.create_sample_holder()
    #
    #         else:
    #             self.delShapePlotItems()

    def addTool(self, toolstr, is_visible=True, units="um"):
        """
        addTool(): description

        :param toolstr: toolstr description
        :type toolstr: toolstr type

        :param units: if the tool supports setting a unit string
        :type units: string

        :returns: None
        """
        """ a function that allows inheriting widgets to add tools
        where tool == a valid guiqwt tool """
        tool = None
        if toolstr == "LabelTool":
            tool = self.add_tool(LabelTool)
        elif toolstr == "DummySeparatorTool":
            tool = self.add_tool(DummySeparatorTool)
        elif toolstr == "SegmentTool":
            tool = self.add_tool(SegmentTool)
        elif toolstr == "RectangleTool":
            tool = self.add_tool(RectangleTool)
        elif toolstr == "CircleTool":
            self.add_tool(CircleTool)
        elif toolstr == "EllipseTool":
            tool = self.add_tool(EllipseTool)
        elif toolstr == "MultiLineTool":
            tool = self.add_tool(MultiLineTool)
        elif toolstr == "tools.clsMultiLineTool":
            tool = self.add_tool(tools.clsMultiLineTool)
        elif toolstr == "FreeFormTool":
            tool = self.add_tool(FreeFormTool)
        elif toolstr == "PlaceAxesTool":
            tool = self.add_tool(PlaceAxesTool)
        elif toolstr == "HRangeTool":
            tool = self.add_tool(HRangeTool)
        elif toolstr == "AnnotatedRectangleTool":
            tool = self.add_tool(AnnotatedRectangleTool)
        elif toolstr == "AnnotatedCircleTool":
            tool = self.add_tool(AnnotatedCircleTool)
        elif toolstr == "AnnotatedEllipseTool":
            tool = self.add_tool(AnnotatedEllipseTool)
        elif toolstr == "AnnotatedSegmentTool":
            tool = self.add_tool(AnnotatedSegmentTool)
        elif toolstr == "AnnotatedPointTool":
            tool = self.add_tool(AnnotatedPointTool)
        elif toolstr == "AspectRatioTool":
            tool = self.add_tool(AspectRatioTool)
        elif toolstr == "ReverseYAxisTool":
            tool = self.add_tool(ReverseYAxisTool)
        elif toolstr == "tools.clsMeasureTool":
            tool = self.add_tool(tools.clsMeasureTool)
            tool.set_units(units)
        elif toolstr == "ItemCenterTool":
            tool = self.add_tool(ItemCenterTool)
        elif toolstr == "tools.clsSignalSelectTool":
            tool = self.add_tool(tools.clsSignalSelectTool)
        elif toolstr == "HelpTool":
            tool = self.add_tool(HelpTool)
        elif toolstr == "SelectPointTool":
            tool = self.add_tool(SelectPointTool)
        elif toolstr == "tools.StxmControlBeamTool":
            # self.add_tool(tools.StxmControlBeamTool)
            tool = self.add_tool(tools.StxmControlBeamTool)
            tool.changed.connect(self.on_new_direct_beam_pos)
            # sdbt.show_title.connect(self.on_new_direct_beam_pos_title)
        elif toolstr == "tools.BeamSpotTool":
            tool = self.add_tool(tools.BeamSpotTool, self.get_plot())
            tool.changed.connect(self.enable_beam_spot)
        elif toolstr == "tools.clsHorizSelectPositionTool":
            tool = self.add_tool(tools.clsHorizSelectPositionTool)
            tool.changed.connect(self.on_new_selected_position)
            # if not is_visible:
            #     tool.set_enabled(False)
        elif toolstr == "tools.clsCrossHairSelectPositionTool":
            tool = self.add_tool(tools.clsCrossHairSelectPositionTool)
            tool.changed.connect(self.on_new_selected_position)
            # if not is_visible:
            #     #tool.set_enabled(False)
            #     tool.action.setVisible(False)
        elif toolstr == "tools.clsHLineSegmentTool":
            # self.add_tool(tools.HLineSegmentTool)
            # aa = self.add_tool(tools.HLineSegmentTool, setup_shape_cb=self._setupsegment, handle_final_shape_cb=self._handle_final_segment_shape)
            tool = self.add_tool(
                tools.clsHLineSegmentTool,
                handle_final_shape_cb=self._handle_final_horiz_segment_shape,
            )
            tool.TITLE = _("%s %d" % (types.spatial_type_prefix.SEG, self.segNum))

        elif toolstr == "tools.clsHorizMeasureTool":
            tool_1 = tools.clsHorizMeasureTool
            tool = self.add_tool(tool_1)

        elif toolstr == "tools.clsSegmentTool":
            # self.add_tool(tools.HLineSegmentTool)
            # aa = self.add_tool(tools.HLineSegmentTool, setup_shape_cb=self._setupsegment, handle_final_shape_cb=self._handle_final_segment_shape)
            tool = self.add_tool(
                tools.clsSegmentTool,
                handle_final_shape_cb=self._handle_final_horiz_segment_shape,
            )
            tool.TITLE = _("%s %d" % (types.spatial_type_prefix.SEG, self.segNum))

        elif toolstr == "tools.clsPointTool":
            tool = self.add_tool(tools.clsPointTool)

        elif toolstr == "tools.clsSquareAspectRatioTool":
            tool = self.add_tool(tools.clsSquareAspectRatioTool, self.get_plot())
            tool.changed.connect(self.on_set_aspect_ratio)

        elif toolstr == "tools.clsAverageCrossSectionTool":
            tool_1 = tools.clsAverageCrossSectionTool
            # art.TITLE = _("selecting")
            tool_1.create_shape = self._create_rect_shape
            tool = self.add_tool(
                tool_1,
                setup_shape_cb=self._setup_rect_shape,
                handle_final_shape_cb=self._handle_final_rect_shape,
            )

        elif toolstr == "tools.StxmShowSampleHolderTool":
            tool = self.add_tool(tools.StxmShowSampleHolderTool)
            if sample_pos_mode == types.sample_positioning_modes.GONIOMETER:
                tool.changed.connect(self.create_goni_sample_holder)
                self.sample_hldr_type = SAMPLE_GONI
            else:
                tool.changed.connect(self.create_stdrd_sample_holder)
                self.sample_hldr_type = SAMPLE_STANDARD

        elif toolstr == "tools.StxmShowOSATool":
            tool = self.add_tool(tools.StxmShowOSATool)
            if sample_pos_mode == types.sample_positioning_modes.GONIOMETER:
                tool.changed.connect(self.create_uhv_osa)
                self.osa_type = OSA_CRYO

            else:
                self.osa_type = OSA_AMBIENT
                tool.changed.connect(self.create_osa)

        elif toolstr == "tools.clsROITool":
            tool_1 = tools.ROITool
            tool = self.add_tool(tool_1)

        if not is_visible:
            tool.action.setVisible(False)

        return tool

    # def enable_tools_by_spatial_type(self, tp=types.spatial_type_prefix.ROI):
    def enable_tools_by_spatial_type(self, tp=None):
        """
        a function that enables or disables tools on teh toolbar depending on the spatial type

        enable_tools_by_spatial_type(): description

        :param tp: types.spatial_type_prefix. type flag
        :type tp: types.spatial_type_prefix.ROI or types.spatial_type_prefix.SEG, or types.spatial_type_prefix.PNT

        :returns: None
        """
        """  """
        en_list = []
        dis_list = []
        if tp == None:
            # disable all
            en_list = []
            dis_list = PNT_tools + SEG_tools + ROI_tools

        elif tp == types.spatial_type_prefix.PNT:
            # enable PNT tools and disable SEG, ROI
            en_list = PNT_tools
            dis_list = SEG_tools + ROI_tools
        elif tp == types.spatial_type_prefix.SEG:
            # enable SEG tools and disable PNT, ROI
            en_list = SEG_tools
            dis_list = PNT_tools + ROI_tools
        elif tp == types.spatial_type_prefix.ROI:
            # enable ROI tools and disable PNT, SEG
            # but if we are in single spatial mode then only enable ROI if there are no current ROI's
            if self.multi_region_enabled:
                en_list = ROI_tools
            else:
                current_shape_items = self.plot.get_items(item_type=IShapeItemType)
                if len(current_shape_items) == 0:
                    en_list = ROI_tools
                # else leave en_list blank
            dis_list = PNT_tools + SEG_tools

        for t_str in en_list:
            self.enable_tool(t_str, True)

        for t_str in dis_list:
            self.enable_tool(t_str, False)

    def enable_tools_by_shape_type(self, shape_type=None, val=True):
        """
        a function that enables or disables tools on teh toolbar depending on the shape type

        enable_tools_by_shape_type(): description

        :param tp: shape. type flag
        :type tp: shape, guiqwt shapeItem

        :returns: None
        """
        """  """
        en_list = []
        dis_list = []
        if shape_type == None:
            # disable all
            en_list = []
            dis_list = PNT_tools + SEG_tools + ROI_tools

        elif shape_type == AnnotatedPoint:
            # enable PNT tools and disable SEG, ROI
            en_list = PNT_tools
            dis_list = SEG_tools + ROI_tools
        elif (shape_type == AnnotatedSegment) or (
            shape_type == AnnotatedHorizontalSegment
        ):
            # enable SEG tools and disable PNT, ROI
            en_list = SEG_tools
            dis_list = PNT_tools + ROI_tools
        elif shape_type == AnnotatedRectangle:
            # enable ROI tools and disable PNT, SEG
            en_list = ROI_tools
            dis_list = PNT_tools + SEG_tools

        if not val:
            # then add the normally enabled list to the dislist and empty the
            # en list
            dis_list = en_list
            en_list = []

        for t_str in en_list:
            self.enable_tool(t_str, True)

        for t_str in dis_list:
            self.enable_tool(t_str, False)

    def enable_tools_by_shape_instance(self, shape_inst=None, val=True):
        """
        a function that enables or disables tools on teh toolbar depending on the shape type

        enable_tools_by_shape_type(): description

        :param shape_inst_type: an instance of a shape type
        :type shape_inst_type: shape, guiqwt shapeItem

        :returns: None
        """
        """  """
        en_list = []
        dis_list = []
        if shape_inst == None:
            # disable all
            en_list = []
            dis_list = PNT_tools + SEG_tools + ROI_tools

        elif isinstance(shape_inst, AnnotatedPoint):
            # enable PNT tools and disable SEG, ROI
            en_list = PNT_tools
            dis_list = SEG_tools + ROI_tools
        elif (isinstance(shape_inst, AnnotatedSegment)) or (
            isinstance(shape_inst, AnnotatedHorizontalSegment)
        ):
            # enable SEG tools and disable PNT, ROI
            en_list = SEG_tools
            dis_list = PNT_tools + ROI_tools
        elif isinstance(shape_inst, AnnotatedRectangle):
            # enable ROI tools and disable PNT, SEG
            en_list = ROI_tools
            dis_list = PNT_tools + SEG_tools

        if not val:
            # then add the normally enabled list to the dislist and empty the
            # en list
            dis_list = en_list
            en_list = []

        for t_str in en_list:
            self.enable_tool(t_str, True)

        for t_str in dis_list:
            self.enable_tool(t_str, False)

    def enable_tool_by_name(self, toolstr=None, val=True):
        """
        a function that enables or disables a tool on the toolbar

        enable_tool_by_name(): description

        :param toolstr: a valid tool name like 'SegmentTool'
        :type toolstr: a string

        :returns: None
        """
        """  """
        if toolstr == None:
            return

        self.enable_tool(toolstr, val)

    def toolclass_to_str(self, tool):
        s = str(tool)
        idx = s.find("object")
        s2 = s[0 : idx - 1]
        s3 = s2.split(".")
        for _s in s3:
            if _s.find("Tool") > -1:
                return _s
        return None

    def toolclasses_to_dct(self):
        dct = {}
        for tool in self.plot.manager.tools:
            tool_nm = self.toolclass_to_str(tool)
            dct[tool_nm] = tool

        return dct

    def clear_all_tools(self):

        tool_dct = self.toolclasses_to_dct()
        for REMTOOL in MAIN_TOOLS_STR:
            i = 0
            for tool in self.plot.manager.tools:
                tool_nm = self.toolclass_to_str(tool)
                if tool_nm == REMTOOL:
                    del self.plot.manager.tools[i]
                    break
                i += 1

    def enable_delete_images(self, val):
        assert type(val) == bool, "enable_delete_images: val != a boolean:"

        self.delete_images_enabled = val

    def enable_tool(self, toolstr, en=True):
        """
        enable_tool(): description

        :param toolstr: toolstr description
        :type toolstr: toolstr type

        :returns: None
        """
        # self.action.setEnabled(item != None)
        toolstrs = toolstr.split(".")
        for s in toolstrs:
            if s.find("Tool") > -1:
                toolstr = s

        dct = self.toolclasses_to_dct()
        if toolstr in list(dct.keys()):
            tool = dct[toolstr]
            tool.set_enabled(en)
        # the following line == extremely important
        # unless set to None one of the tools could be set as "the active item"
        # unless set to None one of the tools could be set as "the active item"
        # which will cause an exception if you just click anywhere in the main plot
        # by setting it to None then none of the code that tries to access a selected tool
        # will execute
        plot = self.get_plot()
        plot.manager.get_active_plot().set_active_item(None)

    #         tools = self.plot.manager.tools
    #         for tool in tools:
    #             tool_class_str = self.toolclass_to_str(tool)
    #             if(tool_class_str != None):
    #                 if(toolstr == tool_class_str):
    #                     tool.set_enabled(en)

    def enable_tool_by_tooltype(self, tooltype, en=True):
        """
        enable_tool_by_tooltype(): description

        :param tooltype: a valid guiqwt tool type
        :type tooltype: a valid tool type

        :returns: None
        """
        # self.action.setEnabled(item != None)
        tools = self.plot.manager.tools
        for tool in tools:
            if isinstance(tool, tooltype):
                tool.set_enabled(en)

    def on_new_direct_beam_pos(self, pos_tuple):
        # print 'on_new_direct_beam_pos: %.2f, %.2f' % (cx, cy)
        (cx, cy) = pos_tuple
        self.new_beam_position.emit(cx, cy)

    def on_new_selected_position(self, pos_tuple):
        # print 'on_new_direct_beam_pos: %.2f, %.2f' % (cx, cy)
        (cx, cy) = pos_tuple
        self.new_selected_position.emit(cx, cy)

    def set_grid_parameters(self, bkgrnd_color, min_color, maj_color):
        """
        set_grid_parameters(): description

        :param bkgrnd_color: bkgrnd_color description
        :type bkgrnd_color: bkgrnd_color type

        :param min_color: min_color description
        :type min_color: min_color type

        :param maj_color: maj_color description
        :type maj_color: maj_color type

        :returns: None
        """
        """
        .. todo::
        there are man other image params that could be set in teh future, for now only implemented min/max
        GridParam:
            Grid:
                Background color: #eeeeee
                maj:
                  : True
                  : True
                  LineStyleParam:
                    Style: Dotted line
                    Color: #121212
                    Width: 1
                min:
                  : False
                  : False
                  LineStyleParam:
                    Style: Dotted line
                    Color: #121212
                    Width: 1

        """
        aplot = self.plot
        gparam = GridParam()
        gparam.background = bkgrnd_color
        gparam.maj_line.color = maj_color
        gparam.min_line.color = min_color
        aplot.grid.set_item_parameters({"GridParam": gparam})

        # QMouseEvent  event(QEvent.MouseButtonPress, pos, 0, 0, 0);
        # QApplication.sendEvent(mainWindow, & event);

        aplot.ensurePolished()
        # QtWidgets.QApplication.sendPostedEvents(aplot, QtCore.QEvent.PolishRequest)
        # aplot.polish()
        aplot.invalidate()
        aplot.replot()
        aplot.update_all_axes_styles()
        aplot.update()

    def set_cs_grid_parameters(self, forgrnd_color, bkgrnd_color, min_color, maj_color):
        """
        set_cs_grid_parameters(): description

        :param forgrnd_color: forgrnd_color description
        :type forgrnd_color: forgrnd_color type

        :param bkgrnd_color: bkgrnd_color description
        :type bkgrnd_color: bkgrnd_color type

        :param min_color: min_color description
        :type min_color: min_color type

        :param maj_color: maj_color description
        :type maj_color: maj_color type

        :returns: None
        """
        """
        .. todo::
        there are many other image params that could be set in the future, for now only implemented min/max
        GridParam:
            Grid:
                Background color: #eeeeee
                maj:
                  : True
                  : True
                  LineStyleParam:
                    Style: Dotted line
                    Color: #121212
                    Width: 1
                min:
                  : False
                  : False
                  LineStyleParam:
                    Style: Dotted line
                    Color: #121212
                    Width: 1

        """
        plot = self.plot
        xcs = self.get_xcs_panel()
        ycs = self.get_ycs_panel()
        xcs.cs_plot.label.hide()
        ycs.cs_plot.label.hide()

        # self.curve_item.update_params()
        cs_items = xcs.cs_plot.get_items()
        # csi = xcs.cs_plot.get_items(item_type=XCrossSectionItem)
        if len(cs_items) == 3:
            csi = cs_items[2]
            cparam = csi.curveparam
            # cparam = CurveParam()
            cparam.line._color = forgrnd_color
            cparam._shade = 0.75
            xcs.cs_plot.set_item_parameters({"CurveParam": cparam})

        # csi = xcs.cs_plot.get_items(item_type=ICurveItemType)
        # print csi

        # csi.curveparam._shade = 0.75

        # cparam = CurveParam()
        # cparam.line._color = forgrnd_color
        # cparam._shade = 0.75

        # xcs.cs_plot.set_item_parameters({"CurveParam":cparam})
        # ycs.cs_plot.set_item_parameters({"CurveParam":cparam})

        gparam = GridParam()
        gparam.background = bkgrnd_color
        gparam.maj_line.color = maj_color
        gparam.min_line.color = min_color
        xcs.cs_plot.grid.set_item_parameters({"GridParam": gparam})
        ycs.cs_plot.grid.set_item_parameters({"GridParam": gparam})

        xcs.cs_plot.ensurePolished()
        ycs.cs_plot.ensurePolished()

        # xcs.cs_plot.polish()
        # ycs.cs_plot.polish()

        xcs.cs_plot.invalidate()
        ycs.cs_plot.invalidate()

        xcs.cs_plot.replot()
        ycs.cs_plot.replot()

        xcs.cs_plot.update_all_axes_styles()
        ycs.cs_plot.update_all_axes_styles()

        xcs.cs_plot.update()
        ycs.cs_plot.update()

    def get_data_dir(self):
        """
        get_data_dir(): description

        :returns: None
        """
        """
        set a durectory to use when calling openfile()
        """
        return self._data_dir

    def set_data_dir(self, ddir):
        """
        set_data_dir(): description

        :param ddir: ddir description
        :type ddir: ddir type

        :returns: None
        """
        """
        set a durectory to use when calling openfile()
        """
        self._data_dir = ddir
        self.opentool.set_directory(self._data_dir)

    def on_set_aspect_ratio(self, force: bool, img_idx: Optional[int] = None):
        """
        on_set_aspect_ratio(): description

        :param force: force description
        :type force: force type

        :returns: None
        """
        items = self.get_all_image_items()
        ratio = 1.

        if any(items):
            if force:
                ymin, ymax, xmin, xmax = np.inf, -np.inf, np.inf, -np.inf
                for item in items:
                    if hasattr(item, "param") and hasattr(item, "ymax"):
                        # prefer the physical data shape if available
                        if item.param.ymin < ymin:
                            ymin = item.param.ymin
                        if item.param.ymax > ymax:
                            ymax = item.param.ymax
                        if item.param.xmin < xmin:
                            xmin = item.param.xmin
                        if item.param.xmax > xmax:
                            xmax = item.param.xmax
                    elif hasattr(item, "data") and hasattr(item.data, "shape"):
                        # ... or default to the array shape
                        y_size, x_size = item.data.shape
                        if 0 < ymin:
                            ymin = 0
                        if y_size > ymax:
                            ymax = y_size
                        if 0 < xmin:
                            xmin = 0
                        if x_size > xmax:
                            xmax = x_size

                if not np.any(np.isinf([ymin, ymax, xmin, xmax])):
                    height = ymax - ymin
                    width = xmax - xmin
                    ratio = width / height

            self.plot.set_aspect_ratio(ratio=ratio)
            self.plot.replot()
            self.set_autoscale()

        # this method may be called by methods outside of the registered toggle widget,
        # ensure that it's checked state is consistent
        tool = self.plot.manager.get_tool(clsSquareAspectRatioTool)
        if tool.ischecked != force:
            tool.ischecked = force
            tool.update_status(self.plot)

    def setColorMap(self, cmap_name):
        """
        setColorMap(): description

        :param cmap_name: cmap_name description
        :type cmap_name: cmap_name type

        :returns: None
        """
        self.color_map_str = cmap_name
        itemList = self.plot.get_items(item_type=ICSImageItemType)
        item = itemList[0]
        item.imageparam.colormap = cmap_name
        item.imageparam.update_image(item)
        # self.action.setText(cmap_name)
        self.plot.invalidate()
        # self.update_status(plot)

    def _toggleVisibility(self, item, on):
        """
        _toggleVisibility(): description

        :param item: item description
        :type item: item type

        :param on: on description
        :type on: on type

        :returns: None
        """
        item.setVisible(on)
        widget = self.plot.legend().find(item)
        if isinstance(widget, Qwt.QwtLegendItem):
            widget.setChecked(on)

        if on:
            # self.plot.set_active_item(self.items)
            self.plot.set_active_item(item)

        self.plot.replot()

    def _setup_rect_shape(self, shape):
        """
        _setup_rect_shape(): description

        :param shape: shape description
        :type shape: shape type

        :returns: None
        """
        # print 'in _setup_rect_shape'
        cur_shapes = self.getShapeItemsByShapeType(AnnotatedRectangle)
        if (not self.multi_region_enabled) and (len(cur_shapes) > 0):
            self.enable_tool_by_name("clsAverageCrossSectionTool", False)
        else:
            self.enable_tool_by_name("clsAverageCrossSectionTool", True)

    def setCheckRegionEnabled(self, val):
        """
        setCheckRegionEnabled(): description

        :param val: val description
        :type val: val type

        :returns: None
        """
        self.checkRegionEnabled = val

    def _setupsegment(self, seg):
        """
        _setupsegment(): description

        :param seg: seg description
        :type seg: seg type

        :returns: None
        """
        seg.setTitle("%s %d" % (types.spatial_type_prefix.SEG, self.segNum))

    def _drawSegment(self, rect):
        """
        _drawSegment(): description

        :param rect: rect description
        :type rect: rect type

        :returns: None
        """
        # print 'stxmImageWidget: _drawSegment'
        pass

    def _resizeItem(self, item, center, size, angle):
        """
        _resizeItem(): description

        :param item: item description
        :type item: item type

        :param center: center description
        :type center: center type

        :param size: size description
        :type size: size type

        :param angle: angle description
        :type angle: angle type

        :returns: None
        """
        A, B, C, E, F, G, I, D, H = calcRectPoints(center, (size[0], size[1]), angle)
        item.set_rect(E.x(), E.y(), I.x(), I.y())
        annotation = True
        if annotation:
            item.shape.set_xdiameter(D.x(), D.y(), H.x(), H.y())
            item.shape.set_ydiameter(F.x(), F.y(), B.x(), B.y())
            dct = item.get_infos()
            self.new_ellipse.emit(dct)
            # print dct
        else:
            item.set_xdiameter(D.x(), D.y(), H.x(), H.y())
            item.set_ydiameter(F.x(), F.y(), B.x(), B.y())

        # set cross_marker to visible and place it at center
        self.plot.cross_marker.set_display_label(False)
        self.plot.cross_marker.setZ(self.plot.get_max_z() + 1)
        self.plot.cross_marker.setVisible(True)
        # r = QRectF(10,50,100,100)
        #        r = QRectF(E.x(),E.y(),I.x(),I.y())
        #        x,y = self.plot.cross_marker.axes_to_canvas(r.topLeft().x(), r.topLeft().y())
        #        tl = QPointF(x,y)
        #        x,y = self.plot.cross_marker.axes_to_canvas(r.bottomRight().x(), r.bottomRight().y())
        #        br = QPointF(x,y)
        #        self.plot.do_zoom_rect_view(tl, br)

        # x,y = self.plot.cross_marker.axes_to_canvas(r.center().x(), r.center().y())
        x, y = self.plot.cross_marker.axes_to_canvas(A.x(), A.y())
        c = QPointF(x, y)
        self.plot.cross_marker.move_local_point_to(0, c)
        self.plot.cross_marker.setVisible(False)
        self.plot.cross_marker.emit_changed()
        del c

    def create_target_circle(self, xc, yc, val):
        """
        create_target_circle(): description

        :param xc: xc description
        :type xc: xc type

        :param yc: yc description
        :type yc: yc type

        :param val: val description
        :type val: val type

        :returns: None
        """
        from plotpy.styles import ShapeParam

        # circ = make.annotated_circle(x0, y0, x1, y1, ratio, title, subtitle)
        rad = val / 2.0
        circ = make.annotated_circle(
            xc - rad, yc + rad, xc + rad, yc - rad, 1, "Target"
        )
        sh = circ.shape.shapeparam
        # circ.set_resizable(False)
        # offset teh annotation so that it != on the center
        circ.shape.shapeparam.fill = circ.shape.shapeparam.sel_fill
        circ.shape.shapeparam.line = circ.shape.shapeparam.sel_line
        circ.label.C = (50, 50)
        circ.set_label_visible(False)
        # print circ.curve_item.curveparam
        # circ.set_style(, option)
        circ.shape.set_item_parameters({"ShapeParam": circ.shape.shapeparam})
        self.plot.add_item(circ, z=999999999)

    def create_osa(self, do_it=True):
        """
        create_osa(): description

        :returns: None
        """
        if do_it:
            # rad = 1000
            # xc = -1230
            # xc = 0.0
            # yc = 0.0
            # rect = (-1250, 500, 1250, -5500)

            xc, yc = self.ss.get("OSA_AMBIENT.CENTER")
            rect = self.ss.get("OSA_AMBIENT.RECT")

            create_rectangle(rect, title="osa_rect", plot=self.plot)

            create_simple_circle(
                rect[0] + 500, rect[1] - 500, 20, title="osa_1", plot=self.plot
            )
            create_simple_circle(
                rect[0] + 1000, rect[1] - 500, 25, title="osa_2", plot=self.plot
            )
            create_simple_circle(
                rect[0] + 1500, rect[1] - 500, 30, title="osa_3", plot=self.plot
            )
            create_simple_circle(
                rect[0] + 2000, rect[1] - 500, 35, title="osa_4", plot=self.plot
            )

        else:
            # remove the sample_holder
            self.blockSignals(True)
            shapes = self.plot.get_items(item_type=IShapeItemType)
            for shape in shapes:
                if hasattr(shape, "shapeparam"):
                    s = shape.shapeparam
                    title = s._title
                    if title.find("osa_") > -1:
                        self.delPlotItem(shape)
            self.blockSignals(False)
        self.plot.replot()

    def create_beam_spot(self, xc, yc, size=0.5):
        """
        a function to create a beam spot shape that will show the current position of the beam on the plot
        :param rect:
        :return:
        """
        diam = size / 2.0
        if self.show_beam_spot:
            bsp = tools.BeamSpotShape(x1=xc, y1=yc, shapeparam=None)
            self.plot.add_item(bsp, z=999999999)
            # self.create_simple_circle(xc, yc, diam, title='beam_spot', clr='yellow', fill_alpha=0.8)

    def move_beam_spot(self, xc, yc):
        if self.show_beam_spot:
            beam_spot_shape = self.get_shape_with_this_title("beam_spot")
            if beam_spot_shape == None:
                self.create_beam_spot(xc, yc)
                self.prev_beam_pos = (xc, yc)
            else:
                # print 'move_beam_spot: (%.2f, %.2f)' % (xc, yc)
                beam_spot_shape.move_shape(self.prev_beam_pos, (xc, yc))
                self.prev_beam_pos = beam_spot_shape.get_center()

        self.plot.replot()

    def create_uhv_osa(self, do_it=True):
        """
        create_osa(): description

        :returns: None
        """
        if do_it:
            xc, yc = self.ss.get("OSA_CRYO.CENTER")
            rect = self.ss.get("OSA_CRYO.RECT")
            x2 = rect[2]
            y1 = rect[1]
            create_rectangle(rect, title="osa_rect", plot=self.plot)
            # from outboard to inboard
            create_simple_circle(x2 - 250, y1 - 250, 35, title="osa_1", plot=self.plot)
            create_simple_circle(x2 - 250, y1 - 2250, 35, title="osa_2", plot=self.plot)

        else:
            # remove the sample_holder

            self.blockSignals(True)
            shapes = self.plot.get_items(item_type=IShapeItemType)

            for shape in shapes:
                title = ""
                if hasattr(shape, "annotationparam"):
                    title = shape.annotationparam._title
                elif hasattr(shape, "shapeparam"):
                    title = shape.shapeparam._title

                if title.find("osa_") > -1:
                    self.delPlotItem(shape)

            self.blockSignals(False)
        self.plot.replot()

    def create_stdrd_sample_holder(self, do_it=True):
        """
        create_sample_holder(): description

        :returns: None
        """
        HOLE_DIAMETER = 2500
        if do_it:
            rad = self.ss.get("%s.RADIUS" % SAMPLE_STANDARD)
            rect = self.ss.get("%s.RECT" % SAMPLE_STANDARD)
            xc = (rect[0] + rect[2]) * 0.5
            yc = (rect[1] + rect[3] - 5000) * 0.5

            create_rectangle(rect, title="sh_rect")

            create_simple_circle(xc - 5000, yc, rad, title="sh_1", plot=self.plot)
            create_simple_circle(xc, yc, rad, title="sh_2", plot=self.plot)
            create_simple_circle(xc + 5000, yc, rad, title="sh_3", plot=self.plot)

            create_simple_circle(
                xc - 5000, yc + 5000, rad, title="sh_4", plot=self.plot
            )
            create_simple_circle(xc, yc + 5000, rad, title="sh_5", plot=self.plot)
            create_simple_circle(
                xc + 5000, yc + 5000, rad, title="sh_6", plot=self.plot
            )
        else:
            # remove the sample_holder
            self.blockSignals(True)
            shapes = self.plot.get_items(item_type=IShapeItemType)
            for shape in shapes:
                title = ""
                if hasattr(shape, "annotationparam"):
                    title = shape.annotationparam._title
                elif hasattr(shape, "shapeparam"):
                    title = shape.shapeparam._title
                # s = shape.shapeparam
                # title = s._title
                if title.find("sh_") > -1:
                    self.delPlotItem(shape)
            self.blockSignals(False)
        self.plot.replot()

    def create_goni_sample_holder(self, do_it=True):
        """
        create_sample_holder(): description

        :returns: None
        """
        if do_it:
            rad = self.ss.get("%s.RADIUS" % SAMPLE_GONI)
            rect = self.ss.get("%s.RECT" % SAMPLE_GONI)
            xc, yc = self.ss.get("%s.CENTER" % SAMPLE_GONI)
            # xc = (rect[0] + rect[2]) * 0.5
            # yc = (rect[1] + rect[3] - 5000) * 0.5
            frame = (0.0, 600.0, 3000.0, -600.0)
            frame_outbrd_edge = xc - ((frame[0] + frame[2]) / 2.0)

            hole = (-100, 400, 100, -400)

            # self.create_rectangle(new_rect, title='sh_rect')
            create_rect_centerd_at(frame, xc, yc, title="sh_rect", plot=self.plot)
            create_rect_centerd_at(
                hole, frame_outbrd_edge + 385.0, yc, title="sh_1", plot=self.plot
            )
            create_rect_centerd_at(
                hole, frame_outbrd_edge + 660.0, yc, title="sh_1", plot=self.plot
            )
            create_rect_centerd_at(
                hole, frame_outbrd_edge + 935.0, yc, title="sh_2", plot=self.plot
            )
            create_rect_centerd_at(
                hole, frame_outbrd_edge + 1210.0, yc, title="sh_3", plot=self.plot
            )
            create_rect_centerd_at(
                hole, frame_outbrd_edge + 1485.0, yc, title="sh_4", plot=self.plot
            )
            create_rect_centerd_at(
                hole, frame_outbrd_edge + 1760.0, yc, title="sh_5", plot=self.plot
            )
            create_rect_centerd_at(
                hole, frame_outbrd_edge + 2035.0, yc, title="sh_6", plot=self.plot
            )
            # self.create_rect_centerd_at(hole, frame_outbrd_edge + 1945.0, yc , title='sh_7')
            # self.create_rect_centerd_at(hole, frame_outbrd_edge + 100.0, yc , title='sh_8')

        else:
            #        else:
            # remove the sample_holder
            self.blockSignals(True)
            shapes = self.plot.get_items(item_type=IShapeItemType)
            for shape in shapes:
                title = ""
                if hasattr(shape, "annotationparam"):
                    title = shape.annotationparam._title
                elif hasattr(shape, "shapeparam"):
                    title = shape.shapeparam._title
                if title.find("sh_") > -1:
                    self.delPlotItem(shape)
            self.blockSignals(False)
        self.plot.replot()

    def show_pattern(self, xc=None, yc=None, pad_size=1.0, do_show=True):
        # passing self will allow the pattern to be added to the plotter
        if do_show:
            if (xc or yc) == None:
                (x, y) = self.plot.get_active_axes()
                xmin, xmax = self.plot.get_axis_limits(x)
                ymin, ymax = self.plot.get_axis_limits(y)
                # xc, yc = self.ss.get('PATTERN.CENTER')
                xc = (xmax + xmin) * 0.5
                yc = (ymax + ymin) * 0.5

            # need to get the current centers
            add_pattern_to_plot(self, xc, yc, pad_size)
            self.register_shape_info(
                shape_info_dct={
                    "shape_title": "pattern",
                    "on_selected": self.select_pattern,
                    "on_deselected": self.deselect_pattern,
                }
            )

            self.set_center_at_XY((xc, yc), (pad_size * 10, pad_size * 10))
        else:
            # remove the pattern
            self.blockSignals(True)
            shapes = self.plot.get_items(item_type=IShapeItemType)
            for shape in shapes:
                title = ""
                if hasattr(shape, "annotationparam"):
                    title = shape.annotationparam._title
                elif hasattr(shape, "shapeparam"):
                    title = shape.shapeparam._title
                if title.find("pattern") > -1:
                    self.delPlotItem(shape)
            self.blockSignals(False)

    def select_pattern(self):
        """
        select the pattern shape
        :return:
        """
        selected_shapes = self.select_main_rect_of_shape("pattern")
        return selected_shapes

    def deselect_pattern(self):
        # self.deselect_main_rect_of_shape('pattern')
        pass

    def move_shape_to_new_center(self, title, xc, yc):
        """
        select the shapes with name 'title' and move them based on a new center
        :param title:
        :param xc:
        :param yc:
        :return:
        """
        selected_shapes = self.select_main_rect_of_shape(title)
        for shape in selected_shapes:
            # shape.add_point((3,3))
            old_cntr = shape.get_center()
            new_center = (xc + old_cntr[0], yc + old_cntr[1])
            shape.move_shape(old_cntr, new_center)

    def addPlotItem(self, item):
        """
        addPlotItem(): description

        :param item: item description
        :type item: item type

        :returns: None
        """
        plot = self.get_plot()
        plot.add_item(item)
        self.update()
        plot.replot()

    def addPlotItems(self, items):
        """
        addPlotItems(): description

        :param items: items description
        :type items: items type

        :returns: None
        """
        plot = self.get_plot()
        for item in items:
            plot.add_item(item)
        self.update()
        plot.replot()

    def _handle_final_segment_shape(self, seg):
        """
        _handle_final_segment_shape(): This == used only by the measure tool

        :param seg: seg description
        :type seg: seg type

        :returns: None
        """
        # seg.setTitle("%s %d" % (types.spatial_type_prefix.SEG, self.segNum))
        #         seg.setItemAttribute(Qwt.QwtPlotItem.Legend)
        #         widget = self.plot.legend().find(seg)
        #         if isinstance(widget, Qwt.QwtLegendItem):
        #             widget.setChecked(True)

        ret = self._anno_seg_to_region(seg)
        # self.new_region.emit(ret)
        self._select_this_item(seg)
        self.update()

    def _handle_final_horiz_segment_shape(self, seg):
        """
        _handle_final_horiz_segment_shape(): this == used by all segment roi selection tools

        :param seg: seg description
        :type seg: seg type

        :returns: None
        """
        ret = self._seg_to_region(seg)
        # print '_handle_final_horiz_segment_shape: emitting new region' , ret
        self.new_region.emit(ret)
        # self._select_this_item(seg)
        self.update()

        # check for either horiz or other segments
        cur_shapes = self.getShapeItemsByShapeType(AnnotatedHorizontalSegment)
        if len(cur_shapes) > 0:
            if not self.multi_region_enabled:
                self.enable_tools_by_shape_type(AnnotatedHorizontalSegment, False)
            else:
                self.enable_tools_by_shape_type(AnnotatedHorizontalSegment, True)
        else:
            cur_shapes = self.getShapeItemsByShapeType(AnnotatedSegment)
            if (not self.multi_region_enabled) and (len(cur_shapes) > 0):
                self.enable_tools_by_shape_type(AnnotatedSegment, False)
            else:
                self.enable_tools_by_shape_type(AnnotatedSegment, True)

    def setuppoint(self, point):
        """
        setuppoint(): description

        :param point: point description
        :type point: point type

        :returns: None
        """
        # print 'in setuppoint'
        pass
        # point.setTitle("%s %d" % (types.spatial_type_prefix.PNT, self.shapeNum))

    def shape_end_rect(self, shape):
        """
        shape_end_rect(): description

        :param shape: shape description
        :type shape: shape type

        :returns: None
        """
        # print shape
        pass

    def _handle_final_point_shape(self, point):
        """
        _handle_final_point_shape(): description

        :param point: point description
        :type point: point type

        :returns: None
        """
        # point.setItemAttribute(Qwt.QwtPlotItem.Legend)
        # widget = self.plot.legend().find(point)
        # if isinstance(widget, Qwt.QwtLegendItem):
        #    widget.setChecked(True)

        ret = self._anno_point_to_region(point)
        self.new_region.emit(ret)
        self._select_this_item(point)
        self.update()

        cur_shapes = self.getShapeItemsByShapeType(AnnotatedPoint)
        if (not self.multi_region_enabled) and (len(cur_shapes) > 0):
            self.enable_tools_by_shape_type(AnnotatedPoint, False)
        else:
            self.enable_tools_by_shape_type(AnnotatedPoint, True)

    def get_shape_with_this_title(self, _title):
        shapes = self.plot.get_items(item_type=IShapeItemType)
        for shape in shapes:
            title = ""
            if hasattr(shape, "annotationparam"):
                title = shape.annotationparam._title
            elif hasattr(shape, "shapeparam"):
                title = shape.shapeparam._title
            if title == _title:
                return shape
        return None

    def select_all_shapes_with_this_title(self, _title):
        shapes = self.plot.get_items(item_type=IShapeItemType)
        for shape in shapes:
            title = ""
            if hasattr(shape, "annotationparam"):
                title = shape.annotationparam._title
            elif hasattr(shape, "shapeparam"):
                title = shape.shapeparam._title
            if title.find(_title) > -1:
                shape.select()

    def select_sample_holder(self):
        self.select_main_rect_of_shape("sh_")

    def select_osa(self):
        self.select_main_rect_of_shape("osa_")

    def select_main_rect_of_shape(self, _title="sh_"):
        # print('select_main_rect_of_shape: looking for shapes with the name [%s] in it' % _title)
        num_found = 0
        shapes = self.plot.get_items(item_type=IShapeItemType)
        selected_shapes = []

        for shape in shapes:
            _rect = shape.get_rect()
            # QtCore.QRectF( top left, btm right)
            qrect = QtCore.QRectF(
                QtCore.QPointF(_rect[0], _rect[2]), QtCore.QPointF(_rect[3], _rect[1])
            )

            title = ""
            if hasattr(shape, "annotationparam"):
                title = shape.annotationparam._title
            elif hasattr(shape, "shapeparam"):
                title = shape.shapeparam._title
            # print('select_main_rect_of_shape: checking [%s]' % title)
            if hasattr(shape, "selection_name"):
                sel_name = shape.selection_name
                if sel_name.find(_title[0:5]) > -1:
                    # shape.select()
                    selected_shapes.append(shape)
                    # print('select_main_rect_of_shape: found selection_name [%d]' % num_found)
                    num_found += 1
            elif title.find(_title[0:5]) > -1:
                # shape.select()
                # print('select_main_rect_of_shape: found name [%d]' % num_found)
                selected_shapes.append(shape)
                num_found += 1
                # if (title.find('%srect' % _title) > -1):
                #     #main_rect = shape
                #     shape.select()
                #     #we will selct this one as the last one before we leave
                # else:
                #     #still want to select all in the shape
                #     shape.select()
                #     #_toselect.append(shape)
            # if(main_rect == None):
            #     main_rect = qrect
            # else:
            #     main_rect = main_rect.united(qrect)
            else:
                print(
                    "select_main_rect_of_shape: the shape title [%s] didnt match [%s]"
                    % (title, _title)
                )
        if len(selected_shapes) > 0:
            selected_shapes.reverse()
            for sh in selected_shapes:
                # print('selecting [%s]' % sh.selection_name)
                sh.select()
        # self.target_moved.emit(main_rect)
        return selected_shapes

    def selected_item_changed(self, plot):
        """
        selected_item_changed():
        Note for de-selections: this function == called AFTER the guiplot has deselected all
        of the shapes and items

        :param plot: plot description
        :type plot: plot type

        :returns: None
        """
        is_regd_shape = False
        shape = None
        item = plot.get_active_item()
        # print('selected_item_changed:', item)
        if isinstance(item, AnnotatedRectangle):
            _logger.debug(
                "ok here == an Annotated Rect, does it have a selection name?: %s"
                % (str(hasattr(item, "selection_name")))
            )

        if hasattr(item, "unique_id"):
            self._cur_shape_uid = item.unique_id

        if item:
            if hasattr(item, "shapeparam"):
                shape = item.shapeparam
                if hasattr(shape, "_title"):
                    title = shape._title
                elif hasattr(shape, "label"):
                    title = shape.label.title()
                else:
                    #title = shape.title().text()
                    pass

            else:
                title = item.title().text()

            if hasattr(item, "shape"):
                shape = item.shape

            if title.find("sh_") > -1:
                # select all sample holder items
                self.select_sample_holder()

            if title.find("osa_") > -1:
                # select all sample holder items
                self.select_osa()

            if hasattr(item, "selection_name"):
                sel_name = item.selection_name
                _logger.debug("sel_name == [%s]" % sel_name)
                sel_prefix = sel_name.split("_")[0]
                regd_shape = self.get_shape_from_registry(sel_prefix)
                if regd_shape:
                    # only look at first 5 chars
                    if sel_prefix.find(regd_shape["shape_title"][0:5]) > -1:
                        # call teh regsitered handler
                        if regd_shape["on_selected"]:
                            regd_shape["on_selected"]()
                            is_regd_shape = True
                        else:
                            _logger.error(
                                "selected_item_changed: on_selected handler registered for [%s]"
                                % regd_shape["shape_title"]
                            )

            #
            # regd_shape = self.get_shape_from_registry(title)
            # if(regd_shape):
            #     #only look at first 5 chars
            #
            #     if (title.find(regd_shape['shape_title'][0:5]) > -1):
            #         #call teh regsitered handler
            #         if(regd_shape['on_selected']):
            #             regd_shape['on_selected']()
            #             is_regd_shape = True
            #         else:
            #             _logger.error('selected_item_changed: on_selected handler registered for [%s]' % regd_shape['shape_title'])

            if not is_regd_shape:
                pass
            else:
                #print("is_regd_shape == True")
                pass
            self.sel_item_id = title

            if hasattr(item, "unique_id"):
                set_current_unique_id(item.unique_id)
                self.inputState.plotitem_id = item.unique_id
                # print 'selected_item_changed: emitting new_roi with cmnd=SELECT_ROI'
                self._emit_new_roi(
                    self.image_type, cmnd=widget_com_cmnd_types.SELECT_ROI
                )

            if hasattr(item, "is_label_visible"):
                item.set_label_visible(True)
        else:
            # deselect all
            # print 'selected_item_changed: emitting new_roi with cmnd=DESELECT_ROI'
            self._emit_new_roi(self.image_type, cmnd=widget_com_cmnd_types.DESELECT_ROI)
            self.auto_scale_contrast_histogram()


    def on_sig_plot_axis_changed(self, plot):
        """
        on_sig_plot_axis_changed(): description

        :param plot: plot description
        :type plot: plot type

        :returns: None
        """
        """
        a sig handler that fires when the plot == panned and zoomed
        which will emit a noi_roi_center signal so that it can be used
        to update scan parameters
        """
        ilist = plot.get_items(item_type=IDecoratorItemType)
        grid = ilist[0]
        rngx = grid.xScaleDiv().range()

        (x1, x2) = self.plot.get_axis_limits("bottom")
        (y1, y2) = self.plot.get_axis_limits("left")

        cx = (x1 + x2) / 2
        rx = x2 - x1

        cy = (y1 + y2) / 2
        ry = y2 - y1

        self.inputState.center = (cx, cy)
        self.inputState.range = (rx, ry)
        self.inputState.rect = (x1, y1, x2, y2)

        # only emit a new_roi_center if the user has the F1 pressed
        # if(self.inputState.keyisPressed[Qt.Key_F1]):
        #    self._emit_new_roi(self.image_type)

    def items_changed(self, plot):
        """
        items_changed(): description

        :param plot: plot description
        :type plot: plot type

        :returns: None
        """
        # items = plot.get_items()
        # disable region select tool
        # ROITool needs to remain the active tool
        if type(self.plot.manager.active_tool) !=  ROITool:
            self.get_default_tool().activate()


    def Image_changed(self, items):
        """
        Image_changed(): description

        :param items: items description
        :type items: items type

        :returns: None
        """
        for i in items:
            # print 'Image_changed:'
            # print i.title().text()
            # print i.get_rect()
            pass

    def AnnotatedRectangle_changed(self, items):
        """
        AnnotatedRectangle_changed(): description

        :param items: items description
        :type items: items type

        :returns: None
        """
        pass
        # for i in items:
        # print 'AnnotatedRectangle_changed: '
        # print i.title().text()
        # print i.get_rect()

    def item_handle_moved(self, item):
        """
        a signal handler for the SIG_ITEM_HANDLE_MOVED signal,
        currently only supports a transformable image item, it
        emits a new_roi so the parent UI can record that the image has been
        resized
        """
        if type(item) == TrImageItem:
            if item.title().text() in self._trimage_max_sizes.keys():
                max_x, max_y = self._trimage_max_sizes[item.title().text()]
                if item.bounds.width() > max_x or item.bounds.height() > max_y:
                    #see if you can change color of image to indicate range violation
                    self.set_image_colormap(colormap="allred", item=item)
                    return
            # user moved an image they loaded so emit new center
            self.set_image_colormap(colormap="gist_gray", item=item)
            self.inputState.keyisPressed[Qt.Key_Alt] = True
            self.inputState.plotitem_title = "TrImageItem"
            self.inputState.plotitem_id = 0
            self.inputState.center = (item.bounds.center().x(), item.bounds.center().y())
            self.inputState.range = (item.bounds.width(), item.bounds.height())
            self.inputState.rect = item.boundingRect().getCoords()
            self._emit_new_roi(self.image_type)
            # print("center: " , (self.inputState.center))
            # print("range: " , (self.inputState.range))
            # print("rect: " , (self.inputState.rect))
            # print()
            return

    def active_item_moved(self, item):
        """
        active_item_moved(): description

        :param item: item description
        :type item: item type

        :returns: None
        """
        if type(item) == TrImageItem:
            #user moved an image they loaded so emit new center
            self.inputState.keyisPressed[Qt.Key_Alt] = True
            self.inputState.plotitem_title = "TrImageItem"
            self.inputState.plotitem_id = 0
            self.inputState.center = (item.bounds.center().x(), item.bounds.center().y())
            self.inputState.range = (item.bounds.width(), item.bounds.height())
            self.inputState.rect = item.boundingRect().getCoords()
            self._emit_new_roi(self.image_type)
            # print("center: " , (self.inputState.center))
            # print("range: " , (self.inputState.range))
            # print("rect: " , (self.inputState.rect))
            # print()
            return

        if hasattr(item, "annotationparam"):
            title = item.annotationparam.title
            if item.annotationparam.title == "Target":
                cntr = item.get_center()
                (self.zoom_scale, dud) = item.get_tr_size()
                self.zoom_scale = self.zoom_scale * 0.75
                self.target_moved.emit(cntr)
            else:
                if self.inputState.keyisPressed[Qt.Key_Alt]:
                    self._emit_new_roi(self.image_type)

        elif hasattr(item, "shapeparam"):
            shape = item.shapeparam
            if hasattr(shape, "_title"):
                title = shape._title
            elif hasattr(shape, "label"):
                title = shape.label.title()
            else:
                title = item.get_title()
        else:
            title = ""

        # print('active_item_moved', (title, item.get_center()))

        if title.find("osa_") > -1:
            shape = self.get_shape_with_this_title("osa_rect")
            if shape:
                self.ss.set("%s.CENTER" % self.osa_type, shape.get_center())
                self.ss.set("%s.RECT" % self.osa_type, shape.get_rect())
                self.ss.update()

        if title.find("sh_") > -1:
            shape = self.get_shape_with_this_title("sh_rect")
            if shape:
                self.ss.set("%s.CENTER" % self.sample_hldr_type, shape.get_center())
                self.ss.set("%s.RECT" % self.sample_hldr_type, shape.get_rect())
                self.ss.update()

        regd_shape = self.get_shape_from_registry(title)
        if regd_shape:
            # only look at first 5 chars
            if title.find(regd_shape["shape_title"][0:5]) > -1:
                cntr = item.get_center()
                self.ss.set("%s.CENTER" % regd_shape["shape_title"].upper(), cntr)
                # self.ss.set('%s.RECT' % regd_shape['shape_title'].upper(), shape.get_rect())
                self.ss.update()
                self._emit_new_roi(self.image_type)

        else:
            # print 'active_item_moved: event for this item not handled' , item
            pass

    def set_transform_factors(self, x, y, z, unit):
        """
        set_transform_factors(): description

        :param x: x description
        :type x: x type

        :param y: y description
        :type y: y type

        :param z: z description
        :type z: z type

        :param unit: unit description
        :type unit: unit type

        :returns: None
        """
        self.xTransform = x
        self.yTransform = y
        self.zTransform = z
        self.unitTransform = unit

    def reset_transform_factors(self):
        """
        reset_transform_factors(): description

        :returns: None
        """
        self.xTransform = 1.0
        self.yTransform = 1.0
        self.zTransform = 1.0
        self.unitTransform = "um"

    def _anno_point_to_region(self, item, set_id=True):
        """
        _anno_point_to_region(): description

        :param item: item description
        :type item: item type

        :param set_id=True: set_id=True description
        :type set_id=True: set_id=True type

        :returns: None
        """
        """ convert an annotated point item to a region dict"""
        (x1, y1) = item.get_pos()
        cntr = (x1, y1)
        sz = (1, 1)
        ret = {}
        ret["type"] = types.spatial_type_prefix.PNT  # types.spatial_type_prefix.PNT
        ret["name"] = str(item.title().text())
        ret["center"] = cntr
        ret["range"] = sz
        ret["rect"] = (x1, y1, x1, y1)
        return ret

    def _anno_seg_to_region(self, item, set_id=True):
        """
        _anno_seg_to_region(): description

        :param item: item description
        :type item: item type

        :param set_id=True: set_id=True description
        :type set_id=True: set_id=True type

        :returns: None
        """
        """ convert an annotated segment item to a region dict"""
        (x1, y1, x2, y2) = item.get_rect()
        cntr = ((x1 + x2) / 2.0, (y2 + y1) / 2.0)

        ret = {}
        ret["type"] = types.spatial_type_prefix.SEG  # types.spatial_type_prefix.SEG
        ret["name"] = str(item.title().text())
        ret["center"] = cntr
        ret["range"] = (abs(x2 - x1), abs(y2 - y1))
        ret["rect"] = (x1, y1, x2, y2)
        return ret

    def _anno_spatial_to_region(self, item, set_id=True):
        """
        _anno_spatial_to_region(): description

        :param item: item description
        :type item: item type

        :param set_id=True: set_id=True description
        :type set_id=True: set_id=True type

        :returns: None
        """
        """ convert an annotated rectangle item to a region dict"""
        cntr = item.get_tr_center()
        sz = item.get_tr_size()
        rect = item.get_rect()

        ret = {}
        ret["type"] = types.spatial_type_prefix.ROI  # SPATIAL_TYPE_PREFIX[TWO_D]
        ret["name"] = str(item.title().text())
        ret["center"] = cntr
        ret["range"] = sz
        ret["rect"] = rect
        return ret

    def _seg_to_region(self, item):
        """
        _seg_to_region(): description

        :param item: item description
        :type item: item type

        :returns: None
        """
        """ convert an annotated segment item to a region dict"""
        (x1, y1, x2, y2) = item.get_rect()
        cntr = ((x1 + x2) / 2.0, (y2 + y1) / 2.0)
        # sz = (item.get_tr_length(), item.get_tr_length())
        ret = {}
        ret["type"] = types.spatial_type_prefix.SEG  # types.spatial_type_prefix.SEG
        ret["name"] = "HSEG"  # str(item.title().text())
        ret["center"] = cntr
        ret["range"] = (x2 - x1, y2 - y1)
        ret["rect"] = (x1, x2, y1, y2)
        return ret

    def _region_name_to_item(self, region_name):
        """
        _region_name_to_item(): description

        :param region_name: region_name description
        :type region_name: region_name type

        :returns: None
        """
        """
        take a region name and return the plot item it corresponds to
        """
        items = self.plot.get_items(item_type=IShapeItemType)
        # items = self.plot.get_items()
        for item in items:
            name = str(item.title().text())
            if name == region_name:
                return item
        return None

    def select_region(self, region_name):
        """
        select_region(): description

        :param region_name: region_name description
        :type region_name: region_name type

        :returns: None
        """
        """
        used by callers to make a region selected, typically this is
        called by the gui which == managing the connection to the scan table
        so that a user can select a scan in the table and this function will make that selection
        active on the plot.
        Args:
            region_name: this == the name of the region which == also the text found in the item.title().text()

        """
        sel_item = self._region_name_to_item(region_name)
        items = self.plot.get_items(item_type=IShapeItemType)

        for item in items:
            if item != None:
                if item == sel_item:
                    # print 'select_region: %s' % region_name
                    # print 'item.text() = %s' %(str(item.title().text()))
                    #
                    item.set_label_visible(True)
                else:
                    item.set_label_visible(False)

        self.plot.replot()

    def _select_this_item(self, item, set_label_visible=True):
        """
        _select_this_item(): description

        :param item: item description
        :type item: item type

        :returns: None
        """
        """
        this function == used to deselect everything on the plot
        and make the current item selected as well as make the annotation visible,
        without this the point and segment shapes do not stay selected after they have been
        created, seems to fix a bug in guiqwt
        """
        plot = self.get_plot()
        plot.unselect_all()
        plot.select_item(item)
        plot.set_active_item(item)
        if set_label_visible:
            item.set_label_visible(True)

    def on_active_item_changed(self, item):
        """
        on_active_item_changed(): description

        :param item: item description
        :type item: item type

        :returns: None
        """
        self.auto_scale_contrast_histogram()

    def auto_scale_contrast_histogram(self):
        """
        when items are selected or deselected the contrast histogram should make sense and
        scale accordingly
        """
        cpnl = self.get_contrast_panel()
        if cpnl:
            for h_item in cpnl.histogram.get_items():
                if isinstance(h_item, HistogramItem):
                    h_item.plot().do_autoscale(True)

    def annotation_item_changed(self, item):
        """
        annotation_item_changed(): description

        :param item: item description
        :type item: item type

        :returns: None
        """
        """
        This function == called whwnever a annotated shapeItem == moved or resized.
        At the time == called though it may not yet have had its item_id assigned, if it hasn't then assign one (by setting set_id=True)
        """
        set_id = False
        if isinstance(item, AnnotatedPoint):
            rect = item.get_pos()
            qrect = QRectF(QPointF(rect[0], rect[1]), QPointF(1, 1))
            s = str(item.title().text()).split()
            ret = self._anno_point_to_region(item, set_id=set_id)
            self.inputState.center = ret["center"]
            self.inputState.range = ret["range"]
            self.inputState.rect = ret["rect"]
            self.inputState.npts = (None, None)

            if hasattr(item, "unique_id"):
                # if(item.unique_id != get_current_unique_id()):
                #     print('why dont these ids match? %d %d' % (item.unique_id, get_current_unique_id()))
                item.unique_id = get_current_unique_id()
                self.inputState.plotitem_id = item.unique_id
                # print 'annotation_item_changed: item unique_id = %d' % self.inputState.plotitem_id
            else:
                print("item has NO unique_id attr why??????")

            self.inputState.plotitem_title = str(item.title().text())
            self.inputState.plotitem_type = types.spatial_type_prefix.PNT
            self.inputState.plotitem_shape = item
            # print '<drag> %s id(item)=%d, unique=%d' %
            # (self.inputState.plotitem_title, id(item), item.unique_id)
            if hasattr(item, "unique_id"):
                if item.unique_id != -1:
                    # print 'AnnotatedPoint: annotation_item_changed: emitting new_roi '
                    self._emit_new_roi(self.image_type)

        elif isinstance(item, tools.clsMeasureTool):
            pass

        elif isinstance(item, AnnotatedHorizontalSegment):
            # if(self.checkRegionEnabled):
            #    qrect = self._check_valid_region(item)
            l = item.label
            lp = l.labelparam
            lp.yc = 50
            l.set_item_parameters({"LabelParam": lp})

            if item.annotationparam.title == "":
                (title, tfm, format) = self._get_seg_anno_params()
                item.annotationparam.title = title
            s = str(item.title().text()).split()
            ret = self._anno_seg_to_region(item, set_id=set_id)
            self.inputState.center = ret["center"]
            self.inputState.range = ret["range"]
            self.inputState.rect = ret["rect"]
            self.inputState.npts = (None, None)
            # extract the plotitem_id of this AnnotatedHorizontalSegment

            if hasattr(item, "unique_id"):
                item.unique_id = get_current_unique_id()
                self.inputState.plotitem_id = item.unique_id

            self.inputState.plotitem_title = str(item.title().text())
            self.inputState.plotitem_type = types.spatial_type_prefix.SEG

            if self.checkRegionEnabled:
                qrect = self._check_valid_region(item)
                self.inputState.rect = qrect.getCoords()
            else:
                self.inputState.rect = item.get_rect()

            self.inputState.plotitem_shape = item

            if hasattr(item, "unique_id"):
                if item.unique_id != -1:
                    # print 'AnnotatedHorizontalSegment: annotation_item_changed: emitting new_roi'
                    self._emit_new_roi(self.image_type)

        elif isinstance(item, AnnotatedSegment):
            # if(self.checkRegionEnabled):
            #    qrect = self._check_valid_region(item)
            l = item.label
            lp = l.labelparam
            lp.yc = 50
            l.set_item_parameters({"LabelParam": lp})
            if item.annotationparam.title == "":
                (title, tfm, format) = self._get_seg_anno_params()
                item.annotationparam.title = title
            s = str(item.title().text()).split()

            ret = self._anno_seg_to_region(item, set_id=set_id)
            self.inputState.center = ret["center"]
            self.inputState.range = ret["range"]
            # self.inputState.rect = ret['rect']
            self.inputState.npts = (None, None)
            if hasattr(item, "unique_id"):
                if item.unique_id != -1:
                    item.unique_id = get_current_unique_id()
                self.inputState.plotitem_id = item.unique_id

            self.inputState.plotitem_title = str(item.title().text())
            self.inputState.plotitem_type = types.spatial_type_prefix.SEG
            self.inputState.rect = item.get_rect()
            self.inputState.plotitem_shape = item

            # dont boundary check teh measureing tool
            if item.get_text().find("Measure") == -1:
                if self.checkRegionEnabled:
                    qrect = self._check_valid_region(item)
                    self.inputState.rect = qrect.getCoords()

            if hasattr(item, "unique_id"):
                if item.unique_id != -1:
                    # print 'AnnotatedSegment: annotation_item_changed: emitting new_roi'
                    self._emit_new_roi(self.image_type)

        elif isinstance(item, shape.RectangleShape):
            # print 'Im a RectangleShape'
            pass

        elif isinstance(item, AnnotatedRectangle):

            self.inputState.center = item.get_center()
            self.inputState.range = item.get_tr_size()
            s = str(item.title().text()).split()
            if hasattr(item, "unique_id"):
                if item.unique_id == None:
                    item.unique_id = get_current_unique_id()
                self.inputState.plotitem_id = item.unique_id
                # print 'annotation_item_changed: item.unique_id=%d' % item.unique_id
                # print 'annotation_item_changed: addr(item.unique_id)=%d' % id(item.unique_id)
                # had to add the following check because for some reason the tool will emit a CHANGE 2 times with the
                # previous unique_id
                if self._cur_shape_uid != item.unique_id:
                    # print 'THE UNIQUE_IDs DO NOT MATCH SKIPPING'
                    return
            self.inputState.plotitem_title = str(item.title().text())
            self.inputState.plotitem_type = types.spatial_type_prefix.ROI
            self.inputState.plotitem_shape = item
            # print 'annotation_item_changed: ', item.unique_id

            if self.checkRegionEnabled:
                qrect = self._check_valid_region(item)
                self.inputState.rect = qrect.getCoords()
            else:
                self.inputState.rect = item.get_rect()

            # print 'self.inputState.rect: ', self.inputState.rect
            if hasattr(item, "unique_id"):
                if item.unique_id != -1:
                    # print 'AnnotatedRectangle: annotation_item_changed: emitting new_roi'
                    self._emit_new_roi(self.image_type)

        elif isinstance(item, AnnotatedCircle):
            if hasattr(item, "unique_id"):
                if item.unique_id == None:
                    item.unique_id = get_current_unique_id()
                self.inputState.plotitem_id = item.unique_id
                self.inputState.plotitem_shape = item

            if self.checkRegionEnabled:
                qrect = self._check_valid_region(item)
            if hasattr(item, "get_tr_center"):
                ret = self._anno_spatial_to_region(item)
        elif isinstance(item, AnnotatedEllipse):
            self.inputState.plotitem_id = self.roiNum
            if self.checkRegionEnabled:
                qrect = self._check_valid_region(item)
            if hasattr(item, "get_tr_center"):
                ret = self._anno_spatial_to_region(item)
            self.inputState.plotitem_shape = item

        if self.xTransform > 0.0:
            item.annotationparam.transform_matrix = [
                [self.xTransform, 0.0, 0.0],
                [0.0, self.yTransform, 0.0],
                [0.0, 0.0, self.zTransform],
            ]
            item.annotationparam.format = "%5.2f " + self.unitTransform
        else:
            item.annotationparam.transform_matrix = [
                [self.xstep, 0.0, 0.0],
                [0.0, self.ystep, 0.0],
                [0.0, 0.0, 1.0],
            ]
            item.annotationparam.format = "%5.2f um"

        item.apply_transform_matrix(1, 1)
        item.set_label_visible(True)

    def set_shape_limits(self, shape=types.spatial_type_prefix.ROI, limit_def=None):
        if limit_def:

            self.enable_tools_by_spatial_type(tp=shape)

            if shape == types.spatial_type_prefix.ROI:
                self.roi_limit_def = limit_def
            elif shape == types.spatial_type_prefix.SEG:
                self.seg_limit_def = limit_def
            elif shape == types.spatial_type_prefix.PNT:
                self.pnt_limit_def = limit_def
        else:
            # disable all roi selection tools
            self.enable_tools_by_spatial_type(None)

    def _restrict_rect_to_positive(self, rect):
        """
        _restrict_rect_to_positive(): description

        :param r: r description
        :type r: r type

        :returns: None
        """
        swap = False
        (x1, y1, x2, y2) = rect
        # if they are negative restrict them so they aren't
        if x2 < x1:
            swap = True
        # if(y2 > y1):
        #    swap = True

        if swap:
            qrect = QRectF(QPointF(x2, y2), QPointF(x1, y1))
        else:
            qrect = QRectF(QPointF(x1, y1), QPointF(x2, y2))

        return qrect

    def _check_valid_region(self, item):
        """
        _check_valid_region(): description

        :param item: item description
        :type item: item type

        :returns: None
        """
        # print '_check_valid_region'
        if self.checkRegionEnabled:

            if isinstance(item, AnnotatedPoint):
                self.inputState.shape_outof_range = False

            elif isinstance(item, AnnotatedSegment) or isinstance(
                item, AnnotatedHorizontalSegment
            ):
                # print 'in AnnotatedSegment'
                rect = item.get_rect()
                sh = item.shape.shapeparam
                qrect = self._restrict_rect_to_positive(rect)
                if self.seg_limit_def:
                    qrect = self.seg_limit_def.check_limits(qrect)
                    # item.setTitle(self.seg_limit_def.get_label())
                    if hasattr(item, "unique_id"):
                        item.setTitle(
                            self.seg_limit_def.get_label() + ": %d" % item.unique_id
                        )

                    if self.seg_limit_def.state == ROI_STATE_ALARM:
                        self.inputState.shape_outof_range = True
                    else:
                        self.inputState.shape_outof_range = False
                else:
                    self.inputState.shape_outof_range = False

                if self.inputState.shape_outof_range:
                    # print 'SEG: setting color red: #ff0000 alpha == ff'
                    lineWidth = 5
                    lineStyle = Qt.DashLine
                    lineColor = get_alarm_clr(255)
                else:
                    # print 'SEG: setting color green #00ff00 alpha == ff'
                    lineWidth = 1
                    lineStyle = Qt.SolidLine
                    lineColor = get_normal_clr(255)

                item.shape.sel_pen.setStyle(lineStyle)
                item.shape.sel_pen.setWidth(lineWidth)
                item.shape.sel_pen.setColor(lineColor)
                item.shape.pen.setStyle(lineStyle)
                item.shape.pen.setWidth(lineWidth)
                item.shape.pen.setColor(lineColor)

                # item.shape.sel_brush.setStyle(self.roi_limit_def.get_fill_pattern())
                # item.shape.sel_brush.setColor(self.roi_limit_def.get_color())

                sh.update_param(item.shape)
                return qrect

            elif isinstance(item, AnnotatedRectangle) or isinstance(item, shape.RectangleShape
            ):
                #                 BRUSHSTYLE_CHOICES = [
                #                     ("NoBrush", _("No brush pattern"), "nobrush.png"),
                #                     ("SolidPattern", _("Uniform color"), "solidpattern.png"),
                #                     ("Dense1Pattern", _("Extremely dense brush pattern"), "dense1pattern.png"),
                #                     ("Dense2Pattern", _("Very dense brush pattern"), "dense2pattern.png"),
                #                     ("Dense3Pattern", _("Somewhat dense brush pattern"), "dense3pattern.png"),
                #                     ("Dense4Pattern", _("Half dense brush pattern"), "dense4pattern.png"),
                #                     ("Dense5Pattern", _("Somewhat sparse brush pattern"), "dense5pattern.png"),
                #                     ("Dense6Pattern", _("Very sparse brush pattern"), "dense6pattern.png"),
                #                     ("Dense7Pattern", _("Extremely sparse brush pattern"), "dense7pattern.png"),
                #                     ("HorPattern", _("Horizontal lines"), "horpattern.png"),
                #                     ("VerPattern", _("Vertical lines"), "verpattern.png"),
                #                     ("CrossPattern", _("Crossing horizontal and vertical lines"),
                #                      "crosspattern.png"),
                #                     ("BDiagPattern", _("Backward diagonal lines"), "bdiagpattern.png"),
                #                     ("FDiagPattern", _("Forward diagonal lines"), "fdiagpattern.png"),
                #                     ("DiagCrossPattern", _("Crossing diagonal lines"), "diagcrosspattern.png"),
                #                 #    ("LinearGradientPattern", _("Linear gradient (set using a dedicated QBrush constructor)"), "none.png"),
                #                 #    ("ConicalGradientPattern", _("Conical gradient (set using a dedicated QBrush constructor)"), "none.png"),
                #                 #    ("RadialGradientPattern", _("Radial gradient (set using a dedicated QBrush constructor)"), "none.png"),
                #                 #    ("TexturePattern", _("Custom pattern (see QBrush::setTexture())"), "none.png"),
                #                 ]
                rect = item.get_rect()
                sh = item.shape.shapeparam
                # if the area being slected == larger than max change color to
                # red
                qrect = self._restrict_rect_to_positive(rect)
                if self.roi_limit_def:
                    qrect = self.roi_limit_def.check_limits(qrect)
                    # item.setTitle(self.roi_limit_def.get_label())
                    item.setTitle(
                        self.roi_limit_def.get_label() + ": %d" % item.unique_id
                    )

                    if self.roi_limit_def.state == ROI_STATE_ALARM:
                        self.inputState.shape_outof_range = True
                    else:
                        self.inputState.shape_outof_range = False
                else:
                    self.inputState.shape_outof_range = False

                if self.roi_limit_def:
                    item.shape.sel_brush.setStyle(self.roi_limit_def.get_fill_pattern())
                    item.shape.sel_brush.setColor(self.roi_limit_def.get_color())

                sh.update_param(item.shape)
                return qrect

    def force_shape_out_of_range(self, out_of_range=False):
        print(("imageWidget: force_shape_out_of_range: ", out_of_range))
        self.inputState.force_out_of_range = out_of_range

    def _emit_select_roi(self, img_type, cmnd=widget_com_cmnd_types.SELECT_ROI):
        """
        _emit_select_roi(): emit when a new ROI has been selected

        :param img_type: img_type description
        :type img_type: img_type type

        :param cmnd=widget_com_cmnd_types.ROI_CHANGED: cmnd=widget_com_cmnd_types.ROI_CHANGED description
        :type cmnd=widget_com_cmnd_types.ROI_CHANGED: cmnd=widget_com_cmnd_types.ROI_CHANGED type

        :returns: None
        """

        if self.inputState.force_out_of_range or self.inputState.shape_outof_range:
            return

        # print 'emitting new roi' , self.inputState.plotitem_id
        dct = make_spatial_db_dict()
        dct_put(dct, WDGCOM_CMND, cmnd)
        # dct_put(dct, SPDB_SCAN_PLUGIN_ITEM_ID, self.inputState.plotitem_id)
        dct_put(dct, SPDB_PLOT_ITEM_ID, self.inputState.plotitem_id)
        dct_put(dct, SPDB_PLOT_ITEM_TITLE, self.inputState.plotitem_title)
        dct_put(dct, SPDB_PLOT_SHAPE_TYPE, self.inputState.plotitem_type)
        dct_put(dct, SPDB_PLOT_KEY_PRESSED, self.inputState.keyisPressed)
        dct_put(dct, SPDB_ID_VAL, self.inputState.plotitem_id)

        cntr = self.inputState.center
        rng = self.inputState.range
        rect = self.inputState.rect

        cx = cntr[0]
        cy = cntr[1]
        rx = rng[0]
        ry = rng[1]
        (x1, y1, x2, y2) = rect

        if cntr != None:
            dct_put(dct, SPDB_XCENTER, cx)
            dct_put(dct, SPDB_YCENTER, cy)
            dct_put(dct, SPDB_XSTART, x1)
            dct_put(dct, SPDB_YSTART, y1)
            dct_put(dct, SPDB_XSTOP, x2)
            dct_put(dct, SPDB_YSTOP, y2)

        else:
            return

        if rx != None:
            dct_put(dct, SPDB_XRANGE, abs(rx))
        else:
            dct_put(dct, SPDB_XRANGE, None)

        if ry != None:
            dct_put(dct, SPDB_YRANGE, abs(ry))
        else:
            dct_put(dct, SPDB_YRANGE, None)

        dct_put(dct, SPDB_ZRANGE, None)
        dct_put(dct, SPDB_PLOT_IMAGE_TYPE, img_type)

        # print 'emitting new roi: ', rect
        self.new_roi_center.emit(dct)

    def do_emit_new_roi(self, img_type):
        """
        used primarily when loading a pattern generator image to force the image params to get loaded into the plugin
        spdb
        @return:
        """
        self._emit_new_roi(img_type, load_pattern=True)


    def _emit_new_roi(self, img_type, cmnd=widget_com_cmnd_types.ROI_CHANGED, load_pattern=False):
        """
        _emit_new_roi(): description

        :param img_type: img_type description
        :type img_type: img_type type

        :param cmnd=widget_com_cmnd_types.ROI_CHANGED: cmnd=widget_com_cmnd_types.ROI_CHANGED description
        :type cmnd=widget_com_cmnd_types.ROI_CHANGED: cmnd=widget_com_cmnd_types.ROI_CHANGED type

        :returns: None
        """
        """
        emit a dict that represents all of the params that scans need
        this == so that we can use the same signal handling for configuring scans
        as well as dynamically configuring the center and range of a scan from the plotter
        """

        if self.inputState.force_out_of_range or self.inputState.shape_outof_range:
            return

        # if((not is_unique_roi_id_in_list(self.inputState.plotitem_id)) and not(self.inputState.keyisPressed[Qt.Key_Alt]) and not(self.inputState.keyisPressed[Qt.Key_C])):
        if (not is_unique_roi_id_in_list(self.inputState.plotitem_id)) and not (
            self.inputState.keyisPressed[Qt.Key_Alt]
        ) and not load_pattern:
            # print '_emit_new_roi: oops: unique_id != in master list, kicking out'
            # print 'self.inputState.keyisPressed' , dump_key_pressed(self.inputState.keyisPressed)
            return

        dct = make_spatial_db_dict()
        dct_put(dct, WDGCOM_CMND, cmnd)
        # dct_put(dct, SPDB_SCAN_PLUGIN_ITEM_ID, self.inputState.plotitem_id)
        dct_put(dct, SPDB_PLOT_ITEM_ID, self.inputState.plotitem_id)
        dct_put(dct, SPDB_PLOT_ITEM_TITLE, self.inputState.plotitem_title)
        dct_put(dct, SPDB_PLOT_SHAPE_TYPE, self.inputState.plotitem_type)
        dct_put(dct, SPDB_PLOT_KEY_PRESSED, self.inputState.keyisPressed)
        dct_put(dct, SPDB_ID_VAL, self.inputState.plotitem_id)

        cntr = self.inputState.center
        rng = self.inputState.range
        rect = self.inputState.rect

        cx = cntr[0]
        cy = cntr[1]
        rx = rng[0]
        ry = rng[1]
        (x1, y1, x2, y2) = rect
        # print '_emit_new_roi: emitting new roi center ', (cx,cy)

        if self.inputState.plotitem_id != None:
            # print '_emit_new_roi: sp_id=%d cx=%.2f cy=%.2f' % (self.inputState.plotitem_id, cx, cy)
            pass

        if cntr != None:
            if self.image_type in [types.image_types.FOCUS, types.image_types.OSAFOCUS]:
                # this == a focus scan so Y == actually the ZP Z axis so copy Y to Z
                dct_put(dct, SPDB_XCENTER, cx)
                dct_put(dct, SPDB_ZZCENTER, cy)
                dct_put(dct, SPDB_YCENTER, None)
                dct_put(dct, SPDB_XSTART, x1)
                dct_put(dct, SPDB_ZZSTART, y1)
                dct_put(dct, SPDB_YSTART, None)
                dct_put(dct, SPDB_XSTOP, x2)
                dct_put(dct, SPDB_ZZSTOP, y2)
                dct_put(dct, SPDB_YSTOP, None)
            else:
                dct_put(dct, SPDB_XCENTER, cx)
                dct_put(dct, SPDB_YCENTER, cy)
                dct_put(dct, SPDB_XSTART, x1)
                dct_put(dct, SPDB_YSTART, y1)
                dct_put(dct, SPDB_XSTOP, x2)
                dct_put(dct, SPDB_YSTOP, y2)

        if rx != None:
            dct_put(dct, SPDB_XRANGE, abs(rx))
        else:
            dct_put(dct, SPDB_XRANGE, None)

        if ry != None:
            if self.image_type in [types.image_types.FOCUS, types.image_types.OSAFOCUS]:
                # this == a focus scan so Y == actually the ZP Z axis so copy Y to Z
                dct_put(dct, SPDB_ZZRANGE, abs(ry))
            else:
                dct_put(dct, SPDB_YRANGE, abs(ry))
        else:
            dct_put(dct, SPDB_YRANGE, None)

        # dct_put(dct, SPDB_ZRANGE, None)
        dct_put(dct, SPDB_PLOT_IMAGE_TYPE, img_type)

        # print('emitting new roi: ', rect)
        self.new_roi_center.emit(dct)

    def on_update_region(self, data):
        """
        on_update_region(): description

        :param data: data description
        :type data: data type

        :returns: None
        """
        # print 'stxmImageWidget: on_update_region'
        # print data
        pass

    def set_cs_label_text(self, cs, msg):
        """
        set_cs_label_text(): description

        :param cs: cs description
        :type cs: cs type

        :param msg: msg description
        :type msg: msg type

        :returns: None
        """
        label = self.get_cs_label_item(cs)
        if label:
            label.set_text(msg)
        else:
            label = make.label(_(msg), "TL", (0, 0), "TL")
            cs.cs_plot.add_item(label, z=999999999)
        cs.cs_plot.update_plot()

    def get_cs_label_item(self, cs):
        """
        get_cs_label_item(): description

        :param cs: cs description
        :type cs: cs type

        :returns: None
        """
        items = cs.cs_plot.get_items()
        for item in items:
            if isinstance(item, LabelItem):
                if item.isVisible():
                    return item
        return None

    def get_cs_item(self, cs):
        """
        get_cs_item(): description

        :param cs: cs description
        :type cs: cs type

        :returns: None
        """
        e = enumerate(cs.cs_plot.known_items.items())
        # if(len(e) > 0):
        for d in e:
            # d = e.next()
            # (0, (<plotpy.items.ImageItem object at 0x053CB030>, <plotpy.panels.csection.cswidget.XCrossSectionItem object at 0x05C8C660>))
            csi = d[1][1]
            # <plotpy.panels.csection.cswidget.XCrossSectionItem object at 0x05C8C660>
            return csi
        # or if there are any then
        return None

    def dump_cross_section_panels(self, x, y):
        """
        dump_cross_section_panels(): description

        :param x: x description
        :type x: x type

        :param y: y description
        :type y: y type

        :returns: None
        """
        xcs = self.get_xcs_panel()
        ycs = self.get_ycs_panel()

        xcsi = self.get_cs_item(xcs)
        ycsi = self.get_cs_item(ycs)

        if xcsi != None:
            datx = xcsi._y
        if ycsi != None:
            daty = ycsi._x

    def marker_changed(self, marker):
        """
        marker_changed(): description
        if I leave this func emitting a new_roi when the alt key == held down then when I am trying to look at an image and
        only update the cross field plots I will also be updating the centerX/Y of the scan which I dont want to do.
        so for now I am leaving it as pass

        :param marker: marker description
        :type marker: marker type

        :returns: None
        """
        pass
        # cntr = marker.get_pos()
        # self.inputState.center = (cntr[0], cntr[1])
        # self.inputState.range = (0, 0)
        # self.inputState.npts = (None , None)
        # self.inputState.rect = (cntr[0], cntr[1], 0, 0)
        # self.inputState.plotitem_type = None
        #
        # if(self.inputState.keyisPressed[Qt.Key_Alt]):
        #     #if Alt key == pressed then this != a segment or something else so make sure the
        #     # flag that plotitem_type == reset to None
        #     self._emit_new_roi(self.image_type)

    def _centersize_to_rect(self, _center, _size):
        """
        _centersize_to_rect(): description

        :param _center: _center description
        :type _center: _center type

        :param _size: _size description
        :type _size: _size type

        :returns: None
        """
        """ center and size are in units (um) """
        centX, centY = _center
        szX, szY = _size

        startX = centX - (szX * 0.5)  # Left
        stopX = centX + (szX * 0.5)  # Right
        startY = centY + (szY * 0.5)  # Top
        stopY = centY - (szY * 0.5)  # Bottom
        # print (startX, stopX, startY, stopY)
        return (startX, startY, stopX, stopY)

    def _handle_final_rect_shape(self, shape):
        """
        _handle_final_rect_shape(): description

        :param shape: shape description
        :type shape: shape type

        :returns: None
        """
        roi = types.spatial_type_prefix.ROI
        shape.setTitle("%s %d" % (types.spatial_type_prefix[roi], shape.shapeNum))
        shape.annotationparam.title = "%s %d" % (
            types.spatial_type_prefix[roi],
            shape.shapeNum,
        )
        if self.checkRegionEnabled:
            rect = self._check_valid_region(shape)
        shape.position_and_size_visible = False
        #         shape.setItemAttribute(Qwt.QwtPlotItem.Legend)
        #         widget = self.plot.legend().find(shape)
        #         if isinstance(widget, Qwt.QwtLegendItem):
        #             widget.setChecked(True)

        ret = self._anno_spatial_to_region(shape, set_id=True)
        self.new_region.emit(ret)

        cur_shapes = self.getShapeItemsByShapeType(AnnotatedRectangle)
        if (not self.multi_region_enabled) and (len(cur_shapes) > 0):
            self.enable_tool_by_name("clsAverageCrossSectionTool", False)
        else:
            self.enable_tool_by_name("clsAverageCrossSectionTool", True)

    def _create_rect_shape(self):
        """
        _create_rect_shape(): description

        :returns: None
        """
        # print '_create_rect_shape:'
        # items = cs.cs_plot.get_items()
        # for item in items:
        #    if(isinstance(item, LabelItem)):
        ap = AnnotationParam()
        # ap.subtitle = 'my _create_rect_shape'
        # ap.title = 'selecting'
        # ap.title = '%s %d' % (SPATIAL_TYPE_PREFIX[TWO_D], self.roiNum)
        ap.transform_matrix = [
            [self.xstep, 0.0, 0.0],
            [0.0, self.ystep, 0.0],
            [0.0, 0.0, 1.0],
        ]
        ap.format = "%5.2f um"
        return AnnotatedRectangle(0, 0, 1, 1, annotationparam=ap), 0, 2

    def _get_seg_anno_params(self):
        """
        _get_seg_anno_params(): description

        :returns: None
        """
        title = "%s %d" % (types.spatial_type_prefix.SEG, self.segNum)
        # title = 'selecting'
        transform_matrix = [
            [self.xstep, 0.0, 0.0],
            [0.0, self.ystep, 0.0],
            [0.0, 0.0, 1.0],
        ]
        format = "%5.2f um"
        return (title, transform_matrix, format)

    def _create_seg_shape(self):
        """
        _create_seg_shape(): description

        :returns: None
        """
        """ this == called when the user lets go of the left mouse button at teh end if the drag """
        # print '_create_seg_shape:'
        ap = AnnotationParam()
        ap.title = "%s %d" % (types.spatial_type_prefix.SEG, self.segNum)
        # ap.title = 'selecting'
        ap.transform_matrix = [
            [self.xstep, 0.0, 0.0],
            [0.0, self.ystep, 0.0],
            [0.0, 0.0, 1.0],
        ]
        ap.format = "%5.2f um"
        return AnnotatedSegment(0, 0, 1, 1, annotationparam=ap), 0, 2

    def _create_point_shape(self):
        """
        _create_point_shape(): description

        :returns: None
        """
        # print '_create_point_shape:'
        ap = AnnotationParam()
        ap.title = "%s %d" % (types.spatial_type_prefix.PNT, self.shapeNum)
        # ap.title = 'selecting:'
        ap.transform_matrix = [
            [self.xstep, 0.0, 0.0],
            [0.0, self.ystep, 0.0],
            [0.0, 0.0, 1.0],
        ]
        ap.format = "%5.2f um"
        return AnnotatedPoint(0, 0, annotationparam=ap), 0, 0

    def _pretty(self, d, indent=1):
        """
        _pretty(): description

        :param d: d description
        :type d: d type

        :param indent=1: indent=1 description
        :type indent=1: indent=1 type

        :returns: None
        """
        for key, value in d.items():
            print("\t" * indent + str(key))
            if isinstance(value, dict):
                self._pretty(value, indent + 1)
            else:
                print("\t" * (indent + 1) + str(value))

    def initData(self, item_name, image_type, rows, cols, parms={}):
        """
        initData(): description

        :param image_type: image_type description
        :type image_type: image_type type

        :param rows: rows description
        :type rows: rows type

        :param cols: cols description
        :type cols: cols type

        :param parms={}: parms={} description
        :type parms={}: parms={} type

        :returns: None
        """
        # clear title
        # print('ImageWidgetPlot: initData called, rows=%d, cols=%d' % (rows, cols))

        plot = self.get_plot()
        plot.set_title("")
        # clear any shapes
        self.delShapePlotItems()
        # scalars for non-square data
        self.htSc = 1
        self.widthSc = 1
        array = np.empty((int(rows), int(cols)))
        array[:] = np.NAN
        #array = np.zeros((int(rows), int(cols)))
        #array[:] = 0
        array[0][0] = 0
        item = self.get_image_item(item_name)
        item.data = array
        #print(f'initData: creating self.data[img_idx] id = {id(self.data[img_idx])}')
        self.wPtr = 0
        self.hPtr = 0

        self.image_type = image_type

        # if it == a focus image I dont want any of the tools screweing up the
        # scan params so disable them
        if self.image_type in [types.image_types.FOCUS, types.image_types.OSAFOCUS]:
            self.enable_tools_by_spatial_type(None)

        # self.items = make.image(self.data[img_idx], title='', interpolation='nearest', colormap='gist_gray')
        # plot.add_item(self.items, z=1)
        new_item = make.image(
            item.data, title="", interpolation="nearest", colormap="gist_gray"
        )
        # plot.add_item(self.items[img_idx], z=1)
        plot.add_item(new_item)
        # plot.set_plot_limits(0.0, 740.0, 0.0, 800.0)
        self.image_is_new = True
        if "RECT" in list(parms.keys()):
            rect = parms["RECT"]
            self.set_image_parameters(item_name, rect[0], rect[1], rect[2], rect[3])
        return self.data[item_name].shape

    ################## THIS IS MEANT TO REPLACE initData eventually
    def init_image_items(self, det_nms, image_type, rows, cols, parms={}):
        """
        initData(): Initialize the image items based on the detector name and size of images needed

        :param image_type: image_type description
        :type image_type: image_type type

        :param rows: rows description
        :type rows: rows type

        :param cols: cols description
        :type cols: cols type

        :param parms={}: parms={} description
        :type parms={}: parms={} type

        :returns: None
        """
        assert type(det_nms) == list, "init_image_items: det_nms != a list:"
        skip_lst = ["DNM_RING_CURRENT"]
        plot = self.get_plot()
        plot.set_title("")
        # clear any shapes
        self.delShapePlotItems()

        for det_nm in det_nms:
            if det_nm in skip_lst:
                continue
            # scalars for non-square data
            self.htSc = 1
            self.widthSc = 1
            array = np.empty((int(rows), int(cols)))
            array[:] = np.NAN
            array[0][0] = 0
            # print(f'initData: creating self.data[img_idx] id = {id(self.data[img_idx])}')
            self.wPtr = 0
            self.hPtr = 0
            self.image_type = image_type
            # if it == a focus image I dont want any of the tools screweing up the
            # scan params so disable them
            if self.image_type in [types.image_types.FOCUS, types.image_types.OSAFOCUS]:
                self.enable_tools_by_spatial_type(None)
            item = make.image(array, title=det_nm, interpolation="nearest", colormap="gist_gray")
            if "RECT" in list(parms.keys()):
                rect = parms["RECT"]
                self.set_image_parameters(det_nm, rect[0], rect[1], rect[2], rect[3], item=item)

            plot.add_item(item, z=len(self.plot.get_items()) + 10)
            self.image_is_new = True
            # if "RECT" in list(parms.keys()):
            #     rect = parms["RECT"]
            #     self.set_image_parameters(det_nm, rect[0], rect[1], rect[2], rect[3])

    def get_image_item(self, item_name=''):
        '''
        based on the name of the image item search list of current plot items and return it if it exists
        '''
        plot = self.get_plot()
        items = plot.get_items()
        img_items = []
        for item in items:
            #if type(item) == ImageItem:
            if type(item) in [ImageItem, TrImageItem]:
                img_items.append(item)
                if item_name == item.title().text():
                    return(item)
        if len(img_items) > 0:
            #return the most recent one because the title was not used for the image item, likely dropped or sent from ThumbnailViewer widget
            return(img_items[-1])
        return(None)

    def get_all_image_items(self):
        plot = self.get_plot()
        items = plot.get_items()
        img_items = []
        for item in items:
            if type(item) in [ImageItem, TrImageItem]:
                img_items.append(item)
        return img_items

    def _makeSquareDataArray(self, array):
        """
        _makeSquareDataArray(): description

        :param array: array description
        :type array: array type

        :returns: None
        """
        """ for display purposes it's easiest to have the data square so repeat
        pixels in the lesser demension, as well make sure that the demensions are 32 bit aligned
        """
        h, w = array.shape

        if h != w:
            if h < w:
                # scale Height and width to something divisible by for (32 bit
                # aligned)
                self.widthSc, self.htSc = nextFactor(w, h)
                newArray = np.repeat(
                    np.repeat(array, self.htSc, axis=0), self.widthSc, axis=1
                )
            else:
                self.htSc, self.widthSc = nextFactor(h, w)
                newArray = np.repeat(
                    np.repeat(array, self.htSc, axis=0), self.widthSc, axis=1
                )
        else:
            newArray = array

        # print '_makeSquareDataArray: shape='
        # print newArray.shape
        return newArray

    def _convSampleToDisplay(self, x, y, item_name=''):
        """
        _convSampleToDisplay(): description

        :param x: x description
        :type x: x type

        :param y: y description
        :type y: y type

        :returns: None
        """
        """remember this == a 2d array array[row][column] so it == [array[y][x]
           so that it will display the data from bottom/up left to right
        """
        item = self.get_image_item(item_name)
        h, w = item.data.shape
        xscaler = self.widthSc
        yscaler = self.htSc
        #         #convert
        rowStart = int((self.dataHeight - 0) + (y * yscaler)) - (h / 2.0)
        colStart = int(x * xscaler) - (w / 2.0)
        rowStop = int(rowStart - self.zoom_scale)
        colStop = int(colStart + self.zoom_scale)

        return (colStart, colStop, rowStart, rowStop)

    def showData(self, item_name=''):
        """
        showData(): description

        :returns: None
        """
        self.show_data(item_name)

    def addData(self, item_name, x, y, val, show=False):
        """
        addData(): description

        :param x: x description
        :type x: x type

        :param y: y description
        :type y: y type

        :param val: val description
        :type val: val type

        :param show=False: show=False description
        :type show=False: show=False type

        :returns: None
        """
        """ this function adds a new point to the 2d array
        kept around for backward compatability but new calls should use addPoint()
        """
        if not self.dataAtMax:
            item = self.get_image_item(item_name)
            # remember this == a 2d array array[row][column] so it == [array[y][x]
            # so that it will display the data from bottom/up left to right
            (colStart, colStop, rowStart, rowStop) = self._convSampleToDisplay(x, y)
            # print 'adding (%d,%d,%d,%d) = %d' % (colStart, colStop, rowStart, rowStop,val)
            # scal data
            # self.data[rowStop:rowStart, colStart:colStop] = copy.deepcopy(val)
            item.data[rowStop:rowStart, colStart:colStop] = val

            if show:
                self.show_data(item_name)


    def get_plot_items(self):
        """
        return all items currently assigned to the plot
        """
        plot = self.get_plot()
        items = plot.items
        return(items)


    def addPixel(self, item_name, x, y, val, pixel_size=50, show=False):
        """
        addPoint(): description

        :param y: y description
        :type y: y type

        :param x: x description
        :type x: x type

        :param val: val description
        :type val: val type

        :param show=False: show=False description
        :type show=False: show=False type

        :returns: None
        """
        """ this function adds a new point to the 2d array
        """
        # if(not self.dataAtMax):

        item = self.get_image_item(item_name)
        if len(self.data) > 0:
            rows, cols = item.data.shape
            if y < rows:
                # remember this == a 2d array array[row][column] so it == [array[y][x]
                # so that it will display the data from bottom/up left to right
                # (colStart, colStop, rowStart, rowStop) = self._convSampleToDisplay( x, y)
                # self.data[rowStop:rowStart , colStart:colStop] = copy.deepcopy(val)
                # self.data[y , x] = copy.deepcopy(val)
                h, w = item.data.shape
                arr_cy = h / 2
                arr_cx = w / 2

                arr_x = arr_cx + x
                arr_y = arr_cy + y

                x1 = arr_x - (pixel_size * 0.5)
                x2 = arr_x + (pixel_size * 0.5)
                y1 = arr_y - (pixel_size * 0.5)
                y2 = arr_y + (pixel_size * 0.5)

                item.data[y1:y2, x1:x2] = val

            if show:
                self.show_data(item_name)


    def add_point(self, item_name, y, x, val, show=False):
        """
        addPoint(): description

        :param y: y description
        :type y: y type

        :param x: x description
        :type x: x type

        :param val: val description
        :type val: val type

        :param show=False: show=False description
        :type show=False: show=False type

        :returns: None
        """
        """ this function adds a new point to the 2d array
        """
        items = self.get_plot_items()
        if len(items) > 0:
            item = self.get_image_item(item_name)
            if item:
                data = item.data
                rows, cols = data.shape
                if (y < rows) and (x < cols):
                    # remember this == a 2d array array[row][column] so it == [array[y][x]
                    # so that it will display the data from bottom/up left to right
                    data[y, x] = val

                if show:
                    self.show_data(item_name)

                if self._auto_contrast:
                    self.apply_auto_contrast(item_name)

    def add_line_at_row_col(self, item_name, row, col, line, show=False):
        """
        addLine(): description

        :param img_idx: the image data is stored in a multidimensional array, user can load more than one image at a time so each gets an index id
        :type img_idx: integer

        :param row: row description
        :type row: row type

        :param line: line description
        :type line: line type

        :param show=False: show=False description
        :type show=False: show=False type

        :param col: col sometimes a scan from a diff detector might only put out a partial line so col is the x offset
        :type col: col type

        :returns: None
        """
        """ this function adds a new line to the 2d array
        """
        # print 'addLine: row=%d' % row
        # print 'addLine: data length = %d vals' % len(line)
        if self.image_is_new:
            self.image_is_new = False
        item = self.get_image_item(item_name)
        if item:
            data = item.data
            rows, cols = data.shape
            if row >= rows:
                # row = rows - 1
                # ignore it
                return
            if col is None:
                data[row, :] = line[:]
            else:
                #  print(f"addLine: len(line) is {len(line)} col={col}")
                # print(f"addLine: line is {line}\n\n")
                #data[row, col:_line_len] = line[:]
                # data[row, col:col + len(line)] = line
                #with Pixelator that can return tiled lines we need to make sure that the data fits the last column
                if len(data[row, col:col + len(line)]) < len(line):
                    short_line = len(data[row, col:col + len(line)])
                    data[row, col:col + len(line)] = line[0:short_line]
                else:
                    data[row, col:col + len(line)] = line

            if show:
                if self._auto_contrast:
                    self.apply_auto_contrast(item_name)
                self.replot()
        else:
            _logger.error(f"stxmImageWidget: addLine: item with name {item_name} does not exist")

    def addLine(self, item_name, row, line, show=False):
        """
        addLine(): description

        :param img_idx: the image data is stored in a multidimensional array, user can load more than one image at a time so each gets an index id
        :type img_idx: integer

        :param row: row description
        :type row: row type

        :param line: line description
        :type line: line type

        :param show=False: show=False description
        :type show=False: show=False type

        :returns: None
        """
        """ this function adds a new line to the 2d array
        """
        # print 'addLine: row=%d' % row
        # print 'addLine: data length = %d vals' % len(line)
        if self.image_is_new:
            self.image_is_new = False
        item = self.get_image_item(item_name)
        if item:
            data = item.data
            rows, cols = data.shape
            if cols != len(line):
                line = np.resize(line, (cols,))

            if row >= rows:
                #row = rows - 1
                #ignore it
                return

            data[row, :] = line[:]
            if show:
                if self._auto_contrast:
                    self.apply_auto_contrast(item_name)
                self.replot()
        else:
            _logger.error(f"stxmImageWidget: addLine: item with name {item_name} does not exist")

    def add_vertical_line(self, item_name, col, line, show=False):
        """
        add_vertical_line(): description

        :param col: column description
        :type col: col type

        :param line: line description
        :type line: line type

        :param show=False: show=False description
        :type show=False: show=False type

        :returns: None
        """
        """ this function adds a new vertical line to the 2d array
        """
        # print 'addLine: row=%d' % row
        # print 'addLine: data length = %d vals' % len(line)
        if self.image_is_new:
            self.image_is_new = False
            if col != 0:
                return
        # this == a catch for a spurious previsou row being sent
        # at the start of a scan, fix this sometime

        # print 'row=%d' % row
        item = self.get_image_item(item_name)
        if item:
            data = item.data
            rows, cols = data.shape

            if col >= cols:
                col = cols - 1

            data[:, col] = line[0:rows]

            #     self.show_data(img_idx, self.data[img_idx])
            if show:
                # self.show_data(img_idx, self.data)
                if self._auto_contrast:
                    self.apply_auto_contrast(item_name)
                self.replot()
        else:
            _logger.error(
                "ImageWidget: add_vertical_line: self.data[%s] == None" % item_name
            )

    def add_vertical_line_at_row_col(self, item_name, row, col, line, show=False):
        """
        addVerticalLine(): this function adds a new vertical line to the 2d array

        :param col: column description
        :type col: col type

        :param line: line description
        :type line: line type

        :param show=False: show=False description
        :type show=False: show=False type

        :returns: None
        """

        # print 'addLine: row=%d' % row
        # print 'addLine: data length = %d vals' % len(line)
        if self.image_is_new:
            self.image_is_new = False
            if col != 0:
                return
        # this == a catch for a spurious previsou row being sent
        # at the start of a scan, fix this sometime

        # print 'row=%d' % row
        item = self.get_image_item(item_name)
        if item:
            rows, cols = item.data.shape

            if col >= cols:
                col = cols - 1

            line_len = len(line)
            # print(f"add_vertical_line_at_row_col: item.name={item.title().text()} item.data.shape = {item.data.shape}")
            # the first pixel in teh nan array has been set to 0.0 in init_items
            # if its left as nan the contrast tool throws an exception, maybe addressed in plotpy in future
            if item.data[0][col] == 0.0:
                index = 0
            else:
                # look for the next NAN value in the column
                index = np.where(np.isnan(item.data[:, col]))[0][0]
            # print(f"addVerticalLineAtRowCol: row={row}, col={col}, index={index}")
            item.data[index:index + line_len, col] = line #line[0:rows]

            if show:
                # self.show_data(img_idx, self.data)
                if self._auto_contrast:
                    self.apply_auto_contrast(item_name)
                self.replot()
        else:
            _logger.error(
                "stxmImageWidget: addVerticalLine: self.data[%s] == None" % item_name
            )

    def get_img_item_keys(self):
        """
        return the keys to teh current dict of data
        """
        return(list(self.data.keys()))

    def load_file_data(self, fileName, data, img_idx):
        """
        load_file_data(): description

        :param fileName: fileName description
        :type fileName: fileName type

        :param data: data description
        :type data: data type

        :returns: None
        """
        self.fileName = fileName
        self.data[img_idx] = data
        # self.show_data(self.data)
        if self.filtVal > 0:
            self.apply_filter(self.filtVal)
        else:
            self.show_data(img_idx)

    def set_data(self, item_name, data):
        """
        set_data(): description

        :param data: data description
        :type data: data type

        :returns: None
        """
        item = self.get_image_item(item_name)

        if item is None:
            item = make.image(data, interpolation="nearest")

        if data.size == 0:
            return
        item.data = data
        # self.show_data(self.data)
        item.set_lut_range([item.data.min(), item.data.max()])
        self.show_data(item_name)
        self.set_autoscale()

    def set_data_from_viewer(self, item_name, img_type, data, rect):
        """

        """

        rows, cols = data.shape
        self.init_image_items([item_name], img_type, rows, cols, parms={SPDB_RECT: rect})


    def set_autoscale(self, fill_plot_window=False):
        """
        set_autoscale(): description

        :param fill_plot_window=False: fill_plot_window=False description
        :type fill_plot_window=False: fill_plot_window=False type

        :returns: None
        """
        plot = self.get_plot()
        if fill_plot_window or self.fill_plot_window:
            # unlock so that an autoscale will work
            self.set_lock_aspect_ratio(False)
            plot.do_autoscale()
            # lock it again
            self.set_lock_aspect_ratio(True)
        else:
            self.set_lock_aspect_ratio(True)
            plot.do_autoscale()

    def show_data(
        self,
        item_name,
        init=False,
    ):
        """
        show_data(): description

        :param data: data description
        :type data: data type

        :param init=False: init=False description
        :type init=False: init=False type

        :returns: None
        """
        # if img_idx not in list(self.data.keys()):
        #     return
        #
        # if self.data[img_idx].size == 0:
        #     return
        plot = self.get_plot()
        # items = len(self.plot.get_items(item_type=ICSImageItemType))
        # # if(self.items[img_idx] == None):
        # if (len(self.items) == 0) or (self.items[img_idx] == None):
        #     self.items[img_idx] = make.image(
        #         self.data[img_idx], interpolation="nearest", colormap="gist_gray"
        #     )
        #     plot.add_item(self.items[img_idx], z=items + 1)
        #     # plot.set_plot_limits(0.0, 740.0, 0.0, 800.0)
        # else:
        #     if self._auto_contrast:
        #         # self.items[img_idx].set_data(data[img_idx])
        #         # self.items[img_idx].set_data(data)
        #         self.items[img_idx].set_data(self.data[img_idx])
        #     else:
        #         lut_range = self.items[img_idx].get_lut_range()
        #         self.items[img_idx].set_data(self.data[img_idx], lut_range)
        plot.replot()

    def apply_auto_contrast(self, item_name, lut_range=None):
        """
        Set Image item data

            * data: 2D NumPy array
            * lut_range: LUT range -- tuple (levelmin, levelmax)
        """
        # if img_idx not in list(self.data.keys()):
        #     return
        item = self.get_image_item(item_name)
        data = item.data
        if lut_range != None:
            _min, _max = lut_range
        else:
            _min, _max = _nanmin(data), _nanmax(data)

        # self.data = self.data[img_idx]
        item.histogram_cache = None
        item.update_bounds()
        item.update_border()
        item.set_lut_range([_min, _max])

    def apply_filter(self, val, item_name=''):
        """
        apply_filter(): description

        :param val: val description
        :type val: val type

        :returns: None
        """
        item = self.get_image_item(item_name)
        if val:
            # apply filter
            if item:

                item.data = self.filterfunc(item.data, val)
        else:
            # no filter just display raw
            # data = self.data[img_idx]
            pass
        self.filtVal = val
        self.show_data(item_name)

    def setCurFilter(self, filtName):
        """
        setCurFilter(): description

        :param filtName: filtName description
        :type filtName: filtName type

        :returns: None
        """
        import scipy
        self.curFilterStr = filtName
        # print 'setCurFilter: filter changed to %s' % self.curFilterStr
        self.curFilterStr = str(filtName)
        self.filterfunc = getattr(scipy.ndimage, self.curFilterStr)
        self.apply_filter(self.filtVal)
        self.get_xcs_panel().update_plot()
        self.get_ycs_panel().update_plot()

    def deselect_all_shapes(self):
        items = self.plot.get_items(item_type=IShapeItemType)
        for item in items:
            item.unselect()
        self.plot.replot()

    def enable_all_shape_labels(self, do=True):
        items = self.plot.get_items(item_type=IShapeItemType)

        for item in items:
            item.unselect()
            if hasattr(item, "is_label_visible"):
                if do:
                    item.set_label_visible(True)
                else:
                    item.set_label_visible(False)
            self.plot.replot()
        return

    def mousePressEvent(self, ev):
        """
        mousePressEvent(): description

        :param ev: ev description
        :type ev: ev type

        :returns: None
        """
        # print 'ImageWidgetPlot: mouse pressed'
        btn = ev.button()
        self.inputState.btnisPressed[btn] = True
        if btn == QtCore.Qt.MouseButton.LeftButton:
            # print 'left mouse button pressed'
            # check to see if the user == using one of the selection tools, if so
            # then set the name of the active plot item, if you can
            tool = self.plot.manager.get_active_tool()
            if isinstance(tool, AverageCrossSectionTool):
                # print 'Average selection tool selected'
                if hasattr(tool, "shapeNum"):
                    self.roiNum = tool.shapeNum
            elif isinstance(tool, AnnotatedSegmentTool):
                # print 'AnnotatedSegmentTool tool selected'
                if hasattr(tool, "shapeNum"):
                    self.segNum = tool.shapeNum
            elif isinstance(tool, AnnotatedPointTool):
                # print 'AnnotatedPointTool tool selected'
                if hasattr(tool, "shapeNum"):
                    self.shapeNum = tool.shapeNum

            plot = self.get_plot()
            # pan = plot.get_itemlist_panel()
            # get all the shapes and turn off their size texts
            active_item = plot.get_active_item()
            if active_item != None:

                if hasattr(active_item, "unique_id"):
                    title = str(active_item.title().text())

                    if title.find("ROI") > -1:
                        self.inputState.plotitem_type = types.spatial_type_prefix.ROI
                        ret = self._anno_spatial_to_region(active_item)

                    elif title.find("SEG") > -1:
                        self.inputState.plotitem_type = types.spatial_type_prefix.SEG
                        ret = self._anno_seg_to_region(active_item)

                    elif title.find("PNT") > -1:
                        self.inputState.plotitem_type = types.spatial_type_prefix.PNT
                        ret = self._anno_point_to_region(active_item)

                    else:
                        # dont do anything
                        return

                    self.inputState.plotitem_id = active_item.unique_id
                    self.inputState.plotitem_title = title
                    self.inputState.plotitem_shape = active_item
                    self.inputState.center = ret["center"]
                    self.inputState.range = ret["range"]
                    self.inputState.rect = ret["rect"]
                    self.inputState.npts = (None, None)
                    # , cmnd=widget_com_cmnd_types.ADD_ROI)
                    # print 'mousePressEvent: emitting_new_roi with cmnd = SELECT_ROI'
                    self._emit_new_roi(
                        self.image_type, cmnd=widget_com_cmnd_types.SELECT_ROI
                    )
            else:
                self.inputState.reset()

        elif btn == QtCore.Qt.MouseButton.MiddleButton:
            # if user has spacebar pressed and they press the middle button then
            # emit a new_roi_center so that scan params can be updated
            # if(self.inputState.keyisPressed[Qt.Key_F1]):
            #    self._emit_new_roi(self.image_type)
            #    return
            pass

    def mouseReleaseEvent(self, ev):
        """
        mouseReleaseEvent(): description

        :param ev: ev description
        :type ev: ev type

        :returns: None
        """
        # print 'ImageWidgetPlot: mouse released'
        pass
        # btn = ev.button()
        # self.inputState.btnisPressed[btn] = False
        #
        # if btn == QtCore.Qt.MouseButton.LeftButton:
        #     # print 'mouse release event'
        #     plot = self.get_plot()
        #     # get all the shapes and turn off their size texts
        #     active_item = plot.get_active_item()
        #     if(active_item != None):
        #         title = str(active_item.title().text())
        #         # print title
        #         if(hasattr(active_item, 'unique_id')):
        #
        #             if(title.find('ROI') > -1):
        #                 self.inputState.plotitem_type = types.spatial_type_prefix.ROI
        #                 ret = self._anno_spatial_to_region(active_item)
        #
        #             elif(title.find('SEG') > -1):
        #                 self.inputState.plotitem_type = types.spatial_type_prefix.SEG
        #                 ret = self._anno_seg_to_region(active_item)
        #
        #             elif(title.find('PNT') > -1):
        #                 self.inputState.plotitem_type = types.spatial_type_prefix.PNT
        #                 ret = self._anno_point_to_region(active_item)
        #             else:
        #                 # dont do anything
        #                 return
        #
        #             self.inputState.plotitem_id = active_item.unique_id
        #             self.inputState.plotitem_title = title
        #             self.inputState.center = ret['center']
        #             self.inputState.range = ret['range']
        #             self.inputState.rect = ret['rect']
        #             self.inputState.npts = (None, None)
        #             # , cmnd=widget_com_cmnd_types.ADD_ROI)
        #             self._emit_new_roi(
        #                 self.image_type, cmnd=widget_com_cmnd_types.SELECT_ROI)
        #     # print 'active_item: ', active_item
        #     items = self.plot.get_items(item_type=IShapeItemType)
        #     for item in items:
        #         #
        #         # if teh user has deselected this plot item then hide its label
        #         if(hasattr(item, "is_label_visible")):
        #             if item.is_label_visible() and (item != active_item):
        #                 item.set_label_visible(False)
        #                 item.unselect()
        #             elif item.is_label_visible() and (item == active_item):
        #                 item.set_label_visible(True)
        #             else:
        #                 pass
        #                 #item.position_and_size_visible = False
        #                 # pass
        #     self.plot.replot()
        #     return

    # note: these handlers are using Qt4.5 syntax, it changes in Qt4.8.3
    def mouseMoveEvent(self, ev):
        """
        mouseMoveEvent(): description

        :param ev: ev description
        :type ev: ev type

        :returns: None
        """
        # print 'mouseMoveEvent', ev
        btn = ev.button()
        # self.inputState.btnisPressed[btn]
        if btn == Qt.MidButton:
            # print 'ImageWidgetPlot: mouse moved with middle button pressed'
            return
        elif btn == QtCore.Qt.MouseButton.LeftButton:
            # print 'ImageWidgetPlot: mouse moved with left button pressed'
            # self.manager.update_cross_sections()
            pass

            return
        elif btn == QtCore.Qt.MouseButton.RightButton:
            # print 'ImageWidgetPlot: mouse moved with right button pressed'
            return

    def wheelEvent(self, event):
        """
        wheelEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        incr = 5
        do_emit = False
        delta = event.angleDelta().y()
        if delta > 0:
            dir = 1
        else:
            dir = -1

        (cx, cy) = self.inputState.center
        (rx, ry) = self.inputState.range
        (nx, ny) = self.inputState.npts

        if self.inputState.keyisPressed[Qt.Key_X]:
            nx = incr * dir
        #            do_emit = True
        else:
            nx = 0

        if self.inputState.keyisPressed[Qt.Key_Y]:
            ny = incr * dir
        #            do_emit = True
        else:
            ny = 0
        # print 'wheelEvent: nx,ny (%d, %d)' % (nx, ny)
        self.inputState.center = (cx, cy)
        self.inputState.range = (rx, ry)
        self.inputState.npts = (nx, ny)
        x1 = cx - (0.5 * rx)
        x2 = cx + (0.5 * rx)
        y1 = cy - (0.5 * ry)
        y2 = cy + (0.5 * ry)
        self.inputState.rect = (x1, y1, x2, y2)
        # dct = {}
        # dct['IMAGE_TYPE'] = self.image_type
        # dct[CENTER] = self.inputState.center
        # dct[RANGE] = self.inputState.range
        # dct[NPOINTS] = self.inputState.npts

        # only emit a new region if an x or y key == pressed
        if do_emit:
            # if(not self.inputStatekey.isPressed[Qt.Key_Alt]):
            # self.new_roi_center.emit(dct)
            self._emit_new_roi(self.image_type)

        # reset the delta points
        self.inputState.npts = (0, 0)

    def keyPressEvent(self, event):
        """
        keyPressEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        key = event.key()
        if event.isAutoRepeat():
            event.ignore()
            return
        if key == Qt.Key_Delete:
            item = self.plot.get_active_item()
            if item:
                # self.delPlotItem(item)
                self.delShapePlotItem(item)
                cur_shapes = self.getShapeItemsByShapeType(item)
                if (self.multi_region_enabled) or (len(cur_shapes) == 0):
                    if hasattr(item, "unique_id"):
                        # its a tool used to select a egion of interest
                        # if not then it == a different type of shapeItem that
                        # != used to select regions of interest so dont do anything with it
                        # self.enable_tools_by_shape_type(item, True)
                        self.enable_tools_by_shape_instance(item, True)
                        # it will only require a singal to any other widget listening if
                        # it was a region of interest (has a unique_id attrib)
                        self._emit_new_roi(None, cmnd=widget_com_cmnd_types.DEL_ROI)

        if key not in list(self.inputState.keyisPressed.keys()):
            _logger.debug(
                "keyPressedEvent: key [%d] not in self.inputState.keyisPressed.keys(), ignoring"
                % key
            )
            event.ignore()
            return

        self.inputState.keyisPressed[key] = True
        # print 'key pressed', self.inputState.keyisPressed

    #         if key == Qt.Key_Delete:
    #             item = self.plot.get_active_item()
    #             if item:
    #                 self.delPlotItem(item)
    #                print 'deleting %s'  % item.title().text()
    #                self.plot.del_item(item)
    #                self.plot.replot()
    #
    #        if key == QtCore.Qt.Key_Up:
    #            self.centerNode.moveBy(0, -20)
    #        elif key == QtCore.Qt.Key_Down:
    #            self.centerNode.moveBy(0, 20)
    #        elif key == QtCore.Qt.Key_Left:
    #            self.centerNode.moveBy(-20, 0)
    #        elif key == QtCore.Qt.Key_Right:
    #            self.centerNode.moveBy(20, 0)
    #        elif key == QtCore.Qt.Key_Plus:
    #            self.scaleView(1.2)
    #        elif key == QtCore.Qt.Key_Minus:
    #            self.scaleView(1 / 1.2)
    #        elif key == QtCore.Qt.Key_Space or key == QtCore.Qt.Key_Enter:
    #            for item in self.scene().items():
    #                if isinstance(item, Node):
    #                    item.setPos(-150 + QtCore.qrand() % 300, -150 + QtCore.qrand() % 300)
    #        else:
    #            super(GraphWidget, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """
        keyReleaseEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        key = event.key()
        if key == Qt.Key_C:
            self.selectTool.s.allow_parm_update = False

        if event.isAutoRepeat():
            event.ignore()
            return
        if key not in list(self.inputState.keyisPressed.keys()):
            event.ignore()
            return

        self.inputState.keyisPressed[key] = False
        # print 'key released', self.inputState.keyisPressed

    def addShapePlotItemCENTER(
        self, item_id, cntr, rng, item_type=types.spatial_type_prefix.ROI
    ):
        """
        addShapePlotItem(): description

        :param item_id: item_id description
        :type item_id: item_id type

        :param cntr: cntr description
        :type cntr: cntr type

        :param rng: rng description
        :type rng: rng type

        :param item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI description
        :type item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI type

        :returns: None
        """
        # make sure item == 'selected'
        startx = cntr[0] - (0.5 * rng[0])
        starty = cntr[1] - (0.5 * rng[1])
        item = self.getShapePlotItem(item_id, item_type)
        # create one
        if item_type == types.spatial_type_prefix.ROI:
            roi = types.spatial_type_prefix.ROI
            title = types.spatial_type_prefix[roi] + " %d" % item_id
            item = make.annotated_rectangle(
                startx, starty, startx + rng[0], starty + rng[1], title=title
            )
            item.shape_id = item_id
            item.unique_id = item_id
            # (item,a,b) = tools.clsAverageCrossSectionTool(self.plot.manager).create_shape()
            # item.shape_id = 0
            # item.unique_id = item_id

        elif item_type == types.spatial_type_prefix.SEG:
            seg = types.spatial_type_prefix.SEG
            title = types.spatial_type_prefix[seg] + " %d" % item_id
            item = make.annotated_horiz_segment(
                startx, starty, startx + rng[0], starty, title=item_id
            )
            # (item,a,b) = tools.HLineSegmentTool(self.plot.manager).create_shape()
            # item.shape_id = 0
            # item.unique_id = item_id

        else:
            # assume PNT type
            startx = cntr[0]
            starty = cntr[1]
            pnt = types.spatial_type_prefix.PNT
            title = types.spatial_type_prefix[pnt] + " %d" % item_id
            item = make.annotated_point(startx, starty, title=title)
            # (item,a,b) = tools.clsPointTool(self.plot.manager).create_shape()
            # item.shape_id = 0
            # item.unique_id = item_id

        # signal to anyone listening that we are adding this item
        # print 'addShapePlotItemCENTER: emitting_new_roi with cmnd=ADD_ROI'
        self._emit_new_roi(None, cntr, rng, None, cmnd=widget_com_cmnd_types.ADD_ROI)

        self.plot.add_item(item, z=999999999)
        item.invalidate_plot()
        self.plot.replot()

    def addShapePlotItem(
        self,
        item_id,
        rect,
        item_type=types.spatial_type_prefix.ROI,
        re_center=False,
        show_anno=True,
    ):
        """
        addShapePlotItem(): description

        :param item_id: item_id description
        :type item_id: item_id type

        :param rect: cntr description
        :type rect: tuple representing the corners of a rect (x1, y1, x2, y2)

        :param item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI description
        :type item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI type

        :returns: None
        """
        # make sure item == 'selected'
        (x1, y1, x2, y2) = rect

        # (x1, y1, x2, y2) = self._limit_rect(rect)

        # print 'addShapePlotItem: item_id = %d' % item_id
        # print 'addShapePlotItem: rect = ' , rect
        item = self.getShapePlotItem(item_id, item_type)
        # create one
        if item_type == types.spatial_type_prefix.ROI:
            roi = types.spatial_type_prefix.ROI
            self.roiNum += 1
            # title = types.spatial_type_prefix[roi] + ' %d' % self.roiNum
            title = types.spatial_type_prefix[roi] + " %d" % item_id
            if show_anno:
                item = make.annotated_rectangle(x1, y1, x2, y2, title=title)
            else:
                item = make.rectangle(x1, y1, x2, y2, title=title)
            item.shape_id = item_id
            item.unique_id = item_id
            item.max_range = (None, None)

        elif item_type == types.spatial_type_prefix.SEG:
            seg = types.spatial_type_prefix.SEG
            self.segNum += 1
            # title = types.spatial_type_prefix[seg] + ' %d' % self.segNum
            title = types.spatial_type_prefix[seg] + " %d" % item_id
            if show_anno:
                item = make.annotated_segment(x1, y1, x2, y2, title=title)
            else:
                item = make.segment(x1, y1, x2, y2, title=title)
            item.shape_id = item_id
            item.unique_id = item_id
            item.max_range = (None, None)

        else:
            # assume PNT type
            pnt = types.spatial_type_prefix.PNT
            self.pntNum += 1
            # title = types.spatial_type_prefix[pnt] + ' %d' % self.pntNum
            title = types.spatial_type_prefix[pnt] + " %d" % item_id
            if show_anno:
                item = make.annotated_point(x1, y1, title=title)
            else:
                item = make.point(x1, y1, title=title)
            item.set_pos(x1, y1)
            item.shape_id = item_id
            item.unique_id = item_id
            item.max_range = (None, None)

        self.plot.add_item(item, z=999999999)

        if re_center:
            if item_type == types.spatial_type_prefix.PNT:
                self.set_center_at_XY((x1, y1), (50, 50))
            else:
                self.set_center_at_XY(
                    ((x1 + x2) * 0.5, (y1 + y2) * 0.5), ((x2 - x1), (y1 - y2))
                )

        item.invalidate_plot()
        self.plot.replot()

    def recenter_plot_to_all_items(self):
        items = self.getShapeItems()

        x1_lst = []
        x2_lst = []
        y1_lst = []
        y2_lst = []
        xc = None
        yc = None
        for item in items:
            if isinstance(item, AnnotatedSegment):
                r = item.get_rect()
                xc = (r[0] + r[2]) * 0.5
                xr = r[2] - r[0]
                yc = (r[1] + r[3]) * 0.5
                yr = r[1] - r[3]
            elif isinstance(item, AnnotatedRectangle):
                xc, yc = item.get_tr_center()
                xr, yr = item.get_tr_size()

            elif isinstance(item, AnnotatedPoint):
                xc, yc = item.get_pos()
                xr = 0.0
                yr = 0.0
            # else:
            #    _logger.error('houston we have a problem')

            if (xc != None) and (yc != None):
                x1_lst.append(xc - (0.5 * xr))
                y1_lst.append(yc + (0.5 * yr))
                x2_lst.append(xc + (0.5 * xr))
                y2_lst.append(yc - (0.5 * yr))

        if not (x1_lst or y1_lst or x2_lst or y2_lst):
            # nothing to do
            return

        x1 = min(x1_lst)
        y1 = max(y1_lst)
        x2 = max(x2_lst)
        y2 = min(y2_lst)

        self.set_center_at_XY(
            ((x1 + x2) * 0.5, (y1 + y2) * 0.5), ((x2 - x1), (y1 - y2))
        )
        self.plot.replot()

    def resizeShapePlotItemCENTER(
        self, item_id, cntr, rng, item=None, item_type=types.spatial_type_prefix.ROI
    ):
        """
        resizeShapePlotItem(): description

        :param item_id: item_id description
        :type item_id: item_id type

        :param cntr: cntr description
        :type cntr: cntr type

        :param rng: rng description
        :type rng: rng type

        :param item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI description
        :type item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI type

        :returns: None
        """
        # make sure item == 'selected'
        startx = cntr[0] - (0.5 * rng[0])
        starty = cntr[1] - (0.5 * rng[1])
        if item == None:
            item = self.getShapePlotItem(item_id, item_type)

        self.plot.set_active_item(item)
        item.select()

        rect = self._restrict_rect_to_positive(QRectF())

        if item_type == types.spatial_type_prefix.ROI:
            item.set_rect(startx, starty, startx + rng[0], starty + rng[1])

        elif item_type == types.spatial_type_prefix.SEG:
            item.set_rect(startx, starty, startx + rng[0], starty)

        else:
            # assumne PNT type
            item.set_pos(startx, starty)

        item.invalidate_plot()
        self.plot.replot()

    def selectShapePlotItem(
        self, item_id, select=True, item=None, item_type=types.spatial_type_prefix.ROI
    ):
        """
        resizeShapePlotItem(): description

        :param item_id: item_id description
        :type item_id: item_id type

        :param item: shapePlotItem
        :type item:

        :param item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI description
        :type item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI type

        :returns: None
        """
        self.deselect_all_shapes()
        self.enable_all_shape_labels(False)

        if item == None:
            item = self.getShapePlotItem(item_id, item_type)

        if select:
            self.plot.set_active_item(item)
            item.select()
            if hasattr(item, "is_label_visible"):
                item.set_label_visible(True)
        else:
            self.plot.set_active_item(None)
            item.deselect()
            if hasattr(item, "is_label_visible"):
                item.set_label_visible(False)

    def set_shape_item_max_range(self, item, max_range):
        item.max_range = max_range

    def set_max_shape_sizes(self, max_size):
        self.max_shape_size = max_size

    def set_max_trimage_size(self, item_name, max_size):
        """
        for transformable image items set a maximum size so if the user sizes
        trimage largeer we can change the colormap to indicate the size violation
        """
        self._trimage_max_sizes[item_name] = max_size

    def set_enable_multi_region(self, enable=True):
        self.multi_region_enabled = enable

    def resizeShapePlotItem(
        self,
        item_id,
        rect,
        item=None,
        item_type=types.spatial_type_prefix.ROI,
        recenter=False,
    ):
        """
        resizeShapePlotItem(): description

        :param item_id: item_id description
        :type item_id: item_id type

        :param rect: cntr description
        :type rect: tuple representing the corners of a rect (x1, y1, x2, y2)

        :param rng: rng description
        :type rng: rng type

        :param item: item description
        :type item: item type

        :param item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI description
        :type item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI type

        :param recenter: a flag to have the plot recenter around the new shape size or not
        :type recenter: bool, default == False

        :returns: None
        """
        # make sure item == 'selected'
        (x1, y1, x2, y2) = rect
        rng = ((x2 - x1), (y1 - y2))
        # print 'resizeShapePlotItem: rect=', rect
        if item == None:
            item = self.getShapePlotItem(item_id, item_type)

        # limit size of item to the max range that has been set for it
        wd = x2 - x1
        ht = y2 - y1

        #         if(wd > item.max_range[0]):
        #             x2 = x1 + item.max_range[0]
        #
        #         if(ht > item.max_range[1]):
        #             y2 = y1 + item.max_range[1]

        if item_type == types.spatial_type_prefix.ROI:
            item.set_rect(x1, y1, x2, y2)

        elif item_type == types.spatial_type_prefix.SEG:
            item.set_rect(x1, y1, x2, y2)

        else:
            # assumne PNT type
            item.set_pos(x1, y1)
            rng = (5, 5)

        if recenter:
            self.set_center_at_XY(((x1 + x2) * 0.5, (y1 + y2) * 0.5), rng)

        item.invalidate_plot()
        self.plot.replot()
        # self.on_set_aspect_ratio()

    def getShapePlotItem(self, item_id, item_type=types.spatial_type_prefix.ROI):
        """
        getShapePlotItem(): description

        :param item_id: item_id description
        :type item_id: item_id type

        :param item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI description
        :type item_type=types.spatial_type_prefix.ROI: item_type=types.spatial_type_prefix.ROI type

        :returns: None
        """
        items = self.plot.get_items(item_type=IShapeItemType)
        for item in items:
            if item_type == types.spatial_type_prefix.ROI:
                if isinstance(item, AnnotatedRectangle):
                    title = str(item.title().text())
                    # print 'getShapePlotItem: Rect:', title
                    if item_id == item.unique_id:
                        # print 'getShapePlotItem: Point:', title
                        return item

            elif item_type == types.spatial_type_prefix.SEG:
                if isinstance(item, AnnotatedHorizontalSegment):
                    title = str(item.title().text())
                    # print 'getShapePlotItem: Segment:', title
                    if item_id == item.unique_id:
                        # print 'getShapePlotItem: Point:', title
                        return item
                if isinstance(item, AnnotatedSegment):
                    title = str(item.title().text())
                    # print 'getShapePlotItem: Segment:', title
                    if item_id == item.unique_id:
                        # print 'getShapePlotItem: Point:', title
                        return item

            elif item_type == types.spatial_type_prefix.PNT:
                if isinstance(item, AnnotatedPoint):
                    title = str(item.title().text())
                    if item_id == item.unique_id:
                        # print 'getShapePlotItem: Point:', title
                        return item

        return None

    def getShapeItems(self):
        """
        getShapeItems(): description

        :returns: a list of the current items
        """
        items = self.get_plot().get_items(item_type=IShapeItemType)
        return items

    def getShapeItemsByShapeType(self, shape_type=AnnotatedRectangle):
        """
        getShapeItemsByShapeType(): description

        :param shape_type: pass the type of shape you are looking for
        :type shape_type: a valid guiqwt ShapeItemType

        :returns: a list of the current items specified
        """
        items_lst = []

        items = self.get_plot().get_items(item_type=IShapeItemType)
        for item in items:
            # if(isinstance(shape_type, QtCore.pyqtWrapperType)):
            if isinstance(shape_type, type(QtCore.QObject)):

                if isinstance(item, shape_type):
                    items_lst.append(item)
            else:
                # it == an instance
                if isinstance(shape_type, type(item)):
                    items_lst.append(item)

        return items_lst

    def getShapeItemsByShapeInstance(self, shape_inst=None):
        """
        getShapeItemsByShapeInstance(): description

        :param shape_inst: pass the instance of shape you are looking for
        :type shape_inst: an instance of a valid guiqwt ShapeItem

        :returns: a list of the current items specified
        """
        items_lst = []

        items = self.get_plot().get_items(item_type=IShapeItemType)
        for item in items:
            if isinstance(shape_inst, type(item)):
                items_lst.append(item)

        return items_lst

    def get_shape_item_types(self, item):
        if isinstance(item, AnnotatedRectangle):
            return {
                "shape_type": AnnotatedRectangle,
                "spatial_type": types.spatial_type_prefix.ROI,
            }

        if isinstance(item, AnnotatedHorizontalSegment):
            return {
                "shape_type": AnnotatedHorizontalSegment,
                "spatial_type": types.spatial_type_prefix.SEG,
            }

        if isinstance(item, AnnotatedSegment):
            return {
                "shape_type": AnnotatedSegment,
                "spatial_type": types.spatial_type_prefix.SEG,
            }

        if isinstance(item, AnnotatedPoint):
            return {
                "shape_type": AnnotatedPoint,
                "spatial_type": types.spatial_type_prefix.PNT,
            }

    def delPlotItem(self, item, replot=True):
        """
        delPlotItem(): description

        :param item: item description
        :type item: item type

        :param replot=True: replot=True description
        :type replot=True: replot=True type

        :returns: None
        """
        # Don't delete the base image
        # if(item.title().text() != 'Image #1'):
        if not isinstance(item, ICSImageItemType):
            title = str(item.title().text())
            # print 'deleting %s'  % title
            self.region_deleted.emit(title)
            self.plot.del_item(item)
            # print 'deleteing [%s] with unique_id [%d]' % (str(item.title().text()), item.unique_id)
            # print 'id(item)=%d, unique=%d' % (id(item), item.unique_id)
            if hasattr(item, "_parent_tool"):
                item._parent_tool.re_init_unique_id()
            del item
            # signal to anyone listening that we are deleting this item
            # print 'delPlotItem: emitting_new_roi with cmnd=DEL_ROI'
            self._emit_new_roi(None, cmnd=widget_com_cmnd_types.DEL_ROI)

            if replot:
                self.plot.replot()

    def delImagePlotItems(self, clear_cached_data=False):
        """
        delImagePlotItems(): description

        :returns: None
        """
        items = self.plot.get_items(item_type=ICSImageItemType)
        for i, item in enumerate(items):
            self.plot.del_item(item)
            del item
            self.items[i] = None
            i += 1

        # delete histogram items
        cpnl = self.get_contrast_panel()
        for item in cpnl.histogram.get_items():
            # I get assertion errors passing HistogramItem directly to get_items()
            if isinstance(item, HistogramItem):
                cpnl.histogram.del_item(item)

        self.items = {}
        if clear_cached_data:
            self.data = {}
        self.plot.replot()

    def delShapePlotItems(self, exclude_rois=True):
        """
        delShapePlotItems(): description

        :returns: None
        """
        items = self.plot.get_items(item_type=IShapeItemType)
        for item in items:
            if exclude_rois:
                if hasattr(item, "title"):
                    if item.title().text().find(SPEC_ROI_PREFIX) == -1:
                        self.delShapePlotItem(item, replot=False)
            else:
                self.delShapePlotItem(item, replot=False)

        self.plot.replot()

    def delShapePlotItem(self, item, replot=True):
        """
        delShapePlotItem(): description

        :returns: None
        """
        dct = self.get_shape_item_types(item)

        if not isinstance(item, ImageItem):
            self.plot.del_item(item)
            del item

            if replot:
                self.plot.replot()

    def deactivate_tools(self):
        dct = self.toolclasses_to_dct()
        for toolstr in list(dct.keys()):
            tool = dct[toolstr]
            if hasattr(tool, "deactivate"):
                tool.deactivate()

    def set_image_parameters(self, item_name: str, xmin: float, ymin: float, xmax: float, ymax: float, item: IBasePlotItem = None):

        """
        set_image_parameters(): description

        Use this function to adjust the image parameters such that the x and y axis are
        within the xmin,xmax and ymin,ymax bounds, this == an easy way to display the image
        in microns as per the scan parameters, as well as the fact that if you have a scan with
        a non-square aspect ratio you can still display the scan as a square because the image will
        repeat pixels as necessary in either direction so that the image == displayed in teh min/max
        bounds you set here

        :param imageItem: a image plot item as returned from make.image()
        :type imageItem: a image plot item as returned from make.image()

        :param xmin: min x that the image will be displayed
        :type xmin: int

        :param ymin: max x that the image will be displayed
        :type ymin: int

        :param xmax: min y that the image will be displayed
        :type xmax: int

        :param ymax: max y that the image will be displayed
        :type ymax: int

        :returns:  None

        .. todo::
        there are man other image params that could be set in teh future, for now only implemented min/max
        ImageParam:
            Image title: Image
            Alpha channel: False
            Global alpha: 1.0
            Colormap: gist_gray
            Interpolation: None (nearest pixel)
            _formats:
              X-Axis: %.1f
              Y-Axis: %.1f
              Z-Axis: %.1f
            Background color: #000000
            _xdata:
              x|min: -
              x|max: -
            _ydata:
              y|min: -
              y|max: -

        """
        if not item:
            item = self.get_image_item(item_name)
        if not item:
            return
        iparam = ImageParam()
        iparam.colormap = item.get_color_map_name()
        iparam.xmin = xmin
        iparam.ymin = ymin
        iparam.xmax = xmax
        iparam.ymax = ymax

        self.zoom_rngx = float(xmax - xmin)
        self.zoom_rngy = float(ymax - ymin)

        axparam = ImageAxesParam()
        axparam.xmin = xmin
        axparam.ymin = ymin
        axparam.xmax = xmax
        axparam.ymax = ymax

        item.set_item_parameters({"ImageParam": iparam})
        item.set_item_parameters({"ImageAxesParam": axparam})

    def set_image_colormap(self, item=None, colormap="gist_gray", item_name=''):
        """
        set_image_colormap(): description

        Use this function to change the colormap of an image item

        :param imageItem: a image plot item as returned from make.image()
        :type imageItem: a image plot item as returned from make.image()

        :param colormap: string indicating a valid colomap name
        :type colormap: string


        :returns:  None

        .. todo::
        there are man other image params that could be set in teh future, for now only implemented min/max
        ImageParam:
            Image title: Image
            Alpha channel: False
            Global alpha: 1.0
            Colormap: gist_gray
            Interpolation: None (nearest pixel)
            _formats:
              X-Axis: %.1f
              Y-Axis: %.1f
              Z-Axis: %.1f
            Background color: #000000
            _xdata:
              x|min: -
              x|max: -
            _ydata:
              y|min: -
              y|max: -

        """
        if not item:
            item = self.get_image_item(item_name)
        if not item:
            return
        iparam = ImageParam()
        iparam.colormap = colormap #item.get_color_map_name()

        item.set_item_parameters({"ImageParam": iparam})

    def emit_image_and_rois(self, item_name=''):
        """
        added so that users can specify roi's and have their spectra plotted as images in a stack are taken
        """
        item = self.get_image_item(item_name)
        if not item:
            return
        #

    def reset_item_data(self, item_name=''):
        """
        if another image has started for this image name reset its data to Nans
        """
        item = self.get_image_item(item_name)
        if not item:
            return
        item.data.fill(np.NaN)



    def set_lock_aspect_ratio(self, val):
        """
        set_lock_aspect_ratio(): description

        :param val: val description
        :type val: val type

        :returns: None
        """
        self.plot.lock_aspect_ratio = bool(val)

    def get_current_data(self):
        return self.data

    def get_file_loading_progbar(self, max):
        """
        creates and returns a QProgressBar
        """

        progbar = QtWidgets.QProgressBar()
        progbar.setFixedWidth(300)
        progbar.setWindowTitle("generating a composite image")
        progbar.setAutoFillBackground(True)
        progbar.setMinimum(0)
        progbar.setMaximum(max)

        ss = """QProgressBar 
              {        
                        border: 5px solid rgb(100,100,100);
                        border-radius: 1 px;
                        text-align: center;
              }
            QProgressBar::chunk
             {
                         background-color:  rgb(114, 148, 240);
                          width: 20 px;
             }"""

        progbar.setStyleSheet(ss)
        return progbar

    @exception
    def openfile(
        self,
        fnames,
        scan_type=None,
        addimages=True,
        rotatable=False,
        flipud=False,
        dropped=False,
        alpha=1.0,
        use_current_plot_center=False,
        stack_index=0,
    ):
        """
        a function for opening/loading files
        fnames = lisdt of file names including full path
        scan_type=None,
        addimages= allow the addition of other images to plot
        rotatable=False,
        flipud= boolean to flip the data up and down
        dropped=boolean to indicate the is a dropped file
        alpha=1.0 a float value between 0.0 and 1.0 that controls the alpha channel indicating how transparent the image should be, 1.0 == full visible
        use_current_plot_center=False,
        """
        if self.show_image_params:
            self.openfile_mod(
                fnames,
                scan_type=scan_type,
                addimages=True,
                dropped=dropped,
                flipud=flipud,
                rotatable=rotatable,
                alpha=alpha,
                use_current_plot_center=use_current_plot_center,
                stack_index=stack_index,
            )
        elif len(fnames) == 1:
            if scan_type == None:
                scan_type = 0
            if (len(self.items) == 0) and (fnames[0].find(".png") > -1):
                # most likely calib camera
                self.openfile_mod(
                    fnames,
                    scan_type=scan_type,
                    addimages=True,
                    dropped=dropped,
                    flipud=flipud,
                    rotatable=rotatable,
                    alpha=alpha,
                    use_current_plot_center=use_current_plot_center,
                    stack_index=stack_index,
                )
            else:
                # most likely adding a VLM image to several data images
                # self.openfile_mod(fnames, scan_type=scan_type, addimages=True, counter='counter0', dropped=dropped)
                self.openfile_mod(
                    fnames,
                    scan_type=scan_type,
                    addimages=True,
                    dropped=dropped,
                    flipud=flipud,
                    rotatable=True,
                    alpha=0.6,
                    use_current_plot_center=True,
                    stack_index=stack_index,
                )
        else:
            num_fnames = len(fnames)
            self.progbar = self.get_file_loading_progbar(num_fnames)

            if num_fnames > 5:
                self.progbar.show()

            thpool_im_ldr = ThreadpoolImageLoader()
            thpool_im_ldr.load_image_items(
                fnames,
                result_fn=self.load_image_items,
                progress_fn=self.load_images_progress,
                thread_complete_fn=self.hide_progbar,
            )

    def load_images_progress(self, prog):
        self.progbar.setValue(prog)

    def load_image_items(self, items_lst):
        plot = self.get_plot()
        plot.setFocus()
        for item in items_lst:
            npts = item.data.shape
            rngx = item.bounds.size().width()
            rngy = item.bounds.size().height()
            items = self.plot.get_items(item_type=ICSImageItemType)
            # plot.add_item(item, z=len(items) + 1)
            z = self.calc_z_score(npts, (rngx, rngy))
            plot.add_item(item, z=z)

        # plot.replot()
        # self.set_autoscale()

    def hide_progbar(self):
        # print("imageWidget: threadpool image loader == done")
        self.progbar.hide()

    def calc_z_score(self, npts, rngs):
        """
        two tuples if the images number of points and ranges
        calc a score based on a priority of:
        higher npts == higher score
        smaller range == higher score
        :param npts:
        :param rngs:
        :return:
        """
        tpnts = npts[0] * npts[1]
        trngs = rngs[0] * rngs[1]
        if trngs < 0.01:
            trngs = 0.01
        score = float(tpnts / float(0.2 * trngs))
        # print('calc_z_score: %d = R(%.1f, %.1f) , P(%d, %d)' % (score, rngs[0], rngs[1], npts[0], npts[1]))
        return score


    def add_image_from_file(self, fname, alpha=0.4, rotatable=True, flipud=False, use_current_plot_center=False):
        """
        mainly used to load png and jpg files
        :param fname:
        :return:
        """
        from plotpy import io

        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        image = ImageParam()
        image.title = str(fname) # to_text_string(fname)
        image.data = io.imread(fname, to_grayscale=True)
        if flipud:
            data = np.flipud(image.data)
            image.data = data
        image.height, image.width = image.data.shape
        plot = self.get_plot()
        # add it to the top of the plot items (z=0)
        # plot.add_item(image, z=0)
        if use_current_plot_center:
            x1, x2, y1, y2 = plot.get_plot_limits()
            item = make.trimage(
                image.data, title=fprefix, x0=(x1 + x2)/2.0, y0=(y1 + y2)/2.0,
                alpha_function='constant', alpha=alpha, colormap="gist_gray"
            )

        else:
            item = make.trimage(
                image.data, title=fprefix,
                dx=0.1, dy=0.1, alpha_function='constant', alpha=alpha, colormap="gist_gray"
            )

        #reassign the trimage move_local_point_to to ours
        #item.move_local_point_to = move_local_point_to

        item.set_selectable(True)
        item.set_movable(True)
        item.set_resizable(True)
        item.set_rotatable(rotatable)
        # use the center of the last image added
        # if len(self.items) == 0:
        #     pass
        # elif len(self.items) > 1:
        #     item.boundingRect().moveCenter(self.items[-1].boundingRect().center())
        #     item.update_bounds()
        # else:
        #     item.boundingRect().moveCenter(self.items[0].boundingRect().center())
        #     item.update_bounds()

        if fprefix not in self.items.keys():
            plot.add_item(item, z=MAX_IMAGE_Z - 1)
            self.items[fprefix] = item
            self.data[fprefix] = item.data


    def openfile_mod(
            self,
            fnames,
            scan_type=None,
            addimages=True,
            dropped=False,
            alpha=0.4,
            flipud=False,
            rotatable=False,
            use_current_plot_center=False,
            stack_index=0,
    ):
        """
        openfile(): description

        :param fnames: a list of filenames
        :type fnames: list

        :param addimages=False: addimages=False description
        :type addimages=False: addimages=False type

        :returns: None
        """
        if scan_type == None:
            _logger.error("scan_type == None")
            return
        if scan_type not in types.image_type_scans:
            # only allow image type scan data to be dropped here
            return
        if stack_index is None:
            stack_index = 0

        num_files = len(fnames)
        idx = 0
        iidx = 0
        progbar = self.get_file_loading_progbar(num_files)
        force = True #force aspect ratio after load
        for fname in fnames:
            fname = str(fname)
            data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
            if data_dir == None:
                _logger.error("Problem with file [%s]" % fname)
                return

            if fsuffix.lower().find("jpg") > -1:
                # trying to load a jpg
                self.add_image_from_file(fname, alpha, flipud=flipud, rotatable=rotatable, use_current_plot_center=use_current_plot_center)
                force = False
                continue
            elif fsuffix.lower().find("png") > -1:
                # trying to load a png
                self.add_image_from_file(fname, alpha, flipud=flipud, rotatable=rotatable, use_current_plot_center=use_current_plot_center)
                force = False
                continue
            elif fsuffix.lower().find("gif") > -1:
                # trying to load a gif
                self.add_image_from_file(fname, alpha, flipud=flipud, rotatable=rotatable, use_current_plot_center=use_current_plot_center)
                force = False
                continue

            if not isinstance(self.data_io, DataIo):
                data_io = self.data_io(data_dir, fprefix)
            else:
                # we have been launched from a parent viewer
                self.data_io.update_data_dir(data_dir)
                self.data_io.update_file_prefix(fprefix)
                self.data_io.update_file_path(fname)
                data_io = self.data_io

            start_time = timeit.default_timer()

            entry_dct = data_io.load()
            # ekey = list(entry_dct.keys())[0]
            # support for older nexus files
            if entry_dct == None:
                return
            ekey = data_io.get_default_entry_key_from_entry(entry_dct)
            nx_datas = data_io.get_NXdatas_from_entry(entry_dct, ekey)
            sp_id = list(entry_dct[ekey]["WDG_COM"]["SPATIAL_ROIS"].keys())
            # scan_type = entry_dct[ekey]['WDG_COM']['SPATIAL_ROIS'][sp_id[0]]['SCAN_PLUGIN']['SCAN_TYPE']

            rng_x = entry_dct[ekey][WDG_COM][SPATIAL_ROIS][sp_id[0]]["X"][RANGE]
            rng_y = entry_dct[ekey][WDG_COM][SPATIAL_ROIS][sp_id[0]]["Y"][RANGE]
            npts_x = entry_dct[ekey][WDG_COM][SPATIAL_ROIS][sp_id[0]]["X"][NPOINTS]
            npts_y = entry_dct[ekey][WDG_COM][SPATIAL_ROIS][sp_id[0]]["Y"][NPOINTS]

            idx += 1
            iidx += 1
            progbar.setValue(iidx)
            elapsed = timeit.default_timer() - start_time
            # print 'elapsed time = ', elapsed

            if num_files > 5:
                if idx > 5:
                    # give the GUI something
                    QtWidgets.QApplication.processEvents()
                    idx = 0

            # Z is the depth of the image in terms of top down layers, the smaller the number the closer to the top
            # if overlaying multiple images
            item_z = self.calc_z_score((npts_x, npts_y), (rng_x, rng_y))

            if not (scan_type in types.acceptable_2dimages_list) and (num_files > 1):
                continue

            counter_name = data_io.get_default_detector_from_entry(entry_dct)
            data = data_io.get_signal_data_from_NXdata(nx_datas, counter_name)

            # while data.shape[0] in (0, 1) and data.ndim > 2:
            #     # cut out extraneous dims
            #     data = data[0]
            while data.shape[0] > 1 and data.ndim > 2:
                # cut out extraneous dims
                data = data[0]

            if data.ndim == 3:
                data = data[stack_index]

            if data.ndim != 2:
                msg = f"Data in file [{fname}] == of wrong dimension, == [{data.ndim}] should be [2]"
                _logger.error(msg)
                print(msg)
            elif np.all(np.isnan(data)):
                msg = f"Data in file [{fname}] == contains NaN data points"
                _logger.error(msg)
                print(msg)
            else:

                wdg_com = data_io.get_wdg_com_from_entry(entry_dct, ekey)
                if scan_type != types.scan_types.SAMPLE_LINE_SPECTRUM:
                    self.load_image_data(
                        fname,
                        wdg_com,
                        data,
                        addimages,
                        flipud=False,
                        name_lbl=False,
                        item_z=item_z,
                        show=False,
                        dropped=dropped,
                        stack_index=stack_index,
                    )
                else:
                    self.do_load_linespec_file(fname, wdg_com, data, dropped=True)

        progbar.hide()
        self.on_set_aspect_ratio(force)
        self.update_contrast()

    def do_load_linespec_file(self, fname, wdg_com, data, dropped=False):
        """
        This function loads all of the ev regions into a single image
        this call can come from a drop onto the plotter or called from the outside in response to a drop on the scan plugin

        :param fname:
        :param wdg_com:
        :param data:
        :param dropped:
        :return:
        """
        self.set_autoscale(fill_plot_window=True)
        self.set_fill_plot_window(True)
        self.delImagePlotItems()
        estart = None
        estop = None
        enpts = 0
        for sp_id in wdg_com[SPDB_SPATIAL_ROIS]:
            strt_stp = []
            spid_ev_rois = wdg_com[SPDB_SPATIAL_ROIS][sp_id][SPDB_EV_ROIS]
            fname = str(fname)
            data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
            img_idx = fprefix

            for eroi in spid_ev_rois:
                if estart == None:
                    estart = eroi[START]
                estop = eroi[STOP]
                enpts += eroi[NPOINTS]

        self.load_linespec_data(
            fname,
            wdg_com,
            data,
            item_z=0,
            dropped=dropped,
            img_idx=img_idx,
            estart=estart,
            estop=estop,
            enpts=enpts,
            show=True,
        )
        self.on_set_aspect_ratio(False, img_idx)
        _logger.info(
            "[%s] scan loaded"
            % dct_get(wdg_com[SPDB_SPATIAL_ROIS][sp_id], SPDB_SCAN_PLUGIN_SECTION_ID)
        )

    def sort_items_z(self, items):
        for item in items:
            # print item
            # old_item1_z, old_item2_z = item1.z(), item2.z()
            # item1.setZ(max([_it.z() for _it in self.itemss]) + 1)
            # item2.setZ(old_item1_z)
            # item1.setZ(old_item2_z)
            pass

    def load_image_data(
        self,
        fname,
        wdg_com,
        data,
        addimages=False,
        flipud=False,
        name_lbl=True,
        item_z=None,
        show=True,
        dropped=False,
        stack_index=0,
    ):
        """
        openfile(): This function loads a nxstxm hdf5 file, if it == a multi ev scan only the first image is
        used

        :param fname: fname description
        :type fname: fname type

        :param addimages=False: addimages=False description
        :type addimages=False: addimages=False type

        :returns: None
        """
        # default to img_idx = 0
        #img_idx = 0
        fname = str(fname)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        # img_idx needs to be unique if user is going to load multiple images.
        # append the stack number to avoid overwriting.
        img_idx = f"{fprefix}_{stack_index}"
        if data_dir is None:
            _logger.error("Problem with file [%s]" % fname)
            return

        plot = self.get_plot()
        plot.setFocus()
        if wdg_com is not None:
            sp_db = get_first_sp_db_from_wdg_com(wdg_com)
            # only display first energy [0]
            data = data.astype(np.float64)

            #data[data == 0.0] = np.nan
            # If a value == INIT values then set them to be nan so that they are not legit data
            data[data == DEFAULT_IMG_INIT_VAL] = np.nan

            self.data[img_idx] = data
            if self.data[img_idx].ndim == 3:
                self.data[img_idx] = self.data[img_idx][0]
            if flipud:
                _data = np.flipud(self.data[img_idx])
            else:
                _data = self.data[img_idx]

            self.data[img_idx] = _data
            _logger.info(
                "[%s] scan loaded" % dct_get(sp_db, SPDB_SCAN_PLUGIN_SECTION_ID)
            )

        self.image_type = dct_get(sp_db, SPDB_PLOT_IMAGE_TYPE)
        # if it == a focus image I dont want any of the tools screweing up the
        # scan params so disable them
        # if the image was dropped do NOT do anything with the tools
        if not dropped:
            if self.image_type in [types.image_types.FOCUS, types.image_types.OSAFOCUS]:
                self.enable_tools_by_spatial_type(None)
            else:
                self.enable_tools_by_spatial_type(dct_get(sp_db, SPDB_PLOT_SHAPE_TYPE))

        dct_put(sp_db, SPDB_PLOT_IMAGE_TYPE, self.image_type)
        if name_lbl:
            _title = str(fname)
            self.setWindowTitle(_title)
            plot.set_title("%s%s" % (fprefix, fsuffix))
        else:
            _title = str(img_idx)

        self.htSc = 1
        self.widthSc = 1

        if len(self.data) > 0:
            shape = self.data[img_idx].shape
            if len(shape) == 3:
                e, self.dataHeight, self.dataWidth = self.data[img_idx].shape
                self.data[img_idx] = self.data[img_idx][0]
            elif len(shape) == 2:
                self.dataHeight, self.dataWidth = self.data[img_idx].shape
            else:
                _logger.error("Not sure what kind of shape this is")
                return

            self.wPtr = 0
            self.hPtr = 0
            # if((not addimages) or (self.items[img_idx] == None)):
            #if (not addimages) or (img_idx not in self.items.keys()): # this breaks dropping a new image onto a viewer
            if not addimages:
                self.delImagePlotItems()
                self.items[img_idx] = make.image(
                    self.data[img_idx],
                    interpolation="nearest",
                    colormap="gist_gray",
                    title=_title,
                )
                plot = self.get_plot()
                plot.add_item(self.items[img_idx], z=0)

            elif img_idx not in self.items:
                self.items[img_idx] = make.image(
                    self.data[img_idx],
                    interpolation="nearest",
                    colormap="gist_gray",
                    title=_title,
                )
                items = self.plot.get_items(item_type=ICSImageItemType)
                plot.add_item(self.items[img_idx], z=len(items) + 1 if item_z is None else item_z)

            (x1, y1, x2, y2) = dct_get(sp_db, SPDB_RECT)
            # self.set_image_parameters(img_idx, self.items, x1, y1, x2, y2)
            self.set_image_parameters(img_idx, x1, y1, x2, y2)

            if show:
                self.show_data(img_idx, True)
                self.set_autoscale()

            dct_put(sp_db, SPDB_PLOT_KEY_PRESSED, self.inputState.keyisPressed)

            # wdg_com = dct_get(sp_db, ADO_CFG_WDG_COM)
            wdg_com[WDGCOM_CMND] = widget_com_cmnd_types.LOAD_SCAN
            sp_db[WDGCOM_CMND] = widget_com_cmnd_types.LOAD_SCAN

            if (
                dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)
                != types.scan_types.SAMPLE_POINT_SPECTRUM
            ):
                # self.on_set_aspect_ratio(True)
                pass

            if dropped:
                # enable signal emission earlier such that we
                # can update the scan param widgets.
                self.blockSignals(False)

            self.scan_loaded.emit(wdg_com)

            if self.show_image_params:
                self.display_image_params(fprefix, sp_db)
            else:
                self.report_image_params(fprefix, sp_db, img_idx=img_idx)

    def load_linespec_data(
        self,
        fname,
        wdg_com,
        data,
        addimages=True,
        flipud=False,
        name_lbl=False,
        item_z=None,
        show=False,
        dropped=False,
        img_idx=None,
        estart=None,
        estop=None,
        enpts=None,
    ):
        """
        openfile(): This function loads a nxstxm hdf5 file, if it == a multi ev scan only the first image is
        used

        :param fname: fname description
        :type fname: fname type

        :param addimages=False: addimages=False description
        :type addimages=False: addimages=False type

        :returns: None
        """
        #catch if user asked for several energy points but failed to give a proper range
        #if we dont handle this here the plotting innerds will throw a divide by zero exception eventually
        if estop == estart:
            estop = estart + 0.01

        fname = str(fname)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        if img_idx is None:
            img_idx = fprefix

        if data_dir == None:
            _logger.error("Problem with file [%s]" % fname)
            return

        plot = self.get_plot()
        plot.setFocus()
        if wdg_com != None:
            sp_db = get_first_sp_db_from_wdg_com(wdg_com)
            # only display first energy [0]
            data = data.astype(np.float32)
            # data[data==0.0] = np.nan
            self.data[img_idx] = data
            if self.data[img_idx].ndim == 3:
                self.data[img_idx] = self.data[img_idx][0]
            if flipud:
                _data = np.flipud(self.data[img_idx])
            else:
                _data = self.data[img_idx]

            self.data[img_idx] = _data

        self.image_type = dct_get(sp_db, SPDB_PLOT_IMAGE_TYPE)
        # if it == a focus image I dont want any of the tools screweing up the
        # scan params so disable them
        # if the image was dropped do NOT do anything with the tools
        if not dropped:
            self.enable_tools_by_spatial_type(dct_get(sp_db, SPDB_PLOT_SHAPE_TYPE))
        dct_put(sp_db, SPDB_PLOT_IMAGE_TYPE, self.image_type)

        if name_lbl:
            _title = str(fname)
            self.setWindowTitle(_title)
            plot.set_title("%s%s" % (fprefix, fsuffix))
        else:
            _title = None
        self.htSc = 1
        self.widthSc = 1

        if len(self.data) > 0:
            shape = self.data[img_idx].shape
            if len(shape) == 3:
                # [e, self.dataHeight, self.dataWidth] = self.data[img_idx].shape
                [e, self.dataHeight, self.dataWidth] = self.data[img_idx].shape
                self.data[img_idx] = self.data[img_idx][0]
            elif len(shape) == 2:
                [self.dataHeight, self.dataWidth] = self.data[img_idx].shape
            else:
                _logger.error("Not sure what kind of shape this is")
                return

            self.wPtr = 0
            self.hPtr = 0
            # if((not addimages) or (self.items[img_idx] == None)):
            if (not addimages) or (img_idx not in self.items):
                # self.delImagePlotItems()
                self.items[img_idx] = make.image(
                    self.data[img_idx],
                    interpolation="nearest",
                    colormap="gist_gray",
                    title=_title,
                )
                plot = self.get_plot()
                plot.add_item(self.items[img_idx], z=item_z)
            else:
                self.items[img_idx] = make.image(
                    self.data[img_idx],
                    interpolation="nearest",
                    colormap="gist_gray",
                    title=_title,
                )
                items = self.plot.get_items(item_type=ICSImageItemType)
                plot.add_item(self.items[img_idx], z=len(items) + 1 if item_z is None else item_z)

            (x1, y1, x2, y2) = dct_get(sp_db, SPDB_RECT)
            self.set_image_parameters(img_idx, x1, y1, x2, y2)

            if show:
                self.show_data(img_idx, True)
                self.set_autoscale()

            dct_put(sp_db, SPDB_PLOT_KEY_PRESSED, self.inputState.keyisPressed)

            # wdg_com = dct_get(sp_db, ADO_CFG_WDG_COM)
            wdg_com[WDGCOM_CMND] = widget_com_cmnd_types.LOAD_SCAN
            sp_db[WDGCOM_CMND] = widget_com_cmnd_types.LOAD_SCAN

            # self.scan_loaded.emit(wdg_com)
            #
            # if(self.show_image_params):
            #     self.display_image_params(fprefix, sp_db)
            # else:
            #     self.report_image_params(fprefix, sp_db)

    def display_image_params(self, fprefix, sp_db, name_lbl=True):
        param = ImageParam()
        if name_lbl:
            param.title = fprefix
        else:
            param.title = None
        endtime_str = dct_get(sp_db, "ACTIVE_DATA_OBJ.END_TIME")
        starttime_str = dct_get(sp_db, "ACTIVE_DATA_OBJ.START_TIME")
        elapsed = datetime_string_to_seconds(endtime_str) - datetime_string_to_seconds(
            starttime_str
        )
        param.scan_time = "%.2f sec" % elapsed
        height, width = self.data.shape

        param.scan_type = (
            types.scan_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)]
            + " "
            + types.scan_sub_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)]
        )
        param.energy = "%.2f eV" % sp_db[EV_ROIS][0][START]
        param.dwell = "%.2f ms" % sp_db[EV_ROIS][0][DWELL]
        param.npoints = "%d x %d" % (width, height)
        param.center = "(%.2f, %.2f) um" % (
            dct_get(sp_db, SPDB_XCENTER),
            dct_get(sp_db, SPDB_YCENTER),
        )
        param.rng = "(%.2f, %.2f) um" % (
            dct_get(sp_db, SPDB_XRANGE),
            dct_get(sp_db, SPDB_YRANGE),
        )

        # param.current =
        update_dataset(self.param_gbox.dataset, param)
        self.param_gbox.get()

    def report_image_params(self, fprefix, sp_db, img_idx):
        """
        print image parameters to the console
        """
        height, width = self.data[img_idx].shape

        s = fprefix
        s += (
            "  Scan Type: %s" % types.scan_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)]
            + " "
            + types.scan_sub_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)]
        )
        s += "  Energy: %.2f eV\n" % sp_db[EV_ROIS][0][START]
        s += "  Dwell: %.2f ms\n" % sp_db[EV_ROIS][0][DWELL]
        s += "  # Points: %d x %d \n" % (width, height)
        s += "  Center: (%.2f, %.2f) um\n" % (
            dct_get(sp_db, SPDB_XCENTER),
            dct_get(sp_db, SPDB_YCENTER),
        )
        s += "  Range: (%.2f, %.2f) um\n" % (
            dct_get(sp_db, SPDB_XRANGE),
            dct_get(sp_db, SPDB_YRANGE),
        )
        _logger.info(s)
        _logger.info("")

    def setZoomLimits(self):
        """
        setZoomLimits(): description

        :returns: None
        """
        if self.stxm_obj.image_obj:
            xaxis, yaxis = self.plot.get_active_axes()
            axis = self.plot.axisScaleDiv(xaxis)
            shape = self.stxm_obj.image_obj.rawData.shape
            xRange = (0, shape[0])
            yRange = (0, shape[1])
            # xMap = Qwt.QwtScaleMap(0, shape[0], *xRange)
            self.plot.setAxisScale(Qwt.QwtPlot.xBottom, *xRange)
            # yMap = Qwt.QwtScaleMap(0, shape[1], *yRange)
            self.plot.setAxisScale(Qwt.QwtPlot.yLeft, *yRange)
            self.plot.set_plot_limits(0, shape[0], 0, shape[1])

    def set_center_at_0(self, xRange, yRange):
        """
        set_center_at_0(): description

        :param xRange: xRange description
        :type xRange: xRange type

        :param yRange: yRange description
        :type yRange: yRange type

        :returns: None
        """
        """ given the ranges specified center the plot around 0
        """
        xRhalf = xRange / 2.0
        yRhalf = yRange / 2.0
        self.plot.set_plot_limits(-xRhalf, xRhalf, -yRhalf, yRhalf)

    def set_center_at_XY(self, center, rng, zoomout=0.35):
        """
        set_center_at_XY(): description

        :param center: center description
        :type center: center type

        :param rng: rng description
        :type rng: rng type

        :returns: None
        """
        """ given the center and range tuples specified center the plot around center
        """
        (cx, cy) = center
        (rx, ry) = rng

        if rx == 0.0:
            rx = 50
        if ry == 0.0:
            ry = 50
        bufferx = zoomout * rx
        buffery = zoomout * ry

        xstart = cx - (0.5 * rx) - bufferx
        xstop = cx + (0.5 * rx) + bufferx

        ystart = cy - (0.5 * ry) - buffery
        ystop = cy + (0.5 * ry) + buffery

        dx = xstop - xstart
        dy = ystop - ystart

        x0, x1, y0, y1 = self.plot.get_plot_limits()

        pdx = x1 - x0
        pdy = y1 - y0

        if pdx > pdy:
            # scale y
            dy = dy * (pdy / pdx)
            ystart = cy - (0.5 * dy)
            ystop = cy + (0.5 * dy)
        else:
            # scale x
            dx = dx * (pdx / pdy)
            xstart = cx - (0.5 * dx)
            xstop = cx + (0.5 * dx)

        self.plot.set_plot_limits(xstart, xstop, ystart, ystop)

    def setPlotAxisStrs(self, ystr=None, xstr=None):
        """
        setPlotAxisStrs(): description

        :param ystr=None: ystr=None description
        :type ystr=None: ystr=None type

        :param xstr=None: xstr=None description
        :type xstr=None: xstr=None type

        :returns: None
        """
        self.plot = self.get_plot()
        # set axis titles
        if ystr != None:
            self.plot.setAxisTitle(Qwt.QwtPlot.yLeft, ystr)
        if xstr != None:
            self.plot.setAxisTitle(Qwt.QwtPlot.xBottom, xstr)

        self.plot.setAxisTitle(Qwt.QwtPlot.xTop, "")
        self.plot.setAxisTitle(Qwt.QwtPlot.yRight, "")

        # self.plot.replot()

    def setXYStep(self, stxm_obj):
        """
        setXYStep(): description

        :param stxm_obj: stxm_obj description
        :type stxm_obj: stxm_obj type

        :returns: None
        """
        # convert to a 1/<> value as it == used to do the pixel to micron
        # conversion
        if self.stxm_obj.header["XStep"] == 0:
            self.stxm_obj.header["XStep"] = 1
        if self.stxm_obj.header["YStep"] == 0:
            self.stxm_obj.header["YStep"] = 1
        self.xstep = float(1.0 / self.stxm_obj.header["XStep"])
        self.ystep = float(1.0 / self.stxm_obj.header["YStep"])

    ############### TEST CODE ########################################
    def timerTestStop(self):
        """
        timerTestStop(): description

        :returns: None
        """
        self.tstTimer.stop()

    def determine_num_images(self, ev_npts_stpts_lst, num_spatial_pnts):
        """
        looking at the setpoints, determine how many images will be required dividing between the delta boundaries
        between the setpoints.
        ex: 3 images for the setpoints
            [1,2,3,4,5,10,15,20,25,30,31,32,33]
            [  first  |   second     |  third ]
        :return:
        """
        dct = {}
        num_images = len(ev_npts_stpts_lst)
        img_idx = 0
        l = []
        indiv_col_idx = []
        dct["num_images"] = num_images
        dct["map"] = {}
        dct["srtstop"] = {}
        ttl_npts = 0
        for npts, strt, stp in ev_npts_stpts_lst:
            # ttl_npts += npts
            ttl_npts += npts * num_spatial_pnts
            # arr = np.ones(npts, dtype=int)
            arr = np.ones(npts * num_spatial_pnts, dtype=int)
            arr *= img_idx
            l = l + list(arr)
            # indiv_col_idx = indiv_col_idx + list(range(0, npts))
            indiv_col_idx = indiv_col_idx + list(range(0, npts))
            dct["srtstop"][img_idx] = (strt, stp)
            img_idx += 1

        seq = np.array(list(range(0, ttl_npts)))
        dct["col_idxs"] = indiv_col_idx
        map_tpl = list(zip(seq, l))
        for i, img_idx in map_tpl:
            dct["map"][i] = img_idx

        # print(dct)
        return dct

    def install_beam_fbk_devs(self, main_obj):
        from cls.applications.pyStxm.widgets.beam_spot_fbk import BeamSpotFeedbackObj

        self.bmspot_fbk_obj = BeamSpotFeedbackObj(main_obj)
        self.bmspot_fbk_obj.new_beam_pos.connect(self.move_beam_spot)


def get_percentage_of_qrect(qrect, p):
    """
    take a qrect and return another qrect that == only a percentage of the passed in qrect. This
    == used mainly to produce warning qrects for a limit_def

    :param qrect: QRectF object
    :type qrect: QRectF

    :param p: The percentage of qrect to return, value == given as a decimal where 0.5 = %50
    :type p: double

    :returns: QRectF

    """
    (x1, y1, x2, y2) = qrect.getCoords()
    return QtCore.QRectF(QtCore.QPointF(x1 * p, y1 * p), QtCore.QPointF(x2 * p, y2 * p))


def make_default_stand_alone_stxm_imagewidget(
    parent=None, data_io=None, _type=None, bndg_rect=None
):
    # from cls.applications.pyStxm.widgets.beam_spot_fbk import BeamSpotFeedbackObjStandAlone
    # from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

    # def on_new_beamspot_fbk(cx, cy):
    #     '''
    #     the beam spot object has emitted a new center x/y so let the plotter know
    #     :param cx:
    #     :param cy:
    #     :return:
    #     '''
    #     global win
    #     print 'on_new_beamspot_fbk: (%.2f, %.2f)' % (cx, cy)
    #     win.move_beam_spot(cx, cy)
    from cls.utils.cfgparser import ConfigClass
    from cls.applications.pyStxm import abs_path_to_ini_file

    # appConfig = ConfigClass(abs_path_to_ini_file)
    # scan_mode = MAIN_OBJ.get_sample_scanning_mode_string()
    # sample_pos_mode = types.scanning_mode.get_value_by_name(scan_mode)
    sample_pos_mode = types.scanning_mode.get_value_by_name("GONI_ZONEPLATE")

    if data_io == None:
        from cls.data_io.stxm_data_io import STXMDataIo

        data_io = STXMDataIo

    # gridparam = make.gridparam(
    #     background=get_plot_bkrgnd_clr(), minor_enabled=(False, False), major_enabled=(False, False)
    # )
    gridparam = make.gridparam(
        minor_enabled=(False, False), major_enabled=(False, False)
    )

    # bmspot_fbk_obj = BeamSpotFeedbackObjStandAlone()
    # bmspot_fbk_obj.new_beam_pos.connect(on_new_beamspot_fbk)

    win = ImageWidgetPlot(
        parent=parent,
        filtStr=FILTER_STRING,
        type=_type,
        options=PlotOptions(
            gridparam=gridparam,
            show_contrast=True,
            show_xsection=True,
            show_ysection=True,
            show_itemlist=False,
            yreverse=False

        ),
    )
    # win = ImageWidgetPlot(
    #     parent=parent,
    #     filtStr=FILTER_STRING,
    #     type=_type,
    #     options=dict(gridparam=gridparam,
    #                  show_itemlist=False))

    win.set_enable_multi_region(False)
    win.enable_beam_spot(True)
    if bndg_rect == None:
        bounding_qrect = QRectF(QPointF(-1000, 1000), QPointF(1000, -1000))
    else:
        bounding_qrect = QRectF(
            QPointF(bndg_rect[0], bndg_rect[1]), QPointF(bndg_rect[2], bndg_rect[3])
        )

    warn_qrect = get_percentage_of_qrect(bounding_qrect, 0.90)  # %80 of max
    alarm_qrect = get_percentage_of_qrect(bounding_qrect, 0.95)  # %95 of max
    # normal_qrect = QtCore.QRectF(QtCore.QPointF(-400, 400), QtCore.QPointF(400, -400))
    normal_qrect = get_percentage_of_qrect(bounding_qrect, 0.40)

    bounding = ROILimitObj(
        bounding_qrect,
        get_alarm_clr(255),
        "Range == beyond Goniometer Capabilities",
        get_alarm_fill_pattern(),
    )
    normal = ROILimitObj(
        normal_qrect, get_normal_clr(45), "Fine ZP Scan", get_normal_fill_pattern()
    )
    warn = ROILimitObj(
        warn_qrect,
        get_warn_clr(65),
        "Goniometer will be required to move",
        get_warn_fill_pattern(),
    )
    alarm = ROILimitObj(
        alarm_qrect,
        get_alarm_clr(255),
        "Range == beyond ZP Capabilities",
        get_alarm_fill_pattern(),
    )

    limit_def = ROILimitDef(bounding, normal, warn, alarm)

    # win.set_shape_limits(types.spatial_type_prefix.PNT, limit_def)

    # win.clear_all_tools()
    win.setObjectName("lineByLineImageDataWidget")
    win.set_max_shape_sizes((100, 30))
    win.setCheckRegionEnabled(True)
    win.addTool("HelpTool")
    # win.addTool('SelectPointTool')

    # win.addTool('tools.StxmControlBeamTool')
    # win.enable_image_param_display(True)
    win.enable_tool_by_name("tools.clsOpenFileTool", True)
    win.addTool("tools.clsHorizMeasureTool")
    win.addTool("tools.clsMeasureTool")
    win.addTool("tools.clsPointTool")
    win.enable_tool_by_name("tools.clsSquareAspectRatioTool", True)
    win.enable_tool_by_name("tools.clsPointTool", True)

    win.addTool("DummySeparatorTool")
    win.register_samplehldr_tool(sample_pos_mode=sample_pos_mode)
    # win.register_samplehldr_tool()
    win.addTool("DummySeparatorTool")
    # win.addTool('ItemCenterTool')
    win.resize(600, 700)

    win.set_dataIO(data_io)
    # win.enable_tool('FreeFormTool')
    # win.resizeShapePlotItem('ROI 1', (200,200), (100,100), item_type='Rect')
    # win.resizeShapePlotItem('SEG 1', (400,400), (500,400), item_type='Segment')
    # win.resizeShapePlotItem('PNT 1', (600,600), (1,1), item_type='Point')

    return win


def make_default_stand_alone_stxm_imagewidget_openfile(fname, parent=None):
    win = make_default_stand_alone_stxm_imagewidget(parent)

    win.openfile(fname, addimages=True)
    return win


def make_flea_camera_widow():
    win = ImageWidgetPlot(
        parent=None,
        filtStr=FILTER_STRING,
        type=None,
        options=PlotOptions(
            show_contrast=False,
            show_xsection=False,
            show_ysection=False,
            show_itemlist=False,
        ),
    )
    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    win.enable_grab_btn()
    win.enable_tool_by_name("tools.clsOpenFileTool", True)
    win.resize(900, 900)
    return win


def make_camera_widow(obj_name=""):
    win = ImageWidgetPlot(
        parent=None,
        filtStr=FILTER_STRING,
        type=None,
        options=PlotOptions(
            show_contrast=True,
            show_xsection=False,
            show_ysection=False,
            show_itemlist=False,
        ),
    )
    win.setStyleSheet(None)
    cpnl = win.get_contrast_panel()
    cpnl.setStyleSheet(None)
    win.setObjectName(obj_name)
    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    #win.enable_tool_by_name("tools.clsOpenFileTool", True)
    #win.resize(900, 900)
    return win

def make_ptycho_camera_widow(obj_name=""):
    win = ImageWidgetPlot(
        parent=None,
        filtStr=FILTER_STRING,
        type="ptycho_camera",
        options=PlotOptions(
            show_contrast=True,
            show_xsection=False,
            show_ysection=False,
            show_itemlist=False,
        ),
    )
    win.setStyleSheet(None)
    cpnl = win.get_contrast_panel()
    cpnl.setStyleSheet(None)
    win.setObjectName(obj_name)
    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    #win.enable_tool_by_name("tools.clsOpenFileTool", True)
    #win.resize(900, 900)
    return win
def make_uhvstxm_distance_verification_window():
    win = ImageWidgetPlot(
        parent=None,
        filtStr=FILTER_STRING,
        type=None,
        options=PlotOptions(
            show_contrast=False,
            show_xsection=False,
            show_ysection=False,
            show_itemlist=False,
        ),
    )
    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    win.enable_grab_btn()
    win.enable_tool_by_name("tools.clsOpenFileTool", False)
    win.addTool("tools.clsMultiLineTool")
    win.resize(900, 900)
    return win


def make_pystxm_window():
    from cls.data_io.stxm_data_io import STXMDataIo

    fg_clr = master_colors["plot_forgrnd"]["rgb_hex"]
    bg_clr = master_colors["plot_bckgrnd"]["rgb_hex"]
    min_clr = master_colors["plot_gridmaj"]["rgb_hex"]
    maj_clr = master_colors["plot_gridmin"]["rgb_hex"]

    win = ImageWidgetPlot(
        parent=None,
        filtStr=FILTER_STRING,
        type=None,
        options=PlotOptions(
            lock_aspect_ratio=True,
            show_contrast=True,
            show_xsection=True,
            show_ysection=True,
            xlabel=("microns", ""),
            ylabel=("microns", ""),
            colormap="gist_gray",
        ),
    )
    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    win.enable_grab_btn()
    win.enable_tool_by_name("tools.clsOpenFileTool", False)
    win.addTool("tools.clsMultiLineTool")
    win.setObjectName("lineByLineImageDataWidget")
    win.set_dataIO(STXMDataIo)
    win.resize(900, 900)
    return win


def make_tst_pattern_gen_window():
    from cls.data_io.stxm_data_io import STXMDataIo

    fg_clr = master_colors["plot_forgrnd"]["rgb_hex"]
    bg_clr = master_colors["plot_bckgrnd"]["rgb_hex"]
    min_clr = master_colors["plot_gridmaj"]["rgb_hex"]
    maj_clr = master_colors["plot_gridmin"]["rgb_hex"]
    
    win = ImageWidgetPlot(
        parent=None,
        filtStr=FILTER_STRING,
        type=None,
        options=PlotOptions(
            lock_aspect_ratio=True,
            show_contrast=True,
            show_xsection=True,
            show_ysection=True,
            xlabel=("microns", ""),
            ylabel=("microns", ""),
            colormap="gist_gray",
        ),
    )
    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    win.enable_grab_btn()
    win.enable_tool_by_name("tools.clsOpenFileTool", False)
    win.addTool("tools.clsMultiLineTool")
    win.setObjectName("lineByLineImageDataWidget")
    win.set_dataIO(STXMDataIo)
    win.resize(900, 900)
    return win


class qobj_OBJ(QObject):
    new_beam_pos = pyqtSignal(float, float)

    def __init__(self):
        QObject.__init__(self)
        from bcm.devices import MotorQt as apsMotor

        self.zx = apsMotor("IOC:m102", name="zoneplateX")
        self.zy = apsMotor("IOC:m103", name="zoneplateY")
        self.gx = apsMotor("IOC:m107", name="goniX")
        self.gy = apsMotor("IOC:m108", name="goniX")
        self.zx.add_callback("RBV", self.on_mtr_fbk_changed)

    def on_mtr_fbk_changed(self, **kwargs):

        zxpos = self.zx.get_position()
        zypos = self.zy.get_position()
        gxpos = self.gx.get_position()
        gypos = self.gy.get_position()
        x = zxpos + gxpos
        y = zypos + gypos
        self.new_beam_pos.emit(x, y)


def tst_pattern_gen(win):
    from cls.utils.roi_utils import get_base_roi

    # print 'on_scanpluggin_roi_changed: rect=' , (rect)
    centers = [0.5, 2.5, 4.5]
    item_idx = 0
    ltr_lst = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
    ltr_lst.reverse()
    rois_dct = {}
    main_rect = None
    for x_center in centers:
        for y_center in centers:
            letter = ltr_lst.pop()
            x_roi = get_base_roi(
                "pattrn_%sx" % letter,
                "",
                x_center,
                1.0,
                10,
                enable=True,
                is_point=False,
                src=None,
            )
            y_roi = get_base_roi(
                "pattrn_%sy" % letter,
                "",
                y_center,
                1.0,
                10,
                enable=True,
                is_point=False,
                src=None,
            )

            x1 = float(x_roi["START"])
            y1 = float(y_roi["START"])
            x2 = float(x_roi["STOP"])
            y2 = float(y_roi["STOP"])

            # print 'on_scanpluggin_roi_changed: item_id = %d' % item_id

            rect = (x1, y1, x2, y2)

            # win.addShapePlotItem(item_idx, rect, show_anno=False)
            # if(item_idx == 4):
            #     #the middle one, will be the one that == selected
            #     title = 'patternrect'
            #     print('patternrect', rect)
            # else:
            title = "pattern"
            #     create_rectangle(rect, title='pattern', plot=win.plot, annotated=True)
            # else:
            #     create_rectangle(rect, title='pattern', plot=win.plot, annotated=False)
            create_rectangle(rect, title=title, plot=win.plot, annotated=False)
            qrect = QtCore.QRectF(
                QtCore.QPointF(rect[0], rect[2]), QtCore.QPointF(rect[3], rect[1])
            )

            if main_rect == None:
                main_rect = qrect
            else:
                main_rect = main_rect.united(qrect)
            item_idx += 1
            rois_dct[letter] = {"X": x_roi, "Y": y_roi}

    shape, z = create_rectangle(
        main_rect.getRect(),
        title="pattern",
        plot=win.plot,
        annotated=True,
        alpha=0.01,
        l_style="DashLine",
        l_clr="#645d03",
    )
    shape.unique_id = get_unique_roi_id()

    return rois_dct


def go():
    from cls.utils.roi_utils import on_centerxy_changed

    def on_new_selected_position(x, y):
        print(f"on_new_selected_position({x},{y})")

    ss = get_style()
    app = guidata.qapplication()
    sys.excepthook = excepthook

    # qobj = qobj_OBJ()

    # win = make_default_stand_alone_stxm_imagewidget()
    # win = make_default_stand_alone_stxm_imagewidget(_type='analyze')
    # (-1000, 1000), QPointF(1000, -1000)
    bndg_rect = (-5.0, 10.0, 10.0, -5.0)
    win = make_default_stand_alone_stxm_imagewidget(bndg_rect=bndg_rect)
    win.addTool("tools.clsSelectPositionTool")
    win.addTool("tools.clsCrossHairSelectPositionTool")
    win.new_selected_position.connect(on_new_selected_position)
    # win.create_beam_spot(0.0, 0.0, size=0.35)

    def on_new_roi_center(wdg_com):
        # print wdg_com.keys()
        # print wdg_com['SPATIAL_IDS']
        # print wdg_com['RECT']
        print("on_new_roi_center", wdg_com["X"][CENTER], wdg_com["Y"][CENTER])

    def select_pattern(img_plot):
        main_rect = img_plot.select_main_rect_of_shape("pattern")

    def assign_centers(dct, cntrs):
        dct["X"]["CENTER"] = cntrs[0]
        dct["Y"]["CENTER"] = cntrs[1]
        on_centerxy_changed(dct["X"])
        on_centerxy_changed(dct["Y"])

    def on_target_moved(Ex, Ey):
        # Ex = main_rect.center().x()
        # Ey = main_rect.center().y()

        # row 1
        Ac = (Ex - 2.0, Ey - 2.0)
        Bc = (Ex, Ey - 2.0)
        Cc = (Ex + 2.0, Ey - 2.0)
        # row 2
        Dc = (Ex - 2.0, Ey)
        # Ec
        Fc = (Ex + 2.0, Ey)
        # row 3
        Gc = (Ex, Ey + 2.0)
        Hc = (Ex, Ey + 2.0)
        Ic = (Ex + 2.0, Ey + 2.0)

        assign_centers(rois_dct["A"], Ac)
        assign_centers(rois_dct["B"], Bc)
        assign_centers(rois_dct["C"], Cc)
        assign_centers(rois_dct["D"], Dc)
        assign_centers(rois_dct["F"], Fc)
        assign_centers(rois_dct["G"], Gc)
        assign_centers(rois_dct["H"], Hc)
        assign_centers(rois_dct["I"], Ic)

        # print('cntr:', (Ex, Ey))
        # print('A center: (%.4f, %.4f)' % (rois_dct['A']['X']['CENTER'], rois_dct['A']['Y']['CENTER']))
        # print('I center: (%.4f, %.4f)' % (rois_dct['I']['X']['CENTER'], rois_dct['I']['Y']['CENTER']))
        # print('A setpoints: ' , rois_dct['A']['X']['SETPOINTS'])

    def on_new_roi(object):
        on_target_moved(object["X"]["CENTER"], object["Y"]["CENTER"])

    # win.set_data_dir(r'S:\STXM-data\Cryo-STXM\2017\guest\0201')
    win.set_data_dir(r"S:\STXM-data\Cryo-STXM\2017\guest\0922")

    win.register_osa_and_samplehldr_tool(
        sample_pos_mode=types.sample_positioning_modes.GONIOMETER
    )
    #win.setStyleSheet(ss)
    win.show()
    # win = make_flea_camera_widow()
    # win = make_uhvstxm_distance_verification_window()
    # win.new_roi_center.connect(on_new_roi_center)
    # win.enable_image_param_display(True)

    # win.show()
    upd_styleBtn = QtWidgets.QPushButton("Update Style")
    activate_selposBtn = QtWidgets.QPushButton("Activate Slect position tool")
    activate_selposBtn.setCheckable(True)
    vbox = QtWidgets.QVBoxLayout()
    vbox.addWidget(upd_styleBtn)
    vbox.addWidget(activate_selposBtn)
    upd_styleBtn.clicked.connect(win.update_style)
    activate_selposBtn.clicked.connect(win.activate_sel_horizontal_pos_tool)
    win.layout().addLayout(vbox)
    # tsting beam spot feedback
    # win.move_beam_spot(5, 10)
    win.enable_menu_action("Clear Plot", True)

    win.register_shape_info(
        shape_info_dct={"shape_title": "pattern", "on_selected": select_pattern}
    )

    win.target_moved.connect(on_target_moved)
    win.new_roi_center.connect(on_new_roi)

    rois_dct = tst_pattern_gen(win)
    app.exec_()

def astxm_lineplot_test():
    from cls.utils.roi_utils import on_centerxy_changed

    ss = get_style()
    app = guidata.qapplication()
    sys.excepthook = excepthook

    bndg_rect = (-5.0, 10.0, 10.0, -5.0)
    win = make_default_stand_alone_stxm_imagewidget(bndg_rect=bndg_rect)


    # win.set_data_dir(r'S:\STXM-data\Cryo-STXM\2017\guest\0201')
    win.set_data_dir(r"S:\STXM-data\Cryo-STXM\2017\guest\0922")

    win.register_osa_and_samplehldr_tool(
        sample_pos_mode=types.sample_positioning_modes.GONIOMETER
    )
    win.setStyleSheet(ss)
    win.show()

    win.initData(0,0, 5,5)
    arr = np.array([[21.0,22.0,23.0,24.0,25.0],[26.0,27.0,28.0,29.0,30.0],[31.0,32.0,33.,34.,35.],[36.,37.,38.,39.,40.],[41.,42.,43.,44.,45.]])
    win.addLine(0, 0, arr[0,:], True)
    win.addLine(0, 1, arr[1, :], True)
    win.addLine(0, 2, arr[2, :], True)
    win.addLine(0, 3, arr[3, :], True)
    win.addLine(0, 4, arr[4, :], True)
    # win.show()
    win.enable_menu_action("Clear Plot", True)

    app.exec_()

def make_sig_selection():
    app = guidata.qapplication()
    bndg_rect = (-5.0, 10.0, 10.0, -5.0)
    win = make_default_stand_alone_stxm_imagewidget(bndg_rect=bndg_rect)
    win.addTool("tools.clsSignalSelectTool")
    win.setObjectName("lineByLineImageDataWidget")

    det_nm_lst =['A','B','C','D','E']
    a_data = np.ones((150,150))
    b_data = np.random.randint(0, 255, size=(150, 150))
    c_data = np.random.randint(0, 255, size=(150, 150))
    d_data = np.random.randint(0, 255, size=(150, 150))
    e_data = np.random.randint(0, 255, size=(150, 150))

    win.init_image_items(det_nm_lst, 0, 150, 150, parms={})
    win.set_selected_detectors(det_nm_lst=det_nm_lst)


    for row in range(150):
        data = a_data[row:row+1] * row
        win.addLine('B', row, data, True)
        win.addLine('C', row, b_data[row:row+1], True)
        win.addLine('D', row, d_data[row:row + 1], True)
        win.addLine('E', row, e_data[row:row + 1], True)

    win.set_dataIO(STXMDataIo)
    win.update_style()
    win.resize(900, 900)
    win.show()
    app.exec_()

def make_style_test():

    def load_array(win):

        from epics import PV

        cam_wv = PV("CCD1610-I10:uhv:calib_cam:wv:fbk")
        data = cam_wv.get()
        data = data.reshape((480, 640))
        data = np.flipud(data)
        image = make.image(data, interpolation="nearest", colormap="gist_gray",)
        plot = win.get_plot()
        plot.add_item(image)
        plot.update()

    def set_grid_parameters(self, bkgrnd_color, min_color, maj_color):
        aplot = self.plot
        gparam = GridParam()
        gparam.background = bkgrnd_color
        gparam.maj_line.color = maj_color
        gparam.min_line.color = min_color
        aplot.grid.set_item_parameters({"GridParam": gparam})

        # QMouseEvent  event(QEvent.MouseButtonPress, pos, 0, 0, 0);
        # QApplication.sendEvent(mainWindow, & event);

        aplot.ensurePolished()
        # QtWidgets.QApplication.sendPostedEvents(aplot, QtCore.QEvent.PolishRequest)
        # aplot.polish()
        aplot.invalidate()
        aplot.replot()
        aplot.update_all_axes_styles()
        aplot.update()

    def set_cs_grid_parameters(self, forgrnd_color, bkgrnd_color, min_color, maj_color):

        plot = self.plot
        xcs = self.get_xcs_panel()
        ycs = self.get_ycs_panel()
        xcs.cs_plot.label.hide()
        ycs.cs_plot.label.hide()

        # self.curve_item.update_params()
        cs_items = xcs.cs_plot.get_items()
        # csi = xcs.cs_plot.get_items(item_type=XCrossSectionItem)
        if len(cs_items) == 3:
            csi = cs_items[2]
            cparam = csi.curveparam
            # cparam = CurveParam()
            cparam.line._color = forgrnd_color
            cparam._shade = 0.75
            xcs.cs_plot.set_item_parameters({"CurveParam": cparam})

        # csi = xcs.cs_plot.get_items(item_type=ICurveItemType)
        # print csi

        # csi.curveparam._shade = 0.75

        # cparam = CurveParam()
        # cparam.line._color = forgrnd_color
        # cparam._shade = 0.75

        # xcs.cs_plot.set_item_parameters({"CurveParam":cparam})
        # ycs.cs_plot.set_item_parameters({"CurveParam":cparam})

        gparam = GridParam()
        gparam.background = bkgrnd_color
        gparam.maj_line.color = maj_color
        gparam.min_line.color = min_color
        xcs.cs_plot.grid.set_item_parameters({"GridParam": gparam})
        ycs.cs_plot.grid.set_item_parameters({"GridParam": gparam})

        xcs.cs_plot.ensurePolished()
        ycs.cs_plot.ensurePolished()

        # xcs.cs_plot.polish()
        # ycs.cs_plot.polish()

        xcs.cs_plot.invalidate()
        ycs.cs_plot.invalidate()

        xcs.cs_plot.replot()
        ycs.cs_plot.replot()

        xcs.cs_plot.update_all_axes_styles()
        ycs.cs_plot.update_all_axes_styles()

        xcs.cs_plot.update()
        ycs.cs_plot.update()

    app = guidata.qapplication()

    main_wdg = uic.loadUi("C:/controls/sandbox/branches/200/pyStxm3/cls/plotWidgets/ui/style_test.ui")
    bndg_rect = (-5.0, 10.0, 10.0, -5.0)
    win = make_default_stand_alone_stxm_imagewidget(bndg_rect=bndg_rect)
    win.addTool("tools.clsSignalSelectTool")
    win.setObjectName("lineByLineImageDataWidget")
    main_wdg.acquireBtn.clicked.connect(lambda arr: load_array(win))
    det_nm_lst =['A','B','C','D','E']
    a_data = np.ones((150,150))
    b_data = np.random.randint(0, 255, size=(150, 150))
    c_data = np.random.randint(0, 255, size=(150, 150))
    d_data = np.random.randint(0, 255, size=(150, 150))
    e_data = np.random.randint(0, 255, size=(150, 150))

    win.init_image_items(det_nm_lst, 0, 150, 150, parms={})
    win.set_selected_detectors(det_nm_lst=det_nm_lst)


    for row in range(150):
        data = a_data[row:row+1] * row
        win.addLine('B', row, data, True)
        win.addLine('C', row, b_data[row:row+1], True)
        win.addLine('D', row, d_data[row:row + 1], True)
        win.addLine('E', row, e_data[row:row + 1], True)

    win.set_dataIO(STXMDataIo)
    vbox = QtWidgets.QVBoxLayout()
    upd_styleBtn = QtWidgets.QPushButton("Update Style")
    upd_styleBtn.clicked.connect(win.update_style)
    vbox.addWidget(win)
    vbox.addWidget(upd_styleBtn)
    main_wdg.camFrame.setLayout(vbox)

    #def set_grid_colors(self):
    fg_clr = master_colors["plot_forgrnd"]["rgb_str"]
    bg_clr = master_colors["plot_bckgrnd"]["rgb_str"]
    min_clr = master_colors["plot_gridmaj"]["rgb_str"]
    maj_clr = master_colors["plot_gridmin"]["rgb_str"]

    # self.set_grid_parameters("#323232", "#343442", "#545454")
    # self.set_grid_parameters("#7d7d7d", "#343442", "#545454")
    # self.set_grid_parameters(bg_clr, min_clr, maj_clr)
    # self.set_cs_grid_parameters(fg_clr, bg_clr, min_clr, maj_clr)

    set_grid_parameters(win, bg_clr, min_clr, maj_clr)
    set_cs_grid_parameters(win, fg_clr, bg_clr, min_clr, maj_clr)

    ss = get_style()
    main_wdg.setStyleSheet(ss)
    #main_wdg.update_style()
    main_wdg.resize(900, 900)
    main_wdg.show()
    app.exec_()



if __name__ == "__main__":
    """"""
    # -- Create QApplication
    import guidata
    from PyQt5 import QtWidgets
    from cls.stylesheets import get_style
    from bcm.devices import MotorQt as apsMotor
    from PyQt5.QtCore import pyqtSignal, QObject
    from cls.utils.profiling import determine_profile_bias_val, profile_it

    # profile_it('go', bias_val=7.40181638985e-07)
    # go()
    #astxm_lineplot_test()
    #make_sig_selection()
    make_style_test()

