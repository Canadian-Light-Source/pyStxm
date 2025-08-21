
from PyQt5 import QtWidgets, QtCore
import os

class DirectorySelectorWidget(QtWidgets.QWidget):
    """
    Widget to select a target directory and display its subdirectories.
    Allows the user to enter a directory path, requests subdirectory list from main_obj,
    and displays them in a QListWidget.
    """
    new_data_dir = QtCore.pyqtSignal(str)  # Signal to emit the new data directory path
    clear_scenes = QtCore.pyqtSignal()
    def __init__(self, main_obj, base_data_dir, data_dir):
        """
        Initialize the DirectorySelectorWidget.

        Args:
            main_obj: The main application object for data directory operations.
            data_dir: The initial data directory path.
            parent: Optional parent widget.
        """
        super().__init__(parent=None)  # No parent widget by default
        self.main_obj = main_obj
        self.data_dir = data_dir
        self.main_obj = main_obj
        self.base_data_dir = base_data_dir
        self.data_dir = data_dir
        self.setWindowTitle("Select data directory")

        self.layout = QtWidgets.QVBoxLayout(self)

        self.dir_label = QtWidgets.QLabel(data_dir)
        self.layout.addWidget(self.dir_label)

        # self.select_base_dir_btn = QtWidgets.QPushButton("Choose directory")
        # self.select_base_dir_btn.clicked.connect(self.req_dir_list)
        # self.layout.addWidget(self.select_base_dir_btn)

        self.subdir_list = QtWidgets.QListWidget()
        self.subdir_list.itemClicked.connect(self.on_subdir_selected)
        self.layout.addWidget(self.subdir_list)

        self.status_label = QtWidgets.QLabel("Click on a subdirectory to select it.\n'..' goes up one level.")
        self.layout.addWidget(self.status_label)

        sub_dirs = self.main_obj.request_data_dir_list(base_dir=self.data_dir)
        self.list_subdirectories(sub_dirs)

    def update_data_dir(self, data_dir):
        """
        Update the data directory and reload the subdirectories.

        Args:
            data_dir: The new data directory path.
        """
        self.data_dir = data_dir
        self.dir_label.setText(data_dir)
        self.new_data_dir.emit(data_dir)

    def reload_directory(self, data_dir=None):
        """
        Reload the data directory using the main_obj's zmq_reload_data_directory method.
        """
        if data_dir is None:
            data_dir = self.data_dir

        # update the directory
        self.update_data_dir(data_dir)
        self.main_obj.reload_data_directory(data_dir=data_dir)

    def req_dir_list(self):
        """
        Prompt the user to enter a data directory path, request its subdirectories,
        and display them in the list widget.
        """
        directory, ok = QtWidgets.QInputDialog.getText(
            self,
            "Enter Data Directory Path",
            "Data Directory path:"
        )
        if ok and directory:
            self.update_data_dir(directory)
            sub_dirs = self.main_obj.request_data_dir_list(base_dir=directory)
            self.list_subdirectories(sub_dirs)

    def list_subdirectories(self, sub_dirs=None):
        """
        Display the provided list of subdirectories in the QListWidget, including '..' to go up one level.

        Args:
            sub_dirs: List of subdirectory names to display.
        """
        self.subdir_list.clear()
        items = ['..']
        if sub_dirs:
            items += [f"{d['sub_dir']} \t({d['num_h5_files']} h5 files)" for d in sub_dirs]
        self.subdir_list.addItems(items)

    def on_subdir_selected(self, selected):
        """
        Slot called when a subdirectory item is clicked in the list.

        Args:
            selected: The clicked QListWidgetItem representing a subdirectory.
        """
        do_hide = True
        if selected:
            subdir_name = selected.text().split('\t')[0].strip()
            if subdir_name == '..':
                if self.data_dir == self.base_data_dir:
                    # if we are at the base directory, request the subdirs from the main_obj
                    # this is to avoid an infinite loop of going up to the base dir
                    return

                new_data_dir = os.path.dirname(self.data_dir)
                do_hide = False
                self.subdir_list.clear()
                sub_dirs = self.main_obj.request_data_dir_list(base_dir=new_data_dir)
                self.list_subdirectories(sub_dirs)
                self.update_data_dir(new_data_dir)

            else:
                new_data_dir = os.path.join(self.data_dir, subdir_name)

            if do_hide:
                # request that the image and spec graphic scenes be cleared
                self.clear_scenes.emit()

                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                self.status_label.setText("Loading selection, please wait...")
                QtWidgets.QApplication.processEvents()
                QtWidgets.QApplication.processEvents()
                self.reload_directory(new_data_dir)
                QtWidgets.QApplication.restoreOverrideCursor()
                self.status_label.setText("Loading selection completed")
                QtWidgets.QApplication.processEvents()
                self.update_data_dir(new_data_dir)

                # update the current list of sub dirs
                sub_dirs = self.main_obj.request_data_dir_list(base_dir=self.data_dir)
                self.list_subdirectories(sub_dirs)
                self.hide()