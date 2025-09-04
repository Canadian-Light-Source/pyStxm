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
from cls.utils.arrays import convert_numpy_to_python
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

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.remote_directory_selector_mgr import RemoteDirectorySelectorWidget

_logger = get_module_logger(__name__)

class ThumbnailSceneManager:
    def __init__(self, image_graphics_view, spec_graphics_view):
        self.image_graphics_view = image_graphics_view
        self.spec_graphics_view = spec_graphics_view
        self.scenes = {}  # Maps directory name to (image_scene, spec_scene)
        self.history = []  # Browser-like history of directories
        self.current_index = -1

    def get_current_scene_directory(self):
        """Return the current scene's directory or None if no scenes exist."""
        if self.current_index >= 0 and self.current_index < len(self.history):
            return self.history[self.current_index]
        return None

    def get_last_scene_directory(self):
        """Return the current scene's directory or None if no scenes exist."""
        return self.history[-1] if self.history else None


    def switch_to_scene(self, directory):
        """Switch to a scene and update history like a browser."""
        if directory in self.scenes:
            # If not at the end, truncate forward history
            if self.current_index < len(self.history) - 1:
                self.history = self.history[:self.current_index + 1]
            # Add new directory to history if not already current
            if not self.history or self.history[self.current_index] != directory:
                self.history.append(directory)
                self.current_index = len(self.history) - 1
            image_scene, spec_scene = self.scenes[directory]
            self.image_graphics_view.setScene(image_scene)
            self.spec_graphics_view.setScene(spec_scene)
            return True
        return False

    def create_scenes(self, directory=None, force_new=False):
        """Create or return scenes, and update history if new."""
        update_history = True
        if directory in self.scenes and not force_new:
            return self.scenes[directory]
        elif directory in self.scenes and force_new:
            # we are replacing this scene with a new one
            update_history = False
        image_scene = QtWidgets.QGraphicsScene()
        image_scene.directory = directory
        image_scene.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60)))
        spec_scene = QtWidgets.QGraphicsScene()
        spec_scene.directory = directory
        spec_scene.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(60, 60, 60)))
        self.scenes[directory] = (image_scene, spec_scene)
        # Update history
        if update_history:
            if self.current_index < len(self.history) - 1:
                self.history = self.history[:self.current_index + 1]
            self.history.append(directory)
            self.current_index = len(self.history) - 1
        self.image_graphics_view.setScene(image_scene)
        self.spec_graphics_view.setScene(spec_scene)
        return (image_scene, spec_scene)

    def show_previous_scene(self):
        """Go back in history."""
        if self.current_index > 0:
            self.current_index -= 1
            dir_name = self.history[self.current_index]
            image_scene, spec_scene = self.scenes[dir_name]
            self.image_graphics_view.setScene(image_scene)
            self.spec_graphics_view.setScene(spec_scene)
            return (image_scene, spec_scene)
        return (None, None)

    def show_next_scene(self):
        """Go forward in history."""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            dir_name = self.history[self.current_index]
            image_scene, spec_scene = self.scenes[dir_name]
            self.image_graphics_view.setScene(image_scene)
            self.spec_graphics_view.setScene(spec_scene)
            return (image_scene, spec_scene)
        return (None, None)

class ContactSheet(QtWidgets.QWidget):

    def __init__(self, main_obj=None, data_dir=None, data_io=None, base_data_dir='/tmp', parent=None):
        super(ContactSheet, self).__init__(parent)

        self.dir_sel_wdg = RemoteDirectorySelectorWidget(main_obj, base_data_dir, data_dir)
        self.dir_sel_wdg.create_scenes.connect(self.create_new_scenes)
        self.dir_sel_wdg.loading_data.connect(self.on_loading_data)

        self.data_dir = data_dir
        self.image_win = self.create_image_viewer()
        self.spec_win = self.create_spectra_viewer()
        self.ptnw = PrintSTXMThumbnailWidget()

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)

        # Directory label
        self.dir_label = QtWidgets.QLabel(self.data_dir)
        self.dir_label.setAlignment(QtCore.Qt.AlignRight)
        self.dir_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        self.dir_label.setFixedWidth(680)  # Set to desired width
        main_layout.addWidget(self.dir_label)

        # Toolbar layout with buttons
        toolbar_layout = QtWidgets.QHBoxLayout()

        # Refresh button
        self.reloadBtn = QtWidgets.QToolButton()
        self.reloadBtn.setText("Reload")
        self.reloadBtn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        self.reloadBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.reloadBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toolbar_layout.addWidget(self.reloadBtn)

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
        images_layout.addWidget(self.images_view)
        self.tab_widget.addTab(images_tab, "Images")

        # Spectra tab
        spectra_tab = QtWidgets.QWidget()
        spectra_layout = QtWidgets.QVBoxLayout(spectra_tab)
        self.spectra_view = QtWidgets.QGraphicsView()
        spectra_layout.addWidget(self.spectra_view)
        self.tab_widget.addTab(spectra_tab, "Spectra")

        self._scene_mgr = ThumbnailSceneManager(self.images_view, self.spectra_view)
        self.images_scene, self.spectra_scene = self._scene_mgr.create_scenes(self.data_dir)

        nav_layout = QtWidgets.QHBoxLayout()

        self.backBtn = QtWidgets.QToolButton()
        self.backBtn.direction = -1
        self.backBtn.setToolTip("Previous loaded scene")
        self.backBtn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowBack))
        self.backBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.backBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        nav_layout.addWidget(self.backBtn)

        nav_layout.addWidget(self.tab_widget)

        self.forwardBtn = QtWidgets.QToolButton()
        self.forwardBtn.direction = 1
        self.forwardBtn.setToolTip("Next loaded scene")
        self.forwardBtn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowForward))
        self.forwardBtn.setIconSize(QtCore.QSize(ICONSIZE, ICONSIZE))
        self.forwardBtn.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        nav_layout.addWidget(self.forwardBtn)

        main_layout.addLayout(nav_layout)

        # Connect signals
        # self.backBtn.clicked.connect(lambda: self.navigate_scene(-1))
        # self.forwardBtn.clicked.connect(lambda: self.navigate_scene(1))
        self.backBtn.clicked.connect(self.navigate_scene)
        self.forwardBtn.clicked.connect(self.navigate_scene)

        # Connect signals
        self.reloadBtn.clicked.connect(self.on_reload_clicked)
        self.changeDirBtn.clicked.connect(self.on_change_dir_clicked)

        # Set window properties
        self.setWindowTitle("Contact Sheet Viewer")
        self.resize(800, 600)

    def navigate_scene(self):
        """
        a slot to navigate between scenes
        """
        btn = self.sender()
        direction = btn.direction
        if direction == -1:
            image_scene, spec_scene = self._scene_mgr.show_previous_scene()
        else:
            image_scene, spec_scene = self._scene_mgr.show_next_scene()

        if image_scene is None or spec_scene is None:
            return
        # Get the current directory name
        current_dir = self._scene_mgr.get_current_scene_directory()
        last_dir = self._scene_mgr.get_last_scene_directory()

        # Disable backBtn if at the first directory
        self.backBtn.setEnabled(self._scene_mgr.current_index > 0)

        # Disable forwardBtn if at the last directory
        self.forwardBtn.setEnabled(current_dir != self._scene_mgr.scenes[last_dir])

        # Optionally, update the directory label
        if image_scene and hasattr(image_scene, 'directory') and image_scene.directory:
            self.set_directory_label(image_scene.directory)

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
        if folder_thumbnail:
            # folder_thumbnail.setPos(0, 0)
            # Tag it so we can identify it later
            folder_thumbnail.setData(0, "folder_thumbnail")

        return folder_thumbnail

    def create_new_scenes(self, directory, force_new=False):
        """
        signal handler for when a new directory is selected in the directory selector widget.
        """
        if directory is None or directory == "":
            _logger.warning("on_create_new_scenes: directory cannot be None or empty")
            return

        self.images_scene, self.spectra_scene = self._scene_mgr.create_scenes(directory, force_new=force_new)
        self.set_directory_label(directory)

    def on_reload_clicked(self):
        """
        signal handler for when the refresh button is clicked.
        """
        self.dir_sel_wdg.data_dir = self._scene_mgr.get_current_scene_directory()
        self.create_new_scenes(self.dir_sel_wdg.data_dir, force_new=True)

        # Reload the directory and change the mouse cursor while reloading
        self.dir_sel_wdg.reload_directory()

    def create_thumbnail_from_h5_file_dct(self, h5_file_dct: dict) -> None:
        """
        Take a data_dct and create a thumbnail widget from it, adding it to the bottom of the scene.
        """
        if h5_file_dct is None:
            _logger.warning("create_thumbnail_from_h5_file_dct: h5_file_dct cannot be None")
            return

        _scan_type = h5_file_dct[h5_file_dct['default']]['sp_db_dct']['pystxm_enum_scan_type']
        is_folder = False
        if _scan_type == scan_types.SAMPLE_IMAGE_STACK:
            # so that it can be identified as a stack
            is_folder = True
        # h5_file_dct['entry1']['sp_db_dct']['file_path']
        thumbnail = create_thumbnail(h5_file_dct, is_folder=is_folder)
        if thumbnail is None:
            _logger.warning("create_thumbnail_from_h5_file_dct: thumbnail creation failed")
            return

        if thumbnail.is_valid():
            thumbnail.select.connect(self.do_select)
            thumbnail.launch_viewer.connect(self.launch_viewer)
            thumbnail.print_thumb.connect(self.print_thumbnail)
            thumbnail.preview_thumb.connect(self.preview_thumbnail)
            thumbnail.dbl_clicked.connect(self.on_thumbnail_dblclicked)
            if thumbnail.draggable:
                thumbnail.drag.connect(self.on_drag)


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

    def create_stack_thumbnails_from_thumbwidget(self,  thumb: ThumbnailWidget) -> None:
        """
        Take a data_dct and create a thumbnail widget from it, adding it to the bottom of the scene.
        """
        if thumb is None:
            _logger.warning("create_stack_thumbnails_from_thumbwidget: thumb cannot be None")
            return

        self.image_thumbs = []
        energies = thumb.h5_file_dct[thumb.h5_file_dct['default']]['sp_db_dct']['energy']
        entry_key = thumb.h5_file_dct['default']
        entry_dct = thumb.h5_file_dct[entry_key]
        sp_db_dct = entry_dct['sp_db_dct']
        sp_key = list(entry_dct['WDG_COM']['SPATIAL_ROIS'].keys())[0]
        sp_db = entry_dct['WDG_COM']['SPATIAL_ROIS'][sp_key]

        num_ev_rois = len(sp_db[EV_ROIS])
        data_idx = 0
        for ev_idx in range(num_ev_rois):
            for ev_pnt in range(len(sp_db[EV_ROIS][ev_idx][SETPOINTS])):
                e_pnt = sp_db[EV_ROIS][ev_idx][SETPOINTS][ev_pnt]
                data = thumb.data[data_idx]
                thumbnail = create_thumbnail(thumb.h5_file_dct, data=data, energy=e_pnt, ev_idx=ev_idx, ev_pnt=ev_pnt,
                                             pol_idx=0, stack_idx=0)
                if thumbnail is None:
                    _logger.warning("create_stack_thumbnails_from_thumbwidget: thumbnail creation failed")
                    continue
                if thumbnail.is_valid():
                    thumbnail.select.connect(self.do_select)
                    thumbnail.launch_viewer.connect(self.launch_viewer)
                    #thumbnail.print_thumb.connect(self.print_thumbnail)
                    #thumbnail.preview_thumb.connect(self.preview_thumbnail)
                    #thumbnail.dbl_clicked.connect(self.on_thumbnail_dblclicked)
                    #if thumbnail.draggable:
                    #    thumbnail.drag.connect(self.on_drag)

                self.image_thumbs.insert(0, thumbnail)
                data_idx += 1

        for item in self.image_thumbs:
            # Find the bottom-most y position
            items = [item for item in self.images_scene.items() if isinstance(item, QtWidgets.QGraphicsWidget)]
            items = sorted(items, key=lambda item: item.pos().y())
            if items:
                max_y = max(item.pos().y() + item.boundingRect().height() for item in items)
            else:
                max_y = 0
            item.setPos(0, max_y + 10)  # 10 px margin
            self.images_scene.addItem(item)

        self.update_scene_layout()
        self.on_loading_data(True)

    def on_thumbnail_dblclicked(self, thumb: ThumbnailWidget) -> None:
        """
        Handle double-click on a thumbnail, if a folder then go up a directory if a stack then load the stack file,
        """
        if thumb.scan_type == scan_types.SAMPLE_IMAGE_STACK:
            # grab current scene
            filename = os.path.join(thumb.directory, thumb.filename)
            result = self._scene_mgr.switch_to_scene(filename)
            if not result:
                self.images_scene, self.spectra_scene = self._scene_mgr.create_scenes(filename)
                self.set_directory_label(filename)
                self.on_loading_data(False)
                self.create_stack_thumbnails_from_thumbwidget(thumb)

    def update_scene_layout(self):
        """
        update_scene_layout(): description
        """
        # Arrange thumbnails based on current view size
        self.rearrange_scene_thumbnails(self.images_scene, self.images_view)
        self.rearrange_scene_thumbnails(self.spectra_scene, self.spectra_view)

    def do_select(self, thumb):
        """
        do_select(): description

        :param thumb: thumb description
        :type thumb: thumb type

        :returns: None
        """
        thumb_items = [item for item in self.images_scene.items() if isinstance(item, ThumbnailWidget)]
        for t in thumb_items:
            t.is_selected = (id(thumb) == id(t))
            t.update()
        self.update_view()

    def update_view(self):
        """
        update_view(): description

        :returns: None
        """
        self.images_view.update()
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

            jstr = json.dumps(convert_numpy_to_python(dct), cls=NumpyAwareJSONEncoder)

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

        #grab both scenes
        # self.spectra_scene_mgr.add_scene(self.spectra_scene)
        # self.image_scene_mgr.add_scene(self.images_scene)
        self.dir_sel_wdg.show()

    def set_directory_label(self, directory):
        self.dir_label.setText(directory)

    def on_loading_data(self, is_done: bool):
        """
        Update the cursor based on loading state.
        """
        if is_done:
            QtWidgets.QApplication.restoreOverrideCursor()
        else:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        QtWidgets.QApplication.processEvents()

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
                    addimages=True,
                    flipud=False,
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
