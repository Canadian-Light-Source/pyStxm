"""
Created on Aug 25, 2014

@author: bergr
"""
from PyQt5 import QtCore, QtGui
from PyQt5 import uic

import copy
import os
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.scanning.base import ScanParamWidget, zp_focus_modes

# from cls.applications.pyStxm.scan_plugins import plugin_dir

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *
from cls.scanning.paramLineEdit import intLineEditParamObj, dblLineEditParamObj
from cls.data_io.stxm_data_io import STXMDataIo
from cls.data_io.utils import (
    test_eq,
    check_roi_for_match,
    get_first_entry_key,
    get_first_sp_db_from_entry,
    get_axis_setpoints_from_sp_db,
)

from cls.utils.roi_utils import (
    get_base_roi,
    get_base_energy_roi,
    make_spatial_db_dict,
    widget_com_cmnd_types,
    on_range_changed,
    on_center_changed,
)
from cls.types.stxmTypes import scan_types, spatial_type_prefix, image_types
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

# from cls.applications.pyStxm.bl_configs.basic.scan_plugins.osa_scan.osa_scan_tester import test_sp_db

_logger = get_module_logger(__name__)


class BaseOsaScanParam(ScanParamWidget):
    def __init__(
        self, parent=None, main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__)
    ):
        super().__init__(main_obj=main_obj, data_io=data_io, dflts=dflts)
        self._parent = parent
        uic.loadUi(os.path.join(ui_path, "osa_scan.ui"), self)

        self.fbk_cntr = 0
        self.scan_mod_path, self.scan_mod_name = self.derive_scan_mod_name(__file__)

        # self.setup_OSA_plotWidget()
        self.scan_class = self.instanciate_scan_class(
            __file__, "OsaScan", "OsaScanClass"
        )

        self.selCenterBtn.clicked.connect(self.on_sel_center_pos_btn)
        self.osaInBtn.clicked.connect(self.on_osa_in)
        self.setCenterBtn.clicked.connect(self.on_set_center)
        self.loadScanBtn.clicked.connect(self.load_scan)
        self.osa_tracking_enabled = False
        if self.main_obj.device("DNM_OSAY_TRACKING", do_warn=False):
            self.osay_trcking_was = self.main_obj.device(
                "DNM_OSAY_TRACKING"
            ).get_position()
            self.osa_tracking_enabled
        else:
            self.osay_trcking_was = None
            self.osa_tracking_enabled = False

        self.sp_db = None
        self.load_from_defaults()
        self.init_sp_db()
        self.connect_paramfield_signals()
        self.on_single_spatial_npoints_changed()
        self.init_test_module()
        self.init_loadscan_menu()

    def init_plugin(self):
        """
        set the plugin specific details to common attributes
        :return:
        """
        self.name = "OSA Scan"
        self.idx = self.main_obj.get_scan_panel_order(__file__)
        self.type = scan_types.OSA_IMAGE
        self.data = {}
        self.section_id = "OSA"
        self.axis_strings = ["OSA Y microns", "OSA X microns", "", ""]
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
        self._help_ttip = "OSA scan documentation and instructions"

    def on_plugin_focus(self):
        """
        This is a function that is called when the plugin first receives focus from the main GUI
        :return:
        """
        if self.isEnabled():
            # make sure that the OSA vertical tracking is off if it is on
            self.update_est_time()
            if self.osa_tracking_enabled:
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
            if self.osa_tracking_enabled:
                # put the OSA vertical tracking back to its previous state
                self.main_obj.device("DNM_OSAY_TRACKING").put(self.osay_trcking_was)

        # call the base class defocus
        super().on_plugin_defocus()

    def on_sel_center_pos_btn(self, chkd):
        """
        when pressed this activates the clsSelectPositionTool in the plotter
        calls the parent (stxmMain) to tell the plotter to activate/deactivate the
        clsSelectPositionTool and to connect the plotters 'new_selected_position' signal to our handler
        """
        if chkd:
            #create the box first
            self.on_new_center_selected()
            self.enable_center_btns()
            self._parent.activate_sel_center_position_tool(True, self.on_new_center_selected)
        else:
            self._parent.activate_sel_center_position_tool(False, self.on_new_center_selected)
            self.reset_center_btns(deactivate_tool=False)

    def on_new_center_selected(self, x=None, y=None):
        """
        a handler for the plotters 'new_selected_position' signal
        that updates our new center position to use for setting center
        """
        if x == None:
            x = float(self.centerXFld.text())
            y = float(self.centerYFld.text())

        self.setCenterBtn.setText(f"Set Center to Cursor (({x:.2f} um, {y:.2f} um)")
        self.centerXFld.setText(f"{x:.2f}")
        self.centerYFld.setText(f"{y:.2f}")
        #force box on plotter to update position
        self.centerXFld.returnPressed.emit()

    def disable_center_btns(self):
        """
            disable the focus btns
        """
        self.setCenterBtn.setText(f"Set Center to Cursor")
        self.setCenterBtn.setEnabled(False)
        self.selCenterBtn.setChecked(False)

    def enable_center_btns(self):
        """
        enable the focus btns
        """
        self.setCenterBtn.setEnabled(True)

    def reset_center_btns(self, deactivate_tool=True):
        """
        called when a set focus btn has been pressed
        """
        self.disable_center_btns()
        if deactivate_tool:
            self._parent.activate_sel_center_position_tool(False, self.on_new_center_selected)
        # self._parent.reset_image_plot()

    def connect_paramfield_signals(self):

        mtr_x = self.main_obj.device("DNM_OSA_X")
        mtr_y = self.main_obj.device("DNM_OSA_Y")

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

        mtr_x = self.main_obj.device("DNM_OSA_X")
        mtr_y = self.main_obj.device("DNM_OSA_Y")

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
        """to be overridden by inheriting class"""
        mtr_x = self.main_obj.device("DNM_OSA_X")
        mtr_y = self.main_obj.device("DNM_OSA_Y")

        xllm = mtr_x.get_low_limit()
        xhlm = mtr_x.get_high_limit()
        yllm = mtr_y.get_low_limit()
        yhlm = mtr_y.get_high_limit()

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
            bounding_qrect, get_normal_clr(45), "OSA Scan", get_normal_fill_pattern()
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
        cx = float(str(self.centerXFld.text()))
        rx = float(str(self.rangeXFld.text()))
        cy = float(str(self.centerYFld.text()))
        ry = float(str(self.rangeYFld.text()))
        dwell = float(str(self.dwellFld.text()))
        nx = int(str(self.npointsXFld.text()))
        ny = int(str(self.npointsYFld.text()))
        sx = float(str(self.stepXFld.text()))
        sy = float(str(self.stepYFld.text()))
        # now create the model that this pluggin will use to record its params
        x_roi = get_base_roi(SPDB_X, "DNM_OSA_X", cx, rx, nx, sx)
        y_roi = get_base_roi(SPDB_Y, "DNM_OSA_Y", cy, ry, ny, sy)
        z_roi = get_base_roi(SPDB_Z, None, 0, 0, 0, enable=False)
        # def get_base_energy_roi(name, positionerName, start, stop, rng, npoints, dwell, pol_rois, stepSize=None, enable=False):
        energy_pos = self.main_obj.device("DNM_ENERGY").get_position()
        # e_rois = [get_base_energy_roi('EV', DNM_ENERGY, energy_pos, energy_pos, 0, 1, dwell, None, enable=False )]
        e_roi = get_base_energy_roi(
            "EV", "DNM_ENERGY", energy_pos, energy_pos, 0, 1, dwell, None, enable=False
        )

        self.sp_db = make_spatial_db_dict(
            x_roi=x_roi, y_roi=y_roi, z_roi=z_roi, e_roi=e_roi
        )

    def check_scan_limits(self):
        """a function to be implemented by the scan pluggin that
        checks the scan parameters against the soft limits of the
        positioners, if all is well return true else false

        This function should provide an explicit error log msg to aide the user
        """
        ret = self.check_center_range_xy_scan_limits("DNM_OSA_X", "DNM_OSA_Y")
        return ret

    def on_set_center(self):
        """
        when user clicks set center btn
        """
        centX = float(str(self.centerXFld.text()))
        centY = float(str(self.centerYFld.text()))

        mtrx = self.main_obj.device("DNM_OSA_X")
        mtry = self.main_obj.device("DNM_OSA_Y")
        mtrx.move(centX)
        mtry.move(centY)

        mtrx.wait_for_stopped_and_zero()
        mtry.wait_for_stopped_and_zero()

        self.sp_db[SPDB_X][CENTER] = 0.0
        on_center_changed(self.sp_db[SPDB_X])
        self.sp_db[SPDB_Y][CENTER] = 0.0
        on_center_changed(self.sp_db[SPDB_Y])

        roi = {}
        roi[CENTER] = (0.0, 0.0, 0.0, 0.0)
        roi[RANGE] = (None, None, None, None)
        roi[NPOINTS] = (None, None, None, None)
        roi[STEP] = (None, None, None, None)
        self.set_roi(roi)

        self.reset_center_btns()

        DEFAULTS.set("PRESETS.OSA.CENTER", (0, 0, 0.0, 0.0))
        DEFAULTS.set("SCAN.OSA.CENTER", (0.0, 0.0, 0.0, 0.0))
        DEFAULTS.set("SCAN.OSA_FOCUS.CENTER", (0.0, 0.0, 0.0, 0.0))
        DEFAULTS.update()

        self.upd_timer.start(250)

    def on_osa_in(self):
        osax_mtr = self.main_obj.device("DNM_OSA_X")
        osay_mtr = self.main_obj.device("DNM_OSA_Y")

        # move to last recorded good center position
        osax_mtr.move(DEFAULTS.get("PRESETS.OSA.CENTER")[0])
        osay_mtr.move(DEFAULTS.get("PRESETS.OSA.CENTER")[1])

    def move_osaxy_mtrs(self, xpos, ypos):
        self.main_obj.device("DNM_OSA_X").move(xpos)
        self.main_obj.device("DNM_OSA_Y").move(ypos)

    def set_roi(self, roi):
        """
        set_roi standard function supported by all scan pluggins to initialize the GUI for this scan with values
        stored in the defaults library

        :param roi: is a standard dict returned from the call to DEFAULTS.get_defaults()
        :type roi: dict.

        :returns: None

        """
        # print 'det_scan: set_roi: ' , roi
        (cx, cy, cz, c0) = roi[CENTER]
        (rx, ry, rz, s0) = roi[RANGE]
        (nx, ny, nz, n0) = roi[NPOINTS]
        (sx, sy, sz, s0) = roi[STEP]

        if DWELL in roi:
            self.set_parm(self.dwellFld, roi[DWELL])

        self.set_parm(self.centerXFld, cx)
        self.set_parm(self.centerYFld, cy)

        if rx != None:
            self.set_parm(self.rangeXFld, rx)
        if ry != None:
            self.set_parm(self.rangeYFld, ry)

        if nx != None:
            self.set_parm(self.npointsXFld, nx, type="int", floor=2)

        if ny != None:
            self.set_parm(self.npointsYFld, ny, type="int", floor=2)

        if sx != None:
            self.set_parm(self.stepXFld, sx, type="float", floor=0)

        if sy != None:
            self.set_parm(self.stepYFld, sy, type="float", floor=0)


    def mod_roi(self, sp_db, do_recalc=True, sp_only=True):
        """
        sp_db is a widget_com dict
        The purpose of the mod_roi() function is to update the fields in the GUI with the correct values
        it can be called by either a signal from one of the edit fields (ex: self.centerXFld) or
        by a signal from a plotWidgetter (via the main gui that is connected to the plotWidgetter) so that as a user
        grabs a region of interest marker in the plotWidget and either moves or resizes it, those new center and size
        values will be delivered here and,  if required, the stepsizes will be recalculated


        :param sp_db: is a standard dict returned from the call to sm.stxm_control.stxm_utils.roi_utils.make_spatial_db_dict()
        :type sp_db: dict.

        :param do_recalc: selectively the STEP of the ROI's for X and Y can be recalculated if the number of points or range have changed
        :type do_recalc: flag.

        :returns: None

        """
        if sp_db[CMND] == widget_com_cmnd_types.DEL_ROI:
            return

        if sp_db[CMND] == widget_com_cmnd_types.LOAD_SCAN:
            self.sp_db = sp_db
        else:
            if sp_db[CMND] == widget_com_cmnd_types.SELECT_ROI:
                dct_put(self.sp_db, SPDB_ID_VAL, dct_get(sp_db, SPDB_PLOT_ITEM_ID))

            self.sp_db[SPDB_X][CENTER] = sp_db[SPDB_X][CENTER]

            if sp_db[SPDB_X][RANGE] != 0:
                self.sp_db[SPDB_X][RANGE] = sp_db[SPDB_X][RANGE]

            self.sp_db[SPDB_Y][CENTER] = sp_db[SPDB_Y][CENTER]

            if sp_db[SPDB_Y][RANGE] != 0:
                self.sp_db[SPDB_Y][RANGE] = sp_db[SPDB_Y][RANGE]

            # on_center_changed(self.sp_db[SPDB_X])
            # on_center_changed(self.sp_db[SPDB_Y])

        x_roi = self.sp_db[SPDB_X]
        y_roi = self.sp_db[SPDB_Y]
        e_rois = self.sp_db[SPDB_EV_ROIS]

        # if do_recalc then it is because mod_roi() has been called by a signal that the
        # plotWidgetter has resized/moved the ROI, the recalc of x/y when the number of points
        # is changed is handled above in the signal for the npointsFld
        if do_recalc:
            on_range_changed(x_roi)
            on_range_changed(y_roi)

        self.set_parm(self.centerXFld, x_roi[CENTER])
        self.set_parm(self.centerYFld, y_roi[CENTER])

        if e_rois[0][DWELL] != None:
            self.set_parm(self.dwellFld, e_rois[0][DWELL])

        if x_roi[RANGE] != None:
            self.set_parm(self.rangeXFld, x_roi[RANGE])
        if y_roi[RANGE] != None:
            self.set_parm(self.rangeYFld, y_roi[RANGE])

        if x_roi[NPOINTS] != None:
            self.set_parm(self.npointsXFld, x_roi[NPOINTS], type="int", floor=2)

        if y_roi[NPOINTS] != None:
            self.set_parm(self.npointsYFld, y_roi[NPOINTS], type="int", floor=2)

        if x_roi[STEP] != None:
            self.set_parm(self.stepXFld, x_roi[STEP], type="float", floor=0)

        if y_roi[STEP] != None:
            self.set_parm(self.stepYFld, y_roi[STEP], type="float", floor=0)

        # if(sp_db[CMND] == widget_com_cmnd_types.SELECT_ROI):
        #      self.update_last_settings()


    def update_last_settings(self):
        """update the 'default' settings that will be reloaded when this scan pluggin is selected again"""
        x_roi = self.sp_db[SPDB_X]
        y_roi = self.sp_db[SPDB_Y]
        e_rois = self.sp_db[SPDB_EV_ROIS]

        DEFAULTS.set("SCAN.OSA.CENTER", (x_roi[CENTER], y_roi[CENTER], 0, 0))
        DEFAULTS.set("SCAN.OSA.RANGE", (x_roi[RANGE], y_roi[RANGE], 0, 0))
        DEFAULTS.set("SCAN.OSA.NPOINTS", (x_roi[NPOINTS], y_roi[NPOINTS], 0, 0))
        DEFAULTS.set("SCAN.OSA.STEP", (x_roi[STEP], y_roi[STEP], 0, 0))
        DEFAULTS.set("SCAN.OSA.DWELL", e_rois[0][DWELL])
        DEFAULTS.update()
        self.update_est_time()

    def update_data(self):
        """
        This is a standard function that all scan pluggins have that is called to
        get the data from the pluggins UI widgets and write them into a dict returned by
        get_base_scanparam_roi(), this dict is emitted by all scan pluggins to be used by
        the scan classes configure() functions

        :returns: None

        """
        # update local widget_com dict
        wdg_com = self.update_single_spatial_wdg_com()
        self.update_est_time()
        self.roi_changed.emit(wdg_com)
        return wdg_com
