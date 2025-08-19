import sys
import os
import zmq
import simplejson as json
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal

from nx_server import NX_SERVER_CMNDS

# Define commands relevant to nx_server
commands = {
    'save_files': None,
    'remove_files': None,
    'test_connection': None,
    'is_windows': None,
    'get_file_sequence_names': None,
    'loadfile_directory': '{"cmd_args":{"directory":"/mnt/srv-unix-home/bergr/Data/2025-08-19","extension":".hdf5"}}',
    'loadfile_file': '{"cmd_args":{"file":"/mnt/srv-unix-home/bergr/Data/2025-08-19/OSA_2025-08-19_010.hdf5"}}',
    'loadfile_files': '{"cmd_args":{"files":["/mnt/srv-unix-home/bergr/Data/2025-08-19/OSA_2025-08-19_002.hdf5","/mnt/srv-unix-home/bergr/Data/2025-08-19/Detector_2025-08-19_001.hdf5"]}}',
    'list_directory': '{"cmd_args":{"directory":"/mnt/srv-unix-home/bergr/Data","fileExtension":".hdf5"}}',
}

class NXServerApp(QMainWindow):
    loadfile_changed = pyqtSignal(object)
    load_directory = pyqtSignal(object)
    scan_finished = pyqtSignal(object)

    def __init__(self, host, port):
        super().__init__()
        self.HOST = host
        self.PORT = port
        self.setWindowTitle("NX Server Qt Application")
        self.setGeometry(100, 100, 400, 250)

        self.main_widget = QWidget(self)
        self.layout = QVBoxLayout(self.main_widget)

        self.cmd_label = QLabel("Select command:", self)
        self.layout.addWidget(self.cmd_label)
        self.multipart_label = QLabel("Enter command arguments (JSON):", self)
        self.layout.addWidget(self.multipart_label)
        self.multipart_input_field = QLineEdit(self)
        self.multipart_input_field.setPlaceholderText("Enter JSON arguments")
        self.layout.addWidget(self.multipart_input_field)

        self.cmd_input_field = QComboBox(self)
        for k in commands.keys():
            self.cmd_input_field.addItem(k)
        self.cmd_input_field.currentTextChanged.connect(self.on_cmd_changed)
        self.layout.addWidget(self.cmd_input_field)

        self.send_multipart_button = QPushButton("Send Request", self)
        self.layout.addWidget(self.send_multipart_button)
        self.send_multipart_button.clicked.connect(self.send_request)

        self.received_message_txtedit = QtWidgets.QTextEdit()
        self.layout.addWidget(self.received_message_txtedit)

        self.setCentralWidget(self.main_widget)

        self.zmq_context = zmq.Context()
        self.req_socket = self.zmq_context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{self.HOST}:{self.PORT}")

    def on_cmd_changed(self, cmd):
        if cmd in commands and commands[cmd] is not None:
            self.multipart_input_field.setText(commands[cmd])
        else:
            self.multipart_input_field.clear()

    def send_request(self):
        command = NX_SERVER_CMNDS.get_value_by_name(self.cmd_input_field.currentText())
        multipart_message = self.multipart_input_field.text()
        if command:
            msg_dct = {
                "cmnd": command,
                "run_uids": [],
                "fprefix": "",
                "data_dir": "",
                "nx_app_def": "nxstxm",
                "fpaths": [],
                "cmd_args": {}
            }
            if multipart_message:
                try:
                    msg_dct.update(json.loads(multipart_message))
                except Exception as e:
                    self.received_message_txtedit.append(f"Error parsing JSON: {e}")
                    return
            self.req_socket.send_string(json.dumps(msg_dct))
            reply = self.req_socket.recv_string()
            self.received_message_txtedit.append(f"Reply:\n{reply}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    host = 'localhost'
    port = int(os.getenv('NX_SERVER_PORT', 5555))
    window = NXServerApp(host, port)
    window.show()
    sys.exit(app.exec_())