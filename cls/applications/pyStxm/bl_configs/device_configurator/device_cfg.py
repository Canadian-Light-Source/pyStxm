import sys
import os
import pathlib
import copy
from importlib import reload
from PyQt5 import QtWidgets, uic, QtGui, QtCore, Qt
from tinydb import TinyDB, Query

from cls.applications.pyStxm.bl_configs.device_configurator.con_checker import (
    con_check_many,
)
from cls.applications.pyStxm.bl_configs.device_configurator.thread_worker import Worker

# import cls.applications.pyStxm.bl_configs.amb_bl10ID1.devs as devs

_q = Query()
X_AXIS = 1
Y_AXIS = 2

dev_dct = {}


def reload_dev_dct():
    global dev_dct
    reload(devs)
    dev_dct = devs.dev_dct


def update_dev_dct_file(bl_config_path, old_dct, new_dct):
    """
    update the devs.py file of dicts which is used as the main starting place for device database creation
    """
    skip_lst = ["connected", "sim", "enable", "units", "rd_only", "con_chk_nm"]
    with open(pathlib.PurePath(bl_config_path.as_posix(), "devs.py"), "r") as f:
        in_lines = f.readlines()
    f.close()
    num_inlines = len(in_lines)
    out_lines = []
    for l in in_lines:
        # l = l.replace('\n','')
        for k, search_val in old_dct.items():
            if k not in skip_lst:
                if k in new_dct.keys():
                    replace_val = new_dct[k]
                    l = l.replace(search_val, replace_val)
        out_lines.append(l)

    if num_inlines == len(out_lines):
        fpath = pathlib.PurePath(bl_config_path.as_posix(), "output.py")
        with open(fpath, "w") as fout:
            for ll in out_lines:
                fout.write(ll)
        fout.close()
        # p = pathlib.Path(fpath)
        # p.replace('devs.py')
        fstr = fpath.as_posix()
        new_fstr = fstr.replace("output.py", "devs.py")
        os.replace(fstr, new_fstr)
        print("The file was exported properly")
    else:
        print("there was an error so not exporting a corrupted file")


class Device_Configure(QtWidgets.QWidget):
    def __init__(self, bl_config_path):
        super(Device_Configure, self).__init__(None)
        uic.loadUi(os.path.join(os.getcwd(), "device_cfg.ui"), self)
        self.devsmodel = QtGui.QStandardItemModel()
        self.disconDevsmodel = QtGui.QStandardItemModel()
        self.rootNode = self.devsmodel.invisibleRootItem()
        self.devsLstView.setModel(self.devsmodel)
        self.disconLstView.setModel(self.disconDevsmodel)

        self.devsLstView.clicked.connect(self.on_dev_selected)
        self.disconLstView.clicked.connect(self.on_dev_selected)
        self.testConnBtn.clicked.connect(self.on_test_connection)
        self.updateDevBtn.clicked.connect(self.on_update_dev)

        self.bl_config_path = bl_config_path
        self.devdb_path = pathlib.PurePath(
            os.path.join(bl_config_path, "device_db.json")
        )

        # self.devTreeView.setModel(self.devsmodel)
        self.threadpool = QtCore.QThreadPool()
        self.dev_db = None
        self.cur_cat = ""

        # need to keep a pre change and post change state of a selected device
        self.pre_devdct = {}
        self.post_devdct = {}

        self.retestBtn.clicked.connect(self.on_retest)
        self.devCatCmboBx.currentIndexChanged.connect(self.on_cat_selected)
        self.setMinimumHeight(600)
        self.do_threaded_many_check()

    def on_dev_selected(self, index):
        """
        function to handle when a new device is selected from the device compbo box
        :param index:
        :return:
        """
        lstView = self.sender()
        self.cur_dev = lstView.model().data(index)
        _dct = self.dev_db.search(_q.name == self.cur_dev)[0]
        # init pre_devdct
        self.pre_devdct = copy.copy(_dct)
        self.selNmFld.setText(_dct["name"])
        self.selDescFld.setText(_dct["desc"])
        self.selDcsNmFld.setText(_dct["dcs_nm"])
        self.set_combo_box_to_txt(self.selCtgCmboBx, _dct["category"])
        self.set_combo_box_to_txt(self.selDevTypeCmboBx, _dct["devtype"])
        if _dct["connected"]:
            clr = "green"
        else:
            clr = "red"
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
        dct = self.dev_db.search(_q.name == nm)[0]
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

    def populate_devnames_lstview(self, lst=None):
        # clean listview
        # if self.devsmodel.rowCount() > 0:
        #     self.devsmodel.removeRows(0, self.devsmodel.rowCount())
        self.devsmodel.clear()
        self.disconDevsmodel.clear()
        if lst is None:
            lst = self.dev_db.all()
        num_poss_cons = len(lst)
        num_cons = len(self.dev_db.search(_q.connected == True))
        # posners = self.dev_db.search(_q.category == 'POSITIONERS')
        self.numSignalsLbl.setText(
            f"{num_cons} connected out of a possible {num_poss_cons} signals"
        )

        # keys = []
        keys = list([" "] + list(dev_dct.keys()))
        types = [" "]
        hash_lst = []
        self.load_combo_box(self.selCtgCmboBx, keys)
        for l_dct in lst:
            dnm = l_dct["name"]
            # print(dnm)
            desc = l_dct["desc"]
            sim = l_dct["sim"]
            en = l_dct["enable"]
            dcs_nm = l_dct["dcs_nm"]
            type_hash = hash(l_dct["devtype"])
            if type_hash not in hash_lst:
                hash_lst.append(type_hash)
                types.append(l_dct["devtype"])
            item1 = QtGui.QStandardItem(dnm)
            if l_dct["connected"]:
                clr = "green"
                self.devsmodel.appendRow(item1)
            else:
                clr = "red"
                self.disconDevsmodel.appendRow(item1)
            item1.setData(
                QtGui.QIcon(os.path.join("images", "%s.png" % clr)),
                QtCore.Qt.DecorationRole,
            )
            item1.setToolTip(dcs_nm)
            self.load_combo_box(self.selDevTypeCmboBx, types)

    def init_devCategories(self):
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
            dev_dct_lst = self.dev_db.search(_q.category == self.cur_cat)
        self.populate_devnames_lstview(lst=dev_dct_lst)

    def on_retest(self):
        self.do_threaded_many_check()

    def do_threaded_many_check(self):
        # worker = Worker(self.build_database) #, delay_return=0.5)  # Any other args, kwargs are passed to the run function
        # worker.signals.result.connect(self.load_results)
        # self.threadpool.start(worker)
        # self.numSignalsLbl.setText('Checking PV connections and building database, one moment')
        # #print('Checking PV connections and building database, one moment')
        self.build_database()
        self.populate_devnames_lstview()

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

    def build_database(self):  # , db_fpath='db.json'):
        global dev_dct
        reload_dev_dct()
        verbose = False
        if self.dev_db:
            self.dev_db.close()
        self.dev_db = TinyDB(self.devdb_path.as_posix())
        self.dev_db.drop_tables()
        self.init_devCategories()
        con_sts = devs.get_connections_status()
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
        # print('DONE build_database')
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

    app = QtWidgets.QApplication([])
    # get bl_config_dir from the command line
    bl_config_dirname = sys.argv[1]
    dbpath = pathlib.PurePath(
        os.path.join(
            pathlib.Path(pathlib.os.getcwd()).parent.as_posix(), bl_config_dirname
        )
    )
    if pathlib.Path(dbpath).exists():
        import_Str = f"cls.applications.pyStxm.bl_configs.{bl_config_dirname}.devs"
        devs = importlib.import_module(import_Str, package=None)
        gen_device_names_file(dbpath, devs.dev_dct)
        dcfg = Device_Configure(dbpath)
        dcfg.show()
    else:
        print(f"Error: db path [{str(dbpath)}] does not exist")
    sys.exit(app.exec_())
