import sys
import os
import pathlib
import copy
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

        self.testConnBtn.clicked.connect(self.on_test_connection)
        self.updateDevBtn.clicked.connect(self.on_update_dev)

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

        # {pystxm_name: dcs_name} – updated live as the user picks combos
        self.name_mapping: dict = {}

        self.retestBtn.clicked.connect(self.on_retest)
        # self.devCatCmboBx.currentIndexChanged.connect(self.on_cat_selected)
        self.setMinimumHeight(600)

        self.dcs_devices = self.engine_widget.engine.get_devices_from_settings()
        self.do_threaded_many_check(devs)


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

    def on_update_dev(self):
        """
        the user has changed a field for a device so update the devs.py file
        """
        replace_dct = self.get_devdct_from_flds()
        update_dev_dct_file(self.bl_config_path, self.pre_devdct, replace_dct)

    def on_test_connection(self):
        nm = self.selNmFld.text()
        dcs_nm = self.selDcsNmFld.text()
        dct = self.dev_db.search(query.name == nm)[0]
        if "con_chk_nm" in dct.keys():
            dcs_nm = dcs_nm + dct["con_chk_nm"]
        self.do_threaded_single_check(dcs_nm)

    def set_combo_box_to_txt(self, cmbobx, txt):
        index = cmbobx.findText(txt, QtCore.Qt.MatchFixedString)
        if index >= 0:
            cmbobx.setCurrentIndex(index)

    def load_combo_box(self, cmbobx, lst):
        cmbobx.clear()
        cmbobx.addItems(lst)

    def populate_devnames_lstview(self, lst=None, devs=None):
        """
        Populate the device-name table with one row per pyStxm device.

        Each row contains:
          - Column 0: read-only pyStxm device name (from TinyDB)
          - Column 1: QComboBox populated with all DCS device names obtained
                      from ``self.dcs_devices`` so the user can pick which DCS
                      positioner/device maps to each pyStxm device.

        Selections are persisted in ``self.name_mapping`` as
        ``{pystxm_name: dcs_name}`` and survive a refresh (the previously
        chosen value is restored when the table is rebuilt).

        Args:
            lst  (list | None): list of TinyDB record dicts to display.
                                Defaults to all records in ``self.dev_db``.
            devs (module | None): devs module (kept for API compatibility with
                                  callers such as ``do_threaded_many_check``).
        """
        if lst is None:
            lst = self.dev_db.all() if self.dev_db else []

        print(f"populate_devnames_lstview: lst has {len(lst)} records")
        num_poss_cons = len(lst)
        num_cons = len(self.dev_db.search(query.connected == True)) if self.dev_db else 0
        self.numSignalsLbl.setText(
            f"{num_cons} connected out of a possible {num_poss_cons} signals"
        )

        # --- build the flat list of DCS device names --------------------------
        # get_devices_from_settings returns the content of positionerConfigFileName
        # which is typically {"positioners": [{"name": "SampleX", ...}, ...]}.
        # Handle dict-with-list, bare list, and empty / None gracefully.
        dcs_names = [""]  # blank entry = unmapped
        raw = self.dcs_devices or {}
        if isinstance(raw, dict):
            dcs_names += list(raw)
        elif isinstance(raw, list):
            dcs_names += [p["name"] for p in raw if isinstance(p, dict) and "name" in p]

        # --- configure the QTableView with a QStandardItemModel ---------------
        tbl = self.deviceNameTblView

        model = QtGui.QStandardItemModel(len(lst), 2, self)
        model.setHorizontalHeaderLabels(["pyStxm Name", "DCS Device"])
        tbl.setModel(model)
        tbl.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Connect row click signal
        try:
            tbl.clicked.disconnect()
        except TypeError:
            pass
        tbl.clicked.connect(lambda idx: self.on_dev_selected(idx.row()))

        # keep a reference to all combos so we can update their item colors
        self._row_combos = []   # [(pystxm_name, combo), ...]

        for row, record in enumerate(lst):
            try:
                pystxm_name = record["name"]

                # col 0 – read-only pyStxm name
                name_item = QtGui.QStandardItem(pystxm_name)
                name_item.setEditable(False)
                bg_color = QtGui.QColor("#d4edda") if record.get("connected") else QtGui.QColor("#f8d7da")
                name_item.setBackground(bg_color)
                model.setItem(row, 0, name_item)

                # col 1 placeholder
                dcs_item = QtGui.QStandardItem("")
                dcs_item.setEditable(False)
                model.setItem(row, 1, dcs_item)

                combo = NoScrollComboBox()
                combo.addItems(dcs_names)

                # pre-select: use existing mapping only
                saved = self.name_mapping.get(pystxm_name, "")
                if saved in dcs_names:
                    combo.setCurrentText(saved)
                else:
                    combo.setCurrentIndex(0)  # always "" by default

                # capture loop variable
                def _on_changed(text, name=pystxm_name):
                    self.name_mapping[name] = text
                    self._refresh_combo_colors()

                combo.currentTextChanged.connect(_on_changed)
                self.name_mapping[pystxm_name] = combo.currentText()
                self._row_combos.append((pystxm_name, combo))

                tbl.setIndexWidget(model.index(row, 1), combo)

            except Exception as e:
                print(f"populate_devnames_lstview: ERROR at row {row}: {e}")
                import traceback
                traceback.print_exc()

        # Apply initial color state
        self._refresh_combo_colors()
        tbl.resizeRowsToContents()

    def get_name_mapping(self) -> dict:
        """
        Return the current pyStxm-name → DCS-name mapping as chosen by the user.

        Returns:
            dict: ``{pystxm_name: dcs_name}``  (empty string means unmapped)
        """
        return dict(self.name_mapping)

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
        self.populate_devnames_lstview(lst=dev_dct_lst)

    def on_retest(self):
        self.do_threaded_many_check(self.devs)

    def do_threaded_many_check(self, devs):
        # worker = Worker(self.build_database) #, delay_return=0.5)  # Any other args, kwargs are passed to the run function
        # worker.signals.result.connect(self.load_results)
        # self.threadpool.start(worker)
        # self.numSignalsLbl.setText('Checking PV connections and building database, one moment')
        # #print('Checking PV connections and building database, one moment')
        self.build_database(devs)
        self.populate_devnames_lstview(devs=devs)

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
                        self.do_insert(k, sig_dct, con_sts[_dct["dcs_nm"]])
                else:
                    if sig_dct.find("POS_TYPE") > -1:
                        dlist = dev_dct[k][sig_dct]
                        for _dct in dlist:
                            self.do_insert(k, _dct, con_sts[_dct["dcs_nm"]])
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
