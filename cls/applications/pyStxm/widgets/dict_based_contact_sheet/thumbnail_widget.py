
import os
import numpy as np
import simplejson as json

from PyQt5 import QtCore, QtGui, QtWidgets
from PIL import Image

from cls.utils.arrays import convert_numpy_to_python
from cls.utils.dict_utils import dct_get
from cls.utils import roi_dict_defs as roi_defs
from cls.utils.pixmap_utils import get_pixmap
from cls.utils.arrays import flip_data_upsdown
from cls.utils.images import array_to_gray_qpixmap, array_to_image, numpy_rgb_to_qpixmap, data_to_rgb

from cls.types.stxmTypes import scan_types, spectra_type_scans, focus_scans, stack_scans
from cls.plotWidgets.lineplot_thumbnail import OneD_MPLCanvas
from cls.applications.pyStxm.widgets.print_stxm_thumbnail import (
    SPEC_THMB_WD,
    SPEC_THMB_HT,
)

from cls.utils.log import get_module_logger
import cls.applications.pyStxm.widgets.dict_based_contact_sheet.utils as utils

FILENAME_FONT_SIZE = 9

_logger = get_module_logger(__name__)

class ThumbnailWidget(QtWidgets.QGraphicsWidget):
    launch_viewer = QtCore.pyqtSignal(object)
    print_thumb = QtCore.pyqtSignal(object)
    preview_thumb = QtCore.pyqtSignal(object)

    drag = QtCore.pyqtSignal(object, object)
    dbl_clicked = QtCore.pyqtSignal(object)
    update_view = QtCore.pyqtSignal()
    select = QtCore.pyqtSignal(object)

    def __init__(self, h5_file_dct, filename, is_folder=False, data=None, energy=None, is_stack=False, parent=None):
        super().__init__(parent)
        self.is_stack = is_stack
        self.h5_file_dct = h5_file_dct

        self.filename = filename
        self.sp_db_dct = utils.get_sp_db_dct_from_h5_file_dct(h5_file_dct)
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
        self.pixmap = None
        self.default_counter = None
        self._original_pos = None

        self.setPreferredSize(utils.THUMB_WIDTH, utils.THUMB_HEIGHT)
        # Enable context menu for this graphics item
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton | QtCore.Qt.RightButton)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setEnabled(True)

        # Extract data using 'default' key
        default_entry = utils.get_first_entry_key(h5_file_dct)
        self.entry_dct = h5_file_dct.get(default_entry, {})

        # Get counter data
        data_section = self.entry_dct['sp_db_dct'].get('nxdata', {})
        self.default_counter = data_section.get('default', list(data_section.keys())[0])
        if data is None:
            self.counter_data = np.array(data_section.get(self.default_counter, [[0]]))
            # make sure any None values are converted to nan
            self.counter_data = np.where(self.counter_data == None, np.nan, self.counter_data).astype(float)
            self.energy = self.sp_db_dct.get('energy', [0])[0]
        else:
            # use the data passed in, likely for a stack thumb
            self.counter_data = data
            self.energy = energy

        self.data = self.counter_data

        # Get scan info from sp_db_dct
        self.sp_db_dct = self.entry_dct.get('sp_db_dct', {})
        self.scan_type = self.sp_db_dct.get('pystxm_enum_scan_type', 'Unknown')

        if is_stack:
            # create a draggable h5_file_dct for stacks
            self.drag_h5_file_dct = {}
            ekey = utils.get_first_entry_key(h5_file_dct)
            self.drag_h5_file_dct['default'] = ekey
            self.drag_h5_file_dct[ekey] = {}
            self.drag_h5_file_dct[ekey]['WDG_COM'] = h5_file_dct[ekey]['WDG_COM']
            self.drag_h5_file_dct[ekey]['sp_db_dct'] = {}
            skip_lst = ['nxdata']
            for k in h5_file_dct[ekey]['sp_db_dct'].keys():
                if k in skip_lst:
                    continue
                self.drag_h5_file_dct[ekey]['sp_db_dct'][k] = h5_file_dct[ekey]['sp_db_dct'][k]

            self.drag_h5_file_dct[ekey]['sp_db_dct']['nxdata'] = {}
            #self.drag_h5_file_dct[ekey]['sp_db_dct']['nxdata'][self.default_counter] = self.counter_data[0]
            self.drag_h5_file_dct[ekey]['sp_db_dct']['nxdata'][self.default_counter] = None

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

        self.pixmap = self.getpic()

        if self.pixmap:
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
        """
        only support double click events for the left mouse button for stacks
        """
        if self.scan_type == scan_types.SAMPLE_IMAGE_STACK:
            # if this is a stack, then we want to emit the signal to load the stack
            self.dbl_clicked.emit(self)

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
        if self.pixmap is not None:
            self.update(
                QtCore.QRectF(
                    0.0,
                    0.0,
                    self.pixmap.rect().width() + border_size,
                    self.pixmap.rect().height() + labelheight + border_size,
                )
            )

        if btn == QtCore.Qt.LeftButton:
            self._original_pos = self.pos()
            self._drag_start_pos = event.pos()

        QtWidgets.QGraphicsItem.mousePressEvent(self, event)


    def mouseMoveEvent(self, event):
        """
        mouseMoveEvent(): check to see if the thumbwidget is being dragged before emitting drag signal
        """
        if event.buttons() & QtCore.Qt.LeftButton:
            if hasattr(self, '_drag_start_pos'):
                distance = (event.pos() - self._drag_start_pos).manhattanLength()
                if distance >= QtWidgets.QApplication.startDragDistance():
                    self.drag.emit(self, event)
        QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        """
        mouseReleaseEvent(): when mouse Release make sure thumbwidget goes back to its original location
        """
        if hasattr(self, '_original_pos') and self._original_pos is not None:
            self.setPos(self._original_pos)  # Reset to original position
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)

    def contextMenuEvent(self, event):
        """Create the popup menu for a right click on a thumbnail"""
        if (self.data is None) or self.is_folder:
            return

        menu = QtWidgets.QMenu()
        launchAction = menu.addAction("Send to Viewer")
        prevAction = menu.addAction("Print Preview")
        # saveTiffAction = menu.addAction("Save as Tiff file")

        # For QGraphicsSceneContextMenuEvent, use screenPos()
        selectedAction = menu.exec_(event.screenPos())

        if selectedAction == launchAction:
            self.launch_vwr(self)
        elif selectedAction == prevAction:
            self.preview_it(self)
        # elif selectedAction == saveTiffAction:
        #     self.save_tif(self)

    def get_generic_scan_launch_viewer_dct(self):
        ekey = utils.get_first_entry_key(self.h5_file_dct)
        entry_dct = self.h5_file_dct[ekey]
        sp_db = utils.get_first_sp_db_from_entry(entry_dct)
        xdata = utils.get_axis_setpoints_from_sp_db(sp_db, axis="X")
        # ydatas = utils.get_generic_scan_data_from_entry(entry_dct, counter=None)
        ydata_lst = [self.counter_data.flatten()]

        dct = {}
        dct["data"] = self.counter_data.flatten()
        dct["xdata"] = xdata
        dct["ydatas"] = ydata_lst
        dct["path"] = self.filename
        dct["sp_db"] = sp_db
        dct["h5_file_dct"] = self.h5_file_dct
        dct["scan_type"] = self.scan_type
        dct['scan_type_str'] = dct_get(sp_db, roi_defs.SPDB_SCAN_PLUGIN_SECTION_ID)
        dct["xlabel"] = dct_get(sp_db, roi_defs.SPDB_XPOSITIONER)
        dct["ylabel"] = dct_get(sp_db, roi_defs.SPDB_YPOSITIONER)
        dct["title"] = None
        if sp_db is not None:
            dct["title"] = self.filename
        return dct

    def get_sample_point_spectrum_launch_viewer_dct(self):
        """
        create a dictionary for the sample point spectrum viewer, this is also used for print preview
        needs to support multiple counters for an entry

        ToDO: currently this only supports the default counter in the default entry, wwill need to be updated to handle
        multi spatial point spectra
        """

        ydata_lst = []
        ekey = utils.get_first_entry_key(self.h5_file_dct)
        entry_dct = self.h5_file_dct[ekey]
        sp_db = utils.get_first_sp_db_from_entry(entry_dct)
        ydata_lst.append(self.counter_data.flatten())
        xdata = utils.get_point_spec_energy_data_setpoints_from_entry(entry_dct)

        dct = {}
        dct["data"] = ydata_lst
        dct["xdata"] = xdata
        dct["ydatas"] = ydata_lst
        dct["path"] = self.filepath
        dct["sp_db"] = sp_db
        dct["h5_file_dct"] = self.h5_file_dct
        dct["scan_type"] = self.scan_type
        dct['scan_type_str'] = dct_get(sp_db, roi_defs.SPDB_SCAN_PLUGIN_SECTION_ID)
        dct["xlabel"] = dct_get(sp_db, roi_defs.SPDB_XPOSITIONER)
        dct["ylabel"] = dct_get(sp_db, roi_defs.SPDB_YPOSITIONER)
        dct["title"] = None
        if sp_db is not None:
            dct["title"] = self.filename
        return dct

    def get_standard_image_launch_viewer_dct(self):
        """
             #roi_defs.SPDB_SCAN_PLUGIN_SECTION_ID = entry_dct['sp_db_dct']['stxm_scan_type']
        """
        ekey = utils.get_first_entry_key(self.h5_file_dct)
        entry_dct = self.h5_file_dct[ekey]
        sp_db = utils.get_first_sp_db_from_entry(entry_dct)
        # data = self.data
        if self.scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
            #data = np.transpose(self.data).copy()
            data = self.data.copy()
        else:
            #data = np.flipud(self.data).copy()
            data = self.data.copy()
        stack_index = None

        if data.ndim == 2:
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
        dct["data"] = data
        dct["stack_index"] = stack_index
        dct["path"] = self.filepath
        dct["sp_db"] = sp_db
        if self.is_stack:
            dct["h5_file_dct"] = self.drag_h5_file_dct
        else:
            dct["h5_file_dct"] = self.h5_file_dct

        dct['scan_type_str'] = dct_get(sp_db, roi_defs.SPDB_SCAN_PLUGIN_SECTION_ID)
        dct["scan_type"] = self.scan_type
        dct["xlabel"] = dct_get(sp_db, roi_defs.SPDB_XPOSITIONER)
        dct["ylabel"] = dct_get(sp_db, roi_defs.SPDB_YPOSITIONER)
        dct["title"] = None
        if sp_db is not None:
            dct["title"] = self.filename
        return dct

    def launch_vwr(self, sender):
        """
        launch_vwr(): description
        need to decide in here what teh scan_type is and create the data such that all data is passed that is needed to recreate the plot by curveViewer widget
        self.sp_db contains everything
        :returns: None
        """
        # print 'launch_viewer %s.hdf5' % self.hdf5_path
        self = sender
        json.loads(self.info_jstr)
        if self.scan_type is scan_types.GENERIC_SCAN:
            dct = self.get_generic_scan_launch_viewer_dct()
            self.launch_viewer.emit(dct)

        elif self.scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
            dct = self.get_sample_point_spectrum_launch_viewer_dct()
            self.launch_viewer.emit(dct)

        else:
            dct = self.get_standard_image_launch_viewer_dct()
            self.launch_viewer.emit(dct)

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
        dct["data_pmap"] = self.getpic(as_thumbnail=False)
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

        if self.scan_type in [scan_types.SAMPLE_POINT_SPECTRUM, scan_types.SAMPLE_LINE_SPECTRUM]:
            # override
            dct["xstart"] = info_dct["estart"]
            dct["xstop"] = info_dct["estop"]
            dct["xcenter"] = (info_dct["estart"] + info_dct["estop"]) * 0.5
            dct["xrange"] = info_dct["estop"] - info_dct["estart"]
            dct["xpositioner"] = "Energy (eV)"
            dct["ypositioner"] = self.default_counter

        type_tpl = info_dct["scan_type"].split()
        dct["scan_type"] = type_tpl[0]
        dct["scan_type_num"] = info_dct["scan_type_num"]
        dct["scan_sub_type"] = type_tpl[1]
        dct["data_dir"] = self.directory

        if self.data.ndim == 3:
            data = self.data[0]
        else:
            data = self.data

        if dct["scan_type"] in [scan_types[scan_types.SAMPLE_POINT_SPECTRUM]]:
            dct["data_min"] = data.min()
            dct["data_max"] = data.max()
        else:

            if data is not None:
                dct["data_min"] = data.min()
                dct["data_max"] = data.max()
            else:
                _logger.error("self.data cannot be None")
                return

        dct["info_dct"] = info_dct
        dct["counter_nm"] = self.default_counter

        # print 'print_it called: %s'% self.filename

        #make sure that the data is converted to a python dict, nans mainly
        self.preview_thumb.emit(convert_numpy_to_python(dct))

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


    def get_2dimage_pic(self, scale_it=True, as_thumbnail=True):
        """
        getpic(): description

        :returns: None
        """
        if self.data is not None:
            if len(self.data.shape) == 2:
                ht, wd = self.data.shape
                # data = flip_data_upsdown(self.data)
                if self.scan_type == scan_types.SAMPLE_LINE_SPECTRUM:
                    #data = np.transpose(self.data).copy()
                    data = np.flipud(self.data).copy()
                else:
                    data = np.flipud(self.data).copy()
                    #data = self.data.copy()

            elif len(self.data.shape) == 3:
                data = np.flipud(self.data[0]).copy()
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

        return pmap

    def get_specplot_pic(self, as_thumbnail=True):
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
        pmap = self._get_spec_pixmap(xdata, ydatas, as_thumbnail)
        return pmap

    def get_generic_scan_pic(self, as_thumbnail=True):
        """

        :param scale_it:
        :return:
        """
        x_axis_name = self.entry_dct['sp_db_dct']['axis_names'][0]
        if x_axis_name not in self.entry_dct['sp_db_dct'].keys():
            e_str = f"ERROR: get_generic_scan_pic: x_axis_name [{x_axis_name}] not in entry_dct['sp_db_dct'].keys()"
            print(e_str)
            _logger.error(e_str)
            return
        xdata = self.entry_dct['sp_db_dct'][x_axis_name]
        #ydatas = utils.get_generic_scan_data_from_entry(entry_dct, counter=counter)
        ydatas = self.counter_data.flatten()
        pmap = self._get_spec_pixmap(xdata, ydatas, as_thumbnail)
        return pmap

    def _get_spec_pixmap(self, xdata, ydatas, as_thumbnail=True):
        """
        return a spectrum matplotlib pixmap from the data
        """
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
                    fullsize_plot=True
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
                    fullsize_plot=False
                )
                pmap = qt_mpl.get_pixmap(as_grayscale=False, as_thumbnail=False)

        if as_thumbnail:
            pmap = pmap.scaled(
                QtCore.QSize(QtCore.QSize(utils.THMB_SIZE, utils.THMB_SIZE)),
                QtCore.Qt.KeepAspectRatio,
            )
        return pmap

    def overlay_icon_on_pixmap(self, base_pixmap, icon_path='stack_files.png', x=5, y=5, size=24):
        """
        overlay an icon on the base_pixmap at position x,y
        """
        icon_pixmap = QtGui.QPixmap(icon_path)
        if not icon_pixmap.isNull():
            icon_pixmap = icon_pixmap.scaled(size, size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            painter = QtGui.QPainter(base_pixmap)
            painter.drawPixmap(x, y, icon_pixmap)
            painter.end()
        return base_pixmap

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
        is_stack = False
        if self.filename.find("..") > -1:
            # image_fname = 'updir.png'
            # image_fname = 'open-folder-icon-png.png'
            image_fname = "directory_up_bw.png"

        else:
            if self.scan_type is scan_types.SAMPLE_IMAGE_STACK:
                image_fname = "stack.bmp"
                is_stack = True
            elif self.scan_type is scan_types.TOMOGRAPHY:
                # image_fname = 'tomo.png'
                image_fname = "folder_bw_tomo.png"
            else:
                image_fname = "folder_bw.ico"

        if is_stack:
            # make a thumbnail from the stack data

            arr = data_to_rgb(np.flipud(np.transpose(self.data, [1, 2, 0])), alpha=True)
            pmap = numpy_rgb_to_qpixmap(arr)
            if pmap is None:
                # fallback to the icon
                pmap = get_pixmap(os.path.join(utils.icoDir, image_fname), sz_x, sz_y)

            pmap = self.overlay_icon_on_pixmap(pmap, icon_path=os.path.join(utils.icoDir, 'stack_files.png'),
                                               x=100, y=3, size=44)

        elif as_thumbnail:
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

        return pmap

    def boundingRect(self):
        return QtCore.QRectF(0, 0, utils.THUMB_WIDTH, utils.THUMB_HEIGHT)

    def paint(self, painter, option, widget):
        # Draw data image with minimal margins
        if self.pixmap is None:
            e_str = "self.pixmap is None in paint()"
            print(e_str)
            _logger.error(e_str)
            return
        
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
        font.setPointSize(FILENAME_FONT_SIZE)
        painter.setFont(font)

        # Reserve minimal space for text
        text_height = 16  # Height for text line
        spacing = 2  # Small spacing between elements

        img_x = int((utils.THUMB_WIDTH - self.pixmap.width()) / 2)
        img_y = spacing  # Very small top margin
        painter.drawPixmap(img_x, img_y, self.pixmap)

        # Draw grey background for text area
        text_area_height = text_height + spacing * 2
        text_rect = QtCore.QRectF(0, utils.THUMB_HEIGHT - text_area_height, utils.THUMB_WIDTH, text_area_height)
        painter.fillRect(text_rect, QtGui.QColor(200, 200, 200))  # Light grey

        # Draw filename at bottom (only text line)
        if self.filename.find(".hdf5") > -1:
            # its the filename
            align_flag = QtCore.Qt.AlignLeft
        else:
            # its a stack energy value
            align_flag = QtCore.Qt.AlignHCenter

        painter.drawText(5, utils.THUMB_HEIGHT - text_height - spacing, utils.THUMB_WIDTH - 10, text_height,
                         align_flag | QtCore.Qt.TextWordWrap,
                         os.path.basename(self.filename))