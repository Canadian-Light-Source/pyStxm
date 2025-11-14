"""
Created on May 30, 2018

@author: bergr
"""
import json
import os

from PyQt5 import QtWidgets
from PyQt5 import uic

from cls.applications.pyStxm.main_obj_init import MAIN_OBJ
from cls.devWidgets.ophydLabelWidget import assign_aiLabelWidget
from cls.appWidgets.basePreference import BasePreference
from cls.utils.log import get_module_logger

widgetsUiDir = os.path.join(os.path.dirname(os.path.abspath(__file__)))

_logger = get_module_logger(__name__)
def focal_length(energy, a1):
    """
    f = A1 * E
    """
    f = a1 * energy

    return f


class FocusParams(BasePreference):
    def __init__(self, name="FocusParams", parent=None):
        super(FocusParams, self).__init__(name, parent)
        self._parent = parent
        uic.loadUi(os.path.join(widgetsUiDir, "focusAndZoneplateParms.ui"), self)

        # reassign the QLabels to be attached to pvs to update when their values change
        #if MAIN_OBJ.device("DNM_ENERGY_RBV"):
        if MAIN_OBJ.device("DNM_ENERGY"):
            self.evFbkLbl = assign_aiLabelWidget(
                self.evFbkLbl,
                MAIN_OBJ.device("DNM_ENERGY"),
                hdrText="Energy",
                egu="eV",
                title_color="white",
                var_clr="white",
            )
        else:
            self.evFbkLbl.setText("No Energy Feedback Device in database")

        if MAIN_OBJ.device("DNM_ZP_DEF_A"):
            self.a1FbkLbl = assign_aiLabelWidget(
                self.a1FbkLbl,
                MAIN_OBJ.device("DNM_ZP_DEF_A"),
                hdrText="A1",
                egu="",
                title_color="white",
                var_clr="white",
                format="%5.4f",
            )
        else:
            self.a1FbkLbl.setText("No DNM_ZP_DEF_A Device in database")

        if MAIN_OBJ.device("DNM_A0MAX"):
            self.a0MaxFbkLbl = assign_aiLabelWidget(
                self.a0MaxFbkLbl,
                MAIN_OBJ.device("DNM_A0MAX"),
                hdrText="A0Max",
                egu="um",
                title_color="white",
                var_clr="white",
                format="%5.2f",
            )
        else:
            self.a0MaxFbkLbl.setText("No DNM_A0MAX Device in database")


        self.flFbkLbl = assign_aiLabelWidget(
            self.flFbkLbl,
            MAIN_OBJ.device("DNM_FOCAL_LENGTH"),
            hdrText="Fl",
            egu="um",
            title_color="white",
            var_clr="white",
            format="%5.2f",
        )

        if MAIN_OBJ.device("DNM_IDEAL_A0"):
            self.sampleZFbkLbl = assign_aiLabelWidget(
                self.sampleZFbkLbl,
                MAIN_OBJ.device("DNM_IDEAL_A0"),
                hdrText="Cz",
                egu="um",
                title_color="white",
                var_clr="white",
                format="%5.2f",
            )
        else:
            self.sampleZFbkLbl.setText("No DNM_IDEAL_A0 Device in database")

        #if MAIN_OBJ.device("DNM_ZPZ_RBV"):
        if MAIN_OBJ.device("DNM_ZONEPLATE_Z"):
            self.zpzFbkLbl = assign_aiLabelWidget(
                self.zpzFbkLbl,
                MAIN_OBJ.device("DNM_ZONEPLATE_Z"),
                hdrText="Zpz",
                egu="um",
                title_color="white",
                var_clr="white",
                format="%5.2f",
            )
        else:
            self.zpzFbkLbl.setText("No DNM_ZPZ_RBV Device in database")

        self.a0Fld.returnPressed.connect(self.on_a0_changed)

        if MAIN_OBJ.device("DNM_ENERGY"):
            #self.energy_fbk = MAIN_OBJ.device("DNM_ENERGY_RBV")
            self.energy_fbk = MAIN_OBJ.device("DNM_ENERGY")
            self.energy_fbk.changed.connect(self.update_fl_label)
        else:
            self.energy_fbk = 0

        self.zpToolBox = QtWidgets.QToolBox()
        self.osaToolBox = QtWidgets.QToolBox()

        self.zp_tbox_widgets = []
        self.osa_tbox_widgets = []

        self._cur_sel_zp_def = {}

        zp_defs = MAIN_OBJ.get_preset_section("ZP_DEFS")
        osa_defs = MAIN_OBJ.get_preset_section("OSA_DEFS")
        self.preset_sections_dct = {}
        # the zp and osa defs PRESET sections save the dict as a string so lets convert and store as a member
        # var to be used later
        self.preset_sections_dct['ZP_DEFS'] = self.convert_section_to_dict(zp_defs)
        self.preset_sections_dct['OSA_DEFS'] = self.convert_section_to_dict(osa_defs)
        # using the beamlines configuration .ini file, load all the zoneplate widgets with the values
        self.zp_panels = []
        pages = 0
        zpdefs = self.preset_sections_dct['ZP_DEFS']
        for k in list(zpdefs.keys()):
            zp_def = zpdefs[k]
            zpParms_ui = uic.loadUi(os.path.join(widgetsUiDir, "zpFlds.ui"))

            # populate fields
            zpParms_ui.zpDFld.setText("%.2f" % zp_def["D"])
            zpParms_ui.zpCStopFld.setText("%.2f" % zp_def["CsD"])
            zpParms_ui.zpOZoneFld.setText("%.2f" % zp_def["OZone"])
            zpParms_ui.zpA1Fld.setText("%.3f" % zp_def["a1"])

            #self.zpToolBox.insertItem(pages, zpParms_ui, "ZP %d" % (pages))
            self.zpToolBox.insertItem(pages, zpParms_ui, f"{zp_def['name']}")
            self.zp_tbox_widgets.append(zpParms_ui)
            pages += 1

            self.zp_panels.append(zpParms_ui)

        self.zpGroupBox.layout().addWidget(self.zpToolBox)

        # now load all the osa widgets with the values
        pages = 0
        # for osa_def in osa_dct:
        osadefs = self.preset_sections_dct['OSA_DEFS']
        for k in list(osadefs.keys()):
            if isinstance(osadefs[k], str):
                s = osadefs[k].replace("'", '"')
                osa_def = json.loads(s)
            else:
                osa_def = osadefs[k]
            osaParms_ui = uic.loadUi(os.path.join(widgetsUiDir, "osaFlds.ui"))

            # populate fields
            osaParms_ui.osaDFld.setText("%.2f" % osa_def["D"])
            #self.osaToolBox.insertItem(pages, osaParms_ui, "OSA %d" % (pages + 1))
            self.osaToolBox.insertItem(pages, osaParms_ui, f"{osa_def['name']}")

            self.osa_tbox_widgets.append(osaParms_ui)
            pages += 1

        self.osaGroupBox.layout().addWidget(self.osaToolBox)

        # get previous selected zp def and load the pvs
        zp_idx = self.get_section("ZP_FOCUS_PARAMS.ZP_IDX")
        if zp_idx is None:
            zp_idx = 0
        self.zpToolBox.setCurrentIndex(zp_idx)

        # do same for osa
        osa_idx = self.get_section("ZP_FOCUS_PARAMS.OSA_IDX")
        if osa_idx is None:
            osa_idx = 0
        self.osaToolBox.setCurrentIndex(osa_idx)

        self.update_zp_selection(zp_idx=zp_idx)
        self.update_osa_selection(osa_idx=osa_idx)

        # A0 = self.get_section("ZP_FOCUS_PARAMS.OSA_A0")
        # self.a0Fld.setText("%.2f" % A0)
        # self.on_a0_changed()

        self.zpToolBox.currentChanged.connect(self.update_zp_selection)
        self.osaToolBox.currentChanged.connect(self.update_osa_selection)

        scan_mode_dev = MAIN_OBJ.device("DNM_ZONEPLATE_SCAN_MODE")
        if scan_mode_dev:
            scan_mode_dev.put(1)

        # configure the preference sections that will be saved in DEFAULTS, create if they dont already exist
        # init with defaults
        self.add_section("ZP_FOCUS_PARAMS.ZP_IDX", zp_idx)
        self.add_section("ZP_FOCUS_PARAMS.OSA_IDX", osa_idx)
        self.add_section("ZP_FOCUS_PARAMS.OSA_A0", 1500.0)
        # init from saved
        self.reload()

    def convert_section_to_dict(self, section_defs_dct):
        dct = {}
        for nm, _dct in section_defs_dct.items():
            if isinstance(_dct, str):
                s = _dct.replace("'", '"')
                _def = json.loads(s)
            else:
                _def = _dct
            dct[nm] = _def
        return dct

    def on_plugin_focus(self):
        """
        This is a function that is called when the plugin first receives focus from the main GUI
        :return:
        """
        A0 = MAIN_OBJ.device("DNM_A0")
        if A0:
            val = A0.get_position()
            self.a0Fld.setText(f"{val:.2f}")
        else:
            _logger.error("on_plugin_focus: the device DNM_A0 does not exist in the device database")


    def get_def_by_id_num(self, section: str, id_num: int) -> (str, dict):
        """
        get the OSA_DEFS PRESET section and walk all defs looking for the one with the id_num, then return the name and
        osa def dict
        """
        if section.find("OSA") > -1:
            id_nm = 'osa_id'
        else:
            id_nm = 'zp_id'

        defs = self.preset_sections_dct[section]
        for name, dct in defs.items():
            if dct[id_nm] == id_num:
                return name, dct
        return None, None

    def set_zp_active_by_id(self, id_num: int):
        """
        set the zp_def with zp_id == id_num to selcted = True all others set to False
        """
        zp_defs = self.preset_sections_dct['ZP_DEFS']
        for zp_name, zp_dct in zp_defs.items():
            if zp_dct['zp_id'] == id_num:
                zp_dct['selected'] = True
            else:
                zp_dct['selected'] = False

    def get_def_from_preset_dict(self, def_name, defs):
        """
        the OSA and zp defs from teh bl_config.ini file have the dicts as strinfgs so might need conversion
        """
        if isinstance(defs[def_name], str):
            s = defs[def_name].replace("'", '"')
            _def = json.loads(s)
        else:
            _def = osadefs[k]
        return _def

    def set_definition_active_by_id(self, section: str, id_num: int):
        """
        search the preset dict and set the matching id num def to active (selected)
        set the zp_def with zp_id == id_num to selcted = True all others set to False
        """
        if section.find('OSA') > -1:
            id_nm = 'osa_id'
        else:
            id_nm = 'zp_id'

        if section in self.preset_sections_dct.keys():
            defs = self.preset_sections_dct[section]
            for name, def_dct in defs.items():
                #def_dct = self.get_def_from_preset_dict(id_nm, defs)
                if def_dct[id_nm] == id_num:
                    def_dct['selected'] = True
                else:
                    def_dct['selected'] = False

    def reload(self):
        """
        load settings saved in the DEFAULTS module, this should only need to be the idx's for
        which zoneplate, OSA was selected and the A0
        :return:
        """
        if not self.section_exists("ZP_FOCUS_PARAMS.ZP_IDX"):
            self.update_zp_data()

        zp_idx = self.get_section("ZP_FOCUS_PARAMS.ZP_IDX")
        osa_idx = self.get_section("ZP_FOCUS_PARAMS.OSA_IDX")
        A0 = self.get_section("ZP_FOCUS_PARAMS.OSA_A0")
        #zp_def = MAIN_OBJ.get_preset_as_dict(f"zp{zp_idx}", "ZP_DEFS")

        zp_name, zp_def = self.get_def_by_id_num("ZP_DEFS", zp_idx)
        if zp_def:
            self.a0Fld.setText("%.2f" % A0)
            zp_pnl = self.zp_panels[zp_idx]
            zp_pnl.zpA1Fld.setText("%.3f" % zp_def["a1"])

            self.zpToolBox.setCurrentIndex(zp_idx)
            self.osaToolBox.setCurrentIndex(osa_idx)

    def update_fl_label(self, val_dct):
        # print(f"update_fl_label: val_dct={val_dct}")
        if isinstance(val_dct, dict):
            if 'zpA1' in self._cur_sel_zp_def.keys():
                new_fl = focal_length(val_dct["value"], self._cur_sel_zp_def["zpA1"])
        else:
            #assume its a scalar
            if 'zpA1' in self._cur_sel_zp_def.keys():
                new_fl = focal_length(val_dct, self._cur_sel_zp_def["zpA1"])
        if 'zpA1' in self._cur_sel_zp_def.keys():
            self.flFbkLbl.on_val_change(new_fl)

            if MAIN_OBJ.get_device_backend() == 'zmq':
                # for zmq backend we need to set the focal length on the device
                MAIN_OBJ.device("DNM_FOCAL_LENGTH").set_readback(new_fl)


    def on_energy_fbk_changed(self, val):
        self.update_zp_data(update_defaults=False)

    def on_a0_changed(self):
        A0 = float(str(self.a0Fld.text()))
        MAIN_OBJ.device("DNM_A0").put(A0)
        MAIN_OBJ.update_a0(A0)
        self.update_zp_data()

    def update_zp_selection(self, zp_idx=None):
        """
        signal handler for when the pv's need to be updated
        for new slection of zoneplate
        """
        if not zp_idx:
            zp_idx = self.zpToolBox.currentIndex()
        #zp_dct = MAIN_OBJ.get_preset_as_dict(f"zp{zp_idx}", "ZP_DEFS")
        self.set_definition_active_by_id("ZP_DEFS", zp_idx)
        zp_name, zp_dct = self.get_def_by_id_num("ZP_DEFS", zp_idx)
        if MAIN_OBJ.get_device_backend() == 'epics' and len(zp_dct) > 0:
            zp_def_pv = MAIN_OBJ.device("DNM_ZP_DEF")
            # because this is a Calc field I need to put values as strings
            zp_def_pv.put("CLCA", str(zp_dct["a1"]))
            zp_def_pv.put("CLCB", str(zp_dct["D"]))
            zp_def_pv.put("CLCC", str(zp_dct["CsD"]))
            zp_def_pv.put("CLCD", str(zp_dct["OZone"]))
            zp_def_pv.put("PROC", 1)

        self.update_zp_data()

    def update_osa_selection(self, osa_idx=None):
        """
        signal handler for when a new OSA has been selected,
        update the pv
        """
        if not osa_idx:
            osa_idx = self.osaToolBox.currentIndex()
        self.set_definition_active_by_id("OSA_DEFS", osa_idx)
        osa_nm, osa_dct = self.get_def_by_id_num("OSA_DEFS", osa_idx)
        if MAIN_OBJ.get_device_backend() == 'epics' and len(osa_dct) > 0:
            osa_def_pv = MAIN_OBJ.device("DNM_OSA_DEF")
            osa_def_pv.put("CLCA", str(osa_dct["D"]))
            osa_def_pv.put("PROC", 1)
        self.update_osa_data()

    def update_osa_data(self):
        osa_idx = self.osaToolBox.currentIndex()
        self.set_section("ZP_FOCUS_PARAMS.OSA_IDX", osa_idx)

        osa_defs = MAIN_OBJ.get_preset_section("OSA_DEFS")
        MAIN_OBJ.set_dcs_osa_definitions(osa_defs)

    def update_zp_data(self, update_defaults=True):
        """
        Write ZP select
        Write OSA Select
        Write A0
        Write
        Mode select
        Store presets

        """
        zp_idx = self.zpToolBox.currentIndex()
        zpParms_ui = self.zp_tbox_widgets[zp_idx]

        osa_idx = self.osaToolBox.currentIndex()
        A0 = float(str(self.a0Fld.text()))
        self._cur_sel_zp_def = {}
        self._cur_sel_zp_def["fl"] = fl = float(str(self.flFbkLbl.get_text()))
        self._cur_sel_zp_def["Zpz_pos"] = Zpz_pos = float(
            str(self.zpzFbkLbl.get_text())
        )
        self._cur_sel_zp_def["Cz_pos"] = Cz_pos = float(
            str(self.sampleZFbkLbl.get_text())
        )
        self._cur_sel_zp_def["zpD"] = zpD = float(str(zpParms_ui.zpDFld.text()))
        self._cur_sel_zp_def["zpCStop"] = zpCStop = float(
            str(zpParms_ui.zpCStopFld.text())
        )
        self._cur_sel_zp_def["zpOZone"] = zpOZone = float(
            str(zpParms_ui.zpOZoneFld.text())
        )
        self._cur_sel_zp_def["zpA1"] = zpA1 = float(str(zpParms_ui.zpA1Fld.text()))
        # self._cur_sel_zp_def['zp_idx'] = zp_idx + 1 # make base 1
        self._cur_sel_zp_def["zp_idx"] = zp_idx

        self.set_section("ZP_FOCUS_PARAMS.ZP_IDX", zp_idx)
        self.set_section("ZP_FOCUS_PARAMS.OSA_IDX", osa_idx)
        self.set_section("ZP_FOCUS_PARAMS.OSA_A0", A0)

        zp_defs = MAIN_OBJ.get_preset_section("ZP_DEFS")
        MAIN_OBJ.set_dcs_zoneplate_definitions(zp_defs)
        MAIN_OBJ.set_zoneplate_definition(self._cur_sel_zp_def, A0)


    def get_cur_zp_def(self):
        self.update_zp_data()
        return self._cur_sel_zp_def


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    window = FocusParams()
    window.show()

    app.exec_()
