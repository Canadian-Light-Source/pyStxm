"""
Created on May 11, 2016

@author: bergr
"""

import os
import time

import numpy as np
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from plotpy.plot.plotwidget import PlotOptions
from plotpy.builder import make

from cls.appWidgets.thread_worker import Worker
from cls.applications.pyStxm import abs_path_to_ini_file
from cls.plotWidgets.imageWidget import ImageWidgetPlot
from cls.utils.log import get_module_logger, log_to_qt
from cls.utils.cfgparser import ConfigClass

from cls.scanning.paramLineEdit import dblLineEditParamObj
from cls.appWidgets.dialogs import excepthook
from cls.utils.enum_utils import Enum

camruler_mode = Enum("LOCAL", "SERVER", "CLIENT")

# read the ini file and load the default directories
appConfig = ConfigClass(abs_path_to_ini_file)
widgetsUiDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
# IMAGE_WIDTH = appConfig.get_value("CAMERA", "frame_wd")
# IMAGE_HT = appConfig.get_value("CAMERA", "frame_ht")
# SCALER_AT_FULL_LENS_ZOOM_OUT = float(appConfig.get_value("CAMERA", "scaling_factor"))
from epics import PV
PREC = 3

_logger = get_module_logger(__name__)

def make_uhvstxm_distance_verification_window():

    win = ImageWidgetPlot(
        parent=None,
        filtStr="*.hdf5",
        type="calib_camera",
        options=PlotOptions(
            lock_aspect_ratio=True,
            show_contrast=True,
            show_xsection=False,
            show_ysection=False,
            show_itemlist=False,
            )
    )

    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    win.enable_tool_by_name('StxmOpenFileTool', False)
    win.addTool('StxmHorizMeasureTool')

    #remove un-needed tools from toolbar
    actions = win.plot.manager.toolbars['default'].actions()
    for act in actions:
        if act.text() in ['Open...', 'Clear Plot', 'Rectangle snapshot', 'Parameters...']:
            win.plot.manager.toolbars['default'].removeAction(act)
    return win


class CameraRuler(QtWidgets.QWidget):
    """
    This is a widget is used to grab an image from a 1394 firewire camera and use it as an absolute encoder to determine
    the positions of:
        Zoneplate Z
        OSA Z
        Sample Z
        Detector Z

    The widget makes the assumption that the pixel scaling has been set correctly such that the measuremenst made using the tools are
    physically accurate.


    """
    def __init__(
        self, mode=camruler_mode.LOCAL, main_obj=None, scaling_factor=1.0, parent=None
    ):
        global zpz, osaz, detz, camera_client
        super(CameraRuler, self).__init__(parent)
        uic.loadUi(os.path.join(widgetsUiDir, "camera_ruler.ui"), self)
        self.plot = make_uhvstxm_distance_verification_window()
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.plot)
        self.plotFrame.setLayout(vlayout)
        self.main_obj = main_obj
        self.threadpool = QtCore.QThreadPool()
        self.run_cont_grab = False
        self.scaler_at_full_lens_zoom_out = scaling_factor

        self.zpz = self.main_obj.device("DNM_ZONEPLATE_Z_BASE")
        self.zpz_c = self.main_obj.device("DNM_ZONEPLATE_Z")
        self.osaz = self.main_obj.device("DNM_OSA_Z_BASE")
        self.osaz_c = self.main_obj.device("DNM_OSA_Z")
        self.detz = self.main_obj.device("DNM_DETECTOR_Z")
        self.camera_client = self.main_obj.device("DNM_CALIB_CAMERA_CLIENT")

        self.load_cur_positions()

        # self.sampleZFld.dpo = dblLineEditParamObj('sampleZFld', -5000, 5000.0, PREC, parent=self.sampleZFld)
        # self.sampleZFld.dpo.valid_returnPressed.connect(self.set_center_and_scale)

        # self.sampleZFld.returnPressed.connect(self.set_center_and_scale)
        # self.sampleZBtn.clicked.connect(self.set_center_and_scale)

        self.zoneplateZFld.dpo = dblLineEditParamObj(
            "zoneplateZFld",
            self.zpz.get_low_limit(),
            self.zpz.get_high_limit(),
            PREC,
            parent=self.zoneplateZFld,
        )
        self.zoneplateZFld.returnPressed.connect(self.set_zoneplate)
        # self.zoneplateZFld.returnPressed.connect(self.set_zoneplate)
        # self.zoneplateZBtn.clicked.connect(self.set_zoneplate)

        self.osaZFld.dpo = dblLineEditParamObj(
            "osaZFld",
            self.osaz.get_low_limit(),
            self.osaz.get_high_limit(),
            PREC,
            parent=self.osaZFld,
        )
        self.osaZFld.returnPressed.connect(self.set_osa)
        # self.osaZFld.returnPressed.connect(self.set_osa)
        # self.osaZBtn.clicked.connect(self.set_osa)

        self.detZFld.dpo = dblLineEditParamObj(
            "detZFld",
            self.detz.get_low_limit(),
            self.detz.get_high_limit(),
            PREC,
            parent=self.detZFld,
        )
        self.detZFld.returnPressed.connect(self.set_detector)
        # self.detZFld.returnPressed.connect(self.set_detector)
        # self.detZBtn.clicked.connect(self.set_detector)
        #

        self.contGrabTimer = QtCore.QTimer()

        self.camera_dev = None
        self.calib_camera = None

        self.mode = mode
        self.init_image_item()

        print("Running CalibCamera in Client Mode")

        self.grabBtn.clicked.connect(self.on_remote_grab_btn)
        self.contGrabBtn.clicked.connect(self.on_remote_cont_grab_btn)

    def init_image_item(self):
        """
        on starup create and add an image item to the plot
        """
        width = self.main_obj.get_preset_as_int("frame_wd", "CAMERA")
        ht = self.main_obj.get_preset_as_int("frame_ht", "CAMERA")
        item = make.image(
            np.zeros((ht, width)), title="0", interpolation="nearest", colormap="gist_gray"
        )
        self.plot.plot.add_item(item, z=0)

    def on_remote_cont_grab_btn(self, chkd):
        """
        This is a signal handler that is responding to the grab button being pressed
        this handler serves for the local and server mode grabBtn clicked signal
        """
        if chkd:
            # start timer
            # self.remote_grab_and_display_image()
            # self.contGrabTimer.timeout.connect(self.remote_continuous_grab)
            # self.contGrabTimer.start(500)

            worker = Worker(
                self.remote_continuous_grab, changed_callback=self.display_continuous_grab
            )  # Any other args, kwargs are passed to the run function
            # worker.signals.result.connect(self.load_thumbs)
            # worker.signals.progress.connect(self.load_images_progress)
            worker.signals.finished.connect(self.continuous_grab_complete)
            worker.signals.changed.connect(self.display_continuous_grab)
            self.run_cont_grab = True
            # Execute
            self.threadpool.start(worker)

        else:
            self.run_cont_grab = False

    def continuous_grab_complete(self):
        print(f"continuous_grab_complete: Done")
    def remote_grab_and_display_image(self):
        data = self.camera_client.get_single_frame()
        if data is not None:
            # #self.plot.set_data(image)
            # image = make.image(data, interpolation="nearest")
            # self.plot.plot.add_item(image, z=0)
            # self.apply_scaling(image)
            # self.plot.plot.replot()
            img_idx = 0
            self.plot.set_data(img_idx, data)
            self.apply_scaling(data)

    def remote_continuous_grab(self, changed_callback=None):
        for i in range(500):
            if self.run_cont_grab:
                image = self.camera_client.get_single_frame()
                if changed_callback:
                    changed_callback.emit(image)
            else:
                i = 501
            # time.sleep(0.05)

    def display_continuous_grab(self, data):
        if data is not None:
            self.plot.set_data(0, data)
            # self.apply_scaling(image)


    def on_remote_grab_btn(self):
        # push the acquire pv so that the server will aquire a frame and write it to teh waveform pv
        data = self.camera_client.get_single_frame()
        if data is not None:

            # image = make.image(data, interpolation="nearest", colormap="gist_gray",)
            # plot = self.plot.get_plot()
            # plot.add_item(image, z=0)
            # self.apply_scaling(data)
            # plot.update()

            img_idx = 0
            self.plot.set_data(img_idx, data)
            self.apply_scaling(data)


    def apply_scaling(self, image, image_idx=0):
        ht, wd = image.shape
        scale = self.scaler_at_full_lens_zoom_out
        cx = 0.0
        xmin = cx - ((0.5 * wd) * scale)
        ymin = 0 - ((0.5 * ht) * scale)
        xmax = cx + ((0.5 * wd) * scale)
        ymax = 0 + ((0.5 * ht) * scale)

        self.plot.set_image_parameters(image_idx, xmin, ymin, xmax, ymax)
        self.plot.set_autoscale(False)

    def load_cur_positions(self):
        zpz = self.zpz.get_position()
        osaz = self.osaz.get_position()
        detz = self.detz.get_position()

        self.zoneplateZFld.setText("%.3f" % zpz)
        self.osaZFld.setText("%.3f" % osaz)
        self.detZFld.setText("%.3f" % detz)

    def set_center_and_scale(self):

        cx = float(str(self.sampleZFld.text()))
        # scale = float(str(self.scaleFld.text()))
        scale = 17.2
        self.plot.on_move_image_center(cx, scale)

    def set_zoneplate(self):
        pos = float(str(self.zoneplateZFld.text()))
        self.zpz.set_position(pos)
        if self.zpz_c:
            self.zpz_c.set_position(pos)

    def set_osa(self):
        pos = float(str(self.osaZFld.text()))
        self.osaz.set_position(pos)
        if self.osaz_c:
            self.osaz_c.set_position(pos)
        # set the soft limits of osaz
        # set the soft limits of zpz

    def set_detector(self):
        pos = float(str(self.detZFld.text()))
        self.detz.set_position(pos)
        # set the soft limits of detz


if __name__ == "__main__":
    import sys
    import os

    sys.excepthook = excepthook

    hostname = os.getenv("COMPUTERNAME")
    if hostname == "IOC1610-303":
        mode = camruler_mode.SERVER
    else:
        mode = camruler_mode.CLIENT

    app = QtWidgets.QApplication(sys.argv)
    # win = CameraRuler(mode=mode)
    # win.resize(900, 900)
    # win.show()

    win = make_uhvstxm_distance_verification_window()
    # item = make.image(
    #     np.zeros((480, 640)), title="0", interpolation="nearest", colormap="gist_gray"
    # )
    # win.plot.add_item(item, z=0)

    win.show()
    app.exec_()
