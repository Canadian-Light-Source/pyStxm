import sys
import threading
import os
import zmq
import simplejson as json
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal, QThread


from cls.applications.pyStxm.widgets.dict_based_contact_sheet.contact_sheet import ContactSheet
from nx_server import NX_SERVER_CMNDS

# Define commands relevant to nx_server
commands = {
    'save_files': None,
    'remove_files': None,
    'test_connection': None,
    'is_windows': None,
    'get_file_sequence_names': None,
    'loadfile_directory': '{"cmd_args":{"directory":"/mnt/srv-unix-home/bergr/Data/2025-08-19","extension":".hdf5"}}',
    'loadfile_file': '{"cmd_args":{"file":"/mnt/srv-unix-home/bergr/Data/2025-08-20/A250820002/A250820002.hdf5"}}',
    #'loadfile_files': '{"cmd_args":{"files":["/mnt/srv-unix-home/bergr/Data/2025-08-19/OSA_2025-08-19_002.hdf5","/mnt/srv-unix-home/bergr/Data/2025-08-19/Detector_2025-08-19_001.hdf5"]}}',
    'loadfile_files': '{ "directory": "/mnt/srv-unix-home/bergr/Data/2025-08-13", "file": "/mnt/srv-unix-home/bergr/Data/2025-08-13/.hdf5", "showHidden": 0, "fileExtension": ".hdf5", "directories": ["..", "discard"], "files": [], "pluginNumber": 0 }',
    'list_directory': '{"cmd_args":{"directory":"/mnt/srv-unix-home/bergr/Data","fileExtension":".hdf5"}}',
}

# filenames = ["A240502001.hdf5", "A240502005.hdf5", "A240502026.hdf5", "A240502079.hdf5", "A240502062.hdf5", "A240502050.hdf5",
#  "A240502040.hdf5", "A240502021.hdf5", "A240502015.hdf5", "A240502035.hdf5", "A240502032.hdf5", "A240502072.hdf5",
#  "A240502044.hdf5", "A240502016.hdf5", "A240502056.hdf5", "A240502042.hdf5", "A240502043.hdf5", "A240502045.hdf5",
#  "A240502074.hdf5", "A240502039.hdf5", "A240502041.hdf5", "A240502017.hdf5", "A240502030.hdf5", "A240502049.hdf5",
#  "A240502038.hdf5", "A240502065.hdf5", "A240502037.hdf5", "A240502027.hdf5", "A240502068.hdf5", "A240502020.hdf5",
#  "A240502014.hdf5", "A240502023.hdf5", "A240502048.hdf5", "A240502052.hdf5", "A240502029.hdf5", "A240502060.hdf5",
#  "A240502031.hdf5", "A240502069.hdf5", "A240502081.hdf5", "A240502054.hdf5", "A240502071.hdf5", "A240502047.hdf5",
#  "A240502033.hdf5", "A240502055.hdf5", "A240502013.hdf5", "A240502070.hdf5", "A240502067.hdf5", "A240502064.hdf5",
#  "A240502051.hdf5", "A240502018.hdf5", "A240502024.hdf5", "A240502034.hdf5", "A240502078.hdf5", "A240502073.hdf5",
#  "A240502022.hdf5", "A240502061.hdf5", "A240502076.hdf5", "A240502075.hdf5", "A240502058.hdf5", "A240502059.hdf5",
#  "A240502053.hdf5", "A240502066.hdf5", "A240502046.hdf5", "A240502077.hdf5", "A240502080.hdf5", "A240502019.hdf5",
#  "A240502025.hdf5", "A240502057.hdf5", "A240502063.hdf5"]

filenames = [
"Detector_2025-08-12_001.hdf5", "Motor_2025-08-12_009.hdf5", "OSA_2025-08-12_013.hdf5", "Sample_Image_2025-08-12_015.hdf5",
"Detector_2025-08-12_002.hdf5",  "Focus_2025-08-12_007.hdf5", "Motor_2025-08-12_018.hdf5", "OSA_Focus_2025-08-12_005.hdf5", "Sample_Line_2025-08-12_008.hdf5",
"Detector_2025-08-12_003.hdf5",  "Focus_2025-08-12_011.hdf5", "Motor2D_2025-08-12_010.hdf5", "OSA_Focus_2025-08-12_014.hdf5", "Sample_Point_2025-08-12_017.hdf5",
"Detector_2025-08-12_012.hdf5",  "Focus_2025-08-12_016.hdf5", "OSA_2025-08-12_004.hdf5", "Sample_Image_2025-08-12_006.hdf5"
]


def get_filenames(data_dir):
    return [os.path.join(data_dir, f) for f in filenames]




class SubListenerThread(QThread):
    message_received = pyqtSignal(str)

    def __init__(self, sub_socket):
        super().__init__()
        self.sub_socket = sub_socket
        self._running = True

    def run(self):
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        while self._running:
            msg = self.sub_socket.recv_string()
            self.message_received.emit(msg)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()



class NXServerApp(QMainWindow):
    loadfile_changed = pyqtSignal(object)
    load_directory = pyqtSignal(object)
    scan_finished = pyqtSignal(object)
    sub_message_received = pyqtSignal(str)

    def __init__(self, host, req_port, sub_port):
        super().__init__()
        self.HOST = host
        self.REQ_PORT = req_port
        self.SUB_PORT = sub_port

        self.setWindowTitle("NX Server Qt Application")
        self.setGeometry(100, 100, 400, 250)
        self.contact_sheet = ContactSheet()

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
        self.layout.addWidget(self.contact_sheet)

        self.setCentralWidget(self.main_widget)

        self.zmq_context = zmq.Context()
        self.req_socket = self.zmq_context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{self.HOST}:{self.REQ_PORT}")

        self.sub_socket = self.zmq_context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{self.HOST}:{self.SUB_PORT}")

        self.sub_message_received.connect(self.on_sub_message_received)
        self.start_sub_listener_thread()

    def start_sub_listener_thread(self):
        self.sub_listener_thread = SubListenerThread(self.sub_socket)
        self.sub_listener_thread.message_received.connect(self.on_sub_message_received)
        self.sub_listener_thread.start()

    def on_sub_message_received(self, msg):
        msg_dct = json.loads(msg)
        if 'scanFileContent' in msg_dct.keys():
            h5_file_dct = json.loads(msg_dct['scanFileContent'])
            self.contact_sheet.create_thumbnail_from_h5_file_dct(h5_file_dct)
            #self.received_message_txtedit.append(f"SUB Message RCVD:\n{msg}\n\n")
        # self.contact_sheet.create_thumbnail_from_h5_file_dct(h5_file_dct)
        # #self.received_message_txtedit.append(f"SUB Message RCVD:\n{msg}\n\n")
        # #print(f"SUB Message RCVD:\n{msg}\n\n")

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
                    if command == NX_SERVER_CMNDS.get_value_by_name("loadfile_files"):
                        self.contact_sheet.on_clear_scenes()
                        fpaths = json.dumps(get_filenames("/mnt/srv-unix-home/bergr/Data/2025-08-13"))
                        dct = {"cmd_args": {"files": fpaths}}
                        msg_dct.update(dct)

                except Exception as e:
                    self.received_message_txtedit.append(f"Error parsing JSON: {e}")
                    return
            self.req_socket.send_string(json.dumps(msg_dct))
            reply = self.req_socket.recv_string()
            self.received_message_txtedit.append(f"Reply:\n{reply}")

if __name__ == "__main__":
    NX_SERVER_REP_PORT = 5555
    NX_SERVER_PUB_PORT = 5565

    app = QApplication(sys.argv)
    host = 'vopi1610-005.clsi.ca'
    # host = 'localhost'
    req_port = int(os.getenv('NX_SERVER_PORT', NX_SERVER_REP_PORT))
    window = NXServerApp(host, req_port=NX_SERVER_REP_PORT, sub_port=NX_SERVER_PUB_PORT)
    window.show()
    sys.exit(app.exec_())