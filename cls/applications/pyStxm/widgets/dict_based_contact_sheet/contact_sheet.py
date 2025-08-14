from PyQt5 import QtCore, QtWidgets
import simplejson as json

from cls.appWidgets.dialogs import setExistingDirectory
from cls.types.stxmTypes import spectra_type_scans, scan_types
from cls.utils.log import get_module_logger
from cls.utils.fileUtils import get_file_path_as_parts
from cls.utils.dict_utils import dct_get, dct_put
from cls.utils.json_threadsave import NumpyAwareJSONEncoder
from cls.utils.roi_dict_defs import *
from cls.stylesheets import master_colors
from cls.utils.roi_utils import make_base_wdg_com, widget_com_cmnd_types
from cls.plotWidgets.imageWidget import make_default_stand_alone_stxm_imagewidget
from cls.data_io.stxm_data_io import STXMDataIo
from cls.stylesheets import get_style
from cls.plotWidgets.curveWidget import (
    get_next_color,
    get_basic_line_style,
    make_spectra_viewer_window,
    reset_color_idx,
)

from cls.applications.pyStxm.widgets.print_stxm_thumbnail import PrintSTXMThumbnailWidget

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.thumbnail_create import create_thumbnail
from cls.applications.pyStxm.widgets.dict_based_contact_sheet.thumbnail_widget import ThumbnailWidget
from cls.applications.pyStxm.widgets.dict_based_contact_sheet.utils import *

from cls.data_io.nxstxm_h5_to_dict import load_nxstxm_file_to_h5_file_dct

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.remote_file_mgr import DirectorySelectorWidget

_logger = get_module_logger(__name__)

class ContactSheet(QtWidgets.QWidget):
    sig_reload_dir = QtCore.pyqtSignal(str)
    sig_req_dir_list = QtCore.pyqtSignal(str)

    def __init__(self, main_obj=None, data_dir=None, data_io=None, base_data_dir='/tmp', parent=None):
        super(ContactSheet, self).__init__(parent)
        self.main_obj = main_obj
        self.dir_sel_wdg = DirectorySelectorWidget(main_obj, base_data_dir, data_dir)
        self.dir_sel_wdg.new_data_dir.connect(self.set_directory_label)
        self.dir_sel_wdg.clear_scenes.connect(self.on_clear_scenes)
        self.data_dir = data_dir
        self.base_data_dir = base_data_dir
        self.data_io_class = data_io
        self.image_win = self.create_image_viewer()
        self.spec_win = self.create_spectra_viewer()
        self.ptnw = PrintSTXMThumbnailWidget()

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)

        # Directory label
        self.dir_label = QtWidgets.QLabel(f"Current Directory: {self.data_dir}")
        main_layout.addWidget(self.dir_label)

        # Toolbar layout with buttons
        toolbar_layout = QtWidgets.QHBoxLayout()

        # Refresh button
        self.refreshBtn = QtWidgets.QToolButton()
        self.refreshBtn.setText("Refresh")
        self.refreshBtn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.refreshBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.refreshBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toolbar_layout.addWidget(self.refreshBtn)

        # Horizontal spacer
        toolbar_layout.addItem(QtWidgets.QSpacerItem(40, 20,
                                                     QtWidgets.QSizePolicy.Expanding,
                                                     QtWidgets.QSizePolicy.Minimum))

        # Change directory button
        self.changeDirBtn = QtWidgets.QToolButton()
        self.changeDirBtn.setText("Change Directory")
        self.changeDirBtn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        self.changeDirBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.changeDirBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toolbar_layout.addWidget(self.changeDirBtn)

        main_layout.addLayout(toolbar_layout)

        self.drag_enabled = True
        self.image_thumbs = []
        self.spectra_thumbs = []

        # Tab widget
        self.tab_widget = QtWidgets.QTabWidget()


        # Images tab
        images_tab = QtWidgets.QWidget()
        images_layout = QtWidgets.QVBoxLayout(images_tab)
        self.images_view = QtWidgets.QGraphicsView()
        self.images_scene = QtWidgets.QGraphicsScene()
        self.images_scene.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60)))  # Dark grey
        self.images_view.setScene(self.images_scene)
        images_layout.addWidget(self.images_view)
        self.tab_widget.addTab(images_tab, "Images")

        # Spectra tab
        spectra_tab = QtWidgets.QWidget()
        spectra_layout = QtWidgets.QVBoxLayout(spectra_tab)
        self.spectra_view = QtWidgets.QGraphicsView()
        self.spectra_scene = QtWidgets.QGraphicsScene()
        self.spectra_scene.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60)))  # Dark grey
        self.spectra_view.setScene(self.spectra_scene)
        spectra_layout.addWidget(self.spectra_view)
        self.tab_widget.addTab(spectra_tab, "Spectra")

        main_layout.addWidget(self.tab_widget)

        # Connect signals
        self.refreshBtn.clicked.connect(self.on_refresh_clicked)
        self.changeDirBtn.clicked.connect(self.on_change_dir_clicked)

        # Set window properties
        self.setWindowTitle("Contact Sheet Viewer")
        self.resize(800, 600)

    def create_image_viewer(self):
        """
        create an instance of the image viewer widget.
        """
        fg_clr = master_colors["plot_forgrnd"]["rgb_str"]
        bg_clr = master_colors["plot_bckgrnd"]["rgb_str"]
        min_clr = master_colors["plot_gridmaj"]["rgb_str"]
        maj_clr = master_colors["plot_gridmin"]["rgb_str"]

        image_win = make_default_stand_alone_stxm_imagewidget(data_io=STXMDataIo)
        image_win.setWindowTitle("Image Viewer")
        qssheet = get_style()
        image_win.setStyleSheet(qssheet)
        image_win.set_grid_parameters(bg_clr, min_clr, maj_clr)
        image_win.set_cs_grid_parameters(fg_clr, bg_clr, min_clr, maj_clr)
        image_win.closeEvent = self.on_viewer_closeEvent
        return image_win

    def create_spectra_viewer(self):
        """
        create an instance of the spectra viewer widget.
        """
        fg_clr = master_colors["plot_forgrnd"]["rgb_str"]
        bg_clr = master_colors["plot_bckgrnd"]["rgb_str"]
        min_clr = master_colors["plot_gridmaj"]["rgb_str"]
        maj_clr = master_colors["plot_gridmin"]["rgb_str"]

        spectra_win = make_spectra_viewer_window(data_io=STXMDataIo)
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

    def create_folder_thumbnail(self):
        """
        Create a thumbnail for the folder that will always be at the top-left corner of the images and spectra views.
        """

        folder_thumbnail = create_thumbnail({}, is_folder=True)
        # folder_thumbnail.setPos(0, 0)
        # Tag it so we can identify it later
        folder_thumbnail.setData(0, "folder_thumbnail")
        return folder_thumbnail

    def on_refresh_clicked(self):
        """
        signal handler for when the refresh button is clicked.
        """
        # Clear the images scene
        self.images_scene.clear()
        self.spectra_scene.clear()
        QtWidgets.QApplication.processEvents()
        self.dir_sel_wdg.reload_directory()

    def create_thumbnails_from_filelist(self, files: [str]) -> None:
        """
        """

        # Clear the images scene
        self.images_scene.clear()
        self.spectra_scene.clear()

        # Add file thumbnails without positioning (will be positioned by rearrange)
        for fname in files:
            try:
                if fname.find('discard') > -1:
                    continue

                data_dict = load_nxstxm_file_to_h5_file_dct(fname, ret_as_dict=True)
                self.create_thumbnail_from_data_dct(data_dict)

            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

        # Add a directory thumbnail that stays at top-left
        img_dir_thumbnail = self.create_folder_thumbnail()
        img_dir_thumbnail.dbl_clicked.connect(self.change_dir)
        self.images_scene.addItem(img_dir_thumbnail)

        spec_dir_thumbnail = self.create_folder_thumbnail()
        spec_dir_thumbnail.dbl_clicked.connect(self.change_dir)
        self.spectra_scene.addItem(spec_dir_thumbnail)

        # Arrange thumbnails based on current view size
        self.update_scene_layout()

    def create_thumbnail_from_h5_file_dct(self, h5_file_dct: dict) -> None:
        """
        Take a data_dct and create a thumbnail widget from it, adding it to the bottom of the scene.
        """
        if h5_file_dct is None:
            _logger.warning("create_thumbnail_from_h5_file_dct: h5_file_dct cannot be None")
            return

        thumbnail = create_thumbnail(h5_file_dct)

        if thumbnail.is_valid():
            thumbnail.select.connect(self.do_select)
            thumbnail.launch_viewer.connect(self.launch_viewer)
            thumbnail.print_thumb.connect(self.print_thumbnail)
            thumbnail.preview_thumb.connect(self.preview_thumbnail)
            if thumbnail.draggable:
                thumbnail.drag.connect(self.on_drag)

        _scan_type = h5_file_dct[h5_file_dct['default']]['sp_db_dct']['pystxm_enum_scan_type']
        if _scan_type in spectra_type_scans:
            scene = self.spectra_scene
            self.spectra_thumbs.append(thumbnail)
        else:
            scene = self.images_scene
            self.image_thumbs.append(thumbnail)

        # Find the bottom-most y position
        items = [item for item in scene.items() if isinstance(item, QtWidgets.QGraphicsWidget)]
        items = sorted(items, key=lambda item: item.pos().y())
        if items:
            max_y = max(item.pos().y() + item.boundingRect().height() for item in items)
        else:
            max_y = 0
        thumbnail.setPos(0, max_y + 10)  # 10 px margin

        scene.addItem(thumbnail)
        self.update_scene_layout()

    def update_scene_layout(self):
        """
        update_scene_layout(): description
        """
        # Arrange thumbnails based on current view size
        self.rearrange_scene_thumbnails(self.images_scene, self.images_view)
        self.rearrange_scene_thumbnails(self.spectra_scene, self.spectra_view)

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

        # # prev_cursor = self.cursor()
        # # QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        # # self.setCursor(QtCore.Qt.WaitCursor)
        # #set to default
        #
        # # check if directory contains a stack
        # if self.is_stack_dir(_dir):
        #     self.set_data_dir(_dir, is_stack_dir=True)
        #     dirs, data_fnames = dirlist_withdirs(_dir, self.data_file_extension)
        #     fname = os.path.join(_dir, data_fnames[0])
        #     # sp_db, data = self.get_stack_data(fname)
        #     #self.load_entries_into_view(data_fnames[0])
        #     self.load_stack_file_image_items(os.path.join(_dir, data_fnames[0]))
        #     self.current_contents_is_dir = True
        #     self.fsys_mon.set_data_dir(self.data_dir)
        #     # self.unsetCursor()
        #     return
        # elif self.is_stack_file(_dir):
        #     self.load_stack_file_image_items(_dir)
        #     self.current_contents_is_dir = False
        #     self.unsetCursor()
        #     return
        # elif os.path.isdir(_dir):
        #     pass
        #
        # if len(_dir) > 0:
        #     self.set_data_dir(_dir, is_stack_dir=False)
        #     self.fsys_mon.set_data_dir(self.data_dir)
        #
        # self.unsetCursor()
        # # QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(prev_cursor))

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
            if obj.scan_type is scan_types.GENERIC_SCAN:
                format = "application/dict-based-lineplot-stxmscan"
                dct = obj.get_generic_scan_launch_viewer_dct()
            elif obj.scan_type is scan_types.SAMPLE_POINT_SPECTRUM:
                format = "application/dict-based-lineplot-stxmscan"
                dct = obj.get_sample_point_spectrum_launch_viewer_dct()
            else:
                format = "application/dict-based-imageplot-stxmscan"
                dct = obj.get_standard_image_launch_viewer_dct()


            jstr = json.dumps(dct, cls=NumpyAwareJSONEncoder)

            itemData = QtCore.QByteArray()
            dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.WriteOnly)
            (
                dataStream
                << QtCore.QByteArray(bytearray(jstr.encode()))
                << QtCore.QByteArray(obj.data.tobytes())
                << (event.pos() - obj.rect().topLeft())
            )
            mimeData = QtCore.QMimeData()
            mimeData.setData(format, itemData)
            mimeData.setText(obj.info_jstr)

            drag = QtGui.QDrag(self)
            drag.setMimeData(mimeData)
            pos = event.pos() - obj.rect().topLeft()
            drag.setHotSpot(QtCore.QPoint(int(pos.x()), int(pos.y())))
            if obj.pixmap is not None:
                drag.setPixmap(obj.pixmap)

            if (
                drag.exec_(
                    QtCore.Qt.MoveAction | QtCore.Qt.CopyAction, QtCore.Qt.CopyAction
                )
                == QtCore.Qt.MoveAction
            ):
                pass
            else:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Only process resize if the widget has been properly initialized
        if hasattr(self, 'images_scene') and hasattr(self, 'spectra_scene'):
            self.rearrange_scene_thumbnails(self.images_scene, self.images_view)
            self.rearrange_scene_thumbnails(self.spectra_scene, self.spectra_view)

    def rearrange_scene_thumbnails(self, scene, view):
        """Rearrange thumbnails in the scene based on available width"""
        # Get all thumbnail items from the scene
        items = [item for item in scene.items() if isinstance(item, QtWidgets.QGraphicsWidget)]

        if not items:
            return

        # Calculate available width
        vscroll = view.verticalScrollBar()
        vscroll_width = vscroll.width() if vscroll.isVisible() else 0
        available_width = view.viewport().width() - vscroll_width - 20  # 20px margin

        # Calculate how many columns can fit
        items_per_row = max(1, int(available_width / (THUMB_WIDTH + 10)))

        # Rearrange items
        x_offset = 0
        y_offset = 0

        for i, item in enumerate(items):
            item.setPos(x_offset, y_offset)

            if (i + 1) % items_per_row == 0:
                x_offset = 0
                y_offset += THUMB_HEIGHT + 10
            else:
                x_offset += THUMB_WIDTH + 10

        # Update scene rect to fit all items
        scene.setSceneRect(scene.itemsBoundingRect())

    def on_change_dir_clicked(self):
        self.dir_sel_wdg.show()

    def set_directory_label(self, directory):
        self.dir_label.setText(f"Current Directory: {directory}")

    def on_clear_scenes(self):
        """
        Clear the images and spectra scenes.
        """
        self.images_scene.clear()
        self.spectra_scene.clear()
        # self.image_thumbs.clear()
        # self.spectra_thumbs.clear()
        self.update_view()

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
        """
        Launch the spectra viewer with the provided data dictionary.
        """
        xdata = dct["xdata"]
        xlabel = dct["xlabel"]
        ydatas = dct["ydatas"]
        num_specs = len(ydatas)

        self.spec_win.clear_plot()
        for i in range(num_specs):
            color = get_next_color(use_dflt=False)
            style = get_basic_line_style(color)
            self.spec_win.create_curve(f"point_spectra_{i}", x=xdata, y=ydatas[i], curve_style=style)

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
                #wdg_com = sp_db
                dct_put(wdg_com, WDGCOM_CMND, widget_com_cmnd_types.LOAD_SCAN)
                dct_put(wdg_com, SPDB_SPATIAL_ROIS, {sp_db[ID_VAL]: sp_db})
                self.image_win.do_load_linespec_file(
                    fname, wdg_com, data, dropped=False
                )
                self.image_win.setPlotAxisStrs(ylabel, xlabel)
                self.image_win.show()
                self.image_win.set_autoscale(fill_plot_window=True)
                self.image_win.raise_()
                if title is not None:
                    self.image_win.plot.set_title(title)
                else:
                    self.image_win.plot.set_title(f"{fprefix}{fsuffix}")

            else:
                data_dir, fprefix, fsuffix = get_file_path_as_parts(fname)
                rect = dct_get(sp_db, SPDB_RECT)
                # self.image_win.openfile([fname], scan_type=dct["scan_type"], stack_index=dct.get("stack_index"))
                self.image_win.load_image_data(
                    fname,
                    sp_db,
                    data,
                    addimages=False,
                    flipud=True,
                    name_lbl=True,
                    item_z=None,
                    show=True,
                    dropped=False,
                    stack_index=0)

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


if __name__ == "__main__":
    import sys
    from cls.data_io.stxm_data_io import STXMDataIo

    # Create QApplication
    app = QtWidgets.QApplication(sys.argv)

    # Create and show main window
    window = ContactSheet('/tmp', data_io=STXMDataIo)
    window.show()

    # Run application
    sys.exit(app.exec_())
