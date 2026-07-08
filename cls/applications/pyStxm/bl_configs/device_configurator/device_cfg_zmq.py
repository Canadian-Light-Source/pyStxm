import sys
import os
import pathlib
import copy
import pprint
from functools import partial
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from tinydb import TinyDB


from cls.scan_engine.bluesky.qt_run_engine import ZMQEngineWidget
from cls.applications.pyStxm.bl_configs.device_configurator.con_checker import (
    con_check_many,
)
from cls.applications.pyStxm.bl_configs.device_configurator.thread_worker import Worker
from utils import query, get_zmq_connections_status


USER_ROLE = getattr(QtCore.Qt, "UserRole", 32)
CUSTOM_CONTEXT_MENU = getattr(QtCore.Qt, "CustomContextMenu", 0)


class NoScrollComboBox(QtWidgets.QComboBox):
    """QComboBox that ignores mouse-wheel events so scrolling the table
    does not accidentally change the selected DCS device name."""

    def wheelEvent(self, event):
        """Ignore wheel events so the combo box cannot be changed accidentally."""
        event.ignore()


class Device_Configure(QtWidgets.QWidget):
    def __init__(self, bl_config_path, devs):
        """Create the device configurator widget and initialize its data sources."""
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

        self.build_database(self.devs)

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
        """Return a permissive boolean conversion for checkbox and combo values."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on")
        return bool(value)

    def _is_active_dcs_entry(self, entry):
        """Return whether a raw DCS entry is marked active."""
        if not isinstance(entry, dict):
            return False
        active = entry.get("active", 0)
        if isinstance(active, str):
            return active.strip() == "1"
        return active is True or active == 1

    def _build_dcs_name_options(self):
        """Build the list of active DCS names with an empty unmapped entry first."""
        dcs_names = [""]
        raw = self.dcs_devices or {}

        if isinstance(raw, dict):
            for key, val in raw.items():
                if isinstance(val, dict):
                    entry = dict(val)
                    if "name" not in entry:
                        entry["name"] = key
                    if self._is_active_dcs_entry(entry):
                        nm = entry.get("name", "")
                        if nm and nm not in dcs_names:
                            dcs_names.append(nm)
                elif isinstance(val, list):
                    for item in val:
                        if self._is_active_dcs_entry(item):
                            nm = item.get("name", "")
                            if nm and nm not in dcs_names:
                                dcs_names.append(nm)
        elif isinstance(raw, list):
            for item in raw:
                if self._is_active_dcs_entry(item):
                    nm = item.get("name", "")
                    if nm and nm not in dcs_names:
                        dcs_names.append(nm)

        return dcs_names

    def _build_category_name_options(self, devs):
        """Build category combo-box options from the current device configuration."""
        devs = devs or self.devs
        category_names = [""] + list(devs.dev_dct.keys())
        if "PVS" not in category_names:
            category_names.append("PVS")
        return category_names

    def _build_devtype_name_options(self, lst):
        """Build devtype combo-box options from the current rows and defaults."""
        devtype_names = [""]
        for record in lst:
            dt = record.get("devtype", "")
            if dt and dt not in devtype_names:
                devtype_names.append(dt)
        if "MotorQt" not in devtype_names:
            devtype_names.append("MotorQt")
        if "sample_abstract_motor" not in devtype_names:
            devtype_names.append("sample_abstract_motor")
        if "make_basedevice" not in devtype_names:
            devtype_names.append("make_basedevice")
        return devtype_names

    def _build_pos_type_name_options(self, lst):
        """Build pos_type combo-box options from the current rows and defaults."""
        pos_type_names = [""]
        for record in lst:
            pt = record.get("pos_type", "")
            if pt and pt not in pos_type_names:
                pos_type_names.append(pt)
        if "POS_TYPE_BL" not in pos_type_names:
            pos_type_names.append("POS_TYPE_BL")
        if "POS_TYPE_ES" not in pos_type_names:
            pos_type_names.append("POS_TYPE_ES")
        return pos_type_names

    def _build_bool_options(self):
        """Return the standard boolean combo-box options."""
        return ["True", "False"]

    def _create_table_item(self, text="", editable=False, bg_color=None, user_role=None):
        """Create a configured `QStandardItem` for the device table."""
        item = QtGui.QStandardItem(str(text))
        item.setEditable(editable)
        if bg_color is not None:
            item.setBackground(bg_color)
        if user_role is not None:
            item.setData(user_role, USER_ROLE)
        return item

    def _find_combo_index(self, combo, text):
        """Return the exact-match index for `text` in `combo`, or `-1` if absent."""
        for idx in range(combo.count()):
            if combo.itemText(idx) == text:
                return idx
        return -1

    def _create_combo_box(self, items, current_text="", bg_color=None):
        """Create a non-scrolling combo box with the given items and selection."""
        combo = NoScrollComboBox()
        combo.addItems(items)
        idx = self._find_combo_index(combo, current_text)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        if bg_color is not None:
            combo.setStyleSheet(f"QComboBox {{ background-color: {bg_color}; }}")
        return combo

    def _store_mapping_text(self, mapping_name, name, text, refresh=False, row_idx=None, apply_positioners=False):
        """Store a combo-box value in the named mapping and apply any side effects."""
        getattr(self, mapping_name)[name] = text
        if apply_positioners and text == "POSITIONERS" and row_idx is not None:
            self._apply_positioners_defaults(row_idx)
        if refresh:
            self._refresh_combo_colors()

    def _apply_positioners_defaults(self, row_idx):
        """When category is POSITIONERS, enforce row defaults."""
        model = self.deviceNameTblView.model()
        if model is None:
            return
        devtype_combo = self.deviceNameTblView.indexWidget(model.index(row_idx, 3))
        pos_type_combo = self.deviceNameTblView.indexWidget(model.index(row_idx, 11))
        if devtype_combo is not None:
            devtype_combo.setCurrentText("MotorQt")
        if pos_type_combo is not None:
            pos_type_combo.setCurrentText("POS_TYPE_BL")
        units_item = model.item(row_idx, 8)
        if units_item is not None:
            units_item.setText("um")

    def _finalize_device_table_population(self, tbl):
        """Finish table population by refreshing colors and resizing rows."""
        self._refresh_combo_colors()
        tbl.resizeRowsToContents()

    def _populate_device_row(
        self,
        model,
        row,
        record,
        dcs_names,
        category_names,
        devtype_names,
        pos_type_names,
        bool_options,
        is_synthetic=False,
    ):
        """Populate one table row from a device record and bind all widgets."""
        pystxm_name = record["name"]
        bg_color = QtGui.QColor("#d4edda") if record.get("connected") else QtGui.QColor("#f8d7da")
        row_bg = QtGui.QColor("#d9ecff") if is_synthetic else bg_color
        editable_bg = QtGui.QColor("#ffffff")

        model.setItem(row, 0, self._create_table_item(pystxm_name, True, row_bg, pystxm_name))

        for col in (1, 2, 3, 5, 6, 7, 9, 11):
            model.setItem(row, col, self._create_table_item("", False, row_bg))

        for field_name, col_idx, is_editable in (
            ("desc", 4, True),
            ("units", 8, True),
            ("con_chk_nm", 10, False),
        ):
            default_text = record.get(field_name, "")
            field_item = self._create_table_item(
                default_text,
                is_editable,
                editable_bg if is_editable else row_bg,
            )
            model.setItem(row, col_idx, field_item)
            if field_name == "desc":
                self.description_mapping[pystxm_name] = field_item.text()
            elif field_name == "units":
                self.units_mapping[pystxm_name] = field_item.text()

        dcs_combo = self._create_combo_box(dcs_names, bg_color=("#d9ecff" if is_synthetic else "white"))
        saved = self.name_mapping.get(pystxm_name, "")
        if saved in dcs_names and saved != "":
            dcs_combo.setCurrentText(saved)
        else:
            dcs_nm = record.get("dcs_nm", "")
            if dcs_nm and dcs_nm in dcs_names:
                dcs_combo.setCurrentText(dcs_nm)
            else:
                dcs_combo.setCurrentIndex(0)
        dcs_combo.currentTextChanged.connect(
            partial(self._store_mapping_text, "name_mapping", pystxm_name, refresh=True)
        )
        self.name_mapping[pystxm_name] = dcs_combo.currentText()
        self._row_combos.append((pystxm_name, dcs_combo))
        if dcs_combo.currentText():
            self._selected_dcs_names.add(dcs_combo.currentText())
        self.deviceNameTblView.setIndexWidget(model.index(row, 1), dcs_combo)

        cat_combo = self._create_combo_box(category_names, bg_color=("#d9ecff" if is_synthetic else "white"))
        category_value = record.get("category", "PVS" if is_synthetic else "")
        if category_value:
            cat_combo.setCurrentText(category_value)
        cat_combo.currentTextChanged.connect(
            partial(
                self._store_mapping_text,
                "category_mapping",
                pystxm_name,
                row_idx=row,
                apply_positioners=True,
            )
        )
        self.category_mapping[pystxm_name] = cat_combo.currentText()
        self.deviceNameTblView.setIndexWidget(model.index(row, 2), cat_combo)

        devtype_combo = self._create_combo_box(devtype_names, bg_color=("#d9ecff" if is_synthetic else "white"))
        devtype_value = record.get("devtype", "make_basedevice" if is_synthetic else "")
        if devtype_value:
            devtype_combo.setCurrentText(devtype_value)
        devtype_combo.currentTextChanged.connect(
            partial(self._store_mapping_text, "devtype_mapping", pystxm_name)
        )
        self.devtype_mapping[pystxm_name] = devtype_combo.currentText()
        self.deviceNameTblView.setIndexWidget(model.index(row, 3), devtype_combo)

        for col, mapping_name, value_key, default_value in (
            (5, "connected_mapping", "connected", False),
            (6, "sim_mapping", "sim", False),
            (7, "enable_mapping", "enable", True),
            (9, "rd_only_mapping", "rd_only", False),
        ):
            combo = self._create_combo_box(bool_options, bg_color=("#d9ecff" if is_synthetic else "white"))
            combo.setCurrentText("True" if self._to_bool(record.get(value_key, default_value)) else "False")
            combo.currentTextChanged.connect(partial(self._store_mapping_text, mapping_name, pystxm_name))
            getattr(self, mapping_name)[pystxm_name] = combo.currentText()
            self.deviceNameTblView.setIndexWidget(model.index(row, col), combo)

        pos_type_combo = self._create_combo_box(pos_type_names, bg_color=("#d9ecff" if is_synthetic else "white"))
        pos_type_value = record.get("pos_type", "")
        if pos_type_value:
            pos_type_combo.setCurrentText(pos_type_value)
        pos_type_combo.currentTextChanged.connect(
            partial(self._store_mapping_text, "pos_type_mapping", pystxm_name)
        )
        self.pos_type_mapping[pystxm_name] = pos_type_combo.currentText()
        self.deviceNameTblView.setIndexWidget(model.index(row, 11), pos_type_combo)

    def _populate_device_rows(self, model, records, dcs_names, category_names, devtype_names, pos_type_names, bool_options):
        """Populate all regular device rows from the TinyDB record list."""
        for row, record in enumerate(records):
            try:
                self._populate_device_row(
                    model,
                    row,
                    record,
                    dcs_names,
                    category_names,
                    devtype_names,
                    pos_type_names,
                    bool_options,
                    is_synthetic=False,
                )
            except Exception as e:
                print(f"populate_devnames_lstview: ERROR at row {row}: {e}")
                import traceback
                traceback.print_exc()

    def _populate_synthetic_dcs_rows(self, model, dcs_names, category_names, devtype_names, pos_type_names, bool_options):
        """Append synthetic rows for DCS devices that are not yet mapped."""
        unselected_dcs_names = [nm for nm in dcs_names if nm and nm not in self._selected_dcs_names]

        for dcs_name in unselected_dcs_names:
            row = model.rowCount()
            model.insertRow(row)
            pystxm_name = self._to_pystxm_name(dcs_name)
            record = {
                "name": pystxm_name,
                "category": "PVS",
                "devtype": "make_basedevice",
                "dcs_nm": dcs_name,
                "desc": "No description in config",
                "units": "",
                "con_chk_nm": "",
                "connected": False,
                "sim": False,
                "enable": True,
                "rd_only": False,
                "pos_type": "",
            }
            self._populate_device_row(
                model,
                row,
                record,
                dcs_names,
                category_names,
                devtype_names,
                pos_type_names,
                bool_options,
                is_synthetic=True,
            )

    def _to_pystxm_name(self, dcs_name):
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
        result = self._normalize_pystxm_name(result)
        return result

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
        # Some UI variants do not include the optional detail panel widgets.
        if not hasattr(self, "selNmFld"):
            return

        self.selNmFld.setText(_dct.get("name", ""))
        if hasattr(self, "selDescFld"):
            self.selDescFld.setText(_dct.get("desc", ""))
        if hasattr(self, "selDcsNmFld"):
            self.selDcsNmFld.setText(_dct.get("dcs_nm", ""))
        if hasattr(self, "selCtgCmboBx"):
            self.set_combo_box_to_txt(self.selCtgCmboBx, _dct.get("category", ""))
        if hasattr(self, "selDevTypeCmboBx"):
            self.set_combo_box_to_txt(self.selDevTypeCmboBx, _dct.get("devtype", ""))
        if hasattr(self, "selConLbl"):
            clr = "green" if _dct.get("connected", False) else "red"
            self.selConLbl.setPixmap(QtGui.QPixmap(os.path.join("images", "%s.png" % clr)))


    def get_devdct_from_flds(self):
        """
        walk all the fields of the device in the GUI and return a dict (only the strings) of them
        """
        dct = {}
        dct["name"] = self.selNmFld.text() if hasattr(self, "selNmFld") else ""
        dct["desc"] = self.selDescFld.text() if hasattr(self, "selDescFld") else ""
        dct["dcs_nm"] = self.selDcsNmFld.text() if hasattr(self, "selDcsNmFld") else ""
        dct["category"] = self.selCtgCmboBx.currentText() if hasattr(self, "selCtgCmboBx") else ""
        dct["devtype"] = self.selDevTypeCmboBx.currentText() if hasattr(self, "selDevTypeCmboBx") else ""
        dct["sim"] = self.selSimChkBx.isChecked() if hasattr(self, "selSimChkBx") else False
        dct["enable"] = self.selEnableChkBx.isChecked() if hasattr(self, "selEnableChkBx") else True
        return dct

    def set_combo_box_to_txt(self, cmbobx, txt):
        index = self._find_combo_index(cmbobx, txt)
        if index >= 0:
            cmbobx.setCurrentIndex(index)

    def load_combo_box(self, cmbobx, lst):
        cmbobx.clear()
        cmbobx.addItems(lst)

    def _setup_table_context_menu(self):
        """Enable right-click context menu for add/delete row actions."""
        tbl = self.deviceNameTblView
        tbl.setContextMenuPolicy(CUSTOM_CONTEXT_MENU)
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
        name_item.setData(pystxm_name, USER_ROLE)
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

        old_name = item.data(USER_ROLE) or ""
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
            item.setData(new_name, USER_ROLE)
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
        item.setData(new_name, USER_ROLE)
        self._refresh_combo_colors()

    def populate_devnames_tableview(self, lst=None, devs=None):
        """Populate ``deviceNameTblView`` using helper methods for each logical phase.

        The implementation is intentionally split into helpers so the orchestration
        here stays small and each responsibility is easier to follow.
        """
        devs = devs or self.devs
        self._loading_table = True

        try:
            if lst is None:
                lst = self.dev_db.all() if self.dev_db else []

            print(f"populate_devnames_lstview: lst has {len(lst)} records")
            num_poss_cons = len(lst)
            num_cons = len(self.dev_db.search(query.connected == True)) if self.dev_db else 0
            self.numSignalsLbl.setText(
                f"{num_cons} connected out of a possible {num_poss_cons} signals"
            )

            dcs_names = self._build_dcs_name_options()
            category_names = self._build_category_name_options(devs)
            devtype_names = self._build_devtype_name_options(lst)
            pos_type_names = self._build_pos_type_name_options(lst)
            bool_options = self._build_bool_options()

            self._dcs_names_options = list(dcs_names)
            self._category_names_options = list(category_names)
            self._devtype_names_options = list(devtype_names)
            self._pos_type_names_options = list(pos_type_names)
            self._bool_options = list(bool_options)

            tbl = self.deviceNameTblView
            col_headers = [
                "pyStxm Name", "DCS Device Name", "Category", "DevType", "Description",
                "Connected", "Sim", "Enable", "Units", "ReadOnly", "ConChkNm", "PosType",
            ]
            model = QtGui.QStandardItemModel(len(lst), len(col_headers), self)
            model.setHorizontalHeaderLabels(col_headers)
            tbl.setModel(model)
            model.itemChanged.connect(self._on_table_item_changed)

            tbl.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            tbl.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            for col in range(2, len(col_headers)):
                tbl.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)

            tbl.verticalHeader().setVisible(False)
            tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            tbl.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
            self._setup_table_context_menu()

            try:
                tbl.clicked.disconnect()
            except TypeError:
                pass
            tbl.clicked.connect(lambda idx: self.on_dev_selected(idx.row()))

            self._row_combos = []
            self._selected_dcs_names = set()
            self._populate_device_rows(model, lst, dcs_names, category_names, devtype_names, pos_type_names, bool_options)
            self._populate_synthetic_dcs_rows(model, dcs_names, category_names, devtype_names, pos_type_names, bool_options)
            self._finalize_device_table_population(tbl)
        finally:
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
        """Return a copy of the current row name → connected-state mapping."""
        return dict(self.connected_mapping)

    def get_sim_mapping(self) -> dict:
        """Return a copy of the current row name → simulation-state mapping."""
        return dict(self.sim_mapping)

    def get_enable_mapping(self) -> dict:
        """Return a copy of the current row name → enabled-state mapping."""
        return dict(self.enable_mapping)

    def get_rd_only_mapping(self) -> dict:
        """Return a copy of the current row name → read-only-state mapping."""
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


    # def init_devCategories(self, dev_dct):
    #     """
    #     Populate the category combo box with the available device categories.
    #
    #     Args:
    #         dev_dct: Device dictionary whose keys define the available categories.
    #     """
    #     self.devCatCmboBx.clear()
    #     keys = list(["All"] + list(dev_dct.keys()))
    #     self.devCatCmboBx.addItems(keys)

    def on_cat_selected(self, index):
        """Filter the table to the currently selected category."""
        self.cur_cat = dev_type = self.devCatCmboBx.currentText()
        # self.dwgsmodel.clear()
        if self.cur_cat == "All":
            dev_dct_lst = self.dev_db.all()
        else:
            dev_dct_lst = self.dev_db.search(query.category == self.cur_cat)
        self.populate_devnames_tableview(lst=dev_dct_lst)

    def do_threaded_many_check(self, devs):
        """Build the TinyDB database and refresh the table for all devices."""
        # worker = Worker(self.build_database) #, delay_return=0.5)  # Any other args, kwargs are passed to the run function
        # worker.signals.result.connect(self.load_results)
        # self.threadpool.start(worker)
        # self.numSignalsLbl.setText('Checking PV connections and building database, one moment')
        # #print('Checking PV connections and building database, one moment')
        self.build_database(devs)
        self.populate_devnames_tableview(devs=devs)

    def do_threaded_single_check(self, dcs_name):
        """Run a single DCS connection check in the worker thread pool."""

        worker = Worker(
            con_check_many, [dcs_name]
        )  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.update_single_conn_sts)
        self.threadpool.start(worker)
        self.selConLbl.setText("Checking DCS connection, one moment")

    def check_single_dcs_name(self, dct):
        """Return the connection status for a single device record."""
        con_sts = devs.get_connections_status(dct)
        return con_sts

    def update_single_conn_sts(self, conn):
        """Update the connection indicator after a single PV check completes."""
        if conn[0]:
            clr = "green"
        else:
            clr = "red"
        self.selConLbl.setPixmap(QtGui.QPixmap(os.path.join("images", "%s.png" % clr)))

    def on_thread_done(self):
        """Debug hook invoked when a worker thread completes."""
        th = self.sender()
        print(th.fn)

    def set_con_sts(self, cons):
        """Store the current connection-status mapping."""
        self.cons = cons

    def build_database(self, devs):  # , db_fpath='db.json'):
        """Rebuild the TinyDB database from the current device configuration."""
        dev_dct = devs.dev_dct
        verbose = False
        if self.dev_db:
            self.dev_db.close()
        self.dev_db = TinyDB(self.devdb_path.as_posix())
        self.dev_db.drop_tables()
        # self.init_devCategories(devs.dev_dct)
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
        """Insert one configuration record into the TinyDB device database."""
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
    """Generate a simple module of `DNM_*` constants from the device dictionary."""
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
