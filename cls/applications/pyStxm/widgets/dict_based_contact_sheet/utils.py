import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from PyQt5 import QtGui

from cls.utils.roi_dict_defs import *

ICONSIZE = 21
THUMB_WIDTH = 100
THUMB_HEIGHT = 120
THUMB_ACTIVE_AREA_WD = 80
THUMB_ACTIVE_AREA_HT = 80

MAX_THUMB_COLUMNS = 3
THMB_SIZE = 90

# Create a grayscale color table
COLORTABLE = []
for i in range(256):
    COLORTABLE.append(QtGui.qRgb(i, i, i))

# appConfig = ConfigClass(abs_path_to_ini_file)
icoDir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..","icons"
)



def get_max_thumb_columns(view_width):
    """Calculate maximum number of thumbnail columns that can fit in the given width"""
    # Account for margins and spacing
    available_width = view_width - THUMB_VIEW_MARGINS
    thumb_total_width = THUMB_ACTIVE_AREA_WD + THUMB_VIEW_HORZ_SPACE

    # Ensure at least 1 column
    columns = max(1, int(available_width / thumb_total_width))
    return columns


def make_thumb_widg_dct(data_dir: str, fname: str, entry_dct: dict, counter: Optional[str] = None) -> Dict[str, Any]:
    """
    a convienience function to create a 'standard' dict for use by thumb widgets
    :param data_dir:
    :param fname:
    :param entry_dct:
    :param counter:
    :return:
    """
    if counter is None and "default" in entry_dct:
        counter = next(iter(entry_dct.keys()))
    dct = {}
    dct["id"] = "temp_thumb_widg_dct"
    dct["data_dir"] = data_dir
    dct["fprefix"] = fname
    dct["counter"] = counter
    dct["entries"] = entry_dct
    return dct


def get_first_entry_key(entries_dct: dict) -> str:
    """
    use the default attribute to return the default entry name to use
    :param entries_dct:
    :return:
    """
    # support for older nexus files
    if "default" in entries_dct:
        return entries_dct["default"]
    return None

def get_sp_db_dct_from_data_dct(data_dct: dict) -> dict:
    """
    Extract the sp_db_dct from the data_dct.
    :param data_dct: Dictionary containing the data structure.
    :return: The sp_db_dct.
    """
    ekey = get_first_entry_key(data_dct)
    if ekey is None:
        return None
    entry_dct = data_dct[ekey]
    if "sp_db_dct" in entry_dct:
        return entry_dct["sp_db_dct"]
    elif "entry1" in entry_dct and "sp_db_dct" in entry_dct["entry1"]:
        return entry_dct["entry1"]["sp_db_dct"]
    else:
        raise KeyError("No 'sp_db_dct' found in the provided data dictionary.")

def get_first_sp_db_from_entry(entry_dct: dict) -> dict:
    return get_first_sp_db_from_wdg_com(entry_dct["WDG_COM"])


def get_first_sp_db_from_wdg_com(wdg_com: dict) -> dict:
    sp_id = next(iter(wdg_com["SPATIAL_ROIS"]))
    return wdg_com["SPATIAL_ROIS"][sp_id]


def get_axis_setpoints_from_sp_db(sp_db: dict, axis: str = "X") -> Optional[list]:
    return sp_db[axis][SETPOINTS] if axis in sp_db else None

def get_default_counter_if_exist(entry_dct: dict) -> str:
    """ given an entry dict return the counter name specified in the default attribute
    if it exists else return the first in list of detectors
    """
    return entry_dct["default"] if "default" in entry_dct else next(iter(entry_dct["data"]))

def get_generic_scan_data_from_entry(entry_dct: dict, *, counter: Optional[str] = None, get_all: bool = False) -> List[list]:
    """
    return 3D generic scan data as 1D list
    :param entry_dct:
    :param counter:
    :return:
    """
    if counter is None:
        if get_all:
            return [entry_dct["data"][k] for k in entry_dct["data"]]
        counter = get_default_counter_if_exist(entry_dct)
    #return [entry_dct["data"][counter]]
    return entry_dct["data"][counter]


def get_point_spec_data_from_entry(entry_dct: dict, counter: Optional[str] = None) -> np.ndarray:
    if counter is None:
        counter = get_default_counter_if_exist(entry_dct)
    return entry_dct["data"][counter]


def get_point_spec_energy_data_from_entry(entry_dct: dict, counter: Optional[str] = None) -> np.ndarray:
    if counter is None:
        counter = get_default_counter_if_exist(entry_dct)

    for k in entry_dct["data"][counter]:
        if str(k) in ("energy", "b'energy"):
            data = entry_dct["data"][counter][k]["signal"]
            break

    return data

def get_wdg_com_from_entry(entry_dct: dict) -> dict:
    return entry_dct['WDG_COM']

def get_spatial_rois_from_wdg_com(wdg_com: dict) -> dict:
    return wdg_com['SPATIAL_ROIS']

def get_first_sp_db_from_spatial_rois(spatial_rois: dict) -> dict:
    keys = list(spatial_rois.keys())
    return  spatial_rois[keys[0]]

def get_ev_rois_from_sp_db(sp_db: dict) -> list:
    ev_rois = sp_db['EV_ROIS']
    return ev_rois

def get_point_spec_energy_data_setpoints_from_entry(entry_dct: dict, counter: Optional[str] = None) -> np.ndarray:
    wdg_com = get_wdg_com_from_entry(entry_dct)
    spatial_rois = get_spatial_rois_from_wdg_com(wdg_com)
    sp_db = get_first_sp_db_from_spatial_rois(spatial_rois)
    ev_rois = get_ev_rois_from_sp_db(sp_db)
    data = ev_rois[0]['SETPOINTS']
    return data

def get_energy_setpoints_from_entry(entry_dct: dict, counter: Optional[str] = None) -> np.ndarray:
    wdg_com = get_wdg_com_from_entry(entry_dct)
    spatial_rois = get_spatial_rois_from_wdg_com(wdg_com)
    sp_db = get_first_sp_db_from_spatial_rois(spatial_rois)
    ev_rois = get_ev_rois_from_sp_db(sp_db)
    data = ev_rois[0]['SETPOINTS']
    return data

def extract_date_time_from_nx_time(nx_time):
    dt = nx_time.split("T")[0]
    _tm = nx_time.split("T")[1]
    tm = _tm.split(".")[0]
    return (dt, tm)

def format_info_text(
    title,
    msg,
    title_clr="blue",
    newline=True,
    start_preformat=False,
    end_preformat=False,
):
    """
    take arguments and create an html string used for tooltips
    :param title: The title will be bolded
    :param msg: The message will be simple black text
    :param title_clr: The Title will use this color
    :param newline: A flag to add a newline at the end of the string or not
    :param start_preformat: If this is the first string we need to start the PREformat tag
    :param end_preformat: If this is the last string we need to stop the PREformat tag
    :return:
    """
    s = ""
    if start_preformat:
        s += "<pre>"

    if newline:
        s += '<font size="3" color="%s"><b>%s</b></font> %s<br>' % (
            title_clr,
            title,
            msg,
        )
    else:
        s += '<font size="3" color="%s"><b>%s</b></font> %s' % (
            title_clr,
            title,
            msg,
        )

    if end_preformat:
        s += "</pre>"
    return s
