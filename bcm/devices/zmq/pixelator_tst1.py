import time
import zmq.asyncio
import asyncio
import json
import ast
import numpy as np
from PyQt5.QtCore import QThread
from asyncio import WindowsSelectorEventLoopPolicy

class ControllerError(Exception):
    """
    Raised from the ZMQ monitor if there was a controller crash/computer dead
    """
    pass


class zmqError(Exception):
    """
    Raised from the ZMQ controller if there was an error in the ZMQ request
    """
    pass


class ScanError(Exception):
    """
    Raised from the ZMQ monitor if there was a scan error
    """
    pass


class ZMQServerThread(QThread):
    def __init__(self, parent=None, pub_host='<PUB host name here>', pub_port=56561):
        super().__init__(parent)
        self.context = zmq.asyncio.Context()
        self.running = True
        self.pub_host = pub_host
        self.pub_port = pub_port

    def zmqDetectorMonitor(self, timeout=30):
        """
        This method is used to listen to the zmq publisher port and record an average of
        the detector values
        """

        try:
            #context = zmq.Context()
            socket = self.context.socket(zmq.SUB)
            socket.connect(
                "tcp://" + self.pub_host + ":" + str(self.pub_port))  ## 55561 is usually the publisher port
            socket.setsockopt_string(zmq.SUBSCRIBE, "")

            ## Setting up a ZMQ poller to check if ZMQ publisher server still alive
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
        except:
            raise zmqError("ERROR >> Error when subscribing to ZMQ publisher port")

        try:
            beamIntensityValues = []
            t0 = time.time()
            while time.time() - t0 <= timeout:
                rcv = dict(poller.poll(timeout))
                if rcv:
                    if rcv.get(socket) == zmq.POLLIN:
                        rcv_mess = socket.recv_multipart(zmq.NOBLOCK)
                        rcv_mess = rcv_mess.result()
                        if rcv_mess[0].decode() in ["detectorValues"]:
                            value = rcv_mess[1].decode()

                            beamIntensityValues.append(float(ast.literal_eval(value)[0]))
                else:  ## Here, we assume that the controller died
                    pass  # raise ControllerError("ERROR >> Controller or computer is dead")
            return (np.mean(beamIntensityValues))
        except (ScanError, ControllerError) as e:
            socket.close()
            self.context.term()
            raise e

    async def send_receive_async(self, message_dict):
        """
        Send a request (as a dictionary) and wait for the multipart reply asynchronously.
        """
        socket = self.context.socket(zmq.REQ)
        socket.connect("tcp://<PUB host name here>:56561")  # Assuming the server is running on this address

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
    zmq_thread.zmqDetectorMonitor()
    window.show()

    # Stop the thread when the app exits
    app.aboutToQuit.connect(zmq_thread.stop)

    sys.exit(app.exec_())
