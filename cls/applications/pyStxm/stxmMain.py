"""
Created on 2014-06-23

@author: bergr
"""

import atexit
import os
import queue
import sys
import time

from importlib.machinery import SourceFileLoader
import logging
import numpy as np
import simplejson as json
import webbrowser
import copy
from PyQt5 import QtCore, QtGui, uic, QtWidgets

from plotpy.items import PolygonShape

from cls.applications.pyStxm import abs_path_to_ini_file
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

from cls.applications.pyStxm.sm_user import usr_acct_manager
from cls.stylesheets import master_colors, get_style, color_str_as_hex, get_default_screen_size
from cls.utils.file_system_tools import get_next_file_num_in_seq
from cls.utils.time_utils import secondsToStr
from cls.utils.log import (
    get_module_logger,
    log_to_qt_and_to_file,
)
from cls.utils.environment import get_environ_var
from cls.utils.json_utils import dict_to_json
from cls.utils.fileUtils import get_file_path_as_parts
from cls.utils.roi_dict_defs import *
from cls.utils.roi_object import integrate_poly_mask
from cls.utils.list_utils import sum_lst
from cls.utils.cfgparser import ConfigClass
from cls.utils.roi_utils import (
    widget_com_cmnd_types,
    get_first_sp_db_from_wdg_com,
    reset_unique_roi_id,
    add_to_unique_roi_id_list,
)

from cls.utils.file_system_tools import (
    get_thumb_file_name_list,
)
from cls.utils.prog_dict_utils import *
from cls.utils.sig_utils import reconnect_signal, disconnect_signal

from cls.plotWidgets.imageWidget import ImageWidgetPlot
from cls.plotWidgets.striptool.stripToolWidget import StripToolWidget
from cls.plotWidgets.striptool.chartWidget import ChartingWidget
from cls.plotWidgets.curveWidget import (
    CurveViewerWidget,
)
from cls.plotWidgets.visual_signals import VisualSignalsClass
from cls.plotWidgets.utils import *

from cls.data_io.stxm_data_io import STXMDataIo
from cls.data_io.exec_nxvalidate import validate_nxstxm_file
from cls.scanning.BaseScan import LOAD_ALL

# from cls.scanning.dataRecorder import HdrData
from cls.types.stxmTypes import (
    image_types,
    scan_types,
    scan_sub_types,
    spectra_type_scans,
    detector_types,
    spatial_type_prefix,
    sample_positioning_modes,
    scan_status_types,
    SPEC_ROI_PREFIX
)


from cls.devWidgets.ophydLabelWidget import (
    ophyd_aiRangeLabelWidget,
    ophyd_aiLabelWidget,
    ophyd_biLabelWidget,
    format_text,
)
from cls.appWidgets.user_account.login import loginWidget

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.contact_sheet import ContactSheet
from cls.applications.pyStxm.widgets.select_detectors_panel import DetectorsPanel
from cls.appWidgets.dialogs import excepthook, notify as dialog_notify, warn as dialog_warn

# from cls.appWidgets.spyder_console import ShellWidget#, ShellDock
from cls.appWidgets.thread_worker import Worker

# from cls.applications.pyStxm.widgets.sampleSelector import SampleSelectorWidget
from cls.applications.pyStxm.widgets.motorPanel import PositionersPanel

from cls.applications.pyStxm.widgets.devDisplayPanel import DevsPanel

# from cls.applications.pyStxm.bl10ID01 import MAIN_OBJ, POS_TYPE_BL, POS_TYPE_ES

from cls.applications.pyStxm.widgets.scan_queue_table import ScanQueueTableWidget
from cls.applications.pyStxm.widgets.ioc_apps_panel import IOCAppsPanel
from cls.applications.pyStxm.widgets.ptycho_viewer import PtychoDataViewerPanel

from cls.types.beamline import BEAMLINE_IDS
# from cls.applications.pyStxm.main_obj_init import MAIN_OBJ

# import suitcase.nxstxm as suit_nxstxm

from cls.data_io.nxstxm import Serializer

# RUSS FEB25 from suitcase.csv import Serializer


def factory(name, start_doc):
    # def factory(data_dir):
    # serializer = Serializer(data_dir)
    serializer = Serializer("C:/controls/stxm-data/2022/guest/0224")
    # serializer = Serializer(name)
    # serializer('start', start_doc)

    return [serializer], []


# from bcm.devices.device_names import *


# from event_model import RunRouter
# from suitcase.nxstxm import Serializer
#
# def factory(name, start_doc):
#
#     serializer = Serializer(data_dir)
#     serializer('start', start_doc)
#
#     return [serializer], []
#
#
# #connect outr data
# rr = RunRouter([factory])
# RE.subscribe(rr)

# read the ini file and load the default directories
appConfig = ConfigClass(abs_path_to_ini_file)
scanPluginDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_plugins")
uiDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
prefsDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preferences")
docs_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "..",
    "docs",
    "_build",
    "html",
    "index.html",
)
PTYCHO_CAMERA = MAIN_OBJ.get_preset("default_cam", "PTYCHO_CAMERA")

sample_pos_mode = MAIN_OBJ.get_sample_positioning_mode()
sample_finepos_mode = MAIN_OBJ.get_fine_sample_positioning_mode()

# setup module logger with a default do-nothing handler
_logger = get_module_logger(__name__)

active_user = None

PLOTTER_IMAGES_TAB = 0
PLOTTER_SPECTRA_TAB = 1

NUM_POINTS_LOST_AFTER_EDIFF = 2
DATA_OFFSET = 1

hostname = os.getenv("COMPUTERNAME")
if hostname == "WKS-W001465":
    # the new test computer in old magnet mapping room
    FAKE_MARKER = False
    UNIT_SCALAR = 0.001
    # VELO_SCALAR = 1
    # VELO_SCALAR = 0.001
    VELO_SCALAR = 1000.0
    USE_PIEZO = True
elif hostname == "NBK-W001021":
    # my notebook computer
    FAKE_MARKER = True
    UNIT_SCALAR = 1.0
    USE_PIEZO = False
else:
    # the old stxm_control conmputer
    FAKE_MARKER = False
    UNIT_SCALAR = 0.001
    VELO_SCALAR = 0.001
    USE_PIEZO = True


class MouseOverEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Enter:
            # print("Mouse entered:", obj.objectName())
            pass

            # widget = QtWidgets.QApplication.instance().childAt(event.pos())
            # widget = QtWidgets.QApplication.instance().focusWidget().childAt(event.pos())
            # get_children_of_widget(obj)

        elif event.type() == QtCore.QEvent.Leave:
            # print("Mouse Leave:", obj.objectName())
            pass

        return False


class EngineLabel(QtWidgets.QLabel):
    """
    QLabel to display the RunEngine Status
    Attributes
    ----------
    color_map : dict
        Mapping of Engine states to color displays
    """
    color_map = {
        "running": (
            master_colors["black"]["rgb_str"],
            master_colors["fbk_moving_ylw"]["rgb_str"],  # Running ON
            master_colors["fbk_dark_ylw"]["rgb_str"],  # Running OFF
            master_colors["app_red"]["rgb_str"],
        ),
        "pausing": (
            master_colors["black"]["rgb_str"],
            master_colors["app_yellow"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
        "paused": (
            master_colors["black"]["rgb_str"],
            master_colors["app_yellow"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
        "stopping": (
            master_colors["black"]["rgb_str"],
            master_colors["app_yellow"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
        "idle": (
            master_colors["white"]["rgb_str"],
            master_colors["app_drkgray"]["rgb_str"],
            master_colors["app_ltblue"]["rgb_str"],
            master_colors["app_blue"]["rgb_str"],
        ),
    }

    def __init__(self, lbl):
        super(EngineLabel, self).__init__()
        self._lbl = lbl
        self._blink_timer = QtCore.QTimer()
        self._blink_timer.timeout.connect(self.on_timeout)
        self._tmr_en = False
        self._blink_timer.start(500)
        self._cur_color = None
        self._state_str = None

    def on_timeout(self):
        if self._tmr_en:
            if self.isEnabled():
                self.setEnabled(False)
            else:
                self.setEnabled(True)
        else:
            if not self.isEnabled():
                self.setEnabled(True)
        self._set_colors()

    def on_state_change(self, new_state, old_state):
        # print(f"EngineLabel: on_state_change: state=[{new_state}], old_state=[{old_state}] ")
        if new_state is None:
            return
        self._state_str = new_state
        # Update the label
        if new_state.find("running") > -1:
            self._tmr_en = True
        else:
            self._tmr_en = False

        self._lbl.setText(self._state_str.upper())
        #print(f"stxmMain: on_state_change: {self._state_str.upper()}")
        # Update the font and background color
        if new_state in self.color_map.keys():
            self._cur_color = self.color_map[new_state]
            self._set_colors()

    def _set_colors(self):
        if self._cur_color:
            if self._tmr_en:
                if self.isEnabled():
                    clr1, clr2, clr3, cl4 = self._cur_color
                else:
                    clr1, clr3, clr2, clr4 = self._cur_color
            else:
                clr1, clr2, clr3, cl4 = self._cur_color

            ss = "QLabel {font-weight: bold; color: %s; background-color: %s}" % (clr1, clr2)
            self._lbl.setStyleSheet(ss)
            self._blink_timer.start(500)

    def connect_to_engine(self, engine):
        """Connect an existing QRunEngine"""
        if engine:
            engine.engine_state_changed.connect(self.on_state_change)
            self.on_state_change(engine.state, "")


##############################################################################################################
##############################################################################################################
class pySTXMWindow(QtWidgets.QMainWindow):
    """
    classdocs
    """
    _set_scan_btns = QtCore.pyqtSignal(object)
    # scan progress signal for scans that do not emit RE scan progress
    # these are typically scans where the progress is delivered via the DataEmitter
    non_re_scan_progress = QtCore.pyqtSignal(object)
    roi_spec_changed = QtCore.pyqtSignal(str, float, float, str)  # f"ROI_{shp_id}", energy, val, clr

    update_rois = QtCore.pyqtSignal(
        object)  # .emit(img_idx, det_name, self.lineByLineImageDataWidget.get_data(det_name), cur_ev)
    integrate = QtCore.pyqtSignal()

    # _check_for_another_scan = QtCore.pyqtSignal(object)

    def __init__(self, parent=None, exec_in_debugger=False, log=None):
        """
        __init__(): description

        :param parent=None: parent=None description
        :type parent=None: parent=None type

        :returns: None
        """
        super(pySTXMWindow, self).__init__(parent)
        # uic.loadUi(os.path.join(os.getcwd(), 'ui', 'pyStxm.ui'), self)
        uic.loadUi(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "pyStxm.ui"),
            self,
        )
        atexit.register(self.on_exit)
        self.executingScan = None

        # connect logger
        # self.log = log_to_qt()
        # logdir = os.path.dirname(os.path.abspath(__file__))
        # logfile = os.path.join(logdir, 'logs', time.strftime("%Y%m%d-%H%M%S") + '.log')
        # self.log = log_to_qt_and_to_file(logfile, level=logging.DEBUG)
        if log is None:
            logdir = os.path.dirname(os.path.abspath(__file__))
            logfile = os.path.join(
                logdir, "logs", time.strftime("%Y%m%d-%H%M%S") + ".log"
            )
            log = log_to_qt_and_to_file(logfile, level=logging.DEBUG)

        self.log = log
        self.log.new_msg.connect(self.add_to_log)
        self.exec_in_debugger = exec_in_debugger

        MAIN_OBJ.export_msg.connect(self.add_exporter_msg_to_log)

        _logger.info("####################### Starting pystxm ####################### ")
        self.setWindowTitle(
            "pyStxm %s.%s Canadian Light Source Inc. [%s] [%s] [%s]"
            % (
                MAIN_OBJ.get("APP.MAJOR_VER"),
                MAIN_OBJ.get("APP.MINOR_VER"),
                os.path.dirname(os.path.abspath(__file__)),
                MAIN_OBJ.get("APP.COMMIT")[0:8],
                MAIN_OBJ.get("APP.DATE"),
            )
        )
        # size the application, default app screen size comes from the sylesheets master_colors.ini file
        df_scrn_sz = get_default_screen_size()
        if df_scrn_sz[0] != None:
            self.setGeometry(10, 100, df_scrn_sz[0], df_scrn_sz[1])
        self.qssheet = get_style()

        # Future: roughed in here is the basics of a future login where the information provided to the user
        # will be based on some authenticated login so that more low level information can be provided to staff
        auto_login = True
        self.loginWdgt = loginWidget(
            usr_acct_manager, auto_login=auto_login, parent=self
        )
        if auto_login:
            self.active_user = self.loginWdgt.get_user_obj()
            _logger.info("%s succesful logged in" % self.active_user.get_username())
            _logger.info("Active user data dir : %s" % self.active_user.get_data_dir())

        MAIN_OBJ.set("APP.USER", self.active_user)

        self._set_scan_btns.connect(self.on_set_scan_btns)
        self.single_energy = True

        self.data = []
        self.rvrsddata = []
        self.shorcuts = self._define_global_shortcuts()
        self.scan_tbox_widgets = []
        self.scan_pluggin = None
        self._toolbox_ids = {}
        self._pref_panels = {}
        self._dcs_server_msg_headers = {}

        self.scan_in_progress = False
        self.image_started = False

        if MAIN_OBJ.device("DNM_RING_CURRENT"):
            self.ring_ma = MAIN_OBJ.device("DNM_RING_CURRENT").get_ophyd_device()
        else:
            self.ring_ma = 0.0

        # self.vidTimer = QtCore.QTimer()
        # self.vidTimer.timeout.connect(self.on_video_timer)

        self.scan_elapsed_timer = QtCore.QTimer()
        self.scan_elapsed_timer.timeout.connect(self.on_elapsed_timer_to)
        self.elapsed_time = 0
        self.non_re_scan_progress.connect(self.on_scan_progress)

        self.integrate.connect(self.do_integrations)

        self.update_rois.connect(self.on_update_rois)
        self.roi_spec_changed.connect(self.add_to_roi_stack_spec_plot)

        self.setup_main_gui()
        self.setup_image_plot()
        self.setup_spectra_plot()
        self.setup_chartmode_plot()
        self.setup_stack_rois_plot()

        # In most cases, when (un)docking multiple widgets from the same area, they may take up an annoying
        # amount of space. By resizing to "zero", when floated, the necessary space is used; when docked, a
        # sensible resize is done with regards to the other docked items. Default sizing can be set here, or
        # using the minimumSize Qt property and/or minimum sizes of child items.
        self.dockWidget_Counts.topLevelChanged.connect(lambda _: self.left_dock_resize(self.dockWidget_Counts))
        self.dockWidget_Beamline.topLevelChanged.connect(lambda _: self.left_dock_resize(self.dockWidget_Beamline))
        self.dockWidget_Endstation.topLevelChanged.connect(lambda _: self.left_dock_resize(self.dockWidget_Endstation))
        self.dockWidget_Info.topLevelChanged.connect(lambda _: self.dockWidget_Info.resize(0, 0))
        self.dockWidget_Configuration.topLevelChanged.connect(lambda _: self.dockWidget_Configuration.resize(0, 0))
        self.dockWidget_Data.topLevelChanged.connect(lambda _: self.dockWidget_Data.resize(0, 0))

        # After being closed/hidden, widgets should be always opened in their docked location.
        self.dockWidget_Counts.visibilityChanged.connect(
            lambda vis: self.on_dockwidget_visibility_changed(self.dockWidget_Counts, vis)
        )
        self.dockWidget_Beamline.visibilityChanged.connect(
            lambda vis: self.on_dockwidget_visibility_changed(self.dockWidget_Beamline, vis)
        )
        self.dockWidget_Endstation.visibilityChanged.connect(
            lambda vis: self.on_dockwidget_visibility_changed(self.dockWidget_Endstation, vis)
        )
        self.dockWidget_Info.visibilityChanged.connect(
            lambda vis: self.on_dockwidget_visibility_changed(self.dockWidget_Info, vis)
        )
        self.dockWidget_Configuration.visibilityChanged.connect(
            lambda vis: self.on_dockwidget_visibility_changed(self.dockWidget_Configuration, vis)
        )
        self.dockWidget_Data.visibilityChanged.connect(
            lambda vis: self.on_dockwidget_visibility_changed(self.dockWidget_Data, vis)
        )
        self.dockWidget_Status.visibilityChanged.connect(
            lambda vis: self.on_dockwidget_visibility_changed(self.dockWidget_Status, vis)
        )
        self.status_label = EngineLabel(self.scanActionLbl)

        MAIN_OBJ.engine_widget.engine.exec_result.connect(self.on_execution_status_changed)
        MAIN_OBJ.engine_widget.prog_changed.connect(self.on_run_engine_progress)
        MAIN_OBJ.engine_widget.msg_to_app.connect(self.on_dcs_msg_to_app)
        MAIN_OBJ.engine_widget.new_data.connect(self.on_new_dcs_server_data)

        self.status_label.connect_to_engine(MAIN_OBJ.engine_widget.engine)

        self.rr = None
        self.rr_id = None

        # beam spot feedback dispatcher
        # self.bmspot_fbk_obj = BeamSpotFeedbackObj(MAIN_OBJ)
        # self.bmspot_fbk_obj.new_beam_pos.connect(self.on_new_beamspot_fbk)
        _cam_en = MAIN_OBJ.get_preset_as_bool("enabled", "CAMERA")
        if _cam_en:
            if int(_cam_en) == 1:
                self.setup_calib_camera(
                    MAIN_OBJ.get_preset_as_float("scaling_factor", "CAMERA")
                )

        if LOAD_ALL:
            self.setup_video_panel()

        if LOAD_ALL:
            self.setup_preferences_panel()

        self.shutterFbkLbl = ophyd_biLabelWidget(
            MAIN_OBJ.device("DNM_SHUTTER"),
            labelWidget=self.shutterFbkLbl,
            hdrText="Shutter",
            title_color="white",
            options=dict(state_clrs=["black", "black"]),
            background_widget=self.shutterBackPanel
        )
        self.shutterFbkLbl.setStyleSheet("")
        #check the flag to see if we are automatically handling the resetting of the shutter control back to 0 ->Auto
        if MAIN_OBJ.device("DNM_SHUTTER").reset_to_default:
            self.shutterFbkLbl.binary_change.connect(self.on_shutter_fbk_changed)

        self.init_beamstatus()

        self.status_dict = {}

        if LOAD_ALL:
            # RUSS FEB25 self.splash.show_msg('Initializing status bar')
            # self.splash.show_msg('Initializing status bar')
            self.init_statusbar()

        self.scan = None
        self.dwell = 0

        # a variable to hold the list of ev_rois for current scan
        self.ev_rois = None
        self.cur_ev_idx = 0
        self.cur_sp_rois = {}
        self.cur_dets = []
        # self.e_roi_queue = Queue.Queue()

        self.ySetpoints = None
        self.xSetpoints = None
        self.npointsX = 0
        self.npointsY = 0

        self.accRange = 0
        self.dccRange = 0

        self.stopping = False
        self.validate_saved_files = {"uname": "", "pword": "", "doit": False}

        # self.init_all_scans()
        self.previousScanType = None

        self._threadpool = QtCore.QThreadPool()

        self._roi_queue = queue.Queue()

        # RUSS FEB25 self.splash.show_msg('Loading scan plugins')
        # self.splash.show_msg('Loading scan plugins')
        self.setup_scan_toolbox()
        self.scan_panel_idx = self.scanTypeStackedWidget.currentIndex()
        self.scan_tbox_widgets[self.scan_panel_idx].set_zp_focus_mode()
        self._scan_type = self.scan_tbox_widgets[self.scan_panel_idx].type
        self._scan_sub_type = self.scan_tbox_widgets[self.scan_panel_idx].sub_type

        self.set_buttons_for_starting()

        bright = master_colors["btn_danger_bright"]["rgb_str"]
        dark = master_colors["btn_danger_dark"]["rgb_str"]
        self.emergStopAllBtn.setStyleSheet(f"border: 4px solid {dark}; color: {bright}")
        self.emergStopAllBtn.clicked.connect(self.on_emergency_stop)

        # Install event filter for all child widgets for debugging
        # event_filter = MouseOverEventFilter()
        # for child_widget in self.findChildren(QtWidgets.QWidget):
        #     child_widget.installEventFilter(event_filter)
        # .children()
        if MAIN_OBJ.get_device_backend() == 'epics':
            # force a loading of the data
            self.contact_sheet.on_refresh_clicked()

        # self.splash.show_msg('initialization done')
        self.enable_energy_change(True)

    def on_update_rois(self, dct):
        """
        handles when the rois need to be updated

        - retrieves the current list of roi tuples
        - does integration and averaging of each
        - emits another signal so that the roi spec plotter can be updated

        """
        # print(f"on_update_rois: put_nowait_into queue =>{dct}")
        self._roi_queue.put_nowait(dct)

    def on_shutter_fbk_changed(self, obj):
        """
        a function to make sure that the feedback and the combo button are synchronized if the
        shutter is closed outside of pyStxm

        0 = AUTO
        1 = OPEN
        2 = CLOSED

        obj = {'val': 0, 'val_str': 'CLOSED', 'val_clr': 'black', 'lbl': <cls.devWidgets.ophydLabelWidget.ophyd_biLabelWidget object at 0x000002204244CDC0>}
        @param obj:
        @return:
        """
        self.shutterCntrlComboBox.blockSignals(True)
        # set button to Auto
        self.shutterCntrlComboBox.setCurrentIndex(0)
        self.shutterCntrlComboBox.blockSignals(False)

    def setup_preferences_panel(self):
        """
        walk a directory where the preferences are kept and load the combobox and stacked widget
        :return:
        """

        self._pref_panels = {}
        # import importlib

        _dirs = os.listdir(prefsDir)

        idx = 0
        for dir in _dirs:
            if dir.find(".py") < 0:
                # get files in pref dir
                _files = os.listdir(os.path.join(prefsDir, dir))
                if "loader.py" in _files:
                    _filepath = os.path.join(prefsDir, dir, "loader.py")
                    if os.path.exists(_filepath):
                        # _mod = importlib.load_source('mod_classname', _filepath)
                        _mod = SourceFileLoader(
                            "mod_classname", _filepath
                        ).load_module()
                        _mod_filepath = os.path.join(prefsDir, dir, _mod.mod_file)
                        # _cls = importlib.load_source(_mod.mod_classname, _mod_filepath)
                        _cls = SourceFileLoader(
                            "mod_classname", _mod_filepath
                        ).load_module()
                        # create an instance of the class
                        _inst = eval("_cls.%s()" % _mod.mod_classname)
                        wdg = QtWidgets.QWidget()
                        _lyt = QtWidgets.QVBoxLayout()
                        _lyt.addWidget(_inst)
                        wdg.setLayout(_lyt)
                        self.apply_stylesheet(wdg, self.qssheet)
                        self.prefsStackedWidget.insertWidget(idx, wdg)
                        # RUSS FEB25 self.splash.show_msg('Loading %s preferences widget' % _mod.mod_file)
                        # self.splash.show_msg('Loading %s preferences widget' % _mod.mod_file)

                        self.prefsComboBox.addItem(_mod.mod_hdr_name, idx)
                        self.prefsComboBox.currentIndexChanged.connect(
                            self.on_preference_changed
                        )

                        self._pref_panels[_cls.mod_classname] = _inst
                        idx += 1

    def get_pref_panel(self, pref_nm):
        if pref_nm in self._pref_panels.keys():
            return self._pref_panels[pref_nm]
        else:
            _logger.error("Pref panel [%s] does not exist" % pref_nm)

    def left_dock_resize(self, widget: QtWidgets.QDockWidget):
        widget.resize(0, 0)
        # also resize the E-STOP widget to take minimum space
        self.dockWidget_StopAll.resize(0, 0)

    def on_dockwidget_visibility_changed(self, widget: QtWidgets.QDockWidget, visible: bool):
        # ensure widget goes back to the dock when closed->reopened
        if not visible and widget.isFloating():
            widget.setFloating(False)

    def on_preference_changed(self, idx):
        self.prefsStackedWidget.setCurrentIndex(idx)
        w = self.prefsStackedWidget.currentWidget()
        children_wdgs = w.children()
        for ch in children_wdgs:
            if hasattr(ch, "on_plugin_focus"):
                ch.on_plugin_focus()

    def on_new_beamspot_fbk(self, cx, cy):
        """
        the beam spot object has emitted a new center x/y so let the plotter know
        :param cx:
        :param cy:
        :return:
        """

        # todo:: need to skip this if the tool is not visible
        # print('on_new_beamspot_fbk: (%.2f, %.2f)' % (cx, cy))
        # self.lineByLineImageDataWidget.move_beam_spot(cx, cy)
        pass

    def set_zp_focus_mode(self, mode=None):
        """
        this function sets the mode that controls how the positions for Zpz and Cz are calculated.
        this function is called when the user switches to a new scan in the scans toolbox
        """
        if MAIN_OBJ.get_beamline_id() is BEAMLINE_IDS.STXM:
            zpz_scanflag = MAIN_OBJ.device("DNM_ZONEPLATE_SCAN_MODE")
            zpz_scanflag.put("user_setpoint", mode)

    def allow_feedback(self):
        if hasattr(self, "esPosPanel"):
            self.esPosPanel.enable_feedback()
        if hasattr(self, "blPosPanel"):
            self.blPosPanel.enable_feedback()

    def load_simulated_image_data(self):
        global SIMULATE_IMAGE_DATA, SIM_DATA

        SIMULATE_IMAGE_DATA = True
        SIM_DATA = self.lineByLineImageDataWidget.get_current_data()
        _logger.info("Loaded Simulated data")

    def start_epics_tasks(self):
        """
        start_epics_tasks(): description

        :returns: None
        """
        MAIN_OBJ.device("ShutterTaskRun").put(1)

    def on_update_style(self):
        """
        on_update_style(): description

        :returns: None
        """
        """ handler for interactive button """
        # self.set_style_timer.stop()
        self.qssheet = get_style(force=True)
        self.setStyleSheet(self.qssheet)
        self.apply_stylesheet(self.centralwidget, self.qssheet)
        self.update_plot_colors()
        self.allow_feedback()
        self.clear_plugin_stylesheets()
        _logger.info("Read stylesheets and updated style")

    def clear_plugin_stylesheets(self):
        """
        a function that will call an API function so that any plugin can undo a global stylesheet
        not sure this actually undoes any style sheet setting, not sure why
        @return:
        """
        for plugin in self.scan_tbox_widgets:
            plugin.clear_stylesheet()

    def update_plot_colors(self):
        """
        update_plot_colors(): description

        :returns: None
        """

        fg_clr = master_colors["plot_forgrnd"]["rgb_hex"]
        bg_clr = master_colors["plot_bckgrnd"]["rgb_hex"]
        min_clr = master_colors["plot_gridmaj"]["rgb_hex"]
        maj_clr = master_colors["plot_gridmin"]["rgb_hex"]

        if hasattr(self, "stripToolWidget"):
            self.stripToolWidget.set_grid_parameters(bg_clr, min_clr, maj_clr)

        if hasattr(self, "lineByLineImageDataWidget"):
            self.lineByLineImageDataWidget.set_grid_parameters(bg_clr, min_clr, maj_clr)
            self.lineByLineImageDataWidget.set_cs_grid_parameters(
                fg_clr, bg_clr, min_clr, maj_clr
            )

        if hasattr(self, "spectraWidget"):
            self.spectraWidget.set_grid_parameters(bg_clr, min_clr, maj_clr)

    def apply_stylesheet(self, widget, ssheet):
        """
        apply_stylesheet(): description

        :param widget: widget description
        :type widget: widget type

        :param ssheet: ssheet description
        :type ssheet: ssheet type

        :returns: None
        """
        # for some reason the stysheet isnt picked up by the central widget and centralFrame so force it here
        widget.setStyleSheet(ssheet)

    def add_to_log(self, clr, msg):
        """
        add_to_log(): description

        :param clr: clr description
        :type clr: clr type

        :param msg: msg description
        :type msg: msg type

        :returns: None
        """
        """
            This is a signal handler that is connected to the logger so that
            messages sent to the logger are  then displayed by this apps loggin
            widget, color is supported for the varying levels of message logged
        """
        if clr is not None:
            self.logWindow.setTextColor(clr)
        self.logWindow.append(msg)

    def add_to_dcs_server_window(self, clr, msg):
        """
            This is a function that is called so that
            messages sent to the logger are  then displayed by this apps loggin
            widget, color is supported for the varying levels of message logged
        """
        if clr is not None:
            self.dcsServerWindow.setTextColor(clr)
        self.dcsServerWindow.append(str(msg))

    def add_exporter_msg_to_log(self, msg_dct):
        """
        from the nx_server process
        """
        # msg = str(msg_dct['status'])
        msg = str(msg_dct)
        clr = QtGui.QColor('#000000')
        if len(msg) < 50:
            self.add_to_log(clr, msg)

    def on_set_scan_btns(self, do_what):
        """
        on_set_scan_btns(): description

        :param do_what: do_what description
        :type do_what: do_what type

        :returns: None
        """
        if do_what == "SET_FOR_SCANNING":
            self.set_buttons_for_scanning()
        elif do_what == "SET_FOR_STARTING":
            self.set_buttons_for_starting()
        else:
            pass

    def set_buttons_for_scanning(self):
        """
        set_buttons_for_scanning(): description

        :returns: None
        """

        self.scan_in_progress = True
        self.startBtn.setEnabled(False)
        self.pauseBtn.setEnabled(True)
        self.mainTabWidget.setEnabled(False)

        # self.dict_based_contact_sheet.set_drag_enabled(False)

        if hasattr(self, "lineByLineImageDataWidget"):
            # self.scan_tbox_widgets[self.scan_panel_idx].set_read_only()
            self.lineByLineImageDataWidget.set_enable_drop_events(False)
            # do not allow user to delete currently acquiring image
            self.lineByLineImageDataWidget.enable_menu_action("Clear Plot", False)

    def enable_disable_scan_btns(self, enable=False):
        """
        disable the buttons if the user is not on the scans_tab
        """
        if enable:
            self.startBtn.setEnabled(True)
            self.pauseBtn.setEnabled(True)
            self.stopBtn.setEnabled(True)
        else:
            self.startBtn.setEnabled(False)
            self.pauseBtn.setEnabled(False)
            self.stopBtn.setEnabled(False)


    def set_buttons_for_starting(self):
        """
        set_buttons_for_starting(): description

        :returns: None
        """
        self.scan_elapsed_timer.stop()
        self.scan_in_progress = False
        self.startBtn.setEnabled(True)
        self.pauseBtn.setEnabled(False)
        self.pauseBtn.setChecked(False)
        self.mainTabWidget.setEnabled(True)

        if hasattr(self, "dict_based_contact_sheet"):
            self.contact_sheet.set_drag_enabled(True)
        if hasattr(self, "lineByLineImageDataWidget"):
            self.lineByLineImageDataWidget.set_enable_drop_events(True)
            # allow user to delete currently acquiring and any other images
            self.lineByLineImageDataWidget.enable_menu_action("Clear Plot", True)

    def init_all_scans(self):
        """
        init_all_scans(): description

        """
        # ensure a connection to dcs values so that the forst data collection goes smooth
        _logger.debug("intializing DCS connections")
        posner_devs = MAIN_OBJ.get_devices_in_category("POSITIONERS")
        detector_devs = MAIN_OBJ.get_devices_in_category("DETECTORS")
        pv_devs = MAIN_OBJ.get_devices_in_category("PVS")
        d = MAIN_OBJ.take_positioner_snapshot(posner_devs)
        d = MAIN_OBJ.take_detectors_snapshot(detector_devs)
        d = MAIN_OBJ.take_pvs_snapshot(pv_devs)
        _logger.debug("intializing DCS connections: Done")

        # self.imageSCAN.stop()
        # self.pointSCAN.stop()
        # self.focusSCAN.stop()

    def closeEvent(self, event):
        """
        closeEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        result = QtWidgets.QMessageBox.question(
            self,
            "Confirm Exit...",
            "Are you sure you want to exit ?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        event.ignore()

        if result == QtWidgets.QMessageBox.Yes:
            self.enable_energy_change(False)
            event.accept()

    def enable_energy_change(self, en):
        # devices = MAIN_OBJ.get_devices()
        # ev_en = devices['PVS'][DNM_ENERGY_ENABLE]
        ev_en = MAIN_OBJ.device("DNM_ENERGY_ENABLE")
        zpz = MAIN_OBJ.device("DNM_ZONEPLATE_Z")

        if ev_en:
            if en:
                ev_en.put(1)
                # enable Zoneplate Z servo
                if zpz:
                    zpz.put("use_torque", 1)
                    zpz.put("disabled", 0)  # GO
            else:
                # park energy change enabled
                ev_en.put(0)
                # disable Zoneplate Z servo
                if zpz:
                    zpz.put("use_torque", 0)
                    zpz.put("disabled", 1)  # STOP

    # def on_edit_zp_params(self):
    #     """
    #     on_edit_zp_params(): description
    #
    #     :returns: None
    #     """
    #
    #     #self.fpForm.show()
    #     self.fpForm = FocusParams(self)
    #     self.apply_stylesheet(self.fpForm, self.qssheet)
    #     self.fpForm.show()

    def on_about_pystxm(self):
        self.aboutForm = uic.loadUi(os.path.join(uiDir, "pyStxm_about.ui"))
        self.aboutForm.okBtn.clicked.connect(self.aboutForm.close)
        ver_str = "version %s.%s %s" % (
            MAIN_OBJ.get("APP.MAJOR_VER"),
            MAIN_OBJ.get("APP.MINOR_VER"),
            MAIN_OBJ.get("APP.DATE"),
        )
        self.aboutForm.versionLbl.setText(ver_str)
        # self.apply_stylesheet(self.aboutForm, self.qssheet)
        self.apply_stylesheet(
            self.aboutForm,
            "QDialog{ background-color: %s ;}"
            % master_colors["master_background_color"]["rgb_str"],
        )
        self.aboutForm.show()

    def on_pystxm_help(self):
        webbrowser.open(docs_path)

    def on_switch_user(self):
        pass

    def _define_global_shortcuts(self):

        shortcuts = []

        # sequence = {
        #     'Ctrl+Shift+Left': self.on_action_previous_comic_triggered,
        #     'Ctrl+Left': self.on_action_first_page_triggered,
        #     'Left': self.on_action_previous_page_triggered,
        #     'Right': self.on_action_next_page_triggered,
        #     'Ctrl+Right': self.on_action_last_page_triggered,
        #     'Ctrl+Shift+Right': self.on_action_next_comic_triggered,
        #     'Ctrl+R': self.on_action_rotate_left_triggered,
        #     'Ctrl+Shift+R': self.on_action_rotate_right_triggered,
        # }

        sequence = {
            "Ctrl+U": self.on_update_style,
        }

        for key, value in list(sequence.items()):
            s = QtWidgets.QShortcut(QtGui.QKeySequence(key), self, value)
            s.setEnabled(True)
            shortcuts.append(s)

        return shortcuts

    def set_widget_background_color(self, widget, r, g, b):
        """
        set a widgets background color directly
        """
        from PyQt5.QtGui import QPalette, QColor
        color = QColor(r, g, b)  # Red color
        palette = widget.palette()
        palette.setColor(QPalette.Background, color)
        widget.setPalette(palette)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            # print("Left button pressed")
            pass
        elif event.button() == QtCore.Qt.MouseButton.RightButton:
            # print("Right button pressed")
            pass
        elif event.button() == QtCore.Qt.MouseButton.MiddleButton:
            print("\n\nMiddle button pressed")
            widget = self.childAt(event.pos())
            # print("Clicked on widget:", widget)
            self.get_children_of_widget(widget)

    def get_widget_color(self, widget, num_tabs):
        from PyQt5.QtGui import QPalette
        tab_str = "".join("\t" for x in range(num_tabs + 1))
        # Retrieve the palette of the widget
        if hasattr(widget, "palette"):
            palette = widget.palette()
            # Get the foreground and background color of the widget
            foreground_color = palette.color(QPalette.Foreground)
            background_color = palette.color(QPalette.Background)
            # Print out the color
            print(f"{tab_str}Foreground color :", color_str_as_hex(foreground_color.name()), foreground_color.name())
            print(f"{tab_str}Background color :", color_str_as_hex(background_color.name()), background_color.name())

    def get_children_of_widget(self, widget, num_tabs=0):
        """
        walk the children of a widget and print the background color
        """
        tab_str = "".join("\t" for x in range(num_tabs))
        if not hasattr(widget, "objectName"):
            return ([])
        if len(widget.objectName()) > 0:
            print(f"{tab_str}The children of the widget[***** {widget.objectName()} ******]: ", widget)
        else:
            print(f"{tab_str}The children of the widget[NO_OBJ_NAME]: ", widget)
        self.get_widget_color(widget, num_tabs)
        children = widget.children()
        for child in children:
            _children = child.children()
            if len(_children) > 0:
                self.get_children_of_widget(child, num_tabs + 1)
            else:
                tab_str = "".join("\t" for x in range(num_tabs))
                if len(child.objectName()) > 0:
                    print(f"{tab_str} child[***** {child.objectName()} *****]: ", child)
                else:
                    print(f"{tab_str} child[NO_OBJ_NAME]: ", child)
                self.get_widget_color(child, num_tabs)

    def setup_main_gui(self):
        """
        setup_main_gui(): description

        :returns: None
        """
        self.mainTabWidget.currentChanged.connect(self.on_main_tab_changed)
        self.mainTabWidget.tabBarClicked.connect(self.on_main_tab_changed)
        # self.statusBar = QtWidgets.QStatusBar()
        # self.layout().addWidget(self.statusBar)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.MinimumExpanding)

        self.actionExit.triggered.connect(self.close)
        # self.actionZP_Params.triggered.connect(self.on_edit_zp_params)
        self.actionAbout_pyStxm.triggered.connect(self.on_about_pystxm)
        self.actionpyStxm_help.triggered.connect(self.on_pystxm_help)
        self.actionSwitch_User.triggered.connect(self.on_switch_user)
        # self.actionDisplay_DCSServer_msgs.triggered.connect(self.on_show_dcs_server_msgs)
        self.dcsServerWindow.contextMenuEvent = self.dcsServerWindow_ContextMenuEvent

        if MAIN_OBJ.get_device_backend() == 'epics':
            # only connect it if running BlueSky RunEngine
            self.actionDisplay_RunEngine_docs.triggered.connect(self.on_show_runengine_docs)
            #disable DCS menu item
            self.actionDisplay_DCSServer_msgs.setEnabled(False)
            self.actionDisplay_DCSServer_msgs.setChecked(False)
        else:
            # disable BS RE docs menu item
            self.actionDisplay_RunEngine_docs.setEnabled(False)
            self.actionDisplay_RunEngine_docs.setChecked(False)

            # enable DCS messages being available in Info tab
            self.actionDisplay_DCSServer_msgs.setEnabled(True)
            self.actionDisplay_DCSServer_msgs.setChecked(True)
            reconnect_signal(
                MAIN_OBJ.engine_widget.engine,
                MAIN_OBJ.engine_widget.engine.msg_changed,
                self.print_dcs_server_msg,
            )


        self.actionValidate_saved_files.triggered.connect(self.on_validate_saved_files)
        self.actionResume_Motors.triggered.connect(self.on_resume_from_emergency_stop)

        self.menuView.addActions(self.createPopupMenu().actions())

        self.startBtn.clicked.connect(self.on_start_scan)
        self.pauseBtn.clicked.connect(self.on_pause)
        self.stopBtn.clicked.connect(self.on_stop)

        # DNM_DFLT_PMT_DWELL is in ms
        # _pmt_dwell = 1.0 / (MAIN_OBJ.device("DNM_DFLT_PMT_DWELL").get() / 1000.0)
        self.stripToolWidget = StripToolWidget(1, sigList=[MAIN_OBJ.device(MAIN_OBJ.default_detector)],
                                               #energy_fbk_dev=MAIN_OBJ.device("DNM_MONO_EV_FBK"),
                                             energy_fbk_dev=MAIN_OBJ.device("DNM_ENERGY"),
                                               labelHeader="Energy:",
                                               parent=self,
                                               scale_factor=10)
        self.stripToolWidget.setObjectName("stripToolWidget")
        plot = self.stripToolWidget.scanplot.get_plot()
        pcan = plot.canvas()
        pcan.setObjectName("stripToolWidgetCanvasBgrnd")
        # self.stripToolWidget.scanplot.plot.setTitle('stripToolPlot')
        # self.get_children_of_widget(self.stripToolWidget)

        self.enable_detfbk = False
        self.enable_osafbk = False

        if LOAD_ALL:
            # self.sample_selector = SampleSelectorWidget(scaler=0.80, parent=self)
            #
            # hbox = QtWidgets.QHBoxLayout()
            # hbox.addWidget(self.sample_selector)
            # hbox.setContentsMargins(0, 0, 0, 0)
            # hbox.addStretch()
            # self.sampleSelFrame.setLayout(hbox)

            if hasattr(self, "stripToolWidget"):
                vbox2 = QtWidgets.QVBoxLayout()
                vbox2.addWidget(self.stripToolWidget)
                vbox2.setContentsMargins(1, 1, 1, 1)
                self.counterPlotFrame.setLayout(vbox2)

            # endstation positioners panel
            dev_obj = MAIN_OBJ.get_device_obj()
            exclude_list = dev_obj.get_exclude_positioners_list()
            es_posners = MAIN_OBJ.get_devices_in_category(
                "POSITIONERS", pos_type="POS_TYPE_ES"
            )
            self.esPosPanel = PositionersPanel(es_posners, exclude_list, parent=self, main_obj=MAIN_OBJ)
            self.esPosPanel.setObjectName("esPosPanel")
            # spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            spacer = QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
            )
            vbox3 = QtWidgets.QVBoxLayout()
            vbox3.addWidget(self.esPosPanel)
            vbox3.addItem(spacer)

            # horizontal line
            hline = QtWidgets.QFrame()
            hline.setFrameShape(QtWidgets.QFrame.HLine)
            hline.setFrameShadow(QtWidgets.QFrame.Sunken)
            # add the line twice
            self.esPosPanel.append_widget_to_positioner_layout(hline)
            self.esPosPanel.append_widget_to_positioner_layout(hline)

            # add Zpz change on energy button
            ev_en_dev = dev_obj.device("DNM_ENERGY_ENABLE")
            if ev_en_dev:
                self.esPosPanel.append_toggle_btn_device(
                    "  FL change with Energy  ",
                    "Enable the Focal Length (FL==Zpz stage) to move to new focal length based on Energy",
                    ev_en_dev,
                    off_val=0,
                    on_val=1,
                    fbk_dev=ev_en_dev,
                    off_str="Disabled",
                    on_str="Enabled",
                )

            # add the beam defocus device
            defoc_dev = dev_obj.device("DNM_BEAM_DEFOCUS")
            if defoc_dev:
                _min = 0.0
                _max = 5000
                self.esPosPanel.append_setpoint_device(
                    "  Defocus spot size by  ",
                    "Defocus the beam as a function of beamspot size (um)",
                    "um",
                    defoc_dev,
                    _min,
                    _max,
                    prec=2
                )

            # add the OSA vertical tracking device
            osay_track_dev = dev_obj.device("DNM_OSAY_TRACKING")
            if osay_track_dev:
                self.esPosPanel.append_toggle_btn_device(
                    "  OSA vertical tracking  ",
                    "Toggle the OSA vertical tracking during zoneplate scanning",
                    osay_track_dev,
                    off_val=0,
                    on_val=1,
                    fbk_dev=osay_track_dev,
                    off_str="Off",
                    on_str="On",
                )

            # add the Focusing Mode
            foc_mode_dev = dev_obj.device("DNM_ZONEPLATE_SCAN_MODE")

            if foc_mode_dev:
                self.esPosPanel.append_toggle_btn_device(
                    "  Focal length mode  ",
                    "Toggle the focal length mode from Sample to OSA focused",
                    foc_mode_dev,
                    fbk_dev=foc_mode_dev,
                    off_val=0,
                    on_val=1,
                    off_str="OSA Focused",
                    on_str="Sample Focused",
                    toggle=True,
                )
            # add zonplate in/out

            zp_inout_dev = dev_obj.device("DNM_ZONEPLATE_INOUT")
            if zp_inout_dev:
                zp_inout_dev_fbk = dev_obj.device("DNM_ZONEPLATE_INOUT_FBK")
                self.esPosPanel.append_toggle_btn_device(
                    " Zoneplate In/Out",
                    "Move the zonpelate Z stage all the way upstream out of the way",
                    zp_inout_dev,
                    off_val=0,
                    on_val=1,
                    off_str="Out",
                    on_str="In",
                    fbk_dev=zp_inout_dev_fbk,
                    toggle=True,
                )

            osa_inout_dev = dev_obj.device("DNM_OSA_INOUT")
            if osa_inout_dev:
                osa_inout_dev_fbk = dev_obj.device("DNM_OSA_INOUT_FBK")
                self.esPosPanel.append_toggle_btn_device(
                    " OSA In/Out",
                    "Move the OSA stage all the way out of the way",
                    osa_inout_dev,
                    off_val=0,
                    on_val=1,
                    off_str="Out",
                    on_str="In",
                    fbk_dev=osa_inout_dev_fbk,
                    toggle=True,
                )

            sample_out_dev = dev_obj.device("DNM_SAMPLE_OUT")
            if sample_out_dev:
                sample_out_dev_fbk = dev_obj.device("DNM_SAMPLE_OUT")
                self.esPosPanel.append_toggle_btn_device(
                    " Sample In/Out",
                    "Move the sample all the way out of the way",
                    sample_out_dev,
                    off_val=0,
                    on_val=1,
                    off_str="Out",
                    on_str="In",
                    toggle=False,
                )


            rset_intfer_dev = dev_obj.device("DNM_RESET_INTERFERS")
            if rset_intfer_dev:
                self.esPosPanel.append_toggle_btn_device(
                    "  Reset Interferometers  ",
                    "Reset Interferometer positions to coarse positions",
                    rset_intfer_dev,
                    off_val=0,
                    on_val=1,
                    off_str="Start",
                    on_str="Start",
                    toggle=False,
                )

            atz_sfx_dev = dev_obj.device("DNM_SFX_AUTOZERO")
            if atz_sfx_dev:
                self.esPosPanel.append_toggle_btn_device(
                    "  ATZ fx  ",
                    "AutoZero Sample Fine X",
                    atz_sfx_dev,
                    off_val=0,
                    on_val=1,
                    off_str="Start",
                    on_str="Stop",
                    toggle=False,
                )
            atz_sfy_dev = dev_obj.device("DNM_SFY_AUTOZERO")
            if atz_sfy_dev:
                self.esPosPanel.append_toggle_btn_device(
                    "  ATZ fy  ",
                    "AutoZero Sample Fine Y",
                    atz_sfy_dev,
                    off_val=0,
                    on_val=1,
                    off_str="Start",
                    on_str="Stop",
                    toggle=False,
                )

            gating_dev = MAIN_OBJ.device('DNM_GATING')
            if gating_dev:
                self.esPosPanel.append_combobox_device(
                    "  Gating  ",
                    gating_dev.desc,
                    gating_dev,
                    gating_dev.fbk_enum_strs,
                    gating_dev.fbk_enum_values,
                    cb=None
                )

            fcs_mode_dev = MAIN_OBJ.device('DNM_FOCUS_MODE')
            if fcs_mode_dev:
                self.esPosPanel.append_combobox_device(
                    "  Focus  ",
                    fcs_mode_dev.desc,
                    fcs_mode_dev,
                    fcs_mode_dev.fbk_enum_strs,
                    fcs_mode_dev.fbk_enum_values,
                    cb=None
                )
            self.endstationPositionersFrame.setLayout(vbox3)

            # #beamline positioners panel
            bl_posners = MAIN_OBJ.get_devices_in_category(
                "POSITIONERS", pos_type="POS_TYPE_BL"
            )
            self.blPosPanel = PositionersPanel(bl_posners, parent=self, main_obj=MAIN_OBJ)
            self.blPosPanel.setObjectName("blPosPanel")
            # spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            spacer = QtWidgets.QSpacerItem(
                1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
            )
            vbox4 = QtWidgets.QVBoxLayout()
            vbox4.addWidget(self.blPosPanel)
            vbox4.addItem(spacer)
            self.beamlinePositionersFrame.setLayout(vbox4)

            # temperatures panel
            temps = MAIN_OBJ.get_devices_in_category(
                "TEMPERATURES", pos_type="POS_TYPE_ES"
            )
            if temps:
                self.esTempPanel = DevsPanel(temps, egu="deg C", parent=None)
                self.esTempPanel.setObjectName("esTempPanel")
                # self.esTempPanel = TemperaturesPanel(POS_TYPE_ES)
                # spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
                spacer = QtWidgets.QSpacerItem(
                    1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
                )
                vbox5 = QtWidgets.QVBoxLayout()
                vbox5.addWidget(self.esTempPanel)
                vbox5.addItem(spacer)
                self.esTempsFrame.setLayout(vbox5)
            #
            # ES pressures panel
            presrs = MAIN_OBJ.get_devices_in_category(
                "PRESSURES", pos_type="POS_TYPE_ES"
            )
            if presrs:
                self.esPressPanel = DevsPanel(
                    presrs, egu="Torr", engineering_notation=True, parent=None
                )
                self.esPressPanel.setObjectName("esPressPanel")
                # self.esTempPanel = TemperaturesPanel(POS_TYPE_ES)
                # spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
                spacer = QtWidgets.QSpacerItem(
                    1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
                )
                vbox6 = QtWidgets.QVBoxLayout()
                vbox6.addWidget(self.esPressPanel)
                vbox6.addItem(spacer)
                self.esPressuresFrame.setLayout(vbox6)

            # BL pressures panel
            bl_presrs = MAIN_OBJ.get_devices_in_category(
                "PRESSURES", pos_type="POS_TYPE_BL"
            )
            #only show if there are pressure devices
            if bl_presrs:
                bl_presrs = self.sort_by_desc(bl_presrs)

                self.blPressPanel = DevsPanel(
                    bl_presrs, egu="Torr", engineering_notation=True, parent=None
                )
                self.blPressPanel.setObjectName("blPressPanel")
                spacer = QtWidgets.QSpacerItem(
                    1, 1, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
                )
                vbox7 = QtWidgets.QVBoxLayout()
                vbox7.addWidget(self.blPressPanel)
                vbox7.addItem(spacer)
                self.blPressuresFrame.setLayout(vbox7)

            # tools panel
            #             self.toolsPanel = ToolsPanel()
            #             spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            #             vbox4 = QtWidgets.QVBoxLayout()
            #             vbox4.addWidget(self.toolsPanel)
            #             vbox4.addItem(spacer)
            #             self.toolsPositionersFrame.setLayout(vbox4)

            # self.detectorsPanel = DetectorsPanel(self)
            # spacer = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            # vbox5 = QtWidgets.QVBoxLayout()
            # vbox5.addWidget(self.detectorsPanel)
            # vbox5.addItem(spacer)
            # self.detectorsFrame.setLayout(vbox5)

        # self.load_dir_view()
        self.pythonshell = None
        shutter_dev = MAIN_OBJ.device('DNM_SHUTTER')
        if shutter_dev:
            # get the shutter control modes strings and populate the combobox
            self.shutterCntrlComboBox.addItems(shutter_dev.ctrl_enum_strs)
        else:
            _logger.error("The device database does not contain a DNM_SHUTTER")

        self.shutterCntrlComboBox.currentIndexChanged.connect(
            self.on_shutterCntrlComboBox
        )
        idx = self.shutterCntrlComboBox.currentIndex()
        self.on_shutterCntrlComboBox(0)  # Auto

        self.scan_progress_table = ScanQueueTableWidget(parent=self)
        self.scanQFrame.layout().addWidget(self.scan_progress_table)

        # initialize the thumbnail viewer
        self.init_images_frame()

        #self.init_ptycho_data_viewer()

        # load the app status panel
        self.setup_select_detectors_frame()

        # self.check_if_pv_exists()

    def check_if_pv_exists(self):
        dev_obj = MAIN_OBJ.get_device_obj()
        psner_dct = dev_obj.devices["POSITIONERS"]
        posner_names = list(psner_dct.keys())

        print("checking for existance of pvs:")
        from epics import cainfo

        for k in posner_names:
            pv = psner_dct[k]
            pv_name = pv.get_name()
            print("checking [%s]: <%s>" % (pv_name, cainfo(pv_name)))

    def sort_by_desc(self, devs):
        """
        sort the device dictionary by description and return the devices as a list sorted by description
        :param devs:
        :return:
        """
        from cls.utils.dict_utils import sort_str_list

        desc_lst = []
        dev_dct = {}
        sorted_dev_lst = []
        for d_k in list(devs.keys()):
            desc = devs[d_k].get_desc()
            desc_lst.append(desc)
            dev_dct[desc] = devs[d_k]

        sorted_desc_lst = sort_str_list(desc_lst)

        for s_d in sorted_desc_lst:
            sorted_dev_lst.append(dev_dct[s_d])
        return sorted_dev_lst

    def on_main_tab_changed(self, index):
        w = self.mainTabWidget.currentWidget()
        w_ch = w.children()
        for ch in w_ch:
            self.walk_children_for_on_focus_event(ch)

        # only allow a user to click scan if they are on the scan tab
        current_tab_widget = self.mainTabWidget.widget(index)
        current_tab_name = current_tab_widget.objectName()
        if current_tab_name == "tab_scans":
            self.enable_disable_scan_btns(True)
        else:
            self.enable_disable_scan_btns(False)

    def walk_children_for_on_focus_event(self, widg):
        w_ch = widg.children()
        for ch in w_ch:
            if hasattr(ch, "on_plugin_focus"):
                ch.on_plugin_focus()
                break
            self.walk_children_for_on_focus_event(ch)

    def setup_select_detectors_frame(self):
        """
        add all of the current selected detectors to the panel
        :return:
        """
        self.sel_detectors_panel = DetectorsPanel(sel_changed_cb=self.on_selected_detectors_changed)

        # ioc_apps_wdg = IOCAppsPanel(MAIN_OBJ)
        # ioc_apps_wdg.setProperty("alertField", True)
        # ioc_apps_wdg.alert.connect(self.on_panel_alert)
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.sel_detectors_panel)

        spacer = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding
        )
        vlayout.addItem(spacer)
        self.selectDetectorsGrpBx.setLayout(vlayout)
        # tb = self.mainTabWidget.tabBar()
        # tb.paintEvent = self.ioc_apps_paintEvent

    def on_selected_detectors_changed(self, sel_det_lst):
        # print(f"stxmMain: on_selected_detectors_changed: {sel_dct}")
        MAIN_OBJ.set_selected_detectors(sel_det_lst)

    def on_panel_alert(self, alert_dct):
        from cls.appWidgets.base_content_panel import alert_lvls

        change_it = False
        alert_lvl = alert_dct["lvl"]
        tab_idx = alert_dct["tab_idx"]
        obj_name = alert_dct["obj_name"]

        if alert_lvl == alert_lvls.NORMAL:
            # no change
            pass
        elif alert_lvl == alert_lvls.WARNING:
            bg_clr = "rgb(255,255,0);"
            change_it = True
        elif alert_lvl == alert_lvls.ERROR:
            bg_clr = "rgb(255,0,0);"
            change_it = True
        else:
            _logger.error("alert level is out of range")
            bg_clr = "rgb(0,0,255);"
            change_it = True

        # if(change_it):
        #     #self.mainTabWidget.tabBar().setStyleSheet("QTabBar::tab:selected { color: #00ff00; background-color: %s}" % bg_clr)
        #     #self.mainTabWidget.tabBar().setStyleSheet("QTabBar::tab:selected { background-color: %s}" % bg_clr)
        #     self.mainTabWidget.tabBar().setStyleSheet("QTabBar::tab[currentIndex = 2] { background-color: %s}" % (bg_clr))

    def ioc_apps_paintEvent(self, event):
        p = QtWidgets.QStylePainter(self)
        painter = QtGui.QPainter(self)
        painter.save()
        for index in range(self.count()):  # for all tabs

            tabRect = self.tabRect(index)
            tabRect.adjust(-1, 3, -1, -1)  # ajust size of every tab (make it smaller)
            if index == 0:  # make first tab red
                color = QtGui.QColor(255, 0, 0)
            elif index == 1:  # make second tab yellow
                color = QtGui.QColor(255, 255, 0)
            else:  # make all other tabs blue
                color = QtGui.QColor(0, 0, 255)
            if index == self.currentIndex():  # if it's the selected tab
                color = color.lighter(
                    130
                )  # highlight the selected tab with a 30% lighter color
                tabRect.adjust(
                    0, -3, 0, 1
                )  # increase height of selected tab and remove bottom border
            brush = QtGui.QBrush(color)
            painter.fillRect(tabRect, brush)

            painter.setPen(
                QtGui.QPen(QtGui.QColor(QtCore.Qt.black))
            )  # black pen (for drawing the text)
            painter.drawText(
                tabRect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter,
                self.tabText(index),
            )

            painter.setPen(
                QtGui.QPen(QtGui.QColor(QtCore.Qt.gray))
            )  # gray pen (for drawing the border)
            painter.drawRect(tabRect)
        painter.restore()

    def init_images_frame(self):
        self.contact_sheet = ContactSheet(MAIN_OBJ,
            self.active_user.get_data_dir(), STXMDataIo, parent=self, base_data_dir=self.active_user.get_base_data_dir()
        )

        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.contact_sheet)
        self.imagesFrame.setLayout(vbox)

    def init_ptycho_data_viewer(self):
        ptycho_dev = MAIN_OBJ.device(PTYCHO_CAMERA, do_warn=False)
        if ptycho_dev:
            self.ptycho_vwr_pnl = PtychoDataViewerPanel(
                MAIN_OBJ.device(PTYCHO_CAMERA), parent=self
            )

            vbox = QtWidgets.QVBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.addWidget(self.ptycho_vwr_pnl)
            self.ptychoFrame.setLayout(vbox)
        else:
            _logger.info("Great Eyes CCD not detected so not loading CCD viewer panel")

    def on_shutterCntrlComboBox(self, idx):
        """
        on_shutterCntrlComboBox(): The Shutter device contains the list of control enumerations so
        Typically:
            0 = Auto
            1 = Open
            2 = Close
        but some bl_configs might define
        :param idx: idx description
        :type idx: idx type

        :returns: None
        """
        """ in order
        
        """
        shutter_dev = MAIN_OBJ.device("DNM_SHUTTER")

        if not shutter_dev.reset_to_default:
            # set the selected value and leave
            shutter_dev.set(idx)
        else:
            # idx = self.shutterCntrlComboBox.currentIndex()
            if idx == 0:
                # print 'setting shutter mode to AUTO'
                shutter_dev.close()
                shutter_dev.set_to_auto()

            elif idx == 1:
                # print 'setting shutter mode to MANUAL'
                shutter_dev.set_to_manual()
                shutter_dev.open()
            else:
                # print 'setting shutter mode to MANUAL'
                shutter_dev.set_to_manual()
                shutter_dev.close()

    def setup_scan_toolbox(self):

        """
        walk a directory where the preferences are kept and load the combobox and stacked widget
        :return:
        """

        # Create plugin manager
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 8, 0, 0)
        layout.setSpacing(0)

        self.scanTypeComboBox = QtWidgets.QComboBox()
        # set the object name so we can use stylesheets to control how it looks
        self.scanTypeComboBox.setObjectName("scanTypeComboBox")

        self.scanTypeStackedWidget = QtWidgets.QStackedWidget()
        self.scanTypeStackedWidget.layout().setContentsMargins(0, 0, 0, 0)
        self.scanTypeStackedWidget.layout().setSpacing(0)
        self.scanTypeComboBox.currentIndexChanged.connect(self.scanTypeStackedWidget.setCurrentIndex)

        # get the beamline config directory from the presets loaded at startup
        bl_config_dir = MAIN_OBJ.get_preset("bl_config_dir", "MAIN")
        plugin_dir = SourceFileLoader("plugin_dir", os.path.join(bl_config_dir,"__init__.py")).load_module().plugin_dir
        # desired_plugins_dct = MAIN_OBJ.get_preset_section("SCAN_PANEL_ORDER")
        _dirs = os.listdir(plugin_dir)
        idx = 0
        pages = 0
        num_scans = 0
        scans = {}
        # walk the subdirs of the beamline config directory looking for scan plugins
        for dir in _dirs:
            if os.path.isdir(os.path.join(plugin_dir, dir)):
                # get files in dir
                _files = os.listdir(os.path.join(plugin_dir, dir))
                if "loader.py" in _files:
                    _filepath = os.path.join(plugin_dir, dir, "loader.py")
                    if os.path.exists(_filepath):
                        _mod = SourceFileLoader("mod_classname", _filepath).load_module()
                        _mod_filepath = os.path.join(plugin_dir, dir, _mod.mod_file)
                        _cls = SourceFileLoader("mod_classname", _mod_filepath).load_module()
                        # create an instance of the class
                        plugin = eval("_cls.%s()" % _mod.mod_classname)
                        # assign parent so that we can use in plugin if need be
                        plugin._parent = self
                        _logger.debug("Found SCAN plugin [%s]" % plugin.name)
                        print("Found SCAN plugin [%d][%s]" % (plugin.idx, plugin.name))
                        # RUSS FEB25 self.splash.show_msg("Found SCAN plugin [%d][%s]" % (plugin.idx, plugin.name))
                        # self.splash.show_msg("Found SCAN plugin [%d][%s]" % (plugin.idx, plugin.name))
                        scans[plugin.idx] = plugin

                        # load_image
                        if hasattr(plugin, "load_image"):
                            plugin.load_image.connect(self.load_patterngen_img)

                        num_scans += 1

        # now insert then in the order the plugins idx value says and make all plugin signal connections
        for idx in range(num_scans):
            self.scanTypeComboBox.insertItem(idx, scans[idx].name)
            self.scanTypeStackedWidget.insertWidget(idx, scans[idx])
            scans[idx].roi_changed.connect(self.on_scanpluggin_roi_changed)
            scans[idx].roi_deleted.connect(self.on_scantable_roi_deleted)
            scans[idx].plot_data.connect(self.on_plot_data_loaded)
            scans[idx].selected.connect(self.set_current_scan_pluggin)
            scans[idx].clear_all_sig.connect(self.on_clear_all)
            scans[idx].new_est_scan_time.connect(self.on_new_est_scan_time)
            scans[idx].call_main_func.connect(self.scan_plugin_func_call)
            scans[idx].test_scan.connect(self.on_test_scan)
            scans[idx].update_plot_strs.connect(self.on_update_plot_strs)

            self.scan_tbox_widgets.append(scans[idx])
            pages += 1

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.scanTypeComboBox)
        layout.addLayout(hbox)
        layout.addWidget(self.scanTypeStackedWidget)
        self.scansFrame.setLayout(layout)

        if len(self.scan_tbox_widgets) <= 0:
            raise sys

        #####
        limit_def = self.scan_tbox_widgets[0].get_max_scan_range_limit_def()
        plot_item_type = self.scan_tbox_widgets[0].plot_item_type

        if hasattr(self, "lineByLineImageDataWidget"):
            if self.scan_tbox_widgets[0].is_multi_region():
                self.lineByLineImageDataWidget.set_enable_multi_region(True)
            else:
                self.lineByLineImageDataWidget.set_enable_multi_region(False)

            self.lineByLineImageDataWidget.set_shape_limits(
                shape=plot_item_type, limit_def=limit_def
            )
        self.plotTabWidget.setCurrentIndex(PLOTTER_IMAGES_TAB)
        ######
        dx = MAIN_OBJ.device("DNM_DETECTOR_X")
        dy = MAIN_OBJ.device("DNM_DETECTOR_Y")
        centers = (dx.get_position(), dy.get_position())

        if hasattr(self, "lineByLineImageDataWidget"):
            self.lineByLineImageDataWidget.set_center_at_XY(centers, (500, 500))

        self.scanTypeStackedWidget.currentChanged.connect(self.on_scan_plugin_stack_changed)

        wdg_com = self.scan_tbox_widgets[0].update_data()
        if hasattr(self, "scan_progress_table"):
            self.scan_progress_table.load_wdg_com(wdg_com)

    def dcsServerWindow_ContextMenuEvent(self, event):
        """
        Create the popup menu for a right click on the DCS Server QTextEdit and show all unique message headers that
        have been received since the "Show DCS server messages" menu item was selected

        :param event: event description
        :type event: event type

        :returns: None
        """
        menu = QtWidgets.QMenu()
        show_all_action = QtWidgets.QAction("Show All", self)
        menu.addAction(show_all_action)
        show_none_action = QtWidgets.QAction("Show None", self)
        menu.addAction(show_none_action)
        clear_action = QtWidgets.QAction("Clear Window", self)
        menu.addAction(clear_action)
        menu.addSeparator()

        #now add
        for k, v in self._dcs_server_msg_headers.items():
            _action = QtWidgets.QAction(k, self)
            font1 = _action.font()
            font1.setItalic(True)
            font1.setBold(True)
            _action.setFont(font1)
            _action.setCheckable(True)
            if v:
                _action.setChecked(True)
            menu.addAction(_action)

        selectedAction = menu.exec_(self.dcsServerWindow.mapToGlobal(event.pos()))
        if selectedAction:
            if selectedAction == clear_action:
                self.dcsServerWindow.clear()

            elif selectedAction == show_all_action:
                for k,v in self._dcs_server_msg_headers.items():
                    self._dcs_server_msg_headers[k] = True

            elif selectedAction == show_none_action:
                for k,v in self._dcs_server_msg_headers.items():
                    self._dcs_server_msg_headers[k] = False

            elif selectedAction.isChecked():
                #selectedAction.setChecked(True)
                self._dcs_server_msg_headers[selectedAction.text()] = True
            else:
                self._dcs_server_msg_headers[selectedAction.text()] = False


    def on_request_focusmode_change(self, val):
        """
        scan plugins can request that the focus mode be changed, this requires that the button on the main
        UI update its value thus the signal from teh plugins was added to make this clean and easy
        """
        pass
        # if val == 1:
        #     self.

    def load_patterngen_img(self, fname):
        """

        """
        max_scan_range_x = MAIN_OBJ.get_preset_as_float("max_fine_x")
        max_scan_range_y = MAIN_OBJ.get_preset_as_float("max_fine_y")
        # remove any existing images
        self.lineByLineImageDataWidget.delImagePlotItems()
        self.lineByLineImageDataWidget.openfile([fname], flipud=True, rotatable=False, alpha=1.0,
                                                use_current_plot_center=True)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        item = self.lineByLineImageDataWidget.get_image_item(fprefix)
        self.lineByLineImageDataWidget.set_max_trimage_size(item.title().text(), (max_scan_range_x, max_scan_range_y))
        self.lineByLineImageDataWidget.do_emit_new_roi(None)

    def on_scantable_roi_deleted(self, wdg_com):
        """
        on_scantable_roi_deleted(): description

        :param wdg_com: wdg_com description
        :type wdg_com: wdg_com type

        :returns: None
        """
        """
        the ScanTableView widget has deleted a spatial row, pass info on to plotter
        so that the shapeItem can also be deleted
        """
        # item_id = dct_get(wdg_com, SPDB_SCAN_PLUGIN_ITEM_ID)
        sp_rois_dct = dct_get(wdg_com, SPDB_SPATIAL_ROIS)
        # there will only be one selection
        item_id = list(sp_rois_dct.keys())[0]
        sp_db = sp_rois_dct[item_id]

        # item_id = dct_get(wdg_com, SPDB_ID_VAL)
        plot_item_type = dct_get(sp_db, SPDB_PLOT_SHAPE_TYPE)

        item = self.lineByLineImageDataWidget.getShapePlotItem(
            item_id, item_type=plot_item_type
        )
        if item:
            self.lineByLineImageDataWidget.blockSignals(True)
            self.lineByLineImageDataWidget.delPlotItem(item, replot=True)
            self.lineByLineImageDataWidget.blockSignals(False)

    def set_current_scan_pluggin(self, idx):
        # _logger.debug('set_current_scan_pluggin: [%d]' % idx)
        self.scan_panel_idx = idx
        self.scanTypeStackedWidget.setCurrentIndex(self.scan_panel_idx)

    def on_new_directed_beam_pos(self, newx, newy):
        """
        The plotter has emitted a new_beam_position signal, so move the beam
        :param cx:
        :param cy:
        :return:
        scanning_mode_strings
            'GONI_ZONEPLATE'
            'COARSE_SAMPLEFINE'
            'COARSE_ZONEPLATE'
        """
        scanning_mode_str = MAIN_OBJ.get_sample_scanning_mode_string()
        if scanning_mode_str.find("GONI_ZONEPLATE") > -1:
            cx_pos = MAIN_OBJ.device("DNM_GONI_X").get_position()
            cy_pos = MAIN_OBJ.device("DNM_GONI_Y").get_position()
            x_mtr = MAIN_OBJ.device("DNM_ZONEPLATE_X")
            y_mtr = MAIN_OBJ.device("DNM_ZONEPLATE_Y")

            # make zero based for zoneplate scan
            x_pos = newx - cx_pos
            y_pos = newy - cy_pos

        elif scanning_mode_str.find("COARSE_ZONEPLATE") > -1:
            cx_pos = MAIN_OBJ.device("DNM_COARSE_X").get_position()
            cy_pos = MAIN_OBJ.device("DNM_COARSE_Y").get_position()
            x_mtr = MAIN_OBJ.device("DNM_SAMPLE_X")
            y_mtr = MAIN_OBJ.device("DNM_SAMPLE_Y")
            # make zero based for zoneplate scan
            x_pos = newx
            y_pos = newy

        elif scanning_mode_str.find("COARSE_SAMPLEFINE") > -1:
            cx_pos = MAIN_OBJ.device("DNM_SAMPLE_X").get_position()
            cy_pos = MAIN_OBJ.device("DNM_SAMPLE_Y").get_position()
            x_mtr = MAIN_OBJ.device("DNM_SAMPLE_X")
            y_mtr = MAIN_OBJ.device("DNM_SAMPLE_Y")
            # using absolute x/y from interferometer
            x_pos = newx
            y_pos = newy

        x_mtr.move(x_pos, wait=False)
        y_mtr.move(y_pos, wait=False)

    def on_scan_loaded(self, wdg_com):
        """
        on_scan_loaded(): This is a slot to service a signal emmitted from the PLOTTER only

        :param wdg_com: wdg_com description
        :type wdg_com: wdg_com type
        self.delShapePlotItems()
        :returns: None
        """
        """ make call to update the scans params defined in the plugin """

        sp_db = get_first_sp_db_from_wdg_com(wdg_com)

        scan_name = dct_get(sp_db, SPDB_SCAN_PLUGIN_SECTION_ID)
        self.scan_panel_idx = MAIN_OBJ.get_scan_panel_id_from_scan_name(scan_name)
        # if(self.scan_panel_idx > 100):{"file": "/tmp/2025-07-22/discard/Detector_2025-07-22_001.hdf5", "scan_type_num": 0, "scan_type": "detector_image Point_by_Point", "stxm_scan_type": "detector image", "energy": [700.0], "estart": 700.0, "estop": 700.0, "e_npnts": 1, "polarization": "CircLeft", "offset": 0.0, "angle": 0.0, "dwell": 1000.0, "npoints": [75, 30], "date": "2025-07-22", "start_time": "10:22:06-06:00", "end_time": "10:22:18-06:00", "center": [0.0, 0.0], "range": [19.733333333333334, 19.333333333333332], "step": [0.2666666666666675, 0.6666666666666661], "start": [-9.866666666666667, -9.666666666666666], "stop": [9.866666666666667, 9.666666666666666], "xpositioner": "DNM_DETECTOR_X", "ypositioner": "DNM_DETECTOR_Y"}
        #    self.scan_panel_idx = scan_panel_order.IMAGE_SCAN

        self.scanTypeStackedWidget.setCurrentIndex(self.scan_panel_idx)
        self.scan_tbox_widgets[self.scan_panel_idx].set_zp_focus_mode()
        time.sleep(0.15)
        # self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(True)
        # self.scan_tbox_widgets[self.scan_panel_idx].mod_roi(sp_db, do_recalc=False)
        if dct_get(sp_db, SPDB_PLOT_IMAGE_TYPE) in [
            image_types.FOCUS,
            image_types.OSAFOCUS,
        ]:
            # dont allow signals that would cause a plot segment to be created
            self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(True)
            self.scan_tbox_widgets[self.scan_panel_idx].load_roi(wdg_com)
            self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(False)
        else:
            self.scan_tbox_widgets[self.scan_panel_idx].load_roi(wdg_com)
            # self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(False)

    def on_scanpluggin_roi_changed(self, wdg_com):
        """
        on_scanpluggin_roi_changed(): description

        :param wdg_com: wdg_com description
        :type wdg_com: wdg_com type

        :returns: None
        """
        # _logger.debug('on_scanpluggin_roi_changed: called')
        if wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.LOAD_SCAN:
            # self.scan_progress_table.set_directory_label(self.active_user.get_data_dir())
            # self.scan_progress_table.load_wdg_com(wdg_com)

            #          #for each spatial region create a plotitem
            #             sp_rois = dct_get(wdg_com, WDGCOM_SPATIAL_ROIS)
            #             for sp_id in sp_rois.keys():
            #                 sp_db = sp_rois[sp_id]
            #                 rect = sp_db[SPDB_RECT]
            #                 scan_item_type = int(dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE))
            #                 plot_item_type = int(dct_get(sp_db, SPDB_PLOT_SHAPE_TYPE))
            #                 self.lineByLineImageDataWidget.addShapePlotItem(int(sp_id), rect, item_type=plot_item_type)
            pass
        else:

            sp_rois = dct_get(wdg_com, WDGCOM_SPATIAL_ROIS)
            # if(sp_rois is None):
            #    return
            if (sp_rois is None) or (len(list(sp_rois.keys())) < 1):
                # no spatial ids so clear unique id list
                reset_unique_roi_id()
                return
            for sp_id in list(sp_rois.keys()):
                add_to_unique_roi_id_list(sp_id)
                # sp_id = sp_rois.keys()[0]
                sp_db = sp_rois[sp_id]
                scan_item_type = int(dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE))
                plot_item_type = int(dct_get(sp_db, SPDB_PLOT_SHAPE_TYPE))
                item_id = int(dct_get(sp_db, SPDB_ID_VAL))

                if plot_item_type == spatial_type_prefix.PNT:
                    x1 = x2 = float(dct_get(sp_db, SPDB_XCENTER))
                    y1 = y2 = float(dct_get(sp_db, SPDB_YCENTER))

                else:
                    x1 = float(dct_get(sp_db, SPDB_XSTART))
                    y1 = float(dct_get(sp_db, SPDB_YSTART))
                    x2 = float(dct_get(sp_db, SPDB_XSTOP))
                    y2 = float(dct_get(sp_db, SPDB_YSTOP))

                xc = float(dct_get(sp_db, SPDB_XCENTER))
                yc = float(dct_get(sp_db, SPDB_YCENTER))

                # print 'on_scanpluggin_roi_changed: item_id = %d' % item_id
                if hasattr(self, "lineByLineImageDataWidget"):
                    item = self.lineByLineImageDataWidget.getShapePlotItem(
                        item_id, plot_item_type
                    )
                    # self.lineByLineImageDataWidget.set_shape_item_max_range(item, dct_get(sp_db, SPDB_SCAN_PLUGIN_MAX_SCANRANGE))

                    rect = (x1, y1, x2, y2)

                    # print 'on_scanpluggin_roi_changed: rect=' , (rect)
                    skip_list = [scan_types.SAMPLE_FOCUS, scan_types.OSA_FOCUS]
                    if (item is None) and scan_item_type is not scan_types.PATTERN_GEN:
                        if scan_item_type not in skip_list:
                            self.lineByLineImageDataWidget.addShapePlotItem(
                                item_id, rect, item_type=plot_item_type, re_center=True
                            )
                    elif scan_item_type is scan_types.PATTERN_GEN:
                        xc, yc = self.scan_pluggin.get_saved_center()
                        # self.lineByLineImageDataWidget.move_shape_to_new_center('pattern', xc, yc)

                    else:
                        self.lineByLineImageDataWidget.blockSignals(True)
                        if wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.SELECT_ROI:
                            self.lineByLineImageDataWidget.selectShapePlotItem(
                                item_id,
                                select=True,
                                item=item,
                                item_type=plot_item_type,
                            )

                        elif wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.ROI_CHANGED:
                            self.lineByLineImageDataWidget.resizeShapePlotItem(
                                item_id, rect, item=item, item_type=plot_item_type
                            )

                        self.lineByLineImageDataWidget.blockSignals(False)

        # self.lineByLineImageDataWidget.recenter_plot_to_all_items()
        if hasattr(self, "scan_progress_table"):
            self.scan_progress_table.load_wdg_com(wdg_com)

    def on_plotitem_roi_changed(self, wdg_com):
        """
        on_plotitem_roi_changed(): description

        :param wdg_com: wdg_com description
        :type wdg_com: wdg_com type

        :returns: None
        """
        """ make call to update the scans params defined in the plugin """
        # print('on_plotitem_roi_changed: ', wdg_com)
        if self.scan_in_progress:
            return

        x1 = dct_get(wdg_com, SPDB_XSTART)
        y1 = dct_get(wdg_com, SPDB_YSTART)
        x2 = dct_get(wdg_com, SPDB_XSTOP)
        y2 = dct_get(wdg_com, SPDB_YSTOP)
        rect = (x1, y1, x2, y2)
        # print 'on_plotitem_roi_changed: rect', rect
        if not self.scan_tbox_widgets[self.scan_panel_idx].is_interactive_plot():
            return

        self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(True)
        if wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.ROI_CHANGED:

            self.scan_tbox_widgets[self.scan_panel_idx].mod_roi(wdg_com)
            wdg_com = self.scan_tbox_widgets[self.scan_panel_idx].update_data()

            # if (self.scan_panel_idx in skip_scan_q_table_plots):
            if self.scan_tbox_widgets[
                self.scan_panel_idx
            ].is_skip_scan_queue_table_plot():
                # just skip because this produces a lot of changes to the scan_q_table whcih currently are very slow when firing a lot of
                # signals to say the plot roi has chnaged
                pass
            else:
                if hasattr(self, "scan_progress_table"):
                    self.scan_progress_table.load_wdg_com(wdg_com)

        elif wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.ADD_ROI:
            # pass on this addition request
            self.scan_tbox_widgets[self.scan_panel_idx].mod_roi(wdg_com)

        elif wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.DEL_ROI:
            # pass on this deletion request
            self.scan_tbox_widgets[self.scan_panel_idx].mod_roi(wdg_com)

        elif wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.SELECT_ROI:
            self.scan_tbox_widgets[self.scan_panel_idx].mod_roi(wdg_com)

        elif wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.DESELECT_ROI:
            self.scan_tbox_widgets[self.scan_panel_idx].mod_roi(wdg_com)

        else:
            _logger.error(
                "on_plotitem_roi_changed: unsupported widget_com command type"
                % wdg_com[WDGCOM_CMND]
            )
        self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(False)

    def on_clear_all(self):
        """the scan plugin is asking us to clear the plot"""
        self.lineByLineImageDataWidget.blockSignals(True)
        self.lineByLineImageDataWidget.delShapePlotItems()
        self.lineByLineImageDataWidget.blockSignals(False)

    def on_plot_data_loaded(self, tpl):
        """
        on_plot_data_loaded(): description

        :param data_dct: data_dct description
        :type data_dct: data_dct type

        :returns: None
        """
        # (fname, ado_obj) = tpl
        # wdg_com = dct_get(ado_obj, ADO_CFG_WDG_COM)
        (fname, wdg_com, data) = tpl
        sp_db = get_first_sp_db_from_wdg_com(wdg_com)

        #         #for each spatial region create a plotitem
        #             sp_rois = dct_get(wdg_com, WDGCOM_SPATIAL_ROIS)
        #             for sp_id in sp_rois.keys():
        #                 sp_db = sp_rois[sp_id]
        #                 rect = sp_db[SPDB_RECT]
        #                 scan_item_type = int(dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE))
        #                 plot_item_type = int(dct_get(sp_db, SPDB_PLOT_SHAPE_TYPE))
        #                 self.lineByLineImageDataWidget.addShapePlotItem(int(sp_id), rect, item_type=plot_item_type)
        #
        if dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) is scan_types.SAMPLE_LINE_SPECTRUM:
            self.lineByLineImageDataWidget.do_load_linespec_file(
                fname, wdg_com, data, dropped=False
            )
            self.lineByLineImageDataWidget.on_set_aspect_ratio(force=True)

        elif dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) not in [
            scan_types.SAMPLE_POINT_SPECTRUM,
            scan_types.GENERIC_SCAN,
        ]:
            self.lineByLineImageDataWidget.blockSignals(True)
            self.lineByLineImageDataWidget.delShapePlotItems()
            self.lineByLineImageDataWidget.load_image_data(fname, wdg_com, data)

            # only allow the scan param shapes to be created if NOT a focus type scan image
            if dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) not in [
                scan_types.OSA_FOCUS,
                scan_types.SAMPLE_FOCUS,
            ]:
                rect = sp_db[SPDB_RECT]
                sp_id = int(dct_get(sp_db, SPDB_ID_VAL))
                # scan_item_type = int(dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE))
                plot_item_type = int(dct_get(sp_db, SPDB_PLOT_SHAPE_TYPE))
                self.lineByLineImageDataWidget.addShapePlotItem(
                    int(sp_id), rect, item_type=plot_item_type
                )

            # make sure plotter is aware if it is supposed to allow more than one ShpeItem
            if self.scan_tbox_widgets[self.scan_panel_idx].is_multi_region():
                self.lineByLineImageDataWidget.set_enable_multi_region(True)
            else:
                self.lineByLineImageDataWidget.set_enable_multi_region(False)

            self.lineByLineImageDataWidget.blockSignals(False)

    def show_pattern_generator_pattern(self, tple):
        """
        called by the pattern generator scan plugin
        :return:
        """
        if hasattr(self, "lineByLineImageDataWidget"):
            chkd, xc, yc, pad_size = tple
            if chkd:
                # check to see if it is currently visible if so hide it if not show it
                self.lineByLineImageDataWidget.show_pattern(
                    xc, yc, pad_size, do_show=True
                )
            else:
                self.lineByLineImageDataWidget.show_pattern(
                    xc, yc, pad_size, do_show=False
                )

    def setup_image_plot(self):
        """
        setup_image_plot(): description

        :returns: None
        """
        #        from guiqwt.plot import ImageDialog
        #        self.lineByLineImageDataWidget = ImageDialog(edit=False, toolbar=True, wintitle="Contrast test",

        fg_clr = master_colors["plot_forgrnd"]["rgb_hex"]
        bg_clr = master_colors["plot_bckgrnd"]["rgb_hex"]
        min_clr = master_colors["plot_gridmaj"]["rgb_hex"]
        maj_clr = master_colors["plot_gridmin"]["rgb_hex"]

        # gridparam = {'fg_clr':fg_clr, 'bg_clr':bg_clr, 'min_clr':min_clr, 'maj_clr':maj_clr}

        # self.lineByLineImageDataWidget = ImageWidgetPlot(parent=None, filtStr="*.hdf5", type=None,
        #         options = dict(lock_aspect_ratio=True, show_contrast=True, show_xsection=True, show_ysection=True,
        #         xlabel=("microns", ""), ylabel=("microns", ""), colormap="gist_gray"))

        self.lineByLineImageDataWidget = ImageWidgetPlot(
            parent=None,
            type="analyze",
            settings_fname="%s_settings.json" % MAIN_OBJ.get_endstation_prefix(),
        )
        if hasattr(self, "lineByLineImageDataWidget"):
            # self.lineByLineImageDataWidget.plot.setTitle('lineByLineImageDataWidget')
            self.lineByLineImageDataWidget.set_lock_aspect_ratio(True)
            # self.bsImagePlotWidget = ImgPlotWindow()
            # vb = QtWidgets.QVBoxLayout()
            # vb.addWidget(self.bsImagePlotWidget)
            # self.bsImagePlotFrame.setLayout(vb)

            self.lineByLineImageDataWidget.setObjectName("lineByLineImageDataWidget")
            self.lineByLineImageDataWidget.register_osa_and_samplehldr_tool(
                sample_pos_mode
            )
            #        self.lineByLineImageDataWidget.register_osa_and_samplehldr_tool(sample_pos_mode)
            # self.lineByLineImageDataWidget.set_transform_factors(0.333, 0.333, 0.333, 'um')
            # self.lineByLineImageDataWidget.setMinimumSize(600, 600)
            self.lineByLineImageDataWidget.enable_tool_by_name(
                "tools.clsOpenFileTool", False
            )
            #   self.lineByLineImageDataWidget.set_sample_positioning_mode(sample_pos_mode)
            self.lineByLineImageDataWidget.set_dataIO(STXMDataIo)

            self.lineByLineImageDataWidget.addTool("DummySeparatorTool")
            self.lineByLineImageDataWidget.addTool("tools.BeamSpotTool")
            self.lineByLineImageDataWidget.addTool("tools.StxmControlBeamTool")

            self.lineByLineImageDataWidget.addTool("DummySeparatorTool")
            self.lineByLineImageDataWidget.addTool("tools.clsHorizSelectPositionTool", is_visible=False)
            self.lineByLineImageDataWidget.addTool("tools.clsCrossHairSelectPositionTool", is_visible=False)

            self.lineByLineImageDataWidget.addTool("DummySeparatorTool")
            self.lineByLineImageDataWidget.addTool("HelpTool")

            roi_tool = self.lineByLineImageDataWidget.addTool("tools.clsROITool", is_visible=False)
            self.visual_signals_obj = VisualSignalsClass()
            roi_tool.set_visual_sigs_obj(self.visual_signals_obj)

            self.lineByLineImageDataWidget.addTool("DummySeparatorTool")
            self.lineByLineImageDataWidget.addTool("tools.clsSignalSelectTool")

            self.lineByLineImageDataWidget.set_grid_parameters(bg_clr, min_clr, maj_clr)
            self.lineByLineImageDataWidget.set_cs_grid_parameters(
                fg_clr, bg_clr, min_clr, maj_clr
            )

            self.lineByLineImageDataWidget.new_roi_center.connect(
                self.on_plotitem_roi_changed
            )
            self.lineByLineImageDataWidget.scan_loaded.connect(self.on_scan_loaded)
            self.lineByLineImageDataWidget.install_beam_fbk_devs(MAIN_OBJ)
            self.lineByLineImageDataWidget.new_beam_position.connect(
                self.on_new_directed_beam_pos
            )

            # self.lineByLineImageDataWidget.create_sample_holder()

            vbox = QtWidgets.QVBoxLayout()
            # ################ TESTING
            # integrate_btn = QtWidgets.QPushButton("Integrate Points")
            # integrate_btn.clicked.connect(self._tst_integrate)
            # vbox.addWidget(integrate_btn)
            # #########################
            vbox.addWidget(self.lineByLineImageDataWidget)
            self.imagePlotFrame.setGeometry(QtCore.QRect(0, 0, 320, 240))
            self.imagePlotFrame.setLayout(vbox)
            self.lineByLineImageDataWidget.set_data_dir(self.active_user.get_data_dir())
            MAIN_OBJ.set("IMAGE_WIDGET", self.lineByLineImageDataWidget)

    def _tst_integrate(self):
        from cls.utils.roi_object import on_integrate_points_btn
        on_integrate_points_btn(self.lineByLineImageDataWidget, self.visual_signals_obj)

    def setup_spectra_plot(self):

        """
        setup_spectra_plot(): description

        :returns: None
        """
        vbox = QtWidgets.QVBoxLayout()
        # self.spectraWidget = CurveViewerWidget(parent = self, winTitleStr = "Spectra Data Viewer")
        self.spectraWidget = CurveViewerWidget(parent=self)
        self.spectraWidget.set_dataIO(STXMDataIo)
        self.spectraWidget.add_legend("TL")
        self.spectraWidget.addTool("tools.clsSignalSelectTool")

        vbox.addWidget(self.spectraWidget)
        self.spectraPlotFrame.setLayout(vbox)

    def setup_chartmode_plot(self):

        """
        setup_chartmode_plot(): description

        :returns: None
        """
        selected_det_dct = MAIN_OBJ.get_detectors()
        MAIN_OBJ.seldets_changed.connect(self.update_chart_selected_detectors)
        vbox = QtWidgets.QVBoxLayout()
        self.chartspectraWidget = ChartingWidget(5.0, signals_dct=selected_det_dct,
                                                 parent=self,
                                                 scale_factor=1.0,
                                                 select_cb=self.update_oscilloscope_definition)
        self.chartspectraWidget.setObjectName("chartspectraWidget")


        plot = self.chartspectraWidget.scanplot.get_plot()
        pcan = plot.canvas()
        pcan.setObjectName("chartspectraWidgetCanvasBgrnd")

        # detector_devs = MAIN_OBJ.get_devices_in_category("DETECTORS")
        # # det_nms = list(detector_devs.keys())


        vbox.addWidget(self.chartspectraWidget)
        self.chartPlotFrame.setLayout(vbox)

    def update_chart_selected_detectors(self, sel_det_lst: list):
        """
        update the chart when the user selects different detectors
        """
        self.chartspectraWidget.update_signal_list(sel_det_lst)


    def update_oscilloscope_definition(self, osc_def):
        """

        based on the selection of the detectors in the chart mode panel signal tool send the command to the
        DCS server
        """
        # print(f"chart_mode_select_detectors: {det_lst}")
        MAIN_OBJ.set_oscilloscope_definition(osc_def)

    def setup_stack_rois_plot(self):

        """
        setup_stack_rois_plot(): Setup the Spectra plotter for stack ROI's, appears on data panel under tab "Stack ROI's"

        :returns: None
        """
        vbox = QtWidgets.QVBoxLayout()
        hbox = QtWidgets.QHBoxLayout()
        # self.roiSpectraWidget = CurveViewerWidget(toolbar=False, type="minimal", parent=self)
        self.roiSpectraWidget = CurveViewerWidget(toolbar=True, type="minimal", parent=self)
        self.roiSpectraWidget.remove_all_tools()
        self.roiSpectraWidget.addTool("tools.clsSignalSelectTool")
        self.create_roi_btn = QtWidgets.QPushButton("Press to create ROI")
        self.clear_all_roi_btn = QtWidgets.QPushButton("Clear All")
        self.create_roi_btn.setCheckable(True)
        self.create_roi_btn.clicked.connect(self.activate_create_roi_tool)
        self.clear_all_roi_btn.clicked.connect(self.roiSpectraWidget.clear_plot)
        self.clear_all_roi_btn.clicked.connect(self.remove_all_rois)
        self.roiSpectraWidget.set_dataIO(STXMDataIo)
        self.roiSpectraWidget.setObjectName("spectraWidget")
        plot = self.roiSpectraWidget.get_plot()
        pcan = plot.canvas()
        pcan.setObjectName("spectraPlotCanvasBgrnd")
        # self.roiSpectraWidget.add_legend("TL")
        hbox.addWidget(self.create_roi_btn)
        hbox.addWidget(self.clear_all_roi_btn)
        vbox.addLayout(hbox)
        vbox.addWidget(self.roiSpectraWidget)
        self.roiPlotFrame.setLayout(vbox)

    def remove_all_rois(self):
        """
        This function is used to remove all of the ROI shapes currently displayed in the plotter
        """
        self.lineByLineImageDataWidget.delShapePlotItems(exclude_rois=False)

    def activate_create_roi_tool(self, chkd):
        """
        The button above the ROI spec plotter is asking for another roi to be created
        """
        if chkd:
            self.create_roi_btn.setText("Press to complete ROI")
        else:
            self.create_roi_btn.setText("Press to create ROI")

        self.lineByLineImageDataWidget.activate_create_roi_tool(chkd)

    def activate_horiz_line_sel_tool(self, chkd):
        """
        The button on usually a focus scan panel that selects a horizontal line
        """
        self.lineByLineImageDataWidget.activate_horiz_line_sel_tool(True)

    def activate_arbitrary_line_sel_tool(self, chkd):
        """
        The button on usually a focus scan panel that selects a horizontal line
        """
        self.lineByLineImageDataWidget.activate_arbitrary_line_sel_tool(True)

    def activate_point_sel_tool(self, chkd):
        """
        The button on usually a focus scan panel that selects a horizontal line
        """
        self.lineByLineImageDataWidget.activate_point_sel_tool(True)

    def setup_calib_camera(self, scaling_factor):
        """
        setup_video_panel(): description

        :returns: None
        plotTabWidget
        tab3
        """
        from cls.applications.pyStxm.widgets.camera_ruler import (
            CameraRuler,
            camruler_mode,
        )

        vbox = QtWidgets.QVBoxLayout()
        # self.spectraWidget = CurveViewerWidget(parent = self, winTitleStr = "Spectra Data Viewer")
        # self.splash.show_msg('Loading Calibration Camera in Client Mode')
        self.calibCamWidget = CameraRuler(
            mode=camruler_mode.CLIENT,
            main_obj=MAIN_OBJ,
            scaling_factor=scaling_factor,
            parent=self,
        )
        self.calibCamWidget.setObjectName("calibCamWidget")

        vbox.addWidget(self.calibCamWidget)
        self.calibCamPlotFrame.setLayout(vbox)

    #     def add_to_plot_tab_widget(self, tab_num, tab_title, widg):
    #         tw = self._get_base_tab_widget()
    #         self.plotTabWidget.setTabPosition(tab_num)
    #         self.plotTabWidget.setTabText(tab_title)
    #         self.plotTabWidget.
    #
    #     def _get_base_tab_widget(self):
    #         tw = QtWidgets.QWidget()
    #         tf = QtWidgets.QFrame()
    #         vbox = QtWidgets.QVBoxLayout()
    #         vbox.addWidget(tf)
    #         tw.setLayout(vbox)
    #         return(tw)

    def setup_video_panel(self):
        """
        setup_video_panel(): description

        :returns: None
        """
        pass
        # QWebSettings.globalSettings().setAttribute(QWebSettings.PluginsEnabled, True)
        # QWebSettings.globalSettings().setAttribute(QWebSettings.AutoLoadImages, True)
        # self.videoWebView.setUrl(QtCore.QUrl("http://ccd1608-500.clsi.ca/jpg/image.jpg"))
        # self.videoWebView.load(QtCore.QUrl("http://ccd1608-500.clsi.ca/jpg/image.jpg"))

        # self.videoWebView.setUrl(QtCore.QUrl("http://v2e1602-101/axis-cgi/mjpg/video.cgi?camera=1"))
        # self.videoWebView.load(QtCore.QUrl("http://v2e1602-101/axis-cgi/mjpg/video.cgi?camera=1"))

        # self.vidTimer.start(250)

        # self.videoPlayer.load(Phonon.MediaSource('http://ccd1608-500.clsi.ca/view/index.shtml'))
        # self.videoPlayer.play()

    def on_video_timer(self):
        """
        on_video_timer(): description

        :returns: None
        """
        self.videoWebView.load(QtCore.QUrl("http://ccd1608-500.clsi.ca/jpg/image.jpg"))
        # self.videoWebView.reload()

    def sscan_faze_cb_report(self, sscans):
        """
        a convienience function to get the current state of all scan callbacks for FAZE field of SSCAN record
        :param sscans:
        :return:
        """
        skeys = sorted(sscans.keys())
        for k in skeys:
            sscan = sscans[k]
            ss = sscan["sscan"]
            cbs = ss._pvs["FAZE"].callbacks
            num_cbs = len(list(cbs.keys()))
            cb_ids = list(cbs.keys())
            id_str = ""
            for _id in cb_ids:
                id_str += "%d " % _id

            print(
                "[%s] has [%d] cbs for FAZE with Ids [%s]" % (ss.NAME, num_cbs, id_str)
            )

    def setup_info_dock(self):
        """
        setup_info_dock(): description

        :returns: None
        """
        pass
        # # ns = {'main': self, 'widget': self, 'det_scan' : scans[1]}
        # ns = {'main': self, 'pythonShell': self.pythonshell, 'g': globals(), 'MAIN_OBJ': MAIN_OBJ, 'scans_plgins': self.scan_tbox_widgets}
        # # msg = "Try for example: widget.set_text('foobar') or win.close()"
        # #self.pythonshell = ShellWidget(parent=None, namespace=ns, commands=[], multithreaded=True, exitfunc=exit)
        # self.pythonshell = ShellWidget(parent=None, namespace=ns, commands=[], multithreaded=True)
        # self.pyconsole_layout.addWidget(self.pythonshell)
        # # self.apply_stylesheet(self.pythonshell, self.qssheet)

    def on_scan_plugin_stack_changed(self, idx):
        """
        on_toolbox_changed(): description

        :param idx: idx description
        :type idx: idx type

        :returns: None
        """
        reset_unique_roi_id()
        ranges = (None, None)
        # print 'on_toolbox_changed: %d' % idx
        # spectra_plot_types = [scan_panel_ord{"file": "C:/controls/stxm-data/2019/1212\\C191212195.hdf5", "scan_type_num": 6, "scan_type": "sample_image Line_Unidir", "scan_panel_idx": 5, "energy": 693.9, "estart": 693.9, "estop": 693.9, "e_npnts": 1, "polarization": "CircLeft", "offset": 0.0, "angle": 0.0, "dwell": 1.0, "npoints": [100, 100], "date": "2019-12-12", "end_time": "22:39:30", "center": [-163.51892127843303, -503.91446634377246], "range": [59.999999999999886, 59.999999999999545], "step": [0.606060606060605, 0.6060606060606014], "start": [-193.51892127843297, -533.9144663437722], "stop": [-133.51892127843308, -473.9144663437727], "xpositioner": "GoniX", "ypositioner": "GoniY", "goni_z_cntr": 0.0, "goni_theta_cntr": 0.0}er.POINT_SCAN, scan_panel_order.POSITIONER_SCAN]
        # non_interactive_plots = [scan_panel_order.POSITIONER_SCAN]
        # multi_spatial_scan_types = [scan_types.SAMPLE_POINT_SPECTRUM, scan_types.SAMPLE_LINE_SPECTRUM,
        #                             scan_types.SAMPLE_IMAGE, \
        #                             scan_types.SAMPLE_IMAGE_STACK]
        # skip_list = [scan_types.SAMPLE_FOCUS, scan_types.OSA_FOCUS]

        # Note: these are scan panel order NOT scan types
        # skip_centering_scans = [scan_panel_order.FOCUS_SCAN, scan_panel_order.TOMOGRAPHY,
        #                        scan_panel_order.LINE_SCAN, scan_panel_order.POINT_SCAN, scan_panel_order.IMAGE_SCAN]

        self.scan_panel_idx = idx
        self.scanTypeComboBox.setCurrentIndex(idx)

        if len(self.scan_tbox_widgets) > 0:
            if hasattr(self, "lineByLineImageDataWidget"):
                self.lineByLineImageDataWidget.delShapePlotItems()

            if hasattr(self, "scan_progress_table"):
                self.scan_progress_table.clear_table()
            sample_positioning_mode = MAIN_OBJ.get_sample_positioning_mode()

            if self.scan_pluggin is not None:
                self.scan_pluggin.on_plugin_defocus()

            scan_pluggin = self.scan_tbox_widgets[self.scan_panel_idx]
            self.scan_pluggin = scan_pluggin

            scan_pluggin.on_plugin_focus()

            if not scan_pluggin.isEnabled():
                # pluggin is disabled so ignore it
                return

            ranges = scan_pluggin.get_saved_range()
            centers = scan_pluggin.get_saved_center()
            axis_strs = scan_pluggin.get_axis_strs()
            max_scan_range = scan_pluggin.get_spatial_scan_range()
            limit_def = scan_pluggin.get_max_scan_range_limit_def()
            plot_item_type = scan_pluggin.plot_item_type
            enable_multi_region = scan_pluggin.is_multi_region()
            scan_type = scan_pluggin.get_scan_type()
            do_center_plot = scan_pluggin.get_do_center_plot_on_focus()
            # wdg_com = self.scan_tbox_widgets[self.scan_panel_idx].update_data()
            # self.scan_progress_table.load_wdg_com(wdg_com)

        # self.lineByLineImageDataWidget.delShapePlotItems()

        # if (idx in spectra_plot_types):
        if scan_pluggin.is_spectra_plot_type():
            # but only switch if it is not a point scan as the selection for a point scan is done on a 2D image
            # if(idx is scan_panel_order.POINT_SCAN):
            if scan_pluggin.type is scan_types.SAMPLE_POINT_SPECTRUM:
                # we have switched to sample point spectrum scan so make sure the plotter knows it is an image (even if it isnt yet)
                # this is to correct a situation of having just done a sample focus scan, if the image type is left as focus scan
                # then the wdg_com dict emiitted by the plotter will think that it should put x/y positions in terms of using z for y
                if hasattr(self, "lineByLineImageDataWidget"):
                    self.lineByLineImageDataWidget.set_image_type(image_types.IMAGE)
                # it is a point scan so zoom the plot to a valid range
                sx = MAIN_OBJ.get_sample_positioner("X")
                sy = MAIN_OBJ.get_sample_positioner("Y")

                centers = (sx.get_position(), sy.get_position())
                if hasattr(self, "lineByLineImageDataWidget"):
                    self.lineByLineImageDataWidget.set_center_at_XY(
                        centers, max_scan_range
                    )
            else:
                self.plotTabWidget.setCurrentIndex(PLOTTER_SPECTRA_TAB)
                self.spectraWidget.setPlotAxisStrs(axis_strs[0], axis_strs[1])
        else:
            self.plotTabWidget.setCurrentIndex(PLOTTER_IMAGES_TAB)

            if (ranges[0] is not None) and (ranges[1] is not None):

                # do_recenter_lst = [scan_panel_order.IMAGE_SCAN, scan_panel_order.TOMOGRAPHY, scan_panel_order.LINE_SCAN]

                # if ((self.scan_panel_idx == scan_panel_order.IMAGE_SCAN) and (sample_positioning_mode == sample_positioning_modes.GONIOMETER)):
                # if ((self.scan_panel_idx in  do_recenter_lst) and (sample_positioning_mode == sample_positioning_modes.GONIOMETER)):
                if (scan_pluggin.is_do_recenter_type()) and (
                        sample_positioning_mode == sample_positioning_modes.GONIOMETER
                ):
                    if hasattr(self, "lineByLineImageDataWidget"):
                        self.lineByLineImageDataWidget.set_center_at_XY(centers, ranges)
                else:

                    # if(self.scan_panel_idx in skip_centering_scans):
                    if scan_pluggin.is_skip_center_type():
                        # we are likely already where we want to be on the plotter if the user switched to one of these scans
                        pass
                    else:
                        sx = MAIN_OBJ.get_sample_positioner("X")
                        sy = MAIN_OBJ.get_sample_positioner("Y")
                        centers = (sx.get_position(), sy.get_position())
                        if hasattr(self, "lineByLineImageDataWidget"):
                            if scan_type is scan_types.PATTERN_GEN:
                                self.lineByLineImageDataWidget.set_center_at_XY(
                                    centers, (ranges[0] * 10, ranges[1] * 10)
                                )
                            else:
                                self.lineByLineImageDataWidget.set_center_at_XY(
                                    centers, ranges
                                )

                # self.lineByLineImageDataWidget.set_shape_limits(shape=plot_item_type, limit_def=limit_def)
                if hasattr(self, "lineByLineImageDataWidget"):
                    self.lineByLineImageDataWidget.setPlotAxisStrs(
                        axis_strs[0], axis_strs[1]
                    )

        if hasattr(self, "lineByLineImageDataWidget"):
            self.lineByLineImageDataWidget.set_max_shape_sizes(max_scan_range)
            self.lineByLineImageDataWidget.set_enable_multi_region(enable_multi_region)

            # NOTE: calling set_shape_limits() also enables/disables the scan selection tools
            if not scan_pluggin.is_interactive_plot():
                # disable all roi selection tools
                self.lineByLineImageDataWidget.set_shape_limits(
                    shape=None, limit_def=None
                )
            else:
                self.lineByLineImageDataWidget.set_shape_limits(
                    shape=plot_item_type, limit_def=limit_def
                )

        if len(self.scan_tbox_widgets) > 0:
            # some of the params on a particular tool box read pv's so make sure the
            # focus calc mode is set correctly and has time to process
            # scan_pluggin.set_zp_focus_mode()
            # time.sleep(0.15)
            scan_pluggin.load_from_defaults()

        # if(scan_type in multi_spatial_scan_types):
        # scan_pluggin.on_focus_init_base_values()

        wdg_com = scan_pluggin.update_data()

        # if(scan_type is scan_types.PATTERN_GEN):
        #    self.show_pattern_generator_pattern()

        # if(wdg_com):
        #    if(len(wdg_com['SPATIAL_ROIS']) > 0):
        #        self.scan_progress_table.load_wdg_com(wdg_com)

    # def scan_plugin_func_call(self, func_nm, chkd):
    def scan_plugin_func_call(self, func_nm, tuple):
        # allow the scan pluggins to (if they know about a function here in stxmMain) to call it by name
        if hasattr(self, func_nm):
            func = getattr(self, func_nm)
            func(tuple)
        else:
            _logger.info(
                "Scan plugin called a function in stxmMain that doesnt exist: [%s]"
                % func_nm
            )

    def on_update_plot_strs(self, axis_strs):
        """
        a signal handler that takes a tuple of 2 axis strings to apply toi the correct plotter
        """
        if self.scan_tbox_widgets[self.scan_panel_idx].is_spectra_plot_type():
            self.spectraWidget.setPlotAxisStrs(axis_strs[0], axis_strs[1])
        else:
            self.lineByLineImageDataWidget.setPlotAxisStrs(axis_strs[0], axis_strs[1])

    def init_beamstatus(self):
        self.beamStatusLayout: QtWidgets.QVBoxLayout = self.beamStatusLayout
        self.beamStatusLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)

        status_title_color = master_colors["app_superltblue"]["rgb_str"]
        status_fbk_color = master_colors["status_fbk_color"]["rgb_str"]

        # w = ophyd_aiLabelWidget(
        #     MAIN_OBJ.device("DNM_MONO_EV_FBK"),
        #     hdrText="Mono Energy:",
        #     egu="eV",
        #     title_color=status_title_color,
        #     var_clr=status_fbk_color,
        # )
        # # w.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        # self.beamStatusLayout.insertWidget(0, w)
        # self.beamStatusLayout.insertSpacing(0, 10)
        # only show the ring current if device exists
        if MAIN_OBJ.device("DNM_RING_CURRENT"):
            w = ophyd_aiLabelWidget(
                MAIN_OBJ.device("DNM_RING_CURRENT"),
                hdrText="Ring Current:",
                egu="mA",
                title_color=status_title_color,
                var_clr=status_fbk_color,
                alarm=5,
                warn=20,
            )
            # w.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
            # self.beamStatusLayout.insertWidget(0, w)
            self.shutterControlLayout.insertWidget(0, w)
            self.shutterControlLayout.insertSpacing(0, 10)

    def init_statusbar(self):
        """
        init_statusbar(): description

        :returns: None
        """

        self.status_list = []
        status_title_color = master_colors["status_title_color"]["rgb_str"]
        status_fbk_color = master_colors["status_fbk_color"]["rgb_str"]

        # separator = QtWidgets.QLabel()
        # separator.setMaximumWidth(5000)
        # separator.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # self.status_list.append(separator)

        #         self.status_list.append(ophyd_strLabel(MAIN_OBJ.device('SRStatus_msgL1'),  hdrText='SR Status', title_color=title_color, var_clr=fbk_color))
        #         self.status_list.append(ophyd_strLabel(MAIN_OBJ.device('SRStatus_msgL2'), title_color=title_color, var_clr=fbk_color))
        #         self.status_list.append(ophyd_strLabel(MAIN_OBJ.device('SRStatus_msgL3'), title_color=title_color, var_clr=fbk_color))

        if MAIN_OBJ.device("DNM_A0"):
            self.status_list.append(
                ophyd_aiRangeLabelWidget(
                    MAIN_OBJ.device("DNM_A0"),
                    hdrText="A0",
                    egu="um",
                    title_color=status_title_color,
                    var_clr=status_fbk_color,
                    alarm=(-10000, 10000),
                    warn=(-9999, 9999),
                )
            )

        if MAIN_OBJ.device("DNM_SFX_PIEZO_VOLTS"):
            self.status_list.append(
                ophyd_aiRangeLabelWidget(
                    MAIN_OBJ.device("DNM_SFX_PIEZO_VOLTS"),
                    hdrText="Ax1 Piezo Volts",
                    egu="volts",
                    title_color=status_title_color,
                    var_clr=status_fbk_color,
                    alarm=(-20, 120),
                    warn=(-15, 115),
                )
            )
        if MAIN_OBJ.device("DNM_SFY_PIEZO_VOLTS"):
            self.status_list.append(
                ophyd_aiRangeLabelWidget(
                    MAIN_OBJ.device("DNM_SFY_PIEZO_VOLTS"),
                    hdrText="Ax2 Piezo",
                    egu="volts",
                    title_color=status_title_color,
                    var_clr=status_fbk_color,
                    alarm=(-20, 120),
                    warn=(-15, 115),
                )
            )

        if MAIN_OBJ.device("DNM_AX1_INTERFER_VOLTS"):
            self.status_list.append(
                ophyd_aiLabelWidget(
                    MAIN_OBJ.device("DNM_AX1_INTERFER_VOLTS"),
                    hdrText="Ax1 Interferometer",
                    egu="volts",
                    title_color=status_title_color,
                    var_clr=status_fbk_color,
                    alarm=0.2,
                    warn=0.29,
                )
            )

        if MAIN_OBJ.device("DNM_AX2_INTERFER_VOLTS"):
            self.status_list.append(
                ophyd_aiLabelWidget(
                    MAIN_OBJ.device("DNM_AX2_INTERFER_VOLTS"),
                    hdrText="Ax2 Interferometer",
                    egu="volts",
                    title_color=status_title_color,
                    var_clr=status_fbk_color,
                    alarm=0.2,
                    warn=0.29,
                )
            )

        # self.status_list.append(
        #     ophyd_aiLabelWidget(
        #         MAIN_OBJ.device("DNM_MONO_EV_FBK"),
        #         hdrText="Energy",
        #         egu="eV",
        #         title_color=status_title_color,
        #         var_clr=status_fbk_color,
        #     )
        # )
        # self.status_list.append(
        #     ophyd_mbbiLabelWidget(
        #         MAIN_OBJ.device("DNM_SYSTEM_MODE_FBK"),
        #         hdrText="SR Mode",
        #         title_color=status_title_color,
        #         var_clr=status_fbk_color,
        #     )
        # )
        # self.status_list.append(
        #     ophyd_aiLabelWidget(
        #         MAIN_OBJ.device("DNM_RING_CURRENT"),
        #         hdrText="Ring",
        #         egu="mA",
        #         title_color=status_title_color,
        #         var_clr=status_fbk_color,
        #         alarm=5,
        #         warn=20,
        #     )
        # )
        bl_txt = format_text(
            "Beamline:",
            MAIN_OBJ.get_beamline_name(),
            title_color=status_title_color,
            var_color=status_fbk_color,
        )
        self.status_list.append(QtWidgets.QLabel(bl_txt))

        es_txt = format_text(
            "EndStation:",
            MAIN_OBJ.get_endstation_name(),
            title_color=status_title_color,
            var_color=status_fbk_color,
        )
        self.status_list.append(QtWidgets.QLabel(es_txt))

        if MAIN_OBJ.get_device_backend().find("zmq") > -1:
            dcs_proc_name = get_environ_var('DCS_HOST_PROC_NAME')
            var_color = status_fbk_color
            if MAIN_OBJ.engine_widget.is_dcs_server_local():
                s = "LOCAL"
            else:
                s = "REMOTE"
                var_color = master_colors["app_yellow"]["rgb_str"]

            dcs_txt_txt = format_text(
                f"{dcs_proc_name} Instance:",
                s,
                title_color=status_title_color,
                var_color=var_color,
            )
            self.status_list.append(QtWidgets.QLabel(dcs_txt_txt))

        sm_txt = format_text(
            "Scanning Mode:",
            MAIN_OBJ.get_sample_scanning_mode_string(),
            title_color=status_title_color,
            var_color=status_fbk_color,
        )
        self.status_list.append(QtWidgets.QLabel(sm_txt))

        for sts in self.status_list:
            self.statusBar().addPermanentWidget(sts)
            # add a separator
            self.statusBar().addPermanentWidget(QtWidgets.QLabel("|"))

        # Too many items on the status bar can inhibit shrinking the main window
        self.statusBar().setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored,
                                       QtWidgets.QSizePolicy.Policy.MinimumExpanding)

    def get_points_dct(self):
        dcts = {}
        items = self.lineByLineImageDataWidget.get_plot().get_items()
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

    def do_integrations(self):
        """
        integrate each ROI polygon and emit the values
        :return:
        """
        roi_emit_dct = {}
        integrated_shps = []
        pnt_keys = []
        pnts_dct = self.get_points_dct()
        while not self._roi_queue.empty():
            resp = self._roi_queue.get()
            # print(f"do_integrations: resp={resp}")
            img_data = resp['plot_data']
            energy = resp['cur_ev']
            pnt_keys = list(pnts_dct.keys())
            pnt_keys.sort()
            for shp_id, pnt_dct in pnts_dct.items():
                if shp_id not in integrated_shps:
                    polygon_dct = pnt_dct[shp_id]
                    integrated_shps.append(shp_id)
                    polygon_lst = polygon_dct["points"]
                    if len(polygon_lst) > 3:
                        # need 4 points at least
                        clr = polygon_dct["color"]
                        val = integrate_poly_mask(img_data, polygon_lst, self.visual_signals_obj.get_plot_boundaries())
                        if val:
                            print(
                                f"emitting roi_changed for [ROI_{shp_id}] energy={energy:.2f} eV, value={val}, clr={clr}")
                            # self.roi_spec_changed.emit(f"ROI_{shp_id}", energy, val, clr)
                            roi_emit_dct[shp_id] = {'nm': f"ROI_{shp_id}", 'energy': energy, 'val': val, 'clr': clr}

        # the default is ROI_0 is I0
        keys = list(roi_emit_dct.keys())
        keys.sort()
        if len(keys) > 0:
            i0 = roi_emit_dct[keys[0]]['val']
            if i0 == 0.0:
                i0 = 1.0
            for shp_id, roi_dct in roi_emit_dct.items():
                # skip plotting first value as it is I0
                if shp_id != pnt_keys[0]:
                    # norm_val = float(roi_dct['val']/i0)
                    # Calculate the logarithm of intensity values relative to I0
                    log_intensity = np.log(i0 / roi_dct['val'])
                    print(
                        f"do_integrations: log_intensity={log_intensity:.3f} = np.log({i0:.3f} / {roi_dct['val']:.3f})")
                    self.roi_spec_changed.emit(f"{SPEC_ROI_PREFIX}{shp_id}", roi_dct['energy'], log_intensity,
                                               roi_dct['clr'])

        self._roi_queue.task_done()

        return

    def add_to_roi_stack_spec_plot(self, nm, energy, val, color):
        """
        f"ROI_{shp_id}", energy, val, clr
        add a point or an entire line
        :param nm:
        :param val:
        :return:
        """
        if not self.roiSpectraWidget.curve_exists(nm):
            # ROI has just been added likely during scan so create the curve for all detectors
            roi_ids = self.visual_signals_obj.get_roi_ids()
            roi_clrs = self.visual_signals_obj.get_roi_colors()
            det_nms = self.roiSpectraWidget.get_selected_detectors()
            for det_nm in det_nms:
                self.roiSpectraWidget.add_curve(det_nm, roi_ids, prefix=SPEC_ROI_PREFIX, clr_set=roi_clrs)

        crv_nm = self.roiSpectraWidget.get_complete_curve_name(nm)
        self.roiSpectraWidget.add_xy_point(f"{crv_nm}", energy, val, update=True)

    def add_line_to_plot(self, counter_to_plotter_com_dct):
        """
        add_line_to_plot(): a function to take data (a full line) and add it to the configured plotters
            Needed a flag to monitor when to start a new image

            CNTR2PLOT_ROW = 'row'           #a y position
            CNTR2PLOT_COL = 'col'           #an x position
            CNTR2PLOT_VAL = 'val'           #the point or array of data
            CNTR2PLOT_IS_POINT = 'is_pxp'   #data is from a point by point scan
            CNTR2PLOT_IS_LINE = 'is_lxl'    #data isfrom a line by line scan

        :returns: None
        """
        # print(f'add_line_to_plot: {counter_to_plotter_com_dct}')
        # return
        # det_id = counter_to_plotter_com_dct[CNTR2PLOT_DETID]
        row = int(counter_to_plotter_com_dct[CNTR2PLOT_ROW])
        col = int(counter_to_plotter_com_dct[CNTR2PLOT_COL])
        val = counter_to_plotter_com_dct[CNTR2PLOT_VAL]
        prog_dct = counter_to_plotter_com_dct[CNTR2PLOT_PROG_DCT]
        det_name = counter_to_plotter_com_dct[CNTR2PLOT_DETNAME]
        is_tiled = counter_to_plotter_com_dct[CNTR2PLOT_IS_TILED]
        is_partial = counter_to_plotter_com_dct[CNTR2PLOT_IS_PARTIAL]

        emit_do_integrations = False
        if self.executingScan.scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
            # print(f'add_line_to_plot: {counter_to_plotter_com_dct}')
            if row > 0:
                self.executingScan.image_started = False

            if isinstance(val, dict):
                # this is SIS3820 support that returns multiple channels in a dict
                keys = list(val.keys())
                # print(f"calling addLine for row={row} for image items [{keys}]")
                for det_name in keys:
                    data = val[det_name]
                    if col == 0:
                        self.do_roi_update(det_name, prog_dct)

                    if is_tiled:
                        # print(f"add_line_to_plot: is_tiled: add_vertical_line_at_row_col({det_name}, row={row}, col={col}, {data}, True)")
                        self.lineByLineImageDataWidget.add_vertical_line_at_row_col(det_name, row, col, data, True)
                    else:
                        # print(f"add_line_to_plot: add_vertical_line({det_name}, col={col}, {data}, True)")
                        self.lineByLineImageDataWidget.add_vertical_line(det_name, col, data, True)


            elif det_name is not None:
                # added to support SLS Pixelator
                data = val[det_name]
                if (col == 0) and (row == 0):
                    self.do_roi_update(det_name, prog_dct)
                    self.lineByLineImageDataWidget.reset_item_data(det_name)
                self.lineByLineImageDataWidget.add_vertical_line(det_name, col, data, True)

        elif det_name is not None:
            # added to support SLS Pixelator
            if (col == 0) and (row == 0):
                # print(f"reset_item_data: col == {col} & row == {row}")
                self.do_roi_update(det_name, prog_dct)
                self.lineByLineImageDataWidget.reset_item_data(det_name)
            data = val[det_name]
            self.lineByLineImageDataWidget.add_line_at_row_col(det_name, row, col, data, True)
            # print(f"self.lineByLineImageDataWidget.addLineAtRowCol({det_name}, {row}, {col}, {val[det_name]}, True)")
        else:
            if row > 0:
                # self.image_started = False
                self.executingScan.image_started = False

            if isinstance(val, dict):
                # this is SIS3820 support that returns multiple channels in a dict
                update_plot = False
                update_div = self.executingScan.get_plot_update_divisor()
                # try to reduce the number of times the plotter updates
                if (row % update_div) == 0 or self.executingScan.is_pxp or (self.executingScan.numY - row) < update_div:
                    update_plot = True

                keys = list(val.keys())
                # cur_ev = MAIN_OBJ.device("DNM_ENERGY_RBV").get_position()
                for det_name in keys:
                    data = val[det_name]
                    if row == 0:
                        # # new image starting, have plotter emit a signal with image and rois
                        # plot_data = self.lineByLineImageDataWidget.get_data(det_name)
                        # if not np.isnan(plot_data).any():
                        #     dct = {}
                        #     dct['img_idx'] = prog_dct['PROG']['CUR_IMG_IDX']
                        #     dct['det_name'] = det_name
                        #     dct['plot_data'] = plot_data
                        #     img_idx = dct['img_idx'] - 1
                        #     if img_idx < 0:
                        #         img_idx = 0
                        #     img_idx_key = str(img_idx)
                        #     img_dct = self.executingScan.img_idx_map[img_idx_key]
                        #     e_idx = img_dct['e_idx']
                        #     cur_ev = self.executingScan.ev_setpoints[e_idx]
                        #     #print(self.executingScan.img_idx_map)
                        #     dct['cur_ev'] = cur_ev
                        #     self.update_rois.emit(dct)
                        #     emit_do_integrations = True
                        #     # print(f"add_line_to_plot: [{img_idx}] {det_name} {plot_data.sum()} {cur_ev}")
                        self.do_roi_update(det_name, prog_dct)
                        self.lineByLineImageDataWidget.reset_item_data(det_name)

                    self.lineByLineImageDataWidget.addLine(det_name, row, data, update_plot)

            if emit_do_integrations:
                self.integrate.emit()


        if len(prog_dct) > 0:
            self.non_re_scan_progress.emit(prog_dct)


    def do_roi_update(self, det_name, prog_dct):
        """
         new image starting, have plotter emit a signal with image and rois
        """
        plot_data = self.lineByLineImageDataWidget.get_data(det_name)
        if not np.isnan(plot_data).any():
            dct = {}
            dct['img_idx'] = prog_dct['PROG']['CUR_IMG_IDX']
            dct['det_name'] = det_name
            dct['plot_data'] = plot_data
            img_idx = dct['img_idx'] - 1
            if img_idx < 0:
                img_idx = 0
            img_idx_key = str(img_idx)
            img_dct = self.executingScan.img_idx_map[img_idx_key]
            e_idx = img_dct['e_idx']
            cur_ev = self.executingScan.ev_setpoints[e_idx]
            # print(self.executingScan.img_idx_map)
            dct['cur_ev'] = cur_ev
            self.update_rois.emit(dct)
            # emit_do_integrations = True
            # print(f"add_line_to_plot: [{img_idx}] {det_name} {plot_data.sum()} {cur_ev}")
            self.integrate.emit()


    def add_point_to_plot(self, counter_to_plotter_com_dct):
        """
        add_point_to_plot(): description
        CNTR2PLOT_TYPE_ID = 'type_id'   #to be used to indicate what kind of counter/scan is sending this info
        CNTR2PLOT_ROW = 'row'           #a y position
        CNTR2PLOT_COL = 'col'           #an x position
        CNTR2PLOT_VAL = 'val'           #the point or array of data
        CNTR2PLOT_IMG_CNTR = 'img_cntr' #current image counter
        CNTR2PLOT_EV_CNTR = 'ev_idx'    #current energy counter
        CNTR2PLOT_SP_ID = 'sp_id'       #spatial id this data belongs to
        CNTR2PLOT_IS_POINT = 'is_pxp'   #data is from a point by point scan
        CNTR2PLOT_IS_LINE = 'is_lxl'    #data isfrom a line by line scan
        CNTR2PLOT_SCAN_TYPE = 'scan_type' # the scan_type from types enum of this scan

        for a pPxP scan the plot_dct is like this
        {'row': 16, 'col': 23, 'val': {
            'DNM_SIS3820_CHAN_00': array([50892]),
            'DNM_SIS3820_CHAN_01': array([0]),
            'DNM_SIS3820_CHAN_12': array([50893]),
            'DNM_SIS3820_CHAN_25': array([0]),
            'DNM_SIS3820_CHAN_27': array([50893]),
            }

        :param row: row description
        :type row: row type

        :param tpl: tpl description
        :type tpl: tpl type

        :returns: None
        """
        """ a function to take data (a full line) and add it to the configured plotters
        Need a flag to monitor when to start a new image
        """
        # print(counter_to_plotter_com_dct)
        # return
        # det_id = counter_to_plotter_com_dct[CNTR2PLOT_DETID]
        row = counter_to_plotter_com_dct[CNTR2PLOT_ROW]
        col = point = counter_to_plotter_com_dct[CNTR2PLOT_COL]
        val = counter_to_plotter_com_dct[CNTR2PLOT_VAL]
        prog_dct = counter_to_plotter_com_dct[CNTR2PLOT_PROG_DCT]
        # img_cntr could be used to have the multiple eve regions be their own images with different resolutions
        # img_cntr = counter_to_plotter_com_dct[CNTR2PLOT_IMG_CNTR]
        # ev_cntr = counter_to_plotter_com_dct[CNTR2PLOT_EV_CNTR]
        sp_id = self.executingScan._current_sp_id

        # print('add_point_to_plot:',sp_id, counter_to_plotter_com_dct)
        if type(val) == dict:
            det_names = list(val.keys())
            for det_name in det_names:
                # data = val[k][0]
                if val[det_name].size > 0:
                    data = val[det_name][0]
                    # print(f"val[{det_name}]")
                    if row == 0 and col == 0:
                        self.lineByLineImageDataWidget.reset_item_data(det_name)
                    self.lineByLineImageDataWidget.add_point(det_name, row, col, data, True)
                else:
                    print("counter_to_plotter_com_dct: error", counter_to_plotter_com_dct)

        if len(prog_dct) > 0:
            self.non_re_scan_progress.emit(prog_dct)

    def add_point_to_spectra(self, counter_to_plotter_com_dct):
        """
        add_point_to_spectra():
        CNTR2PLOT_TYPE_ID = 'type_id'   #to be used to indicate what kind of counter/scan is sending this info
        CNTR2PLOT_ROW = 'row'           #a y position
        CNTR2PLOT_COL = 'col'           #an x position
        CNTR2PLOT_VAL = 'val'           #the point or array of data
        CNTR2PLOT_IMG_CNTR = 'img_cntr' #current image counter
        CNTR2PLOT_EV_CNTR = 'ev_idx'    #current energy counter
        CNTR2PLOT_SP_ID = 'sp_id'       #spatial id this data belongs to
        CNTR2PLOT_IS_POINT = 'is_pxp'   #data is from a point by point scan
        CNTR2PLOT_IS_LINE = 'is_lxl'    #data isfrom a line by line scan

        ex:
        {'row': 0, 'col': -916.6666666666666, 'val': {
            'DNM_SIS3820_CHAN_00':
                {'sp_id': 6, 'data': array([50896])},
            'DNM_SIS3820_CHAN_01':
                {'sp_id': 6, 'data': array([0])},
            'DNM_SIS3820_CHAN_06':
                {'sp_id': 6, 'data': array([0])},
            'DNM_SIS3820_CHAN_15':
                {'sp_id': 6, 'data': array([50686])},
            'DNM_SIS3820_CHAN_28':
                {'sp_id': 6, 'data': array([50896])}},
            'is_pxp': True,
            'is_lxl': False,
            'sp_id': 6,
            'det_id': 'SIS3820'}

        :param row: row description
        :type row: row type

        :param tpl: tpl description
        :type tpl: tpl type

        :returns: None
        """
        """ a function to take data (a full line) and add it to the configured plotters """
        # print(f"add_point_to_spectra: {counter_to_plotter_com_dct}")
        # det_id = counter_to_plotter_com_dct[CNTR2PLOT_DETID]
        # row = counter_to_plotter_com_dct[CNTR2PLOT_ROW]
        col = counter_to_plotter_com_dct[CNTR2PLOT_COL]
        val = counter_to_plotter_com_dct[CNTR2PLOT_VAL]
        det_name = counter_to_plotter_com_dct[CNTR2PLOT_DETNAME]
        prog_dct = counter_to_plotter_com_dct[CNTR2PLOT_PROG_DCT]
        # is_tiled = counter_to_plotter_com_dct[CNTR2PLOT_IS_TILED]
        # is_partial = counter_to_plotter_com_dct[CNTR2PLOT_IS_PARTIAL]


        if type(val) == dict:
            det_names = list(val.keys())
            for curve_name in det_names:
                if len(val[curve_name]) > 0:
                    data = val[curve_name][0]
                    self.spectraWidget.add_xy_point(curve_name, col, data, update=True)

        if len(prog_dct) > 0:
            self.non_re_scan_progress.emit(prog_dct)

    def add_line_to_spec_plot(self, counter_to_plotter_com_dct):
        """
        add_line_to_plot(): description

        :param row: row description
        :type row: row type

        :param scan_data: scan_data description
        :type scan_data: scan_data type

        :returns: None
        """
        # det_id = counter_to_plotter_com_dct[CNTR2PLOT_DETID]
        #rows = int(counter_to_plotter_com_dct[CNTR2PLOT_ROW])
        cols = counter_to_plotter_com_dct[CNTR2PLOT_COL]
        val = counter_to_plotter_com_dct[CNTR2PLOT_VAL]
        prog_dct = counter_to_plotter_com_dct[CNTR2PLOT_PROG_DCT]
        det_name = counter_to_plotter_com_dct[CNTR2PLOT_DETNAME]
        # print(f"add_line_to_spec_plot: {counter_to_plotter_com_dct}")
        #return

        # if isinstance(val, dict):
        #     # this is SIS3820 support that returns multiple channels in a dict
        #     keys = list(val.keys())
        #     # print(f"calling addLine for row={row} for image items [{keys}]")
        #     for det_name in keys:
        #         data = val[det_name]
        #         if col == 0:
        #             self.lineByLineImageDataWidget.reset_item_data(det_name)
        #         self.spectraWidget.set_xy_data(det_name, cols, data, update=False)

        #elif det_name is not None:
        if det_name is not None:
            # added to support SLS Pixelator
            data = val[det_name]
            self.spectraWidget.set_xy_data(det_name, cols, data, update=True)

        if len(prog_dct) > 0:
            self.non_re_scan_progress.emit(prog_dct)

    def activate_sel_position_tool(self, en, cb):
        """
        this function is used by scan pluggins to allow the plotter to emit the 'new_selected_position'
        signal and have the plugin specify a handler to update its own fields or whatever it wants
        """
        self.lineByLineImageDataWidget.activate_sel_horizontal_pos_tool(en)
        if en:
            reconnect_signal(self.lineByLineImageDataWidget, self.lineByLineImageDataWidget.new_selected_position, cb)
        else:
            disconnect_signal(self.lineByLineImageDataWidget, self.lineByLineImageDataWidget.new_selected_position)

    def activate_sel_center_position_tool(self, en, cb):
        """
        this function is used by scan pluggins to allow the plotter to emit the 'new_selected_position'
        signal and have the plugin specify a handler to update its own fields or whatever it wants
        """
        self.lineByLineImageDataWidget.activate_sel_center_pos_tool(en)
        if en:
            reconnect_signal(self.lineByLineImageDataWidget, self.lineByLineImageDataWidget.new_selected_position, cb)
        else:
            disconnect_signal(self.lineByLineImageDataWidget, self.lineByLineImageDataWidget.new_selected_position)

    def reset_image_plot(self, shape_only=False):
        self.image_started == False
        # if I want to experiment with adding image after image start by commenting this next line out
        if shape_only:
            self.lineByLineImageDataWidget.delShapePlotItems()
            self.lineByLineImageDataWidget.activate_tool('clsSelectTool')
        else:
            self.lineByLineImageDataWidget.delImagePlotItems(clear_cached_data=True)
            self.lineByLineImageDataWidget.delShapePlotItems()
            self.lineByLineImageDataWidget.set_auto_contrast(True)


    def assign_datafile_names_to_sp_db(self, sp_db, d, image_idx=0):
        """d keys ['thumb_name', 'prefix', 'data_ext', 'stack_dir', 'data_name', 'thumb_ext']"""
        # print 'image_idx=%d' % image_idx
        # print 'd[data_dir]=%s' % d['data_dir']
        # print 'd[data_name]=%s' % d['data_name']

        ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
        dct_put(ado_obj, ADO_CFG_DATA_DIR, d["data_dir"])
        dct_put(ado_obj, ADO_CFG_PTYCHO_CAM_DATA_DIR, self.active_user.ptycho_cam_data_dir)
        dct_put(ado_obj, ADO_CFG_DATA_FILE_NAME, d["data_name"])
        dct_put(ado_obj, ADO_CFG_DATA_THUMB_NAME, d["thumb_name"])
        dct_put(ado_obj, ADO_CFG_PREFIX, d["prefix"])
        dct_put(ado_obj, ADO_CFG_DATA_EXT, d["data_ext"])
        dct_put(ado_obj, ADO_CFG_STACK_DIR, d["stack_dir"])
        dct_put(ado_obj, ADO_CFG_THUMB_EXT, d["thumb_ext"])
        dct_put(ado_obj, ADO_CFG_DATA_IMG_IDX, image_idx)

    def test_type(self, val, typ):
        if (val is None) or (type(val) != typ):
            return False
        else:
            return True

    def test_assign_datafile_names_to_sp_db(self, wdg_com):
        """a test to make sure that the required data items have been set before allowing them
        to continue on to the scan lass
        d keys ['thumb_name', 'prefix', 'data_ext', 'stack_dir', 'data_name', 'thumb_ext']
        """
        _lst = []
        sp_rois = dct_get(wdg_com, WDGCOM_SPATIAL_ROIS)
        sp_ids = sorted(sp_rois.keys())
        for sp_id in sp_ids:
            sp_db = sp_rois[sp_id]
            ado_obj = dct_get(sp_db, SPDB_ACTIVE_DATA_OBJECT)
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_DATA_DIR), str))
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_DATA_FILE_NAME), str))
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_DATA_THUMB_NAME), str))
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_PREFIX), str))
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_DATA_EXT), str))
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_STACK_DIR), str))
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_THUMB_EXT), str))
            _lst.append(self.test_type(dct_get(ado_obj, ADO_CFG_DATA_IMG_IDX), int))

            for v in _lst:
                if not v:
                    return False

        return True

    def determine_num_thumbnail_images_required(self, wdg_com, as_num=False):
        """
        determine_num_thumbnail_images_required(): take a list of spatial regions and check the scan type and retrun
        the number of images that will be needed

        :param sp_rois: sp_rois description
        :type sp_rois: sp_rois type

        :returns: integer number of images required for the scans
        """
        single_image_scans = [
            scan_types.DETECTOR_IMAGE,
            scan_types.OSA_FOCUS,
            scan_types.OSA_IMAGE,
            scan_types.SAMPLE_FOCUS,
            scan_types.SAMPLE_IMAGE,
            scan_types.GENERIC_SCAN,
            scan_types.SAMPLE_LINE_SPECTRUM,
            scan_types.SAMPLE_POINT_SPECTRUM,
        ]
        sp_rois = dct_get(wdg_com, WDGCOM_SPATIAL_ROIS)
        sp_ids = sorted(sp_rois.keys())
        n_imgs = []
        _imgs = 0
        for sp_id in sp_ids:
            sp_db = sp_rois[sp_id]
            scan_type = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)
            if scan_type in single_image_scans:
                # n_imgs.append(1)
                _imgs = 1
            else:
                # n_imgs.append(self.get_num_ev_points(sp_db[SPDB_EV_ROIS]))
                _imgs = self.get_num_ev_points(sp_db[SPDB_EV_ROIS])
                # n_imgs = sp_db[SPDB_EV_NPOINTS] * sp_db[SPDB_POL_NPOINTS]
            n_imgs.append(_imgs)
        if as_num:
            return sum_lst(n_imgs)
        else:
            return n_imgs

    def get_num_ev_points(self, ev_rois):
        """
        make sure to return an int
        """
        n_ev = 0
        _pol = 0
        _ev = 0

        for ev_roi in ev_rois:
            _ev = ev_roi[NPOINTS]
            _pol = len(ev_roi["EPU_POL_PNTS"])
            n_ev += _ev * _pol
        return int(n_ev)

    def apply_user_settings_to_scan(self, scan):
        """
        apply_user_settings_to_scan: query the appConfig settings file andset any flags of the executing scan here

        :param scan: This is the currently configured executing scan
        :type scan: this is a scan plugin that has ScanParamWiget as its parent class

        """
        appConfig.update()
        # set the save all data flag
        val = appConfig.get_bool_value("DATA", "save_all_data")
        if val is not None:
            scan.set_save_all_data(val)

        val = appConfig.get_bool_value("DATA", "save_jpg_thumbnails")
        if val is not None:
            scan.set_save_jpgs(val)

            # set others below


    def get_user_selected_counters(self, det_types=[detector_types.POINT], scan_class=None):
        """
        get the current user selected counters and populate the counter_dct and set that dict to the sscan
        :param sscan:
        :return:
        """

        # here get the counters that the user has selected and populate the counter dict
        sel_dets_lst = self.sel_detectors_panel.get_selected_detectors()
        dets = []
        for d in sel_dets_lst:
            if d["name"].find("SIS3820") > -1:
                # just need the main SIS3820 device as it reads all enabled channels by default
                dev = MAIN_OBJ.device("DNM_SIS3820")
            else:
                dev = MAIN_OBJ.device(d["name"])

            if hasattr(dev, "get_ophyd_device"):
                dev = dev.get_ophyd_device()

            if dev not in dets:
                dets.append(dev)

        # if its a point scan make sure to include the DNM_RING_CURRENT
        # only add Ring current if device exists
        if MAIN_OBJ.device("DNM_RING_CURRENT"):
            dets.append(MAIN_OBJ.device("DNM_RING_CURRENT").get_ophyd_device())

        if len(sel_dets_lst) == 0:
            _logger.error('No detector selected')

        return dets

    def on_test_scan(self, scan_panel_id):
        _logger.info("ok testing scan plugin [%d]" % scan_panel_id)
        self.set_current_scan_pluggin(scan_panel_id)
        self.on_start_scan(testing=True)

    def do_prescan_checks(self):
        '''
        a function where a battery of checks can be executed prior to a scan running
        :return:
        '''
        return self.check_procs_running()

    def check_procs_running(self):
        """
        this function looks for specific process'es running, at the moment in only checks
        that nx_server is running others could be added
        """
        if MAIN_OBJ.get_device_backend() == 'zmq':
            return True
        else:
            return MAIN_OBJ.nx_server_is_running

    def get_detector_names(self, det_dev_lst=[]):
        det_nms = []
        for d in det_dev_lst:
            det_nms.append(d.name)
        return det_nms

    def get_final_det_list(self, dets):
        """
        a function to take a list of detectors and check to see if there needs to be any
        extra processing done to the names, for example the SIS3820 device needs to grab all the
        names of the enabled channels and add them to the final det list, if there is no conditional
        block that applies to the det just return its name in the list

        this function is used to get the list of channels that the plotter will display during scan
        """
        skip_lst = ["DNM_RING_CURRENT"]
        final_det_nms = []
        for det_dev in dets:
            d_nm = det_dev.name
            if d_nm in skip_lst:
                continue
            if d_nm.find("DNM_SIS3820") > -1:
                # dev = MAIN_OBJ.device(d_nm)
                # get all enabled channels
                chan_id_lst, chan_nm_lst, ch_fbk_attrs = det_dev.get_enabled_chans()
                for _dnm in chan_nm_lst:
                    final_det_nms.append(_dnm)
            else:
                final_det_nms.append(d_nm)
        return final_det_nms

    def on_start_scan(self, testing=False):
        """
        on_start_scan():

        Essentially the following starts a scan, but before it can do that it needs to configure everything so that scan plans
        will be executed by hte BlueSky RunEngine and that the data will be plotted when the detectors collect it, and not all scans
        are the same, so the type of plotting (line by line, point by point or just 2d spectra plotting needs to be setup correctly,
        the main job of every block below that "handles" a particular scan type /types is the following:
         - generate the required filenames
         - assign the filenames to the executing scan class
         - call scan_class.configure()
         - get the selected detectors
         - generate the BlueSky scan plan
         - initialise the subscriptions to the plotting functions

        :returns: None
        """

        if not self.do_prescan_checks():
            _logger.error(
                'on_start_scan: pre scan checks failed as required process(s) are not running, aborting scan execution')
            return

        # if the scan plugin is disabled just return
        if not self.scan_tbox_widgets[self.scan_panel_idx].isEnabled():
            return

        # set main gui widgets up for running a scan
        self.set_buttons_for_scanning()

        # force shutter control back to Auto
        self.on_shutterCntrlComboBox(0)  # Auto

        self.executingScan = None
        self.stopping = False

        # make sure the data dir is up to date in case the 24 hour time has rolled over
        self.active_user.create_data_dir()
        # default to locked aspect ratio

        # set the data dir path translations in nx_server

        # keep the scan plugin from firing any signals that would cause other widgets to respond
        self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(True)
        # make sure that the current scan parameters are recorded
        self.scan_tbox_widgets[self.scan_panel_idx].update_last_settings()

        self.cur_wdg_com = self.scan_tbox_widgets[self.scan_panel_idx].get_roi()

        if (self.cur_wdg_com is None) or (
                len(self.cur_wdg_com[SPDB_SPATIAL_ROIS]) == 0
        ):
            self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(False)
            _logger.info(
                "there was a problem retrieving the data from the scan pluggin via get_roi()"
            )
            self.set_buttons_for_starting()
            return

        # init some variables
        self.data = []
        MAIN_OBJ.clear_scans()

        # if hasattr(self, "lineByLineImageDataWidget"):
        #     self.reset_image_plot()

        self.cur_ev_idx = 0
        new_stack_dir = False
        # a temporary variable to point to either the spec or image plotter
        _scan_plotter = None

        # ok allow the scan plugin to fire signals again
        self.scan_tbox_widgets[self.scan_panel_idx].blockSignals(False)

        # assign these values that are used to decide which GUI signals to connect and disconnect
        self.set_cur_scan_type(self.scan_tbox_widgets[self.scan_panel_idx].type)
        self.set_cur_scan_sub_type(self.scan_tbox_widgets[self.scan_panel_idx].sub_type)

        scan_type = self.get_cur_scan_type()
        scan_sub_type = self.get_cur_scan_sub_type()

        # get an instance of the actual scan class that is used to configure and connect to the sscan records
        # sscan = self.scan_tbox_widgets[self.scan_panel_idx].get_sscan_instance()
        # scan_plan = self.scan_tbox_widgets[self.scan_panel_idx].get_scan_plan(detectors=[MAIN_OBJ.device('POINT_DET')])
        self.scan_tbox_widgets[self.scan_panel_idx].on_plugin_scan_start()
        scan_class = self.scan_tbox_widgets[self.scan_panel_idx].get_scan_class()
        scan_class.set_active_user(self.active_user)
        scan_class.scan_type = scan_type
        # MAIN_OBJ.engine_widget.engine.plan_creator = lambda: scan_plan

        if testing and (self.scan_tbox_widgets[self.scan_panel_idx].test_sp_db is None):
            # the plugin doesnt have the support required for testing so turn testing off
            testing = False
            _logger.error(
                "User requested TESTING but the scan plugin does not have a test_sp_db configured, so turning testing off"
            )
            return

        self.apply_user_settings_to_scan(scan_class)
        self.executingScan = scan_class
        self.executingScan.disconnect_signals()
        self.executingScan.clear_subscriptions(MAIN_OBJ.engine_widget)

        # make sure that all data required by scan metadata is loaded into scan
        fprms_pnl = self.get_pref_panel("FocusParams")
        cur_zp_def = fprms_pnl.get_cur_zp_def()
        self.executingScan.set_zoneplate_info_dct(cur_zp_def)

        # grab some information used by all scans below
        sp_rois = dct_get(self.cur_wdg_com, WDGCOM_SPATIAL_ROIS)
        sp_ids = sorted(sp_rois.keys())
        self.cur_sp_rois = copy.copy(sp_rois)

        scan_class.set_spatial_id_list(sp_ids)
        if not scan_class.pre_flight_chk():
            _logger.error("scan class failed pre flight check, not executing scan")
            return

        # a list of basic scans that use the same configuration block below
        _simple_types = [
            scan_types.DETECTOR_IMAGE,
            scan_types.OSA_IMAGE,
            scan_types.OSA_FOCUS,
            scan_types.GENERIC_SCAN,
            scan_types.SAMPLE_FOCUS,
            scan_types.COARSE_IMAGE,
            scan_types.COARSE_GONI,
            scan_types.TWO_VARIABLE_IMAGE
        ]
        _multispatial_types = [
            scan_types.SAMPLE_IMAGE,
            scan_types.SAMPLE_LINE_SPECTRUM,
            scan_types.SAMPLE_POINT_SPECTRUM,
        ]  # , scan_types.TOMOGRAPHY]
        _stack_types = [scan_types.SAMPLE_IMAGE_STACK, scan_types.TOMOGRAPHY]

        if hasattr(self, "lineByLineImageDataWidget") and scan_type != scan_types.PATTERN_GEN:
            self.reset_image_plot()
        ########################################################################
        ############ OK setup for each scan type(s) ############################
        ########################################################################
        if scan_type in _simple_types:
            sp_id = sp_ids[0]
            sp_db = sp_rois[sp_id]

            master_seq_dct = MAIN_OBJ.get_master_file_seq_names(
                self.active_user.get_data_dir(),
                thumb_ext="jpg",
                dat_ext="hdf5",
                stack_dir=False,
                num_desired_datafiles=1,
                prefix_char=MAIN_OBJ.get_datafile_prefix(),
                dev_backend=MAIN_OBJ.get_device_backend(),
            )
            self.assign_datafile_names_to_sp_db(sp_db, master_seq_dct[0])
            ret = scan_class.configure(self.cur_wdg_com, sp_id=sp_id, line=False)
            if not ret:
                # the configuration did not pass validation, most likely the scan velocity
                self.set_buttons_for_starting()
                return

            if scan_sub_type is scan_sub_types.POINT_BY_POINT:
                # FEB 22 2023 self.point_det.set_scan_type(scan_type)
                # assign the detectors to use
                dets = self.get_user_selected_counters(det_types=[detector_types.POINT], scan_class=scan_class)
                scan_plan = scan_class.generate_scan_plan(detectors=dets)
            else:
                dets = self.get_user_selected_counters(det_types=[detector_types.LINE], scan_class=scan_class)
                scan_plan = scan_class.generate_scan_plan(detectors=dets)

            if scan_type == scan_types.GENERIC_SCAN:
                final_det_nms = self.get_final_det_list(dets)
                self.init_point_spectra(sp_ids, final_det_nms)
                if hasattr(self.executingScan, 'data_plot_type'):
                    if self.executingScan.data_plot_type == 'line':
                        # added to support DCS (Pixelator) which returns all data at end of scan as a point spec line
                        scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_line_to_spec_plot, dets)
                    else:
                        scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_point_to_spectra, dets)
                else:
                    scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_point_to_spectra, dets)

            elif (scan_type in [scan_types.COARSE_IMAGE, scan_types.COARSE_GONI, scan_types.SAMPLE_FOCUS]) and (
                    scan_sub_type is scan_sub_types.LINE_UNIDIR):
                scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_line_to_plot, dets)

            elif hasattr(self.executingScan, 'data_plot_type'):
                # added to support for other labs scans like SLS det scan is line by line
                if self.executingScan.data_plot_type == 'line':
                    # SLS Pixelator returns all data for a positioner scan at the end so plot entire line
                    scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_line_to_plot, dets)
                    #
                else:
                    scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_point_to_plot, dets)
            else:
                # pass along the detector list to be connected to emitters
                scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_point_to_plot, dets)

            # Initialize the plotting widgets for the plotting data
            numX = dct_get(sp_db, SPDB_XNPOINTS)
            numY = dct_get(sp_db, SPDB_YNPOINTS)
            rect = dct_get(sp_db, SPDB_RECT)
            img_type = image_types.IMAGE
            # det_nms = self.get_detector_names(dets)
            if scan_type in [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]:
                # override numY to use the ZZ NPOINTS
                numY = dct_get(sp_db, SPDB_ZZNPOINTS)
                img_type = image_types.FOCUS

            if scan_type == scan_types.GENERIC_SCAN:
                # init spec plot here
                _scan_plotter = self.spectraWidget
            else:
                _scan_plotter = self.lineByLineImageDataWidget
                final_det_nms = self.get_final_det_list(dets)
                _scan_plotter.init_image_items(final_det_nms, img_type, numY, numX, parms={SPDB_RECT: rect})

        ####################################################################################################################
        elif scan_type in _multispatial_types:
            line = True
            num_data_files = 1 if scan_type == scan_types.SAMPLE_POINT_SPECTRUM else len(sp_ids)
            #num_images_lst = self.determine_num_thumbnail_images_required(self.cur_wdg_com)
            master_seq_dct = MAIN_OBJ.get_master_file_seq_names(
                self.active_user.get_data_dir(),
                thumb_ext="jpg",
                dat_ext="hdf5",
                stack_dir=False,
                num_desired_datafiles=num_data_files,
                prefix_char=MAIN_OBJ.get_datafile_prefix(),
                dev_backend=MAIN_OBJ.get_device_backend(),
            )

            idx = 0
            for sp_id in sp_ids:
                sp_db = sp_rois[sp_id]
                if scan_type == scan_types.SAMPLE_POINT_SPECTRUM:
                    # for point spec all spatial regions use same datafile but different entrys
                    self.assign_datafile_names_to_sp_db(sp_db, master_seq_dct[0], image_idx=0)
                else:
                    self.assign_datafile_names_to_sp_db(sp_db, master_seq_dct[idx], image_idx=idx)
                idx += 1

            # if (scan_type == scan_types.SAMPLE_POINT_SPECTRUM):
            if scan_type in spectra_type_scans:
                # here I need to init it with the number of sp_ids (spatial points)
                # self.init_point_spectra(num_curves=len(sp_ids))
                line = False

            self.set_cur_scan_sub_type(dct_get(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE))
            scan_class.set_datafile_names_dict(master_seq_dct)
            sp_id = sp_ids[0]  # scan_class.get_next_spatial_id()
            ret = scan_class.configure(self.cur_wdg_com, sp_id=sp_id, ev_idx=0, line=line)
            if not ret:
                # the configuration did not pass validation, most likely the scan velocity
                self.set_buttons_for_starting()
                return

            if scan_sub_type is scan_sub_types.POINT_BY_POINT:
                # FEB 22 2023 self.point_det.set_scan_type(scan_type)
                if scan_class.e712_enabled:
                    if scan_type == scan_types.SAMPLE_POINT_SPECTRUM:
                        # use point detector
                        dets = self.get_user_selected_counters(det_types=[detector_types.POINT], scan_class=scan_class)
                        scan_plan = scan_class.generate_scan_plan(detectors=dets)
                    else:
                        if scan_class.is_fine_scan:
                            # use the flyer scan because we are using the E712 wavegenerator
                            dets = self.get_user_selected_counters(det_types=[detector_types.LINE_FLYER],
                                                                   scan_class=scan_class)
                        else:
                            dets = self.get_user_selected_counters(det_types=[detector_types.LINE],
                                                                   scan_class=scan_class)
                        scan_plan = scan_class.generate_scan_plan(detectors=dets)
                else:
                    # use point detector
                    dets = self.get_user_selected_counters(det_types=[detector_types.POINT], scan_class=scan_class)
                    scan_plan = scan_class.generate_scan_plan(detectors=dets)
            else:
                if scan_class.is_fine_scan:
                    # use the flyer scan because we are using the E712 wavegenerator
                    dets = self.get_user_selected_counters(det_types=[detector_types.LINE_FLYER], scan_class=scan_class)
                else:
                    dets = self.get_user_selected_counters(det_types=[detector_types.LINE], scan_class=scan_class)
                scan_plan = scan_class.generate_scan_plan(detectors=dets)

            # if (scan_type == scan_types.GENERIC_SCAN):
            if scan_type in spectra_type_scans:
                # final_det_nms = self.get_final_det_list(dets)
                # self.init_point_spectra(sp_ids, final_det_nms)
                scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_point_to_spectra, dets)
                _scan_plotter = self.spectraWidget
            else:
                _scan_plotter = self.lineByLineImageDataWidget
                if hasattr(self.executingScan, 'data_plot_type'):
                    # added to support for other labs scans like SLS det scan is line by line
                    if self.executingScan.data_plot_type == 'line':
                        plotting_func = self.add_line_to_plot
                    else:
                        plotting_func = self.add_point_to_plot
                else:
                    plotting_func = self.add_line_to_plot
                    if scan_sub_type is scan_sub_types.POINT_BY_POINT:
                            # FEB 22 2023 self.point_det.set_scan_type(scan_type)
                            if scan_class.e712_enabled:
                                # PxP controlled by triggers from E712, triggers an entire line of points hence add_line_to_plot()
                                plotting_func = self.add_line_to_plot
                            else:
                                # PxP controlled by software
                                plotting_func = self.add_point_to_plot
                if plotting_func:
                    scan_class.init_subscriptions(MAIN_OBJ.engine_widget, plotting_func, dets)
                else:
                    _logger.error('Plotting function could not be determined so no plotting subscription possible')
                ###################

            if scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
                self.lineByLineImageDataWidget.set_lock_aspect_ratio(False)
                numX = dct_get(sp_db, SPDB_EV_NPOINTS)
            else:
                numX = dct_get(sp_db, SPDB_XNPOINTS)

            numY = dct_get(sp_db, SPDB_YNPOINTS)
            rect = dct_get(sp_db, SPDB_RECT)

            # det_nms = self.get_detector_names(dets)
            # _scan_plotter = self.lineByLineImageDataWidget
            final_det_nms = self.get_final_det_list(dets)
            if _scan_plotter == self.spectraWidget:
                self.init_point_spectra(sp_ids, final_det_nms)
            else:
                # assume its the lineByLineImageDataWidget
                img_type = image_types.IMAGE
                if scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
                    img_type = image_types.LINE_PLOT
                _scan_plotter.init_image_items(final_det_nms, img_type, numY, numX, parms={SPDB_RECT: rect})

        ####################################################################################################################
        elif (scan_type == scan_types.SAMPLE_IMAGE_STACK
              or scan_type == scan_types.TOMOGRAPHY
              or scan_type == scan_types.PATTERN_GEN):
            # use first sp_DB to determine if point by point or line unidir
            idx = 0
            img_idx_fname_dct = {}
            sp_db_seq_names = []
            for sp_id in sp_ids:
                sp_db = sp_rois[sp_id]
                # get num images for this sp_id
                num_images = self.determine_num_thumbnail_images_required(
                    self.cur_wdg_com
                )[idx]
                master_seq_dct = MAIN_OBJ.get_master_file_seq_names(
                    self.active_user.get_data_dir(),
                    thumb_ext="jpg",
                    dat_ext="hdf5",
                    num_desired_datafiles=num_images,
                    new_stack_dir=True,
                    prefix_char=MAIN_OBJ.get_datafile_prefix(),
                    dev_backend=MAIN_OBJ.get_device_backend(),
                )
                sp_db_seq_names.append(master_seq_dct)
                d_keys = list(master_seq_dct.keys())
                if len(sp_ids) > 1:
                    # each spatial roi needs a filename dict
                    for i in range(num_images):
                        k = d_keys[i]
                        self.assign_datafile_names_to_sp_db(sp_db, master_seq_dct[k], image_idx=i)
                else:
                    self.assign_datafile_names_to_sp_db(sp_rois[sp_ids[0]], master_seq_dct[0])

            self.set_cur_scan_sub_type(dct_get(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE))
            scan_class.set_datafile_names_dict(master_seq_dct)
            sp_id = scan_class.get_next_spatial_id()
            ret = scan_class.configure(self.cur_wdg_com, sp_id=sp_id, ev_idx=0, line=True)
            if not ret:
                # the configuration did not pass validation, most likely the scan velocity
                self.set_buttons_for_starting()
                return
            if scan_sub_type is scan_sub_types.POINT_BY_POINT:
                # FEB 22 2023 self.point_det.set_scan_type(scan_type)
                if scan_class.e712_enabled:
                    # use the flyer scan because we are using the E712 wavegenerator
                    dets = self.get_user_selected_counters(
                        det_types=[detector_types.LINE], scan_class=scan_class
                    )
                    scan_plan = scan_class.generate_scan_plan(
                        detectors=dets
                    )
                else:
                    # use point detector
                    dets = self.get_user_selected_counters(
                        det_types=[detector_types.POINT], scan_class=scan_class
                    )
                    scan_plan = scan_class.generate_scan_plan(
                        detectors=dets
                    )
            else:
                dets = self.get_user_selected_counters(det_types=[detector_types.LINE], scan_class=scan_class)
                scan_plan = scan_class.generate_scan_plan(
                    detectors=dets
                )

            if scan_type == scan_types.PATTERN_GEN:
                # scan_class.init_subscriptions(
                #     MAIN_OBJ.engine_widget, self.add_point_to_plot, dets
                # )
                pass
            # apr 12 2023
            if hasattr(self.executingScan, 'data_plot_type'):
                # added to support for other labs scans like SLS det scan is line by line
                if self.executingScan.data_plot_type == 'line':
                    plotting_func = self.add_line_to_plot
                else:
                    plotting_func = self.add_point_to_plot
            else:
                if scan_sub_type is scan_sub_types.POINT_BY_POINT:
                    if scan_class.e712_enabled:
                        #scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_line_to_plot, dets)
                        plotting_func = self.add_line_to_plot
                    else:
                        #scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_point_to_plot, dets)
                        plotting_func = self.add_point_to_plot
                else:
                    scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_line_to_plot, dets)
                    plotting_func = self.add_point_to_plot

            if plotting_func:
                scan_class.init_subscriptions(MAIN_OBJ.engine_widget, plotting_func, dets)
            else:
                _logger.error('Plotting function could not be determined so no plotting subscription possible')

            # now create a sequential list of image names in spatial id order
            cntr = 0
            for i in range(num_images):
                for j in range(len(sp_db_seq_names)):
                    stack_flbl = "%s img/%d" % (
                        sp_db_seq_names[j][i]["data_name"],
                        cntr + 1,
                    )
                    sp_db_seq_names[j][i]["stack_flbl"] = stack_flbl
                    img_idx_fname_dct[cntr] = sp_db_seq_names[j][i]
                    cntr += 1

            master_seq_dct = img_idx_fname_dct

            final_det_nms = self.get_final_det_list(dets)
            numX = dct_get(sp_db, SPDB_XNPOINTS)
            numY = dct_get(sp_db, SPDB_YNPOINTS)
            rect = dct_get(sp_db, SPDB_RECT)
            # det_nms = self.get_detector_names(dets)
            _scan_plotter = self.lineByLineImageDataWidget
            final_det_nms = self.get_final_det_list(dets)
            if scan_type != scan_types.PATTERN_GEN:
                _scan_plotter.init_image_items(final_det_nms, image_types.IMAGE, numY, numX, parms={SPDB_RECT: rect})

        ####################################################################################################################
        elif scan_type == scan_types.PTYCHOGRAPHY:
            _scan_plotter = self.lineByLineImageDataWidget
            sp_id = sp_ids[0]
            sp_db = sp_rois[sp_id]
            master_seq_dct = MAIN_OBJ.get_master_file_seq_names(
                self.active_user.get_data_dir(),
                thumb_ext="jpg",
                dat_ext="hdf5",
                stack_dir=False,
                num_desired_datafiles=1,
                prefix_char=main_obj.get_datafile_prefix(),
                dev_backend=MAIN_OBJ.get_device_backend(),
            )
            self.assign_datafile_names_to_sp_db(sp_db, master_seq_dct[0])
            ret = scan_class.configure(self.cur_wdg_com, sp_id=sp_id, line=False)
            if not ret:
                # the configuration did not pass validation, most likely the scan velocity
                self.set_buttons_for_starting()
                return
            # FEB 22 2023 self.point_det.set_scan_type(scan_type)
            dets = self.get_user_selected_counters(det_types=[detector_types.POINT], scan_class=scan_class)
            scan_plan = scan_class.generate_scan_plan(detectors=dets)
            # this should be something else here
            scan_class.init_subscriptions(MAIN_OBJ.engine_widget, self.add_line_to_plot, dets)
            # if it exists in configuration, add the CCD detector so that it can be unstaged later if scan is aborted
            final_det_nms = self.get_final_det_list(dets)
            numX = dct_get(sp_db, SPDB_XNPOINTS)
            numY = dct_get(sp_db, SPDB_YNPOINTS)
            rect = dct_get(sp_db, SPDB_RECT)
            _scan_plotter = self.lineByLineImageDataWidget
            _scan_plotter.init_image_items(final_det_nms, image_types.IMAGE, numY, numX, parms={SPDB_RECT: rect})
            ###################################################################################################################
        else:
            _logger.error("start_scan: unsupported scan type [%d]" % scan_type)
            self.set_buttons_for_starting()
            return

        # set the visual_signals_obj plot min and maxs
        self.visual_signals_obj.set_plot_boundaries(rect[0], rect[1], rect[2], rect[3])
        if len(final_det_nms) < 1:
            _logger.error("No detectors are selected, the scan cannot be executed")
            self.set_buttons_for_starting()
            return

        _scan_plotter.set_selected_detectors(final_det_nms)
        self.roiSpectraWidget.set_selected_detectors(final_det_nms)
        self.roiSpectraWidget.clear_plot()
        # roi_ids = list of integers that identify the ROI
        roi_ids = self.visual_signals_obj.get_roi_ids()
        roi_clrs = self.visual_signals_obj.get_roi_colors()
        self.roiSpectraWidget.create_curves(final_det_nms, roi_ids, prefix=SPEC_ROI_PREFIX, clr_set=roi_clrs)

        if _scan_plotter == self.lineByLineImageDataWidget:
            self.on_image_start()

        # make sure scan is ready to start, call base class function
        ret = scan_class.go_to_scan_start()
        if not ret:
            _logger.error("The scan violates some limit on the positioners involved, the scan cannot be executed")
            self.set_buttons_for_starting()
            return

        # # assign the scan plan to the engine
        # MAIN_OBJ.engine_widget.engine.plan_creator = lambda: scan_plan

        MAIN_OBJ.set("SCAN.CFG.WDG_COM", self.cur_wdg_com)

        # make sure all scans have set the data file names to their respective active data objects before allowing scan
        # to start
        if not self.test_assign_datafile_names_to_sp_db(self.cur_wdg_com):
            _logger.error(
                "start_scan: incorrectly configured scan: data file names not assigned to active data object"
            )
            self.set_buttons_for_starting()
            return

        # ok all good lets run the scan
        if hasattr(self, "scan_progress_table"):
            self.scan_progress_table.set_queue_file_list(get_thumb_file_name_list(master_seq_dct))
            # self.scan_progress_table.load_wdg_com(self.cur_wdg_com, sp_id)
            if scan_type == scan_types.TOMOGRAPHY:
                # tomo only has one spatial ID yet there is one defined per angle, only send one though
                self.scan_progress_table.load_wdg_com(
                    self.cur_wdg_com, sorted([list(sp_rois.keys())[0]])
                )
            elif scan_type == scan_types.SAMPLE_POINT_SPECTRUM:
                # point spec only has multi spatial IDs yet there is one file, only send one though
                self.scan_progress_table.load_wdg_com(
                    self.cur_wdg_com, sorted([list(sp_rois.keys())[0]])
                )
            else:
                self.scan_progress_table.load_wdg_com(
                    self.cur_wdg_com, sorted(list(sp_rois.keys()))
                )

            if scan_type == scan_types.SAMPLE_IMAGE_STACK:
                self.scan_progress_table.set_directory_label(
                    master_seq_dct[list(master_seq_dct.keys())[0]]["stack_dir"]
                )
            else:
                self.scan_progress_table.set_directory_label(
                    master_seq_dct[list(master_seq_dct.keys())[0]]["data_dir"]
                )

        self.connect_executingScan_signals(testing=testing)

        if testing:
            self.executingScan.set_save_all_data(True)

        self.executingScan.image_started = False

        self.start_time = time.time()
        self.cur_dets = dets

        # set start time and start elapsed timer that updates at 1 sec intervals
        self.executingScan.set_scan_as_aborted(False)
        self.start_time = time.time()
        self.scan_elapsed_timer.start(1000)

        #########################################################
        if MAIN_OBJ.get_device_backend().find("zmq") > -1:
            dct_put(self.executingScan.wdg_com, "SCAN_REQUEST", self.executingScan.ui_module.get_scan_request())
            scan_params = [
                    json.dumps({'command': 'scanRequest'}),  # First part (JSON-encoded)
                    dict_to_json(self.executingScan.wdg_com)
                ]
            MAIN_OBJ.engine_widget.engine.send_scan_request(scan_params)

        else:
            # running Bluesky engine
            # Start the RunEngine
            # assign the scan plan to the engine
            MAIN_OBJ.engine_widget.engine.plan_creator = lambda: scan_plan

            # MAIN_OBJ.engine_widget.engine.md["user"] = "guest"
            # MAIN_OBJ.engine_widget.engine.md["host"] = "myNotebook"
            MAIN_OBJ.engine_widget.control.state_widgets["start"].clicked.emit()

    def on_show_dcs_server_msgs(self, chkd):
        """
        user selectable from the 'Help' menu, connect the DCS Server msg_changed signal for debugging
        :param chkd:
        :return:
        """
        if chkd:

            reconnect_signal(
                MAIN_OBJ.engine_widget.engine,
                MAIN_OBJ.engine_widget.engine.msg_changed,
                self.print_dcs_server_msg,
            )
        else:
            self._dcs_server_msg_headers = {}
            disconnect_signal(
                MAIN_OBJ.engine_widget.engine, MAIN_OBJ.engine_widget.engine.msg_changed
            )

    def on_show_runengine_docs(self, chkd):
        """
        user selectable from the 'Help' menu, connect the BlueSky RunEngine doc_changed signal for debugging
        :param chkd:
        :return:
        """
        if chkd:
            reconnect_signal(
                MAIN_OBJ.engine_widget.engine,
                MAIN_OBJ.engine_widget.engine.doc_changed,
                self.print_re_doc,
            )
        else:
            disconnect_signal(
                MAIN_OBJ.engine_widget.engine, MAIN_OBJ.engine_widget.engine.doc_changed
            )

    def on_validate_saved_files(self, chkd):
        """
        user selectable from the 'Help' menu, connect the Validate_saved_files changed signal for debugging
        :param chkd:
        :return:
        """
        if chkd:
            modal = uic.loadUi(os.path.join(os.getcwd(), "ui", "nxstxm_validate.ui"))
            ss = get_style()
            modal.setStyleSheet(ss)
            res = modal.exec_()

            if res:
                self.actionValidate_saved_files.setChecked(True)
                self.validate_saved_files["uname"] = modal.unameFld.text()
                self.validate_saved_files["pword"] = modal.pwordFld.text()
                self.validate_saved_files["doit"] = True
            else:
                chkd = False

        if not chkd:
            self.actionValidate_saved_files.setChecked(False)
            self.validate_saved_files["uname"] = ""
            self.validate_saved_files["pword"] = ""
            self.validate_saved_files["doit"] = False

    def print_dcs_server_msg(self, msg):
        """
        simple msg handler for debugging
        :param msg:
        :return:
        """
        # print(msg)
        # self.rr(msg[0], msg)
        hdr = msg[0]
        if hdr not in self._dcs_server_msg_headers.keys():
            # set it as not selected
            self._dcs_server_msg_headers[hdr] = False

        if self._dcs_server_msg_headers[hdr]:
            #add the message to the dcsServerWindow
            #self.add_to_dcs_server_window(QtGui.QColor("black"), f"> {msg}")
            s = f'<font color="black"><b>> </b>{msg}</font>'
            self.add_to_dcs_server_window(QtGui.QColor("black"), f"{s}")



    def print_re_doc(self, name, doc):
        """
        simple msg handler for debugging
        :param msg:
        :return:
        """
        print(name, doc)

    def on_dcs_msg_to_app(self, msg):
        """
        handle specific messages from teh DCS server to pyStxm
        """
        print(f"on_dcs_msg_to_app: received[{msg}]")
        # do something to the scan_q_table if the message is 'filename'
        msg_key = list(msg.keys())[0]
        if msg_key == 'filename':
            self.scan_progress_table.override_filenames(msg['filename']['name'])

    def on_new_dcs_server_data(self, h5_file_dct: dict) -> None:
        """
        Thi handler receives a default dictonary from the DCS server, it is the default data dictionary required by
        the ContactSheet widget
        """

        # TODO: in the future all data wil be received from a server so this check before calling is an interum during
        #  refactor
        if hasattr(self.contact_sheet, "create_thumbnail_from_h5_file_dct"):
            # add the data to contact sheet
            self.contact_sheet.create_thumbnail_from_h5_file_dct(h5_file_dct)

    def on_run_engine_progress(self, re_prog_dct):
        """
        accepts a progress dictionarey from the run engine
        """
        #print(f"on_run_engine_progress: {re_prog_dct}")
        if len(re_prog_dct) > 0:
            dct = make_progress_dict(
                sp_id=0, percent=re_prog_dct["prog"], cur_img_idx=re_prog_dct["scan_idx"]
            )
            self.on_scan_progress(dct)

    def on_execution_status_changed(self, run_uids):
        """
        typically called when a scan completes, takes a list of run_uids
        """
        # print("on_execution_status_changed: ", run_uids)
        self.on_state_changed(MAIN_OBJ.engine_widget.engine.state, run_uids)

    # def on_status_changed(self, state_str, style_sheet):
    #     self.scanActionLbl.setText(state_str)
    #     self.scanActionLbl.setStyleSheet(style_sheet)

    def on_state_changed(self, state_str, run_uids):
        """
        fires when the RunEngine is done
        :param state_str:
        :return:
        """
        if self.executingScan == None:
            return
        # print('on_state_changed: [%s]' % state_str)
        if state_str.find("paused") > -1:
            pass
        elif state_str.find("idle") > -1:
            self.executingScan.on_scan_done()
            self.executingScan.clear_subscriptions(MAIN_OBJ.engine_widget)
            # RUSS FEB25 MAIN_OBJ.engine_widget.unsubscribe_cb(self.rr_id)
            self.disconnect_executingScan_signals()
            self.set_buttons_for_starting()

            if MAIN_OBJ.get_device_backend().find("zmq") == -1:
                # fireoff a thread to handle saving data to an nxstxm file
                # ONLY if BACKEND is NOT zmq because zmq doesnt
                worker = Worker(
                    self.do_data_export, run_uids, "datadir", False
                )  # Any other args, kwargs are passed to the run function
                # # Execute
                self._threadpool.start(worker)

            # else:
            #     # using DCS server so

            #only if the scan was not aborted do we save the execution time
            if not self.stopping:
                # update the scan time estimator database
                scan_plugin = self.scan_tbox_widgets[self.scan_panel_idx]
                scan_plugin.update_scantime_estimate(self.elapsed_time)


    def do_data_export(self, run_uids, datadir, is_stack_dir=False, progress_callback=None):
        """
        executes inside a threadpool so it doesnt bog down the main event loop
        :return:CCDViewerPanel
        """

        _logger.info("do_data_export: ok starting export")
        _logger.debug(f"do_data_export: run_uids {run_uids}")

        data_dir = self.active_user.get_data_dir()
        fprefix = str(MAIN_OBJ.get_datafile_prefix()) + str(
            get_next_file_num_in_seq(data_dir, extension="hdf5"))

        scan_type = self.get_cur_scan_type()
        first_uid = run_uids[0]
        is_stack = False
        nx_app_def = "nxstxm"

        if scan_type is scan_types.PATTERN_GEN:
            # we only want the information in the main
            # first_uid = run_uids[4]
            # run_uids = [first_uid]
            pass

        if scan_type in [scan_types.SAMPLE_IMAGE_STACK, scan_types.TOMOGRAPHY]:
            # could also just be multiple rois on a single energy
            data_dir = os.path.join(data_dir, fprefix)
            is_stack = True
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            MAIN_OBJ.save_nx_files(run_uids, fprefix, data_dir, nx_app_def=nx_app_def, host='localhost', port='5555',
                                   verbose=False)

        elif scan_type in [scan_types.PTYCHOGRAPHY]:
            nx_app_def = "nxptycho"
            data_dir = self.executingScan.get_current_scan_data_dir()
            fprefix = data_dir.split("\\")[-1]
            MAIN_OBJ.save_nx_files(run_uids, fprefix, data_dir, nx_app_def=nx_app_def, host='localhost',
                                   port='5555', verbose=False)
            return

        # elif(scan_type is scan_types.SAMPLE_POINT_SPECTRUM):
        elif scan_type in spectra_type_scans:
            MAIN_OBJ.save_nx_files(run_uids, fprefix, data_dir, nx_app_def=nx_app_def, host='localhost', port='5555',
                                   verbose=False)

        else:
            MAIN_OBJ.save_nx_files(run_uids, fprefix, data_dir, nx_app_def=nx_app_def, host='localhost', port='5555',
                                   verbose=False)

        if self.validate_saved_files["doit"]:
            worker = Worker(
                validate_nxstxm_file,
                os.path.join(data_dir, fprefix + ".hdf5"),
                self.validate_saved_files["uname"],
                self.validate_saved_files["pword"],
            )
            # # Execute
            self._threadpool.start(worker)

    def get_counter_from_table(self, tbl, prime_cntr):
        for k in list(tbl.keys()):
            if k.find(prime_cntr) > -1:
                return k
        return None

    def call_do_post_test(self):
        """
        create a dict of hte data to check
        :return:
        """
        time.sleep(0.5)
        dct = {}
        data_dnames_dct = self.executingScan.get_datafile_names_dict()
        scan_pluggin = self.scan_tbox_widgets[self.scan_panel_idx]
        res = scan_pluggin.do_post_test(data_dnames_dct)

        if res:
            _logger.info("Test succeeded")
        else:
            _logger.info("Test Failed")

    def init_point_spectra(self, sp_ids, det_lst):
        """
        init_point_spectra(): description

        :param sp_id=-1: sp_id=-1 description
        :type sp_id=-1: sp_id=-1 type

        :returns: None
        """

        self.spectraWidget.clear_plot()
        det_curve_nms = self.spectraWidget.create_curves(det_lst, sp_ids)


    def is_add_line_to_plot_type(self, scan_type, scan_sub_type, use_hdw_accel):
        """
        a single function to decide if the scan type is the kind that adds a line to a plot
        :param scan_type:
        :param scan_sub_type:
        :param use_hdw_accel:
        :return:
        """

        if (
                (scan_type == scan_types.SAMPLE_IMAGE)
                and (scan_sub_type == scan_sub_types.LINE_UNIDIR)
                or (
                (scan_type == scan_types.SAMPLE_IMAGE)
                and (scan_sub_type == scan_sub_types.POINT_BY_POINT)
                and use_hdw_accel
        )
                or (scan_type == scan_types.SAMPLE_IMAGE_STACK)
                and (scan_sub_type == scan_sub_types.LINE_UNIDIR)
                or (scan_type == scan_types.TOMOGRAPHY)
                and (scan_sub_type == scan_sub_types.LINE_UNIDIR)
                or (scan_type == scan_types.SAMPLE_IMAGE_STACK)
                and (scan_sub_type == scan_sub_types.POINT_BY_POINT)
                or (scan_type == scan_types.SAMPLE_LINE_SPECTRUM)
                and (scan_sub_type == scan_sub_types.LINE_UNIDIR)
                or (
                (scan_type == scan_types.SAMPLE_LINE_SPECTRUM)
                and (scan_sub_type == scan_sub_types.POINT_BY_POINT)
        )
                or (scan_type == scan_types.SAMPLE_FOCUS)
                and (scan_sub_type == scan_sub_types.LINE_UNIDIR)
        ):
            return True
        elif scan_type == scan_types.COARSE_IMAGE:
            return True
        else:
            return False

    def is_add_point_to_plot_type(self, scan_type, scan_sub_type, use_hdw_accel):
        """
        a single function to decide if the scan type is the kind that adds a point to a 2d plot
        :param scan_type:
        :param scan_sub_type:
        :param use_hdw_accel:
        :return:
        """
        if ((scan_type == scan_types.DETECTOR_IMAGE)
                or (
                (scan_type == scan_types.SAMPLE_IMAGE)
                and (scan_sub_type == scan_sub_types.POINT_BY_POINT)
                and (not use_hdw_accel)
        )
                or (scan_type == scan_types.OSA_IMAGE)
                or (scan_type == scan_types.TWO_VARIABLE_IMAGE)
                or (scan_type == scan_types.OSA_FOCUS)
                or  # ((scan_type == scan_types.SAMPLE_LINE_SPECTRUM) and (
                #            scan_sub_type == scan_sub_types.POINT_BY_POINT)) or \
                (scan_type == scan_types.SAMPLE_FOCUS)
                or (scan_type == scan_types.COARSE_IMAGE)
                or (scan_type == scan_types.COARSE_GONI)
                or (scan_type == scan_types.PATTERN_GEN)
        ):
            return True
        else:
            return False

    def is_add_point_to_spectra_type(self, scan_type, scan_sub_type, use_hdw_accel):
        """
        a single function to decide if the scan type is the kind that adds a point to a line  plot
        :param scan_type:
        :param scan_sub_type:
        :param use_hdw_accel:
        :return:
        """
        if (scan_type == scan_types.SAMPLE_POINT_SPECTRUM) or (
                scan_type == scan_types.GENERIC_SCAN
        ):
            return True
        else:
            return False

    def connect_executingScan_signals(self, testing=False):
        """
        connect_executingScan_signals(): description

        :returns: None
        """
        scan_type = self.get_cur_scan_type()
        scan_sub_type = self.get_cur_scan_sub_type()
        sp_db = self.executingScan.sp_db
        use_hdw_accel = dct_get(sp_db, SPDB_HDW_ACCEL_USE)

        _logger.debug("GUI: connect_executingScan_signals")
        if self.is_add_line_to_plot_type(scan_type, scan_sub_type, use_hdw_accel):
            reconnect_signal(self.executingScan.sigs, self.executingScan.sigs.changed, self.add_line_to_plot)
            # reconnect_signal(self.line_det.sigs, self.line_det.sigs.changed, self.add_line_to_plot)

            if not (scan_type == scan_types.SAMPLE_LINE_SPECTRUM):
                # dont connect this for line_spec scans because the data level is energy which would cause a
                # new image for each energy line which is not what we want
                if not use_hdw_accel:
                    reconnect_signal(
                        self.executingScan,
                        self.executingScan.data_start,
                        self.on_image_start,
                    )
                # just skip this signal if using hdw_accel because the on_image_start() will be called when the plotter updates

        elif self.is_add_point_to_plot_type(scan_type, scan_sub_type, use_hdw_accel):
            reconnect_signal(
                self.executingScan.sigs,
                self.executingScan.sigs.changed,
                self.add_point_to_plot,
            )

            if not (scan_type == scan_types.SAMPLE_LINE_SPECTRUM):
                # dont connect this for line_spec scans because the data level is energy which would cause a
                # new image for each energy line which is not what we want
                reconnect_signal(
                    self.executingScan,
                    self.executingScan.data_start,
                    self.on_image_start,
                )

        elif self.is_add_point_to_spectra_type(scan_type, scan_sub_type, use_hdw_accel):
            reconnect_signal(
                self.executingScan.sigs,
                self.executingScan.sigs.changed,
                self.add_point_to_spectra,
            )
        else:
            _logger.error(
                "connect_executingScan_signals: executingScan type [%d] not supported",
                scan_type,
            )

        reconnect_signal(
            self.scan_progress_table,
            self.scan_progress_table.total_prog,
            self.on_total_scan_progress,
        )
        reconnect_signal(
            self.executingScan,
            self.executingScan.low_level_progress,
            self.on_scan_progress,
        )
        reconnect_signal(
            self.executingScan,
            self.executingScan.sigs_disconnected,
            self.on_executing_scan_sigs_discon,
        )
        reconnect_signal(
            self.executingScan.sigs, self.executingScan.sigs.aborted, self.on_scan_done
        )
        reconnect_signal(
            self.executingScan, self.executingScan.all_done, self.on_scan_done
        )

        if testing:
            _logger.debug(
                "connecting self.call_do_post_test to self.executingScan.all_done"
            )
            reconnect_signal(
                self.executingScan, self.executingScan.all_done, self.call_do_post_test
            )

        reconnect_signal(
            self.executingScan, self.executingScan.saving_data, self.on_saving_data
        )

        # _logger.debug('executingScan signals connected')

    def disconnect_executingScan_signals(self):
        """
        disconnect_executingScan_signals(): description

        :returns: None
        """
        scan_type = self.get_cur_scan_type()
        scan_sub_type = self.get_cur_scan_sub_type()
        sp_db = self.executingScan.sp_db
        use_hdw_accel = dct_get(sp_db, SPDB_HDW_ACCEL_USE)
        _logger.debug("disconnect_executingScan_signals: TOP")
        if self.is_add_line_to_plot_type(scan_type, scan_sub_type, use_hdw_accel):
            disconnect_signal(self.executingScan.sigs, self.executingScan.sigs.changed)

            if not (scan_type == scan_types.SAMPLE_LINE_SPECTRUM):
                if not use_hdw_accel:
                    disconnect_signal(self.executingScan, self.executingScan.data_start)

        elif self.is_add_point_to_plot_type(scan_type, scan_sub_type, use_hdw_accel):
            disconnect_signal(self.executingScan.sigs, self.executingScan.sigs.changed)

            if not (scan_type == scan_types.SAMPLE_LINE_SPECTRUM):
                disconnect_signal(self.executingScan, self.executingScan.data_start)

        elif self.is_add_point_to_spectra_type(scan_type, scan_sub_type, use_hdw_accel):
            disconnect_signal(self.executingScan.sigs, self.executingScan.sigs.changed)

        else:
            _logger.error(
                "disconnect_executingScan_signals: executingScan type [%d] not supported",
                scan_type,
            )

        disconnect_signal(self.executingScan.sigs, self.executingScan.sigs.progress)
        disconnect_signal(self.executingScan, self.executingScan.top_level_progress)
        disconnect_signal(self.executingScan, self.executingScan.low_level_progress)
        disconnect_signal(self.executingScan, self.executingScan.sigs_disconnected)
        disconnect_signal(self.executingScan.sigs, self.executingScan.sigs.aborted)
        disconnect_signal(self.executingScan, self.executingScan.all_done)
        disconnect_signal(self.executingScan, self.executingScan.saving_data)
        disconnect_signal(self.executingScan, self.executingScan.all_done)

        self._set_scan_btns.emit("SET_FOR_STARTING")

    def on_saving_data(self, msg):
        self.scanActionLbl.setText(msg)
        # _logger.info('%s' % msg)

    def on_image_start(self, wdg_com=None, sp_id=None, det_id=0):
        """
        on_image_start(): called when a new image  starts

        :param wdg_com=None: wdg_com=None description
        :type wdg_com=None: wdg_com=None type

        :returns: None
        """
        # on_image_start can be called by singal passed from scan with the wdg_com as the arg
        # print 'on_image_start called'
        # _logger.debug('on_image_start called')
        # set these as defaults

        # self.reset_image_plot()
        self.lineByLineImageDataWidget.set_lock_aspect_ratio(True)
        self.lineByLineImageDataWidget.set_fill_plot_window(False)
        # default img_idx is 0
        img_idx = det_id
        if wdg_com is None:
            # use current
            wdg_com = self.cur_wdg_com

        if sp_id is None:
            # print 'on_image_start: sp_id is NONE'
            sp_id = self.executingScan.get_spatial_id()

        # print 'on_image_start: using sp_id=%d' % sp_id

        if sp_id not in list(wdg_com[WDGCOM_SPATIAL_ROIS].keys()):
            _logger.error(
                "Spatial ID [%d] does not exist in widget communication dict, using wdg_com from executingScan"
                % sp_id
            )
            wdg_com = self.executingScan.wdg_com
            if wdg_com is not None:
                sp_id = self.executingScan.get_spatial_id()

        sp_db = wdg_com[WDGCOM_SPATIAL_ROIS][sp_id]
        scan_type = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)

        if self.executingScan.image_started == False:
            if scan_type == scan_types.SAMPLE_FOCUS:
                self.lineByLineImageDataWidget.set_autoscale(fill_plot_window=True)

            elif scan_type == scan_types.OSA_FOCUS:
                self.lineByLineImageDataWidget.set_autoscale(fill_plot_window=True)

            elif scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
                self.lineByLineImageDataWidget.set_autoscale(fill_plot_window=True)
                self.lineByLineImageDataWidget.set_fill_plot_window(True)

            else:
                self.lineByLineImageDataWidget.set_autoscale(fill_plot_window=False)

            self.executingScan.image_started = True

    def on_spectra_start(self):
        """
        on_spectra_start(): description

        :returns: None
        """
        _logger.debug("on_spectra_start")
        self.spectraWidget.clear_plot()

    def on_scan_done(self):
        """
        on_scan_done(): description

        :returns: None
        """
        # idx = self.executingScan.get_imgidx()
        _logger.debug("GUI: scan completed")

        self.set_buttons_for_starting()

    def on_executing_scan_sigs_discon(self):
        """
        on_executing_scan_sigs_discon(): description

        :returns: None
        """
        _logger.debug("GUI: on_executing_scan_sigs_discon")
        if MAIN_OBJ.device("DNM_SHUTTER").is_auto():
            MAIN_OBJ.device("DNM_SHUTTER").close()
        # _logger.info('scan completed')
        # self.curImgProgBar.setValue(0.0)
        self.totalProgBar.setValue(0.0)
        if hasattr(self, "lineByLineImageDataWidget"):
            self.lineByLineImageDataWidget.set_lock_aspect_ratio(True)

        if self.executingScan is not None:
            self.disconnect_executingScan_signals()

    def on_elapsed_timer_to(self):
        """
        the scan eleapsed timer callback to calc new elapsed time and set teh elapsed time label
        """
        self.scan_elapsed_timer.start(1000)
        self.elapsed_time = time.time() - self.start_time
        self.elapsedTimeLbl.setText(secondsToStr(self.elapsed_time))

    def on_new_est_scan_time(self, time_sec):
        """
        a signal handler that accepts total seconds estimated by the scan plugin
        the QLabel self.estimatedTimeLbl is only the time, there is another label on the UI that contains "Estimated Time:"
        """
        #est_time_str = secondsToStr(time_sec)
        _mins = float(time_sec / 60.0)
        if _mins < 1.0:
            est_time_str = "Less than a minute"
        else:
            est_time_str = f"{_mins:.1f} minutes"
        self.estimatedTimeLbl.setText(f"{est_time_str}")
        #print(f"on_new_est_scan_time: label updated with: {est_time_str} \n\n")

    def set_cur_scan_type(self, type):
        self._scan_type = type

    def set_cur_scan_sub_type(self, type):
        self._scan_sub_type = type

    def get_cur_scan_type(self):
        return self._scan_type

    def get_cur_scan_sub_type(self):
        return self._scan_sub_type

    def on_scan_progress(self, prog_dct):
        """
        on_scan_progress(): a signal handler that fires when the progress pv's have been updated, here clip the top of the scan
        percentage at >= 90.0, if >= 90.0 just set it to %100

        :param percent: percent description
        :type percent: percent type

        :returns: None
        """
        if self.scan_progress_table.get_row_count() == 0:
            return

        sp_id = int(dct_get(prog_dct, PROG_DCT_SPID))
        percent = dct_get(prog_dct, PROG_DCT_PERCENT)
        cur_img_idx = int(dct_get(prog_dct, PROG_CUR_IMG_IDX))
        prog_state = dct_get(prog_dct, PROG_DCT_STATE)
        # print(f"on_scan_progress: {percent} => {prog_dct}")

        if self.get_cur_scan_type() is not scan_types.SAMPLE_IMAGE_STACK:
            # set_pixmap = self.scan_progress_table.set_pixmap_by_spid
            # set_progress = self.scan_progress_table.set_progress_by_spid
            set_pixmap = self.scan_progress_table.set_pixmap
            set_progress = self.scan_progress_table.set_progress
            id = sp_id
        else:
            # its a stack
            set_pixmap = self.scan_progress_table.set_pixmap
            set_progress = self.scan_progress_table.set_progress
            id = sp_id

        if percent >= 95.0:
            percent = 100.0
        elif percent < 1.0:
            #ignore less than 1.0 progress
            return

        set_progress(cur_img_idx, percent)

        if percent >= 100.0:
            set_pixmap(cur_img_idx, scan_status_types.DONE)
        elif percent < 100.0:
            # set_pixmap(id, scan_status_types.RUNNING)
            set_pixmap(cur_img_idx, scan_status_types.RUNNING)
        else:
            # set_pixmap(id, scan_status_types.STOPPED)
            set_pixmap(cur_img_idx, scan_status_types.STOPPED)

    def on_total_scan_progress(self, percent):
        """
        on_total_scan_progress(): description

        :param percent: percent description
        :type percent: percent type

        :returns: None
        """

        self.totalProgBar.setValue(int(percent))

    def on_pause(self, chkd):
        """
        on_pause(): description

        :param chkd: chkd description
        :type chkd: chkd type

        :returns: None
        """

        if self.executingScan:
            # idx = self.executingScan.get_imgidx()
            idx = self.executingScan.get_consecutive_scan_idx()
            if chkd:
                # self.executingScan.pause()
                if hasattr(self, "scan_progress_table"):
                    self.scan_progress_table.set_pixmap(idx, scan_status_types.PAUSED)
                # request a pause
                if MAIN_OBJ.get_device_backend().find("zmq") > -1:
                    MAIN_OBJ.engine_widget.engine.pause_scan()
                else:
                    MAIN_OBJ.engine_widget.control.state_widgets["pause"].clicked.emit()
            else:
                # self.executingScan.resume()
                # request a pause
                if hasattr(self, "scan_progress_table"):
                    self.scan_progress_table.set_pixmap(idx, scan_status_types.RUNNING)
                    
                if MAIN_OBJ.get_device_backend().find("zmq") > -1:
                    MAIN_OBJ.engine_widget.engine.resume_scan()
                else:
                    MAIN_OBJ.engine_widget.control.state_widgets["resume"].clicked.emit()

    def on_stop(self):
        """
        on_stop(): description

        :returns: None

        """

        self.scan_elapsed_timer.stop()
        self.on_shutterCntrlComboBox(0)  # Auto
        self.set_buttons_for_starting()
        if self.executingScan:
            self.executingScan.set_scan_as_aborted(True)
            # idx = self.executingScan.get_imgidx()
            idx = self.executingScan.get_consecutive_scan_idx()
            self.executingScan.stop()
            if hasattr(self, "scan_progress_table"):
                self.scan_progress_table.set_pixmap(idx, scan_status_types.ABORTED)
            self.stopping = True
            # self.executingScan.disconnect_signals()

            # stop
            if MAIN_OBJ.get_device_backend().find("zmq") > -1:
                MAIN_OBJ.engine_widget.engine.abort_scan()
            else:
                MAIN_OBJ.engine_widget.control.on_stop_clicked()
            # MAIN_OBJ.engine_widget.control.ask_for_a_stop()

        # #ensure that all detectors have been unstaged in case scan aws aborted
        for d in self.cur_dets:
            d.unstage()

    def on_emergency_stop(self):
        """
        for when the emergency button is pressed on the main screen
        Returns
        -------

        """

        if MAIN_OBJ.get_device_backend().find("zmq") > -1:
            MAIN_OBJ.engine_widget.engine.abort_scan()
            # if dev exists send all motors off to DCS server
            all_mtr_off_dev = MAIN_OBJ.device("DNM_ALL_MOTORS_OFF")
            if all_mtr_off_dev:
                all_mtr_off_dev.put(1)
        else:
            MAIN_OBJ.engine_widget.control.on_stop_clicked()
            # stop configured motors
            self.esPosPanel.stop_all_motors(hard=True)
            self.blPosPanel.stop_all_motors(hard=True)

        bright = master_colors["btn_danger_bright"]["rgb_str"]
        dark = master_colors["btn_danger_dark"]["rgb_str"]

        self.emergStopAllBtn.setStyleSheet(f"border: 4px solid {bright}; color: {bright}; background-color: {dark}")

        # abort any current running scans
        self.on_stop()

        msg = "Endstation motors forced to 'Stop' state.\n\nContact beamline staff to resume."
        dialog_notify("Emergency Stop", msg, "Okay")

        self.emergStopAllBtn.setStyleSheet(f"border: 4px solid {dark}; color: {bright}")

    def on_resume_from_emergency_stop(self):
        msg = (
            "Warning: Any 'stopped' motors will be resumed (e.g. after an emergency stop).\n\n"
            "Contact beamline staff to confirm limits and velocities."
        )
        if dialog_warn("Motor Warning", msg, "Continue", "Cancel") == "Continue":
            if MAIN_OBJ.get_device_backend().find("zmq") > -1:
                print('on_resume_from_emergency_stop: BACKEND == zmq, resume from all motor stop is not implemented')
            else:
                self.esPosPanel.resume_hardstopped_motors()
                self.blPosPanel.resume_hardstopped_motors()

    def on_exit(self):
        """
        on_exit(): description

        :returns: None
        """
        # print 'on_exit: called'
        _logger.debug("Main GUI: on_exit")
        MAIN_OBJ.cleanup()


def go():
    """
    go(): description

    :param go(: go( description
    :type go(: go( type

    :returns: None
    """
    app = QtWidgets.QApplication(sys.argv)

    # RUSS FEB25 from cls.appWidgets.splashScreen import get_splash, del_splash

    def clean_up():
        MAIN_OBJ.cleanup()

    # ca.threads_init()
    # from cls.appWidgets.splashScreen import SplashScreen

    debugger = sys.gettrace()

    # RUSS FEB25 splash = get_splash()
    sys.excepthook = excepthook
    if debugger is None:
        pystxm_win = pySTXMWindow(exec_in_debugger=False)
    else:
        pystxm_win = pySTXMWindow(exec_in_debugger=True)

    # didit = splash.close()
    # del_splash()

    app.aboutToQuit.connect(clean_up)
    pystxm_win.show()

    try:
        # starts event loop
        try:
            sys.exit(app.exec_())
        except:
            print("Exiting")
            exit()
    except:
        print("Exiting")


# app.exec_()


# if __name__ == '__main__':
#     import profile
#     import pstats
#
#     ca.threads_init()
#     #motorCfgObj = StxmMotorConfig(r'C:\controls\py2.7\Beamlines\sm\stxm_control\StxmDir\Microscope Configuration\Motor.cfg')
#     app = QtWidgets.QApplication(sys.argv)
#
#     #log_to_qt()
#     absMtr = pySTXMWindow()
#     absMtr.show()
#     sys.exit(app.exec_())


def determine_profile_bias_val():
    """
    determine_profile_bias_val(): description

    :param determine_profile_bias_val(: determine_profile_bias_val( description
    :type determine_profile_bias_val(: determine_profile_bias_val( type

    :returns: None
    """
    pr = profile.Profile()
    v = 0
    v_t = 0
    for i in range(5):
        v_t = pr.calibrate(100000)
        v += v_t
        print(v_t)

    bval = v / 5.0
    print("bias val = ", bval)
    profile.Profile.bias = bval
    return bval


def profile_it():
    """
    profile_it(): description

    :param profile_it(: profile_it( description
    :type profile_it(: profile_it( type

    :returns: None
    """

    bval = determine_profile_bias_val()

    profile.Profile.bias = 1.36987840635e-05

    profile.run("go()", "testprof.dat")

    p = pstats.Stats("testprof.dat")
    p.sort_stats("cumulative").print_stats(100)


if __name__ == "__main__":
    import profile
    import pstats

    # motorCfgObj = StxmMotorConfig(r'C:\controls\py2.7\Beamlines\sm\stxm_control\StxmDir\Microscope Configuration\Motor.cfg')
    # app = QtWidgets.QApplication(sys.argv)
    go()
    # profile_it()

    # test()
    # app = QtWidgets.QApplication(sys.argv)

    # pystxm_win = pySTXMWindow()
    # sys.excepthook = excepthook
    # pystxm_win.show()

    # try:
    # sys.exit(app.exec_())
    # except:
    #    sys.excepthook(*sys.exc_info())
