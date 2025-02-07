# -*- coding:utf-8 -*-
"""
Created on 2011-03-09

@author: bergr

"""

import os

from PyQt5 import QtGui, QtCore, QtWidgets

import queue

from plotpy.builder import make
from plotpy.styles import GridParam, LineStyleParam
from plotpy.plot import PlotOptions

from bcm.devices.ophyd.base_device import BaseDevice

from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.utils.pixmap_utils import get_pixmap
from cls.plotWidgets.curveWidget import CurveViewerWidget
from cls.devWidgets.ophydLabelWidget import ophyd_aiLabelWidget
from cls.plotWidgets.curveWidget import get_histogram_style
from cls.stylesheets import master_colors, get_style, is_style_light

from bcm.devices import BACKEND

# setup module logger with a default do-nothing handler
_logger = get_module_logger(__name__)

# read the ini file and load the default directories


appConfig = ConfigClass(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "counters.ini")
)
# appConfig = ConfigClass(abs_path_to_top + '\counters.ini')

uiDir = appConfig.get_value("MAIN", "uiDir")
dataDir = appConfig.get_value("MAIN", "dataDir")
cfgDir = appConfig.get_value("MAIN", "cfgDir")
sigList = appConfig.get_value("PV", "sigList")
SLASH = appConfig.get_value("MAIN", "dirslash")
scaler_from_ini = float(appConfig.get_value("PV", "scaler"))
icoDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "icons")


from guidata.dataset.datatypes import DataSet
from guidata.dataset.dataitems import FloatItem, ColorItem

ICONSIZE = 20
BTNSIZE = 25


class gridDataSet(DataSet):
    """
    Parameters
    <b>Striptool Parameters</b>
    plot_bckgrnd = rgb(50,50,50)
    plot_forgrnd = rgb(2,116,255)
    plot_gridmaj = rgb(65,65,65)
    plot_gridmin = rgb(40,40,40)
    """
    
    # enable = BoolItem(u"Enable parameter set",
    #                  help=u"If disabled, the following parameters will be ignored",
    #                  default=False)
    # param0 = ChoiceItem(u"Param 0", ['choice #1', 'choice #2', 'choice #3'])
    timeSpan = FloatItem("Viewable Timespan (minutes)", default=3, min=0.6)
    updateInterval = FloatItem("Data Sample Interval (seconds)", default=1, min=0.1)
    bgColor = ColorItem("Background Color", default=master_colors["plot_bckgrnd"]["rgb_str"])
    #gridColor = ColorItem("Grid Color", default="#515151")
    gridColor = ColorItem("Grid Color", default=master_colors["plot_gridmaj"]["rgb_str"])


# stripToolDataSet.set_defaults()


class StripToolWidget(QtWidgets.QWidget):
    """
    This is a first crack at a striptool, the desired PV's are retrieved from
    a list given in the striptool.ini file under the PV section header,
    when teh app starts the pv names are read from the ini file and then their
    values are posted at a rate of 1Hz, the window size is 300 seconds or 5 min,
    this can be adjusted

    The main ui was created using qtDesigner and it is loaded in MainWindow
    such that MainWindow IS the ui file as a widget. The widgets used in the
    ui file were named in the properties window of qtDesigner.

    """

    def __init__(self, timespan, parent=None, sigList=[], energy_fbk_dev=None, labelHeader="", scale_factor=scaler_from_ini):
        super(StripToolWidget, self).__init__()

        self.parent = parent
        self.setObjectName("stripToolWidget")
        _style = LineStyleParam()
        _style.color = master_colors["plot_gridmaj"]["rgb_hex"]
        gridmaj_style = (_style.style, _style.color, _style.width)

        self.gridparam = make.gridparam(
            background=master_colors["plot_bckgrnd"]["rgb_hex"],
            minor_enabled=(False, False),
            major_enabled=(True, True),
            major_style=gridmaj_style
        )

        self.scanplot = CurveViewerWidget(
            title="",
            toolbar=False,
            options=PlotOptions(xlabel="", gridparam=self.gridparam),
            parent=parent,
        )
        self.scanplot.setObjectName("stripToolWidgetPlot")
        self.scanplot.reg_striptool_tools()
        self.updateInterval = 0.25
        self.timeSpan = timespan  # minutes
        s = "%3.2f minute Window" % (self.timeSpan)

        # self.resetBtn = QtWidgets.QPushButton("Clear")
        # self.resetBtn.setToolTip('Clear the plot')
        # self.resetBtn.setCheckable(False)
        # self.resetBtn.clicked.connect(self.on_reset_btn)
        #
        self.scale_factor = scale_factor
        self.resetBtn = QtWidgets.QToolButton()
        pmap = get_pixmap(os.path.join(icoDir, "restart.ico"), ICONSIZE, ICONSIZE)
        # self.refreshBtn.icon(QtGui.QPixmap(pmap))
        self.resetBtn.setText("")
        self.resetBtn.setIcon(
            QtGui.QIcon(QtGui.QPixmap(pmap))
        )  # .scaled(48,48, QtCore.Qt.KeepAspectRatio)))
        self.resetBtn.setFixedSize(BTNSIZE, BTNSIZE)
        # self.resetBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.resetBtn.setToolTip("Restart the plot")
        self.resetBtn.setCheckable(False)
        self.resetBtn.clicked.connect(self.on_reset_btn)

        # self.autoscaleBtn = QtWidgets.QPushButton("AutoScale")
        self.autoscaleBtn = QtWidgets.QToolButton()
        pmap = get_pixmap(os.path.join(icoDir, "autoScale.ico"), ICONSIZE, ICONSIZE)
        self.autoscaleBtn.setIcon(QtGui.QIcon(QtGui.QPixmap(pmap)))
        self.autoscaleBtn.setFixedSize(BTNSIZE, BTNSIZE)
        self.autoscaleBtn.setToolTip("Toggle autoscaling")
        self.autoscaleBtn.setCheckable(True)
        self.autoscaleBtn.setChecked(True)
        self.autoscaleBtn.clicked.connect(self.on_autoscale_enable)

        self.updateQueue = queue.Queue()

        self.gridDSet = gridDataSet()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        # self.scanplot.right_mouse_click.connect(self.on_rt_mouse)

        #self.signal: BaseDevice = sigHeader or sigList[0]
        self.signal: BaseDevice = energy_fbk_dev
        self.counts_signal: BaseDevice = sigList[0]
        #         #f = QtGui.QFont( "BankGothic lt BT", 10, QtGui.QFont.Bold)
        f = QtGui.QFont("ISOCTUER", 14)  # , QtGui.QFont.Bold)
        if is_style_light:
            var_clr = "black"
        else:
            var_clr = "white"

        if hasattr(self.signal, "_units"):
            units = self.signal._units
        else:
            units = ""

        self.energyFbkLbl = ophyd_aiLabelWidget(
            self.signal,
            hdrText=labelHeader,
            egu=units,
            format="%.1f",
            title_color=master_colors["app_superltblue"]["rgb_str"],
            var_clr=var_clr,
            font=f,
            scale_factor=1
        )
        self.countsFbkLbl = ophyd_aiLabelWidget(
            self.counts_signal,
            hdrText="",
            egu="",
            format="%d",
            title_color=master_colors["gray_255_rgb"]["rgb_str"],
            var_clr=master_colors["gray_255_rgb"]["rgb_str"],
            #font=f,
            scale_factor=self.scale_factor
        )
        self.energyFbkLbl.setObjectName("stripToolFbkLbl")

        self.upd_style_btn = QtWidgets.QPushButton("Update Style")
        self.upd_style_btn.clicked.connect(self.update_stlye)

        hlayout = QtWidgets.QHBoxLayout()
        hlayout.setContentsMargins(2, 0, 0, 0)
        spacer = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        hlayout.addWidget(self.resetBtn)
        hlayout.addWidget(self.autoscaleBtn)
        hlayout.addItem(spacer)
        hlayout.addWidget(self.countsFbkLbl)
        hlayout.addItem(spacer)
        hlayout.addWidget(self.energyFbkLbl)
        hlayout.addItem(spacer)
        layout.addLayout(hlayout)
        # layout.addWidget(self.upd_style_btn)

        self.handlers_connected = False
        self.ctrlrFbkPv = None

        layout.addWidget(self.scanplot)
        # self.py_con = self.get_py_console()
        # layout.addWidget(self.py_con)
        layout.setContentsMargins(0, 0, 0, 0)
        #
        self.setLayout(layout)
        self.total_points = 0
        self.data = []

        self.bpmsigs = {}
        self.sigList = sigList
        self.signalNames = []
        for pv in self.sigList:
            self.signalNames.append(pv.get_name())

        self.connect_pvs(self.sigList)
        self.scanplot.set_time_window(
            self.signalNames, (self.timeSpan * 60.0) * (1.0 / self.updateInterval)
        )

        # self.scanplot.enable_auto_scale(False)

        self.timeIdx = -1

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(int(self.updateInterval * 1000.0))

        self.init = True

        # this logs time stamped messages to the log window at the bottom of the
        # application
        # _logger.info("Application started")
        self.update_stlye()

    def update_stlye(self):
        ss = get_style()
        self.setStyleSheet(ss)

    def get_py_console(self):
        """
        setup_info_dock(): description

        :returns: None
        """
        from cls.appWidgets.spyder_console import ShellWidget

        ns = {"self": self, "g": globals(), "get_style": get_style}
        pythonshell = ShellWidget(
            parent=None, namespace=ns, commands=[], multithreaded=True
        )
        return pythonshell

    def on_reset_btn(self):
        # self.timeIdx = 0
        for curve_name in self.signalNames:
            self.scanplot.reset_curve(curve_name)

    def on_autoscale_enable(self, checked):
        if checked:
            self.scanplot.enable_auto_scale(True)
        else:
            self.scanplot.enable_auto_scale(False)

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
        aplot = self.scanplot.manager.get_active_plot()
        gparam = GridParam()
        gparam.background = bkgrnd_color
        gparam.maj_line.color = maj_color
        gparam.min_line.color = min_color
        aplot.grid.set_item_parameters({"GridParam": gparam})
        aplot.ensurePolished()
        # aplot.polish()
        aplot.replot()

    def get_sigList(self):
        l1 = sigList.replace(" ", "")
        list = l1.split(",")
        return list

    def on_timer(self):
        # print('stripToolWidget.py: 265: on_timer()')
        call_task_done = False
        self.timeIdx += 1
        resp_dct = {}
        while not self.updateQueue.empty():
            #read out all in queue and process the last one
            resp_dct = self.updateQueue.get()
            call_task_done = True

        if call_task_done:
            name = resp_dct["name"]
            val = resp_dct["val"]
            self.scanplot.add_xy_point(name, self.timeIdx, val, update=True)
            self.updateQueue.task_done()

    def connect_pvs(self, sigList):
        """
        walk a list of PVs and create a curve for each
        """
        
        clr = master_colors["plot_forgrnd"]["rgb_str"]
        style = get_histogram_style(clr)

        for sig in sigList:
            name = sig.get_name()
            self.scanplot.create_curve(name, curve_style=style)
            self.bpmsigs[name] = {"sig": sig, "val": 0}
            # _pv.changed.connect(self.on_bpmpv_changed)
            # pv.add_callback(self.on_sig_changed, with_ctrlvars=False)

            # make sure the changed signal returns entire dict because we need the pv name that the value belongs to
            sig.set_return_val_only(False)
            # if BACKEND.find('zmq') > -1:
            #     sig.changed.connect(self.on_zmq_sig_changed)
            # else:
            #     sig.changed.connect(self.on_sig_changed)
            sig.changed.connect(self.on_sig_changed)


    def on_sig_changed(self, kwargs):
        # print('on_sig_changed', kwargs)
        if "value" in kwargs.keys():
            val = kwargs["value"] * self.scale_factor
            signame = kwargs["obj"].name
            self.on_bpmpv_changed(val, signame=signame)
            # print('stripTool: on_sig_changed: need to emit a value here')

    def on_zmq_sig_changed(self, val):
        #print(f'stripToolWidget: on_zmq_sig_changed val=[{val}]')
        if "value" in kwargs.keys():
            val = val * self.scale_factor
            signame = kwargs["obj"].name
            self.on_bpmpv_changed(val, signame=signame)
            # print('stripTool: on_sig_changed: need to emit a value here')

    def on_bpmpv_changed(self, val, signame=None):
        """
        handler to update the ring current label when the PV changes
        """
        if signame is None:
            name = self.sender().signame
        else:
            name = signame
        # print name , val
        # self.bpmsigs[name]['val'] = val
        dct = {"name": name, "val": val}
        self.updateQueue.put_nowait(dct)

    def set_scanplot_axis_strs(self, dacq):
        """
        set the plot axis strings for our cfg file
        """
        plotStrs = self.dacq.acq_info.get_pv_names()
        title = dacq.acq_info.get_scan_name()
        self.currentScanName = title
        self.scanplot.setPlotAxisStrs(title, plotStrs[0], plotStrs[1])
        self.init_feedback_panel(plotStrs)

    def init_feedback_panel(self, ctrlPvNames):
        """
        There is a panel that shows the current scan motor position feedback
        so that the user can see what the motor is doing.
        Use the one that is the motor (SMTR), but use the first by default
        """
        name = ctrlPvNames[0]
        for nm in ctrlPvNames:
            if nm.find("SMTR") > -1:
                name = nm

        if self.ctrlrFbkPv != None:
            self.ctrlrFbkPv.changed.disconnect()

        self.ctrlrLbl.setText(name)
        self.ctrlrFbkPv = ca.PV(name)
        self.ctrlrFbkPv.changed.connect(self.on_ctrlFbkpv_changed)

    def on_ctrlFbkpv_changed(self, val):
        """
        handler to update the Controlelr feedback label when the PV changes
        """
        # print 'on_ringpv_changed: %f' % val
        s = "%.2f" % val
        self.ctrlrFbkFld.setText(s)

    def on_startup(self):
        """
        Signal handler that is connected to the startup signal emitted
        by the acquisition module
        """

        _logger.info("wireScanViewWidg: callback from acq start")


def runApp(mode):

    import sys
    from bcm.devices import BaseDevice

    # ca.threads_init()
    app = QtWidgets.QApplication(sys.argv)
    win = StripToolWidget(0.5, sigList=[BaseDevice("MCS1610-310-02:mcs09:fbk")])
    win.show()
    app.exec_()


if __name__ == "__main__":

    # test file import
    runApp(0)
