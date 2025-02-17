"""
Created on May 11, 2016

@author: bergr
"""

import os
from PyQt5 import QtCore, QtGui, uic, QtWidgets

from cls.applications.pyStxm import abs_path_to_ini_file
from cls.plotWidgets.imageWidget import ImageWidgetPlot

# from bcm.devices.device_names import *
# from cls.applications.pyStxm.stxm_utils.jsonrpc_fleacam_server import RequestHandler

from cls.utils.log import get_module_logger, log_to_qt
from cls.utils.cfgparser import ConfigClass

from cls.scanning.paramLineEdit import dblLineEditParamObj
from cls.appWidgets.dialogs import excepthook

# from cls.applications.pyStxm.bl10ID01 import MAIN_OBJ
from bcm.epics_devices_MOVED.motor_v2 import Motor_V2 as apsMotor
from bcm.epics_devices_MOVED.camera import camera

from cls.utils.enum_utils import Enum

camruler_mode = Enum("LOCAL", "SERVER", "CLIENT")

zpz = apsMotor("IOC:m111")
osaz = apsMotor("IOC:m106")
detz = apsMotor("IOC:m116")
camera_srvr = camera("BL1610-I10:uhv", server=True)
camera_client = camera("BL1610-I10:uhv", server=False)


# read the ini file and load the default directories
appConfig = ConfigClass(abs_path_to_ini_file)
# widgetsUiDir = appConfig.get_value('MAIN', 'widgetsUiDir')
widgetsUiDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
CAMERA_WAVEFORM_PV_STR = appConfig.get_value("CAMERA", "camera_waveform")
IMAGE_WIDTH = appConfig.get_value("CAMERA", "frame_wd")
IMAGE_HT = appConfig.get_value("CAMERA", "frame_ht")
SCALER_AT_FULL_LENS_ZOOM_OUT = float(appConfig.get_value("CAMERA", "scaling_factor"))
PREC = 3

_logger = get_module_logger(__name__)


def make_uhvstxm_distance_verification_window():
    # win = CameraViewerWidget(parent = None, filtStr = "*.hdf5", type=None, options=dict(show_contrast=False, show_xsection=False, show_ysection=False,show_itemlist=False))
    win = ImageWidgetPlot(
        parent=None,
        filtStr="*.hdf5",
        type="calib_camera",
        options=dict(
            show_contrast=False,
            show_xsection=False,
            show_ysection=False,
            show_itemlist=False,
        ),
    )
    win.set_enable_multi_region(False)
    win.enable_image_param_display(False)
    # win.enable_tool_by_name('StxmOpenFileTool', False)
    # win.addTool('StxmHorizMeasureTool')

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

    def __init__(self, mode=camruler_mode.LOCAL, parent=None):
        global zpz, osaz, detz, camera_srvr, camera_client
        super(CameraRuler, self).__init__(parent)
        uic.loadUi(os.path.join(widgetsUiDir, "camera_ruler.ui"), self)
        self.plot = make_uhvstxm_distance_verification_window()
        # hlayout = QtWidgets.QHBoxLayout()
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.addWidget(self.plot)
        self.plotFrame.setLayout(vlayout)

        # self.zpz = MAIN_OBJ.device( DNM_ZONEPLATE_Z_BASE)
        # self.osaz = MAIN_OBJ.device( DNM_OSA_Z_BASE)
        # self.detz = MAIN_OBJ.device( DNM_DETECTOR_Z)

        self.zpz = zpz
        self.osaz = osaz
        self.detz = detz

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

        if mode == camruler_mode.SERVER:
            from bcm.device.camera import FleaCamera

            print("Running CalibCamera in Server Mode")
            self.camera_dev = FleaCamera(cam_id="Grasshopper2")
            # self.calib_camera = MAIN_OBJ.device('DNM_CALIB_CAMERA_SRVR')
            self.calib_camera = camera_srvr
            self.calib_camera.acquire_frame.connect(self.on_aquire_frame)
            self.grabBtn.clicked.connect(self.on_local_grab_btn)
            self.contGrabBtn.clicked.connect(self.on_local_cont_grab_btn)

        elif mode == camruler_mode.CLIENT:
            print("Running CalibCamera in Client Mode")
            # self.calib_camera = MAIN_OBJ.device('DNM_CALIB_CAMERA_CLIENT')
            self.calib_camera = camera_client
            # self.calib_camera.changed.connect(self.on_image_updated)
            self.grabBtn.clicked.connect(self.on_remote_grab_btn)
            self.contGrabBtn.clicked.connect(self.on_remote_cont_grab_btn)
        else:
            from bcm.device.camera import FleaCamera

            print("Running CalibCamera in LOCAL Mode")
            self.camera_dev = FleaCamera(cam_id="Grasshopper2")
            # self.calib_camera = MAIN_OBJ.device('DNM_CALIB_CAMERA_CLIENT')
            self.calib_camera = camera_client
            self.grabBtn.clicked.connect(self.on_local_grab_btn)
            self.contGrabBtn.clicked.connect(self.on_local_cont_grab_btn)

    #    def on_image_updated(self, data):
    #        print data[0:10]

    def on_aquire_frame(self, toggle):
        """
        This is a signal handler that is responding to the grab_frame pv being set
        this handler serves for the remote mode grabBtn clicked signal
        """
        if toggle == 1:
            # only grab a frame on a transition to 1 not back to 0
            image = self.camera_dev.grab_frame(as_1d_array=True)
            self.calib_camera.set_image_data(image)

    def on_local_grab_btn(self):
        """
        This is a signal handler that is responding to the grab button being pressed
        this handler serves for the local and server mode grabBtn clicked signal
        """
        image = self.camera_dev.grab_frame()
        self.plot.set_data(image)
        self.apply_scaling(image)

    def on_local_cont_grab_btn(self, chkd):
        """
        This is a signal handler that is responding to the grab button being pressed
        this handler serves for the local and server mode grabBtn clicked signal
        """
        if chkd:
            # start timer
            self.contGrabTimer.timeout.connect(self.local_grab_and_display_image)
            self.contGrabTimer.start(500)
        else:
            self.contGrabTimer.stop()

    def on_remote_cont_grab_btn(self, chkd):
        """
        This is a signal handler that is responding to the grab button being pressed
        this handler serves for the local and server mode grabBtn clicked signal
        """
        if chkd:
            # start timer
            self.remote_grab_and_display_image()
            self.contGrabTimer.timeout.connect(self.remote_continuous_grab)
            self.contGrabTimer.start(500)
        else:
            self.contGrabTimer.stop()

    def local_grab_and_display_image(self):
        image = self.camera_dev.grab_frame()
        if image is not None:
            self.plot.set_data(image)
            self.apply_scaling(image)
            self.plot.plot.replot()

    def remote_grab_and_display_image(self):
        self.calib_camera.grab_frame()
        image = self.calib_camera.get_image_data()
        if image is not None:
            self.plot.set_data(image)
            self.apply_scaling(image)
            self.plot.plot.replot()

    def remote_continuous_grab(self):
        self.calib_camera.grab_frame()
        image = self.calib_camera.get_image_data()
        if image is not None:
            self.plot.set_data(image)
            self.plot.plot.replot()

    def on_remote_grab_btn(self):
        # push the acquire pv so that the server will aquire a frame and write it to teh waveform pv
        self.calib_camera.grab_frame()
        image = self.calib_camera.get_image_data()
        if image is not None:
            self.plot.set_data(image)
            self.apply_scaling(image)
            self.plot.plot.replot()

    def apply_scaling(self, image):
        # ht, wd, clrs = image.shape
        ht, wd = image.shape
        # scale = float(1000.0/float(wd))
        scale = SCALER_AT_FULL_LENS_ZOOM_OUT
        # if scale != 1.0:
        #    image = cv2.resize(image, (0, 0), fx=scale, fy=scale)
        # get user especified center and scale

        # cx = float(str(self.centerXFld.text()))
        # scale = float(str(self.scaleFld.text()))
        cx = 0.0

        x1 = cx - ((0.5 * wd) * scale)
        y1 = 0 - ((0.5 * ht) * scale)
        x2 = cx + ((0.5 * wd) * scale)
        y2 = 0 + ((0.5 * ht) * scale)

        self.plot.set_image_parameters(self.plot.item, x1, y1, x2, y2)

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

    def set_osa(self):
        pos = float(str(self.osaZFld.text()))
        self.osaz.set_position(pos)
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
    win = CameraRuler(mode=mode)
    win.resize(900, 900)
    win.show()

    app.exec_()
