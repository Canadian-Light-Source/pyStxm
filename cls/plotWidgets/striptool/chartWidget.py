# -*- coding:utf-8 -*-
"""
Created on 2025-04-21

@author: bergr

"""

import os
from PyQt5.QtWidgets import QToolBar, QLabel, QLineEdit, QWidget, QHBoxLayout, QWidgetAction, QSpacerItem, QSizePolicy
from PyQt5 import QtGui, QtCore, QtWidgets

import queue

from guidata.qthelpers import add_actions, create_action
from plotpy.builder import make
from plotpy.styles import GridParam, LineStyleParam
from plotpy.plot import PlotOptions

from cls.utils.sig_utils import disconnect_signal
from cls.utils.log import get_module_logger
from cls.utils.cfgparser import ConfigClass
from cls.utils.pixmap_utils import get_pixmap
from cls.plotWidgets.curveWidget import CurveViewerWidget, get_next_color, reset_color_idx, get_color_by_idx
from cls.plotWidgets.curveWidget import get_histogram_style, get_basic_dot_style
from cls.stylesheets import master_colors, get_style, is_style_light

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
    # gridColor = ColorItem("Grid Color", default="#515151")
    gridColor = ColorItem("Grid Color", default=master_colors["plot_gridmaj"]["rgb_str"])







# stripToolDataSet.set_defaults()

class ChartingWidget(QtWidgets.QWidget):
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

    def __init__(self, timespan, parent=None, signals_dct: dict=None, scale_factor=scaler_from_ini, select_cb=None):
        super(ChartingWidget, self).__init__()

        self.parent = parent
        self.setObjectName("ChartingWidget")
        _style = LineStyleParam()
        _style.color = master_colors["plot_gridmaj"]["rgb_hex"]
        gridmaj_style = (_style.style, _style.color, _style.width)
        self.select_cb = select_cb

        self.gridparam = make.gridparam(
            background=master_colors["plot_bckgrnd"]["rgb_hex"],
            minor_enabled=(False, False),
            major_enabled=(True, True),
            major_style=gridmaj_style
        )

        self.scanplot = CurveViewerWidget(
            title="",
            toolbar=True,
            options=PlotOptions(xlabel="", gridparam=self.gridparam),
            parent=parent,
        )


        #self.scanplot.setObjectName("BaseStripToolWidgetPlot")
        self.scanplot.setObjectName("CurveViewerWidget")

        # self.scanplot.reg_striptool_tools()
        self.updateInterval = 0.5
        self.timeSpan = timespan  # minutes
        s = "%3.2f minute Window" % (self.timeSpan)

        self.scale_factor = scale_factor
        restart_pmap = get_pixmap(os.path.join(icoDir, "restart.ico"), ICONSIZE, ICONSIZE)
        self.autoscaleBtn = QtWidgets.QToolButton()
        autoscale_pmap = get_pixmap(os.path.join(icoDir, "autoScale.ico"), ICONSIZE, ICONSIZE)
        self.scanplot.remove_all_tools(force=True)
        self.autoscale_action = create_action(self, "Enable Autoscale", icon=QtGui.QIcon(QtGui.QPixmap(autoscale_pmap)),
                                              tip="Toggle autoscaling",
                                              checkable=True,
                                              triggered=self.on_autoscale_enable,
                                              toggled=self.on_autoscale_enable,
                                              enabled=True)
        self.autoscale_action.setChecked(True)

        self.reset_plot_action = create_action(self, "Reset Plot", icon=QtGui.QIcon(QtGui.QPixmap(restart_pmap)),
                                              tip="Reset Plot",
                                              checkable=True,
                                              triggered=self.on_reset_btn,
                                              toggled=self.on_reset_btn,
                                              enabled=True)

        add_actions(self.scanplot.manager.get_toolbar('default'), [self.reset_plot_action])
        add_actions(self.scanplot.manager.get_toolbar('default'), [self.autoscale_action])
        self.scanplot.add_separator_tool()
        #self.scanplot.addTool("tools.clsSignalSelectTool")


        # # Example usage:
        # # Assuming `self` is a QMainWindow or a QWidget with a QToolBar
        # toolbar = QToolBar("My Toolbar")
        # self.addToolBar(toolbar)
        self.scanplot.add_separator_tool()
        self.add_label_lineedit_to_toolbar(self.scanplot.manager.get_toolbar("default"), "Interval:", width=75, val=self.updateInterval)

        t = self.scanplot.addTool("tools.clsCheckableSignalSelectTool", signals_dct=signals_dct)
        t.changed.connect(self.on_selection_changed)

        self.updateQueue = queue.Queue()

        layout = QtWidgets.QVBoxLayout()
        # Set the size policy to make it expand
        self.scanplot.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.setContentsMargins(0, 0, 0, 0)

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

        self.plot_signals = {}
        self.signals_dct = signals_dct
        self.signalNames = []
        for pv_name, pv in self.signals_dct.items():
            self.signalNames.append(pv_name)

        self.connect_pvs(self.signals_dct, init=True)
        self.scanplot.set_time_window(
            self.signalNames, (self.timeSpan * 60.0) * (1.0 / self.updateInterval)
        )
        self.scanplot.add_legend("TL")

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

    def add_label_lineedit_to_toolbar(self, toolbar: QToolBar, label_text: str, val=None, width=200):
        """
        Add a QLabel and QLineEdit to the given toolbar.

        :param toolbar: The QToolBar to which the widget will be added.
        :param label_text: The text for the QLabel.
        """
        spacer = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Create a container widget
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 0, 0)  # Remove margins for better alignment
        layout.addSpacerItem(spacer)

        # Create the QLabel and QLineEdit
        label = QLabel(label_text)
        self.interval_fld = QLineEdit()
        validator = QtGui.QDoubleValidator(0.5, 100.0, 2)  # Range: -1000.0 to 1000.0, Precision: 2 decimal places
        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)  # Use standard notation
        self.interval_fld.setValidator(validator)

        self.interval_fld.setMaximumWidth(width)
        self.interval_fld.returnPressed.connect(self.on_interval_changed)

        # Add the QLabel and QLineEdit to the layout
        layout.addWidget(label)
        layout.addWidget(self.interval_fld)
        layout.addWidget(QLabel("(ms)"))
        if val:
            self.interval_fld.setText(str(val))

        # Create the QCheckBox
        self.on_off_checkbox = QtWidgets.QCheckBox("On/Off")
        self.on_off_checkbox.setChecked(True)  # Default state is unchecked
        self.on_off_checkbox.toggled.connect(self.on_checkbox_toggled)
        layout.addWidget(self.on_off_checkbox)

        # Create the QCheckBox
        self.count_checkbox = QtWidgets.QCheckBox("Count rate")
        self.count_checkbox.setChecked(True)  # Default state is unchecked
        self.count_checkbox.toggled.connect(self.on_count_checkbox_toggled)
        layout.addWidget(self.count_checkbox)

        # Add a horizontal spacer
        layout.addSpacerItem(spacer)

        # Create a QWidgetAction and set the container as its default widget
        widget_action = QWidgetAction(toolbar)
        widget_action.setDefaultWidget(container)

        # Add the QWidgetAction to the toolbar
        toolbar.addAction(widget_action)

    def on_execute_callback(self):
        """
        get the data and call the callback with a dict of arguments
        """
        dct = {}
        dct["feedback_interval"] = float(self.interval_fld.text())
        dct["feedback_on_off"] = self.on_off_checkbox.isChecked()
        dct["count_rate"] = self.count_checkbox.isChecked()
        self.select_cb(dct)

    def on_count_checkbox_toggled(self, checked):
        """
        Handle the checkbox toggled signal.
        """
        print(f"Count rate Checkbox toggled: {'On' if checked else 'Off'}")
        self.on_execute_callback()

    def on_checkbox_toggled(self, checked):
        """
        Handle the checkbox toggled signal.
        """
        print(f"Checkbox toggled: {'On' if checked else 'Off'}")
        self.on_execute_callback()

    def on_interval_changed(self):
        """
        when the user presse enter on the interval take the value and send a message
        """
        fld = self.sender()
        val = fld.text()
        print(f"on_ineterval_changed: val={val}")
        self.on_execute_callback()

    def set_selected_detectors_dct(self, sel_detectors_names):
        """
        pass selected detectors to the plot
        """
        # print('BaseStripToolWidget: set_selected_detectors sel_detectors=[{}]'.format(sel_detectors))
        self.scanplot.set_selected_detectors(sel_detectors_names)
        self.selected_detectors = sel_detectors_names

    def on_selection_changed(self, sel_detectors_nms):
        """
        Signal handler that is connected to the selection changed signal emitted
        by the acquisition module

        Here when selections have changed the ploter needs to cancel current subscriptions and resubscribe to all
        selected detectors
        """
        self.set_selected(sel_detectors_nms, self.signals_dct)
        #clear current curves
        self.delete_all_curves(self.signals_dct)
        # self.on_reset_btn()
        # make sure the curves get created and changed signals get connected
        self.connect_pvs(self.signals_dct)

    def set_selected(self, keys, dict_of_dicts):
        """
        Sets the 'selected' attribute to True for the given keys in a dictionary of dictionaries.

        :param keys: List of keys whose 'selected' attribute should be set to True.
        :param dict_of_dicts: The dictionary of dictionaries.
        """
        #first deslect all signals
        for k in dict_of_dicts.keys():
            dict_of_dicts[k]["selected"] = False
        #now set the ones that are selected
        for key in keys:
            if key in dict_of_dicts:
                dict_of_dicts[key]['selected'] = True

    def update_stlye(self):
        ss = get_style()
        self.setStyleSheet(ss)

    def on_reset_btn(self):
        # self.timeIdx = 0
        self.reset_plot_action.setChecked(False)
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
        # print('BaseStripToolWidget.py: 265: on_timer()')
        call_task_done = False
        self.timeIdx += 1
        resp_dct = {}
        while not self.updateQueue.empty():
            # read out all in queue and process the last one
            resp_dct = self.updateQueue.get()
            name = resp_dct["name"]
            val = resp_dct["val"]
            self.scanplot.add_xy_point(name, self.timeIdx, val, update=True)
            call_task_done = True

        if call_task_done:
            self.updateQueue.task_done()


    def connect_pvs(self, signals_dct={}, init=False):
        """
        walk a dict of PVs and create a curve for each
        if init == True then also connect to the changed signal
        if init == False then just create the curve because the signal connection has already been made and
        to disconnect it will mess up any other widgets that have created a signal connection to the changed signal

        """
        # use the color list such that the same detector (index in color list) will always use the same color
        clr_idx = 0
        for sig_name, sig_dct in signals_dct.items():
            sig = sig_dct['dev']
            if sig_dct['selected']:
                if sig_name not in self.plot_signals.keys():
                    clr = get_color_by_idx(clr_idx)
                    style = get_basic_dot_style(clr, marker="NoSymbol", width=3.5)
                    #print(f"connect_pvs: creating a curve for {sig_name}, clr={clr}, style={style}")
                    self.scanplot.create_curve(sig_name, curve_style=style)
                    if init:
                        self.plot_signals[sig_name] = {"sig": sig, "val": 0, "connected": True}
                        # make sure the changed signal returns entire dict because we need the pv name that the value belongs to
                        sig.set_return_val_only(False)
                        sig.changed.connect(self.on_sig_changed)
            clr_idx += 1


    def delete_all_curves(self, signals_dct={}):
        """
        delete all curve items and clean up signals
        """

        for sig_name, sig_dct in signals_dct.items():
            sig = sig_dct['dev']
            if sig_name in self.plot_signals.keys():
                if self.plot_signals[sig_name]['connected']:
                    # sig.changed.disconnect()
                    self.plot_signals[sig_name]['connected'] = False
                    del self.plot_signals[sig_name]
        self.scanplot.delete_all_curve_items()
        reset_color_idx()

    def on_sig_changed(self, kwargs):
        # print('on_sig_changed', kwargs)
        if "value" in kwargs.keys():
            val = kwargs["value"] * self.scale_factor
            signame = kwargs["obj"].name
            self.on_signal_changed_push_to_queue(val, signame=signame)
            #print(f"stripTool: on_sig_changed: [{signame}] val = {val}")

    def on_signal_changed_push_to_queue(self, val, signame=None):
        """
        handler to update the ring current label when the PV changes
        """
        if signame is None:
            name = self.sender().signame
        else:
            name = signame

        if self.signals_dct[name]["selected"]:
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
    win = ChartingWidget(0.5, signals_dct=[BaseDevice("ASTXM1610:Ci-D1C2:cntr:SingleValue_RBV")])
    win.scanplot.remove_all_tools()
    win.scanplot.addTool("tools.clsSignalSelectTool")
    win.show()
    app.exec_()


if __name__ == "__main__":
    # test file import
    runApp(0)
