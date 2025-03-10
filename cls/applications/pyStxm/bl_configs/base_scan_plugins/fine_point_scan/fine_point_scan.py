"""
Created on Aug 25, 2014

@author: bergr
"""

from PyQt5 import uic
from PyQt5 import QtCore, QtGui

import os
from cls.stylesheets import get_style
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS

# from cls.applications.pyStxm.bl_configs.amb_bl10ID1.device_names import *
from cls.scanning.base import MultiRegionScanParamBase, zp_focus_modes

# from cls.applications.pyStxm.scan_plugins import plugin_dir
from cls.applications.pyStxm.widgets.scan_table_view.multiRegionWidget import (
    MultiRegionWidget,
)
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.roi_utils import (
    get_base_roi,
    make_spatial_db_dict,
    widget_com_cmnd_types,
    on_range_changed,
    on_npoints_changed,
    on_step_size_changed,
    on_start_changed,
    on_stop_changed,
    on_center_changed,
    recalc_setpoints,
    get_base_start_stop_roi,
    get_first_sp_db_from_wdg_com,
)
from cls.types.stxmTypes import (
    scan_types,
    scan_sub_types,
    spatial_type_prefix,
    sample_positioning_modes,
)
from cls.utils.dict_utils import dct_get, dct_put
from cls.plotWidgets.shape_restrictions import ROILimitObj, ROILimitDef
from cls.plotWidgets.color_def import (
    get_normal_clr,
    get_warn_clr,
    get_alarm_clr,
    get_normal_fill_pattern,
    get_warn_fill_pattern,
    get_alarm_fill_pattern,
)

from cls.utils.roi_dict_defs import *
from cls.utils.log import get_module_logger

MAX_SCAN_RANGE_FINEX = MAIN_OBJ.get_preset_as_float("max_fine_x")
MAX_SCAN_RANGE_FINEY = MAIN_OBJ.get_preset_as_float("max_fine_y")

_logger = get_module_logger(__name__)


class BasePointSpecScanParam(MultiRegionScanParamBase):
    def __init__(
        self, parent=None, main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__)
    ):
        super().__init__(main_obj=main_obj, data_io=data_io, dflts=dflts)
        self._parent = parent
        uic.loadUi(os.path.join(ui_path, "fine_point_scan.ui"), self)
        self.epu_supported = False
        self.goni_supported = False
        self.single_energy = False

        if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            self.goni_supported = True

        # instead of using centerx etc use startX
        self._multi_region_widget = MultiRegionWidget(
            use_center=False,
            is_point=True,
            enable_multi_spatial=self.enable_multi_region,
            single_ev_model=True,
            single_pol_model=True,
            max_range=MAX_SCAN_RANGE_FINEX,
            main_obj=self.main_obj,
            single_dwell=True
        )

        if not self.main_obj.is_device_supported("DNM_EPU_POLARIZATION"):
            self.multi_region_widget.deslect_all_polarizations()
            self.multi_region_widget.disable_polarization_table(True)
            self.multi_region_widget.set_polarization_table_visible(False)
        else:
            # more
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
        # self.hdwAccelDetailsBtn.clicked.connect(self.show_hdw_accel_details)
        self.pointSelBtn.clicked.connect(self.on_point_sel_btn)
        # self.singleEVChkBx.clicked.connect(self.on_single_energy)
        # self.sscan_class = SampleImageWithEnergySSCAN()
        # self.sscan_class = SampleImageWithE712Wavegen()

        self.wdg_com = None
        self.load_from_defaults()
        self.on_plugin_focus()
        self.init_loadscan_menu()

    def init_plugin(self):
        """
        set the plugin specific details to common attributes
        :return:
        """
        self.name = "Fine Point Scan"
        self.idx = self.main_obj.get_scan_panel_order(__file__)
        self.type = scan_types.SAMPLE_POINT_SPECTRUM
        self.data = {}
        self.section_id = "POINT"
        self.axis_strings = ["counts", "eV", "", ""]
        self.zp_focus_mode = zp_focus_modes.A0MOD
        # data_file_pfx = 'p'
        self.data_file_pfx = self.main_obj.get_datafile_prefix()
        self.plot_item_type = spatial_type_prefix.PNT
        self.enable_multi_region = self.main_obj.get_is_multi_region_enabled()
        self.multi_ev = True

        self._type_interactive_plot = True  # [scan_panel_order.POSITIONER_SCAN]
        self._type_skip_scan_q_table_plots = (
            False  # [scan_panel_order.OSA_FOCUS_SCAN, scan_panel_order.FOCUS_SCAN]
        )
        self._type_spectra_plot_type = (
            True  # [scan_panel_order.POINT_SCAN, scan_panel_order.POSITIONER_SCAN]
        )
        self._type_skip_centering_scans = (
            True  
        )
        # scan_panel_order.LINE_SCAN, scan_panel_order.POINT_SCAN, scan_panel_order.IMAGE_SCAN]
        self._type_do_recenter = False  # [scan_panel_order.IMAGE_SCAN, scan_panel_order.TOMOGRAPHY, scan_panel_order.LINE_SCAN]

        # self._help_html_fpath = os.path.join('interface', 'window_system', 'scan_plugins', 'detector.html')
        self._help_ttip = "Sample Fine point documentation and instructions"

    @property
    def multi_region_widget(self) -> MultiRegionWidget:
        return self._multi_region_widget

    def on_plugin_focus(self):
        """
        this is called when this scan param receives focus on the GUI
        - basically get the current EPU values and assign them to the multiregion widget
        :return:
        """
        if self.isEnabled():
            # call the standard init_base_values function for scan param widgets that contain a multiRegionWidget
            self.on_multiregion_widget_focus_init_base_values()
            self.multi_region_widget.resize_tableviews()

    def on_E712WavegenBtn(self, chkd):
        if chkd:
            # set the wave generator radio box's to enabled
            self.autoDDLRadBtn.setEnabled(True)
            self.reinitDDLRadBtn.setEnabled(True)
        else:
            # set the wave generator radio box's to disabled
            self.autoDDLRadBtn.setEnabled(False)
            self.reinitDDLRadBtn.setEnabled(False)

    def show_hdw_accel_details(self):
        dark = get_style()
        self.sscan_class.e712_wg.setStyleSheet(dark)
        self.sscan_class.e712_wg.show()

    def clear_params(self):
        """meant to clear all params from table"""
        self.multi_region_widget.clear_spatial_table()
        # pass

    # def gen_max_scan_range_limit_def(self):
    #     """ to be overridden by inheriting class
    #     """
    #     mtr_sx = self.main_obj.device('SampleX')
    #     mtr_sy = self.main_obj.device('SampleY')
    #
    #     xllm = mtr_sx.get_low_limit()
    #     xhlm = mtr_sx.get_high_limit()
    #     yllm = mtr_sy.get_low_limit()
    #     yhlm = mtr_sy.get_high_limit()
    #
    #     fxllm = 0.0 - (MAX_SCAN_RANGE_FINEX * 0.5)
    #     fxhlm = 0.0 + (MAX_SCAN_RANGE_FINEX * 0.5)
    #     fyllm = 0.0 - (MAX_SCAN_RANGE_FINEY * 0.5)
    #     fyhlm = 0.0 + (MAX_SCAN_RANGE_FINEY * 0.5)
    #
    #     bounding_qrect = QtCore.QRectF(QtCore.QPointF(xllm, yhlm), QtCore.QPointF(xhlm, yllm))
    #     warn_qrect = self.get_percentage_of_qrect(bounding_qrect, 0.95) #%95 of max
    #     alarm_qrect = self.get_percentage_of_qrect(bounding_qrect, 1.0) #%100 of max
    #
    #     bounding = ROILimitObj(bounding_qrect, get_alarm_clr(255), 'Point is beyond SampleXY Range', get_alarm_fill_pattern())
    #     normal = ROILimitObj(bounding_qrect, get_normal_clr(45), 'Point Scan', get_normal_fill_pattern())
    #     warn = ROILimitObj(warn_qrect, get_warn_clr(150), 'Point Scan, Nearing Limit of Sample X/Y Range', get_warn_fill_pattern())
    #     alarm = ROILimitObj(alarm_qrect, get_alarm_clr(255), 'Beyond Range of Sample X/Y', get_alarm_fill_pattern())
    #
    #     self.roi_limit_def = ROILimitDef(bounding, normal, warn, alarm)

    def gen_max_scan_range_limit_def(self):
        """this function only currently centers around 0,0, this is a problem because in order
        to indicate when the range of the scan is larger than the fine ranges it must be valid around
        whereever o,o is on the fine physical stage is, as this is nly generated and sent to teh plot
        widget at startup it doesnt work properly when the scan is not around 0,0.
        leaving this for future
        """

        # if (self.sample_positioning_mode == sample_positioning_modes.GONIOMETER):
        #     self.gen_GONI_SCAN_max_scan_range_limit_def()
        # else:
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

        self.set_spatial_scan_range((MAX_SCAN_RANGE_FINEX, MAX_SCAN_RANGE_FINEY))

        bounding_qrect = QtCore.QRectF(
            QtCore.QPointF(xllm, yhlm), QtCore.QPointF(xhlm, yllm)
        )

        # adjust the warn qrect by 0.1 in all directions so that a scan range of the exact size of the limit is still allowed
        warn_qrect = QtCore.QRectF(
            QtCore.QPointF(fxllm - 0.1, fyhlm + 0.1),
            QtCore.QPointF(fxhlm + 0.1, fyllm - 0.1),
        )
        alarm_qrect = self.get_percentage_of_qrect(warn_qrect, 0.99999)  # %99 of max
        bounding = ROILimitObj(
            bounding_qrect,
            get_alarm_clr(255),
            "Point is beyond SampleXY Range",
            get_warn_fill_pattern(),
        )
        normal = ROILimitObj(
            bounding_qrect, get_normal_clr(45), "Point Scan", get_normal_fill_pattern()
        )
        warn = ROILimitObj(
            warn_qrect,
            get_warn_clr(150),
            "Point Scan, Nearing Limit of Sample X/Y Range",
            get_warn_fill_pattern(),
        )
        alarm = ROILimitObj(
            alarm_qrect,
            get_alarm_clr(255),
            "Beyond Range of Sample X/Y",
            get_alarm_fill_pattern(),
        )
        self.roi_limit_def = ROILimitDef(bounding, normal, warn, alarm)

    def set_roi(self, roi):
        """
        set_roi standard function supported by all scan pluggins to initialize the GUI for this scan with values
        stored in the defaults library

        :param roi: is a standard dict returned from the call to DEFAULTS.get_defaults()
        :type roi: dict.

        :returns: None

        """
        (cx, cy, cz, c0) = roi[CENTER]
        (rx, ry, rz, s0) = roi[RANGE]
        (nx, ny, nz, n0) = roi[NPOINTS]
        (sx, sy, sz, s0) = roi[STEP]
        # dwell = roi[DWELL]

        # self.centerXFld.setText(str('%.2f' % cx))
        # self.centerYFld.setText(str('%.2f' % cy))

    def mod_roi(self, wdg_com, do_recalc=True, sp_only=False):
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
        # if(self.wdg_com is None):
        #    import copy
        #    self.wdg_com = copy(wdg_com)

        if wdg_com[CMND] == widget_com_cmnd_types.LOAD_SCAN:
            self.load_roi(wdg_com)
            return

        if wdg_com[CMND] == widget_com_cmnd_types.ROI_CHANGED:
            # we are being modified by the plotter
            item_id = dct_get(wdg_com, SPDB_PLOT_ITEM_ID)
            cur_scan = self.multi_region_widget.sp_widg.get_row_data_by_item_id(item_id)
            sx = wdg_com[SPDB_X][START]
            sy = wdg_com[SPDB_Y][START]
            ex = wdg_com[SPDB_X][STOP]
            ey = wdg_com[SPDB_Y][STOP]
            nx = wdg_com[SPDB_X][NPOINTS]
            ny = wdg_com[SPDB_Y][NPOINTS]
            if None in [sx, sy, ex, ey, nx, ny]:
                _logger.error("wdg_com roi had Nones")
                return
            if cur_scan is None:
                # ADD_ROI
                # x_roi = get_base_roi(SPDB_X, 'SampleX', cx, 0, 1, stepSize=None, max_scan_range=None, enable=True, is_point=True)
                # y_roi = get_base_roi(SPDB_Y, 'SampleY', cy, 0, 1, stepSize=None, max_scan_range=None, enable=True, is_point=True)

                x_roi = get_base_start_stop_roi(
                    SPDB_X, "DNM_SAMPLE_X", sx, ex, 1, is_point=True
                )
                y_roi = get_base_start_stop_roi(
                    SPDB_Y, "DNM_SAMPLE_Y", sy, ey, 1, is_point=True
                )

                scan = make_spatial_db_dict(sp_id=item_id, x_roi=x_roi, y_roi=y_roi)
                scan[SPDB_ID_VAL] = item_id
                self.multi_region_widget.sp_widg.on_new_region(scan)
                # self.multi_region_widget.sp_widg.select_row(item_id=item_id)

            else:
                # update the center and range fields that have come from the plotter
                cur_scan[SPDB_X][START] = sx
                on_start_changed(cur_scan[SPDB_X])
                cur_scan[SPDB_X][STOP] = ex
                on_stop_changed(cur_scan[SPDB_X])

                cur_scan[SPDB_Y][START] = sy
                on_start_changed(cur_scan[SPDB_Y])
                cur_scan[SPDB_Y][STOP] = ey
                on_stop_changed(cur_scan[SPDB_Y])

                self.multi_region_widget.sp_widg.select_row(item_id=item_id)
                self.multi_region_widget.sp_widg.modify_row_data(item_id, cur_scan)

        elif wdg_com[CMND] == widget_com_cmnd_types.DEL_ROI:
            # remove this roi from the multi region spatial table
            item_id = dct_get(wdg_com, SPDB_PLOT_ITEM_ID)
            self.multi_region_widget.sp_widg.delete_row(item_id)

        elif wdg_com[CMND] == widget_com_cmnd_types.ADD_ROI:
            pass
        elif wdg_com[CMND] == widget_com_cmnd_types.SELECT_ROI:
            item_id = dct_get(wdg_com, SPDB_PLOT_ITEM_ID)
            self.multi_region_widget.select_spatial_row(item_id)

        elif wdg_com[CMND] == widget_com_cmnd_types.DESELECT_ROI:
            self.multi_region_widget.sp_widg.deselect_all()

        else:
            # we are
            print(
                "point_scan: mod_roi: unsupported widget_com CMND [%d]" % wdg_com[CMND]
            )
            return

    def load_roi(self, wdg_com, append=False, ev_only=False, sp_only=False):
        """
        take a widget communications dict and load the plugin GUI with the spatial region, also
        set the scan subtype selection pulldown for point by point or line
        """
        # wdg_com = dct_get(ado_obj, ADO_CFG_WDG_COM)
        if wdg_com[CMND] == widget_com_cmnd_types.LOAD_SCAN:
            sp_db = get_first_sp_db_from_wdg_com(wdg_com)

            if not ev_only and (
                dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)
                != scan_types.SAMPLE_POINT_SPECTRUM
            ):
                return

            self.multi_region_widget.load_scan(
                wdg_com, append, ev_only=ev_only, sp_only=sp_only
            )
            # emit roi_changed so that the plotter can be signalled to create the ROI shape items
            if not self.multi_region_widget.is_spatial_list_empty():
                self.roi_changed.emit(wdg_com)

    def on_spatial_row_selected(self, wdg_com):
        """
        :param wdg_com: is a standard dict returned from the call to sm.stxm_control.stxm_utils.roi_utils.make_spatial_db_dict()
        :type wdg_com: dict.

        :returns: None

        """
        wdg_com[CMND] = widget_com_cmnd_types.SELECT_ROI
        dct_put(wdg_com, SPDB_PLOT_SHAPE_TYPE, self.plot_item_type)
        self.roi_changed.emit(wdg_com)

    def on_single_energy(self, val):
        self.single_energy = val

    #         if(not val):
    #             pass
    #         else:
    #             self.ev_select_widget.on_single_ev()
    #        self.update_data()

    #     def update_data(self):
    #         """
    #         This is a standard function that all scan pluggins have that is called to
    #         get the data from the pluggins UI widgets and write them into a dict returned by
    #         get_base_scanparam_roi(), this dict is emitted by all scan pluggins to be used by
    #         the scan classes configure() functions
    #
    #         :returns: None
    #
    #         """
    #         wdg_com = self.update_multi_spatial_wdg_com()
    #         self.roi_changed.emit(wdg_com)
    #         return(wdg_com)

    def update_data(self):
        """
        This is a standard function that all scan pluggins have that is called to
        get the data from the pluggins UI widgets and write them into a dict returned by
        get_base_scanparam_roi(), this dict is emitted by all scan pluggins to be used by
        the scan classes configure() functions

        :returns: None

        """

        if self.sample_positioning_mode == sample_positioning_modes.GONIOMETER:
            self.wdg_com = self.GONI_SCAN_update_data()
        else:
            self.wdg_com = self.update_multi_spatial_wdg_com()

        # NEED TO MAKE SURE THAT THE SUB SPATIAL TYPE IS SET HERE FOR ALL
        self.set_spatial_sub_type(self.wdg_com)

        self.roi_changed.emit(self.wdg_com)
        return self.wdg_com

    def set_spatial_sub_type(self, wdg_com):
        """
        Ensure that all spatial ROI's have there sub spatial types set to POINT_BY_POINT

        :returns: None

        """
        sp_rois = dct_get(wdg_com, SPDB_SPATIAL_ROIS)
        for sp_id, sp_db in sp_rois.items():
            # make them all pxp
            dct_put(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE, scan_sub_types.POINT_BY_POINT)

        dct_put(wdg_com, SPDB_SCAN_PLUGIN_SUBTYPE, scan_sub_types.POINT_BY_POINT)
        return wdg_com

    def GONI_SCAN_update_data(self):
        """
        This is a standard function that all scan pluggins have that is called to
        get the data from the pluggins UI widgets and write them into a dict returned by
        get_base_scanparam_roi(), this dict is emitted by all scan pluggins to be used by
        the scan classes configure() functions

        :returns: None

        """
        wdg_com = self.update_multi_spatial_wdg_com()
        sub_spatials = self.create_sub_spatial_dbs(wdg_com)
        if sub_spatials:
            # for now only support single spatial with multi sub spatial
            sp_id = list(sub_spatials.keys())[0]
            sp_db = dct_get(wdg_com, SPDB_SPATIAL_ROIS)[sp_id]

            # added E712 waveform generator support
            dct_put(sp_db, SPDB_HDW_ACCEL_USE, self.useE712WavegenBtn.isChecked())
            dct_put(sp_db, SPDB_HDW_ACCEL_AUTO_DDL, self.autoDDLRadBtn.isChecked())
            dct_put(sp_db, SPDB_HDW_ACCEL_REINIT_DDL, self.reinitDDLRadBtn.isChecked())

        return wdg_com

    def create_sub_spatial_dbs(self, wdg_com):
        """
        Given a set of spatial region dbs, subdivide them into spatial regions that are within the scan range of the
        Zoneplate X and Y, each sub spatial region represents the area that can be scanned when the OSA XY is positioned at the regions center.
        If the desired scan area is smaller than the max subscan range then just return the original spatial region

        This function creates a dict of sub spatial regions as well, the OSA XY position for each sub spatial region can be
        taken from (x_roi[CENTER], y_roi[CENTER])

        :returns: None

        """
        sub_spatials = {}
        sp_dbs = dct_get(wdg_com, WDGCOM_SPATIAL_ROIS)

        for sp_id in sp_dbs:
            sp_db = sp_dbs[sp_id]
            sp_db = self.modify_sp_db_for_goni(sp_db)

        return None
