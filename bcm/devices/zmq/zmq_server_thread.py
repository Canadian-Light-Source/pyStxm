import os
import zmq.asyncio
import asyncio
import json
from PyQt5.QtCore import QThread, pyqtSignal

if os.name == 'nt':
    from asyncio import WindowsSelectorEventLoopPolicy

class ZMQServerThread(QThread):
    # Define the signal that will emit a dictionary when a message is received
    message_received = pyqtSignal(object)

    def __init__(self, name, sub_socket, req_socket, read_only=True, parent=None):
        super().__init__(parent)
        self.name = name
        self.loop = None
        self.sub_socket = sub_socket
        self.req_socket = req_socket
        #self.context = zmq.asyncio.Context()
        self.running = True

    async def send_receive_async(self, command, timeout=500):
        """
        Send a request (as a dictionary) and wait for the multipart reply asynchronously.
        """
        # socket = self.context.socket(zmq.REQ)
        # socket.connect("tcp://localhost:5557")  # Assuming the server is running on this address
        def isListOfStrings(data):
            if type(data) != list:
                return False

            for d in data:
                if type(d) != str:  ## Python 3 str = unicode
                    return False
            return True

        if not isListOfStrings(command):
            #raise Exception("ERROR >> send_receive_async needs a list of strings (use json.dumps if you have a dictionary)")
            print("send_receive_async: ERROR >> send_receive_async needs a list of strings (use json.dumps if you have a dictionary)")

        # Serialize the dictionary to a JSON string
        #message_json = json.dumps(message_dict)
        if len(command) == 0:  # nothing to send
            print("send_receive_async: WARNING >> send_receive_async called without data")
            return {}
        print(f"send_receive_async: Sending command [{command}]")

        # print(f"send_receive_async: command={command}")
        # send all but last part
        for i in range(len(command) - 1):
            await self.req_socket.send_string(command[i], flags=zmq.SNDMORE)
        # send last part
        await self.req_socket.send_string(command[-1])

        # Receive the multipart response
        reply_parts = await self.req_socket.recv_multipart()
        print(f"send_receive_async: Received multipart reply: {reply_parts}")

        # Assuming the server sends back a JSON-encoded response in one of the parts
        # We'll deserialize the first part into a Python dictionary
        if reply_parts:
            response = [json.loads(part.decode('utf-8')) for part in reply_parts]
        else:
            response = {}

        # Emit the signal with the received reply as a dictionary
        #self.message_received.emit(reply_dict)
        if not (type(response) is list and response[0] == {'status': 'ok'}):
            print(f"ZMQ ERROR >> {response[0]['message']}")
        #socket.close()
        return response

    def send_receive(self, message_dict):
        """
        Synchronously send a request (as a dictionary) and return the multipart reply.
        This function will block until the reply is received.
        """
        if os.name == 'nt':
            # Set the event loop policy to WindowsSelectorEventLoopPolicy on Windows
            asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()

        # Run the async send/receive function in the event loop and wait for it to finish
        print(f"zmq_server_thread: send_receive called with message_dict={message_dict}")
        return loop.run_until_complete(self.send_receive_async(message_dict))

    def run(self):

        #asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Schedule the receive function
        self.loop.create_task(self.receive_message())

        # Run the loop
        self.loop.run_forever()

    async def receive_message(self):
        while True:
            # message = await self.sub_socket.recv_string()
            message_parts = await self.sub_socket.recv_multipart()

            # Print each part of the multipart message
            #print("\n\nReceived multipart message:")
            #print(f"message_parts={message_parts}")
            msg_parts = []

            for idx, part in enumerate(message_parts):
                # dct = json.loads(part.decode('utf-8'))
                #print(f"message_parts={message_parts}")
                #print(f"Part {idx + 1}: {part.decode('utf-8')}")
                msg_parts.append(part.decode('utf-8'))

            header = msg_parts[0]
            if header.find('detectorValues') > -1:
                #print(f"ZMQServerThread: sub_socket.rcvd: detectorValues [{msg_parts}]")
                pass
            elif header.find('UPDATE_POSITION') == -1:
                # only print if not updating aposition, there are too many
                # print(f"ZMQServerThread: sub_socket.rcvd:[{msg_parts}]")
                pass

            if header:
                # message_dict = json.loads(message)  # Deserialize the JSON string to a dictionary
                # print(f"{self.name}: Received dictionary: {msg_parts}")
                self.message_received.emit(msg_parts)
    def stop(self):
        """
        Gracefully stop the server.
        """
        self.running = False
        self.quit()
        self.wait()


# Example usage with a PyQt or PySide app
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

    app = QApplication([])

    # Create the ZMQ server thread
    zmq_thread = ZMQServerThread()
    zmq_thread.start()

    # Example GUI
    class ExampleWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.init_ui()

        def init_ui(self):
            self.label = QLabel("ZMQ Client Example")
            self.button = QPushButton("Send Initialize Command")
            self.button.clicked.connect(self.send_request)

            layout = QVBoxLayout()
            layout.addWidget(self.label)
            layout.addWidget(self.button)

            self.setLayout(layout)

            # Connect the `message_received` signal from the thread to the `on_message_received` slot
            zmq_thread.message_received.connect(self.on_message_received)

        def send_request(self):
            # Send the dictionary {'command': 'initialize', 'value': 1} when the button is pressed
            request_dict = {
                'command': 'initialize',
                'value': 1
            }

            # Send request and get the multipart reply (blocking)
            print("Sending request...")
            zmq_thread.send_receive(request_dict)

        def on_message_received(self, reply):
            """
            Slot that is triggered when the `message_received` signal is emitted.
            """
            print(f"Reply received in main thread: {reply}")
            self.label.setText(f"Reply: {reply}")

    window = ExampleWindow()
    window.show()

    # Stop the thread when the app exits
    app.aboutToQuit.connect(zmq_thread.stop)

    sys.exit(app.exec_())
