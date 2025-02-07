import zmq.asyncio
import asyncio
import json
from PyQt5.QtCore import QThread
from asyncio import WindowsSelectorEventLoopPolicy

class ZMQServerThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.context = zmq.asyncio.Context()
        self.running = True

    async def send_receive_async(self, message_dict):
        """
        Send a request (as a dictionary) and wait for the multipart reply asynchronously.
        """
        socket = self.context.socket(zmq.REQ)
        socket.connect("tcp://localhost:5557")  # Assuming the server is running on this address

        # Serialize the dictionary to a JSON string
        message_json = json.dumps(message_dict)

        # Send the JSON string
        await socket.send_string(message_json)
        print(f"Sent request: {message_json}")

        # Receive the multipart response
        reply_parts = await socket.recv_multipart()
        print(f"Received multipart reply: {reply_parts}")

        # Assuming the server sends back a JSON-encoded response in one of the parts
        # We'll deserialize the first part into a Python dictionary
        if reply_parts:
            reply_dict = json.loads(reply_parts[0].decode('utf-8'))
        else:
            reply_dict = {}

        socket.close()
        return reply_dict

    def send_receive(self, message_dict):
        """
        Synchronously send a request (as a dictionary) and return the multipart reply.
        This function will block until the reply is received.
        """
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()

        # Run the async send/receive function in the event loop and wait for it to finish
        return loop.run_until_complete(self.send_receive_async(message_dict))

    def run(self):
        """
        Run the ZMQ event loop (if necessary).
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        finally:
            loop.close()

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

        def send_request(self):
            # Send the dictionary {'command': 'initialize', 'value': 1} when the button is pressed
            request_dict = {
                'command': 'initialize',
                'value': 1
            }

            # Send request and get the multipart reply (blocking)
            print("Sending request...")
            reply = zmq_thread.send_receive(request_dict)
            print(f"Reply received in main thread: {reply}")
            self.label.setText(f"Reply: {reply}")

    window = ExampleWindow()
    window.show()

    # Stop the thread when the app exits
    app.aboutToQuit.connect(zmq_thread.stop)

    sys.exit(app.exec_())
