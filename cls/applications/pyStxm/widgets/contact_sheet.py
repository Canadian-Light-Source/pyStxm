"""
Created on 2016-10-11

@author: bergr

"""
import sys
import os
import itertools
import math
import queue
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import simplejson as json
import pathlib

from PyQt5 import QtCore, QtGui, QtWidgets

from PIL import Image

from bcm.devices.epu import convert_wrapper_epu_to_str
from cls.utils.arrays import flip_data_upsdown
from cls.utils.images import array_to_gray_qpixmap
from cls.utils.images import array_to_image
#from cls.applications.pyStxm import abs_path_to_ini_file
from cls.applications.pyStxm.widgets.print_stxm_thumbnail import PrintSTXMThumbnailWidget
from cls.stylesheets import get_style
from cls.appWidgets.dialogs import setExistingDirectory, getOpenFileName
from cls.appWidgets.thread_worker import Worker
from cls.utils.arrays import flip_data_upsdown
from cls.utils.dirlist import dirlist, dirlist_withdirs
from cls.utils.fileUtils import get_file_path_as_parts
from cls.utils.log import get_module_logger, log_to_qt
#from cls.utils.cfgparser import ConfigClass
from cls.utils.dict_utils import dct_get, dct_put, find_key_in_dict
from cls.utils.roi_utils import make_base_wdg_com, widget_com_cmnd_types
from cls.utils.pixmap_utils import get_pixmap
from cls.utils.hdf_to_dict import (get_sp_db_from_entry_dict,
                                   get_energy_setpoints, get_pystxm_scan_type_from_file_dct,
                                   get_pystxm_scan_type_from_file_dct, get_first_sp_db_from_file_dct,
                                   hdf5_to_dict, get_default_data_from_hdf5_file) # read_hdf5_nxstxm_file_with_attributes

from cls.plotWidgets.lineplot_thumbnail import OneD_MPLCanvas
from cls.plotWidgets.curveWidget import (
    get_next_color,
    get_basic_line_style,
    make_spectra_viewer_window,
    reset_color_idx,
)

from cls.applications.pyStxm.widgets.print_stxm_thumbnail import (
    SPEC_THMB_WD,
    SPEC_THMB_HT,
)

from cls.types.stxmTypes import (
    spatial_type_prefix,
    image_types,
    scan_image_types,
    scan_types,
    scan_sub_types,
    sample_positioning_modes,
    spectra_type_scans,
    image_type_scans,
    stack_scans
)
from cls.stylesheets import master_colors
from cls.plotWidgets.imageWidget import make_default_stand_alone_stxm_imagewidget
from cls.utils.roi_dict_defs import *
from cls.utils.fileSystemMonitor import DirectoryMonitor

from cachetools import (
    cached,
    TTLCache,
)  # 1 - let's import the "cached" decorator and the "TTLCache" object from cachetools

cache = TTLCache(maxsize=100, ttl=300)  # 2 - let's create the cache object.

# appConfig = ConfigClass(abs_path_to_ini_file)
icoDir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "icons"
)

_logger = get_module_logger(__name__)

MAX_THUMB_COLUMNS = 3
THMB_SIZE = 90
SCENE_WIDTH = 290.0
THUMB_WIDTH = 150.0
THUMB_HEIGHT = 130.0

THUMB_ACTIVE_AREA_WD = 90
THUMB_ACTIVE_AREA_HT = 112
THUMB_VIEW_MARGINS = 10
THUMB_VIEW_HORZ_SPACE = 20
THUMB_VIEW_VERT_SPACE = 15

ICONSIZE = 21
BTNSIZE = 25

COLORTABLE = [QtGui.qRgb(i // 4, i, i // 2) for i in range(256)]


def get_max_thumb_columns(area_width):
    return int(max(1, ((area_width) // (THUMB_ACTIVE_AREA_WD + THUMB_VIEW_HORZ_SPACE))))


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
    if "default" in entries_dct["entries"]:
        return entries_dct["entries"]["default"]
    return next(iter(entries_dct["entries"]))


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

class ThumbnailWidget(QtWidgets.QGraphicsWidget):
    update_view = QtCore.pyqtSignal()
    select = QtCore.pyqtSignal(object)
    launch_viewer = QtCore.pyqtSignal(object)
    print_thumb = QtCore.pyqtSignal(object)
    preview_thumb = QtCore.pyqtSignal(object)
    drag = QtCore.pyqtSignal(object, object)
    dbl_clicked = QtCore.pyqtSignal(object)

    def __init__(
        self,
        fname,
        sp_db,
        data,
        title,
        info_dct,
        scan_type=None,
        dct={},
        is_folder=False,
        parent=None,
    ):
        """
        __init__(): description

        :param fname: fname description
        :type fname: fname type

        :param sp_db: sp_db description
        :type sp_db: sp_db type

        :param data: data description
        :type data: data type

        :param title: title description
        :type title: title type

        :param info_dct: info_dct description
        :type info_dct: info_dct type

        :param scan_type=scan_types.SAMPLE_IMAGE one of the defined scan_types
        :type scan_type=int:  integer enumeration

        :param entry_dct= dictionary of entries
        :type entry_dct=int:  dict

        :param is_folder=False: is this a folder icond thumbnail
        :type is_folder=False: bool type

        :param parent=None: parent=None description
        :type parent=None: parent=None type



        :returns: None
        """
        """
        This class is used to create a single graphics widget that displays a thumbnail of
        a stxm image data, the thumbnail is created from the data section of the hdf5 file
        """
        QtWidgets.QGraphicsWidget.__init__(self, parent=None)
        self.parent = parent
        fname = str(fname)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)

        if title is None:
            self.title = str(fprefix)
        else:
            self.title = title

        self.data = data
        self.sp_db = sp_db
        self.dct = dct
        self.labelheight = 20
        self.bordersize = 1
        self.is_folder = is_folder

        self.launchAction = None

        self.hdf5_path = fname
        self.data_dir = data_dir
        self.fname = fname
        self.fprefix = fprefix
        self.fpref_and_suff = fprefix + fsuffix
        self.scan_type = scan_type
        self.counter = None
        self.progbar = None

        self.pen = QtGui.QPen()
        self.pen.setWidth(2)
        self.pen.setBrush(QtCore.Qt.black)
        self.pen.setStyle(QtCore.Qt.SolidLine)
        self.is_selected = False
        self.valid_file = False
        self.pic = None
        self.info_str = info_dct["info_str"]
        self.info_jstr = info_dct["info_jstr"]

        if is_folder:
            self.getpic = self.get_folder_pic

        elif self.scan_type in spectra_type_scans:
            if self.scan_type is scan_types.GENERIC_SCAN:
                self.getpic = self.get_generic_scan_pic
            else:
                self.getpic = self.get_specplot_pic
        else:
            self.getpic = self.get_2dimage_pic

        self.pic = self.getpic()
        if self.pic:
            self.valid_file = True
            self.setToolTip(self.info_str)
            self.setAcceptHoverEvents(True)
        else:
            self.valid_file = False
            _logger.error(f"The file [{self.fname}] contains data that can't be plotted")

    def contextMenuEvent(self, event):
        """
        Create the popup menu for a right click on a thumbnail, what is on the menu depends on data
        
        :param event: event description
        :type event: event type

        :returns: None
        """
        if self.data is None:
            #most likely a stack thumbnail
            return
        menu = QtWidgets.QMenu()
        launchAction = QtWidgets.QAction("Send to Viewer", self)
        prevAction = QtWidgets.QAction("Print Preview", self)
        saveTiffAction = QtWidgets.QAction("Save as Tiff file", self)

        menu.addAction(prevAction)
        menu.addAction(launchAction)
        if self.data.ndim > 1:
            #only allow saving a tiff if it is 2D image data
            menu.addAction(saveTiffAction)

        selectedAction = menu.exec_(event.screenPos())
        if launchAction == selectedAction:
            self.launch_vwr(self)
        elif prevAction == selectedAction:
            self.preview_it(self)
        elif saveTiffAction == selectedAction:
            self.save_tif(self)

    def print_it(self, sender):
        """
        call PrintSTXMThumbnailWidget()
        :param sender:
        :return:
        """
        self = sender
        info_dct = json.loads(self.info_jstr)

        dct = {}
        dct["fpath"] = self.fname
        dct["fname"] = self.fpref_and_suff
        dct["data_pmap"] = self.getpic(scale_it=False)
        dct["contrast_pmap"] = None
        dct["xstart"] = 0
        dct["ystart"] = 0
        dct["xstop"] = info_dct["range"][0]
        dct["ystop"] = info_dct["range"][1]
        dct["xpositioner"] = info_dct["xpositioner"]
        dct["ypositioner"] = info_dct["ypositioner"]
        type_tpl = info_dct["scan_type"].split()
        dct["scan_type"] = type_tpl[0]
        dct["scan_type_num"] = info_dct["scan_type_num"]
        dct["scan_sub_type"] = type_tpl[1]
        dct["data_dir"] = self.data_dir

        dct["data_min"] = self.data.min()
        dct["data_max"] = self.data.max()

        dct["info_dct"] = info_dct

        self.print_thumb.emit(dct)

    def preview_it(self, sender):
        """
        call PrintSTXMThumbnailWidget()
        :param sender:
        :return:
        """
        self = sender
        info_dct = json.loads(self.info_jstr)
        # ekey = self.get_first_entry_key(self.dct)
        # def_counter = self.dct['entries'][ekey]['default']
        dct = {}
        dct["fpath"] = self.fname
        dct["fname"] = self.fpref_and_suff
        # dct['data_pmap'] = self.getpic(scale_it=False, as_thumbnail=False)
        dct["data_pmap"] = self.getpic(scale_it=True, as_thumbnail=False)
        dct["contrast_pmap"] = None
        dct["xstart"] = info_dct["start"][0]
        dct["ystart"] = info_dct["start"][1]
        dct["xstop"] = info_dct["stop"][0]
        dct["ystop"] = info_dct["stop"][1]
        dct["xcenter"] = info_dct["center"][0]
        dct["ycenter"] = info_dct["center"][1]
        dct["xrange"] = info_dct["range"][0]
        dct["yrange"] = info_dct["range"][1]
        dct["xpositioner"] = info_dct["xpositioner"]
        dct["ypositioner"] = info_dct["ypositioner"]

        type_tpl = info_dct["scan_type"].split()
        dct["scan_type"] = type_tpl[0]
        dct["scan_type_num"] = info_dct["scan_type_num"]
        dct["scan_sub_type"] = type_tpl[1]
        dct["data_dir"] = self.data_dir

        if dct["scan_type"] == scan_types[scan_types.SAMPLE_POINT_SPECTRUM]:
            dct["data_min"] = self.data.min()
            dct["data_max"] = self.data.max()
        else:

            if self.data is not None:
                dct["data_min"] = self.data.min()
                dct["data_max"] = self.data.max()
            else:
                _logger.error("self.data cannot be None")
                return

        dct["info_dct"] = info_dct
        dct["counter_nm"] = 'counter'

        # print 'print_it called: %s'% self.fname

        self.preview_thumb.emit(dct)

    def save_tif(self, sender):
        """
        call save_tif(), when saving a tif file keep the dimensions the same as the data, only thunmbnails
        are square
        :param sender:
        :return:
        """
        self = sender
        _data = flip_data_upsdown(self.data)
        rows, cols = _data.shape
        im = array_to_image(_data)
        # make sure tifs are at least 100x100
        if rows < cols:
            # scale by rows
            if rows < 100:
                _fctr = int(100 / rows)
                rows = int(_fctr * rows)
                cols = int(_fctr * cols)
        else:
            if cols < 100:
                _fctr = int(100 / cols)
                rows = int(_fctr * rows)
                cols = int(_fctr * cols)
        # im = im.resize([rows, cols], Image.NEAREST)  # Image.ANTIALIAS)  # resizes to 256x512 exactly
        im = im.resize(
            [cols, rows], Image.NEAREST
        )  # Image.ANTIALIAS)  # resizes to 256x512 exactly
        im.save(self.fname.replace(".hdf5", ".tif"))

    def create_gradient_pmap(self, _min, _max):
        box = QtCore.QSize(20, THUMB_HEIGHT)
        self.maskPixmap = QtGui.QPixmap(box)
        self.maskPixmap.fill(QtCore.Qt.transparent)
        g = QtGui.QLinearGradient()
        g.setStart(0, 0)
        g.setFinalStop(0, box.height())
        # white at top
        g.setColorAt(0, QtGui.QColor(255, 255, 255, 0))
        # black at bottom
        g.setColorAt(1.0, QtGui.QColor(0, 0, 0, 255))

    def is_valid(self):
        """
        is_valid(): description

        :returns: None
        """
        return self.valid_file

    def boundingRect(self):
        """
        boundingRect(): this returns the rect for the entire thumbwidget, so base it on total
        size not the size ofthe data pixmap

        :returns: None
        black_pm = QtGui.QPixmap(THMB_SIZE, THMB_SIZE)
        """
        thumb_widget_rect = QtCore.QRectF(
            0.0, 0.0, THUMB_ACTIVE_AREA_WD, THUMB_ACTIVE_AREA_HT
        )
        return thumb_widget_rect

    def sizeHint(self, which, constraint=QtCore.QSizeF()):
        """
        sizeHint(): description

        :param which: which description
        :type which: which type

        :param constraint=QtCore.QSizeF(): constraint=QtCore.QSizeF() description
        :type constraint=QtCore.QSizeF(): constraint=QtCore.QSizeF() type

        :returns: None
        """
        br = self.boundingRect()
        return br.size()

    def get_generic_scan_pic(self, scale_it=True, as_thumbnail=True):
        """

        :param scale_it:
        :return:
        """
        ekey = self.get_first_entry_key(self.dct)
        entry_dct = self.dct["entries"][ekey]
        sp_db = self.get_first_sp_db_from_file_dct(entry_dct)
        xdata = get_axis_setpoints_from_sp_db(sp_db, axis="X")
        counter = None
        #older nxstxm files may not have used the default attribute
        if "default" in entry_dct:
            counter = entry_dct["default"]

        ydatas = get_generic_scan_data_from_entry(entry_dct, counter=counter)

        if len(xdata) <= 1:
            pmap = QtGui.QPixmap()

        elif len(xdata) != len(ydatas):
            # data in file is not valid for plotting
            return None

        elif as_thumbnail:
            # return a lower res pmap for use as a thumbnail image
            qt_mpl = OneD_MPLCanvas(
                xdata,
                ydatas,
                width=2,
                height=1.65,
                dpi=200,
                axes_bgrnd_color="#FFFFFF",
            )
            pmap = qt_mpl.get_pixmap(as_grayscale=True, as_thumbnail=True)
        else:
            # return a higher res pixmap for eventual printing
            qt_mpl = OneD_MPLCanvas(xdata, ydatas, width=2, height=1.65, dpi=2000)
            pmap = qt_mpl.get_pixmap(as_grayscale=False, as_thumbnail=False)
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(SPEC_THMB_WD, SPEC_THMB_HT)),
                QtCore.Qt.KeepAspectRatio,
            )

        if as_thumbnail:
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(THMB_SIZE, THMB_SIZE)),
                QtCore.Qt.KeepAspectRatio,
            )

        return pmap

    def get_folder_pic(self, scale_it=True, as_thumbnail=True):
        """
        pmap = get_pixmap(os.path.join(icoDir, 'reload.ico'), ICONSIZE, ICONSIZE)
        :param scale_it:
        :type scale_it: bool
        :parm as_thumbnail:
        :type as_thumbnail: bool
        :parm fldr_type:
        :type fldr_type: a string either 'stack' or 'tomo'
        :return:
        """
        sz_x = 222
        sz_y = 164

        if self.title.find(".") > -1:
            # image_fname = 'updir.png'
            # image_fname = 'open-folder-icon-png.png'
            image_fname = "directory_up_bw.png"

        else:
            if self.scan_type is scan_types.SAMPLE_IMAGE_STACK:
                image_fname = "stack.bmp"
            elif self.scan_type is scan_types.TOMOGRAPHY:
                # image_fname = 'tomo.png'
                image_fname = "folder_bw_tomo.png"
            else:
                image_fname = "folder_bw.ico"

        if as_thumbnail:
            # return a lower res pmap for use as a thumbnail image
            pmap = get_pixmap(os.path.join(icoDir, image_fname), sz_x, sz_y)
        else:
            # return a higher res pixmap for eventual printing
            pmap = get_pixmap(os.path.join(icoDir, image_fname), sz_x, sz_y)
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(SPEC_THMB_WD, SPEC_THMB_HT)),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

        if as_thumbnail:
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(THMB_SIZE, THMB_SIZE)),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

        return pmap
    def get_first_entry_key(self, info_dct):
        ekey = info_dct['entries']['default']
        return ekey

    def get_first_sp_db_from_file_dct(self, entry_dct):
        """
        given a file_dct retrieve the first spatial database
        """
        sp_id = list(entry_dct[WDG_COM][SPATIAL_ROIS].keys())[0]
        sp_db = entry_dct[WDG_COM][SPATIAL_ROIS][sp_id]
        return sp_db

    def get_point_spec_energy_data_from_entry(self, sp_db):
        """
        pull the energy spec points from sp_db
        """

        print()

    def get_specplot_pic(self, scale_it=True, as_thumbnail=True):
        """

        :param scale_it:
        :return:
        """
        info_dct = json.loads(self.info_jstr)
        # ekey = self.get_first_entry_key(self.dct)
        # entry_dct = self.dct["entries"][ekey]
        # if "default" in entry_dct.keys():
        #     self.counter = entry_dct["default"]
        ekey = get_first_entry_key(self.dct)
        entry_dct = self.dct["entries"][ekey]
        xdata = get_point_spec_energy_data_setpoints_from_entry(entry_dct)
        ydatas = get_point_spec_data_from_entry(entry_dct)

        if len(xdata) <= 1:
            pmap = QtGui.QPixmap()
        else:
            if as_thumbnail:
                # return a lower res pmap for use as a thumbnail image
                # use a white background
                qt_mpl = OneD_MPLCanvas(
                    xdata,
                    ydatas,
                    width=2,
                    height=1.65,
                    dpi=50,
                    axes_bgrnd_color="#FFFFFF",
                )
                pmap = qt_mpl.get_pixmap(as_grayscale=True, as_thumbnail=True)
            else:
                # return a higher res pixmap for eventual printing
                # qt_mpl = OneD_MPLCanvas(xdata, ydatas, width=2, height=1.65, dpi=2000, axes_bgrnd_color='#FFFFFF')
                # qt_mpl = OneD_MPLCanvas(xdata, ydatas, width=1.5, height=0.68, dpi=1000, axes_bgrnd_color='#FFFFFF')
                qt_mpl = OneD_MPLCanvas(
                    xdata,
                    ydatas,
                    width=6.2,
                    height=5.5,
                    dpi=1500,
                    axes_bgrnd_color="#FFFFFF",
                )
                pmap = qt_mpl.get_pixmap(as_grayscale=False, as_thumbnail=False)

        if as_thumbnail:
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(THMB_SIZE, THMB_SIZE)),
                QtCore.Qt.KeepAspectRatio,
            )

        return pmap

    def get_2dimage_pic(self, scale_it=True, as_thumbnail=True):
        """
        getpic(): description

        :returns: None
        """
        if self.data is not None:
            if len(self.data.shape) == 2:
                wd, ht = self.data.shape
                # data = np.flipud(self.data)
                # data = self.data
                data = flip_data_upsdown(self.data)
                shape = data.shape

            elif len(self.data.shape) == 3:
                img_seq, wd, ht = self.data.shape
                # data = np.flipud(self.data[0])
                # data = self.data[0]
                data = flip_data_upsdown(self.data[0])
                shape = data.shape

            else:
                # _logger.error('unsupported data shape')
                return None
        else:
            _logger.error(f"data is None in [{self.hdf5_path}]" )
            return None

        if data.size == 0:
            _logger.error(f"data is empty in [{self.hdf5_path}]" )
            return None
        # convert it to a QPixmap for display:
        pmap = array_to_gray_qpixmap(data)
        if scale_it:
            # pmap = pmap.scaled(QtCore.QSize(QtCore.QSize(THMB_SIZE, THMB_SIZE)),  QtCore.Qt.KeepAspectRatio)
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(THMB_SIZE, THMB_SIZE)),
                QtCore.Qt.IgnoreAspectRatio,
            )
        else:
            ht, wd = self.data.shape
            # pmap.scaled(QtCore.QSize(QtCore.QSize(wd, ht)), QtCore.Qt.KeepAspectRatio)
            pmap.scaled(QtCore.QSize(QtCore.QSize(wd, ht)), QtCore.Qt.IgnoreAspectRatio)

        return pmap

    def paint(self, painter, option, widget):
        """
        paint(): description

        :param painter: painter description
        :type painter: painter type

        :param option: option description
        :type option: option type

        :param widget: widget description
        :type widget: widget type

        :returns: None
        """
        black_pm = QtGui.QPixmap(THMB_SIZE, THMB_SIZE)
        black_pm.fill(QtCore.Qt.black)
        if self.pic is not None:
            if self.is_selected:
                self.pen.setBrush(QtCore.Qt.blue)
            else:
                self.pen.setBrush(QtCore.Qt.black)
                self.pen.setStyle(QtCore.Qt.SolidLine)

            painter.setPen(self.pen)
            # Draw border
            painter.drawRect(
                QtCore.QRect(
                    0,
                    0,
                    black_pm.rect().width() + self.bordersize,
                    black_pm.rect().height() + self.labelheight + self.bordersize,
                )
            )

            # Fill label
            painter.fillRect(
                QtCore.QRect(
                    self.bordersize,
                    self.bordersize + black_pm.rect().height(),
                    black_pm.rect().width(),
                    self.labelheight,
                ),
                QtCore.Qt.gray,
            )

            btm_rectF = QtCore.QRectF(0, 0, THMB_SIZE, THMB_SIZE)  # the left half

            # drawPixmap(const  QRectF & target, const QPixmap & pixmap, const QRectF & source)
            painter.drawPixmap(btm_rectF, black_pm, QtCore.QRectF(black_pm.rect()))

            # painter.drawPixmap(btm_rectF, self.pic, QtCore.QRectF(black_pm.rect()))
            pic_rectF = QtCore.QRectF(self.pic.rect())
            cb = black_pm.rect().center()
            # now see if the aspect ratio is equal or different, if so adjust image to sit in the center with a black border
            if self.pic.width() < self.pic.height():
                cb.setY(1)
                cp = self.pic.rect().center()
                x = int((THMB_SIZE / 2) - cp.x())
                cb.setX(x)

                painter.drawPixmap(cb, self.pic, pic_rectF)
            elif self.pic.width() > self.pic.height():
                cb.setX(1)
                cp = self.pic.rect().center()
                y = int((THMB_SIZE / 2) - cp.y())
                cb.setY(y)
                # cb is the 0,0, origin point for the drawing
                painter.drawPixmap(cb, self.pic, pic_rectF)
            else:
                painter.drawPixmap(btm_rectF, self.pic, QtCore.QRectF(black_pm.rect()))

            # Draw text
            # QRect(x, y, width, height)
            text_rect = QtCore.QRect(
                0,  # x
                black_pm.rect().y() + black_pm.rect().height(),  # y
                black_pm.rect().width(),  # width
                self.labelheight,
            )  # height
            font = painter.font()
            font.setPixelSize(11)
            painter.setFont(font)
            painter.drawText(text_rect, QtCore.Qt.AlignCenter, self.title)

    def mouseDoubleClickEvent(self, event):
        if self.is_folder:
            path = self.fname
            if self.fname.find("..") > -1:
                # we want an updir path emittted here
                path, folder = os.path.split(self.fname)
                path, folder = os.path.split(path)
                # print('DoubleClicked: [%s]' % path)
            # if currently showing directory contents and self.fname is a file, then load the stack
            if self.parent.current_contents_is_dir and os.path.isfile(path):
                self.dbl_clicked.emit(path)
            elif not self.parent.current_contents_is_dir:
                # we are currently showing a stack file and the updir double click should just reload the current directory
                #reload the directory
                self.dbl_clicked.emit(self.fname.replace("..", ""))
            else:
                # just go up a directory
                self.dbl_clicked.emit(path)

    def mousePressEvent(self, event):
        """
        mousePressEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        btn = event.button()

        if self.is_selected:
            self.is_selected = False
        else:
            self.is_selected = True

        self.select.emit(self)
        if self.pic != None:
            self.update(
                QtCore.QRectF(
                    0.0,
                    0.0,
                    self.pic.rect().width() + self.bordersize,
                    self.pic.rect().height() + self.labelheight + self.bordersize,
                )
            )
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)

        if btn == QtCore.Qt.MouseButton.LeftButton:
            self.drag.emit(self, event)

    def load_scan(self):
        """
        load_scan(): description

        :returns: None
        """
        print("loading %s.hdf5" % self.hdf5_path)

    def launch_vwr(self, sender):
        """
        launch_vwr(): description
        need to decide in here what teh scan_type is and create the data such that all data is passed that is needed to recreate the plot by curveViewer widget
        self.sp_db contains everything
        :returns: None
        """
        # print 'launch_viewer %s.hdf5' % self.hdf5_path
        self = sender
        info_dct = json.loads(self.info_jstr)
        if self.scan_type is scan_types.GENERIC_SCAN:
            ekey = self.get_first_entry_key(self.dct)
            entry_dct = self.dct["entries"][ekey]
            sp_db = get_first_sp_db_from_entry(entry_dct)
            xdata = get_axis_setpoints_from_sp_db(sp_db, axis="X")
            ydatas = get_generic_scan_data_from_entry(entry_dct, counter=None)
            dct = {}
            # because the data in the StxmImageWidget is displayed with 0Y at the btm
            # and maxY at the top I must flip it before sending it
            # dct['data'] = np.flipud(data)
            dct["data"] = None
            dct["xdata"] = xdata
            dct["ydatas"] = ydatas
            dct["path"] = self.hdf5_path
            dct["sp_db"] = self.sp_db
            dct["scan_type"] = self.scan_type
            dct["xlabel"] = dct_get(self.sp_db, SPDB_XPOSITIONER)
            dct["ylabel"] = dct_get(self.sp_db, SPDB_YPOSITIONER)
            dct["title"] = None
            if self.sp_db is not None:
                dct["title"] = self.title
            self.launch_viewer.emit(dct)

        elif self.scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
            ekey = get_first_entry_key(self.dct)
            entry_dct = self.dct["entries"][ekey]
            xdata = get_point_spec_energy_data_setpoints_from_entry(entry_dct)

            ydatas = []
            # it matters that the data is in sequential entry order
            # ekeys = sorted(self.dct['entries'].keys())
            ekeys = sorted(
                [k for k, v in self.dct["entries"].items() if k.find("entry") > -1]
            )
            for ekey in ekeys:
                entry_dct = self.dct["entries"][ekey]
                ydatas.append(get_point_spec_data_from_entry(entry_dct))
                # # ydatas.append(self.dct['entries'][ekey]['data'][self.counter]['signal'])
                #
                # #ydatas.append(get_point_spec_data_from_entry(entry_dct, counter=self.counter))
                # # by not specifying a counter it will use the counter name specified in the entries default attribute
                # #ydatas.append(get_point_spec_data_from_entry(entry_dct))
                # ydatas.append(self.data)

            dct = {}
            dct["data"] = None
            dct["xdata"] = xdata
            dct["ydatas"] = ydatas
            dct["path"] = self.hdf5_path
            dct["sp_db"] = self.sp_db
            dct["scan_type"] = self.scan_type
            dct["xlabel"] = dct_get(self.sp_db, SPDB_XPOSITIONER)
            dct["ylabel"] = dct_get(self.sp_db, SPDB_YPOSITIONER)
            dct["title"] = None
            if self.sp_db is not None:
                dct["title"] = self.title
            self.launch_viewer.emit(dct)

        else:
            data = self.data
            stack_index = None

            if self.data.ndim == 2:
                title = self.title
                num_underscores = title.count('_')
                if "." in title:
                    title = title.split(".")[0]

                if "_" in title and (num_underscores == 1):
                    # found a '_' character indicating its a stack image
                    i = int(title.split("_")[1])
                    stack_index = i
                else:
                    # its a single image
                    stack_index = 0

            dct = {}
            # because the data in the StxmImageWidget is displayed with 0Y at the btm
            # and maxY at the top I must flip it before sending it
            # dct['data'] = np.flipud(data)
            dct["data"] = data
            dct["stack_index"] = stack_index
            dct["path"] = self.hdf5_path
            dct["sp_db"] = self.sp_db
            dct["scan_type"] = self.scan_type
            dct["xlabel"] = dct_get(self.sp_db, SPDB_XPOSITIONER)
            dct["ylabel"] = dct_get(self.sp_db, SPDB_YPOSITIONER)
            dct["title"] = None
            if self.sp_db is not None:
                dct["title"] = self.title
            self.launch_viewer.emit(dct)

    def mouseHoverEvent(self, event):
        """
        mouseHoverEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        print("Widget enter")

    def mouseReleaseEvent(self, event):
        """
        mouseReleaseEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)

    def hoverEnterEvent(self, event):
        """
        hoverEnterEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        pass
        # self.pen.setStyle(QtCore.Qt.DotLine)
        # QtWidgets.QGraphicsWidget.hoverEnterEvent(self, event)

    def hoverLeaveEvent(self, event):
        """
        hoverLeaveEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """
        pass
        # self.pen.setStyle(QtCore.Qt.SolidLine)
        # QtWidgets.QGraphicsWidget.hoverLeaveEvent(self, event)




class MainGraphicsWidget(QtWidgets.QGraphicsWidget):
    def __init__(self):
        """
        __init__(): description

        :returns: None
        """
        QtWidgets.QGraphicsWidget.__init__(self)
        self.gridlayout = None
        self.cur_row = 0
        self.cur_column = 0

        self.init_layout()

    def incr_row(self):
        self.cur_row += 1

    def incr_column(self):
        self.cur_column += 1

    def reset_row(self):
        self.cur_row = 0

    def reset_column(self):
        self.cur_column = 0

    def set_cur_row(self, val):
        self.cur_row = val

    def set_cur_column(self, val):
        self.cur_column = val

    def init_layout(self):
        if self.gridlayout is not None:
            del self.gridlayout
        self.gridlayout = QtWidgets.QGraphicsGridLayout()
        self.gridlayout.setContentsMargins(THUMB_VIEW_MARGINS, THUMB_VIEW_MARGINS,
                                           THUMB_VIEW_MARGINS, THUMB_VIEW_MARGINS)
        self.gridlayout.setHorizontalSpacing(THUMB_VIEW_HORZ_SPACE)
        self.gridlayout.setVerticalSpacing(THUMB_VIEW_VERT_SPACE)
        self.setLayout(self.gridlayout)

    def rearrange_layout(self, max_columns: int):
        """Re-draw the gridlayout with a specific number of columns"""

        # no need to rearrange singular row for the same result
        if self.gridlayout.rowCount() == 1 and self.gridlayout.count() <= max_columns:
            return

        items = []
        while self.gridlayout.count() > 0:
            items.append(self.gridlayout.itemAt(0))
            self.gridlayout.removeAt(0)

        self.set_layout_size(
            QtCore.QRectF(
                0, 0, self.rect().width(), THUMB_ACTIVE_AREA_HT
            )
        )

        self.reset_row()
        self.reset_column()

        num_rows = math.ceil(len(items) / max_columns)
        rowcol = list(itertools.product(range(num_rows), range(max_columns)))

        for index, item in enumerate(items):
            row, col = rowcol[index]
            self.set_cur_row(row)
            self.set_cur_column(col)
            self.gridlayout.addItem(item, row, col)

        self.incr_column()

    def set_layout_size(self, qr):
        """
        set_layout_size(): description

        :param qr: qr description
        :type qr: qr type

        :returns: None
        """
        gwl = self.layout()
        gwl.setGeometry(qr)
        gwl.updateGeometry()

    def boundingRect(self):
        """
        boundingRect(): description

        :returns: None
        """
        # print self.gridlayout.contentsRect()
        return self.gridlayout.contentsRect()

    def clear_layout(self):
        """
        clear_layout(): description

        :returns: None
        """

        if (self.gridlayout.rowCount() == 0) and (self.gridlayout.columnCount() == 0):
            return
        for row in range(self.gridlayout.count()):
            # the count() will change as the items are removed
            # so just keep pulling them from teh top [0]
            item = self.gridlayout.itemAt(self.gridlayout.count() - 1)
            self.gridlayout.removeAt(self.gridlayout.count() - 1)
            # this call makes the thumbwidget dissappear
            item.close()
            # now delete it
            del item

        self.set_layout_size(
            QtCore.QRectF(
                0, 0, self.rect().width(), THUMB_ACTIVE_AREA_HT
            )
        )


class ContactSheet(QtWidgets.QWidget):
    def __init__(
        self, data_dir="", data_io=None, counter=None, parent=None
    ):
        """
        __init__(): description

        :param data_dir="": data_dir="" description
        :type data_dir="": data_dir="" type

        :returns: None
        """
        super(ContactSheet, self).__init__(parent)
        # QtWidgets.QWidget.__init__(parent)

        self.setStyleSheet(
            "QToolTip { color: rgb(20, 20, 20); background-color: rgb(181, 179, 181); border: 1px solid grey; }"
        )
        self.counter_nm = counter
        self.data_io_class = data_io
        self.data_io = None
        self.appname = "Contact Sheet"
        self.setObjectName("contactSheet")

        self.image_win = self.create_image_viewer()
        self.spec_win = self.create_spectra_viewer()

        self.drag_enabled = True
        self.image_thumbs = []
        self.spectra_thumbs = []
        # need a flag to set when the loaded ontents are that of a directory or the individual images of a
        # loaded stack file
        self.current_contents_is_dir = True
        self.setWindowTitle(self.appname)

        self.progbar = None
        self.threadpool = QtCore.QThreadPool()

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        font = self.tabs.font()
        font.setPixelSize(11)
        self.tabs.setFont(font)

        self.tabs.setTabPosition(QtWidgets.QTabWidget.North)

        self.images_scene = QtWidgets.QGraphicsScene()
        self.spectra_scene = QtWidgets.QGraphicsScene()

        self.images_scene.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))
        self.spectra_scene.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(50, 50, 50)))

        self.data_dir = data_dir
        self.image_file_extension = ".jpg"
        self.data_file_extension = ".hdf5"
        self.formats = "*" + self.image_file_extension

        self.dir_lbl = QtWidgets.QLabel("")
        self.dir_lbl.setAlignment(QtCore.Qt.AlignHCenter)
        font = self.dir_lbl.font()
        font.setPixelSize(11)
        font.setBold(True)
        self.dir_lbl.setFont(font)
        self.dir_lbl.contextMenuEvent = self.dirLabelContextMenuEvent

        self.refreshBtn = QtWidgets.QToolButton()
        ico_dir = icoDir
        ico_psize = "/64x64/"
        ico_clr = "gray"

        pmap = get_pixmap(os.path.join(icoDir, "reload.ico"), ICONSIZE, ICONSIZE)

        self.refreshBtn.setIcon(
            QtGui.QIcon(QtGui.QPixmap(pmap))
        )  # .scaled(48,48, QtCore.Qt.KeepAspectRatio)))
        self.refreshBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.refreshBtn.setFixedSize(BTNSIZE, BTNSIZE)
        self.refreshBtn.setToolTip("Reload current directory")
        self.refreshBtn.clicked.connect(self.reload_dir)

        self.changeDirBtn = QtWidgets.QToolButton()
        pmap = get_pixmap(os.path.join(icoDir, "folder_white.ico"), ICONSIZE, ICONSIZE)
        self.changeDirBtn.setIcon(QtGui.QIcon(QtGui.QPixmap(pmap)))
        self.changeDirBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.changeDirBtn.setFixedSize(BTNSIZE, BTNSIZE)
        self.changeDirBtn.setToolTip("Change current directory")
        self.changeDirBtn.clicked.connect(self.on_change_dir)

        self.images_view = QtWidgets.QGraphicsView(self.images_scene)
        self.spectra_view = QtWidgets.QGraphicsView(self.spectra_scene)

        self.f_queue = queue.Queue()

        self.fsys_mon = DirectoryMonitor(self.f_queue)
        self.fsys_mon.set_file_extension_filter("hdf5")
        self.fsys_mon.set_data_dir(self.data_dir)
        self.fsys_mon.changed.connect(self.update_file_list)
        # set QGraphicsView attributes
        hlayout = QtWidgets.QHBoxLayout()
        vlayout = QtWidgets.QVBoxLayout()
        vlayout.setContentsMargins(0, 0, 0, 0)
        hlayout.setContentsMargins(2, 1, 1, 1)
        hlayout.addWidget(self.refreshBtn)
        hlayout.addWidget(self.dir_lbl)
        hlayout.addWidget(self.changeDirBtn)
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.images_view)
        self.setLayout(vlayout)

        self.images_graphics_wdg = MainGraphicsWidget()
        self.images_scene.addItem(self.images_graphics_wdg)

        self.spectra_graphics_wdg = MainGraphicsWidget()
        self.spectra_scene.addItem(self.spectra_graphics_wdg)

        self.updateTimer = QtCore.QTimer()
        self.set_data_dir(data_dir, hide=True)
        self.ptnw = PrintSTXMThumbnailWidget()

        self.tabs.addTab(self.images_view, "Images")
        self.tabs.addTab(self.spectra_view, "Spectra")
        vlayout.addWidget(self.tabs)

        self.reload_mutex = QtCore.QMutex()

    def on_tab_changed(self):
        #resize
        self.resizeEvent(QtGui.QResizeEvent(QtCore.QSize(0,0),QtCore.QSize(1,1)))

    def create_image_viewer(self):
        fg_clr = master_colors["plot_forgrnd"]["rgb_str"]
        bg_clr = master_colors["plot_bckgrnd"]["rgb_str"]
        min_clr = master_colors["plot_gridmaj"]["rgb_str"]
        maj_clr = master_colors["plot_gridmin"]["rgb_str"]

        image_win = make_default_stand_alone_stxm_imagewidget(data_io=self.data_io)
        image_win.setWindowTitle("Image Viewer")
        qssheet = get_style()
        image_win.setStyleSheet(qssheet)
        image_win.set_grid_parameters(bg_clr, min_clr, maj_clr)
        image_win.set_cs_grid_parameters(fg_clr, bg_clr, min_clr, maj_clr)
        image_win.closeEvent = self.on_viewer_closeEvent
        return image_win

    def create_spectra_viewer(self):
        fg_clr = master_colors["plot_forgrnd"]["rgb_str"]
        bg_clr = master_colors["plot_bckgrnd"]["rgb_str"]
        min_clr = master_colors["plot_gridmaj"]["rgb_str"]
        maj_clr = master_colors["plot_gridmin"]["rgb_str"]

        spectra_win = make_spectra_viewer_window(data_io=self.data_io)
        spectra_win.setWindowTitle("Spectra Viewer")
        qssheet = get_style()
        spectra_win.setStyleSheet(qssheet)
        spectra_win.set_grid_parameters(bg_clr, min_clr, maj_clr)
        spectra_win.add_legend("TL")
        spectra_win.closeEvent = self.on_spec_viewer_closeEvent
        return spectra_win

    def set_drag_enabled(self, val):
        self.drag_enabled = val

    def get_drag_enabled(self):
        return self.drag_enabled

    def update_file_list(self):
        """
        an intermediate step to let network file system catch up
        """
        #need to give network file system time to write the file
        self.updateTimer.singleShot(250, self.update_file_list_from_timer)

    def update_file_list_from_timer(self):
        """
        now process the directory changes
        """
        call_task_done = False
        f_added = []
        f_removed = []
        while not self.f_queue.empty():
            resp = self.f_queue.get()
            # if ('added' in resp.keys()):
            if "added" in list(resp):
                f_added = resp["added"]
                call_task_done = True

            if "removed" in list(resp):
                f_removed = resp["removed"]
                call_task_done = True

        if call_task_done:
            self.reload_mutex.lock()
            self.on_dir_changed((f_added, f_removed))
            self.reload_mutex.unlock()
            self.f_queue.task_done()

    def dirLabelContextMenuEvent(self, event):
        """
        dirLabelContextMenuEvent(): description

        :param event: event description
        :type event: event type

        :returns: None
        """

        menu = QtWidgets.QMenu()
        chgdirAction = QtWidgets.QAction("Change Directory", self)
        chgdirAction.triggered.connect(self.on_change_dir)

        menu.addAction(chgdirAction)
        menu.exec_(event.globalPos())

    def is_stack_dir(self, data_dir):
        """
        is_stack_dir(): description

        :param data_dir: data_dir description
        :type data_dir: data_dir type

        :returns: None
        """
        if len(data_dir) > 0:
            d_lst = self.split_data_dir(data_dir)
            dname = d_lst[-1]
            fstr = os.path.join(data_dir, dname + ".hdf5")
            if os.path.exists(fstr):
                return True
            else:
                return False
        else:
            _logger.error("Invalid data directory")
            return False

    def is_stack_file(self, data_dir):
        """
        is_stack_file(): This function was added to support other labs saving stacks into files in teh main data
        directory instead of saving them to individual directories

        :param data_dir: data_dir description
        :type data_dir: data_dir type

        :returns: None
        """
        if len(data_dir) == 0:
            return False

        if data_dir.find('.hdf5') == -1:
            return False

        elif os.path.exists(data_dir):
            return True
        else:
            return False
        # else:
        #     _logger.error("Invalid data file name")
        #     return False

    def get_stack_file_name(self, data_dir):
        """
        get_stack_file_name(): description

        :param data_dir: data_dir description
        :type data_dir: data_dir type

        :returns: None
        """
        d_lst = self.split_data_dir(data_dir)
        dname = d_lst[-1]
        return dname + ".hdf5"

    def get_stack_data(self, fname):
        """
        get_stack_data(): description

        :param fname: fname description
        :type fname: fname type

        :returns: None
        """
        fname = str(fname)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        self.ensure_instance_of_data_io_class(fname)
        if data_dir is None:
            # _logger.info('Problem with file [%s]' % fname)
            return (None, None)

        entry_dct = self.get_h5_nxstxm_file_as_dict(data_dir, fprefix, fsuffix)
        if entry_dct is None:
            _logger.info("Problem with file [%s]" % fname)
            return (None, None)

        ekey = entry_dct['default']
        wdg_com = self.data_io.get_wdg_com_from_entry(entry_dct, ekey)
        sp_db = get_first_sp_db_from_wdg_com(wdg_com)
        # data = ado_obj['DATA']
        data = self.get_data_from_entry(entry_dct, ekey, stack_dir=True, fname=fname)

        return (sp_db, data)



    def get_nxstm_file_dct_and_data(self, fname, stack_dir=False):
        """
        get_sp_db_and_data(): return a spatial database dict and the data

        :param fname: fname description
        :type fname: fname type

        :returns: None
        """

        sp_db = data = None
        sp_db = {}
        fname = str(fname)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        if data_dir is None:
            _logger.info("Problem with file [%s]" % fname)
            return (sp_db, data)

        file_dct = self.get_h5_nxstxm_file_as_dict(data_dir, fprefix, fsuffix)
        if file_dct is None:
            _logger.error("Problem with file [%s]" % fname)
            return (sp_db, data)

        # this needs to look for NX_class NXentry not just 'entry' in the name
        ekeys = [k for k, v in file_dct.items() if k.find("entry") > -1]

        num_entries = len(ekeys)
        sp_db_lst = []
        data_lst = []

        if num_entries > 1:
            #only use the first one to grab data, maybe this should be the default entry's default signal data?
            ekey = ekeys[0]
            _scan_type = get_pystxm_scan_type_from_file_dct(file_dct)
            data = self.get_data_from_entry(
                file_dct, ekey, stack_dir=stack_dir, fname=fname, stype=_scan_type
            )
            sp_db = create_sp_db_from_file_dct(file_dct)

        else:
            if num_entries == 0:
                # there is a problem,
                _logger.error(
                    "get_sp_db_and_data: there is a problem with the file [%s]" % fprefix
                )
                return ([], [])
            ekey = ekeys[0]
            sp_db = file_dct
            _scan_type = get_pystxm_scan_type_from_file_dct(file_dct)
            data = self.get_data_from_entry(
                file_dct, ekey, stack_dir=stack_dir, fname=fname, stype=_scan_type
            )

        try:
            if len(data_lst) > 0:
                stack_dir = 1
                # dl = len(data_lst[0])
                dl_shape = data_lst[0].shape
                if data_lst[0].ndim == 1:
                    data = np.zeros((num_entries, dl_shape[0]))
                elif data_lst[0].ndim == 2:
                    data = np.zeros((num_entries, dl_shape[0], dl_shape[1]))
                elif data_lst[0].ndim == 3:
                    data = np.zeros(
                        (num_entries, dl_shape[0], dl_shape[1], dl_shape[2])
                    )

                # data = np.zeros((num_entries, dl_shape[0], dl_shape[1]))
                for i in range(num_entries):
                    data[i] = data_lst[i]
                sp_db = sp_db_lst[0]

        except:
            _logger.error("get_sp_db_and_data: problem with [%s]" % fname)
        if stack_dir:
            return (sp_db_lst, data_lst)
        else:
            return (sp_db, data)


    def get_nxstm_file_dct_and_stack_data(self, fname):
        """
        get_sp_db_and_data(): return a spatial database dict and the data

        :param fname: fname description
        :type fname: fname type

        :returns: None
        """
        stack_dir = True

        sp_db = data = None
        sp_db = {}
        fname = str(fname)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        if data_dir is None:
            _logger.info("Problem with file [%s]" % fname)
            return (sp_db, data)

        file_dct = self.get_h5_nxstxm_file_as_dict(data_dir, fprefix, fsuffix)
        if file_dct is None:
            _logger.info("Problem with file [%s]" % fname)
            return (sp_db, data)

        # only care about default entry
        # this needs to look for NX_class NXentry not just 'entry' in the name
        # ekeys = [k for k, v in file_dct.items() if k.find("entry") > -1]
        ekey = file_dct['default']
        entry_dct = file_dct[ekey]
        _scan_type = get_pystxm_scan_type_from_file_dct(file_dct)

        num_entries = len(entry_dct)
        sp_db_lst = []
        data_lst = []

        if len(entry_dct) == 0:
            # there is a problem,
            _logger.error(
                "get_sp_db_and_data: there is a problem with the file [%s]" % fprefix
            )
            return ([], [])
        sp_db = file_dct
        data = self.get_data_from_entry(
            file_dct, ekey, stack_dir=stack_dir, fname=fname, stype=_scan_type
        )
        ev_setpoints = get_energy_setpoints_from_entry(file_dct[file_dct['default']])
        #if sp_db["EV_NPOINTS"] > 1:
        if len(ev_setpoints) > 1:
            #sp_db_lst.append(sp_db)
            wdg_com = get_wdg_com_from_entry(file_dct[file_dct['default']])
            sp_db = get_first_sp_db_from_wdg_com(wdg_com)
            sp_db_lst.append(sp_db)
            data_lst.append(data)

        try:
            if len(data_lst) > 0:

                # dl = len(data_lst[0])
                dl_shape = data_lst[0].shape
                if data_lst[0].ndim == 1:
                    data = np.zeros((num_entries, dl_shape[0]))
                elif data_lst[0].ndim == 2:
                    data = np.zeros((num_entries, dl_shape[0], dl_shape[1]))
                elif data_lst[0].ndim == 3:
                    data = np.zeros(
                        (num_entries, dl_shape[0], dl_shape[1], dl_shape[2])
                    )

                # data = np.zeros((num_entries, dl_shape[0], dl_shape[1]))
                for i in range(num_entries):
                    data[i] = data_lst[i]
                sp_db = sp_db_lst[0]

        except:
            _logger.error("get_sp_db_and_data: problem with [%s]" % fname)
        if stack_dir:
            return (sp_db_lst, data_lst)
        else:
            return (sp_db, data)

    def ensure_instance_of_data_io_class(self, fname):
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
        self.data_io = self.data_io_class(data_dir, fprefix)

    def get_h5_nxstxm_file_as_dict(self, data_dir, fprefix, fsuffix):
        """
        get_entries(): description

        :param data_dir: data_dir description
        :type data_dir: data_dir type

        :param fprefix: fprefix description
        :type fprefix: fprefix type

        :param fsuffix: fsuffix description
        :type fsuffix: fsuffix type

        :returns: None
        """
        fname = data_dir + fprefix + fsuffix
        self.ensure_instance_of_data_io_class(fname)
        sp_db = self.data_io.load()
        return sp_db

    def get_data_from_entry(
        self, file_dct, ekey, spid_idx=0, stack_dir=False, fname=None, stype=None
    ):
        """
        get_data_from_entry(): description

        :param ado_obj: ado_obj description
        :type ado_obj: ado_obj type

        :param spid_idx: spid_idx index into list of sp_ids
        :type spid_idx: integer


        :returns: None
        """
        if file_dct is None:
            _logger.error("file_dct cannot be None")
            return

        # ekey = entry_dct.keys()[0]
        if self.data_io is None:
            self.ensure_instance_of_data_io_class(fname)
        nx_datas = self.data_io.get_NXdatas_from_entry(file_dct, ekey)
        self.counter_nm = list(nx_datas.keys())[0] # self.data_io.get_default_detector_from_entry(file_dct)

        data = nx_datas[self.counter_nm]

        if data is not None:
            if data.ndim == 3:
                if stack_dir:
                    return data
                if stype != None:
                    if stype is scan_types.GENERIC_SCAN:
                        return data[0][0]

                if len(data) > 0:
                    data = data[0]
                else:
                    return None
        return data

    def set_image_report(self, info_str, info_jstr):
        """
        set_image_report(): description

        :param info_str: info_str description
        :type info_str: info_str type

        :param info_jstr: info_jstr description
        :type info_jstr: info_jstr type

        :returns: None
        """
        self.image_info_str = info_str
        self.image_info_jstr = info_jstr

    def extract_date_time_from_nx_time(self, nx_time):
        dt = nx_time.split("T")[0]
        _tm = nx_time.split("T")[1]
        tm = _tm.split(".")[0]
        return (dt, tm)

    def build_image_params(
        self,
        fpath,
        sp_db,
        data,
        ev_idx=0,
        ev_pnt=0,
        pol_idx=0,
        pol_pnt=0,
        is_folder=False,
        stack_idx=None,
    ):
        """
        build_image_params(): create a string and json string that represents the key bits of information
            on this image. The json string is used for drag and drop events so that the widget that receives the 'drop' has
            enough info to load the image, scan or display the relevant information.

        :param fpath: the filename
        :type fpath: string

        :param sp_db:  This is the standard spatial database dict that is used throughout the application, refer to
                        make_spatial_db_dict() in stxm_control/stxm_utils/roi_utils.py for a detailed look at the structure
                        of an sp_db
        :type sp_db: sp_db type

        :param data: A numpy array that contains the image data
        :type data: data type

        :param ev_idx: the index into the correct ev_roi for this image
        :type ev_idx: integer

        :param ev_pnt: the index into the correct energy point in the ev_roi for this image
        :type ev_pnt: integer

        :param pol_idx: the index into the correct polarization_roi for this image
        :type pol_idx: integer

        :param pol_pnt: the index into the correct polarization point in the pol_roi for this image
        :type pol_pnt: integer

        :param stack_idx: the image number within a stack scan
        :type stack_idx: integer | None

        :returns:  a tuple consisting of a string used for the tooltip data and a json string used for drag and drop operations

        scan_types = Enum('detector_image', \
				'osa_image', \
				'osa_focus', \
				'sample_focus', \
				'sample_point_spectra', \
				'sample_line_spectra', \
				'sample_image', \
				'sample_image_stack', \
				'generic_scan', \
				'coarse_image')


        """


        if sp_db is None:
            return (None, None)
        focus_scans = [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]
        spectra_scans = [
            scan_types.SAMPLE_POINT_SPECTRUM,
            scan_types.SAMPLE_LINE_SPECTRUM,
        ]
        stack_scans = [scan_types.SAMPLE_IMAGE_STACK]
        _scan_type = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)

        if _scan_type is None:
            #ToDo: after changes to file loading without assumptions about who saved the file the sp_db passed might be
            # an entry_dct, so if type is read as None check to see what the default's say the type is
            # sp_db['entry0']['WDG_COM']['SPATIAL_ROIS']['0']
            sp_db = get_first_sp_db_from_entry(sp_db[sp_db['default']])
            _scan_type = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)

            if _scan_type is None:
                return (None, None)


        if data is None:
            if _scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
                data = np.ones((2, 2))
            else:
                return (None, None)

        if data.size == 0:
            if _scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
                data = np.ones((2, 2))
            else:
                return (None, None)

        if data.ndim == 3:
            data = data[0]

        if data.ndim in [1, 2]:
            # # hack
            e_pnt = sp_db[EV_ROIS][ev_idx][SETPOINTS][ev_pnt]
            e_npts = 0
            for e in sp_db[EV_ROIS]:
                if len(e[SETPOINTS]) > 1:
                    e_npts += len(e[SETPOINTS])
                else:
                    e_npts = 1

            if data.ndim == 1:
                height = 1
                (width,) = data.shape
            else:
                height, width = data.shape

            # s = 'File: %s  \n' %  (fprefix + '.hdf5')
            # if (fpath.find('12162') > -1):
            #    print()
            dct = {}
            dct["file"] = fpath.replace("/", "\\")
            dct["scan_type_num"] = dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)
            dct["scan_type"] = (
                scan_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE)]
                + " "
                + scan_sub_types[dct_get(sp_db, SPDB_SCAN_PLUGIN_SUBTYPE)]
            )
            dct['stxm_scan_type'] = dct_get(sp_db, SPDB_SCAN_PLUGIN_STXM_SCAN_TYPE)
            #this following scan_panel_idx is needed for drag and drop
            # dct["scan_panel_idx"] = dct_get(sp_db, SPDB_SCAN_PLUGIN_PANEL_IDX)
            dct["energy"] = [e_pnt]
            dct["estart"] = sp_db[EV_ROIS][ev_idx][START]
            #if is_folder:
            if len(sp_db[EV_ROIS]) > 1:
                #its a stack folder so show the final energy not just the last in the current region ev_idx
                dct["estop"] = sp_db[EV_ROIS][-1][STOP]
            else:
                dct["estop"] = sp_db[EV_ROIS][ev_idx][STOP]

            dct["e_npnts"] = e_npts

            if stack_idx is not None:
                dct["stack_index"] = stack_idx
            dct["polarization"] = convert_wrapper_epu_to_str(
                sp_db[EV_ROIS][ev_idx][POL_ROIS][pol_idx][POL]
            )
            dct["offset"] = sp_db[EV_ROIS][ev_idx][POL_ROIS][pol_idx][OFF]
            dct["angle"] = sp_db[EV_ROIS][ev_idx][POL_ROIS][pol_idx][ANGLE]
            dct["dwell"] = sp_db[EV_ROIS][ev_idx][DWELL] * 1000.0
            # dct['npoints'] = (width, height)
            dct["npoints"] = (
                dct_get(sp_db, SPDB_XNPOINTS),
                dct_get(sp_db, SPDB_YNPOINTS),
            )
            if width != dct_get(sp_db, SPDB_XNPOINTS):
                _logger.debug(
                    "[%s] The data doesnt match the scan params for X npoints" % fpath
                )
                width = dct_get(sp_db, SPDB_XNPOINTS)

            if height != dct_get(sp_db, SPDB_YNPOINTS):
                _logger.debug(
                    "[%s] The data doesnt match the scan params for Y npoints" % fpath
                )
                height = dct_get(sp_db, SPDB_YNPOINTS)

            start_date_str = sp_db[SPDB_ACTIVE_DATA_OBJECT][ADO_START_TIME]
            if isinstance(start_date_str, bytes):
                start_date_str = start_date_str.decode("utf-8")

            end_date_str = sp_db[SPDB_ACTIVE_DATA_OBJECT][ADO_END_TIME]
            if isinstance(end_date_str, bytes):
                end_date_str = end_date_str.decode("utf-8")

            dt0, tm0 = self.extract_date_time_from_nx_time(start_date_str)
            dt1, tm1 = self.extract_date_time_from_nx_time(end_date_str)
            dct["date"] = dt0
            dct["start_time"] = tm0
            dct["end_time"] = tm1

            if _scan_type in focus_scans:

                zzcntr = dct_get(sp_db, SPDB_ZZCENTER)
                if zzcntr is None:
                    zzcntr = dct_get(sp_db, SPDB_ZCENTER)
                # dct['center'] = (dct_get(sp_db, SPDB_XCENTER), dct_get(sp_db, SPDB_ZZCENTER))
                dct["center"] = (dct_get(sp_db, SPDB_XCENTER), zzcntr)
                zzrng = dct_get(sp_db, SPDB_ZZRANGE)
                if zzrng is None:
                    zzrng = dct_get(sp_db, SPDB_ZRANGE)
                dct["range"] = (dct_get(sp_db, SPDB_XRANGE), zzrng)

                zzstep = dct_get(sp_db, SPDB_ZZSTEP)
                if zzstep is None:
                    zzstep = dct_get(sp_db, SPDB_ZSTEP)
                dct["step"] = (dct_get(sp_db, SPDB_XSTEP), zzstep)

                zzstrt = dct_get(sp_db, SPDB_ZZSTART)
                if zzstrt is None:
                    zzstrt = dct_get(sp_db, SPDB_ZSTART)
                dct["start"] = (dct_get(sp_db, SPDB_XSTART), zzstrt)

                zzstop = dct_get(sp_db, SPDB_ZZSTOP)
                if zzstop is None:
                    zzstop = dct_get(sp_db, SPDB_ZSTOP)
                dct["stop"] = (dct_get(sp_db, SPDB_XSTOP), zzstop)

                zzposner = dct_get(sp_db, SPDB_ZZPOSITIONER)
                if zzposner is None:
                    zzposner = dct_get(sp_db, SPDB_ZPOSITIONER)
                dct["ypositioner"] = zzposner

                dct["xpositioner"] = dct_get(sp_db, SPDB_XPOSITIONER)
            else:
                dct["center"] = (
                    dct_get(sp_db, SPDB_XCENTER),
                    dct_get(sp_db, SPDB_YCENTER),
                )
                dct["range"] = (
                    dct_get(sp_db, SPDB_XRANGE),
                    dct_get(sp_db, SPDB_YRANGE),
                )
                dct["step"] = (dct_get(sp_db, SPDB_XSTEP), dct_get(sp_db, SPDB_YSTEP))
                dct["start"] = (
                    dct_get(sp_db, SPDB_XSTART),
                    dct_get(sp_db, SPDB_YSTART),
                )
                dct["stop"] = (dct_get(sp_db, SPDB_XSTOP), dct_get(sp_db, SPDB_YSTOP))
                dct["xpositioner"] = dct_get(sp_db, SPDB_XPOSITIONER)
                dct["ypositioner"] = dct_get(sp_db, SPDB_YPOSITIONER)

            # if ('GONI' in sp_db.keys()):
            if "GONI" in list(sp_db):
                if dct_get(sp_db, SPDB_GT) is None:
                    pass
                if dct_get(sp_db, SPDB_GZCENTER) != None:
                    # pass
                    dct["goni_z_cntr"] = dct_get(sp_db, SPDB_GZCENTER)
                if dct_get(sp_db, SPDB_GTCENTER) != None:
                    dct["goni_theta_cntr"] = dct_get(sp_db, SPDB_GTCENTER)

            jstr = json.dumps(dct)
            # construct the tooltip string using html formatting for bold etc
            s = "%s" % self.format_info_text("File:", dct["file"], start_preformat=True)
            s += "%s %s %s" % (
                self.format_info_text("Date:", dct["date"], newline=False),
                self.format_info_text("Started:", dct["start_time"], newline=False),
                self.format_info_text("Ended:", dct["end_time"]),
            )

            if _scan_type is scan_types.GENERIC_SCAN:
                # add the positioner name
                # s += '%s' % self.format_info_text('Scan Type:', dct['scan_type'] + ' %s' % dct_get(sp_db, SPDB_XPOSITIONER))
                s += "%s" % self.format_info_text(
                    "Scan Type:", dct["scan_type"], newline=False
                )
                s += " %s" % self.format_info_text(dct_get(sp_db, SPDB_XPOSITIONER), "")

            else:
                s += "%s" % self.format_info_text("Scan Type:", dct["scan_type"])

            # s += '%s' % self.format_info_text('Scan Type:', dct['scan_type'])
            # if (is_folder and ( (_scan_type in spectra_scans) or (_scan_type in stack_scans)) ):
            if (_scan_type in spectra_scans) or (_scan_type in stack_scans and stack_idx is None):
                # s += '%s' % self.format_info_text('Energy:', '[%.2f ---> %.2f] eV' % (dct['estart'], dct['estop']))
                # s += '%s' % self.format_info_text('Num Energy Points:', '%d' % dct['e_npnts'])
                # s += '%s' % self.format_info_text('Energy:', '[%.2f ---> %.2f] eV   %s' % (dct['estart'], dct['estop'],
                #                                    self.format_info_text('Num Energy Points:', '%d' % dct['e_npnts'])))
                s += "%s %s" % (
                    self.format_info_text(
                        "Energy:",
                        "[%.2f ---> %.2f] eV \t" % (dct["estart"], dct["estop"]),
                        newline=False,
                    ),
                    self.format_info_text("Num Energy Points:", "%d" % dct["e_npnts"]),
                )
            else:
                s += "%s" % self.format_info_text("Energy:", "%.2f eV" % (e_pnt))

            if (_scan_type in focus_scans):
                x_start, zpz_start = dct["start"]
                x_stop, zpz_stop = dct["stop"]
                s += '%s' % self.format_info_text('ZoneplateZ:', '[%.2f ---> %.2f] um' % (zpz_start, zpz_stop))

            _s1 = "%s" % (
                self.format_info_text(
                    "Polarization:",
                    "%s"
                    % convert_wrapper_epu_to_str(
                        sp_db[EV_ROIS][ev_idx][EPU_POL_PNTS][pol_idx]
                    ),
                    newline=False,
                )
            )
            _s2 = "%s" % (
                self.format_info_text(
                    "Offset:",
                    "%.2f mm" % sp_db[EV_ROIS][ev_idx][EPU_OFF_PNTS][pol_idx],
                    newline=False,
                )
            )
            _s3 = "%s" % (
                self.format_info_text(
                    "Angle:", "%.2f deg" % sp_db[EV_ROIS][ev_idx][EPU_ANG_PNTS][pol_idx]
                )
            )
            s += "%s %s %s" % (_s1, _s2, _s3)
            s += "%s" % self.format_info_text(
                "Dwell:", "%.2f ms" % (sp_db[EV_ROIS][ev_idx][DWELL] * 1000.0)
            )
            s += "%s" % self.format_info_text("Points:", "%d x %d " % (width, height))
            s += "%s" % self.format_info_text(
                "Center:", "(%.2f, %.2f) um" % dct["center"]
            )
            s += "%s" % self.format_info_text(
                "Range:", "(%.2f, %.2f) um" % dct["range"]
            )

            # if ('goni_theta_cntr' in dct.keys()):
            if "goni_theta_cntr" in list(dct):
                s += "%s" % self.format_info_text(
                    "StepSize:", "(%.3f, %.3f) um" % dct["step"]
                )
                # if ('goni_z_cntr' in dct.keys()):
                if "goni_z_cntr" in list(dct):
                    s += "%s" % self.format_info_text(
                        "Goni Z:", "%.3f um" % dct["goni_z_cntr"]
                    )
                s += "%s" % self.format_info_text(
                    "Goni Theta:",
                    "%.2f deg" % (dct["goni_theta_cntr"]),
                    newline=False,
                    end_preformat=True,
                )
            else:
                s += "%s" % self.format_info_text(
                    "StepSize:",
                    "(%.3f, %.3f) um" % dct["step"],
                    newline=False,
                    end_preformat=True,
                )

            return (s, jstr)
        else:
            # print 'build_image_params: Unsupported dimensions of data ->[%d]'% data.ndim
            return (None, None)

    def build_image_params_from_default_dct(
            self,
            fpath,
            default_dct,
            data,
            ev_idx=0,
            ev_pnt=0,
            pol_idx=0,
            pol_pnt=0,
            is_folder=False,
            stack_idx=None,
    ):
        """
        build_image_params_from_default_dct(): create a string and json string that represents the key bits of information
            on this image. The json string is used for drag and drop events so that the widget that receives the 'drop' has
            enough info to load the image, scan or display the relevant information.

        :param fpath: the filename
        :type fpath: string

        :param default_dct:  This is the standard spatial database dict that is used throughout the application, refer to
                        make_spatial_db_dict() in stxm_control/stxm_utils/roi_utils.py for a detailed look at the structure
                        of an sp_db
        :type default_dct: sp_db type

        :param data: A numpy array that contains the image data
        :type data: data type

        :param ev_idx: the index into the correct ev_roi for this image
        :type ev_idx: integer

        :param ev_pnt: the index into the correct energy point in the ev_roi for this image
        :type ev_pnt: integer

        :param pol_idx: the index into the correct polarization_roi for this image
        :type pol_idx: integer

        :param pol_pnt: the index into the correct polarization point in the pol_roi for this image
        :type pol_pnt: integer

        :param stack_idx: the image number within a stack scan
        :type stack_idx: integer | None

        :returns:  a tuple consisting of a string used for the tooltip data and a json string used for drag and drop operations

        scan_types = Enum('detector_image', \
                'osa_image', \
                'osa_focus', \
                'sample_focus', \
                'sample_point_spectra', \
                'sample_line_spectra', \
                'sample_image', \
                'sample_image_stack', \
                'generic_scan', \
                'coarse_image')


        """

        if default_dct is None:
            return (None, None)
        focus_scans = [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]
        spectra_scans = [
            scan_types.SAMPLE_POINT_SPECTRUM,
            scan_types.SAMPLE_LINE_SPECTRUM,
        ]
        stack_scans = [scan_types.SAMPLE_IMAGE_STACK]
        _scan_type = default_dct['pystxm_enum_scan_type']

        if _scan_type is None:
            # ToDo: after changes to file loading without assumptions about who saved the file the sp_db passed might be
            # an entry_dct, so if type is read as None check to see what the default's say the type is
            # sp_db['entry0']['WDG_COM']['SPATIAL_ROIS']['0']
            #default_dct = get_first_sp_db_from_entry(default_dct[default_dct['default']])
            _scan_type = default_dct['pystxm_enum_scan_type']

            if _scan_type is None:
                return (None, None)

        if data is None:
            if _scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
                data = np.ones((2, 2))
            else:
                return (None, None)

        if data.size == 0:
            if _scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
                data = np.ones((2, 2))
            else:
                return (None, None)

        if data.ndim == 3:
            data = data[0]

        if data.ndim in [1, 2]:
            # # hack
            e_pnt = ev_pnt
            e_npts = len(default_dct['energy'])
            if data.ndim == 1:
                height = 1
                (width,) = data.shape
            else:
                height, width = data.shape

            # s = 'File: %s  \n' %  (fprefix + '.hdf5')
            # if (fpath.find('12162') > -1):
            #    print()
            dct = {}
            dct["file"] = fpath.replace("/", "\\")
            dct["scan_type_num"] = _scan_type
            dct["scan_type"] = (
                    default_dct['stxm_scan_type']
            )
            dct['stxm_scan_type'] = default_dct['stxm_scan_type']
            # this following scan_panel_idx is needed for drag and drop
            # dct["scan_panel_idx"] = dct_get(sp_db, SPDB_SCAN_PLUGIN_PANEL_IDX)
            dct["energy"] = [e_pnt]
            dct["estart"] = e_pnt
            # if is_folder:
            if e_npts > 1:
                # its a stack folder so show the final energy not just the last in the current region ev_idx
                dct["estop"] = default_dct['energy'][-1]
            else:
                dct["estop"] = e_pnt

            dct["e_npnts"] = e_npts

            if stack_idx is not None:
                dct["stack_index"] = stack_idx

            if len(default_dct['polarization']) > 0:
                dct["polarization"] = convert_wrapper_epu_to_str(
                    default_dct[EV_ROIS][ev_idx][POL_ROIS][pol_idx][POL]
                )
                dct["offset"] = default_dct[EV_ROIS][ev_idx][POL_ROIS][pol_idx][OFF]
                dct["angle"] = default_dct[EV_ROIS][ev_idx][POL_ROIS][pol_idx][ANGLE]
            else:
                dct["polarization"] = None
                dct["offset"] = None
                dct["angle"] = None

            dct["dwell"] = default_dct['count_time'][0] * 1000.0
            # dct['npoints'] = (width, height)
            dct["npoints"] = (
                dct_get(default_dct, SPDB_XNPOINTS),
                dct_get(default_dct, SPDB_YNPOINTS),
            )
            if width != dct_get(default_dct, SPDB_XNPOINTS):
                _logger.debug(
                    "[%s] The data doesnt match the scan params for X npoints" % fpath
                )
                width = dct_get(default_dct, SPDB_XNPOINTS)

            if height != dct_get(default_dct, SPDB_YNPOINTS):
                _logger.debug(
                    "[%s] The data doesnt match the scan params for Y npoints" % fpath
                )
                height = dct_get(default_dct, SPDB_YNPOINTS)

            start_date_str = default_dct[SPDB_ACTIVE_DATA_OBJECT][ADO_START_TIME]
            if isinstance(start_date_str, bytes):
                start_date_str = start_date_str.decode("utf-8")

            end_date_str = default_dct[SPDB_ACTIVE_DATA_OBJECT][ADO_END_TIME]
            if isinstance(end_date_str, bytes):
                end_date_str = end_date_str.decode("utf-8")

            dt0, tm0 = self.extract_date_time_from_nx_time(start_date_str)
            dt1, tm1 = self.extract_date_time_from_nx_time(end_date_str)
            dct["date"] = dt0
            dct["start_time"] = tm0
            dct["end_time"] = tm1

            if _scan_type in focus_scans:

                zzcntr = dct_get(default_dct, SPDB_ZZCENTER)
                if zzcntr is None:
                    zzcntr = dct_get(default_dct, SPDB_ZCENTER)
                # dct['center'] = (dct_get(sp_db, SPDB_XCENTER), dct_get(sp_db, SPDB_ZZCENTER))
                dct["center"] = (dct_get(default_dct, SPDB_XCENTER), zzcntr)
                zzrng = dct_get(default_dct, SPDB_ZZRANGE)
                if zzrng is None:
                    zzrng = dct_get(default_dct, SPDB_ZRANGE)
                dct["range"] = (dct_get(default_dct, SPDB_XRANGE), zzrng)

                zzstep = dct_get(default_dct, SPDB_ZZSTEP)
                if zzstep is None:
                    zzstep = dct_get(default_dct, SPDB_ZSTEP)
                dct["step"] = (dct_get(default_dct, SPDB_XSTEP), zzstep)

                zzstrt = dct_get(default_dct, SPDB_ZZSTART)
                if zzstrt is None:
                    zzstrt = dct_get(default_dct, SPDB_ZSTART)
                dct["start"] = (dct_get(default_dct, SPDB_XSTART), zzstrt)

                zzstop = dct_get(default_dct, SPDB_ZZSTOP)
                if zzstop is None:
                    zzstop = dct_get(default_dct, SPDB_ZSTOP)
                dct["stop"] = (dct_get(default_dct, SPDB_XSTOP), zzstop)

                zzposner = dct_get(default_dct, SPDB_ZZPOSITIONER)
                if zzposner is None:
                    zzposner = dct_get(default_dct, SPDB_ZPOSITIONER)
                dct["ypositioner"] = zzposner

                dct["xpositioner"] = dct_get(default_dct, SPDB_XPOSITIONER)
            else:
                dct["center"] = (
                    dct_get(default_dct, SPDB_XCENTER),
                    dct_get(default_dct, SPDB_YCENTER),
                )
                dct["range"] = (
                    dct_get(default_dct, SPDB_XRANGE),
                    dct_get(default_dct, SPDB_YRANGE),
                )
                dct["step"] = (dct_get(default_dct, SPDB_XSTEP), dct_get(default_dct, SPDB_YSTEP))
                dct["start"] = (
                    dct_get(default_dct, SPDB_XSTART),
                    dct_get(default_dct, SPDB_YSTART),
                )
                dct["stop"] = (dct_get(default_dct, SPDB_XSTOP), dct_get(default_dct, SPDB_YSTOP))
                dct["xpositioner"] = dct_get(default_dct, SPDB_XPOSITIONER)
                dct["ypositioner"] = dct_get(default_dct, SPDB_YPOSITIONER)

            # if ('GONI' in sp_db.keys()):
            if "GONI" in list(default_dct):
                if dct_get(default_dct, SPDB_GT) is None:
                    pass
                if dct_get(default_dct, SPDB_GZCENTER) != None:
                    # pass
                    dct["goni_z_cntr"] = dct_get(default_dct, SPDB_GZCENTER)
                if dct_get(default_dct, SPDB_GTCENTER) != None:
                    dct["goni_theta_cntr"] = dct_get(default_dct, SPDB_GTCENTER)

            jstr = json.dumps(dct)
            # construct the tooltip string using html formatting for bold etc
            s = "%s" % self.format_info_text("File:", dct["file"], start_preformat=True)
            s += "%s %s %s" % (
                self.format_info_text("Date:", dct["date"], newline=False),
                self.format_info_text("Started:", dct["start_time"], newline=False),
                self.format_info_text("Ended:", dct["end_time"]),
            )

            if _scan_type is scan_types.GENERIC_SCAN:
                # add the positioner name
                # s += '%s' % self.format_info_text('Scan Type:', dct['scan_type'] + ' %s' % dct_get(sp_db, SPDB_XPOSITIONER))
                s += "%s" % self.format_info_text(
                    "Scan Type:", dct["scan_type"], newline=False
                )
                s += " %s" % self.format_info_text(dct_get(default_dct, SPDB_XPOSITIONER), "")

            else:
                s += "%s" % self.format_info_text("Scan Type:", dct["scan_type"])

            # s += '%s' % self.format_info_text('Scan Type:', dct['scan_type'])
            # if (is_folder and ( (_scan_type in spectra_scans) or (_scan_type in stack_scans)) ):
            if (_scan_type in spectra_scans) or (_scan_type in stack_scans and stack_idx is None):
                # s += '%s' % self.format_info_text('Energy:', '[%.2f ---> %.2f] eV' % (dct['estart'], dct['estop']))
                # s += '%s' % self.format_info_text('Num Energy Points:', '%d' % dct['e_npnts'])
                # s += '%s' % self.format_info_text('Energy:', '[%.2f ---> %.2f] eV   %s' % (dct['estart'], dct['estop'],
                #                                    self.format_info_text('Num Energy Points:', '%d' % dct['e_npnts'])))
                s += "%s %s" % (
                    self.format_info_text(
                        "Energy:",
                        "[%.2f ---> %.2f] eV \t" % (dct["estart"], dct["estop"]),
                        newline=False,
                    ),
                    self.format_info_text("Num Energy Points:", "%d" % dct["e_npnts"]),
                )
            else:
                s += "%s" % self.format_info_text("Energy:", "%.2f eV" % (e_pnt))

            if (_scan_type in focus_scans):
                x_start, zpz_start = dct["start"]
                x_stop, zpz_stop = dct["stop"]
                s += '%s' % self.format_info_text('ZoneplateZ:', '[%.2f ---> %.2f] um' % (zpz_start, zpz_stop))

            _s1 = "%s" % (
                self.format_info_text(
                    "Polarization:",
                    "%s"
                    % convert_wrapper_epu_to_str(
                        default_dct[EV_ROIS][ev_idx][EPU_POL_PNTS][pol_idx]
                    ),
                    newline=False,
                )
            )
            _s2 = "%s" % (
                self.format_info_text(
                    "Offset:",
                    "%.2f mm" % default_dct[EV_ROIS][ev_idx][EPU_OFF_PNTS][pol_idx],
                    newline=False,
                )
            )
            _s3 = "%s" % (
                self.format_info_text(
                    "Angle:", "%.2f deg" % default_dct[EV_ROIS][ev_idx][EPU_ANG_PNTS][pol_idx]
                )
            )
            s += "%s %s %s" % (_s1, _s2, _s3)
            s += "%s" % self.format_info_text(
                "Dwell:", "%.2f ms" % (default_dct[EV_ROIS][ev_idx][DWELL] * 1000.0)
            )
            s += "%s" % self.format_info_text("Points:", "%d x %d " % (width, height))
            s += "%s" % self.format_info_text(
                "Center:", "(%.2f, %.2f) um" % dct["center"]
            )
            s += "%s" % self.format_info_text(
                "Range:", "(%.2f, %.2f) um" % dct["range"]
            )

            # if ('goni_theta_cntr' in dct.keys()):
            if "goni_theta_cntr" in list(dct):
                s += "%s" % self.format_info_text(
                    "StepSize:", "(%.3f, %.3f) um" % dct["step"]
                )
                # if ('goni_z_cntr' in dct.keys()):
                if "goni_z_cntr" in list(dct):
                    s += "%s" % self.format_info_text(
                        "Goni Z:", "%.3f um" % dct["goni_z_cntr"]
                    )
                s += "%s" % self.format_info_text(
                    "Goni Theta:",
                    "%.2f deg" % (dct["goni_theta_cntr"]),
                    newline=False,
                    end_preformat=True,
                )
            else:
                s += "%s" % self.format_info_text(
                    "StepSize:",
                    "(%.3f, %.3f) um" % dct["step"],
                    newline=False,
                    end_preformat=True,
                )

            return (s, jstr)
        else:
            # print 'build_image_params: Unsupported dimensions of data ->[%d]'% data.ndim
            return (None, None)

    def format_info_text(
        self,
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

    def reload_dir(self):
        # reload the current directory
        if self.reload_mutex.tryLock(1):
            self.change_dir(_dir=self.data_dir)
            self.reload_mutex.unlock()

    def on_change_dir(self, dud):
        """
        a handler for the menuContext
        :param dud:
        :return:
        """
        self.reload_mutex.lock()
        self.change_dir()
        self.reload_mutex.unlock()

    def change_dir(self, _dir=None):
        """
        change_dir(): description

        :returns: None
        """
        if _dir is None:
            fpath = getOpenFileName("Pick Directory by selecting a file", filter_str="Data Files (*.hdf5)",
                                    search_path=self.data_dir)
            if fpath == None:
                return
                #_dir = self.data_dir
            else:
                p = pathlib.Path(fpath)
                _dir = p.as_posix().replace(p.name, "")

        # prev_cursor = self.cursor()
        # QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        # self.setCursor(QtCore.Qt.WaitCursor)
        #set to default

        # check if directory contains a stack
        if self.is_stack_dir(_dir):
            self.set_data_dir(_dir, is_stack_dir=True)
            dirs, data_fnames = dirlist_withdirs(_dir, self.data_file_extension)
            fname = os.path.join(_dir, data_fnames[0])
            # sp_db, data = self.get_stack_data(fname)
            #self.load_entries_into_view(data_fnames[0])
            self.load_stack_file_image_items(os.path.join(_dir, data_fnames[0]))
            self.current_contents_is_dir = True
            self.fsys_mon.set_data_dir(self.data_dir)
            # self.unsetCursor()
            return
        elif self.is_stack_file(_dir):
            self.load_stack_file_image_items(_dir)
            self.current_contents_is_dir = False
            self.unsetCursor()
            return
        elif os.path.isdir(_dir):
            pass

        if len(_dir) > 0:
            self.set_data_dir(_dir, is_stack_dir=False)
            self.fsys_mon.set_data_dir(self.data_dir)

        self.unsetCursor()
        # QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(prev_cursor))

    def on_dir_changed(self, f_added_removed):
        """
        on_dir_changed(): this handler needs to discern between files that are not finished writing and those that are ready to be read

        :param (f_added: (f_added description
        :type (f_added: (f_added type

        :param f_removed): f_removed) description
        :type f_removed): f_removed) type

        :returns: None
        """
        f_added, f_removed = f_added_removed

        self.setCursor(QtCore.Qt.WaitCursor)

        if any(f_removed):
            # boylec0: cannot "reload_dir" as we are already
            # within the context of the MUTEX lock scope
            self.change_dir(_dir=self.data_dir)

        elif any(f_added):
            for fname in f_added:
                fstr = os.path.join(self.data_dir, fname)
                sp_db, data = self.get_nxstm_file_dct_and_data(fstr)
                # we dont support stack or multi spatials yet so just load it as a single
                if type(sp_db) is list:
                    if len(sp_db) == 0:
                        _logger.error("on_dir_changed: problem with [%s]" % fname)
                        return

                    sp_db = sp_db[0]
                    data = data[0]

                if sp_db is None:
                    # could be an aborted scan where there is no data of any kind
                    return

                if dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) in spectra_type_scans:
                    graphics_wdg = self.spectra_graphics_wdg
                    graphics_view = self.spectra_view
                    graphics_scene = self.spectra_scene
                else:
                    graphics_wdg = self.images_graphics_wdg
                    graphics_view = self.images_view
                    graphics_scene = self.images_scene

                if graphics_wdg.cur_column >= get_max_thumb_columns(self.images_view.width()):
                    graphics_wdg.incr_row()
                    graphics_wdg.reset_column()

                status = self.add_to_view(
                    fname,
                    sp_db,
                    data,
                    ev_idx=0,
                    ev_pnt=0,
                    pol_idx=0,
                    pol_pnt=0,
                    row=None,
                    col=None,
                    update_scene=False,
                    graphics=graphics_wdg,
                    view=graphics_view,
                    scene=graphics_scene,
                )
                if status is not None:
                    graphics_wdg.incr_column()

            self.update_scenes()

        self.unsetCursor()

    def get_file_loading_progbar(self):
        """
        create a progress bar styled the way we want
        """
        if self.progbar is None:
            self.progbar = QtWidgets.QProgressBar()
            self.progbar.setFixedWidth(400)
            self.progbar.setWindowTitle("Loading data")
            self.progbar.setAutoFillBackground(True)
            self.progbar.setMinimum(0)
            self.progbar.setMaximum(100)
            self.progbar.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
            ss = """QProgressBar 
                          {        
                                    border: 5px solid rgb(100,100,100);
                                    border-radius: 1 px;
                                    text-align: center;
                          }
                        QProgressBar::chunk
                         {
                                     background-color:  rgb(114, 148, 240);
                                      width: 20 px;
                         }"""

            self.progbar.setStyleSheet(ss)
        #progbar.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.progbar.setValue(0)
        return self.progbar

    def load_image_items(self, is_stack_dir=False, hide=False):
        """
                this function is when the user double clicks the thumbnail, it fires up a worker thread to load the
                data from the current data directory and create an thumnail for each image

                """
        if self.data_dir is None:
            return

        if not os.path.exists(self.data_dir):
            _logger.error("Data directory does not exist: [%s]" % self.data_dir)
            return

        # clear the gridlayouts here before the thread populates the scene otherwise it will intermittantly crash
        # because update signals are firing while things are being garbage collected, placing the clear here has
        # removed the crash ...so far
        self.clear_grid_layout(
            self.images_graphics_wdg, self.images_view, self.images_scene
        )
        self.clear_grid_layout(
            self.spectra_graphics_wdg, self.spectra_view, self.spectra_scene
        )

        dirs, data_fnames = dirlist_withdirs(self.data_dir, ".hdf5")
        thumb_fnames = sorted(data_fnames)
        self.progbar = self.get_file_loading_progbar()
        # print(f"load_image_items: [{self.data_dir}], progbar={id(self.progbar)}")
        self.progbar.show()
        # ref: https://www.twobitarcade.net/article/multithreading-pyqt-applications-with-qthreadpool/
        worker = Worker(
            self.reload_view, self.data_dir, is_stack_dir, progress_callback=self.load_images_progress
        )  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.load_thumbs)
        worker.signals.progress.connect(self.load_images_progress)
        worker.signals.finished.connect(self.thread_complete)

        # Execute
        self.threadpool.start(worker)

    def load_stack_file_image_items(self, fpath):
        """
        this function is when the user double clicks the the stack thumbnail, it fires up a worker thread to load the
        data from the stck and create an thumbnail for each image of the stack

        fpath is the stack file
        """

        if self.data_dir is None:
            return

        if not os.path.exists(fpath):
            _logger.error(f"Stack file does not exist: [{fpath}]")
            return

        # clear the gridlayouts here before the thread populates the scene otherwise it will intermittantly crash
        # because update signals are firing while things are being garbage collected, placing the clear here has
        # removed the crash ...so far
        self.clear_grid_layout(
            self.images_graphics_wdg, self.images_view, self.images_scene
        )
        self.clear_grid_layout(
            self.spectra_graphics_wdg, self.spectra_view, self.spectra_scene
        )

        self.progbar = self.get_file_loading_progbar()
        # print(f"load_stack_file_image_items: [{fpath}] , progbar={id(self.progbar)}")
        self.progbar.show()

        worker_stack = Worker(
            self.load_stack_into_view, fpath, progress_callback=self.load_images_progress
        )  # Any other args, kwargs are passed to the run function
        worker_stack.signals.result.connect(self.load_thumbs)
        worker_stack.signals.progress.connect(self.load_images_progress)
        worker_stack.signals.finished.connect(self.thread_complete)

        # Execute
        self.threadpool.start(worker_stack)

    def load_images_progress(self, prog):
        # print(f"load_images_progress: {prog}% done, progbar id={id(self.progbar)}")
        self.progbar.setValue(prog)

    def thread_complete(self):
        # print("THREAD COMPLETE!")
        self.progbar.hide()

    def hide_progbar(self):
        self.progbar.hide()

    def get_next_row_and_col(self, graphics_wdg: MainGraphicsWidget):
        if graphics_wdg.cur_column >= get_max_thumb_columns(self.images_view.width()):
            graphics_wdg.set_cur_row(graphics_wdg.cur_row + 1)
            graphics_wdg.set_cur_column(0)

        return (graphics_wdg.cur_row, graphics_wdg.cur_column)

    def on_drag(self, obj: ThumbnailWidget, event: QtWidgets.QGraphicsSceneDragDropEvent):
        """
        on_drag(): description

        :param obj: obj description
        :type obj: obj type

        :param event: event description
        :type event: event type

        :returns: None
        """
        event.accept()

        if self.get_drag_enabled():
            itemData = QtCore.QByteArray()
            dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.WriteOnly)
            # dataStream << QtCore.QByteArray(obj.info_jstr) << (event.pos() - obj.rect().topLeft())
            (
                dataStream
                << QtCore.QByteArray(bytearray(obj.info_jstr.encode()))
                << (event.pos() - obj.rect().topLeft())
            )

            # dataStream << QtCore.QByteArray(obj.data.tobytes()) << QtCore.QByteArray(obj.info_str) << (event.pos() - obj.rect().topLeft())

            mimeData = QtCore.QMimeData()
            mimeData.setData("application/x-stxmscan", itemData)
            mimeData.setText(obj.info_jstr)

            drag = QtGui.QDrag(self)
            drag.setMimeData(mimeData)
            pos = event.pos() - obj.rect().topLeft()
            drag.setHotSpot(QtCore.QPoint(int(pos.x()), int(pos.y())))
            if obj.pic is not None:
                drag.setPixmap(obj.pic)

            if (
                drag.exec_(
                    QtCore.Qt.MoveAction | QtCore.Qt.CopyAction, QtCore.Qt.CopyAction
                )
                == QtCore.Qt.MoveAction
            ):
                pass
            else:
                pass

    def make_thumbWidget(
        self,
        data_dir,
        fname,
        info_dct,
        title=None,
        sp_db=None,
        data=None,
        stype=scan_types.SAMPLE_POINT_SPECTRUM,
        is_folder=False,
    ):
        """
        make_thumbWidget(): description

        :param data_dir: data_dir description
        :type data_dir: data_dir type

        :param fname: fname description
        :type fname: fname type

        :param info_dct: info_dct description
        :type info_dct: info_dct type

        :param title=None: title=None description
        :type title=None: title=None type

        :param sp_db=None: sp_db=None description
        :type sp_db=None: sp_db=None type

        :param data=None: data=None description
        :type data=None: data=None type

        :returns: None

        """
        skip_draggable_lst = [scan_types.OSA_FOCUS, scan_types.SAMPLE_FOCUS]
        fstr = os.path.join(data_dir, fname)

        # this should prob be just the default not the whole file_dct
        sp_db = sp_db

        if fname == "..":
            thumb_widget = ThumbnailWidget(
                fstr,
                None,
                data,
                "..",
                info_dct,
                scan_type=None,
                is_folder=is_folder,
                parent=self,
            )

        elif is_folder:
            thumb_widget = ThumbnailWidget(
                fstr,
                sp_db,
                data,
                title,
                info_dct,
                scan_type=stype,
                is_folder=is_folder,
                parent=self,
            )

        elif stype in spectra_type_scans:
            from cls.data_io.stxm_data_io import STXMDataIo
            # do I not already have sp_db and data, why do I need to reload?
            fname = fname.split(".")[0]
            data_io = STXMDataIo(data_dir, fname)
            entry_dct = data_io.load()
            # is it possible to get X and Y data here?
            dct = make_thumb_widg_dct(
                data_dir=data_dir,
                fname=fname,
                entry_dct=entry_dct,
                counter=self,
            )
            thumb_widget = ThumbnailWidget(
                fstr,
                sp_db,
                data,
                title,
                info_dct,
                dct=dct,
                scan_type=stype,
                parent=self,
            )
        else:

            thumb_widget = ThumbnailWidget(
                fstr, sp_db, data, title, info_dct, scan_type=stype, parent=self
            )

        if thumb_widget.is_valid():
            if is_folder:
                # thumb_widget.doubleClicked.connect(self.do_select)
                thumb_widget.dbl_clicked.connect(self.change_dir)
            else:
                # thumb_widget.update_view.connect(self.update_view)
                thumb_widget.select.connect(self.do_select)
                thumb_widget.launch_viewer.connect(self.launch_viewer)
                thumb_widget.print_thumb.connect(self.print_thumbnail)
                thumb_widget.preview_thumb.connect(self.preview_thumbnail)

            if stype not in skip_draggable_lst:
                thumb_widget.drag.connect(self.on_drag)

            return thumb_widget
        else:
            return None

    def add_thumb_widget(
        self,
        data_dir,
        fname,
        info_dct,
        row,
        column,
        title=None,
        sp_db=None,
        data=None,
        graphics=None,
        is_folder=False,
    ):
        """

        :param data_dir:
        :param fname:
        :param info_dct:
        :param row:
        :param column:
        :param title:
        :param sp_db:
        :param data:
        :param graphics:
        :param is_folder:
        :return:
        """
        if graphics is None:
            graphics = self.images_graphics_wdg

        if data_dir.find("..") > -1:
            # create a directory widget to go UP a directory
            thumb_widget = self.make_updir_thumbwidget(self.data_dir)
        else:
            thumb_widget = self.make_thumbWidget(
                data_dir,
                fname,
                info_dct,
                title=title,
                sp_db=sp_db,
                data=data,
                stype=dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE),
            )
        if thumb_widget:
            graphics.gridlayout.addItem(thumb_widget, row, column)
            self.image_thumbs.append(thumb_widget)
            return True
        else:
            return False

    def add_thumb_widget_from_default_dct(
        self,
        data_dir,
        fname,
        info_dct,
        row,
        column,
        title=None,
        default_dct=None,
        data=None,
        graphics=None,
        is_folder=False,
    ):
        """

        :param data_dir:
        :param fname:
        :param info_dct:
        :param row:
        :param column:
        :param title:
        :param default_dct:
        :param data:
        :param graphics:
        :param is_folder:
        :return:
        """
        if graphics is None:
            graphics = self.images_graphics_wdg

        if data_dir.find("..") > -1:
            # create a directory widget to go UP a directory
            thumb_widget = self.make_updir_thumbwidget(self.data_dir)
        else:
            thumb_widget = self.make_thumbWidget(
                data_dir,
                fname,
                info_dct,
                title=title,
                sp_db=default_dct,
                data=data,
                stype=dct_get(default_dct, SPDB_SCAN_PLUGIN_TYPE),
            )
        if thumb_widget:
            graphics.gridlayout.addItem(thumb_widget, row, column)
            self.image_thumbs.append(thumb_widget)
            return True
        else:
            return False

    def clear_grid_layout(self, graphics=None, view=None, scene=None):
        """
        clear_grid_layout(): description

        :returns: None
        """
        if graphics is None:
            graphics = self.images_graphics_wdg

        if scene is None:
            scene = self.images_scene

        if view is None:
            view = self.images_view

        if graphics.gridlayout.count() == 0:
            return

        graphics.clear_layout()

        ir = scene.itemsBoundingRect()
        qr = QtCore.QRectF(ir.x(), ir.y(), ir.width(), THUMB_ACTIVE_AREA_HT)

        scene.setSceneRect(qr)
        view.setSceneRect(qr)
        graphics.set_layout_size(qr)
        del self.image_thumbs
        self.image_thumbs = []
        graphics.set_cur_row(0)
        graphics.set_cur_column(0)
        view.viewport().update()


    def add_to_view(
        self,
        fname,
        sp_db,
        data,
        image_num=None,
        ev_idx=0,
        ev_pnt=0,
        pol_idx=0,
        pol_pnt=0,
        row=None,
        col=None,
        update_scene=False,
        graphics=None,
        view=None,
        scene=None,
    ):
        """
        load_stack_into_view(): description

        :param fname: fname description
        :type fname: fname type

        :returns: None

        """
        # print 'add_to_view: row=%d col=%d' % (row, col)
        if graphics is None:
            graphics = self.images_graphics_wdg

        if scene is None:
            scene = self.images_scene

        if view is None:
            view = self.images_view

        if fname.find("..") > -1:
            # is an updir widget
            status = self.add_thumb_widget(
                fname,
                fname,
                {},
                row,
                col,
                title="..",
                sp_db=sp_db,
                data=data,
                graphics=graphics,
            )
            return status

        if data is None:
            return False

        if data.ndim == 3:
            data = data[0]
        elif data.ndim == 2:
            # its a single image
            data = data
        elif data.ndim == 1:
            # its a spectra
            data = data
        else:
            # its unknown
            return None

        # rows, cols = data.shape

        if (sp_db is not None) and (data is not None):
            # if(dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) not in [scan_types.GENERIC_SCAN, scan_types.SAMPLE_POINT_SPECTRUM]):
            # if (dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) not in [scan_types.GENERIC_SCAN]):
            #     fstr = os.path.join(self.data_dir, fname)
            #     info_str, info_jstr = self.build_image_params(fstr, sp_db, data, ev_idx=ev_idx, ev_pnt=ev_pnt, pol_idx=pol_idx, pol_pnt=0)
            #     info_dct = {'info_str': info_str, 'info_jstr': info_jstr}
            #     lfn = len(fname)
            #     title = fname[0:lfn-5]
            # else:
            #     #its not a supported scan type
            #     return

            fstr = os.path.join(self.data_dir, fname)
            info_str, info_jstr = self.build_image_params(
                fstr,
                sp_db,
                data,
                ev_idx=ev_idx,
                ev_pnt=ev_pnt,
                pol_idx=pol_idx,
                pol_pnt=0,
                stack_idx=image_num,
            )
            info_dct = {"info_str": info_str, "info_jstr": info_jstr}
            lfn = len(fname)
            title = fname[0 : lfn - 5]

        if (row is None) and (col is None):
            row, col = self.get_next_row_and_col(graphics)

        num_rows = graphics.gridlayout.rowCount()
        column = 0
        if image_num is None:
            ttl = title
        else:
            ttl = title + "_%d" % image_num

        status = self.add_thumb_widget(
            self.data_dir,
            fname,
            info_dct,
            row,
            col,
            title=ttl,
            sp_db=sp_db,
            data=data,
            graphics=graphics,
        )
        # print('add_to_view: add_thumb_widget [%s] at rowcol (%d, %d)' % (ttl, row, col))

        if update_scene and status:
            # self.update_scenes(graphics, scene, view)
            self.update_scenes()

        return status


    def add_to_view_from_default_dct(
        self,
        fname,
        default_dct,
        data,
        image_num=None,
        ev_idx=0,
        ev_pnt=0,
        pol_idx=0,
        pol_pnt=0,
        row=None,
        col=None,
        update_scene=False,
        graphics=None,
        view=None,
        scene=None,
    ):
        """
        load_stack_into_view(): description

        :param fname: fname description
        :type fname: fname type

        :returns: None

        """
        # print 'add_to_view: row=%d col=%d' % (row, col)
        if graphics is None:
            graphics = self.images_graphics_wdg

        if scene is None:
            scene = self.images_scene

        if view is None:
            view = self.images_view

        if fname.find("..") > -1:
            # is an updir widget
            status = self.add_thumb_widget_from_default_dct(
                fname,
                fname,
                {},
                row,
                col,
                title="..",
                default_dct=default_dct,
                data=data,
                graphics=graphics,
            )
            return status

        if data is None:
            return False

        if data.ndim == 3:
            data = data[0]
        elif data.ndim == 2:
            # its a single image
            data = data
        elif data.ndim == 1:
            # its a spectra
            data = data
        else:
            # its unknown
            return None

        # rows, cols = data.shape

        if (default_dct is not None) and (data is not None):
            fstr = os.path.join(self.data_dir, fname)
            info_str, info_jstr = self.build_image_params_from_default_dct(
                fstr,
                default_dct,
                data,
                ev_idx=ev_idx,
                ev_pnt=ev_pnt,
                pol_idx=pol_idx,
                pol_pnt=0,
                stack_idx=image_num,
            )
            info_dct = {"info_str": info_str, "info_jstr": info_jstr}
            lfn = len(fname)
            title = fname[0 : lfn - 5]

        if (row is None) and (col is None):
            row, col = self.get_next_row_and_col(graphics)

        num_rows = graphics.gridlayout.rowCount()
        column = 0
        if image_num is None:
            ttl = title
        else:
            ttl = title + "_%d" % image_num

        status = self.add_thumb_widget(
            self.data_dir,
            fname,
            info_dct,
            row,
            col,
            title=ttl,
            default_dct=default_dct,
            data=data,
            graphics=graphics,
        )
        # print('add_to_view: add_thumb_widget [%s] at rowcol (%d, %d)' % (ttl, row, col))

        if update_scene and status:
            # self.update_scenes(graphics, scene, view)
            self.update_scenes()

        return status

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.do_sheet_resize(event, self.images_scene, self.images_graphics_wdg, self.images_view)
        self.do_sheet_resize(event, self.spectra_scene, self.spectra_graphics_wdg, self.spectra_view)

    def do_sheet_resize(self, event: QtGui.QResizeEvent, scene, gr_wdg, view):
        # avoid unnecessary rearrange on first load
        if scene.width() <= 50 or gr_wdg.size().width() <= 50:
            return

        # we can get into an infinite loop if the event is sourced to scrollbar visibility...
        # unless the horizontal scrollbar becomes visible, then do try resizing
        vscroll = view.verticalScrollBar()
        hscroll = view.horizontalScrollBar()
        delta = vscroll.width() if vscroll.isVisible() else 0

        curr_cols = gr_wdg.gridlayout.columnCount()
        test_cols = get_max_thumb_columns(view.width() - delta)

        if curr_cols != test_cols or hscroll.isVisible():
            self.reload_mutex.lock()
            gr_wdg.rearrange_layout(get_max_thumb_columns(view.width() - delta))
            self.update_scenes()
            self.reload_mutex.unlock()

    def update_scenes(self):
        """

        :return:
        """
        self.do_update_scene(
            self.images_graphics_wdg, self.images_scene, self.images_view
        )
        self.do_update_scene(
            self.spectra_graphics_wdg, self.spectra_scene, self.spectra_view
        )

    def do_update_scene(self, grphcs_wdg: MainGraphicsWidget, scene: QtWidgets.QGraphicsScene,
                        view: QtWidgets.QGraphicsView):
        """
        overloaded function
        :param grphcs_wdg:
        :param scene:
        :param view:
        :return:
        """
        num_cols = grphcs_wdg.gridlayout.columnCount()
        num_rows = grphcs_wdg.gridlayout.rowCount() + 1  # make sure there is always enough room at the bottom
        width = (num_cols * (THUMB_ACTIVE_AREA_WD + THUMB_VIEW_HORZ_SPACE)) - THUMB_VIEW_HORZ_SPACE + THUMB_VIEW_MARGINS
        height = (num_rows * (THUMB_ACTIVE_AREA_HT + THUMB_VIEW_VERT_SPACE)) - THUMB_VIEW_VERT_SPACE + THUMB_VIEW_MARGINS
        qr = QtCore.QRectF(0.0, 0.0, width, height)
        # print 'num_rows = %d, ht = %d' % (num_rows, num_rows * 170.0)
        grphcs_wdg.set_layout_size(qr)
        qr = QtCore.QRectF(0.0, 0.0,
                           grphcs_wdg.gridlayout.contentsRect().width() + THUMB_VIEW_HORZ_SPACE,
                           grphcs_wdg.gridlayout.contentsRect().height() + THUMB_VIEW_VERT_SPACE * 2)
        scene.setSceneRect(qr)
        view.setSceneRect(qr)
        yPos = view.verticalScrollBar()
        if grphcs_wdg.gridlayout.geometry().height() > view.height():
            yPos.setValue(yPos.maximum())
        else:
            yPos.setValue(yPos.minimum())

    def load_stack_into_view(self, fname, progress_callback=None):
        """
        load_stack_into_view(): description

        :param fname: fname description
        :type fname: fname type

        :returns: None
        """
        fstr = os.path.join(self.data_dir, fname)
        default_dct = get_default_data_from_hdf5_file(fstr)
        sp_db_lst, data_lst = self.get_nxstm_file_dct_and_stack_data(fstr)

        num_ev, rows, cols = data_lst[0].shape
        num_images = len(sp_db_lst) * num_ev
        num_images += 1  # because we are adding an updir thumbnailwidget

        COLS = get_max_thumb_columns(self.images_view.width())
        ROWS = math.ceil(num_images / COLS)
        rowcol = list(itertools.product(range(ROWS + 1), range(COLS)))
        rowcol_iter = 0
        ev_idx = 0
        i = 0
        row, column = rowcol[rowcol_iter]
        status = self.add_to_view(
            os.path.join(self.data_dir, ".."),
            None,
            None,
            image_num=0,
            ev_idx=ev_idx,
            ev_pnt=0.0,
            pol_idx=0,
            pol_pnt=0,
            row=row,
            col=column,
            update_scene=False,
        )
        rowcol_iter += 1
        sp_id_idx = 0
        for sp_db in sp_db_lst:
            for ev_roi in sp_db[EV_ROIS]:
                # ev_idx = 0
                enpnts = int(ev_roi[NPOINTS])
                polnpnts = len(ev_roi[POL_ROIS])
                ev_pol_idxs = list(itertools.product(range(enpnts), range(polnpnts)))
                ev_pol_iter = 0

                # for ev_pol_idxs in itertools.product(range(enpnts), range(polnpnts) ):
                for x in range(enpnts):
                    # for row, column in itertools.product(range(ROWS),range(MAX_THUMB_COLUMNS)):
                    # print 'load_stack_into_view: %d of %d' % (x, enpnts)
                    for p in range(polnpnts):
                        row, column = rowcol[rowcol_iter]
                        ev_pnt, pol_idx = ev_pol_idxs[ev_pol_iter]
                        # print('load_stack_into_view: calling add_to_view for next_iter=%d, i=%d at rowcol (%d, %d)' % (rowcol_iter, i, row, column))
                        ev_pol_iter += 1
                        rowcol_iter += 1
                        if i < num_ev:
                            status = self.add_to_view(
                                fname,
                                sp_db,
                                data_lst[sp_id_idx][i],  # ISSUE IS HERE, data_lst should be [1][108]
                                image_num=i,
                                ev_idx=ev_idx,
                                ev_pnt=ev_pnt,
                                pol_idx=pol_idx,
                                pol_pnt=0,
                                row=row,
                                col=column,
                                update_scene=False,
                            )

                        if not status:
                            continue
                        i += 1
                        if progress_callback is not None:
                            # print(f"load_stack_into_view: prog = {int((float(i) / float(num_images)) * 100.0)}")
                            progress_callback.emit(
                                int((float(i) / float(num_images)) * 100.0)
                            )

                    # pol_idx += 1
                ev_idx += 1
                self.spectra_graphics_wdg.set_cur_row(row + 1)
                self.spectra_graphics_wdg.set_cur_column(column + 1)
            sp_id_idx += 1
        self.update_scenes()

    def make_updir_thumbwidget(self, data_dir):
        info_dct = {"info_str": "up a directory", "info_jstr": "info_jstr"}
        th_wdg = self.make_thumbWidget(
            data_dir, "..", info_dct, sp_db={}, data=None, stype=None, is_folder=True
        )
        return th_wdg

    # @cached(cache)
    def reload_view(self, datadir, is_stack_dir=False, progress_callback=None):
        """
        reload_view(): walk the self.data_dir and try to load every .hdf5 file, display only the ones that are valid
        skip the ones that are not

        :param is_stack_dir=False: is_stack_dir=False description
        :type is_stack_dir=False: is_stack_dir=False type

        :returns: None
        self.images_graphics_wdg.set_layout_size(qr)
        self.images_scene.setSceneRect(qr)
        self.images_view
        """
        self.data_dir = datadir
        if self.data_dir is None:
            return

        if not os.path.exists(self.data_dir):
            _logger.error("Data directory does not exist: [%s]" % self.data_dir)
            return

        stack_dirs, data_fnames = dirlist_withdirs(
            self.data_dir, self.data_file_extension
        )
        # data_fnames = dirlist(self.data_dir, self.data_file_extension, remove_suffix=False)
        # only look at files that have an image and data file, then turn to list, then sort ascending
        # thumb_fnames = sorted( list(set(image_fnames) & set(data_fnames)) )
        if len(stack_dirs) > 0:
            data_fnames = data_fnames + stack_dirs

        thumb_fnames = sorted(data_fnames)
        # dirs = sorted(stack_dirs)
        image_thumb_lst = []
        spectra_thumb_lst = []
        iidx = 0

        # create a directory widget to go UP a directory
        th_wdg = self.make_updir_thumbwidget(self.data_dir)
        image_thumb_lst.append(th_wdg)

        if len(thumb_fnames) < 1:
            return
        #elif len(thumb_fnames) == 1:
        elif (len(thumb_fnames) == 1) and (len(stack_dirs) == 0):
            # there is only a single file in directory
            fstr = os.path.join(self.data_dir, thumb_fnames[0])
            # print(fstr)
            file_dct, data = self.get_nxstm_file_dct_and_data(fstr)
            if (file_dct is None) or (data is None):
                _logger.error(f"reload_view: problem loading [{fstr}],  self.get_nxstm_file_dct_and_data() returned None, None")
                return
            sp_db = get_first_sp_db_from_file_dct(file_dct)
            is_spec = False
            if (sp_db is not None) and (data is not None):
                # if (dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) not in [scan_types.GENERIC_SCAN,scan_types.SAMPLE_POINT_SPECTRUM]):
                if type(sp_db) == list:
                    #only use the first if its multi spatial
                    sp_db = sp_db[0]
                    data = data[0]
                if dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE) not in spectra_type_scans:
                    info_str, info_jstr = self.build_image_params(
                        fstr, sp_db, data, ev_idx=0, pol_idx=0
                    )
                    info_dct = {"info_str": info_str, "info_jstr": info_jstr}
                    th_wdg = self.make_thumbWidget(
                        self.data_dir,
                        thumb_fnames[0],
                        info_dct,
                        sp_db=sp_db,
                        data=data,
                        stype=dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE),
                    )
                else:
                    is_spec = True
                    fstr = os.path.join(self.data_dir, thumb_fnames[0])
                    info_str, info_jstr = self.build_image_params(
                        fstr, sp_db, data, ev_idx=0, pol_idx=0
                    )
                    info_dct = {"info_str": info_str, "info_jstr": info_jstr}
                    th_wdg = self.make_thumbWidget(
                        self.data_dir,
                        thumb_fnames[0],
                        info_dct,
                        sp_db=sp_db,
                        data=data,
                        stype=dct_get(sp_db, SPDB_SCAN_PLUGIN_TYPE),
                    )

                if not th_wdg:
                    # file must have had a problem with it
                    yPos = self.images_view.verticalScrollBar()
                    yPos.setValue(yPos.minimum())
                    return

                if is_spec:
                    spectra_thumb_lst.append(th_wdg)
                else:
                    image_thumb_lst.append(th_wdg)

        else:
            # there are multiple fnames and or directories
            for i in range(len(thumb_fnames)):
                iidx += 1
                if i >= len(thumb_fnames):
                    # if it is less than 1 full row
                    break
                is_folder = False
                fstr = os.path.normpath(os.path.join(self.data_dir, thumb_fnames[i]))
                # print(fstr)
                if os.path.isdir(fstr):
                    # this is likely a stack directory
                    data_dir, fprefix, fsuffix = get_file_path_as_parts(fstr)
                    _fname = os.path.join(fstr, fprefix + self.data_file_extension)
                    # dont say this is a stack dir because we are not creating all of the thumbnails for the stack here
                    # that is done elsewhere, so just return the first sp_db and data
                    if os.path.exists(_fname):
                        file_dct, data = self.get_nxstm_file_dct_and_data(_fname, stack_dir=False)
                        if (file_dct is None) or (data is None):
                            _logger.error(f"reload_view: problem loading [{fstr}],  self.get_nxstm_file_dct_and_data() returned None, None")
                            continue
                        sp_db = get_first_sp_db_from_file_dct(file_dct)
                    else:
                        _logger.warning("missing stack scan file [%s]" % _fname)
                        continue
                    _scan_type = get_pystxm_scan_type_from_file_dct(file_dct)
                    if (file_dct is None) or (data is None):
                        _logger.error("reload_view: problem loading [%s]" % fstr)
                        continue

                    info_str, info_jstr = self.build_image_params(
                        _fname, sp_db, data, ev_idx=0, pol_idx=0, is_folder=True
                    )
                    info_dct = {"info_str": info_str, "info_jstr": info_jstr}

                    if _scan_type in stack_scans:
                        is_folder = True

                    th_wdg = self.make_thumbWidget(
                        self.data_dir,
                        thumb_fnames[i],
                        info_dct,
                        sp_db={},
                        data=None,
                        stype=_scan_type,
                        is_folder=is_folder,
                    )
                    if (not th_wdg) or (not info_str):
                        continue
                    image_thumb_lst.append(th_wdg)

                    if progress_callback is not None:
                        progress_callback.emit(
                            int((float(iidx) / float(len(thumb_fnames))) * 100.0)
                        )
                else:
                    # its files
                    file_dct, data = self.get_nxstm_file_dct_and_data(fstr)
                    if (file_dct is None) or (data is None):
                        _logger.error(f"reload_view: problem loading [{fstr}],  self.get_nxstm_file_dct_and_data() returned None, None")
                        continue

                    sp_db = get_first_sp_db_from_file_dct(file_dct)
                    _scan_type = get_pystxm_scan_type_from_file_dct(file_dct)

                    # if (_scan_type not in spectra_type_scans):
                    if _scan_type not in spectra_type_scans:
                        fstr = os.path.join(self.data_dir, thumb_fnames[i])
                        info_str, info_jstr = self.build_image_params(
                            fstr, sp_db, data, ev_idx=0, pol_idx=0
                        )
                        info_dct = {"info_str": info_str, "info_jstr": info_jstr}
                        if _scan_type == scan_types.SAMPLE_IMAGE_STACK:
                            is_folder = True
                        else:
                            is_folder = False

                        th_wdg = self.make_thumbWidget(
                            self.data_dir,
                            thumb_fnames[i],
                            info_dct,
                            sp_db=sp_db,
                            data=data,
                            stype=_scan_type,
                            is_folder=is_folder
                        )

                        if not th_wdg:
                            continue
                        image_thumb_lst.append(th_wdg)

                        if progress_callback is not None:
                            progress_callback.emit(
                                int((float(iidx) / float(len(thumb_fnames))) * 100.0)
                            )
                    else:
                        fstr = os.path.join(self.data_dir, thumb_fnames[i])
                        info_str, info_jstr = self.build_image_params(
                            fstr, sp_db, data, ev_idx=0, pol_idx=0
                        )
                        info_dct = {"info_str": info_str, "info_jstr": info_jstr}

                        th_wdg = self.make_thumbWidget(
                            self.data_dir,
                            thumb_fnames[i],
                            info_dct,
                            sp_db=sp_db,
                            data=data,
                            stype=_scan_type,
                            is_folder=is_folder,
                        )

                        if not th_wdg:
                            continue
                        spectra_thumb_lst.append(th_wdg)

                        if progress_callback is not None:
                            progress_callback.emit(
                                int((float(iidx) / float(len(thumb_fnames))) * 100.0)
                            )

        return (image_thumb_lst, spectra_thumb_lst)

    def load_thumbs(self, image_thumb_lst_spectra_thumb_lst: Tuple[list]):
        """

        :param image_thumb_lst_spectra_thumb_lst:
        :return:
        """
        image_thumb_lst, spectra_thumb_lst = image_thumb_lst_spectra_thumb_lst

        self.do_load_thumbs(image_thumb_lst, self.image_thumbs, self.images_graphics_wdg,
                            self.images_scene, self.images_view)
        self.do_load_thumbs(spectra_thumb_lst, self.spectra_thumbs, self.spectra_graphics_wdg,
                            self.spectra_scene, self.spectra_view)



    def do_load_thumbs(self, thumbs: List[ThumbnailWidget], thumb_cache: List[ThumbnailWidget],
                       graphics_widget: MainGraphicsWidget, scene: QtWidgets.QGraphicsScene,
                       view: QtWidgets.QGraphicsView):
        """

        Parameters
        ----------
        thumbs
        thumb_cache
        graphics_widget
        scene
        view

        Returns
        -------

        """
        if not any(thumbs):
            return

        cols = get_max_thumb_columns(view.width())
        rows = math.ceil(len(thumbs) / cols)
        rowcol = list(itertools.product(range(rows), range(cols)))
        next_iter = 0
        for thumb in thumbs:
            if not thumb:
                continue
            row, col = rowcol[next_iter]
            next_iter += 1
            graphics_widget.gridlayout.addItem(thumb, row, col)
            thumb_cache.append(thumb)

        graphics_widget.set_cur_row(row)
        graphics_widget.set_cur_column(col + 1)

        self.do_update_scene(graphics_widget, scene, view)

    def split_data_dir(self, data_dir):
        """
        split_data_dir(): description

        :param data_dir: data_dir description
        :type data_dir: data_dir type

        :returns: None
        """
        if data_dir is None:
            return
        data_dir = data_dir.replace("\\", "/")
        sep = "/"
        if data_dir.find("/") > -1:
            sep = "/"
        elif data_dir.find("\\") > -1:
            sep = "\\"
        else:
            _logger.error("Unsupported directory string [%s]" % data_dir)

        d_lst = data_dir.split(sep)
        return d_lst

    def set_data_dir(self, data_dir, is_stack_dir=False, hide=False):
        """
        set_data_dir(): description

        :param data_dir: data_dir description
        :type data_dir: data_dir type

        :param is_stack_dir=False: is_stack_dir=False description
        :type is_stack_dir=False: is_stack_dir=False type

        :returns: None
        """
        # print 'set_data_dir: called'
        if len(data_dir) > 0:
            self.data_dir = data_dir
            d = self.split_data_dir(data_dir)
            # if d[-1] == '..':
            #     d = d[:-1]
            num_dirs = len(d) - 1
            fstr = os.path.join(d[num_dirs - 1], d[num_dirs])
            self.dir_lbl.setText(fstr)
            self.fsys_mon.set_data_dir(data_dir)
            if not is_stack_dir:
                # self.reload_view(is_stack_dir)
                self.load_image_items(is_stack_dir, hide=False)
                # profile_it("go", bias_val=1.2187378126218738e-06)

    def do_select(self, thumb):
        """
        do_select(): description

        :param thumb: thumb description
        :type thumb: thumb type

        :returns: None
        """
        for t in self.image_thumbs:
            if id(thumb) != id(t):
                t.is_selected = False
            else:
                t.is_selected = True
        self.update_view()

    def update_view(self):
        """
        update_view(): description

        :returns: None
        """
        self.images_view.update()
        # self.images_scene.update(rect=QtCore.QRectF(0,0,1500,1500))
        rect = self.images_scene.sceneRect()
        self.images_scene.update(
            rect=QtCore.QRectF(rect.left(), rect.top(), rect.width(), rect.height())
        )

    def print_thumbnail(self, dct):
        self.ptnw.print_file(dct)

    def preview_thumbnail(self, dct):
        self.ptnw.preview_file(dct)

    def launch_viewer(self, dct):
        """
        launch_viewer(): description

        :param dct: dct description
        :type dct: dct type

        :returns: None
        """
        if dct["scan_type"] in spectra_type_scans:
            self.launch_spectra_viewer(dct)
        else:
            self.launch_image_viewer(dct)

    def launch_spectra_viewer(self, dct: dict):
        fname = dct["path"]
        xdata = dct["xdata"]
        ydatas = dct["ydatas"]
        sp_db = dct["sp_db"]
        title = dct["title"]
        num_specs = len(ydatas)
        num_spec_pnts = len(xdata)
        data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)

        self.spec_win.clear_plot()
        for i in range(num_specs):
            color = get_next_color(use_dflt=False)
            style = get_basic_line_style(color)
            self.spec_win.create_curve(f"point_spectra_{i}", x=xdata, y=ydatas[i], curve_style=style)

        xlabel = dct.get("xlabel")
        self.spec_win.setPlotAxisStrs("counts", xlabel)

        self.spec_win.update()
        self.spec_win.set_autoscale()
        self.spec_win.show()
        self.spec_win.raise_()

    def launch_image_viewer(self, dct):
        import traceback

        # fname, data, title=None):
        try:
            fname = dct["path"]
            data = dct["data"]
            sp_db = dct["sp_db"]
            title = dct["title"]
            xlabel = dct.get("xlabel") or "X"
            ylabel = dct.get("ylabel") or "Y"
            if dct["scan_type"] is scan_types.SAMPLE_LINE_SPECTRUM:
                # sample line spec data may have different ev region resolutions so its special
                wdg_com = make_base_wdg_com()
                dct_put(wdg_com, WDGCOM_CMND, widget_com_cmnd_types.LOAD_SCAN)
                dct_put(wdg_com, SPDB_SPATIAL_ROIS, {sp_db[ID_VAL]: sp_db})
                self.image_win.do_load_linespec_file(
                    fname, wdg_com, data, dropped=False
                )
                self.image_win.setPlotAxisStrs(ylabel, xlabel)
                self.image_win.show()
                self.image_win.set_autoscale(fill_plot_window=True)
                self.image_win.raise_()

            else:
                data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
                rect = dct_get(sp_db, SPDB_RECT)
                self.image_win.openfile([fname], scan_type=dct["scan_type"], stack_index=dct.get("stack_index"))
                self.image_win.setPlotAxisStrs(ylabel, xlabel)
                self.image_win.show()
                self.image_win.raise_()

            if title is not None:
                self.image_win.plot.set_title(title)
            else:
                self.image_win.plot.set_title(f"{fprefix}{fsuffix}")

        except Exception:
            traceback.print_exc()

    def on_viewer_closeEvent(self, event: QtGui.QCloseEvent):
        self.image_win.delImagePlotItems()
        self.image_win.hide()
        event.ignore()

    def on_spec_viewer_closeEvent(self, event: QtGui.QCloseEvent):
        self.spec_win.delete_all_curve_items()
        self.spec_win.hide()
        event.ignore()

        reset_color_idx()


def run_contact_sheet():
    from cls.data_io.stxm_data_io import STXMDataIo
    log_to_qt()
    app = QtWidgets.QApplication(sys.argv)
    # app.setApplicationName("Pyqt Image gallery example")
    # dir = r"G:\SM\test_data\guest\0808"
    dir = r"T:\operations\STXM-data\ASTXM_upgrade_tmp\2024\guest\1231"
    # dir = r"T:\operations\STXM-data\ASTXM_upgrade_tmp\2024\guest\2024_05\0516"
    dir = r'C:\test_data\pixelator\wip'
    main = ContactSheet(data_dir=dir, data_io=STXMDataIo)
    # main.set_data_dir(dir)
    main.show()
    main.resize(385, 700)

    sys.exit(app.exec_())

def go_reload_view_profile():
    from cls.data_io.stxm_data_io import STXMDataIo

    log_to_qt()
    app = QtWidgets.QApplication(sys.argv)
    # app.setApplicationName("Pyqt Image gallery example")
    # dir = r"G:\SM\test_data\guest\0808"
    dir = r"T:\operations\STXM-data\ASTXM_upgrade_tmp\2024\guest\1231"

    main = ContactSheet(data_dir=dir, data_io=STXMDataIo)

    # main.set_data_dir(dir)
    main.show()
    main.resize(385, 700)
    sys.exit(app.exec_())

if __name__ == "__main__":
    from cls.utils.profiling import profile_it

    # profile_it("go_reload_view_profile", bias_val=1.2187378126218738e-06)
    run_contact_sheet()
