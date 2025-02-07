
from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QImage
import tifffile

def numpy_array_to_qpixmap(numpy_array):
    # Scale the values to uint8
    scaled_array = ((numpy_array - np.min(numpy_array)) / (np.max(numpy_array) - np.min(numpy_array))) * 255
    scaled_array = scaled_array.astype(np.uint8)

    # Convert the numpy array to a QImage
    height, width = scaled_array.shape
    bytes_per_line = width
    qimage = QImage(scaled_array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)

    # Convert the QImage to a QPixmap
    qpixmap = QPixmap.fromImage(qimage)
    qpixmap = qpixmap.scaled(
            QtCore.QSize(QtCore.QSize(512, 512)),
            QtCore.Qt.IgnoreAspectRatio,
        )

    return qpixmap


def main():
    # Create the application
    app = QApplication(sys.argv)

    # Load the TIFF file into a NumPy array
    tiff_file = "T:/operations/STXM-data/ASTXM_upgrade_tmp/2024/guest/0319/A240319044/00_00/A240319044_000000.tiff"
    uint16_array = tifffile.imread(tiff_file)

    # Convert numpy array to QPixmap
    qpixmap = numpy_array_to_qpixmap(uint16_array)

    # Create a QLabel to display the image
    label = QLabel()
    label.setMaximumSize(512,512)
    label.setPixmap(qpixmap)

    # Create a layout and add the label to it
    layout = QVBoxLayout()
    layout.addWidget(label)

    # Create a main QWidget to contain the layout
    main_window = QWidget()
    main_window.setLayout(layout)
    main_window.setWindowTitle('Array Image Viewer')
    main_window.show()

    # Start the application event loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

# if __name__ == '__main__':
#     # Load the TIFF image into a QPixmap
#
#
#     # Set the pixmap on the QLabel
#     self.camImgLbl.setPixmap(pixmap)
#     self.camImgLbl.setToolTip(tiff_file)