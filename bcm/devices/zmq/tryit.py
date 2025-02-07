from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QMainWindow, QWidget
import sys

class MyEmitter(QObject):
    # Declare a signal that accepts a single object, which can be either a dict or kwargs
    signal = pyqtSignal(object)

    def emit_dict(self, data):
        # Emit the signal with a dictionary
        self.signal.emit(data)

    def emit_kwargs(self, **kwargs):
        # Emit the signal with **kwargs as a dictionary
        self.signal.emit(kwargs)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Signal with Dict or kwargs Example")

        # Create an instance of MyEmitter
        self.emitter = MyEmitter()

        # Connect the signal to the handler function
        self.emitter.signal.connect(self.handle_signal)

        # Create a simple UI with two buttons
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        # Button to emit signal with a dictionary
        dict_button = QPushButton("Emit with Dict")
        dict_button.clicked.connect(self.emit_with_dict)
        layout.addWidget(dict_button)

        # Button to emit signal with kwargs
        kwargs_button = QPushButton("Emit with kwargs")
        kwargs_button.clicked.connect(self.emit_with_kwargs)
        layout.addWidget(kwargs_button)

        central_widget.setLayout(layout)

    def emit_with_dict(self):
        # Emit the signal with a dictionary
        self.emitter.emit_dict({"name": "Alice", "age": 30, "location": "Wonderland"})

    def emit_with_kwargs(self):
        # Emit the signal with keyword arguments
        self.emitter.emit_kwargs(name="Bob", age=25, location="Narnia")

    def handle_signal(self, data):
        # Handle both dict and kwargs cases
        if isinstance(data, dict):
            print("Received a dictionary:")
            for key, value in data.items():
                print(f"{key}: {value}")
        else:
            print("Received something else:", data)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
