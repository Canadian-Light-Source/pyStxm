"""
@author: bergr
"""
from PyQt5 import uic, QtCore
import os
from cls.applications.pyStxm.main_obj_init import MAIN_OBJ, DEFAULTS
from cls.scanning.base import ScanParamWidget
from cls.types.stxmTypes import scan_sub_types
from cls.data_io.stxm_data_io import STXMDataIo

from cls.applications.pyStxm.widgets.scan_table_view.multiRegionWidget import (
    MultiRegionWidget,
)
from cls.utils.roi_utils import (
    set_use_start,
    get_base_roi,
    get_base_energy_roi,
    make_spatial_db_dict,
    on_fixed_start_changed,
    on_range_changed,
    get_first_sp_db_from_wdg_com,
    widget_com_cmnd_types,
)
from cls.types.stxmTypes import scan_types, spatial_type_prefix
from cls.utils.roi_dict_defs import *
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.log import get_module_logger

_logger = get_module_logger(__name__)



class BaseTwoVariableScanParam(ScanParamWidget):

    data = {}

    def __init__(
        self, parent=None, main_obj=MAIN_OBJ, data_io=STXMDataIo, dflts=DEFAULTS, ui_path=os.path.dirname(__file__)
    ):
        super().__init__(main_obj=main_obj, data_io=data_io, dflts=dflts, ui_path=os.path.dirname(__file__))
        self._parent = parent
        uic.loadUi(os.path.join(ui_path, "two_variable_scan.ui"), self)
        self.loadScanBtn.clicked.connect(self.load_scan)
        # self.posnerComboBox.currentIndexChanged.connect(self.positioner_changed)

        self.scan_class = self.instanciate_scan_class(__file__, "TwoVariableScan", "TwoVariableScanClass")
        self.var_dct = {}
        self.populate_variable_cbox()

        self.loadScanBtn.clicked.connect(self.load_scan)

        self.prim_positioner = None
        self.sec_positioner = None
        self.prim_units = None
        self.sec_units = None


        # not inheriting two_variable scans from other bl_configs will for sure support multi ev
        if hasattr(self, 'evGrpBox'):
            self.multi_region_widget = MultiRegionWidget(
                enable_multi_spatial=False,
                single_ev_model=True,
                single_pol_model=True,
                # max_range=MAX_SCAN_RANGE_FINEX,
                min_sp_rois=1,
                x_cntr=0.0,
                y_cntr=0.0,
                main_obj=self.main_obj,
                show_sp=False,
                show_ev=False,
            )

            self.epu_supported = True
            self.multi_region_widget.deslect_all_polarizations()
            self.multi_region_widget.disable_polarization_table(False)
            self.multi_region_widget.set_polarization_table_visible(True)

            # self.multi_region_widget = MultiRegionWidget(enable_multi_spatial=self.enable_multi_region, max_range=MAX_SCAN_RANGE_FINEX)
            self.multi_region_widget.spatial_row_selected.connect(
                self.on_spatial_row_selected
            )
            self.multi_region_widget.spatial_row_changed.connect(
                self.on_spatial_row_changed
            )
            self.multi_region_widget.spatial_row_deleted.connect(
                self.on_spatial_row_deleted
            )
            self.multi_region_widget.spatial_row_added.connect(self.on_spatial_row_changed)

            self.center_plot_on_focus = True

            self.evGrpBox.layout().addWidget(self.multi_region_widget)
            self.evGrpBox.layout().update()

            self.loadScanBtn.clicked.connect(self.load_scan)
            if hasattr(self, 'catComboBox'):
                self.catComboBox.currentIndexChanged.connect(self.category_changed)
            if hasattr(self, 'createROIBtn'):
                self.createROIBtn.clicked.connect(self.on_create_roi_btn)

        self.primVarComboBox.currentIndexChanged.connect(self.prim_variable_changed)
        self.secVarComboBox.currentIndexChanged.connect(self.sec_variable_changed)
        self.sp_db = None
        self.load_from_defaults()
        self.init_sp_db()
        self.connect_paramfield_signals()
        #self.on_single_spatial_npoints_changed()
        self.init_loadscan_menu()

    def init_plugin(self):
        """
        set the plugin specific details to common attributes
        :return:
        """
        self.name = "Two Variable Scan"
        self.idx = self.main_obj.get_scan_panel_order(__file__)
        self.type = scan_types.TWO_VARIABLE_IMAGE
        self.section_id = "TWO_VARIABLE_SCAN"
        # devices = self.main_obj.get_devices_in_category("POSITIONERS")
        # var_keys = list(devices['POSITIONERS'].keys())
        # var_keys = list(devices.keys())
        # var_keys.sort()
        # self.axis_strings = ["Detector Counts", "%s microns" % var_keys[0], "", ""]
        # use the mode that adjusts the zoneplate by calculating the zpz using the A0 mod
        # self.zp_focus_mode = zp_focus_modes.A0MOD
        self.data_file_pfx = self.main_obj.get_datafile_prefix()
        self.plot_item_type = spatial_type_prefix.ROI

        self._type_interactive_plot = False  # [scan_panel_order.POSITIONER_SCAN]
        self._type_skip_scan_q_table_plots = (
            False  # [scan_panel_order.OSA_FOCUS_SCAN, scan_panel_order.FOCUS_SCAN]
        )
        self._type_spectra_plot_type = (
            False
        )
        self._type_skip_centering_scans = (
            False  # [scan_panel_order.FOCUS_SCAN, scan_panel_order.TOMOGRAPHY,
        )
        # scan_panel_order.LINE_SCAN, scan_panel_order.POINT_SCAN, scan_panel_order.IMAGE_SCAN]
        self._type_do_recenter = False  # [scan_panel_order.IMAGE_SCAN, scan_panel_order.TOMOGRAPHY, scan_panel_order.LINE_SCAN]

        self._help_ttip = "Positioner scan documentation and instructions"

    def on_plugin_focus(self):
        """
        This is a function that is called when the plugin first receives focus from the main GUI
        :return:
        """
        if self.isEnabled():
            pass

    def on_plugin_defocus(self):
        """
        This is a function that is called when the plugin leaves focus from the main GUI
        :return:
        """
        if self.isEnabled():
            pass

        # call the base class defocus
        super().on_plugin_defocus()

    def get_selected_dev_name_and_units(self, primary='primary', idx=None):
        """
        get the name and units for the currently selected primary motor
        """
        if primary == 'primary':
            dev = self.var_dct[self.primVarComboBox.currentIndex()]['dev']
            var_dct = self.var_dct[self.primVarComboBox.currentIndex()]
        else:
            if idx:
                if idx == -1:
                    idx = 0
                dev = self.var_dct[idx]['dev']
                var_dct = self.var_dct[idx]
            else:
                dev = self.var_dct[self.secVarComboBox.currentIndex()]['dev']
                var_dct = self.var_dct[self.secVarComboBox.currentIndex()]

        posner_name = var_dct['name']
        units = 'um'
        if hasattr(dev, 'get_units'):
            units = dev.get_units()
        return dev, posner_name, units

    def connect_paramfield_signals(self):
        """
        connect fields to signals
        """

        primary_variable = self.var_dct[self.primVarComboBox.currentIndex()]['dev']
        secondary_variable = self.var_dct[self.secVarComboBox.currentIndex()]['dev']

        self.prim_positioner = self.var_dct[self.primVarComboBox.currentIndex()]['name']
        self.sec_positioner = self.var_dct[self.secVarComboBox.currentIndex()]['name']

        xllm = primary_variable.get_low_limit()
        xhlm = primary_variable.get_high_limit()
        yllm = secondary_variable.get_low_limit()
        yhlm = secondary_variable.get_high_limit()

        rx = xhlm - xllm
        ry = yhlm - yllm

        lim_dct = {}
        lim_dct["X"] = {"llm": xllm, "hlm": xhlm, "rng": rx}
        lim_dct["Y"] = {"llm": yllm, "hlm": yhlm, "rng": ry}
        args = {}
        args['on_range_changed_use_start'] = True
        self.connect_param_flds_to_validator(lim_dct, args)

    def init_sp_db(self):
        """
        init_sp_db standard function supported by all scan pluggins to initialize the local widget_com dict to whatever the
        GUI is currently displaying, this is usually called after the call to self.load_from_defaults()

        :returns: None

        """
        # idx = self.primVarComboBox.currentIndex()
        # var_dct = self.var_dct[idx]
        # x_mtr_name = var_dct['name']
        # self.primary_positioner = str(self.primVarComboBox.itemText(idx))
        #
        # idx = self.secVarComboBox.currentIndex()
        # self.secondary_positioner = str(self.secVarComboBox.itemText(idx))
        # var_dct = self.var_dct[idx]
        # y_mtr_name = var_dct['name']

        x_dev, x_mtr_name, x_units = self.get_selected_dev_name_and_units('primary')
        y_dev, y_mtr_name, y_units = self.get_selected_dev_name_and_units('secondary')

        startx = float(str(self.startXFld.text()))
        stopx = float(str(self.endXFld.text()))
        dwell = float(str(self.dwellFld.text()))
        nx = int(str(self.npointsXFld.text()))
        sx = float(str(self.stepXFld.text()))

        starty = float(str(self.startYFld.text()))
        stopy = float(str(self.endYFld.text()))
        ny = int(str(self.npointsYFld.text()))
        sy = float(str(self.stepYFld.text()))

        # now create the model that this pluggin will use to record its params
        cx = (startx + stopx) * 0.5
        rx = stopx - startx
        cy = (starty + stopy) * 0.5
        ry = stopy - starty

        x_roi = get_base_roi(SPDB_X, x_mtr_name, cx, rx, nx, sx)
        y_roi = get_base_roi(SPDB_Y, y_mtr_name, cy, ry, ny, sy)
        z_roi = get_base_roi(SPDB_Z, "None", 0, 0, 0, enable=False)

        # force range changes to obet whatever START is currently set to
        set_use_start(x_roi)
        set_use_start(y_roi)

        energy_pos = self.main_obj.device("DNM_ENERGY").get_position()
        e_roi = get_base_energy_roi(
            "EV", "DNM_ENERGY", energy_pos, energy_pos, 0, 1, dwell, None, enable=False
        )

        self.sp_db = make_spatial_db_dict(
            x_roi=x_roi, y_roi=y_roi, z_roi=z_roi, e_roi=e_roi
        )

    def on_create_roi_btn(self, chkd):
        """
        when pressed this activates the clsSelectPositionTool in the plotter
        calls the parent (stxmMain) to tell the plotter to activate/deactivate the
        clsSelectPositionTool and to connect the plotters 'new_selected_position' signal to our handler
        """
        if chkd:
            self.createROIBtn.setText("Press to complete current ROI")
            self._parent.activate_create_roi_tool(True, self.on_new_roi_created)

        else:
            self.createROIBtn.setText("Press to create ROI")
            self._parent.activate_create_roi_tool(False, self.on_new_roi_created)

    def on_new_roi_created(self):
        pass

    def check_scan_limits(self):
        """a function to be implemented by the scan pluggin that
        checks the scan parameters against the soft limits of the
        positioners, if all is well return true else false

        This function should provide an explicit error log msg to aide the user
        """
        return True
        # ret = False
        # if len(self.positioner) > 0:
        #     ret = self.check_start_stop_x_scan_limits(self.positioner)
        # return ret

    def generate_display_name(self, name):
        """
        take the name of the motor (typically DNM_ENERGY etc) and return a standard display name
        """
        dev_display_name = name.replace("DNM_", "")
        dev_display_name = dev_display_name.replace("___", " ")
        dev_display_name = dev_display_name.replace("__", " ")
        dev_display_name = dev_display_name.replace("_", " ")
        return dev_display_name

    def populate_variable_cbox(self, category='ALL', primary_selected_motor=''):
        """
        populate the primary and secondary motor combo box's
        this function can be called with the name of the selected primary motor, this will be used to skip adding that
        motor to the secondary list thereby guard railing the user into not selecting ht esame motor for both primary and
        secondary
        """
        valid_categories = ['PVS', 'POSITIONERS', "All"]
        devices = {}
        if category in valid_categories:
            self.primVarComboBox.clear()
            self.secVarComboBox.clear()
            if category in ["PVS", "All"]:
                devices.update(self.main_obj.get_devices_in_category("PVS"))
            # devices = self.main_obj.get_devices()
            idx = 0
            keys = list(devices.keys())
            keys.sort()
            for var in keys:
                dev_display_name = self.generate_display_name(var)
                self.primVarComboBox.addItem(dev_display_name)
                self.var_dct[idx] = {'name': var, 'dev': devices[var]}
                idx += 1
                if primary_selected_motor != dev_display_name:
                    # skip this dev name because it is already selected as the primary
                    self.secVarComboBox.addItem(dev_display_name)
                else:
                    # add it but disabled
                    self.secVarComboBox.addItem(dev_display_name)
                    index = self.secVarComboBox.findText(dev_display_name)
                    model = self.secVarComboBox.model()
                    item = model.item(index)  # Access the second item (index 1)
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)  # Disable the item

            # set default selections of first and second motors for primary and secondary
            self.primVarComboBox.setCurrentIndex(0)
            self.prim_variable_changed(0)
            self.secVarComboBox.setCurrentIndex(1)
            self.prim_variable_changed(0)
            self.sec_variable_changed(1)
            var_dct_mtr_x = self.var_dct[0]
            var_dct_mtr_y = self.var_dct[1]
            var = var_dct_mtr_x['name']
            self.axis_strings = ["Detector Counts", f"{var} microns", "", ""]
        else:
            _logger.error(f"Category [{category}] is not supported")

    def category_changed(self, idx):
        """
        this handler is called when the lenscomboBox changes selection
        """
        category_str = str(self.catComboBox.currentText())
        self.primVarComboBox.blockSignals(True)
        self.secVarComboBox.blockSignals(True)
        self.populate_variable_cbox(category_str)
        self.primVarComboBox.blockSignals(False)
        self.secVarComboBox.blockSignals(False)
        self.prim_variable_changed(0)

    def prim_variable_changed(self, idx):
        """
        this handler is called when the primary comboBox changes selection
        """
        x_dev, x_mtr_name, x_units = self.get_selected_dev_name_and_units('primary')
        y_dev, y_mtr_name, y_units = self.get_selected_dev_name_and_units('secondary')

        # only update the X positioner in sp_db
        # check first because self.sp_db might not be created yet
        if hasattr(self, 'sp_db'):
            if self.sp_db:
                self.prim_positioner = x_mtr_name
                # use current position of selected positioner as new start
                fbk = float(x_dev.get())
                self.startXFld.setText(f"{fbk:.3f}")
                self.sp_db[SPDB_X][START] = fbk
                # recalc X roi
                on_fixed_start_changed(self.sp_db[SPDB_X])
                self.endXFld.setText(f"{self.sp_db[SPDB_X][STOP]:.3f}")
                self.sp_db[SPDB_X][POSITIONER] = x_mtr_name
                self.axis_strings = [f"{y_dev.name} {y_units}", f"{x_dev.name} {x_units}", "", ""]
                self.update_plot_strs.emit(self.axis_strings)

        # update secondary combobox to not show the primary motor
        self.populate_secondary_variable_cbox(primary_selected_motor=x_mtr_name)
        # might need to call mod_roi to update the fields
        self.connect_paramfield_signals()

    def populate_secondary_variable_cbox(self, category='POSITIONERS', primary_selected_motor=''):
        """
        populate the primary and secondary motor combo box's
        this function can be called with the name of the selected primary motor, this will be used to skip adding that
        motor to the secondary list thereby guard railing the user into not selecting ht esame motor for both primary and
        secondary
        """
        primary_selected_motor = self.generate_display_name(primary_selected_motor)
        devices = self.main_obj.get_devices_in_category("POSITIONERS")
        self.secVarComboBox.blockSignals(True)
        self.secVarComboBox.clear()
        self.secVarComboBox.blockSignals(False)
        idx = 0
        keys = list(devices.keys())
        keys.sort()
        # load both Primary and Secondary with positioner names
        for var in keys:
            dev_display_name = self.generate_display_name(var)
            #self.var_dct[idx] = {'name': var, 'dev': devices[var]}
            idx += 1
            if primary_selected_motor != dev_display_name:
                # skip this dev name because it is already selected as the primary
                self.secVarComboBox.addItem(dev_display_name)
            else:
                # add this dev name then disable it because it is already selected as the primary
                # add it but disabled
                self.secVarComboBox.addItem(dev_display_name)
                index = self.secVarComboBox.findText(dev_display_name)
                model = self.secVarComboBox.model()
                item = model.item(index)  # Access the second item (index 1)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)  # Disable the item

        self.secVarComboBox.setCurrentIndex(0)
        self.sec_variable_changed(0)
        x_dev, x_mtr_name, x_units = self.get_selected_dev_name_and_units('primary')
        y_dev, y_mtr_name, y_units = self.get_selected_dev_name_and_units('secondary')
        self.axis_strings = [f"{y_dev.name} {y_units}", f"{x_dev.name} {x_units}", "", ""]
        self.update_plot_strs.emit(self.axis_strings)

    def sec_variable_changed(self, idx):
        """
        this handler is called when the secondary comboBox changes selection
        """
        x_dev, x_mtr_name, x_units = self.get_selected_dev_name_and_units('primary')
        y_dev, y_mtr_name, y_units = self.get_selected_dev_name_and_units('secondary', idx=idx)

        # only update the Y positioner in sp_db
        # check first because self.sp_db might not be created yet
        if hasattr(self, 'sp_db'):
            if self.sp_db:
                self.sec_positioner = y_mtr_name
                # use current position of selected positioner as new start
                fbk = float(y_dev.get())
                self.startYFld.setText(f"{fbk:.3f}")
                self.sp_db[SPDB_Y][START] = fbk
                # recalc Y roi
                on_fixed_start_changed(self.sp_db[SPDB_Y])
                self.endYFld.setText(f"{self.sp_db[SPDB_Y][STOP]:.3f}")
                self.sp_db[SPDB_Y][POSITIONER] = y_mtr_name
                self.axis_strings = [f"{y_dev.name} {y_units}", f"{x_dev.name} {x_units}", "", ""]
                self.update_plot_strs.emit(self.axis_strings)

        self.connect_paramfield_signals()

    def set_dwell(self, dwell):
        self.set_parm(self.dwellFld, dwell)
        self.update_data()

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

        if "DWELL" in roi:
            self.set_parm(self.dwellFld, roi[DWELL])

        self.set_parm(self.startXFld, cx)
        self.set_parm(self.endXFld, rx)


        if nx != None:
            self.set_parm(self.npointsXFld, nx, type="int", floor=2)
        # if ny != None:
        #     self.set_parm(self.npointsYFld, nx, type="int", floor=2)

        if sx != None:
            self.set_parm(self.stepXFld, sx, type="float", floor=0)
        # if sy != None:
        #     self.set_parm(self.stepYFld, sx, type="float", floor=0)

    def mod_roi(self, sp_db, do_recalc=True, sp_only=True):
        """
        sp_db is a widget_com dict
        The purpose of the mod_roi() function is to update the fields in the GUI with the correct values
        it can be called by either a signal from one of the edit fields (ex: self.startXFld) or
        by a signal from a plotter (via the main gui that is connected to the plotter) so that as a user
        grabs a region of interest marker in the plot and either moves or resizes it, those new center and size
        values will be delivered here and,  if required, the stepsizes will be recalculated


        :param sp_db: is a standard dict returned from the call to sm.stxm_control.stxm_utils.roi_utils.make_spatial_db_dict()
        :type sp_db: dict.

        :param do_recalc: selectively the STEP of the ROI's for X and Y can be recalculated if the number of points or range have changed
        :type do_recalc: flag.

        :returns: None

        """
        self.sp_db[SPDB_X][START] = sp_db[SPDB_X][START]
        self.sp_db[SPDB_X][STOP] = sp_db[SPDB_X][STOP]
        self.sp_db[SPDB_Y][START] = sp_db[SPDB_Y][START]
        self.sp_db[SPDB_Y][STOP] = sp_db[SPDB_Y][STOP]

        x_roi = self.sp_db[SPDB_X]
        y_roi = self.sp_db[SPDB_Y]
        e_rois = self.sp_db[SPDB_EV_ROIS]

        if do_recalc:
            on_range_changed(x_roi)
            on_range_changed(y_roi)

        self.set_parm(self.startXFld, x_roi[START])
        self.set_parm(self.endXFld, x_roi[STOP])

        self.set_parm(self.startYFld, y_roi[START])
        self.set_parm(self.endYFld, y_roi[STOP])

        if e_rois[0][DWELL] != None:
            self.set_parm(self.dwellFld, e_rois[0][DWELL])

        if x_roi[NPOINTS] != None:
            self.set_parm(self.npointsXFld, x_roi[NPOINTS], type="int", floor=2)
        if y_roi[NPOINTS] != None:
            self.set_parm(self.npointsYFld, y_roi[NPOINTS], type="int", floor=2)

        if x_roi[STEP] != None:
            self.set_parm(self.stepXFld, x_roi[STEP], type="float", floor=0)
        if y_roi[STEP] != None:
            self.set_parm(self.stepYFld, y_roi[STEP], type="float", floor=0)

    def load_roi(self, wdg_com, append=False, sp_only=False, ev_only=False):
        """
        take a widget communications dict and load the plugin GUI with the spatial region, also
        set the scan subtype selection pulldown for point by point or line
        """

        # wdg_com = dct_get(ado_obj, ADO_CFG_WDG_COM)

        if wdg_com[WDGCOM_CMND] == widget_com_cmnd_types.LOAD_SCAN:
            sp_db = get_first_sp_db_from_wdg_com(wdg_com)
            x_positioner = sp_db[SPDB_X][POSITIONER]
            y_positioner = sp_db[SPDB_Y][POSITIONER]

            if dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) != self.type:
                return

            self.mod_roi(sp_db, do_recalc=False)

            idx = self.var_dct[x_positioner]
            self.primVarComboBox.setCurrentIndex(idx)

            idx = self.var_dct[y_positioner]
            self.secVarComboBox.setCurrentIndex(idx)

    def update_last_settings(self):
        """update the 'default' settings that will be reloaded when this scan pluggin is selected again"""

        x_roi = self.sp_db[SPDB_X]
        y_roi = self.sp_db[SPDB_Y]
        e_rois = self.sp_db[SPDB_EV_ROIS]

        DEFAULTS.set("SCAN.TWO_VARIABLE.DWELL", e_rois[0][DWELL])
        DEFAULTS.set("SCAN.TWO_VARIABLE.CENTER", (x_roi[START],y_roi[START], 0, 0))
        DEFAULTS.set("SCAN.TWO_VARIABLE.RANGE", (x_roi[STOP], y_roi[STOP], 0, 0))
        DEFAULTS.set("SCAN.TWO_VARIABLE.NPOINTS", (x_roi[NPOINTS], y_roi[NPOINTS], 0, 0))
        DEFAULTS.set("SCAN.TWO_VARIABLE.STEP", (x_roi[STEP], y_roi[STEP], 0, 0))

        DEFAULTS.update()

    def update_data(self):
        """
        This is a standard function that all scan pluggins have that is called to
        get the data from the pluggins UI widgets and write them into a dict returned by
        get_base_scanparam_roi(), this dict is emitted by all scan pluggins to be used by
        the scan classes configure() functions

        :returns: None

        """
        wdg_com = self.update_single_spatial_wdg_com(positioner=self.prim_positioner)
        self.sub_type = scan_sub_types.POINT_BY_POINT
        dct_put(wdg_com, SPDB_SCAN_PLUGIN_TYPE, self.type)
        dct_put(wdg_com, SPDB_SCAN_PLUGIN_SUBTYPE, self.sub_type)  # default
        self.update_est_time()
        self.update_last_settings()

        return wdg_com
