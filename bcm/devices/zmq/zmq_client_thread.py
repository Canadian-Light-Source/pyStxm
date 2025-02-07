import json
import zmq
import zmq.asyncio
import asyncio
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
import sys
from asyncio import WindowsSelectorEventLoopPolicy

from bcm.devices.zmq.pixelator.pixelator_commands import cmd_func_map_dct
class ZMQClientThread(QThread):
    message_received = pyqtSignal(dict)  # Signal to notify when a message is received

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.context = zmq.asyncio.Context()

        # PUB socket: Publishing messages to subscribers
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind("tcp://*:5556")  # Bind to an address for PUB

        # REP socket: Replying to incoming requests
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind("tcp://*:5557")  # Bind to an address for REP

        self.loop = None  # Event loop placeholder


    async def handle_rep_socket(self):
        """
        This coroutine handles incoming requests on the REP socket and sends replies.
        """
        while True:
            message = await self.rep_socket.recv_string()
            # if type(message) == str:
            #     message_dct = {'command': message}
            # else:
            #     message_dct = json.loads(message)
            message_dct = json.loads(message)
            # print(f"PIXELATOR: Received request on REP: <{message}>")
            # # Send the reply
            if 'command' in message_dct.keys():
                command = message_dct['command']
            else:
                command = ''

            # if it is a registered command then return its response
            if command in cmd_func_map_dct.keys():
                func = cmd_func_map_dct[command]
                response = func(self.parent, message_dct)
                print(f"zmq_client_thread: handle_rep_socket: called function[{command}] and got response={response}")
                #response = dcs_client_cmnds[command]
                # Encode each part as UTF-8 and send as multipart message
                # send the reply as a multipart
                await self.rep_socket.send_multipart([r.encode('utf-8') for r in response])
            else:
                #reply = f"<DCS: ROGER_THAT [{message}]>"
                reply = f"{message}"
                # # Send the reply
                await self.rep_socket.send_string(reply)

            # finally emit the message_received signal to process the command to the DCS
            self.message_received.emit(message_dct)  # Emit the signal with the reply

    async def send_reply(self, message_dict):
        """
        Sends a message via the PUB socket.
        """
        message_json = json.dumps(message_dict)  # Serialize the dictionary to a JSON string
        # print(f"PIXELATOR: Sending reply on REP: {message_json}")
        await self.rep_socket.send_string(message_json)


    async def send_message(self, message_dict):
        """
        Sends a message via the PUB socket.
        """
        message_json = json.dumps(message_dict)  # Serialize the dictionary to a JSON string
        # print(f"PIXELATOR: Sending command on PUB: {message_json}")
        await self.pub_socket.send_string(message_json)

    def run(self):
        """
        Starts the ZMQ event loop in a separate thread for handling both sockets.
        """
        # Set the event loop policy to WindowsSelectorEventLoopPolicy on Windows
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
        # Initialize the asyncio event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Create tasks for handling both sockets
        # self.loop.create_task(self.handle_pub_socket())
        self.loop.create_task(self.handle_rep_socket())

        # Start the asyncio event loop in this thread
        self.loop.run_forever()


    def stop(self):
        """
        Stops the event loop and quits the thread.
        """
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.quit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZMQ Pixelator SIM")

        # Central widget to hold the layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout for buttons
        self.layout = QVBoxLayout()

        # Create buttons for each command
        commands = ['scanStarted', 'scanLineData', 'scanFinished', 'scanFileContent', 'positionerDefinition']
        self.buttons = []
        for command in commands:
            button = QPushButton(command)
            button.clicked.connect(lambda checked, cmd=command: self.send_command(cmd))
            self.layout.addWidget(button)
            self.buttons.append(button)

        # Set the layout to the central widget
        self.central_widget.setLayout(self.layout)

        # Start the ZMQ client thread
        self.zmq_client_thread = ZMQClientThread()
        self.zmq_client_thread.message_received.connect(self.update_label)
        self.zmq_client_thread.start()

    def send_command(self, command):
        """
        Sends a command to the ZMQ client thread to be sent via the PUB socket.
        """
        asyncio.run_coroutine_threadsafe(self.zmq_client_thread.send_command(command), self.zmq_client_thread.loop)

    def update_label(self, message):
        print(f"Received: {message}")  # Update this to update any UI element if needed

    def closeEvent(self, event):
        # Stop the ZMQ thread when closing the window
        self.zmq_client_thread.stop()
        event.accept()



if __name__ == '__main__':
    # Main application
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(580, 150, 500, 200)
    window.show()
    sys.exit(app.exec_())
