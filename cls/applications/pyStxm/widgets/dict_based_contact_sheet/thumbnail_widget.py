

import sys
import json
import os
import numpy as np
import simplejson as json

from PyQt5 import QtCore, QtGui, QtWidgets
from PIL import Image

from bcm.devices.epu import convert_wrapper_epu_to_str

from cls.utils.dict_utils import dct_get
from cls.utils.roi_dict_defs import *
from cls.utils.pixmap_utils import get_pixmap
from cls.utils.hdf_to_dict import (get_pystxm_scan_type_from_file_dct, get_first_sp_db_from_file_dct,
                                   get_default_data_from_hdf5_file)
from cls.utils.arrays import flip_data_upsdown
from cls.utils.images import array_to_gray_qpixmap, array_to_image

from cls.types.stxmTypes import scan_types, scan_sub_types, image_type_scans, spectra_type_scans, focus_scans
from cls.plotWidgets.lineplot_thumbnail import OneD_MPLCanvas
from cls.applications.pyStxm.widgets.print_stxm_thumbnail import (
    SPEC_THMB_WD,
    SPEC_THMB_HT,
)

from cls.utils.log import get_module_logger, log_to_qt

import cls.applications.pyStxm.widgets.dict_based_contact_sheet.utils as utils
from cls.applications.pyStxm.widgets.dict_based_contact_sheet.build_tooltip_info import dict_based_build_image_params

_logger = get_module_logger(__name__)

class ThumbnailWidget(QtWidgets.QGraphicsWidget):
    launch_viewer = QtCore.pyqtSignal(object)
    print_thumb = QtCore.pyqtSignal(object)
    preview_thumb = QtCore.pyqtSignal(object)

    drag = QtCore.pyqtSignal(object, object)
    dbl_clicked = QtCore.pyqtSignal(object)
    update_view = QtCore.pyqtSignal()
    select = QtCore.pyqtSignal(object)

    def __init__(self, data_dct, filename, is_folder=False, parent=None):
        super().__init__(parent)
        self.data_dct = data_dct
        self.filename = filename
        self.sp_db_dct = utils.get_sp_db_dct_from_data_dct(data_dct)
        if self.sp_db_dct is None:
            self.filepath = filename
            self.directory = filename
        else:
            self.filepath = self.sp_db_dct['file_path']
            self.directory = self.sp_db_dct['directory']

        self.entry_dct = None
        self.is_folder = is_folder
        self.is_selected = False
        self.draggable = True
        self.info_jstr = None

        self.setPreferredSize(utils.THUMB_WIDTH, utils.THUMB_HEIGHT)
        # Enable context menu for this graphics item
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton | QtCore.Qt.RightButton)

        if not is_folder:
            # Extract data using 'default' key
            default_entry = utils.get_first_entry_key(data_dct)
            self.entry_dct = data_dct.get(default_entry, {})

            # Get counter data
            data_section = self.entry_dct.get('data', {})
            default_counter = data_section.get('default', 'counter1')
            self.counter_data = np.array(data_section.get(default_counter, [[0]]))
            self.data = self.counter_data

            # Get scan info from sp_db_dct
            self.sp_db_dct = self.entry_dct.get('sp_db_dct', {})
            self.scan_type = self.sp_db_dct.get('pystxm_enum_scan_type', 'Unknown')
            self.energy = self.sp_db_dct.get('energy', [0])[0]

            if self.scan_type in focus_scans:
                self.draggable = False


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
            self.setAcceptHoverEvents(True)
        else:
            self.valid_file = False
            _logger.error(f"The file [{self.filename}] contains data that can't be plotted")

    def is_valid(self):
        """
        is_valid(): description

        :returns: None
        """
        return self.valid_file

    def mouseDoubleClickEvent(self, event):
        if self.is_folder:
            path = self.filename
            if self.filename.find("..") > -1:
                # we want an updir path emittted here
                path, folder = os.path.split(self.filename)
                path, folder = os.path.split(path)
                # print('DoubleClicked: [%s]' % path)
            # if currently showing directory contents and self.filename is a file, then load the stack
            if self.parent.current_contents_is_dir and os.path.isfile(path):
                self.dbl_clicked.emit(path)
            elif not self.parent.current_contents_is_dir:
                # we are currently showing a stack file and the updir double click should just reload the current directory
                #reload the directory
                self.dbl_clicked.emit(self.filename.replace("..", ""))
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
        border_size = 1
        labelheight = 20
        if self.pic != None:
            self.update(
                QtCore.QRectF(
                    0.0,
                    0.0,
                    self.pic.rect().width() + border_size,
                    self.pic.rect().height() + labelheight + border_size,
                )
            )
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)

        if btn == QtCore.Qt.MouseButton.LeftButton:
            self.drag.emit(self, event)

    def contextMenuEvent(self, event):
        """Create the popup menu for a right click on a thumbnail"""
        if (self.data is None) or self.is_folder:
            return

        menu = QtWidgets.QMenu()
        launchAction = menu.addAction("Send to Viewer")
        prevAction = menu.addAction("Print Preview")
        saveTiffAction = menu.addAction("Save as Tiff file")

        # For QGraphicsSceneContextMenuEvent, use screenPos()
        selectedAction = menu.exec_(event.screenPos())

        if selectedAction == launchAction:
            self.launch_vwr(self)
        elif selectedAction == prevAction:
            self.preview_it(self)
        elif selectedAction == saveTiffAction:
            self.save_tif(self)

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
            ekey = utils.get_first_entry_key(self.data_dct)
            entry_dct = self.data_dct[ekey]
            sp_db = utils.get_first_sp_db_from_entry(entry_dct)
            xdata = utils.get_axis_setpoints_from_sp_db(sp_db, axis="X")
            ydatas = utils.get_generic_scan_data_from_entry(entry_dct, counter=None)
            dct = {}
            # because the data in the StxmImageWidget is displayed with 0Y at the btm
            # and maxY at the top I must flip it before sending it
            # dct['data'] = np.flipud(data)
            dct["data"] = None
            dct["xdata"] = xdata
            dct["ydatas"] = ydatas
            dct["path"] = self.filename
            dct["sp_db"] = sp_db
            dct["scan_type"] = self.scan_type
            dct["xlabel"] = dct_get(sp_db, SPDB_XPOSITIONER)
            dct["ylabel"] = dct_get(sp_db, SPDB_YPOSITIONER)
            dct["title"] = None
            if sp_db is not None:
                dct["title"] = self.filename
            self.launch_viewer.emit(dct)

        elif self.scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
            # ekey = utils.get_first_entry_key(self.data_dct)
            # entry_dct = self.data_dct[ekey]
            # xdata = utils.get_point_spec_energy_data_setpoints_from_entry(entry_dct)

            ydatas = []
            # it matters that the data is in sequential entry order
            # ekeys = sorted(self.data_dct['entries'].keys())
            ekeys = sorted(
                [k for k, v in self.data_dct.items() if k.find("entry") > -1]
            )
            for ekey in ekeys:
                entry_dct = self.data_dct[ekey]
                sp_db = utils.get_first_sp_db_from_entry(entry_dct)
                # ydatas.append(utils.get_point_spec_data_from_entry(entry_dct))
                _data = np.array(utils.get_point_spec_data_from_entry(entry_dct))
                ydatas.append(_data.flatten())

            # ekey = utils.get_first_entry_key(self.data_dct)
            # entry_dct = self.data_dct[ekey]
            xdata = utils.get_point_spec_energy_data_setpoints_from_entry(entry_dct)

            dct = {}
            dct["data"] = None
            dct["xdata"] = xdata
            dct["ydatas"] = ydatas
            dct["path"] = self.filepath
            dct["sp_db"] = sp_db
            dct["scan_type"] = self.scan_type
            dct["xlabel"] = dct_get(sp_db, SPDB_XPOSITIONER)
            dct["ylabel"] = dct_get(sp_db, SPDB_YPOSITIONER)
            dct["title"] = None
            if sp_db is not None:
                dct["title"] = self.filename
            self.launch_viewer.emit(dct)

        else:
            ekey = utils.get_first_entry_key(self.data_dct)
            entry_dct = self.data_dct[ekey]
            sp_db = utils.get_first_sp_db_from_entry(entry_dct)
            data = self.data
            stack_index = None

            if self.data.ndim == 2:
                title = self.filename
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
            dct["path"] = self.filepath
            dct["sp_db"] = sp_db
            dct["scan_type"] = self.scan_type
            dct["xlabel"] = dct_get(sp_db, SPDB_XPOSITIONER)
            dct["ylabel"] = dct_get(sp_db, SPDB_YPOSITIONER)
            dct["title"] = None
            if sp_db is not None:
                dct["title"] = self.filename
            self.launch_viewer.emit(dct)

    def print_it(self, sender):
        """
        call PrintSTXMThumbnailWidget()
        :param sender:
        :return:
        """
        self = sender
        info_dct = json.loads(self.info_jstr)

        dct = {}
        dct["fpath"] = self.filepath
        dct["fname"] = self.filename
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
        # ekey = self.utils.get_first_entry_key(self.data_dct)
        # def_counter = self.data_dct['entries'][ekey]['default']
        dct = {}
        dct["fpath"] = self.filepath
        dct["fname"] = self.filename
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
        dct["data_dir"] = self.directory

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

        # print 'print_it called: %s'% self.filename

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
        im.save(self.filepath.replace(".hdf5", ".tif"))


    def get_specplot_pic(self, scale_it=True, as_thumbnail=True):
        """

        :param scale_it:
        :return:
        """
        axis_names = self.sp_db_dct['axis_names']
        x_axis_name = 'energy'
        for axis_name in axis_names:
            if 'energy' in axis_name.lower():
                x_axis_name = axis_name
        if x_axis_name not in self.sp_db_dct.keys():
            print("get_generic_scan_pic: x_axis_name not in self.sp_db_dct.keys()")
            return
        xdata = self.sp_db_dct[x_axis_name]
        ydatas = self.counter_data.flatten()

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
                QtCore.QSize(QtCore.QSize(utils.THMB_SIZE, utils.THMB_SIZE)),
                QtCore.Qt.KeepAspectRatio,
            )
        self.pixmap = pmap
        return pmap


    # def get_2dimage_pic(self, scale_it=True):
    #     """Create a pixmap from the counter data"""
    #     if self.counter_data.size > 0:
    #         # Normalize data to 0-255
    #         data_min = self.counter_data.min()
    #         data_max = self.counter_data.max()
    #         if data_max > data_min:
    #             normalized = ((self.counter_data - data_min) / (data_max - data_min) * 255).astype(np.uint8)
    #         else:
    #             normalized = np.zeros_like(self.counter_data, dtype=np.uint8)
    #
    #         # Create QImage
    #         height, width = normalized.shape
    #         image = QtGui.QImage(normalized.data, width, height, width, QtGui.QImage.Format_Indexed8)
    #         image.setColorTable(utils.COLORTABLE)
    #
    #         # Convert to pixmap and scale to fill most of the widget
    #         # Minimal space for text: 2px margins + 12px per text line + spacing
    #         text_height = 12
    #         spacing = 2
    #         # total_text_space = (spacing * 3) + (text_height * 2)  # ~30px total
    #         total_text_space = (spacing * 3) + (text_height)  # ~30px total
    #
    #         pixmap_width = utils.THUMB_WIDTH - 4  # 2px margins on each side
    #         pixmap_height = utils.THUMB_HEIGHT - total_text_space
    #
    #         pmap = QtGui.QPixmap.fromImage(image)
    #
    #         if scale_it:
    #             # pmap = pmap.scaled(QtCore.QSize(QtCore.QSize(THMB_SIZE, THMB_SIZE)),  QtCore.Qt.KeepAspectRatio)
    #             # pmap = pmap.scaled(
    #             #     QtCore.QSize(QtCore.QSize(THMB_SIZE, THMB_SIZE)),
    #             #     QtCore.Qt.IgnoreAspectRatio,
    #             # )
    #             pmap = pmap.scaled(
    #                 int(pixmap_width),
    #                 int(pixmap_height),
    #                 QtCore.Qt.KeepAspectRatio,
    #                 QtCore.Qt.FastTransformation
    #             )
    #         else:
    #             ht, wd = self.data.shape
    #             # pmap.scaled(QtCore.QSize(QtCore.QSize(wd, ht)), QtCore.Qt.KeepAspectRatio)
    #             pmap.scaled(QtCore.QSize(QtCore.QSize(wd, ht)), QtCore.Qt.IgnoreAspectRatio)
    #
    #
    #
    #
    #     else:
    #         # Create empty pixmap that fills most of the widget
    #         text_height = 12
    #         spacing = 2
    #         total_text_space = (spacing * 3) + (text_height * 2)
    #
    #         pixmap_width = utils.THUMB_WIDTH
    #         pixmap_height = utils.THUMB_HEIGHT - total_text_space
    #         pmap = QtGui.QPixmap(pixmap_width, pixmap_height)
    #         pmap.fill(QtCore.Qt.lightGray)
    #     self.pixmap = pmap
    #     return pmap

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
                QtCore.QSize(QtCore.QSize(utils.THMB_SIZE, utils.THMB_SIZE)),
                QtCore.Qt.IgnoreAspectRatio,
            )
        else:
            ht, wd = self.data.shape
            # pmap.scaled(QtCore.QSize(QtCore.QSize(wd, ht)), QtCore.Qt.KeepAspectRatio)
            pmap.scaled(QtCore.QSize(QtCore.QSize(wd, ht)), QtCore.Qt.IgnoreAspectRatio)

        self.pixmap = pmap
        return pmap

    def get_generic_scan_pic(self, scale_it=True, as_thumbnail=True):
        """

        :param scale_it:
        :return:
        """
        axis_names = self.entry_dct['sp_db_dct']['axis_names']
        x_axis_name = 'sample_x'
        for axis_name in axis_names:
            if '_x' in axis_name.lower():
                x_axis_name = axis_name
        if x_axis_name not in self.entry_dct['sp_db_dct'].keys():
            print("get_generic_scan_pic: x_axis_name not in entry_dct['sp_db_dct'].keys()")
            return
        xdata = self.entry_dct['sp_db_dct'][x_axis_name]
        #ydatas = utils.get_generic_scan_data_from_entry(entry_dct, counter=counter)
        ydatas = list(self.counter_data.flatten())

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
                QtCore.QSize(QtCore.QSize(utils.THMB_SIZE, utils.THMB_SIZE)),
                QtCore.Qt.KeepAspectRatio,
            )
        self.pixmap = pmap
        return pmap

    def get_folder_pic(self, scale_it=True, as_thumbnail=True):
        """
        pmap = get_pixmap(os.path.join(utils.icoDir, 'reload.ico'), ICONSIZE, ICONSIZE)
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

        if self.filename.find(".") > -1:
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
            pmap = get_pixmap(os.path.join(utils.icoDir, image_fname), sz_x, sz_y)
        else:
            # return a higher res pixmap for eventual printing
            pmap = get_pixmap(os.path.join(utils.icoDir, image_fname), sz_x, sz_y)
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(SPEC_THMB_WD, SPEC_THMB_HT)),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

        if as_thumbnail:
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(utils.THMB_SIZE, utils.THMB_SIZE)),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
        self.pixmap = pmap
        return pmap

    def boundingRect(self):
        return QtCore.QRectF(0, 0, utils.THUMB_WIDTH, utils.THUMB_HEIGHT)

    def paint(self, painter, option, widget):
        # Draw border
        if self.is_selected:
            #print(f"ThumbnailWidget: {self.filename} is selected")
            # Option 1: Use Qt's predefined cyan (light blue)
            painter.setPen(QtGui.QPen(QtCore.Qt.cyan, 2))

            # Option 2: Use a custom light blue color
            # painter.setPen(QtGui.QPen(QtGui.QColor(135, 206, 250), 2))  # Light sky blue

            # Option 3: Another light blue shade
            # painter.setPen(QtGui.QPen(QtGui.QColor(173, 216, 230), 2))  # Light blue
        else:
            #print(f"ThumbnailWidget: {self.filename} is DEselected")
            painter.setPen(QtGui.QPen(QtCore.Qt.black, 1))  # Black border, 1px width

        painter.drawRect(self.boundingRect())

        # Set font for text
        painter.setPen(QtCore.Qt.black)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # Reserve minimal space for text
        text_height = 16  # Height for text line
        spacing = 2  # Small spacing between elements

        # Draw data image with minimal margins
        img_x = int((utils.THUMB_WIDTH - self.pixmap.width()) / 2)
        img_y = spacing  # Very small top margin
        painter.drawPixmap(img_x, img_y, self.pixmap)

        # Draw grey background for text area
        text_area_height = text_height + spacing * 2
        text_rect = QtCore.QRectF(0, utils.THUMB_HEIGHT - text_area_height, utils.THUMB_WIDTH, text_area_height)
        painter.fillRect(text_rect, QtGui.QColor(200, 200, 200))  # Light grey

        # Draw filename at bottom (only text line)
        painter.drawText(5, utils.THUMB_HEIGHT - text_height - spacing, utils.THUMB_WIDTH - 10, text_height,
                         QtCore.Qt.AlignLeft | QtCore.Qt.TextWordWrap,
                         os.path.basename(self.filename))