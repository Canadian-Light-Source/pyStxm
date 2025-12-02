"""
Created on Aug 25, 2014

@author: bergr
"""

from PyQt5 import uic, QtCore
import re
import os
import math

from cls.scanning.base import ScanParamWidget, zp_focus_modes
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *
from cls.scanning.paramLineEdit import intLineEditParamObj, dblLineEditParamObj
from cls.data_io.stxm_data_io import STXMDataIo

from cls.utils.roi_utils import (
    get_base_roi,
    get_base_start_stop_roi,
    get_base_energy_roi,
    make_spatial_db_dict,
)
from cls.utils.focus_calculations import focal_length
from cls.types.stxmTypes import scan_types, spatial_type_prefix, OSA_FOCUS_MODE, SAMPLE_FOCUS_MODE, image_types
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
from cls.appWidgets.dialogs import notify

scanning_mode = MAIN_OBJ.get_preset("scanning_mode","SCANNING_MODE")

_logger = get_module_logger(__name__)


class BaseOsaFocusScanParam(ScanParamWidget):
    def __init__(
        self, parent=None, main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__)
    ):
        super().__init__(main_obj=main_obj, data_io=data_io, dflts=dflts)
        self._parent = parent
        uic.loadUi(os.path.join(ui_path, "osa_focus_scan.ui"), self)

        self.selFocusBtn.clicked.connect(self.on_sel_focus_pos_btn)
        self.setFocusBtn.clicked.connect(self.on_set_focus_btn)
        self.loadScanBtn.clicked.connect(self.load_scan)
        self.horizSelBtn.clicked.connect(self.on_horiz_line_sel_btn)
        self.arbSelBtn.clicked.connect(self.on_arbitrary_line_sel_btn)

        self.scan_class = self.instanciate_scan_class(
            __file__, "OsaFocusScan", "OsaFocusScanClass"
        )

        #self.fl = self.main_obj.device("DNM_FOCAL_LENGTH")
        self.energy_dev = self.main_obj.device("DNM_ENERGY_DEVICE")
        self.energy_dev.focus_params_changed.connect(self.on_update_focus_params)
        self.a1 = self.main_obj.device("DNM_ZP_DEF_A")
        self.energy_mtr = self.main_obj.device("DNM_ENERGY")
        self.sp_db = None
        self.load_from_defaults()
        self.init_sp_db()
        self.connect_paramfield_signals()
        self.on_focus_scan_single_spatial_npoints_changed()
        self.init_loadscan_menu()


        zpz_pos = self.energy_dev.get_new_zpz_for_osa_focussed()
        self.set_parm(self.centerZPFld, zpz_pos)

    def init_plugin(self):
        """
        set the plugin specific details to common attributes
        :return:
        """
        self.name = "OSA Focus Scan"
        self.idx = self.main_obj.get_scan_panel_order(__file__)
        self.type = scan_types.OSA_FOCUS
        self.data = {}
        self.section_id = "OSA_FOCUS"
        # override base parameter idxs for the get center and range calls, params are in a list [X, Y, Z, ?]
        self.p0_idx = 0
        self.p1_idx = 2
        # data_file_pfx = 'of'
        self.data_file_pfx = self.main_obj.get_datafile_prefix()
        # axis_strings = [<left>, <bottom>, <top>, <right>]
        self.axis_strings = ["ZP Z microns", "OSA X microns", "", ""]
        self.zp_focus_mode = zp_focus_modes.FL
        self.plot_item_type = spatial_type_prefix.SEG

        self._type_interactive_plot = True
        self._type_skip_scan_q_table_plots = (
            True  # [scan_panel_order.OSA_FOCUS_SCAN, scan_panel_order.FOCUS_SCAN]
        )
        self._type_spectra_plot_type = (
            False  # [scan_panel_order.POINT_SCAN, scan_panel_order.POSITIONER_SCAN]
        )
        self._type_skip_centering_scans = (
            True  # [scan_panel_order.FOCUS_SCAN, scan_panel_order.TOMOGRAPHY,
        )
        # scan_panel_order.LINE_SCAN, scan_panel_order.POINT_SCAN, scan_panel_order.IMAGE_SCAN]
        self._type_do_recenter = False  # [scan_panel_order.IMAGE_SCAN, scan_panel_order.TOMOGRAPHY, scan_panel_order.LINE_SCAN]

        # self._help_html_fpath = os.path.join('interface', 'window_system', 'scan_plugins', 'detector.html')
        self._help_ttip = "OSA Focus scan documentation and instructions"

    def on_update_focus_params(self, focus_dct: dict):
        """
        Update the ZP center label
        """

        # update the ZP center
        # print(focus_dct)
        zpz_pos = focus_dct["zpz_for_osa_focussed"]
        self.set_parm(self.centerZPFld, zpz_pos)

    def on_plugin_focus(self):
        """
        This is a function that is called when the plugin first receives focus from the main GUI
        :return:
        """
        if self.isEnabled():
            if not self.is_focus_image():
                self.enable_line_select_btns(True)
            else:
                self.enable_line_select_btns(False)

            self.update_est_time()
            self.energy_dev.set_focus_mode("OSA")

            self._new_zpz_pos = None
            if self.main_obj.device("DNM_OSAY_TRACKING", do_warn=False):
                # make sure that the OSA vertical tracking is off if it is on
                self.osay_trcking_was = self.main_obj.device(
                    "DNM_OSAY_TRACKING"
                ).get_position()
                self.main_obj.device("DNM_OSAY_TRACKING").put(0)  # off

    def on_plugin_defocus(self):
        """
        This is a function that is called when the plugin leaves focus from the main GUI
        :return:
        """
        if self.isEnabled():
            if self.main_obj.device("DNM_OSAY_TRACKING", do_warn=False):
                # put the OSA vertical tracking back to its previous state
                self.main_obj.device("DNM_OSAY_TRACKING").put(self.osay_trcking_was)

        # call the base class defocus
        super().on_plugin_defocus()

    def connect_paramfield_signals(self):

        mtr_x = self.main_obj.device("DNM_OSA_X")
        mtr_y = self.main_obj.device("DNM_OSA_Y")
        mtr_z = self.main_obj.device("DNM_ZONEPLATE_Z")

        xllm = mtr_x.get_low_limit()
        xhlm = mtr_x.get_high_limit()
        yllm = mtr_y.get_low_limit()
        yhlm = mtr_y.get_high_limit()
        zllm = mtr_z.get_low_limit()
        zhlm = mtr_z.get_high_limit()

        rx = xhlm - xllm
        ry = yhlm - yllm
        rz = zhlm - zllm

        lim_dct = {}
        lim_dct["X"] = {"llm": xllm, "hlm": xhlm, "rng": rx}
        lim_dct["Y"] = {"llm": yllm, "hlm": yhlm, "rng": ry}
        lim_dct["ZP"] = {"llm": zllm, "hlm": zhlm, "rng": rz}

        self.connect_param_flds_to_validator(lim_dct)

    def enable_line_select_btns(self, en):
        """
        enable or disable the line selection buttons, if the image is currently an OSA focus then disable the buttons

        Args:
            en:

        Returns:

        """
        if en:
            self.horizSelBtn.setEnabled(True)
            self.arbSelBtn.setEnabled(True)
        else:
            self.horizSelBtn.setEnabled(False)
            self.arbSelBtn.setEnabled(False)

    def on_sel_focus_pos_btn(self, chkd):
        """
        when pressed this activates the clsSelectPositionTool in the plotter
        calls the parent (stxmMain) to tell the plotter to activate/deactivate the
        clsSelectPositionTool and to connect the plotters 'new_selected_position' signal to our handler
        """
        if chkd:
            self.enable_focus_btns()
            self._parent.activate_sel_position_tool(True, self.on_new_pos_selected)
        else:
            self._parent.activate_sel_position_tool(False, self.on_new_pos_selected)
            self.reset_focus_btns(deactivate_tool=False)

    def on_new_pos_selected(self, x, y):
        """
        a handler for the plotters 'new_selected_position' signal
        that updates our new focus position to use for setting focus
        """
        self._new_zpz_pos = y
        self.setFocusBtn.setText(f"Set Focus to Cursor ({y:.2f} um)")

    def gen_max_scan_range_limit_def(self):
        """to be overridden by inheriting class"""
        mtr_zpx = self.main_obj.device("DNM_OSA_X")
        mtr_zpy = self.main_obj.device("DNM_OSA_Y")

        xllm = mtr_zpx.get_low_limit()
        xhlm = mtr_zpx.get_high_limit()
        yllm = mtr_zpy.get_low_limit()
        yhlm = mtr_zpy.get_high_limit()

        bounding_qrect = QtCore.QRectF(
            QtCore.QPointF(xllm, yhlm), QtCore.QPointF(xhlm, yllm)
        )
        warn_qrect = self.get_percentage_of_qrect(bounding_qrect, 0.80)  #%80 of max
        alarm_qrect = self.get_percentage_of_qrect(bounding_qrect, 0.95)  #%95 of max

        bounding = ROILimitObj(
            bounding_qrect,
            get_alarm_clr(255),
            "Range is beyond OSA Capabilities",
            get_alarm_fill_pattern(),
        )
        normal = ROILimitObj(
            bounding_qrect,
            get_normal_clr(45),
            "OSA Focus Scan",
            get_normal_fill_pattern(),
        )
        warn = ROILimitObj(
            warn_qrect,
            get_warn_clr(150),
            "Nearing max Range of OSA X/Y",
            get_warn_fill_pattern(),
        )
        alarm = ROILimitObj(
            alarm_qrect,
            get_alarm_clr(255),
            "Beyond range of OSA X/Y",
            get_alarm_fill_pattern(),
        )

        self.roi_limit_def = ROILimitDef(bounding, normal, warn, alarm)

    def init_sp_db(self):
        """
        init_sp_db standard function supported by all scan pluggins to initialize the local widget_com dict to whatever the
        GUI is currently displaying, this is usually called after the call to self.load_from_defaults()

        :returns: None

        """
        sx = float(str(self.startXFld.text()))
        ex = float(str(self.endXFld.text()))
        sy = float(str(self.startYFld.text()))
        ey = float(str(self.endYFld.text()))

        dwell = float(str(self.dwellFld.text()))
        nx = int(
            str(self.npointsXFld.text())
        )  # + NUM_POINTS_LOST_AFTER_EDIFF  #+1 for the first data point being the row
        if nx == 0:
            nx = 1
        ny = nx

        cz = float(str(self.centerZPFld.text()))
        rz = float(str(self.rangeZPFld.text()))
        nz = int(str(self.npointsZPFld.text()))

        # now create the model that this pluggin will use to record its params
        x_roi = get_base_start_stop_roi(
            SPDB_X,
            "DNM_OSA_X",
            sx,
            ex,
            nx,
            src=self.main_obj.device("DNM_OSA_X").get_name(),
        )
        y_roi = get_base_start_stop_roi(
            SPDB_Y,
            "DNM_OSA_Y",
            sy,
            ey,
            ny,
            src=self.main_obj.device("DNM_OSA_Y").get_name(),
        )
        zz_roi = get_base_roi(
            SPDB_ZZ,
            "DNM_ZONEPLATE_Z",
            cz,
            rz,
            nz,
            enable=False,
            src=self.main_obj.device("DNM_ZONEPLATE_Z").get_name(),
        )

        energy_pos = self.main_obj.device("DNM_ENERGY").get_position()
        e_roi = get_base_energy_roi(
            "EV", "DNM_ENERGY", energy_pos, energy_pos, 0, 1, dwell, None, enable=False
        )

        zp_rois = {}
        dct_put(zp_rois, SPDB_ZZ, zz_roi)

        self.sp_db = make_spatial_db_dict(
            x_roi=x_roi, y_roi=y_roi, e_roi=e_roi, zp_rois=zp_rois
        )

    def check_scan_limits(self):
        """a function to be implemented by the scan pluggin that
        checks the scan parameters against the soft limits of the
        positioners, if all is well return true else false

        """
        retxy = self.check_start_stop_xy_scan_limits("DNM_OSA_X", "DNM_OSA_Y")
        retz = self.check_center_range_z_scan_limits("DNM_ZONEPLATE_Z")

        if retxy and retz:
            return True
        else:
            return False

    def disable_focus_btns(self):
        """
            disable the focus btns
        """
        self.setFocusBtn.setText(f"Set Focus to Cursor")
        self.setFocusBtn.setChecked(False)

    def enable_focus_btns(self):
        """
        enable the focus btns
        """
        self.setFocusBtn.setEnabled(True)

    def reset_focus_btns(self, deactivate_tool=True):
        """
        called when a set focus btn has been pressed
        """
        self.disable_focus_btns()
        self.selFocusBtn.setChecked(False)
        if deactivate_tool:
            self._parent.activate_sel_position_tool(False, self.on_new_pos_selected)

    def on_set_focus_btn(self):
        """
        set focus
        """
        if self._new_zpz_pos == None:
            _logger.info("You must first select a position before you can set focus")
            notify(
                "Unable to set focus",
                "You must first select a position before you can set focus",
                accept_str="OK",
            )
            return
        sflag = self.main_obj.device("DNM_ZONEPLATE_SCAN_MODE")
        mtr_zz = self.main_obj.device("DNM_ZONEPLATE_Z")
        mtrx = self.main_obj.device("DNM_OSA_X")
        mtry = self.main_obj.device("DNM_OSA_Y")
        # mtr_cz = self.main_obj.device("DNM_COARSE_Z")
        # cur_cz_pos = mtr_cz.get_position()
        # energy = self.main_obj.device("DNM_ENERGY").get_position()
        # fl = self.main_obj.get_focal_length(energy)
        fl_as_zpz_pos = self.energy_dev.get_focal_length_as_zpz_position()
        # zpz_in_focus = self.energy_dev.calc_new_zoneplate_z_pos_for_focus(energy)
        # a0_val = self.main_obj.get_a0()

        if re.search(scanning_mode, 'COARSE_SAMPLEFINE', re.IGNORECASE):

            # 0 for OSA focus scan 1 for Sample Focus
            # if sflag:
            #     sflag.put(SAMPLE_FOCUS_MODE)

            zp_cent = float(self._new_zpz_pos)

            # support for DCS server motors that use offsets
            if hasattr(mtr_zz, 'apply_delta_to_offset'):
                delta = float(str(self.centerZPFld.text())) - zp_cent
                mtr_zz.apply_delta_to_offset(delta)
            else:
                mtr_zz.call_emit_move(zp_cent, wait=True)

            if hasattr(mtr_zz, 'confirm_stopped'):
                mtr_zz.confirm_stopped()
            if hasattr(mtr_zz, 'set_position'):
                mtr_zz.set_position(fl_as_zpz_pos)

            mtrx.call_emit_move(0.0, wait=False)
            mtry.call_emit_move(0.0, wait=False)

            #now move to Sample Focus position which is == FL - A0
            # zpz_in_focus = -1.0 * (math.fabs(fl) - math.fabs(a0_val))
            #zpz_in_focus = self.main_obj.calc_new_zoneplate_z_pos_for_focus(energy)

            #mtr_zz.call_emit_move(fl_as_zpz_pos, wait=False)
            self.energy_dev.move_to_osa_focussed()


        elif re.search(scanning_mode, 'GONI_ZONEPLATE', re.IGNORECASE):
            ###### NEEDS TO BE TESTED ON CRYO STXM
            oz = self.main_obj.device("DNM_OSA_Z")

            # 0 for OSA focus scan 1 for Sample Focus
            if sflag:
                sflag.put(SAMPLE_FOCUS_MODE)

            #zp_cent = float(str(self.centerZPFld.text()))
            zp_cent = float(self._new_zpz_pos)
            # mtr_zz = self.main_obj.device('DNM_ZONEPLATE_Z')

            # support for DCS server motors that use offsets
            if hasattr(mtr_zz, 'apply_delta_to_offset'):
                delta = float(str(self.centerZPFld.text())) - zp_cent
                mtr_zz.apply_delta_to_offset(delta)
            else:
                mtr_zz.call_emit_move(zp_cent, wait=True)
                mtr_zz.confirm_stopped()

                mtr_zz.set_position(fl_as_zpz_pos)

            mtrx.call_emit_move(0.0, wait=False)
            mtry.call_emit_move(0.0, wait=False)
            # now move to Sample Focus position which is == FL - A0
            # zpz_final_pos = -1.0 * (math.fabs(fl) - math.fabs(a0_val))
            # mtr_zz.call_emit_move(zpz_final_pos, wait=False)
            self.energy_dev.move_to_sample_focussed()

        elif re.search(scanning_mode, 'COARSE_ZONEPLATE', re.IGNORECASE):
            _logger.info("Setting focus for COARSE_ZONEPLATE currently not supported")

        # have the plotter delete the focus image
        self._parent.reset_image_plot(shape_only=True)
        self.reset_focus_btns()

    def set_roi(self, roi):
        """
        set_roi standard function supported by all scan pluggins to initialize the GUI for this scan with values
        stored in the defaults library

        :param roi: is a standard dict returned from the call to DEFAULTS.get_defaults()
        :type roi: dict.

        :returns: None

        """
        sx = sy = ex = ey = None
        (sx, sy, sz, s0) = roi[START]
        (ex, ey, ez, e0) = roi[STOP]

        (cx, cy, cz, c0) = roi[CENTER]
        (rx, ry, rz, s0) = roi[RANGE]
        (nx, ny, nz, n0) = roi[NPOINTS]
        (stpx, stpy, stpz, stp0) = roi[STEP]

        if "DWELL" in roi:
            self.set_parm(self.dwellFld, roi[DWELL])

        self.set_parm(self.startXFld, sx)
        self.set_parm(self.startYFld, sy)

        # we want the ZP center to always be the current Zpz pozition
        # zpz_pos = self.main_obj.device("DNM_ZONEPLATE_Z").get_position()
        # self.set_parm(self.centerZPFld, zpz_pos)

        if ex != None:
            self.set_parm(self.endXFld, ex)

        if ey != None:
            self.set_parm(self.endYFld, ey)

        if rz != None:
            self.set_parm(self.rangeZPFld, rz)

        if nx != None:
            self.set_parm(self.npointsXFld, nx, type="int", floor=0)

        if nz != None:
            self.set_parm(self.npointsZPFld, nz, type="int", floor=0)


    def mod_roi(self, sp_db, do_recalc=True, sp_only=False):
        """
                sp_db is a widget_com dict
                The purpose of the mod_roi() function is to update the fields in the GUI with the correct values
                it can be called by either a signal from one of the edit fields (ex: self.startXFld) or
                by a signal from a plotter (via the main gui that is connected to the plotter) so that as a user
                grabs a region of interest marker in the plot and either moves or resizes it, those new center and size
        R        values will be delivered here and,  if required, the stepsizes will be recalculated


                :param sp_db: is a standard dict returned from the call to sm.stxm_control.stxm_utils.roi_utils.make_spatial_db_dict()
                :type sp_db: dict.

                :param do_recalc: selectively the STEP of the ROI's for X and Y can be recalculated if the number of points or range have changed
                :type do_recalc: flag.

                :returns: None

        """
        dct = self.get_function_caller_info()
        if dct['caller_function_name'] == 'on_plotitem_roi_changed':
            # check to see if the current image is a focus image, if so then skip modifying the roi
            if not self.is_focus_image():
                self.focus_scan_mod_roi(sp_db, do_recalc)
            else:
                self.enable_line_select_btns(False)
        else:
            self.focus_scan_mod_roi(sp_db, do_recalc)

    def update_last_settings(self):
        """
        to be implemented by inheriting class
        example:
            update the 'default' settings that will be reloaded when this scan pluggin is selected again



        :return:
        """
        x_roi = dct_get(self.sp_db, SPDB_X)
        y_roi = dct_get(self.sp_db, SPDB_Y)
        zz_roi = dct_get(self.sp_db, SPDB_ZZ)
        # e_rois = self.sp_db[SPDB_EV_ROIS]
        e_rois = dct_get(self.sp_db, SPDB_EV_ROIS)

        DEFAULTS.set(
            "SCAN.OSA_FOCUS.START", (x_roi[START], y_roi[START], zz_roi[START], 0)
        )
        DEFAULTS.set("SCAN.OSA_FOCUS.STOP", (x_roi[STOP], y_roi[STOP], zz_roi[STOP], 0))
        DEFAULTS.set(
            "SCAN.OSA_FOCUS.CENTER", (x_roi[CENTER], y_roi[CENTER], zz_roi[CENTER], 0)
        )
        DEFAULTS.set(
            "SCAN.OSA_FOCUS.RANGE", (x_roi[RANGE], y_roi[RANGE], zz_roi[RANGE], 0)
        )
        DEFAULTS.set(
            "SCAN.OSA_FOCUS.NPOINTS",
            (x_roi[NPOINTS], y_roi[NPOINTS], zz_roi[NPOINTS], 0),
        )
        DEFAULTS.set("SCAN.OSA_FOCUS.STEP", (x_roi[STEP], y_roi[STEP], zz_roi[STEP], 0))
        DEFAULTS.set("SCAN.OSA_FOCUS.DWELL", e_rois[0][DWELL])
        DEFAULTS.update()
        self.update_est_time()


    def update_data(self):
        """
        This is a standard function that all scan pluggins have that is called to
        get the data from the pluggins UI widgets and write them into a dict returned by
        get_base_scanparam_roi(), this dict is emitted by all scan pluggins to be used by
        the scan classes configure() functions

        :param allow_signals: selectively allow the updating of the params to fire signals, this way we can prevent a change
                                of a ZP param from updating the plot window
        :type allow_signals: flag.

        :returns: None

        """
        # force the subtype to be a PXP
        wdg_com = self.focus_scan_update_data(force_pxp=True)
        self.update_est_time()
        self.roi_changed.emit(wdg_com)
        return wdg_com
