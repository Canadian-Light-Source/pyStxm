"""
Created on 2012-12-21

@author: bergr
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PIL import Image
from PIL import ImageQt
import tifffile
import scipy.misc
import numpy as np


def get_image_details_dict():
    """
    create a standard dict for containing image information
    """
    img_details = {}
    img_details["image.bits"] = None
    img_details["image.filename"] = None
    img_details["image.format"] = None
    img_details["image.size"] = None
    img_details["image.dpi"] = None
    img_details["image.mode"] = None
    return img_details

def array_to_jpg(fpath, data):
    scipy.misc.imsave(fpath, data)

def array_to_tiff_file(file_path, array):
    tifffile.imwrite(file_path, array)

def image_to_array(image):
    arr = np.array(image.getdata()).reshape(image.size[::-1])
    return arr


def array_to_image(data, flip_ud=False):
    # must normalize to 0->255
    max = int(data.max())
    if max == 0:
        max = 255

    # must be dtype uint8
    data = np.multiply(data, 255 / max).astype(np.uint8)

    # data *= 255 / max
    # must flip it upside down
    if flip_ud:
        data = np.flipud(data).copy()
    # turn array into image
    im = Image.fromarray(data, mode="L")
    return im


# im.save('test.tif')


def array_to_qimage(arr):
    h, w = arr.shape
    arr = np.require(arr, np.uint32, "C")
    qi = QtGui.QImage(arr.data, w, h, QtGui.QImage.Format_RGB32)
    qi.ndarray = arr
    # qi.setNumColors(256)
    for y in range(h):
        for x in range(w):
            val = qi.pixel(x, y)
            qi.setPixel(QtCore.QPoint(x, y), QtGui.qRgb(val, val, val))
    return qi


def array_to_gray_qimage(arr):
    arr = np.array(arr, dtype=np.float32)  # Ensure numeric type
    arr = np.where(arr == None, np.nan, arr)  # Replace None with np.nan

    denom = arr.max() - arr.min()
    if denom <= 0:
        qi = QtGui.QImage(
            arr.data,
            arr.shape[1],
            arr.shape[0],
            arr.shape[1],
            QtGui.QImage.Format_Indexed8,
        )
    else:
        arr = np.nan_to_num(arr, nan=1)
        _min = 1 if arr.min() == 0 else arr.min()
        _max = max_with_nans(arr)
        if np.isnan(_max):
            _max = 1
        else:
            _max = arr.max()
        if (_max - _min) == 0.0:
            _max = 2
        im = np.uint8(((arr - _min) * 255 / (_max - _min)))
        qi = QtGui.QImage(
            im.data, im.shape[1], im.shape[0], im.shape[1], QtGui.QImage.Format_Indexed8
        )
    return qi

def max_with_nans(arr):
    # Replace NaN values with a very low value
    arr_with_low_values = np.nan_to_num(arr, nan=-np.inf)
    # Calculate maximum value
    max_val = arr_with_low_values.max()
    # Check if all values are NaNs
    #all_nans = np.all(np.isnan(arr))
    all_nans = np.all(np.isnan(arr.astype(float)))
    # if all_nans:
    #     print("All values in the array are NaNs.")
    # else:
    #     print("Maximum value (NaN treated as low):", max_val)
    return max_val

def array_to_gray_qpixmap(arr):
    qi = array_to_gray_qimage(arr)
    # convert it to a QPixmap for display:
    pmap = QtGui.QPixmap.fromImage(qi)
    return pmap


def array_to_qpixmap(gray):
    """Convert the 2D numpy array `gray` into a 8-bit QImage with a gray
    colormap.  The first dimension represents the vertical image axis."""

    if len(gray.shape) != 2:
        raise ValueError("gray2QImage can only convert 2D arrays")
        return

    qimg = array_to_qimage(gray)

    pixmap = QtGui.QPixmap.fromImage(qimg, QtCore.Qt.MonoOnly)
    return pixmap

def data_to_rgb(data0, alpha=False):
    """Interpret an MxNxP array as an MxNx3 RGB image (vectorized)."""
    data = np.nan_to_num(data0, copy=True, nan=0.)
    N = data.shape[2]
    C = hsv_cmap(N)  # shape (N, 3)
    # Vectorized multiplication and sum over the last axis
    RGB = np.tensordot(data, C, axes=([2], [0]))  # shape (M, N, 3)
    RGB_sum = np.sum(C, axis=0)
    RGB = RGB / RGB_sum
    RGB = RGB / np.amax(RGB)
    if alpha:
        return (255 * np.dstack((RGB, np.ones(RGB.shape[:2])))).astype(np.int64)
    else:
        return (255 * RGB).astype(np.int64)


def numpy_rgb_to_qpixmap(rgb_array, target_width=150, target_height=150):
    if rgb_array.dtype != np.uint8:
        rgb_array = rgb_array.astype(np.uint8)
    height, width = rgb_array.shape[:2]
    if rgb_array.shape[2] == 3:
        fmt = QtGui.QImage.Format_RGB888
    elif rgb_array.shape[2] == 4:
        fmt = QtGui.QImage.Format_RGBA8888
    else:
        raise ValueError("Array must have 3 (RGB) or 4 (RGBA) channels")
    rgb_array = np.ascontiguousarray(rgb_array, dtype=np.uint8)
    qimg = QtGui.QImage(rgb_array.data, width, height, rgb_array.strides[0], fmt)
    pixmap = QtGui.QPixmap.fromImage(qimg)
    if target_width is not None and target_height is not None:
        pixmap = pixmap.scaled(target_width, target_height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
    return pixmap

def hsv_to_rgb(h, s, v):
    if s == 0.0: return (v, v, v)
    i = int(h * 6.)  # XXX assume int() truncates!
    f = (h * 6.) - i;
    p, q, t = v * (1. - s), v * (1. - s * f), v * (1. - s * (1. - f));
    i %= 6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    if i == 5: return (v, p, q)


def hsv_cmap(N):
    """Select N colour hues and return RGB values."""
    if N == 2:
        return np.array([[1, 1, 0], [0, 1, 1]])
    C = np.empty((N, 3))
    for k in range(N):
        val = k / (N * (1.3333333333333) - 1)
        C[k, :] = hsv_to_rgb(val - int(val), 1., 1.)
    return C

__all__ = ["image_to_array", "array_to_image", "array_to_qimage", "array_to_qpixmap"]


class TestWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.scene = QtWidgets.QGraphicsScene()
        self.view = QtWidgets.QGraphicsView(self.scene)
        self.button = QtWidgets.QPushButton("Do test")

        # self.listWidget = QtWidgets.QListWidget()
        # self.listWidget.setWindowTitle('Example List')
        # self.listWidget.setMinimumSize(600, 400)
        # self.model = QtWidgets.QStandardItemModel()
        # Apply the model to the list view
        # self.listWidget.setModel(self.model)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.view)
        # layout.addWidget(self.listWidget)
        self.setLayout(layout)

        self.button.clicked.connect(self.do_array_test)

    def add_to_list(self, name, widget):
        # n_item = QtWidgets.QStandardItem(name)
        # i_item = QtWidgets.QStandardItem(wdgt)

        # add a checkbox to it
        # n_item.setCheckable(True)

        # Add the item to the model
        # self.model.appendRow(n_item)
        # self.model.appendColumn([i_item])
        item = QtWidgets.QListWidgetItem("")
        # self.connect(widget, QtCore.SIGNAL("clicked(int)"), self.on_clicked)
        widget.clicked.connect(self.on_clicked)
        # self.connect(widget, QtCore.SIGNAL("favoriteChange(bool)"), self._favorite_changed)
        # self.connect(widget, QtCore.SIGNAL("deleteMe(QListWidgetItem)"), self._delete_recent_project_item)
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, widget)

    def on_clicked(self, idx):
        print("%d clicked")

    def do_test(self):
        img = Image.open("image.png")
        self.display_image(img)

    # 		enhancer = ImageEnhance.Brightness(img)
    # 		for i in range(1, 8):
    # 			img = enhancer.enhance(i)
    # 			self.display_image(img)
    # 			QtCore.QCoreApplication.processEvents()  # let Qt do his work
    # 			time.sleep(0.5)

    def do_array_test(self):
        from sm.stxm_control.widgets.imgInfo import previewImageWidget

        data = np.random.randint(0, 2**16 - 1, (200, 200))
        h, w = data.shape
        pixmap = array_to_qpixmap(data)
        self.scene.addPixmap(pixmap)
        # self.view.fitInView(QtCore.QRectF(0, 0, w, h), QtCore.Qt.KeepAspectRatio)
        self.scene.update()

    # prevWdgt = previewImageWidget('200 x 200 | 535.3 eV | 3.5 ms', data)
    # self.add_to_list('name1', prevWdgt)

    def display_image(self, img):
        self.scene.clear()
        w, h = img.size
        self.imgQ = ImageQt.ImageQt(
            img
        )  # we need to hold reference to imgQ, or it will crash
        pixMap = QtGui.QPixmap.fromImage(self.imgQ)
        self.scene.addPixmap(pixMap)
        self.view.fitInView(QtCore.QRectF(0, 0, w, h), QtCore.Qt.KeepAspectRatio)
        self.scene.update()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    widget = TestWidget()
    widget.resize(640, 480)
    widget.show()

    sys.exit(app.exec_())
