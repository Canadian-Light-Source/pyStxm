import os
import sys
import numpy as np
import qwt as Qwt
import simplejson as json

from plotpy.builder import make
from plotpy.config import _
from plotpy.items.curve import CurveItem
from plotpy.items.grid import GridItem
from plotpy.plot import PlotDialog, PlotOptions
from plotpy.styles import COLORS, GridParam, ItemParameters
from plotpy.tools import *
from PyQt5 import Qt, QtCore, QtGui, QtWidgets

import cls.types.stxmTypes as types
from cls.plotWidgets import tools
from cls.plotWidgets.curve_object import curve_Obj
from cls.plotWidgets.utils import gen_complete_spec_chan_name
from cls.stylesheets import color_str_as_hex, get_style, is_style_light, master_colors
from cls.utils.fileUtils import get_file_path_as_parts
from cls.utils.roi_utils import make_base_wdg_com, widget_com_cmnd_types
from cls.utils.dict_utils import dct_get, dct_put
import cls.utils.roi_dict_defs as roi_dict_defs
from cls.utils.log import get_module_logger

# setup module logger with a default do-nothing handler
_logger = get_module_logger(__name__)

uiDir = r"./"
icoDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icons")

# print 'uiDir = %s' % uiDir

import copy

color_list = {}
# supply colors in the order I want them
clr_keys = ["b", "y", "r", "g", "c", "m", "k", "w", "G"]
for key in clr_keys:
    color_list[key] = {
        "clr": COLORS[key] if key != "b" else master_colors["app_ltblue"]["rgb_hex"],  # override blue
        "used": key == "k",  # ensure black is never selected for plotting
    }


def get_next_color(use_dflt=True):
    global color_list
    dflt_clr = "#6063ff"
    if use_dflt:
        return dflt_clr

    for k in list(color_list.keys()):
        if not color_list[k]["used"]:
            color_list[k]["used"] = True
            return color_list[k]["clr"]

    return dflt_clr

def get_color_by_idx(i):
    assert i < len(clr_keys), f"Index {i} is out of range for clr_keys with length {len(clr_keys)}"
    return color_list[clr_keys[i]]["clr"]

def reset_color_idx():
    global color_list
    for key in list(color_list.keys()):
        color_list[key]["used"] = False
    # don't use black
    color_list["k"]["used"] = True


def dump_curve_styles():
    """
    Curve styles [0] = Lines
    Curve styles [1] = Sticks
    Curve styles [2] = Steps
    Curve styles [3] = Dots
    Curve styles [4] = NoCurve
    """
    from plotpy.styles.base import CURVESTYLE_CHOICES

    i = 0
    for s in CURVESTYLE_CHOICES:
        print("Curve styles [%d] = %s" % (i, s[0]))
        i += 1


# def dump_curve_types():
#     """
#     Curve Types[0] = "Yfx"     ("Draws y as a function of x")
#     Curve Types[1] = "Xfy"     ("Draws x as a function of y")
#
#     """
#     from plotpy.styles.base import CURVETYPE_CHOICES
#
#     i = 0
#     for s in CURVETYPE_CHOICES:
#         print("Curve types [%d] = %s" % (i, s[0]))
#         i += 1


def dump_line_styles():
    """
    Line styles [0] = SolidLine
    Line styles [1] = DashLine
    Line styles [2] = DotLine
    Line styles [3] = DashDotLine
    Line styles [4] = DashDotDotLine
    Line styles [5] = NoPen

    """
    from plotpy.styles.base import LINESTYLE_CHOICES

    i = 0
    for s in LINESTYLE_CHOICES:
        print("Line styles [%d] = %s" % (i, s[0]))
        i += 1


def dump_marker_choices():
    """
    Marker Choices [0] = Cross
    Marker Choices [1] = Ellipse
    Marker Choices [2] = Star1
    Marker Choices [3] = XCross
    Marker Choices [4] = Rect
    Marker Choices [5] = Diamond
    Marker Choices [6] = UTriangle
    Marker Choices [7] = DTriangle
    Marker Choices [8] = RTriangle
    Marker Choices [9] = LTriangle
    Marker Choices [10] = Star2
    Marker Choices [11] = NoSymbol

    """
    from plotpy.styles.base import MARKER_CHOICES

    i = 0
    for s in MARKER_CHOICES:
        print("Marker Choices [%d] = %s" % (i, s[0]))
        i += 1


def dump_marker_style_choices():
    """
    Brush style Choices [0] = NoBrush
    Brush style Choices [1] = SolidPattern
    Brush style Choices [2] = Dense1Pattern
    Brush style Choices [3] = Dense2Pattern
    Brush style Choices [4] = Dense3Pattern
    Brush style Choices [5] = Dense4Pattern
    Brush style Choices [6] = Dense5Pattern
    Brush style Choices [7] = Dense6Pattern
    Brush style Choices [8] = Dense7Pattern
    Brush style Choices [9] = HorPattern
    Brush style Choices [10] = VerPattern
    Brush style Choices [11] = CrossPattern
    Brush style Choices [12] = BDiagPattern
    Brush style Choices [13] = FDiagPattern
    Brush style Choices [14] = DiagCrossPattern

    """
    from plotpy.styles.base import MARKERSTYLE_CHOICES

    i = 0
    for s in MARKERSTYLE_CHOICES:
        print("Marker Style Choices [%d] = %s" % (i, s[0]))
        i += 1


def dump_brushstyle_choices():
    """
    Marker Style Choices [0] = NoLine
    Marker Style Choices [1] = HLine
    Marker Style Choices [2] = VLine
    Marker Style Choices [3] = Cross

    """
    from plotpy.styles.base import BRUSHSTYLE_CHOICES

    i = 0
    for s in BRUSHSTYLE_CHOICES:
        print("Brush style Choices [%d] = %s" % (i, s[0]))
        i += 1


def dump_style_options():
    dump_curve_styles()
    dump_line_styles()
    dump_marker_choices()
    dump_brushstyle_choices()
    dump_marker_style_choices()


def get_histogram_style(color):
    dct = {}
    dct["line"] = {}
    dct["line"]["style"] = "SolidLine"
    dct["line"]["color"] = color_str_as_hex(color)
    dct["line"]["width"] = 1.0

    dct["symbol"] = {}
    dct["symbol"]["size"] = 8
    dct["symbol"]["alpha"] = 0.0
    dct["symbol"]["edgecolor"] = color_str_as_hex(color)
    dct["symbol"]["facecolor"] = color_str_as_hex(color)

    # dct['symbol']['edgecolor'] =  color_str_as_hex('rgb(128, 128, 128)')
    # dct['symbol']['facecolor'] =  master_colors['plot_forgrnd']["rgb_hex"]
    dct["symbol"]["marker"] = "NoSymbol"

    # dct['curvestyle'] = 'Lines'
    dct["curvestyle"] = "Steps"
    dct["curvetype"] = "Yfx"

    dct["shade"] = 0.75
    dct["fitted"] = False
    dct["baseline"] = 0.0

    return dct


def get_basic_line_style(color, marker="NoSymbol", width=2.0):
    dct = {}

    #   refer to CurveParam in plotpy.styles
    dct["line"] = {}
    dct["line"]["style"] = "SolidLine"
    dct["line"]["color"] = color_str_as_hex(color)
    dct["line"]["width"] = width

    dct["symbol"] = {}
    dct["symbol"]["size"] = 7
    dct["symbol"]["alpha"] = 0.0
    dct["symbol"]["edgecolor"] = color_str_as_hex(color)
    dct["symbol"]["facecolor"] = color_str_as_hex(color)
    # dct['symbol']['marker'] = 'Diamond'
    # dct['symbol']['marker'] = 'NoSymbol'
    # dct['symbol']['marker'] = 'Star1'
    dct["symbol"]["marker"] = marker

    dct["curvestyle"] = "Lines"
    dct["curvetype"] = "Yfx"

    dct["shade"] = 0.00
    dct["fitted"] = False
    dct["baseline"] = 0.0

    return dct

def get_basic_dot_style(color, marker="NoSymbol", width=2.0):
    dct = {}

    #   refer to CurveParam in plotpy.styles
    dct["line"] = {}
    dct["line"]["style"] = "SolidLine"
    dct["line"]["color"] = color_str_as_hex(color)
    dct["line"]["width"] = width

    dct["symbol"] = {}
    dct["symbol"]["size"] = 7
    dct["symbol"]["alpha"] = 0.0
    dct["symbol"]["edgecolor"] = color_str_as_hex(color)
    dct["symbol"]["facecolor"] = color_str_as_hex(color)
    # dct['symbol']['marker'] = 'Diamond'
    # dct['symbol']['marker'] = 'NoSymbol'
    # dct['symbol']['marker'] = 'Star1'
    dct["symbol"]["marker"] = marker

    dct["curvestyle"] = "Dots"
    dct["curvetype"] = "Yfx"

    dct["shade"] = 0.00
    dct["fitted"] = False
    dct["baseline"] = 0.0

    return dct


def get_trigger_line_style(color, marker="NoSymbol"):
    dct = {}

    #   refer to CurveParam in plotpy.styles
    dct["line"] = {}
    dct["line"]["style"] = "NoPen"
    dct["line"]["color"] = color_str_as_hex(color)
    dct["line"]["width"] = 1.0

    dct["symbol"] = {}
    dct["symbol"]["size"] = 7
    dct["symbol"]["alpha"] = 0.0
    dct["symbol"]["edgecolor"] = color_str_as_hex(color)
    dct["symbol"]["facecolor"] = color_str_as_hex(color)
    # dct['symbol']['marker'] = 'Diamond'
    # dct['symbol']['marker'] = 'NoSymbol'
    # dct['symbol']['marker'] = 'Star1'
    dct["symbol"]["marker"] = marker

    dct["curvestyle"] = "Lines"
    dct["curvetype"] = "Yfx"

    dct["shade"] = 0.40
    dct["fitted"] = False
    dct["baseline"] = 0.0

    return dct


def make_gridparam(rgb_color):
    hex_str = color_str_as_hex(rgb_color)
    gridparam = make.gridparam(
        background="%s" % hex_str,
        minor_enabled=(False, False),
        major_enabled=(True, True),
    )
    # self.gridparam.maj_line.color = '#626262'
    # self.gridparam.min_line.color = '#626262'
    return gridparam


class CurveWidgetException(Exception):
    pass


class AutoScaleTool(ToggleTool):
    changed = QtCore.pyqtSignal(object)
    # def __init__(self, manager, icon="move.png", toolbar_id=DefaultToolbarID):
    def __init__(
        self,
        manager,
        icon=os.path.join(icoDir, "autoScale.ico"),
        toolbar_id=DefaultToolbarID,
    ):
        super(AutoScaleTool, self).__init__(
            manager, _("AutoScale"), icon=icon, toolbar_id=toolbar_id
        )
        self.action.setCheckable(True)
        self.action.setChecked(True)

    def activate_command(self, plot, checked):
        """Activate tool"""
        self.changed.emit(checked)


class ClearPlotTool(ToggleTool):
    changed = QtCore.pyqtSignal(object)
    # def __init__(self, manager, icon="xcursor", toolbar_id=DefaultToolbarID):
    def __init__(
        self,
        manager,
        icon=os.path.join(icoDir, "restart.ico"),
        toolbar_id=DefaultToolbarID,
    ):

        super(ClearPlotTool, self).__init__(
            manager, _("Clear Plot"), icon=icon, toolbar_id=toolbar_id
        )
        self.action.setCheckable(True)

    def activate_command(self, plot, checked):
        """Activate tool"""
        self.changed.emit(checked)


class DataAcqSaveAsTool(SaveAsTool):
    filename = QtCore.pyqtSignal(object)

    def __init__(self, manager):
        super(DataAcqSaveAsTool, self).__init__(manager)

    def activate_command(self, plot, checked):
        """Activate tool"""
        # print 'myData saver tool called'
        formats = "\n%s (*.dat)" % _("Data Acquisition data")
        fname = getsavefilename(plot, _("Save as"), _("untitled"), formats)
        if fname:
            print("saving csv file [%s]" % fname)
            self.filename.emit(fname)


class CurveViewerWidget(PlotDialog):

    save_file = QtCore.pyqtSignal(object)
    right_mouse_click = QtCore.pyqtSignal(object)
    dropped = QtCore.pyqtSignal(QtCore.QMimeData)

    def __init__(
        self,
        title="Plot Viewer",
        toolbar=True,
        type="basic",
        filtStr="*.hdf5",
        options=None,
        parent=None,
    ):
        if options == None:
            options = PlotOptions()

        if hasattr(options, "gridparam"):
            # then use a default one
            options.gridparam = make.gridparam(
                background=master_colors["plot_bckgrnd"]["rgb_str"],
                minor_enabled=(False, False),
                major_enabled=(True, True),
            )
            options.gridparam.min_line.width = 0.5
            options.gridparam.maj_line.width = 0.5

        self.parent = parent
        super(CurveViewerWidget, self).__init__(
            edit=False,
            toolbar=toolbar,
            title=title,
            # options=dict(title="", xlabel="xlabel", ylabel="ylabel"))
            options=options,
            parent=parent
        )
        self.setObjectName("CurveViewerWidget")
        self.fileFilterStr = filtStr
        self.addtoplot = False
        self.plot = self.get_plot()
        pcan = self.plot.canvas()
        pcan.setObjectName("curvePlotBgrnd")
        pcan.setStyleSheet("background-color: %s;" % master_colors["plot_bckgrnd"]["rgb_str"])
        self.plot.set_axis_font("left", QtGui.QFont("Courier"))
        # self.get_itemlist_panel().show()
        # self.plot.set_items_readonly(False)

        self.setMinimumSize(100, 150)
        self.curve = None
        self.datFileData = None
        self.plotData = None
        self.plotDataCntr = 0
        self.xData = None
        self.yData = None
        self.maxPoints = 0
        self.curve_item = None
        self.plotTimer = None
        self.timerEnabled = False
        self.setAcceptDrops(True)
        self.drop_enabled = True
        self.max_seconds = 300  # 5 minute rolling window
        self.autoscale_enabled = True
        self._data_dir = ""
        self.data_io = None
        self.selected_detectors = []
        self.selected_detectors_dct = {}
        self.det_curve_nms = {}
        self.type = type
        if self.type == "basic":
            self.regTools = self.register_basic_tools
        elif self.type == "viewer":
            self.regTools = self.register_viewer_tools
        elif self.type == "minimal":
            self.regTools = self.register_minimal_tools
        else:
            self.regTools = self.register_basic_tools

        # legend = make.legend("TL")
        # self._addItems(legend)

        self.plot.SIG_ITEMS_CHANGED.connect(self.items_changed)
        # self.connect(self.plot, SIG_RANGE_CHANGED, self.range_changed)
        self.dropped.connect(self.on_drop)

        self.curve_objs = {}

        # self.style_btn = QtWidgets.QPushButton("Set Style")
        # self.style_btn.clicked.connect(self.update_style)
        #
        # vbox = QtWidgets.QVBoxLayout()
        # vbox.addWidget(self.plot)
        # self.layout().addWidget(self.style_btn)
        # self.setLayout(vbox)

    def get_selected_detectors(self):
        '''
        THIS IS IMPORTANT FOR THE SIGNAL SELECTION TOOL
        return the current list of detectors that have been selected by the parent widget
        '''
        return self.selected_detectors

    def get_selected_detectors_dct(self):
        """
        for signal checkable tool to retrieve the names and slected states of all signals
        """
        return self.selected_detectors_dct

    def set_selected_detectors_dct(self, det_dct={}):
        '''
        walk a list of detector names and set the checked attribute on the acition in the pulldown menu
        '''
        self.selected_detectors_dct = det_dct


    def set_selected_detectors(self, det_nm_lst=[]):
        '''
        set a list of detector names that will be used to populate the SignalSlectionTool pull down list
        '''
        self.selected_detectors = det_nm_lst
        sigsel_tool = self.plot.manager.get_tool(tools.clsSignalSelectTool)
        action = QtWidgets.QAction()
        action.setText(self.selected_detectors[0])
        sigsel_tool.activate_sigsel_tool(action)
        sigsel_tool.update_menu(self.plot.manager)

    def set_enable_drop_events(self, en):
        self.drop_enabled = en

    def dragEnterEvent(self, event):
        if self.drop_enabled:
            event.acceptProposedAction()
            self.dropped.emit(event.mimeData())

    def dragMoveEvent(self, event):
        if self.drop_enabled:
            event.acceptProposedAction()

    # def dropEvent(self, event):
    #     if self.drop_enabled:
    #         # import simplejson as json
    #         mimeData = event.mimeData()
    #         if mimeData.hasImage():
    #             # self.setPixmap(QtGui.QPixmap(mimeData.imageData()))
    #             # print 'dropEvent: mime data has an IMAGE'
    #             pass
    #         elif mimeData.hasHtml():
    #             # self.setText(mimeData.html())
    #             # self.setTextFormat(QtCore.Qt.RichText)
    #             # print 'dropEvent: mime data has HTML'
    #             pass
    #         elif mimeData.hasText():
    #             pass
    #             # # self.setText(mimeData.text())
    #             # # self.setTextFormat(QtCore.Qt.PlainText)
    #             # # print 'dropEvent: mime data has an TEXT = \n[%s]' %
    #             # # mimeData.text()
    #             # dct = mime_to_dct(mimeData)
    #             # # print 'dropped file is : %s' % dct['file']
    #             # self.blockSignals(True)
    #             #
    #             # self.openfile(dct["file"], scan_type=dct["scan_type_num"])
    #             # self.blockSignals(False)
    #         elif mimeData.hasUrls():
    #             # self.setText("\n".join([url.path() for url in mimeData.urls()])){"polarity": "CircLeft", "angle": 0.0, "center": [-419.172, 5624.301], "energy": 1029.0, "step": [110.86591666666668, 114.90791666666667], "scan_type": "coarse_image Line_Unidir", "range": [2660.782, 2757.79], "file": "S:\\STXM-data\\Cryo-STXM\\2017\\guest\\1207\\C171207014.hdf5", "offset": 0.0, "npoints": [25, 25], "dwell": 30.408937142857148, "scan_panel_idx": 8}
    #             # print 'dropEvent: mime data has URLs'
    #             pass
    #         else:
    #             # self.setText("Cannot display data")
    #             # print 'dropEvent: mime data Cannot display data'
    #             pass
    #
    #         # self.setBackgroundRole(QtGui.QPalette.Dark)
    #         event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        if self.drop_enabled:
            event.accept()

    def on_drop(self, mimeData=None):
        # self.formatsTable.setRowCount(0)
        if self.drop_enabled:
            if mimeData is None:
                return

            for format in mimeData.formats():
                formatItem = QtWidgets.QTableWidgetItem(format)
                formatItem.setFlags(QtCore.Qt.ItemIsEnabled)
                formatItem.setTextAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)

                # ToDo remove this
                if format == 'application/x-stxmscan':
                    itemData = mimeData.data("application/x-stxmscan")
                    _stream = QtCore.QDataStream(itemData, QtCore.QIODevice.ReadOnly)
                    _info_jstr = QtCore.QByteArray()
                    _data_bytes = QtCore.QByteArray()
                    _pos = QtCore.QPointF()
                    _stream >> _info_jstr >> _data_bytes >> _pos
                    # import numpy as np
                    _info_str = bytes(_info_jstr).decode()
                    dct = json.loads(_info_str)

                    fname = dct["path"]
                    xdata = dct["xdata"]
                    ydatas = dct["ydatas"]
                    sp_db = dct["sp_db"]
                    title = dct["title"]
                    num_specs = len(ydatas)
                    num_spec_pnts = len(xdata)
                    data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)

                    self.clear_plot()
                    for i in range(num_specs):
                        color = get_next_color(use_dflt=False)
                        style = get_basic_line_style(color)
                        self.create_curve(f"point_spectra_{i}", x=xdata, y=ydatas[i], curve_style=style)

                    xlabel = dct.get("xlabel")
                    self.setPlotAxisStrs("counts", xlabel)
                    self.update()
                    self.set_autoscale()
                    break

                elif format == "application/dict-based-lineplot-stxmscan":
                    itemData = mimeData.data("application/dict-based-lineplot-stxmscan")
                    _stream = QtCore.QDataStream(itemData, QtCore.QIODevice.ReadOnly)
                    _info_jstr = QtCore.QByteArray()
                    _data_bytes = QtCore.QByteArray()
                    _pos = QtCore.QPointF()
                    _stream >> _info_jstr >> _data_bytes >> _pos
                    _info_str = bytes(_info_jstr).decode()
                    drop_dct = json.loads(_info_str)

                    # fname = drop_dct["path"]
                    # convert to array
                    data = np.array(drop_dct["data"])
                    drop_dct["data"] = data
                    sp_db = drop_dct["sp_db"]
                    title = drop_dct["title"]
                    xlabel = drop_dct.get("xlabel") or "X"
                    ylabel = drop_dct.get("ylabel") or "Y"
                    xdata = drop_dct["xdata"]
                    ydatas = drop_dct["ydatas"]
                    sp_db = drop_dct["sp_db"]
                    num_specs = len(ydatas)

                    self.clear_plot()
                    for i in range(num_specs):
                        color = get_next_color(use_dflt=False)
                        style = get_basic_line_style(color)
                        self.create_curve(f"point_spectra_{i}", x=xdata, y=ydatas[i], curve_style=style)

                    xlabel = drop_dct.get("xlabel")
                    self.setPlotAxisStrs("counts", xlabel)

                    self.update()
                    self.set_autoscale()
                    break

                elif format == "text/plain":
                    text = mimeData.text()  # .strip()
                    break
                elif format == "text/html":
                    text = mimeData.html()  # .strip()
                    break
                elif format == "text/uri-list":
                    text = " ".join([url.toString() for url in mimeData.urls()])
                    break
                else:
                    # text = " ".join(["%02X" % ord(datum)
                    #                  for datum in mimeData.data(format)])
                    # text = " ".join(["%02X" % ord(datum) for datum in str(mimeData.data(format), encoding='cp1252')])
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
                            ]
                        )
                    break

                # row = self.formatsTable.rowCount()
                # self.formatsTable.insertRow(row)
                # self.formatsTable.setItem(row, 0, QtWidgets.QTableWidgetItem(format))
                # self.formatsTable.setItem(row, 1, QtWidgets.QTableWidgetItem(text))
                # print text

            # self.formatsTable.resizeColumnToContents(0)

    def update_style(self):
        ss = get_style()
        self.setStyleSheet(ss)

    def set_dataIO(self, data_io_cls):
        self.data_io = data_io_cls

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
        # self.opentool.set_directory(self._data_dir)

    def add_tool(self, toolklass, *args, **kwargs):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        tool = plot.manager.add_tool(toolklass, *args, **kwargs)
        return tool

    def add_separator_tool(self, toolbar_id=None):
        '''
        as part of the port from guiqwt to plotpy, redirect to new location
        '''
        plot = self.get_plot()
        plot.manager.add_separator_tool(toolbar_id)

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

    def register_basic_tools(self):
        """
        register_basic_tools(): description

        :returns: None
        """
        plot = self.get_plot()
        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=self.fileFilterStr)
        self.opentool.set_directory(self._data_dir)
        # self.connect(self.opentool, SIGNAL("openfile(QString*)"), self.openfile)
        self.opentool.openfile.connect(self.openfile)
        self.selectTool = self.add_tool(SelectTool)
        # self.selectTool = self.add_tool(tools.clsSelectTool)
        ast = self.add_tool(AutoScaleTool)
        ast.changed.connect(self.enable_auto_scale)

        #self.add_tool(tools.clsMeasureTool)

        cpt = self.add_tool(ClearPlotTool)
        cpt.changed.connect(self.do_clear_plot)
        # self.selectTool.changed.connect(self.on_select_tool_changed)
        self.add_separator_tool()
        self.add_tool(PrintTool)

        self.add_tool(tools.clsHorizMeasureTool)
        # hmeas_tool = plot.manager.get_tool(tools.clsHorizMeasureTool)
        # hmeas_tool.set_format("%.05f")

        self.set_default_tool(self.selectTool)
        self.get_default_tool().activate()

    def register_viewer_tools(self):
        """
        register_viewer_tools(): description

        :returns: None
        """
        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=self.fileFilterStr)
        self.opentool.set_directory(self._data_dir)
        # self.connect(self.opentool, SIGNAL("openfile(QString*)"), self.openfile)
        self.opentool.openfile.connect(self.openfile)
        self.selectTool = self.add_tool(SelectTool)
        # self.selectTool = self.add_tool(tools.clsSelectTool)

        cpt = self.add_tool(ClearPlotTool)
        cpt.changed.connect(self.do_clear_plot)
        # self.selectTool.changed.connect(self.on_select_tool_changed)
        self.add_separator_tool()
        self.add_tool(PrintTool)

        self.set_default_tool(self.selectTool)
        self.get_default_tool().activate()

    def register_minimal_tools(self):
        """
        register_viewer_tools(): description
        [0] [Selection]
        [1] [Rectangular selection tool]
        [2] [Rectangle zoom]
        [3] [AutoScale]
        [4] [Parameters...]
        [5] []
        [6] [Grid...]
        [7] [Axes style...]
        [8] []
        [9] [Signal statistics]
        [10] []
        DELETE [11] [Colormap]
        DELETE [12] [Rectangle snapshot]
        DELETE [13] [Image statistics]
        DELETE [14] [Cross section]
        DELETE [15] [Average cross section]
        DELETE [16] []
        [17] [Save as...]
        [18] [Copy to clipboard]
        [19] [Print...]
        [20] [Help]
        [21] []
        :returns: None
        """
        rem_list = ["Colormap", "Rectangle snapshot", "Image statistics", "Cross section", "Average cross section"]
        rem_idxs = [11, 12, 13, 14, 15, 16]
        toolbar = self.plot.manager.get_toolbar()
        actions = toolbar.actions()
        i = 0
        for ac in actions:
            #print(f"[{i}] [{ac.text()}]")
            if i in rem_idxs:
                toolbar.removeAction(actions[i])
            i += 1

        self.get_default_tool().activate()

    def remove_all_tools(self, force=False):
        """
        register_viewer_tools(): description
        [16] []
        [17] [Save as...]
        [18] [Copy to clipboard]
        [19] [Print...]
        [20] [Help]
        [21] []
        :returns: None
        """
        if force:
            #  keep "Help"
            keep_idxs = [21]
        else:
            #keep_list = ["Save as...", "Copy to clipboard snapshot", "Print", "Help"]
            keep_idxs = [16, 17, 18, 19, 20, 21]

        toolbar = self.plot.manager.get_toolbar()
        actions = toolbar.actions()
        i = 0
        for ac in actions:
            #print(f"[{i}] [{ac.text()}]")
            if i not in keep_idxs:
                toolbar.removeAction(actions[i])
            i += 1

        self.get_default_tool().activate()

    def set_grid_parameters(self, bkgrnd_color, min_color, maj_color):
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

    def enable_auto_scale(self, val):
        self.autoscale_enabled = bool(val)

    def do_clear_plot(self, val):
        self.reset_curve()

    def add_legend(self, location="TL"):
        """
        options for location are (from guiqwt/styles.py):
            "TL"  = Top left
            "TR" = Top right
            "BL" = Bottom left
            "BR" = Bottom right
            "L" = Left
            "R" = Right
            "T" = Top
            "B" = Bottom
            "C" = Center

        """
        options = ["TL", "TR", "BL", "BR", "L", "R", "T", "B", "C"]
        if location not in options:
            _logger.error("location [%s] is not valid" % location)
            return
        legend = make.legend(location)
        self._addItems(legend)

    def set_time_window(self, curve_names_list, val):
        self.max_seconds = val
        for curve_name in curve_names_list:
            if curve_name in self.curve_objs.keys():
                self.curve_objs[curve_name].set_time_window(val)

    def add_x_point(self, curve_name, point, update=False):
        self.curve_objs[curve_name].add_x_point(point, update)
        if update:
            self.set_autoscale()

        # make sure no curves are selected
        self.clear_selected_curves()

    def add_point(self, curve_name, point, update=False):
        self.curve_objs[curve_name].add_point(point, update)
        if update:
            self.set_autoscale()
        # make sure no curves are selected
        self.clear_selected_curves()

    def add_xy_point(self, curve_name, xpoint, point, update=False):
        # print(f"cureviewer: addXYPoint: {curve_name}, x={xpoint}, point={point}")
        # print(f"cureviewer: add_xy_point: {self.curve_objs}")
        if type(point) == list:
            point = point[0]
        if curve_name in self.curve_objs.keys():
            self.curve_objs[curve_name].add_xy_point(xpoint, point, update)
            if update:
                self.set_autoscale()
        # make sure no curves are selected
        self.clear_selected_curves()

    def set_xy_data(self, curve_name, x, y, update=False):
        self.curve_objs[curve_name].setXYData(x, y)
        if update:
            self.set_autoscale()
        # make sure no curves are selected
        self.clear_selected_curves()

    def clear_selected_curves(self):
        """
        the last curve that was plotted seems to be left in the selected state, this clears all selections
        """
        self.plot.manager.get_itemlist_panel().listwidget.clearSelection()

    def incr_plot_counter(self):
        self.plotDataCntr += 1

    def update_curve(self):
        self.plot.replot()

    def create_curve(self, curve_name, x=None, y=None, curve_style=None, use_dflt=False ):
        """
        create a curve_item
        """
        if y is None:
            num_points = 0
        else:
            if type(y) == list:
                num_points = len(y)
            else:
                num_points = y.shape[0]

        if curve_style is None:
            curve_style = get_basic_line_style(
                get_next_color(use_dflt=use_dflt), marker="Star1", width=2.0
            )

        self.curve_objs[curve_name] = curve_Obj(
            curve_name, x, y, num_points=num_points, curve_style=curve_style
        )
        self.curve_objs[curve_name].changed.connect(self.update_curve)
        self._addItems(self.curve_objs[curve_name].curve_item)
        self.update_curve()

    def reset_curve(self, curve_name=None):
        if curve_name is None:
            curve_name = list(self.curve_objs.keys())[0]

        self.curve_objs[curve_name].reset_curve()

    def curve_exists(self, curve_name):
        """
        return True if it exists in dict of curve_objs or False if not
        """
        #if curve_name in self.curve_objs.keys():
        for crv_nm in self.curve_objs.keys():
        #if curve_name in self.curve_objs.keys():
            if crv_nm.find(curve_name) > -1:
                return True
        return False

    def get_complete_curve_name(self, nm):
        """
        """
        for crv_nm in self.curve_objs.keys():
            # if curve_name in self.curve_objs.keys():
            if crv_nm.find(nm) > -1:
                return crv_nm

        return None

    def set_add_to_plot(self, on):
        self.addtoplot = on

    #     def openfile(self, fileName):
    #         #print 'openfile called for file: %s' % fileName
    #         if(self.addtoplot == False):
    #             self.clear_plot()
    #
    #         if fileName:
    #             self.datFilename = fileName
    #             t = fileName.split('/')
    #             titleName = t[-1]
    #             datStrs = readColumnStrs(str(fileName))
    #             idx = 0
    #             arr = loadDatToArray(str(fileName))
    #             xdata = arr.take([1],axis=1)
    #             sz = xdata.shape[0]
    #             #make a 1d array of appropriate size
    #             xdata = np.reshape(xdata,(sz,))
    #
    #             for i in range(2,len(arr[0])):
    #                 ydata = arr.take([i],axis=1)
    #                 ydata = np.reshape(ydata,(sz,))
    #                 curve_name = datStrs[i-1]
    #                 self.create_curve(curve_name, xdata,ydata)
    #
    #             self.setPlotAxisStrs(titleName, datStrs[0], 'units')
    #             self.set_autoscale()

    def install_data_io_handler(self, data_io_hndlr):
        self.data_io = data_io_hndlr

    def openfile(self, fname, scan_type=None, counter_name="DNM_DEFAULT_COUNTER"):
        """
        openfile(): currently only supports 1 counter per entry

        :param fname: full path to the desired file
        :type fname: string

        :returns: None
        """
        if scan_type is None:
            _logger.error("scan_type is None")
            return
        if scan_type not in types.spectra_type_scans:
            # only allow image type scan data to be dropped here
            return
        if self.data_io is None:
            _logger.error("No data IO module registered")
            return

        fname = str(fname)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        if data_dir is None:
            _logger.error("Problem with file [%s]" % fname)
            return
        self.clear_plot()
        data_io = self.data_io(data_dir, fprefix)
        entry_dct = data_io.load()
        if entry_dct is None:
            _logger.error("No entry in datafile")
            return
        # remove the 'default' key
        if "default" in entry_dct.keys():
            entry_dct.pop("default")
        ekeys = sorted(entry_dct.keys())

        for ekey in ekeys:
            entry = entry_dct[ekey]
            nx_datas = data_io.get_NXdatas_from_entry(entry_dct, ekey)
            # currently only support 1 counter
            counter_name = data_io.get_default_detector_from_entry(entry_dct, ekey=ekey)
            axes = data_io.get_axes_list_from_NXdata(nx_datas, counter_name)

            if scan_type is types.scan_types.GENERIC_SCAN:
                xdata, ydata = self.get_xydata_from_generic_scan(
                    entry, data_io, counter_name
                )
            else:
                xdata = data_io.get_axes_data_by_index_in_NXdata(
                    nx_datas, counter_name, 0
                )
                ydata = data_io.get_signal_data_from_NXdata(nx_datas, counter_name)

                if (xdata.ndim != 1) or (ydata.ndim != 1):
                    _logger.error(
                        "Data in file [%s] is of wrong dimension, is [%d, %d] should be [1, 1]"
                        % (fname, xdata.ndim, ydata.ndim)
                    )
                    print(
                        "Data in file [%s] is of wrong dimension, is [%d, %d] should be [1, 1]"
                        % (fname, xdata.ndim, ydata.ndim)
                    )
                    return

            # data.shape
            wdg_com = data_io.get_wdg_com_from_entry(entry_dct, ekey)

            self.create_curve(ekey, xdata, ydata)

        self.plot.set_title("%s%s" % (fprefix, fsuffix))
        self.setPlotAxisStrs("counts", axes[0])
        self.set_autoscale()

    def get_xydata_from_generic_scan(self, entry_dct, data_io, counter):
        """
        ekey = get_first_entry_key(self.dct)
        entry_dct = self.dct['entries'][ekey]
        sp_db = get_first_sp_db_from_entry(entry_dct)
        xdata = get_axis_setpoints_from_sp_db(sp_db, axis='X')
        ydatas = get_generic_scan_data_from_entry(entry_dct, counter=DNM_DEFAULT_COUNTER)

        :param entry_dct:
        :param data_io:
        :param counter:
        :return:
        """
        sp_db = data_io.get_first_sp_db_from_entry(entry_dct)
        xdata = data_io.get_axis_setpoints_from_sp_db(sp_db, axis="X")
        ydata = data_io.get_generic_scan_data_from_entry(
            entry_dct, counter=counter
        )[0]

        # if ((xdata.ndim is not 1) or (ydata.ndim is not 1)):
        if len(xdata) is not len(ydata):
            _logger.error(
                "Data is of unequal lengths xdata=%d ydata=%d"
                % (len(xdata), len(ydata))
            )
            print(
                "Data is of unequal lengths xdata=%d ydata=%d"
                % (len(xdata), len(ydata))
            )
            return (None, None)
        return (xdata, ydata)

    def set_autoscale(self):
        plot = self.get_plot()
        if self.autoscale_enabled:
            plot.do_autoscale(replot=True)
        # else:
        #    plot.do_autoscale(replot=False)

    def saveFile(self, filename):
        # this will save the file as was received from the data acquisition, the files
        # should look the same
        print("CurveViewerWidget: saveFile called [%s]" % filename)
        self.save_file.emit(filename)

    def clear_actions(self):
        tb = self.get_toolbar()
        actions = tb.actions()
        for action in actions:
            tb.removeAction(action)

    def reg_striptool_tools(self):
        self.clear_actions()
        # opentool = self.add_tool(OpenFileTool, "*.dat")
        # self.connect(opentool, SIGNAL("openfile(QString*)"), self.openfile)
        # opentool.openfile.connect(self.openfile)

        self.opentool = self.add_tool(tools.clsOpenFileTool, formats=self.fileFilterStr)
        self.opentool.set_directory(self._data_dir)
        # self.connect(self.opentool, SIGNAL("openfile(QString*)"), self.openfile)
        self.opentool.openfile.connect(self.openfile)

        saveTool = self.add_tool(DataAcqSaveAsTool)
        saveTool.filename.connect(self.saveFile)

        ast = self.add_tool(AutoScaleTool)
        ast.changed.connect(self.enable_auto_scale)

        cpt = self.add_tool(ClearPlotTool)
        cpt.changed.connect(self.do_clear_plot)
        # self.set_default_tool(self.selectTool)
        # self.get_default_tool().activate()

    #     def regTools(self):
    #         self.clear_actions()
    #         opentool = self.add_tool(OpenFileTool, "*.dat")
    #         self.connect(opentool, SIGNAL("openfile(QString*)"), self.openfile)
    #         saveTool = self.add_tool(DataAcqSaveAsTool)
    #         saveTool.filename.connect(self.saveFile)
    #
    #         ast = self.add_tool(AutoScaleTool)
    #         ast.changed.connect(self.enable_auto_scale)
    #
    #         cpt = self.add_tool(ClearPlotTool)
    #         cpt.changed.connect(self.do_clear_plot)
    #         #self.set_default_tool(self.selectTool)
    #         #self.get_default_tool().activate()

    def items_changed(self, plot):
        # disable region select tool
        self.get_default_tool().activate()

    def range_changed(self, rnge, min, max):
        # SIG_RANGE_CHANGED = SIGNAL("range_changed(PyQt_PyObject,double,double)")
        # print 'SIG_RANGE_CHANGED: caught with values (%f, %f)' % (min, max)
        pass

    def show_items_panel(self):
        self.get_itemlist_panel().show()
        self.plot.set_items_readonly(False)

    def addTool(self, toolstr, **kwargs):
        """a function that allows inheriting widgets to add tools
        where tool is a valid guiqwt tool"""

        if toolstr == "LabelTool":
            tool = self.add_tool(LabelTool)
        elif toolstr == "SegmentTool":
            tool = self.add_tool(SegmentTool)
        elif toolstr == "RectangleTool":
            tool = self.add_tool(RectangleTool)
        elif toolstr == "CircleTool":
            tool = self.add_tool(CircleTool)
        elif toolstr == "EllipseTool":
            tool = self.add_tool(EllipseTool)
        elif toolstr == "MultiLineTool":
            tool = self.add_tool(MultiLineTool)
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
        elif toolstr == "tools.clsSignalSelectTool":
            tool = self.add_tool(tools.clsSignalSelectTool)
        elif toolstr == "tools.clsCheckableSignalSelectTool":
            tool = self.add_tool(tools.clsCheckableSignalSelectTool, **kwargs)
        elif toolstr == "tools.clsROITool":
            tool = self.add_tool(tools.ROITool)
        elif toolstr == "SegmentTool":
            tool = self.add_tool()

        return tool

    def activate_create_roi_tool(self, chkd):
        if chkd:
            self.activate_tool("clsROITool")
        else:
            self.deactivate_tool("clsROITool")
            self.get_default_tool().activate()

    def _setCurveItem(self, item):
        self.curve_item = item
        self.plot = self.get_plot()
        if self.plot is not None:
            self.plot.add_item(self.curve_item)

    def _signal_change(self, **kw):
        point = kw["value"]
        # print 'signal(%d)' % point
        self.add_point(point)

    # update curve is called by the timer, it will take the data that was
    # delivered and updated by the callback '_signal_change()', the plotting
    # Painter complains with teh following:
    # error message: 'Cannot send posted events for objects in another thread'
    # so to handle plotting updates then when connecting to data from a pv
    # I use a timer that calls this function to update the plotting curve
    def _update_curve(self):
        # ---Update curve
        if self.curve_item is not None:
            # here only update the
            # self.curve_item.set_data(self.xData, self.yData)
            self.curve_item.set_data(
                self.xData[0 : self.plotDataCntr], self.yData[0 : self.plotDataCntr]
            )
            self.curve_item.plot().replot()
        # ---
        if self.plotTimer is not None:
            if self.timerEnabled == False:
                self.plotTimer.stop()

    def delete_all_curve_items(self):
        """
        for some reason it requires iterations to remove all of the CurveItems from the plot
        this function keeps at it until the job is done
        """
        is_clean = False
        while not is_clean:
            plot_items = self.plot.get_items()
            for item in plot_items:
                if type(item) != GridItem:
                    self.delPlotItem(item, replot=True)
            #check if all CurveItems are gone?
            is_clean = True
            plot_items = self.plot.get_items()
            for item in plot_items:
                if type(item) == CurveItem:
                    is_clean = False
                    break

    def delete_curve_item(self, curve_nm):
        """
        for some reason it requires iterations to remove all of the CurveItems from the plot
        this function keeps at it until the job is done
        """
        is_clean = False
        while not is_clean:
            plot_items = self.plot.get_items()
            for item in plot_items:
                if type(item) != GridItem:
                    self.delPlotItem(item, replot=True)
            #check if all CurveItems are gone?
            is_clean = True
            plot_items = self.plot.get_items()
            for item in plot_items:
                if type(item) == CurveItem:
                    is_clean = False
                    break

    def clear_plot(self):
        reset_color_idx()
        self.delete_all_curve_items()
        # for crv in self.curve_objs:
        #     self.curve_objs.pop(crv)
        self.curve_objs = {}

        # for d in self.det_curve_nms:
        #     self.det_curve_nms.pop(d)
        self.det_curve_nms = {}

        self.set_autoscale()

    # add the items to the plot
    def _addItems(self, *items):
        plot = self.get_plot()
        for item in items:
            plot.add_item(item)

    def delPlotItem(self, item, replot=True):
        # Don't delete the legend
        try:
            if item.title().text() != "Legend":
                #print("delPlotItem: deleting item: %s"  % item.title().text())
                self.plot.del_item(item)
                if replot:
                    self.plot.replot()
            else:
                #print("delPlotItem: skipping deleting item: %s" % item.title().text())
                pass
        except:
            # pass
            raise CurveWidgetException(
                f"Failed to delete plot item {item.title().text()}"
            )

    # set the X and Y axis strings
    def setPlotAxisStrs(self, ystr=None, xstr=None):
        self.plot = self.get_plot()
        # set axis titles
        if ystr != None:
            self.plot.setAxisTitle(Qwt.QwtPlot.yLeft, ystr)
        if xstr != None:
            self.plot.setAxisTitle(Qwt.QwtPlot.xBottom, xstr)

        self.plot.setAxisTitle(Qwt.QwtPlot.xTop, "")
        self.plot.setAxisTitle(Qwt.QwtPlot.yRight, "")

    def setPlotTitleAndAxisStrs(self, title=None, xstr=None, ystr=None):
        self.plot = self.get_plot()
        if title != None:
            self.plot.set_title(title)
        # set axis titles
        if xstr != None:
            self.plot.setAxisTitle(Qwt.QwtPlot.xBottom, xstr)
        if ystr != None:
            self.plot.setAxisTitle(Qwt.QwtPlot.yLeft, ystr)

    def mousePressEvent(self, ev):
        # print 'StxmImageWidget: mouse pressed'
        if ev.buttons() == QtCore.Qt.MouseButton.LeftButton:
            #            #print 'left mouse button pressed'
            #            #check to see if the user is using one of the selection tools, if so
            #            # then set the name of the active plot item, if you can
            #            tool = self.plot.manager.get_active_tool()
            #            if(isinstance(tool, AverageCrossSectionTool)):
            #                #print 'Average selection tool selected'
            #                self.roiNum += 1
            #            elif(isinstance(tool, AnnotatedSegmentTool)):
            #                #print 'AnnotatedSegmentTool tool selected'
            #                self.segNum += 1
            #            elif(isinstance(tool, AnnotatedPointTool)):
            #                #print 'AnnotatedPointTool tool selected'
            #                self.pntNum += 1
            #
            return
        if ev.buttons() == QtCore.Qt.MouseButton.RightButton:
            # print 'right mouse button pressed'
            self.right_mouse_click.emit(self.sender())

    def create_curves(self, det_nm_lst, sp_ids, prefix="spid-", clr_set={}):
        """
        a function to take a list of detector names and a list of spatial ids and
        create a list of curve names and associated colrs that will be used to access the curve data .
        returns a dict of curve names and colors for each curve
        """
        self.det_curve_nms = {}
        num_specs = len(sp_ids)
        self.det_curve_nms = {}

        for d in det_nm_lst:
            self.add_curve(d, sp_ids, prefix,clr_set)

        return self.det_curve_nms


    def add_curve(self, det_nm, sp_ids, prefix="spid-", clr_set={}):
        """
        a function to take a detector name and a list of sp_ids or a scalar with a specific sp_id to use
         and creates the curve with name <det_nm><prefix>
        """
        num_specs = list(range(len(sp_ids)))
        clr = ""
        for i in num_specs:
            _det_nm = det_nm.replace("DNM_", "")
            _det_nm = gen_complete_spec_chan_name(_det_nm, sp_ids[i], prefix=prefix)
            #self.det_curve_nms[f"{det_nm}-spid-{sp_ids[i]}"] = get_next_color(use_dflt=False)
            if i in clr_set.keys():
                clr = clr_set[i]
            else:
                clr = get_next_color(use_dflt=False)

            self.det_curve_nms[_det_nm] = clr
            style = get_basic_line_style(clr)

            if not self.curve_exists(_det_nm):
                self.create_curve(f"{_det_nm}", curve_style=style)

        return self.det_curve_nms


#    def mouseReleaseEvent(self, ev):
#        #print 'StxmImageWidget: mouse released'
#
#        if ev.button() == QtCore.Qt.MouseButton.LeftButton:
#            #print 'StxmImageWidget: mouse moved with left button pressed'
#            plot = self.get_plot()
#            #pan = plot.get_itemlist_panel()
#            #get all the shapes and turn off their size texts
#            active_item = plot.get_active_item()
#            items = self.plot.get_items(item_type=IShapeItemType)
#            for item in items:
#                if item.is_label_visible() and (item != active_item):
#                    item.set_label_visible(False)
#                #item.position_and_size_visible = False
#                    #pass
#
#            self.plot.replot()
#            return


# note: these handlers are using Qt4.5 syntax, it changes in Qt4.8.3
#    def mouseMoveEvent(self, ev):
#
#        if ev.button() == Qt.MidButton:
#            #print 'StxmImageWidget: mouse moved with middle button pressed'
#            return
#        elif ev.button() == QtCore.Qt.MouseButton.LeftButton:
#            #print 'StxmImageWidget: mouse moved with left button pressed'
#            #self.manager.update_cross_sections()
#
#            return
#        elif ev.button() == QtCore.Qt.MouseButton.RightButton:
#            #print 'StxmImageWidget: mouse moved with right button pressed'
#            return
#
#
#    def wheelEvent(self, ev):
#        pass
#        #print 'StxmImageWidget: wheel event'


def make_spectra_viewer_window(data_io=None):
    if data_io is None:
        from cls.data_io.stxm_data_io import STXMDataIo

        data_io = STXMDataIo

    win = CurveViewerWidget(toolbar=True, type="viewer")
    win.set_dataIO(data_io)
    return win

def get_selected_detector_list():
    l = []
    l.append('DNM_SIS3820_CH_00')
    l.append('DNM_SIS3820_CH_04')
    l.append('DNM_SIS3820_CH_24')

    return(l)

def test_plotting_datarecorder_file(fname):
    import time
    from cls.utils.fileUtils import get_file_path_as_parts
    from bcm.devices.ophyd.e712_wavegen.datarecorder_utils import parse_datarecorder_file
    def openfile(fname):
        global win

        win.setWindowTitle(fname[0])
        win.textedit.clear()
        data_dct = parse_datarecorder_file(fname[0])
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname[0])
        win._data_dir = data_dir
        win.set_data_dir(data_dir)
        dets = data_dct['data'].keys()
        dnms = []
        for d in dets:
            dnms.append(d.replace("Current Position of ",""))

        win.clear_plot()
        time.sleep(0.2)
        reset_color_idx()
        det_curve_nms = win.create_curves(dnms, sp_ids=[0],prefix="")
        det_curve_nms = list(det_curve_nms.keys())
        # so here I need to create num_spec_pnts x num detectors
        x = data_dct['time']
        i = 0
        for det_nm, data in data_dct['data'].items():
            det_nm = det_curve_nms[i]
            #normalize data to base value of 0
            data = np.array(data)
            val = data[0]
            data = data - val
            win.set_xy_data(det_nm, x, data, update=True)
            min = data.min()
            max = data.max()
            print(f"[{det_nm}] min = {min:.3f} max = {max:.3f}, delta = {max - min:.3f}")
            win.textedit.append(f"[{det_nm}] min = {min:.3f} max = {max:.3f}, delta = {max - min:.3f}")

            i += 1

    def openfiles(fpath):
        global win
        import os
        from cls.utils.dirlist import dirlist
        data_dir = os.path.dirname(fpath[0])
        files = dirlist(data_dir, suffix='.dat')
        win.setWindowTitle(data_dir)
        win.textedit.clear()
        win._data_dir = data_dir
        win.set_data_dir(data_dir)
        win.clear_plot()
        time.sleep(0.2)
        reset_color_idx()
        dnms = []
        det_curve_nms = []
        create_curves = True
        i = 0
        for fname in files:
            file = os.path.join(data_dir, fname)
            data_dct = parse_datarecorder_file(file)
            #data_dir, fprefix, fsuffix = get_file_path_as_parts(file)
            dets = data_dct['data'].keys()
            for d in dets:
                if d.find('Target') == -1:
                    if d not in dnms:
                        #dnms.append(d.replace("Current Position of ",""))
                        dnms.append(d)
                    else:
                        create_curves = False
            if create_curves:
                det_curve_nms = win.create_curves(dnms, sp_ids=[0],prefix="")
                det_curve_nms = list(det_curve_nms.keys())

            # so here I need to create num_spec_pnts x num detectors
            x = data_dct['time']

            curve_num = 0
            for det_nm, data in data_dct['data'].items():
                if det_nm.find("Target") > -1:
                    continue
                det_nm = det_curve_nms[curve_num]
                #normalize data to base value of 0
                data = np.array(data)
                min = data.min()
                max = data.max()
                delta = max - min
                win.add_xy_point(det_nm, i, delta, update=True)

                print(f"[{i}]->{fname}: [{det_nm.replace('Current Position of ','')}] min = {min:.3f} max = {max:.3f}, delta = {max - min:.3f}")
                win.textedit.append(f"[{i}]->{fname}: [{det_nm.replace('Current Position of ','')}] min = {min:.3f} max = {max:.3f}, delta = {max - min:.3f}")


                curve_num += 1
            print(f"-------------------------------------------------------------------------------------------------")
            win.textedit.append(
                f"-------------------------------------------------------------------------------------------------")
            i += 1


    # show_std_icons()
    options = PlotOptions(
       show_itemlist=False,
    )
    win = CurveViewerWidget(toolbar=True, options=options)
    win.add_legend("TL")
    win.textedit = QtWidgets.QTextEdit(win)
    font = QtGui.QFont("Arial", 12)  # Set font size to 16
    win.textedit.setFont(font)
    win.fileFilterStr = "*.dat"
    win._data_dir = "Y:/STXM/vibration-measurements-2025"
    win.opentool = win.add_tool(tools.clsOpenFileTool, formats=win.fileFilterStr)
    win.opentool.set_directory(win._data_dir)
    win.opentool.openfile.connect(openfile)

    win.opentool_files = win.add_tool(tools.clsOpenFileTool, formats=win.fileFilterStr)
    win.opentool_files.action.setText("Open Files")
    win.opentool_files.set_directory(win._data_dir)
    win.opentool_files.openfile.connect(openfiles)

    layout = win.layout()
    layout.addWidget(win.textedit)
    win.setMinimumSize(1000,1000)

    return(win)

def make_sig_selection_wip():
    import sys

    # from guiqwt.builder import make
    from plotpy.builder import make

    # from cls.appWidgets.spyder_console import ShellWidget  # , ShellDock
    from cls.data_io.stxm_data_io import STXMDataIo

    app = QtWidgets.QApplication(sys.argv)
    # show_std_icons()
    win = CurveViewerWidget(toolbar=True)
    win.set_data_dir(r"S:\STXM-data\Cryo-STXM\2017\guest\0106")
    win.regTools()
    win.add_legend("TL")
    win.set_dataIO(STXMDataIo)

    dets = get_selected_detector_list()
    win.addTool("tools.clsSignalSelectTool")

    num_specs = len(dets)
    num_spec_pnts = 250

    det_curve_nms = win.create_curves(dets, sp_ids=list(range(0,3)))

    x = np.linspace(-np.pi, np.pi, num_spec_pnts)
    data = np.sin(x)

    # so here I need to create num_spec_pnts x num detectors
    ii = 1
    for det_nm, dct in det_curve_nms.items():
        win.set_xy_data(det_nm, x, data * ii, update=True)
        ii += 0.75

    win.set_selected_detectors(dets)
    #
    # ns = {"win": win, "g": globals()}
    # # msg = "Try for example: widget.set_text('foobar') or win.close()"
    # # pythonshell = ShellWidget(parent=None, namespace=ns,commands=[], multithreaded=True)
    # # win.layout().addWidget(pythonshell)

    win.style_btn = QtWidgets.QPushButton("Set Style")
    win.style_btn.clicked.connect(win.update_style)

    vbox = QtWidgets.QVBoxLayout()
    vbox.addWidget(win.plot)
    win.layout().addWidget(win.style_btn)
    win.setLayout(vbox)

    win.show()

    sys.exit(app.exec_())
    # print "all done"

if __name__ == "__main__":

    import sys

    #from guiqwt.builder import make
    from plotpy.builder import make

    #from cls.appWidgets.spyder_console import ShellWidget  # , ShellDock
    from cls.data_io.stxm_data_io import STXMDataIo

    #dump_style_options()
    #make_sig_selection_wip()
    app = QtWidgets.QApplication(sys.argv)
    # # show_std_icons()
    # # win = CurveViewerWidget(toolbar=True)
    # # win.set_data_dir(r"S:\STXM-data\Cryo-STXM\2017\guest\0106")
    # # win.regTools()
    # # win.add_legend("TL")
    # # win.set_dataIO(STXMDataIo)
    # #
    # # dets = get_selected_detector_list()
    # # win.addTool("tools.clsSignalSelectTool")
    # #
    # # num_specs = len(dets)
    # # num_spec_pnts = 250
    # #
    # # det_curve_nms = win.create_curves(dets, sp_ids=list(range(0,3)))
    # #
    # # x = np.linspace(-np.pi, np.pi, num_spec_pnts)
    # # data = np.sin(x)
    # #
    # # # so here I need to create num_spec_pnts x num detectors
    # # ii = 1
    # # for det_nm, dct in det_curve_nms.items():
    # #     win.setXYData(det_nm, x, data * ii, update=True)
    # #     ii += 0.75
    # #
    # # win.set_selected_detectors(dets)
    # #
    # # ns = {"win": win, "g": globals()}
    # # # msg = "Try for example: widget.set_text('foobar') or win.close()"
    # # # pythonshell = ShellWidget(parent=None, namespace=ns,commands=[], multithreaded=True)
    # # # win.layout().addWidget(pythonshell)
    #
    #
    # filename = "G:/SM/test_data/test_dr.dat"  # Replace with the actual file name
    # filename = "G:/SM/test_data/guest/0717/C230717010/00_02/C230717010_002.dat"
    # filename = 'G:/SM/test_data/guest/0717/test_300ms_b.dat'
    # filename = 'G:/SM/test_data/guest/0718/test_dr.dat'
    # filename = 'G:/SM/test_data/guest/0718/test_dr18.dat' # 5000ms 50 pts
    # filename = 'G:/SM/test_data/guest/0718/test_dr19.dat'  # 1ms 50 pts
    # filename = 'G:/SM/test_data/guest/0718/test_dr20.dat'  # 10ms 50 pts
    filename = "G:\e712_ASTXM_vibration\XY-new-mirror-bracket/xy-Jul10-2024-new-mirrot-bracket.dat"
    win = test_plotting_datarecorder_file(filename)
    #
    # win.style_btn = QtWidgets.QPushButton("Set Style")
    # win.style_btn.clicked.connect(win.update_style)
    #
    # vbox = QtWidgets.QVBoxLayout()
    # vbox.addWidget(win.plot)
    # win.layout().addWidget(win.style_btn)
    # win.setLayout(vbox)
    #
    win.show()
    #
    sys.exit(app.exec_())
    # # print "all done"
