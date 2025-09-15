import pprint
import os
import sys
import zmq
import simplejson as json

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import QTimer, pyqtSignal, QThread

from cls.applications.pyStxm.widgets.dict_based_contact_sheet.contact_sheet import ContactSheet
from bcm.devices.zmq.pixelator.loadfile_reponse import LoadFileResponseClass

# from cls.applications.pyStxm.widgets.dict_based_contact_sheet.contact_sheet import ContactSheet
from cls.data_io.stxm_data_io import STXMDataIo
from cls.utils.fileUtils import get_file_path_as_parts


host = os.getenv('DCS_HOST', 'localhost')
sub_port = os.getenv('DCS_SUB_PORT', 56561)
req_port = os.getenv('DCS_REQ_PORT', 56562)
data_sub_port = os.getenv('DATA_SUB_PORT', 56563)

if sub_port == '56561':
    # vopi1610-005
    commands = {
        'initialize': None,
        'recordedChannels': None,
        'detectorSettings': None,
        'updateDetectorSettings': None,
        'estimatedTime': None,
        'scanRequest': None,
        'abortScan': None,
        'pauseScan': None,
        'resumeScan': None,
        'scanStatus': None,
        'moveRequest': None,
        'moveStatus': None,
        'homeRequest': None,
        'positionerStatus': None,
        'modified positioner definition': None,
        'modified zonePlate definition': None,
        'zonePlateFocus': None,
        'oscilloscopeDefinition': None,
        'focusType': None,
        'scanTypeArchive': None,
        'localFileScanTypeArchive': None,
        'allMotorsOff': None,
        'resetInterferometer': None,
        'OSA_IN': None,
        'OSA_OUT': None,
        'ZonePlate IN': None,
        'ZonePlate OUT': None,
        'Sample OUT': None,
        'topupMode': None,
        'beamShutterMode': None,
        'loadFile directory': '{"directory":"/home/bergr/srv-unix-home/Data/2025-08-08","showHidden":1, "fileExtension":".hdf5"}',
        'listDirectory': '{"directory":"/home/bergr/srv-unix-home/Data"}',
        'loadFile file': '{ "directory": "/home/bergr/srv-unix-home/Data/0502", "file": "/home/bergr/srv-unix-home/Data/0502/A240502001.hdf5", "showHidden": 0, "fileExtension": ".hdf5", "directories": ["..", "discard"], "files": ["A240502001.hdf5"], "pluginNumber": 0 }',
        'loadFile files': '{"cmd_args":{"files":[]}}',
        'loadDefinition': None,
        'change user': None,
        'script info': None,
        'getSettings': None,
    }
    filenames =  ["Detector_2025-08-08_001.hdf5",
              "Detector_2025-08-08_002.hdf5",
              "Focus_2025-08-08_003.hdf5",
              "Focus_2025-08-08_004.hdf5",
              "Motor_2025-08-08_005.hdf5",
              "Sample_Image_2025-08-08_006.hdf5",
              "Detector_2025-08-08_007.hdf5",
              "Motor_2025-08-08_008.hdf5"]

else:
    # SLS
    commands = {
        'initialize': None,
        'recordedChannels': None,
        'detectorSettings': None,
        'updateDetectorSettings': None,
        'estimatedTime': None,
        'scanRequest': None,
        'abortScan': None,
        'pauseScan': None,
        'resumeScan': None,
        'scanStatus': None,
        'moveRequest': None,
        'moveStatus': None,
        'homeRequest': None,
        'positionerStatus': None,
        'modified positioner definition': None,
        'modified zonePlate definition': None,
        'zonePlateFocus': None,
        'oscilloscopeDefinition': None,
        'focusType': None,
        'scanTypeArchive': None,
        'localFileScanTypeArchive': None,
        'allMotorsOff': None,
        'resetInterferometer': None,
        'OSA_IN': None,
        'OSA_OUT': None,
        'ZonePlate IN': None,
        'ZonePlate OUT': None,
        'Sample OUT': None,
        'topupMode': None,
        'beamShutterMode': None,
        'loadFile directory': '{"directory":"/home/control/LocalData/Data1/Data/2025-08-19","showHidden":1, "fileExtension":".hdf5"}',
        'listDirectory': '{"directory":"/home/control/LocalData/Data1"}',
        'loadFile file': '{ "directory": "/home/control/LocalData/Data1/2025-05-21", "file": "/home/control/LocalData/Data1/2025-05-21/OSA_2025-08-19_010.hdf5", "showHidden": 0, "fileExtension": ".hdf5", "directories": ["..", "discard"], "files": ["OSA_2025-08-19_010.hdf5"], "pluginNumber": 0 }',
        'loadFile files': '{ "directory": "/home/control/LocalData/Data1/2025-05-21", "file": "/home/control/LocalData/Data1/2025-05-21/Sample_Image_2025-05-21_002.hdf5", "showHidden": 0, "fileExtension": ".hdf5", "directories": ["..", "discard"], "files": [], "pluginNumber": 0 }',
        #'loadFile files': '{"directory": "/home/control/LocalData/Data1/2025-05-21", "cmd_args":{"files":[]}}',
        'loadDefinition': None,
        'change user': None,
        'script info': None,
    }
    filenames = ["Sample_Image_2025-05-21_002.hdf5", "Sample_Image_2025-05-21_004.hdf5",
                     "Sample_Image_2025-05-21_006.hdf5",
                     "Sample_Image_2025-05-21_001.hdf5", "Sample_Image_2025-05-21_003.hdf5",
                     "Sample_Image_2025-05-21_005.hdf5", "Sample_Image_2025-05-21_007.hdf5"]


def get_filenames(data_dir="/mnt/srv-unix-home/bergr/Data/2025-08-13"):
    return [os.path.join(data_dir, f) for f in filenames]

def gen_loadfile_directory_msg(directory: str, extension: str='.hdf5') -> dict:
    dct = {"directory":f"{directory}",
           "showHidden":1,
           "fileExtension":"{extension}"
,   }
    return dct


def gen_loadfile_msg(directory: str, filename: str) -> dict:
    dct = {
        "directory": f"{directory}"
        , "file": os.path.join(directory, filename)
        , "showHidden": 0
        , "fileExtension": ".hdf5"
        , "directories": [
            ".."
            , "discard"
        ]
        , "files": [
            filename
        ]
        , "pluginNumber": 0
    }
    return dct

class SubListenerThread(QThread):
    message_received = pyqtSignal(list)

    def __init__(self, sub_socket):
        super().__init__()
        self.sub_socket = sub_socket
        self._running = True

    def run(self):
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        while self._running:
            msg_parts = self.sub_socket.recv_multipart()
            # Convert bytes to strings
            str_parts = [part.decode('utf-8') if isinstance(part, bytes) else str(part) for part in msg_parts]
            self.message_received.emit(str_parts)

    def stop(self):
        self._running = False
        self.quit()
        self.wait()

class ZMQApp(QMainWindow):
    loadfile_changed = pyqtSignal(object)
    load_directory = pyqtSignal(object)
    scan_finished = pyqtSignal(object)
    sub_message_received = pyqtSignal(str)

    def __init__(self, host, sub_port, req_port, scan_content_sub_port=56566):
        super().__init__()

        self.HOST = host  # Set the HOST dynamically
        self.setWindowTitle("ZMQ Qt Application")
        self.setGeometry(100, 100, 400, 250)

        # Main widget and layout
        self.main_widget = QWidget(self)
        self.layout = QVBoxLayout(self.main_widget)

        self.contact_sheet = ContactSheet()
        self.contact_sheet.setMinimumSize(600, 400)

        # Label for command part
        self.cmd_label = QLabel("Select command (First Part of Multipart):", self)
        self.layout.addWidget(self.cmd_label)
        # Label for multipart message parts
        self.multipart_label = QLabel("Enter multipart data (comma-separated for part[1], part[2], etc.):", self)
        self.layout.addWidget(self.multipart_label)
        # Text field to type multipart message parts (part[1], part[2], etc.)
        self.multipart_input_field = QLineEdit(self)
        self.multipart_input_field.setPlaceholderText("Enter multipart data (e.g., Part1,Part2,Part3)")


        # ComboBox to select the command (part 0 of the multipart message)
        self.cmd_input_field = QComboBox(self)
        for k,v in commands.items():
            self.cmd_input_field.addItem(k)

        self.cmd_input_field.currentTextChanged.connect(self.on_cmd_changed)
        self.layout.addWidget(self.cmd_input_field)
        self.layout.addWidget(self.multipart_input_field)
        # Button to send the multipart message
        self.send_multipart_button = QPushButton("Send Multipart Request", self)
        self.layout.addWidget(self.send_multipart_button)
        self.send_multipart_button.clicked.connect(self.send_multipart_request)
        # self.send_multipart_button.clicked.connect(self.send_request)

        # Label to display the received message
        self.received_message_txtedit = QtWidgets.QTextEdit()
        self.layout.addWidget(self.received_message_txtedit)

        self.layout.addWidget(self.contact_sheet)

        self.setCentralWidget(self.main_widget)

        # Set up ZMQ context and sockets
        self.zmq_context = zmq.Context()

        print(f"Connecting to ZMQ on {self.HOST} with SUB port {sub_port} and REQ port {req_port}, "
              f"scan data SUB port {scan_content_sub_port}")

        # SUB socket (connects to PUB on port 56561)
        self.sub_socket = self.zmq_context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{self.HOST}:{sub_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')  # Subscribe to all topics

        self.scan_content_sub_sock = self.zmq_context.socket(zmq.SUB)
        self.scan_content_sub_sock.connect(f"tcp://{self.HOST}:{scan_content_sub_port}")
        self.scan_content_sub_sock.setsockopt_string(zmq.SUBSCRIBE, '')  # Subscribe to all topics
        self.sub_message_received.connect(self.on_sub_message_received)
        self.start_scan_content_sub_listener_thread()

        # REQ socket (connects to REP on port 56562)
        self.req_socket = self.zmq_context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{self.HOST}:{req_port}")

        self.load_directory.connect(self.on_loadfile_directory_msg)
        self.loadfile_changed.connect(self.on_loadfile_changed)
        self.scan_finished.connect(self.on_scan_finished)


        # Set up a timer to poll for messages from the SUB socket
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.receive_sub_message)
        self.timer.start(100)  # Poll every 100 milliseconds


    def start_scan_content_sub_listener_thread(self):
        self.sub_listener_thread = SubListenerThread(self.scan_content_sub_sock)
        self.sub_listener_thread.message_received.connect(self.on_sub_message_received)
        self.sub_listener_thread.start()

    def on_sub_message_received(self, msg_lst):
        if msg_lst[0] == 'scanFileContent':
            # print(f"on_sub_message_received: {msg_lst}")  # Print only the first 100 characters for brevity
            msg_dct = json.loads(msg_lst[1])
            h5_file_dct = json.loads(msg_dct['pystxm_load'])
            self.contact_sheet.create_thumbnail_from_h5_file_dct(h5_file_dct)


    def on_loadfile_directory_msg(self, msg_dct: dict) -> None:
        """Handle the loadFile directory message received from pixelator.
              Part 0: {"status":"ok"}
              Part 1: {"directories":["..",
            "discard"],
            "directory":"/mnt/srv-unix-home/bergr/Data/2025-07-14",
            "fileExtension":".hdf5",
            "files":["OSA_Focus_2025-07-14_013.hdf5",
            "Motor2D_2025-07-14_017.hdf5",
            "Sample_Line_2025-07-14_015.hdf5",
            "OSA_2025-07-14_006.hdf5",
            "Sample_Point_2025-07-14_014.hdf5"],
            "showHidden":1}

        """
        print(f"on_loadfile_directory_msg: {msg_dct}")
        # files = msg_dct.get('files', [])
        # directory = msg_dct.get('directory', '/')
        # extension = msg_dct.get('fileExtension', '.hdf5')
        # self.cmd_input_field.setCurrentText("loadFile file")
        # data_dct_lst = []
        # for fname in files:
        #     cmd_arg_str = json.dumps(gen_loadfile_msg(directory, fname))
        #     self.multipart_input_field.setText(cmd_arg_str)
        #     resp = self.send_multipart_request()
        #     data_dct_lst.append(resp)
        #
        # print(f"Received {len(data_dct_lst)} files from directory {directory} with extension {extension}")

    def on_loadfile_changed(self, response_text: str) -> dict:
        """
        Handle the loadFile file response.
        """
        data_dct = self.process_loadfile_changed(response_text)
        #self.contact_sheet.create_thumbnail_from_h5_file_dct(data_dct)


    def on_scan_finished(self, response_text: str) -> dict:
        """
        # '{"filename":"/mnt/srv-unix-home/bergr/Data/2025-07-17/discard/OSA_2025-07-17_005.hdf5","flag":0,"neXusBaseDirectory":"/mnt/srv-unix-home/bergr/Data","neXusDiscardSubDirectory":"discard","neXusLocalBaseDirectory":"/mnt/srv-unix-home/bergr/Data"}']
        """
        print(f"on_scan_finished")
        msg_dct = json.loads(response_text)
        filename = msg_dct.get('filename', '')
        directory, fprefix, fsuffix = get_file_path_as_parts(filename)
        extension = msg_dct.get('fileExtension', '.hdf5')
        self.cmd_input_field.setCurrentText("loadFile file")
        cmd_arg_str = json.dumps(gen_loadfile_msg(directory, f"{fprefix}{fsuffix}"))
        self.multipart_input_field.setText(cmd_arg_str)
        resp = self.send_multipart_request()


    def process_loadfile_changed(self, response_text: str) -> dict:
        """Handle the loadFile file response."""
        #print(f"Load file response received: {response_text}")
        try:
            lfr = LoadFileResponseClass(response_text)
            # First check the raw string
            # print(f"Raw pystxm_load string: [{lfr.pystxm_load}]")

            # Try to clean the string before parsing
            cleaned_json = lfr.pystxm_load.strip()
            if not cleaned_json:
                print("Error: pystxm_load string is empty")
                return

            # Try parsing with error details
            try:
                parsed_data_dct = json.loads(cleaned_json)
                # print(f"Successfully parsed JSON data:")
                # pprint.pprint(parsed_data)
                return parsed_data_dct

            except json.JSONDecodeError as e:
                print(f"JSON parsing failed at position {e.pos}: {e.msg}")
                print(f"Problem character: {cleaned_json[e.pos:e.pos + 10]}...")

        except Exception as e:
            print(f"General error: {str(e)}")

    def on_cmd_changed(self, cmd):
        if cmd in commands.keys():
            if commands[cmd] is not None:
                self.multipart_input_field.setText(commands[cmd])

    def send_request(self):
        command = self.cmd_input_field.currentText()
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
                    if command == "loadFile files":
                        #self.contact_sheet.on_clear_scenes()
                        fpaths = json.dumps(get_filenames(msg_dct["directory"]))
                        dct = {"cmd_args": {"files": fpaths}}
                        msg_dct.update(dct)

                except Exception as e:
                    self.received_message_txtedit.append(f"Error parsing JSON: {e}")
                    return
            self.req_socket.send_string(json.dumps(msg_dct))
            reply = self.req_socket.recv_string()
            self.received_message_txtedit.append(f"Reply:\n{reply}")

    def send_multipart_request(self):
        """Send a multipart message via the REQ socket with a command as the first part."""
        command = self.cmd_input_field.currentText()  # Part 0 (command)
        multipart_message = self.multipart_input_field.text()  # Parts 1, 2, ...
        if len(multipart_message) == 0:
            multipart_message = '{}'
        command_dct = json.loads(multipart_message)
        response = None
        if command and multipart_message:
            print(f"Sending multipart request with command: {command}")
            print(f"Sending multipart message: {multipart_message}")
            if command == "loadFile files":
                #self.contact_sheet.on_clear_scenes()
                fpaths = get_filenames(command_dct["directory"])
                msg_dct = json.loads(multipart_message)
                msg_dct.update({"files": fpaths})
                multipart_message = json.dumps(msg_dct)

            # First send the command as part 0
            self.req_socket.send_string(command, zmq.SNDMORE)

            # Send the multipart message as a single part
            self.req_socket.send_string(multipart_message)

            # Wait for the multipart reply from the REP socket
            reply_parts = self.req_socket.recv_multipart()

            # Convert bytes to strings
            str_parts = []
            for part in reply_parts:
                if isinstance(part, bytes):
                    str_parts.append(part.decode('utf-8'))
                else:
                    str_parts.append(str(part))

            print(f"Received multipart reply with {len(str_parts)} parts:")
            s = None
            for i, part in enumerate(str_parts):
                print(f"  Part {i}: {part}")
                s = part.replace(',', ',\n')
                self.received_message_txtedit.append(f'  Part {i}: {s}')

            # # Display all parts in the label
            # reply_text = "\n".join(str_parts)
            # e_txtedit.append(f"Received reply:\n{reply_text}")

            if command.find('loadFile directory') > -1:
                msg_dct = json.loads(part)
                self.load_directory.emit(msg_dct)

            elif command.find('loadFile file') > -1:
                response = json.loads(part)
                return response


        elif command and not multipart_message:
            print(f"Sending request with command: {command}")

            # First send the command as part 0
            self.req_socket.send_string(command)

            # Wait for the multipart reply from the REP socket
            reply_parts = self.req_socket.recv_multipart()

            # Convert bytes to strings
            str_parts = []
            for part in reply_parts:
                if isinstance(part, bytes):
                    str_parts.append(part.decode('utf-8'))
                else:
                    str_parts.append(str(part))

            print(f"Received multipart reply with {len(str_parts)} parts:")
            for i, part in enumerate(str_parts):
                print(f"  Part {i}: {part}")

            # Display all parts in the label
            reply_text = "\n".join(str_parts)
            self.received_message_txtedit.setText(f"Received reply:\n{reply_text}")

    def receive_sub_message(self):
        """Poll and receive multipart messages from the SUB socket."""
        skip_lst = ['scanLineData', 'detectorValues', 'chartmode_detector_update']
        try:
            # Check if there are any messages in the SUB socket
            if self.sub_socket.poll(100):  # Timeout of 100 milliseconds
                parts = []
                while True:
                    message_part = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                    parts.append(message_part)
                    # Check if this is the last part of the multipart message
                    if not self.sub_socket.getsockopt(zmq.RCVMORE):
                        break
                if parts[0] in skip_lst:
                    pass
                else:
                    s = None
                    received_message = "\n".join(parts)
                    if parts[0].find("scanFileContent") != 0 or parts[0].find("scanLineData") != 0:
                        print("\nSUB: Received multipart message:")
                        # for i, part in enumerate(parts):
                        #     print(f"Part {i + 1}: {part}")
                        # self.received_message_txtedit.append(received_message)
                    else:
                        # skip long output messages
                        print("\nSUB: Received multipart message: for scanFileContent (too long)")
                        self.received_message_txtedit.append(f"SUB: Received multipart message: for scanFileContent (too long)")

                if parts[0].find('scanFileContent') > -1:
                    self.loadfile_changed.emit(parts[1])
                elif parts[0].find("scanFinished") > -1:
                    self.scan_finished.emit(parts[1])
                    #'{"filename":"/mnt/srv-unix-home/bergr/Data/2025-07-17/discard/OSA_2025-07-17_005.hdf5","flag":0,"neXusBaseDirectory":"/mnt/srv-unix-home/bergr/Data","neXusDiscardSubDirectory":"discard","neXusLocalBaseDirectory":"/mnt/srv-unix-home/bergr/Data"}']
                elif parts[0].find('listDirectory') > -1:
                    # Handle loadDirectory message
                    msg_dct = json.loads(parts[1])
                    pprint.pprint(msg_dct)


        except zmq.Again:
            # No message received
            pass

if __name__ == "__main__":
    import pprint

    app = QApplication(sys.argv)
    def on_loadfile_changed(response_text):
        """Handle the loadFile file response."""
        #print(f"Load file response received: {response_text}")
        try:
            lfr = LoadFileResponseClass(response_text)
            # First check the raw string
            # print(f"Raw pystxm_load string: [{lfr.pystxm_load}]")

            # Try to clean the string before parsing
            cleaned_json = lfr.pystxm_load.strip()
            if not cleaned_json:
                print("Error: pystxm_load string is empty")
                return

            # Try parsing with error details
            try:
                parsed_data_dct = json.loads(cleaned_json)
                # print(f"Successfully parsed JSON data:")
                # pprint.pprint(parsed_data)
                return parsed_data_dct

            except json.JSONDecodeError as e:
                print(f"JSON parsing failed at position {e.pos}: {e.msg}")
                print(f"Problem character: {cleaned_json[e.pos:e.pos + 10]}...")

        except Exception as e:
            print(f"General error: {str(e)}")

    # Create the main application window
    window = ZMQApp(host, sub_port, req_port, data_sub_port)
    window.loadfile_changed.connect(on_loadfile_changed)
    window.show()

    # Start the Qt event loop
    sys.exit(app.exec_())