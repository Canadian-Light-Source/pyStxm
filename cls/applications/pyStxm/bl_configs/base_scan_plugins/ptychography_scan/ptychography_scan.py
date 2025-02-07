"""
Created on Aug 25, 2014

@author: bergr
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtGui import QPixmap, QImage
import numpy as np
import tifffile

import os
import time

from cls.stylesheets import master_colors
from cls.scanning.paramLineEdit import dblLineEditParamObj
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.scanning.base import MultiRegionScanParamBase, zp_focus_modes
from cls.appWidgets.dialogs import getSaveFileName
from cls.stylesheets import get_style
from cls.data_io.stxm_data_io import STXMDataIo
from cls.applications.pyStxm.widgets.scan_table_view.multiRegionWidget import (
    MultiRegionWidget,
)
from cls.plotWidgets.imageWidget import make_ptycho_camera_widow
from cls.types.stxmTypes import (
    scan_types,
    scan_sub_types,
    spatial_type_prefix,
    image_types,
    sample_positioning_modes,
    sample_fine_positioning_modes,
)
from cls.utils.images import array_to_tiff_file
from cls.utils.roi_utils import (
    make_spatial_db_dict,
    widget_com_cmnd_types,
    get_unique_roi_id,
    on_range_changed,
    on_npoints_changed,
    on_step_size_changed,
    on_start_changed,
    on_stop_changed,
    on_center_changed,
    recalc_setpoints,
    get_base_start_stop_roi,
    get_base_roi,
    get_first_sp_db_from_wdg_com,
)
from cls.utils.images import get_image_details_dict

from cls.plotWidgets.shape_restrictions import ROILimitObj, ROILimitDef
from cls.plotWidgets.color_def import (
    get_normal_clr,
    get_warn_clr,
    get_alarm_clr,
    get_normal_fill_pattern,
    get_warn_fill_pattern,
    get_alarm_fill_pattern,
)

from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger
from plotpy.builder import make

MAX_SCAN_RANGE_FINEX = MAIN_OBJ.get_preset_as_float("max_fine_x")
MAX_SCAN_RANGE_FINEY = MAIN_OBJ.get_preset_as_float("max_fine_y")
MAX_SCAN_RANGE_X = MAIN_OBJ.get_preset_as_float("max_coarse_x")
MAX_SCAN_RANGE_Y = MAIN_OBJ.get_preset_as_float("max_coarse_y")
USE_E712_HDW_ACCEL = MAIN_OBJ.get_preset_as_bool("USE_E712_HDW_ACCEL", "BL_CFG_MAIN")
PTYCHOGRAPHY_ENABLED = MAIN_OBJ.get_preset_as_bool(
    "PTYCHOGRAPHY_ENABLED", "BL_CFG_MAIN"
)
MIN_PTYCHO_DWELL_MS = MAIN_OBJ.get_preset_as_float(
    "min_ptycho_dwell_ms", "BL_CFG_MAIN"
)
PTYCHO_CAMERA = MAIN_OBJ.get_preset("default_cam", "PTYCHO_CAMERA")

DEFAULT_PTYCHO_IMG_NM = "ptych_align_cam"


_logger = get_module_logger(__name__)


def numpy_array_to_qpixmap(numpy_array, panel_size=512):
    # Scale the values to uint8
    scaled_array = ((numpy_array - np.min(numpy_array)) / (np.max(numpy_array) - np.min(numpy_array))) * 255
    scaled_array = scaled_array.astype(np.uint8)

    # Convert the numpy array to a QImage
    height, width = scaled_array.shape
    bytes_per_line = width
    qimage =QtGui.QImage(scaled_array.data, width, height, bytes_per_line, QtGui.QImage.Format_Grayscale8)
    #QImage.Format_RGB888 or QImage.Format_Indexed8

    # Convert the QImage to a QPixmap
    qpixmap = QtGui.QPixmap.fromImage(qimage)
    qpixmap = qpixmap.scaled(
            QtCore.QSize(QtCore.QSize(panel_size, panel_size)),
            QtCore.Qt.IgnoreAspectRatio,
        )

    return qpixmap

def uint16_array_to_scaled_uint8(numpy_array):
    # Scale the values to uint8
    scaled_array = ((numpy_array - np.min(numpy_array)) / (np.max(numpy_array) - np.min(numpy_array))) * 255
    scaled_array = scaled_array.astype(np.uint8)
    return scaled_array

class BasePtychographyScanParam(MultiRegionScanParamBase):
    img_changed = QtCore.pyqtSignal()
    def __init__(
        self, parent=None, main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__)
    ):
        super().__init__(main_obj=main_obj, data_io=data_io, dflts=dflts)
        self._parent = parent

        ptycho_cam = MAIN_OBJ.device(PTYCHO_CAMERA)

        if not PTYCHOGRAPHY_ENABLED:
            self.name = "Ptychography Scan ---- [DISABLED in app.ini] "
            self.setEnabled(False)
            self.setToolTip(
                "PtychographyScanParam: Scan plugin is disabled beamline config ini file"
            )
        elif ptycho_cam is None:
            self.name = "Ptychography Scan ---- [DISABLED] "
            self.setEnabled(False)
            self.setToolTip(
                "PtychographyScanParam: Scan plugin is disabled because the camera for ptychography does not exist in the configuration database"
            )
        else:

            uic.loadUi(
                os.path.join(ui_path, "ptychography_scan.ui"), self
            )

            x_cntr = self.main_obj.get_sample_fine_positioner("X").get_position()
            y_cntr = self.main_obj.get_sample_fine_positioner("Y").get_position()

            self._multi_region_widget = MultiRegionWidget(
                enable_multi_spatial=False,
                single_ev_model=True,
                single_pol_model=True,
                max_range=MAX_SCAN_RANGE_FINEX,
                min_sp_rois=1,
                x_cntr=x_cntr,
                y_cntr=y_cntr,
                main_obj=self.main_obj,
                sp_scan=self.get_initial_default_scan(x_cntr, y_cntr),
                min_dwell_ms=MIN_PTYCHO_DWELL_MS,
                single_dwell=True
            )

            if not self.main_obj.is_device_supported("DNM_EPU_POLARIZATION"):

                self.multi_region_widget.deslect_all_polarizations()
                self.multi_region_widget.disable_polarization_table(True)
                self.multi_region_widget.set_polarization_table_visible(False)
            else:
                self.epu_supported = True
                self.multi_region_widget.deslect_all_polarizations()
                self.multi_region_widget.disable_polarization_table(False)
                self.multi_region_widget.set_polarization_table_visible(True)

            self.multi_region_widget.spatial_row_selected.connect(
                self.on_spatial_row_selected
            )
            self.multi_region_widget.spatial_row_changed.connect(
                self.on_spatial_row_changed
            )
            self.multi_region_widget.spatial_row_deleted.connect(
                self.on_spatial_row_deleted
            )

            self.evGrpBox.layout().addWidget(self.multi_region_widget)
            self.loadScanBtn.clicked.connect(self.load_scan)

            self.scan_class = self.instanciate_scan_class(
                __file__, "PtychographyScan", "PtychographyScanClass"
            )
            self.hdwAccelDetailsBtn.setToolTip("E712 Wavgen details")
            self.hdwAccelDetailsBtn.clicked.connect(self.show_hdw_accel_details)
            self.on_ev_pol_sel(0)
            self.evpol_flg_comboBox.currentIndexChanged.connect(self.on_ev_pol_sel)
            self.acquireBtn.clicked.connect(self.on_acquire_btn)
            self.saveImgAsBtn.clicked.connect(self.on_save_img_as_btn)

            self.shutter = MAIN_OBJ.device("DNM_SHUTTER")
            self.camera = MAIN_OBJ.device(PTYCHO_CAMERA)
            self.camera.cam.detector_state.subscribe(self.on_new_image, event_type="value")
            self.img_changed.connect(self.on_changed)

            fg_clr = master_colors["plot_forgrnd"]["rgb_str"]
            bg_clr = master_colors["plot_bckgrnd"]["rgb_str"]
            min_clr = master_colors["plot_gridmaj"]["rgb_str"]
            maj_clr = master_colors["plot_gridmin"]["rgb_str"]

            self.cam_plot = make_ptycho_camera_widow("ptychoCamPlot")
            cpnl = self.cam_plot.get_contrast_panel()
            qssheet = get_style()
            self.cam_plot.setStyleSheet(None)
            #self.cam_plot.set_grid_parameters(bg_clr, min_clr, maj_clr)
            #self.cam_plot.set_cs_grid_parameters(fg_clr, bg_clr, min_clr, maj_clr)
            #self.cam_plot.closeEvent = self.on_viewer_closeEvent
            self.cam_plot.init_image_items([DEFAULT_PTYCHO_IMG_NM], 0, 2048, 2048, parms={SPDB_RECT: (0,0,2048,2048)})
            vbox = QtWidgets.QVBoxLayout()
            vbox.addWidget(self.cam_plot)
            self.camFrame.setLayout(vbox)

            self.wdg_com = None
            self.sp_db = None
            self._cur_image_arr = None
            # self.osay_trcking_was = self.main_obj.device('DNM_OSAY_TRACKING).get_position()
            self.load_from_defaults()
            self.init_sp_db()
            # self.connect_paramfield_signals()
            self.on_plugin_focus()
            self.init_loadscan_menu()

    @property
    def multi_region_widget(self) -> MultiRegionWidget:
        return self._multi_region_widget

    def clear_stylesheet(self):
        if self.isEnabled():
            self.cam_plot.setStyleSheet(None)

    def init_plugin(self):
        """
        set the plugin specific details to common attributes
        :return:
        """
        self.name = "Ptychography Scan"
        self.idx = self.main_obj.get_scan_panel_order(__file__)
        self.type = scan_types.PTYCHOGRAPHY
        self.sub_type = scan_sub_types.POINT_BY_POINT
        self.data = {}
        self.section_id = "PTYCHOGRAPHY"
        self.axis_strings = ["Sample Y microns", "Sample X microns", "", ""]
        self.zp_focus_mode = zp_focus_modes.DO_NOTHING
        self.data_file_pfx = self.main_obj.get_datafile_prefix()
        self.plot_item_type = spatial_type_prefix.ROI

        self._type_interactive_plot = True  # [scan_panel_order.POSITIONER_SCAN]
        self._type_skip_scan_q_table_plots = (
            False  # [scan_panel_order.OSA_FOCUS_SCAN, scan_panel_order.FOCUS_SCAN]
        )
        self._type_spectra_plot_type = (
            False  # [scan_panel_order.POINT_SCAN, scan_panel_order.POSITIONER_SCAN]
        )
        self._type_skip_centering_scans = (
            False  # [scan_panel_order.FOCUS_SCAN, scan_panel_order.TOMOGRAPHY,
        )
        # scan_panel_order.LINE_SCAN, scan_panel_order.POINT_SCAN, scan_panel_order.IMAGE_SCAN]
        self._type_do_recenter = False  # [scan_panel_order.IMAGE_SCAN, scan_panel_order.TOMOGRAPHY, scan_panel_order.LINE_SCAN]

        # self._help_html_fpath = os.path.join('interface', 'window_system', 'scan_plugins', 'detector.html')
        self._help_ttip = "Ptychography documentation and instructions"

    def on_plugin_focus(self):
        """
        This is a function that is called when the plugin first receives focus from the main GUI
        :return:
        """
        if self.isEnabled():
            #self.on_acquire_btn()
            self.clear_stylesheet()
            # make sure that the OSA vertical tracking is off if it is on
            dev = self.main_obj.device("DNM_OSAY_TRACKING")
            if dev:
                self.osay_trcking_was = dev.get_position()
            # self.main_obj.device('DNM_OSAY_TRACKING).put(0) #off
            self.on_multiregion_widget_focus_init_base_values()
            self.multi_region_widget.resize_tableviews()

    def on_plugin_defocus(self):
        """
        This is a function that is called when the plugin leaves focus from the main GUI
        :return:
        """
        if self.isEnabled():
            # make sure that the OSA vertical tracking is off if it is on
            dev = self.main_obj.device("DNM_OSAY_TRACKING")
            if dev:
                self.osay_trcking_was = dev.put(self.osay_trcking_was)

        # call the base class defocus
        super().on_plugin_defocus()

    def on_new_image(self, **kwargs):
        """
        when the detector state changes adjust the background color of the image label
        and if the transition is from 2 -> 0 then call an update of the image by emitting the changed signal
        :param kwargs:
        :return:
        """
        if kwargs["old_value"] != 0 and kwargs["value"] == 0:
            self.img_changed.emit()
    def on_acquire_btn(self):
        # load a sample image into cam align viewer
        self.shutter.put(1)
        #setup the camera AD to write a file that we will load after acquire is done
        # disable camera file_plugins
        self.camera.hdf5_file_plugin.enable.put(0)
        self.camera.tif_file_plugin.enable.put(0)

        # set the dwell time
        dwell = float(self.dwellFld.text())
        self.camera.set_dwell(dwell)
        self.camera.cam.image_mode.put(0)  # single
        self.camera.cam.num_images.put(1)
        self.camera.cam.trigger_mode.put(0)  # free run
        self.camera.cam.array_counter.put(0)

        #acquire a frame
        self.camera.cam.acquire.put(1)
        #time.sleep((dwell + 100)*0.001)
        #self.camera.cam.acquire.put(0)

    def on_save_img_as_btn(self):
        datadir = self.main_obj.get_preset_section("BL_CFG_MAIN")['datadir']
        fname = getSaveFileName("Save Image as", '*.tif', filter_str="Tif  Files(*.tif)", search_path=datadir)
        if fname:
            array_to_tiff_file(fname, self._cur_image_arr)
            _logger.info(f"Saved image as: {fname}")


    def on_changed(self):
            self.shutter.put(0)
            #load the file and display
            arr = self.camera.image.image.view(np.uint16)
            arr.byteswap(True)
            self._cur_image_arr = np.copy(arr)
            image_size = self.camFrame.size().width()
            scaled_arr = uint16_array_to_scaled_uint8(arr)
            self.cam_plot.set_data(DEFAULT_PTYCHO_IMG_NM, scaled_arr)
            self.cam_plot.apply_auto_contrast(DEFAULT_PTYCHO_IMG_NM)


            # # pmap = numpy_array_to_qpixmap(self.ccd.image.image)
            # pmap = numpy_array_to_qpixmap(arr, image_size)
            # pmap = pmap.scaled(
            #     QtCore.QSize(QtCore.QSize(image_size, image_size)),
            #     QtCore.Qt.IgnoreAspectRatio,
            # )
            #
            # # Set the pixmap on the QLabel
            # self.camImgLbl.setPixmap(pmap)
            # # Replace the value to ignore with a value outside the range of possible values
            # count = np.count_nonzero(arr == 65535)
            # if count < 3:
            #     print(f"the value 65535 appears <3 ({count} times)) in the array, so ignoring those")
            #     array_2d_modified = np.where(arr == 65535, np.nan, arr)
            #     # Find the minimum and maximum values, ignoring the specified value
            #     min_value = int(np.nanmin(array_2d_modified))
            #     max_value = int(np.nanmax(array_2d_modified))
            # else:
            #     print(f"the value 65535 appears >3 ({count} times)) times in the array, so still using it")
            #     min_value = int(np.nanmin(arr))
            #     max_value = int(np.nanmax(arr))
            #
            # self.minPixelValLbl.setText(f"{min_value}")
            # self.maxPixelValLbl.setText(f"{max_value}")
            # del pmap




    def get_initial_default_scan(self, x_cntr, y_cntr):
        """
        return a spatial dict that has the params default params the ptycho plugin should come up with
        """
        x_roi = get_base_roi(
            SPDB_X,
            "DNM_SAMPLE_X",
            x_cntr,
            10,
            10,
            stepSize=None,
            max_scan_range=None,
            enable=True,
        )
        y_roi = get_base_roi(
            SPDB_Y,
            "DNM_SAMPLE_Y",
            y_cntr,
            10,
            10,
            stepSize=None,
            max_scan_range=None,
            enable=True,
        )
        scan = make_spatial_db_dict(x_roi=x_roi, y_roi=y_roi, sp_id=0)
        return scan

    def show_hdw_accel_details(self):
        # if hasattr(self, 'e712_wg'):
        if USE_E712_HDW_ACCEL:
            dark = get_style("dark")
            self.scan_class.e712_wg.setStyleSheet(dark)
            self.scan_class.e712_wg.show()

    def on_ev_pol_sel(self, idx):
        """
        set the flag, 0 == EV then Pol, 1 == Pol then EV
        :param idx:
        :return:
        """
        self.scan_class.set_ev_first_flg(idx)

    def connect_paramfield_signals(self):

        mtr_x = self.main_obj.get_sample_fine_positioner("X")
        mtr_y = self.main_obj.get_sample_fine_positioner("Y")

        xllm = mtr_x.get_low_limit()
        xhlm = mtr_x.get_high_limit()
        yllm = mtr_y.get_low_limit()
        yhlm = mtr_y.get_high_limit()

        rx = xhlm - xllm
        ry = yhlm - yllm

        lim_dct = {}
        lim_dct["X"] = {"llm": xllm, "hlm": xhlm, "rng": rx}
        lim_dct["Y"] = {"llm": yllm, "hlm": yhlm, "rng": ry}

        self.connect_param_flds_to_validator(lim_dct)

    def update_min_max(self):

        mtr_x = self.main_obj.get_sample_fine_positioner("X")
        mtr_y = self.main_obj.get_sample_fine_positioner("Y")

        xllm = mtr_x.get_low_limit()
        xhlm = mtr_x.get_high_limit()
        yllm = mtr_y.get_low_limit()
        yhlm = mtr_y.get_high_limit()
        rx = xhlm - xllm
        ry = yhlm - yllm

        dpo = self.centerXFld.dpo
        self.update_dpo_min_max(dpo, xllm, xhlm)

        dpo = self.centerYFld.dpo
        self.update_dpo_min_max(dpo, yllm, yhlm)

        dpo = self.rangeXFld.dpo
        self.update_dpo_min_max(dpo, rx, rx)

        dpo = self.rangeYFld.dpo
        self.update_dpo_min_max(dpo, ry, ry)

    def gen_max_scan_range_limit_def(self):
        """this function only currently centers around 0,0, this is a problem because in order
        to indicate when the range of the scan is larger than the fine ranges it must be valid around
        whereever o,o is on the fine physical stage is, as this is nly generated and sent to teh plot
        widget at startup it doesnt work properly when the scan is not around 0,0.
        leaving this for future
        """

        if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            self.gen_GONI_SCAN_max_scan_range_limit_def()
        else:
            mtr_sx = self.main_obj.device("DNM_SAMPLE_X")
            mtr_sy = self.main_obj.device("DNM_SAMPLE_Y")

            mtr_sfx = self.main_obj.get_sample_fine_positioner("X")
            mtr_sfy = self.main_obj.get_sample_fine_positioner("Y")

            center_x = mtr_sx.get_position()
            center_y = mtr_sy.get_position()

            xllm = mtr_sx.get_low_limit()
            xhlm = mtr_sx.get_high_limit()
            yllm = mtr_sy.get_low_limit()
            yhlm = mtr_sy.get_high_limit()

            fxllm = center_x - (MAX_SCAN_RANGE_FINEX * 0.5)
            fxhlm = center_x + (MAX_SCAN_RANGE_FINEX * 0.5)
            fyllm = center_y - (MAX_SCAN_RANGE_FINEY * 0.5)
            fyhlm = center_y + (MAX_SCAN_RANGE_FINEY * 0.5)

            bounding_qrect = QtCore.QRectF(
                QtCore.QPointF(xllm, yhlm), QtCore.QPointF(xhlm, yllm)
            )

            # adjust the warn qrect by 0.1 in all directions so that a scan range of the exact size of the limit is still allowed
            warn_qrect = QtCore.QRectF(
                QtCore.QPointF(fxllm - 0.1, fyhlm + 0.1),
                QtCore.QPointF(fxhlm + 0.1, fyllm - 0.1),
            )
            alarm_qrect = self.get_percentage_of_qrect(
                warn_qrect, 0.99999
            )  # %99 of max

            bounding = ROILimitObj(
                bounding_qrect,
                get_alarm_clr(255),
                "Range is beyond SampleXY Capabilities",
                get_warn_fill_pattern(),
            )
            normal = ROILimitObj(
                bounding_qrect,
                get_normal_clr(45),
                "Sample Image Fine Scan",
                get_normal_fill_pattern(),
            )
            # warn = ROILimitObj(warn_qrect, get_warn_clr(150), 'Sample Image Coarse Scan', get_warn_fill_pattern())
            # warn = ROILimitObj(warn_qrect, get_warn_clr(150), 'Nearing Range Limit for Sample Image Scan', get_warn_fill_pattern())
            warn = ROILimitObj(
                warn_qrect,
                get_warn_clr(150),
                "Coarse X/Y will have to be moved in order to perform scan",
                get_warn_fill_pattern(),
            )
            alarm = ROILimitObj(
                alarm_qrect,
                get_alarm_clr(255),
                "Beyond range of Sample Fine X/Y",
                get_alarm_fill_pattern(),
            )

            self.roi_limit_def = ROILimitDef(bounding, normal, warn, alarm)

    def gen_GONI_SCAN_max_scan_range_limit_def(self):
        """to be overridden by inheriting class"""
        mtr_zpx = self.main_obj.get_sample_fine_positioner("X")
        mtr_zpy = self.main_obj.get_sample_fine_positioner("Y")

        mtr_gx = self.main_obj.device("DNM_GONI_X")
        mtr_gy = self.main_obj.device("DNM_GONI_Y")

        gx_pos = mtr_gx.get_position()
        gy_pos = mtr_gy.get_position()

        # these are all added because the sign is in the LLIM
        xllm = gx_pos - (MAX_SCAN_RANGE_FINEX * 0.5)
        xhlm = gx_pos + (MAX_SCAN_RANGE_FINEX * 0.5)
        yllm = gy_pos - (MAX_SCAN_RANGE_FINEY * 0.5)
        yhlm = gy_pos + (MAX_SCAN_RANGE_FINEY * 0.5)

        gxllm = mtr_gx.get_low_limit()
        gxhlm = mtr_gx.get_high_limit()
        gyllm = mtr_gy.get_low_limit()
        gyhlm = mtr_gy.get_high_limit()

        bounding_qrect = QtCore.QRectF(
            QtCore.QPointF(gxllm, gyhlm), QtCore.QPointF(gxhlm, gyllm)
        )
        # warn_qrect = self.get_percentage_of_qrect(bounding, 0.90) #%80 of max
        # alarm_qrect = self.get_percentage_of_qrect(bounding, 0.95) #%95 of max
        normal_qrect = QtCore.QRectF(
            QtCore.QPointF(xllm, yhlm), QtCore.QPointF(xhlm, yllm)
        )
        warn_qrect = self.get_percentage_of_qrect(normal_qrect, 1.01)  # %95 of max
        alarm_qrect = self.get_percentage_of_qrect(normal_qrect, 1.0)  # %95 of max

        bounding = ROILimitObj(
            bounding_qrect,
            get_alarm_clr(255),
            "Range is beyond Goniometer Capabilities",
            get_alarm_fill_pattern(),
        )
        normal = ROILimitObj(
            normal_qrect, get_normal_clr(45), "Fine ZP Scan", get_normal_fill_pattern()
        )
        warn = ROILimitObj(
            warn_qrect,
            get_warn_clr(150),
            "Goniometer will be required to move",
            get_warn_fill_pattern(),
        )
        alarm = ROILimitObj(
            alarm_qrect,
            get_alarm_clr(255),
            "Range is beyond ZP Capabilities",
            get_alarm_fill_pattern(),
        )

        self.roi_limit_def = ROILimitDef(bounding, normal, warn, alarm)

    def init_sp_db(self):
        """
        init_sp_db standard function supported by all scan pluggins to initialize the local widget_com dict to whatever the
        GUI is currently displaying, this is usually called after the call to self.load_from_defaults()

        :returns: None

        """
        self.sp_db = self.multi_region_widget.sp_widg.get_row_data_by_item_id(0)

        # sgt = float(str(self.startGTFld.text()))
        # egt = float(str(self.endGTFld.text()))
        #
        # cgt = float(sgt + egt) / 2.0
        # rgt = float(egt - sgt)
        # ngt = int(str(self.npointsGTFld.text()))
        # stgt = float(str(self.stepGTFld.text()))
        #
        # # now create the model that this pluggin will use to record its params
        # gt_roi = get_base_roi(SPDB_GT, DNM_GONI_THETA, cgt, rgt, ngt, stgt)
        # goni_rois = {SPDB_GT: gt_roi}
        # self.sp_db = make_spatial_db_dict(goni_rois=goni_rois)

    # def check_scan_limits(self):
    #     ''' a function to be implemented by the scan pluggin that
    #     checks the scan parameters against the soft limits of the
    #     positioners, if all is well return true else false
    #
    #     This function should provide an explicit error log msg to aide the user
    #     '''
    #     ret = self.check_center_range_xy_scan_limits(DNM_SAMPLE_X, DNM_SAMPLE_Y)
    #     return(ret)

    def set_roi(self, roi):
        """
        set_roi standard function supported by all scan pluggins to initialize the GUI for this scan with values
        stored in the defaults library

        :param roi: is a standard dict returned from the call to DEFAULTS.get_defaults()
        :type roi: dict.

        :returns: None

        """
        pass

    def mod_roi(self, wdg_com, do_recalc=True, ev_only=False, sp_only=False):
        """
        wdg_com is a widget_com dict
        The purpose of the mod_roi() function is to update the fields in the GUI with the correct values
        it can be called by either a signal from one of the edit fields (ex: self.centerXFld) or
        by a signal from a plotter (via the main gui that is connected to the plotter) so that as a user
        grabs a region of interest marker in the plot and either moves or resizes it, those new center and size
        values will be delivered here and,  if required, the stepsizes will be recalculated


        :param wdg_com: is a standard dict returned from the call to sm.stxm_control.stxm_utils.roi_utils.make_spatial_db_dict()
        :type wdg_com: dict.

        :param do_recalc: selectively the STEP of the ROI's for X and Y can be recalculated if the number of points or range have changed
        :type do_recalc: flag.

        :returns: None

        """
        item_id = dct_get(wdg_com, SPDB_ID_VAL)
        dct_put(wdg_com, SPDB_PLOT_SHAPE_TYPE, self.plot_item_type)

        if wdg_com[CMND] == widget_com_cmnd_types.LOAD_SCAN:
            self.load_roi(wdg_com)
            return

        # if((wdg_com[CMND] == widget_com_cmnd_types.SELECT_ROI) or (wdg_com[CMND] == widget_com_cmnd_types.LOAD_SCAN)):
        if wdg_com[CMND] == widget_com_cmnd_types.SELECT_ROI:
            cur_scan = self.multi_region_widget.sp_widg.get_row_data_by_item_id(item_id)
            if cur_scan != None:
                # change the command to add this ROI
                self.multi_region_widget.sp_widg.select_row(item_id=item_id)
                return
                # wdg_com[CMND] = widget_com_cmnd_types.ROI_CHANGED
            else:
                x_roi = wdg_com[SPDB_X]
                y_roi = wdg_com[SPDB_Y]
                # x_roi[NPOINTS] = 20
                # y_roi[NPOINTS] = 20
                scan = make_spatial_db_dict(x_roi=x_roi, y_roi=y_roi)
                on_npoints_changed(scan[SPDB_X])
                on_npoints_changed(scan[SPDB_Y])
                scan[SPDB_ID_VAL] = item_id
                self.multi_region_widget.sp_widg.on_new_region(scan)
                self.multi_region_widget.sp_widg.select_row(item_id=item_id)
                return

        if wdg_com[CMND] == widget_com_cmnd_types.ROI_CHANGED:
            # print 'image_scans.mod_roi: item_id = %d' % item_id
            # we are being modified by the plotter
            x_roi = wdg_com[SPDB_X]
            y_roi = wdg_com[SPDB_Y]
            scan = make_spatial_db_dict(x_roi=x_roi, y_roi=y_roi)
            cur_scan = self.multi_region_widget.sp_widg.get_row_data_by_item_id(item_id)

            if cur_scan is None:
                scan[SPDB_ID_VAL] = item_id
                on_npoints_changed(scan[SPDB_X])
                on_npoints_changed(scan[SPDB_Y])

                _dwell = scan[SPDB_EV_ROIS][0][DWELL]
                _x = scan[SPDB_X]
                _y = scan[SPDB_Y]

                # self.multi_region_widget.sp_widg.table_view.add_scan(scan, wdg_com['CURRENT']['PLOT']['ITEM']['ID'])
                self.multi_region_widget.sp_widg.on_new_region(scan, ev_only=ev_only)
                self.multi_region_widget.sp_widg.select_row(item_id=item_id)
                # return
            else:
                # cur_scan = self.multi_region_widget.sp_widg.table_view.get_scan(item_id)
                # update the center and range fields that have come from the plotter
                # first call center recalc, then range
                cur_scan[SPDB_X][CENTER] = scan[SPDB_X][CENTER]
                on_center_changed(cur_scan[SPDB_X])

                cur_scan[SPDB_X][RANGE] = scan[SPDB_X][RANGE]
                on_range_changed(cur_scan[SPDB_X])

                cur_scan[SPDB_Y][CENTER] = scan[SPDB_Y][CENTER]
                on_center_changed(cur_scan[SPDB_Y])

                cur_scan[SPDB_Y][RANGE] = scan[SPDB_Y][RANGE]
                on_range_changed(cur_scan[SPDB_Y])

                _dwell = cur_scan[SPDB_EV_ROIS][0][DWELL]
                _x = cur_scan[SPDB_X]
                _y = cur_scan[SPDB_Y]

                self.multi_region_widget.sp_widg.select_row(item_id=item_id)
                self.multi_region_widget.sp_widg.modify_row_data(item_id, cur_scan)

                # return

            # if (self.sub_type == scan_sub_types.POINT_BY_POINT):
            #     self.calc_new_scan_time_estemate(True, _x, _y, _dwell)
            # else:
            #     self.calc_new_scan_time_estemate(False, _x, _y, _dwell)
            # return

    def get_image_file_format(self):
        """
        a convienience function to return which image file format the user has selected
        """
        if self.h5RadioBtn.isChecked():
            fformat = "HDF5"
        else:
            fformat = "TIFF"
        return fformat

    def update_last_settings(self):
        """update the 'default' settings that will be reloaded when this scan pluggin is selected again"""
        x_roi = self.sp_db[SPDB_X]
        y_roi = self.sp_db[SPDB_Y]
        e_rois = self.sp_db[SPDB_EV_ROIS]
        fformat = self.get_image_file_format()

        DEFAULTS.set("SCAN.PTYCHOGRAPHY.CENTER", (x_roi[CENTER], y_roi[CENTER], 0, 0))
        DEFAULTS.set("SCAN.PTYCHOGRAPHY.RANGE", (x_roi[RANGE], y_roi[RANGE], 0, 0))
        DEFAULTS.set(
            "SCAN.PTYCHOGRAPHY.NPOINTS", (x_roi[NPOINTS], y_roi[NPOINTS], 0, 0)
        )
        DEFAULTS.set("SCAN.PTYCHOGRAPHY.STEP", (x_roi[STEP], y_roi[STEP], 0, 0))
        DEFAULTS.set("SCAN.PTYCHOGRAPHY.DWELL", e_rois[0][DWELL])
        DEFAULTS.set("SCAN.PTYCHOGRAPHY.IMG_FILE_FORMAT", fformat)

        DEFAULTS.update()

    def update_data(self):
        """
        This is a standard function that all scan pluggins have that is called to
        get the data from the pluggins UI widgets and write them into a dict returned by
        get_base_scanparam_roi(), this dict is emitted by all scan pluggins to be used by
        the scan classes configure() functions

        :returns: None

        """
        # update local widget_com dict
        # the follwing is time consuming
        # if (self.sub_type == scan_sub_types.POINT_BY_POINT):
        # self.calc_new_scan_time_estemate(True, _x, _y, _dwell)
        # else:
        #     self.calc_new_scan_time_estemate(False, _x, _y, _dwell)
        # return
        # wdg_com = self.update_single_spatial_wdg_com()
        wdg_com = self.update_multi_spatial_wdg_com()

        #get the fiel type the user has selected and store it in the SPDB
        img_details = get_image_details_dict()
        fformat = self.get_image_file_format()
        img_details["image.format"] = fformat

        #dct_put(wdg_com, SPDB_SCAN_PLUGIN_SUBTYPE, self.sub_type)
        for k,sp_db in wdg_com['SPATIAL_ROIS'].items():
            dct_put(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE, self.sub_type)
            dct_put(sp_db, SPDB_SCAN_PLUGIN_IMG_DETAILS, img_details)

        self.roi_changed.emit(wdg_com)
        return wdg_com
