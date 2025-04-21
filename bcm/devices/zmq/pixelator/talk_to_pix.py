import sys
import zmq
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QLineEdit, QPushButton, QLabel
from PyQt5.QtCore import QTimer

commands = ['initialize',
    'recordedChannels',
    'detectorSettings',
    'updateDetectorSettings',
    'estimatedTime',
    'scanRequest',
    'abortScan',
    'pauseScan'
    'resumeScan',
    'scanStatus',
    'moveRequest',
    'moveStatus',
    'homeRequest',
    'positionerStatus',
    'modified positioner definition',
    'modified zonePlate definition',
    'zonePlateFocus',
    'oscilloscopeDefinition',
    'focusType',
    'scanTypeArchive',
    'localFileScanTypeArchive',
    'allMotorsOff',
    'resetInterferometer',
    'OSA_IN',
    'OSA_OUT',
    'ZonePlate IN',
    'ZonePlate OUT',
    'Sample OUT',
    'topupMode',
    'beamShutterMode',
    'loadFile directory',
    'loadFile file',
    'loadDefinition',
    'change user',
    'script info'
    ]

class ZMQApp(QMainWindow):
    def __init__(self, host):
        super().__init__()

        self.HOST = host  # Set the HOST dynamically
        self.setWindowTitle("ZMQ Qt Application")
        self.setGeometry(100, 100, 400, 250)

        # Main widget and layout
        self.main_widget = QWidget(self)
        self.layout = QVBoxLayout(self.main_widget)

        # Label for command part
        self.cmd_label = QLabel("Select command (First Part of Multipart):", self)
        self.layout.addWidget(self.cmd_label)

        # ComboBox to select the command (part 0 of the multipart message)
        self.cmd_input_field = QComboBox(self)
        self.cmd_input_field.addItems(commands)
        self.layout.addWidget(self.cmd_input_field)

        # Label for multipart message parts
        self.multipart_label = QLabel("Enter multipart data (comma-separated for part[1], part[2], etc.):", self)
        self.layout.addWidget(self.multipart_label)

        # Text field to type multipart message parts (part[1], part[2], etc.)
        self.multipart_input_field = QLineEdit(self)
        self.multipart_input_field.setPlaceholderText("Enter multipart data (e.g., Part1,Part2,Part3)")
        self.layout.addWidget(self.multipart_input_field)

        # Button to send the multipart message
        self.send_multipart_button = QPushButton("Send Multipart Request", self)
        self.layout.addWidget(self.send_multipart_button)
        self.send_multipart_button.clicked.connect(self.send_multipart_request)

        # Label to display the received message
        self.received_message_label = QLabel("Received message will be displayed here.", self)
        self.layout.addWidget(self.received_message_label)

        self.setCentralWidget(self.main_widget)

        # Set up ZMQ context and sockets
        self.zmq_context = zmq.Context()

        # SUB socket (connects to PUB on port 56561)
        self.sub_socket = self.zmq_context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{self.HOST}:56561")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, '')  # Subscribe to all topics

        # REQ socket (connects to REP on port 56562)
        self.req_socket = self.zmq_context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{self.HOST}:56562")

        # Set up a timer to poll for messages from the SUB socket
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.receive_sub_message)
        self.timer.start(100)  # Poll every 100 milliseconds

    def send_multipart_request(self):
        """Send a multipart message via the REQ socket with a command as the first part."""
        command = self.cmd_input_field.currentText()  # Part 0 (command)
        multipart_message = self.multipart_input_field.text()  # Parts 1, 2, ...

        if command and multipart_message:
            print(f"Sending multipart request with command: {command}")
            print(f"Sending multipart message: {multipart_message}")

            # First send the command as part 0
            self.req_socket.send_string(command, zmq.SNDMORE)

            # Send the multipart message as a single part
            self.req_socket.send_string(multipart_message)

            # Wait for the reply from the REP socket
            reply = self.req_socket.recv_string()
            print(f"Received reply: {reply}")
            self.received_message_label.setText(f"Received reply: {reply}")

    def receive_sub_message(self):
        """Poll and receive multipart messages from the SUB socket."""
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
                if parts[0].find('detectorValues') > -1:
                    pass
                else:
                    received_message = "\n".join(parts)
                    print("SUB: Received multipart message:")
                    for i, part in enumerate(parts):
                        print(f"Part {i + 1}: {part}")
                    self.received_message_label.setText(received_message)
        except zmq.Again:
            # No message received
            pass

if __name__ == "__main__":
    # Set the HOST variable dynamically
    HOST = "localhost"  # Change this value to the appropriate host as needed

    app = QApplication(sys.argv)

    # Create the main application window
    window = ZMQApp(HOST)
    window.show()

    # Start the Qt event loop
    sys.exit(app.exec_())