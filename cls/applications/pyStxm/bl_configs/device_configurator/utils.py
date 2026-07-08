import os
import pathlib
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

query = Query()
X_AXIS = 1
Y_AXIS = 2


dev_dct = {}


def reload_dev_dct(devs):
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


def gen_device_names_file(fpath, dev_dct):
    # create a device_names.py file that can be imported by other modules
    # p = pathlib.Path(os.path.abspath(__file__))
    fpath = pathlib.PurePath(os.path.join(fpath.parent.as_posix(), "device_names.py"))
    with open(fpath.as_posix(), "w") as f:
        for sect_nm, sect_lst in dev_dct.items():
            for dct in sect_lst:
                if dct["name"].find("DNM_") > -1:
                    f.write("%s = '%s'\n" % (dct["name"], dct["name"]))


def get_zmq_connections_status(dev_dct=None):
    dev_pvlist = []
    con_lst = []
    # map each device dcs name to the connection string that should be checked
    # (which may include con_chk_nm suffix)
    con_name_by_dev = {}
    if dev_dct is None:
        raise f"Error: no dict provided to get_zmq_connections_status function"
    else:
        keys = list(dev_dct.keys())

    for k in keys:
        # get all the signal names
        dlist = dev_dct[k]
        for sig_dct in dlist:
            if isinstance(sig_dct, dict):
                if "dcs_nm" in sig_dct.keys():
                    dcs_nm = str(sig_dct.get("dcs_nm", "") or "").strip()
                    if "con_chk_nm" in sig_dct.keys():
                        con_nm = dcs_nm + str(sig_dct.get("con_chk_nm", ""))
                    else:
                        con_nm = dcs_nm
                    dev_pvlist.append(dcs_nm)
                    con_name_by_dev[dcs_nm] = con_nm
            else:
                if sig_dct.find("POS_TYPE") > -1:
                    dlist = dev_dct[k][sig_dct]
                    for _dct in dlist:
                        if "dcs_nm" in _dct.keys():
                            dcs_nm = str(_dct.get("dcs_nm", "") or "").strip()
                            if "con_chk_nm" in _dct.keys():
                                con_nm = dcs_nm + str(_dct.get("con_chk_nm", ""))
                            else:
                                con_nm = dcs_nm
                            dev_pvlist.append(dcs_nm)
                            con_name_by_dev[dcs_nm] = con_nm

    # only send valid, non-empty channel names to epics.ca.create_channel
    valid_con_lst = [nm for nm in con_name_by_dev.values() if isinstance(nm, str) and nm.strip()]
    # the list for connections might not be same as the sig_name required to create an instance of the device
    # so for purposes of finding out IS THERE A CONNECTION just make sure to specify an actual PV not just a prefix
    cons = con_check_many(valid_con_lst) if len(valid_con_lst) > 0 else []
    con_status_by_con_name = dict(zip(valid_con_lst, cons))

    # Default any invalid/empty dcs names to disconnected instead of raising.
    both = {}
    for dcs_nm in dev_pvlist:
        con_nm = con_name_by_dev.get(dcs_nm, "")
        both[dcs_nm] = con_status_by_con_name.get(con_nm, False)
    return both


def get_connections_status(dev_dct=None):
    dev_pvlist = []
    con_lst = []
    if dev_dct is None:
        raise f"Error: no dict provided to get_zmq_connections_status function"
    else:
        keys = list(dev_dct.keys())

    for k in keys:
        # get all the signal names
        dlist = dev_dct[k]
        for sig_dct in dlist:
            if isinstance(sig_dct, dict):
                if "dcs_nm" in sig_dct.keys():
                    if "con_chk_nm" in sig_dct.keys():
                        con_lst.append(sig_dct["dcs_nm"] + sig_dct["con_chk_nm"])
                    else:
                        con_lst.append(sig_dct["dcs_nm"])
                    dev_pvlist.append(sig_dct["dcs_nm"])
            else:
                if sig_dct.find("POS_TYPE") > -1:
                    dlist = dev_dct[k][sig_dct]
                    for _dct in dlist:
                        if "dcs_nm" in _dct.keys():
                            if "con_chk_nm" in _dct.keys():
                                con_lst.append(_dct["dcs_nm"] + _dct["con_chk_nm"])
                            else:
                                con_lst.append(_dct["dcs_nm"])
                            dev_pvlist.append(_dct["dcs_nm"])
    # the list for connections might not be same as the sig_name required to create an instance of the device
    # so for purposes of finding out IS THERE A CONNECTION just make sure to specify an actual PV not just a prefix
    cons = con_check_many(con_lst)
    both = dict(zip(dev_pvlist, cons))
    return both


def make_MotorQt(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'pos_type': '',
        'units': '',
        'class': 'MotorQt',
        'abstract_mtr': False,
        'enums': [],
        'enum_values': []
    }
    dct.update(kwargs)
    return dct

def make_sample_abstract_motor(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'fine_mtr_name': '',
        'coarse_mtr_name': '',
        'pos_type': '',
        'class': 'sample_abstract_motor',
    }
    dct.update(kwargs)
    return dct

def make_DCSShutter(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'class': 'DCSShutter',
        "ctrl_enum_strs": ["Auto", "Open", "Closed", "Auto Line"],
        "fbk_enum_strs": ["CLOSED", "OPEN"],
    }
    dct.update(kwargs)
    return dct

def make_make_basedevice(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'units': '',
        'class': 'make_basedevice',
    }
    dct.update(kwargs)
    return dct

def make_Counter(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'class': 'Counter',
    }
    dct.update(kwargs)
    return dct

def make_make_base_simdevice(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'class': 'make_base_simdevice',
    }
    dct.update(kwargs)
    return dct

def make_MultiSelectable(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'class': 'MultiSelectable',
    }
    dct.update(kwargs)
    return dct

def make_Bo(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'class': 'Bo',
    }
    dct.update(kwargs)
    return dct

def make_Command(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'class': 'Command',
        'arg_keywords': [],
    }
    dct.update(kwargs)
    return dct

def make_EnergyDevice(**kwargs):
    dct = {
        'name': '',
        'desc': 'No description in config',
        'dcs_nm': '',
        'energy_nm': '',
        'zz_nm': '',
        'cz_nm': '',
        'pos_type': '',
        'class': 'EnergyDevice',
    }
    dct.update(kwargs)
    return dct