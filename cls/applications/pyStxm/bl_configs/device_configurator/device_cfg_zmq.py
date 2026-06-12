import sys
import os
import pathlib
import copy
import pprint
from importlib import reload
from PyQt5 import QtWidgets, uic, QtGui, QtCore, Qt
from tinydb import TinyDB, Query


from cls.scan_engine.bluesky.qt_run_engine import ZMQEngineWidget
from cls.applications.pyStxm.bl_configs.device_configurator.con_checker import (
    con_check_many,
)
from cls.applications.pyStxm.bl_configs.device_configurator.thread_worker import Worker
from utils import update_dev_dct_file, reload_dev_dct, query, get_zmq_connections_status


class NoScrollComboBox(QtWidgets.QComboBox):
    """QComboBox that ignores mouse-wheel events so scrolling the table
    does not accidentally change the selected DCS device name."""

    def wheelEvent(self, event):
        event.ignore()


class Device_Configure(QtWidgets.QWidget):
    def __init__(self, bl_config_path, devs):
        super(Device_Configure, self).__init__(None)
        uic.loadUi(os.path.join(os.getcwd(), "device_cfg_zmq.ui"), self)
        self.devs = devs
        self.engine_widget = ZMQEngineWidget(devs.dev_dct, do_dev_init=False)

        self.bl_config_path = bl_config_path
        self.devdb_path = pathlib.PurePath(
            os.path.join(bl_config_path, "device_db.json")
        )

        self.threadpool = QtCore.QThreadPool()
        self.dev_db = None
        self.cur_cat = ""

        # need to keep a pre change and post change state of a selected device
        self.pre_devdct = {}
        self.post_devdct = {}

        # ... existing code...
        self.name_mapping: dict = {}
        self.category_mapping: dict = {}
        self.devtype_mapping: dict = {}
        self.description_mapping: dict = {}
        self.units_mapping: dict = {}
        self.pos_type_mapping: dict = {}
        self.connected_mapping: dict = {}
        self.sim_mapping: dict = {}
        self.enable_mapping: dict = {}
        self.rd_only_mapping: dict = {}

        # self.devCatCmboBx.currentIndexChanged.connect(self.on_cat_selected)
        self.setMinimumHeight(600)

        self.dcs_devices = self.engine_widget.engine.get_devices_from_settings()
        self.do_threaded_many_check(devs)

        self.genDevspyBtn.clicked.connect(self.on_gen_devs_py)

    def on_gen_devs_py(self):
        """Generate a devs_tmp.py file using factory functions from utils."""
        dev_dct = self._build_dev_dct_from_table()
        out_fpath = pathlib.Path(self.bl_config_path) / "devs_tmp.py"
        class_names = []
        for entries in dev_dct.values():
            for entry in entries:
                cls_name = entry.get("class", "")
                if cls_name and cls_name not in class_names:
                    class_names.append(cls_name)
        factory_names = [self._class_to_factory_name(cls_name) for cls_name in class_names]

        with open(out_fpath.as_posix(), "w") as fout:
            if factory_names:
                fout.write("from cls.applications.pyStxm.bl_configs.device_configurator.utils import (")
                fout.write(", ".join(factory_names))
                fout.write(")\n\n")
            fout.write("SIM = True\n")
            fout.write("dev_dct = {}\n\n")

            # Emit categories by calling the factory functions.
            for category, entries in dev_dct.items():
                fout.write(f"dev_dct[{category!r}] = [\n")
                for entry in entries:
                    class_name = entry.get("class", "make_basedevice")
                    fn_name = self._class_to_factory_name(class_name)
                    call_kwargs = []
                    for key, val in entry.items():
                        if key == "class":
                            continue
                        call_kwargs.append(f"{key}={self._to_py_literal(val)}")
                    # Format function call with line wrapping for long arguments
                    self._write_wrapped_function_call(fout, fn_name, call_kwargs)
                fout.write("]\n\n")
        num_categories = len(dev_dct)
        num_devices = sum(len(v) for v in dev_dct.values())
        QtWidgets.QMessageBox.information(
            self,
            "devs_tmp.py Generated",
            f"Generated: {out_fpath.as_posix()}\n"
            f"Categories: {num_categories}\n"
            f"Devices: {num_devices}",
        )
        print(f"generated [{out_fpath.as_posix()}]")

    def _class_to_factory_name(self, class_name: str) -> str:
        """Convert a class string into a safe factory function name."""
        if not class_name:
            return "make_entry"
        safe = []
        for ch in str(class_name):
            if ch.isalnum() or ch == "_":
                safe.append(ch)
            else:
                safe.append("_")
        name = "".join(safe).strip("_")
        if not name:
            name = "entry"
        return f"make_{name}"

    def _collect_class_templates(self, dev_dct):
        """Return ordered class->keys mapping based on current generated entries."""
        templates = {}
        for entries in dev_dct.values():
            for entry in entries:
                class_name = entry.get("class", "make_basedevice")
                if class_name not in templates:
                    templates[class_name] = []
                seen = set(templates[class_name])
                for key in entry.keys():
                    if key not in seen:
                        templates[class_name].append(key)
                        seen.add(key)
        return templates

    def _to_py_literal(self, val):
        """Convert Python value to stable source literal."""
        return pprint.pformat(val, width=120, sort_dicts=False)

    def _write_wrapped_function_call(self, fout, fn_name, call_kwargs):
        """Write a function call with line wrapping for long argument lists."""
        # Estimate the length of the full line
        kwargs_str = ", ".join(call_kwargs)
        full_line = f"    {fn_name}({kwargs_str}),"
        
        # If short enough (< 100 chars), write on a single line
        if len(full_line) <= 100:
            fout.write(f"{full_line}\n")
            return
        
        # Otherwise, write with line wrapping: one argument per line
        fout.write(f"    {fn_name}(")
        fout.write(f"{call_kwargs[0]}")
        for kwarg in call_kwargs[1:]:
            fout.write(f",\n                       {kwarg}")
        fout.write("),\n")

    def _combo_text(self, row, col, default=""):
        """Return combo text for a cell if it has an embedded combobox."""
        idx = self.deviceNameTblView.model().index(row, col)
        wdg = self.deviceNameTblView.indexWidget(idx)
        if isinstance(wdg, QtWidgets.QComboBox):
            return wdg.currentText()
        return default

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on")
        return bool(value)

    def _normalize_pystxm_name(self, name):
        """
        Normalize a pyStxm device name by ensuring trailing X/Y/Z axis suffixes have underscores.
        
        Converts names like 'DNM_COARSEX' to 'DNM_COARSE_X', but preserves names
        like 'DNM_ENERGY' that happen to end with Y but aren't axis indicators.
        
        Only adds an underscore before the final X/Y/Z if the preceding stem is a known
        motor/device component name (DETECTOR, COARSE, FINE, SAMPLE, etc.) or if the
        character immediately before the axis is a digit (e.g., MOTOR1X).

        Args:
            name (str): The device name to normalize.
            
        Returns:
            str: The normalized device name.
        """
        # Known motor/device component stems that naturally pair with X/Y/Z axis letters
        MOTOR_STEMS = {
            'DETECTOR', 'COARSE', 'FINE', 'SAMPLE', 'OSA', 'GONI', 'GONIOMETER',
            'ZONEPLATE', 'ZONE', 'GIRDER', 'MIRROR', 'SLIT', 'COUPLER', 'CART',
            'TABLE', 'STAGE', 'AXIS', 'MOTOR', 'MTR',
        }

        if not name or len(name) < 3:
            return name
        
        # Only process names ending with X, Y, or Z
        if name[-1] not in ('X', 'Y', 'Z'):
            return name
        
        # Check if underscore is already before the axis letter
        if name[-2] == '_':
            return name

        # If char before axis is a digit, always add underscore (e.g., MOTOR1X -> MOTOR1_X)
        if name[-2].isdigit():
            return name[:-1] + "_" + name[-1]
        
        # Check if the stem (everything except final letter) matches or contains a known motor stem
        stem = name[:-1]
        for motor_stem in MOTOR_STEMS:
            # Match: stem equals motor, or ends with underscore+motor
            if stem == motor_stem or stem.endswith('_' + motor_stem):
                return name[:-1] + "_" + name[-1]

        # Conservative: if no known stem match, keep the name as-is
        return name

    def _build_dev_dct_from_table(self):
        """Build a dev_dct-style dict from the current table contents."""
        model = self.deviceNameTblView.model()
        # Keep all default categories from the original devs.py, even if empty.
        dev_dct = {k: [] for k in self.devs.dev_dct.keys()}
        # Build quick lookup by device name from original devs.py entries.
        orig_by_name = {}
        for sect_lst in self.devs.dev_dct.values():
            if isinstance(sect_lst, list):
                for entry in sect_lst:
                    if isinstance(entry, dict) and "name" in entry:
                        orig_by_name[entry["name"]] = entry
        if model is None:
            return dev_dct

        for row in range(model.rowCount()):
            name_item = model.item(row, 0)
            if name_item is None:
                continue

            name = name_item.text().strip()
            if not name:
                continue

            # Normalize the pyStxm name to ensure trailing X/Y/Z have underscores
            name = self._normalize_pystxm_name(name)

            category = self._combo_text(row, 2, "").strip() or "UNKNOWN"
            devtype = self._combo_text(row, 3, "").strip()
            dcs_nm = self._combo_text(row, 1, "").strip()
            pos_type = self._combo_text(row, 11, "").strip()

            desc_item = model.item(row, 4)
            units_item = model.item(row, 8)
            con_chk_item = model.item(row, 10)

            desc = desc_item.text().strip() if desc_item else ""
            units = units_item.text().strip() if units_item else ""
            con_chk_nm = con_chk_item.text().strip() if con_chk_item else ""

            connected = self._to_bool(self._combo_text(row, 5, "False"))
            sim = self._to_bool(self._combo_text(row, 6, "False"))
            enable = self._to_bool(self._combo_text(row, 7, "True"))
            rd_only = self._to_bool(self._combo_text(row, 9, "False"))

            entry = {
                "name": name,
                "desc": desc,
                "class": devtype,
                "dcs_nm": dcs_nm,
            }
            orig_entry = orig_by_name.get(name, {})
            if not entry["dcs_nm"] and orig_entry.get("dcs_nm"):
                entry["dcs_nm"] = orig_entry.get("dcs_nm")
            if devtype == "EnergyDevice":
                entry["energy_nm"] = orig_entry.get("energy_nm", "DNM_ENERGY")
                entry["zz_nm"] = orig_entry.get("zz_nm", "DNM_ZONEPLATE_Z")
                entry["cz_nm"] = orig_entry.get("cz_nm", "DNM_COARSE_Z")
            if devtype == "sample_abstract_motor":
                fine_nm = orig_entry.get("fine_mtr_name", "")
                coarse_nm = orig_entry.get("coarse_mtr_name", "")

                # Fallback inference if original keys were not found.
                if (not fine_nm or not coarse_nm) and name.startswith("DNM_SAMPLE_"):
                    axis = name.rsplit("_", 1)[-1]
                    if axis in ("X", "Y", "Z"):
                        if not fine_nm:
                            fine_nm = f"DNM_SAMPLE_FINE_{axis}"
                        if not coarse_nm:
                            coarse_nm = f"DNM_COARSE_{axis}"

                if fine_nm:
                    entry["fine_mtr_name"] = fine_nm
                if coarse_nm:
                    entry["coarse_mtr_name"] = coarse_nm
            if pos_type:
                entry["pos_type"] = pos_type
            if units:
                entry["units"] = units
            if con_chk_nm:
                entry["con_chk_nm"] = con_chk_nm
            if rd_only:
                entry["rd_only"] = True
            # keep non-default booleans explicit
            if sim:
                entry["sim"] = True
            if not enable:
                entry["enable"] = False
            if connected:
                entry["connected"] = True

            # Preserve class-specific fields not represented in table columns.
            skip_copy_keys = {
                "name",
                "desc",
                "class",
                "dcs_nm",
                "category",
                "devtype",
                "connected",
                "sim",
                "enable",
                "rd_only",
                "units",
                "pos_type",
                "con_chk_nm",
            }
            for k, v in orig_entry.items():
                if k not in entry and k not in skip_copy_keys:
                    entry[k] = v

            if category not in dev_dct:
                dev_dct[category] = []
            dev_dct[category].append(entry)

        return dev_dct


    def on_dev_selected(self, row):
        """
        Handle when a device row is selected in the table.
        Reads the pyStxm device name from column 0 and populates the detail
        fields in the lower panel.

        Args:
            row: row index (int) or QModelIndex
        """
        if isinstance(row, QtCore.QModelIndex):
            row = row.row()

        model = self.deviceNameTblView.model()
        if model is None:
            return
        item = model.item(row, 0)
        if item is None:
            return
        self.cur_dev = item.text()
        results = self.dev_db.search(query.name == self.cur_dev)
        if not results:
            return
        _dct = results[0]
        self.pre_devdct = copy.copy(_dct)
        self.selNmFld.setText(_dct["name"])
        self.selDescFld.setText(_dct["desc"])
        self.selDcsNmFld.setText(_dct["dcs_nm"])
        self.set_combo_box_to_txt(self.selCtgCmboBx, _dct["category"])
        self.set_combo_box_to_txt(self.selDevTypeCmboBx, _dct["devtype"])
        clr = "green" if _dct["connected"] else "red"
        self.selConLbl.setPixmap(QtGui.QPixmap(os.path.join("images", "%s.png" % clr)))


    def get_devdct_from_flds(self):
        """
        walk all the fields of the device in the GUI and return a dict (only the strings) of them
        """
        dct = {}
        dct["name"] = self.selNmFld.text()
        dct["desc"] = self.selDescFld.text()
        dct["dcs_nm"] = self.selDcsNmFld.text()
        dct["category"] = self.selCtgCmboBx.currentText()
        dct["devtype"] = self.selDevTypeCmboBx.currentText()
        dct["sim"] = self.selSimChkBx.isChecked()
        dct["enable"] = self.selEnableChkBx.isChecked()
        return dct

    def set_combo_box_to_txt(self, cmbobx, txt):
        index = cmbobx.findText(txt, QtCore.Qt.MatchFixedString)
        if index >= 0:
            cmbobx.setCurrentIndex(index)

    def load_combo_box(self, cmbobx, lst):
        cmbobx.clear()
        cmbobx.addItems(lst)

    def _setup_table_context_menu(self):
        """Enable right-click context menu for add/delete row actions."""
        tbl = self.deviceNameTblView
        tbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        try:
            tbl.customContextMenuRequested.disconnect(self._on_table_context_menu)
        except TypeError:
            pass
        tbl.customContextMenuRequested.connect(self._on_table_context_menu)

    def _on_table_context_menu(self, pos):
        """Show row actions when the user right-clicks the device table."""
        tbl = self.deviceNameTblView
        model = tbl.model()
        if model is None:
            return

        idx = tbl.indexAt(pos)
        row = idx.row() if idx.isValid() else -1

        menu = QtWidgets.QMenu(tbl)
        add_above = menu.addAction("Add Row Above")
        add_below = menu.addAction("Add Row Below")
        delete_row = menu.addAction("Delete Row")

        if row < 0:
            add_above.setEnabled(False)
            delete_row.setEnabled(False)

        action = menu.exec_(tbl.viewport().mapToGlobal(pos))
        if action is None:
            return

        if action == add_above and row >= 0:
            self._insert_manual_row(row)
        elif action == add_below:
            self._insert_manual_row(row + 1 if row >= 0 else model.rowCount())
        elif action == delete_row and row >= 0:
            self._delete_manual_row(row)

    def _next_manual_name(self):
        """Create a unique default name for a manually inserted row."""
        model = self.deviceNameTblView.model()
        existing = set()
        if model is not None:
            for i in range(model.rowCount()):
                item = model.item(i, 0)
                if item is not None:
                    nm = item.text().strip()
                    if nm:
                        existing.add(nm)

        base = "DNM_NEW_DEVICE"
        if base not in existing:
            return base
        n = 1
        while f"{base}_{n}" in existing:
            n += 1
        return f"{base}_{n}"

    def _insert_manual_row(self, row):
        """Insert a new table row with default widgets and values."""
        tbl = self.deviceNameTblView
        model = tbl.model()
        if model is None:
            return

        dcs_names = getattr(self, "_dcs_names_options", [""])
        category_names = getattr(self, "_category_names_options", ["", "PVS"])
        devtype_names = getattr(self, "_devtype_names_options", ["", "make_basedevice"])
        pos_type_names = getattr(self, "_pos_type_names_options", [""])
        bool_options = getattr(self, "_bool_options", ["True", "False"])

        row = max(0, min(row, model.rowCount()))
        model.insertRow(row)

        pystxm_name = self._next_manual_name()
        new_row_bg = QtGui.QColor("#d9ecff")

        name_item = QtGui.QStandardItem(pystxm_name)
        name_item.setEditable(True)
        name_item.setData(pystxm_name, QtCore.Qt.UserRole)
        name_item.setBackground(new_row_bg)
        model.setItem(row, 0, name_item)

        for col in (1, 2, 3, 5, 6, 7, 9, 11):
            cell = QtGui.QStandardItem("")
            cell.setEditable(False)
            cell.setBackground(new_row_bg)
            model.setItem(row, col, cell)

        for col, editable in ((4, True), (8, True), (10, False)):
            default_text = "No description in config" if col == 4 else ""
            cell = QtGui.QStandardItem(default_text)
            cell.setEditable(editable)
            cell.setBackground(QtGui.QColor("#ffffff") if editable else new_row_bg)
            model.setItem(row, col, cell)

        dcs_combo = NoScrollComboBox()
        dcs_combo.addItems(dcs_names)
        dcs_combo.setCurrentIndex(0)
        dcs_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")

        def _on_dcs_changed(text, name=pystxm_name):
            self.name_mapping[name] = text
            self._refresh_combo_colors()

        dcs_combo.currentTextChanged.connect(_on_dcs_changed)
        self.name_mapping[pystxm_name] = dcs_combo.currentText()
        self._row_combos.append((pystxm_name, dcs_combo))
        tbl.setIndexWidget(model.index(row, 1), dcs_combo)

        cat_combo = NoScrollComboBox()
        cat_combo.addItems(category_names)
        cat_combo.setCurrentText("PVS")
        cat_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
        cat_combo.currentTextChanged.connect(
            lambda text, name=pystxm_name: self.category_mapping.__setitem__(name, text)
        )
        self.category_mapping[pystxm_name] = cat_combo.currentText()
        tbl.setIndexWidget(model.index(row, 2), cat_combo)

        devtype_combo = NoScrollComboBox()
        devtype_combo.addItems(devtype_names)
        devtype_combo.setCurrentText("make_basedevice")
        devtype_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
        devtype_combo.currentTextChanged.connect(
            lambda text, name=pystxm_name: self.devtype_mapping.__setitem__(name, text)
        )
        self.devtype_mapping[pystxm_name] = devtype_combo.currentText()
        tbl.setIndexWidget(model.index(row, 3), devtype_combo)

        connected_combo = NoScrollComboBox()
        connected_combo.addItems(bool_options)
        connected_combo.setCurrentText("False")
        connected_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
        connected_combo.currentTextChanged.connect(
            lambda text, name=pystxm_name: self.connected_mapping.__setitem__(name, text)
        )
        self.connected_mapping[pystxm_name] = connected_combo.currentText()
        tbl.setIndexWidget(model.index(row, 5), connected_combo)

        sim_combo = NoScrollComboBox()
        sim_combo.addItems(bool_options)
        sim_combo.setCurrentText("False")
        sim_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
        sim_combo.currentTextChanged.connect(
            lambda text, name=pystxm_name: self.sim_mapping.__setitem__(name, text)
        )
        self.sim_mapping[pystxm_name] = sim_combo.currentText()
        tbl.setIndexWidget(model.index(row, 6), sim_combo)

        enable_combo = NoScrollComboBox()
        enable_combo.addItems(bool_options)
        enable_combo.setCurrentText("True")
        enable_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
        enable_combo.currentTextChanged.connect(
            lambda text, name=pystxm_name: self.enable_mapping.__setitem__(name, text)
        )
        self.enable_mapping[pystxm_name] = enable_combo.currentText()
        tbl.setIndexWidget(model.index(row, 7), enable_combo)

        rd_only_combo = NoScrollComboBox()
        rd_only_combo.addItems(bool_options)
        rd_only_combo.setCurrentText("False")
        rd_only_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
        rd_only_combo.currentTextChanged.connect(
            lambda text, name=pystxm_name: self.rd_only_mapping.__setitem__(name, text)
        )
        self.rd_only_mapping[pystxm_name] = rd_only_combo.currentText()
        tbl.setIndexWidget(model.index(row, 9), rd_only_combo)

        pos_type_combo = NoScrollComboBox()
        pos_type_combo.addItems(pos_type_names)
        pos_type_combo.setCurrentIndex(0)
        pos_type_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
        pos_type_combo.currentTextChanged.connect(
            lambda text, name=pystxm_name: self.pos_type_mapping.__setitem__(name, text)
        )
        self.pos_type_mapping[pystxm_name] = pos_type_combo.currentText()
        tbl.setIndexWidget(model.index(row, 11), pos_type_combo)

        self.description_mapping[pystxm_name] = "No description in config"
        self.units_mapping[pystxm_name] = ""
        self._refresh_combo_colors()
        tbl.resizeRowsToContents()

    def _delete_manual_row(self, row):
        """Delete the selected row and clear tracked mapping entries."""
        model = self.deviceNameTblView.model()
        if model is None or row < 0 or row >= model.rowCount():
            return

        name_item = model.item(row, 0)
        pystxm_name = name_item.text().strip() if name_item is not None else ""
        if pystxm_name:
            for dct in (
                self.name_mapping,
                self.category_mapping,
                self.devtype_mapping,
                self.description_mapping,
                self.units_mapping,
                self.pos_type_mapping,
                self.connected_mapping,
                self.sim_mapping,
                self.enable_mapping,
                self.rd_only_mapping,
            ):
                dct.pop(pystxm_name, None)
            self._row_combos = [t for t in self._row_combos if t[0] != pystxm_name]

        model.removeRow(row)
        self._refresh_combo_colors()

    def _on_table_item_changed(self, item):
        """Keep mapping dictionaries in sync when the editable name cell is changed."""
        if getattr(self, "_loading_table", False):
            return
        if item is None or item.column() != 0:
            return

        model = self.deviceNameTblView.model()
        if model is None:
            return

        old_name = item.data(QtCore.Qt.UserRole) or ""
        new_name = item.text().strip()
        if not old_name:
            old_name = new_name

        # Reject empty names and restore previous value.
        if not new_name:
            self._loading_table = True
            item.setText(old_name)
            self._loading_table = False
            return

        # Enforce unique device names in column 0.
        row = item.row()
        for i in range(model.rowCount()):
            if i == row:
                continue
            other = model.item(i, 0)
            if other is not None and other.text().strip() == new_name:
                self._loading_table = True
                item.setText(old_name)
                self._loading_table = False
                return

        if new_name == old_name:
            item.setData(new_name, QtCore.Qt.UserRole)
            return

        # Move mapping entries from old key to new key.
        mapping_dicts = (
            self.name_mapping,
            self.category_mapping,
            self.devtype_mapping,
            self.description_mapping,
            self.units_mapping,
            self.pos_type_mapping,
            self.connected_mapping,
            self.sim_mapping,
            self.enable_mapping,
            self.rd_only_mapping,
        )
        for dct in mapping_dicts:
            if old_name in dct:
                dct[new_name] = dct.pop(old_name)

        self._row_combos = [
            (new_name if nm == old_name else nm, combo) for nm, combo in self._row_combos
        ]
        item.setData(new_name, QtCore.Qt.UserRole)
        self._refresh_combo_colors()

    def populate_devnames_tableview(self, lst=None, devs=None):
        """
        Populate ``deviceNameTblView`` with one row per device record from TinyDB.

        Column layout:
            0: ``pyStxm Name`` (read-only)
            1: ``DCS Device`` (combobox)
            2: ``Category`` (combobox)
            3: ``DevType`` (combobox)
            4: ``Description`` (editable text)
            5: ``Connected`` (True/False combobox)
            6: ``Sim`` (True/False combobox)
            7: ``Enable`` (True/False combobox)
            8: ``Units`` (editable text)
            9: ``ReadOnly`` (True/False combobox)
            10: ``ConChkNm`` (read-only text)
            11: ``PosType`` (combobox)

        Current user selections/edits are tracked in mapping dicts on ``self``
        (for example ``name_mapping``, ``category_mapping``, ``devtype_mapping``,
        ``pos_type_mapping`` and boolean mappings). DCS name conflict coloring is
        refreshed after table population.

        Args:
            lst (list | None): Records to display; defaults to ``self.dev_db.all()``.
            devs (module | None): Device configuration module, used to build combo
                options (categories/devtypes/pos_types).
        """
        self._loading_table = True

        if lst is None:
            lst = self.dev_db.all() if self.dev_db else []

        print(f"populate_devnames_lstview: lst has {len(lst)} records")
        num_poss_cons = len(lst)
        num_cons = len(self.dev_db.search(query.connected == True)) if self.dev_db else 0
        self.numSignalsLbl.setText(
            f"{num_cons} connected out of a possible {num_poss_cons} signals"
        )

        # --- build the flat list of ACTIVE DCS device names -------------------
        # Keep only names whose source entry has active == 1 (or True / "1").
        dcs_names = [""]  # blank entry = unmapped
        raw = self.dcs_devices or {}

        def _is_active(entry):
            if not isinstance(entry, dict):
                return False
            active = entry.get("active", 0)
            if isinstance(active, str):
                return active.strip() == "1"
            return active is True or active == 1

        def _add_name_if_active(entry):
            if _is_active(entry):
                nm = entry.get("name", "")
                if nm and nm not in dcs_names:
                    dcs_names.append(nm)

        if isinstance(raw, dict):
            # shape A: {"SomeName": {"active": 1, ...}, ...}
            # shape B: {"positioners": [{"name": "SomeName", "active": 1}, ...], ...}
            for key, val in raw.items():
                if isinstance(val, dict):
                    entry = dict(val)
                    if "name" not in entry:
                        entry["name"] = key
                    _add_name_if_active(entry)
                elif isinstance(val, list):
                    for item in val:
                        _add_name_if_active(item)
        elif isinstance(raw, list):
            for item in raw:
                _add_name_if_active(item)

        # --- build category names list -----------------------------------------
        category_names = [""] + list(devs.dev_dct.keys())
        if "PVS" not in category_names:
            category_names.append("PVS")

        # --- build devtype names list -------------------------------------------
        devtype_names = [""]
        for record in lst:
            dt = record.get("devtype", "")
            if dt and dt not in devtype_names:
                devtype_names.append(dt)
        if "MotorQt" not in devtype_names:
            devtype_names.append("MotorQt")
        if "make_basedevice" not in devtype_names:
            devtype_names.append("make_basedevice")

        # --- build pos_type names list ------------------------------------------
        pos_type_names = [""]
        for record in lst:
            pt = record.get("pos_type", "")
            if pt and pt not in pos_type_names:
                pos_type_names.append(pt)
        if "POS_TYPE_BL" not in pos_type_names:
            pos_type_names.append("POS_TYPE_BL")
        if "POS_TYPE_ES" not in pos_type_names:
            pos_type_names.append("POS_TYPE_ES")
        bool_options = ["True", "False"]

        # cache option lists so manual context-menu row insert can reuse them
        self._dcs_names_options = list(dcs_names)
        self._category_names_options = list(category_names)
        self._devtype_names_options = list(devtype_names)
        self._pos_type_names_options = list(pos_type_names)
        self._bool_options = list(bool_options)

        # --- configure the QTableView with a QStandardItemModel ---------------
        # Column order: Name, DCS Device, Category, DevType, Description, Connected, Sim, Enable, Units, ReadOnly, ConChkNm, PosType
        tbl = self.deviceNameTblView
        col_headers = [
            "pyStxm Name", "DCS Device Name", "Category", "DevType", "Description",
            "Connected", "Sim", "Enable", "Units", "ReadOnly", "ConChkNm", "PosType"
        ]
        num_cols = len(col_headers)

        model = QtGui.QStandardItemModel(len(lst), num_cols, self)
        model.setHorizontalHeaderLabels(col_headers)
        tbl.setModel(model)
        model.itemChanged.connect(self._on_table_item_changed)

        # Set column resize modes
        tbl.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Name
        tbl.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)  # DCS Device
        for col in range(2, num_cols):
            tbl.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
        
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self._setup_table_context_menu()

        # Connect row click signal
        try:
            tbl.clicked.disconnect()
        except TypeError:
            pass
        tbl.clicked.connect(lambda idx: self.on_dev_selected(idx.row()))

        # keep a reference to all combos so we can update their item colors
        self._row_combos = []   # [(pystxm_name, combo), ...]
        selected_dcs_names = set()

        def _to_bool_str(value):
            if isinstance(value, str):
                return "True" if value.strip().lower() in ("true", "1", "yes", "on") else "False"
            return "True" if bool(value) else "False"

        def _apply_positioners_defaults(row_idx):
            """When category is POSITIONERS, enforce row defaults."""
            devtype_combo = self.deviceNameTblView.indexWidget(model.index(row_idx, 3))
            pos_type_combo = self.deviceNameTblView.indexWidget(model.index(row_idx, 11))
            if devtype_combo is not None:
                devtype_combo.setCurrentText("MotorQt")
            if pos_type_combo is not None:
                pos_type_combo.setCurrentText("POS_TYPE_BL")
            units_item = model.item(row_idx, 8)
            if units_item is not None:
                units_item.setText("um")

        for row, record in enumerate(lst):
            try:
                pystxm_name = record["name"]
                bg_color = QtGui.QColor("#d4edda") if record.get("connected") else QtGui.QColor("#f8d7da")
                editable_bg = QtGui.QColor("#ffffff")

                # col 0 – pyStxm name
                name_item = QtGui.QStandardItem(pystxm_name)
                name_item.setEditable(True)
                name_item.setData(pystxm_name, QtCore.Qt.UserRole)
                name_item.setBackground(bg_color)
                model.setItem(row, 0, name_item)

                # col 1 – placeholder for DCS device combobox
                dcs_item = QtGui.QStandardItem("")
                dcs_item.setEditable(False)
                dcs_item.setBackground(editable_bg)
                model.setItem(row, 1, dcs_item)

                # col 2 – placeholder for Category combobox
                cat_item = QtGui.QStandardItem("")
                cat_item.setEditable(False)
                cat_item.setBackground(editable_bg)
                model.setItem(row, 2, cat_item)

                # col 3 – placeholder for DevType combobox
                devtype_item = QtGui.QStandardItem("")
                devtype_item.setEditable(False)
                devtype_item.setBackground(editable_bg)
                model.setItem(row, 3, devtype_item)

                # col 5/6/7/9 – placeholders for boolean comboboxes
                for bool_col in (5, 6, 7, 9):
                    bool_item = QtGui.QStandardItem("")
                    bool_item.setEditable(False)
                    bool_item.setBackground(editable_bg)
                    model.setItem(row, bool_col, bool_item)

                # col 11 – placeholder for PosType combobox
                pos_type_item = QtGui.QStandardItem("")
                pos_type_item.setEditable(False)
                pos_type_item.setBackground(editable_bg)
                model.setItem(row, 11, pos_type_item)

                # col 4 onwards – data fields
                col_data = [
                    ("desc", 4, True),      # (field, col_idx, is_editable)
                    ("units", 8, True),     # Units is now editable
                    ("con_chk_nm", 10, False),
                ]
                for field_name, col_idx, is_editable in col_data:
                    field_item = QtGui.QStandardItem(str(record.get(field_name, "")))
                    field_item.setEditable(is_editable)
                    field_item.setBackground(editable_bg if is_editable else bg_color)
                    model.setItem(row, col_idx, field_item)

                    # Track description changes
                    if field_name == "desc":
                        self.description_mapping[pystxm_name] = field_item.text()

                    # Track units changes
                    if field_name == "units":
                        self.units_mapping[pystxm_name] = field_item.text()

                # DCS name combobox (col 1)
                dcs_combo = NoScrollComboBox()
                dcs_combo.addItems(dcs_names)
                dcs_combo.setStyleSheet("QComboBox { background-color: white; }")

                # pre-select priority:
                #   1. existing session mapping (user already picked something)
                #   2. record["dcs_nm"] if it exists and is present in dcs_names
                #   3. fall back to "" (index 0)
                saved = self.name_mapping.get(pystxm_name, "")
                if saved in dcs_names and saved != "":
                    dcs_combo.setCurrentText(saved)
                else:
                    dcs_nm = record.get("dcs_nm", "")
                    if dcs_nm and dcs_nm in dcs_names:
                        dcs_combo.setCurrentText(dcs_nm)
                    else:
                        dcs_combo.setCurrentIndex(0)  # "" = unmapped

                # capture loop variable
                def _on_dcs_changed(text, name=pystxm_name):
                    self.name_mapping[name] = text
                    self._refresh_combo_colors()

                dcs_combo.currentTextChanged.connect(_on_dcs_changed)
                self.name_mapping[pystxm_name] = dcs_combo.currentText()
                self._row_combos.append((pystxm_name, dcs_combo))
                if dcs_combo.currentText():
                    selected_dcs_names.add(dcs_combo.currentText())

                tbl.setIndexWidget(model.index(row, 1), dcs_combo)

                # Category combobox (col 2)
                cat_combo = NoScrollComboBox()
                cat_combo.addItems(category_names)
                cat_combo.setCurrentText(record.get("category", ""))
                cat_combo.setStyleSheet("QComboBox { background-color: white; }")

                def _on_cat_changed(text, name=pystxm_name, row_idx=row):
                    self.category_mapping[name] = text
                    if text == "POSITIONERS":
                        _apply_positioners_defaults(row_idx)

                cat_combo.currentTextChanged.connect(_on_cat_changed)
                self.category_mapping[pystxm_name] = cat_combo.currentText()

                tbl.setIndexWidget(model.index(row, 2), cat_combo)

                # DevType combobox (col 3)
                devtype_combo = NoScrollComboBox()
                devtype_combo.addItems(devtype_names)
                devtype_combo.setCurrentText(record.get("devtype", ""))
                devtype_combo.setStyleSheet("QComboBox { background-color: white; }")

                def _on_devtype_changed(text, name=pystxm_name):
                    self.devtype_mapping[name] = text

                devtype_combo.currentTextChanged.connect(_on_devtype_changed)
                self.devtype_mapping[pystxm_name] = devtype_combo.currentText()

                tbl.setIndexWidget(model.index(row, 3), devtype_combo)

                # Boolean comboboxes (cols 5,6,7,9)
                connected_combo = NoScrollComboBox()
                connected_combo.addItems(bool_options)
                connected_combo.setCurrentText(_to_bool_str(record.get("connected", False)))
                connected_combo.setStyleSheet("QComboBox { background-color: white; }")
                connected_combo.currentTextChanged.connect(
                    lambda text, name=pystxm_name: self.connected_mapping.__setitem__(name, text)
                )
                self.connected_mapping[pystxm_name] = connected_combo.currentText()
                tbl.setIndexWidget(model.index(row, 5), connected_combo)

                sim_combo = NoScrollComboBox()
                sim_combo.addItems(bool_options)
                sim_combo.setCurrentText(_to_bool_str(record.get("sim", False)))
                sim_combo.setStyleSheet("QComboBox { background-color: white; }")
                sim_combo.currentTextChanged.connect(
                    lambda text, name=pystxm_name: self.sim_mapping.__setitem__(name, text)
                )
                self.sim_mapping[pystxm_name] = sim_combo.currentText()
                tbl.setIndexWidget(model.index(row, 6), sim_combo)

                enable_combo = NoScrollComboBox()
                enable_combo.addItems(bool_options)
                enable_combo.setCurrentText(_to_bool_str(record.get("enable", False)))
                enable_combo.setStyleSheet("QComboBox { background-color: white; }")
                enable_combo.currentTextChanged.connect(
                    lambda text, name=pystxm_name: self.enable_mapping.__setitem__(name, text)
                )
                self.enable_mapping[pystxm_name] = enable_combo.currentText()
                tbl.setIndexWidget(model.index(row, 7), enable_combo)

                rd_only_combo = NoScrollComboBox()
                rd_only_combo.addItems(bool_options)
                rd_only_combo.setCurrentText(_to_bool_str(record.get("rd_only", False)))
                rd_only_combo.setStyleSheet("QComboBox { background-color: white; }")
                rd_only_combo.currentTextChanged.connect(
                    lambda text, name=pystxm_name: self.rd_only_mapping.__setitem__(name, text)
                )
                self.rd_only_mapping[pystxm_name] = rd_only_combo.currentText()
                tbl.setIndexWidget(model.index(row, 9), rd_only_combo)

                # PosType combobox (col 11)
                pos_type_combo = NoScrollComboBox()
                pos_type_combo.addItems(pos_type_names)
                pos_type_combo.setCurrentText(record.get("pos_type", ""))
                pos_type_combo.setStyleSheet("QComboBox { background-color: white; }")

                def _on_pos_type_changed(text, name=pystxm_name):
                    self.pos_type_mapping[name] = text

                pos_type_combo.currentTextChanged.connect(_on_pos_type_changed)
                self.pos_type_mapping[pystxm_name] = pos_type_combo.currentText()

                tbl.setIndexWidget(model.index(row, 11), pos_type_combo)

            except Exception as e:
                print(f"populate_devnames_lstview: ERROR at row {row}: {e}")
                import traceback
                traceback.print_exc()

        # Append synthetic rows for any DCS names not yet selected in existing rows.
        unselected_dcs_names = [nm for nm in dcs_names if nm and nm not in selected_dcs_names]

        def _to_pystxm_name(dcs_name):
            """
            Convert a DCS device name to a pyStxm device name.

            This function transforms raw DCS device names into valid pyStxm device names by:
              1. Converting to uppercase
              2. Replacing non-alphanumeric characters (except underscore) with underscores
              3. Prefixing with 'DNM_'
              4. Normalizing trailing axis suffixes (X, Y, Z) to include an underscore

            For example:
              - 'CoarseX' -> 'DNM_COARSEX' -> 'DNM_COARSE_X'
              - 'Energy' -> 'DNM_ENERGY' -> 'DNM_ENERGY' (stays unchanged)

            Args:
                dcs_name (str): The raw DCS device name to convert.

            Returns:
                str: The formatted pyStxm device name with 'DNM_' prefix and normalized suffix.
            """
            sanitized = []
            for ch in dcs_name.upper():
                sanitized.append(ch if (ch.isalnum() or ch == "_") else "_")
            result = "DNM_" + "".join(sanitized).strip("_")
            # Use the smarter class method to normalize axis suffixes
            result = self._normalize_pystxm_name(result)
            return result

        new_row_bg = QtGui.QColor("#d9ecff")
        for dcs_name in unselected_dcs_names:
            row = model.rowCount()
            model.insertRow(row)
            pystxm_name = _to_pystxm_name(dcs_name)

            # Base row cells
            name_item = QtGui.QStandardItem(pystxm_name)
            name_item.setEditable(True)
            name_item.setData(pystxm_name, QtCore.Qt.UserRole)
            name_item.setBackground(new_row_bg)
            model.setItem(row, 0, name_item)

            for col in (1, 2, 3, 5, 6, 7, 9, 11):
                cell = QtGui.QStandardItem("")
                cell.setEditable(False)
                cell.setBackground(new_row_bg)
                model.setItem(row, col, cell)

            for col, editable in ((4, True), (8, True), (10, False)):
                default_text = "No description in config" if col == 4 else ""
                cell = QtGui.QStandardItem(default_text)
                cell.setEditable(editable)
                cell.setBackground(new_row_bg if not editable else QtGui.QColor("#ffffff"))
                model.setItem(row, col, cell)
                if col == 4:
                    self.description_mapping[pystxm_name] = default_text

            # DCS combo preselected with this unselected DCS name
            dcs_combo = NoScrollComboBox()
            dcs_combo.addItems(dcs_names)
            dcs_combo.setCurrentText(dcs_name)
            dcs_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")

            def _on_dcs_changed_new(text, name=pystxm_name):
                self.name_mapping[name] = text
                self._refresh_combo_colors()

            dcs_combo.currentTextChanged.connect(_on_dcs_changed_new)
            self.name_mapping[pystxm_name] = dcs_combo.currentText()
            self._row_combos.append((pystxm_name, dcs_combo))
            tbl.setIndexWidget(model.index(row, 1), dcs_combo)

            # Category combo
            cat_combo = NoScrollComboBox()
            cat_combo.addItems(category_names)
            cat_combo.setCurrentText("PVS")
            cat_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
            def _on_cat_changed_new(text, name=pystxm_name, row_idx=row):
                self.category_mapping[name] = text
                if text == "POSITIONERS":
                    _apply_positioners_defaults(row_idx)

            cat_combo.currentTextChanged.connect(_on_cat_changed_new)
            self.category_mapping[pystxm_name] = cat_combo.currentText()
            tbl.setIndexWidget(model.index(row, 2), cat_combo)

            # DevType combo
            devtype_combo = NoScrollComboBox()
            devtype_combo.addItems(devtype_names)
            devtype_combo.setCurrentText("make_basedevice")
            devtype_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
            devtype_combo.currentTextChanged.connect(
                lambda text, name=pystxm_name: self.devtype_mapping.__setitem__(name, text)
            )
            self.devtype_mapping[pystxm_name] = devtype_combo.currentText()
            tbl.setIndexWidget(model.index(row, 3), devtype_combo)

            # Boolean combos default to False except Enable=True
            connected_combo = NoScrollComboBox()
            connected_combo.addItems(bool_options)
            connected_combo.setCurrentText("False")
            connected_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
            connected_combo.currentTextChanged.connect(
                lambda text, name=pystxm_name: self.connected_mapping.__setitem__(name, text)
            )
            self.connected_mapping[pystxm_name] = connected_combo.currentText()
            tbl.setIndexWidget(model.index(row, 5), connected_combo)

            sim_combo = NoScrollComboBox()
            sim_combo.addItems(bool_options)
            sim_combo.setCurrentText("False")
            sim_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
            sim_combo.currentTextChanged.connect(
                lambda text, name=pystxm_name: self.sim_mapping.__setitem__(name, text)
            )
            self.sim_mapping[pystxm_name] = sim_combo.currentText()
            tbl.setIndexWidget(model.index(row, 6), sim_combo)

            enable_combo = NoScrollComboBox()
            enable_combo.addItems(bool_options)
            enable_combo.setCurrentText("True")
            enable_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
            enable_combo.currentTextChanged.connect(
                lambda text, name=pystxm_name: self.enable_mapping.__setitem__(name, text)
            )
            self.enable_mapping[pystxm_name] = enable_combo.currentText()
            tbl.setIndexWidget(model.index(row, 7), enable_combo)

            rd_only_combo = NoScrollComboBox()
            rd_only_combo.addItems(bool_options)
            rd_only_combo.setCurrentText("False")
            rd_only_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
            rd_only_combo.currentTextChanged.connect(
                lambda text, name=pystxm_name: self.rd_only_mapping.__setitem__(name, text)
            )
            self.rd_only_mapping[pystxm_name] = rd_only_combo.currentText()
            tbl.setIndexWidget(model.index(row, 9), rd_only_combo)

            # PosType combo
            pos_type_combo = NoScrollComboBox()
            pos_type_combo.addItems(pos_type_names)
            pos_type_combo.setCurrentIndex(0)
            pos_type_combo.setStyleSheet("QComboBox { background-color: #d9ecff; }")
            pos_type_combo.currentTextChanged.connect(
                lambda text, name=pystxm_name: self.pos_type_mapping.__setitem__(name, text)
            )
            self.pos_type_mapping[pystxm_name] = pos_type_combo.currentText()
            tbl.setIndexWidget(model.index(row, 11), pos_type_combo)

        # Apply initial color state
        self._refresh_combo_colors()
        tbl.resizeRowsToContents()
        self._loading_table = False

    def get_name_mapping(self) -> dict:
        """
        Return the current pyStxm-name → DCS-name mapping as chosen by the user.

        Returns:
            dict: ``{pystxm_name: dcs_name}``  (empty string means unmapped)
        """
        return dict(self.name_mapping)

    def get_category_mapping(self) -> dict:
        """
        Return the current pyStxm-name → category mapping as chosen by the user.

        Returns:
            dict: ``{pystxm_name: category}``  (empty string means no category)
        """
        return dict(self.category_mapping)

    def get_devtype_mapping(self) -> dict:
        """
        Return the current pyStxm-name → devtype mapping as chosen by the user.

        Returns:
            dict: ``{pystxm_name: devtype}``  (empty string means no devtype)
        """
        return dict(self.devtype_mapping)

    def get_description_mapping(self) -> dict:
        """
        Return the current pyStxm-name → description mapping as edited by the user.

        Returns:
            dict: ``{pystxm_name: description}``
        """
        # Read current values from the model to get live edits
        for row in range(self.deviceNameTblView.model().rowCount()):
            name_item = self.deviceNameTblView.model().item(row, 0)
            desc_item = self.deviceNameTblView.model().item(row, 4)
            if name_item and desc_item:
                pystxm_name = name_item.text()
                self.description_mapping[pystxm_name] = desc_item.text()
        return dict(self.description_mapping)

    def get_units_mapping(self) -> dict:
        """
        Return the current pyStxm-name → units mapping as edited by the user.

        Returns:
            dict: ``{pystxm_name: units}``
        """
        # Read current values from the model to get live edits
        for row in range(self.deviceNameTblView.model().rowCount()):
            name_item = self.deviceNameTblView.model().item(row, 0)
            units_item = self.deviceNameTblView.model().item(row, 8)
            if name_item and units_item:
                pystxm_name = name_item.text()
                self.units_mapping[pystxm_name] = units_item.text()
        return dict(self.units_mapping)

    def get_pos_type_mapping(self) -> dict:
        """
        Return the current pyStxm-name -> pos_type mapping as selected by the user.

        Returns:
            dict: ``{pystxm_name: pos_type}``
        """
        return dict(self.pos_type_mapping)

    def get_connected_mapping(self) -> dict:
        return dict(self.connected_mapping)

    def get_sim_mapping(self) -> dict:
        return dict(self.sim_mapping)

    def get_enable_mapping(self) -> dict:
        return dict(self.enable_mapping)

    def get_rd_only_mapping(self) -> dict:
        return dict(self.rd_only_mapping)

    def _refresh_combo_colors(self):
        """
        Walk every embedded combobox and color the items in its dropdown:
          - Items claimed by *another* row get a light gray background + gray text
            to indicate they are already in use elsewhere.
          - The item currently selected by *this* row, and the blank entry, are
            left with the default (white) background.
        """
        # Build the set of DCS names claimed across all rows
        claimed = {dcs for dcs in self.name_mapping.values() if dcs}

        for pystxm_name, combo in getattr(self, '_row_combos', []):
            own_selection = self.name_mapping.get(pystxm_name, "")
            combo_model = combo.model()
            for idx in range(combo.count()):
                item = combo_model.item(idx)
                if item is None:
                    continue
                dcs_name = item.text()
                # Gray out if claimed by a *different* row (not blank, not own)
                if dcs_name and dcs_name != own_selection and dcs_name in claimed:
                    item.setBackground(QtGui.QColor("#e0e0e0"))
                    item.setForeground(QtGui.QColor("#888888"))
                else:
                    # Restore default white background / default text color
                    item.setBackground(QtGui.QColor("#ffffff"))
                    item.setForeground(QtGui.QColor("#000000"))


    def init_devCategories(self, dev_dct):
        """
        initialize the devtype combobox
        :return:
        """
        self.devCatCmboBx.clear()
        keys = list(["All"] + list(dev_dct.keys()))
        self.devCatCmboBx.addItems(keys)

    def on_cat_selected(self, index):
        self.cur_cat = dev_type = self.devCatCmboBx.currentText()
        # self.dwgsmodel.clear()
        if self.cur_cat == "All":
            dev_dct_lst = self.dev_db.all()
        else:
            dev_dct_lst = self.dev_db.search(query.category == self.cur_cat)
        self.populate_devnames_tableview(lst=dev_dct_lst)

    def do_threaded_many_check(self, devs):
        # worker = Worker(self.build_database) #, delay_return=0.5)  # Any other args, kwargs are passed to the run function
        # worker.signals.result.connect(self.load_results)
        # self.threadpool.start(worker)
        # self.numSignalsLbl.setText('Checking PV connections and building database, one moment')
        # #print('Checking PV connections and building database, one moment')
        self.build_database(devs)
        self.populate_devnames_tableview(devs=devs)

    def do_threaded_single_check(self, dcs_name):

        worker = Worker(
            con_check_many, [dcs_name]
        )  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.update_single_conn_sts)
        self.threadpool.start(worker)
        self.selConLbl.setText("Checking DCS connection, one moment")

    def check_single_dcs_name(self, dct):
        con_sts = devs.get_connections_status(dct)
        return con_sts

    def update_single_conn_sts(self, conn):
        if conn[0]:
            clr = "green"
        else:
            clr = "red"
        self.selConLbl.setPixmap(QtGui.QPixmap(os.path.join("images", "%s.png" % clr)))

    def on_thread_done(self):
        th = self.sender()
        print(th.fn)

    def set_con_sts(self, cons):
        self.cons = cons

    def build_database(self, devs):  # , db_fpath='db.json'):
        #global dev_dct
        #reload_dev_dct(devs)
        dev_dct = devs.dev_dct
        verbose = False
        if self.dev_db:
            self.dev_db.close()
        self.dev_db = TinyDB(self.devdb_path.as_posix())
        self.dev_db.drop_tables()
        self.init_devCategories(devs.dev_dct)
        con_sts = get_zmq_connections_status(devs.dev_dct)
        keys = list(dev_dct.keys())
        keys.sort()
        for k in keys:
            dlist = dev_dct[k]
            for sig_dct in dlist:
                if type(sig_dct) == dict:
                    _dct = sig_dct
                    # check if this is an actual epics pv, might be an ophyd sim device
                    if "dcs_nm" in _dct.keys():
                        self.do_insert(k, sig_dct, con_sts.get(_dct["dcs_nm"], False))
                else:
                    if sig_dct.find("POS_TYPE") > -1:
                        dlist = dev_dct[k][sig_dct]
                        for _dct in dlist:
                            self.do_insert(k, _dct, con_sts.get(_dct["dcs_nm"], False))
        print(f'DONE build_database: [{self.devdb_path.as_posix()}]')
        print(f'build_database: total records inserted = {len(self.dev_db.all())}')
        # self.dev_db.close()

        return True

    def do_insert(self, category, sig_dct, con):
        dct = {
            "category": category,
            "devtype": sig_dct["class"],
            "name": sig_dct["name"],
            "dcs_nm": sig_dct["dcs_nm"],
            "connected": con,
            "sim": False,
            "enable": True,
        }
        if "units" not in sig_dct.keys():
            dct["units"] = ""
        else:
            dct["units"] = sig_dct["units"]

        if "desc" not in sig_dct.keys():
            dct["desc"] = "No description in config"
        else:
            dct["desc"] = sig_dct["desc"]

        if "rd_only" not in sig_dct.keys():
            dct["rd_only"] = False
        else:
            dct["rd_only"] = sig_dct["rd_only"]

        if "con_chk_nm" in sig_dct.keys():
            dct["con_chk_nm"] = sig_dct["con_chk_nm"]

        if "pos_type" not in sig_dct.keys():
            dct["pos_type"] = ""
        else:
            dct["pos_type"] = sig_dct["pos_type"]
        try:
            # print(dct)
            self.dev_db.insert(dct)
        except:
            print("oops")

    # def closeEvent(self, event):


def gen_device_names_file(fpath, dev_dct):
    # create a device_names.py file that can be imported by other modules
    import os
    import pathlib

    # p = pathlib.Path(os.path.abspath(__file__))
    fpath = pathlib.PurePath(os.path.join(fpath.parent.as_posix(), "device_names.py"))
    with open(fpath.as_posix(), "w") as f:
        for sect_nm, sect_lst in dev_dct.items():
            for dct in sect_lst:
                if dct["name"].find("DNM_") > -1:
                    f.write("%s = '%s'\n" % (dct["name"], dct["name"]))


if __name__ == "__main__":
    import importlib
    import os
    from bcm.backend import BACKEND

    app = QtWidgets.QApplication([])
    # get bl_config_dir from the command line
    bl_config_dirname = sys.argv[1]
    dbpath = pathlib.PurePath(
        os.path.join(
            pathlib.Path(os.getcwd()).parent.as_posix(), bl_config_dirname
        )
    )
    if pathlib.Path(dbpath).exists():
        import_Str = f"cls.applications.pyStxm.bl_configs.{bl_config_dirname}.devs"
        devs = importlib.import_module(import_Str, package=None)
        gen_device_names_file(dbpath, devs.dev_dct)
        dcfg = Device_Configure(dbpath, devs)
        dcfg.show()
    else:
        print(f"Error: db path [{str(dbpath)}] does not exist")
    sys.exit(app.exec_())
